import argparse
import os
import sys
import logging
from datetime import datetime

from dotenv import load_dotenv

from fetch_emails import fetch_unread
from gmail_api import fetch_unread_gmail_api
from parser import parse_email
from summarizer import init_summarizer
from storage import is_processed, save_email, update_notion_page_id, get_notion_page_id
from notion_writer import init_notion_writer
from ner_extras import extract_ner_data, get_primary_deadline
from utils import parse_date

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="Fetch unread Gmail emails, summarize, and store to SQLite/Notion")
    parser.add_argument("--limit", type=int, default=10, help="Max unread emails to process")
    parser.add_argument("--dry-run", action="store_true", help="Do not save to DB; print only")
    parser.add_argument("--notion", action="store_true", help="Enable Notion integration")
    parser.add_argument("--gmail-api", action="store_true", help="Use Gmail API instead of IMAP")
    parser.add_argument("--query", type=str, help="Gmail search query (e.g., 'after:2025/09/15')")
    parser.add_argument("--order", type=str, choices=['recent', 'oldest'], default='recent', help="Order results by date (recent or oldest)")
    args = parser.parse_args()

    logger.info("Starting Email to Notion Summary processing...")
    logger.info(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    logger.info(f"Limit: {args.limit} emails")
    logger.info(f"Notion: {'Enabled' if args.notion else 'Disabled'}")
    logger.info(f"Gmail API: {'Enabled' if args.gmail_api else 'Disabled (using IMAP)'}")

    # Initialize components
    logger.info("Initializing summarizer...")
    summarizer = init_summarizer(device=os.getenv('DEVICE', 'cpu'))
    
    # Initialize Notion writer if requested
    notion_writer = None
    notion_available = False
    if args.notion:
        logger.info("Initializing Notion writer...")
        notion_writer = init_notion_writer()
        if notion_writer:
            notion_available = True
            logger.info("Notion integration enabled")
        else:
            logger.warning("Notion integration disabled due to missing credentials")
            if not args.dry_run:
                logger.warning("Running without Notion integration - emails will only be saved to database")

    # Fetch emails
    if args.query:
        logger.info(f"Fetching emails with query: {args.query}")
    else:
        logger.info("Fetching unread emails...")
    
    try:
        if args.gmail_api:
            emails = fetch_unread_gmail_api(limit=args.limit, query=args.query)
        else:
            emails = fetch_unread(limit=args.limit, query=args.query)
    except Exception as e:
        logger.error(f"Failed to fetch emails: {e}")
        return

    if not emails:
        logger.info("No unread emails found.")
        return

    logger.info(f"Found {len(emails)} unread emails")

    # Process emails
    processed_count = 0
    skipped_count = 0
    notion_count = 0

    for i, email_data in enumerate(emails, 1):
        message_id = email_data.get('message_id')
        raw_bytes = email_data.get('raw_bytes', b'')

        if not message_id:
            logger.warning(f"Skipping email {i} with no message_id")
            continue

        logger.info(f"Processing email {i}/{len(emails)}: {message_id}")

        # Check if already processed
        if is_processed(message_id):
            logger.info(f"Already processed, skipping: {message_id}")
            skipped_count += 1
            continue

        try:
            # Parse email
            subject, from_email, date_header, body_text, links = parse_email(raw_bytes)
            logger.info(f"Parsed: {subject[:60]}...")

            # Summarize
            logger.info("Summarizing...")
            summary = summarizer.summarize(body_text, max_length=120)

            # Extract NER data (dates and action items)
            logger.info("Extracting dates and action items...")
            ner_data = extract_ner_data(body_text)
            deadline = get_primary_deadline(ner_data['dates'])

            # Create record
            record = {
                'message_id': message_id,
                'subject': subject,
                'sender': from_email,
                'date': parse_date(date_header) or date_header,
                'summary': summary,
                'body': body_text,
                'links': "\n".join(links or []),
                'processed_at': datetime.utcnow().isoformat(),
                'deadline': deadline.isoformat() if deadline else None,
                'action_items': "\n".join([item['text'] for item in ner_data['action_items']]),
                'ner_summary': ner_data['summary']
            }

            # Save to database
            if not args.dry_run:
                logger.info("Saving to database...")
                save_email(record)
                logger.info("Saved to database")

            # Handle Notion page creation
            if args.notion:
                if args.dry_run:
                    # Dry run mode - show what would be created
                    logger.info("DRY RUN - Creating Notion page payload...")
                    if notion_writer:
                        payload = notion_writer.create_email_page_dry_run(record)
                        logger.info(f"DRY RUN - Notion payload created for {message_id}")
                    else:
                        logger.warning("DRY RUN - Notion writer not available, cannot create payload")
                elif notion_writer:
                    # Live mode with Notion writer available
                    logger.info("Creating Notion page...")
                    notion_page_id = notion_writer.create_email_page(record)
                    if notion_page_id:
                        update_notion_page_id(message_id, notion_page_id)
                        notion_count += 1
                        logger.info(f"Created Notion page: {notion_page_id}")
                    else:
                        logger.warning("Failed to create Notion page")
                else:
                    # Live mode but no Notion writer available
                    logger.warning("Notion integration requested but not available - skipping Notion page creation")

            processed_count += 1
            logger.info(f"Completed processing: {message_id}")

        except Exception as e:
            logger.error(f"Error processing email {message_id}: {e}")
            continue

    # Print summary
    logger.info(f"\n{'='*50}")
    logger.info(f"PROCESSING COMPLETE")
    logger.info(f"{'='*50}")
    logger.info(f"Total emails fetched: {len(emails)}")
    logger.info(f"Already processed (skipped): {skipped_count}")
    logger.info(f"Newly processed: {processed_count}")
    if notion_writer:
        logger.info(f"Notion pages created: {notion_count}")

    # Print sample of processed emails
    if processed_count > 0:
        logger.info(f"\nSample processed emails:")
        # This would require querying the database to show samples
        # For now, just show the count
        logger.info(f"Check the database 'emails.db' for {processed_count} processed emails")


if __name__ == "__main__":
    main()




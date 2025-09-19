"""
Notion integration for writing email summaries to Notion database.

Requires NOTION_TOKEN and NOTION_DATABASE_ID environment variables.
"""

import os
import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from notion_client import Client
from notion_client.errors import APIResponseError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NotionWriter:
    def __init__(self):
        self.token = os.getenv('NOTION_TOKEN')
        self.database_id = os.getenv('NOTION_DATABASE_ID')
        
        if not self.token or not self.database_id:
            raise ValueError("NOTION_TOKEN and NOTION_DATABASE_ID must be set in environment")
        
        self.client = Client(auth=self.token)
        self._verify_database_access()
    
    def _verify_database_access(self):
        """Verify that we can access the Notion database."""
        try:
            self.client.databases.retrieve(database_id=self.database_id)
            logger.info(f"Successfully connected to Notion database: {self.database_id}")
        except APIResponseError as e:
            if e.status == 404:
                raise ValueError(f"Notion database {self.database_id} not found. Check the database ID.")
            elif e.status == 401:
                raise ValueError("Invalid Notion token. Check your NOTION_TOKEN.")
            else:
                raise ValueError(f"Error accessing Notion database: {e}")
    
    def _retry_with_backoff(self, func, max_retries: int = 3, base_delay: float = 1.0):
        """Retry function with exponential backoff for rate limiting."""
        for attempt in range(max_retries):
            try:
                return func()
            except APIResponseError as e:
                if e.status == 429:  # Rate limited
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(f"Rate limited. Retrying in {delay} seconds... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(delay)
                        continue
                    else:
                        logger.error(f"Max retries exceeded for rate limiting: {e}")
                        raise
                else:
                    raise
            except Exception as e:
                logger.error(f"Unexpected error in Notion API call: {e}")
                raise
    
    def _create_bullet_points(self, summary: str) -> List[Dict[str, Any]]:
        """Convert summary into bullet points for Notion blocks."""
        if not summary:
            return []
        
        # Split summary into sentences and create bullet points
        sentences = [s.strip() for s in summary.split('.') if s.strip()]
        bullet_points = []
        
        for sentence in sentences[:5]:  # Limit to 5 bullet points
            bullet_points.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": sentence}}]
                }
            })
        
        return bullet_points
    
    def _create_links_section(self, links: str) -> List[Dict[str, Any]]:
        """Create a links section for Notion blocks."""
        if not links:
            return []
        
        link_list = [link.strip() for link in links.split('\n') if link.strip()]
        if not link_list:
            return []
        
        blocks = [
            {
                "object": "block",
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [{"type": "text", "text": {"content": "Links"}}]
                }
            }
        ]
        
        for link in link_list[:10]:  # Limit to 10 links
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": link, "link": {"url": link}}}]
                }
            })
        
        return blocks
    
    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse date string to ISO format for Notion."""
        if not date_str:
            return None
        
        try:
            # Try parsing with dateparser first
            import dateparser
            parsed = dateparser.parse(date_str)
            if parsed:
                return parsed.isoformat()
        except Exception:
            pass
        
        # Fallback to basic parsing
        try:
            from datetime import datetime
            # Try common formats
            for fmt in ['%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S']:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.isoformat()
                except ValueError:
                    continue
        except Exception:
            pass
        
        return None
    
    def _generate_ai_title(self, subject: str, body: str) -> str:
        """
        Generate a one-line AI summary for the Notion page title.
        Uses subject + first few lines of body to create a concise title.
        """
        try:
            # Import summarizer
            from summarizer import init_summarizer
            
            # Initialize summarizer
            summarizer = init_summarizer(device=os.getenv('DEVICE', 'cpu'))
            
            # Combine subject and first few lines of body
            first_lines = '\n'.join(body.split('\n')[:3])  # First 3 lines
            combined_text = f"Subject: {subject}\n\n{first_lines}"
            
            # Generate a very short summary (one line)
            title = summarizer.summarize(combined_text, max_length=60)
            
            # Clean up the title - remove newlines and extra spaces
            title = ' '.join(title.split())
            
            # Truncate if too long
            if len(title) > 100:
                title = title[:97] + "..."
            
            return title if title else subject[:100]
            
        except Exception as e:
            logger.warning(f"Failed to generate AI title: {e}")
            # Fallback to subject or first line of body
            if subject:
                return subject[:100]
            elif body:
                first_line = body.split('\n')[0].strip()
                return first_line[:100] if first_line else "Email Summary"
            else:
                return "Email Summary"
    
    def create_email_page(self, email_record: Dict[str, Any]) -> Optional[str]:
        """
        Create a Notion page for an email record.
        
        Returns the Notion page ID if successful, None if failed.
        """
        try:
            # Extract data from email record
            message_id = email_record.get('message_id', '')
            subject = email_record.get('subject', 'No Subject')
            sender = email_record.get('sender', 'Unknown')
            date_str = email_record.get('date', '')
            summary = email_record.get('summary', '')
            body = email_record.get('body', '')
            links = email_record.get('links', '')
            
            # Generate AI-powered title
            title = self._generate_ai_title(subject, body)
            
            # Parse date
            parsed_date = self._parse_date(date_str)
            
            properties = {
                "Title": {
                    "title": [{"type": "text", "text": {"content": title}}]
                },
                "Sender": {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content": sender}  # Use the already formatted sender from parser
                    }]
                },
                "Date": {
                    "date": {"start": parsed_date} if parsed_date else None
                },
                "Status": {
                    "status": {"name": "New"}
                },
                "Deadline": {
                    "date": {"start": email_record.get("deadline")} if email_record.get("deadline") else None
                },
                "Short Summary (about)": {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content": summary[:200]}  # store a short snippet
                    }]
                }
            }

            
            # Add date if parsed successfully
            if parsed_date:
                properties["Date"] = {
                    "date": {"start": parsed_date}
                }
            
            # Create child blocks
            children = []
            
            # Add bullet points from summary
            bullet_points = self._create_bullet_points(summary)
            children.extend(bullet_points)
            
            # Add full email text as quote
            if body:
                children.append({
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [{"type": "text", "text": {"content": "Full Email Text"}}]
                    }
                })
                
                # Split body into chunks if too long
                body_chunks = [body[i:i+2000] for i in range(0, len(body), 2000)]
                for chunk in body_chunks:
                    children.append({
                        "object": "block",
                        "type": "quote",
                        "quote": {
                            "rich_text": [{"type": "text", "text": {"content": chunk}}]
                        }
                    })
            
            # Add links section
            links_blocks = self._create_links_section(links)
            children.extend(links_blocks)
            
            # Create the page
            def _create_page():
                return self.client.pages.create(
                    parent={"database_id": self.database_id},
                    properties=properties,
                    children=children
                )
            
            result = self._retry_with_backoff(_create_page)
            page_id = result.get('id')
            
            logger.info(f"Created Notion page for email {message_id}: {page_id}")
            return page_id
            
        except Exception as e:
            logger.error(f"Failed to create Notion page for email {message_id}: {e}")
            return None
    
    def page_exists(self, message_id: str) -> bool:
        """Check if a page already exists for this message_id."""
        try:
            # Query the database for pages with this message_id
            def _query_pages():
                return self.client.databases.query(
                    database_id=self.database_id,
                    filter={
                        "property": "Title",
                        "title": {"contains": message_id}
                    }
                )
            
            result = self._retry_with_backoff(_query_pages)
            return len(result.get('results', [])) > 0
            
        except Exception as e:
            logger.error(f"Error checking if page exists for {message_id}: {e}")
            return False
    
    def create_email_page_dry_run(self, email_record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a dry-run payload for an email record without actually creating the page.
        
        Returns the payload that would be sent to Notion API.
        """
        try:
            # Extract data from email record
            message_id = email_record.get('message_id', '')
            subject = email_record.get('subject', 'No Subject')
            sender = email_record.get('sender', 'Unknown')
            date_str = email_record.get('date', '')
            summary = email_record.get('summary', '')
            body = email_record.get('body', '')
            links = email_record.get('links', '')
            
            # Generate AI-powered title
            title = self._generate_ai_title(subject, body)
            
            # Parse date
            parsed_date = self._parse_date(date_str)
            
            properties = {
                "Title": {
                    "title": [{"type": "text", "text": {"content": title}}]
                },
                "Sender": {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content": sender}
                    }]
                },
                "Date": {
                    "date": {"start": parsed_date} if parsed_date else None
                },
                "Status": {
                    "status": {"name": "New"}
                },
                "Deadline": {
                    "date": {"start": email_record.get("deadline")} if email_record.get("deadline") else None
                },
                "Short Summary (about)": {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content": summary[:200]}
                    }]
                }
            }
            
            # Create child blocks
            children = []
            
            # Add bullet points from summary
            bullet_points = self._create_bullet_points(summary)
            children.extend(bullet_points)
            
            # Add full email text as quote
            if body:
                children.append({
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [{"type": "text", "text": {"content": "Full Email Text"}}]
                    }
                })
                
                # Split body into chunks if too long
                body_chunks = [body[i:i+2000] for i in range(0, len(body), 2000)]
                for chunk in body_chunks:
                    children.append({
                        "object": "block",
                        "type": "quote",
                        "quote": {
                            "rich_text": [{"type": "text", "text": {"content": chunk}}]
                        }
                    })
            
            # Add links section
            links_blocks = self._create_links_section(links)
            children.extend(links_blocks)
            
            # Return the payload that would be sent to Notion
            payload = {
                "parent": {"database_id": self.database_id},
                "properties": properties,
                "children": children
            }
            
            logger.info(f"DRY RUN - Would create Notion page for email {message_id}")
            logger.info(f"DRY RUN - Title: {title}")
            logger.info(f"DRY RUN - Sender: {sender}")
            logger.info(f"DRY RUN - Payload size: {len(str(payload))} characters")
            
            return payload
            
        except Exception as e:
            logger.error(f"Failed to create dry-run payload for email {message_id}: {e}")
            return {}


def init_notion_writer() -> Optional[NotionWriter]:
    """Initialize Notion writer if credentials are available."""
    try:
        return NotionWriter()
    except ValueError as e:
        logger.warning(f"Notion integration disabled: {e}")
        return None

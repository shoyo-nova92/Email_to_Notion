#!/usr/bin/env python3
"""
Background scheduler for Email to Notion Summary.

Runs the main processing script at regular intervals.
"""

import os
import sys
import time
import signal
import logging
from datetime import datetime

import schedule
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scheduler.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Global flag for graceful shutdown
shutdown_requested = False


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global shutdown_requested
    logger.info(f"Received signal {signum}. Initiating graceful shutdown...")
    shutdown_requested = True


def run_email_processing():
    """Run the main email processing script."""
    try:
        logger.info("Starting scheduled email processing...")
        
        # Import and run main processing
        from src.main import main
        
        # Set up arguments for main()
        gmail_api_enabled = os.getenv('GMAIL_USE_API', 'false').lower() == 'true'
        if gmail_api_enabled:
            sys.argv = ['main.py', '--notion', '--gmail-api', '--limit', '20']
        else:
            sys.argv = ['main.py', '--notion', '--limit', '20']
        
        # Run the main function
        main()
        
        logger.info("Scheduled email processing completed successfully")
        
    except Exception as e:
        logger.error(f"Error in scheduled email processing: {e}")
        # Don't raise the exception to prevent scheduler from stopping


def main():
    """Main scheduler function."""
    # Load environment variables
    load_dotenv()
    
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Get configuration from environment
    interval_minutes = int(os.getenv('SCHED_INTERVAL_MINUTES', '30'))
    notion_enabled = os.getenv('NOTION_TOKEN') and os.getenv('NOTION_DATABASE_ID')
    
    logger.info(f"Starting Email to Notion Summary Scheduler")
    logger.info(f"Interval: {interval_minutes} minutes")
    logger.info(f"Notion integration: {'Enabled' if notion_enabled else 'Disabled'}")
    
    # Schedule the job
    schedule.every(interval_minutes).minutes.do(run_email_processing)
    
    # Run immediately on startup
    logger.info("Running initial email processing...")
    run_email_processing()
    
    # Main scheduler loop
    logger.info("Scheduler started. Press Ctrl+C to stop.")
    
    try:
        while not shutdown_requested:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt. Shutting down...")
    except Exception as e:
        logger.error(f"Unexpected error in scheduler: {e}")
    finally:
        logger.info("Scheduler stopped.")


if __name__ == "__main__":
    main()

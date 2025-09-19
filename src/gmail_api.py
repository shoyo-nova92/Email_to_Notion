"""
Gmail API integration as an alternative to IMAP.

Requires Gmail API credentials and OAuth flow setup.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Gmail API scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


class GmailAPIClient:
    def __init__(self):
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Gmail API using OAuth2."""
        creds = None
        token_path = 'token.json'
        credentials_path = 'credentials.json'
        
        # Load existing token
        if os.path.exists(token_path):
            try:
                creds = Credentials.from_authorized_user_file(token_path, SCOPES)
                logger.info("Loaded existing Gmail API credentials")
            except Exception as e:
                logger.warning(f"Error loading existing credentials: {e}")
        
        # If no valid credentials, run OAuth flow
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    logger.info("Refreshed Gmail API credentials")
                except Exception as e:
                    logger.warning(f"Error refreshing credentials: {e}")
                    creds = None
            
            if not creds:
                if not os.path.exists(credentials_path):
                    raise FileNotFoundError(
                        f"Gmail API credentials file not found: {credentials_path}\n"
                        "Please download credentials.json from Google Cloud Console."
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
                logger.info("Completed Gmail API OAuth flow")
            
            # Save credentials for next run
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
            logger.info(f"Saved Gmail API credentials to {token_path}")
        
        # Build the Gmail service
        try:
            self.service = build('gmail', 'v1', credentials=creds)
            logger.info("Gmail API service initialized successfully")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Gmail API service: {e}")
    
    def fetch_unread_emails(self, limit: int = 50, query: str = None) -> List[Dict[str, Any]]:
        """
        Fetch unread emails using Gmail API.
        
        Returns list of dictionaries with keys:
        - message_id: Gmail message ID
        - raw_bytes: Raw RFC822 message bytes
        - flags: Gmail labels
        - date: Internal date
        """
        if not self.service:
            raise RuntimeError("Gmail API service not initialized")
        
        try:
            # Build search query
            if query:
                # Use the provided query directly (Gmail API supports Gmail search syntax)
                search_query = query
                logger.info(f"Searching with Gmail query: {search_query}")
            else:
                # Default to unread messages
                search_query = 'is:unread'
                logger.info("Searching for unread messages")
            
            results = self.service.users().messages().list(
                userId='me',
                q=search_query,
                maxResults=limit
            ).execute()
            
            messages = results.get('messages', [])
            if not messages:
                logger.info("No unread messages found")
                return []
            
            logger.info(f"Found {len(messages)} unread messages")
            
            # Fetch full message details
            email_data = []
            allowed_domains = ["bmu.edu.in", "classroom.google.com"]
            for msg in messages:
                try:
                    # Get full message
                    message = self.service.users().messages().get(
                        userId='me',
                        id=msg['id'],
                        format='raw'
                    ).execute()
                    
                    # Decode raw message
                    import base64
                    raw_bytes = base64.urlsafe_b64decode(message['raw'])
                    
                    # Get message metadata
                    headers = message.get('payload', {}).get('headers', [])
                    message_id = None
                    date_str = None
                    
                    for header in headers:
                        if header['name'].lower() == 'message-id':
                            message_id = header['value']
                        elif header['name'].lower() == 'date':
                            date_str = header['value']
                    
                    # Use Gmail message ID as fallback
                    if not message_id:
                        message_id = f"gmail-{msg['id']}"
                    
                    # Parse date
                    parsed_date = None
                    if date_str:
                        try:
                            from dateparser import parse
                            parsed_date = parse(date_str)
                        except Exception:
                            pass
                    
                    # Filter by allowed sender domains
                    try:
                        import email as _email
                        _msg = _email.message_from_bytes(raw_bytes)
                        sender = (_msg.get('From') or '').lower()
                    except Exception:
                        sender = ''

                    if not any(domain in sender for domain in allowed_domains):
                        logger.info(f"Skipping email from {sender} (not in allowed domains)")
                        continue

                    email_data.append({
                        'message_id': message_id,
                        'raw_bytes': raw_bytes,
                        'flags': message.get('labelIds', []),
                        'date': parsed_date or datetime.now()
                    })
                    
                except Exception as e:
                    logger.error(f"Error fetching message {msg['id']}: {e}")
                    continue
            
            logger.info(f"Successfully fetched {len(email_data)} email messages")
            return email_data
            
        except HttpError as e:
            logger.error(f"Gmail API error: {e}")
            raise RuntimeError(f"Gmail API error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error fetching emails: {e}")
            raise RuntimeError(f"Unexpected error fetching emails: {e}")


def fetch_unread_gmail_api(limit: int = 50, query: str = None) -> List[Dict[str, Any]]:
    """
    Convenience function to fetch unread emails using Gmail API.
    
    Returns same format as IMAP fetch for compatibility.
    """
    try:
        client = GmailAPIClient()
        return client.fetch_unread_emails(limit=limit, query=query)
    except Exception as e:
        logger.error(f"Gmail API fetch failed: {e}")
        raise


def setup_gmail_api_credentials():
    """
    Helper function to guide users through Gmail API setup.
    """
    print("Gmail API Setup Instructions:")
    print("1. Go to Google Cloud Console (https://console.cloud.google.com/)")
    print("2. Create a new project or select existing one")
    print("3. Enable Gmail API for your project")
    print("4. Go to Credentials > Create Credentials > OAuth 2.0 Client IDs")
    print("5. Choose 'Desktop application' as application type")
    print("6. Download the credentials JSON file")
    print("7. Rename it to 'credentials.json' and place in project root")
    print("8. Run this script again to complete OAuth flow")
    print("\nNote: Make sure to add 'http://localhost:8080' to authorized redirect URIs")

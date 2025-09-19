import os
from typing import List, Dict, Any

from imapclient import IMAPClient


def _get_env(name: str, default: str = "") -> str:
    value = os.getenv(name, default)
    if value is None:
        return default
    return value


def fetch_unread(limit: int = 20, query: str = None) -> List[Dict[str, Any]]:
    """
    Connects to Gmail via IMAP and fetches unread messages.

    Returns a list of dictionaries with keys:
      - message_id: The RFC822 Message-ID header if available, else the IMAP UID as fallback
      - raw_bytes: Raw RFC822 message bytes
      - flags: IMAP flags
      - date: Internal IMAP date (python datetime)

    Note: This uses username/password auth (App Password strongly recommended).
    """

    email_addr = _get_env("GMAIL_EMAIL")
    app_password = _get_env("GMAIL_APP_PASSWORD")
    host = _get_env("IMAP_HOST", "imap.gmail.com")
    folder = _get_env("IMAP_FOLDER", "INBOX")

    if not email_addr or not app_password:
        raise RuntimeError("GMAIL_EMAIL and GMAIL_APP_PASSWORD must be set in environment")

    print(f"Connecting to IMAP server {host}...")
    with IMAPClient(host, ssl=True) as client:
        client.login(email_addr, app_password)
        client.select_folder(folder)

        # Build search criteria
        if query:
            print(f"Searching with query: {query}")
            # Convert Gmail-style query to IMAP search criteria
            search_criteria = []
            if 'after:' in query:
                # Extract date from after:YYYY/MM/DD format
                import re
                date_match = re.search(r'after:(\d{4}/\d{1,2}/\d{1,2})', query)
                if date_match:
                    date_str = date_match.group(1)
                    # Convert to IMAP date format (DD-Mon-YYYY)
                    from datetime import datetime
                    try:
                        dt = datetime.strptime(date_str, '%Y/%m/%d')
                        imap_date = dt.strftime('%d-%b-%Y')
                        search_criteria.append(b'SINCE')
                        search_criteria.append(imap_date.encode())
                    except ValueError:
                        print(f"Invalid date format in query: {date_str}")
            
            if 'from:@bmu.edu' in query or 'from:@bmu.edu.in' in query:
                search_criteria.append(b'FROM')
                search_criteria.append(b'bmu.edu.in')
            elif 'from:@classroom.google.com' in query:
                search_criteria.append(b'FROM')
                search_criteria.append(b'classroom.google.com')
            
            # If no specific criteria, default to UNSEEN
            if not search_criteria:
                search_criteria = [b'UNSEEN']
        else:
            print("Searching for UNSEEN messages...")
            search_criteria = [b'UNSEEN']
        
        uids = client.search(search_criteria)
        if not uids:
            print("No messages found matching criteria.")
            return []

        # Limit to small batch for faster local runs
        uids = uids[: max(0, int(limit))]
        print(f"Fetching {len(uids)} message(s)...")

        messages = client.fetch(uids, [b'RFC822', b'FLAGS', b'INTERNALDATE'])

        results: List[Dict[str, Any]] = []
        allowed_domains = ["bmu.edu.in", "classroom.google.com"]
        for uid in uids:
            data = messages.get(uid, {})
            raw_bytes = data.get(b'RFC822', b'')
            flags = data.get(b'FLAGS', ())
            internal_date = data.get(b'INTERNALDATE')

            # Derive a message_id from headers if possible; fallback to UID
            msg_id = None
            try:
                import email
                msg = email.message_from_bytes(raw_bytes)
                msg_id = msg.get('Message-ID') or msg.get('Message-Id')
            except Exception:
                msg_id = None
            if not msg_id:
                msg_id = f"UID-{uid}"

            # Filter by allowed sender domains
            try:
                import email as _email
                _msg = _email.message_from_bytes(raw_bytes)
                sender = (_msg.get('From') or '').lower()
            except Exception:
                sender = ''

            if not any(domain in sender for domain in allowed_domains):
                print(f"Skipping email from {sender} (not in allowed domains)")
                continue

            results.append({
                "message_id": msg_id,
                "raw_bytes": raw_bytes,
                "flags": list(flags) if flags else [],
                "date": internal_date,
            })

        print(f"Fetched {len(results)} unread message(s).")
        return results




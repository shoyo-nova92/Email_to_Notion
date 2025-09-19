import email
import email.message
import re
from typing import Tuple, List, Optional

from bs4 import BeautifulSoup


_LINK_REGEX = re.compile(r"https?://\S+", re.IGNORECASE)


def _get_text_from_email(msg: email.message.Message) -> Tuple[str, Optional[str]]:
    """
    Prefer text/plain. If only text/html is available, convert it to text.
    Returns (body_text, content_type_used)
    """
    # If multipart, iterate parts
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == 'text/plain':
                try:
                    return part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', errors='replace'), 'text/plain'
                except Exception:
                    continue
        # If no text/plain, try html
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == 'text/html':
                try:
                    html = part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', errors='replace')
                    text = BeautifulSoup(html, 'html.parser').get_text("\n")
                    return text, 'text/html'
                except Exception:
                    continue
        return "", None
    # Not multipart
    ctype = msg.get_content_type()
    try:
        payload = msg.get_payload(decode=True)
        decoded = payload.decode(msg.get_content_charset() or 'utf-8', errors='replace') if isinstance(payload, (bytes, bytearray)) else str(payload)
    except Exception:
        decoded = ""
    if ctype == 'text/html':
        text = BeautifulSoup(decoded, 'html.parser').get_text("\n")
        return text, 'text/html'
    return decoded, ctype


def extract_links(text: str) -> List[str]:
    return _LINK_REGEX.findall(text or "")


def _parse_sender(from_header: str) -> str:
    """
    Parse the From header to extract a clean sender format.
    Returns format: "Name <email>" or "Unknown <email>" if name missing.
    """
    if not from_header:
        return "Unknown <unknown@example.com>"
    
    # Handle cases like "Name <email@domain.com>" or "email@domain.com"
    import re
    
    # Pattern to match "Name <email@domain.com>" or just "email@domain.com"
    email_pattern = r'<([^>]+@[^>]+)>'
    name_pattern = r'^([^<]+)<'
    
    # Extract email
    email_match = re.search(email_pattern, from_header)
    if email_match:
        email = email_match.group(1).strip()
    else:
        # No angle brackets, check if it's just an email
        if '@' in from_header and ' ' not in from_header:
            email = from_header.strip()
        else:
            return "Unknown <unknown@example.com>"
    
    # Extract name
    name_match = re.search(name_pattern, from_header)
    if name_match:
        name = name_match.group(1).strip().strip('"\'')
        if name and name != email:
            return f"{name} <{email}>"
    
    # If no name found, return just email
    return f"Unknown <{email}>"


def parse_email(raw_bytes: bytes) -> Tuple[str, str, str, str, List[str]]:
    """
    Parses raw RFC822 email bytes and returns:
    (subject, from_email, date_string, body_text, links)
    """
    msg = email.message_from_bytes(raw_bytes)
    subject = msg.get('Subject', '')
    from_header = msg.get('From', '')
    from_email = _parse_sender(from_header)
    date_str = msg.get('Date', '')

    body_text, _ = _get_text_from_email(msg)
    links = extract_links(body_text)
    return subject, from_email, date_str, body_text, links




from typing import Optional

import dateparser


def parse_date(date_str: str) -> Optional[str]:
    """
    Parses a date string from email headers into ISO format (UTC) if possible.
    Returns the original string if parsing fails.
    """
    if not date_str:
        return None
    dt = dateparser.parse(date_str)
    try:
        return dt.isoformat() if dt else date_str
    except Exception:
        return date_str




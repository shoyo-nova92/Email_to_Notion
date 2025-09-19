import os
import sqlite3
from datetime import datetime
from typing import Dict, Any, Optional


DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'emails.db')


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id TEXT UNIQUE,
            subject TEXT,
            sender TEXT,
            date TEXT,
            summary TEXT,
            body TEXT,
            links TEXT,
            processed_at TEXT,
            notion_page_id TEXT,
            deadline TEXT,
            action_items TEXT,
            ner_summary TEXT
        )
        """
    )
    return conn


def is_processed(message_id: str) -> bool:
    conn = _connect()
    try:
        cur = conn.execute("SELECT 1 FROM emails WHERE message_id = ?", (message_id,))
        row = cur.fetchone()
        return row is not None
    finally:
        conn.close()


def save_email(record: Dict[str, Any]) -> None:
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT OR IGNORE INTO emails (
                message_id, subject, sender, date, summary, body, links, 
                processed_at, notion_page_id, deadline, action_items, ner_summary
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.get('message_id'),
                record.get('subject'),
                record.get('sender'),
                record.get('date'),
                record.get('summary'),
                record.get('body'),
                record.get('links'),
                record.get('processed_at') or datetime.utcnow().isoformat(),
                record.get('notion_page_id'),
                record.get('deadline'),
                record.get('action_items'),
                record.get('ner_summary'),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def update_notion_page_id(message_id: str, notion_page_id: str) -> None:
    """Update the Notion page ID for an email record."""
    conn = _connect()
    try:
        conn.execute(
            "UPDATE emails SET notion_page_id = ? WHERE message_id = ?",
            (notion_page_id, message_id)
        )
        conn.commit()
    finally:
        conn.close()


def get_notion_page_id(message_id: str) -> Optional[str]:
    """Get the Notion page ID for an email record."""
    conn = _connect()
    try:
        cursor = conn.execute(
            "SELECT notion_page_id FROM emails WHERE message_id = ?",
            (message_id,)
        )
        row = cursor.fetchone()
        return row[0] if row and row[0] else None
    finally:
        conn.close()


def mark_processed(message_id: str) -> None:
    conn = _connect()
    try:
        conn.execute(
            "UPDATE emails SET processed_at = ? WHERE message_id = ?",
            (datetime.utcnow().isoformat(), message_id),
        )
        conn.commit()
    finally:
        conn.close()




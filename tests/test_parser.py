"""
Unit tests for email parser functionality.
"""

import unittest
import os
import sys

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from parser import parse_email, extract_links


class TestParser(unittest.TestCase):
    """Test cases for email parsing functions."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.sample_email_path = os.path.join(
            os.path.dirname(__file__), 'fixtures', 'sample_email.eml'
        )
        
        # Read sample email
        with open(self.sample_email_path, 'r', encoding='utf-8') as f:
            self.sample_email_content = f.read()
        
        # Convert to bytes as expected by parse_email
        self.sample_email_bytes = self.sample_email_content.encode('utf-8')
    
    def test_parse_email_basic(self):
        """Test basic email parsing functionality."""
        subject, from_email, date_str, body_text, links = parse_email(self.sample_email_bytes)
        
        # Test subject extraction
        self.assertIn("Meeting Reminder", subject)
        self.assertIn("Project Alpha Review", subject)
        
        # Test sender extraction
        self.assertEqual("john.doe@example.com", from_email)
        
        # Test date extraction
        self.assertIn("Mon, 15 Jan 2024", date_str)
        
        # Test body text extraction
        self.assertIn("Hi Jane", body_text)
        self.assertIn("Project Alpha review meeting", body_text)
        self.assertIn("next Monday", body_text)
        
        # Test link extraction
        self.assertIn("https://project-alpha.company.com", links)
        self.assertIn("https://docs.project-alpha.company.com", links)
    
    def test_extract_links(self):
        """Test link extraction functionality."""
        text = """
        Visit our website: https://example.com
        Documentation: http://docs.example.com
        Contact us at support@example.com
        """
        
        links = extract_links(text)
        
        self.assertIn("https://example.com", links)
        self.assertIn("http://docs.example.com", links)
        self.assertEqual(2, len(links))
    
    def test_parse_email_with_html(self):
        """Test parsing email with HTML content."""
        html_email = """
        From: test@example.com
        To: recipient@example.com
        Subject: HTML Email Test
        Date: Mon, 15 Jan 2024 14:30:00 +0000
        Content-Type: text/html; charset=utf-8
        
        <html>
        <body>
        <h1>Important Meeting</h1>
        <p>Please attend the meeting on <strong>Monday</strong>.</p>
        <p>Visit our <a href="https://example.com">website</a> for more info.</p>
        </body>
        </html>
        """
        
        subject, from_email, date_str, body_text, links = parse_email(html_email.encode('utf-8'))
        
        # Should extract text content from HTML
        self.assertIn("Important Meeting", body_text)
        self.assertIn("Please attend the meeting on Monday", body_text)
        self.assertIn("https://example.com", links)
    
    def test_parse_email_multipart(self):
        """Test parsing multipart email."""
        multipart_email = """
        From: test@example.com
        To: recipient@example.com
        Subject: Multipart Email
        Date: Mon, 15 Jan 2024 14:30:00 +0000
        MIME-Version: 1.0
        Content-Type: multipart/alternative; boundary="boundary123"
        
        --boundary123
        Content-Type: text/plain; charset=utf-8
        
        This is the plain text version.
        Visit https://example.com for more info.
        
        --boundary123
        Content-Type: text/html; charset=utf-8
        
        <html><body>This is the HTML version.</body></html>
        
        --boundary123--
        """
        
        subject, from_email, date_str, body_text, links = parse_email(multipart_email.encode('utf-8'))
        
        # Should prefer plain text over HTML
        self.assertIn("This is the plain text version", body_text)
        self.assertIn("https://example.com", links)


if __name__ == '__main__':
    unittest.main()

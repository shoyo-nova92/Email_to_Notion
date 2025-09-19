# Email to Notion Summary (Production Ready)

A comprehensive email processing system that fetches unread Gmail messages, extracts text and links, summarizes content using Hugging Face models, extracts dates and action items, and stores results in both SQLite and Notion. Supports both IMAP and Gmail API, with background scheduling and production-ready features.

## Features

- **Dual Email Fetching**: IMAP (default) or Gmail API with OAuth2
- **Smart Text Extraction**: Plain text with HTML fallback using BeautifulSoup
- **AI Summarization**: Hugging Face transformers with `sshleifer/distilbart-cnn-12-6`
- **Date & Task Extraction**: NER-based extraction of deadlines and action items
- **Notion Integration**: Automatic page creation with structured data
- **Background Scheduling**: Automated processing with configurable intervals
- **Idempotent Processing**: Skip already processed emails by `message_id`
- **Comprehensive Logging**: Production-ready logging and error handling

## Prerequisites

- Python 3.9+
- Gmail account with IMAP enabled OR Gmail API credentials
- Notion account with integration token (optional)
- 2GB+ free disk space for AI models

## Installation

### 1. Clone and Setup
```bash
git clone <repository-url>
cd Email_to_Notion_Summary
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Gmail Setup (Choose One Method)

#### Method A: IMAP (Recommended for Quick Start)
1. Enable IMAP in Gmail: Settings → See all settings → Forwarding and POP/IMAP → Enable IMAP
2. Create App Password: Google Account → Security → App passwords → Select app: Mail → Generate
3. Copy the 16-character password

#### Method B: Gmail API (More Secure, Better Performance)
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project or select existing
3. Enable Gmail API
4. Go to Credentials → Create Credentials → OAuth 2.0 Client IDs
5. Choose "Desktop application"
6. Download `credentials.json` to project root
7. Run OAuth flow: `python -c "from src.gmail_api import setup_gmail_api_credentials; setup_gmail_api_credentials()"`

### 3. Notion Setup (Optional)
1. Go to [Notion Integrations](https://www.notion.so/my-integrations)
2. Create new integration → Copy token
3. Create a database in Notion with these properties:
   - **Title** (Title)
   - **Sender** (Text)
   - **Date** (Date)
   - **Status** (Select: New, In Progress, Done)
4. Share database with your integration
5. Copy database ID from URL

### 4. Configuration
```bash
# Copy example configuration
cp .env.example .env  # Windows: copy .env.example .env
```

Edit `.env` with your credentials:
```env
# Gmail IMAP (Method A)
GMAIL_EMAIL=your_email@gmail.com
GMAIL_APP_PASSWORD=your_16_char_app_password

# Gmail API (Method B)
GMAIL_USE_API=true

# Notion Integration
NOTION_TOKEN=your_notion_integration_token
NOTION_DATABASE_ID=your_notion_database_id

# Processing Settings
DEVICE=cpu
MODEL_NAME=sshleifer/distilbart-cnn-12-6
SCHEDULER_INTERVAL_MINUTES=30
```

## Usage

### Basic Processing
```bash
# Process 10 emails with IMAP
python src/main.py --limit 10

# Process with Gmail API
python src/main.py --limit 10 --gmail-api

# Process with Notion integration
python src/main.py --limit 10 --notion

# Dry run (test without saving)
python src/main.py --limit 5 --dry-run --notion
```

### Background Scheduling
```bash
# Run scheduler (processes every 30 minutes)
python run_scheduler.py

# Stop with Ctrl+C (graceful shutdown)
```

### Testing
```bash
# Run unit tests
python -m pytest tests/

# Test with sample email
python tests/test_parser.py
```

## Database Schema

The SQLite database (`emails.db`) contains an `emails` table with:
- `message_id` (TEXT, UNIQUE) - Primary identifier
- `subject` (TEXT) - Email subject
- `sender` (TEXT) - Sender email
- `date` (TEXT) - Email date
- `summary` (TEXT) - AI-generated summary
- `body` (TEXT) - Full email text
- `links` (TEXT) - Extracted URLs
- `processed_at` (TEXT) - Processing timestamp
- `notion_page_id` (TEXT) - Notion page ID (if created)
- `deadline` (TEXT) - Extracted deadline date
- `action_items` (TEXT) - Extracted action items
- `ner_summary` (TEXT) - NER extraction summary

## Notion Database Setup

Create a Notion database with these properties:
- **Title** (Title) - Auto-populated from email summary
- **Sender** (Text) - Email sender
- **Date** (Date) - Email date
- **Status** (Select) - New, In Progress, Done
- **Deadline** (Date) - Extracted deadline (optional)
- **Action Items** (Text) - Extracted tasks (optional)

## Project Structure
```
Email_to_Notion_Summary/
├── README.md
├── requirements.txt
├── .env.example
├── token.json.example
├── run_scheduler.py
├── src/
│   ├── fetch_emails.py      # IMAP email fetching
│   ├── gmail_api.py         # Gmail API alternative
│   ├── parser.py            # Email parsing & link extraction
│   ├── summarizer.py        # Hugging Face summarization
│   ├── storage.py           # SQLite database operations
│   ├── notion_writer.py     # Notion integration
│   ├── ner_extras.py        # Date & task extraction
│   ├── utils.py             # Utility functions
│   └── main.py              # Main orchestrator
├── tests/
│   ├── __init__.py
│   ├── test_parser.py       # Unit tests
│   └── fixtures/
│       └── sample_email.eml # Test email
└── emails.db                # SQLite database (created on first run)
```

## Troubleshooting

### Common Issues

**"Invalid credentials" error:**
- For IMAP: Verify App Password is correct and IMAP is enabled
- For Gmail API: Re-run OAuth flow or check `credentials.json`

**"Notion database not found" error:**
- Verify `NOTION_DATABASE_ID` is correct
- Ensure database is shared with your integration

**"Model not found" error:**
- First run downloads models (~1.2GB)
- Ensure stable internet connection
- Run: `python -c "from transformers import pipeline; pipeline('summarization', model='sshleifer/distilbart-cnn-12-6')"`

**Memory issues:**
- Reduce `--limit` parameter
- Set `DEVICE=cpu` in `.env`
- Close other applications

**Rate limiting:**
- Notion API has rate limits (3 requests/second)
- Gmail API has daily quotas
- Scheduler respects rate limits with exponential backoff

### Logs
- Console output shows real-time progress
- `scheduler.log` contains background scheduler logs
- SQLite database tracks all processed emails

## Advanced Configuration

### Custom Models
```env
MODEL_NAME=facebook/bart-large-cnn  # Larger, better quality
MODEL_NAME=google/pegasus-xsum     # Different architecture
```

### Performance Tuning
```env
MAX_SUMMARY_LENGTH=200    # Longer summaries
MIN_SUMMARY_LENGTH=50     # Minimum summary length
CHUNK_SIZE=1000          # Larger text chunks
SCHEDULER_INTERVAL_MINUTES=15  # More frequent processing
```

### Security
- Store `.env` file securely (not in version control)
- Use App Passwords instead of main Gmail password
- Rotate Notion tokens regularly
- Set appropriate file permissions on `token.json`

## Deployment

### Local Development
```bash
python src/main.py --limit 5 --dry-run --notion
```

### Production
```bash
# Run scheduler as background service
nohup python run_scheduler.py > scheduler.log 2>&1 &

# Or use systemd/cron for scheduled runs
# Add to crontab: */30 * * * * cd /path/to/project && python src/main.py --notion --limit 20
```

### Docker (Optional)
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "run_scheduler.py"]
```

## Archive Project
```bash
# Create archive
tar -czf email-to-notion-summary.tar.gz --exclude='.venv' --exclude='emails.db' --exclude='__pycache__' .

# Or on Windows
powershell Compress-Archive -Path . -DestinationPath email-to-notion-summary.zip -Exclude .venv,emails.db,__pycache__
```

## Next Steps
- Add web UI for browsing summaries
- Implement email labeling and archiving
- Add support for multiple email accounts
- Create Notion templates for different email types
- Add email filtering and categorization
- Implement webhook notifications
- Add Docker Compose setup
- Create CI/CD pipeline
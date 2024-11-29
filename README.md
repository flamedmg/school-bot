# School Parent Assistant Bot

A sophisticated Telegram bot that transforms e-klase (school management system) data into a streamlined, organized experience for parents. The bot automatically tracks schedules, grades, homework, and announcements, delivering real-time updates through Telegram.

## Core Features

- 📅 **Automated Schedule Tracking**
  - Real-time schedule monitoring
  - Multi-week schedule view (previous, current, next)
  - Automatic schedule change notifications

- 📊 **Academic Performance Monitoring**
  - Real-time grade notifications with fun emoji feedback
  - Grade change tracking and notifications
  - Historical grade data access

- 📚 **Homework Management**
  - Homework assignment tracking
  - Automatic attachment downloads
  - Assignment change notifications

- 📢 **Smart Announcements**
  - School announcements delivery
  - Behavioral notifications
  - Important updates tracking

- 👥 **Multi-Student Support**
  - Support for multiple student accounts
  - Customizable student nicknames and emojis
  - Individual tracking for each student

## Architecture

### Component Overview

- **Schedule Crawler**: Automated web crawler using Playwright for reliable data extraction
- **Event System**: Asynchronous event processing using FastStream
- **Data Pipeline**: Robust data processing with multiple preprocessors
- **Storage Layer**: SQLite database with SQLModel ORM
- **API Layer**: FastAPI-based REST API for system monitoring
- **Telegram Interface**: Asynchronous Telegram bot using Telethon

### Data Flow

1. Schedule Crawler fetches data from e-klase
2. Raw data is processed through specialized preprocessors
3. Changes are detected and stored in the database
4. Events are generated for significant changes
5. Notifications are sent to users via Telegram

## Technical Stack

### Core Technologies
- Python 3.11+
- SQLite (data storage)
- Redis (message broker)
- Playwright (web automation)
- Docker & Docker Compose

### Key Libraries
- FastStream (async event processing)
- FastAPI (REST API framework)
- SQLModel (SQLAlchemy-based ORM)
- Telethon (Telegram client)
- Pydantic (data validation)
- crawl4ai (web scraping framework)
- loguru (logging)

### Development Tools
- Poetry (dependency management)
- pytest (testing)
- black (code formatting)
- ruff (linting)

## Configuration

### Environment Variables

```env
# Telegram Configuration
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# School Configuration
SCHOOL_WEBSITE_URL=https://www.e-klase.lv
SCHOOL_EMAIL_SERVER=email_server

# Student Configuration (Multiple students supported)
STUDENT_USERNAME_NICKNAME1=username1
STUDENT_PASSWORD_NICKNAME1=password1
STUDENT_EMOJI_NICKNAME1=👦  # Optional, defaults to 👤

STUDENT_USERNAME_NICKNAME2=username2
STUDENT_PASSWORD_NICKNAME2=password2
STUDENT_EMOJI_NICKNAME2=👧  # Optional

# Database Configuration
DATABASE_URL=sqlite:///data/school_bot.db

# Redis Configuration
REDIS_URL=redis://redis:6379/0

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=1
```

## Setup

### Docker Setup (Recommended)

1. Clone the repository
```bash
git clone <repository-url>
cd school-bot
```

2. Configure environment
```bash
cp .env.example .env
# Edit .env with your credentials
```

3. Launch with Docker Compose
```bash
docker-compose up -d
```

### Local Development Setup

1. Install Poetry
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

2. Install dependencies
```bash
poetry install
```

3. Configure environment
```bash
cp .env.example .env
# Edit .env with your credentials
```

4. Run the bot
```bash
poetry shell
python src/main.py
```

## Development

### Project Structure
```
src/
├── api/            # FastAPI endpoints
├── database/       # Database models and repository
├── events/         # Event handlers and types
├── schedule/       # Schedule crawling and processing
│   └── preprocessors/  # Data preprocessors
├── telegram/       # Telegram bot interface
└── utils/          # Utility functions
```

### Testing

Run tests with pytest:
```bash
pytest tests/
```

### Code Style

- Format code with black:
```bash
black src/ tests/
```

- Lint with ruff:
```bash
ruff check src/ tests/
```

## License

MIT License

# School Parent Assistant Bot

A Telegram bot that transforms school's schedule and email communication into a clean, organized Telegram experience for parents.

## Features

- 🗓️ Real-time schedule tracking
- 📧 School email notifications
- 📊 Academic performance monitoring
- 🔔 Smart notifications
- 💾 Historical data access

## Technical Stack

### Core Technologies

- Python 3.11+
- SQLite (data storage)
- Docker
- Telethon (Telegram client library)

### Key Libraries

- telethon (Telegram client)
- crawl4ai (web scraping)
- httpx (async HTTP client)
- SQLModel (SQLAlchemy-based ORM)
- FastStream (async message broker framework)
- Redis (message broker for FastStream)
- beautifulsoup4 (HTML parsing)
- pydantic (data validation)
- python-dotenv (environment management)

### Development Tools

- Poetry (package management)
- pytest (testing)
- black (code formatting)
- ruff (linting)

## Docker Setup

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN pip install uv

COPY requirements.txt .
RUN uv pip install -r requirements.txt

COPY . .

CMD ["python", "src/main.py"]
```

### docker-compose.yml

```yaml
version: "3.8"

services:
  bot:
    build: .
    env_file: .env
    volumes:
      - ./data:/app/data
    depends_on:
      - redis
    restart: unless-stopped

  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped

volumes:
  redis_data:
```

## Environment Variables

```env
# Telegram
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_BOT_TOKEN=your_bot_token

# School
SCHOOL_WEBSITE_URL=school_url
SCHOOL_EMAIL_SERVER=email_server
SCHOOL_EMAIL_USER=email_user
SCHOOL_EMAIL_PASSWORD=email_password

# Database
DATABASE_URL=sqlite:///data/school_bot.db

# Redis
REDIS_URL=redis://redis:6379/0
```

## Setup and Development

1. Clone the repository
2. Copy `.env.example` to `.env` and fill in your credentials
3. Run with Docker:

```bash
docker-compose up -d
```

## Local Development Setup

1. Install Poetry: `curl -sSL https://install.python-poetry.org | python3 -`
2. Install dependencies: `poetry install`
3. Activate virtual environment: `poetry shell`
4. Run the bot: `poetry run python src/main.py`

## Testing

```bash
pytest tests/
```

## License

MIT License

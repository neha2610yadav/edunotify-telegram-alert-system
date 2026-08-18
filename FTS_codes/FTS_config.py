"""Configuration helpers for the EduNotify Telegram integration."""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # The application can still use system environment variables.
    load_dotenv = None


# FTS_config.py lives in <repository>/FTS_codes/.
# Secrets remain in <repository>/.env and are never committed to GitHub.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"


def get_config_value(name):
    """Load one configuration value from the repository .env or process environment."""
    if load_dotenv is not None:
        load_dotenv(ENV_FILE)
    elif not os.getenv(name) and ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            if key.strip() == name:
                os.environ[name] = value.strip()
                break
    return os.getenv(name, "").strip()


def get_telegram_bot_token():
    """Return the configured Telegram token without embedding it in source."""
    return get_config_value("TELEGRAM_BOT_TOKEN")

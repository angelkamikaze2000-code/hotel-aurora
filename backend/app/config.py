import json
import os
import secrets
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
INSTANCE_DIR = BASE_DIR / "instance"
INSTANCE_DIR.mkdir(exist_ok=True)
RUNTIME_SECRETS_FILE = INSTANCE_DIR / "runtime_secrets.json"

load_dotenv(BASE_DIR / ".env")


def _is_unsafe_secret(value):
    normalized = (value or "").strip().lower()
    return normalized in {"", "change-me", "change-me-too"}


def _load_or_create_runtime_secrets():
    if RUNTIME_SECRETS_FILE.exists():
        try:
            return json.loads(RUNTIME_SECRETS_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass

    secrets_payload = {
        "SECRET_KEY": secrets.token_hex(32),
        "JWT_SECRET_KEY": secrets.token_hex(32),
    }
    RUNTIME_SECRETS_FILE.write_text(
        json.dumps(secrets_payload, indent=2),
        encoding="utf-8",
    )
    return secrets_payload


_runtime_secrets = _load_or_create_runtime_secrets()


class Config:
    SECRET_KEY = (
        os.getenv("SECRET_KEY")
        if not _is_unsafe_secret(os.getenv("SECRET_KEY"))
        else _runtime_secrets["SECRET_KEY"]
    )
    JWT_SECRET_KEY = (
        os.getenv("JWT_SECRET_KEY")
        if not _is_unsafe_secret(os.getenv("JWT_SECRET_KEY"))
        else _runtime_secrets["JWT_SECRET_KEY"]
    )
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{(INSTANCE_DIR / 'hotel_aurora.db').as_posix()}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PASSWORD_RESET_TOKEN_MAX_AGE = int(os.getenv("PASSWORD_RESET_TOKEN_MAX_AGE", "1800"))
    PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID", "").strip()
    PAYPAL_CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET", "").strip()
    PAYPAL_ENV = os.getenv("PAYPAL_ENV", "sandbox").strip().lower() or "sandbox"

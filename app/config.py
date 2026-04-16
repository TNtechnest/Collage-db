import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
INSTANCE_DIR = BASE_DIR / "instance"
DEFAULT_DB_PATH = (INSTANCE_DIR / "college_dashboard.sqlite3").as_posix()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or f"sqlite:///{DEFAULT_DB_PATH}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    REMEMBER_COOKIE_DURATION = 86400 * 7
    UPLOAD_FOLDER = str(INSTANCE_DIR / "uploads")
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024
    ITEMS_PER_PAGE = 10
    SMS_PROVIDER_NAME = os.environ.get("SMS_PROVIDER_NAME", "sms-stub")
    WHATSAPP_PROVIDER_NAME = os.environ.get("WHATSAPP_PROVIDER_NAME", "whatsapp-stub")
    WHATSAPP_API_URL = os.environ.get("WHATSAPP_API_URL", "")
    RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "")
    RAZORPAY_WEBHOOK_SECRET = os.environ.get("RAZORPAY_WEBHOOK_SECRET", "")

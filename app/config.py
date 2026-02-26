import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"

DATA_DIR.mkdir(exist_ok=True)

DATABASE_URL = str(DATA_DIR / "audit.db")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MOCK_MODE = not bool(ANTHROPIC_API_KEY)

ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
BATCH_SIZE = 20
MAX_RETRIES = 2

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "compliance@example.com")

CSV_COLUMNS = [
    "Advertiser", "AccountOwner", "AdvertiserID", "AdvertiserVertical",
    "AdvertiserSubvertical", "CampaignID", "CampaignObjective",
    "CampaignBrandName", "CampaignLanguage", "ReferralCreativeID",
    "CreativeName", "CreativeBrandName", "CreativeFormat", "CreativeTitle",
    "CleanCreativeBody", "CTAResponse", "DisclaimerText", "targeturl",
    "CreativeStatus", "CreativeLastUpdated", "ApprovedAt", "Impressions",
    "ApprovedByName",
]

FINAL_CSV_COLUMNS = CSV_COLUMNS + ["pass", "fail_reason"]

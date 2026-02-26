import csv
import io
from typing import Tuple


def parse_csv(content: bytes) -> Tuple[list[str], list[dict]]:
    """Parse CSV bytes into header list and list of row dicts."""
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError("CSV file has no header row")
    headers = list(reader.fieldnames)
    rows = []
    for row in reader:
        rows.append(dict(row))
    if not rows:
        raise ValueError("CSV file has no data rows")
    return headers, rows


def validate_csv(headers: list[str]) -> list[str]:
    """Check for required columns. Returns list of warnings (not errors)."""
    warnings = []
    recommended = [
        "Advertiser", "CampaignBrandName", "CreativeTitle",
        "CleanCreativeBody", "CTAResponse", "targeturl",
    ]
    for col in recommended:
        if col not in headers:
            warnings.append(f"Recommended column '{col}' not found in CSV")
    return warnings

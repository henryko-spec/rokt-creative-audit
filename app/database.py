import aiosqlite
import json
from app.config import DATABASE_URL

SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    total_rows INTEGER NOT NULL DEFAULT 0,
    processed_rows INTEGER NOT NULL DEFAULT 0,
    approved_count INTEGER NOT NULL DEFAULT 0,
    rejected_count INTEGER NOT NULL DEFAULT 0,
    flagged_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS creatives (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    row_index INTEGER NOT NULL,
    advertiser TEXT DEFAULT '',
    advertiser_id TEXT DEFAULT '',
    advertiser_vertical TEXT DEFAULT '',
    advertiser_subvertical TEXT DEFAULT '',
    campaign_id TEXT DEFAULT '',
    campaign_objective TEXT DEFAULT '',
    campaign_brand_name TEXT DEFAULT '',
    campaign_language TEXT DEFAULT '',
    creative_id TEXT DEFAULT '',
    creative_name TEXT DEFAULT '',
    creative_brand_name TEXT DEFAULT '',
    creative_format TEXT DEFAULT '',
    creative_title TEXT DEFAULT '',
    creative_body TEXT DEFAULT '',
    cta_response TEXT DEFAULT '',
    disclaimer_text TEXT DEFAULT '',
    target_url TEXT DEFAULT '',
    creative_status TEXT DEFAULT '',
    alpha_pass INTEGER,
    alpha_fail_reason TEXT DEFAULT '',
    beta_pass INTEGER,
    beta_fail_reason TEXT DEFAULT '',
    arbiter_pass INTEGER,
    arbiter_fail_reason TEXT DEFAULT '',
    review_status TEXT DEFAULT 'pending',
    raw_data TEXT DEFAULT '{}',
    FOREIGN KEY (job_id) REFERENCES audit_jobs(id)
);

CREATE TABLE IF NOT EXISTS email_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    creative_id INTEGER NOT NULL,
    email_to TEXT NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'sent',
    FOREIGN KEY (creative_id) REFERENCES creatives(id)
);
"""


async def get_db() -> aiosqlite.Connection:
    db = await aiosqlite.connect(DATABASE_URL)
    db.row_factory = aiosqlite.Row
    return db


async def init_db():
    db = await get_db()
    try:
        await db.executescript(SCHEMA)
        await db.commit()
    finally:
        await db.close()


async def create_job(filename: str, total_rows: int) -> int:
    db = await get_db()
    try:
        cursor = await db.execute(
            "INSERT INTO audit_jobs (filename, status, total_rows) VALUES (?, 'pending', ?)",
            (filename, total_rows),
        )
        await db.commit()
        return cursor.lastrowid
    finally:
        await db.close()


async def update_job_status(job_id: int, status: str):
    db = await get_db()
    try:
        await db.execute(
            "UPDATE audit_jobs SET status = ? WHERE id = ?", (status, job_id)
        )
        await db.commit()
    finally:
        await db.close()


async def increment_job_processed(job_id: int, passed: bool, flagged: bool = False):
    db = await get_db()
    try:
        if passed:
            await db.execute(
                "UPDATE audit_jobs SET processed_rows = processed_rows + 1, approved_count = approved_count + 1 WHERE id = ?",
                (job_id,),
            )
        elif flagged:
            await db.execute(
                "UPDATE audit_jobs SET processed_rows = processed_rows + 1, flagged_count = flagged_count + 1 WHERE id = ?",
                (job_id,),
            )
        else:
            await db.execute(
                "UPDATE audit_jobs SET processed_rows = processed_rows + 1, rejected_count = rejected_count + 1 WHERE id = ?",
                (job_id,),
            )
        await db.commit()
    finally:
        await db.close()


async def get_job(job_id: int) -> dict | None:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM audit_jobs WHERE id = ?", (job_id,))
        row = await cursor.fetchone()
        if row:
            return dict(row)
        return None
    finally:
        await db.close()


async def get_all_jobs() -> list[dict]:
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM audit_jobs ORDER BY created_at DESC"
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def insert_creative(job_id: int, row_index: int, data: dict) -> int:
    db = await get_db()
    try:
        cursor = await db.execute(
            """INSERT INTO creatives (
                job_id, row_index, advertiser, advertiser_id, advertiser_vertical,
                advertiser_subvertical, campaign_id, campaign_objective,
                campaign_brand_name, campaign_language, creative_id,
                creative_name, creative_brand_name, creative_format,
                creative_title, creative_body, cta_response, disclaimer_text,
                target_url, creative_status, raw_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                job_id,
                row_index,
                data.get("Advertiser", ""),
                data.get("AdvertiserID", ""),
                data.get("AdvertiserVertical", ""),
                data.get("AdvertiserSubvertical", ""),
                data.get("CampaignID", ""),
                data.get("CampaignObjective", ""),
                data.get("CampaignBrandName", ""),
                data.get("CampaignLanguage", ""),
                data.get("ReferralCreativeID", ""),
                data.get("CreativeName", ""),
                data.get("CreativeBrandName", ""),
                data.get("CreativeFormat", ""),
                data.get("CreativeTitle", ""),
                data.get("CleanCreativeBody", ""),
                data.get("CTAResponse", ""),
                data.get("DisclaimerText", ""),
                data.get("targeturl", ""),
                data.get("CreativeStatus", ""),
                json.dumps(data),
            ),
        )
        await db.commit()
        return cursor.lastrowid
    finally:
        await db.close()


async def update_creative_results(
    creative_id: int,
    alpha_pass: bool,
    alpha_fail_reason: str,
    beta_pass: bool,
    beta_fail_reason: str,
    arbiter_pass: bool,
    arbiter_fail_reason: str,
):
    db = await get_db()
    try:
        await db.execute(
            """UPDATE creatives SET
                alpha_pass = ?, alpha_fail_reason = ?,
                beta_pass = ?, beta_fail_reason = ?,
                arbiter_pass = ?, arbiter_fail_reason = ?,
                review_status = ?
            WHERE id = ?""",
            (
                int(alpha_pass),
                alpha_fail_reason,
                int(beta_pass),
                beta_fail_reason,
                int(arbiter_pass),
                arbiter_fail_reason,
                "pending" if not arbiter_pass else "pending",
                creative_id,
            ),
        )
        await db.commit()
    finally:
        await db.close()


async def get_creatives_for_job(job_id: int, filter_status: str | None = None) -> list[dict]:
    db = await get_db()
    try:
        if filter_status == "flagged":
            cursor = await db.execute(
                "SELECT * FROM creatives WHERE job_id = ? AND arbiter_pass = 0 ORDER BY row_index",
                (job_id,),
            )
        elif filter_status == "approved":
            cursor = await db.execute(
                "SELECT * FROM creatives WHERE job_id = ? AND arbiter_pass = 1 ORDER BY row_index",
                (job_id,),
            )
        else:
            cursor = await db.execute(
                "SELECT * FROM creatives WHERE job_id = ? ORDER BY row_index",
                (job_id,),
            )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def get_creative(creative_id: int) -> dict | None:
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM creatives WHERE id = ?", (creative_id,)
        )
        row = await cursor.fetchone()
        if row:
            return dict(row)
        return None
    finally:
        await db.close()


async def update_creative_review(creative_id: int, review_status: str):
    db = await get_db()
    try:
        await db.execute(
            "UPDATE creatives SET review_status = ? WHERE id = ?",
            (review_status, creative_id),
        )
        await db.commit()
    finally:
        await db.close()


async def log_email(creative_id: int, email_to: str, subject: str, body: str, status: str = "sent"):
    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO email_log (creative_id, email_to, subject, body, status) VALUES (?, ?, ?, ?, ?)",
            (creative_id, email_to, subject, body, status),
        )
        await db.commit()
    finally:
        await db.close()

from pydantic import BaseModel
from typing import Optional
from enum import Enum


class JobStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class ReviewStatus(str, Enum):
    pending = "pending"
    looks_good = "looks_good"
    flagged = "flagged"
    flagged_emailed = "flagged_emailed"


class JobOut(BaseModel):
    id: int
    filename: str
    status: JobStatus
    total_rows: int
    processed_rows: int
    approved_count: int
    rejected_count: int
    flagged_count: int
    created_at: str


class JobProgress(BaseModel):
    id: int
    status: JobStatus
    total_rows: int
    processed_rows: int
    approved_count: int
    rejected_count: int
    flagged_count: int


class CreativeOut(BaseModel):
    id: int
    job_id: int
    row_index: int
    advertiser: str
    advertiser_id: str
    campaign_id: str
    campaign_brand_name: str
    campaign_language: str
    creative_id: str
    creative_name: str
    creative_format: str
    creative_title: str
    creative_body: str
    cta_response: str
    disclaimer_text: str
    target_url: str
    alpha_pass: Optional[bool] = None
    alpha_fail_reason: str = ""
    beta_pass: Optional[bool] = None
    beta_fail_reason: str = ""
    arbiter_pass: Optional[bool] = None
    arbiter_fail_reason: str = ""
    review_status: ReviewStatus = ReviewStatus.pending
    raw_data: str = ""


class ReviewAction(BaseModel):
    action: str  # looks_good, flagged, flagged_emailed
    email_to: Optional[str] = None
    note: Optional[str] = None

from fastapi import APIRouter, HTTPException
from app.models import ReviewAction
from app.database import get_creative, update_creative_review
from app.services.email_service import send_flag_email

router = APIRouter()


@router.post("/api/creatives/{creative_id}/review")
async def submit_review(creative_id: int, action: ReviewAction):
    creative = await get_creative(creative_id)
    if not creative:
        raise HTTPException(status_code=404, detail="Creative not found")

    if action.action not in ("looks_good", "flagged", "flagged_emailed"):
        raise HTTPException(status_code=400, detail="Invalid action")

    await update_creative_review(creative_id, action.action)

    if action.action == "flagged_emailed":
        email_to = action.email_to
        if not email_to:
            raise HTTPException(
                status_code=400,
                detail="email_to is required for flagged_emailed action",
            )
        await send_flag_email(
            creative_id=creative_id,
            email_to=email_to,
            advertiser=creative["advertiser"],
            creative_name=creative["creative_name"],
            creative_title=creative["creative_title"],
            fail_reason=creative["arbiter_fail_reason"],
            note=action.note or "",
        )

    return {"status": "ok", "creative_id": creative_id, "review_status": action.action}

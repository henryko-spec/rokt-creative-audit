from fastapi import APIRouter, HTTPException
from app.database import get_all_jobs, get_job, get_creatives_for_job

router = APIRouter()


@router.get("/api/jobs")
async def list_jobs():
    jobs = await get_all_jobs()
    return {"jobs": jobs}


@router.get("/api/jobs/{job_id}")
async def get_job_detail(job_id: int):
    job = await get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/api/jobs/{job_id}/progress")
async def get_job_progress(job_id: int):
    job = await get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "id": job["id"],
        "status": job["status"],
        "total_rows": job["total_rows"],
        "processed_rows": job["processed_rows"],
        "approved_count": job["approved_count"],
        "rejected_count": job["rejected_count"],
        "flagged_count": job["flagged_count"],
    }


@router.get("/api/jobs/{job_id}/creatives")
async def get_job_creatives(job_id: int, filter: str | None = None):
    job = await get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    creatives = await get_creatives_for_job(job_id, filter_status=filter)
    return {"creatives": creatives, "total": len(creatives)}

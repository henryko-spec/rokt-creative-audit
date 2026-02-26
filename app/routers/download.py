from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from app.database import get_job
from app.services.report_generator import generate_final_csv, generate_arbiter_report

router = APIRouter()


@router.get("/api/jobs/{job_id}/download/csv")
async def download_csv(job_id: int):
    job = await get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Job not yet completed")

    csv_content = await generate_final_csv(job_id)
    filename = job["filename"].replace(".csv", "-audited.csv")

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/api/jobs/{job_id}/download/report")
async def download_report(job_id: int):
    job = await get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Job not yet completed")

    report = await generate_arbiter_report(job_id)
    filename = job["filename"].replace(".csv", "-arbiter-report.md")

    return Response(
        content=report,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

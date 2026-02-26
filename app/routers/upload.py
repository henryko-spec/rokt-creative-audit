import asyncio
import logging
from fastapi import APIRouter, UploadFile, File, BackgroundTasks
from fastapi.responses import JSONResponse
from app.services.csv_parser import parse_csv, validate_csv
from app.database import create_job, insert_creative
from app.services.audit_pipeline import run_audit_pipeline

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/api/upload")
async def upload_csv(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if not file.filename or not file.filename.endswith(".csv"):
        return JSONResponse(
            status_code=400,
            content={"error": "Please upload a CSV file"},
        )

    content = await file.read()
    if not content:
        return JSONResponse(
            status_code=400,
            content={"error": "File is empty"},
        )

    try:
        headers, rows = parse_csv(content)
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})
    except Exception as e:
        logger.error(f"CSV parse error: {e}")
        return JSONResponse(
            status_code=400,
            content={"error": f"Failed to parse CSV: {str(e)}"},
        )

    warnings = validate_csv(headers)

    job_id = await create_job(filename=file.filename, total_rows=len(rows))

    for idx, row in enumerate(rows):
        await insert_creative(job_id=job_id, row_index=idx, data=row)

    background_tasks.add_task(run_audit_pipeline, job_id)

    return {
        "job_id": job_id,
        "filename": file.filename,
        "total_rows": len(rows),
        "warnings": warnings,
        "message": "Upload successful. Audit started.",
    }

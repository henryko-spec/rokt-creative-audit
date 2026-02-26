import asyncio
import logging
import json
from app.config import BATCH_SIZE
from app.database import (
    get_creatives_for_job,
    update_creative_results,
    update_job_status,
    increment_job_processed,
)
from app.services.anthropic_client import run_alpha, run_beta, run_arbiter

logger = logging.getLogger(__name__)


async def process_single_creative(creative: dict):
    """Run Alpha -> Beta -> Arbiter pipeline for a single creative."""
    creative_data = json.loads(creative["raw_data"]) if creative["raw_data"] else {}

    try:
        alpha_result = await run_alpha(creative_data)
        beta_result = await run_beta(creative_data)
        arbiter_result = await run_arbiter(creative_data, alpha_result, beta_result)

        await update_creative_results(
            creative_id=creative["id"],
            alpha_pass=alpha_result["pass"],
            alpha_fail_reason=alpha_result["fail_reason"],
            beta_pass=beta_result["pass"],
            beta_fail_reason=beta_result["fail_reason"],
            arbiter_pass=arbiter_result["pass"],
            arbiter_fail_reason=arbiter_result["fail_reason"],
        )

        is_flagged = arbiter_result.get("verdict") == "FLAG FOR REVIEW"
        await increment_job_processed(
            creative["job_id"],
            passed=arbiter_result["pass"],
            flagged=is_flagged and not arbiter_result["pass"],
        )

        logger.info(
            f"Creative {creative['id']} (row {creative['row_index']}): "
            f"alpha={'PASS' if alpha_result['pass'] else 'FAIL'} "
            f"beta={'PASS' if beta_result['pass'] else 'FAIL'} "
            f"arbiter={'PASS' if arbiter_result['pass'] else 'FAIL'}"
        )

    except Exception as e:
        logger.error(f"Error processing creative {creative['id']}: {e}")
        await update_creative_results(
            creative_id=creative["id"],
            alpha_pass=True,
            alpha_fail_reason="",
            beta_pass=True,
            beta_fail_reason="",
            arbiter_pass=True,
            arbiter_fail_reason=f"Processing error: {str(e)}",
        )
        await increment_job_processed(creative["job_id"], passed=True)


async def run_audit_pipeline(job_id: int):
    """Run the full audit pipeline for a job, processing in batches."""
    await update_job_status(job_id, "processing")

    try:
        creatives = await get_creatives_for_job(job_id)

        for i in range(0, len(creatives), BATCH_SIZE):
            batch = creatives[i : i + BATCH_SIZE]
            tasks = [process_single_creative(c) for c in batch]
            await asyncio.gather(*tasks, return_exceptions=True)
            logger.info(
                f"Job {job_id}: batch {i // BATCH_SIZE + 1} complete "
                f"({min(i + BATCH_SIZE, len(creatives))}/{len(creatives)})"
            )

        await update_job_status(job_id, "completed")
        logger.info(f"Job {job_id} completed successfully")

    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}")
        await update_job_status(job_id, "failed")

import csv
import io
import json
from datetime import datetime
from app.config import FINAL_CSV_COLUMNS, CSV_COLUMNS
from app.database import get_creatives_for_job, get_job


async def generate_final_csv(job_id: int) -> str:
    """Generate the final CSV with pass/fail columns appended."""
    creatives = await get_creatives_for_job(job_id)
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=FINAL_CSV_COLUMNS, quoting=csv.QUOTE_MINIMAL)
    writer.writeheader()

    for c in creatives:
        raw = json.loads(c["raw_data"]) if c["raw_data"] else {}
        row = {}
        for col in CSV_COLUMNS:
            row[col] = raw.get(col, "")
        row["pass"] = "TRUE" if c["arbiter_pass"] else "FALSE"
        row["fail_reason"] = c["arbiter_fail_reason"] or ""
        writer.writerow(row)

    return output.getvalue()


async def generate_arbiter_report(job_id: int) -> str:
    """Generate the arbiter report as markdown."""
    job = await get_job(job_id)
    creatives = await get_creatives_for_job(job_id)

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [
        now,
        "",
        f"# Creative Compliance Arbiter Report — {job['filename']}",
        "",
        "## Summary",
        "",
        f"- **Total creatives:** {job['total_rows']}",
        f"- **Approved:** {job['approved_count']}",
        f"- **Rejected:** {job['rejected_count']}",
        f"- **Flagged for review:** {job['flagged_count']}",
        "",
    ]

    # Most common violations
    violation_counts: dict[str, int] = {}
    for c in creatives:
        if c["arbiter_fail_reason"]:
            for reason in c["arbiter_fail_reason"].split(" | "):
                reason = reason.strip()
                if reason:
                    violation_counts[reason] = violation_counts.get(reason, 0) + 1

    if violation_counts:
        lines.append("## Most Common Violations")
        lines.append("")
        lines.append("| Violation | Count |")
        lines.append("|-----------|-------|")
        sorted_violations = sorted(violation_counts.items(), key=lambda x: -x[1])[:10]
        for v, count in sorted_violations:
            lines.append(f"| {v} | {count} |")
        lines.append("")

    # Rejected creatives
    rejected = [c for c in creatives if not c["arbiter_pass"]]
    if rejected:
        lines.append("## Rejected Creatives")
        lines.append("")
        for c in rejected:
            lines.append(
                f"- **Row {c['row_index']}:** {c['advertiser']} — {c['creative_id']}"
            )
            lines.append(f"  - Title: {c['creative_title']}")
            lines.append(f"  - Violations: {c['arbiter_fail_reason']}")
            lines.append(f"  - Alpha: {'PASS' if c['alpha_pass'] else 'FAIL'} | "
                         f"Beta: {'PASS' if c['beta_pass'] else 'FAIL'}")
            lines.append("")

    # Approved creatives
    approved = [c for c in creatives if c["arbiter_pass"]]
    if approved:
        lines.append("## Approved Creatives")
        lines.append("")
        for c in approved:
            lines.append(
                f"- **Row {c['row_index']}:** {c['advertiser']} — {c['creative_id']}"
            )
        lines.append("")

    # Summary table
    lines.append("## Full Results")
    lines.append("")
    lines.append("| Row | Advertiser | Creative ID | Alpha | Beta | Final | Key Findings |")
    lines.append("|-----|-----------|-------------|-------|------|-------|--------------|")
    for c in creatives:
        alpha = "PASS" if c["alpha_pass"] else "FAIL"
        beta = "PASS" if c["beta_pass"] else "FAIL"
        final = "PASS" if c["arbiter_pass"] else "FAIL"
        findings = c["arbiter_fail_reason"][:80] if c["arbiter_fail_reason"] else "—"
        lines.append(
            f"| {c['row_index']} | {c['advertiser']} | {c['creative_id']} | "
            f"{alpha} | {beta} | {final} | {findings} |"
        )

    return "\n".join(lines)

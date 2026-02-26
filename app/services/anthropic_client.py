import json
import logging
from pathlib import Path
from app.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL, MOCK_MODE, PROMPTS_DIR

logger = logging.getLogger(__name__)

if not MOCK_MODE:
    import anthropic
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
else:
    client = None


def _load_prompt(name: str) -> str:
    path = PROMPTS_DIR / f"{name}.md"
    return path.read_text()


def _build_creative_message(creative_data: dict) -> str:
    """Format creative data as a structured message for the AI."""
    lines = ["Review this creative for compliance:\n"]
    field_map = {
        "Advertiser": "Advertiser",
        "AdvertiserID": "Advertiser ID",
        "AdvertiserVertical": "Vertical",
        "AdvertiserSubvertical": "Sub-vertical",
        "CampaignID": "Campaign ID",
        "CampaignObjective": "Objective",
        "CampaignBrandName": "Brand Name",
        "CampaignLanguage": "Language",
        "ReferralCreativeID": "Creative ID",
        "CreativeName": "Creative Name",
        "CreativeBrandName": "Creative Brand Name",
        "CreativeFormat": "Format",
        "CreativeTitle": "Title",
        "CleanCreativeBody": "Body",
        "CTAResponse": "CTA",
        "DisclaimerText": "Disclaimer",
        "targeturl": "Target URL",
        "CreativeStatus": "Status",
    }
    for key, label in field_map.items():
        val = creative_data.get(key, "")
        lines.append(f"**{label}:** {val}")
    return "\n".join(lines)


async def run_alpha(creative_data: dict) -> dict:
    """Run Alpha review. Returns {pass: bool, fail_reason: str}."""
    if MOCK_MODE:
        return _mock_alpha(creative_data)
    return await _call_ai("alpha", creative_data)


async def run_beta(creative_data: dict) -> dict:
    """Run Beta review. Returns {pass: bool, fail_reason: str}."""
    if MOCK_MODE:
        return _mock_beta(creative_data)
    return await _call_ai("beta", creative_data)


async def run_arbiter(creative_data: dict, alpha_result: dict, beta_result: dict) -> dict:
    """Run Arbiter synthesis. Returns {pass: bool, fail_reason: str, verdict: str}."""
    if MOCK_MODE:
        return _mock_arbiter(creative_data, alpha_result, beta_result)
    return await _call_arbiter(creative_data, alpha_result, beta_result)


async def _call_ai(role: str, creative_data: dict) -> dict:
    """Call Anthropic API for Alpha or Beta review."""
    system_prompt = _load_prompt(role)
    user_message = _build_creative_message(creative_data)

    try:
        message = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=2048,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        return _parse_review_response(message.content[0].text)
    except Exception as e:
        logger.error(f"{role} review failed: {e}")
        return {"pass": True, "fail_reason": f"Error during {role} review: {str(e)}"}


async def _call_arbiter(creative_data: dict, alpha_result: dict, beta_result: dict) -> dict:
    """Call Anthropic API for Arbiter synthesis."""
    system_prompt = _load_prompt("arbiter")
    user_message = _build_creative_message(creative_data)
    user_message += f"\n\n---\n\n## Alpha Review Result\n"
    user_message += f"Pass: {alpha_result['pass']}\n"
    user_message += f"Fail Reason: {alpha_result['fail_reason']}\n"
    user_message += f"\n## Beta Review Result\n"
    user_message += f"Pass: {beta_result['pass']}\n"
    user_message += f"Fail Reason: {beta_result['fail_reason']}\n"

    try:
        message = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=2048,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        return _parse_arbiter_response(message.content[0].text)
    except Exception as e:
        logger.error(f"Arbiter review failed: {e}")
        return {
            "pass": alpha_result["pass"] and beta_result["pass"],
            "fail_reason": alpha_result["fail_reason"] or beta_result["fail_reason"],
            "verdict": "FLAG FOR REVIEW",
        }


def _parse_review_response(text: str) -> dict:
    """Parse AI response to extract pass/fail and reason."""
    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(text[start:end])
            return {
                "pass": data.get("pass", True),
                "fail_reason": data.get("fail_reason", ""),
            }
    except (json.JSONDecodeError, KeyError):
        pass

    text_lower = text.lower()
    is_fail = "false" in text_lower or "fail" in text_lower or "reject" in text_lower
    return {
        "pass": not is_fail,
        "fail_reason": text[:500] if is_fail else "",
    }


def _parse_arbiter_response(text: str) -> dict:
    """Parse Arbiter AI response."""
    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(text[start:end])
            return {
                "pass": data.get("pass", True),
                "fail_reason": data.get("fail_reason", ""),
                "verdict": data.get("verdict", "APPROVE" if data.get("pass", True) else "REJECT"),
            }
    except (json.JSONDecodeError, KeyError):
        pass

    text_lower = text.lower()
    is_fail = "reject" in text_lower or "false" in text_lower
    is_flag = "flag for review" in text_lower or "uncertain" in text_lower
    return {
        "pass": not is_fail and not is_flag,
        "fail_reason": text[:500] if is_fail or is_flag else "",
        "verdict": "FLAG FOR REVIEW" if is_flag else ("REJECT" if is_fail else "APPROVE"),
    }


def _mock_alpha(creative_data: dict) -> dict:
    """Mock Alpha review — simulates a thorough but passing review."""
    title = creative_data.get("CreativeTitle", "")
    brand = creative_data.get("CampaignBrandName", "")
    cta = creative_data.get("CTAResponse", "")
    url = creative_data.get("targeturl", "")

    issues = []

    if brand and brand.lower() not in title.lower() and brand.lower() not in creative_data.get("CleanCreativeBody", "").lower():
        issues.append(f"Brand name '{brand}' not found in title or body")

    if cta and len(cta) > 20:
        issues.append(f"CTA exceeds 20 characters ({len(cta)} chars)")

    banned_cta = ["proceed", "continue", "next", "keep going", "advance"]
    if cta and cta.lower().strip() in banned_cta:
        issues.append(f"CTA uses banned word: '{cta}'")

    if url and not url.startswith("https://"):
        issues.append("Target URL is not HTTPS")

    if issues:
        return {"pass": False, "fail_reason": " | ".join(issues)}
    return {"pass": True, "fail_reason": ""}


def _mock_beta(creative_data: dict) -> dict:
    """Mock Beta review — simulates a precise, evidence-based review."""
    title = creative_data.get("CreativeTitle", "")
    brand = creative_data.get("CampaignBrandName", "")
    cta = creative_data.get("CTAResponse", "")
    url = creative_data.get("targeturl", "")

    issues = []

    if brand and brand.lower() not in title.lower() and brand.lower() not in creative_data.get("CleanCreativeBody", "").lower():
        issues.append(f"A1: Brand name '{brand}' absent from title and body")

    if cta and len(cta) > 20:
        issues.append(f"B3: CTA '{cta}' is {len(cta)} chars, max 20")

    if url and not url.startswith("https://"):
        issues.append(f"C4: URL '{url}' does not use HTTPS")

    if issues:
        return {"pass": False, "fail_reason": " | ".join(issues)}
    return {"pass": True, "fail_reason": ""}


def _mock_arbiter(creative_data: dict, alpha_result: dict, beta_result: dict) -> dict:
    """Mock Arbiter — synthesizes Alpha and Beta mock results."""
    if alpha_result["pass"] and beta_result["pass"]:
        return {"pass": True, "fail_reason": "", "verdict": "APPROVE"}

    all_reasons = []
    if alpha_result["fail_reason"]:
        all_reasons.append(alpha_result["fail_reason"])
    if beta_result["fail_reason"]:
        all_reasons.append(beta_result["fail_reason"])

    combined = " | ".join(all_reasons) if all_reasons else ""

    if not alpha_result["pass"] and not beta_result["pass"]:
        return {"pass": False, "fail_reason": combined, "verdict": "REJECT"}

    return {"pass": False, "fail_reason": combined, "verdict": "FLAG FOR REVIEW"}

"""
Nexus Mail — Task 5: Risk/Phishing Detection
Checks for phishing indicators, suspicious links, and security risks.
For meeting invitations, focuses on meeting link validation.
"""

from app.ai_worker.ai_provider import ai_provider
import structlog

logger = structlog.get_logger(__name__)

RISK_DETECT_PROMPT = """You are a cybersecurity AI assistant for Nexus Mail.

Analyze this email for security risks and phishing indicators. Check for:

1. Suspicious sender (mismatched display name and email, unknown domains)
2. Urgency tactics ("act now", "account suspended", "verify immediately")
3. Suspicious links (URL shorteners, misspelled domains, non-HTTPS links)
4. Requests for sensitive info (passwords, credit cards, SSN)
5. Grammar/spelling anomalies typical of phishing
6. Suspicious attachments
7. For MEETING INVITATIONS specifically: check meeting links for phishing
   - Legitimate: meet.google.com, zoom.us, teams.microsoft.com
   - Suspicious: misspelled domains, unusual meeting platforms, links that redirect

Respond in JSON format:
{
    "risk_level": "<none | low | medium | high | critical>",
    "risk_flags": [
        "<specific risk description>"
    ],
    "suspicious_links": [
        {
            "url": "<the suspicious URL>",
            "reason": "<why it's suspicious>"
        }
    ],
    "is_phishing": <true or false>,
    "phishing_confidence": <0.0-1.0>,
    "recommendation": "<what the user should do>"
}"""


async def detect_risks(
    subject: str,
    body: str,
    sender: str,
    sender_email: str,
    is_meeting: bool = False,
) -> dict:
    """
    Task 5: Analyze email for security risks and phishing.
    Extra scrutiny on meeting link URLs for meeting invitations.
    """
    meeting_context = "\nIMPORTANT: This is a MEETING INVITATION. Pay special attention to the meeting link URL for phishing indicators." if is_meeting else ""

    user_prompt = f"""Analyze this email for security risks:{meeting_context}

FROM: {sender} <{sender_email}>
SUBJECT: {subject}

BODY:
{body[:3000]}"""

    try:
        result = await ai_provider.complete_json(
            system_prompt=RISK_DETECT_PROMPT,
            user_prompt=user_prompt,
            temperature=0.1,
        )

        risk_flags = result.get("risk_flags", [])
        if risk_flags:
            logger.warning(
                "Risks detected",
                risk_level=result.get("risk_level"),
                flag_count=len(risk_flags),
                is_phishing=result.get("is_phishing", False),
            )

        return result

    except Exception as e:
        logger.error("Risk detection failed", error=str(e))
        return {
            "risk_level": "none",
            "risk_flags": [],
            "suspicious_links": [],
            "is_phishing": False,
            "phishing_confidence": 0.0,
            "recommendation": "Unable to analyze - review manually",
        }

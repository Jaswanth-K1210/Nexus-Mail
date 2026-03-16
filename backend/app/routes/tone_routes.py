"""
Nexus Mail — Tone Learning Routes
Passive tone profile learning and management endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.routes.middleware import get_current_user
from app.services.tone_learning_service import ToneLearningService
from app.core.database import get_database

router = APIRouter(prefix="/tone", tags=["Tone Learning"])
tone_service = ToneLearningService()


class UserContextUpdate(BaseModel):
    role: str = ""                   # e.g. "Startup Founder", "Software Engineer"
    role_key: str = ""               # e.g. "founder", "student" — maps to role_categories.py
    industry: str = ""               # e.g. "SaaS", "Finance", "Healthcare"
    company_size: str = ""           # e.g. "Solo", "Startup (1-10)", "SMB (10-100)", "Enterprise"
    important_senders: list[str] = []  # e.g. ["investors", "clients", "team", "vendors"]
    custom_persona: str = ""         # free-form override


@router.post("/learn")
async def learn_tone(user: dict = Depends(get_current_user)):
    """
    Trigger tone learning from user's sent emails.
    Scans last 25 sent emails and builds a stylistic profile.
    Called automatically on first login, can also be triggered manually.
    """
    return await tone_service.learn_from_sent_emails(user["user_id"])


@router.get("/profile")
async def get_tone_profile(user: dict = Depends(get_current_user)):
    """Get the user's current learned tone profile."""
    profile = await tone_service.get_tone_profile(user["user_id"])
    if not profile:
        return {"status": "not_learned", "profile": None}
    return profile


@router.get("/context")
async def get_user_context(user: dict = Depends(get_current_user)):
    """Get the user's explicitly set professional context."""
    from bson import ObjectId
    db = get_database()
    doc = await db.users.find_one(
        {"_id": ObjectId(user["user_id"])},
        {"user_context": 1}
    )
    return doc.get("user_context", {}) if doc else {}


# ─── Role-aware persona templates ─────────────────────────────────────────────
_ROLE_PERSONAS: dict[str, dict] = {
    "student": {
        "intro": "I am a {role} studying {industry}.",
        "priorities": "Emails about assignments, exams, internships, scholarships, and faculty communication are high priority for me.",
    },
    "working_professional": {
        "intro": "I am a {role} in the {industry} sector at a {size} organisation.",
        "priorities": "Emails about tasks, deadlines, approvals, client work, and internal updates are high priority for me.",
    },
    "founder": {
        "intro": "I am a {role} in the {industry} space, running a {size} startup.",
        "priorities": "Emails about fundraising, investor updates, customer feedback, hiring, partnerships, and product are high priority for me.",
    },
    "influencer": {
        "intro": "I am a {role} in the {industry} space.",
        "priorities": "Emails about brand deals, collaboration requests, agency communication, payments, and platform updates are high priority for me.",
    },
    "freelancer": {
        "intro": "I am a {role} working in {industry}.",
        "priorities": "Emails about project inquiries, client communication, invoices, contracts, and deadlines are high priority for me.",
    },
    "business_owner": {
        "intro": "I am a {role} in the {industry} sector, running a {size} business.",
        "priorities": "Emails about customer orders, supplier communication, staff matters, financials, and legal compliance are high priority for me.",
    },
    "healthcare": {
        "intro": "I am a {role} in the {industry} field.",
        "priorities": "Emails about patient communication, lab results, clinical trials, compliance, and continuing medical education are high priority for me.",
    },
    "legal": {
        "intro": "I am a {role} in the {industry} field.",
        "priorities": "Emails about case updates, court notices, client communication, document reviews, and billing are high priority for me.",
    },
    "educator": {
        "intro": "I am a {role} in {industry}.",
        "priorities": "Emails about student communication, parent messages, administrative directives, grading, and research are high priority for me.",
    },
    "trades": {
        "intro": "I am a {role} in the {industry} sector.",
        "priorities": "Emails about work orders, site updates, parts procurement, client communication, and safety compliance are high priority for me.",
    },
    "real_estate": {
        "intro": "I am a {role} in the {industry} market.",
        "priorities": "Emails about listing inquiries, offers, escrow updates, client communication, and mortgage/lending are high priority for me.",
    },
    "nonprofit": {
        "intro": "I am a {role} in the {industry} sector.",
        "priorities": "Emails about donor communication, grant applications, volunteer coordination, events, and impact reports are high priority for me.",
    },
    "finance": {
        "intro": "I am a {role} in the {industry} sector.",
        "priorities": "Emails about audits, compliance, financial reports, tax filings, and client accounts are high priority for me.",
    },
    "sales_marketing": {
        "intro": "I am a {role} in the {industry} sector at a {size} company.",
        "priorities": "Emails about inbound leads, deal updates, campaign reports, partner communication, and events are high priority for me.",
    },
}

_DEFAULT_PERSONA = {
    "intro": "I am a {role} in the {industry} field.",
    "priorities": "Emails that are directly relevant to my work and require my response are high priority for me.",
}


def _build_persona(role_key: str, role: str, industry: str, size: str, important_str: str) -> str:
    """Generate a role-appropriate persona string for the AI classifier."""
    template = _ROLE_PERSONAS.get(role_key, _DEFAULT_PERSONA)

    intro = template["intro"].format(
        role=role,
        industry=industry or "my field",
        size=size or "my",
    )

    senders_line = ""
    if important_str:
        senders_line = f" My most important emails come from: {important_str}."

    return f"{intro}{senders_line} {template['priorities']}"


@router.patch("/context")
async def update_user_context(
    body: UserContextUpdate,
    user: dict = Depends(get_current_user)
):
    """
    Let users explicitly declare their professional role and context.
    This is merged with the passively-learned tone profile and injected
    into the email classifier prompt so emails are prioritised correctly
    from day 1 — before enough sent emails exist for passive learning.
    """
    import structlog
    _logger = structlog.get_logger(__name__)

    try:
        from bson import ObjectId
        db = get_database()

        # Build a role-aware persona string for the AI prompt
        important_str = ", ".join(body.important_senders) if body.important_senders else ""
        role_str = body.role or "professional"
        industry_str = body.industry or ""
        size_str = body.company_size or ""
        role_key = body.role_key or ""

        if body.custom_persona.strip():
            persona = body.custom_persona.strip()
        else:
            persona = _build_persona(role_key, role_str, industry_str, size_str, important_str)

        context_doc = {
            "role": body.role,
            "role_key": body.role_key,
            "industry": body.industry,
            "company_size": body.company_size,
            "important_senders": body.important_senders,
            "custom_persona": body.custom_persona,
            "generated_persona": persona,
        }

        user_doc = await db.users.find_one(
            {"_id": ObjectId(user["user_id"])},
            {"tone_profile": 1},
        )

        update_fields: dict = {"user_context": context_doc}

        # Only set nested field if tone_profile already exists as a dict;
        # otherwise initialize it with the persona.
        if user_doc and isinstance(user_doc.get("tone_profile"), dict):
            update_fields["tone_profile.professional_persona"] = persona
        else:
            update_fields["tone_profile"] = {"professional_persona": persona}

        await db.users.update_one(
            {"_id": ObjectId(user["user_id"])},
            {"$set": update_fields},
            upsert=False,
        )

        return {"status": "saved", "persona": persona}

    except Exception as e:
        _logger.error("Failed to update user context", error=str(e), user_id=user.get("user_id"))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save preferences: {str(e)}",
        )


@router.get("/role")
async def get_user_role(user: dict = Depends(get_current_user)):
    """Get the user's selected role key and its category list."""
    from bson import ObjectId
    from app.ai_worker.role_categories import (
        get_role_categories, get_role_display, VALID_ROLES, ROLE_DEFINITIONS,
    )

    db = get_database()
    doc = await db.users.find_one(
        {"_id": ObjectId(user["user_id"])},
        {"user_context.role_key": 1},
    )
    role_key = (doc.get("user_context", {}).get("role_key", "") if doc else "")

    if role_key and role_key in VALID_ROLES:
        display = get_role_display(role_key)
        categories = get_role_categories(role_key)
        return {"role_key": role_key, **display, "categories": categories}

    # No role set — return available roles so frontend can prompt selection
    roles = [
        {"key": k, "name": v["name"], "emoji": v["emoji"]}
        for k, v in ROLE_DEFINITIONS.items()
    ]
    return {"role_key": None, "available_roles": roles}


@router.post("/refresh")
async def refresh_tone(user: dict = Depends(get_current_user)):
    """Refresh the tone profile if it's older than 7 days, otherwise skip."""
    return await tone_service.refresh_if_stale(user["user_id"])

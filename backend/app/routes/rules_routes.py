"""
Nexus Mail — Rules Routes
Natural language email rules CRUD and testing endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from app.routes.middleware import get_current_user
from app.services.rules_engine import RulesEngine

router = APIRouter(prefix="/rules", tags=["Natural Language Rules"])
rules_engine = RulesEngine()


class CreateRuleRequest(BaseModel):
    rule_text: str = Field(
        ...,
        min_length=5,
        max_length=500,
        description="Natural language rule, e.g. 'Emails from investors get labeled VIP'",
    )


class UpdateRuleRequest(BaseModel):
    rule_text: Optional[str] = Field(None, min_length=5, max_length=500)
    is_active: Optional[bool] = None


class TestRuleRequest(BaseModel):
    email_id: str


@router.post("")
async def create_rule(
    body: CreateRuleRequest, user: dict = Depends(get_current_user)
):
    """
    Create a new email rule from natural language.

    Examples:
    - "Emails from @company.com → label VIP and mark important"
    - "Newsletters I haven't read in 30 days → auto-archive"
    - "Meeting invitations from the QA team → auto-accept if I'm free"
    - "First-time senders pitching a product → archive and label Cold Email"
    """
    return await rules_engine.create_rule(user["user_id"], body.rule_text)


@router.get("")
async def list_rules(user: dict = Depends(get_current_user)):
    """List all rules for the current user."""
    rules = await rules_engine.get_rules(user["user_id"])
    return {"rules": rules, "count": len(rules)}


@router.put("/{rule_id}")
async def update_rule(
    rule_id: str,
    body: UpdateRuleRequest,
    user: dict = Depends(get_current_user),
):
    """Update a rule — provide new text to recompile, or toggle active state."""
    try:
        return await rules_engine.update_rule(
            rule_id, user["user_id"], body.rule_text, body.is_active
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{rule_id}")
async def delete_rule(rule_id: str, user: dict = Depends(get_current_user)):
    """Delete a rule."""
    try:
        return await rules_engine.delete_rule(rule_id, user["user_id"])
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{rule_id}/test")
async def test_rule(
    rule_id: str,
    body: TestRuleRequest,
    user: dict = Depends(get_current_user),
):
    """Test a rule against a specific email to preview matching behavior."""
    try:
        return await rules_engine.test_rule(user["user_id"], rule_id, body.email_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

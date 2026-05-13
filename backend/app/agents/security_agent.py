"""
Nexus Mail — Security Review Agent

Responsibilities:
- Phishing detection (wraps risk_detect.py)
- Social engineering pattern detection
- Suspicious sender analysis
- Risk escalation with reasoning

Runs for every email. Produces risk assessment with confidence scoring.
"""

from app.agents.base import BaseAgent, AgentResult
from app.agents.state import WorkflowState, Checkpoint

import structlog

logger = structlog.get_logger(__name__)


class SecurityAgent(BaseAgent):
    """
    Security Review Agent — analyzes emails for threats and suspicious patterns.
    Wraps existing risk_detect.py with enhanced reasoning, sender reputation,
    and human-in-the-loop escalation for high-risk detections.
    """

    name = "security_agent"
    description = "Detects phishing, social engineering, and security risks in emails"
    max_retries = 2

    async def _execute(self, state: WorkflowState) -> AgentResult:
        from app.ai_worker.tasks.risk_detect import detect_risks

        email = state.email
        if not email:
            raise ValueError("No email context in state")

        # Run existing risk detection
        risks = await detect_risks(
            subject=email.subject,
            body=email.body,
            sender=email.sender_name,
            sender_email=email.sender_email,
            is_meeting=state.is_meeting,
        )

        risk_level = risks.get("risk_level", "none")
        risk_flags = risks.get("risk_flags", [])
        is_phishing = risks.get("is_phishing", False)
        phishing_confidence = risks.get("phishing_confidence", 0.0)
        suspicious_links = risks.get("suspicious_links", [])

        # ─── Enhanced: Sender Reputation Check ────────────────────────────
        sender_profile = state.sender_profile
        is_cold = sender_profile.get("is_cold_sender", False)
        relationship = sender_profile.get("relationship_strength", 0)

        # Elevate risk for cold senders with suspicious content
        if is_cold and risk_level in ("medium", "high"):
            risk_level = "high"
            risk_flags.append("Cold sender with suspicious content — elevated risk")

        # ─── Human-in-the-Loop: Escalate critical threats ─────────────────
        if is_phishing and phishing_confidence >= 0.8:
            state.checkpoints.append(Checkpoint(
                agent=self.name,
                action="block_and_report_phishing",
                reason=f"High-confidence phishing detected ({phishing_confidence:.0%}): {', '.join(risk_flags[:2])}",
                requires_approval=True,
            ))
            state.requires_human_approval = True

        # Build reasoning
        reasoning_steps = [
            {
                "thought": f"Scanning email from {email.sender_email} for security threats",
                "action": "AI risk detection (phishing, social engineering, suspicious links)",
                "observation": f"Risk level: {risk_level}, Flags: {len(risk_flags)}, Phishing: {is_phishing} ({phishing_confidence:.0%})",
            },
        ]

        if sender_profile:
            reasoning_steps.append({
                "thought": "Cross-referencing with sender reputation",
                "action": "Sender reputation check",
                "observation": f"Relationship: {relationship:.2f}, Cold sender: {is_cold}",
            })

        if suspicious_links:
            reasoning_steps.append({
                "thought": f"Found {len(suspicious_links)} suspicious link(s)",
                "action": "Link analysis",
                "observation": "; ".join(f"{l.get('url', '')[:40]}... — {l.get('reason', '')}" for l in suspicious_links[:3]),
            })

        if risk_level in ("high", "critical") or is_phishing:
            decision = f"⚠️ SECURITY ALERT: {risk_level} risk — {', '.join(risk_flags[:2])}"
        elif risk_level == "medium":
            decision = f"Moderate risk detected — {len(risk_flags)} flag(s)"
        else:
            decision = "No significant security risks detected"

        confidence = phishing_confidence if is_phishing else (0.5 if risk_flags else 0.9)

        reasoning = self._build_reasoning(
            decision=decision,
            reason=f"Risk level: {risk_level}, Phishing: {is_phishing}, Cold sender: {is_cold}",
            confidence=confidence,
            steps=reasoning_steps,
        )

        output = {
            "risks": risks,
            "risk_level": risk_level,
            "risk_flags": risk_flags,
            "is_phishing": is_phishing,
            "phishing_confidence": phishing_confidence,
            "suspicious_links": suspicious_links,
            "sender_reputation": {
                "is_cold": is_cold,
                "relationship_strength": relationship,
            },
            "_decision": decision,
        }

        return AgentResult(
            agent_name=self.name,
            output=output,
            reasoning=reasoning,
        )

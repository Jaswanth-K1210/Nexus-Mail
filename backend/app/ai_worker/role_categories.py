"""
Nexus Mail — Role-Based Category Definitions
Defines the 14 user roles, their role-specific email categories, shared categories,
and helpers for generating role-aware classification prompts.

This is a standalone definitions file — no imports from other app modules.
"""

# ---------------------------------------------------------------------------
# Shared categories present for every role
# ---------------------------------------------------------------------------

SHARED_CATEGORIES: list[str] = [
    "meeting_invitation",
    "newsletter",
    "transactional",
    "promotional",
    "spam",
    "important",
]

# ---------------------------------------------------------------------------
# Role definitions
# Each entry maps a role key to:
#   name  — human-readable display name
#   emoji — single emoji representing the role
#   categories — role-specific categories (shared ones are added automatically)
# ---------------------------------------------------------------------------

ROLE_DEFINITIONS: dict[str, dict] = {
    "student": {
        "name": "Student",
        "emoji": "🎓",
        "categories": [
            "assignment",
            "exam_notice",
            "internship",
            "interview",
            "job_application",
            "scholarship",
            "campus_event",
            "faculty_communication",
            "study_group",
        ],
    },
    "working_professional": {
        "name": "Working Professional",
        "emoji": "💼",
        "categories": [
            "task_assigned",
            "deadline_reminder",
            "approval_required",
            "client_communication",
            "internal_update",
            "hr_update",
            "interview",
            "training",
        ],
    },
    "founder": {
        "name": "Founder",
        "emoji": "🚀",
        "categories": [
            "investor_communication",
            "fundraising",
            "customer_feedback",
            "partnership",
            "hiring",
            "legal_compliance",
            "press_media",
            "cold_outreach",
            "product_update",
        ],
    },
    "influencer": {
        "name": "Influencer / Creator",
        "emoji": "🎤",
        "categories": [
            "brand_deal",
            "deliverable_request",
            "agency_communication",
            "collab_request",
            "payment",
            "platform_update",
            "event_invite",
            "legal",
            "fan_dm",
        ],
    },
    "freelancer": {
        "name": "Freelancer",
        "emoji": "🖥️",
        "categories": [
            "new_project_inquiry",
            "client_communication",
            "invoice_payment",
            "contract",
            "revision_request",
            "platform_notification",
            "deadline_reminder",
            "legal",
        ],
    },
    "business_owner": {
        "name": "Business Owner",
        "emoji": "🏢",
        "categories": [
            "vendor_supplier",
            "customer_order",
            "financial",
            "staff_hr",
            "legal_compliance",
            "partnership",
            "marketing",
            "operations",
        ],
    },
    "healthcare": {
        "name": "Healthcare Professional",
        "emoji": "🩺",
        "categories": [
            "patient_communication",
            "lab_results",
            "prescription_refill",
            "clinical_trial",
            "conference_cme",
            "admin_compliance",
            "pharma_update",
            "peer_review",
        ],
    },
    "legal": {
        "name": "Legal Professional",
        "emoji": "⚖️",
        "categories": [
            "case_update",
            "client_communication",
            "opposing_counsel",
            "court_notice",
            "document_review",
            "billing_invoice",
            "legal_research",
            "bar_association",
        ],
    },
    "educator": {
        "name": "Educator",
        "emoji": "📚",
        "categories": [
            "student_communication",
            "parent_communication",
            "admin_directive",
            "exam_grading",
            "research",
            "conference",
            "peer_review",
            "training_pd",
        ],
    },
    "trades": {
        "name": "Trades Worker",
        "emoji": "🔧",
        "categories": [
            "work_order",
            "parts_procurement",
            "site_update",
            "client_site_communication",
            "compliance_safety",
            "training",
            "invoice_payment",
            "vendor_supplier",
        ],
    },
    "real_estate": {
        "name": "Real Estate Agent",
        "emoji": "🏠",
        "categories": [
            "listing_inquiry",
            "offer_negotiation",
            "escrow_legal",
            "client_communication",
            "mls_update",
            "lending_mortgage",
            "commission_payment",
            "marketing",
        ],
    },
    "nonprofit": {
        "name": "Nonprofit Professional",
        "emoji": "🤝",
        "categories": [
            "donor_communication",
            "grant_application",
            "volunteer_coordination",
            "beneficiary_update",
            "government_compliance",
            "event_fundraiser",
            "partnership",
            "internal_update",
        ],
    },
    "finance": {
        "name": "Finance Professional",
        "emoji": "📊",
        "categories": [
            "audit_compliance",
            "client_financial_report",
            "tax_filing",
            "investment_update",
            "banking_treasury",
            "payroll",
            "invoice_reconciliation",
            "budget_planning",
        ],
    },
    "sales_marketing": {
        "name": "Sales & Marketing Professional",
        "emoji": "📣",
        "categories": [
            "lead_inbound",
            "prospect_followup",
            "deal_update",
            "client_success",
            "campaign_report",
            "content_asset",
            "partner_affiliate",
            "event_webinar",
            "tool_crm_notification",
        ],
    },
}

# ---------------------------------------------------------------------------
# Flat list of all valid role keys
# ---------------------------------------------------------------------------

VALID_ROLES: list[str] = list(ROLE_DEFINITIONS.keys())

# ---------------------------------------------------------------------------
# Per-category descriptions used when building prompts
# ---------------------------------------------------------------------------

_CATEGORY_DESCRIPTIONS: dict[str, str] = {
    # --- Shared ---
    "meeting_invitation": "Emails proposing a meeting, call, sync, demo, interview, or containing .ics attachments",
    "newsletter": "Periodic digest or subscription content from publications, blogs, or mailing lists",
    "transactional": "Receipts, order confirmations, shipping updates, password resets, or account alerts",
    "promotional": "Marketing emails, sales offers, discount codes, or product announcements",
    "spam": "Junk mail, phishing attempts, suspicious or unsolicited bulk messages",
    "important": "Urgent, action-required emails from known contacts that do not fit a more specific category",

    # --- Student ---
    "assignment": "Course assignments, homework submissions, or project briefs from instructors or course platforms",
    "exam_notice": "Exam schedules, study guides, proctoring instructions, or grade release notifications",
    "internship": "Internship postings, application status updates, or onboarding instructions",
    "interview": "Interview invitations, scheduling requests, or interview outcome notifications",
    "job_application": "Job application acknowledgements, recruiter outreach, or career fair invitations",
    "scholarship": "Scholarship announcements, application deadlines, award notifications, or financial aid updates",
    "campus_event": "University events, club activities, career fairs, or student organization announcements",
    "faculty_communication": "Direct emails from professors, advisors, department staff, or academic offices",
    "study_group": "Messages from classmates coordinating study sessions, group projects, or shared resources",

    # --- Working Professional ---
    "task_assigned": "Work tasks, tickets, or action items formally assigned to the user by a manager or system",
    "deadline_reminder": "Reminders about approaching deadlines for projects, reports, or deliverables",
    "approval_required": "Requests for the user's approval, sign-off, or formal authorisation on a decision or document",
    "client_communication": "Emails from clients or customers regarding ongoing work, requests, or relationship management",
    "internal_update": "Company-wide or team announcements, policy changes, or status updates from internal stakeholders",
    "hr_update": "HR announcements about benefits, payroll, performance reviews, onboarding, or company policies",
    "training": "Training session invitations, e-learning course enrolments, or professional development resources",

    # --- Founder ---
    "investor_communication": "Emails from existing or prospective investors, VCs, angels, or board members",
    "fundraising": "Fundraising round updates, term sheet discussions, cap table requests, or pitch feedback",
    "customer_feedback": "User feedback, NPS surveys, support escalations, or testimonials from customers",
    "partnership": "Business partnership proposals, co-marketing opportunities, or strategic alliance discussions",
    "hiring": "Recruiting pipeline updates, candidate applications, offer letters, or staffing agency outreach",
    "legal_compliance": "Legal notices, regulatory compliance requirements, contracts, or terms review requests",
    "press_media": "Press coverage, journalist inquiries, PR opportunities, or media kit requests",
    "cold_outreach": "Unsolicited sales pitches, vendor demos, or partnership requests from unknown parties",
    "product_update": "Internal or external product roadmap updates, feature launches, or beta announcements",

    # --- Influencer ---
    "brand_deal": "Brand sponsorship proposals, collaboration offers, or paid partnership negotiations",
    "deliverable_request": "Requests from brands or managers for content deliverables, drafts, or posting deadlines",
    "agency_communication": "Emails from talent agencies, management companies, or booking agents",
    "collab_request": "Collaboration requests from other creators, co-creation pitches, or guest appearance invitations",
    "payment": "Payment confirmations, invoices, late payment notices, or revenue share statements",
    "platform_update": "Policy or algorithm updates, monetisation changes, or feature announcements from platforms",
    "event_invite": "Invitations to brand events, launches, press trips, or creator summits",
    "legal": "Contracts, NDAs, IP disputes, DMCA notices, or legal correspondence requiring review",
    "fan_dm": "Direct messages or emails from fans, followers, or community members",

    # --- Freelancer ---
    "new_project_inquiry": "Prospective clients inquiring about availability, rates, or fit for a new project",
    "invoice_payment": "Invoice receipts, payment confirmations, overdue payment notices, or billing disputes",
    "contract": "Contract drafts, amendments, signing requests, or work agreement confirmations",
    "revision_request": "Client requests for changes, edits, or revisions to previously submitted work",
    "platform_notification": "Notifications from freelance platforms (Upwork, Fiverr, Toptal) about bids, reviews, or policy changes",

    # --- Business Owner ---
    "vendor_supplier": "Emails from suppliers, vendors, or distributors about orders, pricing, or account management",
    "customer_order": "Customer purchase orders, order status inquiries, returns, or fulfilment updates",
    "financial": "Bank statements, accounting reports, expense approvals, or financial summaries",
    "staff_hr": "Staff management emails covering hiring, payroll, scheduling, or performance matters",
    "marketing": "Marketing campaign reports, agency briefs, ad performance updates, or creative approvals",
    "operations": "Operational updates covering logistics, facilities, IT, or day-to-day business processes",

    # --- Healthcare ---
    "patient_communication": "Emails from or about patients regarding appointments, treatment, or care coordination",
    "lab_results": "Laboratory test results, diagnostic reports, or pathology findings",
    "prescription_refill": "Prescription refill requests, pharmacy notifications, or medication authorisation emails",
    "clinical_trial": "Clinical trial recruitment, protocol updates, IRB communications, or research study notices",
    "conference_cme": "Medical conference invitations, CME course enrolments, or continuing education credits",
    "admin_compliance": "Hospital or clinic administrative directives, regulatory compliance notices, or credentialing updates",
    "pharma_update": "Pharmaceutical company communications about drug updates, samples, or rep visits",
    "peer_review": "Peer review requests, journal submission feedback, or research manuscript correspondence",

    # --- Legal ---
    "case_update": "Updates on active legal cases including filings, status changes, or opposing motions",
    "opposing_counsel": "Correspondence from opposing counsel, co-counsel, or other attorneys in a matter",
    "court_notice": "Official court notices, hearing schedules, filing deadlines, or clerk communications",
    "document_review": "Requests to review, redline, or approve legal documents, agreements, or briefs",
    "billing_invoice": "Legal billing statements, time entry summaries, client invoices, or expense reports",
    "legal_research": "Research memos, case law summaries, or regulatory analysis from associates or research services",
    "bar_association": "Communications from bar associations regarding dues, CLE requirements, or disciplinary notices",

    # --- Educator ---
    "student_communication": "Emails from students regarding coursework, grades, accommodations, or general inquiries",
    "parent_communication": "Emails from parents or guardians regarding student performance or school matters",
    "admin_directive": "Directives, policy memos, or announcements from school administration or department heads",
    "exam_grading": "Grading-related emails including rubric discussions, grade disputes, or exam logistics",
    "research": "Research collaboration invitations, grant opportunities, or academic publication correspondence",
    "conference": "Academic conference calls for papers, registration confirmations, or presentation schedules",
    "training_pd": "Professional development workshops, teacher training sessions, or certification course notices",

    # --- Trades ---
    "work_order": "New work orders, job assignments, service requests, or task dispatches from supervisors or clients",
    "parts_procurement": "Parts and materials ordering, supplier quotes, procurement approvals, or delivery confirmations",
    "site_update": "On-site status updates, project progress reports, inspection results, or site access notices",
    "client_site_communication": "Direct communication from clients regarding site access, scope changes, or satisfaction",
    "compliance_safety": "Safety regulations, compliance audits, incident reports, or certification renewal notices",

    # --- Real Estate ---
    "listing_inquiry": "Buyer or tenant inquiries about a specific property listing, showings, or availability",
    "offer_negotiation": "Purchase offers, counteroffers, acceptance letters, or negotiation correspondence",
    "escrow_legal": "Escrow instructions, title reports, closing documents, or legal review requests for transactions",
    "mls_update": "MLS listing status changes, new comparable listings, or market data alerts",
    "lending_mortgage": "Mortgage pre-approval updates, lender correspondence, or loan condition requests",
    "commission_payment": "Commission disbursement notices, brokerage splits, or referral fee confirmations",

    # --- Nonprofit ---
    "donor_communication": "Emails from donors, major gift prospects, or fundraising campaign respondents",
    "grant_application": "Grant application submissions, funder RFP announcements, award decisions, or reporting deadlines",
    "volunteer_coordination": "Volunteer sign-ups, scheduling, training materials, or recognition communications",
    "beneficiary_update": "Updates from or about programme beneficiaries, impact reports, or service delivery notes",
    "government_compliance": "Government agency correspondence, tax-exempt status notices, or regulatory filing requirements",
    "event_fundraiser": "Fundraising event logistics, ticket sales, sponsorship confirmations, or gala planning emails",

    # --- Finance ---
    "audit_compliance": "Internal or external audit requests, compliance certifications, or regulatory examination notices",
    "client_financial_report": "Financial statements, portfolio reports, or performance summaries sent to or received from clients",
    "tax_filing": "Tax return preparation requests, filing deadlines, IRS/HMRC correspondence, or tax document distribution",
    "investment_update": "Investment portfolio updates, market research reports, or asset management communications",
    "banking_treasury": "Bank account notices, treasury operations updates, wire transfer confirmations, or liquidity reports",
    "payroll": "Payroll processing confirmations, direct deposit notices, or compensation adjustment communications",
    "invoice_reconciliation": "Invoice matching, accounts payable/receivable reconciliation, or discrepancy resolution emails",
    "budget_planning": "Budget proposal requests, variance analysis, forecast updates, or financial planning cycle emails",

    # --- Sales & Marketing ---
    "lead_inbound": "New inbound leads from web forms, referrals, or marketing campaigns requesting information",
    "prospect_followup": "Follow-up emails in active sales sequences, prospect responses, or re-engagement outreach",
    "deal_update": "CRM deal stage updates, pipeline reviews, proposal submissions, or contract negotiations",
    "client_success": "Existing client check-ins, renewal discussions, upsell opportunities, or satisfaction feedback",
    "campaign_report": "Marketing campaign performance reports, A/B test results, or channel analytics summaries",
    "content_asset": "Content briefs, creative asset approvals, copy reviews, or design delivery notifications",
    "partner_affiliate": "Affiliate programme updates, partner co-marketing opportunities, or channel partner communications",
    "event_webinar": "Webinar registrations, virtual event logistics, trade show planning, or speaking engagements",
    "tool_crm_notification": "Automated notifications from CRM, marketing automation, or sales engagement platforms",
}

# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def get_role_categories(role_key: str) -> list[str]:
    """Return the full list of categories for a role (role-specific + shared)."""
    if role_key not in ROLE_DEFINITIONS:
        raise ValueError(f"Unknown role key: {role_key!r}. Valid roles: {VALID_ROLES}")
    role_specific = ROLE_DEFINITIONS[role_key]["categories"]
    # Preserve order: role-specific first, then shared (deduped)
    seen = set(role_specific)
    combined = list(role_specific)
    for cat in SHARED_CATEGORIES:
        if cat not in seen:
            combined.append(cat)
            seen.add(cat)
    return combined


def get_role_display(role_key: str) -> dict:
    """Return {key, name, emoji} for the given role."""
    if role_key not in ROLE_DEFINITIONS:
        raise ValueError(f"Unknown role key: {role_key!r}. Valid roles: {VALID_ROLES}")
    defn = ROLE_DEFINITIONS[role_key]
    return {
        "key": role_key,
        "name": defn["name"],
        "emoji": defn["emoji"],
    }


def get_role_prompt(role_key: str) -> str:
    """
    Return a classification system prompt tailored to the given role.

    The response format matches what classify.py expects:
      Category: <category>
      Suggested Action: <action>
      Severity: <1-5>
      Is Meeting Invitation: <true|false>
      Confidence: <0.0-1.0>
      Reasoning: <brief explanation>
    """
    if role_key not in ROLE_DEFINITIONS:
        raise ValueError(f"Unknown role key: {role_key!r}. Valid roles: {VALID_ROLES}")

    display = get_role_display(role_key)
    categories = get_role_categories(role_key)
    total = len(categories)

    # Build numbered category list with descriptions
    lines: list[str] = []
    for i, cat in enumerate(categories, start=1):
        description = _CATEGORY_DESCRIPTIONS.get(
            cat, "Emails related to " + cat.replace("_", " ")
        )
        lines.append(f'{i}. "{cat}" — {description}')
    numbered_categories = "\n".join(lines)

    prompt = f"""You are an expert email classifier for Nexus Mail.
The user is a {display['name']}.

Use the USER PERSONA PROFILE (if provided) to personalise the classification and Suggested Action based on who the user is and what they likely care about.
- Elevate the priority and Suggested Action for emails directly relevant to their role as a {display['name']}.
- Downgrade standard or generic emails to "LOW RELEVANCE" or "AUTO-ARCHIVE" if they are not relevant to this role.

Classify the email into EXACTLY ONE of these {total} categories:
{numbered_categories}

For meeting detection, look for AT LEAST TWO of these signals:
- Subject contains: meeting, call, sync, catch up, interview, demo, discussion, let's connect, availability
- Body contains a specific date/time: "Thursday at 3pm", "March 10th, 10:30 AM"
- Body contains a meeting link: Zoom, Google Meet, Teams, Calendly URL
- Body asks about availability: "are you available", "does this time work", "when are you free"
- Email has a .ics calendar attachment

IMPORTANT: If the email has a .ics attachment, ALWAYS classify as "meeting_invitation" regardless of other signals.

Analyze the email and also provide a Suggested Action. It must be EXACTLY ONE of these 4 verdicts:
1. "ACTION REQUIRED" (User must write a reply, click a link to approve something, pay an invoice, or schedule a meeting).
2. "REVIEW ONLY" (Important information from a boss or client, system alerts requiring awareness, but no direct reply is needed).
3. "LOW RELEVANCE" (Newsletters, generic updates, social notifications — safe to skim and ignore).
4. "AUTO-ARCHIVE" (Cold sales emails, pure promotional spam, or noise the user should delete without reading).

Respond in plain text exactly in this format (no json, no quotes):
Category: <one of the {total} categories>
Suggested Action: <one of the 4 actions>
Severity: <1-5 integer>
Is Meeting Invitation: <true or false>
Confidence: <0.0-1.0>
Reasoning: <brief explanation>"""

    return prompt

"""Editable influencer collaboration agreement (Markdown template + LLM fill).

Always carries the not-legal-advice notice. No e-signature workflow.
"""
import json
import re
from datetime import date

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from services.ai_providers.openai_client import OpenAIChatClient

DISCLAIMER = (
    "> **AI-generated template for review. This is not legal advice. "
    "Have qualified counsel review before signing.**"
)

REQUIRED_SECTIONS = [
    "Parties", "Campaign", "Deliverables", "Platforms", "Content Deadlines",
    "Revisions & Approval", "Posting Window", "Compensation & Payment Milestones",
    "Taxes", "Usage Rights", "Whitelisting & Paid Media", "Content Ownership",
    "Exclusivity & Competitor Restrictions", "Disclosure Obligations",
    "Performance Reporting", "Cancellation & Takedown", "Morality & Brand Safety",
    "Confidentiality", "Termination", "Dispute Resolution & Jurisdiction",
    "Signatures",
]


async def generate_contract(fields: dict) -> dict:
    system = (
        "You draft an influencer collaboration agreement in Markdown. Include ALL the "
        "section headings provided, in order, as `##` headings. Use the provided field "
        "values; where a value is missing use a clearly bracketed placeholder like "
        "[TO BE COMPLETED]. Keep language plain and professional. Do not add legal "
        "guarantees or claim the document is legally binding advice."
    )
    user = (
        f"Today: {date.today().isoformat()}\n"
        f"Fields: {json.dumps(fields)[:3000]}\n"
        f"Required section headings (## each): {', '.join(REQUIRED_SECTIONS)}\n"
        "For Dispute Resolution use a [JURISDICTION] placeholder unless a jurisdiction was given. "
        "End with signature placeholder blocks for both parties (name, title, date, signature line)."
    )
    body = await OpenAIChatClient().complete(system, user, max_tokens=2800)
    if not body:
        return {"status": "error", "message": "Contract generation failed — retry"}

    markdown = f"# Influencer Collaboration Agreement\n\n{DISCLAIMER}\n\n{body.strip()}\n\n{DISCLAIMER}\n"
    missing = [s for s in REQUIRED_SECTIONS if not re.search(rf"^##\s+.*{re.escape(s.split(' &')[0].split(' ')[0])}", markdown, re.MULTILINE | re.IGNORECASE)]
    return {
        "status": "ok",
        "editable": True,
        "format": "markdown",
        "disclaimer": DISCLAIMER,
        "sections_missing": missing,
        "markdown": markdown,
    }

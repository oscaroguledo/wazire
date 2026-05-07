from __future__ import annotations

import httpx
from typing import Dict, Any
from pathlib import Path
from datetime import datetime

from core.config import get_settings

TEMPLATE_DIR = Path(__file__).resolve().parents[2] / "templates" / "emails"


def _load_template(name: str) -> str:
    p = TEMPLATE_DIR / name
    return p.read_text(encoding="utf-8")


async def send_email(subject: str, to_email: str, html_content: str, plain_text: str | None = None) -> Dict[str, Any]:
    """Send a transactional email via Brevo (Sendinblue) HTTP API.

    This is intentionally minimal: it sends raw HTML content as the email body. Caller
    should ensure `get_settings().BREVO_API_KEY` and sender fields are configured.
    """
    settings = get_settings()
    api_key = settings.BREVO_API_KEY.get_secret_value() if settings.BREVO_API_KEY else None
    if not api_key:
        raise RuntimeError("BREVO_API_KEY not configured")

    payload = {
        "sender": {"name": settings.BREVO_SENDER_NAME, "email": settings.BREVO_SENDER_EMAIL},
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": html_content,
    }
    if plain_text:
        payload["textContent"] = plain_text

    headers = {"api-key": api_key, "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post("https://api.brevo.com/v3/smtp/email", json=payload, headers=headers)
        r.raise_for_status()
        return r.json()


async def send_verification_email(to_email: str, verify_url: str, full_name: str | None = None) -> Dict[str, Any]:
    tpl = _load_template("verify_email.html")
    html = tpl.format(full_name=full_name or "", verify_url=verify_url, year=datetime.utcnow().year)
    return await send_email("Verify your email", to_email, html)


async def send_invoice_email(to_email: str, invoice_html_snippet: str, invoice_number: str) -> Dict[str, Any]:
    tpl = _load_template("invoice.html")
    html = tpl.format(invoice_html=invoice_html_snippet, invoice_number=invoice_number, year=datetime.utcnow().year)
    return await send_email(f"Invoice #{invoice_number}", to_email, html)


async def send_delete_tenant_email(to_email: str, tenant_name: str) -> Dict[str, Any]:
    tpl = _load_template("delete_tenant.html")
    html = tpl.format(tenant_name=tenant_name, year=datetime.utcnow().year)
    return await send_email(f"Tenant deleted: {tenant_name}", to_email, html)

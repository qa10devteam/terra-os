"""Faza 81 — Onboarding email service (placeholder).

Logs emails to /tmp/terra_emails.log when SMTP is not configured.
Replace with Resend / SendGrid / SMTP in production.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone


_LOG_FILE = os.getenv("EMAIL_LOG_FILE", "/tmp/terra_emails.log")


def send_welcome_email(to_email: str, user_name: str) -> bool:
    """Send welcome email to newly registered user.

    Falls back to file logging if SMTP_HOST is not set.
    Returns True on success (including logged-only mode).
    """
    if not os.getenv("SMTP_HOST"):
        _log_email(
            to=to_email,
            template="welcome",
            data={"name": user_name},
        )
        return True

    # TODO: integrate Resend / SMTP
    # Example with Resend:
    # import httpx
    # resp = httpx.post("https://api.resend.com/emails", json={...}, headers={"Authorization": f"Bearer {os.getenv('RESEND_API_KEY')}"})
    # return resp.status_code == 200
    return False


def send_password_reset_email(to_email: str, reset_token: str) -> bool:
    """Send password reset email (placeholder)."""
    if not os.getenv("SMTP_HOST"):
        _log_email(
            to=to_email,
            template="password_reset",
            data={"token": reset_token},
        )
        return True
    return False


def send_invite_email(to_email: str, inviter_name: str, org_name: str, invite_url: str) -> bool:
    """Send team invitation email (placeholder)."""
    if not os.getenv("SMTP_HOST"):
        _log_email(
            to=to_email,
            template="team_invite",
            data={"inviter": inviter_name, "org": org_name, "url": invite_url},
        )
        return True
    return False


def _log_email(to: str, template: str, data: dict) -> None:
    """Append email record to log file."""
    try:
        entry = json.dumps(
            {
                "ts": datetime.now(timezone.utc).isoformat(),
                "to": to,
                "template": template,
                **data,
            }
        )
        with open(_LOG_FILE, "a") as f:
            f.write(entry + "\n")
    except OSError:
        pass  # Don't crash app if log file write fails

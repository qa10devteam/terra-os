"""Faza 81 — Onboarding email service (placeholder).

Logs emails to /tmp/terra_emails.log when SMTP is not configured.
Supports Resend API when RESEND_API_KEY is set.
Falls back to SMTP when SMTP_HOST is set.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone


_LOG_FILE = os.getenv("EMAIL_LOG_FILE", "/tmp/terra_emails.log")


def _send_via_resend(to_email: str, subject: str, html: str) -> bool:
    """Send email via Resend API. Returns True on success."""
    resend_key = os.getenv('RESEND_API_KEY')
    if resend_key:
        import httpx
        resp = httpx.post(
            'https://api.resend.com/emails',
            json={
                'from': os.getenv('EMAIL_FROM', 'noreply@terra-os.pl'),
                'to': [to_email],
                'subject': subject,
                'html': html,
            },
            headers={'Authorization': f'Bearer {resend_key}'},
        )
        return resp.status_code == 200
    return False


def send_welcome_email(to_email: str, user_name: str) -> bool:
    """Send welcome email to newly registered user.

    Falls back to file logging if neither RESEND_API_KEY nor SMTP_HOST is set.
    Returns True on success (including logged-only mode).
    """
    if not os.getenv("SMTP_HOST"):
        # Try Resend first
        resend_key = os.getenv('RESEND_API_KEY')
        if resend_key:
            import httpx
            subject = "Witamy w Terra.OS!"
            html = f"<h1>Cześć {user_name}!</h1><p>Witamy w Terra.OS. Twoje konto jest gotowe.</p>"
            resp = httpx.post(
                'https://api.resend.com/emails',
                json={
                    'from': os.getenv('EMAIL_FROM', 'noreply@terra-os.pl'),
                    'to': [to_email],
                    'subject': subject,
                    'html': html,
                },
                headers={'Authorization': f'Bearer {resend_key}'},
            )
            return resp.status_code == 200

        # Fallback: log to file
        _log_email(
            to=to_email,
            template="welcome",
            data={"name": user_name},
        )
        return True

    # TODO: integrate SMTP
    return False


def send_password_reset_email(to_email: str, reset_token: str) -> bool:
    """Send password reset email.

    Falls back to file logging if neither RESEND_API_KEY nor SMTP_HOST is set.
    """
    if not os.getenv("SMTP_HOST"):
        # Try Resend first
        resend_key = os.getenv('RESEND_API_KEY')
        if resend_key:
            import httpx
            reset_url = f"{os.getenv('APP_URL', 'https://app.terra-os.pl')}/reset-password?token={reset_token}"
            subject = "Reset hasła — Terra.OS"
            html = (
                f"<h1>Reset hasła</h1>"
                f"<p>Kliknij poniższy link, aby zresetować hasło:</p>"
                f"<a href=\"{reset_url}\">{reset_url}</a>"
                f"<p>Link wygasa za 1 godzinę.</p>"
            )
            resp = httpx.post(
                'https://api.resend.com/emails',
                json={
                    'from': os.getenv('EMAIL_FROM', 'noreply@terra-os.pl'),
                    'to': [to_email],
                    'subject': subject,
                    'html': html,
                },
                headers={'Authorization': f'Bearer {resend_key}'},
            )
            return resp.status_code == 200

        # Fallback: log to file
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
        # Try Resend first
        resend_key = os.getenv('RESEND_API_KEY')
        if resend_key:
            import httpx
            subject = f"Zaproszenie do {org_name} — Terra.OS"
            html = (
                f"<h1>Zaproszenie do zespołu</h1>"
                f"<p>{inviter_name} zaprasza Cię do organizacji {org_name}.</p>"
                f"<a href=\"{invite_url}\">Dołącz teraz</a>"
            )
            resp = httpx.post(
                'https://api.resend.com/emails',
                json={
                    'from': os.getenv('EMAIL_FROM', 'noreply@terra-os.pl'),
                    'to': [to_email],
                    'subject': subject,
                    'html': html,
                },
                headers={'Authorization': f'Bearer {resend_key}'},
            )
            return resp.status_code == 200

        # Fallback: log to file
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

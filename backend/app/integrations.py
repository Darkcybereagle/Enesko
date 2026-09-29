import smtplib
from email.message import EmailMessage

import httpx

from app.config import settings


class DeliveryResult:
    def __init__(self, *, configured: bool, status: str, provider: str, detail: str | None = None):
        self.configured = configured
        self.status = status
        self.provider = provider
        self.detail = detail


class WhatsAppAdapter:
    provider_name = "META_WHATSAPP_CLOUD"

    @property
    def configured(self) -> bool:
        return settings.whatsapp_configured

    def send_text(self, recipient: str, body: str) -> DeliveryResult:
        if not self.configured:
            return DeliveryResult(
                configured=False,
                status="NOT_CONFIGURED",
                provider="NOT_CONFIGURED",
                detail="WhatsApp credentials are not configured.",
            )

        url = (
            f"{settings.whatsapp_graph_url.rstrip('/')}/"
            f"{settings.whatsapp_api_version}/"
            f"{settings.whatsapp_phone_number_id}/messages"
        )
        payload = {
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "text",
            "text": {"body": body},
        }
        headers = {
            "Authorization": f"Bearer {settings.whatsapp_access_token}",
            "Content-Type": "application/json",
        }

        try:
            response = httpx.post(url, json=payload, headers=headers, timeout=12.0)
            response.raise_for_status()
            return DeliveryResult(
                configured=True,
                status="SENT",
                provider=self.provider_name,
            )
        except httpx.HTTPError as exc:
            return DeliveryResult(
                configured=True,
                status="FAILED",
                provider=self.provider_name,
                detail=str(exc),
            )


class EmailAdapter:
    provider_name = "SMTP"

    @property
    def configured(self) -> bool:
        return settings.email_configured

    def send(self, recipient: str, subject: str | None, body: str) -> DeliveryResult:
        if not self.configured:
            return DeliveryResult(
                configured=False,
                status="NOT_CONFIGURED",
                provider="NOT_CONFIGURED",
                detail="SMTP settings are not configured.",
            )

        message = EmailMessage()
        message["From"] = settings.smtp_from_email
        message["To"] = recipient
        message["Subject"] = subject or "ENESKO"
        message.set_content(body)

        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=12) as client:
                if settings.smtp_use_tls:
                    client.starttls()
                if settings.smtp_username:
                    client.login(settings.smtp_username, settings.smtp_password)
                client.send_message(message)
            return DeliveryResult(
                configured=True,
                status="SENT",
                provider=self.provider_name,
            )
        except (OSError, smtplib.SMTPException) as exc:
            return DeliveryResult(
                configured=True,
                status="FAILED",
                provider=self.provider_name,
                detail=str(exc),
            )


def _authorized_json_get(url: str, token: str) -> tuple[bool, dict | list | None, str | None]:
    if not url:
        return False, None, "Integration endpoint is not configured."

    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        response = httpx.get(url, headers=headers, timeout=15.0)
        response.raise_for_status()
        return True, response.json(), None
    except (httpx.HTTPError, ValueError) as exc:
        return True, None, str(exc)


class CinemaAdapter:
    provider_name = "AUTHORIZED_CINEMA_FEED"

    @property
    def configured(self) -> bool:
        return settings.cinema_feed_configured

    def fetch(self) -> tuple[bool, dict | list | None, str | None]:
        return _authorized_json_get(settings.cinema_feed_url, settings.cinema_feed_token)


class ParkingAdapter:
    provider_name = "AUTHORIZED_PARKING_FEED"

    @property
    def configured(self) -> bool:
        return settings.parking_feed_configured

    def fetch(self) -> tuple[bool, dict | list | None, str | None]:
        return _authorized_json_get(settings.parking_feed_url, settings.parking_feed_token)


whatsapp_adapter = WhatsAppAdapter()
email_adapter = EmailAdapter()
cinema_adapter = CinemaAdapter()
parking_adapter = ParkingAdapter()

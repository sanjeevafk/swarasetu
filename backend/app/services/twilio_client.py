"""Twilio client wrapper for WhatsApp and SMS dispatches."""

from __future__ import annotations

import logging
import base64
import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class TwilioClient:
    """Client for dispatching WhatsApp messages and SMS alerts via Twilio REST API."""

    def __init__(
        self,
        account_sid: str | None = None,
        auth_token: str | None = None,
        from_number: str | None = None,
    ):
        self.account_sid = account_sid or settings.twilio_account_sid
        self.auth_token = auth_token or settings.twilio_auth_token
        self.from_number = from_number or settings.twilio_phone_number

    @property
    def is_configured(self) -> bool:
        return bool(self.account_sid and self.auth_token)

    def _auth_header(self) -> dict[str, str]:
        if not self.is_configured:
            return {}
        credentials = f"{self.account_sid}:{self.auth_token}"
        encoded = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
        return {"Authorization": f"Basic {encoded}"}

    async def send_sms(self, to_number: str, body: str) -> dict[str, str]:
        """Dispatch a standard SMS notification (e.g. ASHA dispatch alert)."""
        if not self.is_configured:
            logger.info("[Mock SMS] To: %s | Message: %s", to_number, body)
            return {"status": "mock_sent", "sid": "SM_MOCK_12345"}

        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        headers = self._auth_header()
        data = {
            "From": self.from_number,
            "To": to_number,
            "Body": body,
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(url, headers=headers, data=data)
                res.raise_for_status()
                payload = res.json()
                return {"status": payload.get("status", "sent"), "sid": payload.get("sid", "")}
        except Exception as e:
            logger.error("Twilio SMS dispatch failed: %s", e)
            return {"status": "failed", "error": str(e)}

    async def send_whatsapp_message(
        self,
        to_number: str,
        body: str,
        media_url: str | None = None,
    ) -> dict[str, str]:
        """Send a WhatsApp message response to a patient."""
        # Ensure 'whatsapp:' prefix
        to_whatsapp = to_number if to_number.startswith("whatsapp:") else f"whatsapp:{to_number}"
        from_whatsapp = f"whatsapp:{self.from_number}"

        if not self.is_configured:
            logger.info("[Mock WhatsApp] To: %s | Message: %s", to_whatsapp, body)
            return {"status": "mock_sent", "sid": "WA_MOCK_12345"}

        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        headers = self._auth_header()
        data = {
            "From": from_whatsapp,
            "To": to_whatsapp,
            "Body": body,
        }
        if media_url:
            data["MediaUrl"] = media_url

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(url, headers=headers, data=data)
                res.raise_for_status()
                payload = res.json()
                return {"status": payload.get("status", "sent"), "sid": payload.get("sid", "")}
        except Exception as e:
            logger.error("Twilio WhatsApp dispatch failed: %s", e)
            return {"status": "failed", "error": str(e)}


twilio_client = TwilioClient()

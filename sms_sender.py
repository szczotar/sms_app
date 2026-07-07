import time
from dataclasses import dataclass
from typing import Protocol

import requests


@dataclass
class SendResult:
    success: bool
    error: str | None = None


class SmsSender(Protocol):
    def send(self, phone: str, text: str) -> SendResult:
        ...


class MockSmsSender:
    """Dry-run sender used until real api-sms.pl credentials are configured."""

    def send(self, phone: str, text: str) -> SendResult:
        print(f"[MOCK] wyslalbym SMS do {phone}: {text}")
        return SendResult(success=True)


def _to_international(phone: str) -> str:
    """HostedSMS requires numbers as 48xxxxxxxxx; our parsed phones are bare 9-digit."""
    digits = phone.replace(" ", "").replace("-", "").lstrip("+")
    if digits.startswith("48") and len(digits) == 11:
        return digits
    return "48" + digits


class HostedSmsSender:
    """Real HostedSMS.pl (DCS) integration, using the SimpleApi interface.

    Auth is UserEmail/Password (no separate API key). See
    HostedSms-Opis_Techniczny_API_pl.pdf, section "Interfejs SimpleApi".
    """

    ENDPOINT = "https://api.hostedsms.pl/SimpleApi"

    def __init__(self, email: str, password: str, sender: str = ""):
        self._email = email
        self._password = password
        self._sender = sender

    def send(self, phone: str, text: str) -> SendResult:
        try:
            response = requests.post(
                self.ENDPOINT,
                data={
                    "UserEmail": self._email,
                    "Password": self._password,
                    "Sender": self._sender,
                    "Phone": _to_international(phone),
                    "Message": text,
                },
                headers={"Accept": "application/json"},
                timeout=10,
            )
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            return SendResult(success=False, error=str(exc))
        except ValueError as exc:
            return SendResult(success=False, error=f"Nieprawidlowa odpowiedz serwera: {exc}")

        error_message = payload.get("ErrorMessage")
        if error_message:
            return SendResult(success=False, error=error_message)
        return SendResult(success=True)


def send_with_retry(
    sender: SmsSender, phone: str, text: str, retries: int = 2, delay_seconds: float = 1.0
) -> SendResult:
    result = SendResult(success=False, error="brak prob wysylki")
    for attempt in range(retries + 1):
        result = sender.send(phone, text)
        if result.success:
            return result
        if attempt < retries:
            time.sleep(delay_seconds)
    return result

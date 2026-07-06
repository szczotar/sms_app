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


class ApiSmsPlSender:
    """Real api-sms.pl integration.

    NOTE: endpoint/params below are best-effort placeholders based on typical
    Polish SMS gateway conventions -- confirm against api-sms.pl's actual API
    docs once an account/API key is available, before relying on this in
    production.
    """

    ENDPOINT = "https://api-sms.pl/api/send"

    def __init__(self, api_key: str, sender_name: str = ""):
        self._api_key = api_key
        self._sender_name = sender_name

    def send(self, phone: str, text: str) -> SendResult:
        try:
            response = requests.post(
                self.ENDPOINT,
                data={
                    "key": self._api_key,
                    "to": phone,
                    "message": text,
                    "sender": self._sender_name,
                },
                timeout=10,
            )
            response.raise_for_status()
            return SendResult(success=True)
        except requests.RequestException as exc:
            return SendResult(success=False, error=str(exc))


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

from datetime import date
from typing import Callable, Literal

from models import Visit

ReminderType = Literal["5-day", "2-day"]

_DAYS_TO_REMINDER: dict[int, ReminderType] = {5: "5-day", 2: "2-day"}

# Overridable seam so tests can pin "today" instead of depending on wall-clock.
today_provider: Callable[[], date] = date.today

_MONTHS_PL = {
    1: "stycznia", 2: "lutego", 3: "marca", 4: "kwietnia", 5: "maja", 6: "czerwca",
    7: "lipca", 8: "sierpnia", 9: "września", 10: "października", 11: "listopada", 12: "grudnia",
}


def reminder_type(appointment_date: date, today: date | None = None) -> ReminderType | None:
    if today is None:
        today = today_provider()
    days_until = (appointment_date - today).days
    return _DAYS_TO_REMINDER.get(days_until)


def format_date_pl(d: date) -> str:
    return f"{d.day} {_MONTHS_PL[d.month]} {d.year}"


class _SafeDict(dict):
    def __missing__(self, key):
        return "{" + key + "}"


def build_message(visit: Visit, template: str, clinic_info: dict) -> str:
    values = {
        "imie_nazwisko": visit.patient_name,
        "data": format_date_pl(visit.appointment_date),
        "godzina": visit.appointment_time.strftime("%H:%M"),
        "lekarz": visit.doctor,
        **clinic_info,
    }
    return template.format_map(_SafeDict(values))

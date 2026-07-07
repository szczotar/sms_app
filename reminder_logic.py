from datetime import date

from models import Visit

_MONTHS_PL = {
    1: "stycznia", 2: "lutego", 3: "marca", 4: "kwietnia", 5: "maja", 6: "czerwca",
    7: "lipca", 8: "sierpnia", 9: "września", 10: "października", 11: "listopada", 12: "grudnia",
}


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

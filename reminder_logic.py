from datetime import date

from models import Visit
from text_utils import strip_diacritics

_MONTHS_PL = {
    1: "stycznia", 2: "lutego", 3: "marca", 4: "kwietnia", 5: "maja", 6: "czerwca",
    7: "lipca", 8: "sierpnia", 9: "wrzesnia", 10: "pazdziernika", 11: "listopada", 12: "grudnia",
}


def format_date_pl(d: date) -> str:
    return f"{d.day} {_MONTHS_PL[d.month]} {d.year}"


class _SafeDict(dict):
    def __missing__(self, key):
        return "{" + key + "}"


def build_koszt_info(price: float | None) -> str:
    if price is None:
        return ""
    if price == int(price):
        amount = str(int(price))
    else:
        amount = f"{price:.2f}".replace(".", ",")
    return f" Koszt wizyty: {amount} zl."


def build_message(visit: Visit, template: str, clinic_info: dict, rodzaj_wizyty: str = "wizycie") -> str:
    values = {
        "imie_nazwisko": visit.patient_name,
        "data": format_date_pl(visit.appointment_date),
        "godzina": visit.appointment_time.strftime("%H:%M"),
        "lekarz": visit.doctor,
        "rodzaj_wizyty": rodzaj_wizyty,
        "koszt_info": build_koszt_info(visit.price),
        **clinic_info,
    }
    message = template.format_map(_SafeDict(values))
    return strip_diacritics(message)

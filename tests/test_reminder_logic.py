from datetime import date, time

from models import Visit
from reminder_logic import build_message, reminder_type


def test_reminder_type_five_days_out():
    assert reminder_type(date(2026, 7, 11), today=date(2026, 7, 6)) == "5-day"


def test_reminder_type_two_days_out():
    assert reminder_type(date(2026, 7, 8), today=date(2026, 7, 6)) == "2-day"


def test_reminder_type_other_offsets_are_none():
    assert reminder_type(date(2026, 7, 7), today=date(2026, 7, 6)) is None
    assert reminder_type(date(2026, 7, 6), today=date(2026, 7, 6)) is None
    assert reminder_type(date(2026, 6, 1), today=date(2026, 7, 6)) is None


def _sample_visit() -> Visit:
    return Visit(
        doctor="Pycio Katarzyna",
        appointment_date=date(2026, 7, 11),
        appointment_time=time(14, 30),
        patient_name="Kowalska Anna",
        pesel="11322302640",
        phone="601234567",
        status="Do realizacji",
    )


def test_build_message_fills_all_placeholders():
    template = (
        "{imie_nazwisko}, wizyta {data} {godzina} u {lekarz} w {clinic_name}, "
        "tel. {clinic_phone}"
    )
    clinic_info = {"clinic_name": "Psyche", "clinic_phone": "123456789"}

    message = build_message(_sample_visit(), template, clinic_info)

    assert "Kowalska Anna" in message
    assert "11 lipca 2026" in message
    assert "14:30" in message
    assert "Pycio Katarzyna" in message
    assert "Psyche" in message
    assert "123456789" in message


def test_build_message_leaves_unknown_placeholder_untouched():
    message = build_message(_sample_visit(), "{nieznane_pole}", {})
    assert message == "{nieznane_pole}"

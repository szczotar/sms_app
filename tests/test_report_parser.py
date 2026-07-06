from datetime import date, time
from pathlib import Path

from report_parser import load_report

RAPORTY_DIR = Path(__file__).parent.parent / "raporty"


def test_xls_sample_parses_expected_count_and_first_row():
    visits = load_report(RAPORTY_DIR / "raport1.xls")
    assert len(visits) == 48

    first = visits[0]
    assert first.doctor == "Baczyńska Sylwia"
    assert first.appointment_date == date(2026, 7, 3)
    assert first.appointment_time == time(14, 0)
    assert first.patient_name == "Godlewska Zofia"
    assert first.pesel == "11322302640"
    assert first.status == "Do realizacji"


def test_csv_sample_parses_expected_count_and_dates():
    visits = load_report(RAPORTY_DIR / "raport2.csv")
    assert len(visits) == 216

    dates = {v.appointment_date for v in visits}
    assert dates == {
        date(2026, 7, 3),
        date(2026, 7, 6),
        date(2026, 7, 7),
        date(2026, 7, 8),
    }


def test_csv_sample_all_pesels_are_eleven_digits_except_blocked_slots():
    visits = load_report(RAPORTY_DIR / "raport2.csv")
    for visit in visits:
        if visit.patient_name == "[ blokada wpisu ]":
            assert visit.pesel == ""
        else:
            assert len(visit.pesel) == 11
            assert visit.pesel.isdigit()

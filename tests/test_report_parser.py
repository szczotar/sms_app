from datetime import date, time
from pathlib import Path

from report_parser import load_report

RAPORTY_DIR = Path(__file__).parent.parent / "raporty"


def test_csv_sample_skips_blocked_slot_rows():
    visits = load_report(RAPORTY_DIR / "raport_uwagi.csv")
    assert all(v.patient_name != "[ blokada wpisu ]" for v in visits)


def test_foreign_phone_number_is_not_read_as_price(tmp_path):
    content = (
        "1 sierpnia 2026;Doktor Testowy\n"
        ";;;;;;;\n"
        "12345678901\n"
        "1;1;10:00;Jan Kowalski\n"
        "+41793038058\n"
        "150\n"
    )
    csv_path = tmp_path / "raport.csv"
    csv_path.write_bytes(content.encode("utf-8-sig"))

    visits = load_report(csv_path)

    assert len(visits) == 1
    visit = visits[0]
    assert visit.phones == []
    assert visit.price == 150.0


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


def test_split_module_rows_merge_into_one_visit(tmp_path):
    # A single visit booked across multiple modules is printed as several
    # rows for the same patient/day/doctor, but real Axon exports show every
    # module row carrying the exact same Godz (start time) - these must
    # collapse into a single Visit so only one SMS is sent and zestawienie
    # doesn't count the price more than once.
    content = (
        "1 sierpnia 2026;Doktor Testowy\n"
        ";;;;;;;\n"
        "12345678901\n"
        "1;1;10:00;Jan Kowalski\n"
        "600111222\n"
        "\n"
        "12345678901\n"
        "2;1;10:00;Jan Kowalski\n"
        "150\n"
    )
    csv_path = tmp_path / "raport.csv"
    csv_path.write_bytes(content.encode("utf-8-sig"))

    visits = load_report(csv_path)

    assert len(visits) == 1
    visit = visits[0]
    assert visit.appointment_time == time(10, 0)
    assert visit.phones == ["600111222"]
    assert visit.price == 150.0


def test_same_patient_different_time_same_day_stays_separate(tmp_path):
    # A patient booked for two consecutive full appointments (e.g. two
    # back-to-back 1-hour slots with the same doctor) must NOT be merged
    # just because the patient/day/doctor match - each is a separate,
    # separately-priced visit. Regression test for a real bug: the old
    # merge key (patient+date+doctor only, no time) collapsed these into
    # one visit, dropping one visit's price and status from zestawienie.
    content = (
        "1 sierpnia 2026;Doktor Testowy\n"
        ";;;;;;;\n"
        "12345678901\n"
        "1;1;14:00;Jan Kowalski\n"
        "600111222\n"
        "200;Nie zrealizowane\n"
        "12345678901\n"
        "2;2;15:00;Jan Kowalski\n"
        "600111222\n"
        "200;Nie zrealizowane\n"
    )
    csv_path = tmp_path / "raport.csv"
    csv_path.write_bytes(content.encode("utf-8-sig"))

    visits = load_report(csv_path)

    assert len(visits) == 2
    assert {v.appointment_time for v in visits} == {time(14, 0), time(15, 0)}
    assert all(v.price == 200.0 for v in visits)
    assert all(v.status == "Nie zrealizowane" for v in visits)


def test_same_patient_different_doctor_same_day_stays_separate(tmp_path):
    # A real second appointment with a different doctor the same day must
    # NOT be merged away - that would drop its revenue from zestawienie.
    content = (
        "1 sierpnia 2026;Doktor Pierwszy\n"
        ";;;;;;;\n"
        "12345678901\n"
        "1;1;10:00;Jan Kowalski\n"
        "600111222\n"
        "100\n"
        "\n"
        "1 sierpnia 2026;Doktor Drugi\n"
        ";;;;;;;\n"
        "12345678901\n"
        "1;1;14:00;Jan Kowalski\n"
        "600111222\n"
        "200\n"
    )
    csv_path = tmp_path / "raport.csv"
    csv_path.write_bytes(content.encode("utf-8-sig"))

    visits = load_report(csv_path)

    assert len(visits) == 2
    assert {v.doctor for v in visits} == {"Doktor Pierwszy", "Doktor Drugi"}
    assert {v.price for v in visits} == {100.0, 200.0}


def test_csv_sample_all_pesels_are_eleven_digits_except_blocked_slots():
    visits = load_report(RAPORTY_DIR / "raport2.csv")
    for visit in visits:
        if visit.patient_name == "[ blokada wpisu ]":
            assert visit.pesel == ""
        else:
            assert len(visit.pesel) == 11
            assert visit.pesel.isdigit()


def test_status_extracted_alongside_price_in_same_row(tmp_path):
    # zestawienie template: Uwagi and Status can be two cells of one row.
    content = (
        "1 sierpnia 2026;Doktor Testowy\n"
        ";;;;;;;\n"
        "12345678901\n"
        "1;1;10:00;Jan Kowalski\n"
        "600111222\n"
        "800;Wykonane\n"
    )
    csv_path = tmp_path / "raport.csv"
    csv_path.write_bytes(content.encode("utf-8-sig"))

    visits = load_report(csv_path)

    assert len(visits) == 1
    visit = visits[0]
    assert visit.price == 800.0
    assert visit.status == "Wykonane"
    assert visit.price_note is None


def test_status_only_row_without_uwagi(tmp_path):
    content = (
        "1 sierpnia 2026;Doktor Testowy\n"
        ";;;;;;;\n"
        "12345678901\n"
        "1;1;10:00;Jan Kowalski\n"
        "600111222\n"
        "Nie zrealizowane\n"
    )
    csv_path = tmp_path / "raport.csv"
    csv_path.write_bytes(content.encode("utf-8-sig"))

    visits = load_report(csv_path)

    assert len(visits) == 1
    visit = visits[0]
    assert visit.price is None
    assert visit.status == "Nie zrealizowane"


def test_merge_priority_wykonane_beats_other_statuses(tmp_path):
    # Real data: only one module row is ever "Wykonane" - it must win over
    # "Nie zrealizowane"/"Rezygnacja z wykonania" on the other module rows,
    # regardless of row order. Module rows disagreeing on status is routine,
    # not an error, so it resolves silently (no log call).
    content = (
        "1 sierpnia 2026;Doktor Testowy\n"
        ";;;;;;;\n"
        "12345678901\n"
        "1;1;10:00;Jan Kowalski\n"
        "600111222\n"
        "Nie zrealizowane\n"
        "12345678901\n"
        "2;1;10:00;Jan Kowalski\n"
        "150;Wykonane\n"
        "12345678901\n"
        "3;1;10:00;Jan Kowalski\n"
        "Rezygnacja z wykonania\n"
    )
    csv_path = tmp_path / "raport.csv"
    csv_path.write_bytes(content.encode("utf-8-sig"))

    visits = load_report(csv_path)

    assert len(visits) == 1
    visit = visits[0]
    assert visit.status == "Wykonane"
    assert visit.price == 150.0


def test_merge_priority_nie_zrealizowane_beats_rezygnacja(tmp_path):
    # With no "Wykonane" present, a recorded "Nie zrealizowane" on any module
    # row means the visit still counts - it must win over "Rezygnacja z
    # wykonania" on another module row, not the other way round, otherwise
    # the visit would be silently dropped from the zestawienie export.
    content = (
        "1 sierpnia 2026;Doktor Testowy\n"
        ";;;;;;;\n"
        "12345678901\n"
        "1;1;10:00;Jan Kowalski\n"
        "600111222\n"
        "Nie zrealizowane\n"
        "12345678901\n"
        "2;1;10:00;Jan Kowalski\n"
        "Rezygnacja z wykonania\n"
    )
    csv_path = tmp_path / "raport.csv"
    csv_path.write_bytes(content.encode("utf-8-sig"))

    visits = load_report(csv_path)

    assert len(visits) == 1
    assert visits[0].status == "Nie zrealizowane"


def test_section_title_line_not_treated_as_uwagi(tmp_path):
    # "PACJENCI ..." repeats as a running page header in the zestawienie
    # template and must be skipped like "Strona N", not read as Uwagi text.
    content = (
        "1 sierpnia 2026;Doktor Testowy\n"
        ";;;;;;;\n"
        "12345678901\n"
        "1;1;10:00;Jan Kowalski\n"
        "600111222\n"
        "PACJENCI LEKARZY / PIELEGNIAREK\n"
        "150;Wykonane\n"
    )
    csv_path = tmp_path / "raport.csv"
    csv_path.write_bytes(content.encode("utf-8-sig"))

    visits = load_report(csv_path)

    assert len(visits) == 1
    visit = visits[0]
    assert visit.price == 150.0
    assert visit.status == "Wykonane"
    assert visit.price_note is None

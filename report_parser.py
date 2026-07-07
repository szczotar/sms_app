"""Parser for the clinic's schedule export (xlsx/xls/csv).

The export is not a clean table: it's a "printed schedule" layout with merged
cells, page-break artifacts ("Strona N"), and data laid out as repeating
blocks per doctor/date section:

    <doctor name> ... <date>          <- header row for a new section
    Lp | Nr | Godz | Nazwisko i imię pacjenta   <- column header row
                                       PESEL      <- column header row
    1 | 1 | 14:00 | Godlewska Zofia | Do realizacji   <- patient row
                                       11322302640    <- PESEL (+ phone) row

Column positions shift between xls/xlsx/csv exports of the same data (cell
merging differs per format), so rows are classified by matching value
*patterns* (an HH:MM time, an 11-digit PESEL, a "DD <month> YYYY" date)
rather than by fixed column index.

NOTE: the real production export will include a phone number column that
isn't present in the current sample files. The phone-detection pattern
below is a best guess (9 Polish digits, optionally "+48"-prefixed) and
should be revisited once a real sample with that column is available.
"""

import csv
import re
from datetime import date, time
from pathlib import Path

import pandas as pd

from models import Visit

_MONTHS = {
    "styczeń": 1, "stycznia": 1,
    "luty": 2, "lutego": 2,
    "marzec": 3, "marca": 3,
    "kwiecień": 4, "kwietnia": 4,
    "maj": 5, "maja": 5,
    "czerwiec": 6, "czerwca": 6,
    "lipiec": 7, "lipca": 7,
    "sierpień": 8, "sierpnia": 8,
    "wrzesień": 9, "września": 9,
    "październik": 10, "października": 10,
    "listopad": 11, "listopada": 11,
    "grudzień": 12, "grudnia": 12,
}

_DATE_RE = re.compile(r"(\d{1,2})\s+(" + "|".join(_MONTHS) + r")\s+(\d{4})", re.IGNORECASE)
_TIME_RE = re.compile(r"^(\d{1,2}):(\d{2})(?::\d{2})?$")
_PESEL_RE = re.compile(r"^\d{11}$")
_PHONE_RE = re.compile(r"^(?:\+?48)?(\d{9})$")
_HEADER_KEYWORDS = {"lp", "nr", "godz", "pesel"}

# how many rows after a patient row to keep looking for its PESEL/phone
_PESEL_LOOKAHEAD_ROWS = 3


def _clean_row(row) -> list[str | None]:
    cleaned = []
    for cell in row:
        if pd.isna(cell):
            cleaned.append(None)
        else:
            text = str(cell).strip()
            cleaned.append(text if text else None)
    return cleaned


def _read_grid(path: Path) -> list[list[str | None]]:
    suffix = path.suffix.lower()
    if suffix == ".xlsx":
        df = pd.read_excel(path, engine="openpyxl", header=None, dtype=str)
        return [_clean_row(row) for row in df.itertuples(index=False, name=None)]
    if suffix == ".xls":
        df = pd.read_excel(path, engine="xlrd", header=None, dtype=str)
        return [_clean_row(row) for row in df.itertuples(index=False, name=None)]
    if suffix == ".csv":
        # Rows have inconsistent field counts (merged-cell export artifact),
        # which pandas' C parser rejects; the stdlib csv module tolerates it.
        # The clinic's export is cp1250, but try utf-8 first (strict) in case
        # the file was re-saved as utf-8 - cp1250 almost never raises on
        # random bytes, so decoding a utf-8 file as cp1250 would silently
        # mangle every accented character instead of failing loudly.
        raw = path.read_bytes()
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = raw.decode("cp1250")
        rows = list(csv.reader(text.splitlines(), delimiter=";"))
        return [_clean_row(row) for row in rows]
    raise ValueError(f"Nieobsługiwany format pliku: {suffix}")


def _find_date(row: list[str | None]) -> tuple[date, str] | None:
    for cell in row:
        if not cell:
            continue
        m = _DATE_RE.search(cell)
        if m:
            day, month_name, year = m.groups()
            return date(int(year), _MONTHS[month_name.lower()], int(day)), cell
    return None


def _find_doctor(row: list[str | None], date_cell: str) -> str | None:
    for cell in row:
        if cell and cell != date_cell:
            return cell
    return None


def _is_header_row(row: list[str | None]) -> bool:
    lowered = {c.lower() for c in row if c}
    if lowered & _HEADER_KEYWORDS:
        return True
    return any("strona" in c.lower() for c in row if c)


def _classify_patient_row(row: list[str | None]) -> tuple[time, str, str] | None:
    """Return (time, name, status) if this row starts a new patient entry."""
    time_val = None
    alpha_cells = []
    for cell in row:
        if not cell:
            continue
        m = _TIME_RE.match(cell)
        if m:
            time_val = time(int(m.group(1)), int(m.group(2)))
            continue
        if cell.replace(".", "", 1).isdigit():
            continue  # Lp / Nr counters
        alpha_cells.append(cell)
    if time_val is None or not alpha_cells:
        return None
    name = alpha_cells[0]
    status = alpha_cells[-1] if len(alpha_cells) > 1 else ""
    return time_val, name, status


def _extract_pesel_phone(row: list[str | None]) -> tuple[str | None, str | None]:
    pesel = None
    phone = None
    for cell in row:
        if not cell:
            continue
        digits = cell.replace(" ", "").replace("-", "")
        if pesel is None and _PESEL_RE.match(digits):
            pesel = digits
            continue
        m = _PHONE_RE.match(digits)
        if m:
            phone = m.group(1)
    return pesel, phone


def load_report(path: Path | str) -> list[Visit]:
    grid = _read_grid(Path(path))
    visits: list[Visit] = []

    current_doctor: str | None = None
    current_date: date | None = None
    pending: dict | None = None
    rows_since_pending = 0

    def flush_pending():
        nonlocal pending
        if pending is not None:
            visits.append(Visit(
                doctor=current_doctor or "",
                appointment_date=current_date,
                appointment_time=pending["time"],
                patient_name=pending["name"],
                pesel=pending["pesel"] or "",
                phone=pending["phone"],
                status=pending["status"],
            ))
            pending = None

    for row in grid:
        if all(c is None for c in row):
            flush_pending()
            continue

        found = _find_date(row)
        if found is not None:
            flush_pending()
            current_date, date_cell = found
            current_doctor = _find_doctor(row, date_cell) or current_doctor
            continue

        if _is_header_row(row):
            continue

        patient = _classify_patient_row(row)
        if patient is not None:
            flush_pending()
            time_val, name, status = patient
            pending = {"time": time_val, "name": name, "status": status, "pesel": None, "phone": None}
            rows_since_pending = 0
            continue

        if pending is not None and rows_since_pending < _PESEL_LOOKAHEAD_ROWS:
            pesel, phone = _extract_pesel_phone(row)
            if pesel:
                pending["pesel"] = pesel
            if phone:
                pending["phone"] = phone
            rows_since_pending += 1

    flush_pending()
    return visits

"""Parser for the clinic's schedule export (xlsx/xls/csv).

The export is not a clean table: it's a "printed schedule" layout with merged
cells, page-break artifacts ("Strona N"), and data laid out as repeating
blocks per doctor/date section:

    <doctor name> ... <date>          <- header row for a new section
    Lp | Nr | Godz | Nazwisko i imię pacjenta   <- column header row
                                       Telefon    <- column header row
    <PESEL>                                       <- PESEL row (precedes patient)
    1 | 1 | 14:00 | Godlewska Zofia | Do realizacji   <- patient row
                                       <phone(s)>      <- phone row (comma-separated if several)
                                       <Uwagi>          <- optional price or note row (e.g. "100", "nb-nieobecnosc")

Column positions shift between xls/xlsx/csv exports of the same data (cell
merging differs per format), so rows are classified by matching value
*patterns* (an HH:MM time, an 11-digit PESEL, a "DD <month> YYYY" date, a
9-digit phone) rather than by fixed column index.

There is no per-row status column in this export format: "Do realizacji"
appears once, as a report-level label, not per visit. Callers should assume
the report was already filtered upstream to the visits that matter.
"""

import csv
import re
from datetime import date, time
from pathlib import Path

import pandas as pd

from models import Visit
from text_utils import normalize_name

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
# Broader than _PHONE_RE: matches any digit string that *looks* like a phone
# number (e.g. a foreign number such as "+41793038058") even if it isn't a
# valid Polish one. Content matching this must never fall through to price
# extraction - amounts only ever come from the Uwagi row.
_PHONE_LOOKS_LIKE_RE = re.compile(r"^\+?\d{7,15}$")
_PRICE_NUM_RE = re.compile(r"(\d+(?:[.,]\d{1,2})?)")
_HEADER_KEYWORDS = {"lp", "nr", "godz", "pesel", "telefon", "uwagi"}
_BLOCKED_SLOT_RE = re.compile(r"^\[?\s*blokada\s+wpisu\s*\]?$", re.IGNORECASE)

# how many content rows after a patient row to keep looking for phone/price
_LOOKAHEAD_ROWS = 3


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


def _classify_patient_row(row: list[str | None]) -> tuple[time, str] | None:
    """Return (time, name) if this row starts a new patient entry."""
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
    return time_val, alpha_cells[0]


def _row_content(row: list[str | None]) -> str | None:
    for cell in row:
        if cell:
            return cell
    return None


def _split_phones(content: str) -> list[str] | None:
    phones = []
    for part in content.split(","):
        digits = part.strip().replace(" ", "").replace("-", "")
        m = _PHONE_RE.match(digits)
        if not m:
            return None
        phones.append(m.group(1))
    return phones or None


def _extract_price(content: str) -> tuple[float | None, str]:
    m = _PRICE_NUM_RE.search(content)
    if m:
        return float(m.group(1).replace(",", ".")), content
    return None, content


def _looks_like_phone(content: str) -> bool:
    for part in content.split(","):
        digits = part.strip().replace(" ", "").replace("-", "")
        if not _PHONE_LOOKS_LIKE_RE.match(digits):
            return False
    return True


def _is_blocked_slot(name: str) -> bool:
    return bool(_BLOCKED_SLOT_RE.match(name.strip()))


def _merge_split_visits(visits: list[Visit]) -> list[Visit]:
    """Some doctors' calendars use 15-minute slots, so one longer visit (e.g.
    45 minutes) is printed as several consecutive rows for the same patient.
    Collapse rows that share the same patient, date and doctor into a single
    Visit, so reminders aren't sent more than once and zestawienie doesn't
    count the same visit's revenue more than once.

    The price can appear on every module row or on only one of them, so
    every row in the group is checked - but once a price is found it's kept
    as-is, never summed across rows (it's one visit's price, not one per
    module).
    """
    merged: dict[tuple[str, date, str], Visit] = {}
    for visit in visits:
        key = (normalize_name(visit.patient_name), visit.appointment_date, normalize_name(visit.doctor))
        existing = merged.get(key)
        if existing is None:
            merged[key] = Visit(
                doctor=visit.doctor,
                appointment_date=visit.appointment_date,
                appointment_time=visit.appointment_time,
                patient_name=visit.patient_name,
                pesel=visit.pesel,
                phones=list(visit.phones),
                price=visit.price,
                price_note=visit.price_note,
            )
            continue
        if visit.appointment_time < existing.appointment_time:
            existing.appointment_time = visit.appointment_time
        if not existing.pesel and visit.pesel:
            existing.pesel = visit.pesel
        for phone in visit.phones:
            if phone not in existing.phones:
                existing.phones.append(phone)
        if existing.price is None and visit.price is not None:
            existing.price = visit.price
        if not existing.price_note and visit.price_note:
            existing.price_note = visit.price_note
    return list(merged.values())


def load_report(path: Path | str) -> list[Visit]:
    grid = _read_grid(Path(path))
    visits: list[Visit] = []

    current_doctor: str | None = None
    current_date: date | None = None
    pending: dict | None = None
    pending_pesel: str | None = None
    rows_since_pending = 0

    def flush_pending():
        nonlocal pending
        if pending is not None and _is_blocked_slot(pending["name"]):
            pending = None
            return
        if pending is not None:
            visits.append(Visit(
                doctor=current_doctor or "",
                appointment_date=current_date,
                appointment_time=pending["time"],
                patient_name=pending["name"],
                pesel=pending["pesel"] or "",
                phones=pending["phones"],
                price=pending["price"],
                price_note=pending["price_note"],
            ))
            pending = None

    for row in grid:
        content = _row_content(row)
        if content is None:
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
            time_val, name = patient
            pending = {
                "time": time_val, "name": name, "pesel": pending_pesel,
                "phones": [], "price": None, "price_note": None,
            }
            pending_pesel = None
            rows_since_pending = 0
            continue

        digits = content.replace(" ", "").replace("-", "")
        if pending is None:
            if _PESEL_RE.match(digits):
                pending_pesel = digits
            continue

        if rows_since_pending >= _LOOKAHEAD_ROWS:
            continue
        rows_since_pending += 1

        if not pending["phones"]:
            phones = _split_phones(content)
            if phones is not None:
                pending["phones"] = phones
                continue

        if _looks_like_phone(content):
            # Doesn't match the strict Polish phone pattern (e.g. a foreign
            # number), but is clearly phone-shaped - never misread as a price.
            continue

        price, note = _extract_price(content)
        if price is not None:
            pending["price"] = price
        elif note.strip():
            pending["price_note"] = note.strip()

    flush_pending()
    return _merge_split_visits(visits)

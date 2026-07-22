"""Per-doctor revenue/billing summary ("zestawienie"), exported as .xlsx.

Input is the same schedule-export format as the daily reminder report, but
typically spanning a week or month. No-show/cancelled visits (an Uwagi cell
with a code but no extractable price) are listed with a note but excluded
from the doctor's total.
"""

import re
from pathlib import Path

import openpyxl

import report_parser

_ILLEGAL_SHEET_CHARS = re.compile(r"[\[\]:*?/\\]")


def _safe_sheet_name(name: str, used: set[str]) -> str:
    cleaned = _ILLEGAL_SHEET_CHARS.sub("", name).strip() or "Nieznany"
    cleaned = cleaned[:31]
    candidate = cleaned
    n = 2
    while candidate in used:
        suffix = f" ({n})"
        candidate = cleaned[: 31 - len(suffix)] + suffix
        n += 1
    used.add(candidate)
    return candidate


def generate(input_path: Path | str, output_path: Path | str) -> None:
    visits = report_parser.load_report(input_path)

    by_doctor: dict[str, list] = {}
    for visit in visits:
        by_doctor.setdefault(visit.doctor or "Nieznany", []).append(visit)

    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    summary_ws = wb.create_sheet(title="Podsumowanie")
    summary_ws.append(["Lekarz", "Suma (zl)"])

    used_names: set[str] = {"Podsumowanie"}
    grand_total = 0.0

    for doctor in sorted(by_doctor):
        doctor_visits = sorted(by_doctor[doctor], key=lambda v: (v.appointment_date, v.appointment_time))
        ws = wb.create_sheet(title=_safe_sheet_name(doctor, used_names))
        ws.append(["Data", "Godzina", "Pacjent", "Cena (zl)", "Uwagi"])

        total = 0.0
        for visit in doctor_visits:
            ws.append([
                visit.appointment_date.strftime("%d.%m.%Y"),
                visit.appointment_time.strftime("%H:%M"),
                visit.patient_name,
                visit.price if visit.price is not None else None,
                visit.price_note or "",
            ])
            if visit.price is not None:
                total += visit.price

        ws.append(["", "", "Suma:", total, ""])
        summary_ws.append([doctor, total])
        grand_total += total

    summary_ws.append(["Razem", grand_total])
    wb.move_sheet("Podsumowanie", offset=-len(wb.sheetnames))
    wb.save(output_path)

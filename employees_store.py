import json
from pathlib import Path

from config import APP_DIR, DATA_DIR
from text_utils import normalize_name

_DEFAULT_PATH = DATA_DIR / "employees.json"
_PRACOWNICY_XLSX = APP_DIR / "Pracownicy.xlsx"

PSYCHIATRA = "Psychiatra"


def _import_from_xlsx(path: Path) -> list[dict]:
    import pandas as pd

    df = pd.read_excel(path, header=0, dtype=str)
    employees = []
    for _, row in df.iterrows():
        specjalizacja = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""
        nazwisko = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ""
        if nazwisko:
            employees.append({"name": nazwisko, "specialization": specjalizacja})
    return employees


def load(path: Path = _DEFAULT_PATH) -> list[dict]:
    if not path.exists():
        employees = _import_from_xlsx(_PRACOWNICY_XLSX) if _PRACOWNICY_XLSX.exists() else []
        save(employees, path)
        return employees
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save(employees: list[dict], path: Path = _DEFAULT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(employees, f, ensure_ascii=False, indent=2)


def resolve_rodzaj_wizyty(doctor: str, employees: list[dict]) -> str:
    """Locative-case phrase for the {rodzaj_wizyty} template placeholder."""
    target = normalize_name(doctor)
    for emp in employees:
        if normalize_name(emp["name"]) == target:
            if emp["specialization"].strip().lower() == PSYCHIATRA.lower():
                return "konsultacji lekarskiej"
            return "sesji"
    return "wizycie"

import json
from pathlib import Path

from config import DATA_DIR

_DEFAULT_PATH = DATA_DIR / "templates.json"

_DEFAULTS = {
    "template_5day": (
        "Przypominamy o {rodzaj_wizyty} {imie_nazwisko} w dniu {data} o godz. {godzina} "
        "u {lekarz} w {clinic_name}.{koszt_info} Aby odwołać wizytę, zadzwoń: {clinic_phone}."
    ),
    "template_2day": (
        "Przypominamy o {rodzaj_wizyty} {imie_nazwisko} już za 2 dni, {data} o godz. {godzina} "
        "u {lekarz} w {clinic_name}.{koszt_info} Aby odwołać wizytę, zadzwoń: {clinic_phone}."
    ),
    "template_reschedule": (
        "Przypominamy o możliwości bezpłatnego przełożenia dzisiejszej wizyty do godz. 12:00. "
        "Zadzwoń: {clinic_phone}."
    ),
    "clinic_name": "Centrum Medyczne Psyche",
    "clinic_phone": "",
    "clinic_address": "",
}


def load(path: Path = _DEFAULT_PATH) -> dict:
    if not path.exists():
        return dict(_DEFAULTS)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    merged = dict(_DEFAULTS)
    merged.update(data)
    return merged


def save(data: dict, path: Path = _DEFAULT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

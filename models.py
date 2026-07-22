from dataclasses import dataclass, field
from datetime import date, time


@dataclass
class Visit:
    doctor: str
    appointment_date: date
    appointment_time: time
    patient_name: str
    pesel: str
    phones: list[str] = field(default_factory=list)
    price: float | None = None
    price_note: str | None = None

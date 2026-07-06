from dataclasses import dataclass
from datetime import date, time


@dataclass
class Visit:
    doctor: str
    appointment_date: date
    appointment_time: time
    patient_name: str
    pesel: str
    phone: str | None
    status: str

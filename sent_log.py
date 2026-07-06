import sqlite3
from datetime import date, datetime
from pathlib import Path

from config import DATA_DIR

_DEFAULT_DB_PATH = DATA_DIR / "sent_log.db"


class SentLog:
    """Tracks which (patient, appointment, reminder type) combos already had
    an SMS sent, so an accidental re-run of the same report never double-texts
    a patient."""

    def __init__(self, db_path: Path = _DEFAULT_DB_PATH):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sent (
                pesel TEXT NOT NULL,
                appointment_date TEXT NOT NULL,
                reminder_type TEXT NOT NULL,
                sent_at TEXT NOT NULL,
                PRIMARY KEY (pesel, appointment_date, reminder_type)
            )
            """
        )
        self._conn.commit()

    def already_sent(self, pesel: str, appointment_date: date, reminder_type: str) -> bool:
        cur = self._conn.execute(
            "SELECT 1 FROM sent WHERE pesel = ? AND appointment_date = ? AND reminder_type = ?",
            (pesel, appointment_date.isoformat(), reminder_type),
        )
        return cur.fetchone() is not None

    def mark_sent(self, pesel: str, appointment_date: date, reminder_type: str) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO sent (pesel, appointment_date, reminder_type, sent_at) VALUES (?, ?, ?, ?)",
            (pesel, appointment_date.isoformat(), reminder_type, datetime.now().isoformat()),
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

# utils/vitals_manager.py
import sqlite3
from typing import Optional, Dict, Any

DB_PATH = "database/hospital.db"

def _conn():
    return sqlite3.connect(DB_PATH)

def init_vitals_table():
    """Create vitals table if it doesn't exist."""
    with _conn() as conn:
        c = conn.cursor()
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS vitals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER NOT NULL,
                hr REAL,
                bp_sys REAL,
                bp_dia REAL,
                spo2 REAL,
                temp REAL,
                timestamp TEXT DEFAULT (datetime('now'))
            )
            """
        )
        conn.commit()

def add_vitals(patient_id: int, hr: float, bp_sys: float, bp_dia: float, spo2: float, temp: float):
    """Insert a vitals snapshot for a patient."""
    with _conn() as conn:
        c = conn.cursor()
        c.execute(
            """
            INSERT INTO vitals (patient_id, hr, bp_sys, bp_dia, spo2, temp)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (patient_id, hr, bp_sys, bp_dia, spo2, temp),
        )
        conn.commit()

def get_latest_vitals(patient_id: int) -> Optional[Dict[str, Any]]:
    """
    Return the latest vitals for a patient as a dict:
    {
      "patient_id": int,
      "hr": float | None,
      "bp_sys": float | None,
      "bp_dia": float | None,
      "spo2": float | None,
      "temp": float | None,
      "timestamp": "YYYY-MM-DD HH:MM:SS"
    }
    Returns None if no vitals found.
    """
    with _conn() as conn:
        c = conn.cursor()
        c.execute(
            """
            SELECT hr, bp_sys, bp_dia, spo2, temp, timestamp
            FROM vitals
            WHERE patient_id = ?
            ORDER BY datetime(timestamp) DESC, id DESC
            LIMIT 1
            """,
            (patient_id,),
        )
        row = c.fetchone()

    if not row:
        return None

    hr, bp_sys, bp_dia, spo2, temp, ts = row
    def _num(x):
        try:
            return float(x) if x is not None else None
        except Exception:
            return None

    return {
        "patient_id": int(patient_id),
        "hr": _num(hr),
        "bp_sys": _num(bp_sys),
        "bp_dia": _num(bp_dia),
        "spo2": _num(spo2),
        "temp": _num(temp),
        "timestamp": ts,
    }

# (Optional) If any old code expects a string, keep this helper:
def get_latest_vitals_str(patient_id: int) -> str:
    d = get_latest_vitals(patient_id)
    if not d:
        return "No vitals recorded."
    return (
        f"HR: {d['hr']}, BP: {d['bp_sys']}/{d['bp_dia']}, "
        f"SpO2: {d['spo2']}, Temp: {d['temp']} (at {d['timestamp']})"
    )

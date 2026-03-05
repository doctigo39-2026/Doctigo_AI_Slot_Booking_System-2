# vitals_bridge.py
from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import streamlit as st
import random

PERSIST_PATH = Path("latest_vitals.json")


def _generate_synthetic_vitals() -> Dict[str, Any]:
    """Generate placeholder vitals if none are available."""
    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "systolic_bp": round(random.uniform(110, 130), 1),
        "diastolic_bp": round(random.uniform(70, 85), 1),
        "body_temperature": round(random.uniform(36.4, 37.2), 1),
        "heart_rate": round(random.uniform(65, 90), 0),
        "spo2": round(random.uniform(96, 99), 0),
    }


def get_latest_vitals() -> Optional[Dict[str, Any]]:
    """Return the most recent vitals from session, file, or fallback synthetic."""
    # 1. From session (live Vitals Hub)
    df = st.session_state.get("forecast_data", None)
    if df is not None and getattr(df, "empty", True) is False:
        try:
            row = df.iloc[-1]
            return {
                "timestamp": str(row.get("timestamp", datetime.now().isoformat())),
                "systolic_bp": float(row.get("systolic_bp", 120.0)),
                "diastolic_bp": float(row.get("diastolic_bp", 80.0)),
                "body_temperature": float(row.get("body_temperature", 36.8)),
            }
        except Exception:
            pass

    # 2. From persisted file (shared between all modules)
    if PERSIST_PATH.exists():
        try:
            data = json.loads(PERSIST_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except Exception:
            pass

    # 3. Fallback (nothing available yet)
    v = _generate_synthetic_vitals()
    set_latest_vitals(v)
    return v


def set_latest_vitals(vitals: Dict[str, Any]) -> None:
    """Persist vitals to session and JSON file for sharing across apps."""
    vitals = dict(vitals)
    vitals["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state["latest_vitals_dict"] = vitals
    try:
        PERSIST_PATH.write_text(json.dumps(vitals, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def clear_vitals() -> None:
    """Clear persisted vitals."""
    try:
        if PERSIST_PATH.exists():
            PERSIST_PATH.unlink()
    except Exception:
        pass

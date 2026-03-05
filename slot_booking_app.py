# slot_booking_app.py — voice input + fixed bottom bar + Admin sidebar + i18n + 2 systems + Ronas theme
from pathlib import Path
import streamlit as st
from streamlit.components.v1 import html as components_html
from datetime import datetime
from typing import Dict, Any, List, Optional
import math, json, random

# ===== Page config (must be first Streamlit call) =====
st.set_page_config(page_title="Doctigo AI", page_icon="🩺", layout="centered")
# === Global Password Gate (must be before any UI renders) ===
#APP_PASSWORD = "admin 123"  # exact phrase with space

#if not st.session_state.get("app_auth_ok", False):
    #st.title("🔒 Password Protected")
    #st.write("Please enter password below.")
    #entered = st.text_input("Enter password", type="password", key="__app_pw")
    #if st.button("Submit", key="__app_pw_btn"):
        #if entered == APP_PASSWORD:
            #st.session_state["app_auth_ok"] = True
            #st.experimental_rerun()
        #else:
            #st.error("Incorrect password")
    #st.stop()

# ===== i18n (server-side; safe fallback) =====
try:
    from i18n import t, INDIA_LANGS
except Exception:
    INDIA_LANGS = ["English"]
    def t(s, lang="English"): return s
def _lang() -> str: return st.session_state.get("ui_lang", "English")
def L(s: str) -> str: return t(s, _lang())

def _lang_to_sr_code(lang: str) -> str:
    table = {
        "English": "en-IN",
        "Hindi": "hi-IN",
        "Bengali": "bn-IN",
        "Assamese": "as-IN",
    }
    return table.get(lang, "en-IN")

# ===== Streamlit shims =====
if not hasattr(st, "experimental_rerun") and hasattr(st, "rerun"):
    st.experimental_rerun = st.rerun
def _rerun():
    if hasattr(st, "rerun"): st.rerun()
    elif hasattr(st, "experimental_rerun"): st.experimental_rerun()
    else: st.session_state["_force_refresh"] = st.session_state.get("_force_refresh", 0) + 1

# ===== External UI components =====
from ChatMessage import ChatMessage
from SymptomSelector import SymptomSelector
from DoctorCard import DoctorCard
from BedSelector import BedSelector
from AppointmentCard import AppointmentCard

# Voice UI: prefer external module if present, else fallback inline component (no extra features)
try:
    from voice_ui import mic_to_fixed_bar  # type: ignore
except Exception:
    def mic_to_fixed_bar(lang_code: str = "en-IN", key: str = "mic_fixed_bar") -> Optional[str]:
        comp_key = f"mic_{key}"
        js = f"""
        <style>
          .mic-pill {{ position: fixed; bottom: 92px; left: 50%; transform: translateX(-50%);
                       background:#111827;color:#f9fafb;padding:6px 10px;border-radius:999px;
                       font-size:12px; display:none; z-index:1001; }}
          .mic-btn {{ height:44px;width:44px;border-radius:12px;border:1px solid #2b2f44;
                      background:#151A2D;color:#E5E7EB;cursor:pointer; }}
          .mic-btn:active {{ transform: scale(0.98); }}
        </style>
        <div style="display:flex;gap:8px;align-items:center;">
          <button id="{comp_key}_btn" class="mic-btn" title="Voice input">🎤</button>
        </div>
        <div id="{comp_key}_pill" class="mic-pill">Listening…</div>
        <script>
          const k = "{comp_key}";
          const pill = document.getElementById(k + "_pill");
          const btn  = document.getElementById(k + "_btn");
          let rec = null, listening = false;

          function show(s) {{
            pill.style.display = s ? "inline-block" : "none";
            btn.textContent = s ? "⏹" : "🎤";
            btn.title = s ? "Stop" : "Voice input";
          }}

          function sendValue(val) {{
            window.parent.postMessage({{
              type: "streamlit:setComponentValue",
              key: k,
              value: val
            }}, "*");
          }}

          function init() {{
            const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
            if (!SR) {{ alert("Voice input not supported."); return null; }}
            const r = new SR();
            r.lang = "{lang_code}";
            r.interimResults = false;
            r.continuous = false;
            r.maxAlternatives = 1;
            r.onresult = (e) => {{
              let txt = "";
              for (let i = e.resultIndex; i < e.results.length; i++) {{
                txt += e.results[i][0].transcript;
              }}
              sendValue(txt.trim());
            }};
            r.onend = () => {{ listening = false; show(false); }};
            r.onerror = () => {{ listening = false; show(false); }};
            return r;
          }}

          btn.addEventListener("click", () => {{
            if (!rec) rec = init();
            if (!rec) return;
            if (!listening) {{
              try {{ rec.start(); listening = true; show(true); }} catch(e) {{}}
            }} else {{
              try {{ rec.stop(); }} catch(e) {{}}
            }}
          }});

          window.parent.postMessage({{ type: "streamlit:componentReady", key: k }}, "*");
        </script>
        """
        _ = components_html(js, height=50, scrolling=False)
        k = f"ComponentValue.{comp_key}"
        if k in st.session_state:
            out = st.session_state[k]
            del st.session_state[k]
            return out
        return None

try:
    from models import Appointment, Doctor, Hospital  # noqa
except Exception:
    Appointment = Doctor = Hospital = object

# ===== Ronas theme injection =====
def _inject_theme_css():
    css_path = Path(__file__).parent / "theme_ronas.css"
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

# ===== Data (Doctors + Hospitals) =====
DOCTORS_MASTER = [
    {"name":"Dr. Amit Kumar Kalwar","specialization":"General Medicine",
     "chamber":"Jeevan Jyoti Institute Of Medical Science, Meherpur",
     "visiting_hours":"11.00am-1.30pm",
     "available_slots":["11:00am-11:30am","12:00pm-12:30pm","1:00pm-1:30pm"],"experience":"15 years"},
    {"name":"Dr. Neha Sharma","specialization":"General Medicine",
     "chamber":"Silchar Medical & Collage, Medical Point",
     "visiting_hours":"9.30am-12.30pm",
     "available_slots":["9:30am-10:00am","10:30am-11:00am","12:00pm-12:30pm"],"experience":"12 years"},
    {"name":"Dr. Rakesh Bora","specialization":"General Medicine",
     "chamber":"Munni Medical Hall, Sonai",
     "visiting_hours":"4.00pm-6.00pm",
     "available_slots":["4:00pm-4:30pm","5:00pm-5:30pm","5:30pm-6:00pm"],"experience":" nine years"},

    {"name":"Dr. Suvajoyti Chakraborty","specialization":"General and Laparoscopic Surgeon",
     "chamber":"Silchar Medical & Collage, Medical Point",
     "visiting_hours":"11.00am-1.30pm",
     "available_slots":["11:00am-11:30am","12:00pm-12:30pm","1:00pm-1:30pm"],"experience":"34 years"},
    {"name":"Dr. Manish Agarwal","specialization":"General and Laparoscopic Surgeon",
     "chamber":"Munni Medical Hall, Sonai",
     "visiting_hours":"2.00pm-4.00pm",
     "available_slots":["2:00pm-2:30pm","3:00pm-3:30pm","3:30pm-4:00pm"],"experience":"14 years"},
    {"name":"Dr. Samir Rahman","specialization":"General and Laparoscopic Surgeon",
     "chamber":"Jeevan Jyoti Institute Of Medical Science, Meherpur",
     "visiting_hours":"6.00pm-8.00pm",
     "available_slots":["6:00pm-6:30pm","7:00pm-7:30pm","7:30pm-8:00pm"],"experience":"17 years"},

    {"name":"Dr. Abhinandan Bhattacharjee","specialization":"ENT Surgeon",
     "chamber":"Munni Medical Hall, Sonai",
     "visiting_hours":"11.00am-4.00pm",
     "available_slots":["11:00am-11:30am","1:00pm-1:30pm","3:00pm-3:30pm"],"experience":"10 years"},
    {"name":"Dr. R.P Banik","specialization":"ENT Surgeon",
     "chamber":"Jeevan Jyoti Institute Of Medical Science, Meherpur",
     "visiting_hours":"12.30pm-2.30pm",
     "available_slots":["12:30pm-1:00pm","1:00pm-1:30pm","2:00pm-2:30pm"],"experience":"18 years"},
    {"name":"Dr. Nirmal Deb","specialization":"ENT Surgeon",
     "chamber":"Silchar Medical & Collage, Medical Point",
     "visiting_hours":"9.00am-11.00am",
     "available_slots":["9:00am-9:30am","10:00am-10:30am","10:30am-11:00am"],"experience":"13 years"},

    {"name":"Dr. Tirthankar Roy","specialization":"Cardiologist",
     "chamber":"Silchar Medical & Collage, Medical Point",
     "visiting_hours":"1.30pm-2.30pm",
     "available_slots":["1:30pm-2:00pm","2:00pm-2:30pm"],"experience":"5 years"},
    {"name":"Dr. Raj Kumar Bhattacharjee","specialization":"Cardiologist",
     "chamber":"Jeevan Jyoti Institute Of Medical Science, Meherpur",
     "visiting_hours":"8.00pm-8.30pm",
     "available_slots":["8:00pm-8:30pm"],"experience":"6 years"},
    {"name":"Dr. Sudip Chakrabarti","specialization":"Cardiologist",
     "chamber":"Munni Medical Hall, Sonai",
     "visiting_hours":"10.00am-12.00pm",
     "available_slots":["10:00am-10:30am","11:00am-11:30am","11:30am-12:00pm"],"experience":"16 years"},

    {"name":"Dr. P.P Dutta","specialization":"Urologist",
     "chamber":"Munni Medical Hall, Sonai",
     "visiting_hours":"12.00pm-12.30pm",
     "available_slots":["12:00pm-12:30pm"],"experience":"10 years"},
    {"name":"Dr. Kaushik Sen","specialization":"Urologist",
     "chamber":"Silchar Medical & Collage , Medical Point",
     "visiting_hours":"4.30pm-6.00pm",
     "available_slots":["4:30pm-5:00pm","5:30pm-6:00pm"],"experience":"11 years"},
    {"name":"Dr. Naba Kumar Das","specialization":"Urologist",
     "chamber":"Jeevan Jyoti Institute Of Medical Science, Meherpur",
     "visiting_hours":"7.00pm-8.30pm",
     "available_slots":["7:00pm-7:30pm","8:00pm-8:30pm"],"experience":"14 years"},

    {"name":"Dr. Prithwiraj Bhattacharjee","specialization":"Medicine (Consultant Physician)",
     "chamber":"Silchar Medical & Collage , Medical Point",
     "visiting_hours":"6.00pm-8.00pm",
     "available_slots":["6:00pm-6:30pm","7:00pm-7:30pm"],"experience":"10 years"},
    {"name":"Dr. Anirban Das","specialization":"Medicine (Consultant Physician)",
     "chamber":"Munni Medical Hall, Sonai",
     "visiting_hours":"9.00am-11.00am",
     "available_slots":["9:00am-9:30am","10:00am-10:30am","10:30am-11:00am"],"experience":"12 years"},
    {"name":"Dr. Sunita Devi","specialization":"Medicine (Consultant Physician)",
     "chamber":"Jeevan Jyoti Institute Of Medical Science, Meherpur",
     "visiting_hours":"5.00pm-7.00pm",
     "available_slots":["5:00pm-5:30pm","6:00pm-6:30pm","6:30pm-7:00pm"],"experience":"15 years"},

    {"name":"Dr. P.K Das","specialization":"Dentist",
     "chamber":"Munni Medical Hall, Sonai",
     "visiting_hours":"5.30pm-6.00pm",
     "available_slots":["5:30pm-6:00pm"],"experience":"20 years"},
    {"name":"Dr. Rituparna Dey","specialization":"Dentist",
     "chamber":"Jeevan Jyoti Institute Of Medical Science, Meherpur",
     "visiting_hours":"10.00am-12.00pm",
     "available_slots":["10:00am-10:30am","11:00am-11:30am","11:30am-12:00pm"],"experience":" nine years"},
    {"name":"Dr. Ashok Jain","specialization":"Dentist",
     "chamber":"Silchar Medical College and Hospital, Medical Point",
     "visiting_hours":"6.00pm-8.00pm",
     "available_slots":["6:00pm-6:30pm","7:00pm-7:30pm","7:30pm-8:00pm"],"experience":"18 years"},

    {"name":"Dr. Kinnor Das","specialization":"Dermatology",
     "chamber":"Jeevan Jyoti Institute Of Medical Science, Meherpur",
     "visiting_hours":"1.00pm-2.00pm",
     "available_slots":["1:00pm-1:30pm","1:30pm-2:00pm"],"experience":"3 years"},
    {"name":"Dr. Megha Kapoor","specialization":"Dermatology",
     "chamber":"Silchar Medical College and Hospital, Medical Point",
     "visiting_hours":"11.00am-1.00pm",
     "available_slots":["11:00am-11:30am","12:00pm-12:30pm","12:30pm-1:00pm"],"experience":" 7 years"},
    {"name":"Dr. Partha Sarathi","specialization":"Dermatology",
     "chamber":"MUNNI MEDICAL HALL, Sonai",
     "visiting_hours":"5.00pm-7.00pm",
     "available_slots":["5:00pm-5:30pm","6:00pm-6:30pm","6:30pm-7:00pm"],"experience":" 9 years"},
]
HOSPITALS_MASTER = [
    {"name":"MUNNI MEDICAL HALL","address":"MOTOR STAND, Tulargram Pt I, Sonai, Assam 788119",
     "latitude":24.734,"longitude":92.8913},
    {"name":"Jeevan Jyoti Institute of Medical Sciences","address":"Meherpur, Birbal Bazar, Silchar, Assam 788015",
     "latitude":24.788,"longitude":92.7934},
    {"name":"Silchar Medical College and Hospital","address":"Ghungoor, Masimpur, Silchar, Assam 788014",
     "latitude":24.7758,"longitude":92.7949},
]

# ===== System 1: Static hospital metrics =====
HOSPITAL_STATIC_METRICS: Dict[str, Dict[str, Any]] = {
    "MUNNI MEDICAL HALL": {"distance_km": 5,  "eta_min": 15},
    "Jeevan Jyoti Institute of Medical Sciences": {"distance_km": 10, "eta_min": 20},
    "Silchar Medical College and Hospital": {"distance_km": 20, "eta_min": 30},
}
def _normalize_hospital_key(text: Optional[str]) -> Optional[str]:
    if not text: return None
    tl = text.lower()
    if "munni medical hall" in tl: return "MUNNI MEDICAL HALL"
    if "jeevan jyoti" in tl: return "Jeevan Jyoti Institute of Medical Sciences"
    if "silchar medical" in tl: return "Silchar Medical College and Hospital"
    for k in HOSPITAL_STATIC_METRICS:
        if k.lower() == tl: return k
    return None
def get_hospital_metrics(hospital_name: Optional[str], bed_serial: Optional[str]) -> Dict[str, Any]:
    key = _normalize_hospital_key(hospital_name or "")
    base = HOSPITAL_STATIC_METRICS.get(key or "", {})
    return {"hospital_name": hospital_name or "", "serial_number": bed_serial or None,
            "distance_km": base.get("distance_km"), "eta_min": base.get("eta_min")}

# ===== System 2: Doctor booking constraints =====
DOCTOR_TICKET_STATIC: Dict[str, int] = {
    "Dr. Amit Kumar Kalwar":18,"Dr. Suvajoyti Chakraborty":12,"Dr. Abhinandan Bhattacharjee":8,
    "Dr. R.P Banik":10,"Dr. Tirthankar Roy":6,"Dr. P.P Dutta":7,"Dr. Raj Kumar Bhattacharjee":5,
    "Dr. Prithwiraj Bhattacharjee":9,"Dr. P.K Das":11,"Dr. Kinnor Das":13,
}
def _distance_eta_from_location_hint(hospital_or_chamber: Optional[str]) -> Dict[str, Optional[int]]:
    key = _normalize_hospital_key(hospital_or_chamber or "")
    base = HOSPITAL_STATIC_METRICS.get(key or "", {})
    return {"distance_km": base.get("distance_km"), "eta_min": base.get("eta_min")}
def get_doctor_constraints(doctor_name: Optional[str], chamber: Optional[str], fallback_hospital: Optional[str]) -> Dict[str, Any]:
    loc = chamber or fallback_hospital
    de = _distance_eta_from_location_hint(loc)
    tickets = DOCTOR_TICKET_STATIC.get(doctor_name or "", 10)
    return {"doctor_name": doctor_name or "", "distance_km": de.get("distance_km"),
            "eta_min": de.get("eta_min"), "tickets_available": tickets,
            "counter_status": "Available" if tickets > 0 else "Closed"}

# ===== Bed inventory =====
BED_STOCK = {
    "General Bed": {"total": 50, "booked": 10, "prefix": "G"},
    "General Cabin": {"total": 20, "booked": 4, "prefix": "C"},
    "VIP Cabin": {"total": 10, "booked": 3, "prefix": "V"},
}

# ===== Conversation steps =====
conversationSteps = {
    "INITIAL":"initial","ASK_NAME":"ask_name","ASK_SYMPTOMS":"ask_symptoms","CHOOSE_PATH":"choose_path",
    "LIST_DOCTORS":"list_doctors","LIST_HOSPITALS":"list_hospitals","ASK_BED":"ask_bed",
    "ASK_VITALS":"ask_vitals","COLLECT_DETAILS":"collect_details","FINAL_CARD":"final_card",
}
patientDetailSteps = [
    {"key":"patient_phone","label":L("phone number")},
    {"key":"patient_gender","label":L("gender (male/female/other)")},
    {"key":"patient_age","label":L("age")},
    {"key":"patient_email","label":L("email address")},
    {"key":"patient_address","label":L("address")},
]

# ===== Helpers, receipt, etc. =====
def calculateDistance(lat1, lng1, lat2, lng2):
    if None in [lat1, lng1, lat2, lng2]: return None
    R=6371; dLat=(lat2-lat1)*math.pi/180; dLng=(lng2-lng1)*math.pi/180
    a=math.sin(dLat/2)**2 + math.cos(lat1*math.pi/180)*math.cos(lat2*math.pi/180)*math.sin(dLng/2)**2
    c=2*math.atan2(math.sqrt(a), math.sqrt(1-a)); return R*c
def calculateETA(distance_km: Optional[float]) -> Optional[int]:
    if distance_km is None: return None
    return round(distance_km*2)
def _synth_vitals() -> Dict[str, Any]:
    return {"timestamp":datetime.now().isoformat(timespec="seconds"),
            "systolic_bp":round(random.uniform(110,130),1),
            "diastolic_bp":round(random.uniform(70,85),1),
            "body_temperature":round(random.uniform(36.4,37.2),1)}
def get_recent_vitals() -> Dict[str, Any]:
    try:
        from vitals_bridge import get_latest_vitals  # type: ignore
        v=get_latest_vitals()
        if v: return v
    except Exception: pass
    df = st.session_state.get("forecast_data", None)
    if df is not None and getattr(df,"empty",True) is False:
        try:
            row=df.iloc[-1]
            return {"timestamp":str(row.get("timestamp", datetime.now().isoformat(timespec="seconds"))),
                    "systolic_bp":float(row.get("systolic_bp",120.0)),
                    "diastolic_bp":float(row.get("diastolic_bp",80.0)),
                    "body_temperature":float(row.get("body_temperature",36.8))}
        except Exception: pass
    return _synth_vitals()
def _assign_bed_serial(bed_type: str) -> Optional[str]:
    stock=BED_STOCK.get(bed_type)
    if not stock: return None
    booked=st.session_state.get("booked_map",{}).get(bed_type,set())
    for i in range(1,stock["total"]+1):
        sid=f"{stock['prefix']}-{i}"
        if sid not in booked:
            if i<=stock["booked"]: continue
            booked.add(sid)
            st.session_state.setdefault("booked_map",{})[bed_type]=booked
            return sid
    return None
def _bed_counts_text() -> str:
    out=[]
    for t,s in BED_STOCK.items():
        used=s["booked"]+len(st.session_state.get("booked_map",{}).get(t,set()))
        out.append(f"{t}: {s['total']-used} {L('available')} ({L('of')} {s['total']})")
    return " • ".join(out)

def build_receipt_html(appt: Dict[str, Any]) -> str:
    patient={"name":appt.get("patient_name",""),"age":appt.get("patient_age",""),
             "gender":appt.get("patient_gender",""),"phone":appt.get("patient_phone",""),
             "email":appt.get("patient_email",""),"address":appt.get("patient_address","")}
    booking_type=appt.get("booking_type","normal").capitalize()
    doc=appt.get("doctor_name",""); hosp=appt.get("hospital_name","")
    dt_str=datetime.fromisoformat(appt.get("appointment_date")).strftime("%d/%m/%Y")
    time_slot=appt.get("appointment_time",""); issued=datetime.now().strftime("%d/%m/%Y, %I:%M %p")

    hm=appt.get("hospital_metrics") or {}
    serial_display = hm.get("serial_number") or L("Assigned at admit desk") if appt.get("needs_bed") else L("N/A")
    hospital_metrics_block=f"""
    <section>
      <h2 class="h2">{L('Hospital Access Metrics')}</h2>
      <div class="grid">
        <div><strong>{L('Hospital')}:</strong> {hosp}</div>
        <div><strong>{L('Distance')}:</strong> {hm.get('distance_km','—')} km</div>
        <div><strong>{L('ETA')}:</strong> {hm.get('eta_min','—')} {L('min')}</div>
        <div><strong>{L('Serial Number')}:</strong> {serial_display}</div>
      </div>
    </section>"""

    bed_block=""
    if appt.get("needs_bed") and appt.get("bed_type"):
        bd=appt.get("bed_details") or {}
        feats=bd.get("features",[])
        feats_html="".join([f"<li>{L(f)}</li>" for f in feats]) if feats else "<li>—</li>"
        bed_block=f"""
        <section>
          <h2 class="h2">{L('Bed/Cabin Details')}</h2>
          <p><strong>{L('Type')}:</strong> {appt.get('bed_type')}</p>
          <p><strong>{L('Serial #')}:</strong> {bd.get('serial') or L('Assigned at admit desk')}</p>
          <p><strong>{L('Price per night')}:</strong> ₹{bd.get('price','')}</p>
          <div class="mt"><strong>{L('Features')}:</strong><ul class="ul">{feats_html}</ul></div>
        </section>"""

    syms=appt.get("symptoms") or []
    sym_block=f"""<div class="mt"><strong>{L('Symptoms')}:</strong> {", ".join([L(s) for s in syms])}</div>""" if syms else ""

    rv=appt.get("recent_vitals")
    vitals_block=""
    if rv:
        vitals_block=f"""
        <section>
          <h2 class="h2">{L('Attached Recent Vitals')}</h2>
          <div class="grid">
            <div><strong>{L('Systolic BP')}:</strong> {rv.get('systolic_bp','')} mmHg</div>
            <div><strong>{L('Diastolic BP')}:</strong> {rv.get('diastolic_bp','')} mmHg</div>
            <div><strong>{L('Body Temperature')}:</strong> {rv.get('body_temperature','')} °C</div>
            <div><strong>{L('Recorded')}:</strong> {rv.get('timestamp','')}</div>
          </div>
        </section>"""

    dbc=appt.get("doctor_constraints") or {}
    doctor_constraints_block=f"""
    <section>
      <h2 class="h2">{L('Doctor Booking Constraints')}</h2>
      <div class="grid">
        <div><strong>{L('Doctor')}:</strong> {doc}</div>
        <div><strong>{L('Distance')}:</strong> {dbc.get('distance_km','—')} km</div>
        <div><strong>{L('ETA')}:</strong> {dbc.get('eta_min','—')} {L('min')}</div>
        <div><strong>{L('Ticket availability at counter')}:</strong> {dbc.get('tickets_available','—')} {L('tickets')}</div>
      </div>
      <div class="mt"><span class="badge">{L('Counter Status')}: {L(dbc.get('counter_status','—'))}</span></div>
    </section>""" if doc else ""

    css="""
    body{font-family:Inter,ui-sans-serif,system-ui,-apple-system,'Segoe UI',Roboto,'Helvetica Neue',Arial;color:#E5E7EB;background:#0F1220}
    .wrap{padding:24px;max-width:860px;margin:0 auto;background:#0F1220}
    .title{font-size:28px;font-weight:800;color:#C7D2FE;text-align:center;margin-bottom:6px}
    .sub{font-size:14px;color:#9CA3AF;text-align:center;margin-bottom:20px}
    .h2{font-size:18px;font-weight:700;border-bottom:2px solid rgba(255,255,255,.08);padding-bottom:8px;margin:18px 0 12px}
    .grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
    .foot{color:#9CA3AF;text-align:center;margin-top:28px;font-size:13px}
    .ul{margin:6px 0 0 18px}.mt{margin-top:8px}
    .badge{display:inline-block;padding:4px 10px;border-radius:9999px;background:rgba(99,102,241,.15);color:#C7D2FE;font-size:12px}
    .card{background:#151A2D;border:1px solid rgba(255,255,255,.06);border-radius:16px;box-shadow:0 12px 30px rgba(0,0,0,.35);padding:16px}
    @media print{.no-print{display:none}}
    """
    html=f"""<!doctype html>
<html><head><meta charset="utf-8"/><title>{L('Doctigo Booking Summary')}</title><style>{css}</style></head>
<body>
  <div class="wrap" id="print-receipt">
    <header class="card">
      <h1 class="title">{L('Doctigo Booking Summary')}</h1>
      <p class="sub">{hosp}</p>
    </header>

    <section class="card">
      <h2 class="h2">{L('Patient Details')}</h2>
      <div class="grid">
        <div><strong>{L('Patient Name')}:</strong> {patient["name"]}</div>
        <div><strong>{L('Age')}:</strong> {patient["age"]}</div>
        <div><strong>{L('Gender')}:</strong> {patient["gender"]}</div>
        <div><strong>{L('Phone')}:</strong> {patient["phone"]}</div>
        <div style="grid-column:1/-1;"><strong>{L('Email')}:</strong> {patient["email"]}</div>
        <div style="grid-column:1/-1;"><strong>{L('Address')}:</strong> {patient["address"]}</div>
      </div>
    </section>

    <section class="card">
      <h2 class="h2">{L('Appointment Details')}</h2>
      <div class="grid">
        <div><strong>{L('Doctor')}:</strong> {doc}</div>
        <div><strong>{L('Booking Type')}:</strong> <span class="badge">{L(booking_type)}</span></div>
        <div><strong>{L('Date')}:</strong> {dt_str}</div>
        <div><strong>{L('Time')}:</strong> {time_slot}</div>
      </div>
      {sym_block}
    </section>

    <section class="card">{hospital_metrics_block}</section>
    {bed_block and f'<section class="card">{bed_block}</section>' or '' }
    {vitals_block and f'<section class="card">{vitals_block}</section>' or '' }
    {doctor_constraints_block and f'<section class="card">{doctor_constraints_block}</section>' or '' }

    <footer class="foot">
      <p>{L('This receipt was auto-generated by Doctigo AI.')}</p>
      <p>{L('Issued on')}: {issued}</p>
      <div class="no-print" style="margin-top:16px;text-align:center;">
        <button onclick="window.print()" style="padding:10px 16px;border-radius:12px;background:#4F46E5;color:#fff;border:0;cursor:pointer;">
          {L('Print')}
        </button>
      </div>
    </footer>
  </div>
</body></html>"""
    return html

def _html_download_button(html_str: str, filename: str, label: str = "⬇️ Download HTML (print to PDF)"):
    b = html_str.encode("utf-8")
    st.download_button(label=label, data=b, file_name=filename, mime="text/html")

# ===== Fixed bottom input bar with voice + send =====
def ChatInputBar(onSend, placeholder="Type your message...", disabled=False, formKey="chat"):
    text_key=f"chat_input_text_{formKey}"; btn_key=f"chat_input_btn_{formKey}"
    st.session_state.setdefault(text_key,"")

    st.markdown("""
    <style>
      .fixed-input-bar{position:fixed;left:0;right:0;bottom:0;z-index:1000;
        padding:12px 16px;background:#0F1220;border-top:1px solid rgba(255,255,255,.08);}
      .fixed-input-inner{max-width:980px;margin:0 auto;display:flex;gap:8px;align-items:center}
      .fixed-input-inner input{width:100%;padding:12px 14px;border-radius:12px;border:1px solid rgba(255,255,255,.08);
        background:#151A2D;color:#E5E7EB;outline:none;}
      .fixed-input-inner button{padding:10px 16px;border-radius:12px;border:0;background:#4F46E5;color:#fff;cursor:pointer;}
      .appview-container .main .block-container{padding-bottom:110px;}
    </style>
    """, unsafe_allow_html=True)

    def _send_cb():
        msg=(st.session_state.get(text_key) or "").strip()
        if not msg or disabled: return
        try: onSend(msg)
        finally:
            st.session_state[text_key]=""
            if hasattr(st, "rerun"): st.rerun()
            elif hasattr(st, "experimental_rerun"): st.experimental_rerun()

    st.markdown('<div class="fixed-input-bar"><div class="fixed-input-inner">', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([0.12, 1, 0.18], gap="small")
    with c1:
        mic_to_fixed_bar(lang_code=_lang_to_sr_code(_lang()))
    with c2:
        st.text_input("", key=text_key, placeholder=placeholder,
                      disabled=disabled, label_visibility="collapsed", on_change=_send_cb)
    with c3:
        st.button("Send ➤", key=btn_key, on_click=_send_cb, disabled=disabled)
    st.markdown('</div></div>', unsafe_allow_html=True)

# ===== Simple Admin dashboard =====
def AdminDashboard():
    st.subheader("📊 Admin Dashboard")
    appt = st.session_state.get("finalAppointment")
    st.write("Latest appointment:", appt if appt else "None")
    st.write("Beds in use:", {k: len(st.session_state.get("booked_map", {}).get(k, set())) for k in BED_STOCK})
    st.write("Messages:", len(st.session_state.get("messages", [])))

# ===== Main App =====
def BookingPage():
    _inject_theme_css()

    with st.sidebar:
        st.markdown("## 🩺 Doctigo")
        st.selectbox("Language", INDIA_LANGS,
                     index=INDIA_LANGS.index(_lang()) if _lang() in INDIA_LANGS else 0,
                     key="ui_lang")
        section = st.radio("Section", ["Slot Booking", "Vitals Hub", "Admin Dashboard"], index=0)

    # Session init
    for k,v in {
        "messages":[], "currentStep":conversationSteps["INITIAL"], "patientName":"",
        "bookingType":"", "symptoms":[], "selectedDoctor":None, "selectedHospital":None,
        "bedSelection":None, "patientDetails":{}, "currentDetailStep":0,
        "finalAppointment":None, "recentVitals":None, "booked_map":{},
    }.items(): st.session_state.setdefault(k,v)

    if section == "Admin Dashboard":
        st.title("🧰 " + L("Admin"))
        AdminDashboard()
        return

    st.title("🩺 " + L("Doctigo AI"))
    st.caption(L("Doctigo AI-powered medical booking assistant"))
    step=st.session_state.currentStep

    if step == conversationSteps["INITIAL"]:
        st.subheader(L("Choose booking type"))
        c1,c2=st.columns(2)
        with c1:
            if st.button("📋 " + L("Normal Booking")):
                st.session_state.bookingType="normal"
                st.session_state.messages.append({"text":L("Normal Booking"),"isBot":False})
                st.session_state.currentStep=conversationSteps["ASK_NAME"]; _rerun()
        with c2:
            if st.button("🚨 " + L("Emergency Booking")):
                st.session_state.bookingType="emergency"
                st.session_state.messages.append({"text":L("Emergency Booking"),"isBot":False})
                st.session_state.currentStep=conversationSteps["ASK_NAME"]; _rerun()
    else:
        st.markdown("### " + L("Chat"))
        for msg in st.session_state.messages:
            ChatMessage(message=msg["text"], isBot=msg["isBot"], timestamp=None)

        if step == conversationSteps["ASK_NAME"]:
            ChatMessage(L("Hello! I am Doc, your friendly Doctigo assistant. What's your name?"), True, None)
            ChatInputBar(onSend=handleName, formKey="ask_name", placeholder=L("Type your message..."))
            return

        elif step == conversationSteps["ASK_SYMPTOMS"]:
            ChatMessage(
                L("This is an emergency. Enter your symptoms or type **next**.")
                if st.session_state.bookingType=="emergency"
                else L("Enter your symptoms or type **next**."), True, None
            )
            SymptomSelector(onSubmit=handleSymptoms, onSkip=lambda: handleSymptoms([]))

        elif step == conversationSteps["CHOOSE_PATH"]:
            ChatMessage(L("What would you like to choose next?"), True, None)
            c1,c2=st.columns(2)
            with c1:
                if st.button("👨‍⚕️ " + L("See Doctors")):
                    st.session_state.currentStep=conversationSteps["LIST_DOCTORS"]; _rerun()
            with c2:
                if st.button("🏥 " + L("See Hospitals")):
                    st.session_state.currentStep=conversationSteps["LIST_HOSPITALS"]; _rerun()

        elif step == conversationSteps["LIST_DOCTORS"]:
            ChatMessage(L("Here are the available doctors:"), True, None)
            filtered=DOCTORS_MASTER
            if st.session_state.symptoms:
                sy_lower=" ".join([s.lower() for s in st.session_state.symptoms])
                spec_map=[("fever cough sore throat","General Medicine"),
                          ("chest pain shortness breath","Cardiologist"),
                          ("ear nose throat","ENT Surgeon"),
                          ("skin rash acne","Dermatology"),
                          ("tooth gum","Dentist"),
                          ("urine kidney","Urologist"),
                          ("surgery","Laparoscopic")]
                wanted=set()
                for keys,spec in spec_map:
                    for k in keys.split():
                        if k in sy_lower: wanted.add(spec)
                if wanted:
                    filtered=[d for d in DOCTORS_MASTER if any(ws in d["specialization"] for ws in wanted)] or DOCTORS_MASTER
            for doc in filtered:
                DoctorCard(doctor=doc, availableSlots=doc["available_slots"],
                           estimatedTime=None, distance=None, onBook=handleDoctorSelect)

        elif step == conversationSteps["LIST_HOSPITALS"]:
            ChatMessage(L("Here are the hospitals. Select one to browse beds/cabins:"), True, None)
            for h in HOSPITALS_MASTER:
                with st.container(border=True):
                    st.markdown(f"**{h['name']}**  \n_{h['address']}_")
                    if st.button(f"{L('Select')} **{h['name']}**", key=f"h_{h['name']}"):
                        st.session_state.selectedHospital=h
                        st.session_state.messages.append({"text":f"{L('Selected hospital')}: {h['name']}", "isBot":False})
                        if st.session_state.bookingType == "emergency":
                            st.session_state.currentStep=conversationSteps["ASK_BED"]
                        else:
                            st.session_state.currentStep=conversationSteps["ASK_VITALS"]
                        _rerun()
            st.caption(L("Inventory right now:") + " " + _bed_counts_text())

        elif step == conversationSteps["ASK_BED"]:
            if st.session_state.bookingType != "emergency":
                st.session_state.currentStep = conversationSteps["ASK_VITALS"]; _rerun()
            ChatMessage(L("Do you need to book a **Bed/Cabin**?") + " (" + _bed_counts_text() + ")", True, None)
            BedSelector(onSelect=handleBedSelect)

        elif step == conversationSteps["ASK_VITALS"]:
            ChatMessage(L("Attach your recent vitals? Type **Yes** or **No**."), True, None)
            ChatInputBar(onSend=handleVitalsChoice, formKey="ask_vitals", placeholder=L("Type Yes or No..."))
            return

        elif step == conversationSteps["COLLECT_DETAILS"]:
            idx=st.session_state.currentDetailStep; detail=patientDetailSteps[idx]
            # Fix KeyError from translated placeholders by avoiding .format on translated strings
            ChatMessage(L("Please enter patient's") + " " + detail['label'] + ":", True, None)
            ChatInputBar(onSend=handleDetail, formKey=f"detail_{detail['key']}", placeholder=L("Type your message..."))
            return

        elif step == conversationSteps["FINAL_CARD"]:
            ChatMessage(L("🎉 Appointment confirmed! Use Print to save as PDF:"), True, None)
            appt=st.session_state.finalAppointment or {}
            html=build_receipt_html(appt)
            st.components.v1.html(html, height=920, scrolling=True)
            _html_download_button(html, "doctigo_receipt.html", label=L("⬇️ Download HTML (print to PDF)"))

    # default input bar
    ChatInputBar(onSend=lambda m: st.session_state.messages.append({"text": m, "isBot": False}),
                 formKey="generic", placeholder=L("Type your message..."))

# ===== Handlers =====
def handleName(name: str):
    st.session_state.patientName=name
    st.session_state.messages.append({"text":name,"isBot":False})
    st.session_state.messages.append({"text":L("Hello {n}! Let's continue.").format(n=name),"isBot":True})
    st.session_state.currentStep=conversationSteps["ASK_SYMPTOMS"]; _rerun()

def handleSymptoms(symptoms: List[str]):
    st.session_state.symptoms=symptoms
    st.session_state.messages.append({"text": L("Symptoms: ") + ", ".join([L(s) for s in symptoms]) if symptoms else L("No symptoms"), "isBot":False})
    st.session_state.currentStep=conversationSteps["CHOOSE_PATH"]; _rerun()

def handleDoctorSelect(doctor: Dict[str, Any]):
    st.session_state.selectedDoctor=doctor
    st.session_state.selectedHospital=None
    st.session_state.messages.append({"text":f"{L('Selected')} {doctor['name']}","isBot":False})
    if st.session_state.bookingType == "emergency":
        st.session_state.currentStep=conversationSteps["ASK_BED"]
    else:
        st.session_state.currentStep=conversationSteps["ASK_VITALS"]
    _rerun()

def handleBedSelect(selection: Optional[Dict[str, Any]]):
    if selection:
        serial=_assign_bed_serial(selection["type"])
        sel=dict(selection); sel["serial"]=serial
        st.session_state.bedSelection=sel
        st.session_state.messages.append(
            {"text":f"{L('Selected')} {selection['type']}" + (f' ({L("Serial")} {serial})' if serial else ''),"isBot":False}
        )
    else:
        st.session_state.bedSelection=None
        st.session_state.messages.append({"text":L("No bed needed."),"isBot":False})
    st.session_state.currentStep=conversationSteps["ASK_VITALS"]; _rerun()

def get_recent_vitals_message(vitals: Dict[str, Any]) -> str:
    return L("✅ Attached recent vitals:") + "\n```\n" + json.dumps(vitals, indent=2, ensure_ascii=False) + "\n```"

def handleVitalsChoice(answer: str):
    ans=(answer or "").strip().lower()
    st.session_state.messages.append({"text":answer,"isBot":False})
    if ans in ("yes","y"):
        v=get_recent_vitals(); st.session_state.recentVitals=v
        st.session_state.messages.append({"text": get_recent_vitals_message(v), "isBot":True})
    else:
        st.session_state.recentVitals=None
        st.session_state.messages.append({"text":L("👍 Proceeding without recent vitals."),"isBot":True})
    st.session_state.currentStep=conversationSteps["COLLECT_DETAILS"]; _rerun()

def handleDetail(detail_value: str):
    idx=st.session_state.currentDetailStep
    currentDetail=patientDetailSteps[idx]
    st.session_state.patientDetails[currentDetail["key"]]=detail_value
    st.session_state.messages.append({"text":detail_value,"isBot":False})

    if idx < len(patientDetailSteps)-1:
        st.session_state.currentDetailStep+=1; _rerun(); return

    selected_doc=st.session_state.selectedDoctor
    selected_hosp=st.session_state.selectedHospital
    if selected_doc:
        hospital_name=selected_doc["chamber"]
        appointment_time=selected_doc["available_slots"][0]
        doctor_name=selected_doc["name"]
    else:
        hospital_name=(selected_hosp or {}).get("name","")
        appointment_time="11:00am-11:30am"
        doctor_name="(Hospital admission)"

    is_emergency = (st.session_state.bookingType == "emergency")
    bed_sel = st.session_state.bedSelection if is_emergency else None

    bed_serial = bed_sel.get("serial") if bed_sel else None
    hospital_metrics = get_hospital_metrics(hospital_name, bed_serial)
    doctor_constraints = get_doctor_constraints(
        doctor_name if selected_doc else None,
        selected_doc.get("chamber") if selected_doc else None,
        hospital_name
    )

    appt={"patient_name":st.session_state.patientName,
          "booking_type":st.session_state.bookingType,
          "symptoms":st.session_state.symptoms,
          "doctor_name":doctor_name,
          "hospital_name":hospital_name,
          "appointment_date":datetime.now().isoformat(),
          "appointment_time":appointment_time,
          **st.session_state.patientDetails,
          "needs_bed":bool(bed_sel),
          "bed_type":bed_sel["type"] if bed_sel else None,
          "bed_details":bed_sel if bed_sel else None,
          "recent_vitals":st.session_state.recentVitals,
          "status":"confirmed",
          "hospital_metrics":hospital_metrics,
          "doctor_constraints":doctor_constraints if selected_doc else None}
    st.session_state.finalAppointment=appt
    st.session_state.currentStep=conversationSteps["FINAL_CARD"]; _rerun()

# ===== Entrypoint =====
if __name__ == "__main__":
    BookingPage()






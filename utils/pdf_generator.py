# utils/pdf_generator.py
from fpdf import FPDF
import sqlite3
import os
import tempfile
from typing import Optional, Dict, Any
from urllib.parse import urlencode
import qrcode
from PIL import Image  # noqa: F401 (kept to ensure Pillow is present)
import streamlit as st

DB_PATH = "database/hospital.db"


class PDF(FPDF):
    def header(self):
        # Hospital Name & Details
        self.set_font("Helvetica", "B", 16)
        self.cell(0, 10, " Silchar Medical Collage ", ln=True, align="C")
        self.set_font("Helvetica", "", 10)
        self.cell(0, 6, "Address: 123 Health Street, City - Pincode", ln=True, align="C")
        self.cell(0, 6, "Contact: +91-9876543210 | GSTIN: 29ABCDE1234F1Z5", ln=True, align="C")
        self.ln(5)
        self.line(10, 35, 200, 35)
        self.ln(5)

        # --- QR code (top-right) ---
        qr_path = getattr(self, "qr_path", None)
        if qr_path and os.path.exists(qr_path):
            try:
                # For A4 portrait (210mm wide), x ~ 170–178 is near the right margin
                self.image(qr_path, x=175, y=10, w=25)
            except Exception:
                # Never fail the whole PDF because of a QR rendering issue
                pass

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")


def _hr(pdf: FPDF, pad: float = 3.0):
    """Light horizontal rule with padding."""
    y = pdf.get_y()
    pdf.set_draw_color(200, 200, 200)
    pdf.line(10, y, 200, y)
    pdf.ln(pad)
    pdf.set_draw_color(0, 0, 0)


def _kv(pdf: FPDF, k: str, v: Any, key_w: int = 42, h: int = 7):
    """Key–value row."""
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(key_w, h, f"{k}:", border=0)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, h, f"{'-' if v in (None, '',) else v}", ln=True, border=0)


def _get_base_url() -> str:
    """
    Prefer Streamlit secrets → fallback to env var APP_BASE_URL → localhost.
    Add this to Streamlit Cloud secrets:
      [app]
      BASE_URL = "https://hospital-invoice.streamlit.app"
    """
    try:
        base = st.secrets.get("app", {}).get("BASE_URL")
        if base:
            return str(base).rstrip("/")
    except Exception:
        pass
    return os.environ.get("APP_BASE_URL", "http://localhost:8501").rstrip("/")


def _make_qr_for_patient(patient_id: int, invoice_id: int) -> Optional[str]:
    """
    Create a QR code that links to the Live Monitor view for this patient.
    URL example: {BASE}/?tab=Live+Monitor&billing_patient_id=<id>
    Returns a temp PNG path (caller may delete after PDF is written).
    """
    try:
        base = _get_base_url()
        query = urlencode({"tab": "Live Monitor", "billing_patient_id": patient_id})
        url = f"{base}/?{query}"

        img = qrcode.make(url)  # returns a PIL image
        tmp_dir = tempfile.gettempdir()
        qr_path = os.path.join(tmp_dir, f"qr_invoice_{invoice_id}.png")
        img.save(qr_path)
        return qr_path
    except Exception:
        return None


def generate_invoice_pdf(invoice_id: int, latest_vitals: Optional[Dict[str, Any]] = None) -> str:
    """
    Generate invoice PDF. If latest_vitals is provided, a 'Latest Patient Vitals' block is appended.
    latest_vitals may include: hr, bp_sys, bp_dia, spo2, temp, timestamp, patient_id
    Also embeds a QR in the header linking to the Live Monitor for the billing patient.
    """
    # Ensure invoices folder exists
    os.makedirs("invoices", exist_ok=True)

    # Fetch data from database
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT * FROM invoices WHERE invoice_id=?", (invoice_id,))
    invoice = c.fetchone()
    if not invoice:
        conn.close()
        raise ValueError(f"❌ Invoice ID {invoice_id} not found in database.")

    # invoice tuple expected order:
    # (invoice_id, patient_id, doctor, department, date, total_amount, status)
    inv_id, patient_id, doctor, department, inv_date, total_amt, status = (
        invoice[0], invoice[1], invoice[2], invoice[3], invoice[4], invoice[5], invoice[6]
    )

    c.execute("SELECT * FROM patients WHERE patient_id=?", (patient_id,))
    patient = c.fetchone()
    if not patient:
        # (patient_id, name, age, gender, contact, admission, discharge)
        patient = (patient_id, "Unknown", "N/A", "N/A", "N/A", "N/A", "N/A")

    c.execute("SELECT description, qty, rate, amount FROM invoice_items WHERE invoice_id=?", (invoice_id,))
    items = c.fetchall()
    conn.close()

    # Prepare QR path for header
    qr_path = _make_qr_for_patient(patient_id, invoice_id)

    pdf = PDF()
    pdf.qr_path = qr_path  # header will pick this up
    pdf.add_page()

    # Invoice Heading
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, f"INVOICE #{inv_id}", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Date: {inv_date}", ln=True)
    pdf.ln(3)

    # Patient Details
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Patient Details:", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Patient ID: {patient[0]}", ln=True)
    pdf.cell(0, 6, f"Name: {patient[1]} | Age: {patient[2]} | Gender: {patient[3]}", ln=True)
    pdf.cell(0, 6, f"Contact: {patient[4]}", ln=True)
    pdf.cell(0, 6, f"Admission: {patient[5]} | Discharge: {patient[6]}", ln=True)
    pdf.ln(3)

    # Doctor & Dept
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Doctor & Department:", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Doctor: {doctor} | Department: {department}", ln=True)
    pdf.ln(3)

    # ---------- Latest Vitals (optional) ----------
    if latest_vitals:
        _hr(pdf, pad=2)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "Latest Patient Vitals (Attached):", ln=True)
        pdf.set_font("Helvetica", "", 10)

        # Two-column layout
        y0 = pdf.get_y()
        x_left, x_right = 10, 110

        # Left column
        pdf.set_xy(x_left, y0)
        _kv(pdf, "Heart Rate (bpm)", latest_vitals.get("hr"))
        _kv(pdf, "SpO2 (%)",       latest_vitals.get("spo2"))
        _kv(pdf, "Temperature (°C)", latest_vitals.get("temp"))

        # Right column
        pdf.set_xy(x_right, y0)
        _kv(pdf, "BP Systolic",  latest_vitals.get("bp_sys"))
        _kv(pdf, "BP Diastolic", latest_vitals.get("bp_dia"))
        _kv(pdf, "Timestamp",    latest_vitals.get("timestamp"))

        pdf.ln(2)
        _hr(pdf, pad=3)

    # Table Header
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(80, 8, "Description", border=1)
    pdf.cell(20, 8, "Qty", border=1, align="R")
    pdf.cell(30, 8, "Rate", border=1, align="R")
    pdf.cell(30, 8, "Amount", border=1, align="R", ln=True)

    # Table Rows
    pdf.set_font("Helvetica", "", 10)
    if items:
        for desc, qty, rate, amount in items:
            pdf.cell(80, 8, str(desc), border=1)
            pdf.cell(20, 8, str(qty), border=1, align="R")
            try:
                pdf.cell(30, 8, f"Rs{float(rate):.2f}", border=1, align="R")
            except Exception:
                pdf.cell(30, 8, str(rate), border=1, align="R")
            try:
                pdf.cell(30, 8, f"Rs{float(amount):.2f}", border=1, align="R", ln=True)
            except Exception:
                pdf.cell(30, 8, str(amount), border=1, align="R", ln=True)
    else:
        pdf.cell(160, 8, "No Items Found", border=1, ln=True)

    # Total
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(130, 10, "Total", border=1)
    try:
        pdf.cell(30, 10, f"Rs{float(total_amt):.2f}", border=1, ln=True)
    except Exception:
        pdf.cell(30, 10, str(total_amt), border=1, ln=True)

    # Payment Status
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 10, f"Payment Status: {status}", ln=True)

    # Save in invoices folder
    out_path = os.path.join("invoices", f"invoice_{invoice_id}.pdf")
    pdf.output(out_path)

    # Clean up temp QR image if any
    try:
        if pdf.qr_path and os.path.exists(pdf.qr_path):
            os.remove(pdf.qr_path)
    except Exception:
        pass

    return out_path

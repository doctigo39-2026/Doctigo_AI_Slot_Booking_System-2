import streamlit as st
import pandas as pd
from datetime import datetime
import os
import plotly.express as px

# Shared vitals from vitals_bridge (same data source used in slot_booking_app)
from vitals_bridge import get_latest_vitals

# Core hospital invoice utilities (shared with Doctigo ecosystem)
from utils.db_manager import init_db, add_patient, add_invoice, add_invoice_item, search_invoices
from utils.pdf_generator import generate_invoice_pdf
from utils.billing_ai import suggest_charges
from utils.vitals_manager import init_vitals_table, add_vitals, get_latest_vitals as get_vitals_db

# ===== PAGE CONFIG =====
st.set_page_config(page_title="🏥 Hospital Invoice System", layout="wide")
st.title("🏥 Hospital Invoice System (Integrated with Vitals & Booking)")

# ===== INIT DATABASES =====
init_db()
init_vitals_table()

# ===== SIDEBAR MENU =====
tabs = ["New Invoice", "Search Invoices", "Analytics", "Invoices Archive"]
tab = st.sidebar.radio("Navigation", tabs)

# ===== HELPER =====
def _link_vitals(patient_id: int):
    """Fetch and show latest vitals from the shared vitals hub."""
    latest = get_latest_vitals() or get_vitals_db(patient_id)
    if latest:
        st.info(f"🩺 Latest Vitals: {latest}")
        return latest
    else:
        st.warning("No vitals data available.")
        return None

# ===== NEW INVOICE =====
if tab == "New Invoice":
    st.subheader("➕ Create New Invoice")
    st.write("Auto-links patient vitals from the shared Doctigo Vitals Hub.")

    with st.form("patient_form"):
        name = st.text_input("Patient Name")
        age = st.number_input("Age", 0, 120)
        gender = st.selectbox("Gender", ["Male", "Female", "Other"])
        contact = st.text_input("Contact")
        admission = st.date_input("Admission Date")
        discharge = st.date_input("Discharge Date")
        submitted = st.form_submit_button("Save Patient")

    if submitted:
        pid = add_patient(name, age, gender, contact, str(admission), str(discharge))
        st.success(f"✅ Patient saved with ID {pid}")

        latest_vitals = _link_vitals(pid)
        doctor = st.text_input("Doctor Name")
        dept = st.text_input("Department")
        diagnosis = st.text_input("Diagnosis / Procedure")
        status = st.selectbox("Payment Status", ["Paid", "Pending"])

        ai_items = suggest_charges(diagnosis) if diagnosis else []
        invoice_items = []

        if ai_items:
            st.write("💡 AI Suggested Charges:")
            for desc, qty, rate, amt in ai_items:
                st.write(f"- {desc} ({qty} × ₹{rate}) = ₹{amt}")
                invoice_items.append((desc, qty, rate, amt))

        with st.form("invoice_form"):
            for i in range(5):
                desc = st.text_input(f"Item {i+1} Description", key=f"desc{i}")
                qty = st.number_input(f"Qty {i+1}", 0, 100, key=f"qty{i}")
                rate = st.number_input(f"Rate {i+1}", 0.0, 1_00_000.0, key=f"rate{i}")
                if desc:
                    invoice_items.append((desc, qty, rate, qty * rate))
            gen = st.form_submit_button("Generate Invoice")

        if gen:
            total = sum(i[3] for i in invoice_items)
            inv_id = add_invoice(pid, doctor, dept, str(datetime.now().date()), total, status)
            for item in invoice_items:
                add_invoice_item(inv_id, *item)
            pdf_path = generate_invoice_pdf(inv_id, latest_vitals=latest_vitals)
            st.success(f"✅ Invoice #{inv_id} created successfully!")

            with open(pdf_path, "rb") as f:
                st.download_button("⬇️ Download Invoice PDF", f, file_name=f"invoice_{inv_id}.pdf")

# ===== SEARCH INVOICES =====
elif tab == "Search Invoices":
    st.subheader("🔍 Search Invoices")
    term = st.text_input("Search by Patient or Doctor Name")
    results = search_invoices(term)
    if results:
        df = pd.DataFrame(results, columns=["Invoice ID", "Patient", "Doctor", "Department", "Date", "Total", "Status"])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No results found.")

# ===== ANALYTICS =====
elif tab == "Analytics":
    st.subheader("📊 Billing Analytics")
    data = search_invoices("")
    if data:
        df = pd.DataFrame(data, columns=["Invoice ID", "Patient", "Doctor", "Department", "Date", "Total", "Status"])
        agg = df.groupby("Department", dropna=False)["Total"].sum().reset_index()
        fig = px.bar(agg, x="Department", y="Total", title="Revenue by Department")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No invoice data yet.")

# ===== ARCHIVE =====
elif tab == "Invoices Archive":
    st.subheader("📂 Invoices Archive")
    os.makedirs("invoices", exist_ok=True)
    pdfs = [f for f in os.listdir("invoices") if f.endswith(".pdf")]
    if pdfs:
        for f in sorted(pdfs):
            with open(os.path.join("invoices", f), "rb") as file:
                st.download_button(f"⬇️ {f}", file, file_name=f)
    else:
        st.info("No invoices yet.")



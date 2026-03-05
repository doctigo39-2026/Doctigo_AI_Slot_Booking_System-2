# utils/db_manager.py
import sqlite3
import os

DB_PATH = "database/hospital.db"

# ✅ Ensure database folder exists
os.makedirs("database", exist_ok=True)

def init_db():
    """Initialize database and create tables if not exists"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Patients table
    c.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            patient_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER,
            gender TEXT,
            contact TEXT,
            admission_date TEXT,
            discharge_date TEXT
        )
    """)

    # Invoices table
    c.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            invoice_id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER,
            doctor TEXT,
            department TEXT,
            date TEXT,
            total_amount REAL,
            status TEXT,
            FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
        )
    """)

    # Invoice Items table
    c.execute("""
        CREATE TABLE IF NOT EXISTS invoice_items (
            item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER,
            description TEXT,
            qty INTEGER,
            rate REAL,
            amount REAL,
            FOREIGN KEY (invoice_id) REFERENCES invoices(invoice_id)
        )
    """)

    conn.commit()
    conn.close()


# ✅ Patient functions
def add_patient(name, age, gender, contact, admission_date, discharge_date):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO patients (name, age, gender, contact, admission_date, discharge_date)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (name, age, gender, contact, admission_date, discharge_date))
    conn.commit()
    patient_id = c.lastrowid
    conn.close()
    return patient_id


# ✅ Invoice functions
def add_invoice(patient_id, doctor, department, date, total_amount, status):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO invoices (patient_id, doctor, department, date, total_amount, status)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (patient_id, doctor, department, date, total_amount, status))
    conn.commit()
    invoice_id = c.lastrowid
    conn.close()
    return invoice_id


def add_invoice_item(invoice_id, description, qty, rate, amount):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO invoice_items (invoice_id, description, qty, rate, amount)
        VALUES (?, ?, ?, ?, ?)
    """, (invoice_id, description, qty, rate, amount))
    conn.commit()
    conn.close()


# ✅ Search invoices
def search_invoices(search_term=""):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    query = """
        SELECT invoices.invoice_id, patients.name, invoices.doctor, invoices.department, 
               invoices.date, invoices.total_amount, invoices.status
        FROM invoices
        JOIN patients ON invoices.patient_id = patients.patient_id
        WHERE patients.name LIKE ? OR invoices.doctor LIKE ?
        ORDER BY invoices.date DESC
    """
    c.execute(query, (f"%{search_term}%", f"%{search_term}%"))
    results = c.fetchall()
    conn.close()
    return results

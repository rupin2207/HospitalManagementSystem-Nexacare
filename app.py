from flask import (Flask, render_template, request, redirect,
                   url_for, flash, jsonify, session)
from functools import wraps
import mysql.connector
from mysql.connector import Error
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, date
import os

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "hms-change-this-in-production")

DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "port":     int(os.getenv("DB_PORT", 3306)),
    "user":     os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "Rupin@0404"),
    "database": os.getenv("DB_NAME", "hms"),
}

# ── DB HELPERS ────────────────────────────────────────────────────────────────
def get_db():
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except Error:
        return None

def query(sql, params=(), fetchone=False):
    conn = get_db()
    if not conn:
        return None
    cur = conn.cursor(dictionary=True)
    cur.execute(sql, params)
    result = cur.fetchone() if fetchone else cur.fetchall()
    conn.close()
    return result

def execute(sql, params=()):
    conn = get_db()
    if not conn:
        return False, "Database connection failed"
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()
        lastid = cur.lastrowid
        conn.close()
        return True, lastid
    except Error as e:
        conn.close()
        return False, str(e)

# ── AUTH DECORATORS ───────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if "user_id" not in session:
                flash("Please log in to continue.", "error")
                return redirect(url_for("login"))
            if session.get("role") not in roles:
                flash("You don't have permission to access that page.", "error")
                return redirect(url_for("dashboard"))
            return f(*args, **kwargs)
        return decorated
    return decorator

# ── AUTH ROUTES ───────────────────────────────────────────────────────────────
@app.route("/", methods=["GET"])
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = query("SELECT * FROM users WHERE username=%s", (username,), fetchone=True)
        if user and check_password_hash(user["password"], password):
            session["user_id"]   = user["id"]
            session["username"]  = user["username"]
            session["role"]      = user["role"]
            session["linked_id"] = user["linked_id"]
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.", "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))

# ── DASHBOARD ROUTER ──────────────────────────────────────────────────────────
@app.route("/dashboard")
@login_required
def dashboard():
    role = session.get("role")
    if role == "admin":
        return redirect(url_for("appointments"))
    if role == "doctor":
        return redirect(url_for("doctor_dashboard"))
    if role == "patient":
        return redirect(url_for("patient_dashboard"))
    session.clear()
    return redirect(url_for("login"))

# ── DOCTOR DASHBOARD ──────────────────────────────────────────────────────────
@app.route("/my/schedule")
@role_required("doctor")
def doctor_dashboard():
    did    = session["linked_id"]
    doctor = query("SELECT * FROM doctors WHERE id=%s", (did,), fetchone=True)
    appointments = query("""
        SELECT a.id, a.appointment_at, a.reason, a.status, a.notes,
               p.full_name AS patient_name, p.id AS patient_id,
               p.date_of_birth, p.gender, p.blood_type, p.phone AS patient_phone
        FROM appointments a
        JOIN patients p ON p.id = a.patient_id
        WHERE a.doctor_id = %s
        ORDER BY a.appointment_at DESC
    """, (did,))
    today    = [a for a in (appointments or []) if a["appointment_at"].date() == date.today()]
    upcoming = [a for a in (appointments or [])
                if a["appointment_at"].date() >= date.today() and a["status"] == "scheduled"]
    return render_template("dashboard_doctor.html",
                           doctor=doctor,
                           appointments=appointments or [],
                           today=today,
                           upcoming=upcoming)

@app.route("/my/appointment/<int:appt_id>/status", methods=["POST"])
@role_required("doctor")
def doctor_update_status(appt_id):
    did    = session["linked_id"]
    status = request.form.get("status")
    notes  = request.form.get("notes", "").strip()
    ok, result = execute(
        "UPDATE appointments SET status=%s, notes=%s WHERE id=%s AND doctor_id=%s",
        (status, notes or None, appt_id, did)
    )
    flash("Updated." if ok else f"Error: {result}", "success" if ok else "error")
    return redirect(url_for("doctor_dashboard"))

# ── PATIENT DASHBOARD ─────────────────────────────────────────────────────────
@app.route("/my/appointments")
@role_required("patient")
def patient_dashboard():
    pid     = session["linked_id"]
    patient = query("SELECT * FROM patients WHERE id=%s", (pid,), fetchone=True)
    history = query("""
        SELECT a.appointment_at, a.reason, a.status, a.notes,
               d.full_name AS doctor_name, d.specialty, d.phone AS doctor_phone
        FROM appointments a
        JOIN doctors d ON d.id = a.doctor_id
        WHERE a.patient_id = %s
        ORDER BY a.appointment_at DESC
    """, (pid,))
    upcoming = [h for h in (history or [])
                if h["appointment_at"].date() >= date.today() and h["status"] == "scheduled"]
    return render_template("dashboard_patient.html",
                           patient=patient,
                           history=history or [],
                           upcoming=upcoming)

# ── ADMIN: APPOINTMENTS ───────────────────────────────────────────────────────
@app.route("/appointments")
@role_required("admin")
def appointments():
    rows = query("""
        SELECT a.id, a.appointment_at, a.reason, a.status, a.notes,
               p.full_name AS patient_name, p.id AS patient_id,
               d.full_name AS doctor_name, d.specialty
        FROM appointments a
        JOIN patients p ON p.id = a.patient_id
        JOIN doctors  d ON d.id = a.doctor_id
        ORDER BY a.appointment_at DESC
    """)
    patients = query("SELECT id, full_name FROM patients ORDER BY full_name")
    doctors  = query("SELECT id, full_name, specialty FROM doctors ORDER BY full_name")
    today    = query("""
        SELECT a.appointment_at, p.full_name AS patient, d.full_name AS doctor, a.status
        FROM appointments a
        JOIN patients p ON p.id = a.patient_id
        JOIN doctors  d ON d.id = a.doctor_id
        WHERE DATE(a.appointment_at) = CURDATE()
        ORDER BY a.appointment_at
    """)
    return render_template("appointments.html",
                           appointments=rows or [],
                           patients=patients or [],
                           doctors=doctors or [],
                           today=today or [])

@app.route("/appointments/add", methods=["POST"])
@role_required("admin")
def add_appointment():
    pid    = request.form.get("patient_id")
    did    = request.form.get("doctor_id")
    at     = request.form.get("appointment_at")
    reason = request.form.get("reason", "").strip()
    notes  = request.form.get("notes", "").strip()
    status = request.form.get("status", "scheduled")
    if not all([pid, did, at]):
        flash("Patient, Doctor and Date/Time are required.", "error")
        return redirect(url_for("appointments"))
    ok, result = execute(
        "INSERT INTO appointments (patient_id,doctor_id,appointment_at,reason,status,notes) VALUES (%s,%s,%s,%s,%s,%s)",
        (pid, did, at, reason, status, notes)
    )
    flash("Appointment booked." if ok else f"Error: {result}", "success" if ok else "error")
    return redirect(url_for("appointments"))

@app.route("/appointments/<int:appt_id>/status", methods=["POST"])
@role_required("admin")
def update_status(appt_id):
    status = request.form.get("status")
    ok, result = execute("UPDATE appointments SET status=%s WHERE id=%s", (status, appt_id))
    flash("Status updated." if ok else f"Error: {result}", "success" if ok else "error")
    return redirect(url_for("appointments"))

@app.route("/appointments/<int:appt_id>/delete", methods=["POST"])
@role_required("admin")
def delete_appointment(appt_id):
    ok, result = execute("DELETE FROM appointments WHERE id=%s", (appt_id,))
    flash("Appointment deleted." if ok else f"Error: {result}", "success" if ok else "error")
    return redirect(url_for("appointments"))

# ── ADMIN: PATIENTS ───────────────────────────────────────────────────────────
@app.route("/patients")
@role_required("admin")
def patients():
    rows = query("SELECT * FROM patients ORDER BY created_at DESC")
    return render_template("patients.html", patients=rows or [])

@app.route("/patients/add", methods=["POST"])
@role_required("admin")
def add_patient():
    fields = {k: request.form.get(k, "").strip() for k in
              ["full_name","date_of_birth","gender","blood_type","address","email","phone"]}
    if not fields["full_name"]:
        flash("Full name is required.", "error")
        return redirect(url_for("patients"))
    ok, result = execute(
        "INSERT INTO patients (full_name,date_of_birth,gender,blood_type,address,email,phone) VALUES (%s,%s,%s,%s,%s,%s,%s)",
        (fields["full_name"], fields["date_of_birth"] or None, fields["gender"] or None,
         fields["blood_type"] or None, fields["address"] or None,
         fields["email"] or None, fields["phone"] or None)
    )
    flash("Patient admitted." if ok else f"Error: {result}", "success" if ok else "error")
    return redirect(url_for("patients"))

@app.route("/patients/<int:pid>")
@role_required("admin")
def patient_detail(pid):
    patient = query("SELECT * FROM patients WHERE id=%s", (pid,), fetchone=True)
    if not patient:
        flash("Patient not found.", "error")
        return redirect(url_for("patients"))
    history = query("""
        SELECT a.appointment_at, d.full_name AS doctor, d.specialty, a.reason, a.status, a.notes
        FROM appointments a
        JOIN doctors d ON d.id = a.doctor_id
        WHERE a.patient_id = %s
        ORDER BY a.appointment_at DESC
    """, (pid,))
    return render_template("patient_detail.html", patient=patient, history=history or [])

@app.route("/patients/<int:pid>/delete", methods=["POST"])
@role_required("admin")
def delete_patient(pid):
    ok, result = execute("DELETE FROM patients WHERE id=%s", (pid,))
    flash("Patient removed." if ok else f"Error: {result}", "success" if ok else "error")
    return redirect(url_for("patients"))

# ── ADMIN: DOCTORS ────────────────────────────────────────────────────────────
@app.route("/doctors")
@role_required("admin")
def doctors():
    rows = query("""
        SELECT d.*, COUNT(a.id) AS total_appointments
        FROM doctors d
        LEFT JOIN appointments a ON a.doctor_id = d.id
        GROUP BY d.id
        ORDER BY total_appointments DESC
    """)
    return render_template("doctors.html", doctors=rows or [])

@app.route("/doctors/add", methods=["POST"])
@role_required("admin")
def add_doctor():
    fields = {k: request.form.get(k, "").strip() for k in
              ["full_name","specialty","department","email","phone"]}
    if not fields["full_name"] or not fields["specialty"]:
        flash("Name and specialty are required.", "error")
        return redirect(url_for("doctors"))
    ok, result = execute(
        "INSERT INTO doctors (full_name,specialty,department,email,phone) VALUES (%s,%s,%s,%s,%s)",
        (fields["full_name"], fields["specialty"],
         fields["department"] or None, fields["email"] or None, fields["phone"] or None)
    )
    flash("Doctor added." if ok else f"Error: {result}", "success" if ok else "error")
    return redirect(url_for("doctors"))

@app.route("/doctors/<int:did>/delete", methods=["POST"])
@role_required("admin")
def delete_doctor(did):
    ok, result = execute("DELETE FROM doctors WHERE id=%s", (did,))
    flash("Doctor removed." if ok else f"Error: {result}", "success" if ok else "error")
    return redirect(url_for("doctors"))

# ── ADMIN: USER MANAGEMENT ────────────────────────────────────────────────────
@app.route("/users")
@role_required("admin")
def manage_users():
    users         = query("SELECT id, username, role, linked_id, created_at FROM users ORDER BY role, username")
    doctors_list  = query("SELECT id, full_name FROM doctors ORDER BY full_name")
    patients_list = query("SELECT id, full_name FROM patients ORDER BY full_name")
    return render_template("manage_users.html",
                           users=users or [],
                           doctors_list=doctors_list or [],
                           patients_list=patients_list or [])

@app.route("/users/add", methods=["POST"])
@role_required("admin")
def add_user():
    username  = request.form.get("username", "").strip()
    password  = request.form.get("password", "").strip()
    role      = request.form.get("role", "")
    linked_id = request.form.get("linked_id") or None
    if not all([username, password, role]):
        flash("Username, password and role are required.", "error")
        return redirect(url_for("manage_users"))
    hashed = generate_password_hash(password)
    ok, result = execute(
        "INSERT INTO users (username,password,role,linked_id) VALUES (%s,%s,%s,%s)",
        (username, hashed, role, linked_id)
    )
    flash(f"User '{username}' created." if ok else f"Error: {result}", "success" if ok else "error")
    return redirect(url_for("manage_users"))

@app.route("/users/<int:uid>/delete", methods=["POST"])
@role_required("admin")
def delete_user(uid):
    if uid == session["user_id"]:
        flash("You cannot delete your own account.", "error")
        return redirect(url_for("manage_users"))
    ok, result = execute("DELETE FROM users WHERE id=%s", (uid,))
    flash("User deleted." if ok else f"Error: {result}", "success" if ok else "error")
    return redirect(url_for("manage_users"))

# ── API ───────────────────────────────────────────────────────────────────────
@app.route("/api/workload")
@role_required("admin")
def api_workload():
    rows = query("""
        SELECT d.full_name, COUNT(a.id) AS total
        FROM doctors d LEFT JOIN appointments a ON a.doctor_id = d.id
        GROUP BY d.id, d.full_name ORDER BY total DESC
    """)
    return jsonify(rows or [])

if __name__ == "__main__":
    app.run(debug=True, port=5000)
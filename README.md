# Nexacare — Healthcare Management Portal

A full-stack hospital management web application built with Flask and MySQL, featuring role-based authentication for Admins, Doctors, and Patients. Each role gets a dedicated dashboard with access only to their relevant data.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.10, Flask 3.x |
| Database | MySQL 8.x via mysql-connector-python |
| Auth | Session-based login with Werkzeug password hashing (scrypt) |
| Frontend | Jinja2 templates, plain CSS (no frameworks) |
| Dev Environment | VS Code, MySQL Workbench |

---

## Features

### Role-Based Access Control
Three distinct roles — each sees only what they need:

| Role | Access |
|---|---|
| **Admin** | Full portal — manage appointments, patients, doctors, and user accounts |
| **Doctor** | Personal schedule, today's patients, update appointment status and notes |
| **Patient** | Own appointment history, upcoming visits, personal health details |

### Admin Dashboard
- Book new appointments (patient + doctor dropdowns, datetime, reason, notes)
- Admit new patients with full demographic data (DOB, gender, blood type, address)
- Add doctors with specialty, department, and contact details
- Inline status updates — no separate save step
- Today's schedule at a glance
- Doctor workload bar chart
- Full user management — create/delete logins, assign roles and link to doctors/patients

### Doctor Dashboard
- Today's patient queue with blood type and contact info
- Upcoming appointments list
- Update appointment status (scheduled / completed / cancelled / no-show) and add clinical notes
- Full appointment history

### Patient Dashboard
- Upcoming appointment cards
- Complete visit history with doctor, specialty, reason, status, and notes
- Personal health details (blood type, DOB, contact)

## Observability & Production Patterns

This project implements production-grade logging and error handling:

- **Structured Logging**: Python `logging` module with `RotatingFileHandler` 
  (1MB rotation, 3 backups). Log levels: DEBUG → INFO → WARNING → ERROR → CRITICAL
- **Retry Logic**: DB connections retry 3 times with exponential backoff (2s, 4s) 
  before failing permanently
- **Dead Letter Queue**: Failed DB operations are written to `failed_operations.csv` 
  for inspection and reprocessing
- **Audit Trail**: All login attempts (success/failure), admin actions, 
  and unauthorized access attempts are logged with timestamp and IP
---

## Database Schema

Three core tables with proper relational integrity:

```
doctors     — id, full_name, specialty, department, email, phone
patients    — id, full_name, date_of_birth, gender, blood_type, address, email, phone
appointments — id, patient_id (FK), doctor_id (FK), appointment_at, reason, status, notes
users       — id, username, password (hashed), role, linked_id
```

- `appointments.patient_id` and `appointments.doctor_id` use `ON DELETE CASCADE`
- `users.linked_id` ties a login account to a specific doctor or patient row
- Indexes on `appointment_at`, `doctor_id`, and `patient_id` for query performance

---

## Setup & Installation

### Prerequisites
- Python 3.10+
- MySQL 8.x running locally
- MySQL Workbench (to run the schema SQL)

### Steps

**1. Clone and navigate**
```bash
cd Hospital-Management-System-master/hms
```

**2. Create and activate a virtual environment**
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Set up the database**

Run the schema SQL in MySQL Workbench against a database named `hms`.

**5. Configure the DB connection**

Edit `DB_CONFIG` in `app.py` or set environment variables:
```bash
# Windows PowerShell
$env:DB_HOST="localhost"
$env:DB_PORT="3306"
$env:DB_USER="root"
$env:DB_PASSWORD="your_password"
$env:DB_NAME="hms"
```

**6. Seed user accounts**
```bash
python setup_users.py
```

**7. Run**
```bash
python app.py
# → http://127.0.0.1:5000
```

---

## Project Structure

```
hms/
├── app.py                        # Flask routes, auth decorators, DB helpers
├── setup_users.py                # One-time script to seed hashed user accounts
├── requirements.txt
└── templates/
    ├── base.html                 # Shared layout, role-aware nav, CSS
    ├── login.html                # Login page
    ├── appointments.html         # Admin: appointments tab
    ├── patients.html             # Admin: patients tab
    ├── doctors.html              # Admin: doctors & staff tab
    ├── patient_detail.html       # Admin: per-patient visit history drill-down
    ├── manage_users.html         # Admin: user account management
    ├── dashboard_doctor.html     # Doctor: personal schedule dashboard
    └── dashboard_patient.html    # Patient: appointment history dashboard
```

---

## Security Notes
- Passwords are hashed using Werkzeug's `scrypt`-based `generate_password_hash` — never stored in plaintext
- Role enforcement via a `role_required()` decorator on every protected route — direct URL access is blocked
- Patients and doctors can only query their own data — `WHERE doctor_id = session.linked_id` enforced server-side
- `SECRET_KEY` should be set via environment variable before any production deployment
- Default credentials (`admin123`, `doctor123`, `patient123`) must be changed after first login in any non-local environment


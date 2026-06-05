# HMS – Hospital Management System (Flask)

A minimal, dark-themed web interface for the 3-table HMS MySQL schema.

## Setup

```bash
# 1. Install deps
pip install -r requirements.txt

# 2. Configure DB connection via environment variables (or edit DB_CONFIG in app.py)
export DB_HOST=localhost
export DB_PORT=3306
export DB_USER=root
export DB_PASSWORD=your_password
export DB_NAME=hms           # the database where you ran the SQL schema

# 3. Run
python app.py
# → http://127.0.0.1:5000
```

## Features

| Tab | What you can do |
|---|---|
| **Appointments** | Book new appointments, update status inline, delete, see today's schedule |
| **Patients** | Admit patients, view registry, click any patient for full visit history |
| **Doctors & Staff** | Add doctors, see workload bar chart, delete staff |

## Notes
- Deleting a patient cascades and removes their appointments (matches your FK schema).
- Deleting a doctor does the same.
- Status changes on the Appointments table are done via a `<select>` that auto-submits — no separate save step needed.
- `DB_CONFIG` in `app.py` defaults to `localhost/root/hms` — override with env vars in production.

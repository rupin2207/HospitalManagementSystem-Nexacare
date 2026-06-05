"""
Run this ONCE to seed the users table with hashed passwords.
It skips any username that already exists.

Usage:
    python setup_users.py
"""
import os, sys
import mysql.connector
from mysql.connector import Error
from werkzeug.security import generate_password_hash

DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "port":     int(os.getenv("DB_PORT", 3306)),
    "user":     os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "Rupin@0404"),
    "database": os.getenv("DB_NAME", "hms"),
}

SEED_USERS = [
    # (username,      plaintext_password,  role,      linked_id)
    ("admin",         "admin123",          "admin",   None),
    ("dr.alice",      "doctor123",         "doctor",  1),
    ("dr.brian",      "doctor123",         "doctor",  2),
    ("dr.carla",      "doctor123",         "doctor",  3),
    ("john.smith",    "patient123",        "patient", 1),
    ("mary.jones",    "patient123",        "patient", 2),
    ("sam.patel",     "patient123",        "patient", 3),
]

def main():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
    except Error as e:
        print(f"[ERROR] Cannot connect to DB: {e}")
        sys.exit(1)

    cur = conn.cursor()

    # Create table if not present
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id         INT AUTO_INCREMENT PRIMARY KEY,
            username   VARCHAR(100) UNIQUE NOT NULL,
            password   VARCHAR(255) NOT NULL,
            role       ENUM('admin','doctor','patient') NOT NULL,
            linked_id  INT DEFAULT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB
    """)
    conn.commit()

    created, skipped = 0, 0
    for username, plainpw, role, linked_id in SEED_USERS:
        hashed = generate_password_hash(plainpw)
        try:
            cur.execute(
                "INSERT INTO users (username, password, role, linked_id) VALUES (%s,%s,%s,%s)",
                (username, hashed, role, linked_id)
            )
            conn.commit()
            print(f"  [OK]   {username:20s}  role={role}  password={plainpw}")
            created += 1
        except Error:
            print(f"  [SKIP] {username:20s}  already exists")
            skipped += 1

    conn.close()
    print(f"\nDone. {created} created, {skipped} skipped.")
    print("\nDefault credentials:")
    print("  Admin   → username: admin        password: admin123")
    print("  Doctor  → username: dr.alice     password: doctor123")
    print("  Patient → username: john.smith   password: patient123")

if __name__ == "__main__":
    main()
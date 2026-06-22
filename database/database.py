"""
database.py
------------
Handles SQLite connection, schema creation, and low-level CRUD helpers
for the Smart Digital Plant Monitoring System.

Design notes:
- Single-file SQLite DB so the whole project runs with zero external services.
- Foreign keys are enforced (PRAGMA foreign_keys = ON) so deleting a user
  cascades sensibly and we never end up with orphaned sensor rows.
- All write operations go through context-managed connections so we never
  leak file handles or leave the DB locked on a crash.
"""

import sqlite3
import hashlib
import os
from contextlib import contextmanager
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "plant_system.db")


@contextmanager
def get_connection():
    """
    Context manager that yields a SQLite connection with foreign keys
    enabled and commits/rolls back automatically.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def hash_password(password: str) -> str:
    """
    Hash a plaintext password using SHA-256 with a static pepper.

    NOTE: For a real production system you would use bcrypt/argon2 with a
    per-user salt. SHA-256 is used here to keep dependencies to the
    standard library only, which matters for a portfolio project that
    needs to run on any machine with zero install friction. This is
    documented honestly rather than pretending it's production-grade.
    """
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def init_db():
    """
    Create all tables if they do not already exist.
    Safe to call every time the app starts.
    """
    with get_connection() as conn:
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS Users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS Plants (
                plant_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                plant_name TEXT NOT NULL,
                species TEXT NOT NULL,
                growth_stage TEXT NOT NULL DEFAULT 'Seed',
                planted_date TEXT NOT NULL,
                is_alive INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS SensorData (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plant_id INTEGER NOT NULL,
                moisture REAL NOT NULL,
                water_level REAL NOT NULL,
                sunlight REAL NOT NULL,
                temperature REAL NOT NULL,
                humidity REAL NOT NULL,
                fertilizer REAL NOT NULL,
                weather TEXT NOT NULL,
                recorded_at TEXT NOT NULL,
                FOREIGN KEY (plant_id) REFERENCES Plants(plant_id) ON DELETE CASCADE
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS Predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plant_id INTEGER NOT NULL,
                health_score REAL NOT NULL,
                health_status TEXT NOT NULL,
                growth_rate REAL NOT NULL,
                days_to_flowering REAL,
                predicted_at TEXT NOT NULL,
                FOREIGN KEY (plant_id) REFERENCES Plants(plant_id) ON DELETE CASCADE
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS Notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plant_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                severity TEXT NOT NULL,
                created_at TEXT NOT NULL,
                is_read INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (plant_id) REFERENCES Plants(plant_id) ON DELETE CASCADE
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS DiseaseScans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plant_id INTEGER NOT NULL,
                diagnosis TEXT NOT NULL,
                confidence REAL NOT NULL,
                treatment TEXT NOT NULL,
                scanned_at TEXT NOT NULL,
                FOREIGN KEY (plant_id) REFERENCES Plants(plant_id) ON DELETE CASCADE
            )
        """)


def now_iso() -> str:
    """Return the current timestamp as an ISO-8601 string."""
    return datetime.now().isoformat(timespec="seconds")


if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {DB_PATH}")

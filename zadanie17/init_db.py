import sqlite3
import os
from pathlib import Path
from werkzeug.security import generate_password_hash

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "app.db"

with sqlite3.connect(DB_PATH) as c:
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS users(
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL
        )
        """
    )

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS uploads(
            file_id TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            disk_name TEXT UNIQUE NOT NULL,
            mime_type TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS documents(
            id TEXT PRIMARY KEY,
            owner_username TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )

    if os.environ.get("SEED_DEMO_DATA") == "1":
        for username, password, role in [
            ("jan", "jan123", "user"),
            ("kasia", "kasia123", "user"),
            ("admin", "admin123", "admin")
        ]:
            c.execute(
                "INSERT OR IGNORE INTO users VALUES(?,?,?)",
                (username, generate_password_hash(password), role)
            )

        documents = [
            ("doc1", "jan", "Faktura #1", "Treść faktury 1", "2023-01-01T00:00:00"),
            ("doc2", "kasia", "Faktura #2", "Treść faktury 2", "2023-01-02T00:00:00"),
            ("doc3", "admin", "Dokument Admina", "Poufne dane admina", "2023-01-03T00:00:00")
        ]

        for document in documents:
            c.execute(
                """
                INSERT OR IGNORE INTO documents
                (id, owner_username, title, content, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                document
            )

    c.commit()

print("Baza zainicjalizowana.")

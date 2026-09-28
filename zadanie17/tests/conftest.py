import os
import sqlite3
from pathlib import Path

import pytest
from werkzeug.security import generate_password_hash

# app.py wymaga sekretu już podczas importu.
os.environ.setdefault("JWT_SECRET", "pytest-secret-key-which-is-long-enough-123456")

import app as application


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "app.db"
    upload_dir = tmp_path / "private_uploads"
    upload_dir.mkdir()

    # Testy używają odseparowanej bazy i katalogu uploadów.
    monkeypatch.setattr(application, "DB", db_path)
    monkeypatch.setattr(application, "STORE", upload_dir)

    application.app.config.update(
        TESTING=True,
        LOGIN_MAX_FAILURES=5,
        LOGIN_BLOCK_SECONDS=60,
    )

    # Każdy test zaczyna z pustym stanem Rate Limitera.
    application.LOGIN_ATTEMPTS.clear()

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE users(
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE uploads(
                file_id TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                disk_name TEXT UNIQUE NOT NULL,
                mime_type TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE documents(
                id TEXT PRIMARY KEY,
                owner_username TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE wallets(
                user_id TEXT PRIMARY KEY,
                balance REAL NOT NULL
            )
            """
        )

        for username, password, role in [
            ("jan", "jan123", "user"),
            ("kasia", "kasia123", "user"),
            ("admin", "admin123", "admin"),
        ]:
            conn.execute(
                "INSERT INTO users VALUES (?, ?, ?)",
                (username, generate_password_hash(password), role),
            )

        conn.executemany(
            "INSERT INTO documents VALUES (?, ?, ?, ?, ?)",
            [
                ("doc1", "jan", "Dokument Jana", "Tajne dane Jana", "2026-01-01"),
                ("doc2", "kasia", "Dokument Kasi", "Tajne dane Kasi", "2026-01-01"),
            ],
        )
        conn.executemany(
            "INSERT INTO wallets VALUES (?, ?)",
            [("jan", 100.0), ("kasia", 100.0), ("admin", 10000.0)],
        )
        conn.commit()

    with application.app.test_client() as test_client:
        yield test_client

    application.LOGIN_ATTEMPTS.clear()


@pytest.fixture()
def login(client):
    def _login(username="jan", password="jan123"):
        response = client.post(
            "/api/login",
            json={"username": username, "password": password},
        )
        assert response.status_code == 200
        return response.get_json()["token"]

    return _login

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "app.db"

with sqlite3.connect(DB_PATH) as c:
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS wallets(
            user_id TEXT PRIMARY KEY,
            balance REAL NOT NULL DEFAULT 0.0,
            FOREIGN KEY (user_id) REFERENCES users(username)
        )
        """
    )

    c.execute(
        """
        INSERT OR IGNORE INTO wallets (user_id, balance)
        SELECT username, 100.0
        FROM users
        WHERE role='user'
        """
    )

    c.execute(
        """
        INSERT OR IGNORE INTO wallets (user_id, balance)
        SELECT username, 10000.0
        FROM users
        WHERE role='admin'
        """
    )

    c.commit()

print("Portfele zainicjalizowane.")

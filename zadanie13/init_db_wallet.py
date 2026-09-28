import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "app.db"

with sqlite3.connect(DB_PATH) as c:
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS wallets (
            user_id TEXT PRIMARY KEY,
            balance REAL NOT NULL DEFAULT 0.0,
            FOREIGN KEY (user_id) REFERENCES users(username)
        )
    """)
    
    
    c.execute("INSERT OR IGNORE INTO wallets (user_id, balance) SELECT username, 100.0 FROM users WHERE role='user'")
    c.execute("INSERT OR IGNORE INTO wallets (user_id, balance) SELECT username, 10000.0 FROM users WHERE role='admin'")
    
    c.commit()

print("Portfele zainicjalizowane: Jan i Kasia mają po 100 zł, Admin ma 10000 zł.")
import sqlite3
from pathlib import Path
from werkzeug.security import generate_password_hash

DB_PATH = Path(__file__).resolve().parent / "app.db"

with sqlite3.connect(DB_PATH) as c:
    
    c.execute("CREATE TABLE IF NOT EXISTS users(username TEXT PRIMARY KEY,password_hash TEXT NOT NULL,role TEXT NOT NULL)")
    c.execute("CREATE TABLE IF NOT EXISTS uploads(file_id TEXT PRIMARY KEY,username TEXT NOT NULL,disk_name TEXT UNIQUE NOT NULL,mime_type TEXT NOT NULL,created_at TEXT NOT NULL)")
    
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            owner_username TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

   
    for n, p, r in [("jan", "jan123", "user"), ("kasia", "kasia123", "user"), ("admin", "admin123", "admin")]:
        c.execute("INSERT OR IGNORE INTO users VALUES(?,?,?)", (n, generate_password_hash(p), r))

   
    c.execute("INSERT OR IGNORE INTO documents (id, owner_username, title, content, created_at) VALUES (?, ?, ?, ?, ?)",
              ("doc1", "jan", "Faktura #1", "Treść faktury 1", "2023-01-01T00:00:00"))
    c.execute("INSERT OR IGNORE INTO documents (id, owner_username, title, content, created_at) VALUES (?, ?, ?, ?, ?)",
              ("doc2", "kasia", "Faktura #2", "Treść faktury 2", "2023-01-02T00:00:00"))
    c.execute("INSERT OR IGNORE INTO documents (id, owner_username, title, content, created_at) VALUES (?, ?, ?, ?, ?)",
              ("doc3", "admin", "Dokument Admina", "Poufne dane admina", "2023-01-03T00:00:00"))

    c.commit()

print("Baza zaktualizowana: tabele users, uploads, documents oraz dane testowe.")
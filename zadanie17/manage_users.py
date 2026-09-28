import argparse
import getpass
import sqlite3
from pathlib import Path
from werkzeug.security import generate_password_hash

DB = Path(__file__).resolve().parent / "data" / "app.db"

parser = argparse.ArgumentParser(description="Utwórz lub zaktualizuj użytkownika")
parser.add_argument("--username", required=True)
parser.add_argument("--role", choices=("user", "admin"), default="user")
args = parser.parse_args()

password = getpass.getpass("Hasło: ")
confirmation = getpass.getpass("Powtórz hasło: ")
if not password or len(password) < 12:
    parser.error("Hasło musi mieć co najmniej 12 znaków")
if password != confirmation:
    parser.error("Hasła są różne")

with sqlite3.connect(DB) as conn:
    conn.execute(
        "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?) "
        "ON CONFLICT(username) DO UPDATE SET password_hash=excluded.password_hash, role=excluded.role",
        (args.username, generate_password_hash(password), args.role),
    )
    conn.execute(
        "INSERT OR IGNORE INTO wallets (user_id, balance) VALUES (?, 0)",
        (args.username,),
    )
    conn.commit()
print("Użytkownik został zapisany.")

from flask import Flask, request, jsonify, send_file, render_template
from pathlib import Path
from werkzeug.security import check_password_hash
from functools import wraps
from datetime import datetime, timezone
import sqlite3
import os
import uuid
import jwt
import time

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
STORE = ROOT / "private_uploads"

DATA_DIR.mkdir(exist_ok=True)
STORE.mkdir(exist_ok=True)

DB = DATA_DIR / "app.db"

SECRET = os.environ.get("JWT_SECRET")
if not SECRET:
    raise RuntimeError("Brak wymaganej zmiennej środowiskowej JWT_SECRET")

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
app.config["LOGIN_MAX_FAILURES"] = 5
app.config["LOGIN_BLOCK_SECONDS"] = 60

# Prosty limiter dla pojedynczego procesu Gunicorn.
# Klucz: adres klienta, wartość: liczba błędów i czas blokady.
LOGIN_ATTEMPTS = {}


@app.after_request
def security_headers(response):
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self'; "
        "img-src 'self' data: blob:; "
        "connect-src 'self'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "frame-ancestors 'none'"
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


def conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def auth(fn):
    @wraps(fn)
    def inner(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return jsonify(error="Wymagany token"), 401

        try:
            claims = jwt.decode(
                header[7:],
                SECRET,
                algorithms=["HS256"],
                options={"require": ["sub", "role", "exp"]}
            )
        except jwt.InvalidTokenError:
            return jsonify(error="Token nieprawidłowy lub wygasł"), 401

        request.user = {
            "name": claims["sub"],
            "role": claims["role"]
        }

        return fn(*args, **kwargs)

    return inner


def image_type(data):
    if (
        len(data) >= 24
        and data[:8] == bytes.fromhex("89504e470d0a1a0a")
        and data[12:16] == b"IHDR"
        and data.endswith(bytes.fromhex("49454e44ae426082"))
    ):
        return "png", "image/png"

    if (
        len(data) >= 4
        and data[:3] == bytes.fromhex("ffd8ff")
        and data[-2:] == bytes.fromhex("ffd9")
    ):
        return "jpg", "image/jpeg"

    return None, None


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/login")
def login():
    data = request.get_json(silent=True) or {}
    client_ip = request.remote_addr or "unknown"
    now_ts = time.time()

    state = LOGIN_ATTEMPTS.get(
        client_ip,
        {"failures": 0, "blocked_until": 0.0}
    )

    if state["blocked_until"] > now_ts:
        retry_after = max(1, int(state["blocked_until"] - now_ts + 0.999))
        response = jsonify(error="Zbyt wiele błędnych prób logowania")
        response.headers["Retry-After"] = str(retry_after)
        return response, 429

    with conn() as c:
        user = c.execute(
            "SELECT * FROM users WHERE username=?",
            (data.get("username", ""),)
        ).fetchone()

    if not user or not check_password_hash(
        user["password_hash"],
        data.get("password", "")
    ):
        state["failures"] += 1

        if state["failures"] >= app.config["LOGIN_MAX_FAILURES"]:
            state["blocked_until"] = now_ts + app.config["LOGIN_BLOCK_SECONDS"]
            LOGIN_ATTEMPTS[client_ip] = state

            response = jsonify(error="Zbyt wiele błędnych prób logowania")
            response.headers["Retry-After"] = str(app.config["LOGIN_BLOCK_SECONDS"])
            return response, 429

        LOGIN_ATTEMPTS[client_ip] = state
        return jsonify(error="Błędne dane"), 401

    # Poprawne logowanie zeruje licznik błędów dla danego klienta.
    LOGIN_ATTEMPTS.pop(client_ip, None)

    now = int(datetime.now(timezone.utc).timestamp())

    token = jwt.encode(
        {
            "sub": user["username"],
            "role": user["role"],
            "iat": now,
            "exp": now + 3600
        },
        SECRET,
        algorithm="HS256"
    )

    return jsonify(token=token)


@app.post("/api/upload")
@auth
def upload():
    uploaded = request.files.get("file")

    if uploaded is None:
        return jsonify(error="Brak pliku"), 400

    content = uploaded.stream.read(5 * 1024 * 1024 + 1)

    if not content:
        return jsonify(error="Pusty plik"), 400

    if len(content) > 5 * 1024 * 1024:
        return jsonify(error="Za duży plik"), 413

    ext, mime = image_type(content)
    if not ext:
        return jsonify(error="Nieprawidłowa sygnatura PNG/JPEG"), 400

    file_id = uuid.uuid4().hex
    disk_name = uuid.uuid4().hex + "." + ext
    path = STORE / disk_name

    with open(path, "xb") as output:
        output.write(content)

    os.chmod(path, 0o600)

    with conn() as c:
        c.execute(
            "INSERT INTO uploads VALUES(?,?,?,?,?)",
            (
                file_id,
                request.user["name"],
                disk_name,
                mime,
                datetime.now(timezone.utc).isoformat()
            )
        )
        c.commit()

    return jsonify(file_id=file_id, message="Zapisano"), 201


@app.get("/api/files/<file_id>")
@auth
def download(file_id):
    with conn() as c:
        row = c.execute(
            "SELECT * FROM uploads WHERE file_id=?",
            (file_id,)
        ).fetchone()

    if not row:
        return jsonify(error="Nie znaleziono"), 404

    if (
        row["username"] != request.user["name"]
        and request.user["role"] != "admin"
    ):
        return jsonify(error="Brak uprawnień"), 403

    path = STORE / row["disk_name"]

    if not path.is_file():
        return jsonify(error="Brak pliku na dysku"), 404

    return send_file(
        path,
        as_attachment=False,
        download_name=row["disk_name"],
        mimetype=row["mime_type"]
    )


@app.get("/api/documents/<doc_id>")
@auth
def get_document(doc_id):
    with conn() as c:
        row = c.execute(
            """
            SELECT *
            FROM documents
            WHERE id=?
              AND (owner_username=? OR ?='admin')
            """,
            (
                doc_id,
                request.user["name"],
                request.user["role"]
            )
        ).fetchone()

        if not row:
            exists = c.execute(
                "SELECT 1 FROM documents WHERE id=?",
                (doc_id,)
            ).fetchone()

            if exists:
                return jsonify(error="Brak uprawnień"), 403

            return jsonify(error="Nie znaleziono dokumentu"), 404

    return jsonify({
        "id": row["id"],
        "owner": row["owner_username"],
        "title": row["title"],
        "content": row["content"],
        "created_at": row["created_at"]
    })


@app.put("/api/documents/<doc_id>")
@auth
def update_document(doc_id):
    data = request.get_json(silent=True)

    if not data or "title" not in data or "content" not in data:
        return jsonify(
            error="Brak wymaganych pól: title, content"
        ), 400

    with conn() as c:
        cursor = c.execute(
            """
            UPDATE documents
            SET title=?, content=?, created_at=?
            WHERE id=?
              AND (owner_username=? OR ?='admin')
            """,
            (
                data["title"],
                data["content"],
                datetime.now(timezone.utc).isoformat(),
                doc_id,
                request.user["name"],
                request.user["role"]
            )
        )
        c.commit()

        if cursor.rowcount == 0:
            exists = c.execute(
                "SELECT 1 FROM documents WHERE id=?",
                (doc_id,)
            ).fetchone()

            if exists:
                return jsonify(error="Brak uprawnień"), 403

            return jsonify(error="Nie znaleziono dokumentu"), 404

    return jsonify(message="Zaktualizowano"), 200


@app.post("/api/wallet/transfer")
@auth
def transfer_fixed():
    data = request.get_json(silent=True) or {}

    try:
        amount = float(data.get("amount", 0))
    except (TypeError, ValueError):
        return jsonify(error="Nieprawidłowa kwota"), 400

    if amount <= 0:
        return jsonify(error="Kwota musi być dodatnia"), 400

    with conn() as c:
        cursor = c.execute(
            """
            UPDATE wallets
            SET balance = balance - ?
            WHERE user_id = ?
              AND balance >= ?
            """,
            (
                amount,
                request.user["name"],
                amount
            )
        )
        c.commit()

        if cursor.rowcount == 0:
            check = c.execute(
                "SELECT balance FROM wallets WHERE user_id=?",
                (request.user["name"],)
            ).fetchone()

            if check and check["balance"] < amount:
                return jsonify(error="Niewystarczające środki"), 400

            return jsonify(error="Konflikt transakcji"), 409

        new_balance = c.execute(
            "SELECT balance FROM wallets WHERE user_id=?",
            (request.user["name"],)
        ).fetchone()["balance"]

    return jsonify({
        "status": "sukces",
        "old_balance": new_balance + amount,
        "new_balance": new_balance
    }), 200


if __name__ == "__main__":
    # Do uruchamiania lokalnego bez Gunicorna.
    app.run(host="0.0.0.0", port=int(os.environ.get("APP_PORT", "5000")))

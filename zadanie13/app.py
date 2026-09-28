from flask import Flask, request, jsonify, send_file, render_template
from pathlib import Path
from werkzeug.security import check_password_hash
from functools import wraps
from datetime import datetime, timezone
import sqlite3, os, uuid, jwt

ROOT=Path(__file__).resolve().parent
DB=ROOT/"app.db"
STORE=ROOT/"private_uploads"
STORE.mkdir(exist_ok=True)
SECRET=os.environ.get("JWT_SECRET","local-demo-change-this-secret")
app=Flask(__name__)
app.config["MAX_CONTENT_LENGTH"]=5*1024*1024

def conn():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c

def auth(fn):
    @wraps(fn)
    def inner(*a,**kw):
        h=request.headers.get("Authorization","")
        if not h.startswith("Bearer "): return jsonify(error="Wymagany token"),401
        try: claims=jwt.decode(h[7:],SECRET,algorithms=["HS256"],options={"require":["sub","role","exp"]})
        except jwt.InvalidTokenError: return jsonify(error="Token nieprawidłowy lub wygasł"),401
        request.user={"name":claims["sub"],"role":claims["role"]}
        return fn(*a,**kw)
    return inner

def image_type(b):
    if len(b)>=24 and b[:8]==bytes.fromhex("89504e470d0a1a0a") and b[12:16]==b"IHDR" and b.endswith(bytes.fromhex("49454e44ae426082")):
        return "png","image/png"
    if len(b)>=4 and b[:3]==bytes.fromhex("ffd8ff") and b[-2:]==bytes.fromhex("ffd9"):
        return "jpg","image/jpeg"
    return None,None

@app.get("/")
def index(): return render_template("index.html")

@app.post("/api/login")
def login():
    d=request.get_json(silent=True) or {}
    with conn() as c: u=c.execute("SELECT * FROM users WHERE username=?",(d.get("username",""),)).fetchone()
    if not u or not check_password_hash(u["password_hash"],d.get("password","")): return jsonify(error="Błędne dane"),401
    now=int(datetime.now(timezone.utc).timestamp())
    t=jwt.encode({"sub":u["username"],"role":u["role"],"iat":now,"exp":now+3600},SECRET,algorithm="HS256")
    return jsonify(token=t)

@app.post("/api/upload-vulnerable")
@auth
def weak_upload():
    f=request.files.get("file")
    if not f: return jsonify(error="Brak pliku"),400
    if Path(f.filename or "").suffix.lower() not in {".png",".jpg",".jpeg"} and f.mimetype not in {"image/png","image/jpeg"}:
        return jsonify(error="Dozwolone PNG/JPEG"),400
    b=f.read(5*1024*1024+1)
    if len(b)>5*1024*1024: return jsonify(error="Za duży plik"),413
    name=uuid.uuid4().hex+"_"+Path(f.filename or "upload").name
    (STORE/name).write_bytes(b)
    return jsonify(path="/uploads/"+name),201

@app.get("/uploads/<path:name>")
def weak_public_file(name):
    p=(STORE/name).resolve()
    if STORE.resolve() not in p.parents or not p.is_file(): return jsonify(error="Brak pliku"),404
    return send_file(p,as_attachment=True,download_name=p.name)

@app.post("/api/upload")
@auth
def upload():
    f=request.files.get("file")
    if f is None: return jsonify(error="Brak pliku"),400
    b=f.stream.read(5*1024*1024+1)
    if not b: return jsonify(error="Pusty plik"),400
    if len(b)>5*1024*1024: return jsonify(error="Za duży plik"),413
    ext,mime=image_type(b)
    if not ext: return jsonify(error="Nieprawidłowa sygnatura PNG/JPEG"),400
    fid=uuid.uuid4().hex; disk=uuid.uuid4().hex+"."+ext
    with open(STORE/disk,"xb") as out:
        os.chmod(STORE/disk,0o600); out.write(b)
    with conn() as c:
        c.execute("INSERT INTO uploads VALUES(?,?,?,?,?)",(fid,request.user["name"],disk,mime,datetime.now(timezone.utc).isoformat())); c.commit()
    return jsonify(file_id=fid,message="Zapisano"),201

@app.get("/api/files/<fid>")
@auth
def download(fid):
    with conn() as c: row=c.execute("SELECT * FROM uploads WHERE file_id=?",(fid,)).fetchone()
    if not row: return jsonify(error="Nie znaleziono"),404
    if row["username"]!=request.user["name"] and request.user["role"]!="admin": return jsonify(error="Brak uprawnień"),403
    p=STORE/row["disk_name"]
    if not p.is_file(): return jsonify(error="Brak pliku na dysku"),404
    mime=row["mime_type"]
    return send_file(p,as_attachment=False,download_name=row["disk_name"],mimetype=mime)



@app.get("/api/documents/<doc_id>")
@auth
def get_document(doc_id):
    """
    Pobiera dokument. 
    Weryfikacja: Tylko właściciel lub admin może odczytać.
    """
    with conn() as c:
      
        row = c.execute(
            "SELECT * FROM documents WHERE id=? AND (owner_username=? OR ?='admin')",
            (doc_id, request.user["name"], request.user["role"])
        ).fetchone()
    
    if not row:
    
        exists = c.execute("SELECT 1 FROM documents WHERE id=?", (doc_id,)).fetchone()
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
    """
    Aktualizuje dokument.
    Tylko właściciel lub admin może zaktualizować.
    """
    data = request.get_json(silent=True)
    if not data or "title" not in data or "content" not in data:
        return jsonify(error="Brak wymaganych pól: title, content"), 400

    with conn() as c:
        
        cursor = c.execute(
            "UPDATE documents SET title=?, content=?, created_at=? WHERE id=? AND (owner_username=? OR ?='admin')",
            (data["title"], data["content"], datetime.now(timezone.utc).isoformat(), doc_id, request.user["name"], request.user["role"])
        )
        c.commit()
        
        if cursor.rowcount == 0:
            
            exists = c.execute("SELECT 1 FROM documents WHERE id=?", (doc_id,)).fetchone()
            if exists:
                return jsonify(error="Brak uprawnień"), 403
            return jsonify(error="Nie znaleziono dokumentu"), 404
            
    return jsonify(message="Zaktualizowano"), 200

@app.post("/api/wallet/transfer")
@auth
def transfer_fixed():
    """
    WERSJA BEZPIECZNA (Zadanie 13/3)
    Logika: UPDATE ... WHERE balance >= amount (Atomowa operacja SQL)
    """
    data = request.get_json(silent=True)
    amount = data.get("amount", 0)
    
    if amount <= 0:
        return jsonify(error="Kwota musi być dodatnia"), 400

    with conn() as c:

        cursor = c.execute(
            "UPDATE wallets SET balance = balance - ? WHERE user_id = ? AND balance >= ?",
            (amount, request.user["name"], amount)
        )
        c.commit() # Commit zamyka transakcję i zwalnia blokady

        if cursor.rowcount == 0:
          
            check = c.execute("SELECT balance FROM wallets WHERE user_id=?", (request.user["name"],)).fetchone()
            if check and check['balance'] < amount:
                return jsonify(error="Niewystarczające środki"), 400
            else:
                
                return jsonify(error="Konflikt transakcji (try again)"), 409
                
        new_balance = c.execute("SELECT balance FROM wallets WHERE user_id=?", (request.user["name"],)).fetchone()["balance"]

        return jsonify({
            "status": "sukces",
            "old_balance": new_balance + amount,
            "new_balance": new_balance
        }), 200
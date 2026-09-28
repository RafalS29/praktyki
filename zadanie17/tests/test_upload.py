import argparse
import base64
import requests

parser = argparse.ArgumentParser()
parser.add_argument("--url", required=True)
args = parser.parse_args()
BASE_URL = args.url.rstrip("/")

login = requests.post(
    BASE_URL + "/api/login",
    json={"username": "jan", "password": "jan123"},
    timeout=5
)
login.raise_for_status()

headers = {
    "Authorization": "Bearer " + login.json()["token"]
}

# Udajemy PNG tylko nazwa i MIME. Binarnie to nie jest PNG.
fake = {
    "file": (
        "payload.php.png",
        b"<?php echo 'TO_NIE_JEST_PNG'; ?>",
        "image/png"
    )
}

response = requests.post(
    BASE_URL + "/api/upload",
    headers=headers,
    files=fake,
    timeout=5
)

print(
    "Falsyzywy PNG:",
    response.status_code,
    response.text
)

if response.status_code != 400:
    raise SystemExit("[BLAD] Serwer zaakceptowal nieprawidlowa strukture pliku.")

# Poprawny maly PNG, aby potwierdzic, ze katalog uploadow jest zapisywalny.
png_1x1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9Z9Z8AAAAASUVORK5CYII="
)

valid = {
    "file": (
        "test.png",
        png_1x1,
        "image/png"
    )
}

response = requests.post(
    BASE_URL + "/api/upload",
    headers=headers,
    files=valid,
    timeout=5
)

print(
    "Poprawny PNG:",
    response.status_code,
    response.text
)

if response.status_code != 201:
    raise SystemExit("[BLAD] Poprawny PNG nie zostal zapisany.")

print("[OK] Manipulowany plik zostal odrzucony, a prawidlowy upload dziala.")

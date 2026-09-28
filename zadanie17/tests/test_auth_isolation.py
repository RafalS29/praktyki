import argparse
import requests

parser = argparse.ArgumentParser()
parser.add_argument("--url", required=True)
args = parser.parse_args()
BASE_URL = args.url.rstrip("/")


def token(username, password):
    response = requests.post(
        BASE_URL + "/api/login",
        json={"username": username, "password": password},
        timeout=5
    )
    response.raise_for_status()
    return response.json()["token"]


def headers(jwt_token):
    return {"Authorization": "Bearer " + jwt_token}


jan = token("jan", "jan123")
kasia = token("kasia", "kasia123")
admin = token("admin", "admin123")

tests = []

# Wlasny dokument Jana - powinien byc dostepny.
r = requests.get(
    BASE_URL + "/api/documents/doc1",
    headers=headers(jan),
    timeout=5
)
tests.append(("Jan czyta swoj dokument", r.status_code, 200))

# Jan nie powinien czytac dokumentu Kasi.
r = requests.get(
    BASE_URL + "/api/documents/doc2",
    headers=headers(jan),
    timeout=5
)
tests.append(("Jan czyta dokument Kasi", r.status_code, 403))

# Jan nie powinien modyfikowac dokumentu Kasi.
r = requests.put(
    BASE_URL + "/api/documents/doc2",
    headers=headers(jan),
    json={"title": "atak", "content": "atak"},
    timeout=5
)
tests.append(("Jan modyfikuje dokument Kasi", r.status_code, 403))

# Kasia nie powinna czytac dokumentu Jana.
r = requests.get(
    BASE_URL + "/api/documents/doc1",
    headers=headers(kasia),
    timeout=5
)
tests.append(("Kasia czyta dokument Jana", r.status_code, 403))

# Admin powinien miec dostep.
r = requests.get(
    BASE_URL + "/api/documents/doc1",
    headers=headers(admin),
    timeout=5
)
tests.append(("Admin czyta dokument Jana", r.status_code, 200))

failed = False

for description, actual, expected in tests:
    ok = actual == expected
    print(
        f"{'[OK]' if ok else '[BLAD]'} "
        f"{description}: HTTP {actual}, oczekiwano {expected}"
    )
    if not ok:
        failed = True

if failed:
    raise SystemExit(1)

print("[OK] Izolacja zasobow uzytkownikow dziala poprawnie.")

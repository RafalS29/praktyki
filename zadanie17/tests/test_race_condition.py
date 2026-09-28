import argparse
import concurrent.futures
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

token = login.json()["token"]
headers = {"Authorization": "Bearer " + token}

REQUESTS = 10
AMOUNT = 80


def transfer(_):
    try:
        response = requests.post(
            BASE_URL + "/api/wallet/transfer",
            headers=headers,
            json={"amount": AMOUNT},
            timeout=10
        )
        return response.status_code, response.text
    except requests.RequestException as exc:
        return 0, str(exc)


with concurrent.futures.ThreadPoolExecutor(
    max_workers=REQUESTS
) as executor:
    results = list(executor.map(transfer, range(REQUESTS)))

successes = sum(1 for status, _ in results if status == 200)

print(f"Liczba rownoleglych zapytan: {REQUESTS}")
print(f"Kwota jednego zapytania: {AMOUNT}")
print(f"Sukcesy HTTP 200: {successes}")

for i, (status, body) in enumerate(results, start=1):
    print(f"{i:02d}: HTTP {status} {body}")

# Na swiezej bazie Jan ma 100 zl, wiec maksymalnie jedna operacja po 80 zl
# moze przejsc. 0 sukcesow jest mozliwe przy ponownym uruchomieniu testu,
# gdy saldo bylo juz zuzyte.
if successes > 1:
    raise SystemExit(
        "[BLAD] Wykryto race condition: wiecej niz jedna operacja zostala zaakceptowana."
    )

print("[OK] Nie zaobserwowano wielokrotnego wydania tych samych srodkow.")

import argparse
import requests

parser = argparse.ArgumentParser()
parser.add_argument("--url", required=True)
args = parser.parse_args()

base = args.url.rstrip("/")
response = requests.get(base + "/", timeout=5)

expected = {
    "Content-Security-Policy": None,
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
}

print(f"HTTP {response.status_code}")

failed = False

for header, expected_value in expected.items():
    actual = response.headers.get(header)
    print(f"{header}: {actual}")

    if actual is None:
        failed = True
        print("  [BLAD] Brak naglowka.")
    elif expected_value is not None and actual.lower() != expected_value.lower():
        failed = True
        print(f"  [BLAD] Oczekiwano: {expected_value}")

if failed:
    raise SystemExit(1)

print("[OK] Wymagane naglowki ochronne sa obecne.")

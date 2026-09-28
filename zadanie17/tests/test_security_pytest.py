import base64
import io
import time

import jwt

import app as application


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def test_forged_jwt_is_rejected(client, login):
    """Zmiana payloadu prawidłowego JWT bez ponownego podpisania ma dać 401."""
    valid = login()
    header, payload, signature = valid.split(".")

    # Minimalnie modyfikujemy zakodowany payload. Podpis pozostaje stary.
    replacement = "A" if payload[-1] != "A" else "B"
    forged = ".".join([header, payload[:-1] + replacement, signature])

    response = client.get(
        "/api/documents/doc1",
        headers=auth_header(forged),
    )

    assert response.status_code == 401
    assert "Token" in response.get_json()["error"]


def test_expired_jwt_is_rejected(client):
    """Poprawnie podpisany, ale wygasły JWT ma zostać odrzucony."""
    now = int(time.time())
    expired = jwt.encode(
        {
            "sub": "jan",
            "role": "user",
            "iat": now - 3600,
            "exp": now - 1,
        },
        application.SECRET,
        algorithm="HS256",
    )

    response = client.get(
        "/api/documents/doc1",
        headers=auth_header(expired),
    )

    assert response.status_code == 401


def test_jwt_signed_with_wrong_key_is_rejected(client):
    """Token z poprawną strukturą, lecz podpisany innym sekretem, ma dać 401."""
    now = int(time.time())
    wrong_signature = jwt.encode(
        {
            "sub": "jan",
            "role": "user",
            "iat": now,
            "exp": now + 3600,
        },
        "attacker-secret-key",
        algorithm="HS256",
    )

    response = client.get(
        "/api/documents/doc1",
        headers=auth_header(wrong_signature),
    )

    assert response.status_code == 401


def test_upload_rejects_fake_png_signature(client, login):
    """Nazwa .png i MIME image/png nie wystarczają bez poprawnej sygnatury binarnej."""
    token = login()

    response = client.post(
        "/api/upload",
        headers=auth_header(token),
        data={
            "file": (
                io.BytesIO(b"<?php echo 'not a png'; ?>"),
                "payload.php.png",
                "image/png",
            )
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert "sygnatura" in response.get_json()["error"]


def test_upload_rejects_fake_jpeg_signature(client, login):
    """Samo rozszerzenie JPEG również nie omija kontroli zawartości."""
    token = login()

    response = client.post(
        "/api/upload",
        headers=auth_header(token),
        data={
            "file": (
                io.BytesIO(b"this is plain text, not jpeg"),
                "zdjecie.jpg",
                "image/jpeg",
            )
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 400


def test_idor_user_cannot_read_another_users_document(client, login):
    jan_token = login("jan", "jan123")

    response = client.get(
        "/api/documents/doc2",
        headers=auth_header(jan_token),
    )

    assert response.status_code == 403


def test_idor_user_cannot_modify_another_users_document(client, login):
    jan_token = login("jan", "jan123")

    response = client.put(
        "/api/documents/doc2",
        headers=auth_header(jan_token),
        json={"title": "Przejęte", "content": "Nieautoryzowana zmiana"},
    )

    assert response.status_code == 403

    # Dodatkowa kontrola: właściciel nadal widzi oryginalną treść.
    kasia_token = login("kasia", "kasia123")
    check = client.get(
        "/api/documents/doc2",
        headers=auth_header(kasia_token),
    )

    assert check.status_code == 200
    assert check.get_json()["title"] == "Dokument Kasi"
    assert check.get_json()["content"] == "Tajne dane Kasi"


def test_owner_can_read_own_document(client, login):
    jan_token = login("jan", "jan123")

    response = client.get(
        "/api/documents/doc1",
        headers=auth_header(jan_token),
    )

    assert response.status_code == 200
    assert response.get_json()["owner"] == "jan"


def test_rate_limiting_blocks_after_failed_logins_and_sets_retry_after(client):
    """Po 5 błędnych próbach serwer blokuje klienta i zwraca Retry-After."""
    max_failures = application.app.config["LOGIN_MAX_FAILURES"]

    for attempt in range(1, max_failures):
        response = client.post(
            "/api/login",
            json={"username": "jan", "password": "zle-haslo"},
        )
        assert response.status_code == 401, f"Próba {attempt} powinna dać 401"

    blocked = client.post(
        "/api/login",
        json={"username": "jan", "password": "zle-haslo"},
    )

    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers
    assert int(blocked.headers["Retry-After"]) > 0

    # Nawet poprawne hasło pozostaje zablokowane w czasie aktywnej blokady.
    still_blocked = client.post(
        "/api/login",
        json={"username": "jan", "password": "jan123"},
    )

    assert still_blocked.status_code == 429
    assert int(still_blocked.headers["Retry-After"]) > 0

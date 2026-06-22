"""Pruebas del subsistema de autenticación: registro, login y perfil (/me)."""


def _register(client, username="alice", email="alice@example.com", password="secret123"):
    return client.post(
        "/auth/register",
        json={"username": username, "email": email, "password": password},
    )


def _login(client, email="alice@example.com", password="secret123"):
    return client.post("/auth/login", json={"email": email, "password": password})


# --- Registro ---------------------------------------------------------------

def test_register_success(client):
    r = _register(client)
    assert r.status_code == 201
    body = r.json()
    assert body["username"] == "alice"
    assert body["email"] == "alice@example.com"
    assert "id" in body
    assert "password" not in body  # el hash nunca se expone


def test_register_duplicate_email(client):
    assert _register(client, email="dup@example.com").status_code == 201
    r = _register(client, username="bob", email="dup@example.com")
    assert r.status_code == 400


def test_register_password_too_short(client):
    r = _register(client, password="123")
    assert r.status_code == 422  # validación de Pydantic (min_length=6)


def test_register_invalid_email(client):
    r = _register(client, email="not-an-email")
    assert r.status_code == 422


def test_register_username_too_short(client):
    r = _register(client, username="ab")
    assert r.status_code == 422  # min_length=3


# --- Login ------------------------------------------------------------------

def test_login_success(client):
    _register(client)
    r = _login(client)
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_wrong_password(client):
    _register(client)
    r = _login(client, password="wrongpassword")
    assert r.status_code == 401


def test_login_nonexistent_user(client):
    r = _login(client, email="ghost@example.com")
    assert r.status_code == 401


# --- Perfil (/me) -----------------------------------------------------------

def test_me_with_valid_token(client):
    _register(client)
    token = _login(client).json()["access_token"]
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == "alice@example.com"
    assert body["username"] == "alice"


def test_me_without_token(client):
    r = client.get("/auth/me")
    assert r.status_code == 401


def test_me_with_invalid_token(client):
    r = client.get("/auth/me", headers={"Authorization": "Bearer not.a.valid.token"})
    assert r.status_code == 401

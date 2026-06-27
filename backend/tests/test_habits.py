"""Pruebas del subsistema de hábitos: creación de un hábito (POST /habits)."""


def _auth_token(client, username="alice", email="alice@example.com", password="secret123"):
    client.post(
        "/auth/register",
        json={"username": username, "email": email, "password": password},
    )
    r = client.post("/auth/login", json={"email": email, "password": password})
    return r.json()["access_token"]


def _create_habit(client, token, name="Read", type="Study", importance=2):
    return client.post(
        "/habits",
        json={"name": name, "type": type, "importance": importance},
        headers={"Authorization": f"Bearer {token}"},
    )


# --- Creación ---------------------------------------------------------------

def test_create_habit_success(client):
    token = _auth_token(client)
    r = _create_habit(client, token, name="Read", type="Study", importance=2)
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "Read"
    assert body["type"] == "Study"
    assert body["importance"] == 2
    assert "id" in body
    assert "user_id" in body


def test_create_habit_type_optional(client):
    token = _auth_token(client)
    r = client.post(
        "/habits",
        json={"name": "Meditate", "importance": 1},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201
    assert r.json()["type"] is None


# --- Autenticación ----------------------------------------------------------

def test_create_habit_without_token(client):
    r = client.post("/habits", json={"name": "Read", "type": "Study", "importance": 2})
    assert r.status_code == 401


def test_create_habit_with_invalid_token(client):
    r = client.post(
        "/habits",
        json={"name": "Read", "type": "Study", "importance": 2},
        headers={"Authorization": "Bearer not.a.valid.token"},
    )
    assert r.status_code == 401


# --- Validación (Pydantic) --------------------------------------------------

def test_create_habit_missing_name(client):
    token = _auth_token(client)
    r = client.post(
        "/habits",
        json={"type": "Study", "importance": 2},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422


def test_create_habit_importance_out_of_range(client):
    token = _auth_token(client)
    r = _create_habit(client, token, importance=5)
    assert r.status_code == 422


# --- Listado (GET /habits) --------------------------------------------------

def test_list_habits_empty(client):
    token = _auth_token(client)
    r = client.get("/habits", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json() == []


def test_list_habits_returns_only_own(client):
    token = _auth_token(client)
    _create_habit(client, token, name="Read", importance=1)
    _create_habit(client, token, name="Run", importance=3)

    # Otro usuario con su propio hábito
    other = _auth_token(client, username="bob", email="bob@example.com")
    _create_habit(client, other, name="Bob habit", importance=2)

    r = client.get("/habits", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    names = [h["name"] for h in r.json()]
    assert names == ["Read", "Run"]  # solo los de alice, en orden de id


def test_list_habits_without_token(client):
    r = client.get("/habits")
    assert r.status_code == 401


# --- Obtener uno (GET /habits/{id}) -----------------------------------------

def test_get_habit_success(client):
    token = _auth_token(client)
    habit_id = _create_habit(client, token).json()["id"]
    r = client.get(f"/habits/{habit_id}", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["id"] == habit_id


def test_get_habit_not_found(client):
    token = _auth_token(client)
    r = client.get("/habits/999", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 404


def test_get_habit_of_another_user_is_404(client):
    token = _auth_token(client)
    habit_id = _create_habit(client, token).json()["id"]
    other = _auth_token(client, username="bob", email="bob@example.com")
    r = client.get(f"/habits/{habit_id}", headers={"Authorization": f"Bearer {other}"})
    assert r.status_code == 404


# --- Editar (PUT /habits/{id}) ----------------------------------------------

def test_update_habit_success(client):
    token = _auth_token(client)
    habit_id = _create_habit(client, token, name="Read", type="Study", importance=1).json()["id"]
    r = client.put(
        f"/habits/{habit_id}",
        json={"name": "Read more", "type": "Mindfulness", "importance": 3},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "Read more"
    assert body["type"] == "Mindfulness"
    assert body["importance"] == 3
    assert body["id"] == habit_id


def test_update_habit_of_another_user_is_404(client):
    token = _auth_token(client)
    habit_id = _create_habit(client, token).json()["id"]
    other = _auth_token(client, username="bob", email="bob@example.com")
    r = client.put(
        f"/habits/{habit_id}",
        json={"name": "Hacked", "type": "Other", "importance": 2},
        headers={"Authorization": f"Bearer {other}"},
    )
    assert r.status_code == 404


def test_update_habit_invalid_importance(client):
    token = _auth_token(client)
    habit_id = _create_habit(client, token).json()["id"]
    r = client.put(
        f"/habits/{habit_id}",
        json={"name": "Read", "type": "Study", "importance": 9},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422


# --- Borrar (DELETE /habits/{id}) -------------------------------------------

def test_delete_habit_success(client):
    token = _auth_token(client)
    habit_id = _create_habit(client, token).json()["id"]
    r = client.delete(f"/habits/{habit_id}", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 204
    # Ya no existe
    r2 = client.get(f"/habits/{habit_id}", headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 404


def test_delete_habit_of_another_user_is_404(client):
    token = _auth_token(client)
    habit_id = _create_habit(client, token).json()["id"]
    other = _auth_token(client, username="bob", email="bob@example.com")
    r = client.delete(f"/habits/{habit_id}", headers={"Authorization": f"Bearer {other}"})
    assert r.status_code == 404
    # Sigue existiendo para su dueño
    r2 = client.get(f"/habits/{habit_id}", headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 200

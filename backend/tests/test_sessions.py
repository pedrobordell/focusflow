"""Pruebas del subsistema de sesiones: creación en lote (POST /sessions) con recurrencia."""


def _auth_token(client, username="alice", email="alice@example.com", password="secret123"):
    client.post(
        "/auth/register",
        json={"username": username, "email": email, "password": password},
    )
    r = client.post("/auth/login", json={"email": email, "password": password})
    return r.json()["access_token"]


def _create_habit(client, token, name="Read", type="Study", importance=2):
    r = client.post(
        "/habits",
        json={"name": name, "type": type, "importance": importance},
        headers={"Authorization": f"Bearer {token}"},
    )
    return r.json()["id"]


def _post_sessions(client, token, habit_id, sessions):
    return client.post(
        "/sessions",
        json={"habit_id": habit_id, "sessions": sessions},
        headers={"Authorization": f"Bearer {token}"},
    )


# --- Creación ---------------------------------------------------------------

def test_create_single_session(client):
    token = _auth_token(client)
    habit_id = _create_habit(client, token)
    r = _post_sessions(client, token, habit_id, [
        {"date": "2026-07-01", "start_time": "10:00", "end_time": "11:30"},
    ])
    assert r.status_code == 201
    body = r.json()
    assert len(body) == 1
    assert body[0]["habit_id"] == habit_id
    assert body[0]["date"] == "2026-07-01"
    assert body[0]["start_time"] == "10:00:00"
    assert body[0]["end_time"] == "11:30:00"
    assert body[0]["completed"] is False
    assert "id" in body[0]


def test_create_weekly_recurrence(client):
    token = _auth_token(client)
    habit_id = _create_habit(client, token)
    # Miércoles 2026-07-01 hasta 2026-07-29 (inclusive) -> 1, 8, 15, 22, 29 = 5 sesiones.
    r = _post_sessions(client, token, habit_id, [
        {"date": "2026-07-01", "start_time": "10:00", "end_time": "11:30",
         "repeat_until": "2026-07-29"},
    ])
    assert r.status_code == 201
    body = r.json()
    assert len(body) == 5
    assert [s["date"] for s in body] == [
        "2026-07-01", "2026-07-08", "2026-07-15", "2026-07-22", "2026-07-29",
    ]
    assert all(s["start_time"] == "10:00:00" for s in body)


def test_recurrence_until_equals_date_creates_one(client):
    token = _auth_token(client)
    habit_id = _create_habit(client, token)
    r = _post_sessions(client, token, habit_id, [
        {"date": "2026-07-01", "start_time": "09:00", "end_time": "10:00",
         "repeat_until": "2026-07-01"},
    ])
    assert r.status_code == 201
    assert len(r.json()) == 1


def test_create_multiple_specs_in_one_request(client):
    token = _auth_token(client)
    habit_id = _create_habit(client, token)
    r = _post_sessions(client, token, habit_id, [
        {"date": "2026-07-01", "start_time": "10:00", "end_time": "11:00"},
        {"date": "2026-07-02", "start_time": "18:00", "end_time": "19:00",
         "repeat_until": "2026-07-16"},  # 2, 9, 16 = 3 sesiones
    ])
    assert r.status_code == 201
    assert len(r.json()) == 4  # 1 + 3


# --- Validación -------------------------------------------------------------

def test_end_time_not_after_start_time(client):
    token = _auth_token(client)
    habit_id = _create_habit(client, token)
    r = _post_sessions(client, token, habit_id, [
        {"date": "2026-07-01", "start_time": "11:00", "end_time": "10:00"},
    ])
    assert r.status_code == 422


def test_repeat_until_before_date(client):
    token = _auth_token(client)
    habit_id = _create_habit(client, token)
    r = _post_sessions(client, token, habit_id, [
        {"date": "2026-07-10", "start_time": "10:00", "end_time": "11:00",
         "repeat_until": "2026-07-03"},
    ])
    assert r.status_code == 422


def test_empty_sessions_list(client):
    token = _auth_token(client)
    habit_id = _create_habit(client, token)
    r = _post_sessions(client, token, habit_id, [])
    assert r.status_code == 422


# --- Propiedad --------------------------------------------------------------

def test_create_sessions_for_another_users_habit(client):
    alice = _auth_token(client)
    alice_habit = _create_habit(client, alice)
    bob = _auth_token(client, username="bob", email="bob@example.com")
    r = _post_sessions(client, bob, alice_habit, [
        {"date": "2026-07-01", "start_time": "10:00", "end_time": "11:00"},
    ])
    assert r.status_code == 404


def test_create_sessions_for_nonexistent_habit(client):
    token = _auth_token(client)
    r = _post_sessions(client, token, 9999, [
        {"date": "2026-07-01", "start_time": "10:00", "end_time": "11:00"},
    ])
    assert r.status_code == 404


# --- Autenticación ----------------------------------------------------------

def test_create_sessions_without_token(client):
    r = client.post("/sessions", json={
        "habit_id": 1,
        "sessions": [{"date": "2026-07-01", "start_time": "10:00", "end_time": "11:00"}],
    })
    assert r.status_code == 401


# --- Obtener una sesión -----------------------------------------------------

def _create_one_session(client, token, habit_id, date="2026-07-01", start="10:00", end="11:00"):
    r = _post_sessions(client, token, habit_id, [
        {"date": date, "start_time": start, "end_time": end},
    ])
    return r.json()[0]["id"]


def test_get_session_success(client):
    token = _auth_token(client)
    habit_id = _create_habit(client, token)
    session_id = _create_one_session(client, token, habit_id)
    r = client.get(f"/sessions/{session_id}", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == session_id
    assert body["habit_id"] == habit_id
    assert body["date"] == "2026-07-01"
    assert body["start_time"] == "10:00:00"
    assert body["end_time"] == "11:00:00"
    assert body["completed"] is False


def test_get_session_not_found(client):
    token = _auth_token(client)
    r = client.get("/sessions/9999", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 404


def test_get_session_of_another_user(client):
    alice = _auth_token(client)
    alice_habit = _create_habit(client, alice)
    session_id = _create_one_session(client, alice, alice_habit)
    bob = _auth_token(client, username="bob", email="bob@example.com")
    r = client.get(f"/sessions/{session_id}", headers={"Authorization": f"Bearer {bob}"})
    assert r.status_code == 404


# --- Editar una sesión ------------------------------------------------------

def test_update_session_success(client):
    token = _auth_token(client)
    habit_id = _create_habit(client, token)
    session_id = _create_one_session(client, token, habit_id)
    r = client.put(
        f"/sessions/{session_id}",
        json={"habit_id": habit_id, "date": "2026-07-05",
              "start_time": "15:00", "end_time": "16:30"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["date"] == "2026-07-05"
    assert body["start_time"] == "15:00:00"
    assert body["end_time"] == "16:30:00"
    # Persistido
    g = client.get(f"/sessions/{session_id}", headers={"Authorization": f"Bearer {token}"})
    assert g.json()["start_time"] == "15:00:00"


def test_update_session_change_habit(client):
    token = _auth_token(client)
    habit_a = _create_habit(client, token, name="Read")
    habit_b = _create_habit(client, token, name="Run")
    session_id = _create_one_session(client, token, habit_a)
    r = client.put(
        f"/sessions/{session_id}",
        json={"habit_id": habit_b, "date": "2026-07-01",
              "start_time": "10:00", "end_time": "11:00"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["habit_id"] == habit_b


def test_update_session_to_another_users_habit(client):
    alice = _auth_token(client)
    alice_habit = _create_habit(client, alice)
    session_id = _create_one_session(client, alice, alice_habit)
    bob = _auth_token(client, username="bob", email="bob@example.com")
    bob_habit = _create_habit(client, bob)
    r = client.put(
        f"/sessions/{session_id}",
        json={"habit_id": bob_habit, "date": "2026-07-01",
              "start_time": "10:00", "end_time": "11:00"},
        headers={"Authorization": f"Bearer {alice}"},
    )
    assert r.status_code == 404


def test_update_session_of_another_user(client):
    alice = _auth_token(client)
    alice_habit = _create_habit(client, alice)
    session_id = _create_one_session(client, alice, alice_habit)
    bob = _auth_token(client, username="bob", email="bob@example.com")
    bob_habit = _create_habit(client, bob)
    r = client.put(
        f"/sessions/{session_id}",
        json={"habit_id": bob_habit, "date": "2026-07-01",
              "start_time": "10:00", "end_time": "11:00"},
        headers={"Authorization": f"Bearer {bob}"},
    )
    assert r.status_code == 404


def test_update_session_invalid_times(client):
    token = _auth_token(client)
    habit_id = _create_habit(client, token)
    session_id = _create_one_session(client, token, habit_id)
    r = client.put(
        f"/sessions/{session_id}",
        json={"habit_id": habit_id, "date": "2026-07-01",
              "start_time": "11:00", "end_time": "10:00"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422


def test_update_session_without_token(client):
    r = client.put("/sessions/1", json={
        "habit_id": 1, "date": "2026-07-01", "start_time": "10:00", "end_time": "11:00",
    })
    assert r.status_code == 401


# --- Listar por rango (GET /sessions?from=&to=) -----------------------------

def _list_sessions(client, token, date_from, date_to):
    return client.get(
        "/sessions",
        params={"from": date_from, "to": date_to},
        headers={"Authorization": f"Bearer {token}"},
    )


def test_list_sessions_in_range_ordered(client):
    token = _auth_token(client)
    habit_id = _create_habit(client, token)
    # Creadas en desorden y con una fuera del rango pedido.
    _post_sessions(client, token, habit_id, [
        {"date": "2026-07-10", "start_time": "09:00", "end_time": "10:00"},
        {"date": "2026-07-05", "start_time": "18:00", "end_time": "19:00"},
        {"date": "2026-07-05", "start_time": "08:00", "end_time": "09:00"},
        {"date": "2026-07-20", "start_time": "10:00", "end_time": "11:00"},  # fuera de rango
    ])
    r = _list_sessions(client, token, "2026-07-01", "2026-07-15")
    assert r.status_code == 200
    body = r.json()
    # Solo las 3 dentro del rango, ordenadas por fecha y luego por hora de inicio.
    assert [(s["date"], s["start_time"]) for s in body] == [
        ("2026-07-05", "08:00:00"),
        ("2026-07-05", "18:00:00"),
        ("2026-07-10", "09:00:00"),
    ]


def test_list_sessions_range_is_inclusive(client):
    token = _auth_token(client)
    habit_id = _create_habit(client, token)
    _post_sessions(client, token, habit_id, [
        {"date": "2026-07-01", "start_time": "10:00", "end_time": "11:00"},
        {"date": "2026-07-31", "start_time": "10:00", "end_time": "11:00"},
    ])
    r = _list_sessions(client, token, "2026-07-01", "2026-07-31")
    assert r.status_code == 200
    assert len(r.json()) == 2  # los extremos entran


def test_list_sessions_excludes_other_users(client):
    alice = _auth_token(client)
    alice_habit = _create_habit(client, alice)
    _post_sessions(client, alice, alice_habit, [
        {"date": "2026-07-05", "start_time": "10:00", "end_time": "11:00"},
    ])
    bob = _auth_token(client, username="bob", email="bob@example.com")
    bob_habit = _create_habit(client, bob)
    _post_sessions(client, bob, bob_habit, [
        {"date": "2026-07-05", "start_time": "12:00", "end_time": "13:00"},
    ])
    r = _list_sessions(client, bob, "2026-07-01", "2026-07-31")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["habit_id"] == bob_habit  # solo lo suyo


def test_list_sessions_empty_range(client):
    token = _auth_token(client)
    habit_id = _create_habit(client, token)
    _post_sessions(client, token, habit_id, [
        {"date": "2026-08-01", "start_time": "10:00", "end_time": "11:00"},
    ])
    r = _list_sessions(client, token, "2026-07-01", "2026-07-31")
    assert r.status_code == 200
    assert r.json() == []


def test_list_sessions_without_token(client):
    r = client.get("/sessions", params={"from": "2026-07-01", "to": "2026-07-31"})
    assert r.status_code == 401


def test_list_sessions_missing_params(client):
    token = _auth_token(client)
    r = client.get("/sessions", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 422


def test_list_sessions_invalid_date(client):
    token = _auth_token(client)
    r = client.get(
        "/sessions",
        params={"from": "not-a-date", "to": "2026-07-31"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422


# --- Borrar una sesión (DELETE /sessions/{id}) ------------------------------

def test_delete_session_success(client):
    token = _auth_token(client)
    habit_id = _create_habit(client, token)
    session_id = _create_one_session(client, token, habit_id)
    r = client.delete(f"/sessions/{session_id}", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 204
    # Ya no existe
    g = client.get(f"/sessions/{session_id}", headers={"Authorization": f"Bearer {token}"})
    assert g.status_code == 404


def test_delete_session_not_found(client):
    token = _auth_token(client)
    r = client.delete("/sessions/9999", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 404


def test_delete_session_of_another_user(client):
    alice = _auth_token(client)
    alice_habit = _create_habit(client, alice)
    session_id = _create_one_session(client, alice, alice_habit)
    bob = _auth_token(client, username="bob", email="bob@example.com")
    r = client.delete(f"/sessions/{session_id}", headers={"Authorization": f"Bearer {bob}"})
    assert r.status_code == 404
    # Sigue existiendo para su dueño
    g = client.get(f"/sessions/{session_id}", headers={"Authorization": f"Bearer {alice}"})
    assert g.status_code == 200


def test_delete_session_without_token(client):
    r = client.delete("/sessions/1")
    assert r.status_code == 401


# --- Sesiones que cruzan medianoche (end_date) ------------------------------

def test_create_same_day_defaults_end_date(client):
    token = _auth_token(client)
    habit_id = _create_habit(client, token)
    # Sin end_date -> por defecto end_date = date (misma jornada).
    r = _post_sessions(client, token, habit_id, [
        {"date": "2026-07-01", "start_time": "10:00", "end_time": "11:00"},
    ])
    assert r.status_code == 201
    assert r.json()[0]["end_date"] == "2026-07-01"


def test_create_overnight_session(client):
    token = _auth_token(client)
    habit_id = _create_habit(client, token)
    # Dormir 22:00 -> 07:00 del día siguiente.
    r = _post_sessions(client, token, habit_id, [
        {"date": "2026-07-01", "end_date": "2026-07-02",
         "start_time": "22:00", "end_time": "07:00"},
    ])
    assert r.status_code == 201
    body = r.json()
    assert len(body) == 1
    assert body[0]["date"] == "2026-07-01"
    assert body[0]["end_date"] == "2026-07-02"
    assert body[0]["start_time"] == "22:00:00"
    assert body[0]["end_time"] == "07:00:00"


def test_overnight_without_end_date_is_422(client):
    token = _auth_token(client)
    habit_id = _create_habit(client, token)
    # Sin end_date, end_date = date -> 07:00 <= 22:00 el mismo día -> inválido.
    r = _post_sessions(client, token, habit_id, [
        {"date": "2026-07-01", "start_time": "22:00", "end_time": "07:00"},
    ])
    assert r.status_code == 422


def test_overnight_recurrence_shifts_end_date(client):
    token = _auth_token(client)
    habit_id = _create_habit(client, token)
    r = _post_sessions(client, token, habit_id, [
        {"date": "2026-07-01", "end_date": "2026-07-02",
         "start_time": "22:00", "end_time": "07:00",
         "repeat_until": "2026-07-15"},
    ])
    assert r.status_code == 201
    body = r.json()
    assert [s["date"] for s in body] == ["2026-07-01", "2026-07-08", "2026-07-15"]
    assert [s["end_date"] for s in body] == ["2026-07-02", "2026-07-09", "2026-07-16"]


def test_update_session_to_overnight(client):
    token = _auth_token(client)
    habit_id = _create_habit(client, token)
    session_id = _create_one_session(client, token, habit_id)  # mismo día 10:00-11:00
    r = client.put(
        f"/sessions/{session_id}",
        json={"habit_id": habit_id, "date": "2026-07-01", "end_date": "2026-07-02",
              "start_time": "22:00", "end_time": "07:00"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["end_date"] == "2026-07-02"
    assert body["start_time"] == "22:00:00"
    assert body["end_time"] == "07:00:00"

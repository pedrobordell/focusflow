"""Pruebas del subsistema de Estadísticas (GET /statistics/...) y del tracking
de cumplimiento (PATCH /sessions/{id})."""


def _auth_token(client, username="alice", email="alice@example.com", password="secret123"):
    client.post(
        "/auth/register",
        json={"username": username, "email": email, "password": password},
    )
    r = client.post("/auth/login", json={"email": email, "password": password})
    return r.json()["access_token"]


def _create_habit(client, token, name="Read", type="Study", importance=2, color="#3f8ae0"):
    r = client.post(
        "/habits",
        json={"name": name, "type": type, "importance": importance, "color": color},
        headers={"Authorization": f"Bearer {token}"},
    )
    return r.json()["id"]


def _post_sessions(client, token, habit_id, sessions):
    return client.post(
        "/sessions",
        json={"habit_id": habit_id, "sessions": sessions},
        headers={"Authorization": f"Bearer {token}"},
    )


def _set_completed(client, token, session_id, completed):
    return client.patch(
        f"/sessions/{session_id}",
        json={"completed": completed},
        headers={"Authorization": f"Bearer {token}"},
    )


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _summary(client, token, date_from, date_to):
    return client.get(
        "/statistics/summary",
        params={"from": date_from, "to": date_to},
        headers=_auth(token),
    )


# Crea, postea y marca cumplidas: devuelve la lista de sesiones creadas.
def _seed(client, token, habit_id, specs):
    created = _post_sessions(client, token, habit_id, [s[0] for s in specs]).json()
    for session, spec in zip(created, specs):
        if spec[1]:
            _set_completed(client, token, session["id"], True)
    return created


# --- Tracking: PATCH /sessions/{id} -----------------------------------------

def test_patch_marks_session_completed(client):
    token = _auth_token(client)
    habit_id = _create_habit(client, token)
    sid = _post_sessions(client, token, habit_id, [
        {"date": "2026-07-01", "start_time": "10:00", "end_time": "11:00"},
    ]).json()[0]["id"]
    r = _set_completed(client, token, sid, True)
    assert r.status_code == 200
    assert r.json()["completed"] is True
    g = client.get(f"/sessions/{sid}", headers=_auth(token))
    assert g.json()["completed"] is True
    r2 = _set_completed(client, token, sid, False)
    assert r2.status_code == 200
    assert r2.json()["completed"] is False


def test_patch_nonexistent_session(client):
    token = _auth_token(client)
    r = _set_completed(client, token, 9999, True)
    assert r.status_code == 404


def test_patch_session_of_another_user(client):
    alice = _auth_token(client)
    alice_habit = _create_habit(client, alice)
    sid = _post_sessions(client, alice, alice_habit, [
        {"date": "2026-07-01", "start_time": "10:00", "end_time": "11:00"},
    ]).json()[0]["id"]
    bob = _auth_token(client, username="bob", email="bob@example.com")
    r = _set_completed(client, bob, sid, True)
    assert r.status_code == 404


def test_patch_without_token(client):
    r = client.patch("/sessions/1", json={"completed": True})
    assert r.status_code == 401


# --- Summary: cumplimiento global (widget del dashboard) --------------------

def test_summary_without_token(client):
    r = client.get("/statistics/summary", params={"from": "2026-07-01", "to": "2026-07-31"})
    assert r.status_code == 401


def test_summary_missing_params(client):
    token = _auth_token(client)
    r = client.get("/statistics/summary", headers=_auth(token))
    assert r.status_code == 422


def test_summary_compliance_rate(client):
    token = _auth_token(client)
    habit_id = _create_habit(client, token)
    ids = _post_sessions(client, token, habit_id, [
        {"date": "2026-07-01", "start_time": "10:00", "end_time": "11:00"},
        {"date": "2026-07-02", "start_time": "10:00", "end_time": "11:00"},
        {"date": "2026-07-03", "start_time": "10:00", "end_time": "11:00"},
        {"date": "2026-07-04", "start_time": "10:00", "end_time": "11:00"},
    ]).json()
    for sid in [ids[0]["id"], ids[1]["id"], ids[2]["id"]]:
        _set_completed(client, token, sid, True)

    body = _summary(client, token, "2026-07-01", "2026-07-31").json()
    assert body["scheduled"] == 4
    assert body["completed"] == 3
    assert body["compliance_rate"] == 0.75
    # El summary ahora es mínimo: sin desglose por hábito ni rachas.
    assert "per_habit" not in body


def test_summary_empty_period_is_zero(client):
    token = _auth_token(client)
    habit_id = _create_habit(client, token)
    _post_sessions(client, token, habit_id, [
        {"date": "2026-08-01", "start_time": "10:00", "end_time": "11:00"},
    ])
    body = _summary(client, token, "2026-07-01", "2026-07-31").json()
    assert body["scheduled"] == 0
    assert body["completed"] == 0
    assert body["compliance_rate"] == 0.0


def test_summary_excludes_other_users(client):
    alice = _auth_token(client)
    alice_habit = _create_habit(client, alice)
    sid = _post_sessions(client, alice, alice_habit, [
        {"date": "2026-07-05", "start_time": "10:00", "end_time": "11:00"},
    ]).json()[0]["id"]
    _set_completed(client, alice, sid, True)

    bob = _auth_token(client, username="bob", email="bob@example.com")
    body = _summary(client, bob, "2026-07-01", "2026-07-31").json()
    assert body["scheduled"] == 0
    assert body["compliance_rate"] == 0.0


# --- Weekly Stats: destacados de la semana ----------------------------------

def _weekly(client, token, ref):
    return client.get("/statistics/weekly", params={"ref": ref}, headers=_auth(token))


def test_weekly_highlights(client):
    token = _auth_token(client)
    read = _create_habit(client, token, name="Read")
    gym = _create_habit(client, token, name="Gym")

    # Semana ISO de ref=2026-07-15 (miércoles): lunes 2026-07-13, domingo 2026-07-19.
    # Read: 2 sesiones de 2h, ambas cumplidas -> 4h, 100%.
    _seed(client, token, read, [
        ({"date": "2026-07-13", "start_time": "08:00", "end_time": "10:00"}, True),
        ({"date": "2026-07-14", "start_time": "08:00", "end_time": "10:00"}, True),
    ])
    # Gym: 2 sesiones de 1h, 1 cumplida -> 1h, 50%.
    _seed(client, token, gym, [
        ({"date": "2026-07-15", "start_time": "20:00", "end_time": "21:00"}, True),
        ({"date": "2026-07-16", "start_time": "20:00", "end_time": "21:00"}, False),
    ])
    # Semana anterior (2026-07-06..12): Read 2 sesiones, 1 cumplida -> 50% global previo.
    _seed(client, token, read, [
        ({"date": "2026-07-06", "start_time": "08:00", "end_time": "10:00"}, True),
        ({"date": "2026-07-07", "start_time": "08:00", "end_time": "10:00"}, False),
    ])

    body = _weekly(client, token, "2026-07-15").json()
    assert body["week_from"] == "2026-07-13"
    assert body["week_to"] == "2026-07-19"

    assert body["most_hours"]["habit_name"] == "Read"
    assert body["most_hours"]["completed_hours"] == 4.0
    assert body["most_hours"]["compliance_rate"] == 1.0

    assert body["worst_compliance"]["habit_name"] == "Gym"
    assert body["worst_compliance"]["compliance_rate"] == 0.5

    assert body["compliance_now"] == 0.75      # 3 de 4 esta semana
    assert body["compliance_prev"] == 0.5      # 1 de 2 la anterior
    assert body["improvement_pp"] == 25.0


def test_weekly_empty(client):
    token = _auth_token(client)
    body = _weekly(client, token, "2026-07-15").json()
    assert body["most_hours"] is None
    assert body["worst_compliance"] is None
    assert body["compliance_now"] == 0.0
    assert body["compliance_prev"] == 0.0
    assert body["improvement_pp"] == 0.0


def test_weekly_without_token(client):
    r = client.get("/statistics/weekly", params={"ref": "2026-07-15"})
    assert r.status_code == 401


# --- Habit Stats: detalle de un hábito --------------------------------------

def _habit_detail(client, token, habit_id, date_from, date_to):
    return client.get(
        f"/statistics/habit/{habit_id}",
        params={"from": date_from, "to": date_to},
        headers=_auth(token),
    )


def test_habit_detail(client):
    token = _auth_token(client)
    habit_id = _create_habit(client, token, name="Read", type="Study", importance=3)
    # 3 sesiones de mañana (08:00, franja Morning) cumplidas + 1 de tarde-noche (20:00) sin cumplir.
    _seed(client, token, habit_id, [
        ({"date": "2026-07-01", "start_time": "08:00", "end_time": "09:00"}, True),
        ({"date": "2026-07-02", "start_time": "08:00", "end_time": "09:00"}, True),
        ({"date": "2026-07-03", "start_time": "08:00", "end_time": "09:00"}, True),
        ({"date": "2026-07-04", "start_time": "20:00", "end_time": "21:00"}, False),
    ])
    body = _habit_detail(client, token, habit_id, "2026-07-01", "2026-07-31").json()
    assert body["habit_name"] == "Read"
    assert body["type"] == "Study"
    assert body["importance"] == 3
    assert body["last10_count"] == 4
    assert body["last10_rate"] == 0.75         # 3 de 4
    assert body["best_slot"] == "Morning"      # 100% mañana vs 0% noche


def test_habit_detail_not_found(client):
    token = _auth_token(client)
    r = _habit_detail(client, token, 9999, "2026-07-01", "2026-07-31")
    assert r.status_code == 404


def test_habit_detail_other_user(client):
    alice = _auth_token(client)
    alice_habit = _create_habit(client, alice)
    bob = _auth_token(client, username="bob", email="bob@example.com")
    r = _habit_detail(client, bob, alice_habit, "2026-07-01", "2026-07-31")
    assert r.status_code == 404


def test_habit_detail_without_token(client):
    r = client.get("/statistics/habit/1", params={"from": "2026-07-01", "to": "2026-07-31"})
    assert r.status_code == 401


# --- Gráficas (PNG) ---------------------------------------------------------

def test_daily_chart_returns_png(client):
    token = _auth_token(client)
    habit_id = _create_habit(client, token)
    _seed(client, token, habit_id, [
        ({"date": "2026-07-06", "start_time": "08:00", "end_time": "09:00"}, True),
    ])
    r = client.get(
        "/statistics/daily-chart",
        params={"from": "2026-07-01", "to": "2026-07-31"},
        headers=_auth(token),
    )
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
    assert len(r.content) > 0


def test_daily_chart_without_token(client):
    r = client.get("/statistics/daily-chart", params={"from": "2026-07-01", "to": "2026-07-31"})
    assert r.status_code == 401


def test_hourly_chart_returns_png(client):
    token = _auth_token(client)
    habit_id = _create_habit(client, token)
    _seed(client, token, habit_id, [
        ({"date": "2026-07-06", "start_time": "08:00", "end_time": "09:00"}, True),
    ])
    r = client.get(
        f"/statistics/habit/{habit_id}/hourly-chart",
        params={"from": "2026-07-01", "to": "2026-07-31"},
        headers=_auth(token),
    )
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
    assert len(r.content) > 0


def test_hourly_chart_other_user(client):
    alice = _auth_token(client)
    alice_habit = _create_habit(client, alice)
    bob = _auth_token(client, username="bob", email="bob@example.com")
    r = client.get(
        f"/statistics/habit/{alice_habit}/hourly-chart",
        params={"from": "2026-07-01", "to": "2026-07-31"},
        headers=_auth(bob),
    )
    assert r.status_code == 404


def test_hourly_chart_without_token(client):
    r = client.get("/statistics/habit/1/hourly-chart", params={"from": "2026-07-01", "to": "2026-07-31"})
    assert r.status_code == 401

"""Pruebas del subsistema de Recomendaciones y Mensajes.

Dos bloques bien diferenciados:

1. UNITARIOS de la estrategia: se construyen HabitContext a mano y se comprueba qué mensajes
   produce cada regla. No hace falta ni base de datos ni TestClient, y esa es justamente la
   ventaja de que la estrategia sea pura.
2. INTEGRACIÓN de los endpoints, con TestClient. Las fechas se siembran RELATIVAS a
   date.today() (y no fijas como en el resto de la suite) porque las reglas miran "los últimos
   30 días" y "hace 14 días": con fechas fijas los tests caducarían.
"""

from datetime import date, timedelta

from schemas.recommendation_schema import HabitContext
from schemas.statistics_schema import SlotStat
from services.recommendation_rules import (
    FORGOTTEN_DAYS,
    MIN_WINDOW_SESSIONS,
    STREAK_MIN,
    RulesRecommendationStrategy,
)
from services.statistics_service import MIN_SLOT_SESSIONS, StatisticsService


# --- Utilidades de los tests unitarios --------------------------------------

def _slot(slot, label, scheduled, completed):
    rate = completed / scheduled if scheduled else 0.0
    return SlotStat(
        slot=slot,
        label=label,
        scheduled=scheduled,
        completed=completed,
        compliance_rate=round(rate, 4),
        probability=round((completed + 1) / (scheduled + 2), 4),
    )


# Contexto con valores por defecto "sanos": un hábito normal sin nada que señalar.
def _context(**overrides):
    base = dict(
        habit_id=1,
        habit_name="Reading",
        importance=2,
        analysis_days=30,
        scheduled=10,
        completed=8,
        compliance_rate=0.8,
        days_since_last_completed=0,
        days_since_last_session=0,
        current_streak=0,
        ever_scheduled=True,
        slots=[],
        best_slot=None,
    )
    base.update(overrides)
    return HabitContext(**base)


def _generate(contexts):
    return RulesRecommendationStrategy().generate(contexts)


def _titles(recommendations):
    return [r.title for r in recommendations]


# --- Unitarios: regla 1 (hábito prioritario + franja) -----------------------

def test_priority_picks_highest_importance_times_failure():
    # Gym: 3 x (1 - 0.2) = 2.4  gana a  Reading: 1 x (1 - 0.1) = 0.9
    contexts = [
        _context(habit_id=1, habit_name="Reading", importance=1, compliance_rate=0.1),
        _context(habit_id=2, habit_name="Gym", importance=3, compliance_rate=0.2),
    ]
    recommendations = _generate(contexts)
    assert recommendations[0].type == "recommendation"
    assert recommendations[0].title == "Focus on Gym"


def test_priority_ignores_habits_with_too_little_history():
    # El de puntuación más alta apenas tiene sesiones en la ventana: un 0% sacado de una o dos
    # sesiones no es motivo suficiente para convertirlo en la recomendación del día.
    contexts = [
        _context(habit_id=1, habit_name="Reading", importance=3, compliance_rate=0.0,
                 scheduled=MIN_WINDOW_SESSIONS - 1),
        _context(habit_id=2, habit_name="Gym", importance=1, compliance_rate=0.5, scheduled=8),
    ]
    assert _generate(contexts)[0].title == "Focus on Gym"


def test_no_recommendation_when_no_habit_has_enough_history():
    contexts = [_context(scheduled=MIN_WINDOW_SESSIONS - 1, completed=0, compliance_rate=0.0)]
    assert not any(r.type == "recommendation" for r in _generate(contexts))


def test_priority_is_deterministic_on_ties():
    # Misma puntuación e importancia: gana el id más bajo (mensaje estable entre recargas).
    contexts = [
        _context(habit_id=7, habit_name="Gym", importance=2, compliance_rate=0.5),
        _context(habit_id=3, habit_name="Reading", importance=2, compliance_rate=0.5),
    ]
    assert _generate(contexts)[0].title == "Focus on Reading"


def test_priority_changes_tone_at_full_compliance():
    contexts = [_context(habit_name="Reading", compliance_rate=1.0)]
    assert _generate(contexts)[0].title == "Keep the pace with Reading"


def test_no_recommendation_without_any_history():
    # Usuario con hábitos pero sin sesiones: el sistema no se inventa consejos.
    contexts = [_context(scheduled=0, completed=0, compliance_rate=0.0, ever_scheduled=False)]
    recommendations = _generate(contexts)
    assert not any(r.type == "recommendation" for r in recommendations)


def test_recommendation_proposes_the_best_slot():
    best = _slot(1, "Morning", scheduled=8, completed=7)        # prob 0.8
    worst = _slot(3, "Evening", scheduled=6, completed=2)       # prob 0.375
    contexts = [_context(compliance_rate=0.5, slots=[best, worst], best_slot=best)]
    content = _generate(contexts)[0].content
    assert "Morning" in content
    assert "80%" in content
    assert "Evening" not in content


def test_recommendation_admits_when_there_is_not_enough_data():
    # Sin franja fiable NO se propone horario: se dice que faltan datos.
    contexts = [_context(compliance_rate=0.5, slots=[_slot(1, "Morning", 1, 1)], best_slot=None)]
    content = _generate(contexts)[0].content
    assert "not enough sessions" in content
    assert "Morning" not in content


# --- Unitarios: la probabilidad suavizada (Laplace) -------------------------

def test_laplace_smoothing_avoids_certainty_from_one_session():
    # 1 de 1 no es 100%, es (1+1)/(1+2) = 67%. Es el caso que motivó el suavizado.
    stats = StatisticsService.best_slot([_slot(1, "Morning", scheduled=1, completed=1)])
    assert stats is None                                    # además no llega al mínimo

    single = _slot(1, "Morning", scheduled=1, completed=1)
    assert single.compliance_rate == 1.0
    assert single.probability == 0.6667


def test_best_slot_requires_a_minimum_number_of_sessions():
    poor = _slot(0, "Early morning", scheduled=MIN_SLOT_SESSIONS - 1, completed=MIN_SLOT_SESSIONS - 1)
    solid = _slot(2, "Afternoon", scheduled=10, completed=6)
    # La franja perfecta pero con poca muestra se descarta; gana la que tiene histórico.
    assert StatisticsService.best_slot([poor, solid]).label == "Afternoon"
    assert StatisticsService.best_slot([poor]) is None
    assert StatisticsService.best_slot([]) is None


# --- Unitarios: regla 2 (hábitos olvidados) ---------------------------------

def test_forgotten_habit_after_the_threshold():
    contexts = [_context(
        habit_name="Gym",
        days_since_last_completed=FORGOTTEN_DAYS + 6,
        days_since_last_session=FORGOTTEN_DAYS + 6,
    )]
    forgotten = [r for r in _generate(contexts) if r.title == "You're forgetting Gym"]
    assert len(forgotten) == 1
    assert f"in {FORGOTTEN_DAYS + 6} days" in forgotten[0].content
    assert forgotten[0].type == "notification"


def test_habit_completed_recently_is_not_forgotten():
    contexts = [_context(habit_name="Gym", days_since_last_completed=FORGOTTEN_DAYS - 1)]
    assert "You're forgetting Gym" not in _titles(_generate(contexts))


def test_never_completed_habit_is_reported_with_its_own_wording():
    contexts = [_context(
        habit_name="Gym",
        days_since_last_completed=None,
        days_since_last_session=20,
        compliance_rate=0.0,
    )]
    forgotten = [r for r in _generate(contexts) if r.title == "You're forgetting Gym"][0]
    assert "never completed" in forgotten.content
    assert "20 days ago" in forgotten.content


def test_habit_scheduled_only_in_the_future_is_not_forgotten():
    # Sin ninguna sesión pasada no se puede haber "olvidado" nada todavía.
    contexts = [_context(
        habit_name="Gym",
        scheduled=0,
        days_since_last_completed=None,
        days_since_last_session=None,
    )]
    assert "You're forgetting Gym" not in _titles(_generate(contexts))


def test_habit_without_any_session_gets_its_own_notice():
    contexts = [_context(
        habit_name="Gym",
        scheduled=0,
        completed=0,
        compliance_rate=0.0,
        ever_scheduled=False,
        days_since_last_completed=None,
        days_since_last_session=None,
    )]
    assert "You have not scheduled Gym yet" in _titles(_generate(contexts))


def test_forgotten_habits_come_sorted_by_how_long_they_have_been_ignored():
    contexts = [
        _context(habit_id=1, habit_name="Reading", days_since_last_completed=FORGOTTEN_DAYS + 1,
                 days_since_last_session=FORGOTTEN_DAYS + 1),
        _context(habit_id=2, habit_name="Gym", days_since_last_completed=FORGOTTEN_DAYS + 30,
                 days_since_last_session=FORGOTTEN_DAYS + 30),
    ]
    forgotten = [t for t in _titles(_generate(contexts)) if t.startswith("You're forgetting")]
    assert forgotten == ["You're forgetting Gym", "You're forgetting Reading"]


# --- Unitarios: regla 3 (rachas) --------------------------------------------

def test_streak_is_celebrated_from_the_threshold():
    contexts = [_context(habit_name="Reading", current_streak=STREAK_MIN)]
    streaks = [r for r in _generate(contexts) if "streak" in r.title]
    assert streaks[0].title == f"{STREAK_MIN}-session streak on Reading"
    assert streaks[0].type == "notification"


def test_short_streak_is_not_celebrated():
    contexts = [_context(habit_name="Reading", current_streak=STREAK_MIN - 1)]
    assert not any("streak" in t for t in _titles(_generate(contexts)))


def test_recommendation_comes_before_the_notifications():
    contexts = [_context(
        habit_name="Reading",
        compliance_rate=0.5,
        current_streak=5,
        days_since_last_completed=FORGOTTEN_DAYS + 1,
        days_since_last_session=FORGOTTEN_DAYS + 1,
    )]
    recommendations = _generate(contexts)
    assert recommendations[0].type == "recommendation"
    assert [r.type for r in recommendations[1:]] == ["notification", "notification"]


# --- Integración: helpers ----------------------------------------------------

def _auth_token(client, username="alice", email="alice@example.com", password="secret123"):
    client.post(
        "/auth/register",
        json={"username": username, "email": email, "password": password},
    )
    r = client.post("/auth/login", json={"email": email, "password": password})
    return r.json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _create_habit(client, token, name="Read", type="Study", importance=2, color="#3f8ae0"):
    r = client.post(
        "/habits",
        json={"name": name, "type": type, "importance": importance, "color": "#3f8ae0"},
        headers=_auth(token),
    )
    return r.json()["id"]


def _day(offset):
    """Fecha a 'offset' días de hoy, en el formato de la API."""
    return (date.today() + timedelta(days=offset)).isoformat()


# Crea sesiones de un hábito y marca cumplidas las que toque.
# 'specs' son tuplas (días de desfase respecto a hoy, hora de inicio, cumplida).
# Cada sesión dura 1 hora.
def _seed(client, token, habit_id, specs):
    created = client.post(
        "/sessions",
        json={
            "habit_id": habit_id,
            "sessions": [
                {
                    "date": _day(offset),
                    "start_time": f"{hour:02d}:00",
                    "end_time": f"{hour + 1:02d}:00",
                }
                for offset, hour, _ in specs
            ],
        },
        headers=_auth(token),
    ).json()
    for session, spec in zip(created, specs):
        if spec[2]:
            client.patch(
                f"/sessions/{session['id']}",
                json={"completed": True},
                headers=_auth(token),
            )
    return created


def _generate_messages(client, token):
    return client.post("/recommendations/generate", headers=_auth(token))


def _list_messages(client, token):
    return client.get("/messages", headers=_auth(token))


# --- Integración: generación -------------------------------------------------

def test_generate_without_token(client):
    assert client.post("/recommendations/generate").status_code == 401


def test_generate_with_no_habits_creates_nothing(client):
    token = _auth_token(client)
    r = _generate_messages(client, token)
    assert r.status_code == 200
    assert r.json() == []


def test_generate_creates_a_recommendation_from_the_history(client):
    token = _auth_token(client)
    habit_id = _create_habit(client, token, name="Read", importance=3)
    # 4 sesiones de mañana (2 cumplidas) y 4 de noche (ninguna): la mañana es su mejor franja.
    _seed(client, token, habit_id, [
        (-10, 8, True), (-9, 8, True), (-8, 8, False), (-7, 8, False),
        (-6, 22, False), (-5, 22, False), (-4, 22, False), (-3, 22, False),
    ])

    body = _generate_messages(client, token).json()
    recommendations = [m for m in body if m["type"] == "recommendation"]
    assert len(recommendations) == 1
    assert recommendations[0]["title"] == "Focus on Read"
    assert "Morning" in recommendations[0]["content"]
    assert recommendations[0]["is_read"] is False
    # Dentro de una misma generación se conserva el orden de relevancia: la propuesta
    # va primero y los avisos después.
    assert body[0]["type"] == "recommendation"


def test_generate_is_idempotent(client):
    token = _auth_token(client)
    habit_id = _create_habit(client, token)
    _seed(client, token, habit_id, [(-3, 8, True), (-2, 8, False), (-1, 8, True)])

    first = _generate_messages(client, token).json()
    second = _generate_messages(client, token).json()
    assert len(first) > 0
    # Volver a generar no duplica: el dedupe compara títulos ya creados hoy.
    assert [m["id"] for m in first] == [m["id"] for m in second]
    assert len(_list_messages(client, token).json()) == len(first)


def test_generate_detects_a_forgotten_habit(client):
    token = _auth_token(client)
    habit_id = _create_habit(client, token, name="Gym")
    _seed(client, token, habit_id, [(-(FORGOTTEN_DAYS + 5), 19, False)])

    titles = [m["title"] for m in _generate_messages(client, token).json()]
    assert "You're forgetting Gym" in titles


def test_generate_detects_a_streak(client):
    token = _auth_token(client)
    habit_id = _create_habit(client, token, name="Read")
    _seed(client, token, habit_id, [(-3, 8, True), (-2, 8, True), (-1, 8, True)])

    titles = [m["title"] for m in _generate_messages(client, token).json()]
    assert "3-session streak on Read" in titles


def test_generate_warns_about_a_habit_without_sessions(client):
    token = _auth_token(client)
    _create_habit(client, token, name="Meditate")
    titles = [m["title"] for m in _generate_messages(client, token).json()]
    assert "You have not scheduled Meditate yet" in titles


def test_future_sessions_do_not_count_as_failures(client):
    token = _auth_token(client)
    habit_id = _create_habit(client, token, name="Read")
    # Todo lo pasado está cumplido; lo de la semana que viene todavía no ha llegado.
    _seed(client, token, habit_id, [
        (-3, 8, True), (-2, 8, True), (-1, 8, True), (3, 8, False), (4, 8, False),
    ])
    body = _generate_messages(client, token).json()
    recommendation = [m for m in body if m["type"] == "recommendation"][0]
    # Si las futuras contaran, el cumplimiento sería 50% y el tono sería "Focus on".
    assert recommendation["title"] == "Keep the pace with Read"
    assert "100%" in recommendation["content"]


# --- Integración: bandeja de mensajes ---------------------------------------

def test_list_messages_without_token(client):
    assert client.get("/messages").status_code == 401


def test_list_messages_is_empty_at_first(client):
    token = _auth_token(client)
    assert _list_messages(client, token).json() == []


def test_list_messages_excludes_other_users(client):
    alice = _auth_token(client)
    _create_habit(client, alice, name="Read")
    _generate_messages(client, alice)

    bob = _auth_token(client, username="bob", email="bob@example.com")
    assert _list_messages(client, bob).json() == []


def test_list_messages_is_sorted_by_date_descending(client):
    token = _auth_token(client)
    _create_habit(client, token, name="Read")
    _create_habit(client, token, name="Gym")
    _generate_messages(client, token)

    messages = _list_messages(client, token).json()
    assert len(messages) >= 2
    dates = [m["created_at"] for m in messages]
    assert dates == sorted(dates, reverse=True)


def test_patch_marks_a_message_as_read(client):
    token = _auth_token(client)
    _create_habit(client, token, name="Read")
    message_id = _generate_messages(client, token).json()[0]["id"]

    r = client.patch(f"/messages/{message_id}", json={"is_read": True}, headers=_auth(token))
    assert r.status_code == 200
    assert r.json()["is_read"] is True
    assert _list_messages(client, token).json()[0]["is_read"] is True

    r2 = client.patch(f"/messages/{message_id}", json={"is_read": False}, headers=_auth(token))
    assert r2.json()["is_read"] is False


def test_patch_nonexistent_message(client):
    token = _auth_token(client)
    r = client.patch("/messages/9999", json={"is_read": True}, headers=_auth(token))
    assert r.status_code == 404


def test_patch_message_of_another_user(client):
    alice = _auth_token(client)
    _create_habit(client, alice, name="Read")
    message_id = _generate_messages(client, alice).json()[0]["id"]

    bob = _auth_token(client, username="bob", email="bob@example.com")
    r = client.patch(f"/messages/{message_id}", json={"is_read": True}, headers=_auth(bob))
    assert r.status_code == 404


def test_patch_message_without_token(client):
    assert client.patch("/messages/1", json={"is_read": True}).status_code == 401


def test_delete_message(client):
    token = _auth_token(client)
    _create_habit(client, token, name="Read")
    messages = _generate_messages(client, token).json()
    message_id = messages[0]["id"]

    r = client.delete(f"/messages/{message_id}", headers=_auth(token))
    assert r.status_code == 204
    assert len(_list_messages(client, token).json()) == len(messages) - 1


def test_delete_message_of_another_user(client):
    alice = _auth_token(client)
    _create_habit(client, alice, name="Read")
    message_id = _generate_messages(client, alice).json()[0]["id"]

    bob = _auth_token(client, username="bob", email="bob@example.com")
    assert client.delete(f"/messages/{message_id}", headers=_auth(bob)).status_code == 404


def test_delete_message_without_token(client):
    assert client.delete("/messages/1").status_code == 401

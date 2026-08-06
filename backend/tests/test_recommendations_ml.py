"""Pruebas de la estrategia con MODELOS LIGEROS (RF16).

Continúan a test_recommendations.py y mantienen su misma estructura:

1. UNITARIOS de la estrategia, construyendo HabitContext a mano. Sin base de datos y sin
   TestClient: la estrategia es pura y se puede probar en aislamiento, modelo incluido.
2. INTEGRACIÓN de los endpoints nuevos con TestClient.

Lo que más se prueba aquí no es que el árbol acierte (con un puñado de sesiones eso no se
puede exigir), sino que el sistema se comporte con PRUDENCIA: que sepa cuándo NO tiene datos
suficientes, que no se contradiga y que no pierda por el camino los avisos de RF15.
"""

from datetime import date, timedelta

from schemas.recommendation_schema import HabitContext, SessionFeature
from services.recommendation_ml import (
    MIN_TRAINING_SESSIONS,
    STATE_ABANDONED,
    STATE_AT_RISK,
    STATE_IMPROVING,
    STATE_ON_TRACK,
    STATE_UNKNOWN,
    MLRecommendationStrategy,
    train_tree,
    trend,
)
from services.recommendation_rules import FORGOTTEN_DAYS, STREAK_MIN, RulesRecommendationStrategy


# --- Utilidades de los tests unitarios --------------------------------------

def _strategy():
    return MLRecommendationStrategy(fallback=RulesRecommendationStrategy())


def _session(slot=1, weekday=0, completed=True, day_index=0, duration=60.0):
    return SessionFeature(
        slot=slot,
        weekday=weekday,
        duration=duration,
        completed=completed,
        day_index=day_index,
    )


# Serie de sesiones alternando franja: las de la mañana (slot 1) se cumplen y las de la noche
# (slot 3) no. Es un patrón que el árbol puede aprender, y con 'count' se decide si hay
# suficientes filas para que llegue a entrenarse.
def _learnable_sessions(count=30):
    sessions = []
    for index in range(count):
        morning = index % 2 == 0
        sessions.append(_session(
            slot=1 if morning else 3,
            weekday=index % 7,
            completed=morning,
            day_index=index,
        ))
    return sessions


# Contexto con valores por defecto "sanos", igual que en test_recommendations.py pero con la
# lista de sesiones que necesita el modelo.
def _context(**overrides):
    sessions = overrides.pop("sessions", None)
    if sessions is None:
        sessions = _learnable_sessions()

    completed = sum(1 for session in sessions if session.completed)
    base = dict(
        habit_id=1,
        habit_name="Reading",
        importance=2,
        analysis_days=30,
        scheduled=len(sessions),
        completed=completed,
        compliance_rate=round(completed / len(sessions), 4) if sessions else 0.0,
        days_since_last_completed=0,
        days_since_last_session=0,
        current_streak=0,
        ever_scheduled=bool(sessions),
        slots=[],
        best_slot=None,
        sessions=sessions,
    )
    base.update(overrides)
    return HabitContext(**base)


def _titles(recommendations):
    return [r.title for r in recommendations]


def _recommendations(messages):
    return [m for m in messages if m.type == "recommendation"]


# --- Unitarios: cuándo NO se entrena ----------------------------------------

def test_too_few_sessions_does_not_train():
    contexts = [_context(sessions=_learnable_sessions(MIN_TRAINING_SESSIONS - 1))]
    assert train_tree(contexts) is None


def test_enough_sessions_trains():
    assert train_tree([_context()]) is not None


def test_a_single_label_class_does_not_train():
    # Un hábito que SIEMPRE se cumple es un caso normal, no una rareza. Si se entrenara,
    # predict_proba devolvería una sola columna y leer la segunda daría IndexError.
    always = [_session(slot=index % 4, weekday=index % 7, completed=True, day_index=index)
              for index in range(30)]
    assert train_tree([_context(sessions=always)]) is None


def test_cold_start_falls_back_to_the_rules():
    # Sin modelo la estrategia no se calla: delega en las reglas, que sí saben con pocos datos.
    contexts = [_context(sessions=_learnable_sessions(4), compliance_rate=0.5, scheduled=4)]
    messages = _strategy().generate(contexts)
    assert _titles(messages) == _titles(RulesRecommendationStrategy().generate(contexts))


def test_no_habits_produces_nothing():
    assert _strategy().generate([]) == []


# --- Unitarios: determinismo -------------------------------------------------

def test_two_runs_produce_the_same_titles():
    # La semilla del árbol está fijada precisamente por esto: los mensajes se deduplican por
    # (usuario, título, día), así que un modelo que variara crearía duplicados cada vez que
    # se abre el dashboard.
    contexts = [_context()]
    assert _titles(_strategy().generate(contexts)) == _titles(_strategy().generate(contexts))


# --- Unitarios: RF15 sigue vivo con el modelo activo -------------------------

def test_forgotten_and_streak_notifications_survive():
    # Si la estrategia con modelo sustituyera a la de reglas en lugar de componerla, estos
    # avisos desaparecerían y se incumpliría RF15.
    target = _context(habit_id=1, habit_name="Study")
    forgotten = _context(
        habit_id=2,
        habit_name="Gym",
        days_since_last_completed=FORGOTTEN_DAYS + 5,
        sessions=_learnable_sessions(24),
    )
    on_streak = _context(habit_id=3, habit_name="Read", current_streak=STREAK_MIN + 2)

    titles = _titles(_strategy().generate([target, forgotten, on_streak]))
    assert any("forgetting Gym" in title for title in titles)
    assert any("streak on Read" in title for title in titles)


def test_the_recommendation_comes_before_the_notifications():
    contexts = [_context(habit_id=1), _context(habit_id=2, habit_name="Gym",
                                               current_streak=STREAK_MIN + 1)]
    messages = _strategy().generate(contexts)
    assert messages[0].type == "recommendation"


def test_only_one_recommendation_is_produced():
    contexts = [_context(habit_id=index, habit_name=f"Habit {index}") for index in (1, 2, 3)]
    assert len(_recommendations(_strategy().generate(contexts))) == 1


# --- Unitarios: estados ------------------------------------------------------

def _state_of(context, contexts=None):
    contexts = contexts or [context]
    insights = _strategy().insights(contexts)
    return next(i for i in insights if i.habit_id == context.habit_id).state


def test_habit_without_sessions_is_unknown():
    # Sin sesiones no se diagnostica: se dice "no lo sé" en vez de inventar un 0%.
    empty = _context(habit_id=2, habit_name="New", sessions=[], ever_scheduled=False)
    assert _state_of(empty, [_context(habit_id=1), empty]) == STATE_UNKNOWN


def test_habit_idle_for_too_long_is_abandoned():
    idle = _context(habit_id=2, habit_name="Gym",
                    days_since_last_completed=FORGOTTEN_DAYS + 1)
    assert _state_of(idle, [_context(habit_id=1), idle]) == STATE_ABANDONED


def test_habit_never_completed_is_abandoned():
    never = _context(habit_id=2, habit_name="Gym", days_since_last_completed=None)
    assert _state_of(never, [_context(habit_id=1), never]) == STATE_ABANDONED


def test_reliable_habit_is_on_track():
    # Todas sus sesiones en la franja que el modelo asocia con cumplir.
    reliable = [_session(slot=1, weekday=index % 7, completed=True, day_index=index)
                for index in range(20)]
    context = _context(habit_id=2, habit_name="Read", sessions=reliable)
    assert _state_of(context, [_context(habit_id=1), context]) == STATE_ON_TRACK


def test_weak_habit_that_is_recovering_is_improving():
    # Franja mala (poca probabilidad) pero cumpliendo cada vez más: no es lo mismo que ir mal.
    recovering = [_session(slot=3, weekday=index % 7, completed=index >= 15, day_index=index)
                  for index in range(30)]
    context = _context(habit_id=2, habit_name="Study", sessions=recovering)
    assert _state_of(context, [_context(habit_id=1), context]) == STATE_IMPROVING


def test_weak_and_flat_habit_is_at_risk():
    weak = [_session(slot=3, weekday=index % 7, completed=False, day_index=index)
            for index in range(20)]
    context = _context(habit_id=2, habit_name="Study", sessions=weak)
    assert _state_of(context, [_context(habit_id=1), context]) == STATE_AT_RISK


# --- Unitarios: la propuesta -------------------------------------------------

def test_the_suggestion_can_be_a_combination_never_scheduled():
    # El valor que las reglas no dan: proponer una combinación que el usuario nunca ha
    # probado PARA ESE HÁBITO. Aquí Study solo se ha hecho de noche y en días laborables.
    evenings = [_session(slot=3, weekday=index % 5, completed=False, day_index=index)
                for index in range(20)]
    mornings = [_session(slot=1, weekday=5, completed=True, day_index=index)
                for index in range(20)]
    study = _context(habit_id=1, habit_name="Study", sessions=evenings)
    other = _context(habit_id=2, habit_name="Read", sessions=mornings)

    insight = next(i for i in _strategy().insights([study, other]) if i.habit_id == 1)
    assert insight.best_slot != 3                       # le propone salir de la noche
    assert (insight.best_slot, insight.best_weekday) not in {
        (session.slot, session.weekday) for session in evenings
    }


def test_the_suggestion_never_names_an_unused_time_slot():
    # El árbol puntúa igual de bien las franjas de las que no tiene NI UN dato, porque nada
    # las contradice. Proponer la madrugada porque el usuario nunca madruga sería absurdo.
    contexts = [_context()]                             # solo usa las franjas 1 y 3
    used = {session.slot for session in contexts[0].sessions}
    assert _strategy().insights(contexts)[0].best_slot in used


def test_the_suggestion_omits_the_weekday_when_the_model_ignores_it():
    # Con un patrón que solo depende de la franja, el árbol no llega a partir por 'weekday'.
    # En ese caso no se nombra un día concreto: se propone la franja a secas.
    same_every_day = []
    for index in range(30):
        morning = index % 2 == 0
        same_every_day.append(_session(slot=1 if morning else 3, weekday=index % 7,
                                       completed=morning, day_index=index))
    insight = _strategy().insights([_context(sessions=same_every_day)])[0]
    if insight.best_weekday is None:
        assert "slot" in insight.best_label
    else:                                               # sí distinguió días: debe nombrarlos
        assert insight.best_label.split()[0] in (
            "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"
        )


def test_the_at_risk_message_does_not_contradict_itself():
    # Un hábito con probabilidad alta puede caer a "en riesgo" por la tendencia. El texto no
    # debe entonces presumir del porcentaje, porque quedaría "tienes un 90% y vas mal".
    declining = [_session(slot=1, weekday=index % 7, completed=index < 22, day_index=index)
                 for index in range(30)]
    context = _context(habit_id=1, habit_name="Read", sessions=declining)
    insight = _strategy().insights([context])[0]

    messages = _recommendations(_strategy().generate([context]))
    if insight.state == STATE_AT_RISK and insight.probability >= 0.5:
        assert "going down" in messages[0].content
        # No debe presentar su probabilidad actual como algo tranquilizador mientras avisa
        # de que va a peor: sería "tienes un 71% de cumplirlo y vas mal".
        assert "chance of completing" not in messages[0].content


def test_the_proposal_is_not_what_the_user_already_does():
    # Si la mejor combinación resulta ser la que ya usa, el mensaje no puede proponérsela
    # como si fuera un cambio.
    steady = [_session(slot=1, weekday=index % 7, completed=index % 3 != 0, day_index=index)
              for index in range(30)]
    context = _context(habit_id=1, habit_name="Read", sessions=steady)
    insight = _strategy().insights([context])[0]

    content = _recommendations(_strategy().generate([context]))[0].content
    if insight.best_label == insight.current_label:
        assert "The model suggests" not in content
        assert "already the best time" in content


# --- Unitarios: tendencia ----------------------------------------------------

def test_trend_is_positive_when_compliance_grows():
    growing = [_session(completed=index >= 15, day_index=index) for index in range(30)]
    assert trend(growing) > 0


def test_trend_is_negative_when_compliance_falls():
    falling = [_session(completed=index < 15, day_index=index) for index in range(30)]
    assert trend(falling) < 0


def test_trend_is_flat_without_two_distinct_days():
    # Varias sesiones el mismo día no dibujan ninguna recta.
    assert trend([_session(day_index=0, completed=True),
                  _session(day_index=0, completed=False)]) == 0.0


# --- Integración: helpers ----------------------------------------------------

def _auth_token(client, username="alice", email="alice@example.com", password="secret123"):
    client.post("/auth/register",
                json={"username": username, "email": email, "password": password})
    r = client.post("/auth/login", json={"email": email, "password": password})
    return r.json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _create_habit(client, token, name="Study", importance=2):
    return client.post("/habits", json={"name": name, "type": "Study", "importance": importance},
                       headers=_auth(token)).json()["id"]


# 'specs' son tuplas (días de desfase respecto a hoy, hora de inicio, cumplida).
def _seed(client, token, habit_id, specs):
    created = client.post(
        "/sessions",
        json={
            "habit_id": habit_id,
            "sessions": [
                {
                    "date": (date.today() + timedelta(days=offset)).isoformat(),
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
            client.patch(f"/sessions/{session['id']}", json={"completed": True},
                         headers=_auth(token))


# Histórico amplio y con patrón: mañanas cumplidas, tardes no.
def _seed_learnable(client, token, habit_id):
    _seed(client, token, habit_id, [
        (-offset, 8, True) if offset % 2 else (-offset, 19, False)
        for offset in range(1, 31)
    ])


# --- Integración: endpoints --------------------------------------------------

def test_insights_without_token(client):
    assert client.get("/recommendations/insights").status_code == 401


def test_tree_chart_without_token(client):
    assert client.get("/recommendations/tree-chart").status_code == 401


def test_insights_is_empty_without_habits(client):
    token = _auth_token(client)
    r = client.get("/recommendations/insights", headers=_auth(token))
    assert r.status_code == 200
    assert r.json() == []


def test_insights_reports_unknown_without_enough_history(client):
    token = _auth_token(client)
    habit_id = _create_habit(client, token)
    _seed(client, token, habit_id, [(-1, 22, True), (-2, 22, False)])

    insights = client.get("/recommendations/insights", headers=_auth(token)).json()
    assert [i["state"] for i in insights] == ["unknown"]
    assert insights[0]["probability"] is None


def test_insights_diagnoses_a_habit_with_history(client):
    token = _auth_token(client)
    _seed_learnable(client, token, _create_habit(client, token))

    insight = client.get("/recommendations/insights", headers=_auth(token)).json()[0]
    assert insight["state"] != "unknown"
    assert 0.0 <= insight["probability"] <= 1.0
    assert insight["best_label"] and insight["current_label"]


def test_insights_excludes_other_users(client):
    token = _auth_token(client)
    _seed_learnable(client, token, _create_habit(client, token))
    other = _auth_token(client, username="bob", email="bob@example.com")

    assert client.get("/recommendations/insights", headers=_auth(other)).json() == []


def test_tree_chart_returns_a_png(client):
    token = _auth_token(client)
    _seed_learnable(client, token, _create_habit(client, token))

    r = client.get("/recommendations/tree-chart", headers=_auth(token))
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
    assert r.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_tree_chart_returns_a_placeholder_without_data(client):
    # Sin datos NO es un error: se devuelve una imagen con el aviso, igual que el resto de
    # gráficas de la aplicación, para que el frontend no tenga que tratar dos casos.
    token = _auth_token(client)
    r = client.get("/recommendations/tree-chart", headers=_auth(token))
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"


def test_generate_still_works_with_the_model_active(client):
    token = _auth_token(client)
    _seed_learnable(client, token, _create_habit(client, token))

    messages = client.post("/recommendations/generate", headers=_auth(token)).json()
    assert len([m for m in messages if m["type"] == "recommendation"]) == 1


def test_generate_is_still_idempotent_with_the_model_active(client):
    token = _auth_token(client)
    _seed_learnable(client, token, _create_habit(client, token))

    client.post("/recommendations/generate", headers=_auth(token))
    before = len(client.get("/messages", headers=_auth(token)).json())
    client.post("/recommendations/generate", headers=_auth(token))
    after = len(client.get("/messages", headers=_auth(token)).json())
    assert before == after

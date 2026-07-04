// Lógica de la pantalla Edit session. Reutiliza API_BASE/extractError de api.js y SessionForm
// (lógica común con add-session) de session-form.js.
$(document).ready(function () {

    // Solo corre en la pantalla con el formulario de edición de sesión
    var form = document.getElementById("editSessionForm");
    if (!form) return;

    // Guardia de sesión: sin token, de vuelta a login
    var token = localStorage.getItem("token");
    if (!token) {
        window.location.href = "login.html";
        return;
    }

    // Sesión a editar: ?id=<n>. Sin id no hay nada que editar -> a la lista.
    var sessionId = new URLSearchParams(window.location.search).get("id");
    if (!sessionId) {
        window.location.href = "habit-list.html";
        return;
    }

    var habitSelect = document.getElementById("sessionHabit");
    var block = document.getElementById("editSessionBlock");

    var updatePlaceholder = SessionForm.setupHabitPlaceholder(habitSelect);
    SessionForm.setupRecurrenceToggle(block);

    // Precarga: primero los hábitos del desplegable y, una vez listos, la sesión a editar
    // (para poder fijar el hábito seleccionado).
    SessionForm.loadHabits(habitSelect, token, null, function onDone() {
        fetch(`${API_BASE}/sessions/${sessionId}`, {
            headers: { "Authorization": `Bearer ${token}` }
        })
            .then(function (response) {
                if (response.status === 401) { SessionForm.handleUnauthorized(); return null; }
                if (response.status === 404) {
                    // No existe o no es del usuario: de vuelta a la lista
                    window.location.href = "habit-list.html";
                    return null;
                }
                return response.json();
            })
            .then(function (session) {
                if (!session) return;
                habitSelect.value = session.habit_id;
                updatePlaceholder();
                block.querySelector(".sessionDate").value = session.date;
                // El backend devuelve "HH:MM:SS"; el input time espera "HH:MM".
                block.querySelector(".sessionStart").value = session.start_time.slice(0, 5);
                block.querySelector(".sessionEnd").value = session.end_time.slice(0, 5);
            })
            .catch(function (error) {
                console.error("Error al cargar la sesión:", error);
            });
    });

    // Guardar: actualiza esta sesión (PUT) y, si hay recurrencia, crea la serie semanal (POST).
    form.addEventListener("submit", function (e) {
        e.preventDefault();

        var habitId = habitSelect.value;
        if (!habitId) {
            alert("Please select a habit");
            return;
        }

        var s = SessionForm.readBlock(block, 0);
        if (!s) return;

        habitId = parseInt(habitId, 10);

        fetch(`${API_BASE}/sessions/${sessionId}`, {
            method: "PUT",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify({
                habit_id: habitId,
                date: s.date,
                start_time: s.start_time,
                end_time: s.end_time
            })
        })
            .then(function (response) {
                if (response.status === 401) { SessionForm.handleUnauthorized(); return null; }
                if (response.status === 200) {
                    // Si se marcó recurrencia, crear las semanas siguientes (a partir de día+7)
                    // reutilizando el POST /sessions en lote.
                    var firstExtra = SessionForm.addDays(s.date, 7);
                    if (s.repeat_until && firstExtra <= s.repeat_until) {
                        return createRecurringSeries(habitId, firstExtra, s);
                    }
                    window.location.href = "habit-list.html";
                    return null;
                }
                return response.json().then(function (data) {
                    alert(extractError(data) || "Could not update the session");
                });
            })
            .catch(function (error) {
                console.error("Error al actualizar la sesión:", error);
                alert("Error connecting to server");
            });
    });

    // Crea las sesiones de las semanas siguientes (día+7 .. repeat_until) vía POST /sessions.
    function createRecurringSeries(habitId, firstExtra, s) {
        return fetch(`${API_BASE}/sessions`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify({
                habit_id: habitId,
                sessions: [{
                    date: firstExtra,
                    start_time: s.start_time,
                    end_time: s.end_time,
                    repeat_until: s.repeat_until
                }]
            })
        })
            .then(function (response) {
                if (response.status === 401) { SessionForm.handleUnauthorized(); return null; }
                if (response.status === 201) {
                    window.location.href = "habit-list.html";
                    return null;
                }
                return response.json().then(function (data) {
                    alert(extractError(data) || "The session was updated, but the weekly series could not be created");
                });
            });
    }
});

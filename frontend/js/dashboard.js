// Widget "Today's schedule" del dashboard: lista los HabitSession programados para hoy.
// Reutiliza API_BASE de api.js. Clic en una sesión -> edit-session (flujo ya existente).
$(document).ready(function () {

    // Solo corre en el dashboard
    var list = document.getElementById("todayList");
    if (!list) return;

    // Guardia de sesión: sin token, de vuelta a login
    var token = localStorage.getItem("token");
    if (!token) {
        window.location.href = "login.html";
        return;
    }

    var emptyMsg = document.getElementById("todayEmpty");
    var habitMap = {};                      // id -> { name, importance }

    function handleUnauthorized() {
        localStorage.removeItem("token");
        window.location.href = "login.html";
    }

    // Formatea un Date a "YYYY-MM-DD"
    function fmt(d) {
        return d.getFullYear() + "-" +
            String(d.getMonth() + 1).padStart(2, "0") + "-" +
            String(d.getDate()).padStart(2, "0");
    }

    // Fecha de hoy en formato "YYYY-MM-DD"
    function todayStr() {
        return fmt(new Date());
    }

    // Rellena el widget "Percentage of compliance" con el % de los últimos 30 días.
    function loadCompliance() {
        var valueEl = document.getElementById("complianceValue");
        if (!valueEl) return;
        var from = new Date();
        from.setDate(from.getDate() - 29);      // 30 días incluyendo hoy
        authFetch(`/statistics/summary?from=${fmt(from)}&to=${todayStr()}`)
            .then(function (summary) {
                if (!summary) return;           // 401: authFetch ya redirige a login
                valueEl.textContent = Math.round(summary.compliance_rate * 100) + "%";
            })
            .catch(function (error) {
                console.error("Error al cargar el cumplimiento:", error);
            });
    }
    loadCompliance();

    // Marca/desmarca una sesión como cumplida (PATCH) y refresca el horario de hoy.
    function toggleCompleted(session, checkbox) {
        authFetch(`/sessions/${session.id}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ completed: checkbox.checked })
        })
            .then(function () {
                if (!localStorage.getItem("token")) return;   // 401: redirigiendo a login
                loadToday();
                loadCompliance();
            })
            .catch(function (error) {
                console.error("Error al actualizar la sesión:", error);
                checkbox.checked = !checkbox.checked;   // revierte el toggle ante error
            });
    }

    // Primero los hábitos (para nombre y color) y luego las sesiones de hoy.
    fetch(`${API_BASE}/habits`, { headers: { "Authorization": `Bearer ${token}` } })
        .then(function (response) {
            if (response.status === 401) { handleUnauthorized(); return null; }
            return response.json();
        })
        .then(function (habits) {
            if (!habits) return;
            habits.forEach(function (h) {
                habitMap[h.id] = { name: h.name, importance: h.importance };
            });
            return loadToday();
        })
        .catch(function (error) {
            console.error("Error al cargar los hábitos:", error);
        });

    function loadToday() {
        var t = todayStr();
        return fetch(`${API_BASE}/sessions?from=${t}&to=${t}`, {
            headers: { "Authorization": `Bearer ${token}` }
        })
            .then(function (response) {
                if (response.status === 401) { handleUnauthorized(); return null; }
                return response.json();
            })
            .then(function (sessions) {
                if (!sessions) return;
                render(sessions);
            })
            .catch(function (error) {
                console.error("Error al cargar las sesiones:", error);
            });
    }

    // Las sesiones llegan ya ordenadas por hora de inicio (mismo día).
    function render(sessions) {
        list.innerHTML = "";
        emptyMsg.hidden = sessions.length > 0;

        sessions.forEach(function (s) {
            var habit = habitMap[s.habit_id] || { name: "Habit", importance: 2 };

            var li = document.createElement("li");
            li.className = "todayItem";

            // Checkbox de cumplimiento (tracking): marca/desmarca la sesión.
            var checkbox = document.createElement("input");
            checkbox.type = "checkbox";
            checkbox.className = "todayCheck";
            checkbox.checked = s.completed;
            checkbox.title = "Mark as done";
            checkbox.addEventListener("change", function () { toggleCompleted(s, checkbox); });

            var link = document.createElement("a");
            link.className = "todayLink imp" + habit.importance + (s.completed ? " completed" : "");
            link.href = "edit-session.html?id=" + s.id;

            var time = document.createElement("span");
            time.className = "todayTime";
            time.textContent = s.start_time.slice(0, 5) + "–" + s.end_time.slice(0, 5);

            var name = document.createElement("span");
            name.className = "todayName";
            name.textContent = habit.name;

            link.appendChild(time);
            link.appendChild(name);
            li.appendChild(checkbox);
            li.appendChild(link);
            list.appendChild(li);
        });
    }
});

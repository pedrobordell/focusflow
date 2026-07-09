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

    // Fecha de hoy en formato "YYYY-MM-DD"
    function todayStr() {
        var d = new Date();
        return d.getFullYear() + "-" +
            String(d.getMonth() + 1).padStart(2, "0") + "-" +
            String(d.getDate()).padStart(2, "0");
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

            var link = document.createElement("a");
            link.className = "todayLink imp" + habit.importance;
            link.href = "edit-session.html?id=" + s.id;

            var time = document.createElement("span");
            time.className = "todayTime";
            time.textContent = s.start_time.slice(0, 5) + "–" + s.end_time.slice(0, 5);

            var name = document.createElement("span");
            name.className = "todayName";
            name.textContent = habit.name;

            link.appendChild(time);
            link.appendChild(name);
            li.appendChild(link);
            list.appendChild(li);
        });
    }
});

// Lógica compartida por las pantallas de sesiones (add-session y edit-session).
// Se expone como objeto global SessionForm. Reutiliza API_BASE de api.js.
window.SessionForm = (function () {

    // 401 común: limpia el token y vuelve a login.
    function handleUnauthorized() {
        localStorage.removeItem("token");
        window.location.href = "login.html";
    }

    // Placeholder gris del Select Habit mientras no se elija. Devuelve la función de actualización
    // para poder re-aplicarla tras fijar el valor por código (la precarga no dispara "change").
    function setupHabitPlaceholder(select) {
        function update() {
            select.classList.toggle("placeholder", select.value === "");
        }
        update();
        select.addEventListener("change", update);
        return update;
    }

    // Rellena el desplegable con los hábitos del usuario (GET /habits).
    // onEmpty(): sin hábitos. onDone(habits): tras rellenar (p. ej. para precargar luego una sesión).
    function loadHabits(select, token, onEmpty, onDone) {
        fetch(`${API_BASE}/habits`, {
            headers: { "Authorization": `Bearer ${token}` }
        })
            .then(function (response) {
                if (response.status === 401) { handleUnauthorized(); return null; }
                return response.json();
            })
            .then(function (habits) {
                if (!habits) return;
                if (habits.length === 0) {
                    if (onEmpty) onEmpty();
                    return;
                }
                habits.forEach(function (habit) {
                    var option = document.createElement("option");
                    option.value = habit.id;
                    option.textContent = habit.name;
                    select.appendChild(option);
                });
                if (onDone) onDone(habits);
            })
            .catch(function (error) {
                console.error("Error al cargar los hábitos:", error);
            });
    }

    // Toggle de recurrencia de un bloque: muestra/oculta el campo "Repeat until".
    function setupRecurrenceToggle(block) {
        var toggle = block.querySelector(".recurrenceToggle");
        var limit = block.querySelector(".recurrenceLimit");
        toggle.addEventListener("click", function () {
            var active = toggle.getAttribute("aria-pressed") === "true";
            toggle.setAttribute("aria-pressed", String(!active));
            limit.hidden = active; // estaba activo -> ocultar; estaba inactivo -> mostrar
        });
    }

    // Valida un bloque y devuelve { date, start_time, end_time, repeat_until } o null (avisando).
    // Las horas/fechas son strings ("HH:MM" / "YYYY-MM-DD"): se comparan lexicográficamente.
    function readBlock(block, index) {
        var date = block.querySelector(".sessionDate").value;
        var start = block.querySelector(".sessionStart").value;
        var end = block.querySelector(".sessionEnd").value;
        var endsNextDay = block.querySelector(".sessionEndsNextDay").checked;
        var recurrent = block.querySelector(".recurrenceToggle").getAttribute("aria-pressed") === "true";
        var until = block.querySelector(".sessionUntil").value;
        var n = index + 1;

        if (!date || !start || !end) {
            alert("Session " + n + ": please fill in day, start time and end time");
            return null;
        }
        // Solo exigimos fin > inicio si termina el MISMO día. Si termina al día
        // siguiente, el fin siempre es posterior.
        if (!endsNextDay && end <= start) {
            alert("Session " + n + ": end time must be after start time");
            return null;
        }

        var endDate = endsNextDay ? addDays(date, 1) : date;

        var session = { date: date, end_date: endDate, start_time: start, end_time: end, repeat_until: null };
        if (recurrent) {
            if (!until) {
                alert("Session " + n + ": please choose a 'Repeat until' date");
                return null;
            }
            if (until < date) {
                alert("Session " + n + ": 'Repeat until' must be on or after the day");
                return null;
            }
            session.repeat_until = until;
        }
        return session;
    }

    // Suma días a una fecha "YYYY-MM-DD" y devuelve otra "YYYY-MM-DD".
    function addDays(dateStr, days) {
        var d = new Date(dateStr + "T00:00:00");
        d.setDate(d.getDate() + days);
        var mm = String(d.getMonth() + 1).padStart(2, "0");
        var dd = String(d.getDate()).padStart(2, "0");
        return d.getFullYear() + "-" + mm + "-" + dd;
    }

    // Fecha de hoy en formato "YYYY-MM-DD" (para autocompletar campos de fecha).
    function todayStr() {
        var d = new Date();
        var mm = String(d.getMonth() + 1).padStart(2, "0");
        var dd = String(d.getDate()).padStart(2, "0");
        return d.getFullYear() + "-" + mm + "-" + dd;
    }

    return {
        handleUnauthorized: handleUnauthorized,
        setupHabitPlaceholder: setupHabitPlaceholder,
        loadHabits: loadHabits,
        setupRecurrenceToggle: setupRecurrenceToggle,
        readBlock: readBlock,
        addDays: addDays,
        todayStr: todayStr
    };
})();

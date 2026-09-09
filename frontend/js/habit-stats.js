// Lógica de Habit Stats: elegido un hábito, muestra a la izquierda la gráfica
// de % por hora del día y a la derecha su detalle (info, % de las últimas 10 
// sesiones y mejor franja horaria).
$(document).ready(function () {

    // Hace que el script solo pueda ejecutarse en habit-stats.html
    var container = document.getElementById("habitStatsContainer");
    if (!container) return;

    // Guardia de sesión: sin token, de vuelta a login
    if (!localStorage.getItem("token")) {
        window.location.href = "login.html";
        return;
    }

    var IMPORTANCE_LABELS = { 1: "Low", 2: "Medium", 3: "High" };

    var emptyEl = document.getElementById("habitStatsEmpty");
    var controlsEl = document.getElementById("habitStatsControls");
    var bodyEl = document.getElementById("habitStatsBody");
    var errorEl = document.getElementById("habitStatsError");
    var habitSelect = document.getElementById("habitSelect");
    var periodSelect = document.getElementById("habitPeriod");

    var chartUrl = null;    // objectURL vigente de la gráfica (para revocarlo al recargar)

    // --- Utilidades ---------------------------------------------------------

    // Convierte un objeto Date a texto "YYYY-MM-DD", asegurándose de que el mes y el día tengan dos dígitos
    function formatDate(date) {
        return date.getFullYear() + "-" +
            String(date.getMonth() + 1).padStart(2, "0") + "-" +
            String(date.getDate()).padStart(2, "0");
    }

    // Traduce valor del periodSelect a un rango [from, to] terminando hoy.
    function computePeriod(value) {
        var to = new Date();
        if (value === "all") {
            return { from: "1970-01-01", to: formatDate(to) };
        }
        var days = parseInt(value, 10);     // Días que se van a restar a hoy para obtener from
        var from = new Date();
        from.setDate(from.getDate() - (days - 1));
        return { from: formatDate(from), to: formatDate(to) };
    }

    // 0.75 -> "75%".
    function formatPercent(rate) {
        return Math.round(rate * 100) + "%";
    }

    function showError(message) {
        errorEl.textContent = message;
        errorEl.hidden = false;
    }

    function clearError() {
        errorEl.hidden = true;
    }

    // --- Render del detalle (derecha) ---------------------------------------

    function renderDetail(detail) {
        document.getElementById("habitInfoName").textContent = detail.habit_name;
        var meta = [];
        if (detail.type) meta.push(detail.type);
        meta.push("Importance: " + (IMPORTANCE_LABELS[detail.importance] || detail.importance));
        document.getElementById("habitInfoMeta").textContent = meta.join(" - ");

        var last10 = document.getElementById("last10Value");
        if (detail.last10_rate != null) {
            last10.textContent = formatPercent(detail.last10_rate);
            document.getElementById("last10Meta").textContent =
                "Over the last " + detail.last10_count + " session" + (detail.last10_count === 1 ? "" : "s");
        } else {
            last10.textContent = "-";
            document.getElementById("last10Meta").textContent = "No sessions yet";
        }

        var best = document.getElementById("bestSlotValue");
        best.textContent = detail.best_slot || "-";
        // Sin best_slot puede ser que no haya sesiones o que ninguna franja tenga suficientes
        // (el backend exige un mínimo para no proponer un horario a partir de una casualidad).
        document.getElementById("bestSlotMeta").textContent =
            detail.best_slot ? "Highest compliance in this period" : "Not enough sessions in this period";
    }

    // --- Gráfica (izquierda) ------------------------------------------------

    async function loadChart(habitId, period) {
        var img = document.getElementById("chartHourly");
        var url = await authFetchBlob(
            `/statistics/habit/${habitId}/hourly-chart?from=${period.from}&to=${period.to}`);
        if (!url) return;                            // 401: authFetchBlob ya redirige a login
        if (chartUrl) URL.revokeObjectURL(chartUrl);
        chartUrl = url;
        img.src = url;
    }

    // --- Carga del hábito seleccionado --------------------------------------

    async function load() {
        var habitId = habitSelect.value;
        if (!habitId) return;
        var period = computePeriod(periodSelect.value);
        try {
            var detail = await authFetch(
                `/statistics/habit/${habitId}?from=${period.from}&to=${period.to}`);
            if (!detail) return;                     // 401: authFetch ya redirige a login
            clearError();
            renderDetail(detail);                   // Carga detalles
            await loadChart(habitId, period);       // Carga gráfica
        } catch (error) {
            console.error("Error al cargar el detalle del hábito:", error);
            showError("Could not load this habit's stats. " + error.message);
        }
    }

    // --- Inicialización: poblar el selector de hábitos ----------------------

    async function init() {
        var habits;
        // Carga los hábitos
        try {
            habits = await authFetch("/habits");
        }
        // Manejo de errores
        catch (error) {
            console.error("Error al cargar los hábitos:", error);
            showError("Could not load your habits. " + error.message);
            return;
        }
        if (!habits) return;                // 401: authFetch ya redirige a login
        if (habits.length === 0) {          // sin hábitos: solo el aviso
            emptyEl.hidden = false;
            return;
        }

        habits.forEach(function (h) {
            var opt = document.createElement("option");
            opt.value = h.id;
            opt.textContent = h.name;
            habitSelect.appendChild(opt);
        });

        // Preselección por ?habitId=
        var preselect = new URLSearchParams(window.location.search).get("habitId");
        if (preselect && habits.some(function (h) { return String(h.id) === preselect; })) {
            habitSelect.value = preselect;
        }

        controlsEl.hidden = false;
        bodyEl.hidden = false;
        habitSelect.addEventListener("change", load);
        periodSelect.addEventListener("change", load);
        load();
    }

    init();
});

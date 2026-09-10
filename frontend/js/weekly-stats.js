// Lógica de Weekly Stats: gráfica de % de cumplimiento por día del último mes (izquierda)
// y destacados de la semana actual vs anterior (derecha). Reutiliza authFetch/authFetchBlob.
$(document).ready(function () {

    // Solo se ejecuta en weekly-stats.html
    var container = document.getElementById("weeklyStatsContainer");
    if (!container) return;

    // Guardia de sesión: sin token, de vuelta a login
    if (!localStorage.getItem("token")) {
        window.location.href = "login.html";
        return;
    }

    var chartUrl = null;    // objectURL vigente de la gráfica (para revocarlo al recargar)

    // --- Utilidades ---------------------------------------------------------

    // Convierte un objeto Date a texto "YYYY-MM-DD", asegurándose de que el mes y el día tengan dos dígitos
    function formatDate(date) {
        return date.getFullYear() + "-" +
            String(date.getMonth() + 1).padStart(2, "0") + "-" +
            String(date.getDate()).padStart(2, "0");
    }

    // 0.75 -> "75%".
    function formatPercent(rate) {
        return Math.round(rate * 100) + "%";
    }

    function showError(message) {
        var errorEl = document.getElementById("weeklyError");
        errorEl.textContent = message;
        errorEl.hidden = false;
    }

    // --- Gráfica de la izquierda (últimos 30 días) --------------------------
    async function loadChart() {
        var rangeEnd = new Date();
        var rangeStart = new Date();
        rangeStart.setDate(rangeStart.getDate() - 29);   // 30 días incluyendo hoy
        var imgEl = document.getElementById("chartDaily");
        var objectUrl = await authFetchBlob(
            `/statistics/daily-chart?from=${formatDate(rangeStart)}&to=${formatDate(rangeEnd)}`);
        if (!objectUrl) return;                          // 401: authFetchBlob ya redirige a login
        if (chartUrl) URL.revokeObjectURL(chartUrl);     // libera la gráfica anterior (evita fugas)
        chartUrl = objectUrl;
        imgEl.src = objectUrl;
    }

    // --- Destacados de la derecha (semana actual vs anterior) ---------------
    function renderHighlights(highlights) {
        // Hábito con más horas dedicadas esta semana
        if (highlights.most_hours) {
            document.getElementById("mostHoursValue").textContent =
                highlights.most_hours.completed_hours + " h";
            document.getElementById("mostHoursMeta").textContent =
                highlights.most_hours.habit_name + " - " +
                formatPercent(highlights.most_hours.compliance_rate) + " compliance";
        }

        // Hábito con peor cumplimiento esta semana
        if (highlights.worst_compliance) {
            document.getElementById("worstValue").textContent =
                formatPercent(highlights.worst_compliance.compliance_rate);
            document.getElementById("worstMeta").textContent = highlights.worst_compliance.habit_name;
        }

        // Mejora respecto a la semana anterior (en puntos porcentuales)
        var improvementEl = document.getElementById("improvementValue");
        var improvementPp = highlights.improvement_pp;
        var sign = improvementPp > 0 ? "+" : "";     // los negativos ya llevan "-" del número
        improvementEl.textContent = sign + improvementPp + " pp";
        improvementEl.classList.remove("deltaUp", "deltaDown");
        if (improvementPp > 0) improvementEl.classList.add("deltaUp");
        else if (improvementPp < 0) improvementEl.classList.add("deltaDown");
        document.getElementById("improvementMeta").textContent =
            "This week " + formatPercent(highlights.compliance_now) +
            " vs " + formatPercent(highlights.compliance_prev) + " last week";
    }

    // --- Carga --------------------------------------------------------------
    async function load() {
        try {
            // Carga los destacados de la derecha
            var weeklyData = await authFetch("/statistics/weekly");
            if (!weeklyData) return;                 // 401: authFetch ya redirige a login
            renderHighlights(weeklyData);

            // Carga la gráfica de la izquierda
            await loadChart();
        } catch (error) {
            console.error("Error al cargar las estadísticas semanales:", error);
            showError("Could not load your weekly stats. " + error.message);
        }
    }

    load();
});

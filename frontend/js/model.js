// Lógica de la pantalla Model: el árbol de decisión entrenado con el histórico (izquierda)
// y el diagnóstico de cada hábito (derecha). Reutiliza authFetch/authFetchBlob.
$(document).ready(function () {

    // Solo se ejecuta en model.html
    var container = document.getElementById("modelContainer");
    if (!container) return;

    // Guardia de sesión: sin token, de vuelta a login
    if (!localStorage.getItem("token")) {
        window.location.href = "login.html";
        return;
    }

    var chartUrl = null;    // objectURL vigente de la gráfica (para revocarlo al recargar)

    // Textos y color de cada estado. Las claves son las del backend (HabitInsight.state).
    var STATES = {
        abandoned: { label: "Abandoned", css: "stateAbandoned" },
        at_risk:   { label: "At risk",   css: "stateAtRisk" },
        improving: { label: "Improving", css: "stateImproving" },
        on_track:  { label: "On track",  css: "stateOnTrack" },
        unknown:   { label: "No data",   css: "stateUnknown" }
    };

    // --- Utilidades ---------------------------------------------------------

    // 0.75 -> "75%".
    function formatPercent(rate) {
        return Math.round(rate * 100) + "%";
    }

    function showError(message) {
        var errorEl = document.getElementById("modelError");
        errorEl.textContent = message;
        errorEl.hidden = false;
    }

    function showPanelMessage(message) {
        var emptyEl = document.getElementById("insightsEmpty");
        emptyEl.textContent = message;
        emptyEl.hidden = false;
    }

    // --- Gráfica de la izquierda (el árbol) ---------------------------------
    async function loadChart() {
        var objectUrl = await authFetchBlob("/recommendations/tree-chart");
        if (!objectUrl) return;                          // 401: authFetchBlob ya redirige a login
        if (chartUrl) URL.revokeObjectURL(chartUrl);     // libera la gráfica anterior (evita fugas)
        chartUrl = objectUrl;
        document.getElementById("chartTree").src = objectUrl;
        document.getElementById("chartTreeLink").href = objectUrl;   // abrirla a tamaño real
    }

    // --- Diagnóstico de la derecha ------------------------------------------

    // Pinta la tarjeta de un hábito clonando la plantilla del HTML.
    function renderInsight(insight) {
        var template = document.getElementById("insightCardTemplate");
        var card = template.content.cloneNode(true);
        var state = STATES[insight.state] || STATES.unknown;

        card.querySelector(".insightHabit").textContent = insight.habit_name;

        var badge = card.querySelector(".insightState");
        badge.textContent = state.label;
        badge.classList.add(state.css);

        // Sin modelo no hay cifras que enseñar: se dice por qué y se deja la tarjeta ahí.
        if (insight.probability === null) {
            card.querySelector(".insightCurrent").textContent =
                "Not enough sessions yet to diagnose this habit.";
            return card;
        }

        card.querySelector(".insightProbability").textContent =
            formatPercent(insight.probability);
        card.querySelector(".insightCurrent").textContent =
            "On " + insight.current_label + ", as you usually schedule it · " +
            insight.trend_label.toLowerCase();
        card.querySelector(".insightSuggestion").textContent =
            "Best predicted slot: " + insight.best_label +
            " (" + formatPercent(insight.best_probability) + ")";
        return card;
    }

    function renderInsights(insights) {
        var panel = document.getElementById("insightsPanel");

        if (!insights.length) {
            showPanelMessage("You have no habits yet. Create one to start tracking it.");
            return;
        }

        insights.forEach(function (insight) {
            panel.appendChild(renderInsight(insight));
        });
    }

    // --- Carga --------------------------------------------------------------
    async function load() {
        try {
            var insights = await authFetch("/recommendations/insights");
            if (!insights) return;                   // 401: authFetch ya redirige a login
            renderInsights(insights);

            // La gráfica va después: si no hay datos, el servidor ya devuelve un PNG con el
            // aviso, así que no hace falta tratarlo como error aquí.
            await loadChart();
        } catch (error) {
            console.error("Error al cargar el modelo:", error);
            showError("Could not load your model. " + error.message);
        }
    }

    load();
});

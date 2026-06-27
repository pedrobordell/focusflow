// Lógica de la pantalla Habit List. Reutiliza API_BASE y extractError de api.js.
$(document).ready(function () {

    // Solo corre en la pantalla de la lista
    var tbody = document.getElementById("habitTableBody");
    if (!tbody) return;

    // Guardia de sesión: sin token, de vuelta a login
    var token = localStorage.getItem("token");
    if (!token) {
        window.location.href = "login.html";
        return;
    }

    var IMPORTANCE_LABELS = { 1: "Low", 2: "Medium", 3: "High" };
    var table = document.getElementById("habitTable");
    var emptyMsg = document.getElementById("habitEmpty");

    // Maneja el 401 común a todas las peticiones: limpia el token y vuelve a login.
    function handleUnauthorized() {
        localStorage.removeItem("token");
        window.location.href = "login.html";
    }

    // Pinta una fila de la tabla a partir de un hábito
    function renderRow(habit) {
        var tr = $("<tr>");

        $("<td>").text(habit.name).appendTo(tr);
        $("<td>").text(habit.type || "—").appendTo(tr);
        $("<td>").text(IMPORTANCE_LABELS[habit.importance] || habit.importance).appendTo(tr);
        // Completed: placeholder hasta tener el subsistema de sesiones
        $("<td>").append($("<span>").addClass("emptyState").text("—")).appendTo(tr);

        // Stats: enlaza a la gráfica (pasa el id para el futuro)
        $("<td>").addClass("iconCol").append(
            $("<a>")
                .addClass("iconLink")
                .attr("href", "statistics.html?habitId=" + habit.id)
                .attr("title", "View stats")
                .text("📊")
        ).appendTo(tr);

        // Editar: lleva al formulario de edición precargado
        $("<td>").addClass("iconCol").append(
            $("<a>")
                .addClass("iconLink")
                .attr("href", "edit-habit.html?id=" + habit.id)
                .attr("title", "Edit")
                .text("✏️")
        ).appendTo(tr);

        // Borrar: pide confirmación y elimina
        $("<td>").addClass("iconCol").append(
            $("<button>")
                .attr("type", "button")
                .addClass("iconBtn iconBtnDanger")
                .attr("title", "Delete")
                .text("🗑️")
                .on("click", function () { deleteHabit(habit); })
        ).appendTo(tr);

        tr.appendTo(tbody);
    }

    // Carga (o recarga) la lista de hábitos del usuario
    function loadHabits() {
        fetch(`${API_BASE}/habits`, {
            headers: { "Authorization": `Bearer ${token}` }
        })
            .then(function (response) {
                if (response.status === 401) { handleUnauthorized(); return null; }
                return response.json();
            })
            .then(function (habits) {
                if (!habits) return;
                tbody.innerHTML = "";
                habits.forEach(renderRow);
                var hasHabits = habits.length > 0;
                table.hidden = !hasHabits;
                emptyMsg.hidden = hasHabits;
            })
            .catch(function (error) {
                console.error("Error al cargar los hábitos:", error);
            });
    }

    // Borra un hábito tras confirmación y refresca la tabla
    function deleteHabit(habit) {
        if (!window.confirm(`Delete "${habit.name}"?`)) return;

        fetch(`${API_BASE}/habits/${habit.id}`, {
            method: "DELETE",
            headers: { "Authorization": `Bearer ${token}` }
        })
            .then(function (response) {
                if (response.status === 401) { handleUnauthorized(); return; }
                if (response.status === 204) { loadHabits(); return; }
                alert("Could not delete the habit");
            })
            .catch(function (error) {
                console.error("Error al borrar el hábito:", error);
                alert("Error connecting to server");
            });
    }

    loadHabits();
});

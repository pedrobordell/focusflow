// Lógica de la pantalla Edit habit. Reutiliza API_BASE y extractError de api.js.
$(document).ready(function () {

    // Solo corre en la pantalla con el formulario de edición
    var form = document.getElementById("editHabitForm");
    if (!form) return;

    // Guardia de sesión: sin token, de vuelta a login
    var token = localStorage.getItem("token");
    if (!token) {
        window.location.href = "login.html";
        return;
    }

    // Hábito a editar: ?id=<n>. Sin id no hay nada que editar -> a la lista.
    var habitId = new URLSearchParams(window.location.search).get("id");
    if (!habitId) {
        window.location.href = "habit-list.html";
        return;
    }

    // Color del placeholder del Type: gris mientras no se elija categoría
    var typeSelect = document.getElementById("habitType");
    function updateTypePlaceholder() {
        typeSelect.classList.toggle("placeholder", typeSelect.value === "");
    }
    typeSelect.addEventListener("change", updateTypePlaceholder);

    // Slider de importancia: actualiza la etiqueta (Low/Medium/High) y el relleno
    var IMPORTANCE_LABELS = { 1: "Low", 2: "Medium", 3: "High" };
    var range = document.getElementById("habitImportance");
    var valueLabel = document.getElementById("importanceValue");
    function updateImportance() {
        var v = parseInt(range.value, 10);
        valueLabel.textContent = IMPORTANCE_LABELS[v];
        range.style.setProperty("--range-progress", ((v - 1) / 2 * 100) + "%");
    }
    range.addEventListener("input", updateImportance);

    // Precarga el formulario con los datos actuales del hábito
    fetch(`${API_BASE}/habits/${habitId}`, {
        headers: { "Authorization": `Bearer ${token}` }
    })
        .then(function (response) {
            if (response.status === 401) {
                localStorage.removeItem("token");
                window.location.href = "login.html";
                return null;
            }
            if (response.status === 404) {
                // No existe o no es del usuario: de vuelta a la lista
                window.location.href = "habit-list.html";
                return null;
            }
            return response.json();
        })
        .then(function (habit) {
            if (!habit) return;
            document.getElementById("habitName").value = habit.name;
            typeSelect.value = habit.type || "";   // null -> placeholder
            range.value = habit.importance;
            updateTypePlaceholder();
            updateImportance();
        })
        .catch(function (error) {
            console.error("Error al cargar el hábito:", error);
        });

    // Confirmar: guarda los cambios (PUT /habits/{id}) y vuelve a la lista
    form.addEventListener("submit", function (e) {
        e.preventDefault();

        var name = document.getElementById("habitName").value.trim();
        if (!name) {
            alert("Please enter a habit name");
            return;
        }

        var payload = {
            name: name,
            type: typeSelect.value || null,
            importance: parseInt(range.value, 10)
        };

        fetch(`${API_BASE}/habits/${habitId}`, {
            method: "PUT",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify(payload)
        })
            .then(function (response) {
                if (response.status === 401) {
                    localStorage.removeItem("token");
                    window.location.href = "login.html";
                    return null;
                }
                if (response.status === 200) {
                    window.location.href = "habit-list.html";
                    return null;
                }
                return response.json().then(function (data) {
                    alert(extractError(data) || "Could not update the habit");
                });
            })
            .catch(function (error) {
                console.error("Error al actualizar el hábito:", error);
                alert("Error connecting to server");
            });
    });

    // Cancelar: vuelve a la lista sin guardar
    document.getElementById("cancelBtn").addEventListener("click", function () {
        window.location.href = "habit-list.html";
    });
});

// Lógica de la pantalla Add habit.
$(document).ready(function () {

    // Solo corre en la pantalla con el formulario
    var form = document.getElementById("addHabitForm");
    if (!form) return;

    // Color del placeholder del Type: gris mientras no se elija categoría
    var typeSelect = document.getElementById("habitType");
    function updateTypePlaceholder() {
        typeSelect.classList.toggle("placeholder", typeSelect.value === "");
    }
    updateTypePlaceholder();
    typeSelect.addEventListener("change", updateTypePlaceholder);

    // Slider de importancia: 1 -> Low, 2 -> Medium, 3 -> High.
    // Actualiza la etiqueta y el relleno (--range-progress: 0% / 50% / 100%).
    var IMPORTANCE_LABELS = { 1: "Low", 2: "Medium", 3: "High" };
    var range = document.getElementById("habitImportance");
    var valueLabel = document.getElementById("importanceValue");

    function updateImportance() {
        var v = parseInt(range.value, 10);
        valueLabel.textContent = IMPORTANCE_LABELS[v];
        range.style.setProperty("--range-progress", ((v - 1) / 2 * 100) + "%");
    }
    updateImportance();
    range.addEventListener("input", updateImportance);

    // Confirmar: crea el hábito en el backend (POST /habits) y navega a la lista.
    // Reutiliza API_BASE y extractError de api.js.
    form.addEventListener("submit", function (e) {
        e.preventDefault();

        // Sin token no se puede crear; de vuelta a login.
        var token = localStorage.getItem("token");
        if (!token) {
            window.location.href = "login.html";
            return;
        }

        // Validación mínima en cliente (el servidor vuelve a validar).
        var name = document.getElementById("habitName").value.trim();
        if (!name) {
            alert("Please enter a habit name");
            return;
        }

        var payload = {
            name: name,
            type: typeSelect.value || null,   // "" (placeholder) -> null
            importance: parseInt(range.value, 10)
        };

        fetch(`${API_BASE}/habits`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify(payload)
        })
            .then(function (response) {
                if (response.status === 401) {
                    // Token caducado o inválido: limpiar y volver a login.
                    localStorage.removeItem("token");
                    window.location.href = "login.html";
                    return null;
                }
                if (response.status === 201) {
                    window.location.href = "habit-list.html";
                    return null;
                }
                // Otros errores (p. ej. 422 de validación): mostrar el mensaje.
                return response.json().then(function (data) {
                    alert(extractError(data) || "Could not create the habit");
                });
            })
            .catch(function (error) {
                console.error("Error al crear el hábito:", error);
                alert("Error connecting to server");
            });
    });

    // Cancelar: vuelve a la lista de hábitos
    document.getElementById("cancelBtn").addEventListener("click", function () {
        window.location.href = "habit-list.html";
    });
});

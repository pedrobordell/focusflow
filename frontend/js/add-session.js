// Lógica de la pantalla Add Session. Reutiliza API_BASE/extractError de api.js y SessionForm
// (lógica común con edit-session) de session-form.js.
$(document).ready(function () {

    // Solo corre en la pantalla con el formulario de sesiones
    var form = document.getElementById("addSessionForm");
    if (!form) return;

    // Guardia de sesión: sin token, de vuelta a login
    var token = localStorage.getItem("token");
    if (!token) {
        window.location.href = "login.html";
        return;
    }

    var habitSelect = document.getElementById("sessionHabit");
    var blocksContainer = document.getElementById("sessionBlocks");
    var template = document.getElementById("sessionBlockTemplate");
    var addBtn = document.getElementById("addSessionBtn");
    var submitBtn = document.getElementById("addSessionsSubmit");
    var noHabitsMsg = document.getElementById("noHabitsMsg");

    SessionForm.setupHabitPlaceholder(habitSelect);

    // Rellena el desplegable; sin hábitos no se pueden crear sesiones: avisar y deshabilitar.
    SessionForm.loadHabits(habitSelect, token, function onEmpty() {
        noHabitsMsg.hidden = false;
        submitBtn.disabled = true;
        addBtn.disabled = true;
    });

    // Añade un bloque clonando el <template>. El primero no es eliminable.
    function addBlock(removable) {
        var fragment = template.content.cloneNode(true);
        var block = fragment.querySelector(".sessionBlock");
        // Autocompletar el día con la fecha de hoy (el usuario puede cambiarlo).
        block.querySelector(".sessionDate").value = SessionForm.todayStr();
        SessionForm.setupRecurrenceToggle(block);
        if (removable) {
            var removeBtn = block.querySelector(".removeSessionBtn");
            removeBtn.hidden = false;
            removeBtn.addEventListener("click", function () {
                block.remove();
            });
        }
        blocksContainer.appendChild(fragment);
    }

    // Primer bloque al cargar
    addBlock(false);

    addBtn.addEventListener("click", function () {
        addBlock(true);
    });

    // Confirmar: crea todas las sesiones (POST /sessions) y vuelve a la lista de hábitos.
    form.addEventListener("submit", function (e) {
        e.preventDefault();

        var habitId = habitSelect.value;
        if (!habitId) {
            alert("Please select a habit");
            return;
        }

        // Valida y recoge cada bloque (SessionForm.readBlock avisa y devuelve null si hay error).
        var blocks = blocksContainer.querySelectorAll(".sessionBlock");
        var sessions = [];
        for (var i = 0; i < blocks.length; i++) {
            var session = SessionForm.readBlock(blocks[i], i);
            if (!session) return;
            sessions.push(session);
        }

        var payload = { habit_id: parseInt(habitId, 10), sessions: sessions };

        fetch(`${API_BASE}/sessions`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify(payload)
        })
            .then(function (response) {
                if (response.status === 401) { SessionForm.handleUnauthorized(); return null; }
                if (response.status === 201) {
                    window.location.href = "habit-list.html";
                    return null;
                }
                return response.json().then(function (data) {
                    alert(extractError(data) || "Could not create the sessions");
                });
            })
            .catch(function (error) {
                console.error("Error al crear las sesiones:", error);
                alert("Error connecting to server");
            });
    });
});

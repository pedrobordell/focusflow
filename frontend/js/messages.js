// Bandeja de mensajes: recomendaciones y avisos que el sistema genera a partir del histórico.
// Al abrir la pantalla se pide primero una generación (POST /recommendations/generate) y
// después el listado completo (GET /messages). Reutiliza authFetch de api.js.
$(document).ready(function () {

    // Solo se ejecuta en messages.html
    var container = document.getElementById("messagesContainer");
    if (!container) return;

    // Guardia de sesión: sin token, de vuelta a login
    if (!localStorage.getItem("token")) {
        window.location.href = "login.html";
        return;
    }

    var listEl = document.getElementById("messageList");
    var emptyEl = document.getElementById("messagesEmpty");
    var errorEl = document.getElementById("messagesError");
    var unreadEl = document.getElementById("unreadCount");

    // --- Utilidades ---------------------------------------------------------

    // Crea un elemento con clase y texto (mismo ayudante que en el calendario).
    function el(tag, className, text) {
        var node = document.createElement(tag);
        if (className) node.className = className;
        if (text != null) node.textContent = text;
        return node;
    }

    // "2026-07-28T09:15:00" -> "28 Jul 2026, 09:15". Los mensajes de hoy se muestran
    // solo con la hora, que es lo que interesa cuando se acaban de generar.
    function formatDate(isoText) {
        var when = new Date(isoText);
        if (isNaN(when)) return isoText;
        var time = String(when.getHours()).padStart(2, "0") + ":" +
            String(when.getMinutes()).padStart(2, "0");
        var today = new Date();
        var sameDay = when.getFullYear() === today.getFullYear() &&
            when.getMonth() === today.getMonth() &&
            when.getDate() === today.getDate();
        if (sameDay) return "Today, " + time;
        return when.toLocaleDateString("en-GB", {
            day: "numeric", month: "short", year: "numeric"
        }) + ", " + time;
    }

    function showError(message) {
        errorEl.textContent = message;
        errorEl.hidden = false;
    }

    // --- Acciones sobre un mensaje ------------------------------------------

    // Marca/desmarca como leído y refresca la lista (sin volver a generar).
    async function toggleRead(message) {
        try {
            await authFetch(`/messages/${message.id}`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ is_read: !message.is_read })
            });
            if (!localStorage.getItem("token")) return;   // 401: redirigiendo a login
            await reload();
        } catch (error) {
            console.error("Error al actualizar el mensaje:", error);
            showError("Could not update the message. " + error.message);
        }
    }

    // Borra el mensaje tras confirmación y refresca la lista.
    async function deleteMessage(message) {
        if (!window.confirm(`Delete "${message.title}"?`)) return;
        try {
            await authFetch(`/messages/${message.id}`, { method: "DELETE" });
            if (!localStorage.getItem("token")) return;
            await reload();
        } catch (error) {
            console.error("Error al borrar el mensaje:", error);
            showError("Could not delete the message. " + error.message);
        }
    }

    // --- Render -------------------------------------------------------------

    function buildItem(message) {
        // Los no leídos se distinguen con la clase 'unread' (borde de color y título en negrita).
        var item = el("li", "messageItem" + (message.is_read ? "" : " unread"));

        var head = el("div", "messageHead");
        head.appendChild(el("span", "messageTitle", message.title));
        // El tipo distingue lo que el sistema PROPONE de lo que solo INFORMA.
        head.appendChild(el("span", "messageTag tag-" + message.type,
            message.type === "recommendation" ? "Recommendation" : "Reminder"));
        item.appendChild(head);

        item.appendChild(el("p", "messageContent", message.content));

        var foot = el("div", "messageFoot");
        foot.appendChild(el("span", "messageMeta", formatDate(message.created_at)));

        var actions = el("div", "messageActions");

        var read = el("button", "messageBtn", message.is_read ? "Mark as unread" : "Mark as read");
        read.type = "button";
        read.addEventListener("click", function () { toggleRead(message); });
        actions.appendChild(read);

        var remove = el("button", "messageBtn", "🗑️");
        remove.type = "button";
        remove.title = "Delete";
        remove.addEventListener("click", function () { deleteMessage(message); });
        actions.appendChild(remove);

        foot.appendChild(actions);
        item.appendChild(foot);
        return item;
    }

    // Los mensajes llegan ya ordenados por fecha descendente desde la API.
    function render(messages) {
        listEl.innerHTML = "";
        emptyEl.hidden = messages.length > 0;

        var unread = messages.filter(function (m) { return !m.is_read; }).length;
        unreadEl.textContent = unread + " unread";
        unreadEl.hidden = unread === 0;

        messages.forEach(function (message) {
            listEl.appendChild(buildItem(message));
        });
    }

    // --- Carga --------------------------------------------------------------

    // Solo relee el listado (para después de marcar leído o borrar).
    async function reload() {
        var messages = await authFetch("/messages");
        if (!messages) return;                       // 401: authFetch ya redirige a login
        render(messages);
    }

    async function load() {
        try {
            // El actor "Sistema" genera al abrir la pantalla. Es idempotente: si los mensajes
            // de hoy ya existen, no se duplican.
            await authFetch("/recommendations/generate", { method: "POST" });
            if (!localStorage.getItem("token")) return;
            await reload();
        } catch (error) {
            console.error("Error al cargar los mensajes:", error);
            showError("Could not load your messages. " + error.message);
        }
    }

    load();
});

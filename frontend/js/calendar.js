// Lógica de la pantalla Calendar
$(document).ready(function () {

    // Solo se ejecute en calendar.html
    var grid = document.getElementById("weekGrid");
    if (!grid) return;

    // Si no hay token de sesión, redige a login
    var token = localStorage.getItem("token");
    if (!token) {
        window.location.href = "login.html";
        return;
    }

    var HOUR_PX = 72;
    var PX_PER_MIN = HOUR_PX / 60;
    var DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
    var MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

    var weekLabel = document.getElementById("weekLabel");
    var emptyMsg = document.getElementById("calendarEmpty");

    var habitMap = {};                      // id -> { name, importance }.
    var weekStart = mondayOf(todayStr());   // Lunes

    // --- Utilidades de fecha ("YYYY-MM-DD") ---------------------------------

    // Devuelve la fecha de hoy
    function todayStr() {
        var d = new Date();
        return d.getFullYear() + "-" +
            String(d.getMonth() + 1).padStart(2, "0") + "-" +
            String(d.getDate()).padStart(2, "0");
    }

    // Lunes de la semana que contiene 'dateStr'
    function mondayOf(dateStr) {
        var d = new Date(dateStr + "T00:00:00");
        var offset = (d.getDay() + 6) % 7;              // días transcurridos desde el lunes
        return SessionForm.addDays(dateStr, -offset);
    }

    // Calcula los minutos desde media noche
    function minutesOf(timeStr) {
        var p = timeStr.split(":");
        return parseInt(p[0], 10) * 60 + parseInt(p[1], 10);
    }

    // Formatea Date a -> 'Jan 1'
    function formatDay(dateStr) {
        var d = new Date(dateStr + "T00:00:00");
        return MONTHS[d.getMonth()] + " " + d.getDate();
    }

    // --- Avisos de error (visibles, no solo en consola) ---------------------

    var errorMsg = null;    // Banner de error creado bajo demanda

    // Muestra un aviso de error sobre la rejilla, reutilizando el estilo .emptyState.
    function showError(message) {
        if (!errorMsg) {
            errorMsg = document.createElement("p");
            errorMsg.className = "emptyState";
            errorMsg.id = "calendarError";
            grid.parentNode.insertBefore(errorMsg, grid);
        }
        errorMsg.textContent = message;
        errorMsg.hidden = false;
    }

    // Oculta el aviso de error (p. ej. tras una carga correcta).
    function clearError() {
        if (errorMsg) errorMsg.hidden = true;
    }

    // --- Carga de datos -----------------------------------------------------

    // Primero los Habit (nombre e importancia) y luego las Sessions
    async function loadHabitsThenSessions() {
        try {
            var habits = await authFetch("/habits");
            if (!habits) return;    // 401: authFetch ya está redirigiendo a login
            habitMap = {};
            habits.forEach(function (h) {
                habitMap[h.id] = { name: h.name, type: h.type, importance: h.importance };
            });
            emptyMsg.hidden = habits.length > 0;
            await loadSessions();
        } catch (error) {
            console.error("Error al cargar los hábitos:", error);
            showError("Could not load your habits. " + error.message);
        }
    }

    // Pide las sesiones de la semana visible y re-renderiza.
    async function loadSessions() {
        var weekEnd = SessionForm.addDays(weekStart, 6);
        // Pedimos también el día anterior por si hay alguna sesión del Domingo pasado
        // que termine dentro de la semana actual y poder pintarla.
        var fetchFrom = SessionForm.addDays(weekStart, -1);
        try {
            var sessions = await authFetch(`/sessions?from=${fetchFrom}&to=${weekEnd}`);
            if (!sessions) return;  // 401: authFetch ya está redirigiendo a login
            clearError();
            render(sessions);
        } catch (error) {
            console.error("Error al cargar las sesiones:", error);
            showError("Could not load your sessions. " + error.message);
        }
    }

    // --- Render de la rejilla -----------------------------------------------

    // Crea un elemento con clase y texto opcionales (evita repetir createElement).
    function el(tag, className, text) {
        var node = document.createElement(tag);
        if (className) node.className = className;
        if (text != null) node.textContent = text;
        return node;
    }

    // Orquesta el pintado de la semana: cabecera + columna de horas + 7 columnas de día.
    function render(sessions) {
        var today = todayStr();
        var weekEnd = SessionForm.addDays(weekStart, 6);
        weekLabel.textContent = formatDay(weekStart) + " - " + formatDay(weekEnd) +
            " " + weekStart.slice(0, 4);

        // Fechas ("YYYY-MM-DD") de los 7 días de la semana visible
        var days = [];
        for (var i = 0; i < 7; i++) days.push(SessionForm.addDays(weekStart, i));

        grid.innerHTML = "";    // Vacía la rejilla anterior
        grid.appendChild(buildWeekHeader(days, today));

        var body = el("div", "weekBody");
        body.appendChild(buildHoursColumn());
        days.forEach(function (dayStr) {
            body.appendChild(buildDayColumn(dayStr, sessions, today));
        });
        grid.appendChild(body);
    }

    // Cabecera (1ª fila): esquina vacía + una cabecera por cada día de la semana.
    function buildWeekHeader(days, today) {
        var head = el("div", "weekHead");
        head.appendChild(el("div", "weekHeadCorner"));
        days.forEach(function (dayDate, i) {
            var dh = el("div", "weekHeadDay" + (dayDate === today ? " isToday" : ""));
            dh.appendChild(el("span", "weekHeadName", DAY_NAMES[i]));
            dh.appendChild(el("span", "weekHeadDate", formatDay(dayDate)));
            head.appendChild(dh);
        });
        return head;
    }

    // Columna de la izquierda con las 24 etiquetas de hora.
    function buildHoursColumn() {
        var hoursCol = el("div", "hoursCol");
        for (var hr = 0; hr < 24; hr++) {
            var label = el("div", "hourLabel", String(hr).padStart(2, "0") + ":00");
            label.style.height = HOUR_PX + "px";
            hoursCol.appendChild(label);
        }
        return hoursCol;
    }

    // Columna de un día: 24 celdas de fondo + los "chips" de las sesiones,
    // ya repartidos en columnas para que los solapamientos no se pisen.
    function buildDayColumn(dayStr, sessions, today) {
        var col = el("div", "dayCol" + (dayStr === today ? " isToday" : ""));
        col.style.height = (24 * HOUR_PX) + "px";

        // Celdas de fondo, con la misma altura que la columna de horas
        for (var hc = 0; hc < 24; hc++) {
            var cell = el("div", "dayHourCell");
            cell.style.height = HOUR_PX + "px";
            col.appendChild(cell);
        }

        // Clasifica las sesiones en head (comienza ese día) o tail (overnight que
        // termina ese día, distinto del día en que empezó).
        var segs = [];
        sessions.forEach(function (s) {
            if (s.date === dayStr) segs.push({ session: s, segment: "head" });
            else if (s.end_date === dayStr && s.end_date !== s.date) segs.push({ session: s, segment: "tail" });
        });

        // Calcula los límites verticales de cada tramo
        segs.forEach(function (seg) {
            var b = segmentBounds(seg.session, seg.segment);
            seg.startMin = b.topMin;
            seg.endMin = b.topMin + b.heightMin;
        });

        // Reparte los solapamientos en columnas
        layoutColumns(segs);

        // Pinta cada tramo
        segs.forEach(function (seg) {
            var chip = buildEvent(seg.session, seg.segment);
            if (seg.cols > 1) {
                var w = 100 / seg.cols;
                chip.style.left = "calc(" + (w * seg.col) + "% + 2px)";
                chip.style.width = "calc(" + w + "% - 4px)";
                chip.style.right = "auto";   // anula el right del CSS
            }
            col.appendChild(chip);
        });

        return col;
    }

    // Límites verticales de una Session (en minutos desde medianoche).
    function segmentBounds(session, segment) {
        var overnight = session.end_date && session.end_date !== session.date;
        var startMin = minutesOf(session.start_time);
        var endMin = minutesOf(session.end_time);
        if (segment === "tail") {                       // Si es la tail de una overnight
            return { topMin: 0, heightMin: endMin };
        }
        return { topMin: startMin, heightMin: (overnight ? 1440 : endMin) - startMin };
    }

    // Crea el "chip" de una Session
    function buildEvent(session, segment) {
        var overnight = session.end_date && session.end_date !== session.date;
        var habit = habitMap[session.habit_id] || { name: "Habit", type: null, importance: 2 };
        var bounds = segmentBounds(session, segment);
        var timeLabel = (segment === "tail")
            ? "→ " + session.end_time.slice(0, 5)
            : session.start_time.slice(0, 5);

        // Contenedor del chip; se calculan top y height a partir de los bounds
        var chip = el("div", "evt imp" + habit.importance);
        chip.style.top = (bounds.topMin * PX_PER_MIN) + "px";
        chip.style.height = Math.max(bounds.heightMin * PX_PER_MIN, 18) + "px";
        chip.title = habit.name + (habit.type ? " (" + habit.type + ")" : "") + " · " +
            session.start_time.slice(0, 5) + "–" + session.end_time.slice(0, 5) +
            (overnight ? " (+1)" : "");

        // Hora, nombre y (si lo tiene) tipo del hábito
        chip.appendChild(el("span", "evtTime", timeLabel));
        chip.appendChild(el("span", "evtName", habit.name));
        if (habit.type) chip.appendChild(el("span", "evtType", habit.type));

        // Acciones: editar (enlace) y borrar (botón)
        var actions = el("div", "evtActions");

        var edit = el("a", "evtBtn", "✏️");
        edit.href = "edit-session.html?id=" + session.id;
        edit.title = "Edit";
        actions.appendChild(edit);

        var del = el("button", "evtBtn", "🗑️");
        del.type = "button";
        del.title = "Delete";
        del.addEventListener("click", function () { deleteSession(session); });
        actions.appendChild(del);

        chip.appendChild(actions);
        return chip;
    }

    // Controla que las sesiones de un mismo día que ocurran en las mismas horas no se solapen,
    // creando un grupo de solape con varias columnas dentro del día.
    // Todos los segmentos tienen:
    //  - .col: en qué columna se pinta
    //  - .cols: nº máximo de eventos del grupo de solape
    function layoutColumns(segments) {
        // Ordena los eventos por min. de inicio, en caso de empate por fin.
        segments.sort(function (a, b) {
            return a.startMin - b.startMin || a.endMin - b.endMin;
        });

        var columns = [];       // columns[c] guarda el endMin del último evento puesto en la columna c
                                //  sirve para poder reutilizar columnas dentro del mismo grupo de solape
        var group = [];         // Eventos del grupo de solape que se está construyendo
        var groupEnd = -1;      // Fin máximo alcanzado por el grupo
                                //  sirve para comprobar si un grupo de solape ha terminado o no

        // A todos los eventos del grupo les pone el atributo cols = columns.length,
        // después resetea todo para el siguiente.
        function closeGroup() {
            for (var i = 0; i < group.length; i++) {
                group[i].cols = columns.length;
            }
            columns = [];
            group = [];
            groupEnd = -1;
        }

        segments.forEach(function (seg) {
            // El grupo de solape se cierra cuando llega un evento que empieza
            // después del fin de todos los elementos del grupo
            // Comprueba que el evento esté dentro del grupo de colapse
            if (group.length > 0 && seg.startMin >= groupEnd) closeGroup();

            // Recorre las columnas del grupo de colapse buscando si el evento puede insertarse
            // en alguna columna ya existente (reutilizarla)
            var placed = false;
            for (var c = 0; c < columns.length; c++) {
                // columns[c] está libre si: groupEnd > startMin >= columns[c],
                // es decir, el evento está dentro del grupo de colapse (groupEnd > startMin)
                // y comienza después del último evento insertado en la columna (startMin >= columns[c])
                if (seg.startMin >= columns[c]) {
                    // Actualiza columns[c] y guarda seg.col = c
                    columns[c] = seg.endMin;
                    seg.col = c;
                    placed = true;
                    break;
                }
            }

            // Si ninguna estaba libre, abre una nueva columna nueva
            if (!placed) {
                seg.col = columns.length;
                columns.push(seg.endMin);
            }

            // Actualiza group y groupEnd
            group.push(seg);
            groupEnd = Math.max(groupEnd, seg.endMin);
        });
        closeGroup();       // Cierra el último grupo de solape
    }

    // Borra la Session tras confirmación y refresca la semana
    async function deleteSession(session) {
        var habit = habitMap[session.habit_id] || { name: "this habit" };
        // Confirmación
        if (!window.confirm(`Delete this session of "${habit.name}"?`)) return;

        try {
            await authFetch(`/sessions/${session.id}`, { method: "DELETE" });
            // authFetch devuelve null tanto en 204 (éxito) como en 401 (redirigiendo).
            // Si fue un 401 ya no hay token: no refrescamos porque la página va a login.
            if (!localStorage.getItem("token")) return;
            loadSessions();
        } catch (error) {
            console.error("Error al borrar la sesión:", error);
            alert(error.message || "Could not delete the session");
        }
    }

    // --- Navegación de semana -----------------------------------------------

    document.getElementById("prevWeek").addEventListener("click", function () {
        weekStart = SessionForm.addDays(weekStart, -7);
        loadSessions();
    });
    document.getElementById("nextWeek").addEventListener("click", function () {
        weekStart = SessionForm.addDays(weekStart, 7);
        loadSessions();
    });
    document.getElementById("todayWeek").addEventListener("click", function () {
        weekStart = mondayOf(todayStr());
        loadSessions();
    });

    loadHabitsThenSessions();
});

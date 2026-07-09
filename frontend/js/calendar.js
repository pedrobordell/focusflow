// Lógica de la pantalla Calendar: vista semanal por horas de las sesiones del usuario.
// Reutiliza API_BASE de api.js y SessionForm.addDays/handleUnauthorized de session-form.js.
$(document).ready(function () {

    // Solo corre en la pantalla del calendario
    var grid = document.getElementById("weekGrid");
    if (!grid) return;

    // Guardia de sesión: sin token, de vuelta a login
    var token = localStorage.getItem("token");
    if (!token) {
        window.location.href = "login.html";
        return;
    }

    var HOUR_PX = 72;                       // alto de cada hora en la rejilla (deja ver el contenido del chip)
    var PX_PER_MIN = HOUR_PX / 60;
    var DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
    var MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

    var weekLabel = document.getElementById("weekLabel");
    var emptyMsg = document.getElementById("calendarEmpty");

    var habitMap = {};                      // id -> { name, importance }
    var weekStart = mondayOf(todayStr());   // lunes (ISO) de la semana visible

    // --- Utilidades de fecha ("YYYY-MM-DD") ---------------------------------

    function todayStr() {
        var d = new Date();
        return d.getFullYear() + "-" +
            String(d.getMonth() + 1).padStart(2, "0") + "-" +
            String(d.getDate()).padStart(2, "0");
    }

    // Lunes de la semana que contiene 'dateStr' (ISO: la semana empieza en lunes).
    function mondayOf(dateStr) {
        var d = new Date(dateStr + "T00:00:00");
        var offset = (d.getDay() + 6) % 7;  // días transcurridos desde el lunes
        return SessionForm.addDays(dateStr, -offset);
    }

    // "HH:MM:SS" o "HH:MM" -> minutos desde medianoche.
    function minutesOf(timeStr) {
        var p = timeStr.split(":");
        return parseInt(p[0], 10) * 60 + parseInt(p[1], 10);
    }

    // "YYYY-MM-DD" -> "Jul 7"
    function formatDay(dateStr) {
        var d = new Date(dateStr + "T00:00:00");
        return MONTHS[d.getMonth()] + " " + d.getDate();
    }

    // --- Carga de datos -----------------------------------------------------

    // Primero los hábitos (nombre y color) y, una vez listos, las sesiones de la semana.
    function loadHabitsThenSessions() {
        fetch(`${API_BASE}/habits`, { headers: { "Authorization": `Bearer ${token}` } })
            .then(function (response) {
                if (response.status === 401) { SessionForm.handleUnauthorized(); return null; }
                return response.json();
            })
            .then(function (habits) {
                if (!habits) return;
                habitMap = {};
                habits.forEach(function (h) {
                    habitMap[h.id] = { name: h.name, type: h.type, importance: h.importance };
                });
                emptyMsg.hidden = habits.length > 0;
                return loadSessions();
            })
            .catch(function (error) {
                console.error("Error al cargar los hábitos:", error);
            });
    }

    // Pide las sesiones de la semana visible y re-renderiza.
    function loadSessions() {
        var weekEnd = SessionForm.addDays(weekStart, 6);
        // Pedimos también el día anterior para poder pintar la "cola" de una sesión
        // que empezó justo antes de la semana y termina dentro de ella.
        var fetchFrom = SessionForm.addDays(weekStart, -1);
        return fetch(`${API_BASE}/sessions?from=${fetchFrom}&to=${weekEnd}`, {
            headers: { "Authorization": `Bearer ${token}` }
        })
            .then(function (response) {
                if (response.status === 401) { SessionForm.handleUnauthorized(); return null; }
                return response.json();
            })
            .then(function (sessions) {
                if (!sessions) return;
                render(sessions);
            })
            .catch(function (error) {
                console.error("Error al cargar las sesiones:", error);
            });
    }

    // --- Render de la rejilla -----------------------------------------------

    function render(sessions) {
        var today = todayStr();
        var weekEnd = SessionForm.addDays(weekStart, 6);
        weekLabel.textContent = formatDay(weekStart) + " – " + formatDay(weekEnd) +
            " " + weekStart.slice(0, 4);

        grid.innerHTML = "";

        // Cabecera: esquina vacía + 7 cabeceras de día
        var head = document.createElement("div");
        head.className = "weekHead";
        var corner = document.createElement("div");
        corner.className = "weekHeadCorner";
        head.appendChild(corner);

        var days = [];
        for (var i = 0; i < 7; i++) {
            var dayDate = SessionForm.addDays(weekStart, i);
            days.push(dayDate);

            var dh = document.createElement("div");
            dh.className = "weekHeadDay" + (dayDate === today ? " isToday" : "");
            var name = document.createElement("span");
            name.className = "weekHeadName";
            name.textContent = DAY_NAMES[i];
            var num = document.createElement("span");
            num.className = "weekHeadDate";
            num.textContent = formatDay(dayDate);
            dh.appendChild(name);
            dh.appendChild(num);
            head.appendChild(dh);
        }
        grid.appendChild(head);

        // Cuerpo: columna de horas + 7 columnas de día
        var body = document.createElement("div");
        body.className = "weekBody";

        var hoursCol = document.createElement("div");
        hoursCol.className = "hoursCol";
        for (var hr = 0; hr < 24; hr++) {
            var label = document.createElement("div");
            label.className = "hourLabel";
            label.style.height = HOUR_PX + "px";
            label.textContent = String(hr).padStart(2, "0") + ":00";
            hoursCol.appendChild(label);
        }
        body.appendChild(hoursCol);

        for (var d = 0; d < 7; d++) {
            var dayStr = days[d];
            var col = document.createElement("div");
            col.className = "dayCol" + (dayStr === today ? " isToday" : "");
            col.style.height = (24 * HOUR_PX) + "px";

            // Celdas de hora de fondo: dibujan las líneas horarias con el MISMO
            // border que .hourLabel (así el grosor coincide con la columna de horas).
            for (var hc = 0; hc < 24; hc++) {
                var cell = document.createElement("div");
                cell.className = "dayHourCell";
                cell.style.height = HOUR_PX + "px";
                col.appendChild(cell);
            }

            // Recoger los tramos que caen en este día (cabeza el día de inicio; cola el
            // día en que termina una sesión que cruza medianoche).
            var segs = [];
            sessions.forEach(function (s) {
                if (s.date === dayStr) segs.push({ session: s, segment: "head" });
                else if (s.end_date === dayStr && s.end_date !== s.date) segs.push({ session: s, segment: "tail" });
            });

            // Calcular su intervalo [startMin, endMin) y repartir en columnas los solapados.
            segs.forEach(function (seg) {
                var b = segmentBounds(seg.session, seg.segment);
                seg.startMin = b.topMin;
                seg.endMin = b.topMin + b.heightMin;
            });
            layoutColumns(segs);

            // Pintar cada tramo; solo si hay solape se reparte el ancho en columnas.
            segs.forEach(function (seg) {
                var el = buildEvent(seg.session, seg.segment);
                if (seg.cols > 1) {
                    var w = 100 / seg.cols;
                    el.style.left = "calc(" + (w * seg.col) + "% + 2px)";
                    el.style.width = "calc(" + w + "% - 4px)";
                    el.style.right = "auto";   // anula el right:3px del CSS al fijar left+width
                }
                col.appendChild(el);
            });

            body.appendChild(col);
        }
        grid.appendChild(body);
    }

    // Límites verticales de un tramo dentro de su columna de día (en minutos desde
    // medianoche). 'segment' = "head" (día de inicio) o "tail" (continuación al día
    // siguiente en sesiones que cruzan medianoche). Lo usan buildEvent y layoutColumns.
    function segmentBounds(session, segment) {
        var overnight = session.end_date && session.end_date !== session.date;
        var startMin = minutesOf(session.start_time);
        var endMin = minutesOf(session.end_time);
        if (segment === "tail") {
            return { topMin: 0, heightMin: endMin };                       // medianoche -> fin
        }
        return { topMin: startMin, heightMin: (overnight ? 1440 : endMin) - startMin };
    }

    // Crea el "chip" de una sesión. 'segment' = "head" (día de inicio) o "tail"
    // (continuación en el día siguiente para sesiones que cruzan medianoche).
    // El chip ya NO es un enlace: se edita/borra con los iconos de abajo a la derecha.
    function buildEvent(session, segment) {
        var overnight = session.end_date && session.end_date !== session.date;
        var habit = habitMap[session.habit_id] || { name: "Habit", type: null, importance: 2 };

        // La cabeza va de inicio a medianoche (si es overnight) o al fin (mismo día);
        // la cola va de medianoche al fin, en la columna del día siguiente.
        var bounds = segmentBounds(session, segment);
        var timeLabel = (segment === "tail")
            ? "→ " + session.end_time.slice(0, 5)
            : session.start_time.slice(0, 5);

        var el = document.createElement("div");
        el.className = "evt imp" + habit.importance;
        el.style.top = (bounds.topMin * PX_PER_MIN) + "px";
        el.style.height = Math.max(bounds.heightMin * PX_PER_MIN, 18) + "px";
        el.title = habit.name + (habit.type ? " (" + habit.type + ")" : "") + " · " +
            session.start_time.slice(0, 5) + "–" + session.end_time.slice(0, 5) +
            (overnight ? " (+1)" : "");

        var time = document.createElement("span");
        time.className = "evtTime";
        time.textContent = timeLabel;
        el.appendChild(time);

        var name = document.createElement("span");
        name.className = "evtName";
        name.textContent = habit.name;
        el.appendChild(name);

        // El tipo solo si el hábito lo tiene (es opcional)
        if (habit.type) {
            var type = document.createElement("span");
            type.className = "evtType";
            type.textContent = habit.type;
            el.appendChild(type);
        }

        // Acciones: editar (navega) y borrar (en el sitio), abajo a la derecha
        var actions = document.createElement("div");
        actions.className = "evtActions";

        var edit = document.createElement("a");
        edit.className = "evtBtn";
        edit.href = "edit-session.html?id=" + session.id;
        edit.title = "Edit";
        edit.textContent = "✏️";
        actions.appendChild(edit);

        var del = document.createElement("button");
        del.type = "button";
        del.className = "evtBtn";
        del.title = "Delete";
        del.textContent = "🗑️";
        del.addEventListener("click", function () { deleteSession(session); });
        actions.appendChild(del);

        el.appendChild(actions);
        return el;
    }

    // Reparte en columnas los tramos que se solapan en el tiempo dentro de un día,
    // para pintarlos lado a lado en vez de unos encima de otros. A cada tramo le fija
    // { col, cols }: su columna y el nº total de columnas de su grupo de solape.
    // Algoritmo clásico: ordenar por inicio, colocar cada evento en la primera columna
    // cuyo último evento ya terminó (si no, abrir una nueva); un "grupo" se cierra al
    // llegar un evento que empieza en o después del fin máximo del grupo.
    function layoutColumns(segments) {
        segments.sort(function (a, b) { return a.startMin - b.startMin || a.endMin - b.endMin; });
        var columns = [];      // fin del último evento colocado en cada columna del grupo actual
        var group = [];        // tramos del grupo de solape en curso
        var groupEnd = -1;     // fin máximo alcanzado por el grupo

        function closeGroup() {
            for (var i = 0; i < group.length; i++) group[i].cols = columns.length;
            columns = []; group = []; groupEnd = -1;
        }

        segments.forEach(function (seg) {
            if (group.length > 0 && seg.startMin >= groupEnd) closeGroup();  // sin solape -> nuevo grupo
            var placed = false;
            for (var c = 0; c < columns.length; c++) {
                if (seg.startMin >= columns[c]) { columns[c] = seg.endMin; seg.col = c; placed = true; break; }
            }
            if (!placed) { seg.col = columns.length; columns.push(seg.endMin); }
            group.push(seg);
            groupEnd = Math.max(groupEnd, seg.endMin);
        });
        closeGroup();
    }

    // Borra una sesión tras confirmación y refresca la semana visible.
    // Calcado del borrado de habit-list.js.
    function deleteSession(session) {
        var habit = habitMap[session.habit_id] || { name: "this habit" };
        if (!window.confirm(`Delete this session of "${habit.name}"?`)) return;

        fetch(`${API_BASE}/sessions/${session.id}`, {
            method: "DELETE",
            headers: { "Authorization": `Bearer ${token}` }
        })
            .then(function (response) {
                if (response.status === 401) { SessionForm.handleUnauthorized(); return; }
                if (response.status === 204) { loadSessions(); return; }
                alert("Could not delete the session");
            })
            .catch(function (error) {
                console.error("Error al borrar la sesión:", error);
                alert("Error connecting to server");
            });
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

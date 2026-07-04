// Navegación dirigida por configuración para las páginas autenticadas.
// Nivel 1: secciones (se eligen con la hamburguesa). Nivel 2: subsecciones = pantallas
// de la sección actual (se muestran en el header). La sección actual se deduce de la página abierta.

// Única fuente de verdad. Para añadir pantallas futuras, ampliar esta estructura.
const NAV_SECTIONS = [
    {
        id: "user",
        label: "User",
        screens: [
            { label: "Dashboard", href: "dashboard.html" },
            { label: "Profile", href: "profile.html" },
        ],
    },
    {
        id: "habits",
        label: "Habits and Sessions",
        screens: [
            { label: "Add habit", href: "add-habit.html" },
            { label: "Habit List", href: "habit-list.html" },
            { label: "Statistics", href: "statistics.html" },
            { label: "Add session", href: "add-session.html" },
            // Pantallas de detalle: pertenecen a la sección para la navegación pero no se
            // muestran como subsecciones en el header.
            { label: "Edit habit", href: "edit-habit.html", hidden: true },
            { label: "Edit session", href: "edit-session.html", hidden: true },
        ],
    },
    // Futuras: calendar, stats, ai, messages
];

$(document).ready(function () {
    var subsectionNav = document.getElementById("subsectionNav");
    if (!subsectionNav) return; // Solo actúa en páginas con header de navegación

    // Archivo actual (basename), p.ej. "profile.html". Fallback a la primera pantalla.
    var currentFile = window.location.pathname.split("/").pop() || NAV_SECTIONS[0].screens[0].href;

    // Sección que contiene la pantalla actual; si no aparece, la primera por defecto.
    var currentSection = NAV_SECTIONS.find(function (section) {
        return section.screens.some(function (screen) { return screen.href === currentFile; });
    }) || NAV_SECTIONS[0];

    // Subsecciones (pantallas) de la sección actual -> header
    currentSection.screens.forEach(function (screen) {
        if (screen.hidden) return; // pantallas de detalle no van en el header
        var isActive = screen.href === currentFile;
        $("<li>").append(
            $("<a>")
                .addClass("navLink" + (isActive ? " active" : ""))
                .attr("href", screen.href)
                .text(screen.label)
        ).appendTo(subsectionNav);
    });

    // Secciones -> cajón lateral de la hamburguesa
    var sectionMenu = document.getElementById("sectionMenu");
    var sectionList = document.getElementById("sectionList");
    if (sectionMenu && sectionList) {
        NAV_SECTIONS.forEach(function (section) {
            var isActive = section.id === currentSection.id;
            $("<a>")
                .addClass("sectionItem" + (isActive ? " active" : ""))
                .attr("href", section.screens[0].href) // pantalla por defecto de la sección
                .attr("role", "menuitem")
                .text(section.label)
                .appendTo(sectionList);
        });
    }

    // Abrir / cerrar el cajón
    var navToggle = document.getElementById("navToggle");
    if (navToggle && sectionMenu) {
        var logo = document.querySelector(".logo");

        // El ancho llega hasta donde termina el .logo (su borde derecho)
        function applyWidth() {
            if (logo) {
                sectionMenu.style.width = logo.getBoundingClientRect().right + "px";
            }
        }

        function openMenu() {
            applyWidth();
            sectionMenu.classList.add("open");
            navToggle.setAttribute("aria-expanded", "true");
            sectionMenu.setAttribute("aria-hidden", "false");
        }

        function closeMenu() {
            sectionMenu.classList.remove("open");
            navToggle.setAttribute("aria-expanded", "false");
            sectionMenu.setAttribute("aria-hidden", "true");
        }

        navToggle.addEventListener("click", function (e) {
            e.stopPropagation();
            if (sectionMenu.classList.contains("open")) closeMenu();
            else openMenu();
        });

        // Botón de cerrar del propio cajón
        var closeBtn = document.getElementById("sectionMenuClose");
        if (closeBtn) {
            closeBtn.addEventListener("click", closeMenu);
        }

        // Cerrar al hacer clic fuera
        document.addEventListener("click", function (e) {
            if (sectionMenu.classList.contains("open") &&
                !sectionMenu.contains(e.target) && e.target !== navToggle) {
                closeMenu();
            }
        });

        // Cerrar con Escape
        document.addEventListener("keydown", function (e) {
            if (e.key === "Escape") closeMenu();
        });

        // Mantener el borde alineado con el .logo al redimensionar
        window.addEventListener("resize", function () {
            if (sectionMenu.classList.contains("open")) applyWidth();
        });
    }
});

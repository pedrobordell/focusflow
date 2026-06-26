$(document).ready(function () {
    var toggle = document.getElementById("themeToggle");
    var select = document.getElementById("themeSelect");

    // Aplica un tema y mantiene sincronizados localStorage, el icono del botón y el selector.
    // Fuente de verdad: la clase html.light + localStorage.theme.
    function applyTheme(isLight) {
        document.documentElement.classList.toggle("light", isLight);
        localStorage.setItem("theme", isLight ? "light" : "dark");

        // Pone en el botón el icono del tema al que se cambiaría al pulsar
        if (toggle) {
            toggle.textContent = isLight ? "🌙" : "☀";
            toggle.setAttribute("aria-label", isLight ? "Switch to dark mode" : "Switch to light mode");
        }
        if (select) {
            select.value = isLight ? "light" : "dark";
        }
    }

    // Estado inicial según la clase ya aplicada (el <head> la añade antes de pintar)
    applyTheme(document.documentElement.classList.contains("light"));

    if (toggle) {
        toggle.addEventListener("click", function () {
            applyTheme(!document.documentElement.classList.contains("light"));
        });
    }

    if (select) {
        select.addEventListener("change", function () {
            applyTheme(select.value === "light");
        });
    }
});

$(document).ready(function () {
    var toggle = document.getElementById("themeToggle");

    // Pone en el botón el icono del tema al que se cambiaría al pulsar
    function applyIcon() {
        if (!toggle) return;
        var isLight = document.documentElement.classList.contains("light");
        toggle.textContent = isLight ? "🌙" : "☀";
        toggle.setAttribute("aria-label", isLight ? "Switch to dark mode" : "Switch to light mode");
    }

    applyIcon();

    if (toggle) {
        toggle.addEventListener("click", function () {
            var isLight = document.documentElement.classList.toggle("light");
            localStorage.setItem("theme", isLight ? "light" : "dark");
            applyIcon();
        });
    }
});

// Lógica de la pantalla Perfil. Reutiliza API_BASE y extractError de api.js.
$(document).ready(function () {

    // Solo corre en la pantalla de perfil
    if (!document.getElementById("profileContainer")) return;

    // Guardia de sesión: sin token, de vuelta a login
    var token = localStorage.getItem("token");
    if (!token) {
        window.location.href = "login.html";
        return;
    }

    // Carga los datos del usuario autenticado y rellena la sección de cuenta
    fetch(`${API_BASE}/auth/me`, {
        headers: { "Authorization": `Bearer ${token}` }
    })
        .then(function (response) {
            if (response.status === 401) {
                // Token caducado o inválido: limpiar y volver a login
                localStorage.removeItem("token");
                window.location.href = "login.html";
                return null;
            }
            return response.json();
        })
        .then(function (data) {
            if (!data) return;
            $("#profileUsername").text(data.username);
            $("#profileEmail").text(data.email);
        })
        .catch(function (error) {
            console.error("Error al cargar el perfil:", error);
        });

    // El selector de tema (#themeSelect) lo gestiona theme.js.
});

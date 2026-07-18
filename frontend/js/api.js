const API_BASE = "http://localhost:8000";

// Extrae un mensaje legible de una respuesta de error de FastAPI.
// detail puede ser un string (400/401) o una lista de errores de validación (422).
function extractError(data) {
    if (!data || !data.detail) return null;
    if (typeof data.detail === "string") return data.detail;
    if (Array.isArray(data.detail)) return data.detail.map(function(d) { return d.msg; }).join("\n");
    return null;
}

// Petición autenticada a la API con manejo de errores centralizado.
// - Añade la cabecera Authorization con el token de localStorage.
// - Ante un 401 (sesión caducada/no válida) limpia el token y vuelve a login.
// - Ante cualquier otro estado de error lanza un Error con el mensaje del backend.
// - Devuelve el JSON de la respuesta (o null en 204 No Content y en 401).
// 'path' es relativo a API_BASE (p. ej. "/habits"); 'options' es el objeto de fetch.
async function authFetch(path, options) {
    options = options || {};
    var token = localStorage.getItem("token");
    var headers = Object.assign({ "Authorization": `Bearer ${token}` }, options.headers || {});
    var response = await fetch(`${API_BASE}${path}`, Object.assign({}, options, { headers: headers }));

    if (response.status === 401) {
        // Sesión no válida: limpiar token y redirigir. Cortamos el flujo devolviendo null.
        localStorage.removeItem("token");
        window.location.href = "login.html";
        return null;
    }
    if (response.status === 204) return null;   // Sin cuerpo (p. ej. DELETE con éxito)

    var data = null;
    try {
        data = await response.json();
    } catch (e) {
        data = null;    // Respuesta sin cuerpo JSON válido
    }
    if (!response.ok) {
        throw new Error(extractError(data) || `Request failed (${response.status})`);
    }
    return data;
}

$(document).ready(function() {

    // Guardia de sesión: las páginas protegidas requieren token; si no hay, volver a login.
    // Cubre el dashboard y cualquier contenedor marcado con la clase .requiresAuth.
    var requiresAuth = document.getElementById("dashboardContainer") || document.querySelector(".requiresAuth");
    if (requiresAuth && !localStorage.getItem("token")) {
        window.location.href = "login.html";
        return;
    }

    // REGISTRO
    var registerForm = document.getElementById("registerContainer");
    if (registerForm) {
        registerForm.addEventListener("submit", async (e) => {
            e.preventDefault();

            var username = $("#usernameRegister").val();
            var email = $("#emailRegister").val();
            var password = $("#passwordRegister").val();
            var pConfirm = $("#pConfirmRegister").val();

            // Validación en cliente (el servidor vuelve a validar)
            $(".errorMsg").hide();
            var valid = true;
            if (username.length < 3 || username.length > 50) { $("#usernameError").show(); valid = false; }
            if (!emailValidation(email)) { $("#emailError").show(); valid = false; }
            if (password.length < 6) { $("#passwordError").show(); valid = false; }
            if (password !== pConfirm) { $("#pConfirmError").show(); valid = false; }
            if (!valid) return;

            try {
                var response = await fetch(`${API_BASE}/auth/register`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ username: username, email: email, password: password })
                });
                var data = await response.json();

                if (response.ok) {
                    // El registro NO devuelve token; se inicia sesión por separado.
                    // Redirigimos a login con el email prefijado.
                    window.location.href = "login.html?emailLogin=" + encodeURIComponent(email);
                } else {
                    alert(extractError(data) || "Registration failed");
                }
            } catch (error) {
                console.error(error);
                alert("Error connecting to server");
            }
        });
    }

    // LOGIN
    var loginForm = document.getElementById("loginContainer");
    if (loginForm) {
        loginForm.addEventListener("submit", async (e) => {
            e.preventDefault();

            var email = $("#emailLogin").val();
            var password = $("#passwordLogin").val();

            $(".errorMsg").hide();
            var valid = true;
            if (!emailValidation(email)) { $("#emailError").show(); valid = false; }
            if (password.length < 6) { $("#passwordError").show(); valid = false; }
            if (!valid) return;

            try {
                var response = await fetch(`${API_BASE}/auth/login`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ email: email, password: password })
                });
                var data = await response.json();

                if (response.ok) {
                    localStorage.setItem("token", data.access_token);
                    window.location.href = "dashboard.html";
                } else {
                    alert(extractError(data) || "Login failed");
                }
            } catch (error) {
                console.error(error);
                alert("Error connecting to server");
            }
        });
    }

    // LOGOUT
    var logoutBtn = document.getElementById("logoutBtn");
    if (logoutBtn) {
        logoutBtn.addEventListener("click", async (e) => {
            e.preventDefault();
            var token = localStorage.getItem("token");
            if (token) {
                try {
                    await fetch(`${API_BASE}/auth/logout`, {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                            "Authorization": `Bearer ${token}`
                        }
                    });
                } catch (error) {
                    console.log("Error al comunicar con el servidor:", error);
                }
            }
            localStorage.removeItem("token");
            window.location.href = "index.html";
        });
    }
});

$(document).ready(function() {
    
    var registerForm = document.getElementById("registerContainer")

    if(registerForm) {
        registerForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            var username = document.getElementById("usernameRegister").value;
            var email = document.getElementById("emailRegister").value;
            var password = document.getElementById("passwordRegister").value;
            
            try {
                var response = await fetch("http://localhost:8000/auth/register", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        username: username,
                        email: email,
                        password: password
                    })
                });

                var data = await response.json();
                
                if (response.ok) {
                    localStorage.setItem("token", data.access_token);
                    window.location.href = "login.html";
                } else {
                    alert(data.detail || "Registration failed");
                }
                
            } catch (error) {
                console.error(error);
                alert("Error connecting to server");
            }
        });
    }

    var loginForm = document.getElementById("loginContainer");

    if (loginForm) {
        loginForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            var email = document.getElementById("emailLogin").value;
            var password = document.getElementById("passwordLogin").value;
        
            try {
                var response = await fetch("http://localhost:8000/auth/login", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        email: email,
                        password: password
                    })
                });
        
                var data = await response.json();
        
                if (response.ok) {
                    localStorage.setItem("token", data.access_token);
                    window.location.href = "dashboard.html";
                } else {
                    alert(data.detail || "Login failed");
                }
        
            } catch (error) {
                console.error(error);
                alert("Error connecting to server");
            }
        });
    }

    var logoutBtn = document.getElementById("logoutBtn");

    if(logoutBtn) {
        logoutBtn.addEventListener("click", async (e) => {
            e.preventDefault();
            var token = localStorage.getItem("token");
            if(token) {
                try {
                    await fetch("http://localhost:8000/auth/logout", {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                            "Authorization": "Bearer ${token}"
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
$(document).ready(function() {
    
    document.getElementById("registerContainer").addEventListener("submit", async (e) => {
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

    document.getElementById("loginContainer").addEventListener("submit", async (e) => {
        e.preventDefault();
        var email = document.getElementById("emailLogin").value;
        var password = document.getElementById("passwordLogin").value;
    
        try {
            var response = await fetch("http://localhost:8000/login", {
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
                window.location.href = "index.html";
            } else {
                alert(data.detail || "Login failed");
            }
    
        } catch (error) {
            console.error(error);
            alert("Error connecting to server");
        }
    });
});
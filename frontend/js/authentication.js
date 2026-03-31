$(document).ready(function() {

    $("#indexContainer").submit(function(e) {
        var valido = true;

        var email = $("#emailLogin").val();
        
        $(".errorMsg").hide();

        if (!emailValidation(email)) {
            $("#errorEmail").show();
            valido = false;
        }

        if (!valido) {
            e.preventDefault();
        }
    });

    $("#loginContainer").submit(function(e) {
        var valido = true;

        var email = $("#emailLogin").val();
        var password = $("#passwordLogin").val();

        $(".errorMsg").hide();

        if (!emailValidation(email)) {
            $("#emailError").show();
            valido = false;
        }

        if (password.length < 6) {
            $("#passwordError").show();
            valido = false;
        }

        if (!valido) {
            e.preventDefault();
        }
    });

    $("#registerContainer").submit(function(e) {
        var valido = true;

        var username = $("#usernameRegister").val();
        var email = $("#emailRegister").val();
        var password = $("#passwordRegister").val();
        var pConfirm = $("#pConfirmRegister").val();

        $(".errorMsg").hide();

        if (username.length > 16) {
            $("#usernameError").show();
        }

        if (!emailValidation(email)) {
            $("#emailError").show();
            valido = false;
        }

        if (password.length < 6) {
            $("#passwordError").show();
            valido = false;
        }

        if (password !== pConfirm) {
            $("#pConfirmError").show();
            valido = false;
        }

        if (!valido) {
            e.preventDefault();
        }
    });

    function emailValidation(email) {
        var regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return regex.test(email);
    };
});

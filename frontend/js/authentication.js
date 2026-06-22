// Validación de email reutilizable (global; la usa también api.js)
function emailValidation(email) {
    var regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return regex.test(email);
}

$(document).ready(function() {

    // Landing (index.html): valida el email antes de redirigir a login.html
    $("#indexContainer").submit(function(e) {
        $(".errorMsg").hide();
        if (!emailValidation($("#emailLogin").val())) {
            $("#errorEmail").show();
            e.preventDefault();
        }
    });

    // Si llega ?emailLogin=... (desde la landing o tras registrarse), rellena el email
    var params = new URLSearchParams(window.location.search);
    var email = params.get('emailLogin');
    if (email && $('#emailLogin').length) {
        $('#emailLogin').val(email);
    }
});

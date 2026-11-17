document.addEventListener("DOMContentLoaded", function () {

    // ==========================================
    // CAMBIAR ENTRE INICIO DE SESIÓN Y REGISTRO
    // ==========================================

    const vistaLogin = document.getElementById("vistaLogin");
    const vistaRegistro = document.getElementById("vistaRegistro");

    const tabLogin = document.getElementById("tabLogin");
    const tabRegistro = document.getElementById("tabRegistro");

    const btnRegistroInferior = document.getElementById("btnRegistroInferior");
    const btnVolver = document.getElementById("btnVolver");

    function mostrarLogin() {

        vistaLogin.hidden = false;
        vistaRegistro.hidden = true;

        tabLogin.classList.add("tab-active");
        tabLogin.classList.remove("tab-register");

        tabRegistro.classList.remove("tab-active");
        tabRegistro.classList.add("tab-register");

    }

    function mostrarRegistro() {

        vistaLogin.hidden = true;
        vistaRegistro.hidden = false;

        tabRegistro.classList.add("tab-active");
        tabRegistro.classList.remove("tab-register");

        tabLogin.classList.remove("tab-active");
        tabLogin.classList.add("tab-register");

        // Limpiar campos de registro al abrir
        document.getElementById("registroForm").reset();

    }

    // BOTÓN SUPERIOR REGISTRARSE
    tabRegistro.addEventListener("click", mostrarRegistro);

    // BOTÓN INFERIOR REGÍSTRATE AQUÍ
    btnRegistroInferior.addEventListener("click", mostrarRegistro);

    // BOTÓN VOLVER
    btnVolver.addEventListener("click", mostrarLogin);


    // ==========================================
    // MOSTRAR / OCULTAR TODAS LAS CONTRASEÑAS
    // ==========================================

    const botonesPassword = document.querySelectorAll(".toggle-password");

    botonesPassword.forEach(function (boton) {

        boton.addEventListener("click", function () {

            const idInput = boton.dataset.target;
            const input = document.getElementById(idInput);
            const icono = boton.querySelector("i");

            if (!input || !icono) return;

            const mostrar = input.type === "password";

            input.type = mostrar ? "text" : "password";

            icono.classList.toggle("bi-eye", !mostrar);
            icono.classList.toggle("bi-eye-slash", mostrar);

            boton.setAttribute(
                "aria-label",
                mostrar ? "Ocultar contraseña" : "Mostrar contraseña"
            );

            boton.title = mostrar
                ? "Ocultar contraseña"
                : "Mostrar contraseña";

        });

    });


    // ==========================================
    // EVITAR DOBLE ENVÍO DEL LOGIN
    // ==========================================

    const loginForm = document.getElementById("loginForm");
    const btnLogin = document.getElementById("btnLogin");

    loginForm.addEventListener("submit", function () {

        if (!loginForm.checkValidity()) {
            return;
        }

        btnLogin.disabled = true;

        btnLogin.querySelector("span").textContent = "Validando...";

    });


    // ==========================================
    // VALIDAR REGISTRO DE CLIENTES
    // ==========================================

    const registroForm = document.getElementById("registroForm");

    const passwordRegistro = document.getElementById("nueva_password");
    const confirmarPassword = document.getElementById("confirmar_password");

    const btnCrear = document.getElementById("btnCrear");

    registroForm.addEventListener("submit", function (event) {

        // COMPROBAR QUE LAS CONTRASEÑAS COINCIDAN
        if (passwordRegistro.value !== confirmarPassword.value) {

            event.preventDefault();

            alert("Las contraseñas no coinciden.");

            confirmarPassword.focus();

            return;
        }

        // VALIDAR CAMPOS
        if (!registroForm.checkValidity()) {
            return;
        }

        // EVITAR DOBLE ENVÍO
        btnCrear.disabled = true;

        btnCrear.querySelector("span").textContent = "Creando cuenta...";

    });


    // ==========================================
    // RECUPERACIÓN DE CONTRASEÑA
    // ==========================================

    const forgotPassword = document.getElementById("forgotPassword");

    forgotPassword.addEventListener("click", function (event) {

        event.preventDefault();

        alert(
            "La recuperación de contraseña estará disponible próximamente. " +
            "Contacta al administrador del sistema."
        );

    });


    // ==========================================
    // ESTADO INICIAL
    // ==========================================

    mostrarLogin();

});
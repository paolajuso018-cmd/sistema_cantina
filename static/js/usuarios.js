
document.addEventListener("DOMContentLoaded", () => {

    const modal = document.getElementById("modalUsuario");
    const abrir = document.getElementById("abrirModalUsuario");
    const cerrar = document.getElementById("cerrarModalUsuario");
    const cancelar = document.getElementById("cancelarModalUsuario");

    const formulario = document.getElementById("formNuevoUsuario");

    const password = document.getElementById("nuevoPassword");
    const mostrarPassword = document.getElementById("mostrarPassword");


    // =====================================
    // ABRIR MODAL
    // =====================================

    function abrirModal() {

        if (!modal) return;

        modal.classList.add("visible");
        document.body.style.overflow = "hidden";

    }


    // =====================================
    // CERRAR MODAL
    // =====================================

    function cerrarModal() {

        if (!modal) return;

        modal.classList.remove("visible");
        document.body.style.overflow = "";

    }


    if (abrir) {
        abrir.addEventListener("click", abrirModal);
    }

    if (cerrar) {
        cerrar.addEventListener("click", cerrarModal);
    }

    if (cancelar) {
        cancelar.addEventListener("click", cerrarModal);
    }


    // Cerrar al hacer clic fuera del formulario

    if (modal) {

        modal.addEventListener("click", (event) => {

            if (event.target === modal) {
                cerrarModal();
            }

        });

    }


    // Cerrar con Escape

    document.addEventListener("keydown", (event) => {

        if (event.key === "Escape" && modal?.classList.contains("visible")) {
            cerrarModal();
        }

    });


    // =====================================
    // MOSTRAR / OCULTAR CONTRASEÑA
    // =====================================

    if (mostrarPassword && password) {

        mostrarPassword.addEventListener("click", () => {

            const mostrar = password.type === "password";

            password.type = mostrar ? "text" : "password";

            mostrarPassword.innerHTML = mostrar
                ? '<i class="bi bi-eye-slash"></i>'
                : '<i class="bi bi-eye"></i>';

            mostrarPassword.setAttribute(
                "aria-label",
                mostrar ? "Ocultar contraseña" : "Mostrar contraseña"
            );

        });

    }


    // =====================================
    // ESTADO VISUAL SELECCIONADO
    // =====================================

    const opcionesEstado = document.querySelectorAll(".opcion-estado");

    opcionesEstado.forEach((opcion) => {

        const radio = opcion.querySelector("input");

        radio.addEventListener("change", () => {

            opcionesEstado.forEach((elemento) => {
                elemento.classList.remove("activo-seleccionado");
            });

            opcion.classList.add("activo-seleccionado");

        });

    });


    // =====================================
    // VALIDACIÓN ANTES DE ENVIAR
    // =====================================

    if (formulario) {

        formulario.addEventListener("submit", (event) => {

            if (!formulario.checkValidity()) {

                event.preventDefault();
                formulario.reportValidity();

                return;

            }

        });

    }


    // =====================================
    // MODAL EDITAR USUARIO
    // =====================================

    const modalEditar = document.getElementById("modalEditarUsuario");

    const formularioEditar = document.getElementById("formEditarUsuario");

    const botonesEditar = document.querySelectorAll(".btn-abrir-edicion");

    const cerrarEditar = document.getElementById("cerrarModalEditar");

    const cancelarEditar = document.getElementById("cancelarModalEditar");


    function cerrarModalEdicion() {

        modalEditar.classList.remove("visible");

        document.body.style.overflow = "";

    }


    // Abrir y cargar los datos del usuario seleccionado

    botonesEditar.forEach((boton) => {

        boton.addEventListener("click", () => {

            const id = boton.dataset.id;

            document.getElementById("editarNombre").value =
                boton.dataset.nombre;

            document.getElementById("editarCorreo").value =
                boton.dataset.correo;

            document.getElementById("editarUsername").value =
                boton.dataset.username;

            document.getElementById("editarRol").value =
                boton.dataset.rol;

            document.getElementById("editarEstado").value =
                boton.dataset.estado;

            // La contraseña nunca se carga ni se muestra
            document.getElementById("editarPassword").value = "";

            const urlBase = formularioEditar.dataset.urlBase;

            formularioEditar.action =
                urlBase.replace(/0$/, id);

            modalEditar.classList.add("visible");

            document.body.style.overflow = "hidden";

        });

    });


    // Cerrar con la X

    if (cerrarEditar) {

        cerrarEditar.addEventListener(
            "click",
            cerrarModalEdicion
        );

    }


    // Cerrar con Cancelar

    if (cancelarEditar) {

        cancelarEditar.addEventListener(
            "click",
            cerrarModalEdicion
        );

    }


    // Cerrar al pulsar fuera del modal

    if (modalEditar) {

        modalEditar.addEventListener("click", (event) => {

            if (event.target === modalEditar) {
                cerrarModalEdicion();
            }

        });

    }


    // Mostrar u ocultar contraseña nueva

    const passwordEditar =
        document.getElementById("editarPassword");

    const mostrarPasswordEditar =
        document.getElementById("mostrarPasswordEditar");

    if (mostrarPasswordEditar && passwordEditar) {

        mostrarPasswordEditar.addEventListener("click", () => {

            const mostrar = passwordEditar.type === "password";

            passwordEditar.type = mostrar ? "text" : "password";

            mostrarPasswordEditar.innerHTML = mostrar
                ? '<i class="bi bi-eye-slash"></i>'
                : '<i class="bi bi-eye"></i>';

        });

    }


    // Validar formulario de edición

    if (formularioEditar) {

        formularioEditar.addEventListener("submit", (event) => {

            if (!formularioEditar.checkValidity()) {

                event.preventDefault();

                formularioEditar.reportValidity();

            }

        });

    }


    // =====================================
    // MODAL PERSONALIZADO PARA ELIMINAR
    // =====================================

    const modalEliminar = document.getElementById("modalEliminarUsuario");

    const formulariosEliminar = document.querySelectorAll(
        ".form-eliminar-usuario"
    );

    const nombreUsuarioEliminar = document.getElementById(
        "nombreUsuarioEliminar"
    );

    const cerrarEliminar = document.getElementById(
        "cerrarModalEliminar"
    );

    const cancelarEliminar = document.getElementById(
        "cancelarModalEliminar"
    );

    const confirmarEliminar = document.getElementById(
        "confirmarEliminar"
    );

    let formularioPendiente = null;


    // Abrir modal al intentar eliminar

    formulariosEliminar.forEach((formulario) => {

        formulario.addEventListener("submit", (event) => {

            event.preventDefault();

            formularioPendiente = formulario;

            nombreUsuarioEliminar.textContent =
                formulario.dataset.username;

            modalEliminar.classList.add("visible");

            document.body.style.overflow = "hidden";

        });

    });


    // Cerrar modal

    function cerrarModalEliminar() {

        modalEliminar.classList.remove("visible");

        document.body.style.overflow = "";

        formularioPendiente = null;

        confirmarEliminar.disabled = false;

    }


    if (cerrarEliminar) {

        cerrarEliminar.addEventListener(
            "click",
            cerrarModalEliminar
        );

    }

    if (cancelarEliminar) {

        cancelarEliminar.addEventListener(
            "click",
            cerrarModalEliminar
        );

    }


    // Cerrar al pulsar fuera

    if (modalEliminar) {

        modalEliminar.addEventListener("click", (event) => {

            if (event.target === modalEliminar) {
                cerrarModalEliminar();
            }

        });

    }


    // Cerrar con Escape

    document.addEventListener("keydown", (event) => {

        if (
            event.key === "Escape" &&
            modalEliminar?.classList.contains("visible")
        ) {
            cerrarModalEliminar();
        }

    });


    // Confirmar desactivación

    if (confirmarEliminar) {

        confirmarEliminar.addEventListener("click", () => {

            if (!formularioPendiente) return;

            confirmarEliminar.disabled = true;

            // Enviar directamente el formulario a Flask
            formularioPendiente.submit();

        });

    }


});

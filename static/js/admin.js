document.addEventListener("DOMContentLoaded", () => {

    const botonMenu = document.getElementById("botonMenu");
    const sidebar = document.getElementById("sidebar");

    const perfilBoton = document.getElementById("perfilBoton");
    const perfilMenu = document.getElementById("perfilMenu");


    // =====================================
    // ABRIR Y CERRAR MENÚ LATERAL
    // =====================================

    if (botonMenu && sidebar) {

        botonMenu.addEventListener("click", () => {
            sidebar.classList.toggle("abierto");
        });

        document.addEventListener("click", (event) => {

            if (
                window.innerWidth <= 900 &&
                !sidebar.contains(event.target) &&
                !botonMenu.contains(event.target)
            ) {
                sidebar.classList.remove("abierto");
            }

        });

    }


    // =====================================
    // MENÚ DEL PERFIL
    // =====================================

    if (perfilBoton && perfilMenu) {

        perfilBoton.addEventListener("click", (event) => {

            event.stopPropagation();

            perfilMenu.classList.toggle("visible");

        });

        document.addEventListener("click", (event) => {

            if (
                !perfilMenu.contains(event.target) &&
                !perfilBoton.contains(event.target)
            ) {
                perfilMenu.classList.remove("visible");
            }

        });

    }


    // =====================================
    // MARCAR OPCIÓN ACTIVA
    // =====================================

    const enlaces = document.querySelectorAll(".menu-enlace");

    enlaces.forEach((enlace) => {

        enlace.addEventListener("click", () => {

            enlaces.forEach((elemento) => {
                elemento.classList.remove("activo");
            });

            enlace.classList.add("activo");

        });

    });

    // =====================================
    // FECHA ACTUAL DEL DASHBOARD
    // =====================================

    const fechaActual = document.getElementById("fechaActual");

    if (fechaActual) {

        const hoy = new Date();

        fechaActual.textContent = hoy.toLocaleDateString("es-MX", {
            weekday: "long",
            day: "numeric",
            month: "long",
            year: "numeric"
        });

    }

});
document.addEventListener("DOMContentLoaded", () => {

    const formulario = document.getElementById("formReservacion");
    const fecha = document.getElementById("fecha");
    const mesas = document.querySelectorAll(".zona-mesa");
    const mesaElegida = document.getElementById("mesaElegida");
    const personas = document.getElementById("personas");
    const campoMesa = document.getElementById("id_mesa");

    let mesaSeleccionada = null;
    let temporizadorNotificacion = null;


    // =====================================
    // FECHA MÍNIMA: HOY
    // =====================================

    const hoy = new Date();

    const fechaLocal = new Date(
        hoy.getTime() - hoy.getTimezoneOffset() * 60000
    ).toISOString().split("T")[0];

    fecha.min = fechaLocal;


    // =====================================
    // NOTIFICACIONES
    // =====================================

    function mostrarNotificacion(mensaje, tipo = "success") {

        const notificacion = document.getElementById("notificacion");
        const texto = document.getElementById("textoNotificacion");
        const icono = document.getElementById("iconoNotificacion");

        if (!notificacion || !texto || !icono) return;

        clearTimeout(temporizadorNotificacion);

        texto.textContent = mensaje;

        notificacion.className = "notificacion visible " + tipo;

        icono.textContent =
            tipo === "success" ? "✓" : "⚠";

        temporizadorNotificacion = setTimeout(() => {
            notificacion.classList.remove("visible");
        }, 4500);
    }


    const cerrarNotificacion =
        document.getElementById("cerrarNotificacion");

    if (cerrarNotificacion) {

        cerrarNotificacion.addEventListener("click", () => {

            document.getElementById("notificacion")
                .classList.remove("visible");

            clearTimeout(temporizadorNotificacion);

        });

    }


    // =====================================
    // MENSAJES ENVIADOS DESDE FLASK
    // =====================================

    const mensajesFlask =
        document.querySelectorAll("#mensajesFlask div");

    mensajesFlask.forEach((mensaje) => {

        mostrarNotificacion(
            mensaje.textContent.trim(),
            mensaje.dataset.tipo
        );

    });


    // =====================================
    // LIMPIAR MESA SELECCIONADA
    // =====================================

    function limpiarSeleccion() {

        mesas.forEach((mesa) => {
            mesa.classList.remove("seleccionada");
        });

        mesaSeleccionada = null;

        campoMesa.value = "";

        mesaElegida.textContent = "Ninguna";
    }


    // =====================================
    // CONSULTAR MESAS OCUPADAS
    // =====================================

    async function consultarMesasOcupadas() {

        const fechaSeleccionada = fecha.value;

        limpiarSeleccion();

        // Si no hay fecha, todas las mesas quedan disponibles
        if (!fechaSeleccionada) {

            mesas.forEach((mesa) => {

                mesa.disabled = false;

                mesa.classList.remove("ocupada");

                mesa.title = "Mesa disponible";

            });

            return;
        }

        try {

            const respuesta = await fetch(
                `/reservaciones/mesas-ocupadas?fecha=${encodeURIComponent(fechaSeleccionada)}`
            );

            if (!respuesta.ok) {
                throw new Error("No fue posible consultar la disponibilidad.");
            }

            const datos = await respuesta.json();

            if (datos.error) {
                throw new Error(datos.error);
            }

            const ocupadas = new Set(
                datos.ocupadas.map(Number)
            );

            mesas.forEach((mesa) => {

                const idMesa = Number(mesa.dataset.id);

                const estaOcupada = ocupadas.has(idMesa);

                mesa.disabled = estaOcupada;

                mesa.classList.toggle(
                    "ocupada",
                    estaOcupada
                );

                mesa.classList.remove("seleccionada");

                mesa.title = estaOcupada
                    ? "No disponible: ya tiene una reservación para esta fecha."
                    : "Mesa disponible";

            });

            if (ocupadas.size > 0) {

                mostrarNotificacion(
                    "Las mesas ocupadas aparecen en rojo.",
                    "error"
                );

            }

        } catch (error) {

            console.error(
                "Error al consultar mesas:",
                error
            );

            mesas.forEach((mesa) => {
                mesa.disabled = false;

                mesa.classList.remove("Ocupada");

                mesa.title = "Disponibilidad pendiente de verificar";
            });

            mostrarNotificacion(
                "No se pudo consultar la disponibilidad. Intenta nuevamente.",
                "error"
            );

        }

    }


    // =====================================
    // ACTUALIZAR AL CAMBIAR LA FECHA
    // =====================================

    fecha.addEventListener(
        "change",
        consultarMesasOcupadas
    );


    // =====================================
// SELECCIÓN DE MESAS
// =====================================

mesas.forEach((mesa) => {

    mesa.addEventListener("click", () => {

        if (
            mesa.disabled ||
            mesa.classList.contains("ocupada")
        ) {
            mostrarNotificacion(
                "Esta mesa ya está reservada para la fecha seleccionada.",
                "error"
            );

            return;
        }

        const capacidad = Number(mesa.dataset.capacidad);

        const cantidadPersonas = Number(personas.value);

        // Validar capacidad solamente si ya se eligieron personas
        if (
            cantidadPersonas &&
            cantidadPersonas > capacidad
        ) {

            mostrarNotificacion(
                `Esta mesa tiene capacidad para ${capacidad} personas.`,
                "error"
            );

            return;
        }

        // Quitar selección anterior
        mesas.forEach((elemento) => {
            elemento.classList.remove("seleccionada");
        });

        // Seleccionar mesa
        mesa.classList.add("seleccionada");

        mesaSeleccionada = {
            id: mesa.dataset.id,
            nombre: mesa.dataset.mesa,
            capacidad: capacidad
        };

        campoMesa.value = mesaSeleccionada.id;

        mesaElegida.textContent =
            `${mesaSeleccionada.nombre} - ${capacidad} personas`;

    });

});

    // =====================================
    // VALIDAR CAPACIDAD AL CAMBIAR PERSONAS
    // =====================================

    personas.addEventListener("change", () => {

        const cantidad = Number(personas.value);

        if (
            mesaSeleccionada &&
            cantidad > mesaSeleccionada.capacidad
        ) {

            limpiarSeleccion();

            mostrarNotificacion(
                "La mesa seleccionada no tiene capacidad suficiente. Elige otra mesa.",
                "error"
            );

        }

    });


    // =====================================
    // VALIDAR ANTES DE ENVIAR
    // =====================================

    formulario.addEventListener("submit", async (event) => {

        if (!formulario.checkValidity()) {

            event.preventDefault();

            formulario.reportValidity();

            return;
        }

        if (!mesaSeleccionada || !campoMesa.value) {

            event.preventDefault();

            mostrarNotificacion(
                "Selecciona una mesa disponible para continuar.",
                "error"
            );

            return;
        }

        if (
            mesaSeleccionada &&
            (
                document.querySelector(
                    `.zona-mesa[data-id="${mesaSeleccionada.id}"]`
                ).disabled
            )
        ) {

            event.preventDefault();

            limpiarSeleccion();

            mostrarNotificacion(
                "La mesa ya no está disponible. Selecciona otra.",
                "error"
            );

            return;
        }

        // Si todo está correcto, el formulario se envía a Flask.
    });


    // =====================================
    // CONSULTAR AL CARGAR SI HAY FECHA
    // =====================================

    if (fecha.value) {
        consultarMesasOcupadas();
    }

});
// ==========================================
// RESERVACIONES - LA CANTINA
// ==========================================

document.addEventListener("DOMContentLoaded", () => {

    const $ = id => document.getElementById(id);

    let fechaSeleccionada = new Date();
    let fechaConsulta = formatoFecha(fechaSeleccionada);

    let reservaciones = [];
    let mesas = [];
    let reservacionSeleccionada = null;
    let calendario = {};
    let pestanaActual = "todas";

    const nombresMeses = [
        "Enero", "Febrero", "Marzo", "Abril",
        "Mayo", "Junio", "Julio", "Agosto",
        "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ];

    function formatoFecha(fecha) {
        const anio = fecha.getFullYear();
        const mes = String(fecha.getMonth() + 1).padStart(2, "0");
        const dia = String(fecha.getDate()).padStart(2, "0");
        return `${anio}-${mes}-${dia}`;
    }

    function escapar(valor) {
        return String(valor ?? "").replace(/[&<>"']/g, caracter => ({
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#039;"
        })[caracter]);
    }

    function mostrarToast(mensaje) {
        const toast = $("resToast");
        toast.textContent = mensaje;
        toast.classList.add("visible");

        setTimeout(() => {
            toast.classList.remove("visible");
        }, 3000);
    }

    function claseEstado(estado) {
        return {
            "Reservada": "reservada",
            "Confirmada": "confirmada",
            "En curso": "encurso",
            "Finalizada": "finalizada",
            "Cancelada": "cancelada"
        }[estado] || "";
    }

    function fechaBonita(fecha) {
        if (!fecha) return "";
        const partes = fecha.split("-");
        return `${partes[2]}/${partes[1]}/${partes[0]}`;
    }

    // ==========================================
    // CARGAR INFORMACIÓN
    // ==========================================

    async function cargarDatos() {
        try {
            const mes = `${fechaSeleccionada.getFullYear()}-${String(
                fechaSeleccionada.getMonth() + 1
            ).padStart(2, "0")}`;

            const url = new URL(API_RESERVACIONES, window.location.origin);

            url.searchParams.set("fecha", fechaConsulta);
            url.searchParams.set("mes", mes);

            if (pestanaActual === "historial") {
                url.searchParams.set("filtro", "historial");
            } else if (pestanaActual === "canceladas") {
                url.searchParams.set("filtro", "canceladas");
            } else {
                url.searchParams.set("filtro", "activas");
            }

            const respuesta = await fetch(url);
            const datos = await respuesta.json();

            if (!respuesta.ok || !datos.ok) {
                throw new Error(datos.mensaje || "No fue posible cargar los datos.");
            }

            reservaciones = datos.reservaciones || [];
            mesas = datos.mesas || [];
            calendario = datos.calendario || {};

            actualizarIndicadores(datos.indicadores);
            renderizarCalendario();
            renderizarReservaciones();
            renderizarMesas();
            llenarFiltrosMesas();

        } catch (error) {
            console.error("ERROR RESERVACIONES:", error);
            mostrarToast(error.message);
        }
    }

    // ==========================================
    // INDICADORES
    // ==========================================

    function actualizarIndicadores(datos) {
        $("totalReservaciones").textContent = datos.reservaciones ?? 0;
        $("totalPersonas").textContent = datos.personas ?? 0;
        $("totalMesas").textContent = datos.mesas ?? 0;
        $("totalPendientes").textContent = datos.pendientes ?? 0;
    }

    // ==========================================
    // CALENDARIO
    // ==========================================

    function renderizarCalendario() {
        const anio = fechaSeleccionada.getFullYear();
        const mes = fechaSeleccionada.getMonth();

        $("nombreMes").textContent = `${nombresMeses[mes]} ${anio}`;

        const calendarioGrid = $("calendarioGrid");
        calendarioGrid.innerHTML = "";

        const primerDia = new Date(anio, mes, 1).getDay();
        const diasMes = new Date(anio, mes + 1, 0).getDate();
        const hoy = formatoFecha(new Date());

        for (let i = 0; i < primerDia; i++) {
            calendarioGrid.appendChild(document.createElement("span"));
        }

        for (let dia = 1; dia <= diasMes; dia++) {
            const fecha = new Date(anio, mes, dia);
            const valorFecha = formatoFecha(fecha);
            const boton = document.createElement("button");

            boton.type = "button";
            boton.className = "dia-calendario";
            boton.textContent = dia;

            if (valorFecha === fechaConsulta) boton.classList.add("seleccionado");
            if (valorFecha === hoy) boton.classList.add("hoy");

            if (calendario[valorFecha]) {
                boton.classList.add("tiene-reservas");
                boton.title = `${calendario[valorFecha]} reservaciones`;
            }

            boton.addEventListener("click", () => {
                fechaSeleccionada = fecha;
                fechaConsulta = valorFecha;
                reservacionSeleccionada = null;
                pestanaActual = "todas";

                actualizarPestanas();
                mostrarDetalle();
                cargarDatos();
            });

            calendarioGrid.appendChild(boton);
        }
    }

    $("mesAnterior").addEventListener("click", () => {
        fechaSeleccionada.setDate(1);
        fechaSeleccionada.setMonth(fechaSeleccionada.getMonth() - 1);
        fechaConsulta = formatoFecha(fechaSeleccionada);
        reservacionSeleccionada = null;
        mostrarDetalle();
        cargarDatos();
    });

    $("mesSiguiente").addEventListener("click", () => {
        fechaSeleccionada.setDate(1);
        fechaSeleccionada.setMonth(fechaSeleccionada.getMonth() + 1);
        fechaConsulta = formatoFecha(fechaSeleccionada);
        reservacionSeleccionada = null;
        mostrarDetalle();
        cargarDatos();
    });

    // ==========================================
    // TABLA DE RESERVACIONES
    // ==========================================

    function renderizarReservaciones() {
        const tabla = $("tablaReservaciones");
        const filtroMesa = $("filtroMesa").value;

        let lista = reservaciones;

        if (filtroMesa) {
            lista = lista.filter(
                reserva => String(reserva.id_mesa) === filtroMesa
            );
        }

        if (!lista.length) {
            tabla.innerHTML = `
                <tr>
                    <td colspan="6">No hay reservaciones para mostrar.</td>
                </tr>
            `;
            return;
        }

        tabla.innerHTML = lista.map(reserva => `
            <tr class="fila-reservacion
                ${reservacionSeleccionada?.id === reserva.id ? "seleccionada" : ""}"
                data-id="${reserva.id}">

                <td>R-${String(reserva.id).padStart(4, "0")}</td>
                <td>${escapar(reserva.cliente)}</td>
                <td>${escapar(reserva.mesa)}</td>
                <td>${reserva.personas}</td>
                <td>${fechaBonita(reserva.fecha)} · ${escapar(reserva.hora)}</td>

                <td>
                    <span class="estado-res ${claseEstado(reserva.estado)}">
                        ${escapar(reserva.estado)}
                    </span>
                </td>
            </tr>
        `).join("");

        tabla.querySelectorAll(".fila-reservacion").forEach(fila => {
            fila.addEventListener("click", () => {
                const id = Number(fila.dataset.id);

                reservacionSeleccionada = lista.find(
                    reserva => Number(reserva.id) === id
                );

                renderizarReservaciones();
                mostrarDetalle();
            });
        });
    }

    // ==========================================
    // ESTADO DE MESAS
    // ==========================================

    function renderizarMesas() {
        const mesasGrid = $("mesasGrid");

        if (!mesas.length) {
            mesasGrid.innerHTML = "<p>No hay mesas activas.</p>";
            return;
        }

        mesasGrid.innerHTML = mesas.map(mesa => `
            <article class="mesa-card ${mesa.estado.toLowerCase()}">
                <h3>
                    <i class="bi bi-table"></i>
                    ${escapar(mesa.nombre)}
                </h3>

                <p>
                    <i class="bi bi-people"></i>
                    ${mesa.capacidad} personas
                </p>

                <p>${escapar(mesa.tipo || "Mesa")}</p>

                <strong>${escapar(mesa.estado)}</strong>
            </article>
        `).join("");
    }

    // ==========================================
    // FILTROS
    // ==========================================

    function llenarFiltrosMesas() {
        const select = $("filtroMesa");
        const valorAnterior = select.value;

        select.innerHTML = '<option value="">Todas las mesas</option>';

        mesas.forEach(mesa => {
            const opcion = document.createElement("option");
            opcion.value = mesa.id;
            opcion.textContent = mesa.nombre;
            select.appendChild(opcion);
        });

        select.value = valorAnterior;

        const selectNueva = $("selectMesa");
        selectNueva.innerHTML = '<option value="">Selecciona una mesa</option>';

        mesas.forEach(mesa => {
            const opcion = document.createElement("option");
            opcion.value = mesa.id;
            opcion.textContent = `${mesa.nombre} - ${mesa.capacidad} personas`;
            selectNueva.appendChild(opcion);
        });
    }

    $("filtroMesa").addEventListener("change", renderizarReservaciones);

    $("filtroFecha").addEventListener("change", function () {
        if (this.value === "hoy") {
            fechaSeleccionada = new Date();
            fechaConsulta = formatoFecha(fechaSeleccionada);
            cargarDatos();
        }
    });

    $("filtroEstado").addEventListener("change", function () {
        const valor = this.value;

        if (valor === "historial" || valor === "canceladas") {
            pestanaActual = valor;
        } else {
            pestanaActual = "todas";
        }

        actualizarPestanas();
        reservacionSeleccionada = null;
        mostrarDetalle();
        cargarDatos();
    });

    // ==========================================
    // PESTAÑAS
    // ==========================================

    function actualizarPestanas() {
        document.querySelectorAll(".res-tab").forEach(boton => {
            boton.classList.toggle(
                "activo",
                boton.dataset.tab === pestanaActual
            );
        });
    }

    document.querySelectorAll(".res-tab").forEach(boton => {
        boton.addEventListener("click", () => {
            pestanaActual = boton.dataset.tab;
            reservacionSeleccionada = null;

            $("filtroEstado").value =
                pestanaActual === "todas" ? "todas" : pestanaActual;

            actualizarPestanas();
            mostrarDetalle();
            cargarDatos();
        });
    });

    // ==========================================
    // DETALLE DE RESERVACIÓN
    // ==========================================

    function mostrarDetalle() {
        const reserva = reservacionSeleccionada;

        const botones = [
            "btnConfirmar",
            "btnIniciar",
            "btnLiberar",
            "btnCancelar"
        ];

        botones.forEach(id => {
            $(id).disabled = !reserva;
        });

        if (!reserva) {
            $("detalleReservacion").innerHTML = `
                <p>Selecciona una reservación para consultar sus detalles.</p>
            `;
            return;
        }

        $("detalleReservacion").innerHTML = `
            <div class="detalle-dato">
                <i class="bi bi-person"></i>
                <div><strong>Cliente:</strong> ${escapar(reserva.cliente)}</div>
            </div>

            <div class="detalle-dato">
                <i class="bi bi-upc"></i>
                <div><strong>Folio:</strong> R-${String(reserva.id).padStart(4, "0")}</div>
            </div>

            <div class="detalle-dato">
                <i class="bi bi-table"></i>
                <div><strong>Mesa:</strong> ${escapar(reserva.mesa)}</div>
            </div>

            <div class="detalle-dato">
                <i class="bi bi-people"></i>
                <div><strong>Personas:</strong> ${reserva.personas}</div>
            </div>

            <div class="detalle-dato">
                <i class="bi bi-calendar"></i>
                <div><strong>Fecha:</strong> ${fechaBonita(reserva.fecha)}</div>
            </div>

            <div class="detalle-dato">
                <i class="bi bi-clock"></i>
                <div><strong>Hora:</strong> ${escapar(reserva.hora)}</div>
            </div>

            <div class="detalle-dato">
                <i class="bi bi-telephone"></i>
                <div><strong>Teléfono:</strong> ${escapar(reserva.telefono)}</div>
            </div>

            <div class="detalle-dato">
                <i class="bi bi-envelope"></i>
                <div><strong>Correo:</strong> ${escapar(reserva.correo)}</div>
            </div>

            <div class="detalle-dato">
                <i class="bi bi-chat-left-text"></i>
                <div><strong>Observaciones:</strong> ${escapar(reserva.observaciones || "Sin observaciones")}</div>
            </div>

            <div class="detalle-dato">
                <i class="bi bi-info-circle"></i>
                <div><strong>Estado:</strong> ${escapar(reserva.estado)}</div>
            </div>
        `;

        $("btnConfirmar").disabled = reserva.estado !== "Reservada";

        $("btnIniciar").disabled =
            !["Reservada", "Confirmada"].includes(reserva.estado);

        $("btnLiberar").disabled = reserva.estado !== "En curso";

        $("btnCancelar").disabled =
            !["Reservada", "Confirmada", "En curso"].includes(reserva.estado);
    }

    // ==========================================
    // VENTANA EMERGENTE PERSONALIZADA
    // ==========================================

    function confirmarAccion(titulo, mensaje, icono = "bi-question-circle") {
        return new Promise(resolve => {
            const modal = $("modalConfirmacion");

            if (!modal) {
                resolve(window.confirm(mensaje));
                return;
            }

            $("confirmacionTitulo").textContent = titulo;
            $("confirmacionMensaje").textContent = mensaje;
            $("confirmacionIcono").innerHTML = `<i class="bi ${icono}"></i>`;

            modal.classList.add("visible");

            function cerrar(resultado) {
                modal.classList.remove("visible");

                $("btnAceptarConfirmacion").removeEventListener("click", aceptar);
                $("btnCancelarConfirmacion").removeEventListener("click", cancelar);
                modal.removeEventListener("click", clicExterior);

                resolve(resultado);
            }

            function aceptar() {
                cerrar(true);
            }

            function cancelar() {
                cerrar(false);
            }

            function clicExterior(evento) {
                if (evento.target === modal) cancelar();
            }

            $("btnAceptarConfirmacion").addEventListener("click", aceptar);
            $("btnCancelarConfirmacion").addEventListener("click", cancelar);
            modal.addEventListener("click", clicExterior);
        });
    }

    // ==========================================
    // ACTUALIZAR ESTADO EN MYSQL
    // ==========================================

    async function cambiarEstado(nuevoEstado) {
        if (!reservacionSeleccionada) {
            mostrarToast("Selecciona una reservación primero.");
            return;
        }

        const id = reservacionSeleccionada.id;

        if (id === undefined || id === null || id === "") {
            mostrarToast("No se encontró el identificador de la reservación.");
            return;
        }

        const configuracion = {
            Confirmada: {
                titulo: "Confirmar reservación",
                mensaje: "¿Deseas confirmar esta reservación?",
                icono: "bi-calendar-check"
            },
            "En curso": {
                titulo: "Recibir cliente",
                mensaje: "¿Confirmas que el cliente ha llegado y ocupará la mesa?",
                icono: "bi-person-check"
            },
            Finalizada: {
                titulo: "Liberar mesa",
                mensaje: "¿Deseas finalizar la reservación y liberar esta mesa?",
                icono: "bi-unlock"
            },
            Cancelada: {
                titulo: "Cancelar reservación",
                mensaje: "¿Estás seguro de que deseas cancelar esta reservación?",
                icono: "bi-x-circle"
            }
        };

        const config = configuracion[nuevoEstado];
        if (!config) return;

        const aceptado = await confirmarAccion(
            config.titulo,
            config.mensaje,
            config.icono
        );

        if (!aceptado) return;

        try {
            const url = API_CAMBIAR_ESTADO.replace(
                /\/0\/estado$/,
                `/${encodeURIComponent(id)}/estado`
            );

            console.log("Actualizando reservación:", id, nuevoEstado, url);

            const respuesta = await fetch(url, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ estado: nuevoEstado })
            });

            const datos = await respuesta.json();

            if (!respuesta.ok || !datos.ok) {
                throw new Error(datos.mensaje || "No se pudo actualizar la reservación.");
            }

            mostrarToast(datos.mensaje);

            reservacionSeleccionada = null;
            mostrarDetalle();

            await cargarDatos();

        } catch (error) {
            console.error("ERROR AL CAMBIAR ESTADO:", error);
            mostrarToast(error.message);
        }
    }

    // ==========================================
    // EVENTOS DE LOS BOTONES EXISTENTES
    // ==========================================

    $("btnConfirmar").addEventListener("click", () => {
        cambiarEstado("Confirmada");
    });

    $("btnIniciar").addEventListener("click", () => {
        cambiarEstado("En curso");
    });

    $("btnLiberar").addEventListener("click", () => {
        cambiarEstado("Finalizada");
    });

    $("btnCancelar").addEventListener("click", () => {
        cambiarEstado("Cancelada");
    });

    // ==========================================
    // MODAL NUEVA RESERVACIÓN
    // ==========================================

    const modal = $("modalReserva");

    function abrirModal() {
        $("formReserva").reset();
        $("fechaNuevaReserva").value = fechaConsulta;
        $("fechaNuevaReserva").min = formatoFecha(new Date());
        modal.classList.add("abierto");
    }

    function cerrarModal() {
        modal.classList.remove("abierto");
    }

    $("btnNuevaReserva").addEventListener("click", abrirModal);
    $("cerrarModal").addEventListener("click", cerrarModal);
    $("cancelarModal").addEventListener("click", cerrarModal);

    modal.addEventListener("click", evento => {
        if (evento.target === modal) cerrarModal();
    });

    // ==========================================
    // REGISTRAR NUEVA RESERVACIÓN
    // ==========================================

    $("formReserva").addEventListener("submit", async evento => {
        evento.preventDefault();

        const formulario = new FormData(evento.target);
        const datos = Object.fromEntries(formulario.entries());

        try {
            const respuesta = await fetch(
                `${API_RESERVACIONES}/crear`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify(datos)
                }
            );

            const resultado = await respuesta.json();

            if (!respuesta.ok || !resultado.ok) {
                throw new Error(resultado.mensaje || "No se pudo guardar.");
            }

            // Cerrar y limpiar el formulario
            cerrarModal();
            $("formReserva").reset();

            // Actualizar la información de la pantalla
            fechaSeleccionada = new Date(datos.fecha + "T12:00:00");
            fechaConsulta = datos.fecha;

            pestanaActual = "todas";
            actualizarPestanas();

            await cargarDatos();

            // Mostrar resultado del registro y envío del correo
            mostrarToast(resultado.mensaje);

        } catch (error) {
            console.error("ERROR AL REGISTRAR:", error);
            mostrarToast(error.message);
        }
    });

    // ==========================================
    // INICIALIZAR
    // ==========================================

    cargarDatos();

});

document.addEventListener("DOMContentLoaded", () => {

    // ==========================================
    // ELEMENTOS PRINCIPALES
    // ==========================================

    const formulario = document.getElementById("formGenerarPedido");

    const proveedorSelect = document.getElementById("proveedorPedido");
    const fechaEntrega = document.getElementById("fechaEntrega");
    const observaciones = document.getElementById("observacionesPedido");

    const btnAgregarInsumo = document.getElementById("btnAgregarInsumo");
    const btnCancelarPedido = document.getElementById("btnCancelarPedido");
    const btnGenerarPedido = document.getElementById("btnGenerarPedido");

    const tablaInsumosPedido = document.getElementById("tablaInsumosPedido");
    const totalPedido = document.getElementById("totalPedido");

    const modal = document.getElementById("modalAgregarInsumo");
    const cerrarModal = document.getElementById("cerrarModalInsumo");
    const cancelarModal = document.getElementById("cancelarModalInsumo");
    const confirmarAgregar = document.getElementById("confirmarAgregarInsumo");

    const seleccionarInsumo = document.getElementById("seleccionarInsumo");
    const cantidadInsumo = document.getElementById("cantidadInsumo");

    const informacionInsumo = document.getElementById("informacionInsumo");
    const unidadInsumo = document.getElementById("unidadInsumo");
    const stockInsumo = document.getElementById("stockInsumo");
    const costoInsumo = document.getElementById("costoInsumo");

    const mensajeCompras = document.getElementById("mensajeCompras");
    const notificacion = document.getElementById("notificacionCompras");

    // ==========================================
    // VARIABLES
    // ==========================================

    let catalogoProveedor = [];
    let insumosPedido = [];
    let temporizadorNotificacion = null;

    const formatoMoneda = new Intl.NumberFormat("es-MX", {
        style: "currency",
        currency: "MXN"
    });

    // ==========================================
    // FUNCIONES DE MENSAJES
    // ==========================================

    function mostrarMensaje(mensaje, tipo = "success") {

        if (!mensajeCompras) return;

        mensajeCompras.textContent = mensaje;
        mensajeCompras.className = `mensaje-compras visible ${tipo}`;

    }


    function ocultarMensaje() {

        if (!mensajeCompras) return;

        mensajeCompras.textContent = "";
        mensajeCompras.className = "mensaje-compras";

    }


    function mostrarNotificacion(mensaje, tipo = "success") {

        if (!notificacion) {
            alert(mensaje);
            return;
        }

        clearTimeout(temporizadorNotificacion);

        notificacion.textContent = mensaje;
        notificacion.className = `notificacion-compras visible ${tipo}`;

        temporizadorNotificacion = setTimeout(() => {

            notificacion.classList.remove("visible");

        }, 4000);

    }


    // ==========================================
    // FUNCIONES DEL MODAL
    // ==========================================

    function abrirModal() {

        if (!modal) return;

        modal.classList.add("visible");
        document.body.style.overflow = "hidden";

    }


    function cerrarModalCompra() {

        if (!modal) return;

        modal.classList.remove("visible");
        document.body.style.overflow = "";

        seleccionarInsumo.value = "";
        cantidadInsumo.value = "";

        informacionInsumo.hidden = true;

    }


    cerrarModal?.addEventListener("click", cerrarModalCompra);

    cancelarModal?.addEventListener("click", cerrarModalCompra);


    modal?.addEventListener("click", event => {

        if (event.target === modal) {
            cerrarModalCompra();
        }

    });


    document.addEventListener("keydown", event => {

        if (event.key === "Escape" && modal?.classList.contains("visible")) {
            cerrarModalCompra();
        }

    });


    // ==========================================
    // FECHA MÍNIMA DE ENTREGA
    // ==========================================

    function establecerFechaMinima() {

        if (!fechaEntrega) return;

        const hoy = new Date();

        const anio = hoy.getFullYear();
        const mes = String(hoy.getMonth() + 1).padStart(2, "0");
        const dia = String(hoy.getDate()).padStart(2, "0");

        const fechaActual = `${anio}-${mes}-${dia}`;

        fechaEntrega.min = fechaActual;

    }

    establecerFechaMinima();


    // ==========================================
    // CONSULTAR INSUMOS DEL PROVEEDOR
    // ==========================================

    async function cargarInsumosProveedor(idProveedor) {

        catalogoProveedor = [];

        seleccionarInsumo.innerHTML = `
            <option value="">Cargando insumos...</option>
        `;

        seleccionarInsumo.disabled = true;

        informacionInsumo.hidden = true;

        try {

            const respuesta = await fetch(
                `/gerente/compras/proveedor/${encodeURIComponent(idProveedor)}/insumos`
            );

            const datos = await respuesta.json();

            if (!respuesta.ok) {
                throw new Error(datos.error || "No se pudieron cargar los insumos.");
            }

            catalogoProveedor = datos.insumos || [];

            seleccionarInsumo.innerHTML = `
                <option value="">Selecciona un insumo</option>
            `;

            if (catalogoProveedor.length === 0) {

                seleccionarInsumo.innerHTML = `
                    <option value="">Este proveedor no tiene insumos registrados</option>
                `;

                mostrarNotificacion(
                    "El proveedor seleccionado no tiene insumos disponibles.",
                    "error"
                );

                return;

            }

            catalogoProveedor.forEach(insumo => {

                const opcion = document.createElement("option");

                opcion.value = insumo.id_insumo;
                opcion.textContent = `${insumo.nombre} (${insumo.abreviatura || insumo.unidad})`;

                seleccionarInsumo.appendChild(opcion);

            });

            seleccionarInsumo.disabled = false;

        } catch (error) {

            seleccionarInsumo.innerHTML = `
                <option value="">No se pudieron cargar los insumos</option>
            `;

            mostrarNotificacion(error.message, "error");

        }

    }


    // ==========================================
    // CAMBIAR PROVEEDOR
    // ==========================================

    proveedorSelect?.addEventListener("change", async () => {

        const idProveedor = proveedorSelect.value;

        insumosPedido = [];

        renderizarPedido();

        informacionInsumo.hidden = true;

        ocultarMensaje();

        if (!idProveedor) {

            catalogoProveedor = [];

            seleccionarInsumo.innerHTML = `
                <option value="">Primero selecciona un proveedor</option>
            `;

            seleccionarInsumo.disabled = true;

            return;

        }

        await cargarInsumosProveedor(idProveedor);

    });


    // ==========================================
    // ABRIR MODAL PARA AGREGAR INSUMO
    // ==========================================

    btnAgregarInsumo?.addEventListener("click", () => {

        ocultarMensaje();

        if (!proveedorSelect.value) {

            mostrarNotificacion(
                "Primero selecciona un proveedor.",
                "error"
            );

            proveedorSelect.focus();

            return;

        }

        if (catalogoProveedor.length === 0) {

            mostrarNotificacion(
                "El proveedor no tiene insumos disponibles.",
                "error"
            );

            return;

        }

        abrirModal();

    });


    // ==========================================
    // MOSTRAR INFORMACIÓN DEL INSUMO
    // ==========================================

    seleccionarInsumo?.addEventListener("change", () => {

        const id = Number(seleccionarInsumo.value);

        const insumo = catalogoProveedor.find(
            elemento => Number(elemento.id_insumo) === id
        );

        if (!insumo) {

            informacionInsumo.hidden = true;

            return;

        }

        unidadInsumo.textContent =
            insumo.abreviatura || insumo.unidad || "-";

        stockInsumo.textContent =
            Number(insumo.stock_actual).toFixed(3);

        costoInsumo.textContent =
            formatoMoneda.format(Number(insumo.costo_unitario));

        informacionInsumo.hidden = false;

    });


    // ==========================================
    // AGREGAR INSUMO AL PEDIDO
    // ==========================================

    confirmarAgregar?.addEventListener("click", () => {

        const id = Number(seleccionarInsumo.value);

        const cantidad = Number(cantidadInsumo.value);

        if (!id) {

            mostrarNotificacion(
                "Selecciona un insumo.",
                "error"
            );

            return;

        }

        if (!Number.isFinite(cantidad) || cantidad <= 0) {

            mostrarNotificacion(
                "Ingresa una cantidad mayor a cero.",
                "error"
            );

            cantidadInsumo.focus();

            return;

        }

        const insumo = catalogoProveedor.find(
            elemento => Number(elemento.id_insumo) === id
        );

        if (!insumo) {

            mostrarNotificacion(
                "El insumo seleccionado no es válido.",
                "error"
            );

            return;

        }

        const yaExiste = insumosPedido.some(
            elemento => elemento.id_insumo === id
        );

        if (yaExiste) {

            mostrarNotificacion(
                "Este insumo ya está agregado al pedido. Modifica su cantidad en la tabla.",
                "error"
            );

            return;

        }

        insumosPedido.push({

            id_insumo: id,

            nombre: insumo.nombre,

            cantidad: cantidad,

            unidad: insumo.abreviatura || insumo.unidad,

            costo_unitario: Number(insumo.costo_unitario)

        });

        renderizarPedido();

        cerrarModalCompra();

        mostrarNotificacion(
            "El insumo se agregó correctamente."
        );

    });


    // ==========================================
    // DIBUJAR TABLA DEL PEDIDO
    // ==========================================

    function renderizarPedido() {

        tablaInsumosPedido.innerHTML = "";

        if (insumosPedido.length === 0) {

            tablaInsumosPedido.innerHTML = `
                <tr id="pedidoVacio">
                    <td colspan="4" class="pedido-sin-insumos">
                        <i class="fas fa-box-open"></i>
                        <p>Aún no hay insumos agregados.</p>
                    </td>
                </tr>
            `;

            actualizarTotal();

            return;

        }

        insumosPedido.forEach((insumo, indice) => {

            const fila = document.createElement("tr");

            fila.className = "fila-insumo-pedido";

            const celdaNombre = document.createElement("td");
            celdaNombre.className = "nombre-insumo-pedido";
            celdaNombre.textContent = insumo.nombre;

            const celdaCantidad = document.createElement("td");

            const inputCantidad = document.createElement("input");

            inputCantidad.type = "number";
            inputCantidad.min = "0.001";
            inputCantidad.step = "0.001";
            inputCantidad.value = insumo.cantidad;
            inputCantidad.className = "cantidad-insumo-pedido";
            inputCantidad.setAttribute("aria-label", `Cantidad de ${insumo.nombre}`);

            inputCantidad.addEventListener("change", () => {

                const nuevaCantidad = Number(inputCantidad.value);

                if (!Number.isFinite(nuevaCantidad) || nuevaCantidad <= 0) {

                    inputCantidad.value = insumo.cantidad;

                    mostrarNotificacion(
                        "La cantidad debe ser mayor a cero.",
                        "error"
                    );

                    return;

                }

                insumosPedido[indice].cantidad = nuevaCantidad;

                actualizarTotal();

            });

            celdaCantidad.appendChild(inputCantidad);

            const celdaUnidad = document.createElement("td");
            celdaUnidad.textContent = insumo.unidad || "-";

            const celdaAcciones = document.createElement("td");

            const btnEliminar = document.createElement("button");

            btnEliminar.type = "button";
            btnEliminar.className = "btn-quitar-insumo";
            btnEliminar.innerHTML = '<i class="fas fa-trash"></i>';
            btnEliminar.title = "Quitar insumo";

            btnEliminar.addEventListener("click", () => {

                insumosPedido.splice(indice, 1);

                renderizarPedido();

                mostrarNotificacion(
                    "Se eliminó el insumo del pedido."
                );

            });

            celdaAcciones.appendChild(btnEliminar);

            fila.append(
                celdaNombre,
                celdaCantidad,
                celdaUnidad,
                celdaAcciones
            );

            tablaInsumosPedido.appendChild(fila);

        });

        actualizarTotal();

    }


    // ==========================================
    // CALCULAR TOTAL ESTIMADO
    // ==========================================

    function actualizarTotal() {

        const total = insumosPedido.reduce((acumulado, insumo) => {

            return acumulado +
                (insumo.cantidad * insumo.costo_unitario);

        }, 0);

        totalPedido.textContent = formatoMoneda.format(total);

    }


    // ==========================================
    // CANCELAR PEDIDO
    // ==========================================

    btnCancelarPedido?.addEventListener("click", () => {

        const confirmar = confirm(
            "¿Deseas limpiar el formulario y cancelar este pedido?"
        );

        if (!confirmar) return;

        formulario.reset();

        catalogoProveedor = [];
        insumosPedido = [];

        seleccionarInsumo.innerHTML = `
            <option value="">Primero selecciona un proveedor</option>
        `;

        seleccionarInsumo.disabled = true;

        informacionInsumo.hidden = true;

        renderizarPedido();

        ocultarMensaje();

        establecerFechaMinima();

        mostrarNotificacion(
            "El formulario se limpió correctamente."
        );

    });


    // ==========================================
    // GENERAR PEDIDO
    // ==========================================

    formulario?.addEventListener("submit", async event => {

        event.preventDefault();

        ocultarMensaje();

        const idProveedor = proveedorSelect.value;

        const fecha = fechaEntrega.value;

        if (!idProveedor) {

            mostrarMensaje(
                "Selecciona un proveedor antes de generar el pedido.",
                "error"
            );

            proveedorSelect.focus();

            return;

        }

        if (!fecha) {

            mostrarMensaje(
                "Selecciona una fecha de entrega.",
                "error"
            );

            fechaEntrega.focus();

            return;

        }

        if (fecha < fechaEntrega.min) {

            mostrarMensaje(
                "La fecha de entrega no puede ser anterior a hoy.",
                "error"
            );

            fechaEntrega.focus();

            return;

        }

        if (insumosPedido.length === 0) {

            mostrarMensaje(
                "Agrega al menos un insumo al pedido.",
                "error"
            );

            return;

        }

        const datosPedido = {

            id_proveedor: idProveedor,

            fecha_entrega: fecha,

            observaciones: observaciones.value.trim(),

            insumos: insumosPedido.map(insumo => ({

                id_insumo: insumo.id_insumo,

                cantidad: insumo.cantidad

            }))

        };

        const confirmar = confirm(
            "¿Deseas generar este pedido de compra?"
        );

        if (!confirmar) return;

        try {

            btnGenerarPedido.disabled = true;

            btnGenerarPedido.innerHTML = `
                <i class="fas fa-spinner fa-spin"></i>
                Generando pedido...
            `;

            const respuesta = await fetch(
                "/gerente/compras/generar",
                {
                    method: "POST",

                    headers: {
                        "Content-Type": "application/json"
                    },

                    body: JSON.stringify(datosPedido)
                }
            );

            const datos = await respuesta.json();

            if (!respuesta.ok) {

                throw new Error(
                    datos.error || "No se pudo generar el pedido."
                );

            }

            mostrarMensaje(
                `${datos.mensaje} Número de pedido: #${datos.id_compra}. Total estimado: ${formatoMoneda.format(datos.total)}.`,
                "success"
            );

            mostrarNotificacion(
                `Pedido #${datos.id_compra} generado correctamente.`
            );

            // Actualizar estadísticas y limpiar el formulario
            setTimeout(() => {

                location.reload();

            }, 1800);

        } catch (error) {

            mostrarMensaje(
                error.message,
                "error"
            );

            mostrarNotificacion(
                error.message,
                "error"
            );

        } finally {

            btnGenerarPedido.disabled = false;

            btnGenerarPedido.innerHTML = `
                <i class="far fa-paper-plane"></i>
                Generar Pedido
            `;

        }

    });


    // ==========================================
    // INICIALIZAR
    // ==========================================

    if (seleccionarInsumo) {
        seleccionarInsumo.disabled = true;
    }

    renderizarPedido();

});

/* ==========================================
   PROVEEDORES - LA CANTINA
========================================== */

document.addEventListener("DOMContentLoaded", () => {

    const $ = id => document.getElementById(id);

    let proveedores = [];
    let catalogoInsumos = [];
    let proveedorSeleccionado = null;
    let idEstadoPendiente = null;
    let estadoPendiente = null;
    let graficaDesempeno = null;

    // ======================================
    // UTILIDADES
    // ======================================

    function escaparHTML(valor) {
        return String(valor ?? "").replace(/[&<>"']/g, c => ({
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#039;"
        })[c]);
    }

    function moneda(valor) {
        return Number(valor || 0).toLocaleString("es-MX", {
            style: "currency",
            currency: "MXN"
        });
    }

    function numero(valor) {
        return Number(valor || 0).toLocaleString("es-MX", {
            maximumFractionDigits: 2
        });
    }

    function mostrarToast(mensaje) {
        const toast = $("provToast");
        toast.textContent = mensaje;
        toast.classList.add("visible");

        clearTimeout(mostrarToast.timer);

        mostrarToast.timer = setTimeout(() => {
            toast.classList.remove("visible");
        }, 3500);
    }

    function cargar(visible) {
        $("provCargando").classList.toggle("visible", visible);
    }

    async function peticion(url, opciones = {}) {
        const respuesta = await fetch(url, {
            credentials: "same-origin",
            ...opciones,
            headers: {
                "Accept": "application/json",
                ...(opciones.body ? {"Content-Type": "application/json"} : {}),
                ...(opciones.headers || {})
            }
        });

        const resultado = await respuesta.json();

        if (!respuesta.ok || !resultado.ok) {
            throw new Error(
                resultado.mensaje || "No fue posible completar la operación."
            );
        }

        return resultado;
    }

    // ======================================
    // CARGAR CATÁLOGO DE INSUMOS
    // ======================================

    async function cargarCatalogoInsumos() {
        const resultado = await peticion(API_INSUMOS_PROVEEDORES);
        catalogoInsumos = resultado.insumos || [];
    }

    // ======================================
    // RENDERIZAR CASILLAS DE INSUMOS
    // ======================================

    function renderizarSelectorInsumos(seleccionados = []) {
        const contenedor = $("listaInsumosProveedor");
        const busqueda = $("buscarInsumo").value.trim().toLowerCase();

        if (!catalogoInsumos.length) {
            contenedor.innerHTML = `
                <p class="prov-sin-insumos">
                    No hay insumos registrados en el almacén.
                </p>
            `;
            actualizarContadorInsumos();
            return;
        }

        const seleccion = new Set(seleccionados.map(Number));

        const filtrados = catalogoInsumos.filter(insumo =>
            insumo.nombre.toLowerCase().includes(busqueda)
        );

        if (!filtrados.length) {
            contenedor.innerHTML = `
                <p class="prov-sin-insumos">
                    No se encontraron insumos.
                </p>
            `;
            actualizarContadorInsumos();
            return;
        }

        contenedor.innerHTML = filtrados.map(insumo => `
            <label class="prov-insumo-opcion">
                <input
                    type="checkbox"
                    name="insumosProveedor"
                    value="${insumo.id}"
                    ${seleccion.has(Number(insumo.id)) ? "checked" : ""}
                >
                <span>${escaparHTML(insumo.nombre)}</span>
            </label>
        `).join("");

        actualizarContadorInsumos();
    }

    function obtenerInsumosSeleccionados() {
        return [
            ...document.querySelectorAll(
                '#listaInsumosProveedor input[name="insumosProveedor"]:checked'
            )
        ].map(input => Number(input.value));
    }

    function actualizarContadorInsumos() {
        $("contadorInsumos").textContent =
            `${obtenerInsumosSeleccionados().length} seleccionados`;
    }

    // ======================================
    // CARGAR PROVEEDORES
    // ======================================

    async function cargarProveedores() {
        cargar(true);

        try {
            const parametros = new URLSearchParams({
                estado: $("filtroEstado").value,
                buscar: $("buscarProveedor").value.trim()
            });

            const resultado = await peticion(
                `${API_PROVEEDORES}?${parametros.toString()}`
            );

            proveedores = resultado.proveedores || [];

            actualizarIndicadores(resultado.indicadores);
            renderizarProveedores();
            actualizarSelectHistorial();

            if (proveedorSeleccionado) {
                const existe = proveedores.some(
                    p => Number(p.id) === Number(proveedorSeleccionado.id)
                );

                if (existe) {
                    await seleccionarProveedor(proveedorSeleccionado.id);
                } else {
                    proveedorSeleccionado = null;
                    mostrarDetalleVacio();
                }
            } else if (proveedores.length) {
                await seleccionarProveedor(proveedores[0].id);
            } else {
                mostrarDetalleVacio();
            }

        } catch (error) {
            console.error("ERROR PROVEEDORES:", error);
            mostrarToast(error.message);

            $("tablaProveedores").innerHTML = `
                <tr><td colspan="7">No fue posible cargar los proveedores.</td></tr>
            `;

        } finally {
            cargar(false);
        }
    }

    function actualizarIndicadores(datos) {
        $("totalProveedores").textContent =
            numero(datos.total_proveedores);

        $("totalCompras").textContent =
            numero(datos.total_compras);

        $("gastoProveedores").textContent =
            moneda(datos.gasto_total);

        $("proveedoresInactivos").textContent =
            numero(datos.proveedores_inactivos);
    }

    // ======================================
    // TABLA DE PROVEEDORES
    // ======================================

    function renderizarProveedores() {
        const tabla = $("tablaProveedores");

        if (!proveedores.length) {
            tabla.innerHTML = `
                <tr><td colspan="7">No se encontraron proveedores.</td></tr>
            `;
            return;
        }

        tabla.innerHTML = proveedores.map((p, indice) => {
            const seleccionado =
                proveedorSeleccionado &&
                Number(proveedorSeleccionado.id) === Number(p.id);

            return `
                <tr class="${seleccionado ? "seleccionado" : ""}"
                    data-id="${p.id}">

                    <td>${indice + 1}</td>
                    <td class="nombre-proveedor">${escaparHTML(p.nombre)}</td>
                    <td>${escaparHTML(p.telefono || "Sin teléfono")}</td>
                    <td>${escaparHTML(p.correo || "Sin correo")}</td>

                    <td>
                        <span class="prov-estado ${p.estado === "Activo" ? "activo" : "inactivo"}">
                            ${escaparHTML(p.estado)}
                        </span>
                    </td>

                    <td>${numero(p.total_insumos)}</td>

                    <td>
                        <div class="prov-acciones">
                            <button type="button" data-accion="ver"
                                    data-id="${p.id}" title="Ver">
                                <i class="bi bi-eye"></i>
                            </button>

                            <button type="button" data-accion="editar"
                                    data-id="${p.id}" title="Editar">
                                <i class="bi bi-pencil"></i>
                            </button>

                            <button type="button" data-accion="estado"
                                    data-id="${p.id}"
                                    title="${p.estado === "Activo" ? "Desactivar" : "Activar"}">
                                <i class="bi ${p.estado === "Activo" ? "bi-toggle-on" : "bi-toggle-off"}"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        }).join("");
    }

    // ======================================
    // DETALLE DEL PROVEEDOR
    // ======================================

    async function seleccionarProveedor(id) {
        try {
            const resultado = await peticion(
                API_DETALLE_PROVEEDOR.replace("/0", `/${id}`)
            );

            proveedorSeleccionado = resultado.proveedor;

            renderizarProveedores();
            renderizarDetalle(resultado.proveedor);
            renderizarProductos(resultado.insumos);
            renderizarHistorial(resultado.historial);

        } catch (error) {
            console.error(error);
            mostrarToast(error.message);
        }
    }

    function renderizarDetalle(p) {
        $("detalleProveedor").innerHTML = `
            <div class="prov-identidad">
                <div class="prov-identidad-icono">
                    <i class="bi bi-shop"></i>
                </div>
                <div>
                    <h3>${escaparHTML(p.nombre)}</h3>
                    <span class="prov-estado ${p.estado === "Activo" ? "activo" : "inactivo"}">
                        ${escaparHTML(p.estado)}
                    </span>
                </div>
            </div>

            <div class="prov-dato">
                <i class="bi bi-telephone"></i>
                <strong>Teléfono:</strong>
                <span>${escaparHTML(p.telefono || "No registrado")}</span>
            </div>

            <div class="prov-dato">
                <i class="bi bi-envelope"></i>
                <strong>Correo:</strong>
                <span>${escaparHTML(p.correo || "No registrado")}</span>
            </div>

            <div class="prov-dato">
                <i class="bi bi-geo-alt"></i>
                <strong>Dirección:</strong>
                <span>${escaparHTML(p.direccion || "No registrada")}</span>
            </div>

            <div class="prov-dato">
                <i class="bi bi-box-seam"></i>
                <strong>Insumos:</strong>
                <span>${numero((p.insumos || []).length)}</span>
            </div>
        `;

        $("resumenCompras").innerHTML = `
            <div class="prov-resumen-dato">
                <span>Compras registradas</span>
                <strong>${numero(p.total_compras)}</strong>
            </div>
            <div class="prov-resumen-dato">
                <span>Gasto acumulado</span>
                <strong>${moneda(p.gasto_total)}</strong>
            </div>
        `;
    }

    function mostrarDetalleVacio() {
        $("detalleProveedor").innerHTML = `
            <div class="prov-detalle-vacio">
                <i class="bi bi-person-lines-fill"></i>
                <p>Selecciona un proveedor para consultar sus datos.</p>
            </div>
        `;

        $("tablaProductos").innerHTML =
            `<tr><td colspan="2">Selecciona un proveedor.</td></tr>`;

        $("tablaHistorial").innerHTML =
            `<tr><td colspan="4">Selecciona un proveedor.</td></tr>`;

        $("resumenCompras").innerHTML =
            "<p>Selecciona un proveedor para ver su resumen.</p>";
    }

    // ======================================
    // INSUMOS DEL PROVEEDOR
    // ======================================

    function renderizarProductos(insumos) {
        if (!insumos || !insumos.length) {
            $("tablaProductos").innerHTML = `
                <tr>
                    <td colspan="2">
                        Este proveedor no tiene insumos asignados.
                    </td>
                </tr>
            `;
            return;
        }

        $("tablaProductos").innerHTML = insumos.map((insumo, indice) => `
            <tr>
                <td>${indice + 1}</td>
                <td>${escaparHTML(insumo.nombre)}</td>
            </tr>
        `).join("");
    }

    // ======================================
    // HISTORIAL
    // ======================================

    function renderizarHistorial(compras) {
        if (!compras || !compras.length) {
            $("tablaHistorial").innerHTML = `
                <tr><td colspan="4">No hay compras registradas.</td></tr>
            `;
            return;
        }

        $("tablaHistorial").innerHTML = compras.map(c => `
            <tr>
                <td>${escaparHTML(c.folio)}</td>
                <td>${escaparHTML(c.fecha)}</td>
                <td>${moneda(c.total)}</td>
                <td>${escaparHTML(c.estado)}</td>
            </tr>
        `).join("");
    }

    function actualizarSelectHistorial() {
        const select = $("filtroHistorialProveedor");
        const anterior = select.value;

        select.innerHTML = `<option value="">Selecciona un proveedor</option>`;

        proveedores.forEach(p => {
            const opcion = document.createElement("option");
            opcion.value = p.id;
            opcion.textContent = p.nombre;
            select.appendChild(opcion);
        });

        if ([...select.options].some(o => o.value === anterior)) {
            select.value = anterior;
        }
    }

    // ======================================
    // MODAL: NUEVO PROVEEDOR
    // ======================================

    function abrirModal() {
        $("modalProveedor").classList.add("visible");
    }

    function cerrarModal() {
        $("modalProveedor").classList.remove("visible");
        $("formProveedor").reset();
        $("idProveedor").value = "";
        $("buscarInsumo").value = "";
        renderizarSelectorInsumos([]);
    }

    function nuevoProveedor() {
        $("formProveedor").reset();
        $("idProveedor").value = "";
        $("estadoProveedor").value = "Activo";
        $("buscarInsumo").value = "";

        $("tituloModalProveedor").innerHTML =
            '<i class="bi bi-person-plus"></i> Nuevo proveedor';

        renderizarSelectorInsumos([]);
        abrirModal();
    }

    // ======================================
    // MODAL: EDITAR PROVEEDOR
    // ======================================

    async function editarProveedor(id) {
        try {
            cargar(true);

            const resultado = await peticion(
                API_DETALLE_PROVEEDOR.replace("/0", `/${id}`)
            );

            const p = resultado.proveedor;

            $("idProveedor").value = p.id;
            $("nombreProveedor").value = p.nombre;
            $("telefonoProveedor").value = p.telefono;
            $("correoProveedor").value = p.correo;
            $("direccionProveedor").value = p.direccion;
            $("estadoProveedor").value = p.estado;
            $("buscarInsumo").value = "";

            $("tituloModalProveedor").innerHTML =
                '<i class="bi bi-pencil-square"></i> Editar proveedor';

            renderizarSelectorInsumos(
                resultado.insumos.map(insumo => insumo.id)
            );

            abrirModal();

        } catch (error) {
            mostrarToast(error.message);
        } finally {
            cargar(false);
        }
    }

    // ======================================
    // GUARDAR / ACTUALIZAR
    // ======================================

    async function guardarProveedor(evento) {
        evento.preventDefault();

        const id = $("idProveedor").value;

        const datos = {
            nombre: $("nombreProveedor").value.trim(),
            telefono: $("telefonoProveedor").value.trim(),
            correo: $("correoProveedor").value.trim(),
            direccion: $("direccionProveedor").value.trim(),
            estado: $("estadoProveedor").value,
            insumos: obtenerInsumosSeleccionados()
        };

        if (!datos.nombre) {
            mostrarToast("El nombre del proveedor es obligatorio.");
            return;
        }

        const boton = $("formProveedor").querySelector(
            'button[type="submit"]'
        );

        boton.disabled = true;
        cargar(true);

        try {
            if (id) {
                await peticion(`${API_PROVEEDORES}/${id}`, {
                    method: "PUT",
                    body: JSON.stringify(datos)
                });

                mostrarToast("Proveedor actualizado correctamente.");
            } else {
                await peticion(API_PROVEEDORES, {
                    method: "POST",
                    body: JSON.stringify(datos)
                });

                mostrarToast("Proveedor registrado correctamente.");
            }

            cerrarModal();
            proveedorSeleccionado = null;
            await cargarProveedores();

        } catch (error) {
            mostrarToast(error.message);
        } finally {
            boton.disabled = false;
            cargar(false);
        }
    }

    // ======================================
    // CAMBIAR ESTADO
    // ======================================

    function solicitarCambioEstado(id) {
        const p = proveedores.find(x => Number(x.id) === Number(id));
        if (!p) return;

        idEstadoPendiente = p.id;
        estadoPendiente = p.estado === "Activo" ? "Inactivo" : "Activo";

        $("tituloConfirmacion").textContent =
            estadoPendiente === "Inactivo"
                ? "Desactivar proveedor"
                : "Activar proveedor";

        $("mensajeConfirmacion").textContent =
            `¿Deseas cambiar el estado de ${p.nombre} a ${estadoPendiente}?`;

        $("modalEstadoProveedor").classList.add("visible");
    }

    async function confirmarCambioEstado() {
        if (!idEstadoPendiente) return;

        cargar(true);

        try {
            await peticion(
                API_ESTADO_PROVEEDOR.replace(
                    "/0/estado",
                    `/${idEstadoPendiente}/estado`
                ),
                {
                    method: "PATCH",
                    body: JSON.stringify({estado: estadoPendiente})
                }
            );

            $("modalEstadoProveedor").classList.remove("visible");
            proveedorSeleccionado = null;

            mostrarToast("Estado actualizado correctamente.");
            await cargarProveedores();

        } catch (error) {
            mostrarToast(error.message);
        } finally {
            idEstadoPendiente = null;
            estadoPendiente = null;
            cargar(false);
        }
    }

    // ======================================
    // DESEMPEÑO
    // ======================================

    async function cargarDesempeno() {
        try {
            const resultado = await peticion(API_PROVEEDORES);
            const datos = resultado.proveedores
                .filter(p => Number(p.gasto) > 0)
                .sort((a, b) => b.gasto - a.gasto);

            if (graficaDesempeno) {
                graficaDesempeno.destroy();
            }

            graficaDesempeno = new Chart($("graficaDesempeno"), {
                type: "bar",
                data: {
                    labels: datos.map(p => p.nombre),
                    datasets: [{
                        label: "Gasto acumulado",
                        data: datos.map(p => p.gasto),
                        backgroundColor: "#8b1725",
                        borderRadius: 7
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {display: false},
                        tooltip: {
                            callbacks: {
                                label: ctx => moneda(ctx.raw)
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                callback: v => "$" + Number(v).toLocaleString("es-MX")
                            }
                        }
                    }
                }
            });

        } catch (error) {
            mostrarToast(error.message);
        }
    }

    // ======================================
    // PESTAÑAS
    // ======================================

    function cambiarTab(nombre) {
        document.querySelectorAll(".prov-tab").forEach(tab => {
            tab.classList.toggle("activo", tab.dataset.tab === nombre);
        });

        document.querySelectorAll(".prov-vista").forEach(vista => {
            vista.classList.remove("activa");
        });

        const vistas = {
            proveedores: "vistaProveedores",
            historial: "vistaHistorial",
            desempeno: "vistaDesempeno"
        };

        $(vistas[nombre]).classList.add("activa");

        if (nombre === "desempeno") {
            cargarDesempeno();
        }
    }

    // ======================================
    // EVENTOS
    // ======================================

    $("btnNuevoProveedor").addEventListener("click", nuevoProveedor);
    $("cerrarModalProveedor").addEventListener("click", cerrarModal);
    $("cancelarModalProveedor").addEventListener("click", cerrarModal);

    $("formProveedor").addEventListener("submit", guardarProveedor);

    $("listaInsumosProveedor").addEventListener("change", actualizarContadorInsumos);

    $("buscarInsumo").addEventListener("input", () => {
        const seleccionados = obtenerInsumosSeleccionados();
        renderizarSelectorInsumos(seleccionados);
    });

    $("tablaProveedores").addEventListener("click", evento => {
        const boton = evento.target.closest("button[data-accion]");

        if (!boton) {
            const fila = evento.target.closest("tr[data-id]");
            if (fila) seleccionarProveedor(fila.dataset.id);
            return;
        }

        const id = boton.dataset.id;

        if (boton.dataset.accion === "ver") seleccionarProveedor(id);
        if (boton.dataset.accion === "editar") editarProveedor(id);
        if (boton.dataset.accion === "estado") solicitarCambioEstado(id);
    });

    $("confirmarCambioEstado").addEventListener(
        "click",
        confirmarCambioEstado
    );

    $("cancelarCambioEstado").addEventListener("click", () => {
        $("modalEstadoProveedor").classList.remove("visible");
        idEstadoPendiente = null;
        estadoPendiente = null;
    });

    $("filtroEstado").addEventListener("change", cargarProveedores);

    let temporizadorBusqueda;

    $("buscarProveedor").addEventListener("input", () => {
        clearTimeout(temporizadorBusqueda);
        temporizadorBusqueda = setTimeout(cargarProveedores, 350);
    });

    $("filtroHistorialProveedor").addEventListener("change", evento => {
        if (evento.target.value) {
            seleccionarProveedor(evento.target.value);
        }
    });

    document.querySelectorAll(".prov-tab").forEach(tab => {
        tab.addEventListener("click", () => cambiarTab(tab.dataset.tab));
    });

    // ======================================
    // INICIALIZAR
    // ======================================

    async function iniciar() {
        cargar(true);

        try {
            await cargarCatalogoInsumos();
            await cargarProveedores();
        } catch (error) {
            console.error(error);
            mostrarToast(error.message);
        } finally {
            cargar(false);
        }
    }

    iniciar();

});
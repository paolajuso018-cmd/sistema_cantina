
/* =====================================================
   LA CANTINA - MÓDULO DE VENTAS DEL CAJERO
   ===================================================== */

(() => {
    "use strict";

    const API = "/ventas/api";
    const $ = id => document.getElementById(id);

    const money = amount => Number(amount || 0).toLocaleString("es-MX", {
        style: "currency",
        currency: "MXN"
    });

    const state = {
        productos: [],
        categorias: [],
        mesas: [],
        cuentas: [],
        cuenta: null,
        detalles: [],
        categoria: "all",
        metodo: "Efectivo",
        cuentaCobrada: false
    };

    // =================================================
    // COMUNICACIÓN CON FLASK
    // =================================================

    async function api(url, options = {}) {
        const response = await fetch(url, {
            ...options,
            headers: {
                "Content-Type": "application/json",
                ...(options.headers || {})
            }
        });

        let data;

        try {
            data = await response.json();
        } catch {
            throw new Error("El servidor devolvió una respuesta no válida.");
        }

        if (!response.ok || data.ok === false) {
            throw new Error(
                data.mensaje ||
                data.error ||
                "No se pudo completar la operación."
            );
        }

        return data;
    }

    // =================================================
    // NOTIFICACIONES
    // =================================================

    function notify(text) {
        const toast = $("notificacionVentas");
        toast.textContent = text;
        toast.classList.add("show");

        setTimeout(() => {
            toast.classList.remove("show");
        }, 2800);
    }

    function message(text, error = false) {
        $("mensajeVentas").textContent = text || "";
        $("mensajeVentas").style.color = error ? "#bd1e2d" : "#278b3c";
    }

    // =================================================
    // MODAL DE MESAS Y CUENTAS
    // =================================================

    function openAccountsModal() {
        $("modalCuentas").classList.add("open");
        $("modalCuentas").setAttribute("aria-hidden", "false");
    }

    function closeAccountsModal() {
        $("modalCuentas").classList.remove("open");
        $("modalCuentas").setAttribute("aria-hidden", "true");
    }

    // =================================================
    // UTILIDADES
    // =================================================

    function escapeHtml(value) {
        return String(value ?? "").replace(/[&<>"']/g, character => ({
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#39;"
        }[character]));
    }

    function imageUrl(path) {
        const value = String(path || "").trim();

        if (
            value.startsWith("http://") ||
            value.startsWith("https://") ||
            value.startsWith("/")
        ) {
            return value;
        }

        return `/static/${value.replace(/^static\//, "")}`;
    }

    // =================================================
    // CARGAR PRODUCTOS
    // =================================================

    async function loadProducts() {
        const data = await api(`${API}/productos`);

        state.productos = data.productos || [];
        state.categorias = data.categorias || [];

        renderCategories();
        renderProducts();
    }

    // =================================================
    // CATEGORÍAS
    // =================================================

    function renderCategories() {
        const icons = [
            "fa-border-all",
            "fa-martini-glass",
            "fa-wine-bottle",
            "fa-beer-mug-empty",
            "fa-utensils",
            "fa-cookie-bite"
        ];

        $("categorias").innerHTML = `
            <button
                class="category-btn ${state.categoria === "all" ? "active" : ""}"
                data-category="all"
                type="button">

                <i class="fa-solid fa-border-all"></i>
                <span>Todos</span>
            </button>

            ${state.categorias.map((categoria, index) => `
                <button
                    class="category-btn ${
                        String(state.categoria) === String(categoria.id_categoria)
                            ? "active" : ""
                    }"
                    data-category="${categoria.id_categoria}"
                    type="button">

                    <i class="fa-solid ${icons[(index + 1) % icons.length]}"></i>
                    <span>${escapeHtml(categoria.nombre)}</span>
                </button>
            `).join("")}
        `;

        $("categorias").querySelectorAll("button").forEach(button => {
            button.addEventListener("click", () => {
                state.categoria = button.dataset.category;
                renderCategories();
                renderProducts();
            });
        });
    }

    // =================================================
    // PRODUCTOS
    // =================================================

    function renderProducts() {
        const query = $("buscarProducto").value.trim().toLowerCase();

        const filtered = state.productos.filter(producto => {
            const categoryOk =
                state.categoria === "all" ||
                String(producto.id_categoria) === String(state.categoria);

            const textOk = `
                ${producto.nombre}
                ${producto.codigo || ""}
            `.toLowerCase().includes(query);

            return categoryOk && textOk;
        });

        if (!filtered.length) {
            $("productos").innerHTML = `
                <p class="pos-loading">No se encontraron productos.</p>
            `;
            return;
        }

        $("productos").innerHTML = filtered.map(producto => {
            const image = producto.imagen
                ? `
                    <img
                        class="product-image"
                        src="${escapeHtml(imageUrl(producto.imagen))}"
                        alt="${escapeHtml(producto.nombre)}"
                        onerror="this.style.display='none';">
                `
                : "";

            return `
                <article class="product-card">
                    ${image}

                    <div class="product-info">
                        <h3>${escapeHtml(producto.nombre)}</h3>

                        <span class="product-price">
                            ${money(producto.precio_venta)}
                        </span>

                        <div class="product-bottom">
                            <span class="product-category">
                                ${escapeHtml(producto.categoria || "")}
                            </span>

                            <button
                                class="add-product"
                                type="button"
                                data-product="${producto.id_producto}"
                                title="Agregar producto">

                                <i class="fa-solid fa-plus"></i>
                            </button>
                        </div>
                    </div>
                </article>
            `;
        }).join("");

        $("productos").querySelectorAll("[data-product]").forEach(button => {
            button.addEventListener("click", () => {
                addProduct(Number(button.dataset.product));
            });
        });
    }

    // =================================================
    // CONSULTAR MESAS Y CUENTAS
    // =================================================

    async function refreshAccounts() {
        const data = await api(`${API}/cuentas`);

        state.cuentas = data.cuentas || [];
        state.mesas = data.mesas || [];

        renderAccounts();
    }

    // =================================================
    // MOSTRAR MESAS Y CUENTAS DE BARRA
    // =================================================

    
function renderAccounts() {

    const openByTable = new Map(
        state.cuentas
            .filter(cuenta => cuenta.tipo_cuenta === "Mesa")
            .map(cuenta => [
                Number(cuenta.id_mesa),
                cuenta
            ])
    );

    // =========================================
    // MOSTRAR MESAS
    // =========================================

    $("listaMesas").innerHTML = state.mesas.length

        ? state.mesas.map(mesa => {

            const account = openByTable.get(
                Number(mesa.id_mesa)
            );

            // Priorizar las cuentas abiertas.
            const status = account
                ? "Ocupada"
                : (mesa.disponibilidad || "Disponible");

            const active = mesa.estado === "Activa";

            const statusClass = {
                "Disponible": "available",
                "Reservada": "reserved",
                "Ocupada": "occupied"
            }[status] || "available";

            return `
                <button
                    class="table-card ${statusClass}"
                    data-table="${mesa.id_mesa}"
                    type="button"
                    ${!active ? "disabled" : ""}>

                    <i class="fa-solid fa-chair"></i>

                    <strong>
                        ${escapeHtml(mesa.nombre_mesa)}
                    </strong>

                    <small>
                        ${
                            status === "Ocupada" && account
                                ? "Ocupada · " + money(account.total)
                                : status
                        }
                    </small>

                    <small>
                        ${
                            account
                                ? "Continuar cuenta"
                                : status === "Reservada"
                                    ? "Reservación asignada"
                                    : mesa.capacidad + " personas"
                        }
                    </small>

                </button>
            `;

        }).join("")

        : `
            <p class="pos-loading">
                No hay mesas registradas.
            </p>
        `;

    // =========================================
    // EVENTOS DE LAS MESAS
    // =========================================

    $("listaMesas")
        .querySelectorAll("[data-table]")
        .forEach(button => {

            button.addEventListener("click", async () => {

                const id = Number(button.dataset.table);

                const existing = openByTable.get(id);

                const selectedTable = state.mesas.find(
                    mesa => Number(mesa.id_mesa) === id
                );

                // No permitir abrir una mesa reservada
                // desde caja antes de recibir al cliente.
                if (
                    !existing &&
                    selectedTable?.disponibilidad === "Reservada"
                ) {
                    notify(
                        "Esta mesa tiene una reservación. Recepción debe recibir al cliente primero."
                    );
                    return;
                }

                if (existing) {

                    // Recuperar cuenta abierta.
                    await selectAccount(existing.id_venta);

                } else {

                    // Abrir cuenta de mesa disponible.
                    await openAccount("Mesa", id);

                }

            });

        });

    // =========================================
    // MOSTRAR CUENTAS DE BARRA
    // =========================================

    const bars = state.cuentas.filter(
        cuenta => cuenta.tipo_cuenta === "Barra"
    );

    $("listaBarra").innerHTML = bars.length

        ? bars.map(cuenta => `

            <div class="bar-account">

                <div>

                    <strong>
                        ${escapeHtml(cuenta.folio)}
                    </strong>

                    <br>

                    <small>
                        ${escapeHtml(cuenta.fecha_venta || "")}
                        ·
                        ${money(cuenta.total)}
                    </small>

                </div>

                <button
                    type="button"
                    data-account="${cuenta.id_venta}">

                    Continuar

                </button>

            </div>

        `).join("")

        : `
            <p class="pos-loading">
                No hay cuentas de Barra abiertas.
            </p>
        `;

    // =========================================
    // EVENTOS DE CUENTAS DE BARRA
    // =========================================

    $("listaBarra")
        .querySelectorAll("[data-account]")
        .forEach(button => {

            button.addEventListener("click", () => {

                selectAccount(
                    Number(button.dataset.account)
                );

            });

        });

}


    // =================================================
    // ABRIR CUENTA NUEVA
    // =================================================

    async function openAccount(type, tableId = null) {
        if (type === "Mesa" && !tableId) {
            notify("Primero debes seleccionar una mesa disponible.");
            openAccountsModal();
            return;
        }

        if (type === "Mesa") {
            const mesa = state.mesas.find(
                item => Number(item.id_mesa) === Number(tableId)
            );

            if (!mesa || mesa.estado !== "Activa") {
                notify("La mesa seleccionada no está disponible.");
                return;
            }

            const existing = state.cuentas.find(cuenta =>
                cuenta.tipo_cuenta === "Mesa" &&
                Number(cuenta.id_mesa) === Number(tableId)
            );

            if (existing) {
                await selectAccount(existing.id_venta);
                return;
            }
        }

        try {
            const data = await api(`${API}/abrir-cuenta`, {
                method: "POST",
                body: JSON.stringify({
                    tipo_cuenta: type,
                    id_mesa: type === "Mesa" ? tableId : null
                })
            });

            notify(data.mensaje || "Cuenta abierta correctamente.");

            await refreshAccounts();
            await selectAccount(data.id_venta);

        } catch (error) {
            notify(error.message);

            try {
                await refreshAccounts();
            } catch (refreshError) {
                console.error(refreshError);
            }
        }
    }

    // =================================================
    // SELECCIONAR CUENTA
    // =================================================

    async function selectAccount(id) {
        try {
            const data = await api(`${API}/cuenta/${id}`);

            state.cuenta = data.cuenta;
            state.detalles = data.detalles || [];

            // IMPORTANTE:
            // Al seleccionar una cuenta abierta se habilita la edición.
            state.cuentaCobrada = false;

            // Limpiar datos de pago al seleccionar otra cuenta.
            [
                "montoRecibido",
                "referenciaTarjeta",
                "referenciaTransferencia",
                "referenciaMixta"
            ].forEach(fieldId => {
                const field = $(fieldId);
                if (field) field.value = "";
            });

            [
                "mixtoEfectivo",
                "mixtoTarjeta",
                "mixtoRecibido"
            ].forEach(fieldId => {
                const field = $(fieldId);
                if (field) field.value = "0";
            });

            if ($("cambio")) $("cambio").textContent = money(0);
            if ($("cambioMixto")) $("cambioMixto").textContent = money(0);

            const accountName = state.cuenta.tipo_cuenta === "Mesa"
                ? state.cuenta.nombre_mesa
                : "Barra";

            $("cuentaActual").textContent =
                `${state.cuenta.folio} · ${accountName}`;

            closeAccountsModal();
            updateChange();
            renderCart();

        } catch (error) {
            notify(error.message);
        }
    }

    // =================================================
    // AGREGAR PRODUCTO
    // =================================================

    async function addProduct(id) {
        if (!state.cuenta || state.cuentaCobrada) {
            openAccountsModal();
            notify("Selecciona una cuenta abierta para agregar productos.");
            return;
        }

        try {
            const data = await api(`${API}/agregar-producto`, {
                method: "POST",
                body: JSON.stringify({
                    id_venta: state.cuenta.id_venta,
                    id_producto: id,
                    cantidad: 1
                })
            });

            await selectAccount(state.cuenta.id_venta);
            message(data.mensaje);

        } catch (error) {
            message(error.message, true);
        }
    }

    // =================================================
    // MODIFICAR O ELIMINAR PRODUCTO
    // =================================================

    async function updateLine(detailId, quantity) {
        // Solo se bloquean las cuentas cobradas.
        // Una cuenta abierta permite eliminar productos con cantidad 0.
        if (!state.cuenta || state.cuentaCobrada) {
            return;
        }

        try {
            const idVenta = state.cuenta.id_venta;

            await api(`${API}/actualizar-producto`, {
                method: "POST",
                body: JSON.stringify({
                    id_venta: idVenta,
                    id_detalle: detailId,
                    cantidad: quantity
                })
            });

            await selectAccount(idVenta);

        } catch (error) {
            notify(error.message);
        }
    }

    // =========================================
    // MODAL PERSONALIZADO DE CONFIRMACIÓN
    // =========================================

    function confirmAction() {
        return new Promise(resolve => {

            const modal = $("modalConfirmacion");
            const btnAceptar = $("aceptarConfirmacion");
            const btnCancelar = $("cancelarConfirmacion");

            modal.classList.add("active");
            modal.setAttribute("aria-hidden", "false");

            function closeModal(result) {
                modal.classList.remove("active");
                modal.setAttribute("aria-hidden", "true");

                btnAceptar.removeEventListener("click", accept);
                btnCancelar.removeEventListener("click", cancel);

                resolve(result);
            }

            function accept() {
                closeModal(true);
            }

            function cancel() {
                closeModal(false);
            }

            btnAceptar.addEventListener("click", accept);
            btnCancelar.addEventListener("click", cancel);
        });
    }

    // =================================================
    // LIMPIAR CUENTA
    // SOLO SE EJECUTA AL PRESIONAR EL BOTÓN
    // =================================================

    async function clearAccount() {
        if (!state.cuenta) {
            notify("Primero selecciona una cuenta.");
            return;
        }

        if (state.cuentaCobrada) {
            notify("No puedes limpiar una cuenta que ya fue cobrada.");
            return;
        }

        if (!state.detalles.length) {
            notify("La cuenta ya está vacía.");
            return;
        }

        const confirmado = await confirmAction();

        if(!confirmado){
            return;
        }

        const idVenta = state.cuenta.id_venta;
        const detalles = [...state.detalles];

        try {
            for (const detalle of detalles) {
                await api(`${API}/actualizar-producto`, {
                    method: "POST",
                    body: JSON.stringify({
                        id_venta: idVenta,
                        id_detalle: detalle.id_detalle_venta,
                        cantidad: 0
                    })
                });
            }

            await selectAccount(idVenta);
            notify("La cuenta se limpió correctamente.");

        } catch (error) {
            notify(error.message);
        }
    }

    // =================================================
    // DIBUJAR CARRITO
    // =================================================

    function renderCart() {
        const rows = state.detalles;
        const bloqueada = state.cuentaCobrada;

        $("carrito").innerHTML = rows.length
            ? rows.map(detail => `
                <tr>
                    <td>${escapeHtml(detail.nombre)}</td>

                    <td>
                        <div class="qty-control">
                            <button
                                data-minus="${detail.id_detalle_venta}"
                                type="button"
                                ${bloqueada ? "disabled" : ""}>
                                −
                            </button>

                            <span>${detail.cantidad}</span>

                            <button
                                data-plus="${detail.id_detalle_venta}"
                                type="button"
                                ${bloqueada ? "disabled" : ""}>
                                +
                            </button>
                        </div>
                    </td>

                    <td>${money(detail.precio_unitario)}</td>
                    <td>${money(detail.subtotal)}</td>

                    <td>
                        <button
                            class="remove-line"
                            data-remove="${detail.id_detalle_venta}"
                            type="button"
                            title="Eliminar"
                            ${bloqueada ? "disabled" : ""}>

                            <i class="fa-regular fa-trash-can"></i>
                        </button>
                    </td>
                </tr>
            `).join("")
            : `
                <tr>
                    <td colspan="5" class="empty-cart">
                        Agrega productos a esta cuenta.
                    </td>
                </tr>
            `;

        // RESTAR CANTIDAD
        $("carrito").querySelectorAll("[data-minus]").forEach(button => {
            button.addEventListener("click", () => {
                const detail = rows.find(
                    item => Number(item.id_detalle_venta) ===
                        Number(button.dataset.minus)
                );

                if (detail) {
                    updateLine(
                        detail.id_detalle_venta,
                        Number(detail.cantidad) - 1
                    );
                }
            });
        });

        // SUMAR CANTIDAD
        $("carrito").querySelectorAll("[data-plus]").forEach(button => {
            button.addEventListener("click", () => {
                const detail = rows.find(
                    item => Number(item.id_detalle_venta) ===
                        Number(button.dataset.plus)
                );

                if (detail) {
                    updateLine(
                        detail.id_detalle_venta,
                        Number(detail.cantidad) + 1
                    );
                }
            });
        });

        // ELIMINAR PRODUCTO COMPLETO
        $("carrito").querySelectorAll("[data-remove]").forEach(button => {
            button.addEventListener("click", () => {
                if (state.cuentaCobrada) return;

                updateLine(Number(button.dataset.remove), 0);
            });
        });

        const subtotal = Number(state.cuenta?.subtotal || 0);
        const total = Number(state.cuenta?.total || 0);

        $("subtotal").textContent = money(subtotal);
        $("total").textContent = money(total);

        $("btnCobrar").disabled =
            !state.cuenta || !rows.length || total <= 0 || bloqueada;

        $("btnTicket").disabled = !state.cuenta;

        $("btnVaciar").disabled =
            !state.cuenta || !rows.length || bloqueada;

        updateChange();
    }

    // =================================================
    // CALCULAR CAMBIO Y VALIDAR PAGOS
    // =================================================

    function updateChange() {
        const total = Number(state.cuenta?.total || 0);
        const method = state.metodo;
        let valid = false;

        if (method === "Efectivo") {
            const received = Number($("montoRecibido").value || 0);

            $("cambio").textContent = money(
                Math.max(0, received - total)
            );

            valid = received >= total && total > 0;

        } else if (method === "Tarjeta") {
            valid =
                $("referenciaTarjeta").value.trim().length > 0 &&
                total > 0;

        } else if (method === "Transferencia") {
            valid =
                $("referenciaTransferencia").value.trim().length > 0 &&
                total > 0;

        } else if (method === "Mixto") {
            const cash = Number($("mixtoEfectivo").value || 0);
            const card = Math.max(0, total - cash);
            const received = Number($("mixtoRecibido").value || 0);
            const reference = $("referenciaMixta").value.trim();

            $("mixtoTarjeta").value = card.toFixed(2);

            $("cambioMixto").textContent = money(
                Math.max(0, received - cash)
            );

            valid =
                cash >= 0 &&
                cash <= total &&
                received >= cash &&
                (card <= 0 || reference.length > 0) &&
                total > 0;
        }

        $("btnCobrar").dataset.paymentsValid = valid ? "1" : "0";
    }

    // =================================================
    // SELECCIONAR MÉTODO DE PAGO
    // =================================================

    function chooseMethod(method) {
        state.metodo = method;

        document.querySelectorAll(".payment-btn").forEach(button => {
            button.classList.toggle(
                "active",
                button.dataset.method === method
            );
        });

        $("pagoSimple").hidden = method === "Mixto";
        $("pagoEfectivo").hidden = method !== "Efectivo";
        $("pagoTarjeta").hidden = method !== "Tarjeta";
        $("pagoTransferencia").hidden = method !== "Transferencia";
        $("pagoMixto").hidden = method !== "Mixto";

        updateChange();
    }

    // =================================================
    // COBRAR VENTA
    // NO LIMPIAR EL CARRITO AUTOMÁTICAMENTE
    // =================================================

    async function charge() {
        if (!state.cuenta || state.cuentaCobrada) return;

        updateChange();

        if ($("btnCobrar").dataset.paymentsValid !== "1") {
            notify("Completa los datos del pago y verifica que cubran el total.");
            return;
        }

        const total = Number(state.cuenta.total || 0);
        const idVenta = state.cuenta.id_venta;
        let pagos = [];

        if (state.metodo === "Efectivo") {
            pagos = [{
                metodo: "Efectivo",
                monto: total,
                recibido: Number($("montoRecibido").value || 0)
            }];

        } else if (state.metodo === "Tarjeta") {
            pagos = [{
                metodo: "Tarjeta",
                monto: total,
                recibido: total,
                referencia: $("referenciaTarjeta").value.trim()
            }];

        } else if (state.metodo === "Transferencia") {
            pagos = [{
                metodo: "Transferencia",
                monto: total,
                recibido: total,
                referencia: $("referenciaTransferencia").value.trim()
            }];

        } else if (state.metodo === "Mixto") {
            const cash = Number($("mixtoEfectivo").value || 0);
            const card = Number($("mixtoTarjeta").value || 0);
            const received = Number($("mixtoRecibido").value || 0);
            const reference = $("referenciaMixta").value.trim();

            if (cash > 0) {
                pagos.push({
                    metodo: "Efectivo",
                    monto: cash,
                    recibido: received
                });
            }

            if (card > 0) {
                pagos.push({
                    metodo: "Tarjeta",
                    monto: card,
                    recibido: card,
                    referencia: reference
                });
            }
        }

        try {
            const data = await api(`${API}/cobrar`, {
                method: "POST",
                body: JSON.stringify({
                    id_venta: idVenta,
                    pagos: pagos
                })
            });

            notify(
                `${data.mensaje || "Venta cobrada correctamente."} Cambio: ${money(data.cambio)}`
            );

            // BLOQUEAR LA CUENTA DESPUÉS DEL COBRO.
            state.cuentaCobrada = true;

            // LIMPIAR CAMPOS DE PAGO.
            [
                "montoRecibido",
                "referenciaTarjeta",
                "referenciaTransferencia",
                "referenciaMixta"
            ].forEach(fieldId => {
                const field = $(fieldId);
                if (field) field.value = "";
            });

            [
                "mixtoEfectivo",
                "mixtoTarjeta",
                "mixtoRecibido"
            ].forEach(fieldId => {
                const field = $(fieldId);
                if (field) field.value = "0";
            });

            // RESTABLECER LOS INDICADORES DE CAMBIO.
            if ($("cambio")) {
                $("cambio").textContent = money(0);
            }

            if ($("cambioMixto")) {
                $("cambioMixto").textContent = money(0);
            }

            // CONSERVAR EL CARRITO VISIBLE.
            renderCart();

            await refreshAccounts();
            await printTicket(idVenta);

            // MOSTRAR MODAL PARA SELECCIONAR OTRA CUENTA.
            openAccountsModal();

        } catch (error) {
            notify(error.message);
        }
    }

    // =================================================
    // GENERAR E IMPRIMIR TICKET
    // =================================================

    async function printTicket(id) {
        try {
            const data = await api(`${API}/ticket/${id}`);

            const ticketWindow = window.open(
                "",
                "_blank",
                "width=420,height=700"
            );

            if (!ticketWindow) {
                notify("Permite las ventanas emergentes para imprimir el ticket.");
                return;
            }

            const venta = data.venta;

            ticketWindow.document.write(`
                <!DOCTYPE html>
                <html lang="es">
                <head>
                    <meta charset="UTF-8">
                    <title>Ticket ${escapeHtml(venta.folio)}</title>

                    <style>
                        body {
                            font-family: monospace;
                            padding: 18px;
                            color: #222;
                        }

                        h2, p {
                            text-align: center;
                        }

                        table {
                            width: 100%;
                            border-collapse: collapse;
                        }

                        td {
                            padding: 5px 0;
                            border-bottom: 1px dashed #aaa;
                        }

                        .right {
                            text-align: right;
                        }

                        .total {
                            font-weight: bold;
                            font-size: 18px;
                        }
                    </style>
                </head>

                <body>
                    <h2>LA CANTINA</h2>
                    <p>Tradición y buen ambiente</p>
                    <hr>

                    <p>
                        ${escapeHtml(venta.folio)}
                        <br>
                        ${escapeHtml(venta.fecha_venta)}
                        <br>
                        Cajero: ${escapeHtml(venta.cajero)}
                    </p>

                    <hr>

                    <table>
                        ${data.detalles.map(detail => `
                            <tr>
                                <td>
                                    ${escapeHtml(detail.nombre)}
                                    x ${detail.cantidad}
                                </td>

                                <td class="right">
                                    ${money(detail.subtotal)}
                                </td>
                            </tr>
                        `).join("")}
                    </table>

                    <hr>

                    <p class="right total">
                        TOTAL: ${money(venta.total)}
                    </p>

                    <p>
                        Pago: ${escapeHtml(venta.metodo_pago)}
                    </p>

                    <p>¡Gracias por tu visita!</p>

                    <script>
                        window.onload = function() {
                            window.print();
                        };
                    </script>
                </body>
                </html>
            `);

            ticketWindow.document.close();

        } catch (error) {
            notify(error.message);
        }
    }

    // =================================================
    // INICIAR MÓDULO
    // =================================================

    async function start() {
        // BUSCADOR
        $("buscarProducto").addEventListener("input", renderProducts);

        // CAMBIAR CUENTA
        $("btnCambiarCuenta").addEventListener("click", async () => {
            try {
                await refreshAccounts();
                openAccountsModal();
            } catch (error) {
                notify(error.message);
            }
        });

        // CERRAR MODAL
        $("cerrarCuentas").addEventListener("click", closeAccountsModal);

        // NUEVA CUENTA DE BARRA
        $("btnNuevaBarra").addEventListener("click", () => {
            openAccount("Barra");
        });

        // MÉTODOS DE PAGO
        $("metodosPago").querySelectorAll("button").forEach(button => {
            button.addEventListener("click", () => {
                chooseMethod(button.dataset.method);
            });
        });

        chooseMethod("Efectivo");

        // ACTUALIZAR CAMBIO
        [
            "montoRecibido",
            "referenciaTarjeta",
            "referenciaTransferencia",
            "mixtoEfectivo",
            "mixtoTarjeta",
            "referenciaMixta",
            "mixtoRecibido"
        ].forEach(id => {
            $(id).addEventListener("input", updateChange);
        });

        // COBRAR
        $("btnCobrar").addEventListener("click", charge);

        // TICKET
        $("btnTicket").addEventListener("click", () => {
            if (state.cuenta) {
                notify("El ticket se genera al cobrar la cuenta.");
            }
        });

        // LIMPIAR CUENTA
        $("btnVaciar").addEventListener("click", clearAccount);

        // CARGAR INFORMACIÓN
        try {
            await Promise.all([
                loadProducts(),
                refreshAccounts()
            ]);

            openAccountsModal();
            renderCart();

        } catch (error) {
            message(error.message, true);
            notify(error.message);
        }
    }

    // =================================================
    // EJECUTAR CUANDO CARGUE EL DOCUMENTO
    // =================================================

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", start);
    } else {
        start();
    }

})();

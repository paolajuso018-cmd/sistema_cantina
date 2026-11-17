
// ======================================================
// LA CANTINA - SISTEMA DE VENTAS
// ======================================================

let productos = [];
let categorias = [];
let cuentas = [];
let mesas = [];

let cuentaActiva = null;
let categoriaActiva = "todas";

const formatoDinero = valor =>
    Number(valor || 0).toLocaleString("es-MX", {
        style: "currency",
        currency: "MXN"
    });

const elemento = id => document.getElementById(id);


// ======================================================
// NOTIFICACIONES
// ======================================================

function notificar(mensaje) {
    const aviso = elemento("notificacion");

    if (!aviso) {
        alert(mensaje);
        return;
    }

    aviso.textContent = mensaje;
    aviso.classList.add("visible");

    setTimeout(() => {
        aviso.classList.remove("visible");
    }, 3000);
}


// ======================================================
// PETICIONES AL SERVIDOR
// ======================================================

async function peticion(url, opciones = {}) {

    const respuesta = await fetch(url, {
        headers: {
            "Content-Type": "application/json"
        },
        ...opciones
    });

    let datos;

    try {
        datos = await respuesta.json();
    } catch {
        throw new Error("El servidor no devolvió una respuesta válida.");
    }

    if (!respuesta.ok || !datos.ok) {
        throw new Error(datos.mensaje || "Ocurrió un error.");
    }

    return datos;
}


// ======================================================
// MODALES
// ======================================================

function mostrarModal(id) {
    const modal = elemento(id);

    if (modal) {
        modal.classList.add("visible");
    }
}

function cerrarModal(id) {
    const modal = elemento(id);

    if (modal) {
        modal.classList.remove("visible");
    }
}


// ======================================================
// FECHA
// ======================================================

function actualizarFecha() {
    const fecha = elemento("fechaActual");

    if (!fecha) return;

    fecha.textContent = new Date().toLocaleDateString("es-MX", {
        weekday: "long",
        day: "numeric",
        month: "long",
        year: "numeric"
    });
}


// ======================================================
// CARGA INICIAL
// ======================================================

async function inicializarVentas() {

    actualizarFecha();

    document.querySelectorAll("[data-cerrar]").forEach(boton => {
        boton.addEventListener("click", () => {
            cerrarModal(boton.dataset.cerrar);
        });
    });

    // Cargar productos y cuentas de manera independiente
    // para que un error no impida cargar el otro módulo.

    await Promise.allSettled([
        cargarProductos(),
        cargarCuentas()
    ]);

    conectarEventos();

}


// ======================================================
// CONECTAR EVENTOS
// ======================================================

function conectarEventos() {

    const buscar = elemento("buscarProducto");

    if (buscar) {
        buscar.addEventListener("input", dibujarProductos);
    }

    const btnBarra = elemento("btnAbrirBarra");

    if (btnBarra) {
        btnBarra.addEventListener("click", () => {
            elemento("nombreClienteBarra").value = "";
            mostrarModal("modalBarra");
        });
    }

    const confirmarMesa = elemento("confirmarMesa");

    if (confirmarMesa) {
        confirmarMesa.addEventListener("click", abrirCuentaMesa);
    }

    const confirmarBarra = elemento("confirmarBarra");

    if (confirmarBarra) {
        confirmarBarra.addEventListener("click", abrirCuentaBarra);
    }

    const btnCobrar = elemento("btnCobrar");

    if (btnCobrar) {
        btnCobrar.addEventListener("click", abrirModalCobro);
    }

    const btnAgregarPago = elemento("btnAgregarPago");

    if (btnAgregarPago) {
        btnAgregarPago.addEventListener("click", agregarFilaPago);
    }

    const listaPagos = elemento("listaPagos");

    if (listaPagos) {
        listaPagos.addEventListener("input", calcularResumenPagos);
        listaPagos.addEventListener("change", calcularResumenPagos);
    }

    const confirmarCobro = elemento("confirmarCobro");

    if (confirmarCobro) {
        confirmarCobro.addEventListener("click", confirmarPago);
    }

    const cerrarTicket = elemento("cerrarTicket");

    if (cerrarTicket) {
        cerrarTicket.addEventListener("click", () => {
            cerrarModal("modalTicket");
        });
    }

    const imprimirTicket = elemento("imprimirTicket");

    if (imprimirTicket) {
        imprimirTicket.addEventListener("click", imprimirComprobante);
    }
}


// ======================================================
// PRODUCTOS Y CATEGORÍAS
// ======================================================

async function cargarProductos() {

    const contenedor = elemento("productosGrid");
    const contenedorCategorias = elemento("categoriasProductos");

    if (contenedor) {
        contenedor.innerHTML = `
            <div class="estado-vacio">
                <i class="bi bi-arrow-repeat"></i>
                <p>Consultando menú...</p>
            </div>
        `;
    }

    try {

        const datos = await peticion(URL_PRODUCTOS);

        productos = datos.productos || [];
        categorias = datos.categorias || [];

        console.log("PRODUCTOS RECIBIDOS:", productos);
        console.log("CATEGORÍAS RECIBIDAS:", categorias);

        categoriaActiva = "todas";

        dibujarCategorias();
        dibujarProductos();

    } catch (error) {

        console.error("ERROR AL CARGAR PRODUCTOS:", error);

        if (contenedor) {
            contenedor.innerHTML = `
                <div class="estado-vacio">
                    <i class="bi bi-exclamation-triangle"></i>
                    <p>No fue posible cargar el menú.</p>
                    <small>${error.message}</small>
                </div>
            `;
        }

        if (contenedorCategorias) {
            contenedorCategorias.innerHTML = `
                <button class="categoria-btn activa"
                        data-categoria="todas">
                    Todos
                </button>
            `;
        }

        notificar(error.message);
    }
}


// ======================================================
// DIBUJAR CATEGORÍAS DESDE MYSQL
// ======================================================

function dibujarCategorias() {

    const contenedor = elemento("categoriasProductos");

    if (!contenedor) return;

    contenedor.innerHTML = `
        <button class="categoria-btn activa"
                data-categoria="todas">
            Todos
        </button>
    `;

    categorias.forEach(categoria => {

        contenedor.innerHTML += `
            <button class="categoria-btn"
                    data-categoria="${categoria.id_categoria}">
                ${categoria.nombre}
            </button>
        `;

    });

    contenedor.querySelectorAll(".categoria-btn").forEach(boton => {

        boton.addEventListener("click", () => {

            categoriaActiva = boton.dataset.categoria;

            contenedor.querySelectorAll(".categoria-btn")
                .forEach(b => b.classList.remove("activa"));

            boton.classList.add("activa");

            dibujarProductos();

        });

    });

}


// ======================================================
// NORMALIZAR RUTAS DE IMÁGENES
// ======================================================

function obtenerRutaImagen(imagen) {

    if (!imagen) return "";

    let ruta = String(imagen).trim().replace(/\\/g, "/");

    if (/^https?:\/\//i.test(ruta)) {
        return ruta;
    }

    if (ruta.startsWith("/")) {
        return ruta;
    }

    if (ruta.startsWith("static/")) {
        return "/" + ruta;
    }

    return "/static/" + ruta.replace(/^\/+/, "");
}


// ======================================================
// DIBUJAR PRODUCTOS
// ======================================================

function dibujarProductos() {

    const contenedor = elemento("productosGrid");
    const buscador = elemento("buscarProducto");

    if (!contenedor) return;

    const busqueda = (buscador?.value || "").trim().toLowerCase();

    const filtrados = productos.filter(producto => {

        const coincideCategoria =
            categoriaActiva === "todas" ||
            String(producto.id_categoria) === String(categoriaActiva);

        const nombre = String(producto.nombre || "").toLowerCase();
        const codigo = String(producto.codigo || "").toLowerCase();
        const categoria = String(producto.categoria || "").toLowerCase();

        const coincideBusqueda =
            nombre.includes(busqueda) ||
            codigo.includes(busqueda) ||
            categoria.includes(busqueda);

        return coincideCategoria && coincideBusqueda;

    });

    if (!filtrados.length) {

        contenedor.innerHTML = `
            <div class="estado-vacio">
                <i class="bi bi-search"></i>
                <p>No se encontraron productos.</p>
            </div>
        `;

        return;
    }

    contenedor.innerHTML = filtrados.map(producto => {

        const imagen = producto.imagen
            ? `
                <img
                    src="${obtenerRutaImagen(producto.imagen)}"
                    alt="${producto.nombre}"
                    onerror="
                        this.style.display='none';
                        this.nextElementSibling.style.display='block';
                    "
                >
                <i class="bi bi-cup-hot" style="display:none"></i>
            `
            : `<i class="bi bi-cup-hot"></i>`;

        return `
            <article class="producto-card">

                <div class="producto-imagen">
                    ${imagen}
                </div>

                <div class="producto-informacion">

                    <h4>${producto.nombre}</h4>

                    <p>${producto.categoria || "Otros"}</p>

                    <div class="producto-pie">

                        <span class="producto-precio">
                            ${formatoDinero(producto.precio_venta)}
                        </span>

                        <button
                            class="btn-agregar"
                            onclick="agregarProducto(${producto.id_producto})"
                            title="Agregar producto"
                        >
                            <i class="bi bi-plus-lg"></i>
                        </button>

                    </div>

                </div>

            </article>
        `;

    }).join("");

}


// ======================================================
// MESAS Y CUENTAS ABIERTAS
// ======================================================

async function cargarCuentas() {

    try {

        const datos = await peticion(URL_CUENTAS);

        cuentas = datos.cuentas || [];
        mesas = datos.mesas || [];

        dibujarMesas();
        dibujarCuentas();

    } catch (error) {

        console.error("ERROR AL CARGAR CUENTAS:", error);
        notificar(error.message);

    }
}


// ======================================================
// DIBUJAR MESAS
// ======================================================

function dibujarMesas() {

    const contenedor = elemento("listaMesas");
    const selector = elemento("selectMesa");

    if (!contenedor || !selector) return;

    contenedor.innerHTML = "";

    selector.innerHTML = `
        <option value="">Selecciona una mesa</option>
    `;

    mesas.forEach(mesa => {

        const ocupada = mesa.disponibilidad === "Ocupada";

        contenedor.innerHTML += `
            <button
                class="mesa-item ${ocupada ? "ocupada" : ""}"
                ${ocupada ? "disabled" : ""}
                onclick="seleccionarMesa(${mesa.id_mesa})"
            >

                <span>
                    <i class="bi bi-grid-3x3-gap"></i>
                    ${mesa.nombre_mesa}
                </span>

                <span class="disponibilidad">
                    ${ocupada ? "Ocupada" : "Disponible"}
                </span>

            </button>
        `;

        selector.innerHTML += `
            <option
                value="${mesa.id_mesa}"
                ${ocupada ? "disabled" : ""}
            >
                ${mesa.nombre_mesa} - ${ocupada ? "Ocupada" : "Disponible"}
            </option>
        `;

    });

}


// ======================================================
// DIBUJAR CUENTAS ABIERTAS
// ======================================================

function dibujarCuentas() {

    const contenedor = elemento("listaCuentas");
    const contador = elemento("contadorCuentas");

    if (!contenedor) return;

    if (contador) {
        contador.textContent = cuentas.length;
    }

    if (!cuentas.length) {

        contenedor.innerHTML = `
            <p class="mensaje-carga">
                No hay cuentas abiertas.
            </p>
        `;

        return;
    }

    contenedor.innerHTML = cuentas.map(cuenta => `

        <button
            class="cuenta-item ${
                cuentaActiva == cuenta.id_venta ? "activa" : ""
            }"
            onclick="seleccionarCuenta(${cuenta.id_venta})"
        >

            <strong>
                ${
                    cuenta.tipo_cuenta === "Mesa"
                        ? cuenta.nombre_mesa
                        : "Barra"
                }
                · ${cuenta.folio}
            </strong>

            <small>
                ${cuenta.nombre_cliente || "Sin nombre"}
                · ${formatoDinero(cuenta.total)}
            </small>

        </button>

    `).join("");

}


// ======================================================
// SELECCIONAR MESA
// ======================================================

function seleccionarMesa(idMesa) {

    elemento("selectMesa").value = idMesa;

    mostrarModal("modalMesa");

}


// ======================================================
// ABRIR CUENTA DE MESA
// ======================================================

async function abrirCuentaMesa() {

    const idMesa = elemento("selectMesa").value;

    const nombre = elemento("nombreClienteMesa").value.trim();

    if (!idMesa) {

        notificar("Selecciona una mesa.");

        return;
    }

    try {

        const datos = await peticion(URL_ABRIR_CUENTA, {

            method: "POST",

            body: JSON.stringify({
                tipo_cuenta: "Mesa",
                id_mesa: idMesa,
                nombre_cliente: nombre
            })

        });

        cerrarModal("modalMesa");

        await cargarCuentas();

        await seleccionarCuenta(datos.id_venta);

        notificar(datos.mensaje);

    } catch (error) {

        notificar(error.message);

    }

}


// ======================================================
// ABRIR CUENTA DE BARRA
// ======================================================

async function abrirCuentaBarra() {

    const nombre = elemento("nombreClienteBarra").value.trim();

    try {

        const datos = await peticion(URL_ABRIR_CUENTA, {

            method: "POST",

            body: JSON.stringify({
                tipo_cuenta: "Barra",
                nombre_cliente: nombre
            })

        });

        cerrarModal("modalBarra");

        await cargarCuentas();

        await seleccionarCuenta(datos.id_venta);

        notificar(datos.mensaje);

    } catch (error) {

        notificar(error.message);

    }

}


// ======================================================
// SELECCIONAR CUENTA
// ======================================================

async function seleccionarCuenta(idVenta) {

    try {

        const url = URL_DETALLE_CUENTA.replace(/0$/, idVenta);

        const datos = await peticion(url);

        cuentaActiva = idVenta;

        const cuenta = datos.cuenta;

        elemento("folioCuenta").textContent = cuenta.folio;

        elemento("tipoCuenta").textContent = cuenta.tipo_cuenta;

        elemento("clienteCuenta").textContent =
            cuenta.tipo_cuenta === "Mesa"
                ? (cuenta.nombre_cliente || "Mesa " + cuenta.id_mesa)
                : (cuenta.nombre_cliente || "Cliente de barra");

        elemento("estadoCuenta").textContent = "Abierta";

        elemento("estadoCuenta").classList.add("activa");

        dibujarDetalle(datos.detalles || []);

        dibujarCuentas();

    } catch (error) {

        notificar(error.message);

    }

}


// ======================================================
// DIBUJAR DETALLE DE LA CUENTA
// ======================================================

function dibujarDetalle(detalles) {

    const contenedor = elemento("ticketProductos");

    if (!contenedor) return;

    if (!detalles.length) {

        contenedor.innerHTML = `
            <div class="ticket-vacio">
                <i class="bi bi-receipt"></i>
                <p>Agrega productos a esta cuenta.</p>
            </div>
        `;

    } else {

        contenedor.innerHTML = detalles.map(detalle => `

            <div class="linea-ticket">

                <div class="linea-ticket-superior">

                    <strong>${detalle.nombre}</strong>

                    <strong>${formatoDinero(detalle.subtotal)}</strong>

                </div>

                <small>
                    ${formatoDinero(detalle.precio_unitario)} por unidad
                </small>

                <div class="cantidad-controles">

                    <button onclick="cambiarCantidad(
                        ${detalle.id_detalle_venta},
                        ${detalle.cantidad - 1}
                    )">−</button>

                    <span>${detalle.cantidad}</span>

                    <button onclick="cambiarCantidad(
                        ${detalle.id_detalle_venta},
                        ${detalle.cantidad + 1}
                    )">+</button>

                </div>

            </div>

        `).join("");

    }

    const subtotal = detalles.reduce(
        (suma, detalle) => suma + Number(detalle.subtotal),
        0
    );

    elemento("subtotalCuenta").textContent = formatoDinero(subtotal);

    elemento("totalCuenta").textContent = formatoDinero(subtotal);

    elemento("btnCobrar").disabled =
        !cuentaActiva || subtotal <= 0;

}


// ======================================================
// AGREGAR PRODUCTO
// ======================================================

async function agregarProducto(idProducto) {

    if (!cuentaActiva) {

        notificar("Primero abre o selecciona una cuenta.");

        return;
    }

    try {

        await peticion(URL_AGREGAR_PRODUCTO, {

            method: "POST",

            body: JSON.stringify({
                id_venta: cuentaActiva,
                id_producto: idProducto,
                cantidad: 1
            })

        });

        await seleccionarCuenta(cuentaActiva);

        await cargarCuentas();

        notificar("Producto agregado.");

    } catch (error) {

        notificar(error.message);

    }

}


// ======================================================
// CAMBIAR CANTIDAD
// ======================================================

async function cambiarCantidad(idDetalle, cantidad) {

    try {

        await peticion(URL_ACTUALIZAR_PRODUCTO, {

            method: "POST",

            body: JSON.stringify({
                id_venta: cuentaActiva,
                id_detalle: idDetalle,
                cantidad: cantidad
            })

        });

        await seleccionarCuenta(cuentaActiva);

        await cargarCuentas();

    } catch (error) {

        notificar(error.message);

    }

}


// ======================================================
// ABRIR MODAL DE COBRO
// ======================================================

function abrirModalCobro() {

    if (!cuentaActiva) return;

    const total = Number(
        elemento("totalCuenta").textContent.replace(/[^0-9.]/g, "")
    );

    elemento("totalModalCobro").textContent = formatoDinero(total);

    elemento("listaPagos").innerHTML = `
        <div class="fila-pago">

            <label>Método de pago</label>

            <select class="metodo-pago">
                <option value="Efectivo">Efectivo</option>
                <option value="Tarjeta">Tarjeta</option>
                <option value="Transferencia">Transferencia</option>
            </select>

            <label>Monto</label>

            <input
                type="number"
                class="monto-pago"
                min="0"
                step="0.01"
                value="${total.toFixed(2)}"
            >

            <label>Recibido (solo efectivo)</label>

            <input
                type="number"
                class="recibido-pago"
                min="0"
                step="0.01"
                value="${total.toFixed(2)}"
            >

        </div>
    `;

    calcularResumenPagos();

    mostrarModal("modalCobro");

}


// ======================================================
// AGREGAR OTRO MÉTODO DE PAGO
// ======================================================

function agregarFilaPago() {

    elemento("listaPagos").insertAdjacentHTML("beforeend", `

        <div class="fila-pago">

            <label>Método de pago</label>

            <select class="metodo-pago">
                <option value="Efectivo">Efectivo</option>
                <option value="Tarjeta">Tarjeta</option>
                <option value="Transferencia">Transferencia</option>
            </select>

            <label>Monto</label>

            <input
                type="number"
                class="monto-pago"
                min="0"
                step="0.01"
                placeholder="0.00"
            >

            <label>Recibido (solo efectivo)</label>

            <input
                type="number"
                class="recibido-pago"
                min="0"
                step="0.01"
                placeholder="0.00"
            >

        </div>

    `);

    calcularResumenPagos();

}


// ======================================================
// CALCULAR RESUMEN DE PAGOS
// ======================================================

function calcularResumenPagos() {

    const filas = document.querySelectorAll(".fila-pago");

    let pagado = 0;
    let recibido = 0;

    filas.forEach(fila => {

        const metodo = fila.querySelector(".metodo-pago").value;

        const monto = Number(
            fila.querySelector(".monto-pago").value || 0
        );

        const recibidoCampo = Number(
            fila.querySelector(".recibido-pago").value || 0
        );

        pagado += monto;

        recibido += metodo === "Efectivo"
            ? recibidoCampo
            : monto;

    });

    const total = Number(
        elemento("totalCuenta").textContent.replace(/[^0-9.]/g, "")
    );

    elemento("totalPagado").textContent = formatoDinero(pagado);

    elemento("restantePago").textContent =
        formatoDinero(Math.max(0, total - pagado));

    elemento("cambioPago").textContent =
        formatoDinero(Math.max(0, recibido - total));

}


// ======================================================
// CONFIRMAR COBRO
// ======================================================

async function confirmarPago() {

    const filas = document.querySelectorAll(".fila-pago");

    const pagos = Array.from(filas).map(fila => ({

        metodo: fila.querySelector(".metodo-pago").value,

        monto: Number(
            fila.querySelector(".monto-pago").value || 0
        ),

        recibido: Number(
            fila.querySelector(".recibido-pago").value || 0
        )

    }));

    try {

        const resultado = await peticion(URL_COBRAR, {

            method: "POST",

            body: JSON.stringify({
                id_venta: cuentaActiva,
                pagos: pagos
            })

        });

        cerrarModal("modalCobro");

        await mostrarTicket(resultado.id_venta);

        cuentaActiva = null;

        await cargarCuentas();

        elemento("estadoCuenta").textContent = "Sin cuenta";
        elemento("estadoCuenta").classList.remove("activa");

        elemento("folioCuenta").textContent = "---";
        elemento("tipoCuenta").textContent = "---";
        elemento("clienteCuenta").textContent = "---";

        elemento("ticketProductos").innerHTML = `
            <div class="ticket-vacio">
                <i class="bi bi-receipt"></i>
                <p>Selecciona una cuenta para comenzar.</p>
            </div>
        `;

        elemento("subtotalCuenta").textContent = formatoDinero(0);
        elemento("totalCuenta").textContent = formatoDinero(0);
        elemento("btnCobrar").disabled = true;

        notificar(resultado.mensaje);

    } catch (error) {

        notificar(error.message);

    }

}


// ======================================================
// GENERAR TICKET
// ======================================================

async function mostrarTicket(idVenta) {

    try {

        const url = URL_TICKET.replace(/0$/, idVenta);

        const datos = await peticion(url);

        const venta = datos.venta;

        elemento("contenidoTicket").innerHTML = `

            <div class="ticket-impresion">

                <div style="text-align:center; margin-bottom:18px">

                    <h2 style="font-family:Georgia;color:#641f2b">
                        LA CANTINA
                    </h2>

                    <p>Comprobante de venta</p>

                    <p>${venta.fecha_venta}</p>

                </div>

                <hr>

                <p><strong>Folio:</strong> ${venta.folio}</p>

                <p><strong>Cajero:</strong> ${venta.cajero}</p>

                <p>
                    <strong>Cuenta:</strong>
                    ${venta.nombre_mesa || venta.tipo_cuenta}
                </p>

                <p>
                    <strong>Cliente:</strong>
                    ${venta.nombre_cliente || "Público general"}
                </p>

                <hr>

                ${datos.detalles.map(item => `

                    <div style="display:flex;justify-content:space-between;margin:9px 0">

                        <span>
                            ${item.cantidad} x ${item.nombre}
                        </span>

                        <strong>
                            ${formatoDinero(item.subtotal)}
                        </strong>

                    </div>

                `).join("")}

                <hr>

                <h3 style="text-align:right;color:#641f2b">
                    TOTAL: ${formatoDinero(venta.total)}
                </h3>

                <p>
                    <strong>Método:</strong>
                    ${venta.metodo_pago}
                </p>

                <hr>

                <p style="text-align:center;margin-top:18px">
                    ¡Gracias por tu visita!
                </p>

            </div>

        `;

        mostrarModal("modalTicket");

    } catch (error) {

        notificar(error.message);

    }

}


// ======================================================
// IMPRIMIR TICKET
// ======================================================

function imprimirComprobante() {

    const contenido = elemento("contenidoTicket").innerHTML;

    const ventana = window.open(
        "",
        "_blank",
        "width=400,height=650"
    );

    if (!ventana) {

        notificar("Permite las ventanas emergentes para imprimir.");

        return;
    }

    ventana.document.write(`

        <html>

        <head>

            <title>Ticket La Cantina</title>

            <style>

                body {
                    font-family: Arial, sans-serif;
                    padding: 15px;
                    color: #382a27;
                }

                hr {
                    border: 0;
                    border-top: 1px dashed #aaa;
                }

                p {
                    font-size: 12px;
                }

            </style>

        </head>

        <body>
            ${contenido}
        </body>

        </html>

    `);

    ventana.document.close();
    ventana.focus();
    ventana.print();
    ventana.close();

}


// ======================================================
// INICIAR SISTEMA
// ======================================================

document.addEventListener(
    "DOMContentLoaded",
    inicializarVentas
);

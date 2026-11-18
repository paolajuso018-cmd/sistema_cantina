/* ==========================================
   REPORTES DE COMPRAS - LA CANTINA
========================================== */

document.addEventListener("DOMContentLoaded", () => {

    const $ = (id) => document.getElementById(id);

    let datosReporte = null;
    let graficaMes = null;
    let graficaProveedores = null;

    // ======================================
    // UTILIDADES
    // ======================================

    function escaparHTML(valor) {
        return String(valor ?? "").replace(/[&<>"']/g, caracter => ({
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#039;"
        })[caracter]);
    }

    function formatoMoneda(valor) {
        return Number(valor || 0).toLocaleString("es-MX", {
            style: "currency",
            currency: "MXN",
            minimumFractionDigits: 2
        });
    }

    function formatoNumero(valor) {
        return Number(valor || 0).toLocaleString("es-MX", {
            maximumFractionDigits: 3
        });
    }

    function formatoFecha(fecha) {
        if (!fecha) return "--";

        const partes = fecha.split("-");

        if (partes.length !== 3) return fecha;

        return `${partes[2]}/${partes[1]}/${partes[0]}`;
    }

    function fechaLocal(fecha) {
        const anio = fecha.getFullYear();
        const mes = String(fecha.getMonth() + 1).padStart(2, "0");
        const dia = String(fecha.getDate()).padStart(2, "0");

        return `${anio}-${mes}-${dia}`;
    }

    function mostrarToast(mensaje) {
        const toast = $("rcToast");

        toast.textContent = mensaje;
        toast.classList.add("visible");

        clearTimeout(mostrarToast.temporizador);

        mostrarToast.temporizador = setTimeout(() => {
            toast.classList.remove("visible");
        }, 3500);
    }

    function mostrarCarga(visible) {
        $("rcCargando").classList.toggle("visible", visible);
    }

    function claseEstado(estado) {
        const estados = {
            "Registrada": "registrada",
            "Pendiente": "pendiente",
            "Cancelada": "cancelada"
        };

        return estados[estado] || "";
    }

    // ======================================
    // FECHAS INICIALES
    // ======================================

    function establecerFechasIniciales() {
        const hoy = new Date();

        const primerDia = new Date(
            hoy.getFullYear(),
            hoy.getMonth(),
            1
        );

        $("filtroDesde").value = fechaLocal(primerDia);
        $("filtroHasta").value = fechaLocal(hoy);
    }

    // ======================================
    // CONSULTAR API
    // ======================================

    async function cargarReporte() {

        const desde = $("filtroDesde").value;
        const hasta = $("filtroHasta").value;
        const proveedor = $("filtroProveedor").value;
        const estado = $("filtroEstado").value;

        if (!desde || !hasta) {
            mostrarToast("Selecciona las fechas del reporte.");
            return;
        }

        if (desde > hasta) {
            mostrarToast("La fecha inicial no puede ser posterior a la final.");
            return;
        }

        const parametros = new URLSearchParams({
            desde,
            hasta,
            proveedor,
            estado
        });

        mostrarCarga(true);

        try {

            const respuesta = await fetch(
                `${API_REPORTES_COMPRAS}?${parametros.toString()}`,
                {
                    method: "GET",
                    headers: {
                        "Accept": "application/json"
                    },
                    credentials: "same-origin"
                }
            );

            const resultado = await respuesta.json();

            if (!respuesta.ok || !resultado.ok) {
                throw new Error(
                    resultado.mensaje || "No fue posible consultar los reportes."
                );
            }

            datosReporte = resultado;

            actualizarIndicadores(resultado.indicadores);
            actualizarProveedores(resultado.proveedores);
            actualizarGraficaMes(resultado.compras_por_mes);
            actualizarGraficaProveedores(resultado.gasto_proveedores);
            actualizarTablaInsumos(resultado.insumos_top);
            actualizarHistorial(resultado.historial);
            actualizarResumen(resultado.filtros);

        } catch (error) {

            console.error("ERROR REPORTES DE COMPRAS:", error);

            mostrarToast(error.message || "Error al cargar los reportes.");

            $("tablaHistorial").innerHTML = `
                <tr>
                    <td colspan="7">
                        No fue posible consultar las compras.
                    </td>
                </tr>
            `;

        } finally {
            mostrarCarga(false);
        }
    }

    // ======================================
    // INDICADORES
    // ======================================

    function actualizarIndicadores(indicadores) {

        $("totalCompras").textContent =
            formatoNumero(indicadores.total_compras);

        $("gastoTotal").textContent =
            formatoMoneda(indicadores.gasto_total);

        $("insumosComprados").textContent =
            formatoNumero(indicadores.insumos_comprados);

        $("comprasPendientes").textContent =
            formatoNumero(indicadores.compras_pendientes);
    }

    // ======================================
    // PROVEEDORES DEL FILTRO
    // ======================================

    function actualizarProveedores(proveedores) {

        const select = $("filtroProveedor");
        const valorActual = select.value;

        select.innerHTML = `
            <option value="">Todos los proveedores</option>
        `;

        proveedores.forEach(proveedor => {

            const opcion = document.createElement("option");

            opcion.value = proveedor.id;
            opcion.textContent = proveedor.nombre;

            select.appendChild(opcion);
        });

        if (
            valorActual &&
            [...select.options].some(opcion => opcion.value === valorActual)
        ) {
            select.value = valorActual;
        }
    }

    // ======================================
    // GRÁFICA DE COMPRAS POR MES
    // ======================================

    function actualizarGraficaMes(datos) {

        const contexto = $("graficaComprasMes");

        const etiquetas = datos.map(item => item.mes);
        const valores = datos.map(item => item.total);

        if (graficaMes) {
            graficaMes.destroy();
        }

        graficaMes = new Chart(contexto, {
            type: "bar",

            data: {
                labels: etiquetas,

                datasets: [{
                    label: "Gasto en compras",
                    data: valores,
                    backgroundColor: "#9b2636",
                    borderColor: "#790c1a",
                    borderWidth: 1,
                    borderRadius: 7,
                    maxBarThickness: 55
                }]
            },

            options: {
                responsive: true,
                maintainAspectRatio: false,

                plugins: {
                    legend: {
                        display: false
                    },

                    tooltip: {
                        callbacks: {
                            label: (contexto) =>
                                formatoMoneda(contexto.raw)
                        }
                    }
                },

                scales: {
                    y: {
                        beginAtZero: true,

                        ticks: {
                            callback: valor =>
                                "$" + Number(valor).toLocaleString("es-MX")
                        }
                    },

                    x: {
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
    }

    // ======================================
    // GRÁFICA POR PROVEEDOR
    // ======================================

    function actualizarGraficaProveedores(datos) {

        const contexto = $("graficaProveedores");

        if (graficaProveedores) {
            graficaProveedores.destroy();
        }

        graficaProveedores = new Chart(contexto, {

            type: "doughnut",

            data: {
                labels: datos.map(item => item.proveedor),

                datasets: [{
                    data: datos.map(item => item.total),

                    backgroundColor: [
                        "#790c1a",
                        "#bd5260",
                        "#d5a23a",
                        "#77a66a",
                        "#a77ab0",
                        "#e5a47d",
                        "#6b9eaa",
                        "#bd8a43",
                        "#916b7d",
                        "#a5a5a5"
                    ],

                    borderWidth: 2,
                    borderColor: "#fffaf1"
                }]
            },

            options: {
                responsive: true,
                maintainAspectRatio: false,

                plugins: {
                    legend: {
                        position: "bottom",

                        labels: {
                            boxWidth: 12,
                            padding: 12,
                            font: {
                                size: 11
                            }
                        }
                    },

                    tooltip: {
                        callbacks: {
                            label: contexto => {
                                return `${contexto.label}: ${formatoMoneda(contexto.raw)}`;
                            }
                        }
                    }
                }
            }
        });
    }

    // ======================================
    // TABLA DE INSUMOS
    // ======================================

    function actualizarTablaInsumos(datos) {

        const tabla = $("tablaInsumos");

        if (!datos || datos.length === 0) {

            tabla.innerHTML = `
                <tr>
                    <td colspan="4">
                        No hay insumos comprados en este periodo.
                    </td>
                </tr>
            `;

            return;
        }

        tabla.innerHTML = datos.map((item, indice) => `
            <tr>
                <td>
                    <span class="rc-posicion">${indice + 1}</span>
                </td>

                <td>${escaparHTML(item.nombre)}</td>

                <td>${formatoNumero(item.cantidad)}</td>

                <td>${formatoMoneda(item.importe)}</td>
            </tr>
        `).join("");
    }

    // ======================================
    // HISTORIAL DE COMPRAS
    // ======================================

    function actualizarHistorial(compras) {

        const tabla = $("tablaHistorial");

        $("totalRegistros").textContent =
            `${compras.length} registros`;

        if (!compras || compras.length === 0) {

            tabla.innerHTML = `
                <tr>
                    <td colspan="7">
                        No se encontraron compras con los filtros seleccionados.
                    </td>
                </tr>
            `;

            $("textoResultados").textContent = "Sin resultados";

            return;
        }

        tabla.innerHTML = compras.map(compra => {

            const clase = claseEstado(compra.estado);

            return `
                <tr>
                    <td>${escaparHTML(compra.folio)}</td>

                    <td>${escaparHTML(compra.proveedor)}</td>

                    <td>${formatoFecha(compra.fecha)}</td>

                    <td>${formatoNumero(compra.productos)}</td>

                    <td>${formatoNumero(compra.cantidad_insumos)}</td>

                    <td>${formatoMoneda(compra.total)}</td>

                    <td>
                        <span class="rc-estado ${clase}">
                            ${escaparHTML(compra.estado)}
                        </span>
                    </td>
                </tr>
            `;
        }).join("");

        $("textoResultados").textContent =
            `Mostrando ${compras.length} compras del periodo seleccionado`;
    }

    // ======================================
    // RESUMEN DE FILTROS
    // ======================================

    function actualizarResumen(filtros) {

        $("resumenPeriodo").textContent =
            `${formatoFecha(filtros.desde)} al ${formatoFecha(filtros.hasta)}`;

        const opcionProveedor = $("filtroProveedor").selectedOptions[0];

        $("resumenProveedor").textContent =
            opcionProveedor ? opcionProveedor.textContent : "Todos";

        $("resumenEstado").textContent =
            filtros.estado || "Todos";
    }

    // ======================================
    // EXPORTAR HISTORIAL A CSV
    // ======================================

    function exportarCSV() {

        if (!datosReporte || !datosReporte.historial.length) {
            mostrarToast("No hay compras para exportar.");
            return;
        }

        const encabezados = [
            "Folio",
            "Proveedor",
            "Fecha",
            "Productos",
            "Cantidad de insumos",
            "Total",
            "Estado"
        ];

        const filas = datosReporte.historial.map(compra => [
            compra.folio,
            compra.proveedor,
            compra.fecha,
            compra.productos,
            compra.cantidad_insumos,
            compra.total,
            compra.estado
        ]);

        const contenido = [
            encabezados,
            ...filas
        ].map(fila =>
            fila.map(valor =>
                `"${String(valor ?? "").replace(/"/g, '""')}"`
            ).join(",")
        ).join("\r\n");

        const blob = new Blob(
            ["\uFEFF" + contenido],
            {
                type: "text/csv;charset=utf-8;"
            }
        );

        const url = URL.createObjectURL(blob);
        const enlace = document.createElement("a");

        enlace.href = url;
        enlace.download = "reporte_compras.csv";

        document.body.appendChild(enlace);
        enlace.click();
        enlace.remove();

        URL.revokeObjectURL(url);

        mostrarToast("Reporte exportado correctamente.");
    }

    // ======================================
    // LIMPIAR FILTROS
    // ======================================

    function limpiarFiltros() {

        establecerFechasIniciales();

        $("filtroProveedor").value = "";
        $("filtroEstado").value = "";

        cargarReporte();
    }

    // ======================================
    // EVENTOS
    // ======================================

    $("btnAplicarFiltros").addEventListener(
        "click",
        cargarReporte
    );

    $("btnLimpiarFiltros").addEventListener(
        "click",
        limpiarFiltros
    );

    $("btnExportarCSV").addEventListener(
        "click",
        exportarCSV
    );

    $("btnImprimir").addEventListener(
        "click",
        () => window.print()
    );

    // ======================================
    // INICIALIZAR
    // ======================================

    establecerFechasIniciales();
    cargarReporte();

});
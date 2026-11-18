document.addEventListener("DOMContentLoaded", () => {

    const elemento = id => document.getElementById(id);

    const dinero = cantidad =>
        Number(cantidad || 0).toLocaleString("es-MX", {
            style: "currency",
            currency: "MXN"
        });

    const escapar = texto =>
        String(texto ?? "").replace(/[&<>"']/g, caracter => ({
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#39;"
        })[caracter]);

    const toast = mensaje => {
        const caja = elemento("ventasToast");
        if (!caja) return;

        caja.textContent = mensaje;
        caja.classList.add("visible");

        setTimeout(() => caja.classList.remove("visible"), 3000);
    };


    // ==========================================
    // CARGAR INFORMACIÓN DE MYSQL
    // ==========================================

    async function cargarVentas() {

        const periodo = elemento("periodoVentas")?.value || "Hoy";

        const equivalencias = {
            "Hoy": "hoy",
            "Esta semana": "semana",
            "Este mes": "mes"
        };

        try {

            const respuesta = await fetch(
                `${URL_API_VENTAS}?periodo=${encodeURIComponent(equivalencias[periodo] || "hoy")}`,
                {
                    method: "GET",
                    headers: {
                        "Accept": "application/json"
                    }
                }
            );

            const datos = await respuesta.json();

            if (!respuesta.ok || !datos.ok) {
                throw new Error(datos.mensaje || "No se pudieron cargar las ventas.");
            }

            dibujarIndicadores(datos.indicadores);
            dibujarGrafica(datos.ventas_hora);
            dibujarPagos(datos.pagos, datos.indicadores.ventas_dia);
            dibujarProductos(datos.top_productos);
            dibujarCuentas(datos.cuentas);
            dibujarUltimasVentas(datos.ultimas_ventas);

        } catch (error) {

            console.error("ERROR VENTAS ADMIN:", error);
            toast(error.message);

        }
    }


    // ==========================================
    // INDICADORES
    // ==========================================

    function dibujarIndicadores(datos) {

        elemento("ventasDia").textContent = dinero(datos.ventas_dia);

        elemento("numeroVentas").textContent = datos.numero_ventas;

        elemento("productosVendidos").textContent = datos.productos_vendidos;

        elemento("cuentasAbiertas").textContent = datos.cuentas_abiertas;

    }


    // ==========================================
    // GRÁFICA DE VENTAS POR HORA
    // ==========================================

    function dibujarGrafica(datos) {

        const horas = [10, 12, 14, 16, 18, 20, 22];

        const valores = horas.map(hora => Number(datos[hora] || 0));

        const maximo = Math.max(...valores, 100);

        const puntos = valores.map((valor, indice) => {

            const x = 8 + indice * 80;

            const y = 175 - (valor / maximo) * 145;

            return `${x},${y}`;

        });

        const linea = puntos.join(" ");

        const area = `M${puntos[0]} L${puntos.slice(1).join(" L")} L488,180 L8,180 Z`;

        elemento("lineaVentas")?.setAttribute("points", linea);

        elemento("areaVentasGrafica")?.setAttribute("d", area);

    }


    // ==========================================
    // MÉTODOS DE PAGO
    // ==========================================

    function dibujarPagos(pagos, totalVentas) {

        const colores = {
            "Efectivo": "#8f1024",
            "Tarjeta": "#e5a300",
            "Transferencia": "#26983b"
        };

        const normalizar = metodo =>
            String(metodo || "").toLowerCase();

        const orden = ["Efectivo", "Tarjeta", "Transferencia"];

        const lista = orden.map(metodo => {

            const encontrado = pagos.find(
                pago => normalizar(pago.metodo) === normalizar(metodo)
            );

            return {
                metodo,
                total: encontrado ? Number(encontrado.total) : 0
            };

        });

        const totalPagado = lista.reduce(
            (suma, pago) => suma + pago.total,
            0
        );

        let acumulado = 0;

        const segmentos = lista.map(pago => {

            const porcentaje = totalPagado > 0
                ? pago.total / totalPagado * 100
                : 0;

            const inicio = acumulado;

            acumulado += porcentaje;

            return `${colores[pago.metodo]} ${inicio}% ${acumulado}%`;

        });

        elemento("graficaDona").style.background =
            `conic-gradient(${segmentos.join(", ")})`;

        elemento("graficaDona").querySelector("b").textContent =
            dinero(totalVentas);

        elemento("leyendaPagos").innerHTML = lista.map(pago => {

            const porcentaje = totalPagado > 0
                ? pago.total / totalPagado * 100
                : 0;

            const clase = pago.metodo.toLowerCase();

            return `
                <li>
                    <i class="${clase}"></i>
                    ${pago.metodo}
                    <b>${porcentaje.toFixed(1)}%</b>
                </li>
            `;

        }).join("");

    }


    // ==========================================
    // TOP 5 PRODUCTOS
    // ==========================================

    function dibujarProductos(productos) {

        const lista = elemento("listaTopProductos");

        if (!productos.length) {
            lista.innerHTML = "<li>No hay productos vendidos en este periodo.</li>";
            return;
        }

        lista.innerHTML = productos.map((producto, indice) => {

            const clases = ["p1", "p2", "p3", "p4", "p5"];

            return `
                <li>
                    <span class="producto ${clases[indice]}">
                        <i class="bi bi-cup-straw"></i>
                    </span>

                    <b>${escapar(producto.nombre)}</b>

                    <strong>${producto.cantidad} ventas</strong>
                </li>
            `;

        }).join("");

    }


    // ==========================================
    // TIEMPO DE CUENTAS ABIERTAS
    // ==========================================

    function calcularTiempo(fecha) {

        if (!fecha) return "-";

        const inicio = new Date(fecha.replace(" ", "T"));

        const minutos = Math.max(
            0,
            Math.floor((Date.now() - inicio.getTime()) / 60000)
        );

        const horas = Math.floor(minutos / 60);
        const restantes = minutos % 60;

        return horas > 0
            ? `${horas} h ${restantes} min`
            : `${restantes} min`;

    }


    // ==========================================
    // CUENTAS ABIERTAS
    // ==========================================

    function dibujarCuentas(cuentas) {

        const tabla = elemento("tablaCuentasAbiertas");

        if (!cuentas.length) {
            tabla.innerHTML = `
                <tr>
                    <td colspan="6">No hay cuentas abiertas.</td>
                </tr>
            `;
            return;
        }

        tabla.innerHTML = cuentas.map(cuenta => {

            const nombre = cuenta.tipo_cuenta === "Mesa"
                ? cuenta.nombre_mesa || "Mesa"
                : "Barra";

            const fecha = cuenta.fecha_venta
                ? new Date(cuenta.fecha_venta.replace(" ", "T"))
                : null;

            const apertura = fecha
                ? fecha.toLocaleTimeString("es-MX", {
                    hour: "2-digit",
                    minute: "2-digit"
                }) + " h"
                : "-";

            return `
                <tr>
                    <td>${escapar(cuenta.tipo_cuenta)}</td>

                    <td>${escapar(cuenta.folio || nombre)}</td>

                    <td>${dinero(cuenta.total)}</td>

                    <td>${apertura}</td>

                    <td>${calcularTiempo(cuenta.fecha_venta)}</td>

                    <td>
                        <button class="btn-ver"
                            data-id="${cuenta.id_venta}">
                            <i class="bi bi-eye"></i> Ver
                        </button>
                    </td>
                </tr>
            `;

        }).join("");

    }


    // ==========================================
    // ÚLTIMAS VENTAS
    // ==========================================

    function dibujarUltimasVentas(ventas) {

        const tabla = elemento("tablaUltimasVentas");

        if (!ventas.length) {
            tabla.innerHTML = `
                <tr>
                    <td colspan="6">No hay ventas registradas en este periodo.</td>
                </tr>
            `;
            return;
        }

        tabla.innerHTML = ventas.map(venta => {

            const lugar = venta.tipo_cuenta === "Mesa"
                ? venta.nombre_mesa || "Mesa"
                : "Barra";

            return `
                <tr>
                    <td>${escapar(venta.folio || venta.id_venta)}</td>
                    <td>${escapar(lugar)}</td>
                    <td>${dinero(venta.total)}</td>
                    <td>${escapar(venta.metodo_pago)}</td>
                    <td>${escapar(venta.empleado)}</td>
                    <td>${escapar(venta.hora)} h</td>
                </tr>
            `;

        }).join("");

    }


    // ==========================================
    // FILTRO DE PERIODO
    // ==========================================

    elemento("periodoVentas")?.addEventListener("change", cargarVentas);


    // ==========================================
    // EXPORTAR INFORMACIÓN REAL A CSV
    // ==========================================

    elemento("exportarVentas")?.addEventListener("click", async () => {

        try {

            const respuesta = await fetch(URL_API_VENTAS);

            const datos = await respuesta.json();

            if (!respuesta.ok || !datos.ok) {
                throw new Error("No se pudo exportar la información.");
            }

            const filas = [
                ["Indicador", "Valor"],
                ["Ventas", datos.indicadores.ventas_dia],
                ["Número de ventas", datos.indicadores.numero_ventas],
                ["Productos vendidos", datos.indicadores.productos_vendidos],
                ["Cuentas abiertas", datos.indicadores.cuentas_abiertas],
                [],
                ["Últimas ventas"],
                ["Folio", "Lugar", "Total", "Método", "Empleado", "Hora"]
            ];

            datos.ultimas_ventas.forEach(venta => {

                filas.push([
                    venta.folio,
                    venta.nombre_mesa || venta.tipo_cuenta,
                    venta.total,
                    venta.metodo_pago,
                    venta.empleado,
                    venta.hora
                ]);

            });

            const csv = filas.map(fila =>
                fila.map(valor =>
                    `"${String(valor ?? "").replaceAll('"', '""')}"`
                ).join(",")
            ).join("\r\n");

            const archivo = new Blob(
                ["\uFEFF" + csv],
                { type: "text/csv;charset=utf-8" }
            );

            const url = URL.createObjectURL(archivo);

            const enlace = document.createElement("a");

            enlace.href = url;
            enlace.download = "reporte_ventas_cantina.csv";
            enlace.click();

            URL.revokeObjectURL(url);

            toast("Reporte exportado correctamente.");

        } catch (error) {

            toast(error.message);

        }

    });


    // CARGA INICIAL
    cargarVentas();

});

// ==========================================
// NAVEGACIÓN DE PESTAÑAS DE VENTAS
// ==========================================

document.addEventListener("DOMContentLoaded", function () {

    const botones = document.querySelectorAll(".tab-venta");

    const indicadores = document.getElementById("indicadoresVentas");
    const graficas = document.getElementById("graficasVentas");
    const tablas = document.getElementById("tablasVentas");

    if (!botones.length || !indicadores || !graficas || !tablas) {
        console.error("No se encontraron las secciones de ventas.");
        return;
    }

    const panelesGraficas = graficas.querySelectorAll(".panel-ventas");
    const panelesTablas = tablas.querySelectorAll(".panel-ventas");

    function mostrarPestana(pestana) {

        // Actualizar botón seleccionado
        botones.forEach(boton => {
            boton.classList.toggle(
                "activo",
                boton.dataset.tab === pestana
            );
        });

        // Primero ocultar las secciones
        indicadores.style.display = "none";
        graficas.style.display = "none";
        tablas.style.display = "none";

        // RESUMEN: mostrar absolutamente todo
        if (pestana === "resumen") {

            indicadores.style.display = "";
            graficas.style.display = "";
            tablas.style.display = "";

            panelesGraficas.forEach(panel => {
                panel.style.display = "";
            });

            panelesTablas.forEach(panel => {
                panel.style.display = "";
            });
        }

        // CUENTAS ABIERTAS
        else if (pestana === "cuentas") {

            tablas.style.display = "block";

            panelesTablas.forEach((panel, indice) => {
                panel.style.display = indice === 0 ? "" : "none";
            });
        }

        // HISTORIAL DE VENTAS
        else if (pestana === "historial") {

            tablas.style.display = "block";

            panelesTablas.forEach((panel, indice) => {
                panel.style.display = indice === 1 ? "" : "none";
            });
        }

        // PRODUCTOS MÁS VENDIDOS
        else if (pestana === "productos") {

            graficas.style.display = "grid";

            panelesGraficas.forEach((panel, indice) => {
                panel.style.display = indice === 2 ? "" : "none";
            });
        }

    }

    // Eventos de los botones
    botones.forEach(boton => {

        boton.addEventListener("click", function () {
            mostrarPestana(this.dataset.tab);
        });

    });

    // Iniciar en resumen
    mostrarPestana("resumen");

});
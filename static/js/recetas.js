document.addEventListener("DOMContentLoaded", () => {

    const modal = document.getElementById("modalNuevaReceta");
    const abrir = document.getElementById("abrirModalReceta");
    const cerrar = document.getElementById("cerrarModalReceta");
    const cancelar = document.getElementById("cancelarModalReceta");
    const lista = document.getElementById("listaIngredientes");
    const agregar = document.getElementById("agregarIngrediente");

    const utilidad = document.getElementById("utilidadReceta");
    const costoCalculado = document.getElementById("costoCalculado");
    const precioCalculado = document.getElementById("precioCalculado");
    const formulario = document.getElementById("formNuevaReceta");
    const tituloModal = document.getElementById("tituloModalReceta");
    const botonGuardar = document.getElementById("btnGuardarReceta");
    const idRecetaEditar = document.getElementById("idRecetaEditar");
    const accionNuevaReceta = formulario.action;

    const plantillaInsumos = document.getElementById("opcionesInsumos");
    const plantillaUnidades = document.getElementById("opcionesUnidades");

    const formatoMoneda = valor =>
        Number(valor).toLocaleString("es-MX", {
            style: "currency",
            currency: "MXN"
        });

    function abrirModal() {
        modal.classList.add("visible");
        document.body.style.overflow = "hidden";
    }

    function cerrarModal() {
        modal.classList.remove("visible");
        document.body.style.overflow = "";
    }

    function prepararNuevaReceta() {
        formulario.reset();
        formulario.action = accionNuevaReceta;
        idRecetaEditar.value = "";
        lista.innerHTML = "";
        tituloModal.innerHTML = '<i class="bi bi-cup-straw"></i> Nueva Receta';
        botonGuardar.innerHTML = '<i class="bi bi-floppy"></i> Guardar receta';
        vistaImagen.hidden = true;
        vistaImagen.removeAttribute("src");
        agregarFila();
        calcularTotales();
        abrirModal();
    }

    abrir?.addEventListener("click", prepararNuevaReceta);
    cerrar?.addEventListener("click", cerrarModal);
    cancelar?.addEventListener("click", cerrarModal);

    modal?.addEventListener("click", event => {
        if (event.target === modal) cerrarModal();
    });

    document.addEventListener("keydown", event => {
        if (event.key === "Escape" && modal.classList.contains("visible")) {
            cerrarModal();
        }
    });


    // ====================================
    // AGREGAR INGREDIENTES
    // ====================================

    function agregarFila() {

        const fila = document.createElement("div");
        fila.className = "fila-ingrediente";

        fila.innerHTML = `
            <div class="campo-receta">
                <label>Insumo</label>
                <select name="id_insumo[]" class="select-insumo" required>
                    <option value="">Selecciona un insumo</option>
                </select>
            </div>

            <div class="campo-receta">
                <label>Cantidad</label>
                <input type="number" name="cantidad[]" class="cantidad-insumo"
                       min="0.001" step="0.001" placeholder="0.000" required>
            </div>

            <div class="campo-receta">
                <label>Unidad de receta</label>
                <select name="id_unidad_receta[]" class="select-unidad" required>
                    <option value="">Selecciona unidad</option>
                </select>
            </div>

            <div class="resultado-ingrediente">
                <span>Subtotal</span>
                <strong>$0.00</strong>
            </div>

            <button type="button" class="quitar-ingrediente"
                    title="Eliminar ingrediente">
                <i class="bi bi-trash"></i>
            </button>
        `;

        const selectInsumo = fila.querySelector(".select-insumo");
        const selectUnidad = fila.querySelector(".select-unidad");
        const cantidad = fila.querySelector(".cantidad-insumo");

        selectInsumo.append(
            ...plantillaInsumos.content.cloneNode(true).children
        );

        selectUnidad.append(
            ...plantillaUnidades.content.cloneNode(true).children
        );

        selectInsumo.addEventListener("change", () => {
            const opcion = selectInsumo.selectedOptions[0];

            if (!selectInsumo.value) {
                actualizarSubtotal(fila);
                return;
            }

            selectUnidad.value = opcion.dataset.unidad;

            filtrarUnidadesCompatibles(fila);
            actualizarSubtotal(fila);
        });

        cantidad.addEventListener("input", () => actualizarSubtotal(fila));
        selectUnidad.addEventListener("change", () => actualizarSubtotal(fila));

        fila.querySelector(".quitar-ingrediente").addEventListener("click", () => {
            fila.remove();
            calcularTotales();
        });

        lista.appendChild(fila);
    }


    // ====================================
    // CARGAR RECETA EXISTENTE PARA EDITAR
    // ====================================

    document.querySelectorAll(".btn-editar-receta").forEach(boton => {
        boton.addEventListener("click", async () => {
            const id = boton.dataset.id;

            try {
                const respuesta = await fetch(`/recetas/${id}/datos`);
                const datos = await respuesta.json();

                if (!respuesta.ok) {
                    throw new Error(datos.error || "No se pudo cargar la receta.");
                }

                const receta = datos.receta;

                formulario.reset();
                lista.innerHTML = "";
                formulario.action = `/recetas/${id}/editar`;
                idRecetaEditar.value = id;

                tituloModal.innerHTML = '<i class="bi bi-pencil-square"></i> Editar Receta';
                botonGuardar.innerHTML = '<i class="bi bi-floppy"></i> Guardar cambios';

                formulario.querySelector('[name="codigo"]').value = receta.codigo || "";
                formulario.querySelector('[name="nombre"]').value = receta.nombre || "";
                formulario.querySelector('[name="id_categoria"]').value = receta.id_categoria;
                formulario.querySelector('[name="porciones"]').value = receta.porciones;
                formulario.querySelector('[name="descripcion"]').value = receta.descripcion || "";
                formulario.querySelector('[name="instrucciones"]').value = receta.instrucciones || "";

                utilidad.value = receta.porcentaje_utilidad;

                if (receta.imagen) {
                    vistaImagen.src = `/static/${receta.imagen}`;
                    vistaImagen.hidden = false;
                } else {
                    vistaImagen.hidden = true;
                    vistaImagen.removeAttribute("src");
                }

                datos.ingredientes.forEach(ingrediente => {
                    agregarFila();

                    const fila = lista.lastElementChild;
                    const selectInsumo = fila.querySelector(".select-insumo");
                    const selectUnidad = fila.querySelector(".select-unidad");
                    const cantidad = fila.querySelector(".cantidad-insumo");

                    selectInsumo.value = String(ingrediente.id_insumo);
                    selectInsumo.dispatchEvent(new Event("change"));

                    cantidad.value = ingrediente.cantidad;
                    selectUnidad.value = String(ingrediente.id_unidad_receta);

                    filtrarUnidadesCompatibles(fila);
                    actualizarSubtotal(fila);
                });

                calcularTotales();
                abrirModal();

            } catch (error) {
                console.error("Error al cargar receta:", error);
                alert(error.message || "No se pudo abrir la receta para editar.");
            }
        });
    });


    // ====================================
    // FILTRAR UNIDADES COMPATIBLES
    // ====================================

    function filtrarUnidadesCompatibles(fila) {

        const insumo = fila.querySelector(".select-insumo");
        const unidad = fila.querySelector(".select-unidad");

        const opcionInsumo = insumo.selectedOptions[0];

        if (!opcionInsumo || !insumo.value) return;

        const tipo = opcionInsumo.dataset.tipo;

        Array.from(unidad.options).forEach(opcion => {

            if (!opcion.value) return;

            opcion.hidden = opcion.dataset.tipo !== tipo;
            opcion.disabled = opcion.dataset.tipo !== tipo;

        });

    }


    // ====================================
    // CALCULAR COSTO DE CADA INGREDIENTE
    // ====================================

    function actualizarSubtotal(fila) {

        const insumo = fila.querySelector(".select-insumo");
        const unidad = fila.querySelector(".select-unidad");
        const cantidad = fila.querySelector(".cantidad-insumo");

        const resultado = fila.querySelector(".resultado-ingrediente strong");

        const opcionInsumo = insumo.selectedOptions[0];
        const opcionUnidad = unidad.selectedOptions[0];

        if (
            !insumo.value ||
            !unidad.value ||
            !cantidad.value ||
            !opcionInsumo ||
            !opcionUnidad
        ) {
            resultado.textContent = "$0.00";
            calcularTotales();
            return;
        }

        const costo = Number(opcionInsumo.dataset.costo);
        const factorAlmacen = Number(opcionInsumo.dataset.factor);
        const factorReceta = Number(opcionUnidad.dataset.factor);
        const cantidadReceta = Number(cantidad.value);

        if (
            opcionInsumo.dataset.tipo !== opcionUnidad.dataset.tipo ||
            factorAlmacen <= 0 ||
            factorReceta <= 0
        ) {
            resultado.textContent = "Unidad incompatible";
            calcularTotales();
            return;
        }

        const cantidadConvertida =
            cantidadReceta * factorReceta / factorAlmacen;

        const subtotal = cantidadConvertida * costo;

        resultado.textContent = formatoMoneda(subtotal);

        calcularTotales();
    }


    // ====================================
    // COSTO TOTAL Y PRECIO DE VENTA
    // ====================================

    function calcularTotales() {

        let costoTotal = 0;

        document.querySelectorAll(".fila-ingrediente").forEach(fila => {

            const insumo = fila.querySelector(".select-insumo");
            const unidad = fila.querySelector(".select-unidad");
            const cantidad = fila.querySelector(".cantidad-insumo");

            if (
                !insumo.value ||
                !unidad.value ||
                !cantidad.value
            ) return;

            const producto = insumo.selectedOptions[0];
            const medida = unidad.selectedOptions[0];

            const factorAlmacen = Number(producto.dataset.factor);
            const factorReceta = Number(medida.dataset.factor);

            if (
                producto.dataset.tipo !== medida.dataset.tipo ||
                factorAlmacen <= 0 ||
                factorReceta <= 0
            ) return;

            const cantidadConvertida =
                Number(cantidad.value) * factorReceta / factorAlmacen;

            costoTotal += cantidadConvertida * Number(producto.dataset.costo);
        });

        const margen = Number(utilidad.value);

        let precio = 0;

        if (margen >= 0 && margen < 100) {
            precio = costoTotal / (1 - margen / 100);
        }

        costoCalculado.textContent = formatoMoneda(costoTotal);
        precioCalculado.textContent = formatoMoneda(precio);
    }


    agregar?.addEventListener("click", agregarFila);
    utilidad?.addEventListener("input", calcularTotales);


    // ====================================
    // VISTA PREVIA DE FOTOGRAFÍA
    // ====================================

    const inputImagen = document.getElementById("imagenReceta");
    const vistaImagen = document.getElementById("vistaImagenReceta");

    inputImagen?.addEventListener("change", () => {

        const archivo = inputImagen.files[0];

        if (!archivo) {
            vistaImagen.hidden = true;
            vistaImagen.removeAttribute("src");
            return;
        }

        vistaImagen.src = URL.createObjectURL(archivo);
        vistaImagen.hidden = false;

    });


    // ====================================
    // BUSCADOR Y FILTROS DEL LISTADO
    // ====================================

    const buscar = document.getElementById("buscarReceta");
    const filtroCategoria = document.getElementById("filtroCategoria");
    const filtroEstado = document.getElementById("filtroEstado");
    const limpiar = document.getElementById("limpiarFiltros");

    function filtrarRecetas() {

        const texto = buscar.value.toLowerCase().trim();
        const categoria = filtroCategoria.value;
        const estado = filtroEstado.value;

        document.querySelectorAll(".fila-receta").forEach(fila => {

            const coincideNombre =
                fila.dataset.nombre.includes(texto);

            const coincideCategoria =
                !categoria || fila.dataset.categoria === categoria;

            const coincideEstado =
                !estado || fila.dataset.estado === estado;

            fila.style.display =
                coincideNombre && coincideCategoria && coincideEstado
                    ? ""
                    : "none";

        });

    }

    buscar?.addEventListener("input", filtrarRecetas);
    filtroCategoria?.addEventListener("change", filtrarRecetas);
    filtroEstado?.addEventListener("change", filtrarRecetas);

    limpiar?.addEventListener("click", () => {
        buscar.value = "";
        filtroCategoria.value = "";
        filtroEstado.value = "";
        filtrarRecetas();
    });


    // ====================================
    // VALIDAR FORMULARIO
    // ====================================

    document.getElementById("formNuevaReceta")?.addEventListener("submit", event => {

        const filas = document.querySelectorAll(".fila-ingrediente");

        if (filas.length === 0) {
            event.preventDefault();
            alert("Agrega al menos un ingrediente.");
            return;
        }

        for (const fila of filas) {

            const insumo = fila.querySelector(".select-insumo");
            const unidad = fila.querySelector(".select-unidad");
            const cantidad = fila.querySelector(".cantidad-insumo");

            if (!insumo.value || !unidad.value || Number(cantidad.value) <= 0) {
                event.preventDefault();
                alert("Completa correctamente todos los ingredientes.");
                return;
            }
        }

    });


    agregarFila();

});

document.addEventListener("DOMContentLoaded", () => {

    // ==========================================
    // ELEMENTOS GENERALES
    // ==========================================

    const modalNuevo = document.getElementById("modalNuevoInsumo");
    const formNuevo = document.getElementById("formNuevoInsumo");

    let idInsumoSeleccionado = null;
    let temporizadorToast = null;

    const notificacion = document.getElementById("notificacionAlmacen");

    function mostrarMensaje(mensaje, tipo = "success") {

        if (!notificacion) {
            alert(mensaje);
            return;
        }

        clearTimeout(temporizadorToast);

        notificacion.textContent = mensaje;
        notificacion.className = "notificacion-almacen visible " + tipo;

        temporizadorToast = setTimeout(() => {
            notificacion.classList.remove("visible");
        }, 4000);
    }


    // ==========================================
    // ABRIR Y CERRAR MODALES
    // ==========================================

    function abrirModal(id) {
        const modal = document.getElementById(id);

        if (!modal) return;

        modal.classList.add("visible");
        document.body.style.overflow = "hidden";
    }

    function cerrarModal(id) {
        const modal = document.getElementById(id);

        if (!modal) return;

        modal.classList.remove("visible");

        if (!document.querySelector(".modal-overlay.visible")) {
            document.body.style.overflow = "";
        }
    }

    // Modal nuevo insumo
    document.getElementById("abrirModalInsumo")
        ?.addEventListener("click", () => abrirModal("modalNuevoInsumo"));

    document.getElementById("cerrarModalInsumo")
        ?.addEventListener("click", () => cerrarModal("modalNuevoInsumo"));

    document.getElementById("cancelarModalInsumo")
        ?.addEventListener("click", () => cerrarModal("modalNuevoInsumo"));

    // Cierres de los demás modales
    document.querySelectorAll("[data-cerrar]").forEach(boton => {
        boton.addEventListener("click", () => {
            cerrarModal(boton.dataset.cerrar);
        });
    });

    // Cerrar al hacer clic fuera
    document.querySelectorAll(".modal-overlay").forEach(modal => {
        modal.addEventListener("click", event => {
            if (event.target === modal) {
                cerrarModal(modal.id);
            }
        });
    });

    // Cerrar con Escape
    document.addEventListener("keydown", event => {
        if (event.key === "Escape") {
            document.querySelectorAll(".modal-overlay.visible").forEach(modal => {
                cerrarModal(modal.id);
            });
        }
    });


    // ==========================================
    // FUNCIÓN PARA CONSULTAR DATOS
    // ==========================================

    async function consultarInsumo(id) {

        const respuesta = await fetch(`/almacen/${id}/datos`);

        const datos = await respuesta.json();

        if (!respuesta.ok) {
            throw new Error(datos.error || "No se pudieron consultar los datos.");
        }

        return datos;
    }


    // ==========================================
    // BOTÓN EDITAR
    // ==========================================

    document.querySelectorAll(".btn-editar-insumo").forEach(boton => {

        boton.addEventListener("click", async () => {

            const id = boton.dataset.id;

            try {

                const insumo = await consultarInsumo(id);

                idInsumoSeleccionado = id;

                document.getElementById("editarCodigo").value = insumo.codigo;
                document.getElementById("editarNombre").value = insumo.nombre;
                document.getElementById("editarCategoria").value = insumo.id_categoria;
                document.getElementById("editarUnidad").value = insumo.id_unidad;
                document.getElementById("editarDescripcion").value = insumo.descripcion || "";
                document.getElementById("editarCosto").value = insumo.costo_unitario;
                document.getElementById("editarStockActual").value = insumo.stock_actual;
                document.getElementById("editarStockMinimo").value = insumo.stock_minimo;

                document.getElementById("editarActivo").checked =
                    insumo.estado === "Activo";

                document.getElementById("editarInactivo").checked =
                    insumo.estado === "Inactivo";

                abrirModal("modalEditarInsumo");

            } catch (error) {
                mostrarMensaje(error.message, "error");
            }

        });

    });


    // Guardar edición
    document.getElementById("formEditarInsumo")
        ?.addEventListener("submit", async event => {

            event.preventDefault();

            if (!idInsumoSeleccionado) return;

            const formulario = event.currentTarget;

            try {

                const respuesta = await fetch(
                    `/almacen/${idInsumoSeleccionado}/editar`,
                    {
                        method: "POST",
                        body: new FormData(formulario)
                    }
                );

                const datos = await respuesta.json();

                if (!respuesta.ok) {
                    throw new Error(datos.error || "No se pudo editar el insumo.");
                }

                cerrarModal("modalEditarInsumo");

                mostrarMensaje(datos.mensaje);

                setTimeout(() => location.reload(), 900);

            } catch (error) {
                mostrarMensaje(error.message, "error");
            }

        });


    // ==========================================
    // BOTÓN MOVIMIENTO
    // ==========================================

    document.querySelectorAll(".btn-movimiento-insumo").forEach(boton => {

        boton.addEventListener("click", async () => {

            const id = boton.dataset.id;

            try {

                const insumo = await consultarInsumo(id);

                idInsumoSeleccionado = id;

                document.getElementById("nombreMovimiento").textContent =
                    `Registrar movimiento: ${insumo.nombre}`;

                document.getElementById("movimientoStockActual").value =
                    insumo.stock_actual;

                document.getElementById("formMovimientoInsumo").reset();

                document.getElementById("movimientoStockActual").value =
                    insumo.stock_actual;

                document.getElementById("etiquetaCantidad").textContent =
                    "Cantidad *";

                abrirModal("modalMovimientoInsumo");

            } catch (error) {
                mostrarMensaje(error.message, "error");
            }

        });

    });


    // Cambiar etiqueta cuando sea ajuste
    document.getElementById("tipoMovimiento")
        ?.addEventListener("change", event => {

            const etiqueta = document.getElementById("etiquetaCantidad");

            if (event.target.value === "Ajuste") {
                etiqueta.textContent = "Nuevo stock físico *";
            } else {
                etiqueta.textContent = "Cantidad *";
            }

        });


    // Guardar movimiento
    document.getElementById("formMovimientoInsumo")
        ?.addEventListener("submit", async event => {

            event.preventDefault();

            if (!idInsumoSeleccionado) return;

            const formulario = event.currentTarget;

            try {

                const respuesta = await fetch(
                    `/almacen/${idInsumoSeleccionado}/movimiento`,
                    {
                        method: "POST",
                        body: new FormData(formulario)
                    }
                );

                const datos = await respuesta.json();

                if (!respuesta.ok) {
                    throw new Error(datos.error || "No se pudo registrar el movimiento.");
                }

                cerrarModal("modalMovimientoInsumo");

                mostrarMensaje(
                    `${datos.mensaje} Nuevo stock: ${Number(datos.stock_actual).toFixed(3)}`
                );

                setTimeout(() => location.reload(), 1200);

            } catch (error) {
                mostrarMensaje(error.message, "error");
            }

        });


    // ==========================================
    // BOTÓN DESACTIVAR
    // ==========================================

    document.querySelectorAll(".btn-eliminar-insumo").forEach(boton => {

        boton.addEventListener("click", async () => {

            const id = boton.dataset.id;

            try {

                const insumo = await consultarInsumo(id);

                idInsumoSeleccionado = id;

                document.getElementById("nombreDesactivar").textContent =
                    insumo.nombre;

                abrirModal("modalDesactivarInsumo");

            } catch (error) {
                mostrarMensaje(error.message, "error");
            }

        });

    });


    // Confirmar desactivación
    document.getElementById("confirmarDesactivar")
        ?.addEventListener("click", async () => {

            if (!idInsumoSeleccionado) return;

            try {

                const respuesta = await fetch(
                    `/almacen/${idInsumoSeleccionado}/desactivar`,
                    {
                        method: "POST"
                    }
                );

                const datos = await respuesta.json();

                if (!respuesta.ok) {
                    throw new Error(datos.error || "No se pudo desactivar el insumo.");
                }

                cerrarModal("modalDesactivarInsumo");

                mostrarMensaje(datos.mensaje);

                setTimeout(() => location.reload(), 900);

            } catch (error) {
                mostrarMensaje(error.message, "error");
            }

        });

});

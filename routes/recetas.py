import os
from decimal import Decimal, InvalidOperation

from flask import (
    Blueprint, render_template, request, redirect,
    url_for, session, flash, abort, current_app, jsonify
)
from werkzeug.utils import secure_filename
from models.conexion import obtener_conexion


recetas_bp = Blueprint("recetas", __name__, url_prefix="/recetas")

EXTENSIONES_PERMITIDAS = {"png", "jpg", "jpeg", "webp"}


def extension_permitida(nombre):
    return (
        "." in nombre
        and nombre.rsplit(".", 1)[1].lower() in EXTENSIONES_PERMITIDAS
    )


def obtener_menu():
    from routes.administrativo import MENUS_ROLES
    return MENUS_ROLES.get(session.get("rol"), [])


def calcular_precio(costo, utilidad):
    if utilidad < 0 or utilidad >= 100:
        raise ValueError("La utilidad debe ser menor al 100%.")

    return (
        costo / (Decimal("1") - utilidad / Decimal("100"))
    ).quantize(Decimal("0.01"))


def obtener_ingredientes(cursor, ids_insumos, cantidades, unidades_receta):
    if not ids_insumos or not (
        len(ids_insumos) == len(cantidades) == len(unidades_receta)
    ):
        raise ValueError("Agrega al menos un ingrediente correctamente.")

    ingredientes = []
    costo_total = Decimal("0.00")

    for id_insumo, cantidad_texto, id_unidad_texto in zip(
        ids_insumos, cantidades, unidades_receta
    ):
        cantidad_receta = Decimal(cantidad_texto)

        if cantidad_receta <= 0:
            raise ValueError("Las cantidades deben ser mayores que cero.")

        cursor.execute("""
            SELECT
                i.id_insumo,
                i.nombre,
                i.costo_unitario,
                ua.tipo_medida AS tipo_almacen,
                ua.factor_conversion AS factor_almacen,
                ur.tipo_medida AS tipo_receta,
                ur.factor_conversion AS factor_receta
            FROM insumos i
            INNER JOIN unidades_medida ua
                ON ua.id_unidad = i.id_unidad
            INNER JOIN unidades_medida ur
                ON ur.id_unidad = %s
            WHERE i.id_insumo = %s
              AND i.estado = 'Activo'
        """, (id_unidad_texto, id_insumo))

        insumo = cursor.fetchone()

        if not insumo:
            raise ValueError(
                "Uno de los insumos no existe o está inactivo."
            )

        if insumo["tipo_almacen"] != insumo["tipo_receta"]:
            raise ValueError(
                f"Las unidades de {insumo['nombre']} no son compatibles."
            )

        factor_almacen = Decimal(str(insumo["factor_almacen"]))
        factor_receta = Decimal(str(insumo["factor_receta"]))

        if factor_almacen <= 0 or factor_receta <= 0:
            raise ValueError("Factor de conversión inválido.")

        cantidad_convertida = (
            cantidad_receta * factor_receta / factor_almacen
        ).quantize(Decimal("0.001"))

        costo_unitario = Decimal(str(insumo["costo_unitario"]))

        subtotal = (
            cantidad_convertida * costo_unitario
        ).quantize(Decimal("0.01"))

        costo_total += subtotal

        ingredientes.append({
            "id_insumo": insumo["id_insumo"],
            "cantidad": cantidad_convertida,
            "cantidad_receta": cantidad_receta,
            "id_unidad_receta": int(id_unidad_texto),
            "costo_unitario": costo_unitario,
            "subtotal": subtotal
        })

    return ingredientes, costo_total.quantize(Decimal("0.01"))


def guardar_detalles(cursor, id_receta, ingredientes):
    for ingrediente in ingredientes:
        cursor.execute("""
            INSERT INTO detalle_recetas (
                id_receta,
                id_insumo,
                cantidad,
                cantidad_receta,
                id_unidad_receta,
                costo_unitario,
                subtotal
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (
            id_receta,
            ingrediente["id_insumo"],
            ingrediente["cantidad"],
            ingrediente["cantidad_receta"],
            ingrediente["id_unidad_receta"],
            ingrediente["costo_unitario"],
            ingrediente["subtotal"]
        ))


@recetas_bp.route("/", methods=["GET", "POST"])
def gestionar_recetas():

    if "id_usuario" not in session:
        return redirect(url_for("login.login"))

    if session.get("rol") not in (
        "Administrador", "Gerente", "Bartender"
    ):
        abort(403)

    conexion = obtener_conexion()

    if conexion is None:
        flash("No se pudo conectar con la base de datos.", "error")
        return redirect(url_for("administrativo.dashboard"))

    cursor = None

    try:
        cursor = conexion.cursor(dictionary=True)

        if request.method == "POST":

            codigo = request.form.get("codigo", "").strip()
            nombre = request.form.get("nombre", "").strip()
            descripcion = request.form.get("descripcion", "").strip()
            id_categoria = request.form.get("id_categoria", "").strip()
            porciones = Decimal(request.form.get("porciones", "1"))
            instrucciones = request.form.get("instrucciones", "").strip()
            utilidad = Decimal(
                request.form.get("porcentaje_utilidad", "60")
            )
            estado = request.form.get("estado", "Activo")

            if not all([codigo, nombre, id_categoria]):
                raise ValueError(
                    "Completa el código, nombre y categoría."
                )

            if porciones <= 0:
                raise ValueError(
                    "Las porciones deben ser mayores que cero."
                )

            if utilidad < 0 or utilidad >= 100:
                raise ValueError(
                    "La utilidad debe ser menor al 100%."
                )

            cursor.execute("""
                SELECT id_categoria
                FROM categorias_productos
                WHERE id_categoria = %s
            """, (id_categoria,))

            if not cursor.fetchone():
                raise ValueError("La categoría seleccionada no existe.")

            ids_insumos = request.form.getlist("id_insumo[]")
            cantidades = request.form.getlist("cantidad[]")
            unidades_receta = request.form.getlist(
                "id_unidad_receta[]"
            )

            ingredientes, costo_total = obtener_ingredientes(
                cursor,
                ids_insumos,
                cantidades,
                unidades_receta
            )

            precio_venta = calcular_precio(costo_total, utilidad)

            ruta_imagen = None
            imagen = request.files.get("imagen")

            if imagen and imagen.filename:
                if not extension_permitida(imagen.filename):
                    raise ValueError(
                        "La imagen debe ser PNG, JPG, JPEG o WEBP."
                    )

                nombre_archivo = (
                    f"{codigo}_{secure_filename(imagen.filename)}"
                )

                carpeta = os.path.join(
                    current_app.static_folder,
                    "img",
                    "productos"
                )

                os.makedirs(carpeta, exist_ok=True)
                imagen.save(os.path.join(carpeta, nombre_archivo))

                ruta_imagen = f"img/productos/{nombre_archivo}"

            cursor.execute("""
                INSERT INTO productos (
                    codigo,
                    id_categoria,
                    nombre,
                    descripcion,
                    imagen,
                    costo_preparacion,
                    porcentaje_utilidad,
                    precio_venta,
                    estado
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                codigo,
                id_categoria,
                nombre,
                descripcion or None,
                ruta_imagen,
                costo_total,
                utilidad,
                precio_venta,
                estado
            ))

            id_producto = cursor.lastrowid

            cursor.execute("""
                INSERT INTO recetas (
                    id_producto,
                    nombre,
                    porciones,
                    instrucciones,
                    costo_total
                )
                VALUES (%s,%s,%s,%s,%s)
            """, (
                id_producto,
                nombre,
                porciones,
                instrucciones or None,
                costo_total
            ))

            id_receta = cursor.lastrowid

            guardar_detalles(cursor, id_receta, ingredientes)

            conexion.commit()
            flash("La receta se registró correctamente.", "success")

            return redirect(url_for("recetas.gestionar_recetas"))

        # Categorías
        cursor.execute("""
            SELECT id_categoria, nombre
            FROM categorias_productos
            ORDER BY nombre
        """)
        categorias = cursor.fetchall()

        # Insumos activos
        cursor.execute("""
            SELECT
                i.id_insumo,
                i.codigo,
                i.nombre,
                i.costo_unitario,
                i.stock_actual,
                i.id_unidad,
                u.nombre AS unidad,
                u.abreviatura,
                u.tipo_medida,
                u.factor_conversion
            FROM insumos i
            INNER JOIN unidades_medida u
                ON u.id_unidad = i.id_unidad
            WHERE i.estado = 'Activo'
            ORDER BY i.nombre
        """)
        insumos = cursor.fetchall()

        # Unidades
        cursor.execute("""
            SELECT
                id_unidad,
                nombre,
                abreviatura,
                tipo_medida,
                factor_conversion
            FROM unidades_medida
            ORDER BY nombre
        """)
        unidades = cursor.fetchall()

        # Recetas y productos
        cursor.execute("""
            SELECT
                p.id_producto,
                p.codigo,
                p.nombre,
                p.descripcion,
                p.imagen,
                p.costo_preparacion,
                p.porcentaje_utilidad,
                p.precio_venta,
                p.estado,
                p.id_categoria,
                cp.nombre AS categoria,
                r.id_receta,
                r.porciones,
                r.instrucciones,
                r.costo_total
            FROM productos p
            INNER JOIN recetas r
                ON r.id_producto = p.id_producto
            INNER JOIN categorias_productos cp
                ON cp.id_categoria = p.id_categoria
            ORDER BY p.id_producto DESC
        """)
        recetas = cursor.fetchall()

        # Estadísticas
        cursor.execute("""
            SELECT
                COUNT(*) AS total,
                SUM(
                    CASE WHEN p.estado = 'Activo'
                    THEN 1 ELSE 0 END
                ) AS activas,
                SUM(
                    CASE WHEN p.estado = 'Inactivo'
                    THEN 1 ELSE 0 END
                ) AS inactivas,
                AVG(p.costo_preparacion) AS costo_promedio
            FROM productos p
            INNER JOIN recetas r
                ON r.id_producto = p.id_producto
        """)
        estadisticas = cursor.fetchone()

        for clave in ("total", "activas", "inactivas"):
            estadisticas[clave] = estadisticas[clave] or 0

        estadisticas["costo_promedio"] = (
            estadisticas["costo_promedio"] or 0
        )

        # Receta seleccionada
        id_seleccionada = request.args.get("id", type=int)

        receta_seleccionada = None

        if id_seleccionada:
            receta_seleccionada = next(
                (
                    r for r in recetas
                    if r["id_receta"] == id_seleccionada
                ),
                None
            )

        if not receta_seleccionada and recetas:
            receta_seleccionada = recetas[0]

        ingredientes_seleccionados = []

        if receta_seleccionada:
            cursor.execute("""
                SELECT
                    dr.cantidad,
                    dr.cantidad_receta,
                    dr.costo_unitario,
                    dr.subtotal,
                    i.nombre AS insumo,
                    u.abreviatura AS unidad_receta
                FROM detalle_recetas dr
                INNER JOIN insumos i
                    ON i.id_insumo = dr.id_insumo
                LEFT JOIN unidades_medida u
                    ON u.id_unidad = dr.id_unidad_receta
                WHERE dr.id_receta = %s
                ORDER BY dr.id_detalle_receta
            """, (receta_seleccionada["id_receta"],))

            ingredientes_seleccionados = cursor.fetchall()

        return render_template(
            "admin/recetas.html",
            menu=obtener_menu(),
            nombre=session.get("nombre"),
            rol=session.get("rol"),
            recetas=recetas,
            categorias=categorias,
            insumos=insumos,
            unidades=unidades,
            estadisticas=estadisticas,
            receta_seleccionada=receta_seleccionada,
            ingredientes_seleccionados=ingredientes_seleccionados
        )

    except (ValueError, InvalidOperation) as error:
        conexion.rollback()
        flash(str(error), "error")
        return redirect(url_for("recetas.gestionar_recetas"))

    except Exception as error:
        conexion.rollback()
        print("ERROR EN RECETAS:", repr(error))
        flash("Ocurrió un error al procesar la receta.", "error")
        return redirect(url_for("administrativo.dashboard"))

    finally:
        if cursor:
            cursor.close()
        conexion.close()


# ============================================================
# CONSULTAR LOS DATOS DE UNA RECETA PARA EDITAR
# ============================================================
@recetas_bp.route("/<int:id_receta>/datos", methods=["GET"])
def obtener_datos_receta(id_receta):

    if "id_usuario" not in session:
        return jsonify({"error": "Sesión no válida"}), 401

    if session.get("rol") not in (
        "Administrador", "Gerente", "Bartender"
    ):
        return jsonify({"error": "No tienes permiso"}), 403

    conexion = obtener_conexion()

    if conexion is None:
        return jsonify({
            "error": "No hay conexión con la base de datos"
        }), 500

    cursor = None

    try:
        cursor = conexion.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                r.id_receta,
                r.id_producto,
                r.nombre AS nombre_receta,
                r.porciones,
                r.instrucciones,
                p.codigo,
                p.nombre,
                p.descripcion,
                p.imagen,
                p.id_categoria,
                p.porcentaje_utilidad,
                p.estado
            FROM recetas r
            INNER JOIN productos p
                ON p.id_producto = r.id_producto
            WHERE r.id_receta = %s
        """, (id_receta,))

        receta = cursor.fetchone()

        if not receta:
            return jsonify({"error": "La receta no existe"}), 404

        cursor.execute("""
            SELECT
                id_insumo,
                cantidad_receta,
                id_unidad_receta
            FROM detalle_recetas
            WHERE id_receta = %s
            ORDER BY id_detalle_receta
        """, (id_receta,))

        ingredientes = cursor.fetchall()

        return jsonify({
            "receta": {
                "id_receta": receta["id_receta"],
                "id_producto": receta["id_producto"],
                "codigo": receta["codigo"],
                "nombre": receta["nombre"],
                "descripcion": receta["descripcion"] or "",
                "imagen": receta["imagen"] or "",
                "id_categoria": receta["id_categoria"],
                "porciones": float(receta["porciones"]),
                "instrucciones": receta["instrucciones"] or "",
                "porcentaje_utilidad": float(
                    receta["porcentaje_utilidad"]
                ),
                "estado": receta["estado"]
            },
            "ingredientes": [
                {
                    "id_insumo": item["id_insumo"],
                    "cantidad": float(item["cantidad_receta"] or 0),
                    "id_unidad_receta": item["id_unidad_receta"]
                }
                for item in ingredientes
            ]
        })

    except Exception as error:
        print("ERROR AL CONSULTAR RECETA:", repr(error))
        return jsonify({
            "error": "No se pudieron cargar los datos de la receta"
        }), 500

    finally:
        if cursor:
            cursor.close()
        conexion.close()


# ============================================================
# EDITAR UNA RECETA EXISTENTE SIN DUPLICARLA
# ============================================================
@recetas_bp.route("/<int:id_receta>/editar", methods=["POST"])
def editar_receta(id_receta):

    if "id_usuario" not in session:
        return redirect(url_for("login.login"))

    if session.get("rol") not in (
        "Administrador", "Gerente", "Bartender"
    ):
        abort(403)

    conexion = obtener_conexion()

    if conexion is None:
        flash("No se pudo conectar con la base de datos.", "error")
        return redirect(url_for("recetas.gestionar_recetas"))

    cursor = None

    try:
        cursor = conexion.cursor(dictionary=True)

        # Buscar el producto y receta existentes.
        cursor.execute("""
            SELECT
                r.id_receta,
                r.id_producto,
                p.imagen
            FROM recetas r
            INNER JOIN productos p
                ON p.id_producto = r.id_producto
            WHERE r.id_receta = %s
        """, (id_receta,))

        existente = cursor.fetchone()

        if not existente:
            raise ValueError("La receta que intentas editar no existe.")

        id_producto = existente["id_producto"]

        codigo = request.form.get("codigo", "").strip()
        nombre = request.form.get("nombre", "").strip()
        descripcion = request.form.get("descripcion", "").strip()
        id_categoria = request.form.get("id_categoria", "").strip()
        porciones = Decimal(request.form.get("porciones", "1"))
        instrucciones = request.form.get("instrucciones", "").strip()
        utilidad = Decimal(
            request.form.get("porcentaje_utilidad", "60")
        )

        ids_insumos = request.form.getlist("id_insumo[]")
        cantidades = request.form.getlist("cantidad[]")
        unidades_receta = request.form.getlist(
            "id_unidad_receta[]"
        )

        if not all([codigo, nombre, id_categoria]):
            raise ValueError(
                "Completa el código, nombre y categoría."
            )

        if porciones <= 0:
            raise ValueError(
                "Las porciones deben ser mayores que cero."
            )

        if utilidad < 0 or utilidad >= 100:
            raise ValueError(
                "La utilidad debe ser menor al 100%."
            )

        cursor.execute("""
            SELECT id_categoria
            FROM categorias_productos
            WHERE id_categoria = %s
        """, (id_categoria,))

        if not cursor.fetchone():
            raise ValueError("La categoría seleccionada no existe.")

        # Evitar códigos duplicados en otros productos.
        cursor.execute("""
            SELECT id_producto
            FROM productos
            WHERE codigo = %s
              AND id_producto <> %s
        """, (codigo, id_producto))

        if cursor.fetchone():
            raise ValueError(
                "Ese código ya está registrado en otro producto."
            )

        # Conservar la fotografía anterior si no se sube otra.
        ruta_imagen = existente["imagen"]
        imagen = request.files.get("imagen")

        if imagen and imagen.filename:
            if not extension_permitida(imagen.filename):
                raise ValueError(
                    "La imagen debe ser PNG, JPG, JPEG o WEBP."
                )

            nombre_archivo = (
                f"{codigo}_{secure_filename(imagen.filename)}"
            )

            carpeta = os.path.join(
                current_app.static_folder,
                "img",
                "productos"
            )

            os.makedirs(carpeta, exist_ok=True)
            imagen.save(os.path.join(carpeta, nombre_archivo))

            ruta_imagen = f"img/productos/{nombre_archivo}"

        ingredientes, costo_total = obtener_ingredientes(
            cursor,
            ids_insumos,
            cantidades,
            unidades_receta
        )

        precio_venta = calcular_precio(costo_total, utilidad)

        # UPDATE del producto existente: no INSERT.
        cursor.execute("""
            UPDATE productos
            SET
                codigo = %s,
                id_categoria = %s,
                nombre = %s,
                descripcion = %s,
                imagen = %s,
                costo_preparacion = %s,
                porcentaje_utilidad = %s,
                precio_venta = %s
            WHERE id_producto = %s
        """, (
            codigo,
            id_categoria,
            nombre,
            descripcion or None,
            ruta_imagen,
            costo_total,
            utilidad,
            precio_venta,
            id_producto
        ))

        # UPDATE de la receta existente: no INSERT.
        cursor.execute("""
            UPDATE recetas
            SET
                nombre = %s,
                porciones = %s,
                instrucciones = %s,
                costo_total = %s
            WHERE id_receta = %s
        """, (
            nombre,
            porciones,
            instrucciones or None,
            costo_total,
            id_receta
        ))

        # Eliminar únicamente los ingredientes de esta receta.
        cursor.execute("""
            DELETE FROM detalle_recetas
            WHERE id_receta = %s
        """, (id_receta,))

        # Insertar nuevamente sus ingredientes actualizados.
        guardar_detalles(cursor, id_receta, ingredientes)

        conexion.commit()

        flash("La receta se actualizó correctamente.", "success")

    except (ValueError, InvalidOperation) as error:
        conexion.rollback()
        flash(str(error), "error")

    except Exception as error:
        conexion.rollback()
        print("ERROR AL EDITAR RECETA:", repr(error))
        flash("Ocurrió un error al actualizar la receta.", "error")

    finally:
        if cursor:
            cursor.close()
        conexion.close()

    return redirect(
        url_for("recetas.gestionar_recetas", id=id_receta)
    )

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    abort,
    jsonify
)

from models.conexion import obtener_conexion

from decimal import Decimal, InvalidOperation
from datetime import datetime, date


compras_gerente_bp = Blueprint(
    "compras_gerente",
    __name__,
    url_prefix="/gerente/compras"
)


# ==========================================
# VERIFICAR ACCESO
# ==========================================

def verificar_acceso():

    if "id_usuario" not in session:
        return False

    if session.get("rol") != "Gerente":
        abort(403)

    return True


# ==========================================
# VISTA PRINCIPAL DE COMPRAS
# ==========================================

@compras_gerente_bp.route("/", methods=["GET"])
def compras():

    if not verificar_acceso():
        return redirect(url_for("login.login"))

    conexion = obtener_conexion()

    if conexion is None:
        flash("No se pudo conectar con la base de datos.", "error")
        return redirect(url_for("administrativo.dashboard"))

    cursor = None

    try:

        cursor = conexion.cursor(dictionary=True)

        # Menú lateral del Gerente
        from routes.administrativo import MENUS_ROLES

        menu = MENUS_ROLES.get("Gerente", [])

        # ----------------------------------
        # INSUMOS CON BAJO STOCK
        # ----------------------------------

        cursor.execute("""
            SELECT
                i.id_insumo,
                i.codigo,
                i.nombre,
                i.stock_actual,
                i.stock_minimo,
                i.costo_unitario,
                c.nombre AS categoria,
                u.nombre AS unidad,
                u.abreviatura

            FROM insumos i

            INNER JOIN categorias_insumos c
                ON i.id_categoria = c.id_categoria

            INNER JOIN unidades_medida u
                ON i.id_unidad = u.id_unidad

            WHERE i.estado = 'Activo'
              AND i.stock_actual <= i.stock_minimo

            ORDER BY
                (i.stock_actual <= 0) DESC,
                i.stock_actual ASC,
                i.nombre ASC
        """)

        insumos_bajo_stock = cursor.fetchall()

        # ----------------------------------
        # CONTAR INSUMOS CON BAJO STOCK
        # ----------------------------------

        total_bajo_stock = len(insumos_bajo_stock)

        # ----------------------------------
        # PEDIDOS PENDIENTES
        # ----------------------------------

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM compras
            WHERE estado = 'Pendiente'
        """)

        pedidos = cursor.fetchone()

        pedidos_en_proceso = pedidos["total"] or 0

        # ----------------------------------
        # PROVEEDORES ACTIVOS
        # ----------------------------------

        cursor.execute("""
            SELECT
                id_proveedor,
                nombre,
                telefono,
                correo
            FROM proveedores
            WHERE estado = 'Activo'
            ORDER BY nombre ASC
        """)

        proveedores = cursor.fetchall()

        return render_template(
            "gerente/compras.html",
            insumos_bajo_stock=insumos_bajo_stock,
            total_bajo_stock=total_bajo_stock,
            pedidos_en_proceso=pedidos_en_proceso,
            proveedores=proveedores,
            nombre=session.get("nombre"),
            rol=session.get("rol"),
            menu=menu
        )

    except Exception as error:

        print("ERROR AL CARGAR COMPRAS:", repr(error))

        raise

    finally:

        if cursor:
            cursor.close()

        conexion.close()


# ==========================================
# CONSULTAR INSUMOS DE UN PROVEEDOR
# ==========================================

@compras_gerente_bp.route(
    "/proveedor/<int:id_proveedor>/insumos",
    methods=["GET"]
)
def obtener_insumos_proveedor(id_proveedor):

    if not verificar_acceso():
        return jsonify({
            "error": "No tienes permiso para realizar esta acción."
        }), 403

    conexion = obtener_conexion()

    if conexion is None:
        return jsonify({
            "error": "No se pudo conectar con MySQL."
        }), 500

    cursor = None

    try:

        cursor = conexion.cursor(dictionary=True)

        # Verificar que el proveedor esté activo
        cursor.execute("""
            SELECT id_proveedor
            FROM proveedores
            WHERE id_proveedor = %s
              AND estado = 'Activo'
        """, (id_proveedor,))

        proveedor = cursor.fetchone()

        if not proveedor:
            return jsonify({
                "error": "El proveedor no existe o está inactivo."
            }), 404

        # Consultar insumos relacionados con el proveedor
        cursor.execute("""
            SELECT
                i.id_insumo,
                i.codigo,
                i.nombre,
                i.costo_unitario,
                i.stock_actual,
                i.stock_minimo,
                u.nombre AS unidad,
                u.abreviatura

            FROM proveedores_insumos pi

            INNER JOIN insumos i
                ON pi.id_insumo = i.id_insumo

            INNER JOIN unidades_medida u
                ON i.id_unidad = u.id_unidad

            WHERE pi.id_proveedor = %s
              AND i.estado = 'Activo'

            ORDER BY i.nombre ASC
        """, (id_proveedor,))

        insumos = cursor.fetchall()

        for insumo in insumos:
            insumo["costo_unitario"] = float(insumo["costo_unitario"])
            insumo["stock_actual"] = float(insumo["stock_actual"])
            insumo["stock_minimo"] = float(insumo["stock_minimo"])

        return jsonify({
            "ok": True,
            "insumos": insumos
        })

    except Exception as error:

        print("ERROR AL CONSULTAR INSUMOS DEL PROVEEDOR:", repr(error))

        return jsonify({
            "error": "No se pudieron consultar los insumos del proveedor."
        }), 500

    finally:

        if cursor:
            cursor.close()

        conexion.close()


# ==========================================
# GENERAR PEDIDO DE COMPRA
# ==========================================

@compras_gerente_bp.route("/generar", methods=["POST"])
def generar_pedido():

    if not verificar_acceso():
        return jsonify({
            "error": "No tienes permiso para realizar esta acción."
        }), 403

    datos = request.get_json(silent=True)

    if not datos:
        return jsonify({
            "error": "No se recibieron los datos del pedido."
        }), 400

    # ----------------------------------
    # VALIDAR DATOS GENERALES
    # ----------------------------------

    try:

        id_proveedor = int(datos.get("id_proveedor"))

        fecha_entrega_texto = str(
            datos.get("fecha_entrega", "")
        ).strip()

        fecha_entrega = datetime.strptime(
            fecha_entrega_texto,
            "%Y-%m-%d"
        ).date()

        if fecha_entrega < date.today():
            raise ValueError("La fecha de entrega no puede ser anterior a hoy.")

        observaciones = str(
            datos.get("observaciones", "")
        ).strip()

        insumos = datos.get("insumos", [])

        if not insumos:
            raise ValueError("Agrega al menos un insumo al pedido.")

        if not isinstance(insumos, list):
            raise ValueError("La lista de insumos no es válida.")

    except (ValueError, TypeError) as error:

        return jsonify({
            "error": str(error)
        }), 400

    # ----------------------------------
    # VALIDAR CANTIDADES Y PRODUCTOS
    # ----------------------------------

    insumos_validos = []
    ids_insumos = set()

    try:

        for elemento in insumos:

            id_insumo = int(elemento.get("id_insumo"))

            cantidad = Decimal(
                str(elemento.get("cantidad"))
            )

            if not cantidad.is_finite() or cantidad <= 0:
                raise ValueError("Todas las cantidades deben ser mayores a cero.")

            if id_insumo in ids_insumos:
                raise ValueError("No agregues el mismo insumo más de una vez.")

            ids_insumos.add(id_insumo)

            insumos_validos.append({
                "id_insumo": id_insumo,
                "cantidad": cantidad
            })

    except (ValueError, TypeError, InvalidOperation) as error:

        return jsonify({
            "error": str(error)
        }), 400

    conexion = obtener_conexion()

    if conexion is None:
        return jsonify({
            "error": "No se pudo conectar con MySQL."
        }), 500

    cursor = None

    try:

        cursor = conexion.cursor(dictionary=True)

        # ----------------------------------
        # VERIFICAR PROVEEDOR
        # ----------------------------------

        cursor.execute("""
            SELECT id_proveedor
            FROM proveedores
            WHERE id_proveedor = %s
              AND estado = 'Activo'
        """, (id_proveedor,))

        proveedor = cursor.fetchone()

        if not proveedor:
            conexion.rollback()

            return jsonify({
                "error": "Selecciona un proveedor activo."
            }), 400

        # ----------------------------------
        # CONSULTAR COSTOS DE LOS INSUMOS
        # ----------------------------------

        total = Decimal("0.00")
        detalles = []

        for elemento in insumos_validos:

            cursor.execute("""
                SELECT
                    i.id_insumo,
                    i.nombre,
                    i.costo_unitario

                FROM proveedores_insumos pi

                INNER JOIN insumos i
                    ON pi.id_insumo = i.id_insumo

                WHERE pi.id_proveedor = %s
                  AND i.id_insumo = %s
                  AND i.estado = 'Activo'
            """, (
                id_proveedor,
                elemento["id_insumo"]
            ))

            insumo = cursor.fetchone()

            if not insumo:
                raise ValueError(
                    "Uno de los insumos no pertenece al proveedor seleccionado "
                    "o está inactivo."
                )

            costo_unitario = Decimal(
                str(insumo["costo_unitario"])
            )

            cantidad = elemento["cantidad"]

            subtotal = cantidad * costo_unitario

            total += subtotal

            detalles.append({
                "id_insumo": insumo["id_insumo"],
                "cantidad": cantidad,
                "costo_unitario": costo_unitario
            })

        total = total.quantize(Decimal("0.01"))

        # ----------------------------------
        # REGISTRAR COMPRA
        # ----------------------------------

        cursor.execute("""
            INSERT INTO compras (
                id_proveedor,
                id_usuario,
                fecha_entrega,
                total,
                observaciones,
                estado
            )
            VALUES (%s, %s, %s, %s, %s, 'Pendiente')
        """, (
            id_proveedor,
            session["id_usuario"],
            fecha_entrega,
            total,
            observaciones or None
        ))

        id_compra = cursor.lastrowid

        # ----------------------------------
        # REGISTRAR DETALLES DE LA COMPRA
        # ----------------------------------

        for detalle in detalles:

            cursor.execute("""
                INSERT INTO detalle_compras (
                    id_compra,
                    id_insumo,
                    cantidad,
                    costo_unitario
                )
                VALUES (%s, %s, %s, %s)
            """, (
                id_compra,
                detalle["id_insumo"],
                detalle["cantidad"],
                detalle["costo_unitario"]
            ))

        # Confirmar todos los registros
        conexion.commit()

        return jsonify({
            "ok": True,
            "mensaje": "El pedido se generó correctamente.",
            "id_compra": id_compra,
            "total": float(total)
        })

    except ValueError as error:

        conexion.rollback()

        return jsonify({
            "error": str(error)
        }), 400

    except Exception as error:

        conexion.rollback()

        print("ERROR AL GENERAR PEDIDO:", repr(error))

        return jsonify({
            "error": "No se pudo generar el pedido. Inténtalo nuevamente."
        }), 500

    finally:

        if cursor:
            cursor.close()

        conexion.close()
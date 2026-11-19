from flask import (
    Blueprint,
    render_template,
    request,
    jsonify,
    session,
    redirect,
    url_for,
    abort
)

from models.conexion import obtener_conexion

from functools import wraps
from decimal import Decimal, InvalidOperation
from datetime import datetime
import uuid


# ==========================================================
# CREAR BLUEPRINT
# ==========================================================

ventas_bp = Blueprint(
    "ventas",
    __name__,
    url_prefix="/ventas"
)


# ==========================================================
# FUNCIONES GENERALES
# ==========================================================

def requiere_cajero(funcion):
    @wraps(funcion)
    def decorada(*args, **kwargs):

        if "id_usuario" not in session:
            return redirect(url_for("login.login"))

        rol = str(session.get("rol", "")).strip().lower()

        if rol != "cajero":
            abort(403)

        return funcion(*args, **kwargs)

    return decorada


def obtener_conexion_segura():
    conexion = obtener_conexion()

    if conexion is None:
        raise Exception("No fue posible conectar con MySQL.")

    return conexion


def respuesta_error(mensaje, codigo=400):
    return jsonify({
        "ok": False,
        "mensaje": mensaje
    }), codigo


def convertir_json(valor):

    if isinstance(valor, Decimal):
        return float(valor)

    if isinstance(valor, datetime):
        return valor.strftime("%Y-%m-%d %H:%M:%S")

    if isinstance(valor, dict):
        return {
            clave: convertir_json(dato)
            for clave, dato in valor.items()
        }

    if isinstance(valor, list):
        return [
            convertir_json(dato)
            for dato in valor
        ]

    return valor


def recalcular_totales(cursor, id_venta):

    cursor.execute("""
        SELECT COALESCE(SUM(subtotal), 0) AS total
        FROM detalle_ventas
        WHERE id_venta = %s
    """, (id_venta,))

    resultado = cursor.fetchone()
    total = Decimal(str(resultado["total"]))

    cursor.execute("""
        UPDATE ventas
        SET subtotal = %s,
            total = %s
        WHERE id_venta = %s
    """, (
        total,
        total,
        id_venta
    ))

    return total



def verificar_cuenta(cursor, id_venta):
    """
    Verifica que la cuenta exista y continúe abierta.

    No limita la cuenta al usuario que la creó,
    porque recepción puede abrirla al recibir una reservación.
    """

    cursor.execute("""
        SELECT
            id_venta,
            total,
            subtotal,
            estado,
            tipo_cuenta,
            id_mesa,
            folio,
            nombre_cliente
        FROM ventas
        WHERE id_venta = %s
          AND estado = 'Abierta'
        FOR UPDATE
    """, (id_venta,))

    return cursor.fetchone()


# ==========================================================
# VENTANA PRINCIPAL
# ==========================================================

@ventas_bp.route("/")
@requiere_cajero
def ventana_ventas():

    from routes.administrativo import MENUS_ROLES

    menu = MENUS_ROLES.get("Cajero", [])

    return render_template(
        "cajero/ventas.html",
        nombre=session.get("nombre", "Cajero"),
        rol=session.get("rol", "Cajero"),
        menu=menu
    )


# ==========================================================
# CONSULTAR PRODUCTOS Y CATEGORÍAS
# ==========================================================

@ventas_bp.route("/api/productos")
@requiere_cajero
def api_productos():

    conexion = None

    try:
        conexion = obtener_conexion_segura()
        cursor = conexion.cursor(dictionary=True)

        # PRODUCTOS ACTIVOS CON SU CATEGORÍA

        cursor.execute("""
            SELECT
                p.id_producto,
                p.codigo,
                p.nombre,
                p.descripcion,
                p.imagen,
                p.precio_venta,
                p.id_categoria,
                c.nombre AS categoria

            FROM productos p

            INNER JOIN categorias_productos c
                ON c.id_categoria = p.id_categoria

            WHERE p.estado = 'Activo'

            ORDER BY c.nombre, p.nombre
        """)

        productos = cursor.fetchall()

        # CATEGORÍAS QUE TIENEN PRODUCTOS ACTIVOS
        # ESTA ES LA MODIFICACIÓN PRINCIPAL

        cursor.execute("""
            SELECT DISTINCT
                c.id_categoria,
                c.nombre

            FROM categorias_productos c

            INNER JOIN productos p
                ON p.id_categoria = c.id_categoria

            WHERE p.estado = 'Activo'

            ORDER BY c.nombre
        """)

        categorias = cursor.fetchall()

        cursor.close()

        return jsonify({
            "ok": True,
            "productos": convertir_json(productos),
            "categorias": convertir_json(categorias)
        })

    except Exception as error:

        print("ERROR API PRODUCTOS:", repr(error))

        return respuesta_error(
            "No fue posible cargar los productos.",
            500
        )

    finally:
        if conexion:
            conexion.close()



# ==========================================================
# CONSULTAR MESAS Y CUENTAS ABIERTAS
# ==========================================================

@ventas_bp.route("/api/cuentas")
@requiere_cajero
def api_cuentas():

    conexion = None

    try:
        conexion = obtener_conexion_segura()
        cursor = conexion.cursor(dictionary=True)

        # TODAS LAS CUENTAS ABIERTAS
        # INCLUYE LAS CREADAS POR RECEPCIÓN.

        cursor.execute("""
            SELECT
                v.id_venta,
                v.folio,
                v.tipo_cuenta,
                v.id_mesa,
                v.nombre_cliente,
                v.fecha_venta,
                v.total,
                m.nombre_mesa,
                COUNT(d.id_detalle_venta) AS cantidad_productos

            FROM ventas v

            LEFT JOIN mesas m
                ON m.id_mesa = v.id_mesa

            LEFT JOIN detalle_ventas d
                ON d.id_venta = v.id_venta

            WHERE v.estado = 'Abierta'

            GROUP BY
                v.id_venta,
                v.folio,
                v.tipo_cuenta,
                v.id_mesa,
                v.nombre_cliente,
                v.fecha_venta,
                v.total,
                m.nombre_mesa

            ORDER BY v.fecha_venta DESC
        """)

        cuentas = cursor.fetchall()

        # CONSULTAR MESAS Y SU DISPONIBILIDAD.

        
        cursor.execute("""
            SELECT
                m.id_mesa,
                m.nombre_mesa,
                m.capacidad,
                m.tipo,
                m.estado,

                CASE
                    WHEN EXISTS (
                        SELECT 1
                        FROM ventas v
                        WHERE v.id_mesa = m.id_mesa
                        AND v.tipo_cuenta = 'Mesa'
                        AND v.estado = 'Abierta'
                    )
                    THEN 'Ocupada'

                    WHEN EXISTS (
                        SELECT 1
                        FROM reservaciones r
                        WHERE r.id_mesa = m.id_mesa
                        AND r.fecha = CURDATE()
                        AND r.estado = 'En curso'
                    )
                    THEN 'Ocupada'

                    WHEN EXISTS (
                        SELECT 1
                        FROM reservaciones r
                        WHERE r.id_mesa = m.id_mesa
                        AND r.fecha = CURDATE()
                        AND r.estado IN ('Reservada', 'Confirmada')
                    )
                    THEN 'Reservada'

                    ELSE 'Disponible'
                END AS disponibilidad

            FROM mesas m
            WHERE m.estado = 'Activa'
            ORDER BY m.id_mesa
        """)

        mesas = cursor.fetchall()


        cursor.close()

        return jsonify({
            "ok": True,
            "cuentas": convertir_json(cuentas),
            "mesas": convertir_json(mesas)
        })

    except Exception as error:

        print("ERROR API CUENTAS:", repr(error))

        return respuesta_error(
            "No fue posible cargar las cuentas.",
            500
        )

    finally:
        if conexion:
            conexion.close()


# ==========================================================
# ABRIR CUENTA DE MESA O BARRA
# ==========================================================

@ventas_bp.route("/api/abrir-cuenta", methods=["POST"])
@requiere_cajero
def abrir_cuenta():

    datos = request.get_json(silent=True) or {}

    tipo_cuenta = str(
        datos.get("tipo_cuenta", "")
    ).strip()

    nombre_cliente = str(
        datos.get("nombre_cliente") or ""
    ).strip() or None

    id_mesa = datos.get("id_mesa")

    if tipo_cuenta not in ("Mesa", "Barra"):
        return respuesta_error(
            "Selecciona un tipo de cuenta válido."
        )

    if tipo_cuenta == "Mesa":

        try:
            id_mesa = int(id_mesa)

        except (TypeError, ValueError):
            return respuesta_error(
                "Selecciona una mesa válida."
            )

    else:
        id_mesa = None

    conexion = None

    try:
        conexion = obtener_conexion_segura()
        cursor = conexion.cursor(dictionary=True)

        if tipo_cuenta == "Mesa":

            cursor.execute("""
                SELECT id_mesa
                FROM mesas
                WHERE id_mesa = %s
                FOR UPDATE
            """, (id_mesa,))

            mesa = cursor.fetchone()

            if not mesa:
                conexion.rollback()

                return respuesta_error(
                    "La mesa seleccionada no existe."
                )

            # EVITAR DOS CUENTAS ABIERTAS EN LA MISMA MESA

            cursor.execute("""
                SELECT id_venta
                FROM ventas
                WHERE id_mesa = %s
                  AND tipo_cuenta = 'Mesa'
                  AND estado = 'Abierta'
                LIMIT 1
                FOR UPDATE
            """, (id_mesa,))

            cuenta_existente = cursor.fetchone()

            if cuenta_existente:
                conexion.rollback()

                return respuesta_error(
                    "Esta mesa ya tiene una cuenta abierta."
                )

        # GENERAR FOLIO

        folio = (
            "LC-"
            + datetime.now().strftime("%y%m%d")
            + "-"
            + uuid.uuid4().hex[:6].upper()
        )

        cursor.execute("""
            INSERT INTO ventas (
                id_usuario,
                tipo_cuenta,
                id_mesa,
                nombre_cliente,
                folio,
                subtotal,
                total,
                metodo_pago,
                estado
            )
            VALUES (
                %s, %s, %s, %s, %s,
                0, 0, NULL, 'Abierta'
            )
        """, (
            session["id_usuario"],
            tipo_cuenta,
            id_mesa,
            nombre_cliente,
            folio
        ))

        id_venta = cursor.lastrowid

        conexion.commit()
        cursor.close()

        return jsonify({
            "ok": True,
            "mensaje": "Cuenta abierta correctamente.",
            "id_venta": id_venta,
            "folio": folio
        })

    except Exception as error:

        if conexion:
            conexion.rollback()

        print("ERROR ABRIR CUENTA:", repr(error))

        return respuesta_error(
            "No fue posible abrir la cuenta.",
            500
        )

    finally:
        if conexion:
            conexion.close()



# ==========================================================
# CONSULTAR DETALLE DE UNA CUENTA
# ==========================================================

@ventas_bp.route("/api/cuenta/<int:id_venta>")
@requiere_cajero
def detalle_cuenta(id_venta):

    conexion = None

    try:
        conexion = obtener_conexion_segura()
        cursor = conexion.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                v.id_venta,
                v.folio,
                v.tipo_cuenta,
                v.id_mesa,
                v.nombre_cliente,
                v.subtotal,
                v.total,
                v.estado,
                m.nombre_mesa

            FROM ventas v

            LEFT JOIN mesas m
                ON m.id_mesa = v.id_mesa

            WHERE v.id_venta = %s
              AND v.estado = 'Abierta'
        """, (id_venta,))

        cuenta = cursor.fetchone()

        if not cuenta:
            cursor.close()

            return respuesta_error(
                "La cuenta no existe o ya fue cerrada.",
                404
            )

        cursor.execute("""
            SELECT
                d.id_detalle_venta,
                d.id_producto,
                p.nombre,
                p.imagen,
                d.cantidad,
                d.precio_unitario,
                d.subtotal

            FROM detalle_ventas d

            INNER JOIN productos p
                ON p.id_producto = d.id_producto

            WHERE d.id_venta = %s

            ORDER BY d.id_detalle_venta
        """, (id_venta,))

        detalles = cursor.fetchall()

        cursor.close()

        return jsonify({
            "ok": True,
            "cuenta": convertir_json(cuenta),
            "detalles": convertir_json(detalles)
        })

    except Exception as error:

        print("ERROR DETALLE CUENTA:", repr(error))

        return respuesta_error(
            "No fue posible consultar la cuenta.",
            500
        )

    finally:
        if conexion:
            conexion.close()


# ==========================================================
# AGREGAR PRODUCTO A UNA CUENTA
# ==========================================================

@ventas_bp.route("/api/agregar-producto", methods=["POST"])
@requiere_cajero
def agregar_producto():

    datos = request.get_json(silent=True) or {}

    try:
        id_venta = int(datos.get("id_venta"))
        id_producto = int(datos.get("id_producto"))
        cantidad = int(datos.get("cantidad", 1))

        if cantidad < 1:
            return respuesta_error(
                "La cantidad debe ser mayor que cero."
            )

    except (TypeError, ValueError):
        return respuesta_error(
            "Los datos del producto no son válidos."
        )

    conexion = None

    try:
        conexion = obtener_conexion_segura()
        cursor = conexion.cursor(dictionary=True)

        cuenta = verificar_cuenta(
            cursor,
            id_venta
        )

        if not cuenta:
            conexion.rollback()

            return respuesta_error(
                "La cuenta no está disponible.",
                404
            )

        cursor.execute("""
            SELECT
                id_producto,
                precio_venta,
                costo_preparacion
            FROM productos
            WHERE id_producto = %s
              AND estado = 'Activo'
        """, (id_producto,))

        producto = cursor.fetchone()

        if not producto:
            conexion.rollback()

            return respuesta_error(
                "El producto no existe o está inactivo."
            )

        precio = Decimal(str(producto["precio_venta"]))
        costo = Decimal(str(producto["costo_preparacion"] or 0))

        cursor.execute("""
            SELECT
                id_detalle_venta,
                cantidad
            FROM detalle_ventas
            WHERE id_venta = %s
              AND id_producto = %s
            LIMIT 1
            FOR UPDATE
        """, (
            id_venta,
            id_producto
        ))

        detalle = cursor.fetchone()

        if detalle:

            nueva_cantidad = detalle["cantidad"] + cantidad
            nuevo_subtotal = precio * nueva_cantidad

            cursor.execute("""
                UPDATE detalle_ventas
                SET cantidad = %s,
                    precio_unitario = %s,
                    costo_unitario = %s,
                    subtotal = %s
                WHERE id_detalle_venta = %s
            """, (
                nueva_cantidad,
                precio,
                costo,
                nuevo_subtotal,
                detalle["id_detalle_venta"]
            ))

        else:

            subtotal = precio * cantidad

            cursor.execute("""
                INSERT INTO detalle_ventas (
                    id_venta,
                    id_producto,
                    cantidad,
                    precio_unitario,
                    costo_unitario,
                    subtotal
                )
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                id_venta,
                id_producto,
                cantidad,
                precio,
                costo,
                subtotal
            ))

        recalcular_totales(cursor, id_venta)

        conexion.commit()
        cursor.close()

        return jsonify({
            "ok": True,
            "mensaje": "Producto agregado a la cuenta."
        })

    except Exception as error:

        if conexion:
            conexion.rollback()

        print("ERROR AGREGAR PRODUCTO:", repr(error))

        return respuesta_error(
            "No fue posible agregar el producto.",
            500
        )

    finally:
        if conexion:
            conexion.close()


# ==========================================================
# MODIFICAR CANTIDAD O ELIMINAR PRODUCTO
# ==========================================================

@ventas_bp.route("/api/actualizar-producto", methods=["POST"])
@requiere_cajero
def actualizar_producto():

    datos = request.get_json(silent=True) or {}

    try:
        id_venta = int(datos.get("id_venta"))
        id_detalle = int(datos.get("id_detalle"))
        cantidad = int(datos.get("cantidad"))

    except (TypeError, ValueError):
        return respuesta_error(
            "Los datos enviados no son válidos."
        )

    conexion = None

    try:
        conexion = obtener_conexion_segura()
        cursor = conexion.cursor(dictionary=True)

        cuenta = verificar_cuenta(
            cursor,
            id_venta
        )

        if not cuenta:
            conexion.rollback()

            return respuesta_error(
                "La cuenta no está disponible.",
                404
            )

        cursor.execute("""
            SELECT id_detalle_venta
            FROM detalle_ventas
            WHERE id_detalle_venta = %s
              AND id_venta = %s
            FOR UPDATE
        """, (
            id_detalle,
            id_venta
        ))

        detalle = cursor.fetchone()

        if not detalle:
            conexion.rollback()

            return respuesta_error(
                "El producto no pertenece a esta cuenta.",
                404
            )

        if cantidad <= 0:

            cursor.execute("""
                DELETE FROM detalle_ventas
                WHERE id_detalle_venta = %s
                  AND id_venta = %s
            """, (
                id_detalle,
                id_venta
            ))

        else:

            cursor.execute("""
                UPDATE detalle_ventas
                SET cantidad = %s,
                    subtotal = %s * precio_unitario
                WHERE id_detalle_venta = %s
                  AND id_venta = %s
            """, (
                cantidad,
                cantidad,
                id_detalle,
                id_venta
            ))

        recalcular_totales(cursor, id_venta)

        conexion.commit()
        cursor.close()

        return jsonify({
            "ok": True,
            "mensaje": "Cuenta actualizada correctamente."
        })

    except Exception as error:

        if conexion:
            conexion.rollback()

        print("ERROR ACTUALIZAR PRODUCTO:", repr(error))

        return respuesta_error(
            "No fue posible actualizar el producto.",
            500
        )

    finally:
        if conexion:
            conexion.close()


# ==========================================================
# COBRAR CUENTA
# ADMITE PAGOS SENCILLOS Y MIXTOS
# ==========================================================

@ventas_bp.route("/api/cobrar", methods=["POST"])
@requiere_cajero
def cobrar():

    datos = request.get_json(silent=True) or {}

    try:
        id_venta = int(datos.get("id_venta"))
        pagos = datos.get("pagos", [])

        if not isinstance(pagos, list) or not pagos:
            return respuesta_error(
                "Agrega al menos un método de pago."
            )

        metodos_validos = {
            "Efectivo",
            "Tarjeta",
            "Transferencia"
        }

        pagos_limpios = []
        total_pagado = Decimal("0.00")
        total_recibido = Decimal("0.00")

        for pago in pagos:

            metodo = str(
                pago.get("metodo", "")
            ).strip()

            monto = Decimal(
                str(pago.get("monto", "0"))
            )

            recibido = Decimal(
                str(pago.get("recibido", monto))
            )

            if metodo not in metodos_validos:
                return respuesta_error(
                    "Selecciona un método de pago válido."
                )

            if monto <= 0:
                return respuesta_error(
                    "Los montos deben ser mayores que cero."
                )

            if recibido < 0:
                return respuesta_error(
                    "El monto recibido no puede ser negativo."
                )

            if metodo == "Efectivo":

                if recibido < monto:
                    return respuesta_error(
                        "El efectivo recibido no cubre el monto."
                    )

            else:
                recibido = monto

            pagos_limpios.append({
                "metodo": metodo,
                "monto": monto,
                "recibido": recibido
            })

            total_pagado += monto
            total_recibido += recibido

    except (TypeError, ValueError, InvalidOperation):
        return respuesta_error(
            "Los importes de pago no son válidos."
        )

    conexion = None

    try:
        conexion = obtener_conexion_segura()
        cursor = conexion.cursor(dictionary=True)

        cuenta = verificar_cuenta(
            cursor,
            id_venta
        )

        if not cuenta:
            conexion.rollback()

            return respuesta_error(
                "La cuenta no existe o ya fue cobrada.",
                404
            )

        total = Decimal(str(cuenta["total"]))

        if total <= 0:
            conexion.rollback()

            return respuesta_error(
                "No puedes cobrar una cuenta sin productos."
            )

        if total_pagado != total:
            conexion.rollback()

            return respuesta_error(
                f"Los pagos deben sumar exactamente ${total:.2f}."
            )

        metodo_resumen = (
            pagos_limpios[0]["metodo"]
            if len(pagos_limpios) == 1
            else "Mixto"
        )

        cambio_total = total_recibido - total_pagado

        # REGISTRAR CADA MÉTODO DE PAGO

        for pago in pagos_limpios:

            metodo = pago["metodo"]
            monto = pago["monto"]
            recibido = pago["recibido"]

            cambio = max(
                Decimal("0.00"),
                recibido - monto
            )

            cursor.execute("""
                INSERT INTO pagos_venta (
                    id_venta,
                    metodo_pago,
                    monto,
                    monto_recibido,
                    cambio
                )
                VALUES (%s, %s, %s, %s, %s)
            """, (
                id_venta,
                metodo,
                monto,
                recibido,
                cambio
            ))

        # CERRAR VENTA

        cursor.execute("""
            UPDATE ventas
            SET estado = 'Completada',
                metodo_pago = %s
            WHERE id_venta = %s
              AND estado = 'Abierta'
        """, (
            metodo_resumen,
            id_venta
        ))

        conexion.commit()
        cursor.close()

        return jsonify({
            "ok": True,
            "mensaje": "Venta cobrada correctamente.",
            "id_venta": id_venta,
            "total": float(total),
            "cambio": float(cambio_total)
        })

    except Exception as error:

        if conexion:
            conexion.rollback()

        print("ERROR COBRAR VENTA:", repr(error))

        return respuesta_error(
            "No fue posible completar el cobro.",
            500
        )

    finally:
        if conexion:
            conexion.close()


# ==========================================================
# CONSULTAR TICKET DE VENTA
# ==========================================================

@ventas_bp.route("/api/ticket/<int:id_venta>")
@requiere_cajero
def ticket(id_venta):

    conexion = None

    try:
        conexion = obtener_conexion_segura()
        cursor = conexion.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                v.id_venta,
                v.folio,
                v.fecha_venta,
                v.tipo_cuenta,
                v.nombre_cliente,
                v.subtotal,
                v.total,
                v.metodo_pago,
                u.nombre AS cajero,
                m.nombre_mesa

            FROM ventas v

            INNER JOIN usuarios u
                ON u.id_usuario = v.id_usuario

            LEFT JOIN mesas m
                ON m.id_mesa = v.id_mesa

            WHERE v.id_venta = %s
              AND v.id_usuario = %s
              AND v.estado = 'Completada'
        """, (
            id_venta,
            session["id_usuario"]
        ))

        venta = cursor.fetchone()

        if not venta:
            cursor.close()

            return respuesta_error(
                "No se encontró el ticket.",
                404
            )

        cursor.execute("""
            SELECT
                p.nombre,
                d.cantidad,
                d.precio_unitario,
                d.subtotal

            FROM detalle_ventas d

            INNER JOIN productos p
                ON p.id_producto = d.id_producto

            WHERE d.id_venta = %s
        """, (id_venta,))

        detalles = cursor.fetchall()

        cursor.execute("""
            SELECT
                metodo_pago,
                monto,
                monto_recibido,
                cambio
            FROM pagos_venta
            WHERE id_venta = %s
            ORDER BY id_pago
        """, (id_venta,))

        pagos = cursor.fetchall()

        cursor.close()

        return jsonify({
            "ok": True,
            "venta": convertir_json(venta),
            "detalles": convertir_json(detalles),
            "pagos": convertir_json(pagos)
        })

    except Exception as error:

        print("ERROR TICKET:", repr(error))

        return respuesta_error(
            "No fue posible generar el ticket.",
            500
        )

    finally:
        if conexion:
            conexion.close()
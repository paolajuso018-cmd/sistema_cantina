from flask import (
    Blueprint,
    render_template,
    session,
    redirect,
    url_for,
    flash,
    jsonify,
    request
)
from models.conexion import obtener_conexion
from datetime import datetime, timedelta

from models.comprobante_reservacion import(
    generar_pdf_reservacion,
    enviar_correo_reservacion
)


administrativo_bp = Blueprint("administrativo", __name__)


# ==========================================
# MENÚS SEGÚN EL ROL
# ==========================================

MENUS_ROLES = {

    "Administrador": [
        {"nombre": "Inicio", "icono": "bi-house-door", "url": "#"},
        {"nombre": "Usuarios", "icono": "bi-people", "url": "/usuarios/"},
        {"nombre": "Almacén", "icono": "bi-box-seam", "url": "/almacen/"},
        {"nombre": "Ventas", "icono": "bi-cash-stack", "url": "/admin/ventas"},
        {"nombre": "Reservaciones", "icono": "bi-calendar-check", "url": "/admin/reservaciones"},
        {"nombre": "Recetas", "icono": "bi-journal-text", "url": "/recetas/"},
        {"nombre": "Proveedores", "icono": "bi bi-truck", "url": "/admin/proveedores"},
        {"nombre": "Compras", "icono": "bi-cart3", "url": "/admin/reportes/compras"}
    ],

    "Gerente": [
        {"nombre": "Inicio", "icono": "bi-house-door", "url": "#"},
        {"nombre": "Personal", "icono": "bi-people", "url": "/usuarios/"},
        {"nombre": "Ventas", "icono": "bi-cash-stack", "url": "/admin/ventas"},
        {"nombre": "Reservaciones", "icono": "bi-calendar-check", "url": "/admin/reservaciones"},
        {"nombre": "Almacén", "icono": "bi-box-seam", "url": "/almacen/"},
        {"nombre": "Compras", "icono": "bi-cart3", "url": "/gerente/compras/"}
    ],

    "Cajero": [
        {"nombre": "Inicio", "icono": "bi-house-door", "url": "#"},
        {"nombre": "Caja", "icono": "bi-safe", "url": "#"},
        {"nombre": "Ventas", "icono": "bi-receipt", "url": "/ventas/"},
        {"nombre": "Cuentas abiertas", "icono": "bi-journal-text", "url": "#"},
        {"nombre": "Corte de caja", "icono": "bi-calculator", "url": "#"}
    ],

    "Mesero": [
        {"nombre": "Inicio", "icono": "bi-house-door", "url": "#"},
        {"nombre": "Mis mesas", "icono": "bi-grid-3x3", "url": "#"},
        {"nombre": "Menú", "icono": "bi-book", "url": "#"},
        {"nombre": "Tomar pedido", "icono": "bi-pencil-square", "url": "#"},
        {"nombre": "Mis pedidos", "icono": "bi-receipt", "url": "#"}
    ],

    "Bartender": [
        {"nombre": "Inicio", "icono": "bi-house-door", "url": "#"},
        {"nombre": "Pedidos de barra", "icono": "bi-cup-straw", "url": "#"},
        {"nombre": "En preparación", "icono": "bi-hourglass-split", "url": "#"},
        {"nombre": "Pedidos listos", "icono": "bi-check-circle", "url": "#"},
        {"nombre": "Recetas", "icono": "bi-journal-text", "url": "/recetas/"}
    ],

    "Recepcionista": [
        {"nombre": "Inicio", "icono": "bi-house-door", "url": "#"},
        {"nombre": "Reservaciones", "icono": "bi-calendar-check", "url": "/admin/reservaciones"},
        {"nombre": "Plano de mesas", "icono": "bi-grid-3x3", "url": "#"},
    ]

}


# ==========================================
# DASHBOARD GENERAL
# ==========================================

@administrativo_bp.route("/dashboard")
def dashboard():

    if "id_usuario" not in session:
        return redirect(url_for("login.login"))

    rol = session.get("rol", "")

    if rol not in MENUS_ROLES:
        flash("No tienes un rol autorizado para acceder.", "error")
        return redirect(url_for("login.login"))

    indicadores = {
        "ventas_dia": 0,
        "pedidos_dia": 0,
        "reservaciones_dia": 0,
        "insumos_bajo_stock": 0
    }

    ventas_semana = []
    productos_vendidos = []
    actividad = []

    mesas = {
        "total": 0,
        "ocupadas": 0,
        "disponibles": 0
    }

    conexion = None
    cursor = None

    try:

        conexion = obtener_conexion()

        if conexion is None:
            raise Exception("No se pudo conectar con MySQL.")

        cursor = conexion.cursor()

        # INDICADORES PRINCIPALES

        cursor.execute("""
            SELECT COALESCE(SUM(total), 0)
            FROM ventas
            WHERE DATE(fecha_venta) = CURDATE()
              AND estado = 'Completada'
        """)

        indicadores["ventas_dia"] = float(cursor.fetchone()[0] or 0)

        cursor.execute("""
            SELECT COALESCE(SUM(dv.cantidad), 0)
            FROM detalle_ventas dv
            INNER JOIN ventas v
                ON dv.id_venta = v.id_venta
            WHERE DATE(v.fecha_venta) = CURDATE()
              AND v.estado = 'Completada'
        """)

        indicadores["pedidos_dia"] = int(cursor.fetchone()[0] or 0)

        cursor.execute("""
            SELECT COUNT(*)
            FROM reservaciones
            WHERE fecha = CURDATE()
              AND estado = 'Reservada'
        """)

        indicadores["reservaciones_dia"] = int(cursor.fetchone()[0] or 0)

        cursor.execute("""
            SELECT COUNT(*)
            FROM insumos
            WHERE estado = 'Activo'
              AND stock_actual <= stock_minimo
        """)

        indicadores["insumos_bajo_stock"] = int(cursor.fetchone()[0] or 0)

        # VENTAS DE LOS ÚLTIMOS 7 DÍAS

        cursor.execute("""
            SELECT
                DATE(fecha_venta),
                COALESCE(SUM(total), 0)
            FROM ventas
            WHERE fecha_venta >= CURDATE() - INTERVAL 6 DAY
              AND fecha_venta < CURDATE() + INTERVAL 1 DAY
              AND estado = 'Completada'
            GROUP BY DATE(fecha_venta)
            ORDER BY DATE(fecha_venta)
        """)

        resultados = cursor.fetchall()

        ventas_por_dia = {
            fila[0]: float(fila[1] or 0)
            for fila in resultados
        }

        nombres_dias = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
        hoy = datetime.now().date()

        for desplazamiento in range(6, -1, -1):

            dia = hoy - timedelta(days=desplazamiento)

            ventas_semana.append({
                "fecha": dia,
                "dia": nombres_dias[dia.weekday()],
                "total": ventas_por_dia.get(dia, 0)
            })

        maximo_ventas = max(
            (v["total"] for v in ventas_semana),
            default=0
        )

        for venta in ventas_semana:

            venta["altura"] = (
                max(5, venta["total"] / maximo_ventas * 100)
                if maximo_ventas > 0 else 5
            )

        # ESTADO DE LAS MESAS

        cursor.execute("""
            SELECT COUNT(*)
            FROM mesas
            WHERE estado = 'Activa'
        """)

        mesas["total"] = int(cursor.fetchone()[0] or 0)

        cursor.execute("""
            SELECT COUNT(DISTINCT r.id_mesa)
            FROM reservaciones r
            INNER JOIN mesas m ON r.id_mesa = m.id_mesa
            WHERE r.fecha = CURDATE()
              AND r.estado = 'Reservada'
              AND m.estado = 'Activa'
        """)

        mesas["ocupadas"] = int(cursor.fetchone()[0] or 0)

        mesas["disponibles"] = max(
            0,
            mesas["total"] - mesas["ocupadas"]
        )

        # PRODUCTOS MÁS VENDIDOS

        cursor.execute("""
            SELECT
                p.nombre,
                SUM(dv.cantidad) AS total_vendido
            FROM detalle_ventas dv
            INNER JOIN ventas v ON dv.id_venta = v.id_venta
            INNER JOIN productos p ON dv.id_producto = p.id_producto
            WHERE v.estado = 'Completada'
            GROUP BY p.id_producto, p.nombre
            ORDER BY total_vendido DESC
            LIMIT 3
        """)

        productos_vendidos = [
            {
                "nombre": fila[0],
                "cantidad": int(fila[1] or 0)
            }
            for fila in cursor.fetchall()
        ]

        # ACTIVIDAD DEL DÍA: VENTAS

        cursor.execute("""
            SELECT v.fecha_venta, u.nombre
            FROM ventas v
            INNER JOIN usuarios u ON v.id_usuario = u.id_usuario
            WHERE DATE(v.fecha_venta) = CURDATE()
              AND v.estado = 'Completada'
            ORDER BY v.fecha_venta DESC
            LIMIT 10
        """)

        for fila in cursor.fetchall():

            actividad.append({
                "fecha": fila[0],
                "tipo": "venta",
                "mensaje": f"Venta registrada por {fila[1]}"
            })

        # ACTIVIDAD DEL DÍA: RESERVACIONES

        cursor.execute("""
            SELECT r.fecha_registro, c.nombre, m.nombre_mesa
            FROM reservaciones r
            INNER JOIN clientes c ON r.id_cliente = c.id_cliente
            INNER JOIN mesas m ON r.id_mesa = m.id_mesa
            WHERE DATE(r.fecha_registro) = CURDATE()
              AND r.estado = 'Reservada'
            ORDER BY r.fecha_registro DESC
            LIMIT 10
        """)

        for fila in cursor.fetchall():

            actividad.append({
                "fecha": fila[0],
                "tipo": "reservacion",
                "mensaje": f"Nueva reservación de {fila[1]} - {fila[2]}"
            })

        # ACTIVIDAD DEL DÍA: INVENTARIO

        cursor.execute("""
            SELECT
                mi.fecha_movimiento,
                mi.tipo_movimiento,
                mi.cantidad,
                i.nombre
            FROM movimientos_inventario mi
            INNER JOIN insumos i ON mi.id_insumo = i.id_insumo
            WHERE DATE(mi.fecha_movimiento) = CURDATE()
            ORDER BY mi.fecha_movimiento DESC
            LIMIT 10
        """)

        for fila in cursor.fetchall():

            if fila[1] == "Entrada":
                mensaje = f"Entrada de inventario: {fila[3]} ({fila[2]} unidades)"

            elif fila[1] == "Salida":
                mensaje = f"Salida de inventario: {fila[3]} ({fila[2]} unidades)"

            else:
                mensaje = f"Ajuste de inventario: {fila[3]} ({fila[2]} unidades)"

            actividad.append({
                "fecha": fila[0],
                "tipo": "inventario",
                "mensaje": mensaje
            })

        # ORDENAR ACTIVIDAD

        actividad.sort(
            key=lambda elemento: elemento["fecha"] or datetime.min,
            reverse=True
        )

        actividad = actividad[:5]

        for elemento in actividad:
            elemento["hora"] = elemento["fecha"].strftime("%H:%M")

    except Exception as error:

        print("ERROR AL CARGAR DASHBOARD:", repr(error))

        flash(
            "No fue posible actualizar toda la información del panel.",
            "error"
        )

    finally:

        if cursor:
            cursor.close()

        if conexion:
            conexion.close()

    return render_template(
        "admin/dashboard.html",
        nombre=session.get("nombre", session.get("username", "Usuario")),
        rol=rol,
        menu=MENUS_ROLES[rol],
        indicadores=indicadores,
        ventas_semana=ventas_semana,
        mesas=mesas,
        productos_vendidos=productos_vendidos,
        actividad=actividad
    )


# ==========================================
# VENTAS DEL ADMINISTRADOR
# ==========================================

@administrativo_bp.route("/admin/ventas")
def ventas_administrador():

    if "id_usuario" not in session:
        return redirect(url_for("login.login"))

    rol = session.get("rol", "")

    if rol not in ["Administrador", "Gerente"]:
        flash("No tienes permiso para acceder a esta sección.", "error")
        return redirect(url_for("login.login"))

    return render_template(
        "admin/ventas.html",
        nombre=session.get("nombre", session.get("username", "Usuario")),
        rol=rol,
        menu=MENUS_ROLES[rol]
    )


# ==========================================
# API DE VENTAS DEL ADMINISTRADOR
# ==========================================

@administrativo_bp.route("/admin/api/ventas")
def api_ventas_administrador():

    if "id_usuario" not in session:
        return jsonify({
            "ok": False,
            "mensaje": "Sesión no válida."
        }), 401

    rol = str(session.get("rol", "")).strip().lower()

    if rol not in ["Administrador", "gerente"]:
        return jsonify({
            "ok": False,
            "mensaje": "No tienes permiso."
        }), 403

    periodo = request.args.get("periodo", "hoy").lower()
    ahora = datetime.now()

    if periodo == "semana":

        desde = (ahora - timedelta(days=ahora.weekday())).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0
        )

    elif periodo == "mes":

        desde = ahora.replace(
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0
        )

    else:

        desde = ahora.replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0
        )

    hasta = ahora + timedelta(seconds=1)

    conexion = None
    cursor = None

    try:

        conexion = obtener_conexion()

        if conexion is None:
            raise Exception("No se pudo conectar con MySQL.")

        cursor = conexion.cursor()

        # INDICADORES DE VENTAS COMPLETADAS

        cursor.execute("""
            SELECT
                COALESCE(SUM(total), 0),
                COUNT(*)
            FROM ventas
            WHERE estado = 'Completada'
              AND fecha_venta >= %s
              AND fecha_venta < %s
        """, (desde, hasta))

        fila = cursor.fetchone()

        total_ventas = float(fila[0] or 0)
        numero_ventas = int(fila[1] or 0)

        # PRODUCTOS VENDIDOS

        cursor.execute("""
            SELECT COALESCE(SUM(dv.cantidad), 0)
            FROM detalle_ventas dv
            INNER JOIN ventas v ON v.id_venta = dv.id_venta
            WHERE v.estado = 'Completada'
              AND v.fecha_venta >= %s
              AND v.fecha_venta < %s
        """, (desde, hasta))

        productos_vendidos = int(cursor.fetchone()[0] or 0)

        # CUENTAS ABIERTAS

        cursor.execute("""
            SELECT COUNT(*)
            FROM ventas
            WHERE estado = 'Abierta'
        """)

        cuentas_abiertas = int(cursor.fetchone()[0] or 0)

        # VENTAS POR HORA

        cursor.execute("""
            SELECT
                HOUR(fecha_venta),
                COALESCE(SUM(total), 0)
            FROM ventas
            WHERE estado = 'Completada'
              AND fecha_venta >= %s
              AND fecha_venta < %s
            GROUP BY HOUR(fecha_venta)
            ORDER BY HOUR(fecha_venta)
        """, (desde, hasta))

        ventas_hora = {
            int(fila[0]): float(fila[1] or 0)
            for fila in cursor.fetchall()
        }

        # MÉTODOS DE PAGO

        try:

            cursor.execute("""
                SELECT
                    p.metodo_pago,
                    COALESCE(SUM(p.monto), 0)
                FROM pagos_venta p
                INNER JOIN ventas v ON v.id_venta = p.id_venta
                WHERE v.estado = 'Completada'
                  AND v.fecha_venta >= %s
                  AND v.fecha_venta < %s
                GROUP BY p.metodo_pago
            """, (desde, hasta))

            filas_pagos = cursor.fetchall()

        except Exception:

            conexion.rollback()

            cursor.execute("""
                SELECT
                    metodo_pago,
                    COALESCE(SUM(total), 0)
                FROM ventas
                WHERE estado = 'Completada'
                  AND fecha_venta >= %s
                  AND fecha_venta < %s
                GROUP BY metodo_pago
            """, (desde, hasta))

            filas_pagos = cursor.fetchall()

        pagos = [
            {
                "metodo": fila[0] or "No especificado",
                "total": float(fila[1] or 0)
            }
            for fila in filas_pagos
        ]

        # TOP 5 PRODUCTOS MÁS VENDIDOS

        cursor.execute("""
            SELECT
                p.id_producto,
                p.nombre,
                p.imagen,
                COALESCE(SUM(dv.cantidad), 0) AS cantidad
            FROM detalle_ventas dv
            INNER JOIN ventas v ON v.id_venta = dv.id_venta
            INNER JOIN productos p ON p.id_producto = dv.id_producto
            WHERE v.estado = 'Completada'
              AND v.fecha_venta >= %s
              AND v.fecha_venta < %s
            GROUP BY p.id_producto, p.nombre, p.imagen
            ORDER BY cantidad DESC
            LIMIT 5
        """, (desde, hasta))

        top_productos = [
            {
                "id_producto": fila[0],
                "nombre": fila[1],
                "imagen": fila[2],
                "cantidad": int(fila[3] or 0)
            }
            for fila in cursor.fetchall()
        ]

        # CUENTAS ABIERTAS

        cursor.execute("""
            SELECT
                v.id_venta,
                v.tipo_cuenta,
                v.folio,
                v.nombre_cliente,
                v.total,
                v.fecha_venta,
                m.nombre_mesa
            FROM ventas v
            LEFT JOIN mesas m ON m.id_mesa = v.id_mesa
            WHERE v.estado = 'Abierta'
            ORDER BY v.fecha_venta ASC
        """)

        cuentas = []

        for fila in cursor.fetchall():

            cuentas.append({
                "id_venta": fila[0],
                "tipo_cuenta": fila[1] or "Barra",
                "folio": fila[2],
                "nombre_cliente": fila[3],
                "total": float(fila[4] or 0),
                "fecha_venta": (
                    fila[5].strftime("%Y-%m-%d %H:%M:%S")
                    if fila[5] else None
                ),
                "nombre_mesa": fila[6]
            })

        # ÚLTIMAS VENTAS

        cursor.execute("""
            SELECT
                v.id_venta,
                v.folio,
                v.tipo_cuenta,
                v.total,
                v.metodo_pago,
                u.nombre,
                v.fecha_venta,
                m.nombre_mesa
            FROM ventas v
            INNER JOIN usuarios u ON u.id_usuario = v.id_usuario
            LEFT JOIN mesas m ON m.id_mesa = v.id_mesa
            WHERE v.estado = 'Completada'
              AND v.fecha_venta >= %s
              AND v.fecha_venta < %s
            ORDER BY v.fecha_venta DESC
            LIMIT 10
        """, (desde, hasta))

        ultimas_ventas = []

        for fila in cursor.fetchall():

            ultimas_ventas.append({
                "id_venta": fila[0],
                "folio": fila[1],
                "tipo_cuenta": fila[2] or "Barra",
                "total": float(fila[3] or 0),
                "metodo_pago": fila[4] or "No registrado",
                "empleado": fila[5],
                "hora": fila[6].strftime("%H:%M") if fila[6] else "",
                "nombre_mesa": fila[7]
            })

        return jsonify({
            "ok": True,

            "indicadores": {
                "ventas_dia": total_ventas,
                "numero_ventas": numero_ventas,
                "productos_vendidos": productos_vendidos,
                "cuentas_abiertas": cuentas_abiertas
            },

            "ventas_hora": ventas_hora,
            "pagos": pagos,
            "top_productos": top_productos,
            "cuentas": cuentas,
            "ultimas_ventas": ultimas_ventas
        })

    except Exception as error:

        print("ERROR API VENTAS ADMIN:", repr(error))

        return jsonify({
            "ok": False,
            "mensaje": "No fue posible consultar las ventas.",
            "error": str(error)
        }), 500

    finally:

        if cursor:
            cursor.close()

        if conexion:
            conexion.close()

# ==========================================
# PANEL ADMINISTRATIVO DE RESERVACIONES
# ==========================================

@administrativo_bp.route("/admin/reservaciones")
def reservaciones_administrador():

    if "id_usuario" not in session:
        return redirect(url_for("login.login"))

    rol = str(session.get("rol", "")).strip().lower()

    if rol not in ["administrador", "gerente"]:
        flash("No tienes permiso para acceder.", "error")
        return redirect(url_for("login.login"))

    return render_template(
        "admin/reservaciones.html",
        nombre=session.get("nombre", session.get("username", "Usuario")),
        rol=session.get("rol"),
        menu=MENUS_ROLES.get(session.get("rol"), MENUS_ROLES["Administrador"])
    )


# ==========================================
# API: CONSULTAR RESERVACIONES
# ==========================================

@administrativo_bp.route("/admin/api/reservaciones")
def api_reservaciones_administrador():

    if "id_usuario" not in session:
        return jsonify({"ok": False, "mensaje": "Sesión no válida."}), 401

    rol = str(session.get("rol", "")).strip().lower()

    if rol not in ["administrador", "gerente"]:
        return jsonify({"ok": False, "mensaje": "Sin autorización."}), 403

    conexion = None
    cursor = None

    try:
        fecha = request.args.get("fecha", datetime.now().strftime("%Y-%m-%d"))
        mes = request.args.get("mes", datetime.now().strftime("%Y-%m"))
        filtro = request.args.get("filtro", "todas")

        conexion = obtener_conexion()
        cursor = conexion.cursor()

        # Indicadores del día
        cursor.execute("""
            SELECT
                COUNT(*),
                COALESCE(SUM(numero_personas), 0),
                COUNT(DISTINCT id_mesa),
                SUM(CASE WHEN estado = 'Reservada' THEN 1 ELSE 0 END)
            FROM reservaciones
            WHERE fecha = %s
              AND estado IN ('Reservada', 'Confirmada', 'En curso')
        """, (fecha,))

        indicadores = cursor.fetchone()

        # Reservaciones del día seleccionado
        sql = """
            SELECT
                r.id_reservacion,
                r.fecha,
                r.hora,
                r.numero_personas,
                r.observaciones,
                r.estado,
                c.nombre,
                c.telefono,
                c.correo,
                m.id_mesa,
                m.nombre_mesa,
                m.capacidad,
                m.tipo
            FROM reservaciones r
            INNER JOIN clientes c ON c.id_cliente = r.id_cliente
            INNER JOIN mesas m ON m.id_mesa = r.id_mesa
            WHERE r.fecha = %s
        """

        parametros = [fecha]

        if filtro == "activas":
            sql += " AND r.estado IN ('Reservada', 'Confirmada', 'En curso')"
        elif filtro == "historial":
            sql += " AND r.estado = 'Finalizada'"
        elif filtro == "canceladas":
            sql += " AND r.estado = 'Cancelada'"

        sql += " ORDER BY r.hora ASC"

        cursor.execute(sql, parametros)

        reservaciones = []

        for fila in cursor.fetchall():
            reservaciones.append({
                "id": fila[0],
                "fecha": fila[1].strftime("%Y-%m-%d"),
                "hora": str(fila[2])[:5],
                "personas": fila[3],
                "observaciones": fila[4] or "",
                "estado": fila[5],
                "cliente": fila[6],
                "telefono": fila[7] or "",
                "correo": fila[8] or "",
                "id_mesa": fila[9],
                "mesa": fila[10],
                "capacidad": fila[11],
                "tipo_mesa": fila[12] or ""
            })

        # Mesas y su disponibilidad para la fecha seleccionada
        cursor.execute("""
            SELECT
                m.id_mesa,
                m.nombre_mesa,
                m.capacidad,
                m.tipo,
                CASE
                    WHEN EXISTS (
                        SELECT 1
                        FROM reservaciones r
                        WHERE r.id_mesa = m.id_mesa
                          AND r.fecha = %s
                          AND r.estado = 'En curso'
                    ) THEN 'Ocupada'
                    WHEN EXISTS (
                        SELECT 1
                        FROM reservaciones r
                        WHERE r.id_mesa = m.id_mesa
                          AND r.fecha = %s
                          AND r.estado IN ('Reservada', 'Confirmada')
                    ) THEN 'Reservada'
                    ELSE 'Disponible'
                END AS disponibilidad
            FROM mesas m
            WHERE m.estado = 'Activa'
            ORDER BY m.id_mesa
        """, (fecha, fecha))

        mesas = [{
            "id": fila[0],
            "nombre": fila[1],
            "capacidad": fila[2],
            "tipo": fila[3] or "",
            "estado": fila[4]
        } for fila in cursor.fetchall()]

        # Calendario: días con reservaciones en el mes
        cursor.execute("""
            SELECT fecha, COUNT(*)
            FROM reservaciones
            WHERE DATE_FORMAT(fecha, '%Y-%m') = %s
              AND estado IN ('Reservada', 'Confirmada', 'En curso')
            GROUP BY fecha
        """, (mes,))

        calendario = {
            fila[0].strftime("%Y-%m-%d"): int(fila[1])
            for fila in cursor.fetchall()
        }

        return jsonify({
            "ok": True,
            "indicadores": {
                "reservaciones": int(indicadores[0] or 0),
                "personas": int(indicadores[1] or 0),
                "mesas": int(indicadores[2] or 0),
                "pendientes": int(indicadores[3] or 0)
            },
            "reservaciones": reservaciones,
            "mesas": mesas,
            "calendario": calendario
        })

    except Exception as error:
        print("ERROR API RESERVACIONES:", repr(error))
        return jsonify({
            "ok": False,
            "mensaje": "No se pudieron consultar las reservaciones.",
            "error": str(error)
        }), 500

    finally:
        if cursor:
            cursor.close()
        if conexion:
            conexion.close()


# ==========================================
# API: CAMBIAR ESTADO DE RESERVACIÓN
# ==========================================

@administrativo_bp.route(
    "/admin/api/reservaciones/<int:id_reservacion>/estado",
    methods=["POST"]
)
def cambiar_estado_reservacion_admin(id_reservacion):

    if "id_usuario" not in session:
        return jsonify({"ok": False, "mensaje": "Sesión no válida."}), 401

    rol = str(session.get("rol", "")).strip().lower()

    if rol not in ["administrador", "gerente"]:
        return jsonify({"ok": False, "mensaje": "Sin autorización."}), 403

    datos = request.get_json(silent=True) or {}
    estado = datos.get("estado", "").strip()

    permitidos = ["Confirmada", "En curso", "Finalizada", "Cancelada"]

    if estado not in permitidos:
        return jsonify({"ok": False, "mensaje": "Estado no válido."}), 400

    conexion = None
    cursor = None

    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()

        cursor.execute("""
            SELECT estado
            FROM reservaciones
            WHERE id_reservacion = %s
        """, (id_reservacion,))

        actual = cursor.fetchone()

        if not actual:
            return jsonify({"ok": False, "mensaje": "Reservación no encontrada."}), 404

        if actual[0] in ["Finalizada", "Cancelada"]:
            return jsonify({
                "ok": False,
                "mensaje": "La reservación ya está cerrada."
            }), 400

        cursor.execute("""
            UPDATE reservaciones
            SET estado = %s
            WHERE id_reservacion = %s
        """, (estado, id_reservacion))

        conexion.commit()

        mensajes = {
            "Confirmada": "Reservación confirmada.",
            "En curso": "La mesa ahora aparece como ocupada.",
            "Finalizada": "Reservación finalizada. La mesa quedó liberada.",
            "Cancelada": "Reservación cancelada. La mesa quedó liberada."
        }

        return jsonify({
            "ok": True,
            "mensaje": mensajes[estado]
        })

    except Exception as error:
        if conexion:
            conexion.rollback()

        print("ERROR CAMBIANDO ESTADO:", repr(error))
        return jsonify({"ok": False, "mensaje": str(error)}), 500

    finally:
        if cursor:
            cursor.close()
        if conexion:
            conexion.close()

# ==========================================
# API: CREAR RESERVACIÓN DESDE ADMINISTRACIÓN
# ==========================================

@administrativo_bp.route(
    "/admin/api/reservaciones/crear",
    methods=["POST"]
)
def crear_reservacion_admin():

    if "id_usuario" not in session:
        return jsonify({"ok": False, "mensaje": "Sesión no válida."}), 401

    rol = str(session.get("rol", "")).strip().lower()

    if rol not in ["administrador", "gerente"]:
        return jsonify({"ok": False, "mensaje": "Sin autorización."}), 403

    datos = request.get_json(silent=True) or {}

    nombre = str(datos.get("nombre_cliente", "")).strip()
    correo = str(datos.get("correo", "")).strip()
    telefono = str(datos.get("telefono", "")).strip()
    fecha = str(datos.get("fecha", "")).strip()
    hora = str(datos.get("hora", "")).strip()
    observaciones = str(datos.get("observaciones", "")).strip()

    try:
        personas = int(datos.get("numero_personas"))
        id_mesa = int(datos.get("id_mesa"))
        fecha_reserva = datetime.strptime(fecha, "%Y-%m-%d").date()

        hora_reserva = datetime.strptime(hora, "%H:%M").time()

        hora_minima = datetime.strptime("19:00", "%H:%M").time()
        hora_maxima = datetime.strptime("22:00", "%H:%M").time()

        if not hora_minima <= hora_reserva <= hora_maxima:
            return jsonify({
                "ok": False,
                "mensaje": "Las reservaciones solo están permitidas de 19:00 a 22:00."
            }), 400
    except (ValueError, TypeError):
        return jsonify({"ok": False, "mensaje": "Verifica fecha, hora, mesa y número de personas."}), 400

    if not all([nombre, correo, telefono]):
        return jsonify({"ok": False, "mensaje": "Completa los datos del cliente."}), 400

    if fecha_reserva < datetime.now().date():
        return jsonify({"ok": False, "mensaje": "No puedes reservar fechas anteriores."}), 400

    if personas < 1 or personas > 8:
        return jsonify({"ok": False, "mensaje": "El número de personas debe ser de 1 a 8."}), 400

    conexion = None
    cursor = None

    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()

        cursor.execute("""
            SELECT nombre_mesa, capacidad, estado
            FROM mesas
            WHERE id_mesa = %s
        """, (id_mesa,))

        mesa = cursor.fetchone()

        if not mesa:
            return jsonify({"ok": False, "mensaje": "La mesa no existe."}), 404

        if mesa[2] != "Activa":
            return jsonify({"ok": False, "mensaje": "La mesa no está activa."}), 400

        if personas > mesa[1]:
            return jsonify({
                "ok": False,
                "mensaje": f"{mesa[0]} tiene capacidad para {mesa[1]} personas."
            }), 400

        cursor.execute("""
            SELECT id_reservacion
            FROM reservaciones
            WHERE id_mesa = %s
              AND fecha = %s
              AND estado IN ('Reservada', 'Confirmada', 'En curso')
            LIMIT 1
        """, (id_mesa, fecha_reserva))

        if cursor.fetchone():
            return jsonify({
                "ok": False,
                "mensaje": "La mesa ya tiene una reservación activa para esa fecha."
            }), 409

        cursor.execute("""
            SELECT id_cliente
            FROM clientes
            WHERE correo = %s
            LIMIT 1
        """, (correo,))

        cliente = cursor.fetchone()

        if cliente:
            id_cliente = cliente[0]

            cursor.execute("""
                UPDATE clientes
                SET nombre = %s, telefono = %s
                WHERE id_cliente = %s
            """, (nombre, telefono, id_cliente))

        else:
            cursor.execute("""
                INSERT INTO clientes (nombre, correo, telefono)
                VALUES (%s, %s, %s)
            """, (nombre, correo, telefono))

            id_cliente = cursor.lastrowid

        cursor.execute("""
            INSERT INTO reservaciones (
                id_cliente,
                id_mesa,
                fecha,
                hora,
                numero_personas,
                observaciones,
                estado
            )
            VALUES (%s, %s, %s, %s, %s, %s, 'Reservada')
        """, (
            id_cliente,
            id_mesa,
            fecha_reserva,
            hora,
            personas,
            observaciones
        ))

                
        id_reservacion = cursor.lastrowid

        # Guardar definitivamente la reservación
        conexion.commit()

        print("RESERVACIÓN ADMINISTRATIVA GUARDADA:", id_reservacion)

        # ==========================================
        # GENERAR PDF Y ENVIAR CORREO AL CLIENTE
        # ==========================================

        correo_enviado = False
        mensaje = "Reservación registrada correctamente."

        datos_reserva = {
            "id_reservacion": id_reservacion,
            "nombre_cliente": nombre,
            "correo": correo,
            "telefono": telefono,
            "fecha": fecha_reserva,
            "hora": hora,
            "numero_personas": personas,
            "nombre_mesa": mesa[0],
            "observaciones": observaciones
        }

        try:

            # Generar comprobante PDF
            pdf = generar_pdf_reservacion(datos_reserva)

            print("PDF DE RESERVACIÓN ADMIN GENERADO.")

            # Enviar comprobante al correo del cliente
            enviar_correo_reservacion(
                correo,
                nombre,
                pdf
            )

            correo_enviado = True

            mensaje = (
                "Reservación registrada correctamente. "
                "El comprobante PDF fue enviado al correo del cliente."
            )

            print("CORREO ENVIADO CORRECTAMENTE A:", correo)

        except Exception as error:

            print(
                "ERROR AL GENERAR O ENVIAR CORREO DE RESERVACIÓN ADMIN:",
                repr(error)
            )

            mensaje = (
                "La reservación se registró correctamente, "
                "pero no fue posible enviar el comprobante por correo."
            )

        return jsonify({
            "ok": True,
            "mensaje": mensaje,
            "id_reservacion": id_reservacion,
            "correo_enviado": correo_enviado
        })


    except Exception as error:
        if conexion:
            conexion.rollback()

        print("ERROR CREANDO RESERVACIÓN ADMIN:", repr(error))

        return jsonify({
            "ok": False,
            "mensaje": "No fue posible registrar la reservación.",
            "error": str(error)
        }), 500

    finally:
        if cursor:
            cursor.close()

        if conexion:
            conexion.close()
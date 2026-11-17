from flask import Blueprint, render_template, session, redirect, url_for, flash
from models.conexion import obtener_conexion
from datetime import datetime, timedelta


administrativo_bp = Blueprint("administrativo", __name__)


# ==========================================
# MENÚS SEGÚN EL ROL
# ==========================================

MENUS_ROLES = {

    "Administrador": [
        {"nombre": "Inicio", "icono": "bi-house-door", "url": "#"},
        {"nombre": "Usuarios", "icono": "bi-people", "url": "/usuarios/"},
        {"nombre": "Almacén", "icono": "bi-box-seam", "url": "/almacen/"},
        {"nombre": "Ventas", "icono": "bi-cash-stack", "url": "/admin/ventas/"},
        {"nombre": "Reservaciones", "icono": "bi-calendar-check", "url": "#"},
        {"nombre": "Recetas", "icono": "bi-journal-text", "url": "/recetas/"},
        {"nombre": "Compras", "icono": "bi-cart3", "url": "#"},
        {"nombre": "Reportes", "icono": "bi-bar-chart", "url": "#"},
        {"nombre": "Configuración", "icono": "bi-gear", "url": "#"}
    ],

    "Gerente": [
        {"nombre": "Inicio", "icono": "bi-house-door", "url": "#"},
        {"nombre": "Personal", "icono": "bi-people", "url": "#"},
        {"nombre": "Ventas", "icono": "bi-cash-stack", "url": "#"},
        {"nombre": "Reservaciones", "icono": "bi-calendar-check", "url": "#"},
        {"nombre": "Almacén", "icono": "bi-box-seam", "url": "#"},
        {"nombre": "Reportes", "icono": "bi-bar-chart", "url": "#"}
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
        {"nombre": "Recetas", "icono": "bi-journal-text", "url": "#"}
    ],

    "Recepcionista": [
        {"nombre": "Inicio", "icono": "bi-house-door", "url": "#"},
        {"nombre": "Reservaciones", "icono": "bi-calendar-check", "url": "#"},
        {"nombre": "Plano de mesas", "icono": "bi-grid-3x3", "url": "#"},
        {"nombre": "Registro de clientes", "icono": "bi-person-plus", "url": "#"}
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

        # ==================================
        # INDICADORES PRINCIPALES
        # ==================================

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


        # ==================================
        # VENTAS DE LOS ÚLTIMOS 7 DÍAS
        # ==================================

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


        # ==================================
        # ESTADO DE LAS MESAS
        # ==================================

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


        # ==================================
        # PRODUCTOS MÁS VENDIDOS
        # ==================================

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


        # ==================================
        # ACTIVIDAD DEL DÍA: VENTAS
        # ==================================

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


        # ==================================
        # ACTIVIDAD DEL DÍA: RESERVACIONES
        # ==================================

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


        # ==================================
        # ACTIVIDAD DEL DÍA: INVENTARIO
        # ==================================

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


        # ==================================
        # ORDENAR ACTIVIDAD
        # ==================================

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

    if rol != "Administrador":
        flash("No tienes permiso para acceder a esta sección.", "error")
        return redirect(url_for("login.login"))

    return render_template(
        "admin/ventas.html",
        nombre=session.get("nombre", session.get("username", "Usuario")),
        rol=rol,
        menu=MENUS_ROLES[rol]
    )
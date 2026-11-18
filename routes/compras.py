
from flask import (
    Blueprint,
    render_template,
    request,
    session,
    redirect,
    url_for,
    flash,
    jsonify
)

from models.conexion import obtener_conexion
from datetime import datetime

# Reutilizar el menú definido en administrativo.py
from routes.administrativo import MENUS_ROLES


# ==========================================
# BLUEPRINT DE COMPRAS
# ==========================================

compras_bp = Blueprint("compras", __name__)


# ==========================================
# VALIDAR ACCESO DEL ADMINISTRADOR
# ==========================================

def validar_administrador():

    if "id_usuario" not in session:
        return False

    rol = str(session.get("rol", "")).strip().lower()

    return rol == "administrador"


# ==========================================
# PANTALLA DE REPORTES DE COMPRAS
# ==========================================

@compras_bp.route("/admin/reportes/compras")
def reportes_compras():

    if "id_usuario" not in session:
        return redirect(url_for("login.login"))

    rol = session.get("rol", "")

    if not validar_administrador():
        flash("No tienes permiso para acceder.", "error")
        return redirect(url_for("login.login"))

    return render_template(
        "admin/reportes_compras.html",
        nombre=session.get(
            "nombre",
            session.get("username", "Usuario")
        ),
        rol=rol,
        menu=MENUS_ROLES.get(rol, [])
    )


# ==========================================
# API: DATOS Y ESTADÍSTICAS DE COMPRAS
# ==========================================

@compras_bp.route("/admin/api/reportes/compras")
def api_reportes_compras():

    if "id_usuario" not in session:
        return jsonify({
            "ok": False,
            "mensaje": "Sesión no válida."
        }), 401

    if not validar_administrador():
        return jsonify({
            "ok": False,
            "mensaje": "No tienes autorización."
        }), 403

    conexion = None
    cursor = None

    try:

        # ==================================
        # RECIBIR FILTROS
        # ==================================

        hoy = datetime.now().date()
        primer_dia = hoy.replace(day=1)

        desde = request.args.get(
            "desde",
            primer_dia.strftime("%Y-%m-%d")
        )

        hasta = request.args.get(
            "hasta",
            hoy.strftime("%Y-%m-%d")
        )

        id_proveedor = request.args.get(
            "proveedor",
            ""
        ).strip()

        estado = request.args.get(
            "estado",
            ""
        ).strip()

        fecha_desde = datetime.strptime(
            desde,
            "%Y-%m-%d"
        ).date()

        fecha_hasta = datetime.strptime(
            hasta,
            "%Y-%m-%d"
        ).date()

        if fecha_desde > fecha_hasta:
            return jsonify({
                "ok": False,
                "mensaje": "La fecha inicial no puede ser posterior a la final."
            }), 400

        if id_proveedor:
            id_proveedor = int(id_proveedor)

        estados_permitidos = [
            "Registrada",
            "Pendiente",
            "Cancelada"
        ]

        if estado and estado not in estados_permitidos:
            return jsonify({
                "ok": False,
                "mensaje": "El estado seleccionado no es válido."
            }), 400

        # ==================================
        # CONEXIÓN A MYSQL
        # ==================================

        conexion = obtener_conexion()

        if conexion is None:
            raise Exception("No se pudo conectar con MySQL.")

        cursor = conexion.cursor()

        # ==================================
        # CONSTRUIR FILTROS
        # ==================================

        condiciones = [
            "c.fecha_compra >= %s",
            "c.fecha_compra < DATE_ADD(%s, INTERVAL 1 DAY)"
        ]

        parametros = [
            fecha_desde,
            fecha_hasta
        ]

        if id_proveedor:

            condiciones.append(
                "c.id_proveedor = %s"
            )

            parametros.append(id_proveedor)

        if estado:

            condiciones.append(
                "c.estado = %s"
            )

            parametros.append(estado)

        where_sql = " AND ".join(condiciones)

        # ==================================
        # INDICADORES GENERALES
        # ==================================

        cursor.execute(f"""
            SELECT
                COUNT(DISTINCT c.id_compra),

                COALESCE(SUM(
                    CASE
                        WHEN c.estado = 'Registrada'
                        THEN c.total
                        ELSE 0
                    END
                ), 0),

                COALESCE(SUM(
                    CASE
                        WHEN c.estado = 'Pendiente'
                        THEN 1
                        ELSE 0
                    END
                ), 0)

            FROM compras c

            WHERE {where_sql}

        """, tuple(parametros))

        fila = cursor.fetchone()

        total_compras = int(fila[0] or 0)
        gasto_total = float(fila[1] or 0)
        compras_pendientes = int(fila[2] or 0)

        # ==================================
        # CANTIDAD DE INSUMOS COMPRADOS
        # ==================================

        cursor.execute(f"""
            SELECT
                COALESCE(SUM(dc.cantidad), 0)

            FROM compras c

            INNER JOIN detalle_compras dc
                ON dc.id_compra = c.id_compra

            WHERE {where_sql}

              AND c.estado = 'Registrada'

        """, tuple(parametros))

        insumos_comprados = float(
            cursor.fetchone()[0] or 0
        )

        # ==================================
        # COMPRAS POR MES
        # ==================================

        cursor.execute(f"""
            SELECT
                DATE_FORMAT(
                    c.fecha_compra,
                    '%Y-%m'
                ),

                COALESCE(SUM(
                    CASE
                        WHEN c.estado = 'Registrada'
                        THEN c.total
                        ELSE 0
                    END
                ), 0)

            FROM compras c

            WHERE {where_sql}

            GROUP BY
                DATE_FORMAT(c.fecha_compra, '%Y-%m')

            ORDER BY
                DATE_FORMAT(c.fecha_compra, '%Y-%m')

        """, tuple(parametros))

        compras_por_mes = [
            {
                "mes": fila[0],
                "total": float(fila[1] or 0)
            }
            for fila in cursor.fetchall()
        ]

        # ==================================
        # GASTOS POR PROVEEDOR
        # ==================================

        cursor.execute(f"""
            SELECT
                p.nombre,

                COALESCE(SUM(
                    CASE
                        WHEN c.estado = 'Registrada'
                        THEN c.total
                        ELSE 0
                    END
                ), 0)

            FROM compras c

            INNER JOIN proveedores p
                ON p.id_proveedor = c.id_proveedor

            WHERE {where_sql}

            GROUP BY
                p.id_proveedor,
                p.nombre

            ORDER BY 2 DESC

            LIMIT 10

        """, tuple(parametros))

        gasto_proveedores = [
            {
                "proveedor": fila[0],
                "total": float(fila[1] or 0)
            }
            for fila in cursor.fetchall()
        ]

        # ==================================
        # INSUMOS MÁS COMPRADOS
        # ==================================

        cursor.execute(f"""
            SELECT
                i.nombre,

                COALESCE(SUM(dc.cantidad), 0),

                COALESCE(SUM(
                    dc.cantidad * dc.costo_unitario
                ), 0)

            FROM compras c

            INNER JOIN detalle_compras dc
                ON dc.id_compra = c.id_compra

            INNER JOIN insumos i
                ON i.id_insumo = dc.id_insumo

            WHERE {where_sql}

              AND c.estado = 'Registrada'

            GROUP BY
                i.id_insumo,
                i.nombre

            ORDER BY 2 DESC

            LIMIT 10

        """, tuple(parametros))

        insumos_top = [
            {
                "nombre": fila[0],
                "cantidad": float(fila[1] or 0),
                "importe": float(fila[2] or 0)
            }
            for fila in cursor.fetchall()
        ]

        # ==================================
        # HISTORIAL DE COMPRAS
        # ==================================

        cursor.execute(f"""
            SELECT
                c.id_compra,
                p.nombre,
                c.fecha_compra,
                c.total,
                c.estado,

                COUNT(
                    DISTINCT dc.id_detalle_compra
                ),

                COALESCE(
                    SUM(dc.cantidad),
                    0
                )

            FROM compras c

            INNER JOIN proveedores p
                ON p.id_proveedor = c.id_proveedor

            LEFT JOIN detalle_compras dc
                ON dc.id_compra = c.id_compra

            WHERE {where_sql}

            GROUP BY
                c.id_compra,
                p.nombre,
                c.fecha_compra,
                c.total,
                c.estado

            ORDER BY
                c.fecha_compra DESC,
                c.id_compra DESC

        """, tuple(parametros))

        historial = []

        for fila in cursor.fetchall():

            historial.append({
                "id_compra": fila[0],

                "folio": f"C-{int(fila[0]):05d}",

                "proveedor": fila[1],

                "fecha": (
                    fila[2].strftime("%Y-%m-%d")
                    if fila[2]
                    else ""
                ),

                "total": float(fila[3] or 0),

                "estado": fila[4],

                "productos": int(fila[5] or 0),

                "cantidad_insumos": float(fila[6] or 0)
            })

        # ==================================
        # PROVEEDORES PARA LOS FILTROS
        # ==================================

        cursor.execute("""
            SELECT
                id_proveedor,
                nombre

            FROM proveedores

            WHERE estado = 'Activo'

            ORDER BY nombre ASC

        """)

        proveedores = [
            {
                "id": fila[0],
                "nombre": fila[1]
            }
            for fila in cursor.fetchall()
        ]

        # ==================================
        # RESPUESTA JSON
        # ==================================

        return jsonify({

            "ok": True,

            "filtros": {
                "desde": desde,
                "hasta": hasta,
                "proveedor": id_proveedor or "",
                "estado": estado
            },

            "indicadores": {
                "total_compras": total_compras,
                "gasto_total": gasto_total,
                "insumos_comprados": insumos_comprados,
                "compras_pendientes": compras_pendientes
            },

            "compras_por_mes": compras_por_mes,

            "gasto_proveedores": gasto_proveedores,

            "insumos_top": insumos_top,

            "historial": historial,

            "proveedores": proveedores

        })

    except ValueError:

        return jsonify({
            "ok": False,
            "mensaje": "Verifica las fechas y el proveedor seleccionado."
        }), 400

    except Exception as error:

        print(
            "ERROR REPORTES DE COMPRAS:",
            repr(error)
        )

        return jsonify({
            "ok": False,
            "mensaje": "No fue posible generar los reportes.",
            "error": str(error)
        }), 500

    finally:

        if cursor:
            cursor.close()

        if conexion:
            conexion.close()

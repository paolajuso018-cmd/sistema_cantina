
from flask import (
    Blueprint, render_template, request, session,
    redirect, url_for, flash, jsonify
)

from models.conexion import obtener_conexion
from routes.administrativo import MENUS_ROLES


proveedores_bp = Blueprint("proveedores", __name__)


# =====================================================
# UTILIDADES
# =====================================================

def es_administrador():
    return (
        "id_usuario" in session
        and str(session.get("rol", "")).strip().lower() == "administrador"
    )


def error_json(mensaje, codigo=400):
    return jsonify({"ok": False, "mensaje": mensaje}), codigo


def obtener_datos_proveedor(datos):
    nombre = str(datos.get("nombre", "")).strip()
    telefono = str(datos.get("telefono", "")).strip()
    correo = str(datos.get("correo", "")).strip()
    direccion = str(datos.get("direccion", "")).strip()
    estado = str(datos.get("estado", "Activo")).strip()

    if not nombre:
        raise ValueError("El nombre del proveedor es obligatorio.")

    if len(nombre) > 120:
        raise ValueError("El nombre no puede superar 120 caracteres.")

    if len(telefono) > 20:
        raise ValueError("El teléfono no puede superar 20 caracteres.")

    if len(correo) > 120:
        raise ValueError("El correo no puede superar 120 caracteres.")

    if len(direccion) > 200:
        raise ValueError("La dirección no puede superar 200 caracteres.")

    if estado not in ("Activo", "Inactivo"):
        raise ValueError("Selecciona un estado válido.")

    insumos = datos.get("insumos", [])

    if not isinstance(insumos, list):
        raise ValueError("La selección de insumos no es válida.")

    try:
        insumos = list(dict.fromkeys(int(x) for x in insumos))
    except (TypeError, ValueError):
        raise ValueError("Hay identificadores de insumos no válidos.")

    if any(x <= 0 for x in insumos):
        raise ValueError("Hay identificadores de insumos no válidos.")

    return nombre, telefono, correo, direccion, estado, insumos


def guardar_relaciones_insumos(cursor, id_proveedor, insumos):
    # Comprobar que todos los insumos existen.
    if insumos:
        marcadores = ",".join(["%s"] * len(insumos))

        cursor.execute(
            f"""
            SELECT id_insumo
            FROM insumos
            WHERE id_insumo IN ({marcadores})
            """,
            tuple(insumos)
        )

        encontrados = {int(fila[0]) for fila in cursor.fetchall()}

        if encontrados != set(insumos):
            raise ValueError(
                "Uno o más insumos seleccionados ya no existen."
            )

    # Sustituir la selección anterior por la nueva.
    cursor.execute(
        "DELETE FROM proveedores_insumos WHERE id_proveedor = %s",
        (id_proveedor,)
    )

    if insumos:
        cursor.executemany(
            """
            INSERT INTO proveedores_insumos
                (id_proveedor, id_insumo)
            VALUES (%s, %s)
            """,
            [(id_proveedor, id_insumo) for id_insumo in insumos]
        )


# =====================================================
# PANTALLA PRINCIPAL
# =====================================================

@proveedores_bp.route("/admin/proveedores")
def administrar_proveedores():

    if "id_usuario" not in session:
        return redirect(url_for("login.login"))

    if not es_administrador():
        flash("No tienes permiso para acceder.", "error")
        return redirect(url_for("login.login"))

    rol = session.get("rol", "")

    return render_template(
        "admin/proveedores.html",
        nombre=session.get("nombre", session.get("username", "Usuario")),
        rol=rol,
        menu=MENUS_ROLES.get(rol, [])
    )


# =====================================================
# API: CATÁLOGO DE INSUMOS
# =====================================================

@proveedores_bp.route("/admin/api/proveedores/insumos", methods=["GET"])
def listar_insumos_proveedores():

    if not es_administrador():
        return error_json("No tienes autorización.", 403)

    conexion = cursor = None

    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()

        cursor.execute("""
            SELECT id_insumo, nombre
            FROM insumos
            ORDER BY nombre ASC
        """)

        insumos = [
            {"id": int(fila[0]), "nombre": fila[1]}
            for fila in cursor.fetchall()
        ]

        return jsonify({"ok": True, "insumos": insumos})

    except Exception as error:
        print("ERROR CATÁLOGO INSUMOS:", repr(error))
        return error_json("No fue posible cargar los insumos.", 500)

    finally:
        if cursor:
            cursor.close()
        if conexion:
            conexion.close()


# =====================================================
# API: LISTAR PROVEEDORES E INDICADORES
# =====================================================

@proveedores_bp.route("/admin/api/proveedores", methods=["GET"])
def listar_proveedores():

    if not es_administrador():
        return error_json("No tienes autorización.", 403)

    conexion = cursor = None

    try:
        estado = request.args.get("estado", "").strip()
        buscar = request.args.get("buscar", "").strip()

        if estado and estado not in ("Activo", "Inactivo"):
            return error_json("El estado seleccionado no es válido.")

        conexion = obtener_conexion()
        cursor = conexion.cursor()

        cursor.execute("""
            SELECT
                COUNT(*),
                COALESCE(SUM(estado = 'Activo'), 0),
                COALESCE(SUM(estado = 'Inactivo'), 0)
            FROM proveedores
        """)

        fila = cursor.fetchone()

        indicadores = {
            "total_proveedores": int(fila[0] or 0),
            "proveedores_activos": int(fila[1] or 0),
            "proveedores_inactivos": int(fila[2] or 0)
        }

        cursor.execute("""
            SELECT
                COUNT(DISTINCT id_compra),
                COALESCE(SUM(
                    CASE WHEN estado = 'Registrada'
                    THEN total ELSE 0 END
                ), 0)
            FROM compras
        """)

        fila = cursor.fetchone()

        indicadores["total_compras"] = int(fila[0] or 0)
        indicadores["gasto_total"] = float(fila[1] or 0)

        condiciones = []
        parametros = []

        if estado:
            condiciones.append("p.estado = %s")
            parametros.append(estado)

        if buscar:
            condiciones.append("""
                (
                    p.nombre LIKE %s
                    OR p.telefono LIKE %s
                    OR p.correo LIKE %s
                    OR p.direccion LIKE %s
                )
            """)
            patron = f"%{buscar}%"
            parametros.extend([patron] * 4)

        where_sql = (
            "WHERE " + " AND ".join(condiciones)
            if condiciones else ""
        )

        cursor.execute(f"""
            SELECT
                p.id_proveedor,
                p.nombre,
                p.telefono,
                p.correo,
                p.direccion,
                p.estado,
                COUNT(DISTINCT c.id_compra),
                COALESCE(SUM(
                    CASE WHEN c.estado = 'Registrada'
                    THEN c.total ELSE 0 END
                ), 0),
                COUNT(DISTINCT pi.id_insumo)

            FROM proveedores p

            LEFT JOIN compras c
                ON c.id_proveedor = p.id_proveedor

            LEFT JOIN proveedores_insumos pi
                ON pi.id_proveedor = p.id_proveedor

            {where_sql}

            GROUP BY
                p.id_proveedor, p.nombre, p.telefono,
                p.correo, p.direccion, p.estado

            ORDER BY p.nombre ASC
        """, tuple(parametros))

        proveedores = []

        for fila in cursor.fetchall():
            proveedores.append({
                "id": int(fila[0]),
                "nombre": fila[1],
                "telefono": fila[2] or "",
                "correo": fila[3] or "",
                "direccion": fila[4] or "",
                "estado": fila[5],
                "compras": int(fila[6] or 0),
                "gasto": float(fila[7] or 0),
                "total_insumos": int(fila[8] or 0)
            })

        return jsonify({
            "ok": True,
            "indicadores": indicadores,
            "proveedores": proveedores
        })

    except Exception as error:
        print("ERROR LISTAR PROVEEDORES:", repr(error))
        return error_json("No fue posible consultar los proveedores.", 500)

    finally:
        if cursor:
            cursor.close()
        if conexion:
            conexion.close()


# =====================================================
# API: DETALLE DE UN PROVEEDOR
# =====================================================

@proveedores_bp.route(
    "/admin/api/proveedores/<int:id_proveedor>",
    methods=["GET"]
)
def detalle_proveedor(id_proveedor):

    if not es_administrador():
        return error_json("No tienes autorización.", 403)

    conexion = cursor = None

    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()

        cursor.execute("""
            SELECT
                id_proveedor, nombre, telefono,
                correo, direccion, estado
            FROM proveedores
            WHERE id_proveedor = %s
        """, (id_proveedor,))

        fila = cursor.fetchone()

        if not fila:
            return error_json("Proveedor no encontrado.", 404)

        proveedor = {
            "id": int(fila[0]),
            "nombre": fila[1],
            "telefono": fila[2] or "",
            "correo": fila[3] or "",
            "direccion": fila[4] or "",
            "estado": fila[5]
        }

        cursor.execute("""
            SELECT
                i.id_insumo,
                i.nombre
            FROM proveedores_insumos pi
            INNER JOIN insumos i
                ON i.id_insumo = pi.id_insumo
            WHERE pi.id_proveedor = %s
            ORDER BY i.nombre
        """, (id_proveedor,))

        insumos = [
            {"id": int(r[0]), "nombre": r[1]}
            for r in cursor.fetchall()
        ]

        cursor.execute("""
            SELECT
                COUNT(*),
                COALESCE(SUM(
                    CASE WHEN estado = 'Registrada'
                    THEN total ELSE 0 END
                ), 0)
            FROM compras
            WHERE id_proveedor = %s
        """, (id_proveedor,))

        fila = cursor.fetchone()

        proveedor["total_compras"] = int(fila[0] or 0)
        proveedor["gasto_total"] = float(fila[1] or 0)

        cursor.execute("""
            SELECT
                c.id_compra,
                c.fecha_compra,
                c.total,
                c.estado
            FROM compras c
            WHERE c.id_proveedor = %s
            ORDER BY c.fecha_compra DESC, c.id_compra DESC
            LIMIT 20
        """, (id_proveedor,))

        historial = []

        for r in cursor.fetchall():
            historial.append({
                "id": int(r[0]),
                "folio": f"C-{int(r[0]):05d}",
                "fecha": r[1].strftime("%d/%m/%Y") if r[1] else "",
                "total": float(r[2] or 0),
                "estado": r[3]
            })

        return jsonify({
            "ok": True,
            "proveedor": proveedor,
            "insumos": insumos,
            "historial": historial
        })

    except Exception as error:
        print("ERROR DETALLE PROVEEDOR:", repr(error))
        return error_json("No fue posible consultar el proveedor.", 500)

    finally:
        if cursor:
            cursor.close()
        if conexion:
            conexion.close()


# =====================================================
# API: CREAR PROVEEDOR
# =====================================================

@proveedores_bp.route("/admin/api/proveedores", methods=["POST"])
def crear_proveedor():

    if not es_administrador():
        return error_json("No tienes autorización.", 403)

    conexion = cursor = None

    try:
        datos = request.get_json(silent=True) or {}

        nombre, telefono, correo, direccion, estado, insumos = (
            obtener_datos_proveedor(datos)
        )

        conexion = obtener_conexion()
        cursor = conexion.cursor()

        cursor.execute("""
            INSERT INTO proveedores
                (nombre, telefono, correo, direccion, estado)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            nombre,
            telefono or None,
            correo or None,
            direccion or None,
            estado
        ))

        id_proveedor = cursor.lastrowid

        guardar_relaciones_insumos(cursor, id_proveedor, insumos)

        conexion.commit()

        return jsonify({
            "ok": True,
            "mensaje": "Proveedor registrado correctamente.",
            "id_proveedor": id_proveedor
        })

    except ValueError as error:
        if conexion:
            conexion.rollback()
        return error_json(str(error))

    except Exception as error:
        if conexion:
            conexion.rollback()
        print("ERROR CREAR PROVEEDOR:", repr(error))
        return error_json("No fue posible registrar el proveedor.", 500)

    finally:
        if cursor:
            cursor.close()
        if conexion:
            conexion.close()


# =====================================================
# API: EDITAR PROVEEDOR Y SUS INSUMOS
# =====================================================

@proveedores_bp.route(
    "/admin/api/proveedores/<int:id_proveedor>",
    methods=["PUT"]
)
def actualizar_proveedor(id_proveedor):

    if not es_administrador():
        return error_json("No tienes autorización.", 403)

    conexion = cursor = None

    try:
        datos = request.get_json(silent=True) or {}

        nombre, telefono, correo, direccion, estado, insumos = (
            obtener_datos_proveedor(datos)
        )

        conexion = obtener_conexion()
        cursor = conexion.cursor()

        cursor.execute("""
            UPDATE proveedores
            SET
                nombre = %s,
                telefono = %s,
                correo = %s,
                direccion = %s,
                estado = %s
            WHERE id_proveedor = %s
        """, (
            nombre,
            telefono or None,
            correo or None,
            direccion or None,
            estado,
            id_proveedor
        ))

        if cursor.rowcount == 0:
            cursor.execute("""
                SELECT id_proveedor
                FROM proveedores
                WHERE id_proveedor = %s
            """, (id_proveedor,))

            if not cursor.fetchone():
                return error_json("Proveedor no encontrado.", 404)

        guardar_relaciones_insumos(cursor, id_proveedor, insumos)

        conexion.commit()

        return jsonify({
            "ok": True,
            "mensaje": "Proveedor actualizado correctamente."
        })

    except ValueError as error:
        if conexion:
            conexion.rollback()
        return error_json(str(error))

    except Exception as error:
        if conexion:
            conexion.rollback()
        print("ERROR ACTUALIZAR PROVEEDOR:", repr(error))
        return error_json("No fue posible actualizar el proveedor.", 500)

    finally:
        if cursor:
            cursor.close()
        if conexion:
            conexion.close()


# =====================================================
# API: CAMBIAR ESTADO
# =====================================================

@proveedores_bp.route(
    "/admin/api/proveedores/<int:id_proveedor>/estado",
    methods=["PATCH"]
)
def cambiar_estado_proveedor(id_proveedor):

    if not es_administrador():
        return error_json("No tienes autorización.", 403)

    conexion = cursor = None

    try:
        datos = request.get_json(silent=True) or {}
        estado = str(datos.get("estado", "")).strip()

        if estado not in ("Activo", "Inactivo"):
            return error_json("Estado no válido.")

        conexion = obtener_conexion()
        cursor = conexion.cursor()

        cursor.execute("""
            UPDATE proveedores
            SET estado = %s
            WHERE id_proveedor = %s
        """, (estado, id_proveedor))

        if cursor.rowcount == 0:
            cursor.execute("""
                SELECT id_proveedor
                FROM proveedores
                WHERE id_proveedor = %s
            """, (id_proveedor,))

            if not cursor.fetchone():
                return error_json("Proveedor no encontrado.", 404)

        conexion.commit()

        return jsonify({
            "ok": True,
            "mensaje": f"Proveedor actualizado a {estado}."
        })

    except Exception as error:
        if conexion:
            conexion.rollback()
        print("ERROR CAMBIAR ESTADO:", repr(error))
        return error_json("No fue posible cambiar el estado.", 500)

    finally:
        if cursor:
            cursor.close()
        if conexion:
            conexion.close()

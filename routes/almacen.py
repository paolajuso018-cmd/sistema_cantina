
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

import math


almacen_bp = Blueprint(
    "almacen",
    __name__,
    url_prefix="/almacen"
)


# ==========================================
# FUNCIONES AUXILIARES
# ==========================================

def verificar_acceso():

    if "id_usuario" not in session:
        return False

    if session.get("rol") not in ("Administrador", "Gerente"):
        abort(403)

    return True


def convertir_decimal(valor, nombre, permitir_cero=True):

    try:
        numero = Decimal(str(valor))

        if not numero.is_finite():
            raise InvalidOperation()

        if permitir_cero:
            if numero < 0:
                raise ValueError()
        else:
            if numero <= 0:
                raise ValueError()

        return numero

    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(f"El campo {nombre} contiene un valor inválido.")


def obtener_catalogos(cursor):

    cursor.execute("""
        SELECT id_categoria, nombre
        FROM categorias_insumos
        ORDER BY nombre ASC
    """)

    categorias = cursor.fetchall()

    cursor.execute("""
        SELECT id_unidad, nombre, abreviatura
        FROM unidades_medida
        ORDER BY nombre ASC
    """)

    unidades = cursor.fetchall()

    return categorias, unidades


# ==========================================
# VISTA PRINCIPAL DEL ALMACÉN
# ==========================================

@almacen_bp.route("/", methods=["GET"])
def inventario():

    if not verificar_acceso():
        return redirect(url_for("login.login"))

    conexion = obtener_conexion()

    if conexion is None:

        flash("No se pudo conectar con la base de datos.", "error")

        return render_template(
            "admin/almacen.html",
            insumos=[],
            categorias=[],
            unidades=[],
            estadisticas={
                "total": 0,
                "con_stock": 0,
                "stock_bajo": 0,
                "sin_stock": 0
            },
            pagina=1,
            total_paginas=1,
            total_registros=0,
            busqueda="",
            categoria_seleccionada="",
            estado_seleccionado="",
            nombre=session.get("nombre"),
            rol=session.get("rol"),
            menu=[]
        )

    cursor = None

    try:

        cursor = conexion.cursor(dictionary=True)

        # ----------------------------------
        # MENÚ LATERAL
        # ----------------------------------

        from routes.administrativo import MENUS_ROLES

        menu = MENUS_ROLES.get(session.get("rol"), [])

        # ----------------------------------
        # FILTROS
        # ----------------------------------

        busqueda = request.args.get("buscar", "").strip()

        categoria_seleccionada = request.args.get(
            "categoria", ""
        ).strip()

        estado_seleccionado = request.args.get(
            "estado", ""
        ).strip()

        pagina = request.args.get("pagina", 1, type=int)

        if pagina < 1:
            pagina = 1

        registros_por_pagina = 8

        # ----------------------------------
        # ESTADÍSTICAS DEL INVENTARIO
        # ----------------------------------

        cursor.execute("""
            SELECT
                COUNT(*) AS total,

                SUM(
                    CASE
                        WHEN stock_actual > 0
                        THEN 1 ELSE 0
                    END
                ) AS con_stock,

                SUM(
                    CASE
                        WHEN stock_actual > 0
                         AND stock_actual <= stock_minimo
                        THEN 1 ELSE 0
                    END
                ) AS stock_bajo,

                SUM(
                    CASE
                        WHEN stock_actual <= 0
                        THEN 1 ELSE 0
                    END
                ) AS sin_stock

            FROM insumos
            WHERE estado = 'Activo'
        """)

        estadisticas = cursor.fetchone()

        for clave in estadisticas:
            estadisticas[clave] = estadisticas[clave] or 0

        # ----------------------------------
        # CATEGORÍAS Y UNIDADES
        # ----------------------------------

        categorias, unidades = obtener_catalogos(cursor)

        # ----------------------------------
        # CONSTRUIR FILTROS
        # ----------------------------------

        condiciones = []
        parametros = []

        if busqueda:

            condiciones.append("""
                (
                    i.nombre LIKE %s
                    OR i.codigo LIKE %s
                )
            """)

            parametros.extend([
                f"%{busqueda}%",
                f"%{busqueda}%"
            ])

        if categoria_seleccionada:

            condiciones.append("i.id_categoria = %s")

            parametros.append(categoria_seleccionada)

        if estado_seleccionado in ("Activo", "Inactivo"):

            condiciones.append("i.estado = %s")

            parametros.append(estado_seleccionado)

        where_sql = ""

        if condiciones:
            where_sql = "WHERE " + " AND ".join(condiciones)

        # ----------------------------------
        # CONTAR REGISTROS
        # ----------------------------------

        cursor.execute(f"""
            SELECT COUNT(*) AS total
            FROM insumos i
            {where_sql}
        """, parametros)

        total_registros = cursor.fetchone()["total"]

        total_paginas = max(
            1,
            math.ceil(total_registros / registros_por_pagina)
        )

        if pagina > total_paginas:
            pagina = total_paginas

        desplazamiento = (
            pagina - 1
        ) * registros_por_pagina

        # ----------------------------------
        # CONSULTAR INSUMOS
        # ----------------------------------

        consulta = f"""
            SELECT
                i.id_insumo,
                i.codigo,
                i.nombre,
                i.descripcion,
                i.costo_unitario,
                i.stock_actual,
                i.stock_minimo,
                i.estado,

                i.id_categoria,
                i.id_unidad,

                c.nombre AS categoria,
                u.nombre AS unidad,
                u.abreviatura,

                CASE
                    WHEN i.stock_actual <= 0
                        THEN 'Sin stock'

                    WHEN i.stock_actual <= i.stock_minimo
                        THEN 'Stock bajo'

                    ELSE 'Activo'
                END AS estado_stock

            FROM insumos i

            INNER JOIN categorias_insumos c
                ON i.id_categoria = c.id_categoria

            INNER JOIN unidades_medida u
                ON i.id_unidad = u.id_unidad

            {where_sql}

            ORDER BY i.id_insumo DESC

            LIMIT %s OFFSET %s
        """

        parametros_consulta = parametros + [
            registros_por_pagina,
            desplazamiento
        ]

        cursor.execute(
            consulta,
            parametros_consulta
        )

        insumos = cursor.fetchall()

        return render_template(
            "admin/almacen.html",
            insumos=insumos,
            categorias=categorias,
            unidades=unidades,
            estadisticas=estadisticas,
            pagina=pagina,
            total_paginas=total_paginas,
            total_registros=total_registros,
            busqueda=busqueda,
            categoria_seleccionada=categoria_seleccionada,
            estado_seleccionado=estado_seleccionado,
            nombre=session.get("nombre"),
            rol=session.get("rol"),
            menu=menu
        )

    except Exception as error:

        print("ERROR AL CARGAR ALMACÉN:", repr(error))

        flash("Ocurrió un error al cargar el inventario.", "error")

        return redirect(url_for("administrativo.dashboard"))

    finally:

        if cursor:
            cursor.close()

        conexion.close()


# ==========================================
# REGISTRAR NUEVO INSUMO
# ==========================================

@almacen_bp.route("/nuevo", methods=["POST"])
def nuevo_insumo():

    if not verificar_acceso():
        return redirect(url_for("login.login"))

    codigo = request.form.get("codigo", "").strip()
    nombre = request.form.get("nombre", "").strip()
    id_categoria = request.form.get("id_categoria", "").strip()
    id_unidad = request.form.get("id_unidad", "").strip()
    descripcion = request.form.get("descripcion", "").strip()
    estado = request.form.get("estado", "Activo").strip()

    try:

        costo_unitario = convertir_decimal(
            request.form.get("costo_unitario"),
            "costo unitario"
        )

        stock_actual = convertir_decimal(
            request.form.get("stock_actual"),
            "stock actual"
        )

        stock_minimo = convertir_decimal(
            request.form.get("stock_minimo"),
            "stock mínimo"
        )

        id_categoria = int(id_categoria)
        id_unidad = int(id_unidad)

        if not codigo or not nombre:
            raise ValueError("El código y el nombre son obligatorios.")

        if estado not in ("Activo", "Inactivo"):
            raise ValueError("El estado seleccionado no es válido.")

    except (ValueError, TypeError) as error:

        flash(str(error), "error")

        return redirect(url_for("almacen.inventario"))

    conexion = obtener_conexion()

    if conexion is None:

        flash("No se pudo conectar con la base de datos.", "error")

        return redirect(url_for("almacen.inventario"))

    cursor = None

    try:

        cursor = conexion.cursor()

        cursor.execute("""
            INSERT INTO insumos (
                codigo,
                id_categoria,
                id_unidad,
                nombre,
                descripcion,
                costo_unitario,
                stock_actual,
                stock_minimo,
                estado
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            codigo,
            id_categoria,
            id_unidad,
            nombre,
            descripcion or None,
            costo_unitario,
            stock_actual,
            stock_minimo,
            estado
        ))

        id_insumo = cursor.lastrowid

        # Registrar el inventario inicial como entrada
        if stock_actual > 0:

            cursor.execute("""
                INSERT INTO movimientos_inventario (
                    id_insumo,
                    id_usuario,
                    tipo_movimiento,
                    cantidad,
                    motivo
                )
                VALUES (%s, %s, 'Entrada', %s, %s)
            """, (
                id_insumo,
                session["id_usuario"],
                stock_actual,
                "Registro de inventario inicial"
            ))

        conexion.commit()

        flash("El insumo se registró correctamente.", "success")

    except Exception as error:

        conexion.rollback()

        print("ERROR AL REGISTRAR INSUMO:", repr(error))

        if getattr(error, "errno", None) == 1062:
            flash("El código del insumo ya está registrado.", "error")
        else:
            flash("No se pudo registrar el insumo.", "error")

    finally:

        if cursor:
            cursor.close()

        conexion.close()

    return redirect(url_for("almacen.inventario"))


# ==========================================
# CONSULTAR DATOS DE UN INSUMO
# ==========================================

@almacen_bp.route("/<int:id_insumo>/datos", methods=["GET"])
def obtener_datos_insumo(id_insumo):

    if not verificar_acceso():
        return jsonify({"error": "No tienes una sesión válida."}), 401

    conexion = obtener_conexion()

    if conexion is None:
        return jsonify({"error": "No se pudo conectar con MySQL."}), 500

    cursor = None

    try:

        cursor = conexion.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                id_insumo,
                codigo,
                nombre,
                id_categoria,
                id_unidad,
                descripcion,
                costo_unitario,
                stock_actual,
                stock_minimo,
                estado
            FROM insumos
            WHERE id_insumo = %s
        """, (id_insumo,))

        insumo = cursor.fetchone()

        if not insumo:
            return jsonify({"error": "El insumo no existe."}), 404

        return jsonify(insumo)

    except Exception as error:

        print("ERROR AL CONSULTAR INSUMO:", repr(error))

        return jsonify({
            "error": "No se pudieron consultar los datos del insumo."
        }), 500

    finally:

        if cursor:
            cursor.close()

        conexion.close()


# ==========================================
# EDITAR INSUMO
# ==========================================

@almacen_bp.route("/<int:id_insumo>/editar", methods=["POST"])
def editar_insumo(id_insumo):

    if not verificar_acceso():
        return jsonify({"error": "No tienes una sesión válida."}), 401

    codigo = request.form.get("codigo", "").strip()
    nombre = request.form.get("nombre", "").strip()
    id_categoria = request.form.get("id_categoria", "").strip()
    id_unidad = request.form.get("id_unidad", "").strip()
    descripcion = request.form.get("descripcion", "").strip()
    estado = request.form.get("estado", "").strip()

    try:

        if not all([
            codigo,
            nombre,
            id_categoria,
            id_unidad
        ]):
            raise ValueError("Completa todos los campos obligatorios.")

        id_categoria = int(id_categoria)
        id_unidad = int(id_unidad)

        costo_unitario = convertir_decimal(
            request.form.get("costo_unitario"),
            "costo unitario"
        )

        stock_minimo = convertir_decimal(
            request.form.get("stock_minimo"),
            "stock mínimo"
        )

        if estado not in ("Activo", "Inactivo"):
            raise ValueError("El estado seleccionado no es válido.")

    except (ValueError, TypeError) as error:

        return jsonify({"error": str(error)}), 400

    conexion = obtener_conexion()

    if conexion is None:
        return jsonify({"error": "No se pudo conectar con MySQL."}), 500

    cursor = None

    try:

        cursor = conexion.cursor()

        cursor.execute("""
            UPDATE insumos
            SET
                codigo = %s,
                nombre = %s,
                id_categoria = %s,
                id_unidad = %s,
                descripcion = %s,
                costo_unitario = %s,
                stock_minimo = %s,
                estado = %s
            WHERE id_insumo = %s
        """, (
            codigo,
            nombre,
            id_categoria,
            id_unidad,
            descripcion or None,
            costo_unitario,
            stock_minimo,
            estado,
            id_insumo
        ))

        if cursor.rowcount == 0:

            cursor.execute("""
                SELECT id_insumo
                FROM insumos
                WHERE id_insumo = %s
            """, (id_insumo,))

            if not cursor.fetchone():
                return jsonify({"error": "El insumo no existe."}), 404

        conexion.commit()

        return jsonify({
            "ok": True,
            "mensaje": "El insumo se actualizó correctamente."
        })

    except Exception as error:

        conexion.rollback()

        print("ERROR AL EDITAR INSUMO:", repr(error))

        if getattr(error, "errno", None) == 1062:
            return jsonify({
                "error": "Ese código ya está registrado."
            }), 409

        return jsonify({
            "error": "No se pudo actualizar el insumo."
        }), 500

    finally:

        if cursor:
            cursor.close()

        conexion.close()


# ==========================================
# REGISTRAR MOVIMIENTO DE INVENTARIO
# ==========================================

@almacen_bp.route("/<int:id_insumo>/movimiento", methods=["POST"])
def registrar_movimiento(id_insumo):

    if not verificar_acceso():
        return jsonify({"error": "No tienes una sesión válida."}), 401

    tipo = request.form.get("tipo_movimiento", "").strip()
    cantidad_texto = request.form.get("cantidad", "").strip()
    motivo = request.form.get("motivo", "").strip()

    if tipo not in ("Entrada", "Salida", "Ajuste"):

        return jsonify({
            "error": "Selecciona un tipo de movimiento válido."
        }), 400

    if not motivo:

        return jsonify({
            "error": "Escribe el motivo del movimiento."
        }), 400

    try:

        cantidad = convertir_decimal(
            cantidad_texto,
            "cantidad",
            permitir_cero=(tipo == "Ajuste")
        )

    except ValueError as error:

        return jsonify({"error": str(error)}), 400

    conexion = obtener_conexion()

    if conexion is None:
        return jsonify({"error": "No se pudo conectar con MySQL."}), 500

    cursor = None

    try:

        cursor = conexion.cursor(dictionary=True)

        # Bloquear el registro mientras se actualiza el stock
        cursor.execute("""
            SELECT stock_actual, estado
            FROM insumos
            WHERE id_insumo = %s
            FOR UPDATE
        """, (id_insumo,))

        insumo = cursor.fetchone()

        if not insumo:

            conexion.rollback()

            return jsonify({
                "error": "El insumo no existe."
            }), 404

        if insumo["estado"] != "Activo":

            conexion.rollback()

            return jsonify({
                "error": "No puedes registrar movimientos en un insumo inactivo."
            }), 400

        stock_anterior = Decimal(str(insumo["stock_actual"]))

        # ----------------------------------
        # CALCULAR NUEVO STOCK
        # ----------------------------------

        if tipo == "Entrada":

            nuevo_stock = stock_anterior + cantidad
            cantidad_movimiento = cantidad

        elif tipo == "Salida":

            if cantidad > stock_anterior:

                conexion.rollback()

                return jsonify({
                    "error": "La salida supera el stock disponible."
                }), 400

            nuevo_stock = stock_anterior - cantidad
            cantidad_movimiento = cantidad

        else:

            # El ajuste establece el stock físico contado.
            nuevo_stock = cantidad
            cantidad_movimiento = nuevo_stock - stock_anterior

        # ----------------------------------
        # ACTUALIZAR EXISTENCIAS
        # ----------------------------------

        cursor.execute("""
            UPDATE insumos
            SET stock_actual = %s
            WHERE id_insumo = %s
        """, (
            nuevo_stock,
            id_insumo
        ))

        # ----------------------------------
        # GUARDAR HISTORIAL
        # ----------------------------------

        cursor.execute("""
            INSERT INTO movimientos_inventario (
                id_insumo,
                id_usuario,
                tipo_movimiento,
                cantidad,
                motivo
            )
            VALUES (%s, %s, %s, %s, %s)
        """, (
            id_insumo,
            session["id_usuario"],
            tipo,
            cantidad_movimiento,
            motivo
        ))

        conexion.commit()

        return jsonify({
            "ok": True,
            "mensaje": "Movimiento registrado correctamente.",
            "stock_anterior": float(stock_anterior),
            "stock_actual": float(nuevo_stock)
        })

    except Exception as error:

        conexion.rollback()

        print("ERROR AL REGISTRAR MOVIMIENTO:", repr(error))

        return jsonify({
            "error": "No se pudo registrar el movimiento."
        }), 500

    finally:

        if cursor:
            cursor.close()

        conexion.close()


# ==========================================
# DESACTIVAR INSUMO
# ==========================================

@almacen_bp.route("/<int:id_insumo>/desactivar", methods=["POST"])
def desactivar_insumo(id_insumo):

    if not verificar_acceso():
        return jsonify({"error": "No tienes una sesión válida."}), 401

    conexion = obtener_conexion()

    if conexion is None:
        return jsonify({"error": "No se pudo conectar con MySQL."}), 500

    cursor = None

    try:

        cursor = conexion.cursor()

        cursor.execute("""
            UPDATE insumos
            SET estado = 'Inactivo'
            WHERE id_insumo = %s
              AND estado = 'Activo'
        """, (id_insumo,))

        if cursor.rowcount == 0:

            cursor.execute("""
                SELECT estado
                FROM insumos
                WHERE id_insumo = %s
            """, (id_insumo,))

            resultado = cursor.fetchone()

            if not resultado:

                return jsonify({
                    "error": "El insumo no existe."
                }), 404

            return jsonify({
                "error": "El insumo ya está inactivo."
            }), 400

        conexion.commit()

        return jsonify({
            "ok": True,
            "mensaje": "El insumo se desactivó correctamente."
        })

    except Exception as error:

        conexion.rollback()

        print("ERROR AL DESACTIVAR INSUMO:", repr(error))

        return jsonify({
            "error": "No se pudo desactivar el insumo."
        }), 500

    finally:

        if cursor:
            cursor.close()

        conexion.close()

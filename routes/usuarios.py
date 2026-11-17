from flask import (
    Blueprint, render_template, request,
    redirect, url_for, session, flash
)
from models.conexion import obtener_conexion
import math
from werkzeug.security import generate_password_hash

from routes.administrativo import MENUS_ROLES


usuarios_bp = Blueprint("usuarios", __name__)


# ==========================================
# GESTIÓN DE USUARIOS
# ==========================================

@usuarios_bp.route("/usuarios/")
def gestionar_usuarios():

    # Verificar sesión
    if "id_usuario" not in session:
        return redirect(url_for("login.login"))

    # Solo administrador puede gestionar usuarios
    if session.get("rol") != "Administrador":
        flash("No tienes permiso para gestionar usuarios.", "error")
        return redirect(url_for("administrativo.dashboard"))

    busqueda = request.args.get("busqueda", "").strip()
    rol_filtro = request.args.get("rol", "").strip()
    estado_filtro = request.args.get("estado", "").strip()

    try:
        pagina = max(1, int(request.args.get("pagina", 1)))
    except ValueError:
        pagina = 1

    por_pagina = 7
    offset = (pagina - 1) * por_pagina

    conexion = None
    cursor = None

    usuarios = []
    roles = []

    estadisticas = {
        "total": 0,
        "activos": 0,
        "inactivos": 0,
        "roles": 0
    }

    total_paginas = 1
    total_filtrados = 0

    try:

        conexion = obtener_conexion()

        if conexion is None:
            raise Exception("No se pudo conectar con MySQL.")

        cursor = conexion.cursor(dictionary=True)

        # ==================================
        # ESTADÍSTICAS GENERALES
        # ==================================

        cursor.execute("""
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN estado = 'Activo' THEN 1 ELSE 0 END) AS activos,
                SUM(CASE WHEN estado = 'Inactivo' THEN 1 ELSE 0 END) AS inactivos
            FROM usuarios
        """)

        resultado = cursor.fetchone()

        estadisticas["total"] = resultado["total"] or 0
        estadisticas["activos"] = resultado["activos"] or 0
        estadisticas["inactivos"] = resultado["inactivos"] or 0

        cursor.execute("""
            SELECT COUNT(*) AS total_roles
            FROM roles
            WHERE estado = 'Activo'
        """)

        estadisticas["roles"] = cursor.fetchone()["total_roles"] or 0

        # ==================================
        # LISTA DE ROLES PARA LOS FILTROS
        # ==================================

        cursor.execute("""
            SELECT id_rol, nombre
            FROM roles
            WHERE estado = 'Activo'
            ORDER BY nombre
        """)

        roles = cursor.fetchall()

        # ==================================
        # CONSTRUIR FILTROS
        # ==================================

        condiciones = []
        parametros = []

        if busqueda:

            condiciones.append("""
                (
                    u.nombre LIKE %s
                    OR u.username LIKE %s
                    OR u.correo LIKE %s
                )
            """)

            termino = f"%{busqueda}%"

            parametros.extend([
                termino,
                termino,
                termino
            ])

        if rol_filtro:
            condiciones.append("u.id_rol = %s")
            parametros.append(rol_filtro)

        if estado_filtro in ("Activo", "Inactivo"):
            condiciones.append("u.estado = %s")
            parametros.append(estado_filtro)

        where_sql = ""

        if condiciones:
            where_sql = "WHERE " + " AND ".join(condiciones)

        # ==================================
        # CONTAR RESULTADOS
        # ==================================

        cursor.execute(f"""
            SELECT COUNT(*) AS total
            FROM usuarios u
            INNER JOIN roles r
                ON u.id_rol = r.id_rol
            {where_sql}
        """, tuple(parametros))

        total_filtrados = cursor.fetchone()["total"]

        total_paginas = max(
            1,
            math.ceil(total_filtrados / por_pagina)
        )

        if pagina > total_paginas:
            pagina = total_paginas
            offset = (pagina - 1) * por_pagina

        # ==================================
        # CONSULTAR USUARIOS
        # ==================================

        consulta = f"""
            SELECT
                u.id_usuario,
                u.id_rol,
                u.nombre,
                u.correo,
                u.username,
                u.estado,
                u.fecha_registro,
                r.nombre AS rol
            FROM usuarios u
            INNER JOIN roles r
                ON u.id_rol = r.id_rol
            {where_sql}
            ORDER BY u.fecha_registro DESC, u.id_usuario DESC
            LIMIT %s OFFSET %s
        """

        parametros_consulta = parametros + [
            por_pagina,
            offset
        ]

        cursor.execute(
            consulta,
            tuple(parametros_consulta)
        )

        usuarios = cursor.fetchall()

    except Exception as error:

        print("ERROR AL CARGAR USUARIOS:", repr(error))

        flash(
            "No fue posible cargar la información de usuarios.",
            "error"
        )

    finally:

        if cursor:
            cursor.close()

        if conexion:
            conexion.close()

    return render_template(
        "admin/usuarios.html",
        nombre=session.get("nombre", "Administrador"),
        menu=MENUS_ROLES["Administrador"],
        usuarios=usuarios,
        roles=roles,
        estadisticas=estadisticas,
        busqueda=busqueda,
        rol_filtro=rol_filtro,
        estado_filtro=estado_filtro,
        pagina=pagina,
        total_paginas=total_paginas,
        total_filtrados=total_filtrados
    )


# ==========================================
# REGISTRAR NUEVO USUARIO
# ==========================================

@usuarios_bp.route("/nuevo", methods=["POST"])
def nuevo_usuario():

    if "id_usuario" not in session:
        return redirect(url_for("login.login"))

    if session.get("rol") != "Administrador":
        flash("No tienes permiso para registrar usuarios.", "error")
        return redirect(url_for("administrativo.dashboard"))

    nombre = request.form.get("nombre", "").strip()
    correo = request.form.get("correo", "").strip()
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    id_rol = request.form.get("id_rol", "").strip()
    estado = request.form.get("estado", "Activo").strip()

    if not all([nombre, correo, username, password, id_rol]):
        flash("Completa todos los campos obligatorios.", "error")
        return redirect(url_for("usuarios.gestionar_usuarios"))

    if estado not in ("Activo", "Inactivo"):
        flash("El estado seleccionado no es válido.", "error")
        return redirect(url_for("usuarios.gestionar_usuarios"))

    if len(password) < 8:
        flash("La contraseña debe tener al menos 8 caracteres.", "error")
        return redirect(url_for("usuarios.gestionar_usuarios"))

    conexion = None
    cursor = None

    try:

        conexion = obtener_conexion()

        if conexion is None:
            raise Exception("No se pudo conectar con MySQL.")

        cursor = conexion.cursor(dictionary=True)

        # Comprobar que el nombre de usuario no exista
        cursor.execute("""
            SELECT id_usuario
            FROM usuarios
            WHERE username = %s
            LIMIT 1
        """, (username,))

        if cursor.fetchone():
            flash("Ese nombre de usuario ya está registrado.", "error")
            return redirect(url_for("usuarios.gestionar_usuarios"))

        # Comprobar que el rol exista y esté activo
        cursor.execute("""
            SELECT id_rol
            FROM roles
            WHERE id_rol = %s
              AND estado = 'Activo'
            LIMIT 1
        """, (id_rol,))

        rol = cursor.fetchone()

        if not rol:
            flash("El rol seleccionado no existe o está inactivo.", "error")
            return redirect(url_for("usuarios.gestionar_usuarios"))

        # Generar hash seguro de la contraseña
        password_hash = generate_password_hash(password)

        # Insertar usuario
        cursor.execute("""
            INSERT INTO usuarios (
                id_rol,
                nombre,
                correo,
                username,
                password,
                estado
            )
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            id_rol,
            nombre,
            correo,
            username,
            password_hash,
            estado
        ))

        conexion.commit()

        flash("El usuario se registró correctamente.", "success")

    except Exception as error:

        if conexion:
            conexion.rollback()

        print("ERROR AL REGISTRAR USUARIO:", repr(error))

        flash("No fue posible registrar el usuario.", "error")

    finally:

        if cursor:
            cursor.close()

        if conexion:
            conexion.close()

    return redirect(url_for("usuarios.gestionar_usuarios"))


# ==========================================
# EDITAR USUARIO
# ==========================================

@usuarios_bp.route("/editar/<int:id_usuario>", methods=["POST"])
def editar_usuario(id_usuario):

    if "id_usuario" not in session:
        return redirect(url_for("login.login"))

    if session.get("rol") != "Administrador":
        flash("No tienes permiso para editar usuarios.", "error")
        return redirect(url_for("administrativo.dashboard"))

    nombre = request.form.get("nombre", "").strip()
    correo = request.form.get("correo", "").strip()
    username = request.form.get("username", "").strip()
    id_rol = request.form.get("id_rol", "").strip()
    estado = request.form.get("estado", "").strip()
    password = request.form.get("password", "")

    if not all([nombre, correo, username, id_rol, estado]):
        flash("Completa todos los campos obligatorios.", "error")
        return redirect(url_for("usuarios.gestionar_usuarios"))

    if estado not in ("Activo", "Inactivo"):
        flash("El estado seleccionado no es válido.", "error")
        return redirect(url_for("usuarios.gestionar_usuarios"))

    if password and len(password) < 8:
        flash("La contraseña debe tener al menos 8 caracteres.", "error")
        return redirect(url_for("usuarios.gestionar_usuarios"))

    conexion = None
    cursor = None

    try:

        conexion = obtener_conexion()

        if conexion is None:
            raise Exception("No se pudo conectar con MySQL.")

        cursor = conexion.cursor(dictionary=True)

        # Verificar que el usuario exista
        cursor.execute("""
            SELECT id_usuario, id_rol, estado
            FROM usuarios
            WHERE id_usuario = %s
        """, (id_usuario,))

        usuario_actual = cursor.fetchone()

        if not usuario_actual:
            flash("El usuario que intentas editar no existe.", "error")
            return redirect(url_for("usuarios.gestionar_usuarios"))

        # Evitar desactivar la propia cuenta
        if (
            id_usuario == session.get("id_usuario")
            and estado == "Inactivo"
        ):
            flash("No puedes desactivar tu propia cuenta.", "error")
            return redirect(url_for("usuarios.gestionar_usuarios"))

        # Verificar que el username no pertenezca a otro usuario
        cursor.execute("""
            SELECT id_usuario
            FROM usuarios
            WHERE username = %s
              AND id_usuario <> %s
            LIMIT 1
        """, (username, id_usuario))

        if cursor.fetchone():
            flash("Ese nombre de usuario ya está registrado.", "error")
            return redirect(url_for("usuarios.gestionar_usuarios"))

        # Verificar que el rol exista y esté activo
        cursor.execute("""
            SELECT id_rol
            FROM roles
            WHERE id_rol = %s
              AND estado = 'Activo'
        """, (id_rol,))

        if not cursor.fetchone():
            flash("El rol seleccionado no existe o está inactivo.", "error")
            return redirect(url_for("usuarios.gestionar_usuarios"))

        # Actualizar con o sin cambio de contraseña
        if password:

            password_hash = generate_password_hash(password)

            cursor.execute("""
                UPDATE usuarios
                SET nombre = %s,
                    correo = %s,
                    username = %s,
                    id_rol = %s,
                    estado = %s,
                    password = %s
                WHERE id_usuario = %s
            """, (
                nombre,
                correo,
                username,
                id_rol,
                estado,
                password_hash,
                id_usuario
            ))

        else:

            cursor.execute("""
                UPDATE usuarios
                SET nombre = %s,
                    correo = %s,
                    username = %s,
                    id_rol = %s,
                    estado = %s
                WHERE id_usuario = %s
            """, (
                nombre,
                correo,
                username,
                id_rol,
                estado,
                id_usuario
            ))

        conexion.commit()

        flash("Los datos del usuario se actualizaron correctamente.", "success")

    except Exception as error:

        if conexion:
            conexion.rollback()

        print("ERROR AL EDITAR USUARIO:", repr(error))

        flash("No fue posible actualizar el usuario.", "error")

    finally:

        if cursor:
            cursor.close()

        if conexion:
            conexion.close()

    return redirect(url_for("usuarios.gestionar_usuarios"))


# ==========================================
# ELIMINAR USUARIO (BAJA LÓGICA)
# ==========================================

@usuarios_bp.route("/eliminar/<int:id_usuario>", methods=["POST"])
def eliminar_usuario(id_usuario):

    if "id_usuario" not in session:
        return redirect(url_for("login.login"))

    if session.get("rol") != "Administrador":
        flash("No tienes permiso para eliminar usuarios.", "error")
        return redirect(url_for("administrativo.dashboard"))

    # No permitir que el administrador se desactive a sí mismo
    if id_usuario == session.get("id_usuario"):
        flash("No puedes desactivar tu propia cuenta.", "error")
        return redirect(url_for("usuarios.gestionar_usuarios"))

    conexion = None
    cursor = None

    try:

        conexion = obtener_conexion()

        if conexion is None:
            raise Exception("No se pudo conectar con MySQL.")

        cursor = conexion.cursor()

        cursor.execute("""
            UPDATE usuarios
            SET estado = 'Inactivo'
            WHERE id_usuario = %s
              AND estado = 'Activo'
        """, (id_usuario,))

        if cursor.rowcount == 0:
            flash("El usuario no existe o ya está inactivo.", "error")
        else:
            conexion.commit()
            flash("El usuario fue desactivado correctamente.", "success")

    except Exception as error:

        if conexion:
            conexion.rollback()

        print("ERROR AL DESACTIVAR USUARIO:", repr(error))

        flash("No fue posible desactivar el usuario.", "error")

    finally:

        if cursor:
            cursor.close()

        if conexion:
            conexion.close()

    return redirect(url_for("usuarios.gestionar_usuarios"))

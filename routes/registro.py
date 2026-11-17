from flask import Blueprint, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash
from models.conexion import obtener_conexion

registro_bp = Blueprint("registro", __name__)


@registro_bp.route("/registro", methods=["POST"])
def registrar():

    # ==========================================
    # OBTENER DATOS DEL FORMULARIO
    # ==========================================

    nombre = request.form.get("nombre", "").strip()
    correo = request.form.get("correo", "").strip().lower()
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    confirmar_password = request.form.get("confirmar_password", "")

    # ==========================================
    # VALIDACIONES
    # ==========================================

    if not nombre or not correo or not username or not password:
        flash("Todos los campos son obligatorios.", "error")
        return redirect(url_for("login.login"))

    if len(nombre) > 100:
        flash("El nombre no puede superar los 100 caracteres.", "error")
        return redirect(url_for("login.login"))

    if len(correo) > 120:
        flash("El correo no puede superar los 120 caracteres.", "error")
        return redirect(url_for("login.login"))

    if len(username) > 50:
        flash("El usuario no puede superar los 50 caracteres.", "error")
        return redirect(url_for("login.login"))

    if len(password) < 8:
        flash("La contraseña debe tener al menos 8 caracteres.", "error")
        return redirect(url_for("login.login"))

    if password != confirmar_password:
        flash("Las contraseñas no coinciden.", "error")
        return redirect(url_for("login.login"))

    conexion = None
    cursor = None

    try:
        # ==========================================
        # CONECTAR A MYSQL
        # ==========================================

        conexion = obtener_conexion()
        cursor = conexion.cursor(dictionary=True)

        # ==========================================
        # VERIFICAR SI EL USUARIO O CORREO EXISTEN
        # ==========================================

        cursor.execute("""
            SELECT id_usuario
            FROM usuarios
            WHERE username = %s OR correo = %s
        """, (username, correo))

        usuario_existente = cursor.fetchone()

        if usuario_existente:
            flash("El usuario o correo electrónico ya está registrado.", "error")
            return redirect(url_for("login.login"))

        # ==========================================
        # OBTENER EL ROL CLIENTE
        # ==========================================

        cursor.execute("""
            SELECT id_rol
            FROM roles
            WHERE nombre = 'Cliente'
              AND estado = 'Activo'
            LIMIT 1
        """)

        rol = cursor.fetchone()

        if not rol:
            flash("No se encontró el rol Cliente activo. Contacta al administrador.", "error")
            return redirect(url_for("login.login"))

        # ==========================================
        # ENCRIPTAR CONTRASEÑA
        # ==========================================

        password_hash = generate_password_hash(password)

        # ==========================================
        # INSERTAR NUEVO USUARIO
        # ==========================================

        cursor.execute("""
            INSERT INTO usuarios
            (
                id_rol,
                nombre,
                correo,
                username,
                password,
                estado
            )
            VALUES (%s, %s, %s, %s, %s, 'Activo')
        """, (
            rol["id_rol"],
            nombre,
            correo,
            username,
            password_hash
        ))

        conexion.commit()

        flash(
            "¡Tu cuenta se creó correctamente! Ya puedes iniciar sesión.",
            "success"
        )

        return redirect(url_for("login.login"))

    except Exception as error:

        if conexion:
            conexion.rollback()

        print("Error al registrar usuario:", error)

        flash("Ocurrió un error al crear tu cuenta. Inténtalo nuevamente.", "error")

        return redirect(url_for("login.login"))

    finally:

        if cursor:
            cursor.close()

        if conexion:
            conexion.close()
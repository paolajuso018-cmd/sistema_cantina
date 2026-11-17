
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash
from models.conexion import obtener_conexion

login_bp = Blueprint("login", __name__)


# ==========================================
# INICIAR SESIÓN
# ==========================================

@login_bp.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Completa todos los campos.", "error")
            return render_template("login.html")

        conexion = obtener_conexion()

        if conexion is None:
            flash("No se pudo conectar con la base de datos.", "error")
            return render_template("login.html")

        try:

            cursor = conexion.cursor(dictionary=True)

            consulta = """
                SELECT
                    u.id_usuario,
                    u.nombre,
                    u.username,
                    u.password,
                    r.nombre AS rol
                FROM usuarios u
                INNER JOIN roles r
                    ON u.id_rol = r.id_rol
                WHERE u.username = %s
                  AND u.estado = 'Activo'
                  AND r.estado = 'Activo'
            """

            cursor.execute(consulta, (username,))
            usuario = cursor.fetchone()

            cursor.close()

            if usuario and check_password_hash(
                usuario["password"], password
            ):

                session.clear()

                session["id_usuario"] = usuario["id_usuario"]
                session["nombre"] = usuario["nombre"]
                session["username"] = usuario["username"]
                session["rol"] = usuario["rol"]

                # ==================================
                # REDIRECCIÓN SEGÚN EL ROL
                # ==================================

                if usuario["rol"].strip().lower() == "cajero":
                    return redirect(url_for("ventas.ventana_ventas"))

                return redirect(
                    url_for("administrativo.dashboard")
                )

            flash("Usuario o contraseña incorrectos.", "error")

        except Exception as error:

            print("Error al iniciar sesión:", repr(error))

            flash("Ocurrió un error al iniciar sesión.", "error")

        finally:

            conexion.close()

    return render_template("login.html")


# ==========================================
# CERRAR SESIÓN
# ==========================================

@login_bp.route("/cerrar-sesion")
def cerrar_sesion():

    session.clear()

    flash("Sesión cerrada correctamente.", "success")

    return redirect(url_for("login.login"))

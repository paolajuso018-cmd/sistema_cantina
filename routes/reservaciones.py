from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    send_file,
    jsonify
)

from models.conexion import obtener_conexion

from models.comprobante_reservacion import (
    generar_pdf_reservacion,
    enviar_correo_reservacion
)

from datetime import datetime, date
from io import BytesIO


# ==========================================
# BLUEPRINT DE RESERVACIONES
# ==========================================

reservaciones_bp = Blueprint(
    "reservaciones",
    __name__,
    url_prefix="/reservaciones"
)


# ==========================================
# CONSULTAR MESAS
# ==========================================

def obtener_mesas():

    conexion = None
    cursor = None

    try:

        conexion = obtener_conexion()

        if conexion is None:
            return []

        cursor = conexion.cursor()

        cursor.execute("""
            SELECT
                id_mesa,
                nombre_mesa,
                capacidad,
                tipo,
                estado
            FROM mesas
            ORDER BY id_mesa
        """)

        return cursor.fetchall()

    finally:

        if cursor:
            cursor.close()

        if conexion:
            conexion.close()


# ==========================================
# MOSTRAR FORMULARIO Y REGISTRAR RESERVACIÓN
# ==========================================

@reservaciones_bp.route("/", methods=["GET", "POST"])
def index():

    conexion = None
    cursor = None

    # ======================================
    # MOSTRAR FORMULARIO
    # ======================================

    if request.method == "GET":

        try:

            mesas = obtener_mesas()

            return render_template(
                "reservaciones.html",
                mesas=mesas
            )

        except Exception as error:

            print(
                "ERROR AL CONSULTAR MESAS:",
                repr(error)
            )

            flash(
                "No fue posible cargar las mesas. Intenta nuevamente.",
                "error"
            )

            return render_template(
                "reservaciones.html",
                mesas=[]
            )

    # ======================================
    # REGISTRAR RESERVACIÓN
    # ======================================

    try:

        conexion = obtener_conexion()

        if conexion is None:

            flash(
                "No fue posible conectar con la base de datos.",
                "error"
            )

            return redirect(
                url_for("reservaciones.index")
            )

        cursor = conexion.cursor()

        # ----------------------------------
        # RECIBIR DATOS DEL FORMULARIO
        # ----------------------------------

        nombre = request.form.get(
            "nombre_cliente", ""
        ).strip()

        correo = request.form.get(
            "correo", ""
        ).strip()

        telefono = request.form.get(
            "telefono", ""
        ).strip()

        fecha = request.form.get(
            "fecha", ""
        ).strip()

        hora = request.form.get(
            "hora", ""
        ).strip()

        numero_personas = request.form.get(
            "numero_personas", ""
        ).strip()

        observaciones = request.form.get(
            "observaciones", ""
        ).strip()

        id_mesa = request.form.get(
            "id_mesa", ""
        ).strip()

        # ----------------------------------
        # VALIDAR CAMPOS OBLIGATORIOS
        # ----------------------------------

        if not all([
            nombre,
            correo,
            telefono,
            fecha,
            hora,
            numero_personas,
            id_mesa
        ]):

            flash(
                "Completa todos los campos obligatorios.",
                "error"
            )

            return redirect(
                url_for("reservaciones.index")
            )

        # ----------------------------------
        # VALIDAR FECHA, HORA Y NÚMEROS
        # ----------------------------------

        try:

            fecha_reserva = datetime.strptime(
                fecha,
                "%Y-%m-%d"
            ).date()

            datetime.strptime(
                hora,
                "%H:%M"
            )

            personas = int(numero_personas)
            mesa_id = int(id_mesa)

        except ValueError:

            flash(
                "Verifica la fecha, hora, personas y mesa seleccionada.",
                "error"
            )

            return redirect(
                url_for("reservaciones.index")
            )

        if fecha_reserva < date.today():

            flash(
                "No puedes reservar en una fecha anterior a hoy.",
                "error"
            )

            return redirect(
                url_for("reservaciones.index")
            )

        if personas <= 0 or personas > 8:

            flash(
                "El número de personas no es válido.",
                "error"
            )

            return redirect(
                url_for("reservaciones.index")
            )

        # ----------------------------------
        # VERIFICAR MESA Y CAPACIDAD
        # ----------------------------------

        cursor.execute("""
            SELECT
                capacidad,
                estado,
                nombre_mesa
            FROM mesas
            WHERE id_mesa = %s
        """, (mesa_id,))

        mesa = cursor.fetchone()

        if not mesa:

            flash(
                "La mesa seleccionada no existe.",
                "error"
            )

            return redirect(
                url_for("reservaciones.index")
            )

        capacidad = mesa[0]
        estado_mesa = mesa[1]
        nombre_mesa = mesa[2]

        if estado_mesa != "Activa":

            flash(
                "La mesa seleccionada no está activa.",
                "error"
            )

            return redirect(
                url_for("reservaciones.index")
            )

        if personas > capacidad:

            flash(
                f"La mesa seleccionada tiene capacidad para {capacidad} personas.",
                "error"
            )

            return redirect(
                url_for("reservaciones.index")
            )

        # ----------------------------------
        # VERIFICAR DISPONIBILIDAD
        # ----------------------------------
        # Una mesa solamente puede tener
        # una reservación activa por día.
        # No importa la hora seleccionada.

        cursor.execute("""
            SELECT id_reservacion
            FROM reservaciones
            WHERE id_mesa = %s
              AND fecha = %s
              AND estado = 'Reservada'
            LIMIT 1
        """, (mesa_id, fecha_reserva))

        reservacion_existente = cursor.fetchone()

        if reservacion_existente:

            flash(
                "Esta mesa ya tiene una reservación para ese día. Selecciona otra mesa o fecha.",
                "error"
            )

            return redirect(
                url_for("reservaciones.index")
            )

        # ==================================
        # BUSCAR O REGISTRAR CLIENTE
        # ==================================

        cursor.execute("""
            SELECT id_cliente
            FROM clientes
            WHERE correo = %s
            LIMIT 1
        """, (correo,))

        cliente = cursor.fetchone()

        if cliente:

            # El cliente ya existe
            id_cliente = cliente[0]

            # Actualizar sus datos de contacto
            cursor.execute("""
                UPDATE clientes
                SET nombre = %s,
                    telefono = %s
                WHERE id_cliente = %s
            """, (
                nombre,
                telefono,
                id_cliente
            ))

        else:

            # Registrar cliente nuevo
            cursor.execute("""
                INSERT INTO clientes (
                    nombre,
                    correo,
                    telefono
                )
                VALUES (%s, %s, %s)
            """, (
                nombre,
                correo,
                telefono
            ))

            id_cliente = cursor.lastrowid

        # ==================================
        # INSERTAR RESERVACIÓN EN MYSQL
        # ==================================

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
            VALUES (
                %s, %s, %s, %s, %s, %s, 'Reservada'
            )
        """, (
            id_cliente,
            mesa_id,
            fecha_reserva,
            hora,
            personas,
            observaciones
        ))

        # Obtener ID generado por MySQL
        id_reservacion = cursor.lastrowid

        # Confirmar la transacción
        conexion.commit()

        print(
            "RESERVACIÓN GUARDADA CORRECTAMENTE:",
            id_reservacion
        )

        print(
            "CLIENTE RELACIONADO:",
            id_cliente
        )

        # ==================================
        # PREPARAR DATOS DEL COMPROBANTE
        # ==================================

        datos_reserva = {

            "id_reservacion": id_reservacion,

            "nombre_cliente": nombre,

            "correo": correo,

            "telefono": telefono,

            "fecha": fecha_reserva,

            "hora": hora,

            "numero_personas": personas,

            "nombre_mesa": nombre_mesa,

            "observaciones": observaciones

        }

        # ==================================
        # GENERAR PDF Y ENVIAR CORREO
        # ==================================

        try:

            pdf = generar_pdf_reservacion(
                datos_reserva
            )

            print(
                "PDF GENERADO CORRECTAMENTE."
            )

            enviar_correo_reservacion(
                correo,
                nombre,
                pdf
            )

            print(
                "CORREO ENVIADO CORRECTAMENTE A:",
                correo
            )

            flash(
                "¡Reservación registrada! Tu comprobante PDF fue enviado a tu correo.",
                "success"
            )

        except Exception as error:

            print(
                "ERROR AL GENERAR O ENVIAR EL COMPROBANTE:",
                repr(error)
            )

            flash(
                "Tu reservación quedó guardada, pero no se pudo enviar el comprobante. Contacta al establecimiento.",
                "error"
            )

        return redirect(
            url_for("reservaciones.index")
        )

    except Exception as error:

        if conexion:

            try:
                conexion.rollback()
            except Exception:
                pass

        print(
            "ERROR REAL AL REGISTRAR RESERVACIÓN:",
            repr(error)
        )

        flash(
            "Ocurrió un error al registrar tu reservación. Revisa la terminal.",
            "error"
        )

        return redirect(
            url_for("reservaciones.index")
        )

    finally:

        if cursor:

            try:
                cursor.close()
            except Exception:
                pass

        if conexion:

            try:
                conexion.close()
            except Exception:
                pass


# ==========================================
# CONSULTAR DISPONIBILIDAD DE MESAS POR FECHA
# ==========================================

@reservaciones_bp.route("/mesas-ocupadas")
def mesas_ocupadas():

    conexion = None
    cursor = None

    try:

        fecha = request.args.get(
            "fecha", ""
        ).strip()

        if not fecha:

            return jsonify({
                "ocupadas": []
            })

        # Validar formato de fecha
        fecha_consulta = datetime.strptime(
            fecha,
            "%Y-%m-%d"
        ).date()

        conexion = obtener_conexion()

        if conexion is None:

            return jsonify({
                "error": "No fue posible conectar con MySQL."
            }), 500

        cursor = conexion.cursor()

        # Consultar mesas reservadas para esa fecha
        # Se bloquea todo el día, sin importar la hora.

        cursor.execute("""
            SELECT DISTINCT id_mesa
            FROM reservaciones
            WHERE fecha = %s
              AND estado = 'Reservada'
        """, (fecha_consulta,))

        resultados = cursor.fetchall()

        ids_ocupadas = [
            int(fila[0])
            for fila in resultados
        ]

        return jsonify({
            "ocupadas": ids_ocupadas
        })

    except ValueError:

        return jsonify({
            "error": "La fecha proporcionada no es válida."
        }), 400

    except Exception as error:

        print(
            "ERROR AL CONSULTAR DISPONIBILIDAD:",
            repr(error)
        )

        return jsonify({
            "error": "No fue posible consultar las mesas."
        }), 500

    finally:

        if cursor:

            cursor.close()

        if conexion:

            conexion.close()


# ==========================================
# VISTA PREVIA DEL COMPROBANTE PDF
# ==========================================

@reservaciones_bp.route("/vista-previa")
def vista_previa():

    datos_ejemplo = {

        "id_reservacion": 1,

        "nombre_cliente": "Ingrid Paola Juárez Soto",

        "correo": "paola.juarez@email.com",

        "telefono": "55 1234 5678",

        "fecha": date(2026, 11, 14),

        "hora": "19:00",

        "numero_personas": 4,

        "nombre_mesa": "Mesa 4",

        "observaciones": "Celebración de cumpleaños."

    }

    try:

        pdf = generar_pdf_reservacion(
            datos_ejemplo
        )

        return send_file(
            BytesIO(pdf),
            mimetype="application/pdf",
            as_attachment=False,
            download_name="Vista_Previa_La_Cantina.pdf"
        )

    except Exception as error:

        print(
            "ERROR AL GENERAR VISTA PREVIA:",
            repr(error)
        )

        return (
            "No se pudo generar el comprobante. Revisa la terminal.",
            500
        )
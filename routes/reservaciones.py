import uuid

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    send_file,
    jsonify,
    session
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
              AND estado IN ('Reservada', 'Confirmada', 'En curso')
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
              AND estado IN  ('Reservada', 'Confirmada', 'En curso')
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


# ==========================================
# ACTUALIZAR ESTADO DE UNA RESERVACIÓN
# AL RECIBIR CLIENTE, ABRIR CUENTA AUTOMÁTICA
# ==========================================

@reservaciones_bp.route(
    "/admin/api/<int:id_reservacion>/estado",
    methods=["POST"]
)
def actualizar_estado_reservacion(id_reservacion):

    if "id_usuario" not in session:
        return jsonify({
            "ok": False,
            "mensaje": "Debes iniciar sesión."
        }), 401

    rol = str(session.get("rol", "")).strip().lower()

    if rol not in ["administrador", "gerente", "recepcionista"]:
        return jsonify({
            "ok": False,
            "mensaje": "No tienes autorización."
        }), 403

    datos = request.get_json(silent=True) or {}
    nuevo_estado = str(datos.get("estado", "")).strip()

    estados_permitidos = [
        "Confirmada",
        "En curso",
        "Finalizada",
        "Cancelada"
    ]

    if nuevo_estado not in estados_permitidos:
        return jsonify({
            "ok": False,
            "mensaje": "Estado no válido."
        }), 400

    conexion = None
    cursor = None

    try:
        conexion = obtener_conexion()

        if conexion is None:
            raise Exception("No fue posible conectar con MySQL.")

        cursor = conexion.cursor()

        # Obtener los datos de la reservación y bloquear el registro.
        cursor.execute("""
            SELECT
                r.estado,
                r.id_mesa,
                c.nombre
            FROM reservaciones r
            INNER JOIN clientes c
                ON c.id_cliente = r.id_cliente
            WHERE r.id_reservacion = %s
            FOR UPDATE
        """, (id_reservacion,))

        reservacion = cursor.fetchone()

        if not reservacion:
            return jsonify({
                "ok": False,
                "mensaje": "La reservación no existe."
            }), 404

        estado_actual, id_mesa, nombre_cliente = reservacion

        if estado_actual in ["Finalizada", "Cancelada"]:
            return jsonify({
                "ok": False,
                "mensaje": "Esta reservación ya está cerrada."
            }), 400

        id_venta = None
        folio = None

        # ======================================
        # RECIBIR CLIENTE Y ABRIR CUENTA
        # ======================================

        if nuevo_estado == "En curso":

            # Comprobar si ya existe una cuenta abierta para esa mesa.
            cursor.execute("""
                SELECT id_venta, folio
                FROM ventas
                WHERE id_mesa = %s
                  AND tipo_cuenta = 'Mesa'
                  AND estado = 'Abierta'
                LIMIT 1
                FOR UPDATE
            """, (id_mesa,))

            cuenta_existente = cursor.fetchone()

            if cuenta_existente:

                if estado_actual == "En curso":
                    id_venta, folio = cuenta_existente

                else:
                    return jsonify({
                        "ok": False,
                        "mensaje": (
                            "La mesa ya tiene una cuenta abierta. "
                            "Revisa la mesa antes de recibir esta reservación."
                        )
                    }), 409

            else:

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
                        %s, 'Mesa', %s, %s, %s,
                        0, 0, NULL, 'Abierta'
                    )
                """, (
                    session["id_usuario"],
                    id_mesa,
                    nombre_cliente,
                    folio
                ))

                id_venta = cursor.lastrowid

        # ======================================
        # ACTUALIZAR ESTADO DE LA RESERVACIÓN
        # ======================================

        cursor.execute("""
            UPDATE reservaciones
            SET estado = %s
            WHERE id_reservacion = %s
        """, (
            nuevo_estado,
            id_reservacion
        ))

        conexion.commit()

        mensajes = {
            "Confirmada": "Reservación confirmada.",
            "En curso": (
                "Cliente recibido. "
                "La cuenta de la mesa se abrió correctamente."
            ),
            "Finalizada": "Reservación finalizada.",
            "Cancelada": "Reservación cancelada."
        }

        return jsonify({
            "ok": True,
            "mensaje": mensajes[nuevo_estado],
            "estado": nuevo_estado,
            "id_venta": id_venta,
            "folio": folio
        })

    except Exception as error:

        if conexion:
            conexion.rollback()

        print(
            "ERROR AL ACTUALIZAR RESERVACIÓN / ABRIR CUENTA:",
            repr(error)
        )

        return jsonify({
            "ok": False,
            "mensaje": (
                "No fue posible actualizar la reservación "
                "ni abrir la cuenta."
            )
        }), 500

    finally:

        if cursor:
            cursor.close()

        if conexion:
            conexion.close()
    
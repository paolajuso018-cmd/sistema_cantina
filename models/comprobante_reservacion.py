import os
import smtplib
from io import BytesIO
from datetime import datetime
from email.message import EmailMessage

from flask import current_app

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image
)


# ==========================================
# COLORES DE LA CANTINA
# ==========================================

VINO = colors.HexColor("#762F2C")
VINO_OSCURO = colors.HexColor("#5B1E20")
DORADO = colors.HexColor("#B58A4A")
MARFIL = colors.HexColor("#F2EBDD")
CAFE = colors.HexColor("#241D1A")
BEIGE = colors.HexColor("#F8E5CC")


# ==========================================
# FECHA EN ESPAÑOL
# ==========================================

def fecha_espanol(fecha):

    if isinstance(fecha, str):
        fecha = datetime.strptime(fecha, "%Y-%m-%d").date()

    dias = [
        "lunes", "martes", "miércoles", "jueves",
        "viernes", "sábado", "domingo"
    ]

    meses = [
        "enero", "febrero", "marzo", "abril",
        "mayo", "junio", "julio", "agosto",
        "septiembre", "octubre", "noviembre", "diciembre"
    ]

    return (
        f"{dias[fecha.weekday()]}, {fecha.day} "
        f"de {meses[fecha.month - 1]} de {fecha.year}"
    )


# ==========================================
# FONDO DECORATIVO DEL PDF
# ==========================================
def dibujar_fondo(canvas, documento):

    ancho, alto = A4

    canvas.saveState()

    ruta_fondo = os.path.join(
        current_app.root_path,
        "static",
        "img",
        "fondo_comprobante.png"
    )

    if os.path.exists(ruta_fondo):

        canvas.drawImage(
            ruta_fondo,
            0,
            0,
            width=ancho,
            height=alto,
            preserveAspectRatio=False,
            mask="auto"
        )

    else:
        canvas.setFillColor(MARFIL)
        canvas.rect(0, 0, ancho, alto, fill=1, stroke=0)

    canvas.restoreState()

# ==========================================
# GENERAR COMPROBANTE PDF
# ==========================================

def generar_pdf_reservacion(datos):

    archivo = BytesIO()

    documento = SimpleDocTemplate(
        archivo,
        pagesize=A4,
        rightMargin=23 * mm,
        leftMargin=23 * mm,
        topMargin=17 * mm,
        bottomMargin=21 * mm
    )

    estilos = getSampleStyleSheet()

    estilo_titulo = ParagraphStyle(
        "TituloCantina",
        parent=estilos["Title"],
        fontName="Helvetica-Bold",
        fontSize=21,
        leading=25,
        textColor=colors.white,
        alignment=TA_CENTER
    )

    estilo_saludo = ParagraphStyle(
        "Saludo",
        parent=estilos["Normal"],
        fontName="Times-Bold",
        fontSize=19,
        leading=23,
        textColor=VINO,
        alignment=TA_CENTER
    )

    estilo_texto = ParagraphStyle(
        "Texto",
        parent=estilos["Normal"],
        fontName="Times-Roman",
        fontSize=11,
        leading=15,
        textColor=CAFE,
        alignment=TA_CENTER
    )

    estilo_etiqueta = ParagraphStyle(
        "Etiqueta",
        parent=estilos["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=VINO_OSCURO
    )

    estilo_valor = ParagraphStyle(
        "Valor",
        parent=estilos["Normal"],
        fontName="Times-Roman",
        fontSize=10,
        leading=12,
        textColor=CAFE
    )

    estilo_final = ParagraphStyle(
        "Final",
        parent=estilos["Normal"],
        fontName="Times-BoldItalic",
        fontSize=17,
        leading=21,
        textColor=VINO,
        alignment=TA_CENTER
    )

    contenido = []

    # --------------------------------------
    # LOGOTIPO
    # --------------------------------------

    ruta_logo = os.path.join(
        current_app.root_path,
        "static",
        "img",
        "logo_portada.png"
    )

    if os.path.exists(ruta_logo):

        logo = Image(
            ruta_logo,
            width=70 * mm,
            height=40 * mm,
            kind="proportional"
        )

        logo.hAlign = "CENTER"
        contenido.append(logo)

    else:

        contenido.append(
            Paragraph("LA CANTINA", estilo_saludo)
        )

    contenido.append(Spacer(1, 4 * mm))

    # --------------------------------------
    # ENCABEZADO VINO
    # --------------------------------------

    titulo = Table(
        [[Paragraph("CONFIRMACIÓN DE RESERVA", estilo_titulo)]],
        colWidths=[164 * mm],
        rowHeights=[17 * mm]
    )

    titulo.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), VINO),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROUNDEDCORNERS", [7, 7, 7, 7]),
        ("LEFTPADDING", (0, 0), (-1, -1), 5 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5 * mm)
    ]))

    contenido.append(titulo)
    contenido.append(Spacer(1, 7 * mm))

    # --------------------------------------
    # SALUDO PERSONALIZADO
    # --------------------------------------

    contenido.append(
        Paragraph(
            f"¡Hola, {datos['nombre_cliente']}!",
            estilo_saludo
        )
    )

    contenido.append(Spacer(1, 2 * mm))

    contenido.append(
        Paragraph(
            "Tu reserva en <b>La Cantina</b> ha sido confirmada "
            "con éxito.<br/>A continuación, te compartimos los detalles:",
            estilo_texto
        )
    )

    contenido.append(Spacer(1, 8 * mm))

    # --------------------------------------
    # DATOS DE LA RESERVACIÓN
    # --------------------------------------

    contenido.append(
        Paragraph(
            "<b>DATOS DE LA RESERVA</b>",
            ParagraphStyle(
                "Subtitulo",
                parent=estilo_titulo,
                fontSize=16,
                leading=18
            )
        )
    )

    contenido.append(Spacer(1, 4 * mm))

    observaciones = datos.get("observaciones") or "Sin observaciones"

    filas = [
        [
            Paragraph("Nombre:", estilo_etiqueta),
            Paragraph(datos["nombre_cliente"], estilo_valor)
        ],
        [
            Paragraph("Correo electrónico:", estilo_etiqueta),
            Paragraph(datos["correo"], estilo_valor)
        ],
        [
            Paragraph("Teléfono:", estilo_etiqueta),
            Paragraph(datos["telefono"], estilo_valor)
        ],
        [
            Paragraph("Fecha:", estilo_etiqueta),
            Paragraph(fecha_espanol(datos["fecha"]), estilo_valor)
        ],
        [
            Paragraph("Hora:", estilo_etiqueta),
            Paragraph(str(datos["hora"])[:5] + " h", estilo_valor)
        ],
        [
            Paragraph("Número de personas:", estilo_etiqueta),
            Paragraph(str(datos["numero_personas"]), estilo_valor)
        ],
        [
            Paragraph("Mesa asignada:", estilo_etiqueta),
            Paragraph(
                f"<b>{datos['nombre_mesa']}</b>",
                estilo_valor
            )
        ],
        [
            Paragraph("Observaciones:", estilo_etiqueta),
            Paragraph(observaciones, estilo_valor)
        ]
    ]

    tabla = Table(
        filas,
        colWidths=[61 * mm, 103 * mm],
        rowHeights=[11 * mm] * 8
    )

    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), BEIGE),
        ("BACKGROUND", (1, 0), (1, -1), colors.HexColor("#FFF3E2")),
        ("BOX", (0, 0), (-1, -1), 1, VINO),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, DORADO),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm),
        ("ROUNDEDCORNERS", [5, 5, 5, 5])
    ]))

    contenido.append(tabla)

    contenido.append(Spacer(1, 10 * mm))

    # --------------------------------------
    # RECORDATORIO
    # --------------------------------------

    contenido.append(
        Paragraph(
            "Te recordamos llegar 10 minutos antes de tu reserva.",
            ParagraphStyle(
                "Recordatorio",
                parent=estilo_texto,
                fontName="Times-Bold",
                fontSize=10
            )
        )
    )

    contenido.append(Spacer(1, 10 * mm))

    # --------------------------------------
    # MENSAJE FINAL
    # --------------------------------------

    contenido.append(
        Paragraph(
            "¡Gracias por reservar en La Cantina!",
            estilo_final
        )
    )

    contenido.append(Spacer(1, 3 * mm))

    contenido.append(
        Paragraph(
            "Te esperamos para que disfrutes de una gran experiencia "
            "llena de tradición y buen ambiente.",
            estilo_texto
        )
    )

    documento.build(
        contenido,
        onFirstPage= dibujar_fondo,
        onLaterPages= dibujar_fondo
    )

    archivo.seek(0)

    return archivo.getvalue()


# ==========================================
# ENVIAR PDF POR CORREO
# ==========================================

def enviar_correo_reservacion(destinatario, nombre, pdf_bytes):

    servidor = current_app.config.get("MAIL_SERVER")
    puerto = current_app.config.get("MAIL_PORT")
    usuario = current_app.config.get("MAIL_USERNAME")
    contrasena = current_app.config.get("MAIL_PASSWORD")
    remitente = current_app.config.get("MAIL_DEFAULT_SENDER")

    if not all([servidor, puerto, usuario, contrasena, remitente]):
        raise ValueError(
            "Falta configurar el correo electrónico en el archivo .env."
        )

    mensaje = EmailMessage()

    mensaje["Subject"] = "Confirmación de tu reserva | La Cantina"
    mensaje["From"] = remitente
    mensaje["To"] = destinatario

    mensaje.set_content(
        f"Hola, {nombre}.\n\n"
        "Tu reservación en La Cantina ha sido confirmada.\n"
        "Adjuntamos tu comprobante en formato PDF.\n\n"
        "¡Gracias por reservar con nosotros!"
    )

    mensaje.add_attachment(
        pdf_bytes,
        maintype="application",
        subtype="pdf",
        filename="Comprobante_Reservacion_La_Cantina.pdf"
    )

    with smtplib.SMTP(servidor, puerto) as smtp:

        smtp.starttls()
        smtp.login(usuario, contrasena)
        smtp.send_message(mensaje)
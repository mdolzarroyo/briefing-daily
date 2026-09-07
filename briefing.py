#!/usr/bin/env python3
"""
Briefing macroeconómico y geopolítico automático.
Genera un análisis usando la API de Anthropic (con búsqueda web) y lo envía por email.

Uso:
    python briefing.py

Variables de entorno requeridas (ver .env.example):
    ANTHROPIC_API_KEY   - tu API key de Anthropic (console.anthropic.com)
    SMTP_HOST           - servidor SMTP (ej: smtp.gmail.com)
    SMTP_PORT           - puerto SMTP (ej: 587)
    SMTP_USER           - usuario/email remitente
    SMTP_PASSWORD       - contraseña o "app password" del remitente
    RECIPIENT_EMAIL     - destinatario (mdolzaaroyo@gmail.com por defecto)
"""

import os
import re
import smtplib
import ssl
import sys
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from zoneinfo import ZoneInfo

import anthropic
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

# ---------- Configuración ----------
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ["SMTP_USER"]
SMTP_PASSWORD = os.environ["SMTP_PASSWORD"]
RECIPIENT_EMAIL = os.environ.get("RECIPIENT_EMAIL", "mdolzaaroyo@gmail.com")

MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """Eres un analista macroeconómico y geopolítico senior. Generas
briefings de inteligencia de mercado en español, con estilo terso y directivo,
sin elaboración conversacional innecesaria.

Estructura obligatoria:
1. **Panorama global** — principales desarrollos geopolíticos y macro de las
   últimas horas (usa búsqueda web para datos actuales).
2. **Revisión de mercado** — precios de referencia (Brent/WTI, treasuries,
   índices bursátiles, forex relevante) con variación reciente.
3. **Lectura conjunta** — síntesis que conecta los temas macro con las
   implicaciones de mercado.

Sé concreto, cita cifras y fechas, evita relleno. Usa búsqueda web para
verificar cualquier dato que pueda haber cambiado recientemente."""

USER_PROMPT = """Genera el briefing macro de hoy. Cubre como mínimo:
- Estado del conflicto EEUU-Irán y su impacto en el Estrecho de Hormuz y precios
  de energía
- Postura de la Fed (Kevin Warsh) de cara a la próxima reunión, y probabilidades
  de mercado de subida de tipos
- Datos de mercado laboral relevantes recientes
- Movimientos de mercado del día/sesión más reciente (Brent, WTI, treasuries,
  índices bursátiles)
- Cualquier otro desarrollo geopolítico/macro de peso (BCE, flujos de deuda
  soberana, Latinoamérica, etc.) si hay novedades

Formato en Markdown, listo para enviar por email."""


def markdown_inline_a_reportlab(texto: str) -> str:
    """Convierte negrita/cursiva markdown básica a las etiquetas XML de ReportLab."""
    texto = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", texto)
    texto = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<i>\1</i>", texto)
    return texto


def construir_pdf(cuerpo_markdown: str, ruta_salida: str) -> None:
    """Genera un PDF con formato legible a partir del briefing en Markdown."""
    doc = SimpleDocTemplate(
        ruta_salida,
        pagesize=A4,
        topMargin=2.2 * cm,
        bottomMargin=2 * cm,
        leftMargin=2.2 * cm,
        rightMargin=2.2 * cm,
        title="Briefing macro",
    )

    styles = getSampleStyleSheet()

    estilo_titulo = ParagraphStyle(
        "TituloBriefing",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=20,
        textColor="#1a1a2e",
        spaceAfter=4,
    )
    estilo_fecha = ParagraphStyle(
        "Fecha",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        textColor="#666666",
        spaceAfter=16,
    )
    estilo_h1 = ParagraphStyle(
        "Seccion",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=14,
        textColor="#16213e",
        spaceBefore=18,
        spaceAfter=8,
    )
    estilo_h2 = ParagraphStyle(
        "Subseccion",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        textColor="#0f3460",
        spaceBefore=12,
        spaceAfter=6,
    )
    estilo_cuerpo = ParagraphStyle(
        "Cuerpo",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10.5,
        leading=15,
        alignment=TA_JUSTIFY,
        spaceAfter=8,
    )
    estilo_lista = ParagraphStyle(
        "Lista",
        parent=estilo_cuerpo,
        spaceAfter=4,
    )

    story = []
    ahora = datetime.now(ZoneInfo("Europe/Madrid"))
    dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
    meses = [
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
    ]
    fecha_es = (
        f"{dias[ahora.weekday()]}, {ahora.day} de {meses[ahora.month - 1]} "
        f"de {ahora.year} — {ahora.strftime('%H:%M')} (Madrid)"
    )
    story.append(Paragraph("Briefing macro y geopolítico", estilo_titulo))
    story.append(Paragraph(fecha_es, estilo_fecha))
    story.append(HRFlowable(width="100%", thickness=1, color="#cccccc", spaceAfter=10))

    lineas = cuerpo_markdown.split("\n")
    items_lista_actual = []

    def volcar_lista():
        nonlocal items_lista_actual
        if items_lista_actual:
            story.append(
                ListFlowable(
                    [ListItem(Paragraph(it, estilo_lista)) for it in items_lista_actual],
                    bulletType="bullet",
                    leftIndent=14,
                )
            )
            items_lista_actual = []

    for linea in lineas:
        linea = linea.rstrip()

        if not linea.strip():
            volcar_lista()
            continue

        # Encabezados markdown
        if linea.startswith("### "):
            volcar_lista()
            story.append(Paragraph(markdown_inline_a_reportlab(linea[4:]), estilo_h2))
        elif linea.startswith("## "):
            volcar_lista()
            story.append(Paragraph(markdown_inline_a_reportlab(linea[3:]), estilo_h2))
        elif linea.startswith("# "):
            volcar_lista()
            story.append(Paragraph(markdown_inline_a_reportlab(linea[2:]), estilo_h1))
        elif re.match(r"^\d+\.\s+\*\*", linea) or re.match(r"^\*\*\d", linea):
            # Línea tipo "1. **Título**" -> tratar como sub-encabezado
            volcar_lista()
            texto = re.sub(r"^\d+\.\s+", "", linea)
            story.append(Paragraph(markdown_inline_a_reportlab(texto), estilo_h1))
        elif linea.startswith(("- ", "* ")):
            items_lista_actual.append(markdown_inline_a_reportlab(linea[2:]))
        else:
            volcar_lista()
            story.append(Paragraph(markdown_inline_a_reportlab(linea), estilo_cuerpo))

    volcar_lista()
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=0.5, color="#dddddd"))
    story.append(
        Paragraph(
            "Generado automáticamente. No constituye asesoramiento financiero.",
            ParagraphStyle("Pie", parent=styles["Normal"], fontSize=8, textColor="#999999", spaceBefore=6),
        )
    )

    doc.build(story)


def generar_briefing() -> str:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    response = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": USER_PROMPT}],
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
    )

    # Concatenar todos los bloques de texto de la respuesta (puede haber
    # varios si el modelo intercala búsquedas con texto)
    texto = "\n".join(
        block.text for block in response.content if block.type == "text"
    )
    return texto


def enviar_email(cuerpo_markdown: str, ruta_pdf: str) -> None:
    ahora = datetime.now().strftime("%d/%m/%Y %H:%M")
    asunto = f"Briefing macro — {ahora}"

    msg = MIMEMultipart()
    msg["Subject"] = asunto
    msg["From"] = SMTP_USER
    msg["To"] = RECIPIENT_EMAIL

    cuerpo_correo = (
        "Adjunto el briefing macro de hoy en PDF.\n\n"
        "— Enviado automáticamente."
    )
    msg.attach(MIMEText(cuerpo_correo, "plain", "utf-8"))

    with open(ruta_pdf, "rb") as f:
        adjunto = MIMEApplication(f.read(), _subtype="pdf")
        nombre_archivo = f"briefing-{datetime.now().strftime('%Y-%m-%d_%H%M')}.pdf"
        adjunto.add_header(
            "Content-Disposition", "attachment", filename=nombre_archivo
        )
        msg.attach(adjunto)

    context = ssl.create_default_context()
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls(context=context)
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, RECIPIENT_EMAIL, msg.as_string())


def hora_objetivo_madrid() -> bool:
    """Comprueba si la hora actual en Madrid está cerca de las 8:00 o 22:00.

    Esto permite que el workflow de GitHub Actions se dispare 4 veces al día
    (para cubrir verano/invierno) pero solo se ejecute de verdad 2 veces.
    Si se ejecuta manualmente (workflow_dispatch) o localmente, se ignora
    esta comprobación mediante la variable IGNORAR_HORARIO=1.
    """
    if os.environ.get("IGNORAR_HORARIO") == "1":
        return True

    ahora_madrid = datetime.now(ZoneInfo("Europe/Madrid"))
    return ahora_madrid.hour in (8, 22)


def main():
    if not hora_objetivo_madrid():
        print(
            f"[{datetime.now()}] No es hora de enviar briefing "
            "(objetivo: 8:00 o 22:00 hora de Madrid). Saliendo sin hacer nada."
        )
        sys.exit(0)

    print(f"[{datetime.now()}] Generando briefing...")
    briefing_md = generar_briefing()

    print(f"[{datetime.now()}] Maquetando PDF...")
    ruta_pdf = "/tmp/briefing.pdf"
    construir_pdf(briefing_md, ruta_pdf)

    print(f"[{datetime.now()}] Enviando email a {RECIPIENT_EMAIL}...")
    enviar_email(briefing_md, ruta_pdf)
    print(f"[{datetime.now()}] Listo.")


if __name__ == "__main__":
    main()

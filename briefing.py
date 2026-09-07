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
import smtplib
import ssl
import sys
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from zoneinfo import ZoneInfo

import anthropic

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


def enviar_email(cuerpo_markdown: str) -> None:
    ahora = datetime.now().strftime("%d/%m/%Y %H:%M")
    asunto = f"Briefing macro — {ahora}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = asunto
    msg["From"] = SMTP_USER
    msg["To"] = RECIPIENT_EMAIL

    # Versión texto plano
    msg.attach(MIMEText(cuerpo_markdown, "plain", "utf-8"))

    # Versión HTML simple (convierte saltos de línea y negritas básicas)
    html_body = cuerpo_markdown.replace("\n", "<br>")
    html = f"<html><body style='font-family: sans-serif;'>{html_body}</body></html>"
    msg.attach(MIMEText(html, "html", "utf-8"))

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
    briefing = generar_briefing()
    print(f"[{datetime.now()}] Enviando email a {RECIPIENT_EMAIL}...")
    enviar_email(briefing)
    print(f"[{datetime.now()}] Listo.")


if __name__ == "__main__":
    main()

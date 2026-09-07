# Briefing macro automático — configuración

Este sistema genera tu briefing macro/geopolítico dos veces al día (8:00 y
22:00, hora de Madrid) y lo envía a `mdolzaaroyo@gmail.com`, usando GitHub
Actions como "reloj" gratuito (no necesitas tener ningún ordenador
encendido).

## Qué necesitas

1. Una cuenta de GitHub (gratis) — https://github.com
2. Una API key de Anthropic — https://console.anthropic.com/settings/keys
   (esto tiene coste por uso, muy bajo para 2 llamadas/día)
3. Un "App Password" de Gmail para enviar el correo — ver paso 3 abajo

## Paso 1 — Crear el repositorio

1. Entra en GitHub y crea un repositorio nuevo, **privado** (Settings →
   New repository → marca "Private").
2. Sube estos archivos a la raíz del repo:
   - `briefing.py`
   - `requirements.txt`
3. Crea la carpeta `.github/workflows/` dentro del repo y sube ahí el
   archivo `briefing-schedule.yml` (dentro de esa carpeta exacta, GitHub
   lo detecta automáticamente).

Estructura final:
```
tu-repo/
├── briefing.py
├── requirements.txt
└── .github/
    └── workflows/
        └── briefing-schedule.yml
```

## Paso 2 — Conseguir tu API key de Anthropic

1. Ve a https://console.anthropic.com/settings/keys
2. Crea una nueva key y cópiala (empieza por `sk-ant-...`)

## Paso 3 — Crear un "App Password" de Gmail

Gmail no permite usar tu contraseña normal para enviar correos desde un
script. Necesitas una contraseña de aplicación:

1. Activa la verificación en dos pasos en tu cuenta de Google (si no la
   tienes ya): https://myaccount.google.com/security
2. Ve a https://myaccount.google.com/apppasswords
3. Crea una nueva "contraseña de aplicación" (puedes llamarla "Briefing
   macro"). Google te dará un código de 16 caracteres — cópialo.

Puedes usar tu propio Gmail como remitente, o crear uno nuevo solo para
esto si prefieres separar cuentas.

## Paso 4 — Guardar los secretos en GitHub

En tu repositorio: **Settings → Secrets and variables → Actions → New
repository secret**. Crea estos tres secretos:

| Nombre            | Valor                                          |
|-------------------|-------------------------------------------------|
| `ANTHROPIC_API_KEY` | tu key de Anthropic (`sk-ant-...`)             |
| `SMTP_USER`         | tu email de Gmail (el remitente)               |
| `SMTP_PASSWORD`     | el App Password de 16 caracteres del paso 3    |

No hace falta tocar nada más — el destinatario (`mdolzaaroyo@gmail.com`)
ya está fijado en el workflow.

## Paso 5 — Probarlo

1. Ve a la pestaña **Actions** de tu repositorio.
2. Selecciona el workflow "Briefing Macro".
3. Pulsa **Run workflow** (esto lo ejecuta manualmente, ignorando el
   horario, para que puedas comprobar que todo funciona).
4. Revisa tu bandeja de entrada en `mdolzaaroyo@gmail.com`.

Si todo llega bien, ya está: a partir de ahora se enviará solo, todos los
días, a las 8:00 y 22:00 hora de Madrid.

## Notas

- GitHub Actions programa las ejecuciones con cierto margen (puede haber
  algunos minutos de retraso, no es instantáneo al segundo).
- El coste de la API de Anthropic para esto es mínimo (unos céntimos al
  día como mucho, dependiendo del uso de búsqueda web).
- Si quieres cambiar el destinatario o los horarios, edita directamente
  `briefing-schedule.yml` (los cron) y la constante `RECIPIENT_EMAIL` en
  ese mismo archivo.
- Si prefieres NO usar GitHub Actions y correrlo en tu propio servidor,
  basta con añadir estas líneas a tu crontab (`crontab -e`):
  ```
  0 8 * * * cd /ruta/a/briefing_macro && IGNORAR_HORARIO=1 python3 briefing.py
  0 22 * * * cd /ruta/a/briefing_macro && IGNORAR_HORARIO=1 python3 briefing.py
  ```
  (cargando antes las variables de entorno desde tu `.env`).

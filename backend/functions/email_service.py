"""
Envío de correos (OTP de recuperación de contraseña).
Si SMTP no está configurado, se imprime el código en consola (modo desarrollo).
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from App.config import get_settings

settings = get_settings()


def send_otp_email(to_email: str, code: str, username: str | None = None) -> bool:
    """
    Envía el código OTP al correo del usuario.
    Retorna True si se envió (o se simuló) correctamente.
    """
    subject = f"{settings.APP_NAME} – Código de recuperación de contraseña"
    name = username or "usuario"
    body = f"""Hola {name},

Has solicitado restablecer tu contraseña en {settings.APP_NAME}.

Tu código de un solo uso es:

    {code}

Este código expira en {settings.OTP_EXPIRE_MINUTES} minutos.
Si no solicitaste este cambio, ignora este mensaje.

— Equipo {settings.APP_NAME}
"""

    # Modo desarrollo: sin SMTP configurado → solo log
    if not settings.SMTP_HOST or not settings.SMTP_USER:
        print("=" * 50)
        print(f"[DEV] OTP para {to_email}: {code}")
        print(f"[DEV] Válido {settings.OTP_EXPIRE_MINUTES} minutos")
        print("=" * 50)
        return True

    try:
        msg = MIMEMultipart()
        msg["From"] = settings.SMTP_FROM
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"[ERROR] No se pudo enviar correo a {to_email}: {e}")
        # En desarrollo seguimos mostrando el código para no bloquear pruebas
        if settings.DEBUG:
            print(f"[DEV FALLBACK] OTP para {to_email}: {code}")
            return True
        return False

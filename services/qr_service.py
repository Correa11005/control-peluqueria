import re
import secrets
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import os
import qrcode

ACCIONES_VALIDAS = {
    "entrada",
    "salida",
    "inicio_comida",
    "fin_comida",
    "inicio_descanso",
    "fin_descanso"
}


def generar_qr_token():
    return secrets.token_urlsafe(32)


def validar_pin(pin: str) -> bool:
    return bool(re.fullmatch(r"\d{4}", pin or ""))


def hash_pin(pin: str) -> str:
    if not validar_pin(pin):
        raise ValueError("El PIN debe tener exactamente 4 dígitos.")
    return generate_password_hash(pin)


def verificar_pin(pin_plano: str, pin_hash: str) -> bool:
    if not pin_hash:
        return False
    return check_password_hash(pin_hash, pin_plano)


def empleado_bloqueado(bloqueado_hasta):
    if not bloqueado_hasta:
        return False
    return datetime.now() < bloqueado_hasta


def calcular_bloqueo(intentos_fallidos: int):
    if intentos_fallidos >= 5:
        return datetime.now() + timedelta(minutes=5)
    return None


def generar_imagen_qr(url: str, nombre_archivo: str):
    carpeta = os.path.join("static", "qr")
    os.makedirs(carpeta, exist_ok=True)

    ruta = os.path.join(carpeta, f"{nombre_archivo}.png")

    qr = qrcode.QRCode(
        version=1,
        box_size=10,
        border=4
    )
    qr.add_data(url)
    qr.make(fit=True)

    imagen = qr.make_image(fill_color="black", back_color="white")
    imagen.save(ruta)

    return ruta
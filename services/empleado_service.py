from services.qr_service import generar_qr_token, hash_pin


def configurar_qr_y_pin(conn, empleado_id: int, pin: str):
    token = generar_qr_token()
    pin_hash = hash_pin(pin)

    cursor = conn.cursor()
    cursor.execute("""
        UPDATE empleados
        SET qr_token = %s,
            pin_hash = %s,
            pin_intentos_fallidos = 0,
            bloqueado_hasta = NULL,
            activo = 1
        WHERE id = %s
    """, (token, pin_hash, empleado_id))
    conn.commit()
    cursor.close()

    return token


def obtener_empleado_por_token(conn, token: str):
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT id, nombre, qr_token, pin_hash, pin_intentos_fallidos,
               bloqueado_hasta, activo
        FROM empleados
        WHERE qr_token = %s
        LIMIT 1
    """, (token,))
    empleado = cursor.fetchone()
    cursor.close()
    return empleado


def resetear_intentos_pin(conn, empleado_id: int):
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE empleados
        SET pin_intentos_fallidos = 0,
            bloqueado_hasta = NULL
        WHERE id = %s
    """, (empleado_id,))
    conn.commit()
    cursor.close()


def registrar_intento_fallido(conn, empleado_id: int, intentos: int, bloqueado_hasta=None):
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE empleados
        SET pin_intentos_fallidos = %s,
            bloqueado_hasta = %s
        WHERE id = %s
    """, (intentos, bloqueado_hasta, empleado_id))
    conn.commit()
    cursor.close()
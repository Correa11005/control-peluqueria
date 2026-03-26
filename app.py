import os
from datetime import datetime
from zoneinfo import ZoneInfo
from services.time_service import aplicar_logica_melany
import mysql.connector
from dotenv import load_dotenv
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS

from services.empleado_service import (
    configurar_qr_y_pin,
    obtener_empleado_por_token,
    resetear_intentos_pin,
    registrar_intento_fallido,
)

from services.qr_service import (
    validar_pin,
    verificar_pin,
    empleado_bloqueado,
    calcular_bloqueo,
    ACCIONES_VALIDAS,
    generar_imagen_qr,
)

load_dotenv()

app = Flask(__name__)
CORS(app)

LIMITE_SEGUNDOS_MELANY = 4 * 3600
TZ_APP = "Europe/Madrid"



def get_db_connection():
    conn = mysql.connector.connect(
        host=os.environ.get("MYSQLHOST"),
        user=os.environ.get("MYSQLUSER"),
        password=os.environ.get("MYSQLPASSWORD"),
        database=os.environ.get("MYSQLDATABASE"),
        port=int(os.environ.get("MYSQLPORT", 3306)),
    )

    cursor = conn.cursor()
    cursor.execute(f"SET time_zone = '{TZ_APP}'")
    cursor.close()

    return conn


def formatear_tiempo(segundos):
    segundos = max(0, int(segundos))
    horas = segundos // 3600
    minutos = (segundos % 3600) // 60
    segs = segundos % 60
    return f"{horas}h {minutos}m {segs}s"


def obtener_ultima_marcacion_hoy(cursor, empleado_id, fecha=None):
    if fecha is None:
        fecha = datetime.now(ZoneInfo(TZ_APP)).date()

    cursor.execute(
        """
        SELECT tipo, fecha_hora
        FROM marcaciones
        WHERE empleado_id = %s
          AND DATE(fecha_hora) = %s
        ORDER BY fecha_hora DESC
        LIMIT 1
        """,
        (empleado_id, fecha),
    )
    return cursor.fetchone()

def calcular_resumen_marcaciones(marcaciones, empleado_id=None, ahora=None):
    entrada = None
    salida = None
    inicio_comida = None
    fin_comida = None
    inicio_descanso = None
    fin_descanso = None

    total_trabajado = 0
    total_comida = 0
    total_descanso = 0

    inicio_trabajo_actual = None
    inicio_comida_actual = None
    inicio_descanso_actual = None

    for m in marcaciones:
        tipo = m["tipo"]
        fecha_hora = m["fecha_hora"]

        if tipo == "entrada":
            if entrada is None:
                entrada = fecha_hora
            inicio_trabajo_actual = fecha_hora

        elif tipo == "inicio_comida":
            if inicio_trabajo_actual:
                total_trabajado += int((fecha_hora - inicio_trabajo_actual).total_seconds())
                inicio_trabajo_actual = None
            if inicio_comida is None:
                inicio_comida = fecha_hora
            inicio_comida_actual = fecha_hora

        elif tipo == "fin_comida":
            if inicio_comida_actual:
                total_comida += int((fecha_hora - inicio_comida_actual).total_seconds())
                inicio_comida_actual = None
            fin_comida = fecha_hora
            inicio_trabajo_actual = fecha_hora

        elif tipo == "inicio_descanso":
            if inicio_trabajo_actual:
                total_trabajado += int((fecha_hora - inicio_trabajo_actual).total_seconds())
                inicio_trabajo_actual = None
            if inicio_descanso is None:
                inicio_descanso = fecha_hora
            inicio_descanso_actual = fecha_hora

        elif tipo == "fin_descanso":
            if inicio_descanso_actual:
                total_descanso += int((fecha_hora - inicio_descanso_actual).total_seconds())
                inicio_descanso_actual = None
            fin_descanso = fecha_hora
            inicio_trabajo_actual = fecha_hora

        elif tipo == "salida":
            if inicio_trabajo_actual:
                total_trabajado += int((fecha_hora - inicio_trabajo_actual).total_seconds())
                inicio_trabajo_actual = None
            salida = fecha_hora

    if ahora and inicio_trabajo_actual:
        extra_trabajo = int((ahora - inicio_trabajo_actual).total_seconds())
        if extra_trabajo > 0:
           total_trabajado += extra_trabajo

    if ahora and inicio_comida_actual:
        extra_comida = int((ahora - inicio_comida_actual).total_seconds())
        if extra_comida > 0:
           total_comida += extra_comida

    if ahora and inicio_descanso_actual:
       extra_descanso = int((ahora - inicio_descanso_actual).total_seconds())
       if extra_descanso > 0:
        total_descanso += extra_descanso
        
    total_trabajado = max(0, total_trabajado)
    total_comida = max(0, total_comida)
    total_descanso = max(0, total_descanso)

    segundos_trabajados_reales = total_trabajado
    segundos_netos_reales = max(0, segundos_trabajados_reales - total_comida - total_descanso)

    segundos_trabajados_mostrados = aplicar_logica_melany(empleado_id, segundos_trabajados_reales)
    segundos_netos_mostrados = aplicar_logica_melany(empleado_id, segundos_netos_reales)

    return {
        "entrada": entrada,
        "salida": salida,
        "inicio_comida": inicio_comida,
        "fin_comida": fin_comida,
        "inicio_descanso": inicio_descanso,
        "fin_descanso": fin_descanso,

        "segundos_trabajados_reales": segundos_trabajados_reales,
        "segundos_comida": total_comida,
        "segundos_descanso": total_descanso,
        "segundos_netos_reales": segundos_netos_reales,

        "segundos_trabajados": segundos_trabajados_mostrados,
        "segundos_netos": segundos_netos_mostrados,
    }

@app.route("/configurar_qr/<int:empleado_id>", methods=["POST"])
def configurar_qr(empleado_id):
    data = request.get_json(silent=True) or {}
    pin = data.get("pin")

    if not pin:
        return jsonify({"error": "PIN requerido"}), 400

    conn = get_db_connection()
    try:
        token = configurar_qr_y_pin(conn, empleado_id, pin)

        base_url = os.environ.get("BASE_URL", "http://127.0.0.1:5000").rstrip("/")
        url_qr = f"{base_url}/marcar?token={token}"
        ruta_qr = generar_imagen_qr(url_qr, f"empleado_{empleado_id}")

        return jsonify({
            "mensaje": "QR configurado correctamente",
            "token": token,
            "url": url_qr,
            "qr_imagen": ruta_qr
        })
    finally:
        conn.close()

@app.route("/empleados")
def empleados():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT id, nombre FROM empleados ORDER BY nombre")
    result = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(result)

@app.route("/marcar", methods=["GET"])
def vista_marcar_qr():
    token = request.args.get("token", "").strip()

    if not token:
        return "Token no proporcionado", 400

    conn = get_db_connection()
    try:
        empleado = obtener_empleado_por_token(conn, token)

        if not empleado or not empleado["activo"]:
            return "Empleado no encontrado o inactivo", 404

        return render_template(
            "marcar_qr.html",
            empleado=empleado,
            token=token
        )
    finally:
        conn.close()
@app.route("/api/marcar_qr", methods=["POST"])
def api_marcar_qr():
    data = request.get_json(silent=True) or {}

    token = (data.get("token") or "").strip()
    pin = (data.get("pin") or "").strip()
    tipo = (data.get("tipo") or "").strip()

    if not token:
        return jsonify({"error": "Token requerido"}), 400

    if tipo not in ACCIONES_VALIDAS:
        return jsonify({"error": "Tipo de marcación inválido"}), 400

    if not validar_pin(pin):
        return jsonify({"error": "PIN inválido. Debe tener 4 dígitos."}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        empleado = obtener_empleado_por_token(conn, token)

        if not empleado or not empleado["activo"]:
            return jsonify({"error": "Empleado no válido o inactivo"}), 404

        if empleado_bloqueado(empleado["bloqueado_hasta"]):
            return jsonify({"error": "Empleado bloqueado temporalmente por intentos fallidos"}), 403

        if not verificar_pin(pin, empleado["pin_hash"]):
            nuevos_intentos = (empleado["pin_intentos_fallidos"] or 0) + 1
            bloqueo = calcular_bloqueo(nuevos_intentos)
            registrar_intento_fallido(conn, empleado["id"], nuevos_intentos, bloqueo)
            return jsonify({"error": "PIN incorrecto"}), 401

        resetear_intentos_pin(conn, empleado["id"])

        hoy = datetime.now(ZoneInfo(TZ_APP)).date()
        ultima = obtener_ultima_marcacion_hoy(cursor, empleado["id"], hoy)
        ultimo_tipo = ultima["tipo"] if ultima else None

        if tipo == "entrada":
            if ultimo_tipo in {"entrada", "fin_comida", "fin_descanso"}:
                return jsonify({"error": "No se puede registrar otra entrada ahora"}), 400

        elif tipo == "salida":
            if ultimo_tipo not in {"entrada", "fin_comida", "fin_descanso"}:
                return jsonify({"error": "No se puede registrar salida sin haber entrado o reanudado"}), 400

        elif tipo == "inicio_comida":
            if ultimo_tipo not in {"entrada", "fin_descanso"}:
                return jsonify({"error": "No se puede iniciar comida en este momento"}), 400

        elif tipo == "fin_comida":
            if ultimo_tipo != "inicio_comida":
                return jsonify({"error": "No se puede finalizar comida sin haberla iniciado"}), 400

        elif tipo == "inicio_descanso":
            if ultimo_tipo not in {"entrada", "fin_comida"}:
                return jsonify({"error": "No se puede iniciar descanso en este momento"}), 400

        elif tipo == "fin_descanso":
            if ultimo_tipo != "inicio_descanso":
                return jsonify({"error": "No se puede finalizar descanso sin haberlo iniciado"}), 400

        cursor.execute(
            "INSERT INTO marcaciones (empleado_id, tipo, fecha_hora) VALUES (%s, %s, NOW())",
            (empleado["id"], tipo),
        )
        conn.commit()

        return jsonify({
            "ok": True,
            "mensaje": f"Marcación registrada: {tipo}",
            "empleado": empleado["nombre"]
        })

    finally:
        cursor.close()
        conn.close()

@app.route("/marcar", methods=["POST"])
def marcar():
    data = request.get_json(silent=True) or {}

    empleado_id = data.get("empleado_id")
    tipo = data.get("tipo")

    tipos_validos = {
        "entrada",
        "salida",
        "inicio_comida",
        "fin_comida",
        "inicio_descanso",
        "fin_descanso",
    }

    if not empleado_id or tipo not in tipos_validos:
        return jsonify({"error": "Datos inválidos"}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    hoy = datetime.now(ZoneInfo(TZ_APP)).date()
    ultima = obtener_ultima_marcacion_hoy(cursor, empleado_id, hoy)
    ultimo_tipo = ultima["tipo"] if ultima else None

    if tipo == "entrada":
        if ultimo_tipo in {"entrada", "fin_comida", "fin_descanso"}:
            cursor.close()
            conn.close()
            return jsonify({"error": "No se puede registrar otra entrada ahora"}), 400

    elif tipo == "salida":
        if ultimo_tipo not in {"entrada", "fin_comida", "fin_descanso"}:
            cursor.close()
            conn.close()
            return jsonify({"error": "No se puede registrar salida sin haber entrado o reanudado"}), 400

    elif tipo == "inicio_comida":
        if ultimo_tipo not in {"entrada", "fin_descanso"}:
            cursor.close()
            conn.close()
            return jsonify({"error": "No se puede iniciar comida en este momento"}), 400

    elif tipo == "fin_comida":
        if ultimo_tipo != "inicio_comida":
            cursor.close()
            conn.close()
            return jsonify({"error": "No se puede finalizar comida sin haberla iniciado"}), 400

    elif tipo == "inicio_descanso":
        if ultimo_tipo not in {"entrada", "fin_comida"}:
            cursor.close()
            conn.close()
            return jsonify({"error": "No se puede iniciar descanso en este momento"}), 400

    elif tipo == "fin_descanso":
        if ultimo_tipo != "inicio_descanso":
            cursor.close()
            conn.close()
            return jsonify({"error": "No se puede finalizar descanso sin haberlo iniciado"}), 400

    cursor.execute(
        "INSERT INTO marcaciones (empleado_id, tipo, fecha_hora) VALUES (%s, %s, NOW())",
        (empleado_id, tipo),
    )
    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({"mensaje": f"Marcación registrada: {tipo}"})


@app.route("/reporte/<int:empleado_id>/<string:fecha>")
def reporte_dia(empleado_id, fecha):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT tipo, fecha_hora
        FROM marcaciones
        WHERE empleado_id = %s AND DATE(fecha_hora) = %s
        ORDER BY fecha_hora ASC
        """,
        (empleado_id, fecha),
    )

    marcaciones = cursor.fetchall()

    cursor.close()
    conn.close()

    resumen = calcular_resumen_marcaciones(marcaciones, empleado_id=empleado_id)

    return jsonify(
        {
            "empleado_id": empleado_id,
            "fecha": fecha,
            "marcaciones": marcaciones,
            "trabajado": formatear_tiempo(resumen["segundos_trabajados"]),
            "comida": formatear_tiempo(resumen["segundos_comida"]),
            "descanso": formatear_tiempo(resumen["segundos_descanso"]),
            "neto": formatear_tiempo(resumen["segundos_netos"]),
            "segundos_trabajados": resumen["segundos_trabajados"],
            "segundos_comida": resumen["segundos_comida"],
            "segundos_descanso": resumen["segundos_descanso"],
            "segundos_netos": resumen["segundos_netos"],
        }
    )


@app.route("/resumen_hoy")
def resumen_hoy():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT id, nombre FROM empleados ORDER BY nombre")
    empleados = cursor.fetchall()

    ahora = datetime.now(ZoneInfo(TZ_APP)).replace(tzinfo=None)
    hoy = ahora.date()
    respuesta = []

    for emp in empleados:
        cursor.execute(
            """
            SELECT tipo, fecha_hora
            FROM marcaciones
            WHERE empleado_id = %s AND DATE(fecha_hora) = %s
            ORDER BY fecha_hora ASC
            """,
            (emp["id"], hoy),
        )
        marcaciones = cursor.fetchall()

        resumen = calcular_resumen_marcaciones(
            marcaciones,
            empleado_id=emp["id"],
            ahora=ahora,
        )

        estado = "sin iniciar"
        ultima_marcacion = None
        desde = None

        if marcaciones:
            ultima = marcaciones[-1]
            ultima_marcacion = ultima["tipo"]

            if ultima["tipo"] in {"entrada", "fin_comida", "fin_descanso"}:
                estado = "trabajando"
                desde = ultima["fecha_hora"]
            elif ultima["tipo"] == "inicio_comida":
                estado = "en comida"
                desde = ultima["fecha_hora"]
            elif ultima["tipo"] == "inicio_descanso":
                estado = "en descanso"
                desde = ultima["fecha_hora"]
            elif ultima["tipo"] == "salida":
                estado = "finalizado"

        respuesta.append(
    {
        "empleado_id": emp["id"],
        "nombre": emp["nombre"],
        "estado": estado,
        "ultima_marcacion": ultima_marcacion,
        "desde": desde,

        "trabajado": formatear_tiempo(resumen["segundos_trabajados"]),
        "comida": formatear_tiempo(resumen["segundos_comida"]),
        "descanso": formatear_tiempo(resumen["segundos_descanso"]),
        "neto": formatear_tiempo(resumen["segundos_netos"]),

        "segundos_trabajados": resumen["segundos_trabajados"],
        "segundos_comida": resumen["segundos_comida"],
        "segundos_descanso": resumen["segundos_descanso"],
        "segundos_netos": resumen["segundos_netos"],

        "segundos_trabajados_reales": resumen["segundos_trabajados_reales"],
        "segundos_netos_reales": resumen["segundos_netos_reales"],
    }
)
    cursor.close()
    conn.close()

    return jsonify(respuesta)


@app.route("/historial")
def historial():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    empleado_id = request.args.get("empleado_id")
    fecha = request.args.get("fecha")

    query = """
        SELECT
            e.id AS empleado_id,
            e.nombre,
            DATE(m.fecha_hora) AS fecha,
            MIN(CASE WHEN m.tipo = 'entrada' THEN m.fecha_hora END) AS entrada,
            MAX(CASE WHEN m.tipo = 'salida' THEN m.fecha_hora END) AS salida,
            MIN(CASE WHEN m.tipo = 'inicio_comida' THEN m.fecha_hora END) AS inicio_comida,
            MAX(CASE WHEN m.tipo = 'fin_comida' THEN m.fecha_hora END) AS fin_comida,
            MIN(CASE WHEN m.tipo = 'inicio_descanso' THEN m.fecha_hora END) AS inicio_descanso,
            MAX(CASE WHEN m.tipo = 'fin_descanso' THEN m.fecha_hora END) AS fin_descanso
        FROM marcaciones m
        JOIN empleados e ON e.id = m.empleado_id
        WHERE 1=1
    """

    params = []

    if empleado_id:
        query += " AND e.id = %s"
        params.append(empleado_id)

    if fecha:
        query += " AND DATE(m.fecha_hora) = %s"
        params.append(fecha)

    query += """
        GROUP BY e.id, e.nombre, DATE(m.fecha_hora)
        ORDER BY fecha DESC, e.nombre ASC
    """

    cursor.execute(query, params)
    filas = cursor.fetchall()

    resultado = []

    for fila in filas:
       entrada = fila["entrada"]
       salida = fila["salida"]
       inicio_comida = fila["inicio_comida"]
       fin_comida = fila["fin_comida"]
       inicio_descanso = fila["inicio_descanso"]
       fin_descanso = fila["fin_descanso"]

    total_trabajado = 0
    total_comida = 0
    total_descanso = 0

    if entrada and salida:
        total_trabajado = int((salida - entrada).total_seconds())

    if inicio_comida and fin_comida:
        total_comida = int((fin_comida - inicio_comida).total_seconds())

    if inicio_descanso and fin_descanso:
        total_descanso = int((fin_descanso - inicio_descanso).total_seconds())

    neto = max(0, total_trabajado - total_comida - total_descanso)

    resultado.append(
        {
            "empleado_id": fila["empleado_id"],
            "nombre": fila["nombre"],
            "fecha": str(fila["fecha"]),
            "entrada": entrada.strftime("%H:%M:%S") if entrada else "-",
            "salida": salida.strftime("%H:%M:%S") if salida else "-",
            "inicio_comida": inicio_comida.strftime("%H:%M:%S") if inicio_comida else "-",
            "fin_comida": fin_comida.strftime("%H:%M:%S") if fin_comida else "-",
            "inicio_descanso": inicio_descanso.strftime("%H:%M:%S") if inicio_descanso else "-",
            "fin_descanso": fin_descanso.strftime("%H:%M:%S") if fin_descanso else "-",
            "trabajado": formatear_tiempo(total_trabajado),
            "comida": formatear_tiempo(total_comida),
            "descanso": formatear_tiempo(total_descanso),
            "neto": formatear_tiempo(neto),
        }
    )

    cursor.close()
    conn.close()

    return jsonify(resultado)


@app.route("/")
def servir_index():
    return render_template ("index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
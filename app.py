import os

from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os
import mysql.connector
import urllib.parse as urlparse

LIMITE_SEGUNDOS_MELANY = 4 * 3600

#FUNCION TIEMPO LIMITE DE MELANY 4 HORAS
load_dotenv()
app = Flask(__name__)
CORS(app)

def aplicar_limite_empleado(nombre, segundos_trabajados, segundos_netos):
    if nombre.strip().lower() == "melany":
        segundos_trabajados = min(segundos_trabajados, LIMITE_SEGUNDOS_MELANY)
        segundos_netos = min(segundos_netos, LIMITE_SEGUNDOS_MELANY)

    return segundos_trabajados, segundos_netos
def get_db_connection():
    url = os.environ.get("MYSQL_PUBLIC_URL")

    urlparse.uses_netloc.append("mysql")
    parsed = urlparse.urlparse(url)

    return mysql.connector.connect(
        host=parsed.hostname,
        port=parsed.port,
        user=parsed.username,
        password=parsed.password,
        database=parsed.path.lstrip("/")
    )

def calcular_reporte_dia(empleado_id, fecha):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT tipo, fecha_hora
        FROM marcaciones
        WHERE empleado_id = %s AND DATE(fecha_hora) = %s
        ORDER BY fecha_hora ASC
    """, (empleado_id, fecha))

    marcaciones = cursor.fetchall()

    cursor.close()
    conn.close()

    entrada = None
    salida = None
    inicio_comida = None
    fin_comida = None
    inicio_descanso = None
    fin_descanso = None

    for m in marcaciones:
        if m["tipo"] == "entrada" and entrada is None:
            entrada = m["fecha_hora"]
        elif m["tipo"] == "salida":
            salida = m["fecha_hora"]
        elif m["tipo"] == "inicio_comida" and inicio_comida is None:
            inicio_comida = m["fecha_hora"]
        elif m["tipo"] == "fin_comida":
            fin_comida = m["fecha_hora"]
        elif m["tipo"] == "inicio_descanso" and inicio_descanso is None:
            inicio_descanso = m["fecha_hora"]
        elif m["tipo"] == "fin_descanso":
            fin_descanso = m["fecha_hora"]

    segundos_trabajados = 0
    segundos_comida = 0
    segundos_descanso = 0

    if entrada and salida:
        segundos_trabajados = int((salida - entrada).total_seconds())

    if inicio_comida and fin_comida:
        segundos_comida = int((fin_comida - inicio_comida).total_seconds())

    if inicio_descanso and fin_descanso:
        segundos_descanso = int((fin_descanso - inicio_descanso).total_seconds())

    segundos_netos = segundos_trabajados - segundos_comida - segundos_descanso

    return {
        "entrada": entrada.strftime("%H:%M:%S") if entrada else "-",
        "salida": salida.strftime("%H:%M:%S") if salida else "-",
        "inicio_comida": inicio_comida.strftime("%H:%M:%S") if inicio_comida else "-",
        "fin_comida": fin_comida.strftime("%H:%M:%S") if fin_comida else "-",
        "inicio_descanso": inicio_descanso.strftime("%H:%M:%S") if inicio_descanso else "-",
        "fin_descanso": fin_descanso.strftime("%H:%M:%S") if fin_descanso else "-",
        "segundos_trabajados": segundos_trabajados,
        "segundos_comida": segundos_comida,
        "segundos_descanso": segundos_descanso,
        "segundos_netos": segundos_netos
    }

def formatear_tiempo(segundos):
    horas = segundos // 3600
    minutos = (segundos % 3600) // 60
    return f"{horas}h {minutos}m"

def obtener_ultima_marcacion_hoy(cursor, empleado_id):
    cursor.execute("""
        SELECT tipo, fecha_hora
        FROM marcaciones
        WHERE empleado_id = %s
          AND DATE(fecha_hora) = CURDATE()
        ORDER BY fecha_hora DESC
        LIMIT 1
    """, (empleado_id,))
    
    return cursor.fetchone()

def calcular_resumen_marcaciones(marcaciones, empleado_id=None):
    entrada = None
    salida = None
    inicio_comida = None        
    fin_comida = None
    inicio_descanso = None
    fin_descanso = None

    total_trabajado = 0
    total_comida = 0
    total_descanso = 0

    for m in marcaciones:
        tipo = m["tipo"]
        fecha_hora = m["fecha_hora"]

        if tipo == "entrada" and entrada is None:
            entrada = fecha_hora
        elif tipo == "salida":
            salida = fecha_hora
        elif tipo == "inicio_comida" and inicio_comida is None:
            inicio_comida = fecha_hora
        elif tipo == "fin_comida":
            fin_comida = fecha_hora
        elif tipo == "inicio_descanso" and inicio_descanso is None:
            inicio_descanso = fecha_hora
        elif tipo == "fin_descanso":
            fin_descanso = fecha_hora

    if entrada and salida:
        total_trabajado = int((salida - entrada).total_seconds())

    if inicio_comida and fin_comida:
        total_comida = int((fin_comida - inicio_comida).total_seconds())

    if inicio_descanso and fin_descanso:
        total_descanso = int((fin_descanso - inicio_descanso).total_seconds())

    neto = total_trabajado - total_comida - total_descanso

    if neto < 0:
        neto = 0

    # 🔥 REGLA MELANY (empleado_id = 3)
    if empleado_id == 3:
        limite = 4 * 3600
        total_trabajado = min(total_trabajado, limite)
        neto = min(neto, limite)

    return {
        "entrada": entrada,
        "salida": salida,
        "inicio_comida": inicio_comida,
        "fin_comida": fin_comida,
        "inicio_descanso": inicio_descanso,
        "fin_descanso": fin_descanso,
        "segundos_trabajados": total_trabajado,
        "segundos_comida": total_comida,
        "segundos_descanso": total_descanso,
        "segundos_netos": neto
    }
@app.route('/historial')
def historial():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    empleado_id = request.args.get('empleado_id')
    fecha = request.args.get('fecha')

    query = """
        SELECT DISTINCT
            m.empleado_id,
            e.nombre,
            DATE(m.fecha_hora) AS fecha
        FROM marcaciones m
        JOIN empleados e ON e.id = m.empleado_id
        WHERE 1=1
    """

    params = []

    if empleado_id:
        query += " AND m.empleado_id = %s"
        params.append(empleado_id)

    if fecha:
        query += " AND DATE(m.fecha_hora) = %s"
        params.append(fecha)

    query += " ORDER BY fecha DESC, e.nombre ASC"

    cursor.execute(query, params)
    dias = cursor.fetchall()

    cursor.close()
    conn.close()

    resultado = []

    for dia in dias:
        reporte = calcular_reporte_dia(dia["empleado_id"], dia["fecha"])

        resultado.append({
            "empleado_id": dia["empleado_id"],
            "nombre": dia["nombre"],
            "fecha": str(dia["fecha"]),
            "entrada": reporte["entrada"],
            "salida": reporte["salida"],
            "inicio_comida": reporte["inicio_comida"],
            "fin_comida": reporte["fin_comida"],
            "inicio_descanso": reporte["inicio_descanso"],
            "fin_descanso": reporte["fin_descanso"],
            "trabajado": formatear_tiempo(reporte["segundos_trabajados"]),
            "comida": formatear_tiempo(reporte["segundos_comida"]),
            "descanso": formatear_tiempo(reporte["segundos_descanso"]),
            "neto": formatear_tiempo(reporte["segundos_netos"])
        })

    return jsonify(resultado)

@app.route("/")
def home():
    return "Servidor funcionando"


@app.route("/empleados")
def empleados():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM empleados ORDER BY nombre")
    result = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(result)


@app.route("/marcar", methods=["POST"])
def marcar():
    data = request.get_json()

    empleado_id = data.get("empleado_id")
    tipo = data.get("tipo")

    tipos_validos = {
        "entrada",
        "salida",
        "inicio_comida",
        "fin_comida",
        "inicio_descanso",
        "fin_descanso"
    }

    if not empleado_id or tipo not in tipos_validos:
        return jsonify({"error": "Datos inválidos"}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    ultima = obtener_ultima_marcacion_hoy(cursor, empleado_id)
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
        (empleado_id, tipo)
    )
    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({"mensaje": f"Marcación registrada: {tipo}"})


@app.route("/reporte/<int:empleado_id>/<string:fecha>")
def reporte_dia(empleado_id, fecha):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT tipo, fecha_hora
        FROM marcaciones
        WHERE empleado_id = %s AND DATE(fecha_hora) = %s
        ORDER BY fecha_hora ASC
    """, (empleado_id, fecha))

    marcaciones = cursor.fetchall()

    cursor.close()
    conn.close()

    resumen = calcular_resumen_marcaciones(marcaciones)

    return jsonify({
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
        "segundos_netos": resumen["segundos_netos"]
        
    })

 

@app.route("/resumen_hoy")
def resumen_hoy():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT id, nombre FROM empleados ORDER BY nombre")
    empleados = cursor.fetchall()

    ahora = datetime.now()
    respuesta = []

    for emp in empleados:
        cursor.execute("""
            SELECT tipo, fecha_hora
            FROM marcaciones
            WHERE empleado_id = %s AND DATE(fecha_hora) = CURDATE()
            ORDER BY fecha_hora ASC
        """, (emp["id"],))
        marcaciones = cursor.fetchall()

        resumen = calcular_resumen_marcaciones(marcaciones, emp["id"])

        estado = "sin iniciar"
        ultima_marcacion = None
        desde = None
        segundos_actuales = resumen["segundos_netos"]

        if marcaciones:
            ultima = marcaciones[-1]
            ultima_marcacion = ultima["tipo"]

            if ultima["tipo"] in {"entrada", "fin_comida", "fin_descanso"}:
                estado = "trabajando"
                desde = ultima["fecha_hora"]

                extra = int((ahora - ultima["fecha_hora"]).total_seconds())
                if extra < 0:
                    extra = 0

                segundos_actuales += extra

            elif ultima["tipo"] == "inicio_comida":
                estado = "en comida"
                desde = ultima["fecha_hora"]

            elif ultima["tipo"] == "inicio_descanso":
                estado = "en descanso"
                desde = ultima["fecha_hora"]

            elif ultima["tipo"] == "salida":
                estado = "finalizado"

        # límite visual para Melany también en tiempo en vivo
        if emp["id"] == 3:
            limite = 4 * 3600
            segundos_actuales = min(segundos_actuales, limite)

        respuesta.append({
            "empleado_id": emp["id"],
            "nombre": emp["nombre"],
            "estado": estado,
            "ultima_marcacion": ultima_marcacion,
            "desde": desde,
            "trabajado": formatear_tiempo(
                min(resumen["segundos_trabajados"], 4 * 3600) if emp["id"] == 3 else resumen["segundos_trabajados"]
            ),
            "comida": formatear_tiempo(resumen["segundos_comida"]),
            "descanso": formatear_tiempo(resumen["segundos_descanso"]),
            "neto": formatear_tiempo(segundos_actuales),
            "segundos_netos": segundos_actuales
        })

    cursor.close()
    conn.close()

    return jsonify(respuesta)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
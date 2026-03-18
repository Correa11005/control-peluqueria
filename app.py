import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector

app = Flask(__name__)
CORS(app)


def get_db_connection():
    return mysql.connector.connect(
        host=os.environ.get("MYSQLHOST"),
        port=int(os.environ.get("MYSQLPORT", 3306)),
        user=os.environ.get("MYSQLUSER"),
        password=os.environ.get("MYSQLPASSWORD"),
        database=os.environ.get("MYSQLDATABASE")
    )


def formatear_tiempo(segundos):
    horas = segundos // 3600
    minutos = (segundos % 3600) // 60
    return f"{horas}h {minutos}m"


def obtener_ultima_marcacion_hoy(cursor, empleado_id):
    cursor.execute("""
        SELECT tipo, fecha_hora
        FROM marcaciones
        WHERE empleado_id = %s AND DATE(fecha_hora) = CURDATE()
        ORDER BY fecha_hora DESC
        LIMIT 1
    """, (empleado_id,))
    return cursor.fetchone()


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

    total_trabajado = 0
    total_comida = 0
    total_descanso = 0

    if entrada and salida:
        total_trabajado = int((salida - entrada).total_seconds())

    if inicio_comida and fin_comida:
        total_comida = int((fin_comida - inicio_comida).total_seconds())

    if inicio_descanso and fin_descanso:
        total_descanso = int((fin_descanso - inicio_descanso).total_seconds())

    neto = total_trabajado - total_comida - total_descanso

    return jsonify({
        "empleado_id": empleado_id,
        "fecha": fecha,
        "marcaciones": marcaciones,
        "trabajado": formatear_tiempo(total_trabajado),
        "comida": formatear_tiempo(total_comida),
        "descanso": formatear_tiempo(total_descanso),
        "neto": formatear_tiempo(neto),
        "segundos_trabajados": total_trabajado,
        "segundos_comida": total_comida,
        "segundos_descanso": total_descanso,
        "segundos_netos": neto
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
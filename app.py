import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
from datetime import datetime

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

@app.route("/")
def home():
    return "Servidor funcionando"

@app.route("/empleados")
def empleados():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM empleados")
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(result)

@app.route("/registro", methods=["POST"])
def registro():
    data = request.json
    empleado_id = data["empleado_id"]
    hoy = datetime.now().date()

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM registros WHERE empleado_id=%s AND fecha=%s",
        (empleado_id, hoy)
    )
    registro = cursor.fetchone()

    if registro and registro["hora_salida"] is None:
        cursor.execute(
            "UPDATE registros SET hora_salida=NOW() WHERE id=%s",
            (registro["id"],)
        )
        conn.commit()
        mensaje = {"mensaje": "Salida registrada"}
    else:
        cursor.execute(
            "INSERT INTO registros (empleado_id, fecha, hora_entrada) VALUES (%s,%s,NOW())",
            (empleado_id, hoy)
        )
        conn.commit()
        mensaje = {"mensaje": "Entrada registrada"}

    cursor.close()
    conn.close()
    return jsonify(mensaje)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
from flask import Flask, request, jsonify
import mysql.connector
from datetime import datetime
from flask_cors import CORS
app = Flask(__name__)
CORS(app)
# conexión a la base de datos
def conectar_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="peluqueria_control"
    )


# OBTENER EMPLEADOS
@app.route("/empleados", methods=["GET"])
def obtener_empleados():

    conexion = conectar_db()
    cursor = conexion.cursor(dictionary=True)

    cursor.execute("SELECT id, nombre FROM empleados")

    empleados = cursor.fetchall()

    conexion.close()

    return jsonify(empleados)


# REGISTRAR ENTRADA O SALIDA
@app.route("/registro", methods=["POST"])
def registrar():

    data = request.json
    empleado_id = data["empleado_id"]

    conexion = conectar_db()
    cursor = conexion.cursor(dictionary=True)

    hoy = datetime.now().date()

    # buscar si ya registró entrada hoy
    cursor.execute(
        "SELECT * FROM registros WHERE empleado_id=%s AND fecha=%s",
        (empleado_id, hoy)
    )

    registro = cursor.fetchone()

    if registro is None:

        # registrar entrada
        cursor.execute(
            "INSERT INTO registros (empleado_id, fecha, hora_entrada) VALUES (%s,%s,NOW())",
            (empleado_id, hoy)
        )

        conexion.commit()
        conexion.close()

        return jsonify({"mensaje": "Entrada registrada"})


    elif registro["hora_salida"] is None:

        # registrar salida
        cursor.execute(
            "UPDATE registros SET hora_salida=NOW() WHERE id=%s",
            (registro["id"],)
        )

        conexion.commit()
        conexion.close()

        return jsonify({"mensaje": "Salida registrada"})


    else:

        conexion.close()

        return jsonify({"mensaje": "Ya registraste entrada y salida hoy"})


# ejecutar servidor
if __name__ == "__main__":
    app.run(debug=True)
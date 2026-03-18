import mysql.connector

conexion = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="peluqueria_control"
)

cursor = conexion.cursor()

cursor.execute("SELECT * FROM empleados")

resultados = cursor.fetchall()

for fila in resultados:
    print(fila)

conexion.close()
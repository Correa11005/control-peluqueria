import os
from dotenv import load_dotenv
import mysql.connector

load_dotenv()

conn = mysql.connector.connect(
    host=os.environ.get("MYSQLHOST"),
    user=os.environ.get("MYSQLUSER"),
    password=os.environ.get("MYSQLPASSWORD"),
    database=os.environ.get("MYSQLDATABASE"),
    port=int(os.environ.get("MYSQLPORT", 3306)),
)

cursor = conn.cursor()

consultas = [
    "DROP TABLE IF EXISTS marcaciones",
    "DROP TABLE IF EXISTS empleados",

    """
    CREATE TABLE empleados (
        id INT AUTO_INCREMENT PRIMARY KEY,
        nombre VARCHAR(100) NOT NULL,
        qr_token VARCHAR(255) UNIQUE,
        pin_hash VARCHAR(255),
        pin_intentos_fallidos INT NOT NULL DEFAULT 0,
        bloqueado_hasta DATETIME NULL,
        activo TINYINT(1) NOT NULL DEFAULT 1,
        creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,

    """
    CREATE TABLE marcaciones (
        id INT AUTO_INCREMENT PRIMARY KEY,
        empleado_id INT NOT NULL,
        tipo ENUM(
            'entrada',
            'salida',
            'inicio_comida',
            'fin_comida',
            'inicio_descanso',
            'fin_descanso'
        ) NOT NULL,
        fecha_hora DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (empleado_id) REFERENCES empleados(id)
            ON DELETE CASCADE
            ON UPDATE CASCADE
    )
    """,

    """
    INSERT INTO empleados (id, nombre, activo)
    VALUES
    (1, 'Camilo', 1),
    (2, 'Ronald', 1),
    (3, 'Melany', 1)
    """
]

try:
    for consulta in consultas:
        cursor.execute(consulta)

    conn.commit()
    print("✅ Tablas creadas correctamente")
    print("✅ Empleados insertados correctamente")

except Exception as e:
    conn.rollback()
    print("❌ Error:", e)

finally:
    cursor.close()
    conn.close()
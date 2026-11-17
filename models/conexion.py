import mysql.connector
from config import Config


def obtener_conexion():

    try:

        conexion = mysql.connector.connect(
            host=Config.MYSQL_HOST,
            port=Config.MYSQL_PORT,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DATABASE
        )

        return conexion

    except mysql.connector.Error as error:

        print("Error al conectar con MySQL:", error)

        return None
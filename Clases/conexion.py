import mysql.connector
from mysql.connector import Error

class Conexion:
    def __init__(self):
        try:
            self.connection = mysql.connector.connect(
                host='localhost',
                port=3306,                 # ← Cambia este valor si tu MySQL usa otro puerto
                user='root',         # ← Tu usuario de MySQL
                password='',  # ← Tu contraseña de MySQL
                database='TestIngles'      # ← Nombre de tu base de datos
            )
            if self.connection.is_connected():
                print("✅ Conexión exitosa a la base de datos")
        except Error as e:
            print(f"❌ Error al conectar a la base de datos: {e}")
            self.connection = None

    def obtener_conexion(self):
        return self.connection

    def obtener_cursor(self):
        """Devuelve un cursor de la conexión para ejecutar consultas SQL"""
        if self.connection and self.connection.is_connected():
            return self.connection.cursor()
        else:
            print("❌ No se pudo obtener el cursor. La conexión no está activa.")
            return None

    def cerrar_conexion(self):
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("🔒 Conexión cerrada")

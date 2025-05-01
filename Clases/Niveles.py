from enum import Enum
from datetime import datetime
from typing import Optional, List
from mysql.connector import Error

class Niveles:
    def __init__(self, nivel_id: int, nombre: str):
        self.nivel_id = nivel_id  # PRIMARY KEY AUTO_INCREMENT
        self.nombre = nombre      # VARCHAR(50) NOT NULL UNIQUE

    @staticmethod
    def obtener_todos(conexion) -> List['Niveles']:
        """
        Método estático para obtener todos los niveles de la base de datos
        Retorna una lista de objetos Nivel
        """
        try:
            cursor = conexion.obtener_conexion().cursor(dictionary=True)
            query = "SELECT * FROM Niveles"
            cursor.execute(query)

            niveles = []
            for row in cursor.fetchall():
                nivel = Niveles(
                    nivel_id=row['nivel_id'],
                    nombre=row['nombre']
                )
                niveles.append(nivel)

            print(f"✅ Se obtuvieron {len(niveles)} niveles")
            return niveles

        except Error as e:
            print(f"❌ Error al obtener niveles: {e}")
            return []

        finally:
            if cursor:
                cursor.close()

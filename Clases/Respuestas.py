from enum import Enum
from datetime import datetime
from typing import Optional, List
from mysql.connector import Error

class Respuestas:
    def __init__(self, respuesta_id: int, pregunta_id: int, texto: str, es_correcta: bool = False):
        self.respuesta_id = respuesta_id  # PRIMARY KEY AUTO_INCREMENT
        self.pregunta_id = pregunta_id    # INT NOT NULL (FOREIGN KEY)
        self.texto = texto                # TEXT NOT NULL
        self.es_correcta = es_correcta    # BOOLEAN DEFAULT FALSE

    def __repr__(self):
        return f"Respuestas(respuesta_id={self.respuesta_id}, es_correcta={self.es_correcta})"
    
    @staticmethod
    def obtener_todos(conexion) -> List['Respuestas']:
        """
        Método estático para obtener todas las respuestas de la base de datos
        Retorna una lista de objetos Respuesta
        """
        try:
            cursor = conexion.obtener_conexion().cursor(dictionary=True)
            query = "SELECT * FROM Respuestas"
            cursor.execute(query)

            respuestas = []
            for row in cursor.fetchall():
                respuesta = Respuestas(
                    respuesta_id=row['respuesta_id'],
                    pregunta_id=row['pregunta_id'],
                    texto=row['texto'],
                    es_correcta=row['es_correcta']
                )
                respuestas.append(respuesta)

            print(f"✅ Se obtuvieron {len(respuestas)} respuestas")
            return respuestas

        except Error as e:
            print(f"❌ Error al obtener respuestas: {e}")
            return []

        finally:
            if cursor:
                cursor.close()
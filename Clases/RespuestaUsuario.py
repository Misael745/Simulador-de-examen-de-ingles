import random
from typing import List
from Clases.conexion import Conexion
from Clases.Preguntas import Preguntas
from Clases.Respuestas import Respuestas
from mysql.connector import Error

class RespuestaUsuario:
    def __init__(self, examen_id, pregunta_id, respuesta_id):
        self.examen_id = examen_id
        self.pregunta_id = pregunta_id
        self.respuesta_id = respuesta_id

    def guardar_respuesta(self, conexion):
        try:
            cursor = conexion.obtener_cursor()
            sql = """
                INSERT INTO RespuestasDadas (examen_id, pregunta_id, respuesta_id)
                VALUES (%s, %s, %s)
            """
            valores = (self.examen_id, self.pregunta_id, self.respuesta_id)
            cursor.execute(sql, valores)
            conexion.obtener_conexion().commit()  # Usamos commit() para confirmar cambios
            
        except Exception as e:
            print(f"❌ Error al guardar respuesta: {e}")

from enum import Enum
from datetime import datetime
from typing import Optional, List
from Clases.Respuestas import Respuestas
from mysql.connector import Error
import random

class Preguntas:
    def __init__(self, pregunta_id: int, texto: str, nivel_id: int):
        self.pregunta_id = pregunta_id  # PRIMARY KEY AUTO_INCREMENT
        self.texto = texto              # TEXT NOT NULL
        self.nivel_id = nivel_id        # INT NOT NULL (FOREIGN KEY)
        self.respuestas: List[Respuestas] = []

    def agregar_respuesta(self, respuesta: 'Respuestas'):
        self.respuestas.append(respuesta)

    @staticmethod
    def obtener_todos(conexion) -> List['Preguntas']:
        """
        Método estático para obtener todas las preguntas de la base de datos.
        Retorna una lista de objetos Preguntas.
        """
        try:
            cursor = conexion.obtener_conexion().cursor(dictionary=True)
            query = "SELECT * FROM Preguntas"
            cursor.execute(query)

            preguntas = []
            for row in cursor.fetchall():
                pregunta = Preguntas(
                    pregunta_id=row['pregunta_id'],
                    texto=row['texto'],
                    nivel_id=row['nivel_id']
                )
                preguntas.append(pregunta)

            print(f"✅ Se obtuvieron {len(preguntas)} preguntas")
            return preguntas

        except Error as e:
            print(f"❌ Error al obtener preguntas: {e}")
            return []

        finally:
            if cursor:
                cursor.close()
                
    @staticmethod
    def generar_examen_practica(preguntas: List['Preguntas'], cantidad_total: int = 20) -> List['Preguntas']:
 

        # Clasificar preguntas por nivel
        preguntas_por_nivel = {}
        for pregunta in preguntas:
            preguntas_por_nivel.setdefault(pregunta.nivel_id, []).append(pregunta)

        niveles = list(preguntas_por_nivel.keys())
        num_niveles = len(niveles)
        preguntas_por_nivel_reparto = cantidad_total // num_niveles
        restante = cantidad_total % num_niveles

        examen = []

        # Asignar las preguntas por nivel de forma equitativa
        for nivel_id in niveles:
            disponibles = preguntas_por_nivel[nivel_id]
            num_a_seleccionar = preguntas_por_nivel_reparto

            if restante > 0:
                num_a_seleccionar += 1
                restante -= 1

            seleccionadas = random.sample(disponibles, min(num_a_seleccionar, len(disponibles)))
            examen.extend(seleccionadas)

        # Mezclar el orden de las preguntas del examen
        random.shuffle(examen)
        return examen
    
    @staticmethod
    def generar_examen_final(preguntas: List['Preguntas'], cantidad_total: int = 3) -> List['Preguntas']:
    
        # Clasificar preguntas por nivel
        preguntas_por_nivel = {}
        for pregunta in preguntas:
            preguntas_por_nivel.setdefault(pregunta.nivel_id, []).append(pregunta)

        niveles = list(preguntas_por_nivel.keys())
        num_niveles = len(niveles)
        preguntas_por_nivel_reparto = cantidad_total // num_niveles
        restante = cantidad_total % num_niveles

        examen = []

        # Asignar las preguntas por nivel de forma equitativa
        for nivel_id in niveles:
            disponibles = preguntas_por_nivel[nivel_id]
            num_a_seleccionar = preguntas_por_nivel_reparto

            if restante > 0:
                num_a_seleccionar += 1
                restante -= 1

            seleccionadas = random.sample(disponibles, min(num_a_seleccionar, len(disponibles)))
            examen.extend(seleccionadas)

        # Mezclar el orden de las preguntas del examen
        random.shuffle(examen)
        return examen
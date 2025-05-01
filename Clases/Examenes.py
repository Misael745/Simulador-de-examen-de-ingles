from datetime import datetime
from typing import List
from mysql.connector import Error
from Clases.Niveles import Niveles
from Clases.Preguntas import Preguntas
from Clases.conexion import Conexion
import random
from collections import Counter

class Examenes:
    def __init__(self, examen_id: int, tipo: str, usuario_id: int, nivel: str, puntuacion: float = None, porcentaje: float = None, fecha: datetime = None):
        self.examen_id = examen_id
        self.tipo = tipo
        self.usuario_id = usuario_id
        self.nivel = nivel
        self.puntuacion = puntuacion
        self.porcentaje = porcentaje
        self.fecha = fecha if fecha else datetime.now()

    def __repr__(self):
        return f"Examenes(examen_id={self.examen_id}, tipo='{self.tipo}', nivel='{self.nivel}')"

    @staticmethod
    def obtener_examenes_por_usuario(conexion: Conexion, usuario_id: int) -> List['Examenes']:
        """
        Obtiene todos los exámenes realizados por un usuario específico.
        """
        try:
            cursor = conexion.obtener_conexion().cursor()
            query = """
                SELECT examen_id, tipo, usuario_id, nivel, puntuacion, porcentaje, fecha
                FROM Examenes
                WHERE usuario_id = %s
            """
            cursor.execute(query, (usuario_id,))
            resultados = cursor.fetchall()

            examenes = []
            for fila in resultados:
                examen = Examenes(
                    examen_id=fila[0],
                    tipo=fila[1],
                    usuario_id=fila[2],
                    nivel=fila[3],
                    puntuacion=fila[4],
                    porcentaje=fila[5],
                    fecha=fila[6]
                )
                examenes.append(examen)
            
            return examenes
        except Error as e:
            print(f"Error al obtener los exámenes del usuario {usuario_id}: {e}")
            return []

    @staticmethod
    def crear_examen_para_usuario(conexion: Conexion, usuario_id: int) -> 'Examenes':
        """
        Crea un examen para el usuario seleccionado. Asigna un nivel basado en las preguntas seleccionadas.
        """
        # Generar las preguntas del examen para el usuario
        preguntas = Preguntas.obtener_todos(conexion)
        examen_preguntas = Preguntas.generar_examen_practica(preguntas)
        
        # Calcular el nivel basado en las preguntas seleccionadas
        niveles = [p.nivel_id for p in examen_preguntas]
        nivel_mas_comun_id = Counter(niveles).most_common(1)[0][0]  # Nivel más frecuente

        # Obtener el nombre del nivel más frecuente
        niveles = Niveles.obtener_todos(conexion)
        nivel_mas_comun_nombre = next(nivel.nombre for nivel in niveles if nivel.nivel_id == nivel_mas_comun_id)

        # Crear el examen en la base de datos
        tipo = 'practica'  # O puedes hacer que esto sea dinámico
        examen = Examenes(
            examen_id=0,  # Será asignado automáticamente
            tipo=tipo,
            usuario_id=usuario_id,
            nivel=nivel_mas_comun_nombre
        )

        # Guardar el examen en la base de datos
        examen_id = examen.guardar_examen(conexion)
        examen.examen_id = examen_id

        # Devolver el objeto Examen con el examen_id asignado
        return examen

    @staticmethod
    def crear_examen_final_para_usuario(conexion: Conexion, usuario_id: int) -> 'Examenes':
        """
        Crea un examen final para el usuario seleccionado.
        """
        # Generar las preguntas del examen final para el usuario
        preguntas = Preguntas.obtener_todos(conexion)
        examen_preguntas = Preguntas.generar_examen_final(preguntas)
        
        # Calcular el nivel basado en las preguntas seleccionadas
        niveles = [p.nivel_id for p in examen_preguntas]
        nivel_mas_comun_id = Counter(niveles).most_common(1)[0][0]  # Nivel más frecuente

        # Obtener el nombre del nivel más frecuente
        niveles = Niveles.obtener_todos(conexion)
        nivel_mas_comun_nombre = next(nivel.nombre for nivel in niveles if nivel.nivel_id == nivel_mas_comun_id)

        # Crear el examen final en la base de datos
        tipo = 'final'
        examen = Examenes(
            examen_id=0,  # Será asignado automáticamente
            tipo=tipo,
            usuario_id=usuario_id,
            nivel=nivel_mas_comun_nombre
        )

        # Guardar el examen en la base de datos
        examen_id = examen.guardar_examen(conexion)
        examen.examen_id = examen_id

        # Devolver el objeto Examen con el examen_id asignado
        return examen

    def guardar_examen(self, conexion: Conexion) -> int:
        """
        Guarda el examen en la base de datos y devuelve el examen_id generado.
        """
        try:
            cursor = conexion.obtener_conexion().cursor()  # Aseguramos obtener el cursor correctamente
            query = """
                INSERT INTO Examenes (tipo, usuario_id, nivel)
                VALUES (%s, %s, %s)
            """
            cursor.execute(query, (self.tipo, self.usuario_id, self.nivel))
            conexion.obtener_conexion().commit()
            return cursor.lastrowid  # Devolvemos el examen_id generado
        except Error as e:
            print(f"Error al guardar examen: {e}")
            conexion.obtener_conexion().rollback()
            return None

    def calificar_examen(self, conexion):
        try:
            # Paso 1: Obtener las respuestas dadas para este examen
            cursor = conexion.obtener_cursor()
            sql_respuestas = """
                SELECT r.pregunta_id, r.respuesta_id, res.es_correcta, p.nivel_id
                FROM RespuestasDadas r
                JOIN Respuestas res ON r.respuesta_id = res.respuesta_id
                JOIN Preguntas p ON r.pregunta_id = p.pregunta_id
                WHERE r.examen_id = %s
            """
            cursor.execute(sql_respuestas, (self.examen_id,))
            respuestas = cursor.fetchall()

            # Paso 2: Calcular la puntuación y porcentaje de aciertos
            puntuacion_total = 0
            respuestas_correctas = 0
            respuestas_por_nivel = Counter()
            respuestas_correctas_por_nivel = Counter()

            for respuesta in respuestas:
                pregunta_id, respuesta_id, es_correcta, nivel_id = respuesta
                if es_correcta:
                    # La calificación varía según el tipo de examen
                    if self.tipo == 'final':
                        puntuacion_total += 2.5  # 2.5 puntos por respuesta correcta en el examen final
                    else:
                        puntuacion_total += 5  # 5 puntos por respuesta correcta en el examen de práctica
                    respuestas_correctas += 1
                    respuestas_correctas_por_nivel[nivel_id] += 1
                respuestas_por_nivel[nivel_id] += 1

            porcentaje_aciertos = (respuestas_correctas / len(respuestas)) * 100

            # Paso 3: Calcular el nivel aprobado
            niveles_aprobados = []
            niveles_requisitos = {1: 70, 2: 70, 3: 70}  # Básico: 1, Intermedio: 2, Avanzado: 3
            niveles_aprobados_total = []

            # Validamos cada nivel por separado, considerando que el usuario debe aprobar los niveles anteriores
            for nivel_id in range(1, 4):  # Revisar los 3 niveles: Básico (1), Intermedio (2), Avanzado (3)
                if nivel_id in respuestas_por_nivel:
                    total_respuestas_nivel = respuestas_por_nivel[nivel_id]
                    respuestas_correctas_nivel = respuestas_correctas_por_nivel.get(nivel_id, 0)
                    porcentaje_nivel = (respuestas_correctas_nivel / total_respuestas_nivel) * 100

                    if porcentaje_nivel >= niveles_requisitos[nivel_id]:
                        niveles_aprobados_total.append(nivel_id)
                    else:
                        break  # Si no pasa el 70% en el nivel actual, se detiene y se mantiene el último nivel aprobado

            # Determinar el nivel final
            if niveles_aprobados_total:
                nivel_final = max(niveles_aprobados_total)  # El último nivel aprobado
            else:
                nivel_final = 1  # Si no pasa en ningún nivel, se queda en Básico

            # Paso 4: Actualizar la puntuación, el porcentaje y el nivel en la base de datos
            sql_update = """
                UPDATE Examenes
                SET puntuacion = %s, porcentaje = %s, nivel = %s
                WHERE examen_id = %s
            """
            cursor.execute(sql_update, (puntuacion_total, porcentaje_aciertos, nivel_final, self.examen_id))
            conexion.obtener_conexion().commit()

            print(f"✅ Examen calificado: Puntuación = {puntuacion_total}, Porcentaje = {porcentaje_aciertos}%, Nivel final = {nivel_final}")

        except Exception as e:
            print(f"❌ Error al calificar el examen: {e}")

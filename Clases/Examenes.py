from datetime import datetime
from typing import List
from mysql.connector import Error
from Clases.Niveles import Niveles
from Clases.Preguntas import Preguntas
from Clases.Respuestas import Respuestas
from Clases.RespuestaUsuario import RespuestaUsuario
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
            cursor = conexion.obtener_cursor()
            # 1) Traer respuestas del examen
            sql = """
                SELECT res.es_correcta, p.nivel_id
                FROM RespuestasDadas r
                JOIN Respuestas res ON r.respuesta_id = res.respuesta_id
                JOIN Preguntas p ON r.pregunta_id = p.pregunta_id
                WHERE r.examen_id = %s
            """
            cursor.execute(sql, (self.examen_id,))
            filas = cursor.fetchall()

            # 2) Contar aciertos y total de preguntas
            correctas = sum(1 for es_correcta, _ in filas if es_correcta)
            total = len(filas)

            # 3) Definir valor por respuesta según tipo de examen
            valor_por_resp = 2.5 if self.tipo == 'final' else 5

            # 4) Calcular puntuación bruta y redondear
            puntaje = correctas * valor_por_resp
            self.puntuacion = round(puntaje, 2)

            # 5) Calcular porcentaje global de aciertos
            pct = (correctas / total * 100) if total else 0
            self.porcentaje = round(pct, 2)

            # 6) Determinar nivel aprobado
            cont_por_nivel = Counter()
            corr_por_nivel = Counter()
            for es_correcta, nivel_id in filas:
                cont_por_nivel[nivel_id] += 1
                if es_correcta:
                    corr_por_nivel[nivel_id] += 1
            requisitos = {1:70, 2:70, 3:70}
            aprobados = []
            for nid in range(1, 4):
                if cont_por_nivel[nid]:
                    pct_n = corr_por_nivel[nid] / cont_por_nivel[nid] * 100
                    if pct_n >= requisitos[nid]:
                        aprobados.append(nid)
                    else:
                        break
            nivel_id_final = max(aprobados) if aprobados else 1
            nombres = {1: 'Básico', 2: 'Intermedio', 3: 'Avanzado'}
            self.nivel = nombres[nivel_id_final]

            # 7) Guardar correctas y total de preguntas para la sesión
            self.correctas = correctas
            self.total_preguntas = total

            # 8) Actualizar la base de datos
            cursor.execute(
                "UPDATE Examenes SET puntuacion=%s, porcentaje=%s, nivel=%s WHERE examen_id=%s",
                (self.puntuacion, self.porcentaje, self.nivel, self.examen_id)
            )
            conexion.obtener_conexion().commit()

            print(f"✅ Calificado: {self.correctas}/{self.total_preguntas} correctas → {self.puntuacion} pts, {self.porcentaje}% → {self.nivel}")
        except Exception as e:
            conexion.obtener_conexion().rollback()
            print(f"❌ Error al calificar el examen: {e}")
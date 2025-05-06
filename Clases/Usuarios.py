from enum import Enum
from typing import List, Dict
from mysql.connector import Error

class GeneroEnum(Enum):
    MASCULINO = 'masculino'
    FEMENINO = 'femenino'
    OTRO = 'otro'

class Usuarios:
    def __init__(self, usuario_id: int, nombre: str, apellido: str, correo: str, 
                 contrasena: str, genero: GeneroEnum = GeneroEnum.OTRO):
        self.usuario_id = usuario_id  
        self.nombre = nombre          
        self.apellido = apellido      
        self.correo = correo          
        self.contrasena = contrasena  
        self.genero = genero

    @staticmethod
    def obtener_todos(conexion) -> List['Usuarios']:
        """
        Método estático para obtener todos los usuarios de la base de datos
        Retorna una lista de objetos Usuarios
        """
        try:
            cursor = conexion.obtener_conexion().cursor(dictionary=True)
            query = "SELECT * FROM Usuarios"
            cursor.execute(query)
            
            usuarios = []
            for row in cursor.fetchall():
                usuario = Usuarios(
                    usuario_id=row['usuario_id'],
                    nombre=row['nombre'],
                    apellido=row['apellido'],
                    correo=row['correo'],
                    contrasena=row['contrasena'],
                    genero=GeneroEnum(row['genero'])
                )
                usuarios.append(usuario)
            
            print(f"✅ Se obtuvieron {len(usuarios)} usuarios")
            return usuarios
            
        except Error as e:
            print(f"❌ Error al obtener usuarios: {e}")
            return []
        
        finally:
            if cursor:
                cursor.close()

    @staticmethod
    def insertar_usuario(conexion, nombre, apellido, correo, contrasena, genero):
        try:
            conn = conexion.obtener_conexion()
            cursor = conn.cursor()
            sql = """
                INSERT INTO Usuarios (nombre, apellido, correo, contrasena, genero)
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (nombre, apellido, correo, contrasena, genero))
            conn.commit()
            return True
        except Error as e:
            print(f"❌ Error al insertar usuario: {e}")
            return False
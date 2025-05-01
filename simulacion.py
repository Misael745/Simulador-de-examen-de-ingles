import random
from Clases.conexion import Conexion
from Clases.Usuarios import Usuarios
from Clases.Niveles import Niveles
from Clases.Preguntas import Preguntas
from Clases.Respuestas import Respuestas
from Clases.RespuestaUsuario import RespuestaUsuario
from Clases.Examenes import Examenes


def seleccionar_usuarios_aleatorios(conexion, min_usuarios=1):
    todos_usuarios = Usuarios.obtener_todos(conexion)
    total_usuarios = len(todos_usuarios)

    if total_usuarios == 0:
        print("⚠️ No hay usuarios disponibles")
        return [], 0

    min_usuarios = min(min_usuarios, total_usuarios)
    cantidad = random.randint(min_usuarios, total_usuarios)
    usuarios_seleccionados = random.sample(todos_usuarios, cantidad)

    print(f"✅ Seleccionados {cantidad} de {total_usuarios} usuarios disponibles")
    return usuarios_seleccionados, cantidad

def verificar_examenes_usuario(conexion, usuario_id, examen_tipo):
    # Verificar si el usuario ya tiene el número máximo de exámenes del tipo especificado
    exámenes_realizados = Examenes.obtener_examenes_por_usuario(conexion, usuario_id) 
    cantidad_practicas = sum(1 for examen in exámenes_realizados if examen.tipo == 'practica')
    cantidad_finales = sum(1 for examen in exámenes_realizados if examen.tipo == 'final')

    if examen_tipo == 'practica' and cantidad_practicas >= 5:
        print(f"⚠️ El usuario {usuario_id} ya tiene 5 exámenes de práctica.")
        return False
    elif examen_tipo == 'final' and cantidad_finales >= 2:
        print(f"⚠️ El usuario {usuario_id} ya tiene 2 exámenes finales.")
        return False
    
    return True

def ejecutar_simulacion_practica():
    conexion = Conexion()

    try:
        # Selección automática de usuarios para el examen
        usuarios, cantidad = seleccionar_usuarios_aleatorios(conexion)

        # Obtener todas las preguntas
        preguntas = Preguntas.obtener_todos(conexion)

        # Obtener todas las respuestas
        respuestas = Respuestas.obtener_todos(conexion)
        
        for usuario in usuarios:
            print(f"Usuario seleccionado: {usuario.nombre} {usuario.apellido} (ID: {usuario.usuario_id})")
        # 🔗 Asociar respuestas a las preguntas
        preguntas_dict = {p.pregunta_id: p for p in preguntas}
        for respuesta in respuestas:
            if respuesta.pregunta_id in preguntas_dict:
                preguntas_dict[respuesta.pregunta_id].agregar_respuesta(respuesta)

        # Mostrar usuarios seleccionados
        print("\n🔹 Usuarios seleccionados para el examen: ")
        for usuario in usuarios:
            print(f"- {usuario.nombre} {usuario.apellido} (ID: {usuario.usuario_id})")

            # Verificar si el usuario puede recibir un examen de práctica
            if verificar_examenes_usuario(conexion, usuario.usuario_id, 'practica'):
                # 📋 Generar un examen diferente para cada usuario
                examen = Preguntas.generar_examen_practica(preguntas)

                # Crear un examen para el usuario actual
                examen_usuario = Examenes.crear_examen_para_usuario(conexion, usuario.usuario_id)

                # Registrar respuestas aleatorias para el examen
                for pregunta in examen:
                    # Seleccionar una respuesta aleatoria de las respuestas disponibles para la pregunta
                    respuesta_aleatoria = random.choice(pregunta.respuestas)

                    # Crear una instancia de RespuestaUsuario para registrar la respuesta
                    respuesta_usuario = RespuestaUsuario(
                        examen_id=examen_usuario.examen_id,
                        pregunta_id=pregunta.pregunta_id,
                        respuesta_id=respuesta_aleatoria.respuesta_id
                    )

                    # Guardar la respuesta en la tabla RespuestasDadas
                    respuesta_usuario.guardar_respuesta(conexion)

                # Calificar el examen después de registrar las respuestas
                examen_usuario.calificar_examen(conexion)
                    # Mostrar examen generado con respuestas
                print("\n📝 Examen generado: ")
                for i, pregunta in enumerate(examen, 1):
                    print(f"{i}. (Nivel {pregunta.nivel_id}) {pregunta.texto[:100]}...")
                    
            else:
                print(f"🔸 El usuario {usuario.nombre} {usuario.apellido} no puede recibir más exámenes de práctica.")



    finally:
        conexion.cerrar_conexion()


def ejecutar_simulacion_final():
    conexion = Conexion()

    try:
        # Selección automática de usuarios para el examen
        usuarios, cantidad = seleccionar_usuarios_aleatorios(conexion)

        # Obtener todas las preguntas
        preguntas = Preguntas.obtener_todos(conexion)

        # Obtener todas las respuestas
        respuestas = Respuestas.obtener_todos(conexion)

       
        for usuario in usuarios:
            print(f"Usuario seleccionado: {usuario.nombre} {usuario.apellido} (ID: {usuario.usuario_id})")

        # 🔗 Asociar respuestas a las preguntas
        preguntas_dict = {p.pregunta_id: p for p in preguntas}
        for respuesta in respuestas:
            if respuesta.pregunta_id in preguntas_dict:
                preguntas_dict[respuesta.pregunta_id].agregar_respuesta(respuesta)
       
        # Mostrar usuarios seleccionados
        print("\n🔹 Usuarios seleccionados para el examen: ")
        for usuario in usuarios:
            print(f"- {usuario.nombre} {usuario.apellido} (ID: {usuario.usuario_id})")

            # Verificar si el usuario puede recibir un examen final
            if verificar_examenes_usuario(conexion, usuario.usuario_id, 'final'):
                # 📋 Generar un examen final para cada usuario
                examen = Preguntas.generar_examen_final(preguntas)  # Llamamos a generar_examen_final

                # Crear un examen para el usuario actual
                examen_usuario = Examenes.crear_examen_final_para_usuario(conexion, usuario.usuario_id)  # Usamos el método para examen final

                # Registrar respuestas aleatorias para el examen
                for pregunta in examen:
                    # Seleccionar una respuesta aleatoria de las respuestas disponibles para la pregunta
                    respuesta_aleatoria = random.choice(pregunta.respuestas)

                    # Crear una instancia de RespuestaUsuario para registrar la respuesta
                    respuesta_usuario = RespuestaUsuario(
                        examen_id=examen_usuario.examen_id,
                        pregunta_id=pregunta.pregunta_id,
                        respuesta_id=respuesta_aleatoria.respuesta_id
                    )

                    # Guardar la respuesta en la tabla RespuestasDadas
                    respuesta_usuario.guardar_respuesta(conexion)

                # Calificar el examen después de registrar las respuestas
                examen_usuario.calificar_examen(conexion)

                print("\n📝 Examen generado: ")
                for i, pregunta in enumerate(examen, 1):
                    print(f"{i}. (Nivel {pregunta.nivel_id}) {pregunta.texto[:50]}...")
            else:
                print(f"🔸 El usuario {usuario.nombre} {usuario.apellido} no puede recibir más exámenes finales.")


    finally:
        conexion.cerrar_conexion()


if __name__ == "__main__":
  ejecutar_simulacion_practica
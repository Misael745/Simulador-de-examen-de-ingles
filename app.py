from flask import Flask, render_template, request, redirect, session, flash, url_for
from Clases.conexion import Conexion
from Clases.Preguntas import Preguntas
from Clases.Respuestas import Respuestas
from Clases.Examenes import Examenes
from Clases.RespuestaUsuario import RespuestaUsuario
import hashlib
import random

app = Flask(__name__, template_folder='interfaz', static_folder='Style')
app.secret_key = 'super_secret_key'

@app.route('/')
def home():
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo = request.form['correo']
        contrasena = request.form['contrasena']
        hashed = hashlib.sha256(contrasena.encode()).hexdigest()

        conexion = Conexion()
        conn = conexion.obtener_conexion()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Usuarios WHERE correo = %s AND contrasena = %s", (correo, hashed))
        user = cursor.fetchone()

        if user:
            session['usuario_id'] = user['usuario_id']
            session['nombre'] = user['nombre']
            return redirect('/dashboard')
        else:
            flash('Correo o contraseña incorrectos')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nombre = request.form['nombre']
        apellido = request.form['apellido']
        correo = request.form['correo']
        contrasena = request.form['contrasena']
        genero = request.form['genero']

        conexion = Conexion()
        conn = conexion.obtener_conexion()
        cursor = conn.cursor()

        try:
            cursor.execute("INSERT INTO Usuarios (nombre, apellido, correo, contrasena, genero) VALUES (%s, %s, %s, %s, %s)",
                           (nombre, apellido, correo, contrasena, genero))
            conn.commit()
            flash('Usuario registrado exitosamente')
            return redirect('/login')
        except Exception as e:
            flash('Error al registrar: ' + str(e))
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'usuario_id' not in session:
        return redirect('/login')
    return render_template('menu.html')

@app.route('/iniciar_examen/<tipo>')
def iniciar_examen(tipo):
    if 'usuario_id' not in session:
        return redirect('/login')

    conexion = Conexion()
    preguntas = Preguntas.obtener_todos(conexion)
    respuestas = Respuestas.obtener_todos(conexion)

    preguntas_dict = {p.pregunta_id: p for p in preguntas}
    for r in respuestas:
        if r.pregunta_id in preguntas_dict:
            preguntas_dict[r.pregunta_id].agregar_respuesta(r)

    if tipo == 'practica':
        preguntas_examen = Preguntas.generar_examen_practica(preguntas)
        examen_usuario = Examenes.crear_examen_para_usuario(conexion, session['usuario_id'])
    else:
        preguntas_examen = Preguntas.generar_examen_final(preguntas)
        examen_usuario = Examenes.crear_examen_final_para_usuario(conexion, session['usuario_id'])

    session['preguntas'] = [p.pregunta_id for p in preguntas_examen]
    session['examen_id'] = examen_usuario.examen_id
    session['respuestas'] = {}

    return redirect('/mostrar_examen?indice=0')

@app.route('/mostrar_examen', methods=['GET'])
def mostrar_examen():
    if 'usuario_id' not in session:
        return redirect('/login')

    indice = int(request.args.get('indice', 0))
    pregunta_id = session['preguntas'][indice]

    conexion = Conexion()
    preguntas = Preguntas.obtener_todos(conexion)
    respuestas = Respuestas.obtener_todos(conexion)

    preguntas_dict = {p.pregunta_id: p for p in preguntas}
    for r in respuestas:
        if r.pregunta_id in preguntas_dict:
            preguntas_dict[r.pregunta_id].agregar_respuesta(r)

    pregunta_actual = preguntas_dict[pregunta_id]
    respuesta_guardada = session['respuestas'].get(str(pregunta_id))

    return render_template('mostrar_examen.html',
                           pregunta=pregunta_actual,
                           respuesta_guardada=respuesta_guardada,
                           indice_actual=indice,
                           total_preguntas=len(session['preguntas']),
                           examen_id=session['examen_id'])

@app.route('/guardar_respuesta', methods=['POST'])
def guardar_respuesta():
    if 'usuario_id' not in session:
        return redirect('/login')

    indice = int(request.form['indice_actual'])
    respuesta_id = request.form.get('respuesta_id')
    pregunta_id = request.form['pregunta_id']
    examen_id = session['examen_id']

    if respuesta_id:
        session['respuestas'][str(pregunta_id)] = int(respuesta_id)
        conexion = Conexion()
        respuesta_usuario = RespuestaUsuario(
            examen_id=examen_id,
            pregunta_id=int(pregunta_id),
            respuesta_id=int(respuesta_id)
        )
        respuesta_usuario.guardar_respuesta(conexion)
        conexion.cerrar_conexion()

    accion = request.form['accion']

    if accion == 'anterior':
        return redirect(f'/mostrar_examen?indice={indice - 1}')
    elif accion == 'siguiente':
        return redirect(f'/mostrar_examen?indice={indice + 1}')
    elif accion == 'terminar':
        conexion = Conexion()
        examen = Examenes(examen_id=examen_id, tipo='', usuario_id=session['usuario_id'], nivel='')
        examen.calificar_examen(conexion)
        flash("Examen finalizado y calificado correctamente.")
        session.pop('preguntas', None)
        session.pop('respuestas', None)
        session.pop('examen_id', None)
        return redirect('/dashboard')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == '__main__':
    app.run(debug=True)

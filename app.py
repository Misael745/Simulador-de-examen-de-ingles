from flask import Flask, render_template, request, redirect, session, flash, url_for
from Clases.conexion import Conexion
from Clases.Usuarios import Usuarios
from Clases.Preguntas import Preguntas
from Clases.Respuestas import Respuestas
from Clases.Examenes import Examenes
from Clases.RespuestaUsuario import RespuestaUsuario
import hashlib

app = Flask(__name__, template_folder='interfaz', static_folder='Style')
app.secret_key = 'super_secret_key'

# Página inicial
@app.route('/')
def home():
    return redirect('/login')

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo = request.form['correo']
        contrasena = request.form['contrasena']
        hashed = hashlib.sha256(contrasena.encode()).hexdigest()

        conexion = Conexion()
        conn = conexion.obtener_conexion()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM Usuarios WHERE correo = %s AND contrasena = %s",
            (correo, hashed)
        )
        user = cursor.fetchone()
        conexion.cerrar_conexion()

        if user:
            session.clear()
            session['usuario_id'] = user['usuario_id']
            session['nombre'] = user['nombre']
            return redirect('/dashboard')
        else:
            flash('Correo o contraseña incorrectos')
    else:
        session.pop('_flashes', None)
    return render_template('login.html')

# Registro de usuario
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nombre = request.form['nombre']
        apellido = request.form['apellido']
        correo = request.form['correo']
        contrasena = request.form['contrasena']  # trigger en DB aplica SHA2
        genero = request.form['genero']

        conexion = Conexion()
        conn = conexion.obtener_conexion()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO Usuarios (nombre, apellido, correo, contrasena, genero) VALUES (%s, %s, %s, %s, %s)",
                (nombre, apellido, correo, contrasena, genero)
            )
            conn.commit()
            conexion.cerrar_conexion()
            flash('Usuario registrado exitosamente')
            return redirect('/login')
        except Exception as e:
            conexion.cerrar_conexion()
            flash('Error al registrar usuario: ' + str(e))
    return render_template('register.html')

# Dashboard con intentos restantes
@app.route('/dashboard')
def dashboard():
    if 'usuario_id' not in session:
        return redirect('/login')

    conexion = Conexion()
    conn = conexion.obtener_conexion()
    cursor = conn.cursor(dictionary=True)

    usuario_id = session['usuario_id']
    cursor.execute("SELECT tipo FROM Examenes WHERE usuario_id = %s", (usuario_id,))
    examenes = cursor.fetchall()
    conexion.cerrar_conexion()

    practicas = sum(1 for e in examenes if e['tipo'] == 'practica')
    finales   = sum(1 for e in examenes if e['tipo'] == 'final')

    intentos_pract = max(0, 5 - practicas)
    intentos_final = max(0, 2 - finales)

    return render_template(
        'menu.html',
        nombre=session['nombre'],
        intentos_practica=intentos_pract,
        intentos_final=intentos_final
    )

# Iniciar examen
@app.route('/iniciar_examen/<tipo>')
def iniciar_examen(tipo):
    if 'usuario_id' not in session:
        return redirect('/login')
    if tipo not in ['practica','final']:
        flash('Tipo de examen inválido')
        return redirect('/dashboard')

    session['tipo'] = tipo

    # 1) Cargamos preguntas/Respuestas para el front
    conexion = Conexion()
    preguntas = Preguntas.obtener_todos(conexion)
    respuestas = Respuestas.obtener_todos(conexion)
    # asociamos aquí…
    # ¡NO cerrar la conexión aún!

    # 2) Creamos el examen con UNA NUEVA conexión
    from Clases.conexion import Conexion as Conn2
    conn2 = Conn2()
    if tipo == 'practica':
        examen_usuario = Examenes.crear_examen_para_usuario(conn2, session['usuario_id'])
        preguntas_examen = Preguntas.generar_examen_practica(preguntas)
    else:
        examen_usuario = Examenes.crear_examen_final_para_usuario(conn2, session['usuario_id'])
        preguntas_examen = Preguntas.generar_examen_final(preguntas)
    conn2.cerrar_conexion()

    # 3) Ahora sí cierro la primera conexión
    conexion.cerrar_conexion()

    # 4) Guardo todo en session y redirijo …
    session['preguntas']   = [p.pregunta_id for p in preguntas_examen]
    session['examen_id']   = examen_usuario.examen_id
    session['respuestas']  = {}
    session['time_lefts']  = { str(i):60 for i in range(len(preguntas_examen)) }
    session.modified = True

    return redirect('/mostrar_examen?indice=0')

# Mostrar examen y gestionar saltos/timeouts
@app.route('/mostrar_examen', methods=['GET'])
def mostrar_examen_route():
    if 'usuario_id' not in session:
        return redirect('/login')

    preguntas_ids = session.get('preguntas', [])
    # Si ya respondimos todas, calificar
    if preguntas_ids and len(session.get('respuestas', {})) == len(preguntas_ids):
        conexion = Conexion()
        examen = Examenes(session['examen_id'], session['tipo'], session['usuario_id'], '')
        examen.calificar_examen(conexion)
        flash('Examen calificado automáticamente.')
        for k in ['preguntas','respuestas','examen_id','tipo','time_lefts']:
            session.pop(k, None)
        return redirect('/dashboard')

    indice = int(request.args.get('indice', 0))
    total  = len(preguntas_ids)
    pid    = preguntas_ids[indice]

    # Saltar expiradas al avanzar
    if request.args.get('volver') != '1' and str(indice) in session['respuestas'] and session['respuestas'][str(indice)] is None:
        siguiente = indice + 1
        if siguiente < total:
            return redirect(f'/mostrar_examen?indice={siguiente}')
        # Última expiró → calificar
        conexion = Conexion()
        examen = Examenes(session['examen_id'], session['tipo'], session['usuario_id'], '')
        examen.calificar_examen(conexion)
        flash('Examen calificado automáticamente.')
        for k in ['preguntas','respuestas','examen_id','tipo','time_lefts']:
            session.pop(k, None)
        return redirect('/dashboard')

    rem = session['time_lefts'].get(str(indice), 60)
    conexion = Conexion()
    preguntas = Preguntas.obtener_todos(conexion)
    respuestas = Respuestas.obtener_todos(conexion)
    dict_preg = {p.pregunta_id: p for p in preguntas}
    for r in respuestas:
        dict_preg[r.pregunta_id].agregar_respuesta(r)
    conexion.cerrar_conexion()

    pregunta_actual   = dict_preg[pid]
    respuesta_guardada = session['respuestas'].get(str(indice))

    return render_template(
        'mostrar_examen.html',
        pregunta=pregunta_actual,
        respuesta_guardada=respuesta_guardada,
        indice_actual=indice,
        total_preguntas=total,
        examen_id=session['examen_id'],
        tipo=session['tipo'],
        time_left=rem
    )

# Guardar respuesta o timeout
@app.route('/guardar_respuesta', methods=['POST'])
def guardar_respuesta():
    if 'usuario_id' not in session:
        return redirect('/login')

    indice       = int(request.form['indice_actual'])
    accion       = request.form['accion']
    respuesta_id = request.form.get('respuesta_id')
    pregunta_id  = request.form['pregunta_id']
    examen_id    = session['examen_id']
    timed_out    = request.form.get('timed_out') == '1'
    rem          = int(request.form.get('time_left', 0))

    # 1) Actualizar tiempo restante
    session['time_lefts'][str(indice)] = rem
    session.modified = True

    conexion = Conexion()
    conn     = conexion.obtener_conexion()
    cur      = conn.cursor()

    # 2) Registrar timeout como respuesta incorrecta
    if timed_out and not respuesta_id:
        cur.execute(
            "SELECT respuesta_id FROM Respuestas WHERE pregunta_id=%s AND es_correcta=FALSE LIMIT 1",
            (pregunta_id,)
        )
        fila = cur.fetchone()
        if fila:
            wrong = fila[0]
            cur.execute(
                "INSERT INTO RespuestasDadas (examen_id,pregunta_id,respuesta_id) VALUES(%s,%s,%s)",
                (examen_id, pregunta_id, wrong)
            )
            session['respuestas'][str(indice)] = wrong
        else:
            session['respuestas'][str(indice)] = None
        conn.commit()
        conexion.cerrar_conexion()

    # 3) Registrar respuesta manual (insert/update)
    elif respuesta_id:
        val = int(respuesta_id)
        session['respuestas'][str(indice)] = val

        cur.execute(
            "SELECT 1 FROM RespuestasDadas WHERE examen_id=%s AND pregunta_id=%s",
            (examen_id, pregunta_id)
        )
        if cur.fetchone():
            cur.execute(
                "UPDATE RespuestasDadas SET respuesta_id=%s WHERE examen_id=%s AND pregunta_id=%s",
                (val, examen_id, pregunta_id)
            )
        else:
            cur.execute(
                "INSERT INTO RespuestasDadas (examen_id,pregunta_id,respuesta_id) VALUES(%s,%s,%s)",
                (examen_id, pregunta_id, val)
            )
        conn.commit()
        conexion.cerrar_conexion()

    # 4) Navegación entre preguntas
    if accion == 'anterior':
        return redirect(f'/mostrar_examen?indice={indice-1}&volver=1')
    if accion == 'siguiente':
        return redirect(f'/mostrar_examen?indice={indice+1}')

    # 5) Al pulsar "Terminar": validar pendientes antes de calificar
    if accion == 'terminar':
        preguntas_ids = session.get('preguntas', [])
        total = len(preguntas_ids)
        respuestas = session.get('respuestas', {})

        # Índices de preguntas sin respuesta
        pendientes = [i for i in range(total) if str(i) not in respuestas]

        if pendientes:
            nums = [str(i+1) for i in pendientes]  # convertir a 1-based
            flash(f'Debes responder las preguntas: {", ".join(nums)}.')
            return redirect(f'/mostrar_examen?indice={pendientes[0]}')

        # 6) Si no hay pendientes, calificar el examen
        conexion = Conexion()
        examen = Examenes(session['examen_id'], session['tipo'], session['usuario_id'], '')
        examen.calificar_examen(conexion)

        # 7) Guardar resultados en sesión
        session['correctas']       = examen.correctas
        session['total_preguntas'] = examen.total_preguntas
        session['puntuacion']      = examen.puntuacion
        session['max_puntos']      = examen.total_preguntas * (2.5 if session['tipo']=='final' else 5)
        session['percentage']      = examen.porcentaje
        session['level']           = examen.nivel

        flash('Examen finalizado y calificado.')

        # 8) Limpiar datos del examen en sesión
        for k in ['preguntas','respuestas','examen_id','tipo','time_lefts']:
            session.pop(k, None)

        return redirect('/resultados')

    # 9) En cualquier otro caso, volver al dashboard
    return redirect('/dashboard')


@app.route('/resultados')
def resultados():
    if 'usuario_id' not in session:
        return redirect('/login')

    correctas = session.pop('correctas', 0)
    total_preguntas = session.pop('total_preguntas', 0)
    puntuacion = session.pop('puntuacion', 0)
    max_puntos = session.pop('max_puntos', 0)
    percentage = session.pop('percentage', 0)
    level = session.pop('level', 'Desconocido')

    return render_template(
        'resultados.html',
        correctas=correctas,
        total_preguntas=total_preguntas,
        puntuacion=puntuacion,
        max_puntos=max_puntos,
        percentage=percentage,
        level=level
    )


# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == '__main__':
    app.run(debug=True)

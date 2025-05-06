from flask import Flask, render_template, request, redirect, session, flash, url_for
from Clases.conexion import Conexion
from Clases.Usuarios import Usuarios
from Clases.Preguntas import Preguntas
from Clases.Respuestas import Respuestas
from Clases.Examenes import Examenes
from Clases.RespuestaUsuario import RespuestaUsuario
import hashlib
import random
import matplotlib.pyplot as plt
from io import BytesIO
import base64

app = Flask(__name__, template_folder='interfaz', static_folder='Style')
app.secret_key = 'super_secret_key'

def obtener_examenes_filtrados(start_date, end_date, tipo):
    """
    Devuelve lista de examenes (con usuario) filtrados por fecha y tipo.
    """
    conexion = Conexion()
    conn = conexion.obtener_conexion()
    cursor = conn.cursor(dictionary=True)
    sql = (
        "SELECT e.examen_id, e.tipo, e.usuario_id, u.nombre AS usuario, "
        "e.nivel, e.puntuacion, e.porcentaje, e.fecha "
        "FROM Examenes e JOIN Usuarios u ON e.usuario_id = u.usuario_id "
        "WHERE 1=1"
    )
    params = []
    if tipo and tipo != 'todos':
        sql += " AND e.tipo = %s"
        params.append(tipo)
    if start_date:
        sql += " AND e.fecha >= %s"
        params.append(start_date)
    if end_date:
        # incluir todo el día
        sql += " AND e.fecha <= %s"
        params.append(end_date + " 23:59:59")
    sql += " ORDER BY e.fecha DESC"
    cursor.execute(sql, tuple(params))
    rows = cursor.fetchall()
    conexion.cerrar_conexion()
    return rows

def fig_to_base64(fig):
    buf = BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    data = base64.b64encode(buf.getvalue()).decode('ascii')
    plt.close(fig)
    return data

@app.route('/', methods=['GET'])
def home():
    # Recuperar filtros
    start_date = request.args.get('start_date', '')
    end_date   = request.args.get('end_date', '')
    tipo       = request.args.get('tipo', 'todos')
    # Obtener los exámenes
    examenes = obtener_examenes_filtrados(start_date, end_date, tipo)

    # 1) Gráfica de puntuación en el tiempo
    fechas     = [e['fecha'] for e in examenes]
    puntuaciones = [e['puntuacion'] or 0 for e in examenes]
    fig1, ax1 = plt.subplots()
    ax1.plot(fechas, puntuaciones, marker='o')
    ax1.set_title('Puntuación en el Tiempo')
    ax1.set_xlabel('Fecha')
    ax1.set_ylabel('Puntuación')
    chart_scores = fig_to_base64(fig1)

    # 2) Gráfica de cantidad por tipo de examen
    tipos = [e['tipo'] for e in examenes]
    tipos_unicos = list(set(tipos))
    counts = [tipos.count(t) for t in tipos_unicos]
    fig2, ax2 = plt.subplots()
    ax2.bar(tipos_unicos, counts)
    ax2.set_title('Cantidad de Exámenes por Tipo')
    ax2.set_ylabel('Cantidad')
    chart_types = fig_to_base64(fig2)

    # 3) Gráfica de usuarios únicos
    usuarios_unicos = len({e['usuario_id'] for e in examenes})
    fig3, ax3 = plt.subplots()
    ax3.bar(['Usuarios'], [usuarios_unicos])
    ax3.set_title('Usuarios Únicos')
    ax3.set_ylabel('Cantidad')
    chart_users = fig_to_base64(fig3)

    # Renderiza la plantilla pasando las tres gráficas
    return render_template(
        'index.html',
        examenes=examenes,
        start_date=start_date,
        end_date=end_date,
        tipo=tipo,
        chart_scores=chart_scores,
        chart_types=chart_types,
        chart_users=chart_users
    )


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo    = request.form['correo']
        contrasena= request.form['contrasena']
        hashed    = hashlib.sha256(contrasena.encode()).hexdigest()
        conexion  = Conexion()
        conn      = conexion.obtener_conexion()
        cursor    = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM Usuarios WHERE correo = %s AND contrasena = %s",
            (correo, hashed)
        )
        user = cursor.fetchone()
        conexion.cerrar_conexion()

        if user:
            session.clear()
            session['usuario_id'] = user['usuario_id']
            session['nombre']     = user['nombre']
            return redirect('/dashboard')
        else:
            flash('Correo o contraseña incorrectos')
    else:
        # limpia flashes anteriores
        session.pop('_flashes', None)
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nombre    = request.form['nombre']
        apellido  = request.form['apellido']
        correo    = request.form['correo']
        contrasena= request.form['contrasena']
        genero    = request.form['genero']
        conexion  = Conexion()
        conn      = conexion.obtener_conexion()
        cursor    = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO Usuarios (nombre, apellido, correo, contrasena, genero) "
                "VALUES (%s, %s, %s, %s, %s)",
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

@app.route('/dashboard')
def dashboard():
    if 'usuario_id' not in session:
        return redirect('/login')

    conexion     = Conexion()
    conn         = conexion.obtener_conexion()
    cursor       = conn.cursor(dictionary=True)
    usuario_id   = session['usuario_id']
    cursor.execute(
        "SELECT fecha, tipo FROM Examenes WHERE usuario_id = %s",
        (usuario_id,)
    )
    examenes     = cursor.fetchall()
    conexion.cerrar_conexion()

    practicas    = sum(1 for e in examenes if e['tipo'] == 'practica')
    finales      = sum(1 for e in examenes if e['tipo'] == 'final')
    intentos_pr  = max(0, 5 - practicas)
    intentos_fin = max(0, 2 - finales)

    return render_template(
        'menu.html',
        nombre=session['nombre'],
        intentos_practica=intentos_pr,
        intentos_final=intentos_fin
    )

@app.route('/iniciar_examen/<tipo>')
def iniciar_examen(tipo):
    if 'usuario_id' not in session:
        return redirect('/login')
    if tipo not in ['practica','final']:
        flash('Tipo de examen inválido')
        return redirect('/dashboard')

    session['tipo'] = tipo
    # 1) Cargamos preguntas y respuestas
    c1 = Conexion()
    preguntas = Preguntas.obtener_todos(c1)
    respuestas = Respuestas.obtener_todos(c1)
    dict_preg = {p.pregunta_id: p for p in preguntas}
    for r in respuestas:
        dict_preg[r.pregunta_id].agregar_respuesta(r)
    c1.cerrar_conexion()

    # 2) Creamos examen en BD
    c2 = Conexion()
    if tipo == 'practica':
        examen_usuario  = Examenes.crear_examen_para_usuario(c2, session['usuario_id'])
        preguntas_examen = Preguntas.generar_examen_practica(preguntas)
    else:
        examen_usuario  = Examenes.crear_examen_final_para_usuario(c2, session['usuario_id'])
        preguntas_examen = Preguntas.generar_examen_final(preguntas)
    c2.cerrar_conexion()

    # 3) Guardamos en sesión y redirigimos a la primera pregunta
    session['preguntas']  = [p.pregunta_id for p in preguntas_examen]
    session['examen_id']  = examen_usuario.examen_id
    session['respuestas'] = {}
    session['time_lefts'] = { str(i): 60 for i in range(len(preguntas_examen)) }
    session.modified       = True

    return redirect('/mostrar_examen?indice=0')

@app.route('/mostrar_examen', methods=['GET'])
def mostrar_examen_route():
    if 'usuario_id' not in session:
        return redirect('/login')

    preguntas_ids = session.get('preguntas', [])
    # si todas respondidas → calificar y volver
    if preguntas_ids and len(session.get('respuestas', {})) == len(preguntas_ids):
        c = Conexion()
        examen = Examenes(session['examen_id'], session['tipo'], session['usuario_id'], '')
        examen.calificar_examen(c)
        flash('Examen calificado automáticamente.')
        for k in ['preguntas','respuestas','examen_id','tipo','time_lefts']:
            session.pop(k, None)
        return redirect('/dashboard')

    indice = int(request.args.get('indice', 0))
    total  = len(preguntas_ids)
    pid    = preguntas_ids[indice]

    # cargar pregunta actual
    c = Conexion()
    preguntas = Preguntas.obtener_todos(c)
    respuestas= Respuestas.obtener_todos(c)
    dict_preg = {p.pregunta_id: p for p in preguntas}
    for r in respuestas:
        dict_preg[r.pregunta_id].agregar_respuesta(r)
    c.cerrar_conexion()

    pregunta_actual   = dict_preg[pid]
    respuesta_guardada= session['respuestas'].get(str(indice))
    time_left         = session['time_lefts'].get(str(indice), 60)

    return render_template(
        'mostrar_examen.html',
        pregunta=pregunta_actual,
        respuesta_guardada=respuesta_guardada,
        indice_actual=indice,
        total_preguntas=total,
        examen_id=session['examen_id'],
        tipo=session['tipo'],
        time_left=time_left
    )

@app.route('/guardar_respuesta', methods=['POST'])
def guardar_respuesta():
    if 'usuario_id' not in session:
        return redirect('/login')

    indice      = int(request.form['indice_actual'])
    accion      = request.form['accion']
    respuesta_id= request.form.get('respuesta_id')
    pregunta_id = request.form['pregunta_id']
    examen_id   = session['examen_id']
    timed_out   = request.form.get('timed_out') == '1'
    rem         = int(request.form.get('time_left', 0))

    # actualizar tiempo
    session['time_lefts'][str(indice)] = rem
    session.modified = True

    c = Conexion()
    conn = c.obtener_conexion()
    cur  = conn.cursor()

    # timeout → respuesta incorrecta aleatoria
    if timed_out and not respuesta_id:
        cur.execute(
            "SELECT respuesta_id FROM Respuestas WHERE pregunta_id=%s AND es_correcta=FALSE LIMIT 1",
            (pregunta_id,)
        )
        row = cur.fetchone()
        wrong = row[0] if row else None
        if wrong:
            cur.execute(
                "INSERT INTO RespuestasDadas (examen_id,pregunta_id,respuesta_id) VALUES(%s,%s,%s)",
                (examen_id, pregunta_id, wrong)
            )
            session['respuestas'][str(indice)] = wrong
        else:
            session['respuestas'][str(indice)] = None
        conn.commit()
        c.cerrar_conexion()

    # respuesta manual
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
        c.cerrar_conexion()

    # navegación
    if accion == 'anterior':
        return redirect(f'/mostrar_examen?indice={indice-1}&volver=1')
    if accion == 'siguiente':
        return redirect(f'/mostrar_examen?indice={indice+1}')

    # terminar → validar pendientes y calificar
    if accion == 'terminar':
        preguntas_ids = session.get('preguntas', [])
        total = len(preguntas_ids)
        pendientes = [i for i in range(total) if str(i) not in session['respuestas']]
        if pendientes:
            nums = [str(i+1) for i in pendientes]
            flash(f'Debes responder las preguntas: {", ".join(nums)}.')
            return redirect(f'/mostrar_examen?indice={pendientes[0]}')

        c2 = Conexion()
        examen = Examenes(session['examen_id'], session['tipo'], session['usuario_id'], '')
        examen.calificar_examen(c2)

        # guardar resultados
        session['correctas']       = getattr(examen, 'correctas', 0)
        session['total_preguntas'] = getattr(examen, 'total_preguntas', 0)
        session['puntuacion']      = getattr(examen, 'puntuacion', 0)
        session['max_puntos']      = session['total_preguntas'] * (2.5 if session['tipo']=='final' else 5)
        session['percentage']      = getattr(examen, 'porcentaje', 0)
        session['level']           = getattr(examen, 'nivel', 'Desconocido')

        flash('Examen finalizado y calificado.')
        for k in ['preguntas','respuestas','examen_id','tipo','time_lefts']:
            session.pop(k, None)
        return redirect('/resultados')

    return redirect('/dashboard')

@app.route('/resultados')
def resultados():
    if 'usuario_id' not in session:
        return redirect('/login')

    correctas       = session.pop('correctas', 0)
    total_preguntas = session.pop('total_preguntas', 0)
    puntuacion      = session.pop('puntuacion', 0)
    max_puntos      = session.pop('max_puntos', 0)
    percentage      = session.pop('percentage', 0)
    level           = session.pop('level', 'Desconocido')

    return render_template(
        'resultados.html',
        correctas=correctas,
        total_preguntas=total_preguntas,
        puntuacion=puntuacion,
        max_puntos=max_puntos,
        percentage=percentage,
        level=level
    )

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == '__main__':
    app.run(debug=True)
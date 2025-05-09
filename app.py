from flask import Flask, render_template, request, redirect, session, flash, url_for
from Clases.conexion import Conexion
from Clases.Usuarios import Usuarios
from Clases.Preguntas import Preguntas
from Clases.Respuestas import Respuestas
from Clases.Examenes import Examenes
from Clases.RespuestaUsuario import RespuestaUsuario
import hashlib
import random
from collections import Counter
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from io import BytesIO
import base64
import pandas as pd

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
    img = base64.b64encode(buf.getvalue()).decode('ascii')
    buf.close()
    plt.close(fig)
    return data
    return img

def load_examenes(start_date, end_date, tipo):
    # Carga los exámenes en un DataFrame
    c = Conexion()
    conn = c.obtener_conexion()
    query = """
      SELECT e.fecha, e.porcentaje, e.tipo, e.nivel
      FROM Examenes e
      WHERE (%s = 'todos' OR e.tipo = %s)
        AND (%s = '' OR e.fecha >= %s)
        AND (%s = '' OR e.fecha <= %s)
    """
    params = [tipo, tipo, start_date, start_date, end_date, end_date + " 23:59:59"]
    df = pd.read_sql_query(query, conn, params=params, parse_dates=['fecha'])
    c.cerrar_conexion()
    return df

@app.route('/', methods=['GET'])
def home():
    start_date = request.args.get('start_date', '')
    end_date   = request.args.get('end_date', '')
    tipo       = request.args.get('tipo', 'todos')
    examenes   = obtener_examenes_filtrados(start_date, end_date, tipo)

    df = load_examenes(start_date, end_date, tipo)
    puntuaciones = []
    for e in examenes:
        try:
            # convierte a float; si falla, pon 0.0
            puntuaciones.append(float(e.get('puntuacion') or 0.0))
        except Exception:
            puntuaciones.append(0.0)

    fig1, ax1 = plt.subplots()
    ax1.hist(puntuaciones, bins=10, edgecolor='black')
    ax1.set_title('Distribución de Puntuaciones')
    ax1.set_xlabel('Puntuación')
    ax1.set_ylabel('Frecuencia')
    chart_scores = fig_to_base64(fig1)
    
    fig1, ax1 = plt.subplots()
    ax1.hist(df['porcentaje'].dropna(), bins=10, edgecolor='black')
    ax1.set_title('Distribución de Porcentajes')
    ax1.set_xlabel('Porcentaje')
    ax1.set_ylabel('Cantidad')
    chart_hist = fig_to_base64(fig1)

    # 2) Gráfico de pastel de tipos de examen
    tipos = [e['tipo'] for e in examenes]
    tipos_unicos = list(set(tipos))
    counts = [tipos.count(t) for t in tipos_unicos]
    fig2, ax2 = plt.subplots()
    ax2.pie(counts, labels=tipos_unicos, autopct='%1.1f%%', startangle=90)
    ax2.axis('equal')
    ax2.set_title('Distribución por Tipo de Examen')
    buf2 = BytesIO(); fig2.savefig(buf2, format='png', bbox_inches='tight'); buf2.seek(0)
    chart_types = base64.b64encode(buf2.getvalue()).decode('ascii')
    plt.close(fig2)

    # 3) Histograma de número de exámenes por usuario
    #    (histograma de la lista [conteo_examenes_por_usuario])
    from collections import Counter
    user_counts = list(Counter(e['usuario_id'] for e in examenes).values())
    fig3, ax3 = plt.subplots()
    ax3.hist(user_counts, bins=range(1, max(user_counts or [1]) + 2), align='left', edgecolor='black')
    ax3.set_xticks(range(1, max(user_counts or [1]) + 1))
    ax3.set_title('Exámenes por Usuario')
    ax3.set_xlabel('Número de Exámenes')
    ax3.set_ylabel('Cantidad de Usuarios')
    buf3 = BytesIO(); fig3.savefig(buf3, format='png', bbox_inches='tight'); buf3.seek(0)
    chart_users = base64.b64encode(buf3.getvalue()).decode('ascii')
    plt.close(fig3)
    
    avg_by_type = df.groupby('tipo')['porcentaje'].mean()
    fig3, ax3 = plt.subplots()
    ax3.bar(avg_by_type.index, avg_by_type.values)
    ax3.set_title('Promedio de Porcentaje por Tipo')
    ax3.set_xlabel('Tipo de Examen')
    ax3.set_ylabel('Promedio (%)')
    chart_avgtype = fig_to_base64(fig3)
    
    counts_nivel = df['nivel'].value_counts()
    fig4, ax4 = plt.subplots()
    ax4.pie(counts_nivel.values, labels=counts_nivel.index, autopct='%1.1f%%', startangle=90)
    ax4.set_title('Distribución de Niveles Aprobados')
    ax4.axis('equal')
    chart_pie = fig_to_base64(fig4)

    return render_template(
        'index.html',
        start_date=start_date,
        end_date=end_date,
        tipo=tipo,
        # ya no necesitas pasar examenes si sólo vas a mostrar gráficos
        chart_scores=chart_scores,
        chart_hist=chart_hist,
        chart_types=chart_types,
        chart_users=chart_users,
        chart_avgtype=chart_avgtype,
        chart_pie=chart_pie
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

    user_id = session['usuario_id']

    # 1) Exámenes calificados (tabla + histograma)
    c = Conexion()
    cursor = c.obtener_conexion().cursor(dictionary=True)
    cursor.execute("""
        SELECT examen_id, fecha, tipo, nivel, puntuacion
        FROM Examenes
        WHERE usuario_id = %s AND puntuacion IS NOT NULL
        ORDER BY fecha DESC
    """, (user_id,))
    examenes = cursor.fetchall()
    c.cerrar_conexion()

    # 2) Contar intentos usados
    c2 = Conexion()
    cur2 = c2.obtener_conexion().cursor()
    cur2.execute("""
        SELECT tipo, COUNT(*) FROM Examenes
        WHERE usuario_id = %s
        GROUP BY tipo
    """, (user_id,))
    counts = {row[0]: row[1] for row in cur2.fetchall()}
    c2.cerrar_conexion()

    used_pr = counts.get('practica', 0)
    used_fn = counts.get('final', 0)
    max_pr = 5
    max_fn = 2
    left_pr = max(0, max_pr - used_pr)
    left_fn = max(0, max_fn - used_fn)

    # 3) Histograma de calificaciones
    puntuaciones = []
    for e in examenes:
        try:
            puntuaciones.append(float(e['puntuacion']))
        except:
            continue

    fig, ax = plt.subplots()
    ax.hist(puntuaciones, bins=10, edgecolor='black')
    ax.set_title('Histograma de Mis Calificaciones')
    ax.set_xlabel('Calificación')
    ax.set_ylabel('Frecuencia')
    buf = BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    chart_scores = base64.b64encode(buf.getvalue()).decode('ascii')
    plt.close(fig)

    return render_template(
        'menu.html',
        nombre=session['nombre'],
        examenes=examenes,
        chart_scores=chart_scores,
        used_pr=used_pr,
        used_fn=used_fn,
        left_pr=left_pr,
        left_fn=left_fn,
        max_pr=max_pr,
        max_fn=max_fn
    )

@app.route('/iniciar_examen/<tipo>')
def iniciar_examen(tipo):
    if 'usuario_id' not in session:
        return redirect('/login')
    if tipo not in ['practica','final']:
        flash('Tipo de examen inválido')
        return redirect('/dashboard')

    # Valida intentos antes de crear examen
    user_id = session['usuario_id']
    c = Conexion()
    cur = c.obtener_conexion().cursor()
    cur.execute("""
        SELECT COUNT(*) FROM Examenes WHERE usuario_id = %s AND tipo = %s
    """, (user_id, tipo))
    used = cur.fetchone()[0]
    c.cerrar_conexion()

    limit = 5 if tipo == 'practica' else 2
    if used >= limit:
        flash(f'Has agotado tus {limit} intentos de examen "{tipo}".')
        return redirect('/dashboard')

    # Si quedan intentos, procedemos como antes
    session['tipo'] = tipo

    # 1) Carga preguntas/respuestas
    c1 = Conexion()
    preguntas = Preguntas.obtener_todos(c1)
    respuestas = Respuestas.obtener_todos(c1)
    dict_preg = {p.pregunta_id: p for p in preguntas}
    for r in respuestas:
        dict_preg[r.pregunta_id].agregar_respuesta(r)
    c1.cerrar_conexion()

    # 2) Crear examen en BD
    c2 = Conexion()
    if tipo == 'practica':
        examen_usuario = Examenes.crear_examen_para_usuario(c2, user_id)
        preguntas_examen = Preguntas.generar_examen_practica(preguntas)
    else:
        examen_usuario = Examenes.crear_examen_final_para_usuario(c2, user_id)
        preguntas_examen = Preguntas.generar_examen_final(preguntas)
    c2.cerrar_conexion()

    # 3) Guardar en sesión y redirigir
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

    # Datos del formulario
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

    # 2) Conexión para registro
    conexion = Conexion()
    conn     = conexion.obtener_conexion()
    cur      = conn.cursor()

    # 3) Timeout o salto marcado
    if timed_out and not respuesta_id:
        # Selecciona alguna respuesta incorrecta para registrar
        cur.execute(
            "SELECT respuesta_id FROM Respuestas WHERE pregunta_id=%s AND es_correcta=FALSE LIMIT 1",
            (pregunta_id,)
        )
        fila = cur.fetchone()
        wrong = fila[0] if fila else None
        if wrong:
            cur.execute(
                "INSERT INTO RespuestasDadas (examen_id,pregunta_id,respuesta_id) VALUES (%s,%s,%s)",
                (examen_id, pregunta_id, wrong)
            )
        session['respuestas'][str(indice)] = wrong
        conn.commit()
        conexion.cerrar_conexion()
        flash('Se te acabó el tiempo o decidiste saltar esta pregunta.')
    # 4) Respuesta manual
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
                "INSERT INTO RespuestasDadas (examen_id,pregunta_id,respuesta_id) VALUES (%s,%s,%s)",
                (examen_id, pregunta_id, val)
            )
        conn.commit()
        conexion.cerrar_conexion()

    # 5) Navegación
    if accion == 'siguiente':
        return redirect(f'/mostrar_examen?indice={indice+1}')
    # El botón “Anterior” ya no existe, así que no lo manejamos

    # 6) Al terminar: validar pendientes
    if accion == 'terminar':
        preguntas_ids = session.get('preguntas', [])
        total = len(preguntas_ids)
        respuestas = session.get('respuestas', {})

        pendientes = [i for i in range(total) if str(i) not in respuestas]
        if pendientes:
            nums = [str(i+1) for i in pendientes]
            flash(f'Debes responder las preguntas: {", ".join(nums)}.')
            return redirect(f'/mostrar_examen?indice={pendientes[0]}')

        # 7) Calificar
        conexion2 = Conexion()
        examen = Examenes(session['examen_id'], session['tipo'], session['usuario_id'], '')
        examen.calificar_examen(conexion2)

        # 8) Guardar resultados en sesión
        session['correctas']         = examen.correctas
        session['total_preguntas']   = examen.total_preguntas
        session['puntuacion']        = examen.puntuacion
        session['max_puntos']        = examen.total_preguntas * (2.5 if session['tipo']=='final' else 5)
        session['percentage']        = examen.porcentaje
        session['level']             = examen.nivel
        session['respuestas_usuario']  = session['respuestas']
        session['preguntas_ordenadas'] = session['preguntas']

        flash('Examen finalizado y calificado.')

        # 9) Limpiar variables de examen
        for k in ['preguntas','respuestas','examen_id','tipo','time_lefts']:
            session.pop(k, None)

        return redirect('/resultados')

    # 10) En cualquier otro caso, volver al dashboard
    return redirect('/dashboard')

@app.route('/resultados')
def resultados():
    if 'usuario_id' not in session:
        return redirect('/login')

    # ——— 1) totales ———
    correctas       = session.pop('correctas', 0)
    total_preguntas = session.pop('total_preguntas', 0)
    puntuacion      = session.pop('puntuacion', 0)
    max_puntos      = session.pop('max_puntos', 0)
    percentage      = session.pop('percentage', 0)
    level           = session.pop('level', 'Desconocido')

    # ——— 2) detalle de preguntas y respuestas ———
    preguntas_ids = session.pop('preguntas_ordenadas', [])
    resp_usu     = session.pop('respuestas_usuario', {})

    conexion = Conexion()
    preguntas = Preguntas.obtener_todos(conexion)
    respuestas= Respuestas.obtener_todos(conexion)
    conexion.cerrar_conexion()

    # armar lista en orden
    detalle = []
    for idx, pid in enumerate(preguntas_ids):
        p = next(q for q in preguntas if q.pregunta_id == pid)
        # respuestas de la pregunta
        opts = [r for r in respuestas if r.pregunta_id == pid]
        # id correcta
        corr_id = next(r.respuesta_id for r in opts if r.es_correcta)
        sel_id  = resp_usu.get(str(idx))
        detalle.append({
            'texto': p.texto,
            'opciones': opts,
            'seleccionada': sel_id,
            'correcta': corr_id
        })

    return render_template(
        'resultados.html',
        correctas=correctas,
        total_preguntas=total_preguntas,
        puntuacion=puntuacion,
        max_puntos=max_puntos,
        percentage=percentage,
        level=level,
        detalle=detalle
    )

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == '__main__':
    app.run(debug=True)
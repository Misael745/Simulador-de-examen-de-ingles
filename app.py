from flask import Flask, render_template, request, redirect, session, flash, url_for
from Clases.conexion import Conexion
import hashlib

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


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == '__main__':
    app.run(debug=True)

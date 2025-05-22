
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from werkzeug.utils import secure_filename
import mysql.connector
import os

app = Flask(__name__)
CORS(app)

# Configuración de carpeta para subir imágenes
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['plantas'] = os.path.join(os.path.dirname(__file__), 'static', 'imgs','plantas')

# Función para conectar a la base de datos
def get_connection():
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='',
        database='bdplantas'
    )

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/registrar', methods=['POST'])
def registrar():
    data = request.get_json()
    nombre = data.get('nombre')
    correo = data.get('correo')

    if not nombre or not correo:
        return jsonify({'error': 'Nombre y correo son requeridos'}), 400

    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO usuarios (nombre, correo) VALUES (%s, %s)", (nombre, correo))
        conn.commit()
        return jsonify({'mensaje': 'Usuario registrado'})
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/usuarios')
def usuarios():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT nombre, correo FROM usuarios")
        rows = cursor.fetchall()
        return jsonify([{'nombre': r[0], 'correo': r[1]} for r in rows])
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/plantas', methods=['GET', 'POST'])
def plantas():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                p.idPlantas, 
                p.nombreCientifico, 
                p.linkimagen,
                GROUP_CONCAT(n.nombreComun SEPARATOR ', ') AS nombres_comunes
            FROM 
                plantas p
            LEFT JOIN 
                nombres_comunes n ON p.idPlantas = n.fk_Plantas
            GROUP BY 
                p.idPlantas, p.nombreCientifico, p.linkimagen
        """)
        rows = cursor.fetchall()
        resultado = []
        for r in rows:
            resultado.append({
                'idPlantas': r[0],
                'nombreCientifico': r[1],
                'linkimagen': r[2],
                'nombres_comunes': r[3] if r[3] else ''
            })
        return render_template('visualizar_plantas.html', plantas=resultado)
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/registrar_planta', methods=['GET', 'POST'])
def registrar_planta():
    familias = []
    mensaje = None

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT nomFamilia FROM familiasPlantas")
        familias = [row['nomFamilia'] for row in cursor.fetchall()]
        print(familias) 
    finally:
        cursor.close()
        conn.close()
    

    if request.method == 'POST':
        nombreCientifico = request.form['nombreCientifico']
        nomFamilia = request.form['nomFamilia']
        nombresComunes = request.form['nombresComunes']
        imagen = request.files['imagen']

        if imagen and imagen.filename.endswith('.jpg'):
            nombre_cientifico = request.form['nombreCientifico']
            nombre_archivo = secure_filename(nombre_cientifico).lower()
            nombre_archivo = nombre_archivo + ".jpg"
            ruta = os.path.join(app.config['plantas'], nombre_archivo)
            imagen.save(ruta)

            try:
                conn = get_connection()
                cursor = conn.cursor(dictionary=True)
                cursor.callproc('gestionar_plantas', [1, None, nombreCientifico, nombre_archivo, nomFamilia, nombresComunes])
                for result in cursor.stored_results():
                    mensaje = result.fetchall()[0]['respuesta']
                conn.commit()
            except Exception as e:
                mensaje = f'Error en el servidor: {str(e)}'
            finally:
                cursor.close()
                conn.close()

    return render_template('registro_plantas.html', mensaje=mensaje, familias=familias)

if __name__ == '__main__':
    app.run(debug=True)

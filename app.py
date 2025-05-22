import requests
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from werkzeug.utils import secure_filename
import mysql.connector
import os

app = Flask(__name__)
CORS(app)

PLANTNET_API_KEY = '2b10Q1pjh95QnKNGhW1eXZLO'
PLANTNET_API_URL = f"https://my-api.plantnet.org/v2/identify/all?api-key={PLANTNET_API_KEY}&lang=es&include-related-images=true"
IA_UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads', 'identificador_ia')
os.makedirs(IA_UPLOAD_FOLDER, exist_ok=True)

# Configuración de carpeta para subir imágenes
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'subidas')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['plantas'] = os.path.join(os.path.dirname(__file__), 'static', 'imgs','plantas')

######################
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg'}

@app.route('/identificar_ia', methods=['GET', 'POST'])
def identificar_ia():
    if request.method == 'POST':
        if 'image' not in request.files:
            return jsonify({'error': 'No se proporcionó imagen'}), 400
        file = request.files['image']

        if file.filename == '' or not allowed_file(file.filename):
            return jsonify({'error': 'Archivo no válido'}), 400

        filename = secure_filename(file.filename)
        filepath = os.path.join(IA_UPLOAD_FOLDER, filename)
        file.save(filepath)

        with open(filepath, 'rb') as img:
            files = {'images': img}
            data = {'organs': request.form.get('organ', 'leaf')}

            try:
                response = requests.post(PLANTNET_API_URL, files=files, data=data)
                response.raise_for_status()
                result = response.json()

                if not result["results"]:
                    return jsonify({'message': 'No se encontraron coincidencias'})

                top = result["results"][0]
                species = top["species"]
                images = top.get("images", [])

                image_urls = []
                for i, img_data in enumerate(images[:1]):
                    url = img_data.get("url")
                    if url:
                        specific_url = url.get("m")
                        if specific_url:
                            image_urls.append(specific_url)

                return jsonify({
                    'identifiedOrgan': images[0].get("organ") if images else 'Desconocido',
                    'scientificName': species.get("scientificNameWithoutAuthor", "Desconocido"),
                    'authorship': species.get("scientificNameAuthorship", ""),
                    'commonNames': species.get("commonNames", []),
                    'genus': species.get("genus", {}).get("scientificNameWithoutAuthor", ""),
                    'family': species.get("family", {}).get("scientificNameWithoutAuthor", ""),
                    'score': round(top.get("score", 0) * 100, 2),
                    'imageUrls': image_urls
                })

            except requests.RequestException:
                return jsonify({'message': 'Error al identificar la planta'}), 500

    return render_template('identificador_ia.html')

############

# Función para conectar a la base de datos
def get_connection():
    return mysql.connector.connect(
        host='bdyuri.cpikeig8qwsl.us-east-1.rds.amazonaws.com',
        user='admin',
        password='23072208aaA',
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
        cursor.execute("SELECT nomFamilia FROM familiasplantas")
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

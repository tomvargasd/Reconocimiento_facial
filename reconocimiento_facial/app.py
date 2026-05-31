import os
# pyrefly: ignore [missing-import]
from flask import Flask, render_template, request, redirect, url_for
import database
import face_utils
import cv2
import numpy as np
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/profiles_data'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/profiles', methods=['GET', 'POST'])
def profiles():
    conn = database.get_conn()
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        if nombre:
            conn.execute('INSERT INTO Personas (nombre) VALUES (?)', (nombre,))
            conn.commit()
            return redirect(url_for('profiles'))
            
    personas = conn.execute('SELECT * FROM Personas').fetchall()
    conn.close()
    return render_template('profiles.html', personas=personas)

@app.route('/upload_profile_image/<int:persona_id>', methods=['POST'])
def upload_profile_image(persona_id):
    if 'image' not in request.files:
        return redirect(url_for('profiles'))
    file = request.files['image']
    if file.filename == '':
        return redirect(url_for('profiles'))
        
    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{persona_id}_{filename}")
        file.save(filepath)
        
        # Procesar la imagen
        image = cv2.imread(filepath)
        rects = face_utils.detect_faces(image)
        if len(rects) > 0:
            x, y, w, h = rects[0] # Tomar el primer rostro
            face_image = image[y:y+h, x:x+w]
            features = face_utils.extract_features(face_image)
            
            conn = database.get_conn()
            conn.execute('INSERT INTO ImagenesPerfil (persona_id, ruta_imagen, caracteristicas_faciales) VALUES (?, ?, ?)', 
                         (persona_id, filepath, features.tobytes()))
            conn.commit()
            conn.close()
            
    return redirect(url_for('profiles'))

app.config['VIDEO_UPLOAD_FOLDER'] = 'static/uploads'
app.config['DETECTIONS_FOLDER'] = 'static/detections_data'

def identify_face(face_features, conn):
    perfiles = conn.execute('SELECT persona_id, caracteristicas_faciales FROM ImagenesPerfil').fetchall()
    mejor_similitud = 0.0
    persona_identificada = None
    umbral = 0.8  # Umbral de similitud

    for perfil in perfiles:
        similitud = face_utils.compare_features(face_features, perfil['caracteristicas_faciales'])
        if similitud > mejor_similitud and similitud > umbral:
            mejor_similitud = similitud
            persona_identificada = perfil['persona_id']
            
    return persona_identificada, mejor_similitud

@app.route('/upload', methods=['GET'])
def upload():
    return render_template('upload.html')

@app.route('/analyze_video', methods=['POST'])
def analyze_video():
    if 'video' not in request.files:
        return redirect(url_for('upload'))
    file = request.files['video']
    if file.filename == '':
        return redirect(url_for('upload'))
        
    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['VIDEO_UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Procesar el video
        cap = cv2.VideoCapture(filepath)
        conn = database.get_conn()
        frame_count = 0
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            # Procesar 1 de cada 10 frames para no sobrecargar
            if frame_count % 10 == 0:
                rects = face_utils.detect_faces(frame)
                for (x, y, w, h) in rects:
                    face_image = frame[y:y+h, x:x+w]
                    features = face_utils.extract_features(face_image)
                    persona_id, sim = identify_face(features, conn)
                    
                    from datetime import datetime
                    det_filename = f"det_{datetime.now().strftime('%Y%m%d%H%M%S%f')}.jpg"
                    det_filepath = os.path.join(app.config['DETECTIONS_FOLDER'], det_filename)
                    cv2.imwrite(det_filepath, face_image)
                    
                    conn.execute('INSERT INTO Detecciones (persona_id, ruta_imagen_captura, fecha_hora) VALUES (?, ?, ?)',
                                 (persona_id, det_filepath, datetime.now()))
                    conn.commit()
            frame_count += 1
            
        cap.release()
        conn.close()
        return "Video procesado correctamente."

def gen_frames():
    cap = cv2.VideoCapture(0)
    conn = database.get_conn()
    
    while True:
        success, frame = cap.read()
        if not success:
            break
        else:
            rects = face_utils.detect_faces(frame)
            for (x, y, w, h) in rects:
                face_image = frame[y:y+h, x:x+w]
                features = face_utils.extract_features(face_image)
                persona_id, sim = identify_face(features, conn)
                
                nombre = "Desconocido"
                if persona_id:
                    p = conn.execute('SELECT nombre FROM Personas WHERE id=?', (persona_id,)).fetchone()
                    if p: nombre = p['nombre']
                
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                cv2.putText(frame, f"{nombre} ({sim:.2f})", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0,255,0), 2)
                
            ret, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
    cap.release()
    conn.close()

@app.route('/video_feed')
def video_feed():
    from flask import Response
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    database.init_db()
    for folder in [app.config['UPLOAD_FOLDER'], app.config['VIDEO_UPLOAD_FOLDER'], app.config['DETECTIONS_FOLDER']]:
        if not os.path.exists(folder):
            os.makedirs(folder)
    app.run(debug=True)

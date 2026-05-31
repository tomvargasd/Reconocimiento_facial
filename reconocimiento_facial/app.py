import os
from datetime import datetime
# pyrefly: ignore [missing-import]
from flask import Flask, render_template, request, redirect, url_for, flash, Response
import database
import face_utils
import cv2
import numpy as np
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'faceid_secret_key_2026'
app.config['UPLOAD_FOLDER'] = 'static/profiles_data'
app.config['VIDEO_UPLOAD_FOLDER'] = 'static/uploads'
app.config['DETECTIONS_FOLDER'] = 'static/detections_data'


@app.route('/')
def index():
    conn = database.get_conn()
    num_personas = conn.execute('SELECT COUNT(*) as c FROM Personas').fetchone()['c']
    num_detecciones = conn.execute('SELECT COUNT(*) as c FROM Detecciones').fetchone()['c']
    conn.close()
    return render_template('index.html', num_personas=num_personas, num_detecciones=num_detecciones)


@app.route('/profiles', methods=['GET', 'POST'])
def profiles():
    conn = database.get_conn()
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        if nombre:
            conn.execute('INSERT INTO Personas (nombre) VALUES (?)', (nombre,))
            conn.commit()
            flash('Persona registrada correctamente.', 'success')
            conn.close()
            return redirect(url_for('profiles'))

    # Get personas with image count
    personas_raw = conn.execute('SELECT * FROM Personas').fetchall()
    personas = []
    for p in personas_raw:
        num_imagenes = conn.execute(
            'SELECT COUNT(*) as c FROM ImagenesPerfil WHERE persona_id = ?', (p['id'],)
        ).fetchone()['c']
        personas.append({
            'id': p['id'],
            'nombre': p['nombre'],
            'num_imagenes': num_imagenes
        })
    conn.close()
    return render_template('profiles.html', personas=personas)


@app.route('/upload_profile_image/<int:persona_id>', methods=['POST'])
def upload_profile_image(persona_id):
    if 'image' not in request.files:
        flash('No se seleccionó ninguna imagen.', 'error')
        return redirect(url_for('profiles'))
    file = request.files['image']
    if file.filename == '':
        flash('No se seleccionó ninguna imagen.', 'error')
        return redirect(url_for('profiles'))

    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{persona_id}_{filename}")
        file.save(filepath)

        # Procesar la imagen
        image = cv2.imread(filepath)
        rects = face_utils.detect_faces(image)
        if len(rects) > 0:
            x, y, w, h = rects[0]  # Tomar el primer rostro
            face_image = image[y:y+h, x:x+w]
            features = face_utils.extract_features(face_image)

            conn = database.get_conn()
            conn.execute(
                'INSERT INTO ImagenesPerfil (persona_id, ruta_imagen, caracteristicas_faciales) VALUES (?, ?, ?)',
                (persona_id, filepath, features.tobytes())
            )
            conn.commit()
            conn.close()
            flash('Imagen procesada y rostro registrado exitosamente.', 'success')
        else:
            flash('No se detectó ningún rostro en la imagen. Intenta con otra foto.', 'error')

    return redirect(url_for('profiles'))


@app.route('/delete_persona/<int:persona_id>', methods=['POST'])
def delete_persona(persona_id):
    conn = database.get_conn()
    # Delete profile images from filesystem
    imagenes = conn.execute(
        'SELECT ruta_imagen FROM ImagenesPerfil WHERE persona_id = ?', (persona_id,)
    ).fetchall()
    for img in imagenes:
        if os.path.exists(img['ruta_imagen']):
            os.remove(img['ruta_imagen'])

    # Delete from database
    conn.execute('DELETE FROM ImagenesPerfil WHERE persona_id = ?', (persona_id,))
    conn.execute('DELETE FROM Personas WHERE id = ?', (persona_id,))
    conn.commit()
    conn.close()
    flash('Persona y sus datos eliminados correctamente.', 'success')
    return redirect(url_for('profiles'))


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
        flash('No se seleccionó ningún video.', 'error')
        return redirect(url_for('upload'))
    file = request.files['video']
    if file.filename == '':
        flash('No se seleccionó ningún video.', 'error')
        return redirect(url_for('upload'))

    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['VIDEO_UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Procesar el video
        cap = cv2.VideoCapture(filepath)
        conn = database.get_conn()
        frame_count = 0
        analysis_detection_ids = []

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

                    det_filename = f"det_{datetime.now().strftime('%Y%m%d%H%M%S%f')}.jpg"
                    det_filepath = os.path.join(app.config['DETECTIONS_FOLDER'], det_filename)
                    cv2.imwrite(det_filepath, face_image)

                    cursor = conn.execute(
                        'INSERT INTO Detecciones (persona_id, ruta_imagen_captura, fecha_hora) VALUES (?, ?, ?)',
                        (persona_id, det_filepath, datetime.now())
                    )
                    conn.commit()
                    analysis_detection_ids.append(cursor.lastrowid)
            frame_count += 1

        cap.release()

        # Fetch results for this analysis
        detections = []
        total = len(analysis_detection_ids)
        identified_count = 0

        for det_id in analysis_detection_ids:
            det = conn.execute(
                '''SELECT d.*, p.nombre FROM Detecciones d
                   LEFT JOIN Personas p ON d.persona_id = p.id
                   WHERE d.id = ?''', (det_id,)
            ).fetchone()
            if det:
                det_dict = dict(det)
                detections.append(det_dict)
                if det_dict.get('nombre'):
                    identified_count += 1

        conn.close()

        return render_template('results.html',
                               detections=detections,
                               total_detections=total,
                               identified=identified_count,
                               unknown=total - identified_count)

    return redirect(url_for('upload'))


@app.route('/detections')
def detections():
    conn = database.get_conn()
    filter_persona = request.args.get('persona_id', '')

    if filter_persona == 'unknown':
        detections_data = conn.execute(
            '''SELECT d.*, p.nombre FROM Detecciones d
               LEFT JOIN Personas p ON d.persona_id = p.id
               WHERE d.persona_id IS NULL
               ORDER BY d.fecha_hora DESC'''
        ).fetchall()
    elif filter_persona:
        detections_data = conn.execute(
            '''SELECT d.*, p.nombre FROM Detecciones d
               LEFT JOIN Personas p ON d.persona_id = p.id
               WHERE d.persona_id = ?
               ORDER BY d.fecha_hora DESC''', (filter_persona,)
        ).fetchall()
    else:
        detections_data = conn.execute(
            '''SELECT d.*, p.nombre FROM Detecciones d
               LEFT JOIN Personas p ON d.persona_id = p.id
               ORDER BY d.fecha_hora DESC'''
        ).fetchall()

    personas = conn.execute('SELECT * FROM Personas').fetchall()
    conn.close()

    return render_template('detections.html',
                           detections=detections_data,
                           personas=personas,
                           filter_persona=filter_persona)


def gen_frames():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        # Return a single frame with error message if webcam not available
        error_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(error_frame, "Camara no disponible", (120, 240),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 2)
        ret, buffer = cv2.imencode('.jpg', error_frame)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        return

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
                    if p:
                        nombre = p['nombre']

                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                cv2.putText(frame, f"{nombre} ({sim:.2f})", (x, y-10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

            ret, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

    cap.release()
    conn.close()


@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == '__main__':
    database.init_db()
    for folder in [app.config['UPLOAD_FOLDER'], app.config['VIDEO_UPLOAD_FOLDER'], app.config['DETECTIONS_FOLDER']]:
        if not os.path.exists(folder):
            os.makedirs(folder)
    app.run(debug=True)

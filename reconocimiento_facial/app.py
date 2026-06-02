import os
import uuid
import threading
import time
import json
from datetime import datetime
# pyrefly: ignore [missing-import]
from flask import Flask, render_template, request, redirect, url_for, flash, Response, jsonify
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

# Diccionario en memoria para rastrear tareas en segundo plano
job_store = {}


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
        if nombre and nombre.strip():
            conn.execute('INSERT INTO Personas (nombre) VALUES (?)', (nombre,))
            conn.commit()
            flash('Persona registrada correctamente.', 'success')
            conn.close()
            return redirect(url_for('profiles'))
        else:
            flash('El nombre no puede estar vacío.', 'error')
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
    files = request.files.getlist('image')
    if not files or all(f.filename == '' for f in files):
        flash('No se seleccionó ninguna imagen.', 'error')
        return redirect(url_for('profiles'))

    conn = database.get_conn()
    # Obtenemos los perfiles existentes para validación
    perfiles_existentes_rows = conn.execute(
        'SELECT caracteristicas_faciales, file_hash FROM ImagenesPerfil WHERE persona_id = ?', 
        (persona_id,)
    ).fetchall()
    
    perfiles_existentes = [{'file_hash': p['file_hash'], 'caracteristicas_faciales': p['caracteristicas_faciales']} for p in perfiles_existentes_rows]

    procesadas = 0
    duplicados = 0
    errores = 0

    for file in files:
        if file.filename == '':
            continue
            
        filename = secure_filename(file.filename)
        # Usar uuid para evitar sobreescribir archivos con el mismo nombre pero diferente contenido
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{persona_id}_{uuid.uuid4().hex[:8]}_{filename}")
        file.save(filepath)

        # 1. Validación de duplicado exacto (hash de archivo)
        f_hash = face_utils.file_hash(filepath)
        is_duplicate = False
        for p in perfiles_existentes:
            if p['file_hash'] and p['file_hash'] == f_hash:
                is_duplicate = True
                break
        
        if is_duplicate:
            os.remove(filepath)
            duplicados += 1
            continue

        # Procesar la imagen
        image = cv2.imread(filepath)
        if image is None:
            os.remove(filepath)
            errores += 1
            continue

        rects = face_utils.detect_faces(image)
        if len(rects) > 0:
            x, y, w, h = rects[0]  # Tomar el primer rostro detectado
            face_image = image[y:y+h, x:x+w]
            features = face_utils.extract_features(face_image)

            # 2. Validación de duplicado facial (similitud muy alta > 0.97)
            is_face_dup = False
            for p in perfiles_existentes:
                sim = face_utils.compare_features(features, p['caracteristicas_faciales'])
                if sim > 0.97:
                    is_face_dup = True
                    break
            
            if is_face_dup:
                os.remove(filepath)
                duplicados += 1
                continue

            conn.execute(
                'INSERT INTO ImagenesPerfil (persona_id, ruta_imagen, caracteristicas_faciales, file_hash) VALUES (?, ?, ?, ?)',
                (persona_id, filepath, features.tobytes(), f_hash)
            )
            # Agregamos a la lista en memoria para evitar duplicados en el mismo batch de carga
            perfiles_existentes.append({'file_hash': f_hash, 'caracteristicas_faciales': features.tobytes()})
            procesadas += 1
        else:
            os.remove(filepath)
            errores += 1

    conn.commit()
    conn.close()

    msg = f"{procesadas} imagen(es) procesada(s) correctamente."
    if duplicados > 0:
        msg += f" {duplicados} omitida(s) por ser duplicada(s)."
    if errores > 0:
        msg += f" {errores} omitida(s) (no se detectó rostro o error de archivo)."
        
    if procesadas > 0:
        flash(msg, 'success')
    elif duplicados > 0:
        flash(msg, 'info')
    else:
        flash(msg, 'error')

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
    conn.execute('UPDATE Detecciones SET persona_id = NULL WHERE persona_id = ?', (persona_id,))
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


@app.route('/start_video_analysis', methods=['POST'])
def start_video_analysis():
    if 'video' not in request.files:
        return jsonify({"error": "No se seleccionó ningún video"}), 400
    file = request.files['video']
    if file.filename == '':
        return jsonify({"error": "No se seleccionó ningún video"}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['VIDEO_UPLOAD_FOLDER'], f"{uuid.uuid4().hex[:8]}_{filename}")
    file.save(filepath)

    job_id = str(uuid.uuid4())
    job_store[job_id] = {
        "status": "processing",
        "progress": 0,
        "results": None
    }

    thread = threading.Thread(target=process_video_async, args=(filepath, job_id))
    thread.daemon = True
    thread.start()

    return jsonify({"job_id": job_id})


def process_video_async(filepath, job_id):
    try:
        cap = cv2.VideoCapture(filepath)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0:
            total_frames = 100 # Fallback safety
            
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
            # Update progress
            progress = min(99, int((frame_count / total_frames) * 100))
            job_store[job_id]["progress"] = progress

        cap.release()

        # Generar resultados
        detections = []
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

        job_store[job_id]["results"] = {
            "detections": detections,
            "total_detections": len(analysis_detection_ids),
            "identified": identified_count,
            "unknown": len(analysis_detection_ids) - identified_count
        }
        job_store[job_id]["progress"] = 100
        job_store[job_id]["status"] = "done"

    except Exception as e:
        job_store[job_id]["status"] = "error"
        job_store[job_id]["error_msg"] = str(e)


@app.route('/video_progress/<job_id>')
def video_progress(job_id):
    def generate():
        while True:
            if job_id not in job_store:
                yield f"data: {json.dumps({'status': 'error', 'error_msg': 'Job no encontrado'})}\n\n"
                break
            job = job_store[job_id]
            yield f"data: {json.dumps({'status': job['status'], 'progress': job['progress']})}\n\n"
            if job['status'] in ['done', 'error']:
                break
            time.sleep(0.5)
    return Response(generate(), mimetype='text/event-stream')


@app.route('/results/<job_id>')
def results(job_id):
    if job_id not in job_store or job_store[job_id]["status"] != "done":
        flash("Resultados no encontrados o análisis no completado.", "error")
        return redirect(url_for('upload'))
    
    res = job_store[job_id]["results"]
    
    conn = database.get_conn()
    personas = conn.execute('SELECT * FROM Personas ORDER BY nombre ASC').fetchall()
    conn.close()
    
    return render_template('results.html',
                           detections=res["detections"],
                           total_detections=res["total_detections"],
                           identified=res["identified"],
                           unknown=res["unknown"],
                           personas=personas)


@app.route('/assign_detection/<int:det_id>', methods=['POST'])
def assign_detection(det_id):
    data = request.get_json()
    persona_id = data.get('persona_id')
    if not persona_id:
        return jsonify({"ok": False, "error": "Falta persona_id"}), 400
        
    conn = database.get_conn()
    conn.execute('UPDATE Detecciones SET persona_id = ? WHERE id = ?', (persona_id, det_id))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.route('/unlink_detection/<int:det_id>', methods=['POST'])
def unlink_detection(det_id):
    conn = database.get_conn()
    conn.execute('UPDATE Detecciones SET persona_id = NULL WHERE id = ?', (det_id,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


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

    personas = conn.execute('SELECT * FROM Personas ORDER BY nombre ASC').fetchall()
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

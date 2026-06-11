import os
import sys
import uuid
import threading
import time
import json
import base64
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from flask import Flask, render_template, request, redirect, url_for, flash, Response, jsonify
import database as db
import vehicle_counter as vc
import cv2
import numpy as np
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'vehicle_count_secret_key_2026'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['VIDEO_UPLOAD_FOLDER'] = 'uploaded_videos'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024

job_store = {}
video_previews = {}

ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'wmv'}

VEHICLE_ICONS = {
    'car': '🚗', 'motorcycle': '🏍️', 'bus': '🚌',
    'truck': '🚚', 'bicycle': '🚲',
}
VEHICLE_LABELS = {
    'car': 'Autos', 'motorcycle': 'Motos', 'bus': 'Buses',
    'truck': 'Camiones', 'bicycle': 'Bicicletas',
}
VEHICLE_ORDER = ['car', 'motorcycle', 'bus', 'truck', 'bicycle']


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    conn = db.get_conn()
    videos = conn.execute(
        'SELECT id, original_filename, status, total_vehicles, total_entry, total_exit, processed_at FROM Videos ORDER BY processed_at DESC LIMIT 10'
    ).fetchall()
    total_videos = conn.execute('SELECT COUNT(*) as c FROM Videos').fetchone()['c']
    total_vehicles_all = conn.execute('SELECT COALESCE(SUM(total_vehicles), 0) as s FROM Videos').fetchone()['s']
    conn.close()
    return render_template('index.html',
                           videos=[dict(v) for v in videos],
                           total_videos=total_videos,
                           total_vehicles_all=total_vehicles_all)


@app.route('/processing', methods=['GET', 'POST'])
def processing():
    if request.method == 'POST':
        if 'video' not in request.files:
            flash('No se seleccionó ningún video.', 'error')
            return redirect(url_for('processing'))

        file = request.files['video']
        if file.filename == '':
            flash('No se seleccionó ningún video.', 'error')
            return redirect(url_for('processing'))

        if not allowed_file(file.filename):
            flash('Formato no soportado. Usa: mp4, avi, mov, mkv, wmv', 'error')
            return redirect(url_for('processing'))

        filename = secure_filename(file.filename)
        unique_name = f"{uuid.uuid4().hex[:8]}_{filename}"
        filepath = os.path.join(app.config['VIDEO_UPLOAD_FOLDER'], unique_name)
        os.makedirs(app.config['VIDEO_UPLOAD_FOLDER'], exist_ok=True)
        file.save(filepath)

        orientation = request.form.get('orientation', 'horizontal')
        position = float(request.form.get('position', 0.5))
        conf_threshold = float(request.form.get('conf_threshold', 0.35))

        db.init_db()
        video_id = db.insert_video(
            filename=unique_name,
            original_filename=filename,
            orientation=orientation,
            position=position,
            conf_threshold=conf_threshold,
        )
        db.update_video_status(video_id, 'processing')

        job_id = str(uuid.uuid4())
        job_store[job_id] = {
            "status": "processing",
            "progress": 0,
            "video_id": video_id,
            "results": None,
        }

        thread = threading.Thread(
            target=process_video_async,
            args=(filepath, job_id, orientation, position, conf_threshold, video_id),
            daemon=True,
        )
        thread.start()

        return redirect(url_for('processing_status', job_id=job_id))

    return render_template('processing.html',
                           VEHICLE_ICONS=VEHICLE_ICONS,
                           VEHICLE_LABELS=VEHICLE_LABELS)


@app.route('/processing_status/<job_id>')
def processing_status(job_id):
    if job_id not in job_store:
        flash('Trabajo no encontrado.', 'error')
        return redirect(url_for('processing'))

    job = job_store[job_id]
    return render_template('processing_status.html',
                           job_id=job_id,
                           job=job)


@app.route('/job_progress/<job_id>')
def job_progress(job_id):
    def generate():
        while True:
            if job_id not in job_store:
                yield f"data: {json.dumps({'status': 'error', 'error_msg': 'Job no encontrado'})}\n\n"
                break
            job = job_store[job_id]
            data = {'status': job['status'], 'progress': job['progress']}
            if job.get('counts'):
                data['counts'] = job['counts']
            yield f"data: {json.dumps(data)}\n\n"
            if job['status'] in ['done', 'error']:
                if job['status'] == 'done' and job.get('results'):
                    yield f"data: {json.dumps({'status': 'results', 'results': job['results']})}\n\n"
                break
            time.sleep(0.5)

    return Response(generate(), mimetype='text/event-stream')


@app.route('/results/<int:video_id>')
def results(video_id):
    video = db.get_video_detail(video_id)
    if not video:
        flash('Video no encontrado.', 'error')
        return redirect(url_for('index'))

    return render_template('results.html',
                           video=video,
                           VEHICLE_ICONS=VEHICLE_ICONS,
                           VEHICLE_LABELS=VEHICLE_LABELS,
                           VEHICLE_ORDER=VEHICLE_ORDER)


@app.route('/dashboard')
def dashboard():
    videos = db.get_all_videos()
    return render_template('dashboard.html',
                           videos=videos,
                           VEHICLE_ICONS=VEHICLE_ICONS,
                           VEHICLE_LABELS=VEHICLE_LABELS,
                           VEHICLE_ORDER=VEHICLE_ORDER)


@app.route('/delete_video/<int:video_id>', methods=['POST'])
def delete_video(video_id):
    video = db.get_video_detail(video_id)
    if not video:
        flash('Video no encontrado.', 'error')
        return redirect(url_for('dashboard'))

    filepath = os.path.join(app.config['VIDEO_UPLOAD_FOLDER'], video['filename'])
    if os.path.exists(filepath):
        os.remove(filepath)

    db.delete_video(video_id)
    flash('Video eliminado correctamente.', 'success')
    return redirect(url_for('dashboard'))


@app.route('/api/preview_frame', methods=['POST'])
def preview_frame():
    data = request.get_json()
    session_id = data.get('video_path', '')
    position = float(data.get('position', 0.5))
    orientation = data.get('orientation', 'horizontal')

    filepath = video_previews.get(session_id, '')
    if not filepath or not os.path.exists(filepath):
        return jsonify({"error": "Video no encontrado"}), 404

    cap = cv2.VideoCapture(filepath)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        return jsonify({"error": "No se pudo leer el video"}), 400

    h, w = frame.shape[:2]
    if orientation == 'horizontal':
        y = int(h * position)
        cv2.line(frame, (0, y), (w, y), (0, 255, 0), 3)
        cv2.putText(frame, f'LINEA ({int(position*100)}%)', (10, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    else:
        x = int(w * position)
        cv2.line(frame, (x, 0), (x, h), (0, 255, 0), 3)
        cv2.putText(frame, f'LINEA ({int(position*100)}%)', (x + 10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

    ret, buffer = cv2.imencode('.jpg', frame)
    return jsonify({"frame": base64.b64encode(buffer).decode('utf-8')})


@app.route('/api/session_video', methods=['POST'])
def session_video():
    if 'video' not in request.files:
        return jsonify({"error": "No file"}), 400
    file = request.files['video']
    if file.filename == '':
        return jsonify({"error": "No file"}), 400

    filename = secure_filename(file.filename)
    unique_name = f"preview_{uuid.uuid4().hex[:8]}_{filename}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    file.save(filepath)

    session_id = str(uuid.uuid4())
    video_previews[session_id] = filepath

    cap = cv2.VideoCapture(filepath)
    ret, frame = cap.read()
    cap.release()

    info = {"session_id": session_id, "filename": filename, "has_preview": ret}
    if ret:
        h, w = frame.shape[:2]
        info['width'] = w
        info['height'] = h

    return jsonify(info)


def process_video_async(filepath, job_id, orientation, position, conf_threshold, video_id):
    try:
        counts, duration, entry_counts, exit_counts = vc.process_video(
            video_path=filepath,
            orientation=orientation,
            position=position,
            progress_callback=lambda p: job_store_update(job_id, 'progress', p),
            counts_callback=lambda c: job_store_update(job_id, 'counts', c),
            video_id=video_id,
            conf_threshold=conf_threshold,
        )

        video = db.get_video_detail(video_id)
        job_store[job_id]["results"] = video
        job_store[job_id]["progress"] = 100
        job_store[job_id]["status"] = "done"

    except Exception as e:
        job_store[job_id]["status"] = "error"
        job_store[job_id]["error_msg"] = str(e)
        if video_id:
            db.update_video_status(video_id, 'error')


def job_store_update(job_id, key, value):
    if job_id in job_store:
        job_store[job_id][key] = value


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Servicio de Conteo de Vehículos")
    parser.add_argument('--port', type=int, default=5001, help="Puerto para ejecutar el servidor Flask")
    args = parser.parse_args()

    db.init_db()
    for folder in [app.config['UPLOAD_FOLDER'], app.config['VIDEO_UPLOAD_FOLDER']]:
        if not os.path.exists(folder):
            os.makedirs(folder)

    debug_mode = args.port == 5001
    app.run(host='127.0.0.1', port=args.port, debug=debug_mode, use_reloader=debug_mode)

import os
import sys
import uuid
import cv2
from pathlib import Path
from ultralytics import solutions

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Modulos.conteo_vehiculos import database as db

COCO_VEHICLE_IDS = [1, 2, 3, 5, 7]

# inicializo el modelo directo en una carptema models
MODEL_PATH = "../../models/yolo11s.pt"

def build_region_points(width, height, orientation, position):
    if orientation == 'horizontal':
        y_center = int(height * position)
        return [(0, y_center), (width, y_center)]
    else:
        x_center = int(width * position)
        return [(x_center, 0), (x_center, height)]


def process_video(
    video_path,
    orientation,
    position,
    progress_callback=None,
    frame_callback=None,
    counts_callback=None,
    cancel_event=None,
    video_id=None,
    conf_threshold=0.35,
):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise IOError(f"No se pudo abrir el video: {video_path}")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    if total_frames <= 0:
        total_frames = 100

    region_points = build_region_points(width, height, orientation, position)

    counter = solutions.ObjectCounter(
        show=False,
        region=region_points,
        model=MODEL_PATH,
        classes=COCO_VEHICLE_IDS,
        line_width=2,
        conf=conf_threshold,
    )

    frame_count = 0
    skip_factor = max(1, int(fps / 20))

    while cap.isOpened():
        if frame_count % skip_factor != 0:
            cap.grab()
            frame_count += 1
            continue

        if cancel_event and cancel_event.is_set():
            break

        ret, frame = cap.read()
        if not ret:
            break

        results = counter.process(frame)
        frame_annotated = results.plot_im

        if frame_callback:
            frame_callback(frame_annotated)

        if counts_callback:
            named_counts = {}
            for cls_name, dir_counts in results.classwise_count.items():
                in_val = dir_counts.get('IN', 0)
                out_val = dir_counts.get('OUT', 0)
                named_counts[cls_name] = in_val + out_val
                named_counts[f'{cls_name}_entry'] = in_val
                named_counts[f'{cls_name}_exit'] = out_val
            total = sum(named_counts.get(t, 0) for t in ['car','motorcycle','bus','truck','bicycle'])
            total_entry = sum(named_counts.get(f'{t}_entry', 0) for t in ['car','motorcycle','bus','truck','bicycle'])
            total_exit = sum(named_counts.get(f'{t}_exit', 0) for t in ['car','motorcycle','bus','truck','bicycle'])
            named_counts['total'] = total
            named_counts['total_entry'] = total_entry
            named_counts['total_exit'] = total_exit
            counts_callback(named_counts)

        frame_count += 1
        progress = int((frame_count / total_frames) * 100)
        if progress > 99 and frame_count < total_frames - 1:
            progress = 99
        if progress_callback:
            progress_callback(min(progress, 100))

    cap.release()

    duration = total_frames / fps if fps > 0 else 0

    final_counts = {}
    final_entry = {}
    final_exit = {}
    for cls_name, dir_counts in counter.classwise_count.items():
        in_val = dir_counts.get('IN', 0)
        out_val = dir_counts.get('OUT', 0)
        final_counts[cls_name] = in_val + out_val
        final_entry[cls_name] = in_val
        final_exit[cls_name] = out_val

    if video_id is not None:
        total_vehicles = sum(final_counts.values())
        total_entry_all = sum(final_entry.values())
        total_exit_all = sum(final_exit.values())
        db.update_video_status(
            video_id,
            'done' if not (cancel_event and cancel_event.is_set()) else 'cancelled',
            total_vehicles=total_vehicles,
            duration_seconds=duration,
            total_entry=total_entry_all,
            total_exit=total_exit_all,
        )
        for vtype, vcount in final_counts.items():
            db.upsert_vehicle_count(video_id, vtype, vcount,
                                    entry_count=final_entry.get(vtype, 0),
                                    exit_count=final_exit.get(vtype, 0))

    return final_counts, duration, final_entry, final_exit


def process_video_standalone(
    video_path,
    orientation='horizontal',
    position=0.5,
    conf_threshold=0.35,
):
    db.init_db()

    original_name = Path(video_path).name
    filename = f"{uuid.uuid4().hex[:8]}_{original_name}"

    video_id = db.insert_video(
        filename=filename,
        original_filename=original_name,
        orientation=orientation,
        position=position,
        conf_threshold=conf_threshold,
    )

    db.update_video_status(video_id, 'processing')

    try:
        counts, duration, entry_counts, exit_counts = process_video(
            video_path=video_path,
            orientation=orientation,
            position=position,
            video_id=video_id,
            conf_threshold=conf_threshold,
        )
        print(f"Procesamiento completado: {counts}")
        return video_id, counts
    except Exception as e:
        db.update_video_status(video_id, 'error')
        raise e


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Procesar video para conteo de vehículos")
    parser.add_argument('video_path', help="Ruta al archivo de video")
    parser.add_argument('--orientation', choices=['horizontal', 'vertical'], default='horizontal')
    parser.add_argument('--position', type=float, default=0.5)
    parser.add_argument('--conf', type=float, default=0.35)
    args = parser.parse_args()

    db.init_db()
    process_video_standalone(
        args.video_path,
        args.orientation,
        args.position,
        conf_threshold=args.conf,
    )

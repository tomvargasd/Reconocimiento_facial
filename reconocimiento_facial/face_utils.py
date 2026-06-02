import cv2
import numpy as np
import hashlib
from ultralytics import YOLO

# Cargamos el modelo YOLO (usaremos yolov8n.pt por defecto, idealmente yolov8n-face.pt)
try:
    model = YOLO('models/yolov8n-face.pt')
except Exception:
    model = YOLO('yolov8n.pt')

def detect_faces(image):
    results = model(image)
    rects = []
    for r in results:
        boxes = r.boxes
        for box in boxes:
            x1, y1, x2, y2 = box.xyxy[0]
            x, y, w, h = int(x1), int(y1), int(x2 - x1), int(y2 - y1)
            rects.append((x, y, w, h))
    return rects

def extract_features(face_image):
    # Placeholder simple para las características. 
    # En un sistema real se usaría un modelo como FaceNet para el embedding.
    resized = cv2.resize(face_image, (128, 128))
    return resized.flatten().astype(np.float32)

def compare_features(feat1, feat2):
    # Calcular similitud del coseno
    feat1 = np.frombuffer(feat1, dtype=np.float32) if isinstance(feat1, bytes) else feat1
    feat2 = np.frombuffer(feat2, dtype=np.float32) if isinstance(feat2, bytes) else feat2
    dot_product = np.dot(feat1, feat2)
    norm1 = np.linalg.norm(feat1)
    norm2 = np.linalg.norm(feat2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot_product / (norm1 * norm2)

def file_hash(filepath):
    """Calcula el hash MD5 de un archivo para detectar duplicados exactos."""
    h = hashlib.md5()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


import cv2
import numpy as np

def detect_faces(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    rects = face_cascade.detectMultiScale(gray, 1.1, 4)
    return rects

def extract_features(face_image):
    return np.mean(face_image, axis=(0,1)).astype(np.float32)

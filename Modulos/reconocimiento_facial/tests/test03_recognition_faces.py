"""
test03_recognition_faces.py — Prueba los algoritmos de extracción y comparación de características faciales.
"""
import unittest
import sys
import numpy as np
from pathlib import Path

# Agregar la ruta del módulo
module_dir = Path(__file__).parent.parent.resolve()
sys.path.append(str(module_dir))

import database
import face_utils
from app import identify_face


class TestFaceRecognition(unittest.TestCase):

    def setUp(self):
        self.original_db_path = database.DB_PATH
        database.DB_PATH = module_dir / 'test_database.db'
        database.init_db()

    def tearDown(self):
        database.DB_PATH = self.original_db_path
        test_db = module_dir / 'test_database.db'
        if test_db.exists():
            try:
                test_db.unlink()
            except OSError:
                pass

    def test_compare_features_identical(self):
        """Verifica que comparar vectores idénticos retorne una similitud de 1.0."""
        vec = np.array([1.0, 0.0, 0.0, 2.0], dtype=np.float32)
        sim = face_utils.compare_features(vec, vec)
        self.assertAlmostEqual(sim, 1.0, places=5)

    def test_compare_features_orthogonal(self):
        """Verifica que comparar vectores ortogonales retorne una similitud de 0.0."""
        vec1 = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
        vec2 = np.array([0.0, 1.0, 0.0, 0.0], dtype=np.float32)
        sim = face_utils.compare_features(vec1, vec2)
        self.assertAlmostEqual(sim, 0.0, places=5)

    def test_identify_face(self):
        """Verifica la lógica de identificación de rostros contra perfiles guardados."""
        # Insertar un perfil de prueba
        conn = database.get_conn()
        conn.execute("INSERT INTO Personas (id, nombre) VALUES (?, ?)", (10, "Target Person"))
        
        # Guardar un embedding de prueba
        features = np.array([1.0, 0.5, -0.2, 0.1], dtype=np.float32)
        conn.execute(
            "INSERT INTO ImagenesPerfil (persona_id, ruta_imagen, caracteristicas_faciales, file_hash) VALUES (?, ?, ?, ?)",
            (10, "dummy.jpg", features.tobytes(), "dummyhash")
        )
        conn.commit()

        # Caso 1: Rostro idéntico (similitud = 1.0 > umbral 0.8)
        persona_id, sim = identify_face(features, conn)
        self.assertEqual(persona_id, 10)
        self.assertAlmostEqual(sim, 1.0, places=5)

        # Caso 2: Rostro diferente (similitud ortogonal = 0.0 < umbral 0.8)
        different_features = np.array([-0.5, 1.0, 0.0, 0.0], dtype=np.float32)
        persona_id_diff, sim_diff = identify_face(different_features, conn)
        self.assertIsNone(persona_id_diff)

        conn.close()


if __name__ == '__main__':
    unittest.main()

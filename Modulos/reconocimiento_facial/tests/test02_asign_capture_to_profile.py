"""
test02_asign_capture_to_profile.py — Prueba la asignación de una detección (captura) a un perfil de usuario.
"""
import unittest
import sys
import json
from pathlib import Path

# Agregar la ruta del módulo
module_dir = Path(__file__).parent.parent.resolve()
sys.path.append(str(module_dir))

import database
from app import app


class TestAssignCapture(unittest.TestCase):

    def setUp(self):
        self.app_client = app.test_client()
        app.config['TESTING'] = True
        
        self.original_db_path = database.DB_PATH
        database.DB_PATH = module_dir / 'test_database.db'
        database.init_db()

        # Insertar datos de prueba
        conn = database.get_conn()
        conn.execute("INSERT INTO Personas (id, nombre) VALUES (?, ?)", (1, "Juan Perez"))
        conn.execute(
            "INSERT INTO Detecciones (id, persona_id, ruta_imagen_captura, fecha_hora) VALUES (?, ?, ?, ?)",
            (100, None, "static/detections_data/test_det.jpg", "2026-06-05 21:00:00")
        )
        conn.commit()
        conn.close()

    def tearDown(self):
        database.DB_PATH = self.original_db_path
        test_db = module_dir / 'test_database.db'
        if test_db.exists():
            try:
                test_db.unlink()
            except OSError:
                pass

    def test_assign_detection_route(self):
        """Verifica la asignación de una detección a una persona a través de la ruta HTTP POST."""
        payload = {"persona_id": 1}
        response = self.app_client.post(
            '/assign_detection/100',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data.decode('utf-8'))
        self.assertTrue(data["ok"])

        # Verificar en base de datos
        conn = database.get_conn()
        row = conn.execute("SELECT persona_id FROM Detecciones WHERE id = 100").fetchone()
        conn.close()

        self.assertEqual(row['persona_id'], 1)

    def test_unlink_detection_route(self):
        """Verifica la desvinculación de una detección."""
        # Primero asociamos
        conn = database.get_conn()
        conn.execute("UPDATE Detecciones SET persona_id = 1 WHERE id = 100")
        conn.commit()
        conn.close()

        # Desvincular
        response = self.app_client.post('/unlink_detection/100')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data.decode('utf-8'))
        self.assertTrue(data["ok"])

        # Verificar en base de datos
        conn = database.get_conn()
        row = conn.execute("SELECT persona_id FROM Detecciones WHERE id = 100").fetchone()
        conn.close()

        self.assertIsNone(row['persona_id'])


if __name__ == '__main__':
    unittest.main()

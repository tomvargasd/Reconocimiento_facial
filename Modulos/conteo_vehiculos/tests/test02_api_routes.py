"""
test02_api_routes.py — Prueba las rutas HTTP de la aplicación Flask del módulo de conteo de vehículos.
"""
import unittest
import sys
import json
from pathlib import Path

module_dir = Path(__file__).parent.parent.resolve()
sys.path.append(str(module_dir))

import database as db
from app import app


class TestApiRoutes(unittest.TestCase):

    def setUp(self):
        self.app_client = app.test_client()
        app.config['TESTING'] = True

        self.original_db_path = db.DB_PATH
        db.DB_PATH = module_dir / 'tests' / 'test_database.db'
        db.init_db()

    def tearDown(self):
        db.DB_PATH = self.original_db_path
        test_db = module_dir / 'tests' / 'test_database.db'
        if test_db.exists():
            try:
                test_db.unlink()
            except OSError:
                pass

    def test_index_route(self):
        """Verifica que la ruta principal GET / devuelve 200."""
        response = self.app_client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_dashboard_route(self):
        """Verifica que la ruta GET /dashboard devuelve 200."""
        response = self.app_client.get('/dashboard')
        self.assertEqual(response.status_code, 200)

    def test_processing_route(self):
        """Verifica que la ruta GET /processing devuelve 200."""
        response = self.app_client.get('/processing')
        self.assertEqual(response.status_code, 200)

    def test_processing_post_no_file(self):
        """Verifica que POST /processing sin archivo redirige."""
        response = self.app_client.post('/processing', follow_redirects=True)
        self.assertEqual(response.status_code, 200)

    def test_session_video_no_file(self):
        """Verifica que POST /api/session_video sin archivo devuelve 400."""
        response = self.app_client.post('/api/session_video')
        self.assertEqual(response.status_code, 400)

    def test_preview_frame_no_session(self):
        """Verifica que POST /api/preview_frame con sesión inválida devuelve 404."""
        response = self.app_client.post(
            '/api/preview_frame',
            data=json.dumps({'video_path': 'invalid_session', 'position': 0.5, 'orientation': 'horizontal'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 404)

    def test_results_not_found(self):
        """Verifica que GET /results/9999 para video inexistente redirige."""
        response = self.app_client.get('/results/9999', follow_redirects=True)
        self.assertEqual(response.status_code, 200)

    def test_results_existing_video(self):
        """Verifica que GET /results para un video existente devuelve 200."""
        vid = db.insert_video('test.mp4', 'original.mp4', 'horizontal', 0.5)
        db.update_video_status(vid, 'done', total_vehicles=5)
        response = self.app_client.get(f'/results/{vid}')
        self.assertEqual(response.status_code, 200)

    def test_delete_video_route(self):
        """Verifica que POST /delete_video elimina el video."""
        vid = db.insert_video('test.mp4', 'original.mp4', 'horizontal', 0.5)
        response = self.app_client.post(f'/delete_video/{vid}', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        detail = db.get_video_detail(vid)
        self.assertIsNone(detail)

    def test_job_progress_not_found(self):
        """Verifica que GET /job_progress/invalido devuelve un evento de error."""
        response = self.app_client.get('/job_progress/invalid_job')
        data = response.data.decode('utf-8')
        self.assertIn('error', data)


if __name__ == '__main__':
    unittest.main()

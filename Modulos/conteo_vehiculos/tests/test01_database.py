"""
test01_database.py — Prueba las operaciones CRUD de la base de datos del módulo de conteo de vehículos.
"""
import unittest
import sys
from pathlib import Path

module_dir = Path(__file__).parent.parent.resolve()
sys.path.append(str(module_dir))

import database as db


class TestDatabase(unittest.TestCase):

    def setUp(self):
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

    def test_insert_video(self):
        """Verifica la inserción de un video en la BD."""
        vid = db.insert_video('test.mp4', 'original.mp4', 'horizontal', 0.5)
        self.assertIsNotNone(vid)
        self.assertGreater(vid, 0)

    def test_insert_video_with_conf(self):
        """Verifica la inserción con umbral de confianza personalizado."""
        vid = db.insert_video('test.mp4', 'original.mp4', 'horizontal', 0.5, conf_threshold=0.7)
        detail = db.get_video_detail(vid)
        self.assertAlmostEqual(detail['conf_threshold'], 0.7)

    def test_update_status(self):
        """Verifica la actualización del estado y contadores de un video."""
        vid = db.insert_video('test.mp4', 'original.mp4', 'vertical', 0.3)
        db.update_video_status(vid, 'done', total_vehicles=50, duration_seconds=120.0, total_entry=30, total_exit=20)
        detail = db.get_video_detail(vid)
        self.assertEqual(detail['status'], 'done')
        self.assertEqual(detail['total_vehicles'], 50)
        self.assertEqual(detail['total_entry'], 30)
        self.assertEqual(detail['total_exit'], 20)

    def test_upsert_vehicle_counts(self):
        """Verifica la inserción y actualización de conteos por tipo de vehículo."""
        vid = db.insert_video('test.mp4', 'original.mp4', 'horizontal', 0.5)
        db.upsert_vehicle_count(vid, 'car', 10, entry_count=6, exit_count=4)
        db.upsert_vehicle_count(vid, 'truck', 5, entry_count=3, exit_count=2)
        detail = db.get_video_detail(vid)
        counts = {c['vehicle_type']: c for c in detail['counts']}
        self.assertEqual(counts['car']['count'], 10)
        self.assertEqual(counts['car']['entry_count'], 6)
        self.assertEqual(counts['car']['exit_count'], 4)
        self.assertEqual(counts['truck']['count'], 5)

    def test_upsert_vehicle_counts_update(self):
        """Verifica que upsert actualice conteos existentes."""
        vid = db.insert_video('test.mp4', 'original.mp4', 'horizontal', 0.5)
        db.upsert_vehicle_count(vid, 'car', 5, entry_count=3, exit_count=2)
        db.upsert_vehicle_count(vid, 'car', 8, entry_count=5, exit_count=3)
        detail = db.get_video_detail(vid)
        counts = {c['vehicle_type']: c for c in detail['counts']}
        self.assertEqual(counts['car']['count'], 8)

    def test_get_video_detail(self):
        """Verifica que get_video_detail devuelve todos los campos."""
        vid = db.insert_video('test_detail.mp4', 'detail.mp4', 'horizontal', 0.5, conf_threshold=0.4)
        db.update_video_status(vid, 'done', total_vehicles=10, total_entry=5, total_exit=5)
        db.upsert_vehicle_count(vid, 'car', 8, entry_count=4, exit_count=4)
        detail = db.get_video_detail(vid)
        self.assertEqual(detail['filename'], 'test_detail.mp4')
        self.assertEqual(detail['line_orientation'], 'horizontal')
        self.assertEqual(detail['total_entry'], 5)
        self.assertEqual(detail['total_exit'], 5)
        self.assertEqual(len(detail['counts']), 1)

    def test_get_all_videos(self):
        """Verifica que get_all_videos devuelve todos los videos ordenados."""
        v1 = db.insert_video('a.mp4', 'A.mp4', 'horizontal', 0.5)
        v2 = db.insert_video('b.mp4', 'B.mp4', 'vertical', 0.7)
        videos = db.get_all_videos()
        self.assertGreaterEqual(len(videos), 2)
        ids = [v['id'] for v in videos]
        self.assertIn(v1, ids)
        self.assertIn(v2, ids)

    def test_delete_video(self):
        """Verifica que eliminar un video también elimina sus conteos."""
        vid = db.insert_video('test.mp4', 'test.mp4', 'horizontal', 0.5)
        db.upsert_vehicle_count(vid, 'car', 5)
        db.delete_video(vid)
        detail = db.get_video_detail(vid)
        self.assertIsNone(detail)


if __name__ == '__main__':
    unittest.main()

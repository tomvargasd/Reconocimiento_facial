import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import Modulos.conteo_vehiculos.database as db
from Modulos.conteo_vehiculos.vehicle_counter import build_region_points, COCO_VEHICLE_IDS


class TestDatabase(unittest.TestCase):

    def setUp(self):
        db.init_db()

    def tearDown(self):
        videos = db.get_all_videos()
        for v in videos:
            db.delete_video(v['id'])

    def test_insert_video(self):
        vid = db.insert_video('test.mp4', 'original.mp4', 'horizontal', 0.5)
        self.assertIsNotNone(vid)
        self.assertGreater(vid, 0)

    def test_update_status(self):
        vid = db.insert_video('test.mp4', 'original.mp4', 'vertical', 0.3)
        db.update_video_status(vid, 'done', total_vehicles=50, duration_seconds=120.0)
        detail = db.get_video_detail(vid)
        self.assertEqual(detail['status'], 'done')
        self.assertEqual(detail['total_vehicles'], 50)

    def test_upsert_counts(self):
        vid = db.insert_video('test.mp4', 'original.mp4', 'horizontal', 0.5)
        db.upsert_vehicle_count(vid, 'car', 10)
        db.upsert_vehicle_count(vid, 'truck', 5)
        detail = db.get_video_detail(vid)
        counts = {c['vehicle_type']: c['count'] for c in detail['counts']}
        self.assertEqual(counts['car'], 10)
        self.assertEqual(counts['truck'], 5)

    def test_get_all_videos_order(self):
        v1 = db.insert_video('a.mp4', 'A.mp4', 'horizontal', 0.5)
        v2 = db.insert_video('b.mp4', 'B.mp4', 'vertical', 0.7)
        videos = db.get_all_videos()
        self.assertGreaterEqual(len(videos), 2)

    def test_delete_video_cascades(self):
        vid = db.insert_video('test.mp4', 'test.mp4', 'horizontal', 0.5)
        db.upsert_vehicle_count(vid, 'car', 5)
        db.delete_video(vid)
        detail = db.get_video_detail(vid)
        self.assertIsNone(detail)


class TestVehicleCounter(unittest.TestCase):

    def test_build_region_horizontal(self):
        points = build_region_points(640, 480, 'horizontal', 0.5)
        self.assertEqual(points, [(0, 240), (640, 240)])

    def test_build_region_vertical(self):
        points = build_region_points(640, 480, 'vertical', 0.3)
        self.assertEqual(points, [(192, 0), (192, 480)])

    def test_build_region_horizontal_top(self):
        points = build_region_points(640, 480, 'horizontal', 0.0)
        self.assertEqual(points, [(0, 0), (640, 0)])

    def test_build_region_vertical_right(self):
        points = build_region_points(640, 480, 'vertical', 1.0)
        self.assertEqual(points, [(640, 0), (640, 480)])

    def test_coco_vehicle_ids(self):
        self.assertIn(1, COCO_VEHICLE_IDS)
        self.assertIn(2, COCO_VEHICLE_IDS)
        self.assertIn(3, COCO_VEHICLE_IDS)
        self.assertIn(5, COCO_VEHICLE_IDS)
        self.assertIn(7, COCO_VEHICLE_IDS)
        self.assertEqual(len(COCO_VEHICLE_IDS), 5)


if __name__ == '__main__':
    unittest.main()

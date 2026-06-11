"""
test03_vehicle_processing.py — Prueba las funciones de procesamiento de vehículos,
incluyendo la construcción de puntos de región, constantes e inferencia
con un video de ejemplo proporcionado manualmente en la carpeta tests/samples/.
"""
import unittest
import sys
import os
from pathlib import Path

module_dir = Path(__file__).parent.parent.resolve()
sys.path.append(str(module_dir))

from vehicle_counter import build_region_points, COCO_VEHICLE_IDS


class TestVehicleCounterUtils(unittest.TestCase):
    """Pruebas unitarias de las funciones auxiliares de conteo de vehículos."""

    def test_build_region_horizontal(self):
        """Verifica que build_region_points calcule correctamente una línea horizontal al 50%."""
        points = build_region_points(640, 480, 'horizontal', 0.5)
        self.assertEqual(points, [(0, 240), (640, 240)])

    def test_build_region_vertical(self):
        """Verifica que build_region_points calcule correctamente una línea vertical al 30%."""
        points = build_region_points(640, 480, 'vertical', 0.3)
        self.assertEqual(points, [(192, 0), (192, 480)])

    def test_build_region_horizontal_top(self):
        """Verifica que la posición 0% coloque la línea en el borde superior."""
        points = build_region_points(640, 480, 'horizontal', 0.0)
        self.assertEqual(points, [(0, 0), (640, 0)])

    def test_build_region_vertical_right(self):
        """Verifica que la posición 100% coloque la línea en el borde derecho."""
        points = build_region_points(640, 480, 'vertical', 1.0)
        self.assertEqual(points, [(640, 0), (640, 480)])

    def test_coco_vehicle_ids(self):
        """Verifica que COCO_VEHICLE_IDS contenga los IDs correctos de vehículos COCO."""
        self.assertIn(1, COCO_VEHICLE_IDS)
        self.assertIn(2, COCO_VEHICLE_IDS)
        self.assertIn(3, COCO_VEHICLE_IDS)
        self.assertIn(5, COCO_VEHICLE_IDS)
        self.assertIn(7, COCO_VEHICLE_IDS)
        self.assertEqual(len(COCO_VEHICLE_IDS), 5)


class TestVehicleInference(unittest.TestCase):
    """
    Prueba de inferencia con un video de ejemplo.

    Para ejecutar esta prueba, coloca un archivo de video (sample_video.mp4)
    dentro de la carpeta tests/samples/ del módulo.
    Si no hay un video de ejemplo, la prueba se omite con un mensaje claro.
    """

    SAMPLES_DIR = module_dir / 'tests' / 'samples'

    @classmethod
    def setUpClass(cls):
        cls.sample_video = None
        if cls.SAMPLES_DIR.exists():
            videos = list(cls.SAMPLES_DIR.glob('*.mp4')) + list(cls.SAMPLES_DIR.glob('*.avi'))
            if videos:
                cls.sample_video = str(videos[0])

    def _check_sample(self):
        if not self.sample_video:
            self.skipTest(
                f"No se encontró video de ejemplo en {self.SAMPLES_DIR}/.\n"
                "Coloca manualmente un archivo .mp4 en tests/samples/ para ejecutar "
                "la prueba de inferencia."
            )

    def test_process_video_standalone_inference(self):
        """
        Prueba de inferencia completa usando process_video_standalone.
        Verifica que el pipeline se ejecute sin errores y devuelva conteos.

        NOTA: Esta prueba requiere que coloques manualmente un video de ejemplo
        en la carpeta Modulos/conteo_vehiculos/tests/samples/.
        """
        self._check_sample()

        try:
            import database as db

            original_db_path = db.DB_PATH
            db.DB_PATH = module_dir / 'tests' / 'test_inference.db'
            db.init_db()

            from vehicle_counter import process_video_standalone

            video_id, counts = process_video_standalone(
                video_path=self.sample_video,
                orientation='horizontal',
                position=0.5,
                conf_threshold=0.35,
            )

            self.assertIsNotNone(video_id)
            self.assertIsInstance(counts, dict)
            self.assertGreater(video_id, 0)

            db.DB_PATH = original_db_path
            test_db = module_dir / 'tests' / 'test_inference.db'
            if test_db.exists():
                try:
                    test_db.unlink()
                except OSError:
                    pass

        except Exception as e:
            db.DB_PATH = original_db_path
            raise e

    def test_process_video_with_callbacks(self):
        """
        Prueba que process_video ejecute correctamente los callbacks de progreso y conteos.

        NOTA: Esta prueba requiere que coloques manualmente un video de ejemplo
        en la carpeta Modulos/conteo_vehiculos/tests/samples/.
        """
        self._check_sample()

        import database as db
        import vehicle_counter as vc

        original_db_path = db.DB_PATH
        db.DB_PATH = module_dir / 'tests' / 'test_callbacks.db'
        db.init_db()

        progress_values = []
        counts_values = []

        def on_progress(p):
            progress_values.append(p)

        def on_counts(c):
            counts_values.append(c)

        try:
            vid = db.insert_video('inference_test.mp4', 'inference_test.mp4', 'horizontal', 0.5)
            db.update_video_status(vid, 'processing')

            counts, duration, entry_counts, exit_counts = vc.process_video(
                video_path=self.sample_video,
                orientation='horizontal',
                position=0.5,
                progress_callback=on_progress,
                counts_callback=on_counts,
                video_id=vid,
                conf_threshold=0.35,
            )

            self.assertIsInstance(counts, dict)
            self.assertIsInstance(entry_counts, dict)
            self.assertIsInstance(exit_counts, dict)
            self.assertGreater(duration, 0)
            self.assertGreater(len(progress_values), 0)
            self.assertGreaterEqual(progress_values[-1], 0)

        finally:
            db.DB_PATH = original_db_path
            test_db = module_dir / 'tests' / 'test_callbacks.db'
            if test_db.exists():
                try:
                    test_db.unlink()
                except OSError:
                    pass


if __name__ == '__main__':
    unittest.main()

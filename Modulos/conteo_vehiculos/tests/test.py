"""
test.py — Ejecutor de pruebas (test runner) de todos los tests del módulo de conteo de vehículos.
"""
import unittest
import sys
from pathlib import Path

module_dir = Path(__file__).parent.parent.resolve()
sys.path.append(str(module_dir))


def run_all_tests():
    print("=" * 60)
    print("Iniciando Pruebas Unitarias del Módulo de Conteo de Vehículos")
    print("=" * 60)

    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=str(module_dir / 'tests'), pattern='test*.py')

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    if not result.wasSuccessful():
        sys.exit(1)


if __name__ == '__main__':
    run_all_tests()

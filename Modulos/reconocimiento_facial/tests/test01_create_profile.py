"""
test01_create_profile.py — Prueba la creación de un perfil de persona a través de la base de datos y la ruta de Flask.
"""
import unittest
import sys
from pathlib import Path

# Agregar la ruta del módulo para que los imports funcionen correctamente
module_dir = Path(__file__).parent.parent.resolve()
sys.path.append(str(module_dir))

import database
from app import app


class TestCreateProfile(unittest.TestCase):

    def setUp(self):
        # Usar la base de datos de pruebas configurada en memoria o archivo temporal
        self.app_client = app.test_client()
        app.config['TESTING'] = True
        
        # Guardar la ruta original de la BD
        self.original_db_path = database.DB_PATH
        # Configurar base de datos de pruebas temporal
        database.DB_PATH = module_dir / 'test_database.db'
        database.init_db()

    def tearDown(self):
        # Restaurar la ruta de la base de datos original
        database.DB_PATH = self.original_db_path
        # Limpiar archivo temporal de base de datos de pruebas
        test_db = module_dir / 'test_database.db'
        if test_db.exists():
            try:
                test_db.unlink()
            except OSError:
                pass

    def test_create_profile_db(self):
        """Verifica la inserción de una persona directamente en la BD."""
        conn = database.get_conn()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Personas (nombre) VALUES (?)", ("Test Persona",))
        conn.commit()
        
        row = conn.execute("SELECT * FROM Personas WHERE nombre = ?", ("Test Persona",)).fetchone()
        conn.close()
        
        self.assertIsNotNone(row)
        self.assertEqual(row['nombre'], "Test Persona")

    def test_create_profile_route(self):
        """Verifica la creación de un perfil mediante la ruta HTTP POST."""
        response = self.app_client.post('/profiles', data={'nombre': 'Juan Perez'}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        conn = database.get_conn()
        row = conn.execute("SELECT * FROM Personas WHERE nombre = ?", ("Juan Perez",)).fetchone()
        conn.close()

        self.assertIsNotNone(row)
        self.assertEqual(row['nombre'], "Juan Perez")


if __name__ == '__main__':
    unittest.main()

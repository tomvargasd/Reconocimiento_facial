import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / 'database.db'

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS Personas (id INTEGER PRIMARY KEY, nombre TEXT NOT NULL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS ImagenesPerfil (id INTEGER PRIMARY KEY, persona_id INTEGER, ruta_imagen TEXT NOT NULL, caracteristicas_faciales BLOB)''')
    c.execute('''CREATE TABLE IF NOT EXISTS Detecciones (id INTEGER PRIMARY KEY, persona_id INTEGER, ruta_imagen_captura TEXT NOT NULL, fecha_hora TIMESTAMP)''')
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / 'database.db'

VEHICLE_CLASSES = {
    1: 'bicycle',
    2: 'car',
    3: 'motorcycle',
    5: 'bus',
    7: 'truck',
}

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS Videos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        original_filename TEXT NOT NULL,
        processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        line_orientation TEXT NOT NULL,
        line_position REAL NOT NULL,
        total_vehicles INTEGER DEFAULT 0,
        duration_seconds REAL DEFAULT 0,
        status TEXT DEFAULT 'pending'
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS VehicleCounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        video_id INTEGER NOT NULL,
        vehicle_type TEXT NOT NULL,
        count INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY (video_id) REFERENCES Videos(id) ON DELETE CASCADE,
        UNIQUE(video_id, vehicle_type)
    )''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_videos_status ON Videos(status)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_counts_video ON VehicleCounts(video_id)')
    conn.commit()
    conn.close()

def insert_video(filename, original_filename, orientation, position):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        'INSERT INTO Videos (filename, original_filename, line_orientation, line_position, status) VALUES (?, ?, ?, ?, ?)',
        (filename, original_filename, orientation, position, 'pending')
    )
    conn.commit()
    video_id = c.lastrowid
    conn.close()
    return video_id

def update_video_status(video_id, status, total_vehicles=None, duration_seconds=None):
    conn = get_conn()
    fields = ['status = ?']
    values = [status]
    if total_vehicles is not None:
        fields.append('total_vehicles = ?')
        values.append(total_vehicles)
    if duration_seconds is not None:
        fields.append('duration_seconds = ?')
        values.append(duration_seconds)
    values.append(video_id)
    conn.execute(f'UPDATE Videos SET {", ".join(fields)} WHERE id = ?', values)
    conn.commit()
    conn.close()

def upsert_vehicle_count(video_id, vehicle_type, count):
    conn = get_conn()
    conn.execute(
        'INSERT INTO VehicleCounts (video_id, vehicle_type, count) VALUES (?, ?, ?) '
        'ON CONFLICT(video_id, vehicle_type) DO UPDATE SET count = ?',
        (video_id, vehicle_type, count, count)
    )
    conn.commit()
    conn.close()

def get_all_videos():
    conn = get_conn()
    rows = conn.execute(
        'SELECT * FROM Videos ORDER BY processed_at DESC'
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_video_detail(video_id):
    conn = get_conn()
    video = conn.execute('SELECT * FROM Videos WHERE id = ?', (video_id,)).fetchone()
    if not video:
        conn.close()
        return None
    counts = conn.execute(
        'SELECT vehicle_type, count FROM VehicleCounts WHERE video_id = ? ORDER BY vehicle_type',
        (video_id,)
    ).fetchall()
    conn.close()
    return {**dict(video), 'counts': [dict(c) for c in counts]}

def delete_video(video_id):
    conn = get_conn()
    conn.execute('DELETE FROM Videos WHERE id = ?', (video_id,))
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()

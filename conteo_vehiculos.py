import sys
import argparse
from pathlib import Path

module_dir = Path(__file__).parent / 'Modulos' / 'conteo_vehiculos'
sys.path.insert(0, str(module_dir))

import database as db
from app import app

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Conteo de Vehículos")
    parser.add_argument('--port', type=int, default=5001)
    args = parser.parse_args()

    db.init_db()
    for folder in ['uploads', 'uploaded_videos']:
        p = module_dir / folder
        p.mkdir(exist_ok=True)

    app.run(host='127.0.0.1', port=args.port, debug=True)

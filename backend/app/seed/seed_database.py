"""Initialize the local SQLite demo database."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

if __name__ == '__main__':
    database = ROOT / 'smart_operator.db'
    if '--reset' in sys.argv and database.exists():
        database.unlink()
    from app.main import seed

    seed()
    print('Smart Operator Companion SQLite database seeded.')

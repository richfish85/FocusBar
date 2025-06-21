import json
import os
from datetime import datetime

_DATA_DIR = os.path.join(os.path.expanduser('~'), '.pomopad')
os.makedirs(_DATA_DIR, exist_ok=True)


def _data_file():
    now = datetime.now()
    return os.path.join(_DATA_DIR, f'sessions_{now:%Y-%m}.json')


def load_sessions():
    """Return saved sessions and categories from disk."""
    try:
        with open(_data_file(), 'r') as f:
            return json.load(f)
    except Exception:
        return {'sessions_by_date': {}, 'categories': {}}


def save_sessions(data):
    """Persist sessions and categories to disk."""
    with open(_data_file(), 'w') as f:
        json.dump(data, f, indent=2)

import sqlite3
from pathlib import Path


DEFAULT_DB_PATH = Path(__file__).resolve().parent / 'data' / 'kungfu_chess.db'


def open_database(db_path=None) -> sqlite3.Connection:
    path = Path(db_path) if db_path is not None else DEFAULT_DB_PATH
    if str(path) != ':memory:':
        path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(str(path), check_same_thread=False)
    else:
        connection = sqlite3.connect(':memory:', check_same_thread=False)
    return connection

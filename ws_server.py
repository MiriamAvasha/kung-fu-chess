import asyncio
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent / 'kungfu_chess'
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from server.websocket.config import (
    AUTO_RESIGN_SECONDS,
    DB_PATH,
    HOST,
    PORT,
)
from server.websocket_server import main


if __name__ == '__main__':
    asyncio.run(
        main(
            host=HOST,
            port=PORT,
            db_path=DB_PATH,
            auto_resign_seconds=AUTO_RESIGN_SECONDS,
        )
    )

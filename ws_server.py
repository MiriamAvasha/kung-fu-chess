import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENGINE = ROOT / 'engine'
for path in (ENGINE, ROOT):
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)

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

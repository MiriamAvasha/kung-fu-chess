"""Double-click launcher for the graphical online client on Windows."""

import asyncio
import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent / 'kungfu_chess'
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from client.websocket_client import main


if __name__ == '__main__':
    asyncio.run(main())

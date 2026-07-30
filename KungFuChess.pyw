"""Double-click launcher for the graphical online client on Windows."""

import asyncio
import sys
from pathlib import Path
from client.websocket_client import main


ROOT = Path(__file__).resolve().parent
ENGINE = ROOT / 'engine'
for path in (ENGINE, ROOT):
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)



if __name__ == '__main__':
    asyncio.run(main())

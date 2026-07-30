"""Compatibility facade for the graphical WebSocket client."""

from client.gui.app import main
from client.network.config import DEFAULT_URI


URI = DEFAULT_URI

__all__ = ['URI', 'main']

from shared.activity_log import setup_activity_logger

DEFAULT_URI = 'ws://localhost:8765'

# Logs go to logs/client.log only — keep the terminal for the game UI.
client_logger = setup_activity_logger(
    'kungfu.client',
    'client.log',
    console=False,
)

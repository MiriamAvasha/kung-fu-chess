import importlib

from server.db import DEFAULT_DB_PATH


def _reload_config():
    import server.websocket.config as config

    return importlib.reload(config)


def test_config_defaults_without_env(monkeypatch):
    for name in (
        'KUNGFU_HOST',
        'KUNGFU_PORT',
        'KUNGFU_DB_PATH',
        'KUNGFU_TICK_SECONDS',
        'KUNGFU_AUTO_RESIGN_SECONDS',
    ):
        monkeypatch.delenv(name, raising=False)

    config = _reload_config()
    try:
        assert config.HOST == 'localhost'
        assert config.PORT == 8765
        assert config.DB_PATH == DEFAULT_DB_PATH
        assert config.TICK_SECONDS == 0.05
        assert config.AUTO_RESIGN_SECONDS == 20
    finally:
        _reload_config()


def test_config_reads_container_env(monkeypatch):
    monkeypatch.setenv('KUNGFU_HOST', '0.0.0.0')
    monkeypatch.setenv('KUNGFU_PORT', '9000')
    monkeypatch.setenv('KUNGFU_DB_PATH', '/data/kungfu.db')
    monkeypatch.setenv('KUNGFU_TICK_SECONDS', '0.1')
    monkeypatch.setenv('KUNGFU_AUTO_RESIGN_SECONDS', '30')

    config = _reload_config()
    try:
        assert config.HOST == '0.0.0.0'
        assert config.PORT == 9000
        assert str(config.DB_PATH).replace('\\', '/') == '/data/kungfu.db'
        assert config.TICK_SECONDS == 0.1
        assert config.AUTO_RESIGN_SECONDS == 30
    finally:
        for name in (
            'KUNGFU_HOST',
            'KUNGFU_PORT',
            'KUNGFU_DB_PATH',
            'KUNGFU_TICK_SECONDS',
            'KUNGFU_AUTO_RESIGN_SECONDS',
        ):
            monkeypatch.delenv(name, raising=False)
        _reload_config()

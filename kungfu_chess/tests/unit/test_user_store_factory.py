import os

import pytest

from server.auth.store_factory import open_user_store, persistence_backend


def test_persistence_backend_defaults_to_sqlite(monkeypatch):
    monkeypatch.delenv('KUNGFU_PERSISTENCE', raising=False)
    monkeypatch.setenv('DATABASE_URL', '')
    # Reload settings module binding used by factory
    import server.infra.settings as settings
    import server.auth.store_factory as factory

    monkeypatch.setattr(settings, 'DATABASE_URL', '')
    monkeypatch.setattr(factory, 'DATABASE_URL', '')
    assert persistence_backend() == 'sqlite'


def test_persistence_backend_uses_postgres_url(monkeypatch):
    monkeypatch.delenv('KUNGFU_PERSISTENCE', raising=False)
    import server.auth.store_factory as factory

    monkeypatch.setattr(
        factory,
        'DATABASE_URL',
        'postgresql://kungfu:kungfu@localhost:5432/kungfu',
    )
    assert persistence_backend() == 'postgres'


def test_open_user_store_sqlite_memory(monkeypatch):
    monkeypatch.setenv('KUNGFU_PERSISTENCE', 'sqlite')
    repo, connection = open_user_store(':memory:')
    assert connection is not None
    created = repo.create_user('Dana', 'hash', rating=1200)
    assert created.username == 'Dana'
    assert repo.get_by_username('dana').rating == 1200
    connection.close()


@pytest.mark.skipif(
    os.environ.get('KUNGFU_TEST_POSTGRES', '').strip() != '1',
    reason='Set KUNGFU_TEST_POSTGRES=1 with DATABASE_URL to run',
)
def test_open_user_store_postgres_roundtrip():
    os.environ['KUNGFU_PERSISTENCE'] = 'postgres'
    repo, connection = open_user_store()
    assert connection is None
    name = 'PgUser_{}'.format(os.getpid())
    existing = repo.get_by_username(name)
    if existing is None:
        repo.create_user(name, 'hash', rating=1300)
    account = repo.get_by_username(name)
    assert account is not None
    repo.update_rating(name, 1310)
    assert repo.get_by_username(name).rating == 1310

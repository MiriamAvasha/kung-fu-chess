import sqlite3

import pytest

from server.auth import AuthError, AuthService, DEFAULT_RATING, UserRepository
from server.auth.password_hasher import hash_password, verify_password
from server.rating import update_ratings
from server.rating.rating_service import RatingService
from shared.password import validate_password


def test_password_hasher_roundtrip():
    stored = hash_password('secret123')
    assert verify_password('secret123', stored) is True
    assert verify_password('wrong', stored) is False


def test_validate_password_rules():
    ok, value = validate_password('abcd')
    assert ok is True
    assert value == 'abcd'
    bad, message = validate_password('ab')
    assert bad is False
    assert 'at least' in message


def test_auth_registers_then_logs_in():
    connection = sqlite3.connect(':memory:')
    service = AuthService(UserRepository(connection))

    created = service.login_or_register('Alice', 'pass1234')
    assert created.username == 'Alice'
    assert created.rating == DEFAULT_RATING

    again = service.login_or_register('Alice', 'pass1234')
    assert again.username == 'Alice'
    assert again.rating == DEFAULT_RATING


def test_auth_rejects_wrong_password():
    connection = sqlite3.connect(':memory:')
    service = AuthService(UserRepository(connection))
    service.login_or_register('Alice', 'pass1234')

    with pytest.raises(AuthError) as error:
        service.login_or_register('Alice', 'badpass')
    assert error.value.code == 'invalid_credentials'


def test_elo_equal_ratings_winner_gains_loser_loses():
    winner, loser = update_ratings(1200, 1200, score_a=1.0)
    assert winner == 1216
    assert loser == 1184


def test_rating_service_persists_match_result():
    connection = sqlite3.connect(':memory:')
    repository = UserRepository(connection)
    auth = AuthService(repository)
    ratings = RatingService(repository)

    auth.login_or_register('Alice', 'pass1234')
    auth.login_or_register('Bob', 'pass1234')

    updated = ratings.apply_match_result('Alice', 'Bob')
    assert updated['Alice'] == 1216
    assert updated['Bob'] == 1184
    assert repository.get_by_username('Alice').rating == 1216
    assert repository.get_by_username('Bob').rating == 1184

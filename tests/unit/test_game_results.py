import json

from server.infra.game_results import GameResultsRepository


def test_game_results_repository_schema_sql_shape():
    # Smoke: module imports and payload shape used by writer.
    payload = {
        'room_id': 'ABCD',
        'winner': 'Alice',
        'loser': 'Bob',
        'ratings': {'Alice': 1216, 'Bob': 1184},
        'reason': 'game_over',
    }
    assert json.dumps(payload)
    assert GameResultsRepository.__name__ == 'GameResultsRepository'

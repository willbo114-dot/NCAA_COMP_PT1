from cbs.normalize import NUMERIC_FIELDS, PLAYER_FIELDS, flatten_boxscore


SAMPLE_PLAYERS = [
    {
        "athlete": {"displayName": "Player One"},
        "starter": True,
        "statistics": [
            {"name": "PTS", "value": "12"},
            {"name": "REB", "value": "5"},
            {"name": "MIN", "value": "30:15"},
        ],
    },
    {
        "athlete": {"displayName": "Player Two"},
        "starter": False,
        "stats": {"PTS": 8, "REB": 7, "MIN": "18"},
    },
]


def _assert_rows(rows):
    assert rows, "expected rows"
    for row in rows:
        for field in PLAYER_FIELDS:
            assert field in row
        for numeric in NUMERIC_FIELDS:
            assert numeric in row


def test_flatten_structure_a():
    payload = {
        "game": {"startDate": "2024-03-01T20:00:00Z"},
        "teams": [
            {"team": {"displayName": "Team A"}, "players": SAMPLE_PLAYERS},
            {"team": {"displayName": "Team B"}, "players": SAMPLE_PLAYERS},
        ],
    }
    rows = flatten_boxscore("123", payload)
    _assert_rows(rows)
    assert any(row["team"] == "Team A" for row in rows)
    assert any(row["opponent"] == "Team B" for row in rows)


def test_flatten_structure_b():
    payload = {
        "boxscore": {
            "teams": [
                {"team": {"displayName": "Team C"}, "players": SAMPLE_PLAYERS},
                {"team": {"displayName": "Team D"}, "players": SAMPLE_PLAYERS},
            ]
        }
    }
    rows = flatten_boxscore("456", payload)
    _assert_rows(rows)


def test_flatten_structure_c():
    payload = {
        "home": {"name": "Team E", "players": SAMPLE_PLAYERS},
        "away": {"name": "Team F", "players": SAMPLE_PLAYERS},
    }
    rows = flatten_boxscore("789", payload)
    _assert_rows(rows)
    assert any(row["team"] == "Team E" for row in rows)

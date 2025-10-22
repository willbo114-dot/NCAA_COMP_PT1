from datetime import date

from cbs import cli


def test_run_pipeline_with_mocks(tmp_path, monkeypatch):
    start = date(2024, 3, 1)
    end = date(2024, 3, 1)

    scoreboard_payload = {
        "2024-03-01": [
            {"url": "/game/111", "home": {"displayName": "Team A"}, "away": {"displayName": "Team B"}},
            {"url": "/game/222", "home": {"displayName": "Team C"}, "away": {"displayName": "Team D"}},
        ]
    }

    def fake_scoreboard(day: str, base: str):
        return scoreboard_payload.get(day, [])

    def fake_boxscore(game_id: str, base: str):
        return {
            "game": {"startDate": "2024-03-01T20:00:00Z"},
            "teams": [
                {
                    "team": {"displayName": f"Team {game_id[-1]}"},
                    "players": [
                        {
                            "athlete": {"displayName": f"Player {game_id}-1"},
                            "statistics": [
                                {"name": "PTS", "value": "10"},
                                {"name": "REB", "value": "5"},
                                {"name": "AST", "value": "3"},
                                {"name": "MIN", "value": "25"},
                            ],
                        }
                    ],
                },
                {
                    "team": {"displayName": "Opponent"},
                    "players": [
                        {
                            "athlete": {"displayName": f"Opponent Player {game_id}"},
                            "statistics": [
                                {"name": "PTS", "value": "8"},
                                {"name": "REB", "value": "4"},
                                {"name": "AST", "value": "2"},
                                {"name": "MIN", "value": "20"},
                            ],
                        }
                    ],
                },
            ],
        }

    df_logs, df_summary, label, outputs = cli.run_pipeline(
        start,
        end,
        team_filter="all",
        progress=False,
        write_output=False,
        scoreboard_fetch=fake_scoreboard,
        boxscore_fetch=fake_boxscore,
    )

    if hasattr(df_logs, "empty"):
        assert not df_logs.empty
    else:
        assert len(df_logs) > 0
    if hasattr(df_summary, "empty"):
        assert not df_summary.empty
    else:
        assert len(df_summary) > 0
    assert outputs == {}
    assert label == "2024-03-01_2024-03-01_all"

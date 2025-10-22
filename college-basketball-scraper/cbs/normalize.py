"""Normalization utilities for NCAA box scores."""

from __future__ import annotations

from typing import Any

try:
    from dateutil import parser as date_parser  # type: ignore
except ImportError:  # pragma: no cover
    date_parser = None  # type: ignore

from datetime import datetime

NUMERIC_FIELDS = [
    "PTS",
    "REB",
    "AST",
    "STL",
    "BLK",
    "FGM",
    "FGA",
    "3PM",
    "3PA",
    "FTM",
    "FTA",
    "OREB",
    "DREB",
    "PF",
    "TOV",
    "MIN",
]

PLAYER_FIELDS = [
    "date",
    "game_id",
    "player",
    "team",
    "opponent",
    "starter",
    "position",
    *NUMERIC_FIELDS,
]


def _parse_any_date(value: Any) -> str | None:
    if value in (None, "", "-", "--"):
        return None
    if date_parser is not None:
        try:
            parsed = date_parser.parse(str(value))
            return parsed.date().isoformat()
        except (ValueError, TypeError, AttributeError):
            pass
    try:
        return datetime.fromisoformat(str(value)).date().isoformat()
    except (ValueError, TypeError, AttributeError):
        return None


def _extract_game_date(boxscore: dict[str, Any]) -> str | None:
    candidates = [
        ("game", "startDate"),
        ("game", "date"),
        ("game", "startTime"),
        ("header", "startTime"),
        ("header", "gameDate"),
        ("status", "startTime"),
    ]
    for prefix, key in candidates:
        obj = boxscore.get(prefix) if isinstance(boxscore, dict) else None
        if not isinstance(obj, dict):
            continue
        value = obj.get(key)
        if not value:
            continue
        parsed = _parse_any_date(value)
        if parsed:
            return parsed
    # sometimes the date exists at the top level
    for key in ("gameDate", "startTime", "date"):
        value = boxscore.get(key)
        parsed = _parse_any_date(value)
        if parsed:
            return parsed
    return None


def _team_entries(boxscore: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(boxscore.get("teams"), list):
        return boxscore["teams"]
    if isinstance(boxscore.get("boxscore"), dict):
        inner = boxscore["boxscore"].get("teams")
        if isinstance(inner, list):
            return inner
    if {"home", "away"}.issubset(boxscore.keys()):
        entries = []
        for key in ("home", "away"):
            team_obj = boxscore.get(key)
            if isinstance(team_obj, dict):
                entries.append(team_obj)
        if entries:
            return entries
    return []


def _team_name(team_entry: dict[str, Any]) -> str | None:
    if not isinstance(team_entry, dict):
        return None
    team = team_entry.get("team")
    if isinstance(team, dict):
        for key in ("displayName", "name", "nickname", "shortDisplayName"):
            value = team.get(key)
            if value:
                return str(value)
    for key in ("name", "displayName", "nickname", "team"):
        value = team_entry.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _player_name(player: dict[str, Any]) -> str | None:
    athlete = player.get("athlete")
    if isinstance(athlete, dict):
        for key in ("displayName", "shortName", "fullName", "name"):
            value = athlete.get(key)
            if value:
                return str(value)
    for key in ("displayName", "name", "player", "full_name", "athlete"):
        value = player.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _collect_stats(player: dict[str, Any]) -> dict[str, Any]:
    stats: dict[str, Any] = {}

    def ingest(obj: Any) -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(value, (dict, list)):
                    ingest(value)
                else:
                    stats.setdefault(str(key), value)
        elif isinstance(obj, list):
            for item in obj:
                if isinstance(item, dict):
                    name = item.get("name") or item.get("abbr") or item.get("stat") or item.get("label")
                    value = item.get("value") or item.get("statValue") or item.get("displayValue")
                    if name is not None and value is not None:
                        stats.setdefault(str(name), value)
                else:
                    continue

    for key, value in player.items():
        if key in {"statistics", "stats", "totals", "statValues", "statisticsByType"}:
            ingest(value)
        elif isinstance(value, (dict, list)):
            continue
        else:
            stats.setdefault(str(key), value)

    return stats


def _coerce_minutes(value: Any) -> float | None:
    if value in (None, "", "-", "--"):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value)
    if ":" in text:
        try:
            minutes, seconds = text.split(":", 1)
            total = int(minutes) + int(seconds) / 60
            return round(total, 3)
        except ValueError:
            return None
    try:
        return float(text)
    except ValueError:
        return None


def _coerce_numeric(value: Any) -> float | None:
    if value in (None, "", "-", "--"):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if text.endswith("%"):
        text = text[:-1]
    try:
        return float(text)
    except ValueError:
        return None


def flatten_boxscore(game_id: str, boxscore: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalise a box score to per-player rows."""

    teams = _team_entries(boxscore)
    results: list[dict[str, Any]] = []
    game_date = _extract_game_date(boxscore)
    resolved_teams: list[str] = []

    for team_entry in teams:
        team_name = _team_name(team_entry) or ""
        if team_name:
            resolved_teams.append(team_name)
        players = team_entry.get("players")
        if not isinstance(players, list):
            # some payloads use "athletes"
            players = team_entry.get("athletes")
        if not isinstance(players, list):
            continue

        for player in players:
            if not isinstance(player, dict):
                continue
            stats_map = _collect_stats(player)
            row: dict[str, Any] = {key: None for key in PLAYER_FIELDS}
            row["date"] = game_date
            row["game_id"] = str(game_id)
            row["team"] = team_name or None
            row["player"] = _player_name(player)
            row["starter"] = _normalise_starter(stats_map.get("starter"))
            row["position"] = stats_map.get("position") or stats_map.get("pos")

            for stat_key in NUMERIC_FIELDS:
                source_keys = {stat_key, stat_key.lower(), stat_key.upper()}
                # handle alternate labels
                if stat_key == "3PM":
                    source_keys.update({"3PM", "threePointFieldGoalsMade", "tpMade", "threePointersMade"})
                elif stat_key == "3PA":
                    source_keys.update({"threePointFieldGoalsAttempted", "tpAtt", "threePointersAttempted"})
                elif stat_key == "FGM":
                    source_keys.update({"fieldGoalsMade", "fgMade"})
                elif stat_key == "FGA":
                    source_keys.update({"fieldGoalsAttempted", "fgAttempted"})
                elif stat_key == "FTM":
                    source_keys.update({"freeThrowsMade", "ftMade"})
                elif stat_key == "FTA":
                    source_keys.update({"freeThrowsAttempted", "ftAttempted"})
                elif stat_key == "OREB":
                    source_keys.update({"offensiveRebounds", "oReb"})
                elif stat_key == "DREB":
                    source_keys.update({"defensiveRebounds", "dReb"})

                value = None
                for key in source_keys:
                    if key in stats_map:
                        value = stats_map[key]
                        break
                if stat_key == "MIN":
                    row[stat_key] = _coerce_minutes(value)
                else:
                    row[stat_key] = _coerce_numeric(value)

            results.append(row)

    if len(set(filter(None, resolved_teams))) == 2:
        teams_unique = list(dict.fromkeys(filter(None, resolved_teams)))  # preserve order
        if len(teams_unique) == 2:
            for row in results:
                team_name = row.get("team")
                if team_name == teams_unique[0]:
                    row["opponent"] = teams_unique[1]
                elif team_name == teams_unique[1]:
                    row["opponent"] = teams_unique[0]

    return results


def _normalise_starter(value: Any) -> bool | None:
    if value in (None, "", "-", "--"):
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    truthy = {"1", "true", "yes", "y", "starter", "started"}
    falsy = {"0", "false", "no", "n", "bench", "reserve"}
    if text in truthy:
        return True
    if text in falsy:
        return False
    return None


__all__ = ["flatten_boxscore", "NUMERIC_FIELDS", "PLAYER_FIELDS"]

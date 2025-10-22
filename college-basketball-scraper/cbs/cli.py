"""Interactive entry point for the College Basketball Scraper."""

from __future__ import annotations

import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any, Callable, Iterable, Sequence

try:  # pragma: no cover - optional dependency
    import pandas as pd  # type: ignore
except ImportError:  # pragma: no cover
    pd = None  # type: ignore

try:  # pragma: no cover - optional dependency
    from tqdm import tqdm as tqdm_cls
except ImportError:  # pragma: no cover
    def tqdm_cls(iterable, **kwargs):  # type: ignore
        return iterable

from . import normalize
from .export import write_outputs
from .providers import ncaa_api
from .utils import io as io_utils
from .utils.dates import daterange, parse_date
from .utils.display import preview_table

ScoreboardFetcher = Callable[[str, str], Sequence[dict[str, Any]]]
BoxscoreFetcher = Callable[[str, str], dict[str, Any] | None]
NUMERIC_STATS = [
    "PTS",
    "REB",
    "AST",
    "STL",
    "BLK",
    "3PM",
    "3PA",
    "FGM",
    "FGA",
    "FTM",
    "FTA",
    "OREB",
    "DREB",
    "PF",
    "TOV",
    "MIN",
]


def _yesterday() -> date:
    return date.today() - timedelta(days=1)


def _prompt(prompt: str, default: str) -> str:
    response = input(prompt).strip()
    return response or default


def _game_contains_team(game: dict[str, Any], target: str) -> bool:
    if not target or target.lower() == "all":
        return True
    target_norm = target.lower()
    names: set[str] = set()

    for key in ("home", "away", "team"):
        obj = game.get(key)
        if isinstance(obj, dict):
            for name_key in (
                "displayName",
                "name",
                "nickname",
                "shortDisplayName",
                "teamDisplayName",
            ):
                value = obj.get(name_key)
                if isinstance(value, str):
                    names.add(value.lower())
    teams = game.get("teams")
    if isinstance(teams, list):
        for team in teams:
            if isinstance(team, dict):
                team_obj = team.get("team") if isinstance(team.get("team"), dict) else team
                if isinstance(team_obj, dict):
                    for name_key in (
                        "displayName",
                        "name",
                        "nickname",
                        "shortDisplayName",
                    ):
                        value = team_obj.get(name_key)
                        if isinstance(value, str):
                            names.add(value.lower())
    return any(target_norm in name for name in names)


def _label_for_outputs(start: date, end: date, team: str) -> str:
    team_slug = team.lower().replace(" ", "_") if team and team.lower() != "all" else "all"
    return f"{start.isoformat()}_{end.isoformat()}_{team_slug}"


def _progress(iterable: Iterable[Any], *, desc: str, enabled: bool) -> Iterable[Any]:
    if enabled:
        return tqdm_cls(iterable, desc=desc)
    return iterable


def _ensure_date_string(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, datetime):
        return value.date().isoformat()
    return str(value)


def _aggregate_with_pandas(player_rows: list[dict[str, Any]]):
    assert pd is not None  # for type checkers
    df_logs = pd.DataFrame(player_rows, columns=normalize.PLAYER_FIELDS)
    for field in normalize.NUMERIC_FIELDS:
        if field in df_logs.columns:
            df_logs[field] = pd.to_numeric(df_logs[field], errors="coerce")
    if not df_logs.empty:
        df_logs["date"] = pd.to_datetime(df_logs["date"], errors="coerce").dt.date.astype(str)
        df_logs["date_dt"] = pd.to_datetime(df_logs["date"], errors="coerce")
        grouped = df_logs.groupby(["player", "team"], dropna=False)
        summary_records: list[dict[str, Any]] = []
        for (player, team), group in grouped:
            group_sorted = group.sort_values("date_dt")
            season_means = group_sorted[NUMERIC_STATS].mean()
            rolling = group_sorted[NUMERIC_STATS].rolling(window=5, min_periods=1).mean()
            recent_means = rolling.iloc[-1]
            record: dict[str, Any] = {
                "player": player,
                "team": team,
                "n_games": int(len(group_sorted)),
            }
            for stat in NUMERIC_STATS:
                record[f"season_{stat.lower()}"] = season_means.get(stat)
                record[f"recent_{stat.lower()}"] = recent_means.get(stat)
            summary_records.append(record)
        df_summary = pd.DataFrame(summary_records)
        if not df_summary.empty:
            df_summary.sort_values(["player", "team"], inplace=True)
        df_logs.drop(columns=["date_dt"], inplace=True)
    else:
        df_summary = pd.DataFrame(
            columns=["player", "team", "n_games"]
            + [f"season_{s.lower()}" for s in NUMERIC_STATS]
            + [f"recent_{s.lower()}" for s in NUMERIC_STATS]
        )
    return df_logs, df_summary


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _aggregate_without_pandas(player_rows: list[dict[str, Any]]):
    cleaned_rows: list[dict[str, Any]] = []
    for row in player_rows:
        new_row = dict(row)
        new_row["date"] = _ensure_date_string(row.get("date"))
        cleaned_rows.append(new_row)

    grouped: dict[tuple[Any, Any], list[dict[str, Any]]] = defaultdict(list)
    for row in cleaned_rows:
        key = (row.get("player"), row.get("team"))
        grouped[key].append(row)

    summary_records: list[dict[str, Any]] = []
    for (player, team), games in grouped.items():
        games_sorted = sorted(games, key=lambda r: r.get("date") or "")
        record: dict[str, Any] = {
            "player": player,
            "team": team,
            "n_games": len(games_sorted),
        }
        for stat in NUMERIC_STATS:
            season_vals = [
                float(v)
                for v in (game.get(stat) for game in games_sorted)
                if isinstance(v, (int, float))
            ]
            recent_vals = [
                float(v)
                for v in (game.get(stat) for game in games_sorted[-5:])
                if isinstance(v, (int, float))
            ]
            record[f"season_{stat.lower()}"] = _mean(season_vals)
            record[f"recent_{stat.lower()}"] = _mean(recent_vals)
        summary_records.append(record)

    summary_records.sort(key=lambda r: (r.get("player") or "", r.get("team") or ""))
    return cleaned_rows, summary_records


def run_pipeline(
    start_date: date,
    end_date: date,
    team_filter: str = "all",
    base_url: str = ncaa_api.DEFAULT_BASE_URL,
    *,
    progress: bool = True,
    write_output: bool = True,
    scoreboard_fetch: ScoreboardFetcher | None = None,
    boxscore_fetch: BoxscoreFetcher | None = None,
) -> tuple[Any, Any, str, dict[str, Any]]:
    """Execute the scraping pipeline and return the resulting tables."""

    scoreboard_fetch = scoreboard_fetch or ncaa_api.scoreboard_mbb_d1
    boxscore_fetch = boxscore_fetch or ncaa_api.game_boxscore

    all_dates = list(daterange(start_date, end_date))
    date_strings = [d.isoformat() for d in all_dates]
    game_dates: dict[str, str] = {}
    game_ids: list[str] = []

    for day in _progress(date_strings, desc="Collecting games", enabled=progress):
        games = scoreboard_fetch(day, base_url) or []
        for game in games:
            if not isinstance(game, dict):
                continue
            if not _game_contains_team(game, team_filter):
                continue
            ids = ncaa_api.extract_game_ids([game])
            if not ids:
                continue
            game_id = ids[0]
            if game_id not in game_dates:
                game_dates[game_id] = day
                game_ids.append(game_id)

    player_rows: list[dict[str, Any]] = []

    for game_id in _progress(game_ids, desc="Downloading boxscores", enabled=progress):
        payload = boxscore_fetch(game_id, base_url)
        if not payload:
            continue
        rows = normalize.flatten_boxscore(game_id, payload)
        for row in rows:
            if not row.get("date"):
                row["date"] = game_dates.get(game_id)
            player_rows.append(row)

    if pd is not None:
        df_logs, df_summary = _aggregate_with_pandas(player_rows)
    else:
        df_logs, df_summary = _aggregate_without_pandas(player_rows)

    label = _label_for_outputs(start_date, end_date, team_filter)
    outputs: dict[str, Any] = {}

    if write_output:
        io_utils.ensure_dirs()
        csv_path = io_utils.raw_csv_path(label)
        xlsx_path = io_utils.xlsx_path(label)
        write_outputs(df_logs, df_summary, csv_path, xlsx_path)
        outputs = {"csv": csv_path, "xlsx": xlsx_path}

    return df_logs, df_summary, label, outputs


def main() -> None:
    print("==== NCAA MBB Scraper ====")
    default_start = _yesterday().isoformat()
    start_raw = _prompt(f"Enter START date (YYYY-MM-DD) [default: {default_start}]: ", default_start)
    try:
        start_date = parse_date(start_raw)
    except Exception as exc:
        print(f"Error: {exc}")
        sys.exit(1)

    default_end = start_raw
    end_raw = _prompt(f"Enter END date (YYYY-MM-DD)   [default: {default_end}]: ", default_end)
    try:
        end_date = parse_date(end_raw)
    except Exception as exc:
        print(f"Error: {exc}")
        sys.exit(1)

    team_raw = _prompt("Enter TEAM name (or 'all')    [default: all]: ", "all")
    base_default = ncaa_api.DEFAULT_BASE_URL
    base_raw = _prompt(
        f"NCAA API base URL             [default: {base_default}]: ",
        base_default,
    )

    df_logs, df_summary, label, outputs = run_pipeline(
        start_date,
        end_date,
        team_raw,
        base_raw,
        progress=True,
        write_output=True,
    )

    print("\nPlayer logs preview:")
    print(preview_table(df_logs))
    print("\nSummary preview:")
    print(preview_table(df_summary))

    if outputs:
        print("\nOutputs written:")
        for kind, path in outputs.items():
            print(f"  {kind}: {path}")


if __name__ == "__main__":  # pragma: no cover - CLI entry
    main()

"""Client for the local NCAA basketball API."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Iterable

try:
    import requests  # type: ignore
except ImportError:  # pragma: no cover
    requests = None  # type: ignore

try:
    from requests import Response  # type: ignore
except ImportError:  # pragma: no cover
    Response = Any  # type: ignore

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "http://localhost:3000"
_GAME_ID_PATTERN = re.compile(r"/game/(\d+)")


@dataclass
class _RequestConfig:
    path: str
    description: str


def _request_json(path: str, base_url: str, *, attempts: int = 2) -> dict[str, Any] | None:
    if requests is None:  # pragma: no cover - dependency guard
        raise RuntimeError("The 'requests' package is required for network access.")
    url = base_url.rstrip("/") + path
    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            response: Response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:  # pragma: no cover - network dependent
            last_exc = exc
            logger.warning("Request to %s failed on attempt %s/%s: %s", url, attempt, attempts, exc)
    if last_exc:
        logger.error("Giving up on %s after %s attempts", url, attempts)
    return None


def scoreboard_mbb_d1(game_date: str, base_url: str = DEFAULT_BASE_URL) -> list[dict[str, Any]]:
    """Fetch the Division I men's scoreboard for ``game_date`` (YYYY-MM-DD)."""

    try:
        year, month, day = game_date.split("-")
    except ValueError as exc:  # pragma: no cover - validated earlier
        raise ValueError("game_date must be YYYY-MM-DD") from exc

    path = f"/scoreboard/basketball-men/d1/{year}/{month}/{day}/all-conf"
    data = _request_json(path, base_url) or {}
    games = data.get("games")
    if isinstance(games, list):
        return games
    return []


def game_boxscore(game_id: str, base_url: str = DEFAULT_BASE_URL) -> dict[str, Any] | None:
    """Fetch a game's box score, attempting multiple endpoints."""

    for path in (f"/game/{game_id}/boxscore", f"/game/{game_id}"):
        payload = _request_json(path, base_url)
        if not payload:
            continue
        if "teams" in payload and isinstance(payload["teams"], list):
            return payload
        if (
            isinstance(payload.get("boxscore"), dict)
            and isinstance(payload["boxscore"].get("teams"), list)
        ):
            return payload
        if {"home", "away"}.issubset(payload.keys()):
            return payload
    logger.warning("No usable box score structure for game %s", game_id)
    return None


def extract_game_ids(games_payload: Iterable[dict[str, Any]]) -> list[str]:
    """Extract game identifiers from scoreboard payloads."""

    game_ids: list[str] = []
    for game in games_payload:
        url = game.get("url") or game.get("link") or ""
        match = _GAME_ID_PATTERN.search(str(url))
        if match:
            game_ids.append(match.group(1))
            continue
        # fallbacks
        gid = game.get("id") or game.get("gameId")
        if gid:
            game_ids.append(str(gid))
    return game_ids


__all__ = [
    "DEFAULT_BASE_URL",
    "scoreboard_mbb_d1",
    "game_boxscore",
    "extract_game_ids",
]

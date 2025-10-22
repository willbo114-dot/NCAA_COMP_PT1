# College Basketball Scraper

The **College Basketball Scraper** fetches NCAA Men's Division I box scores from a locally hosted NCAA API and exports per-player logs along with summary statistics. The tool is aimed at analysts who want a repeatable workflow for downloading, normalizing, and exploring player performance data.

## Prerequisites

1. **Python 3.10+** installed (Windows users can use the `py` launcher).
2. **Docker Desktop** with the [local NCAA API](https://github.com/) running and listening on `http://localhost:3000`.
   - Ensure the service responds, e.g. `GET http://localhost:3000/schools-index` should return HTTP 200.
3. (Optional) Existing `data/` directory can be reused; it will be created automatically if missing.

## QuickStart (Windows)

Double-click `run.bat`. The script will:

1. Create a local virtual environment (`.venv`) if needed.
2. Upgrade `pip` and install project requirements.
3. Launch the interactive scraper (`python -m cbs.cli`).
4. Pause when finished so you can review any console output.

## Manual Usage

```bat
py -m venv .venv
.venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
python -m cbs.cli
```

You will be prompted for:

- **Start date** (default: yesterday)
- **End date** (default: same as start)
- **Team filter** (default: all teams)
- **API base URL** (default: `http://localhost:3000`)

## Outputs

- `data/raw/logs_<label>.csv`
- `data/processed/report_<label>.xlsx`
  - Sheet **stats_raw** contains every player-game record.
  - Sheet **summary_players** aggregates per player (season averages + last-5-game averages).

The Excel workbook will auto-open on Windows once generated. The console prints previews of the player logs and summary tables using GitHub-flavored Markdown for easy copying.

## Troubleshooting

- **Port 3000 in use** – Stop other services or run the NCAA API on another port and override the base URL when prompted.
- **Empty results** – Make sure you scrape dates during the NCAA season (e.g., `2024-11-06` through `2024-11-10`).
- **API health** – Confirm the API is reachable: `curl http://localhost:3000/schools-index` should respond quickly.
- **SSL / Network issues** – The scraper only targets a local HTTP service; no TLS is expected.

## Development

Run tests with `pytest` from the project root. The codebase favors readability and includes docstrings and type hints where helpful.

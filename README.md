# bikesharebots

Daily bikeshare stats bots for Bluesky. Each run fetches trip data from the [bikeraccoon](https://github.com/mjarrett/bikeraccoon) API, generates four figures, and posts them with a summary to a Bluesky account.

## Generated output

Each run produces:
- **Post text** — trip count, busiest station, least busy station, active station count
- **Last week** — hourly trip chart for the past 7 days
- **Last month** — daily trip chart for the past 31 days
- **All time** — daily trips overlaid by year
- **Station map** — map of stations sized by trip count

Weather overlays are included on the weekly and monthly charts when a Visual Crossing API key is configured.

## Setup

Install dependencies with [uv](https://docs.astral.sh/uv/):

```bash
uv sync
```

Create `bot.credentials.json` in the project root:

```json
{
    "api_key": "...",
    "mapbox_token": "...",
    "mapbox_style_username": "...",
    "mapbox_style_id": "...",
    "visual_crossing_key": "...",
    "bsky_passwords": {
        "toronto.raccoon.bike": "...",
        "montreal.raccoon.bike": "..."
    }
}
```

## Bot configs

Each bot has a config file in `configs/`:

```json
{
    "sys_name": "bike_share_toronto",
    "account": "toronto.raccoon.bike",
    "lang": "EN",
    "brand": "Toronto Bikeshare",
    "hashtags": ["#bikeTO"],
    "palette": ["#8357B2", "#3286AD"],
    "sys_type": "stations",
    "extent": [-79.556, -79.283, 43.572, 43.774]
}
```

| Field | Description |
|---|---|
| `sys_name` | System identifier used by the bikeraccoon API |
| `account` | Bluesky handle (password stored in `bot.credentials.json`) |
| `lang` | Post language: `EN` or `FR` |
| `brand` | Display name used in post text |
| `hashtags` | List of hashtags to append to the post |
| `palette` | Two-colour matplotlib palette |
| `sys_type` | `stations` (default) |
| `extent` | Map bounding box `[lon_min, lon_max, lat_min, lat_max]` |

## Usage

```bash
# Normal run — generates figures and posts to Bluesky
bikesharebots configs/bike_share_toronto.json

# Test run — generates figures and prints post text, no post made
bikesharebots configs/bike_share_toronto.json --test
```

Output files are written to `output/<sys_name>/`. Weather API responses are cached per-day in `.weather_cache/` to avoid redundant API calls across runs.

## Bots

| Config | Account | City |
|---|---|---|
| `avelo_quebec.json` | quebec.raccoon.bike | Québec City |
| `bike_share_toronto.json` | toronto.raccoon.bike | Toronto |
| `bixi_montreal.json` | montreal.raccoon.bike | Montréal |
| `lime_vancouver.json` | vancouver.raccoon.bike | Vancouver (Lime) |
| `mobi_vancouver.json` | vancouver.raccoon.bike | Vancouver (Mobi) |

import json
import os
import re
import subprocess
import time
from datetime import datetime, timedelta, timezone
from glob import glob

from atproto import Client
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

CREDENTIALS_FILE = "bot.credentials.json"
CACHE_TTL = 300  # seconds

app = FastAPI()
templates = Jinja2Templates(directory="templates")

_cache: dict = {}


def load_credentials():
    with open(CREDENTIALS_FILE) as f:
        return json.load(f)


def fmt_time(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.astimezone().strftime("%Y-%m-%d %H:%M")
    except Exception:
        return iso


def parse_post_date(iso: str):
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.astimezone().date()
    except Exception:
        return None


def fetch_account_data(handle: str, password: str) -> list:
    client = Client()
    client.login(handle, password)

    feed_resp = client.get_author_feed(actor=handle, limit=20)
    posts = []
    for item in feed_resp.feed:
        p = item.post
        text = getattr(p.record, "text", "")
        embed_images = []
        if p.embed and hasattr(p.embed, "images"):
            embed_images = [img.thumb for img in p.embed.images]

        rkey = p.uri.split("/")[-1]
        post_url = f"https://bsky.app/profile/{handle}/post/{rkey}"
        posts.append({
            "text": text,
            "uri": p.uri,
            "url": post_url,
            "indexed_at": fmt_time(p.indexed_at),
            "date": parse_post_date(p.indexed_at),
            "like_count": p.like_count or 0,
            "reply_count": p.reply_count or 0,
            "repost_count": p.repost_count or 0,
            "images": embed_images,
        })

    return posts


def get_posting_windows() -> dict:
    """Returns {account: (window_start_hour, window_end_hour)} parsed from crontab."""
    try:
        result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        lines = result.stdout.splitlines()
    except Exception:
        return {}

    # Map config filename -> cron window
    config_windows = {}
    for line in lines:
        if "bikesharebots" not in line:
            continue
        parts = line.strip().split()
        if len(parts) < 5:
            continue
        try:
            hour = int(parts[1])
        except ValueError:
            continue
        delay_hours = 0
        m = re.search(r'RANDOM\s*%\s*(\d+)', line)
        if m:
            delay_hours = int(m.group(1)) // 3600
        m = re.search(r'configs/(\S+\.json)', line)
        if m:
            config_windows[m.group(1)] = (hour, hour + delay_hours)

    # Map account -> union of windows and config count across all its configs
    account_windows = {}
    account_counts = {}
    for config_file in glob("configs/*.json"):
        with open(config_file) as f:
            cfg = json.load(f)
        config_name = os.path.basename(config_file)
        account = cfg.get("account")
        if not account or config_name not in config_windows:
            continue
        start, end = config_windows[config_name]
        account_counts[account] = account_counts.get(account, 0) + 1
        if account not in account_windows:
            account_windows[account] = (start, end)
        else:
            ex_start, ex_end = account_windows[account]
            account_windows[account] = (min(ex_start, start), max(ex_end, end))

    return account_windows, account_counts


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, refresh: bool = False):
    creds = load_credentials()
    now = time.time()
    today = datetime.now().date()
    posting_windows, posting_counts = get_posting_windows()
    accounts = {}

    def fmt_h(h):
        return datetime.now().replace(hour=h, minute=0).strftime("%-I:%M %p")

    for handle, password in creds["bsky_passwords"].items():
        cached = _cache.get(handle)
        if refresh or not cached or (now - cached["ts"]) > CACHE_TTL:
            try:
                posts = fetch_account_data(handle, password)
                _cache[handle] = {"ts": now, "posts": posts, "error": None}
            except Exception as e:
                _cache[handle] = {"ts": now, "posts": [], "error": str(e)}

        entry = _cache[handle]
        posts = entry["posts"]
        expected = posting_counts.get(handle, 1)
        posts_today = sum(1 for p in posts if p["date"] == today)

        window = posting_windows.get(handle)
        window_str = f"{fmt_h(window[0])}–{fmt_h(window[1])}" if window else None

        accounts[handle] = {
            **entry,
            "last_post": posts[0] if posts else None,
            "posts_today": posts_today,
            "expected": expected,
            "window_str": window_str,
        }

    yesterday = today - timedelta(days=1)
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"accounts": accounts, "today": today, "yesterday": yesterday},
    )


if __name__ == "__main__":
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser()
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload (development)")
    args = parser.parse_args()

    uvicorn.run("dashboard:app", host="0.0.0.0", port=8000, reload=args.reload)

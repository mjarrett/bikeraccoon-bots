import json
import pathlib
import pandas as pd
import requests
import datetime as dt

VISUAL_CROSSING_KEY = ''
CACHE_DIR = pathlib.Path('.weather_cache')


def _day_cache_path(lat, lon, date_str, freq_key):
    return CACHE_DIR / f'{lat:.4f}_{lon:.4f}_{date_str}_{freq_key}.json'


def _date_range(day1, day2):
    dates = []
    d = day1.replace(hour=0, minute=0, second=0, microsecond=0)
    end = day2.replace(hour=0, minute=0, second=0, microsecond=0)
    while d <= end:
        dates.append(d)
        d += dt.timedelta(days=1)
    return dates


def get_weather_range(api, freq, day1, day2=None):
    sdf = api.get_stations()
    lat = sdf['lat'].mean()
    lon = sdf['lon'].mean()

    if day2 is None:
        day2 = day1
    elif day2 < day1:
        day1, day2 = day2, day1

    freq_key = 'days' if freq == 'daily' else 'hours'
    dates = _date_range(day1, day2)

    missing = [d for d in dates if not _day_cache_path(lat, lon, d.strftime('%Y-%m-%d'), freq_key).exists()]

    if missing:
        miss_start = missing[0].strftime('%Y-%m-%d')
        miss_end = missing[-1].strftime('%Y-%m-%d')
        url = (
            f'https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/'
            f'{lat}%2C{lon}/{miss_start}/{miss_end}'
            f'?unitGroup=metric&key={VISUAL_CROSSING_KEY}&contentType=json&include={freq_key}'
        )
        r = requests.get(url)
        if not r.ok:
            raise RuntimeError(f"Weather API error {r.status_code}: {r.text.strip()}")
        CACHE_DIR.mkdir(exist_ok=True)
        for day_data in r.json()['days']:
            date_str = dt.datetime.fromtimestamp(day_data['datetimeEpoch'], dt.UTC).strftime('%Y-%m-%d')
            _day_cache_path(lat, lon, date_str, freq_key).write_text(json.dumps(day_data))

    days_data = [
        json.loads(_day_cache_path(lat, lon, d.strftime('%Y-%m-%d'), freq_key).read_text())
        for d in dates
    ]

    if freq == 'daily':
        df = pd.DataFrame(days_data)
        df.index = [dt.datetime.fromtimestamp(x, dt.UTC) for x in df['datetimeEpoch']]
    elif freq == 'hourly':
        df = pd.concat([pd.DataFrame(day['hours']) for day in days_data])
        df.index = [dt.datetime.fromtimestamp(x, dt.UTC) for x in df['datetimeEpoch']]

    df.index = df.index.tz_convert(api.info['tz'])
    return df

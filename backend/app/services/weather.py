"""Weather for one hiking day: Open-Meteo hourly forecast plus sunrise/sunset.

All datetimes in this module are timezone-aware UTC. Converting to UK local
time (BST/GMT) is the caller's job (see planning.py).
"""

from datetime import date, datetime, timedelta, timezone

import httpx
from astral import Observer
from astral.sun import sun
from pydantic import BaseModel

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
HOURLY_FIELDS = (
    "temperature_2m,precipitation,precipitation_probability,"
    "wind_speed_10m,wind_gusts_10m,weather_code"
)
# Open-Meteo serves today plus 15 more days (16 in total).
MAX_DAYS_AHEAD = 15
HTTP_TIMEOUT_S = 10.0

# WMO weather interpretation codes, as listed in the Open-Meteo docs.
WMO_CODE_TEXT: dict[int, str] = {
    0: "clear sky",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "fog",
    48: "freezing fog",
    51: "light drizzle",
    53: "moderate drizzle",
    55: "heavy drizzle",
    56: "light freezing drizzle",
    57: "heavy freezing drizzle",
    61: "light rain",
    63: "moderate rain",
    65: "heavy rain",
    66: "light freezing rain",
    67: "heavy freezing rain",
    71: "light snow",
    73: "moderate snow",
    75: "heavy snow",
    77: "snow grains",
    80: "light rain showers",
    81: "moderate rain showers",
    82: "violent rain showers",
    85: "light snow showers",
    86: "heavy snow showers",
    95: "thunderstorm",
    96: "thunderstorm with light hail",
    99: "thunderstorm with heavy hail",
}


class WeatherError(Exception):
    """Raised when Open-Meteo cannot be reached or returns a bad response."""


class HourlyWeather(BaseModel):
    """Forecast for one hour, starting at `time` (UTC)."""

    time: datetime
    temp_c: float
    precip_mm: float
    precip_prob: int | None
    wind_kmh: float
    gust_kmh: float
    code: int


class DayForecast(BaseModel):
    """Everything the planner needs to know about the weather on one day."""

    day: date
    lat: float
    lon: float
    sunrise: datetime
    sunset: datetime
    hourly: list[HourlyWeather]
    in_forecast_range: bool
    source_url: str
    fetched_at: datetime
    # URLs of neighbouring days merged in by merge_forecasts (midnight hikes).
    extra_source_urls: list[str] = []


def weather_code_text(code: int) -> str:
    """Turn a WMO weather code (e.g. 61) into plain English ("light rain")."""
    return WMO_CODE_TEXT.get(code, f"unknown weather (code {code})")


def sun_times(lat: float, lon: float, day: date) -> tuple[datetime, datetime]:
    """Return (sunrise, sunset) in UTC for a place and date.

    Computed locally with `astral`, so it works for any date, even one far
    beyond the forecast range.
    """
    times = sun(Observer(latitude=lat, longitude=lon), date=day, tzinfo=timezone.utc)
    return times["sunrise"], times["sunset"]


def today_utc() -> date:
    """Today's date in UTC (a separate function so tests can replace it)."""
    return datetime.now(timezone.utc).date()


def is_in_forecast_range(day: date, today: date | None = None) -> bool:
    """True if Open-Meteo has a forecast for `day` (today up to 15 days ahead)."""
    if today is None:
        today = today_utc()
    return today <= day <= today + timedelta(days=MAX_DAYS_AHEAD)


def build_forecast_url(lat: float, lon: float, day: date) -> str:
    """Build the exact Open-Meteo URL we call, so it can be cited as a source."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": HOURLY_FIELDS,
        "timezone": "UTC",
        "start_date": day.isoformat(),
        "end_date": day.isoformat(),
    }
    return str(httpx.URL(OPEN_METEO_URL, params=params))


def fetch_open_meteo(url: str) -> dict:
    """GET the Open-Meteo URL and return the JSON body.

    Raises WeatherError with a readable message on timeouts, network errors
    and non-2xx responses.
    """
    try:
        with httpx.Client(timeout=HTTP_TIMEOUT_S) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:
        raise WeatherError(
            f"Open-Meteo returned HTTP {exc.response.status_code} for {url}"
        ) from exc
    except httpx.HTTPError as exc:
        raise WeatherError(f"Could not reach Open-Meteo at {url}: {exc}") from exc
    except ValueError as exc:
        raise WeatherError(f"Open-Meteo returned invalid JSON for {url}") from exc


def parse_hourly(payload: dict) -> list[HourlyWeather]:
    """Convert Open-Meteo's column-style `hourly` block into a list of hours.

    Open-Meteo sends one list per variable, e.g. {"time": [...],
    "temperature_2m": [...]}. Hours with a missing (null) required value are
    skipped; a missing precipitation probability is kept as None.
    """
    try:
        block = payload["hourly"]
        columns = zip(
            block["time"],
            block["temperature_2m"],
            block["precipitation"],
            block["precipitation_probability"],
            block["wind_speed_10m"],
            block["wind_gusts_10m"],
            block["weather_code"],
        )
    except (KeyError, TypeError) as exc:
        raise WeatherError(f"Open-Meteo response is missing hourly data: {exc}") from exc

    hours: list[HourlyWeather] = []
    for time_str, temp, precip, prob, wind, gust, code in columns:
        if None in (temp, precip, wind, gust, code):
            continue
        # timezone=UTC was requested, so the naive ISO times are UTC.
        when = datetime.fromisoformat(time_str).replace(tzinfo=timezone.utc)
        hours.append(
            HourlyWeather(
                time=when,
                temp_c=temp,
                precip_mm=precip,
                precip_prob=None if prob is None else int(prob),
                wind_kmh=wind,
                gust_kmh=gust,
                code=int(code),
            )
        )
    return hours


def get_day_forecast(lat: float, lon: float, day: date) -> DayForecast:
    """Get the hourly forecast and sunrise/sunset for one place and day.

    If `day` is in the past or more than 15 days ahead, no HTTP call is made:
    `hourly` is empty and `in_forecast_range` is False. Sunrise and sunset
    are always filled in from `sun_times`.
    """
    sunrise, sunset = sun_times(lat, lon, day)
    url = build_forecast_url(lat, lon, day)
    in_range = is_in_forecast_range(day)
    hourly = parse_hourly(fetch_open_meteo(url)) if in_range else []
    return DayForecast(
        day=day,
        lat=lat,
        lon=lon,
        sunrise=sunrise,
        sunset=sunset,
        hourly=hourly,
        in_forecast_range=in_range,
        source_url=url,
        fetched_at=datetime.now(timezone.utc),
    )


def utc_days_between(start_utc: datetime, end_utc: datetime) -> list[date]:
    """List every UTC date that a hike from start_utc to end_utc touches.

    Open-Meteo answers one UTC date per call, so a hike from 23:30 to 02:30
    UTC needs two calls. A hike ending exactly at midnight stays on one day.
    """
    last = (end_utc - timedelta(microseconds=1)).date() if end_utc > start_utc else start_utc.date()
    days = [start_utc.date()]
    while days[-1] < last:
        days.append(days[-1] + timedelta(days=1))
    return days


def merge_forecasts(main: DayForecast, others: list[DayForecast]) -> DayForecast:
    """Add the hourly data of neighbouring days to the hike day's forecast.

    Day, sunrise, sunset and in_forecast_range stay those of `main` (the hike
    day). Hours are sorted by time and an hour already in `main` is kept.
    """
    by_time = {h.time: h for other in others for h in other.hourly}
    by_time.update({h.time: h for h in main.hourly})
    extra_urls = [other.source_url for other in others if other.hourly]
    return main.model_copy(
        update={
            "hourly": [by_time[t] for t in sorted(by_time)],
            "extra_source_urls": main.extra_source_urls + extra_urls,
        }
    )


def get_hike_forecast(
    lat: float, lon: float, day: date, start_utc: datetime, end_utc: datetime
) -> DayForecast:
    """Get the forecast for a hike, fetching a neighbouring day if needed.

    `day` is the hike's local date (it sets sunrise/sunset). If the hike runs
    into another UTC date (e.g. a night hike), that day is fetched too and
    merged in, so every hour of the hike can be checked.
    """
    main = get_day_forecast(lat, lon, day)
    others = [get_day_forecast(lat, lon, d) for d in utc_days_between(start_utc, end_utc) if d != day]
    return merge_forecasts(main, others) if others else main

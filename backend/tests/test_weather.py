"""Tests for app.services.weather. Open-Meteo is mocked with respx (no network)."""

from datetime import date, datetime, timezone

import httpx
import pytest
import respx

from app.services import weather
from app.services.weather import (
    OPEN_METEO_URL,
    WeatherError,
    get_day_forecast,
    get_hike_forecast,
    is_in_forecast_range,
    merge_forecasts,
    sun_times,
    utc_days_between,
    weather_code_text,
)

LAT, LON = 51.5074, -0.1278  # central London
TODAY = date(2026, 10, 24)
HIKE_DAY = date(2026, 10, 31)


def open_meteo_payload(day: date) -> dict:
    """A synthetic response shaped like Open-Meteo's documented JSON (24 hours, UTC)."""
    hours = [f"{day.isoformat()}T{h:02d}:00" for h in range(24)]
    return {
        "latitude": 51.5,
        "longitude": -0.12,
        "generationtime_ms": 0.08,
        "utc_offset_seconds": 0,
        "timezone": "UTC",
        "timezone_abbreviation": "UTC",
        "elevation": 23.0,
        "hourly_units": {
            "time": "iso8601",
            "temperature_2m": "°C",
            "precipitation": "mm",
            "precipitation_probability": "%",
            "wind_speed_10m": "km/h",
            "wind_gusts_10m": "km/h",
            "weather_code": "wmo code",
        },
        "hourly": {
            "time": hours,
            "temperature_2m": [6.0 + 0.4 * h for h in range(24)],
            "precipitation": [0.0] * 12 + [0.4] * 6 + [0.0] * 6,
            # Open-Meteo can send null; the parser keeps it as None.
            "precipitation_probability": [None] + [10] * 11 + [65] * 6 + [20] * 6,
            "wind_speed_10m": [12.0] * 24,
            "wind_gusts_10m": [25.0] * 24,
            "weather_code": [3] * 12 + [61] * 6 + [2] * 6,
        },
    }


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    """Pin 'today' so forecast-range logic is deterministic."""
    monkeypatch.setattr(weather, "today_utc", lambda: TODAY)


@respx.mock
def test_get_day_forecast_parses_open_meteo():
    route = respx.get(url__startswith=OPEN_METEO_URL).mock(
        return_value=httpx.Response(200, json=open_meteo_payload(HIKE_DAY))
    )
    fc = get_day_forecast(LAT, LON, HIKE_DAY)

    assert route.call_count == 1
    assert fc.in_forecast_range is True
    assert fc.source_url == str(route.calls.last.request.url)
    assert len(fc.hourly) == 24
    first, rainy = fc.hourly[0], fc.hourly[12]
    assert first.time == datetime(2026, 10, 31, 0, 0, tzinfo=timezone.utc)
    assert first.precip_prob is None
    assert first.temp_c == 6.0
    assert rainy.precip_prob == 65
    assert rainy.precip_mm == 0.4
    assert rainy.code == 61
    assert rainy.gust_kmh == 25.0
    assert (fc.sunrise, fc.sunset) == sun_times(LAT, LON, HIKE_DAY)
    assert fc.fetched_at.tzinfo is not None


@respx.mock
def test_request_uses_spec_query_params():
    route = respx.get(url__startswith=OPEN_METEO_URL).mock(
        return_value=httpx.Response(200, json=open_meteo_payload(HIKE_DAY))
    )
    get_day_forecast(LAT, LON, HIKE_DAY)
    params = route.calls.last.request.url.params
    assert params["hourly"] == (
        "temperature_2m,precipitation,precipitation_probability,"
        "wind_speed_10m,wind_gusts_10m,weather_code"
    )
    assert params["timezone"] == "UTC"
    assert params["start_date"] == params["end_date"] == "2026-10-31"
    assert params["latitude"] == str(LAT)
    assert params["longitude"] == str(LON)


@pytest.mark.parametrize("day", [date(2026, 10, 23), date(2026, 11, 9), date(2027, 6, 1)])
@respx.mock
def test_out_of_range_day_makes_no_http_call(day):
    route = respx.get(url__startswith=OPEN_METEO_URL).mock(
        return_value=httpx.Response(200, json=open_meteo_payload(day))
    )
    fc = get_day_forecast(LAT, LON, day)
    assert route.call_count == 0
    assert fc.in_forecast_range is False
    assert fc.hourly == []
    # Daylight still works for any date.
    assert fc.sunrise < fc.sunset


def test_forecast_range_boundaries():
    assert is_in_forecast_range(date(2026, 10, 24), TODAY)  # today
    assert is_in_forecast_range(date(2026, 11, 8), TODAY)  # today + 15
    assert not is_in_forecast_range(date(2026, 11, 9), TODAY)  # today + 16
    assert not is_in_forecast_range(date(2026, 10, 23), TODAY)  # yesterday


@respx.mock
def test_http_error_raises_weather_error():
    respx.get(url__startswith=OPEN_METEO_URL).mock(return_value=httpx.Response(500))
    with pytest.raises(WeatherError, match="HTTP 500"):
        get_day_forecast(LAT, LON, HIKE_DAY)


@respx.mock
def test_timeout_raises_weather_error():
    respx.get(url__startswith=OPEN_METEO_URL).mock(side_effect=httpx.ConnectTimeout("slow"))
    with pytest.raises(WeatherError, match="Could not reach"):
        get_day_forecast(LAT, LON, HIKE_DAY)


@respx.mock
def test_missing_hourly_block_raises_weather_error():
    respx.get(url__startswith=OPEN_METEO_URL).mock(
        return_value=httpx.Response(200, json={"latitude": 51.5})
    )
    with pytest.raises(WeatherError, match="missing hourly"):
        get_day_forecast(LAT, LON, HIKE_DAY)


@respx.mock
def test_hours_with_null_required_values_are_skipped():
    payload = open_meteo_payload(HIKE_DAY)
    payload["hourly"]["temperature_2m"][5] = None
    respx.get(url__startswith=OPEN_METEO_URL).mock(return_value=httpx.Response(200, json=payload))
    fc = get_day_forecast(LAT, LON, HIKE_DAY)
    assert len(fc.hourly) == 23
    assert all(h.time.hour != 5 for h in fc.hourly)


def test_sun_times_london_late_october():
    sunrise, sunset = sun_times(LAT, LON, date(2026, 10, 31))
    assert sunrise < sunset
    for t in (sunrise, sunset):
        assert t.utcoffset().total_seconds() == 0
        assert t.date() == date(2026, 10, 31)
        assert 6 <= t.hour < 18


def test_weather_code_text():
    assert weather_code_text(0) == "clear sky"
    assert weather_code_text(61) == "light rain"
    assert weather_code_text(95) == "thunderstorm"
    assert weather_code_text(42) == "unknown weather (code 42)"


def utc(day: date, hour: int, minute: int = 0) -> datetime:
    """A UTC datetime on `day`, for building hike windows in tests."""
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=timezone.utc)


def payload_for_request(request: httpx.Request) -> httpx.Response:
    """Answer each mocked call with the day it asked for (start_date)."""
    day = date.fromisoformat(request.url.params["start_date"])
    return httpx.Response(200, json=open_meteo_payload(day))


def test_utc_days_between_one_and_two_days():
    prev_day = date(2026, 10, 30)
    assert utc_days_between(utc(HIKE_DAY, 9), utc(HIKE_DAY, 12)) == [HIKE_DAY]
    assert utc_days_between(utc(prev_day, 23, 30), utc(HIKE_DAY, 2, 30)) == [prev_day, HIKE_DAY]
    # Ending exactly at midnight needs no extra day.
    assert utc_days_between(utc(prev_day, 21), utc(HIKE_DAY, 0)) == [prev_day]


@respx.mock
def test_hike_forecast_single_day_makes_one_call():
    route = respx.get(url__startswith=OPEN_METEO_URL).mock(side_effect=payload_for_request)
    fc = get_hike_forecast(LAT, LON, HIKE_DAY, utc(HIKE_DAY, 9), utc(HIKE_DAY, 13))
    assert route.call_count == 1
    assert len(fc.hourly) == 24
    assert fc.extra_source_urls == []


@respx.mock
def test_hike_forecast_crossing_midnight_merges_both_days():
    # Starts 23:00 UTC on the 31st, ends 02:00 UTC on 1 Nov.
    next_day = date(2026, 11, 1)
    route = respx.get(url__startswith=OPEN_METEO_URL).mock(side_effect=payload_for_request)
    fc = get_hike_forecast(LAT, LON, HIKE_DAY, utc(HIKE_DAY, 23), utc(next_day, 2))

    assert route.call_count == 2
    asked = [call.request.url.params["start_date"] for call in route.calls]
    assert asked == ["2026-10-31", "2026-11-01"]
    assert len(fc.hourly) == 48
    assert fc.hourly[0].time == utc(HIKE_DAY, 0)
    assert fc.hourly[-1].time == utc(next_day, 23)
    # The hike day still sets the daylight and the main source.
    assert fc.day == HIKE_DAY
    assert (fc.sunrise, fc.sunset) == sun_times(LAT, LON, HIKE_DAY)
    assert fc.source_url == str(route.calls[0].request.url)
    assert fc.extra_source_urls == [str(route.calls[1].request.url)]


@respx.mock
def test_neighbour_day_out_of_range_adds_no_hours():
    # Hike day is today + 15; the next UTC day is out of range, so no call for it.
    last_day, beyond = date(2026, 11, 8), date(2026, 11, 9)
    route = respx.get(url__startswith=OPEN_METEO_URL).mock(side_effect=payload_for_request)
    fc = get_hike_forecast(LAT, LON, last_day, utc(last_day, 23), utc(beyond, 1))
    assert route.call_count == 1
    assert len(fc.hourly) == 24
    assert fc.extra_source_urls == []


@respx.mock
def test_merge_keeps_main_hour_when_both_have_it():
    respx.get(url__startswith=OPEN_METEO_URL).mock(side_effect=payload_for_request)
    main = get_day_forecast(LAT, LON, HIKE_DAY)
    clash = main.model_copy(update={"hourly": [main.hourly[0].model_copy(update={"gust_kmh": 99.0})]})
    merged = merge_forecasts(main, [clash])
    assert len(merged.hourly) == 24
    assert merged.hourly[0].gust_kmh == 25.0

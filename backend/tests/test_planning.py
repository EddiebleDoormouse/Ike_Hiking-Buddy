"""Tests for app.services.planning. Pure maths: no network, no LLM."""

from datetime import date, datetime, time, timedelta, timezone

import pytest

from app.services.planning import (
    Check,
    Hazard,
    KitItem,
    PlanDraft,
    all_passed,
    failed_summary,
    leave_by,
    local_start_to_utc,
    missing_window_hours,
    naismith_minutes,
    run_checks,
    window_hours,
)
from app.services.weather import DayForecast, HourlyWeather, sun_times

LAT, LON = 51.5074, -0.1278
GMT_DAY = date(2026, 10, 31)  # after the clock change: local time == UTC
DIST_KM, ASCENT_M = 10.0, 600.0  # Naismith: 180 min


def make_forecast(
    day: date = GMT_DAY,
    temp: float = 8.0,
    gust: float = 20.0,
    prob: int | None = 10,
    overrides: dict[int, dict] | None = None,
    in_range: bool = True,
    drop_hours: frozenset[int] = frozenset(),
) -> DayForecast:
    """Synthetic 24-hour forecast; `overrides` changes fields for given UTC hours.

    `drop_hours` removes hours, like parse_hourly does when Open-Meteo sends null.
    """
    overrides = overrides or {}
    sunrise, sunset = sun_times(LAT, LON, day)
    hourly = []
    if in_range:
        for h in range(24):
            if h in drop_hours:
                continue
            fields = {"temp_c": temp, "gust_kmh": gust, "precip_prob": prob}
            fields.update(overrides.get(h, {}))
            hourly.append(
                HourlyWeather(
                    time=datetime(day.year, day.month, day.day, h, tzinfo=timezone.utc),
                    precip_mm=0.0,
                    wind_kmh=10.0,
                    code=3,
                    **fields,
                )
            )
    return DayForecast(
        day=day,
        lat=LAT,
        lon=LON,
        sunrise=sunrise,
        sunset=sunset,
        hourly=hourly,
        in_forecast_range=in_range,
        source_url="https://api.open-meteo.com/v1/forecast?test",
        fetched_at=datetime(2026, 10, 24, 12, tzinfo=timezone.utc),
    )


def make_draft(
    start: time = time(9, 0),
    est: int = 180,
    kit: list[str] | None = None,
    hazards: list[Hazard] | None = None,
) -> PlanDraft:
    """Synthetic plan draft that passes every check by default."""
    kit_items = [KitItem(item=name, reason="test") for name in (kit or ["Waterproof jacket"])]
    if hazards is None:
        hazards = [Hazard(text="Muddy path", source_url="https://example.org/mud", source_title="Trail notice")]
    return PlanDraft(
        summary_md="Test plan", start_time_local=start, est_duration_min=est, kit=kit_items, hazards=hazards
    )


def check_named(checks: list[Check], name: str) -> Check:
    """Pick one check out of run_checks' result by its name."""
    return next(c for c in checks if c.name == name)


def run(draft: PlanDraft | None = None, forecast: DayForecast | None = None) -> list[Check]:
    """run_checks with the default 10 km / 600 m route."""
    return run_checks(draft or make_draft(), forecast or make_forecast(), DIST_KM, ASCENT_M)


# --- maths -----------------------------------------------------------------


def test_naismith_10km_600m_is_180_min():
    assert naismith_minutes(10, 600) == 180


def test_naismith_pace_factor_and_flat():
    assert naismith_minutes(10, 600, pace_factor=1.2) == 216
    assert naismith_minutes(15, 0) == 180
    assert naismith_minutes(0, 0) == 0


def test_leave_by_maths():
    sunset = datetime(2026, 10, 31, 16, 35, tzinfo=timezone.utc)
    assert leave_by(sunset, 180) == datetime(2026, 10, 31, 12, 35, tzinfo=timezone.utc)
    assert leave_by(sunset, 180, buffer_min=30) == datetime(2026, 10, 31, 13, 5, tzinfo=timezone.utc)
    assert leave_by(sunset, 0, buffer_min=0) == sunset


def test_window_hours_covers_partial_hours():
    start = datetime(2026, 10, 31, 9, 30, tzinfo=timezone.utc)
    hours = window_hours(make_forecast(), start, 105)  # 09:30 -> 11:15
    assert [h.time.hour for h in hours] == [9, 10, 11]


def test_window_hours_empty_when_no_forecast():
    start = datetime(2026, 10, 31, 9, tzinfo=timezone.utc)
    assert window_hours(make_forecast(in_range=False), start, 180) == []


# --- default draft passes everything --------------------------------------------


def test_good_plan_passes_all_checks():
    checks = run()
    assert [c.name for c in checks] == [
        "Finish before dark",
        "Duration realistic",
        "Wind",
        "Rain",
        "Cold",
        "Sources cited",
        "Forecast available",
    ]
    assert all_passed(checks), failed_summary(checks)
    assert failed_summary(checks) == ""
    for c in checks:
        assert c.detail.endswith(".")
        assert any(ch.isdigit() for ch in c.detail)


# --- 1 Finish before dark ------------------------------------------------------


def test_finish_before_dark_pass_and_detail():
    check = check_named(run(), "Finish before dark")
    assert check.passed
    # London sunset on 31 Oct is about 16:35 GMT, so latest start is about 12:35.
    assert "09:00 GMT" in check.detail and "12:00 GMT" in check.detail
    assert "latest safe start is 12:3" in check.detail


def test_finish_before_dark_fail_late_start():
    check = check_named(run(make_draft(start=time(14, 0))), "Finish before dark")
    assert not check.passed
    assert "17:00 GMT" in check.detail and "after sunset" in check.detail


def test_finish_before_dark_uses_naismith_when_draft_is_optimistic():
    # Draft says 140 min (within 25%), but Naismith's 180 min is used for safety.
    # Starting 200 min before sunset: 140 min would leave 60 min spare, 180 leaves 20.
    sunset = make_forecast().sunset
    start_local = (sunset - timedelta(minutes=200)).time().replace(second=0, microsecond=0)
    check = check_named(run(make_draft(start=start_local, est=140)), "Finish before dark")
    assert not check.passed
    assert "3 h 00 min" in check.detail


# --- 2 Duration realistic ------------------------------------------------------


@pytest.mark.parametrize("est, passed", [(180, True), (225, True), (135, True), (226, False), (130, False)])
def test_duration_realistic(est, passed):
    check = check_named(run(make_draft(est=est)), "Duration realistic")
    assert check.passed is passed
    assert "180 min" in check.detail and "135-225 min" in check.detail


# --- 3 Wind ----------------------------------------------------------------


def test_wind_pass_below_limit():
    check = check_named(run(forecast=make_forecast(gust=49.0)), "Wind")
    assert check.passed and "49 km/h" in check.detail


def test_wind_fail_at_limit_inside_window():
    check = check_named(run(forecast=make_forecast(overrides={10: {"gust_kmh": 50.0}})), "Wind")
    assert not check.passed and "50 km/h" in check.detail


def test_wind_ignores_gusts_outside_window():
    check = check_named(run(forecast=make_forecast(overrides={20: {"gust_kmh": 90.0}})), "Wind")
    assert check.passed


# --- 4 Rain ----------------------------------------------------------------


def test_rain_pass_below_limit():
    check = check_named(run(forecast=make_forecast(prob=69)), "Rain")
    assert check.passed and "69%" in check.detail


def test_rain_fail_at_limit():
    check = check_named(run(forecast=make_forecast(overrides={11: {"precip_prob": 70}})), "Rain")
    assert not check.passed and "70%" in check.detail


def test_rain_ignores_missing_probabilities():
    forecast = make_forecast(overrides={9: {"precip_prob": None}, 10: {"precip_prob": 30}})
    check = check_named(run(forecast=forecast), "Rain")
    assert check.passed and "30%" in check.detail


# --- 5 Cold ----------------------------------------------------------------


def test_cold_pass_when_above_freezing():
    check = check_named(run(forecast=make_forecast(temp=0.5)), "Cold")
    assert check.passed and "0.5 °C" in check.detail


def test_cold_fail_when_freezing_without_kit():
    check = check_named(run(forecast=make_forecast(overrides={9: {"temp_c": -1.0}})), "Cold")
    assert not check.passed and "-1.0 °C" in check.detail and "has no" in check.detail


@pytest.mark.parametrize("item", ["Warm gloves", "Wool hat", "Insulated jacket", "Thermal base layer"])
def test_cold_pass_when_freezing_with_cold_kit(item):
    draft = make_draft(kit=["Waterproof jacket", item])
    check = check_named(run(draft, make_forecast(temp=-2.0)), "Cold")
    assert check.passed and "includes" in check.detail


def test_cold_kit_match_is_whole_word():
    draft = make_draft(kit=["Chatterbox walkie-talkie"])  # contains "hat" but isn't one
    assert not check_named(run(draft, make_forecast(temp=-2.0)), "Cold").passed


# --- 6 Sources cited ------------------------------------------------------------


def test_sources_cited_pass_with_no_hazards():
    check = check_named(run(make_draft(hazards=[])), "Sources cited")
    assert check.passed and "0 hazards" in check.detail


def test_sources_cited_fail_when_one_is_missing():
    hazards = [
        Hazard(text="Muddy path", source_url="https://example.org/mud", source_title="Notice"),
        Hazard(text="Bridge closed", source_url=None, source_title=None),
        Hazard(text="Cattle in field", source_url="trust me", source_title=None),
    ]
    check = check_named(run(make_draft(hazards=hazards)), "Sources cited")
    assert not check.passed
    assert "2 of 3" in check.detail and "Bridge closed" in check.detail


# --- 7 Forecast available ------------------------------------------------------


def test_forecast_available_pass():
    check = check_named(run(), "Forecast available")
    assert check.passed and "24 hours" in check.detail


def test_forecast_not_available_fails_with_message():
    checks = run(forecast=make_forecast(in_range=False))
    check = check_named(checks, "Forecast available")
    assert not check.passed
    assert check.detail == "Forecast not available yet for 2026-10-31; re-check within 7 days of the hike."
    # With no hourly data, weather checks fail rather than silently pass.
    assert not check_named(checks, "Wind").passed
    assert not check_named(checks, "Rain").passed


# --- summary helpers ------------------------------------------------------------


def test_failed_summary_lists_only_failures():
    checks = run(make_draft(start=time(14, 0)), make_forecast(gust=60.0))
    assert not all_passed(checks)
    lines = failed_summary(checks).splitlines()
    assert len(lines) == 2
    assert lines[0].startswith("- Finish before dark: ")
    assert lines[1].startswith("- Wind: ")


# --- UK clock change (BST -> GMT at 01:00 UTC on Sun 25 Oct 2026) ------------------


def test_local_start_respects_bst_and_gmt():
    assert local_start_to_utc(date(2026, 10, 24), time(9, 0)) == datetime(2026, 10, 24, 8, 0, tzinfo=timezone.utc)
    assert local_start_to_utc(date(2026, 10, 25), time(9, 0)) == datetime(2026, 10, 25, 9, 0, tzinfo=timezone.utc)


def test_hike_spanning_clock_change():
    # Night hike: 00:30 BST (23:30 UTC on the 24th) for 3 h. Clocks go back at
    # 02:00 BST, so it ends at 02:30 GMT, not 03:30.
    day = date(2026, 10, 25)
    checks = run(make_draft(start=time(0, 30)), make_forecast(day=day, overrides={2: {"gust_kmh": 55.0}}))
    dark = check_named(checks, "Finish before dark")
    assert "00:30 BST" in dark.detail and "02:30 GMT" in dark.detail
    assert dark.passed
    start_utc = local_start_to_utc(day, time(0, 30))
    assert [h.time.hour for h in window_hours(make_forecast(day=day), start_utc, 180)] == [0, 1, 2]
    # The 23:00 UTC hour on the 24th is not in the 25th's forecast, so weather checks fail.
    wind = check_named(checks, "Wind")
    assert not wind.passed and "missing 1 of 4 hours" in wind.detail


def test_finish_before_dark_on_clock_change_day_uses_gmt():
    # 25 Oct sunset is about 16:42 GMT. Start 13:00 local (= 13:00 UTC) + 3 h ends
    # at 16:00, under 60 min before sunset, so it fails. A fixed +01:00 offset
    # would wrongly start at 12:00 UTC and pass.
    day = date(2026, 10, 25)
    check = check_named(run(make_draft(start=time(13, 0)), make_forecast(day=day)), "Finish before dark")
    assert not check.passed
    assert "13:00 GMT" in check.detail and "16:00 GMT" in check.detail


# --- forecast coverage gaps (unchecked hours must not count as safe) ------------------


def test_missing_window_hours_lists_gaps():
    start = datetime(2026, 10, 31, 9, 30, tzinfo=timezone.utc)
    assert missing_window_hours(make_forecast(), start, 105) == []
    gaps = missing_window_hours(make_forecast(drop_hours=frozenset({10})), start, 105)
    assert gaps == [datetime(2026, 10, 31, 10, tzinfo=timezone.utc)]


def test_null_hour_inside_window_fails_weather_checks():
    checks = run(forecast=make_forecast(drop_hours=frozenset({10})))  # 09:00-12:00 hike
    for name in ("Wind", "Rain", "Cold"):
        check = check_named(checks, name)
        assert not check.passed
        assert "missing 1 of 3 hours" in check.detail and "10:00 UTC on 2026-10-31" in check.detail


def test_null_hour_outside_window_is_ignored():
    checks = run(forecast=make_forecast(drop_hours=frozenset({20})))
    assert all_passed(checks), failed_summary(checks)


def test_hike_crossing_utc_midnight_fails_weather_checks():
    # 00:30 BST on 24 Oct is 23:30 UTC on the 23rd, which the 24th's forecast lacks.
    day = date(2026, 10, 24)
    checks = run(make_draft(start=time(0, 30)), make_forecast(day=day))
    wind = check_named(checks, "Wind")
    assert not wind.passed
    assert "missing 1 of 4 hours" in wind.detail and "23:00 UTC on 2026-10-23" in wind.detail
    assert not check_named(checks, "Rain").passed


def test_cold_kit_still_passes_cold_check_with_gaps():
    draft = make_draft(kit=["Warm gloves"])
    check = check_named(run(draft, make_forecast(drop_hours=frozenset({10}))), "Cold")
    assert check.passed

"""Planning maths and the automatic checks run on every LLM plan draft.

No LLM here: these are plain, testable rules. The planner loop (plan_hike)
calls `run_checks`, and if anything fails it sends `failed_summary` back to
the LLM for a revision.

Times: forecasts are in UTC; the draft's start time is UK local time. We
convert with zoneinfo("Europe/London") so the BST -> GMT clock change
(Sun 25 Oct 2026) is handled correctly. Never use a fixed +01:00 offset.
"""

import re
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from pydantic import BaseModel

from app.services.weather import DayForecast, HourlyWeather

# Thresholds for run_checks. Change them here, not inside the checks.
FINISH_BUFFER_MIN = 60
DURATION_TOLERANCE = 0.25
MAX_GUST_KMH = 50.0
MAX_PRECIP_PROB = 70
MIN_TEMP_C = 0.0
COLD_KIT_PATTERN = re.compile(r"\b(gloves?|hats?|insulated|thermals?)\b", re.IGNORECASE)

# Naismith's rule: 5 km per hour on the flat, plus 1 hour per 600 m of ascent.
NAISMITH_KM_PER_HOUR = 5.0
NAISMITH_ASCENT_M_PER_HOUR = 600.0


class Hazard(BaseModel):
    """A hazard or closure claim, with the source that backs it up."""

    text: str
    source_url: str | None
    source_title: str | None


class KitItem(BaseModel):
    """One line of the kit checklist; `done` is ticked by the user in the UI."""

    item: str
    reason: str
    done: bool = False


class PlanDraft(BaseModel):
    """A plan as drafted (or revised) by the LLM, before checks."""

    summary_md: str
    start_time_local: time
    est_duration_min: int
    kit: list[KitItem]
    hazards: list[Hazard]
    notes: list[str] = []


class Check(BaseModel):
    """The result of one automatic check, shown in the verification panel."""

    name: str
    passed: bool
    detail: str


def naismith_minutes(distance_km: float, ascent_m: float, pace_factor: float = 1.0) -> int:
    """Estimate walking time in minutes with Naismith's rule.

    (distance / 5 km/h + ascent / 600 m/h) x pace_factor. A pace_factor of
    1.2 means "20% slower than Naismith", e.g. learned from past hikes.
    """
    hours = distance_km / NAISMITH_KM_PER_HOUR + ascent_m / NAISMITH_ASCENT_M_PER_HOUR
    return round(hours * 60 * pace_factor)


def leave_by(sunset_utc: datetime, duration_min: int, buffer_min: int = FINISH_BUFFER_MIN) -> datetime:
    """Latest start time that still finishes `buffer_min` minutes before sunset."""
    return sunset_utc - timedelta(minutes=duration_min + buffer_min)


def window_hours(forecast: DayForecast, start_utc: datetime, duration_min: int) -> list[HourlyWeather]:
    """Return the forecast hours that overlap the hike, from start to finish.

    Each HourlyWeather covers [time, time + 1 h), so a hike from 09:30 to
    11:15 uses the 09:00, 10:00 and 11:00 hours.
    """
    end_utc = start_utc + timedelta(minutes=duration_min)
    one_hour = timedelta(hours=1)
    return [h for h in forecast.hourly if h.time < end_utc and h.time + one_hour > start_utc]


def missing_window_hours(forecast: DayForecast, start_utc: datetime, duration_min: int) -> list[datetime]:
    """Return the UTC hour starts the hike needs that the forecast doesn't have.

    A gap appears when the hike crosses UTC midnight (the forecast covers one
    UTC day) or when Open-Meteo sent a null value and that hour was dropped.
    Weather checks must treat these hours as unknown, not as safe.
    """
    end_utc = start_utc + timedelta(minutes=duration_min)
    available = {h.time for h in forecast.hourly}
    missing: list[datetime] = []
    hour = start_utc.replace(minute=0, second=0, microsecond=0)
    while hour < end_utc:
        if hour not in available:
            missing.append(hour)
        hour += timedelta(hours=1)
    return missing


def local_start_to_utc(day: date, start_time_local: time, tz: str = "Europe/London") -> datetime:
    """Combine a date and a local wall-clock time into a UTC datetime.

    zoneinfo picks BST or GMT for that exact date. For the repeated hour on
    the night the clocks go back, the first (BST) occurrence is used.
    """
    local = datetime.combine(day, start_time_local, tzinfo=ZoneInfo(tz))
    return local.astimezone(timezone.utc)


def format_local(when_utc: datetime, tz: str = "Europe/London") -> str:
    """Format a UTC datetime as local time with its zone, e.g. "16:41 GMT"."""
    return when_utc.astimezone(ZoneInfo(tz)).strftime("%H:%M %Z")


def format_duration(minutes: int) -> str:
    """Format minutes as e.g. "3 h 05 min"."""
    hours, mins = divmod(int(minutes), 60)
    return f"{hours} h {mins:02d} min"


def check_finish_before_dark(
    start_utc: datetime, duration_min: int, sunset_utc: datetime, tz: str
) -> Check:
    """Check 1: the hike ends at least FINISH_BUFFER_MIN minutes before sunset."""
    end_utc = start_utc + timedelta(minutes=duration_min)
    latest_start = leave_by(sunset_utc, duration_min)
    passed = start_utc <= latest_start
    margin_min = round((sunset_utc - end_utc).total_seconds() / 60)
    if margin_min >= 0:
        margin_text = f"{format_duration(margin_min)} before sunset"
    else:
        margin_text = f"{format_duration(-margin_min)} after sunset"
    detail = (
        f"Starting at {format_local(start_utc, tz)} and walking {format_duration(duration_min)} "
        f"finishes at {format_local(end_utc, tz)}, {margin_text} at {format_local(sunset_utc, tz)}; "
        f"the latest safe start is {format_local(latest_start, tz)} "
        f"({FINISH_BUFFER_MIN} min buffer)."
    )
    return Check(name="Finish before dark", passed=passed, detail=detail)


def check_duration_realistic(est_duration_min: int, naismith_min: int) -> Check:
    """Check 2: the draft's duration is within ±DURATION_TOLERANCE of Naismith."""
    allowed = DURATION_TOLERANCE * naismith_min
    passed = abs(est_duration_min - naismith_min) <= allowed
    low = round(naismith_min - allowed)
    high = round(naismith_min + allowed)
    detail = (
        f"The plan estimates {est_duration_min} min and Naismith's rule gives {naismith_min} min, "
        f"so the acceptable range is {low}-{high} min (±{DURATION_TOLERANCE:.0%})."
    )
    return Check(name="Duration realistic", passed=passed, detail=detail)


def check_wind(hours: list[HourlyWeather]) -> Check:
    """Check 3: the strongest gust during the hike is below MAX_GUST_KMH."""
    if not hours:
        detail = "No hourly forecast covers the hike window, so gusts could not be checked."
        return Check(name="Wind", passed=False, detail=detail)
    max_gust = max(h.gust_kmh for h in hours)
    passed = max_gust < MAX_GUST_KMH
    detail = (
        f"The strongest gust forecast during the hike is {max_gust:.0f} km/h "
        f"(limit: below {MAX_GUST_KMH:.0f} km/h)."
    )
    return Check(name="Wind", passed=passed, detail=detail)


def check_rain(hours: list[HourlyWeather]) -> Check:
    """Check 4: the highest chance of rain during the hike is below MAX_PRECIP_PROB."""
    probs = [h.precip_prob for h in hours if h.precip_prob is not None]
    if not probs:
        detail = "No rain probability is forecast for the hike window, so rain could not be checked."
        return Check(name="Rain", passed=False, detail=detail)
    max_prob = max(probs)
    passed = max_prob < MAX_PRECIP_PROB
    detail = (
        f"The highest chance of rain during the hike is {max_prob}% "
        f"(limit: below {MAX_PRECIP_PROB}%)."
    )
    return Check(name="Rain", passed=passed, detail=detail)


def fail_for_gaps(check: Check, what: str, missing: list[datetime], total: int, has_data: bool) -> Check:
    """Fail a weather check because some hours of the hike have no forecast.

    The reading from the hours we do have (e.g. a 65 km/h gust) stays in the
    detail, so a known hazard is never hidden behind the gap message.
    """
    first_gap = missing[0].strftime("%H:%M UTC on %Y-%m-%d")
    gap_text = (
        f"the forecast is missing {len(missing)} of {total} hours of the hike "
        f"(first gap {first_gap}), so {what} could not be fully checked."
    )
    if has_data:
        detail = f"{check.detail.removesuffix('.')}, but {gap_text}"
    else:
        detail = gap_text[0].upper() + gap_text[1:]
    return Check(name=check.name, passed=False, detail=detail)


def kit_has_cold_items(kit: list[KitItem]) -> bool:
    """True if any kit item mentions gloves, a hat, insulated or thermal layers."""
    return any(COLD_KIT_PATTERN.search(k.item) for k in kit)


def check_cold(hours: list[HourlyWeather], kit: list[KitItem]) -> Check:
    """Check 5: no frost (min temp above MIN_TEMP_C), or the kit has cold-weather items."""
    has_cold_kit = kit_has_cold_items(kit)
    kit_text = "includes" if has_cold_kit else "has no"
    if not hours:
        detail = (
            f"No hourly temperatures cover the hike window, and the kit {kit_text} "
            f"gloves, hat, insulated or thermal items."
        )
        return Check(name="Cold", passed=has_cold_kit, detail=detail)
    min_temp = min(h.temp_c for h in hours)
    passed = min_temp > MIN_TEMP_C or has_cold_kit
    detail = (
        f"The lowest temperature during the hike is {min_temp:.1f} °C "
        f"(limit: above {MIN_TEMP_C:.0f} °C unless packing cold-weather kit), and the kit "
        f"{kit_text} gloves, hat, insulated or thermal items."
    )
    return Check(name="Cold", passed=passed, detail=detail)


def has_source_url(hazard: Hazard) -> bool:
    """True if the hazard cites a web link (http:// or https://)."""
    url = (hazard.source_url or "").strip()
    return url.startswith(("http://", "https://"))


def check_sources_cited(hazards: list[Hazard]) -> Check:
    """Check 6: every hazard or closure claim has a source URL."""
    missing = [h for h in hazards if not has_source_url(h)]
    passed = not missing
    if not hazards:
        detail = "The plan lists 0 hazards, so there is nothing to cite."
    elif passed:
        detail = f"All {len(hazards)} hazards cite a source URL."
    else:
        names = "; ".join(f'"{h.text}"' for h in missing)
        detail = f"{len(missing)} of {len(hazards)} hazards have no source URL: {names}."
    return Check(name="Sources cited", passed=passed, detail=detail)


def check_forecast_available(forecast: DayForecast) -> Check:
    """Check 7: Open-Meteo had a forecast for the hike date."""
    day_text = forecast.day.isoformat()
    if forecast.in_forecast_range:
        # Count only the hike day: merged neighbour-day hours are not "for" this date.
        day_hours = sum(1 for h in forecast.hourly if h.time.date() == forecast.day)
        detail = f"An hourly forecast with {day_hours} hours is available for {day_text}."
        return Check(name="Forecast available", passed=True, detail=detail)
    detail = f"Forecast not available yet for {day_text}; re-check within 7 days of the hike."
    return Check(name="Forecast available", passed=False, detail=detail)


def checked_duration_min(
    draft: PlanDraft, distance_km: float, ascent_m: float, pace_factor: float = 1.0
) -> int:
    """The duration the checks use: the longer of the draft's and Naismith's."""
    return max(draft.est_duration_min, naismith_minutes(distance_km, ascent_m, pace_factor))


def hike_window_utc(
    draft: PlanDraft,
    day: date,
    distance_km: float,
    ascent_m: float,
    pace_factor: float = 1.0,
    tz: str = "Europe/London",
) -> tuple[datetime, datetime]:
    """Return the (start, end) in UTC that run_checks will check the weather for.

    Pass these to weather.get_hike_forecast before run_checks, so a hike that
    crosses UTC midnight gets both days of forecast.
    """
    start_utc = local_start_to_utc(day, draft.start_time_local, tz)
    duration = checked_duration_min(draft, distance_km, ascent_m, pace_factor)
    return start_utc, start_utc + timedelta(minutes=duration)


def run_checks(
    draft: PlanDraft,
    forecast: DayForecast,
    distance_km: float,
    ascent_m: float,
    pace_factor: float = 1.0,
    tz: str = "Europe/London",
) -> list[Check]:
    """Run all 7 automatic checks on a plan draft, in a fixed order.

    The finish-before-dark check and the weather window use the longer of
    the draft's estimate and Naismith's rule, so an optimistic draft can't
    hide a late finish. Wind, Rain and Cold fail if any hour of the hike
    has no forecast, because an unchecked hour is not a safe hour.
    """
    naismith = naismith_minutes(distance_km, ascent_m, pace_factor)
    duration = checked_duration_min(draft, distance_km, ascent_m, pace_factor)
    start_utc = local_start_to_utc(forecast.day, draft.start_time_local, tz)
    hours = window_hours(forecast, start_utc, duration)
    missing = missing_window_hours(forecast, start_utc, duration)
    total = len(hours) + len(missing)
    wind = check_wind(hours)
    rain = check_rain(hours)
    cold = check_cold(hours, draft.kit)
    if missing:
        has_data = bool(hours)
        wind = fail_for_gaps(wind, "gusts", missing, total, has_data)
        rain = fail_for_gaps(rain, "rain", missing, total, has_data)
        # Packing cold-weather kit makes the Cold check pass even with gaps.
        if not kit_has_cold_items(draft.kit):
            cold = fail_for_gaps(cold, "temperatures", missing, total, has_data)
    return [
        check_finish_before_dark(start_utc, duration, forecast.sunset, tz),
        check_duration_realistic(draft.est_duration_min, naismith),
        wind,
        rain,
        cold,
        check_sources_cited(draft.hazards),
        check_forecast_available(forecast),
    ]


def all_passed(checks: list[Check]) -> bool:
    """True if every check passed."""
    return all(c.passed for c in checks)


def failed_summary(checks: list[Check]) -> str:
    """Bullet list of failed checks, fed back to the LLM so it can revise.

    Returns an empty string if nothing failed.
    """
    return "\n".join(f"- {c.name}: {c.detail}" for c in checks if not c.passed)

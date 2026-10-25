"""Create a completed hike in MongoDB straight from a GPX file.

Stopgap for the demo until POST /hikes/{id}/track (task D1) is merged:
the planner needs a based-on hike with a route, a start point and stats.

Usage (from backend/, with the real .env at the repo root):
    python scripts/seed_hike.py ~/hb-data/<hike>/track.gpx \
        --title "Afternoon hike" --trail "Chiltern Way" \
        --hiker friend --date 2026-10-10

Prints the new hike id. Raw GPX stays outside the repo; only the
downsampled route and summary stats are stored.
"""

import argparse
import sys
from datetime import date, datetime, time, timezone
from pathlib import Path

import gpxpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import get_db  # noqa: E402


def load_points(path: Path) -> list:
    """Return every track point in the GPX file, in order."""
    gpx = gpxpy.parse(path.read_text(encoding="utf-8"))
    points = [p for t in gpx.tracks for s in t.segments for p in s.points]
    if not points:
        raise SystemExit(f"No track points in {path}")
    return gpx, points


def route_geojson(points: list, max_points: int = 500) -> dict:
    """Downsample to at most max_points, always keeping first and last."""
    step = max(1, -(-len(points) // (max_points - 1)))
    kept = points[::step]
    if kept[-1] is not points[-1]:
        kept.append(points[-1])
    return {
        "type": "LineString",
        "coordinates": [[p.longitude, p.latitude] for p in kept],
    }


def build_stats(gpx) -> dict:
    """Distance, time and climb, using gpxpy's own smoothing."""
    moving = gpx.get_moving_data()
    climb = gpx.get_uphill_downhill()
    start, end = gpx.get_time_bounds()
    distance_km = gpx.length_2d() / 1000
    moving_s = moving.moving_time if moving else 0
    return {
        "distance_km": round(distance_km, 2),
        "duration_s": (end - start).total_seconds() if start and end else None,
        "moving_s": moving_s,
        "ascent_m": round(climb.uphill or 0, 0),
        "descent_m": round(climb.downhill or 0, 0),
        "avg_hr": None,
        "max_hr": None,
        "start_time": start.isoformat() if start else None,
        "end_time": end.isoformat() if end else None,
        "avg_moving_speed_kmh": (
            round(distance_km / (moving_s / 3600), 2) if moving_s else None
        ),
    }


def pace_factor(stats: dict) -> float | None:
    """Moving time divided by Naismith time, clamped to 0.5-2.0."""
    naismith_h = stats["distance_km"] / 5 + stats["ascent_m"] / 600
    if not stats["moving_s"] or naismith_h <= 0:
        return None
    return round(min(2.0, max(0.5, stats["moving_s"] / 3600 / naismith_h)), 2)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("gpx", type=Path)
    parser.add_argument("--title", required=True)
    parser.add_argument("--trail", required=True)
    parser.add_argument("--hiker", required=True)
    parser.add_argument("--date", type=date.fromisoformat,
                        help="defaults to the first GPX timestamp")
    args = parser.parse_args()

    gpx, points = load_points(args.gpx.expanduser())
    stats = build_stats(gpx)
    day = args.date or (points[0].time.date() if points[0].time else date.today())
    first = points[0]
    doc = {
        "title": args.title,
        "trail_name": args.trail,
        "hiker": args.hiker,
        "date": datetime.combine(day, time.min, tzinfo=timezone.utc),
        "status": "completed",
        "based_on_hike_id": None,
        "route": route_geojson(points),
        "start": {"type": "Point",
                  "coordinates": [first.longitude, first.latitude]},
        "stats": stats,
        "pace_factor": pace_factor(stats),
        "plan": None,
        "recap_md": None,
        "created_at": datetime.now(timezone.utc),
    }
    result = get_db().hikes.insert_one(doc)
    print(f"Created hike {result.inserted_id}: {stats['distance_km']} km, "
          f"{stats['ascent_m']:.0f} m ascent, pace factor {doc['pace_factor']}")


if __name__ == "__main__":
    main()

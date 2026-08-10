"""Adaptateur JSON des positions théoriques calculées depuis le GTFS STM."""

from datetime import datetime

from metro_schedule_data import FEED, GENERATED_AT, LINES, PATTERNS
from stations import STATION_ORDER
from train_schedule import feed_is_current, positions_now, station_levels


def _trip_display_details(line, direction, first, second):
    """Retrouve la destination et la durée du segment courant."""
    fallback_headsign = ""
    for candidate in PATTERNS:
        if candidate[0] != line or candidate[1] != direction:
            continue
        fallback_headsign = candidate[2].replace("Station ", "")
        stations = candidate[3]
        offsets = candidate[4]
        for index in range(len(stations) - 1):
            if stations[index] == first and stations[index + 1] == second:
                return (
                    fallback_headsign,
                    max(1, offsets[index + 1] - offsets[index]),
                )
    return fallback_headsign, 1


def current_train_payload(epoch=None):
    if epoch is None:
        import time
        epoch = time.time()
    positions, local_parts = positions_now(epoch)
    levels, counts = station_levels(
        positions,
        len(STATION_ORDER),
        animation_seconds=epoch,
    )

    trains = []
    for line, first, second, progress, direction in positions:
        pattern_headsign, segment_duration = _trip_display_details(
            line,
            direction,
            first,
            second,
        )
        trains.append({
            "line": LINES[line],
            "line_index": line,
            "from": first,
            "to": second,
            "progress": round(progress, 4),
            "segment_duration": segment_duration,
            "direction": direction,
            "headsign": pattern_headsign,
        })

    local_datetime = datetime(
        local_parts[0],
        local_parts[1],
        local_parts[2],
        local_parts[3],
        local_parts[4],
        local_parts[5],
    )
    return {
        "estimate": True,
        "feed_current": feed_is_current(local_parts),
        "feed_start": FEED[0],
        "feed_end": FEED[1],
        "schedule_generated_at": GENERATED_AT,
        "generated_epoch": epoch,
        "fetched_at": local_datetime.isoformat(timespec="seconds"),
        "animation": "station_marker",
        "levels": [round(level, 4) for level in levels],
        "counts": {
            line_name: counts[index]
            for index, line_name in enumerate(LINES)
        },
        "trains": trains,
        "train_count": len(trains),
        "attribution": "Données planifiées © Société de transport de Montréal",
        "disclaimer": (
            "Positions théoriques calculées à partir des horaires indicatifs "
            "GTFS; ce ne sont pas les positions réelles des trains."
        ),
    }

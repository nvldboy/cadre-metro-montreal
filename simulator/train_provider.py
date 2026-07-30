"""Adaptateur JSON des positions théoriques calculées depuis le GTFS STM."""

from datetime import datetime

from metro_schedule_data import FEED, GENERATED_AT, LINES, PATTERNS
from stations import STATION_ORDER
from train_schedule import feed_is_current, positions_now, station_levels


def current_train_payload(epoch=None):
    positions, local_parts = positions_now(epoch)
    levels, counts = station_levels(positions, len(STATION_ORDER))

    trains = []
    for line, first, second, progress, direction in positions:
        pattern_headsign = ""
        for candidate in PATTERNS:
            if candidate[0] == line and candidate[1] == direction:
                pattern_headsign = candidate[2].replace("Station ", "")
                break
        trains.append({
            "line": LINES[line],
            "from": first,
            "to": second,
            "progress": round(progress, 4),
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
        "fetched_at": local_datetime.isoformat(timespec="seconds"),
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

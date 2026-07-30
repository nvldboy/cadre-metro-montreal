"""Positions théoriques des trains à partir de l'horaire GTFS planifié."""

import time

from metro_schedule_data import (
    DEPARTURES,
    EXCEPTIONS,
    FEED,
    LINES,
    PATTERNS,
    SERVICES,
)

_utc_tuple = getattr(time, "gmtime", time.localtime)
_service_cache = {}


def _weekday(year, month, day):
    """Retourne 0=lundi à 6=dimanche sans dépendre de datetime."""
    month_offsets = (0, 3, 2, 5, 0, 3, 5, 1, 4, 6, 2, 4)
    adjusted_year = year - 1 if month < 3 else year
    sunday_zero = (
        adjusted_year
        + adjusted_year // 4
        - adjusted_year // 100
        + adjusted_year // 400
        + month_offsets[month - 1]
        + day
    ) % 7
    return (sunday_zero + 6) % 7


def _first_sunday(year, month):
    return 1 + ((6 - _weekday(year, month, 1)) % 7)


def _montreal_utc_offset(utc_parts):
    """Fuseau America/Toronto, règles nord-américaines depuis 2007."""
    year, month, day, hour = (
        utc_parts[0],
        utc_parts[1],
        utc_parts[2],
        utc_parts[3],
    )
    if month < 3 or month > 11:
        return -5 * 3600
    if 3 < month < 11:
        return -4 * 3600
    if month == 3:
        transition_day = _first_sunday(year, 3) + 7
        if day > transition_day or (day == transition_day and hour >= 7):
            return -4 * 3600
        return -5 * 3600

    transition_day = _first_sunday(year, 11)
    if day < transition_day or (day == transition_day and hour < 6):
        return -4 * 3600
    return -5 * 3600


def montreal_clock(epoch=None):
    """Retourne l'heure locale de Montréal à partir de l'horloge UTC du Pico."""
    if epoch is None:
        epoch = time.time()
    whole_epoch = int(epoch)
    utc_parts = _utc_tuple(whole_epoch)
    local_epoch = epoch + _montreal_utc_offset(utc_parts)
    return local_epoch, _utc_tuple(int(local_epoch))


def _date_code(parts):
    return parts[0] * 10000 + parts[1] * 100 + parts[2]


def _active_services(date_code, weekday):
    cached = _service_cache.get(date_code)
    if cached is not None:
        return cached

    active = set()
    for index, (start_date, end_date, weekday_mask) in enumerate(SERVICES):
        if start_date <= date_code <= end_date:
            if weekday_mask & (1 << weekday):
                active.add(index)

    added, removed = EXCEPTIONS.get(date_code, ((), ()))
    active.update(added)
    for service in removed:
        active.discard(service)
    if len(_service_cache) > 3:
        _service_cache.clear()
    _service_cache[date_code] = active
    return active


def _lower_bound(values, target):
    low = 0
    high = len(values)
    while low < high:
        middle = (low + high) // 2
        if values[middle] < target:
            low = middle + 1
        else:
            high = middle
    return low


def _upper_bound(values, target):
    low = 0
    high = len(values)
    while low < high:
        middle = (low + high) // 2
        if values[middle] <= target:
            low = middle + 1
        else:
            high = middle
    return low


def _append_positions(result, date_code, weekday, service_second):
    active_services = _active_services(date_code, weekday)
    if not active_services:
        return

    for service_index, pattern_index, starts in DEPARTURES:
        if service_index not in active_services:
            continue

        line, direction, _headsign, stations, offsets = PATTERNS[pattern_index]
        duration = offsets[-1]
        first = _lower_bound(starts, service_second - duration)
        last = _upper_bound(starts, service_second)

        for departure in starts[first:last]:
            elapsed = service_second - departure
            segment = _upper_bound(offsets, elapsed) - 1
            if segment < 0:
                continue
            if segment >= len(stations) - 1:
                result.append(
                    (line, stations[-1], stations[-1], 0.0, direction)
                )
                continue

            segment_duration = offsets[segment + 1] - offsets[segment]
            if segment_duration <= 0:
                progress = 1.0
            else:
                progress = (
                    elapsed - offsets[segment]
                ) / segment_duration
            result.append(
                (
                    line,
                    stations[segment],
                    stations[segment + 1],
                    max(0.0, min(1.0, progress)),
                    direction,
                )
            )


def positions_at(local_parts, previous_parts=None, fractional_second=0.0):
    """Calcule les trains actifs pour une heure locale déjà décomposée."""
    seconds = (
        local_parts[3] * 3600
        + local_parts[4] * 60
        + local_parts[5]
        + fractional_second
    )
    result = []
    _append_positions(
        result,
        _date_code(local_parts),
        local_parts[6],
        seconds,
    )

    if previous_parts is not None:
        _append_positions(
            result,
            _date_code(previous_parts),
            previous_parts[6],
            seconds + 86400,
        )
    return result


def positions_now(epoch=None):
    """Retourne les positions estimées à l'heure actuelle de Montréal."""
    if epoch is None:
        epoch = time.time()
    fractional_second = epoch - int(epoch)
    local_epoch, local_parts = montreal_clock(epoch)
    previous_parts = _utc_tuple(int(local_epoch - 86400))
    return (
        positions_at(local_parts, previous_parts, fractional_second),
        local_parts,
    )


def station_levels(positions, station_count=68):
    """Partage l'intensité d'un train entre ses deux stations voisines."""
    levels = [0.0] * station_count
    line_counts = [0] * len(LINES)
    for line, first_station, second_station, progress, _direction in positions:
        line_counts[line] += 1
        first_level = 1.0 - progress
        levels[first_station] = max(levels[first_station], first_level)
        levels[second_station] = max(levels[second_station], progress)
    return levels, line_counts


def without_interrupted_lines(positions, system_status):
    """Retire immédiatement les trains des lignes déclarées interrompues."""
    return [
        position
        for position in positions
        if system_status.get(LINES[position[0]], "ok") != "interrupted"
    ]


def feed_is_current(local_parts):
    date_code = _date_code(local_parts)
    return int(FEED[0]) <= date_code <= int(FEED[1])

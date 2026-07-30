"""Mode nuit piloté par l'heure locale et les voyages GTFS actifs."""

from config import (
    NIGHT_END_HOUR,
    NIGHT_MODE_ENABLED,
    NIGHT_START_HOUR,
)


def is_night_hour(
    hour,
    enabled=NIGHT_MODE_ENABLED,
    start_hour=NIGHT_START_HOUR,
    end_hour=NIGHT_END_HOUR,
):
    if not enabled:
        return False
    if hour < 0 or hour > 23:
        raise ValueError("Heure invalide")
    if start_hour == end_hour:
        return True
    if start_hour < end_hour:
        return start_hour <= hour < end_hour
    return hour >= start_hour or hour < end_hour


def is_night(local_parts, trains_running):
    # L'heure définit seulement une fenêtre admissible. Un train planifié,
    # notamment lors d'un service prolongé, garde toujours le cadre éveillé.
    return not trains_running and is_night_hour(local_parts[3])

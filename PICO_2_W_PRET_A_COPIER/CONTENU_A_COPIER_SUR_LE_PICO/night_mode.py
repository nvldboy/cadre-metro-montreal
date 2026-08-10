"""Mode nuit piloté par l'heure locale et les voyages GTFS actifs."""

from runtime_settings import get_settings


def anchored_clock_parts(anchor_epoch, elapsed_ms):
    """Avance l'horloge sans convertir le timestamp Unix en float 32 bits."""
    elapsed_seconds, fractional_ms = divmod(int(elapsed_ms), 1000)
    return int(anchor_epoch) + elapsed_seconds, fractional_ms


def is_night_hour(
    hour,
    enabled=None,
    start_hour=None,
    end_hour=None,
):
    settings = get_settings()
    if enabled is None:
        enabled = settings["night_enabled"]
    if start_hour is None:
        start_hour = settings["night_start_hour"]
    if end_hour is None:
        end_hour = settings["night_end_hour"]
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


def resolve_night_mode(local_parts, trains_running, display_mode=None):
    """Applique le choix manuel sans perdre le mode automatique."""
    if display_mode is None:
        display_mode = get_settings()["display_mode"]
    if display_mode == "night":
        return True
    if display_mode in ("day", "off"):
        return False
    return is_night(local_parts, trains_running)

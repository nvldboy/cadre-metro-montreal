"""Interprétation des alertes structurées de l'API Transit v4."""

from stm_status import (
    NORMAL,
    SLOW,
    STOPPED,
    empty_status,
    find_lines_and_stations,
)

_STOP_EFFECTS = ("NO_SERVICE",)
_SLOW_EFFECTS = (
    "REDUCED_SERVICE",
    "SIGNIFICANT_DELAYS",
    "DETOUR",
    "MODIFIED_SERVICE",
    "STOP_MOVED",
)


def _alert_severity(alert):
    effect = str(alert.get("effect", "")).upper()
    severity = str(alert.get("severity", "")).lower()
    if effect in _STOP_EFFECTS or severity == "severe":
        return STOPPED
    if effect in _SLOW_EFFECTS or severity == "warning":
        return SLOW
    return NORMAL


def parse_transit_alerts(payload, route_map=None, stop_map=None):
    """Convertit Transit v4 en la même structure que le client STM.

    route_map associe global_route_id -> green/orange/yellow/blue.
    stop_map associe global_stop_id -> nom canonique d'une station.
    """
    route_map = route_map or {}
    stop_map = stop_map or {}
    result = empty_status()

    for alert in payload.get("alerts", []):
        severity = _alert_severity(alert)
        if severity == NORMAL:
            continue

        text = " ".join(
            part for part in (
                str(alert.get("title", "")),
                str(alert.get("description", "")),
            )
            if part
        ).strip()

        lines = []
        stations = []
        for entity in alert.get("informed_entities", []):
            line_name = route_map.get(entity.get("global_route_id"))
            station_name = stop_map.get(entity.get("global_stop_id"))
            if line_name and line_name not in lines:
                lines.append(line_name)
            if station_name and station_name not in stations:
                stations.append(station_name)

        text_lines, text_stations = find_lines_and_stations(text)
        for line_name in text_lines:
            if line_name not in lines:
                lines.append(line_name)
        for station_name in text_stations:
            if station_name not in stations:
                stations.append(station_name)

        # Ignore les nombreuses alertes d'autobus qui n'affectent ni une
        # ligne ni une station de métro.
        if not lines and not stations:
            continue

        for line_name in lines:
            result["lines"][line_name] = max(
                result["lines"][line_name], severity
            )
        for station_name in stations:
            result["stations"][station_name] = max(
                result["stations"].get(station_name, NORMAL), severity
            )

        if text and text not in result["messages"]:
            result["messages"].append(text[:240])

    result["message_count"] = len(result["messages"])
    return result

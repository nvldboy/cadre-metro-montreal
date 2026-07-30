"""Interprétation tolérante du JSON « état du service » de la STM.

Le Swagger STM ne décrit pas le schéma de la réponse. Le parseur se base donc
sur les champs et le texte présents, sans dépendre d'une structure JSON unique.
"""

from stations import STATION_ORDER

NORMAL = 0
SLOW = 1
STOPPED = 2

_ACCENTS = {
    "à": "a", "â": "a", "ä": "a",
    "ç": "c",
    "é": "e", "è": "e", "ê": "e", "ë": "e",
    "î": "i", "ï": "i",
    "ô": "o", "ö": "o",
    "ù": "u", "û": "u", "ü": "u",
    "œ": "oe",
    "–": "-", "—": "-", "’": "'", " ": " ",
}

_LINE_ALIASES = {
    "green": ("1", "verte", "vert", "green"),
    "orange": ("2", "orange"),
    "yellow": ("4", "jaune", "yellow"),
    "blue": ("5", "bleue", "bleu", "blue"),
}

_STOP_WORDS = (
    "interruption", "service interrompu", "arret de service",
    "hors service", "suspendu", "suspendue", "fermee", "ferme",
    "non desservie", "non desservi",
)

_SLOW_WORDS = (
    "ralenti", "ralentie", "retard", "delai", "perturb",
    "incident", "probleme",
)

_NORMAL_WORDS = (
    "service normal", "aucune interruption", "pas d'interruption",
    "normal service",
)

_SERVICE_STOP_WORDS = (
    "interruption de service",
    "service interrompu",
    "service suspendu",
    "service suspended",
    "no metro service",
)

_SERVICE_SLOW_WORDS = (
    "service ralenti",
    "ralentissement de service",
    "metro service slowdown",
)


def fold(value):
    """Minuscule sans accents, compatible avec MicroPython."""
    text = str(value).lower()
    return "".join(_ACCENTS.get(character, character) for character in text)


def _search_fold(value):
    text = fold(value)
    for character in ("-", "'", "/", ".", ",", ":", ";", "(", ")"):
        text = text.replace(character, " ")
    return " ".join(text.split())


def _scalars(node):
    if isinstance(node, dict):
        values = []
        for value in node.values():
            values.extend(_scalars(value))
        return values
    if isinstance(node, (list, tuple)):
        values = []
        for value in node:
            values.extend(_scalars(value))
        return values
    if node is None:
        return []
    return [str(node)]


def _records(node):
    """Retourne les dictionnaires susceptibles de représenter un message."""
    records = []
    if isinstance(node, dict):
        direct_scalars = [
            value for value in node.values()
            if not isinstance(value, (dict, list, tuple)) and value is not None
        ]
        if direct_scalars:
            records.append(node)
        for value in node.values():
            records.extend(_records(value))
    elif isinstance(node, (list, tuple)):
        for value in node:
            records.extend(_records(value))
    return records


def _exact_line_alias(value):
    value = fold(value).strip()
    for line_name, aliases in _LINE_ALIASES.items():
        if value in aliases:
            return line_name
        if value.startswith("ligne ") and value[6:].strip() in aliases:
            return line_name
        if value.startswith("line ") and value[5:].strip() in aliases:
            return line_name
    return None


def _lines_from_fields(node):
    found = []
    if isinstance(node, dict):
        for key, value in node.items():
            folded_key = fold(key)
            if (
                "ligne" in folded_key
                or "line" in folded_key
                or "route" in folded_key
            ):
                for scalar in _scalars(value):
                    line_name = _exact_line_alias(scalar)
                    if line_name and line_name not in found:
                        found.append(line_name)
            if isinstance(value, (dict, list, tuple)):
                for line_name in _lines_from_fields(value):
                    if line_name not in found:
                        found.append(line_name)
    elif isinstance(node, (list, tuple)):
        for value in node:
            for line_name in _lines_from_fields(value):
                if line_name not in found:
                    found.append(line_name)
    return found


def _lines_from_text(text):
    found = []
    padded = " " + fold(text).replace("-", " ") + " "
    for line_name, aliases in _LINE_ALIASES.items():
        for alias in aliases:
            phrases = (
                " ligne " + alias + " ",
                " line " + alias + " ",
            )
            if any(phrase in padded for phrase in phrases):
                found.append(line_name)
                break
    return found


def _severity_from_fields(node):
    if not isinstance(node, dict):
        return None
    for key, value in node.items():
        folded_key = fold(key)
        if any(word in folded_key for word in ("etat", "status", "severity")):
            folded_value = fold(" ".join(_scalars(value))).strip()
            if any(word in folded_value for word in _STOP_WORDS):
                return STOPPED
            if any(word in folded_value for word in _SLOW_WORDS):
                return SLOW
            if any(word in folded_value for word in _NORMAL_WORDS):
                return NORMAL
            if folded_value in ("normal", "ok", "good"):
                return NORMAL
        if isinstance(value, dict):
            severity = _severity_from_fields(value)
            if severity is not None:
                return severity
    return None


def _severity_from_text(text):
    text = fold(text)
    if any(phrase in text for phrase in _NORMAL_WORDS):
        return NORMAL
    if any(phrase in text for phrase in _STOP_WORDS):
        return STOPPED
    if any(phrase in text for phrase in _SLOW_WORDS):
        return SLOW
    return None


def _stations_from_text(text):
    folded_text = " " + _search_fold(text) + " "
    found = []
    # Les noms longs sont vérifiés en premier pour limiter les faux positifs.
    ordered = sorted(STATION_ORDER, key=len, reverse=True)
    for station_name in ordered:
        folded_station = " " + _search_fold(station_name) + " "
        if folded_station in folded_text:
            found.append(station_name)
    return found


def find_lines_and_stations(text):
    """Extrait les lignes et stations nommées dans un texte libre."""
    return _lines_from_text(text), _stations_from_text(text)


def empty_status():
    return {
        "lines": {
            "green": NORMAL,
            "orange": NORMAL,
            "yellow": NORMAL,
            "blue": NORMAL,
        },
        "stations": {},
        "messages": [],
        "message_count": 0,
    }


def _french_text(items):
    for item in items or ():
        if item.get("language") == "fr" and item.get("text"):
            return item["text"]
    for item in items or ():
        if item.get("text"):
            return item["text"]
    return ""


def _parse_structured_i3(payload):
    """Traite la structure réelle i3 sans confondre les avis d'accès."""
    alerts = payload.get("alerts")
    if not isinstance(alerts, list):
        return None

    result = empty_status()
    seen_messages = set()
    for alert in alerts:
        if not isinstance(alert, dict):
            continue
        entities = alert.get("informed_entities") or ()

        # Les avis avec stop_code concernent souvent un arrêt d'autobus ou un
        # accès de station. Ils ne décrivent pas l'état de service d'une ligne.
        if any(entity.get("stop_code") for entity in entities):
            continue

        lines = []
        for entity in entities:
            line_name = _exact_line_alias(entity.get("route_short_name", ""))
            if line_name and line_name not in lines:
                lines.append(line_name)
        if not lines:
            continue

        description = _french_text(alert.get("description_texts"))
        normalized = fold(description)
        if any(phrase in normalized for phrase in _NORMAL_WORDS):
            severity = NORMAL
        elif any(phrase in normalized for phrase in _SERVICE_STOP_WORDS):
            severity = STOPPED
        elif any(phrase in normalized for phrase in _SERVICE_SLOW_WORDS):
            severity = SLOW
        else:
            # Travaux, accès fermés et messages d'information ne changent pas
            # l'état des trains s'ils ne nomment pas un état de service.
            continue

        for line_name in lines:
            result["lines"][line_name] = max(
                result["lines"][line_name],
                severity,
            )

        if severity != NORMAL:
            for station_name in _stations_from_text(description):
                result["stations"][station_name] = max(
                    result["stations"].get(station_name, NORMAL),
                    severity,
                )
            compact_message = " ".join(description.split())
            if compact_message and compact_message not in seen_messages:
                seen_messages.add(compact_message)
                result["messages"].append(compact_message[:240])

    result["message_count"] = len(result["messages"])
    return result


def parse_service_status(payload):
    """Convertit une réponse STM en états de lignes et de stations."""
    if isinstance(payload, dict):
        structured = _parse_structured_i3(payload)
        if structured is not None:
            return structured

    result = empty_status()
    seen_messages = set()

    for record in _records(payload):
        text = " ".join(_scalars(record)).strip()
        if not text:
            continue

        severity = _severity_from_fields(record)
        if severity is None:
            severity = _severity_from_text(text)
        if severity is None:
            continue

        lines = _lines_from_fields(record)
        if not lines:
            lines = _lines_from_text(text)
        stations = _stations_from_text(text)

        # Un état sans ligne ni station n'est pas exploitable par la carte.
        if not lines and not stations:
            continue

        for line_name in lines:
            result["lines"][line_name] = max(
                result["lines"][line_name], severity
            )

        for station_name in stations:
            result["stations"][station_name] = max(
                result["stations"].get(station_name, NORMAL),
                severity,
            )

        compact_message = " ".join(text.split())
        if compact_message not in seen_messages:
            seen_messages.add(compact_message)
            result["messages"].append(compact_message[:240])

    result["message_count"] = len(result["messages"])
    return result

"""Réglages modifiables depuis le panneau Web local."""

import json
import os

from config import (
    BRIGHTNESS,
    NIGHT_BRIGHTNESS,
    NIGHT_END_HOUR,
    NIGHT_MODE_ENABLED,
    NIGHT_START_HOUR,
    STATUS_BRIGHTNESS,
)

SETTINGS_PATH = "user_settings.json"
DISPLAY_MODES = ("auto", "day", "night", "off")

DEFAULTS = {
    "day_brightness": BRIGHTNESS,
    "night_brightness": NIGHT_BRIGHTNESS,
    "status_brightness": STATUS_BRIGHTNESS,
    "night_enabled": NIGHT_MODE_ENABLED,
    "night_start_hour": NIGHT_START_HOUR,
    "night_end_hour": NIGHT_END_HOUR,
    "display_mode": "auto",
}

_settings = dict(DEFAULTS)
_loaded = False


def _number(value, minimum, maximum, name):
    if isinstance(value, bool):
        raise ValueError("{} doit être un nombre".format(name))
    try:
        value = float(value)
    except (TypeError, ValueError):
        raise ValueError("{} doit être un nombre".format(name))
    if value < minimum or value > maximum:
        raise ValueError(
            "{} doit être entre {} et {}".format(name, minimum, maximum)
        )
    return value


def _hour(value, name):
    if isinstance(value, bool):
        raise ValueError("{} doit être une heure entière".format(name))
    try:
        value = int(value)
    except (TypeError, ValueError):
        raise ValueError("{} doit être une heure entière".format(name))
    if value < 0 or value > 23:
        raise ValueError("{} doit être entre 0 et 23".format(name))
    return value


def validate_settings(candidate, base=None):
    """Valide seulement les clés connues et conserve les autres réglages."""
    if not isinstance(candidate, dict):
        raise ValueError("Les réglages doivent être un objet JSON")
    result = dict(DEFAULTS if base is None else base)

    if "day_brightness" in candidate:
        result["day_brightness"] = _number(
            candidate["day_brightness"], 0.01, 0.20, "Luminosité de jour"
        )
    if "night_brightness" in candidate:
        result["night_brightness"] = _number(
            candidate["night_brightness"],
            0.0005,
            0.02,
            "Luminosité de nuit",
        )
    if "status_brightness" in candidate:
        result["status_brightness"] = _number(
            candidate["status_brightness"],
            0.02,
            0.15,
            "Luminosité des signaux",
        )
    if "night_enabled" in candidate:
        if not isinstance(candidate["night_enabled"], bool):
            raise ValueError("Le mode nuit doit être activé ou désactivé")
        result["night_enabled"] = candidate["night_enabled"]
    if "night_start_hour" in candidate:
        result["night_start_hour"] = _hour(
            candidate["night_start_hour"], "Début de nuit"
        )
    if "night_end_hour" in candidate:
        result["night_end_hour"] = _hour(
            candidate["night_end_hour"], "Fin de nuit"
        )
    if "display_mode" in candidate:
        mode = str(candidate["display_mode"])
        if mode not in DISPLAY_MODES:
            raise ValueError("Mode d'affichage invalide")
        result["display_mode"] = mode
    return result


def load_settings(path=SETTINGS_PATH):
    """Charge les réglages; un fichier absent ou abîmé garde les valeurs sûres."""
    global _settings, _loaded
    loaded = {}
    try:
        with open(path, "r") as handle:
            loaded = json.load(handle)
    except OSError:
        pass
    except Exception as error:
        print("Réglages ignorés:", error)
    try:
        _settings = validate_settings(loaded, DEFAULTS)
    except Exception as error:
        print("Réglages invalides; valeurs par défaut:", error)
        _settings = dict(DEFAULTS)
    _loaded = True
    return dict(_settings)


def get_settings():
    global _loaded
    if not _loaded:
        load_settings()
    return _settings


def save_settings(candidate, path=SETTINGS_PATH):
    """Valide et remplace le fichier sans laisser un JSON partiel."""
    global _settings, _loaded
    updated = validate_settings(candidate, get_settings())
    temporary = path + ".tmp"
    with open(temporary, "w") as handle:
        handle.write(json.dumps(updated))
    try:
        os.rename(temporary, path)
    except OSError:
        try:
            os.remove(path)
        except OSError:
            pass
        os.rename(temporary, path)
    _settings = updated
    _loaded = True
    return dict(_settings)

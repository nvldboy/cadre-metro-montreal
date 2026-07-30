"""Sauvegarde et validation de la correspondance DEL physique ↔ station."""

import json
import os

MAPPING_FILE = "led_mapping.json"
DRAFT_FILE = "led_mapping_draft.json"
MAPPING_VERSION = 1


def validate_physical_to_logical(mapping, station_count=68, allow_partial=False):
    if (
        not isinstance(mapping, list)
        or station_count <= 0
        or len(mapping) != station_count
    ):
        return False

    assigned = []
    for value in mapping:
        if value is None and allow_partial:
            continue
        if type(value) is not int:
            return False
        if value < 0 or value >= station_count:
            return False
        assigned.append(value)
    return len(assigned) == len(set(assigned))


def logical_to_physical(physical_to_logical):
    station_count = (
        len(physical_to_logical)
        if isinstance(physical_to_logical, list)
        else 0
    )
    if not validate_physical_to_logical(
        physical_to_logical,
        station_count,
    ):
        raise ValueError("La correspondance des DEL est invalide")
    result = [0] * len(physical_to_logical)
    for physical_index, logical_index in enumerate(physical_to_logical):
        result[logical_index] = physical_index
    return result


def _read_json(path):
    try:
        with open(path, "r") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def _write_json_atomic(path, payload):
    temporary = path + ".tmp"
    with open(temporary, "w") as handle:
        json.dump(payload, handle)

    replace = getattr(os, "replace", None)
    if replace is not None:
        replace(temporary, path)
        return

    try:
        os.remove(path)
    except OSError:
        pass
    os.rename(temporary, path)


def load_led_mapping(path=MAPPING_FILE, station_count=68):
    payload = _read_json(path)
    if not isinstance(payload, dict):
        return None
    if payload.get("version") != MAPPING_VERSION:
        return None
    mapping = payload.get("physical_to_logical")
    if not validate_physical_to_logical(mapping, station_count):
        return None
    return logical_to_physical(mapping)


def save_led_mapping(physical_to_logical, path=MAPPING_FILE):
    station_count = (
        len(physical_to_logical)
        if isinstance(physical_to_logical, list)
        else 0
    )
    if not validate_physical_to_logical(
        physical_to_logical,
        station_count,
    ):
        raise ValueError("Chaque station doit être attribuée une seule fois")
    _write_json_atomic(
        path,
        {
            "version": MAPPING_VERSION,
            "physical_to_logical": physical_to_logical,
        },
    )


def load_draft(path=DRAFT_FILE, station_count=68):
    payload = _read_json(path)
    if not isinstance(payload, dict):
        return [None] * station_count
    if payload.get("version") != MAPPING_VERSION:
        return [None] * station_count
    mapping = payload.get("physical_to_logical")
    if not validate_physical_to_logical(
        mapping,
        station_count,
        allow_partial=True,
    ):
        return [None] * station_count
    return mapping


def save_draft(physical_to_logical, path=DRAFT_FILE):
    if not validate_physical_to_logical(
        physical_to_logical,
        len(physical_to_logical),
        allow_partial=True,
    ):
        raise ValueError("Brouillon de correspondance invalide")
    _write_json_atomic(
        path,
        {
            "version": MAPPING_VERSION,
            "physical_to_logical": physical_to_logical,
        },
    )


def remove_draft(path=DRAFT_FILE):
    try:
        os.remove(path)
    except OSError:
        pass

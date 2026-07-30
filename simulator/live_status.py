#!/usr/bin/env python3
"""Affiche une prévision des DEL directement dans le Terminal."""

import argparse
import time

from server import PROVIDER

LABELS = {
    "green": "Ligne verte",
    "orange": "Ligne orange",
    "yellow": "Ligne jaune",
    "blue": "Ligne bleue",
}
STATES = {
    0: "couleur normale",
    1: "PULSATION AMBRE",
    2: "CLIGNOTEMENT ROUGE",
}


def display(status):
    print("\033[2J\033[H", end="")
    mode = "EN DIRECT" if status["live"] else "SANS CLÉ - MODE NORMAL"
    print("Cadre du métro -", mode)
    print("Mise à jour:", status["fetched_at"])
    print("Source:", ", ".join(status["source"]) or "aucune")
    print()
    for line_name in ("green", "orange", "yellow", "blue"):
        severity = status["lines"][line_name]
        print("{:<15} {}".format(LABELS[line_name], STATES[severity]))
    if status["stations"]:
        print("\nStations touchées:")
        for station_name, severity in status["stations"].items():
            print(" - {}: {}".format(station_name, STATES[severity]))
    if status["messages"]:
        print("\nMessages:")
        for message in status["messages"]:
            print(" -", message)
    if status["errors"]:
        print("\nInformations:")
        for error in status["errors"]:
            print(" -", error)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--watch",
        action="store_true",
        help="actualiser automatiquement chaque minute",
    )
    args = parser.parse_args()
    while True:
        display(PROVIDER.get(force=True))
        if not args.watch:
            break
        time.sleep(60)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Recalcule les empreintes du dossier partageable destiné au Pico."""

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKAGE = (
    ROOT / "PICO_2_W_PRET_A_COPIER" / "CONTENU_A_COPIER_SUR_LE_PICO"
)
DEFAULT_MANIFEST = ROOT / "PICO_2_W_PRET_A_COPIER" / "MANIFEST_SHA256.txt"
EXCLUDED = {".DS_Store", "secrets.py"}


def update_manifest(package_dir=DEFAULT_PACKAGE, manifest=DEFAULT_MANIFEST):
    lines = []
    for path in sorted(package_dir.iterdir()):
        if not path.is_file() or path.name in EXCLUDED:
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append("{}  {}".format(digest, path.name))
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(lines)


if __name__ == "__main__":
    count = update_manifest()
    print("Manifeste du Pico mis à jour: {} fichiers".format(count))

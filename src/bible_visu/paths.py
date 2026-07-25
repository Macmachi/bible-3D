# © 2026 Rymentz — Bible 3D, visualisation sémantique de la Bible.
# Distribué sous licence CC BY-NC 4.0 — usage non commercial, voir LICENSE.
"""Emplacements sur disque. Tout reste à l'intérieur du dossier du projet."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

DATA = ROOT / "data"
RAW = DATA / "raw"
RAW_HEBREW = RAW / "hebrew"
RAW_GREEK = RAW / "greek"
RAW_TRANSLATIONS = RAW / "translations"
PROCESSED = DATA / "processed"

VIEWER = ROOT / "viewer"
VIEWER_DATA = VIEWER / "data"

#: Cache des poids de modèles — dans le projet, pas dans ~/.cache.
MODELS = DATA / "models"

VERSES = PROCESSED / "verses.parquet"
#: Éditions retenues par `corpus` — le parquet ne garde que les textes.
CORPUS_META = PROCESSED / "corpus.json"
EMBEDDINGS = PROCESSED / "embeddings.npy"
EMBEDDINGS_META = PROCESSED / "embeddings.json"
POINTS = PROCESSED / "points.parquet"

CROSSREFS_ZIP = RAW / "cross-references.zip"
CROSSREFS = PROCESSED / "crossrefs.npz"
AXES = PROCESSED / "axes.npz"

ALL_DIRS = (
    RAW_HEBREW, RAW_GREEK, RAW_TRANSLATIONS, PROCESSED, VIEWER_DATA, MODELS,
)


def ensure_dirs() -> None:
    for directory in ALL_DIRS:
        directory.mkdir(parents=True, exist_ok=True)

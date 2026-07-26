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

#: Les deux textes sur lesquels une carte peut être calculée. Ce ne sont pas
#: deux versions d'une même carte : deux versets voisins chez Segond ne le sont
#: pas forcément chez la World English Bible, et c'est le sujet.
BASES = ("fr", "en")

#: Texte de référence pour chaque base, et colonne du corpus qui le porte.
BASIS_COLUMN = {"fr": "text_fr", "en": "text_en"}


def for_basis(path: Path, basis: str) -> Path:
    """``embeddings.npy`` pour le français, ``embeddings_en.npy`` pour l'anglais.

    Le français ne prend pas de suffixe : c'est la carte d'origine, et lui en
    donner un renommerait des fichiers déjà publiés, déjà référencés dans le
    README et déjà en cache chez les visiteurs.
    """
    if basis not in BASES:
        raise ValueError(f"base inconnue : {basis!r} (attendu {BASES})")
    if basis == "fr":
        return path
    return path.with_name(f"{path.stem}_{basis}{path.suffix}")


def embeddings(basis: str = "fr") -> Path:
    return for_basis(EMBEDDINGS, basis)


def embeddings_meta(basis: str = "fr") -> Path:
    return for_basis(EMBEDDINGS_META, basis)


def points(basis: str = "fr") -> Path:
    return for_basis(POINTS, basis)


def axes(basis: str = "fr") -> Path:
    return for_basis(AXES, basis)


def ensure_dirs() -> None:
    for directory in ALL_DIRS:
        directory.mkdir(parents=True, exist_ok=True)

# © 2026 Rymentz — Bible 3D, visualisation sémantique de la Bible.
# Distribué sous licence CC BY-NC 4.0 — usage non commercial, voir LICENSE.
"""Étape 2 — construction de la table de versets alignés.

    python -m bible_visu.corpus

Produit ``data/processed/verses.parquet``, une ligne par verset avec :

==================  ===========================================================
``ref``             identifiant canonique, p.ex. ``19.23.1`` (livre.chap.verset)
``text_fr``         Louis Segond 1910 — sert de base au calcul sémantique
``text_orig``       hébreu vocalisé (WLC) ou grec (SBLGNT), vide si non aligné
``text_consonants`` hébreu réduit aux 22 consonnes, sans espace (pour l'ELS)
==================  ===========================================================

La colonne vertébrale est la traduction : elle couvre les 66 livres sans trou.
Le texte original est joint dessus et **peut manquer** là où la versification
massorétique diffère de celle de Segond (titres des Psaumes surtout). Le taux
d'alignement réel est affiché à la fin, jamais masqué.
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata

import pandas as pd
from lxml import etree

from . import paths, sources

OSIS_NS = "{http://www.bibletechnologies.net/2003/OSIS/namespace}"

#: Séparateur de morphèmes ajouté par OSHB à l'intérieur des mots.
MORPHEME_SEP = "/"

MAQQEF = "־"
SOF_PASUQ = "׃"
PASEQ = "׀"

#: Marqueurs de section (parashot) — retirés du texte lisible.
SECTION_SEGS = {"x-samekh", "x-pe", "x-reversednun", "x-large", "x-small",
                "x-suspended"}

HEBREW_LETTERS = re.compile(r"[^א-ת]")

#: Formes finales -> forme de base, pour l'analyse en lettres.
FINAL_FORMS = str.maketrans({
    "ך": "כ",  # ך -> כ
    "ם": "מ",  # ם -> מ
    "ן": "נ",  # ן -> נ
    "ף": "פ",  # ף -> פ
    "ץ": "צ",  # ץ -> צ
})


# --------------------------------------------------------------------------
# Hébreu (OSHB / Westminster Leningrad Codex)
# --------------------------------------------------------------------------

def _hebrew_verse_text(verse_el) -> str:
    """Reconstruit le texte d'un verset en respectant maqqef et ponctuation."""
    parts: list[str] = []
    for child in verse_el:
        tag = child.tag
        if tag == f"{OSIS_NS}w":
            word = "".join(child.itertext()).replace(MORPHEME_SEP, "")
            word = word.strip()
            if not word:
                continue
            if parts and not parts[-1].endswith(MAQQEF):
                parts.append(" ")
            parts.append(word)
        elif tag == f"{OSIS_NS}seg":
            seg_type = child.get("type", "")
            text = (child.text or "").strip()
            if seg_type in SECTION_SEGS or not text:
                continue
            if seg_type == "x-maqqef":
                parts.append(MAQQEF)
            elif seg_type == "x-paseq":
                parts.append(f" {PASEQ}")
            else:  # x-sof-pasuq et divers
                parts.append(text)
    return "".join(parts).strip()


def consonants_only(text: str) -> str:
    """Réduit l'hébreu aux 22 lettres, formes finales normalisées, sans espace."""
    stripped = HEBREW_LETTERS.sub("", unicodedata.normalize("NFC", text))
    return stripped.translate(FINAL_FORMS)


def load_hebrew() -> dict[tuple[int, int, int], str]:
    verses: dict[tuple[int, int, int], str] = {}
    for book in sources.BOOKS:
        if book.morphgnt is not None:
            continue
        path = paths.RAW_HEBREW / f"{book.osis}.xml"
        tree = etree.parse(str(path))
        for verse_el in tree.iter(f"{OSIS_NS}verse"):
            osis_id = verse_el.get("osisID")
            if not osis_id:
                continue
            _, chapter, verse = osis_id.split(".")[:3]
            key = (book.book_id, int(chapter), int(verse))
            text = _hebrew_verse_text(verse_el)
            if text:
                verses[key] = text
    return verses


# --------------------------------------------------------------------------
# Grec (MorphGNT / SBLGNT)
# --------------------------------------------------------------------------

def load_greek() -> dict[tuple[int, int, int], str]:
    verses: dict[tuple[int, int, int], list[str]] = {}
    for book in sources.BOOKS:
        if book.morphgnt is None:
            continue
        path = paths.RAW_GREEK / f"{book.morphgnt}-morphgnt.txt"
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                fields = line.split()
                if len(fields) < 7:
                    continue
                code = fields[0]
                chapter, verse = int(code[2:4]), int(code[4:6])
                key = (book.book_id, chapter, verse)
                # champ 3 = « text » : le mot tel qu'imprimé, ponctuation incluse
                verses.setdefault(key, []).append(fields[3])
    return {key: " ".join(words) for key, words in verses.items()}


# --------------------------------------------------------------------------
# Traduction (getbible)
# --------------------------------------------------------------------------

def load_translation(abbrev: str) -> list[dict]:
    path = paths.RAW_TRANSLATIONS / f"{abbrev}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    rows: list[dict] = []
    for book in data["books"]:
        book_id = int(book["nr"])
        for chapter in book["chapters"]:
            for verse in chapter["verses"]:
                text = re.sub(r"\s+", " ", (verse.get("text") or "")).strip()
                rows.append({
                    "book_id": book_id,
                    "chapter": int(verse["chapter"]),
                    "verse": int(verse["verse"]),
                    "text": text,
                })
    return rows


def load_translation_map(abbrev: str) -> dict[tuple[int, int, int], str]:
    return {(r["book_id"], r["chapter"], r["verse"]): r["text"]
            for r in load_translation(abbrev)}


# --------------------------------------------------------------------------

def build(abbrev: str = sources.DEFAULT_TRANSLATION,
          secondary: str | None = sources.DEFAULT_SECONDARY) -> pd.DataFrame:
    rows = load_translation(abbrev)
    hebrew = load_hebrew()
    greek = load_greek()
    originals = {**hebrew, **greek}
    print(f"  hébreu   : {len(hebrew):>6} versets lus")
    print(f"  grec     : {len(greek):>6} versets lus")
    print(f"  {abbrev:<9}: {len(rows):>6} versets lus")

    english: dict[tuple[int, int, int], str] = {}
    if secondary:
        english = load_translation_map(secondary)
        print(f"  {secondary:<9}: {len(english):>6} versets lus")

    records = []
    for row in rows:
        book = sources.BY_ID[row["book_id"]]
        key = (row["book_id"], row["chapter"], row["verse"])
        original = originals.get(key, "")
        records.append({
            "ref": f"{row['book_id']}.{row['chapter']}.{row['verse']}",
            "book_id": row["book_id"],
            "book": book.name_fr,
            "osis": book.osis,
            "testament": book.testament,
            "genre": book.genre,
            "lang": book.lang,
            "chapter": row["chapter"],
            "verse": row["verse"],
            "label": f"{book.name_fr} {row['chapter']}:{row['verse']}",
            "text_fr": row["text"],
            "text_en": english.get(key, ""),
            "text_orig": original,
            "text_consonants": (consonants_only(original)
                                if book.testament == "Ancien" else ""),
        })

    frame = pd.DataFrame.from_records(records)
    frame["n_words_fr"] = frame["text_fr"].str.split().str.len().fillna(0).astype(int)
    frame["has_orig"] = frame["text_orig"].str.len() > 0
    frame["has_en"] = frame["text_en"].str.len() > 0
    # position relative dans le canon, utile pour colorer par progression
    frame["canon_pos"] = frame.index / max(len(frame) - 1, 1)
    return frame


def report(frame: pd.DataFrame) -> None:
    total = len(frame)
    matched = int(frame["has_orig"].sum())
    print(f"\nAlignement original <-> Segond : {matched}/{total} "
          f"({100 * matched / total:.2f} %)")

    missing = frame.loc[~frame["has_orig"]]
    if not missing.empty:
        by_book = missing.groupby("book", observed=True).size().sort_values(
            ascending=False)
        print(f"\n{len(missing)} versets sans texte original "
              f"(versification massorétique différente) :")
        for book, count in by_book.head(12).items():
            print(f"   {book:<26} {count:>4}")
        if len(by_book) > 12:
            print(f"   ... et {len(by_book) - 12} autre(s) livre(s)")

    if "has_en" in frame:
        matched_en = int(frame["has_en"].sum())
        print(f"\nAlignement anglais : {matched_en}/{total} "
              f"({100 * matched_en / total:.2f} %)")

    empty_fr = int((frame["text_fr"].str.len() == 0).sum())
    if empty_fr:
        print(f"\nATTENTION : {empty_fr} verset(s) sans texte français.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--translation", default=sources.DEFAULT_TRANSLATION,
                        help="traduction servant au calcul sémantique")
    parser.add_argument("--secondary", default=sources.DEFAULT_SECONDARY,
                        help="traduction affichée en regard ; 'none' pour aucune")
    args = parser.parse_args(argv)

    secondary = None if args.secondary in ("none", "") else args.secondary

    paths.ensure_dirs()
    print("Lecture des sources…")
    frame = build(args.translation, secondary)
    report(frame)
    frame.to_parquet(paths.VERSES, index=False)

    # Quelles éditions ont servi ? La question se pose devant chaque verset
    # affiché — « Bouillonnant d'ardeur », est-ce Segond ou Darby ? — et la
    # réponse ne se lit nulle part dans le parquet, qui ne garde que les
    # colonnes text_fr / text_en. On l'écrit donc à côté, pour l'export.
    editions = {"translation": args.translation, "secondary": secondary}
    paths.CORPUS_META.write_text(
        json.dumps(editions, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n{len(frame)} versets -> {paths.VERSES}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

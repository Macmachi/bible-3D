# © 2026 Rymentz — Bible 3D, visualisation sémantique de la Bible.
# Distribué sous licence CC BY-NC 4.0 — usage non commercial, voir LICENSE.
"""Table canonique des 66 livres et URL des textes sources.

Trois sources, toutes librement redistribuables :

* OSHB / morphhb  — Westminster Leningrad Codex, hébreu vocalisé + morphologie (CC BY 4.0)
* MorphGNT/SBLGNT — Nouveau Testament grec + morphologie (CC BY-SA 4.0 / SBL licence)
* getbible v2     — Louis Segond 1910, français, domaine public

L'identifiant canonique d'un verset est le triplet ``(book_id, chapter, verse)``
avec ``book_id`` de 1 (Genèse) à 66 (Apocalypse).
"""

from __future__ import annotations

from dataclasses import dataclass

OSHB_BASE = "https://raw.githubusercontent.com/openscriptures/morphhb/master/wlc"
MORPHGNT_BASE = "https://raw.githubusercontent.com/morphgnt/sblgnt/master"
GETBIBLE_BASE = "https://api.getbible.net/v2"

#: Renvois bibliques d'openbible.info (CC BY) — le jeu de données qui a servi à
#: la visualisation en arcs de Harrison & Römhild. Références au format OSIS.
CROSSREFS_URL = "https://a.openbible.info/data/cross-references.zip"

#: Traduction servant de colonne vertébrale sémantique (voir README).
DEFAULT_TRANSLATION = "ls1910"

#: Traduction d'appoint, affichée en regard mais jamais utilisée pour le calcul.
DEFAULT_SECONDARY = "web"

#: Traductions connues de getbible, avec leur langue et leur colonne de sortie.
#: `kjv` reste disponible pour qui préfère l'anglais classique à l'anglais
#: moderne de la World English Bible.
TRANSLATIONS: dict[str, tuple[str, str, str]] = {
    # code      (langue, colonne,   libellé)
    "ls1910":   ("fr", "text_fr", "Louis Segond 1910"),
    "darby":    ("fr", "text_fr", "Darby (français)"),
    "martin":   ("fr", "text_fr", "Martin 1744"),
    "web":      ("en", "text_en", "World English Bible"),
    "kjv":      ("en", "text_en", "King James Version"),
    "asv":      ("en", "text_en", "American Standard Version"),
    "ylt":      ("en", "text_en", "Young's Literal Translation"),
}


@dataclass(frozen=True)
class Book:
    book_id: int
    name_fr: str
    name_en: str
    osis: str
    genre: str
    #: Nom du fichier MorphGNT (NT uniquement), p.ex. ``61-Mt``.
    morphgnt: str | None = None

    @property
    def testament(self) -> str:
        return "Ancien" if self.book_id <= 39 else "Nouveau"

    @property
    def lang(self) -> str:
        return "hébreu" if self.book_id <= 39 else "grec"

    @property
    def source_url(self) -> str:
        if self.morphgnt is not None:
            return f"{MORPHGNT_BASE}/{self.morphgnt}-morphgnt.txt"
        return f"{OSHB_BASE}/{self.osis}.xml"


_TORAH = "Pentateuque"
_HIST = "Livres historiques"
_SAG = "Sagesse et poésie"
_GRANDS = "Grands prophètes"
_PETITS = "Petits prophètes"
_EVANG = "Évangiles"
_ACTES = "Actes"
_PAUL = "Épîtres pauliniennes"
_GEN = "Épîtres générales"
_APOC = "Apocalypse"

BOOKS: tuple[Book, ...] = (
    Book(1, "Genèse", "Genesis", "Gen", _TORAH),
    Book(2, "Exode", "Exodus", "Exod", _TORAH),
    Book(3, "Lévitique", "Leviticus", "Lev", _TORAH),
    Book(4, "Nombres", "Numbers", "Num", _TORAH),
    Book(5, "Deutéronome", "Deuteronomy", "Deut", _TORAH),
    Book(6, "Josué", "Joshua", "Josh", _HIST),
    Book(7, "Juges", "Judges", "Judg", _HIST),
    Book(8, "Ruth", "Ruth", "Ruth", _HIST),
    Book(9, "1 Samuel", "1 Samuel", "1Sam", _HIST),
    Book(10, "2 Samuel", "2 Samuel", "2Sam", _HIST),
    Book(11, "1 Rois", "1 Kings", "1Kgs", _HIST),
    Book(12, "2 Rois", "2 Kings", "2Kgs", _HIST),
    Book(13, "1 Chroniques", "1 Chronicles", "1Chr", _HIST),
    Book(14, "2 Chroniques", "2 Chronicles", "2Chr", _HIST),
    Book(15, "Esdras", "Ezra", "Ezra", _HIST),
    Book(16, "Néhémie", "Nehemiah", "Neh", _HIST),
    Book(17, "Esther", "Esther", "Esth", _HIST),
    Book(18, "Job", "Job", "Job", _SAG),
    Book(19, "Psaumes", "Psalms", "Ps", _SAG),
    Book(20, "Proverbes", "Proverbs", "Prov", _SAG),
    Book(21, "Ecclésiaste", "Ecclesiastes", "Eccl", _SAG),
    Book(22, "Cantique des cantiques", "Song of Songs", "Song", _SAG),
    Book(23, "Ésaïe", "Isaiah", "Isa", _GRANDS),
    Book(24, "Jérémie", "Jeremiah", "Jer", _GRANDS),
    Book(25, "Lamentations", "Lamentations", "Lam", _GRANDS),
    Book(26, "Ézéchiel", "Ezekiel", "Ezek", _GRANDS),
    Book(27, "Daniel", "Daniel", "Dan", _GRANDS),
    Book(28, "Osée", "Hosea", "Hos", _PETITS),
    Book(29, "Joël", "Joel", "Joel", _PETITS),
    Book(30, "Amos", "Amos", "Amos", _PETITS),
    Book(31, "Abdias", "Obadiah", "Obad", _PETITS),
    Book(32, "Jonas", "Jonah", "Jonah", _PETITS),
    Book(33, "Michée", "Micah", "Mic", _PETITS),
    Book(34, "Nahum", "Nahum", "Nah", _PETITS),
    Book(35, "Habacuc", "Habakkuk", "Hab", _PETITS),
    Book(36, "Sophonie", "Zephaniah", "Zeph", _PETITS),
    Book(37, "Aggée", "Haggai", "Hag", _PETITS),
    Book(38, "Zacharie", "Zechariah", "Zech", _PETITS),
    Book(39, "Malachie", "Malachi", "Mal", _PETITS),
    Book(40, "Matthieu", "Matthew", "Matt", _EVANG, "61-Mt"),
    Book(41, "Marc", "Mark", "Mark", _EVANG, "62-Mk"),
    Book(42, "Luc", "Luke", "Luke", _EVANG, "63-Lk"),
    Book(43, "Jean", "John", "John", _EVANG, "64-Jn"),
    Book(44, "Actes", "Acts", "Acts", _ACTES, "65-Ac"),
    Book(45, "Romains", "Romans", "Rom", _PAUL, "66-Ro"),
    Book(46, "1 Corinthiens", "1 Corinthians", "1Cor", _PAUL, "67-1Co"),
    Book(47, "2 Corinthiens", "2 Corinthians", "2Cor", _PAUL, "68-2Co"),
    Book(48, "Galates", "Galatians", "Gal", _PAUL, "69-Ga"),
    Book(49, "Éphésiens", "Ephesians", "Eph", _PAUL, "70-Eph"),
    Book(50, "Philippiens", "Philippians", "Phil", _PAUL, "71-Php"),
    Book(51, "Colossiens", "Colossians", "Col", _PAUL, "72-Col"),
    Book(52, "1 Thessaloniciens", "1 Thessalonians", "1Thess", _PAUL, "73-1Th"),
    Book(53, "2 Thessaloniciens", "2 Thessalonians", "2Thess", _PAUL, "74-2Th"),
    Book(54, "1 Timothée", "1 Timothy", "1Tim", _PAUL, "75-1Ti"),
    Book(55, "2 Timothée", "2 Timothy", "2Tim", _PAUL, "76-2Ti"),
    Book(56, "Tite", "Titus", "Titus", _PAUL, "77-Tit"),
    Book(57, "Philémon", "Philemon", "Phlm", _PAUL, "78-Phm"),
    Book(58, "Hébreux", "Hebrews", "Heb", _GEN, "79-Heb"),
    Book(59, "Jacques", "James", "Jas", _GEN, "80-Jas"),
    Book(60, "1 Pierre", "1 Peter", "1Pet", _GEN, "81-1Pe"),
    Book(61, "2 Pierre", "2 Peter", "2Pet", _GEN, "82-2Pe"),
    Book(62, "1 Jean", "1 John", "1John", _GEN, "83-1Jn"),
    Book(63, "2 Jean", "2 John", "2John", _GEN, "84-2Jn"),
    Book(64, "3 Jean", "3 John", "3John", _GEN, "85-3Jn"),
    Book(65, "Jude", "Jude", "Jude", _GEN, "86-Jud"),
    Book(66, "Apocalypse", "Revelation", "Rev", _APOC, "87-Re"),
)

BY_ID: dict[int, Book] = {b.book_id: b for b in BOOKS}
BY_OSIS: dict[str, Book] = {b.osis: b for b in BOOKS}

#: Ordre d'affichage des genres dans l'interface.
GENRE_ORDER: tuple[str, ...] = (
    _TORAH, _HIST, _SAG, _GRANDS, _PETITS, _EVANG, _ACTES, _PAUL, _GEN, _APOC,
)

#: Le genre reste identifié par son libellé français dans les données ; cette
#: table ne sert qu'à l'affichage.
GENRE_EN: dict[str, str] = {
    _TORAH: "Pentateuch",
    _HIST: "Historical books",
    _SAG: "Wisdom and poetry",
    _GRANDS: "Major prophets",
    _PETITS: "Minor prophets",
    _EVANG: "Gospels",
    _ACTES: "Acts",
    _PAUL: "Pauline epistles",
    _GEN: "General epistles",
    _APOC: "Revelation",
}

TESTAMENT_EN: dict[str, str] = {"Ancien": "Old", "Nouveau": "New"}

LANG_EN: dict[str, str] = {"hébreu": "Hebrew", "grec": "Greek"}


def translation_url(abbrev: str = DEFAULT_TRANSLATION) -> str:
    return f"{GETBIBLE_BASE}/{abbrev}.json"


def _self_check() -> None:
    assert len(BOOKS) == 66, len(BOOKS)
    assert [b.book_id for b in BOOKS] == list(range(1, 67))
    ot = [b for b in BOOKS if b.testament == "Ancien"]
    nt = [b for b in BOOKS if b.testament == "Nouveau"]
    assert len(ot) == 39 and len(nt) == 27
    assert all(b.morphgnt is None for b in ot)
    assert all(b.morphgnt is not None for b in nt)
    assert len({b.osis for b in BOOKS}) == 66
    assert len({b.name_fr for b in BOOKS}) == 66
    assert len({b.name_en for b in BOOKS}) == 66
    assert set(GENRE_ORDER) == {b.genre for b in BOOKS}
    assert set(GENRE_EN) == set(GENRE_ORDER)
    assert set(TESTAMENT_EN) == {b.testament for b in BOOKS}
    assert set(LANG_EN) == {b.lang for b in BOOKS}
    assert all(t in TRANSLATIONS for t in (DEFAULT_TRANSLATION, DEFAULT_SECONDARY))


_self_check()

# © 2026 Rymentz — Bible 3D, visualisation sémantique de la Bible.
# Distribué sous licence CC BY-NC 4.0 — usage non commercial, voir LICENSE.
"""Étape 1 — téléchargement des textes sources dans ``data/raw/``.

    python -m bible_visu.fetch

Les fichiers déjà présents ne sont pas re-téléchargés (``--force`` pour outrepasser).
"""

from __future__ import annotations

import argparse
import sys
import time
import urllib.error
import urllib.request

from . import paths, sources

USER_AGENT = "bible_visu/0.1 (projet personnel de visualisation)"
RETRIES = 3


def download(url: str, dest, force: bool = False) -> tuple[bool, int]:
    """Télécharge ``url`` vers ``dest``. Renvoie ``(a_telecharge, taille)``."""
    if dest.exists() and dest.stat().st_size > 0 and not force:
        return False, dest.stat().st_size

    last_error: Exception | None = None
    for attempt in range(1, RETRIES + 1):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=120) as response:
                payload = response.read()
            if not payload:
                raise OSError("réponse vide")
            tmp = dest.with_suffix(dest.suffix + ".part")
            tmp.write_bytes(payload)
            tmp.replace(dest)
            return True, len(payload)
        except (urllib.error.URLError, OSError) as exc:
            last_error = exc
            if attempt < RETRIES:
                time.sleep(2 * attempt)
    raise RuntimeError(f"échec du téléchargement de {url} : {last_error}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true",
                        help="re-télécharge même si le fichier existe déjà")
    parser.add_argument("--translation", default=sources.DEFAULT_TRANSLATION,
                        help="traduction servant au calcul (défaut : ls1910)")
    parser.add_argument("--secondary", default=sources.DEFAULT_SECONDARY,
                        help="traduction affichée en regard (défaut : web) ; "
                             "'none' pour s'en passer")
    args = parser.parse_args(argv)

    paths.ensure_dirs()
    downloaded = skipped = 0
    total_bytes = 0

    print(f"Textes originaux — {len(sources.BOOKS)} livres")
    for book in sources.BOOKS:
        if book.morphgnt is not None:
            dest = paths.RAW_GREEK / f"{book.morphgnt}-morphgnt.txt"
        else:
            dest = paths.RAW_HEBREW / f"{book.osis}.xml"
        try:
            fresh, size = download(book.source_url, dest, args.force)
        except RuntimeError as exc:
            print(f"  ERREUR  {book.name_fr}: {exc}", file=sys.stderr)
            return 1
        total_bytes += size
        if fresh:
            downloaded += 1
            print(f"  {book.book_id:>2}. {book.name_fr:<24} {size / 1024:>8.0f} Ko")
        else:
            skipped += 1

    print()
    wanted = [args.translation]
    if args.secondary and args.secondary != "none":
        wanted.append(args.secondary)
    for abbrev in wanted:
        dest = paths.RAW_TRANSLATIONS / f"{abbrev}.json"
        fresh, size = download(sources.translation_url(abbrev), dest, args.force)
        total_bytes += size
        label = sources.TRANSLATIONS.get(abbrev, ("", "", abbrev))[2]
        print(f"Traduction {abbrev} ({label}) : {size / 1024 / 1024:.1f} Mo"
              f"{'' if fresh else ' (déjà présente)'}")

    fresh, size = download(sources.CROSSREFS_URL, paths.CROSSREFS_ZIP, args.force)
    total_bytes += size
    print(f"Renvois openbible.info : {size / 1024 / 1024:.1f} Mo"
          f"{'' if fresh else ' (déjà présents)'}")

    print(f"\n{downloaded} fichier(s) téléchargé(s), {skipped} déjà présent(s) — "
          f"{total_bytes / 1024 / 1024:.1f} Mo au total dans {paths.RAW}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

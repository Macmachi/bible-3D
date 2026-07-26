# © 2026 Rymentz — Bible 3D, visualisation sémantique de la Bible.
# Distribué sous licence CC BY-NC 4.0 — usage non commercial, voir LICENSE.
"""Étape 7 — export des données pour le visualiseur.

    python -m bible_visu.export

Écrit dans ``viewer/data/`` :

* ``positions.bin``   — coordonnées XYZ en Float32, lues directement dans un
  buffer WebGL sans passer par un parseur JSON ;
* ``verses.json``     — textes, métadonnées, amas, voisinage et renvois ;
* ``verses.json.gz``  — la même chose compressée. ``serve.py`` la sert
  automatiquement aux navigateurs qui acceptent gzip, ce qui divise le transfert
  par trois environ. Le fichier non compressé reste la référence, pour qu'un
  hébergement statique quelconque fonctionne sans configuration.

Quand une seconde carte a été calculée — ``project --basis en`` — s'y ajoutent
``positions_en.bin``, ``axes_en.bin`` et ``geometry_en.json``. Ce dernier ne
contient que ce qui dépend du texte de calcul : amas, voisinage, échos entre
Testaments. Les textes, les livres et les renvois traditionnels sont communs aux
deux cartes et restent dans ``verses.json``, qui n'est donc pas expédié deux
fois. Le visualiseur ne charge la seconde carte que si on la lui demande.
"""

from __future__ import annotations

import argparse
import gzip
import json

import numpy as np
import pandas as pd

from . import paths, sources


def load_crossrefs(n: int, limit: int):
    """Renvois par verset, limités aux mieux votés, plus le compte d'accords."""
    if not paths.CROSSREFS.exists():
        return None
    blob = np.load(paths.CROSSREFS)
    indptr, indices, votes = blob["indptr"], blob["indices"], blob["votes"]

    per_verse: list[list[int]] = []
    for i in range(n):
        start, stop = int(indptr[i]), int(indptr[i + 1])
        if stop <= start:
            per_verse.append([])
            continue
        block = slice(start, stop)
        order = np.argsort(-votes[block])[:limit]
        per_verse.append([int(x) for x in indices[block][order]])
    # `confirmed` sert au bilan imprimé par `crossrefs`, pas au visualiseur :
    # inutile de l'expédier au navigateur.
    return {"xref": per_verse}


def editions() -> dict[str, str]:
    """Nom lisible de chaque édition affichée, pour la légende d'un verset.

    Devant « Bouillonnant d'ardeur », le lecteur doit pouvoir savoir s'il lit
    Segond ou Darby. `corpus` note son choix dans corpus.json ; à défaut — un
    corpus construit avant l'ajout de ce fichier — on retombe sur les valeurs
    par défaut, qui sont celles qu'il aurait employées.
    """
    chosen = {"translation": sources.DEFAULT_TRANSLATION,
              "secondary": sources.DEFAULT_SECONDARY}
    if paths.CORPUS_META.exists():
        try:
            chosen.update(json.loads(
                paths.CORPUS_META.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            pass

    named: dict[str, str] = {
        # les textes originaux ne changent jamais : une seule édition de chaque
        "he": "Westminster Leningrad Codex",
        "grc": "SBL Greek New Testament",
    }
    for key in ("translation", "secondary"):
        abbrev = chosen.get(key)
        if abbrev and abbrev in sources.TRANSLATIONS:
            code, _column, label = sources.TRANSLATIONS[abbrev]
            named[code] = label
    return named


def geometry(frame: pd.DataFrame) -> dict:
    """Ce qui dépend du texte sur lequel la carte a été calculée.

    Amas, voisinage et échos entre Testaments changent d'une base à l'autre :
    deux versets voisins chez Segond ne le sont pas forcément dans la World
    English Bible. Les textes eux-mêmes, les livres, les genres et les renvois
    traditionnels ne bougent pas, et n'ont donc pas à être expédiés deux fois —
    ce sont eux qui pèsent les vingt mégaoctets.
    """
    clusters = []
    for cid, group in frame.loc[frame.cluster >= 0].groupby("cluster", observed=True):
        dominant = group["book"].mode()
        book_fr = dominant.iloc[0] if len(dominant) else ""
        book = next((b for b in sources.BOOKS if b.name_fr == book_fr), None)
        clusters.append({
            "id": int(cid),
            "label": group["cluster_label"].iloc[0],
            "size": int(len(group)),
            "book": book_fr,
            "bookEn": book.name_en if book else book_fr,
        })
    clusters.sort(key=lambda c: -c["size"])

    return {
        "clusters": clusters,
        "cluster": frame["cluster"].astype(int).tolist(),
        "nn": [list(map(int, row)) for row in frame["neighbours"]],
        "nnSim": [[round(float(v), 3) for v in row]
                  for row in frame["neighbour_sim"]],
        "crossT": frame["nn_cross_testament"].astype(int).tolist(),
    }


def build_payload(frame: pd.DataFrame, crossrefs, bases: list[str]) -> dict:
    payload = {
        "count": int(len(frame)),
        "editions": editions(),
        # les variantes anglaises par livre ne sont pas reprises ici : le
        # visualiseur traduit genres et testaments par sa propre table, et
        # `genresEn` plus bas suffit pour la légende
        # `osis` sert aux permaliens : une référence partagée s'écrit
        # « Matt.6.12 » et non « 40.6.12 ». C'est le standard d'échange des
        # références bibliques, et un lien lisible dit déjà quelque chose avant
        # d'être ouvert. Coût : 66 chaînes courtes, ~500 octets.
        "books": [{"id": b.book_id, "name": b.name_fr, "nameEn": b.name_en,
                   "osis": b.osis, "genre": b.genre, "testament": b.testament,
                   "lang": b.lang}
                  for b in sources.BOOKS],
        "genres": list(sources.GENRE_ORDER),
        "genresEn": [sources.GENRE_EN[g] for g in sources.GENRE_ORDER],
        # Les bases disponibles, la première étant celle que porte ce fichier.
        # Le visualiseur n'offre le choix que si la liste en compte plusieurs.
        "bases": bases,
        "bookId": frame["book_id"].astype(int).tolist(),
        "chapter": frame["chapter"].astype(int).tolist(),
        "verse": frame["verse"].astype(int).tolist(),
        "fr": frame["text_fr"].tolist(),
        "orig": frame["text_orig"].tolist(),
    }
    payload.update(geometry(frame))
    if "text_en" in frame:
        payload["en"] = frame["text_en"].fillna("").tolist()
    if crossrefs:
        payload.update(crossrefs)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--xref-limit", type=int, default=12,
                        help="renvois conservés par verset pour l'affichage")
    args = parser.parse_args(argv)

    paths.ensure_dirs()
    if not paths.points("fr").exists():
        raise SystemExit("points.parquet absent. Lance `python -m bible_visu.project`.")

    # La base française reste la référence : ses fichiers gardent leur nom, ce
    # sont eux que le README cite et que les navigateurs ont en cache. Les
    # autres bases s'ajoutent à côté, et le visualiseur ignore ce qui manque.
    available = [b for b in paths.BASES if paths.points(b).exists()]
    written: list[str] = []

    for basis in available:
        frame = pd.read_parquet(paths.points(basis))
        suffix = "" if basis == "fr" else f"_{basis}"

        positions = frame[["x", "y", "z"]].to_numpy(dtype=np.float32).ravel()
        bin_path = paths.VIEWER_DATA / f"positions{suffix}.bin"
        bin_path.write_bytes(positions.tobytes())

        # Les scores d'axes vont dans un binaire séparé : 8 × 31 170 flottants
        # gonfleraient le JSON d'un mégaoctet de chiffres pour rien.
        axes_meta = None
        axes_path = paths.VIEWER_DATA / f"axes{suffix}.bin"
        if paths.axes(basis).exists():
            blob = np.load(paths.axes(basis))
            scores = blob["scores"].astype(np.float32)
            if len(scores) != len(frame):
                print(f"[{basis}] axes ignorés : nombre de versets incohérent, "
                      f"relance `axes --basis {basis}`.")
            else:
                # rangés axe par axe : le visualiseur en lit un d'un seul tenant
                axes_path.write_bytes(np.ascontiguousarray(scores.T).tobytes())
                axes_meta = json.loads(
                    paths.axes(basis).with_suffix(".json").read_text(encoding="utf-8"))
        elif axes_path.exists():
            axes_path.unlink()

        if basis == "fr":
            crossrefs = load_crossrefs(len(frame), args.xref_limit)
            payload = build_payload(frame, crossrefs, available)
            name = "verses.json"
        else:
            # Seule la géométrie change : textes, livres, genres et renvois
            # restent ceux de verses.json, déjà chargés par le visualiseur.
            crossrefs = None
            payload = geometry(frame)
            payload["basis"] = basis
            name = f"geometry_{basis}.json"
        if axes_meta:
            payload["axes"] = axes_meta

        text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        json_path = paths.VIEWER_DATA / name
        json_path.write_text(text, encoding="utf-8")
        gz_path = paths.VIEWER_DATA / f"{name}.gz"
        gz_path.write_bytes(gzip.compress(text.encode("utf-8"), compresslevel=6))
        written.append(basis)

        print(f"\n── base {basis} ──")
        print(f"positions{suffix}.bin{'':<4}{bin_path.stat().st_size / 1024:>8.0f} Ko "
              f"({len(frame)} points)")
        print(f"{name:<20}{json_path.stat().st_size / 1024 / 1024:>8.1f} Mo "
              f"({len(payload['clusters'])} amas)")
        print(f"{name + '.gz':<20}{gz_path.stat().st_size / 1024 / 1024:>8.1f} Mo "
              f"({100 * gz_path.stat().st_size / json_path.stat().st_size:.0f} % "
              f"de l'original)")
        if axes_meta:
            print(f"axes{suffix}.bin{'':<9}{axes_path.stat().st_size / 1024:>8.0f} Ko "
                  f"({len(axes_meta)} axes)")
        else:
            print(f"Axes thématiques absents — lance "
                  f"`python -m bible_visu.axes --basis {basis}`.")
        if basis == "fr":
            if crossrefs is None:
                print("Renvois absents — lance `python -m bible_visu.crossrefs` "
                      "pour la couche Harrison.")
            if "en" not in payload:
                print("Texte anglais absent — relance `corpus` avec --secondary web.")

    # Une carte dont le parquet a disparu ne doit pas rester servie en ligne
    # avec des coordonnées orphelines : mieux vaut qu'elle ne soit plus offerte.
    for basis in paths.BASES:
        if basis in written or basis == "fr":
            continue
        for stale in (paths.VIEWER_DATA / f"geometry_{basis}.json",
                      paths.VIEWER_DATA / f"geometry_{basis}.json.gz",
                      paths.VIEWER_DATA / f"positions_{basis}.bin",
                      paths.VIEWER_DATA / f"axes_{basis}.bin"):
            if stale.exists():
                stale.unlink()
                print(f"retiré : {stale.name}")

    if written == ["fr"]:
        print("\nSeule la carte française est calculée. Pour la seconde :"
              "\n  python -m bible_visu.embed   --basis en"
              "\n  python -m bible_visu.project --basis en"
              "\n  python -m bible_visu.axes    --basis en"
              "\n  python -m bible_visu.export")
    print("\nLancer :  python serve.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# © 2026 Rymentz — Bible 3D, visualisation sémantique de la Bible.
# Distribué sous licence CC BY-NC 4.0 — usage non commercial, voir LICENSE.
"""Renvois traditionnels, et confrontation avec la carte sémantique.

    python -m bible_visu.crossrefs

Les 344 799 renvois d'openbible.info sont le jeu de données qui a servi à la
visualisation en arcs de Harrison & Römhild. Ils représentent **ce que des
générations d'éditeurs ont jugé lié**. La carte, elle, représente ce qu'un
modèle de langue juge proche. Les deux ne coïncident pas, et c'est tout
l'intérêt :

* un lien **confirmé** — proche sémantiquement *et* renvoi traditionnel —
  ne surprend personne, mais valide la méthode ;
* un lien **inédit** — très proche sémantiquement, jamais renvoyé — désigne
  un rapprochement que la tradition n'a pas retenu. C'est là qu'il faut
  regarder si l'on cherche quelque chose de non évident ;
* un renvoi **sémantiquement lointain** signale à l'inverse un lien fondé sur
  autre chose que la ressemblance du texte : une figure, un accomplissement,
  une doctrine. Ce n'est pas une erreur de la tradition, c'est une dimension
  que le modèle ne voit pas.

Aucun de ces trois cas n'est une découverte en soi. Ce sont des pistes.
"""

from __future__ import annotations

import argparse
import re
import zipfile

import numpy as np
import pandas as pd

from . import paths, sources

REF_RE = re.compile(r"^([A-Za-z0-9]+)\.(\d+)\.(\d+)$")

#: Nombre de renvois conservés par verset pour l'affichage (les mieux votés).
EXPORT_LIMIT = 12


def parse_ref(ref: str, index_of: dict[str, int]) -> int | None:
    match = REF_RE.match(ref.strip())
    if not match:
        return None
    osis, chapter, verse = match.groups()
    book = sources.BY_OSIS.get(osis)
    if book is None:
        return None
    return index_of.get(f"{book.book_id}.{int(chapter)}.{int(verse)}")


def load_pairs(index_of: dict[str, int]) -> tuple[list[tuple[int, int, int]], dict]:
    """Lit l'archive et rend les couples ``(i, j, votes)``, plages développées."""
    pairs: list[tuple[int, int, int]] = []
    stats = {"lignes": 0, "ignorés_votes": 0, "ignorés_ref": 0, "plages": 0}

    with zipfile.ZipFile(paths.CROSSREFS_ZIP) as archive:
        name = archive.namelist()[0]
        with archive.open(name) as handle:
            handle.readline()                     # en-tête
            for raw in handle:
                fields = raw.decode("utf-8").rstrip("\n").split("\t")
                if len(fields) < 3:
                    continue
                stats["lignes"] += 1
                source_ref, target_ref, vote_text = fields[0], fields[1], fields[2]
                try:
                    votes = int(vote_text)
                except ValueError:
                    continue
                # les renvois rejetés par les votes ne sont pas retenus
                if votes <= 0:
                    stats["ignorés_votes"] += 1
                    continue

                start = parse_ref(source_ref, index_of)
                if start is None:
                    stats["ignorés_ref"] += 1
                    continue

                if "-" in target_ref:
                    stats["plages"] += 1
                    left, right = target_ref.split("-", 1)
                    a = parse_ref(left, index_of)
                    b = parse_ref(right, index_of)
                    if a is None or b is None:
                        stats["ignorés_ref"] += 1
                        continue
                    # les versets sont en ordre canonique : la plage est un
                    # intervalle contigu d'indices
                    targets = range(min(a, b), max(a, b) + 1)
                else:
                    target = parse_ref(target_ref, index_of)
                    if target is None:
                        stats["ignorés_ref"] += 1
                        continue
                    targets = (target,)

                for target in targets:
                    if target != start:
                        pairs.append((start, target, votes))
    return pairs, stats


def build_adjacency(pairs, n: int) -> list[dict[int, int]]:
    """Adjacence symétrique ``verset -> {voisin: votes}``.

    Le fichier est orienté, mais un renvoi lie deux passages : on garde les
    deux sens, en conservant le meilleur score quand les deux existent.
    """
    adjacency: list[dict[int, int]] = [dict() for _ in range(n)]
    for i, j, votes in pairs:
        if votes > adjacency[i].get(j, 0):
            adjacency[i][j] = votes
        if votes > adjacency[j].get(i, 0):
            adjacency[j][i] = votes
    return adjacency


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=EXPORT_LIMIT,
                        help="renvois conservés par verset pour l'affichage")
    parser.add_argument("--window", type=int, default=1,
                        help="tolérance en versets lors de la comparaison avec "
                             "la tradition (0 = comparaison stricte)")
    # Les renvois eux-mêmes ne dépendent d'aucune carte : ils viennent
    # d'openbible et sont indexés par référence. Ce qui dépend de la carte,
    # c'est le *bilan* imprimé — combien de voisins sémantiques la tradition
    # relie aussi. Changer de base rejoue donc la mesure sans rien changer au
    # fichier exporté, qui reste commun aux deux cartes.
    parser.add_argument("--basis", default="fr", choices=list(paths.BASES),
                        help="carte confrontée à la tradition (défaut : fr)")
    args = parser.parse_args(argv)

    if not paths.CROSSREFS_ZIP.exists():
        raise SystemExit("Archive absente — lance d'abord `python -m bible_visu.fetch`")

    points = pd.read_parquet(paths.points(args.basis))
    index_of = {ref: i for i, ref in enumerate(points["ref"])}
    n = len(points)

    print("Lecture des renvois…")
    pairs, stats = load_pairs(index_of)
    adjacency = build_adjacency(pairs, n)

    linked = sum(1 for a in adjacency if a)
    total = sum(len(a) for a in adjacency) // 2
    print(f"  {stats['lignes']} lignes lues, {stats['plages']} plages développées")
    print(f"  {stats['ignorés_votes']} rejetées (votes ≤ 0), "
          f"{stats['ignorés_ref']} références non résolues")
    print(f"  {total} liens distincts, {linked} versets reliés "
          f"({100 * linked / n:.1f} %)")

    # ------------------------------------------------------------------
    # Confrontation avec le voisinage sémantique
    # ------------------------------------------------------------------
    neighbours = points["neighbours"].tolist()
    sims = points["neighbour_sim"].tolist()
    book_of = points["book_id"].to_numpy()

    def is_known(i: int, j: int, window: int) -> bool:
        """Le lien i–j est-il attesté par la tradition, à ``window`` versets près ?

        Indispensable : openbible enregistre les renvois **au niveau du
        passage**. Le lien de la Pentecôte figure sous la forme
        ``Joël 2:30 → Actes 2:19-20``, jamais comme la paire exacte
        Joël 2:31 ↔ Actes 2:20. Une comparaison verset à verset déclarerait
        donc « inédite » l'une des citations les plus connues de la Bible.
        La fenêtre ne franchit pas les frontières de livre.
        """
        for di in range(-window, window + 1):
            a = i + di
            if not (0 <= a < n) or book_of[a] != book_of[i]:
                continue
            known = adjacency[a]
            if not known:
                continue
            for dj in range(-window, window + 1):
                b = j + dj
                if 0 <= b < n and book_of[b] == book_of[j] and b in known:
                    return True
        return False

    confirmed = np.zeros(n, dtype=np.int16)
    confirmed_strict = np.zeros(n, dtype=np.int16)
    novel_sim = np.zeros(n, dtype=np.float32)
    for i in range(n):
        strict = {k for k, j in enumerate(neighbours[i]) if j in adjacency[i]}
        loose = {k for k, j in enumerate(neighbours[i])
                 if k in strict or is_known(i, j, args.window)}
        confirmed_strict[i] = len(strict)
        confirmed[i] = len(loose)
        fresh = [sims[i][k] for k in range(len(neighbours[i])) if k not in loose]
        novel_sim[i] = max(fresh) if fresh else 0.0

    with_refs = np.array([len(a) > 0 for a in adjacency])
    print(f"\nAccord entre les deux sources, sur les {int(with_refs.sum())} "
          f"versets qui ont au moins un renvoi :")
    for k in range(0, 5):
        share = 100 * (confirmed[with_refs] == k).mean()
        print(f"  {k} des 8 voisins sémantiques sont aussi des renvois : {share:>5.1f} %")
    print(f"  au moins un : {100 * (confirmed[with_refs] > 0).mean():.1f} % "
          f"(comparaison stricte : "
          f"{100 * (confirmed_strict[with_refs] > 0).mean():.1f} %)")

    # similarité sémantique des liens traditionnels
    embeddings = np.load(paths.embeddings(args.basis))
    sample_pairs = [(i, j) for i, a in enumerate(adjacency) for j in a if i < j]
    rng = np.random.default_rng(0)
    picked = rng.choice(len(sample_pairs), min(40000, len(sample_pairs)), replace=False)
    link_sim = np.array([float(embeddings[sample_pairs[k][0]] @ embeddings[sample_pairs[k][1]])
                         for k in picked], dtype=np.float32)
    print(f"\nSimilarité sémantique des renvois traditionnels "
          f"(échantillon de {len(link_sim)}) :")
    for q in (10, 25, 50, 75, 90):
        print(f"  {q}e centile : {np.percentile(link_sim, q):.3f}")

    # `confirmed` et `novel_sim` sont mesurés sur la carte confrontée. Écrire
    # ceux d'une autre base dans le fichier de référence y laisserait des
    # chiffres qui ne correspondent plus à son nom : on ne réécrit donc que
    # depuis la base française, et une autre base ne produit qu'un bilan.
    if args.basis == "fr":
        np.savez_compressed(
            paths.CROSSREFS,
            indptr=np.array([0] + list(np.cumsum([len(a) for a in adjacency])),
                            dtype=np.int64),
            indices=np.array([j for a in adjacency for j in a], dtype=np.int32),
            votes=np.array([v for a in adjacency for v in a.values()], dtype=np.int32),
            confirmed=confirmed,
            novel_sim=novel_sim,
            limit=np.int32(args.limit),
        )
        print(f"\n{total} liens -> {paths.CROSSREFS}")
    else:
        print(f"\n{total} liens — base « {args.basis} » : bilan seul, "
              f"{paths.CROSSREFS.name} inchangé")

    # ------------------------------------------------------------------
    print("\nPonts AT ↔ NT les plus forts que la tradition ne relie pas :")
    order = np.argsort(-novel_sim)
    seen: set[tuple[int, int]] = set()
    shown = 0
    for i in order:
        if shown >= 10:
            break
        if not with_refs[i]:
            continue
        best = max((k for k in range(len(neighbours[i]))
                    if not is_known(i, neighbours[i][k], args.window)),
                   key=lambda k: sims[i][k], default=None)
        if best is None:
            continue
        j = int(neighbours[i][best])
        if points.testament[i] == points.testament[j]:
            continue                      # on met en avant les ponts AT ↔ NT
        pair = (min(i, j), max(i, j))     # le lien est symétrique : une seule ligne
        if pair in seen:
            continue
        seen.add(pair)
        print(f"  {points.label[i]:<20} ↔ {points.label[j]:<20} "
              f"({sims[i][best]:.3f})")
        print(f"     « {points.text_fr[i][:72]} »")
        print(f"     « {points.text_fr[j][:72]} »")
        shown += 1

    print("\nCes rapprochements ne sont pas des découvertes : la plupart seront "
          "des formules communes\nou des faux amis. Ce sont des endroits où "
          "regarder, rien de plus.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

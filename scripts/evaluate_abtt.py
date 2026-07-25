# © 2026 Rymentz — Bible 3D, visualisation sémantique de la Bible.
# Distribué sous licence CC BY-NC 4.0 — usage non commercial, voir LICENSE.
"""Mesure l'effet du débruitage All-but-the-Top sur un étalon connu.

    PYTHONPATH=src python scripts/evaluate_abtt.py

L'étalon est constitué de citations de l'Ancien Testament par le Nouveau, dont
la correspondance ne fait pas débat. Pour chaque paire, on demande : à quel rang
le vrai partenaire apparaît-il dans le classement de similarité, sur les 31 170
versets ? Rang 1 = premier voisin trouvé. Plus le rang médian est bas, mieux
l'espace vectoriel relie ce qui est réellement lié.

On mesure aussi la « gravité narrative » : la part des 8 plus proches voisins
qui proviennent du même livre. Une valeur élevée signifie que les versets sont
surtout attirés par leur propre contexte, au détriment du thème.
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "src")

from bible_visu import paths, vectors as vec  # noqa: E402

#: (référence AT, référence NT, description) — le NT cite explicitement l'AT.
GOLD: tuple[tuple[str, str, str], ...] = (
    ("23.53.5", "60.2.24", "Ésaïe 53:5 — par ses meurtrissures / 1 Pierre 2:24"),
    ("19.22.2", "40.27.46", "Psaume 22:2 — Éli, Éli / Matthieu 27:46"),
    ("1.15.6", "45.4.3", "Genèse 15:6 — Abraham crut / Romains 4:3"),
    ("5.6.5", "41.12.30", "Deutéronome 6:5 — tu aimeras l'Éternel / Marc 12:30"),
    ("3.19.18", "40.22.39", "Lévitique 19:18 — ton prochain comme toi-même / Matthieu 22:39"),
    ("35.2.4", "45.1.17", "Habacuc 2:4 — le juste vivra par la foi / Romains 1:17"),
    ("38.9.9", "40.21.5", "Zacharie 9:9 — ton roi vient monté sur un âne / Matthieu 21:5"),
    ("23.7.14", "40.1.23", "Ésaïe 7:14 — la vierge enfantera / Matthieu 1:23"),
    ("19.110.1", "40.22.44", "Psaume 110:1 — assieds-toi à ma droite / Matthieu 22:44"),
    ("28.11.1", "40.2.15", "Osée 11:1 — j'ai appelé mon fils / Matthieu 2:15"),
    ("23.40.3", "41.1.3", "Ésaïe 40:3 — une voix crie dans le désert / Marc 1:3"),
    ("19.118.22", "40.21.42", "Psaume 118:22 — la pierre rejetée / Matthieu 21:42"),
    ("24.31.31", "58.8.8", "Jérémie 31:31 — une alliance nouvelle / Hébreux 8:8"),
    ("1.2.24", "49.5.31", "Genèse 2:24 — une seule chair / Éphésiens 5:31"),
    ("23.61.1", "42.4.18", "Ésaïe 61:1 — l'Esprit est sur moi / Luc 4:18"),
)

CANDIDATES = (0, 1, 2, 3, 4, 6, 8, 12, 16, 24)


def main() -> int:
    frame = pd.read_parquet(paths.VERSES)
    index_of = {ref: i for i, ref in enumerate(frame["ref"])}
    base = np.load(paths.EMBEDDINGS)

    pairs = []
    print("Étalon — citations de l'AT dans le NT\n")
    for ot_ref, nt_ref, label in GOLD:
        if ot_ref not in index_of or nt_ref not in index_of:
            print(f"  ABSENT  {label}")
            continue
        a, b = index_of[ot_ref], index_of[nt_ref]
        pairs.append((a, b, label))
        print(f"  {frame.label[a]:<22} « {frame.text_fr[a][:52]}… »")
        print(f"  {frame.label[b]:<22} « {frame.text_fr[b][:52]}… »\n")

    book = frame["book_id"].to_numpy()
    print(f"{len(pairs)} paires retenues, {len(base)} versets\n")
    print(f"{'ABTT':>5}  {'var. retirée':>12}  {'rang médian':>11}  "
          f"{'rang moyen':>10}  {'top-10':>6}  {'top-100':>7}  {'même livre':>10}")
    print("-" * 78)

    results = []
    for d in CANDIDATES:
        space = vec.abtt(base, d) if d else base
        removed = vec.explained_by_top(base, d) if d else 0.0

        ranks = np.array([min(vec.rank_of(space, a, b), vec.rank_of(space, b, a))
                          for a, b, _ in pairs])

        # gravité narrative sur un échantillon : part des 8 voisins du même livre
        rng = np.random.default_rng(0)
        sample = rng.choice(len(space), 1500, replace=False)
        same_book = []
        for i in sample:
            sim = space[i] @ space.T
            sim[i] = -np.inf
            top = np.argpartition(-sim, 8)[:8]
            same_book.append((book[top] == book[i]).mean())

        results.append((d, ranks, float(np.mean(same_book))))
        print(f"{d:>5}  {100 * removed:>11.1f}%  {np.median(ranks):>11.0f}  "
              f"{ranks.mean():>10.0f}  {(ranks <= 10).sum():>4}/{len(ranks)}  "
              f"{(ranks <= 100).sum():>5}/{len(ranks)}  "
              f"{100 * np.mean(same_book):>9.1f}%")

    best = min(results, key=lambda r: (np.median(r[1]), r[1].mean()))
    print(f"\nMeilleur rang médian : ABTT = {best[0]}")

    print("\nDétail par paire (rang : sans débruitage -> avec le meilleur réglage)")
    zero = next(r for r in results if r[0] == 0)
    for k, (_, _, label) in enumerate(pairs):
        print(f"  {int(zero[1][k]):>6} -> {int(best[1][k]):>6}   {label}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

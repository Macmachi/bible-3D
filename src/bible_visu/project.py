# © 2026 Rymentz — Bible 3D, visualisation sémantique de la Bible.
# Distribué sous licence CC BY-NC 4.0 — usage non commercial, voir LICENSE.
"""Étape 4 — projection 3D, regroupement et voisinage sémantique.

    python -m bible_visu.project

Trois calculs enchaînés :

1. **UMAP** ramène les 1024 dimensions du modèle à 3, en préservant au mieux la
   structure locale *et* globale (métrique cosinus).
2. **HDBSCAN** repère les amas de densité, sans imposer leur nombre à l'avance,
   et laisse hors amas les versets isolés (étiquette ``-1``) au lieu de les
   forcer quelque part. Chaque amas est nommé par ses termes TF-IDF dominants.
3. **Voisinage** : pour chaque verset, les ``k`` versets les plus proches dans
   toute la Bible, calculés sur les vecteurs *avant* réduction — donc sans la
   distorsion inévitable du passage en 3D.
"""

from __future__ import annotations

import argparse
import json
import re

import numpy as np
import pandas as pd

from . import paths

#: Mots-outils français exclus du nommage des amas.
STOPWORDS_FR = {
    "a", "afin", "ai", "aie", "ainsi", "alors", "apres", "après", "as", "au",
    "aucun", "aujourd", "auquel", "aura", "aurez", "aussi", "autre", "autres",
    "aux", "avaient", "avait", "avant", "avec", "avez", "avoir", "avons", "ayant",
    "beaucoup", "bien", "car", "ce", "ceci", "cela", "celle", "celles", "celui",
    "cent", "cependant", "certains", "ces", "cet", "cette", "ceux", "chacun",
    "chaque", "chez", "ci", "comme", "comment", "d", "dans", "de", "dedans",
    "dehors", "deja", "déjà", "depuis", "des", "desquels", "dessus", "deux",
    "devant", "doit", "donc", "dont", "du", "duquel", "elle", "elles", "en",
    "encore", "entre", "es", "est", "et", "etaient", "étaient", "etait", "était",
    "etant", "étant", "ete", "été", "etes", "êtes", "etre", "être", "eu", "eux",
    "fait", "faire", "fais", "fit", "font", "fur", "hors", "ici", "il", "ils",
    "j", "je", "jusqu", "jusque", "l", "la", "laquelle", "le", "lequel", "les",
    "lesquels", "leur", "leurs", "lors", "lorsque", "lui", "m", "ma", "mais",
    "me", "meme", "même", "mes", "mien", "moi", "moins", "mon", "n", "ne", "ni",
    "non", "nos", "notre", "nous", "on", "ont", "ou", "où", "oui", "par",
    "parce", "pas", "pendant", "peu", "peut", "plus", "plusieurs", "point",
    "pour", "pourquoi", "puis", "puisque", "qu", "quand", "que", "quel",
    "quelle", "quelles", "quels", "qui", "quoi", "s", "sa", "sans", "se",
    "selon", "sera", "seront", "ses", "si", "sien", "soi", "soit", "son",
    "sont", "sous", "sur", "t", "ta", "tandis", "tant", "te", "tel", "telle",
    "tes", "toi", "ton", "tous", "tout", "toute", "toutes", "tu", "un", "une",
    "va", "vers", "voici", "voila", "voilà", "vos", "votre", "vous", "vu", "y",
    "etc", "dit", "dire", "ait", "aient", "eut", "eurent", "firent", "furent",
}

TOKEN_RE = re.compile(r"(?u)\b[a-zà-öø-ÿ]{3,}\b")


def reduce_dimensions(vectors: np.ndarray, *, n_neighbors: int, min_dist: float,
                      pca_dims: int, seed: int) -> np.ndarray:
    """1024 dimensions -> 3, via une PCA de débruitage puis UMAP."""
    from sklearn.decomposition import PCA
    import umap

    if 0 < pca_dims < vectors.shape[1]:
        print(f"  PCA  {vectors.shape[1]} -> {pca_dims} dimensions…")
        pca = PCA(n_components=pca_dims, random_state=seed)
        vectors = pca.fit_transform(vectors).astype(np.float32)
        kept = float(pca.explained_variance_ratio_.sum())
        print(f"       variance conservée : {100 * kept:.1f} %")

    print(f"  UMAP -> 3 dimensions (n_neighbors={n_neighbors}, "
          f"min_dist={min_dist})…")
    reducer = umap.UMAP(
        n_components=3,
        n_neighbors=n_neighbors,
        min_dist=min_dist,
        metric="cosine",
        random_state=seed,     # reproductible (au prix du parallélisme)
        verbose=True,
    )
    return reducer.fit_transform(vectors).astype(np.float32)


def find_clusters(coords3d: np.ndarray, min_cluster_size: int) -> np.ndarray:
    from sklearn.cluster import HDBSCAN

    print(f"  HDBSCAN (min_cluster_size={min_cluster_size})…")
    labels = HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=5,
        cluster_selection_method="eom",
    ).fit_predict(coords3d)
    n_clusters = len({int(x) for x in labels} - {-1})
    noise = int((labels == -1).sum())
    print(f"       {n_clusters} amas, {noise} versets hors amas "
          f"({100 * noise / len(labels):.1f} %)")
    return labels


def name_clusters(texts: list[str], labels: np.ndarray,
                  top_n: int = 4) -> dict[int, str]:
    """Nomme chaque amas par ses termes les plus caractéristiques (TF-IDF)."""
    from sklearn.feature_extraction.text import TfidfVectorizer

    ids = sorted({int(x) for x in labels} - {-1})
    if not ids:
        return {}
    documents = []
    for cid in ids:
        mask = labels == cid
        documents.append(" ".join(t for t, m in zip(texts, mask) if m))

    vectorizer = TfidfVectorizer(
        lowercase=True,
        token_pattern=TOKEN_RE.pattern,
        stop_words=sorted(STOPWORDS_FR),
        max_df=0.6,
        sublinear_tf=True,
    )
    matrix = vectorizer.fit_transform(documents)
    vocabulary = np.array(vectorizer.get_feature_names_out())

    names: dict[int, str] = {}
    for row, cid in enumerate(ids):
        weights = matrix.getrow(row).toarray().ravel()
        best = np.argsort(weights)[::-1][:top_n]
        names[cid] = " · ".join(vocabulary[i] for i in best if weights[i] > 0)
    return names


def nearest_neighbours(vectors: np.ndarray, k: int,
                       chunk: int = 1024) -> tuple[np.ndarray, np.ndarray]:
    """Les ``k`` plus proches voisins de chaque verset (cosinus, hors soi-même).

    Les vecteurs étant normés, le produit scalaire *est* le cosinus. Le calcul
    est découpé pour ne jamais matérialiser la matrice 31170 x 31170.
    """
    n = vectors.shape[0]
    idx_out = np.empty((n, k), dtype=np.int32)
    sim_out = np.empty((n, k), dtype=np.float32)

    for start in range(0, n, chunk):
        stop = min(start + chunk, n)
        similarity = vectors[start:stop] @ vectors.T
        # neutralise la diagonale : un verset n'est pas son propre voisin
        rows = np.arange(stop - start)
        similarity[rows, np.arange(start, stop)] = -np.inf

        part = np.argpartition(-similarity, kth=k, axis=1)[:, :k]
        part_sim = np.take_along_axis(similarity, part, axis=1)
        order = np.argsort(-part_sim, axis=1)
        idx_out[start:stop] = np.take_along_axis(part, order, axis=1)
        sim_out[start:stop] = np.take_along_axis(part_sim, order, axis=1)
        print(f"       voisins {stop}/{n}", end="\r")
    print(" " * 40, end="\r")
    return idx_out, sim_out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-neighbors", type=int, default=25,
                        help="UMAP : petit = structure locale, grand = globale")
    parser.add_argument("--min-dist", type=float, default=0.02,
                        help="UMAP : compacité des amas")
    parser.add_argument("--pca-dims", type=int, default=64)
    parser.add_argument("--min-cluster-size", type=int, default=60)
    parser.add_argument("--neighbours", type=int, default=8)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--abtt-neighbours", type=int, default=8,
                        help="débruitage ABTT appliqué au calcul des voisins "
                             "(0 pour désactiver)")
    parser.add_argument("--abtt-layout", type=int, default=0,
                        help="débruitage ABTT appliqué à la disposition 3D — "
                             "déconseillé, cela efface les amas")
    args = parser.parse_args(argv)

    frame = pd.read_parquet(paths.VERSES)
    vectors = np.load(paths.EMBEDDINGS)
    if len(frame) != len(vectors):
        raise SystemExit(
            f"Incohérence : {len(frame)} versets mais {len(vectors)} vecteurs. "
            "Relance `python -m bible_visu.embed`.")
    meta = json.loads(paths.EMBEDDINGS_META.read_text(encoding="utf-8"))
    print(f"{len(frame)} versets, vecteurs {vectors.shape} ({meta['model']})\n")

    # Deux usages, deux espaces — c'est un résultat de mesure, pas une élégance.
    #
    # Le débruitage ABTT retire les directions communes à tout le corpus. Sur la
    # *recherche de voisins* il est très bénéfique : sur un étalon de citations
    # de l'AT dans le NT, il fait remonter Lévitique 19:18 ↔ Matthieu 22:39 du
    # rang 379 au rang 3. Mais appliqué à la *disposition*, il aplatit les
    # différences de densité dont HDBSCAN se nourrit : les 71 amas s'effondrent
    # en 4, dont un seul qui absorbe 94 % des versets.
    #
    # On garde donc l'espace brut pour dessiner la carte, et l'espace débruité
    # pour dire qui ressemble à qui.
    from .vectors import abtt, explained_by_top

    layout_vectors = vectors
    if args.abtt_layout:
        removed = explained_by_top(vectors, args.abtt_layout)
        layout_vectors = abtt(vectors, args.abtt_layout)
        print(f"  Débruitage de la disposition : {args.abtt_layout} directions "
              f"({100 * removed:.1f} % de variance) — attention aux amas")

    knn_vectors = vectors
    if args.abtt_neighbours:
        removed = explained_by_top(vectors, args.abtt_neighbours)
        knn_vectors = abtt(vectors, args.abtt_neighbours)
        print(f"  Débruitage du voisinage : {args.abtt_neighbours} directions "
              f"dominantes retirées ({100 * removed:.1f} % de la variance)")

    coords = reduce_dimensions(layout_vectors, n_neighbors=args.n_neighbors,
                               min_dist=args.min_dist, pca_dims=args.pca_dims,
                               seed=args.seed)

    # centrage + mise à l'échelle : le nuage tient dans une sphère de rayon ~100
    coords -= coords.mean(axis=0)
    coords *= 100.0 / np.percentile(np.linalg.norm(coords, axis=1), 99)

    labels = find_clusters(coords, args.min_cluster_size)
    names = name_clusters(frame["text_fr"].tolist(), labels)

    print(f"  Voisinage sémantique (k={args.neighbours})…")
    neighbour_idx, neighbour_sim = nearest_neighbours(knn_vectors, args.neighbours)

    frame["x"], frame["y"], frame["z"] = coords[:, 0], coords[:, 1], coords[:, 2]
    frame["cluster"] = labels.astype(np.int16)
    frame["cluster_label"] = [names.get(int(c), "hors amas") for c in labels]
    frame["neighbours"] = [row.tolist() for row in neighbour_idx]
    frame["neighbour_sim"] = [np.round(row, 4).tolist() for row in neighbour_sim]

    testament = frame["testament"].to_numpy()
    frame["nn_cross_testament"] = [
        int(sum(testament[j] != testament[i] for j in neighbour_idx[i]))
        for i in range(len(frame))
    ]

    frame.to_parquet(paths.POINTS, index=False)
    print(f"\n{len(frame)} points -> {paths.POINTS}")

    print("\nAmas les plus peuplés :")
    sizes = frame.loc[frame.cluster >= 0].groupby("cluster", observed=True).size()
    for cid, size in sizes.sort_values(ascending=False).head(15).items():
        dominant = frame.loc[frame.cluster == cid, "book"].mode()
        book = dominant.iloc[0] if len(dominant) else "?"
        print(f"  #{cid:<3} {size:>5} versets  [{book:<22}] {names.get(int(cid), '')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

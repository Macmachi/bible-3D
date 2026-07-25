# © 2026 Rymentz — Bible 3D, visualisation sémantique de la Bible.
# Distribué sous licence CC BY-NC 4.0 — usage non commercial, voir LICENSE.
"""Traitements appliqués à l'espace vectoriel avant projection.

Le seul traitement ici est ``abtt`` — *All-but-the-Top* (Mu & Viswanath, ICLR
2018). Les vecteurs de phrases ne sont pas centrés : quelques directions
dominantes, communes à tout le corpus, encodent la langue, le registre et le
style narratif plutôt que le contenu. Elles écrasent les similarités et tirent
chaque verset vers la masse de son propre livre.

Le remède tient en trois gestes : centrer, retirer les ``d`` premières
composantes principales, renormer.

**À vérifier, pas à croire.** Ce traitement peut aussi détruire du signal utile.
``scripts/evaluate_abtt.py`` mesure son effet sur un étalon de citations
vétérotestamentaires dans le Nouveau Testament, dont la correspondance est
connue. Voir le README pour le résultat obtenu ici.
"""

from __future__ import annotations

import numpy as np


def abtt(vectors: np.ndarray, n_components: int) -> np.ndarray:
    """Centre, retire les ``n_components`` directions dominantes, renorme.

    ``vectors`` doit être de forme ``(n, d)``. Le résultat est de même forme,
    à lignes de norme 1 — le produit scalaire reste donc le cosinus.
    """
    if n_components <= 0:
        return vectors.astype(np.float32, copy=True)

    centred = vectors.astype(np.float32) - vectors.mean(axis=0, dtype=np.float32)

    # SVD tronquée : on ne veut que les premières directions principales
    from sklearn.decomposition import PCA
    pca = PCA(n_components=n_components, svd_solver="randomized", random_state=0)
    pca.fit(centred)
    directions = pca.components_.astype(np.float32)          # (d_comp, d)

    # retrait des projections sur chaque direction dominante
    cleaned = centred - (centred @ directions.T) @ directions

    norms = np.linalg.norm(cleaned, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return (cleaned / norms).astype(np.float32)


def explained_by_top(vectors: np.ndarray, n_components: int) -> float:
    """Part de variance portée par les ``n_components`` premières directions."""
    from sklearn.decomposition import PCA
    pca = PCA(n_components=n_components, svd_solver="randomized", random_state=0)
    pca.fit(vectors - vectors.mean(axis=0))
    return float(pca.explained_variance_ratio_.sum())


def rank_of(vectors: np.ndarray, source: int, target: int) -> int:
    """Rang de ``target`` dans le classement de similarité vu depuis ``source``.

    Rang 1 = plus proche voisin. Le verset lui-même est exclu.
    """
    similarity = vectors @ vectors[source]
    similarity[source] = -np.inf
    return int((similarity > similarity[target]).sum()) + 1

# © 2026 Rymentz — Bible 3D, visualisation sémantique de la Bible.
# Distribué sous licence CC BY-NC 4.0 — usage non commercial, voir LICENSE.
"""Étape 3 — vecteurs sémantiques, un par verset.

    python -m bible_visu.embed                # modèle par défaut
    python -m bible_visu.embed --limit 500    # test de vitesse sur un échantillon

Le sens est calculé sur le **français** (Segond 1910), pas sur l'hébreu ni le
grec : aucun modèle d'embedding de phrases n'est entraîné sur l'hébreu biblique
ou le grec koinè, et les employer produirait une carte sans signification. Les
versets étant alignés 1:1, la carte reste attachée au texte original, qui est
affiché dans la visualisation.

``--text-column text_orig`` permet malgré tout de calculer une carte sur le
texte source, pour comparer les deux — c'est le protocole décrit dans le README.

``--text-column text_en`` calcule la seconde carte du visualiseur, celle de la
World English Bible. Elle n'est pas une traduction de la carte française : c'est
une autre carte, et les écarts entre les deux sont précisément ce qu'elles ont à
montrer.

Les poids sont mis en cache dans ``data/models/``, jamais dans ``~/.cache``.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from . import paths

# Doit précéder l'import de sentence_transformers : tout reste dans le projet.
paths.ensure_dirs()
os.environ.setdefault("HF_HOME", str(paths.MODELS))
os.environ.setdefault("SENTENCE_TRANSFORMERS_HOME", str(paths.MODELS))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

DEFAULT_MODEL = "intfloat/multilingual-e5-large"

#: Les modèles E5 exigent un préfixe ; pour une tâche symétrique c'est ``query:``.
E5_PREFIX = "query: "


def needs_e5_prefix(model_name: str) -> bool:
    return "e5" in model_name.lower()


def load_texts(column: str) -> tuple[pd.DataFrame, list[str]]:
    """Les textes d'une colonne, les trous comblés par le français.

    120 versets n'ont pas de texte anglais, 139 pas de texte original. Les
    encoder à vide serait la pire des solutions : la chaîne vide produit un
    vecteur, toujours le même, si bien que ces versets deviendraient
    identiques entre eux et se retrouveraient tous voisins parfaits les uns
    des autres, au milieu d'un amas dense qui ne dit rien. On retombe donc sur
    le Segond, qui les place au moins selon leur sens ; le compte est affiché
    pour que la carte ne prétende pas être plus pure qu'elle n'est.
    """
    frame = pd.read_parquet(paths.VERSES)
    texts = frame[column].fillna("").astype(str).tolist()
    if column != "text_fr":
        fallback = frame["text_fr"].fillna("").astype(str).tolist()
        holes = [i for i, text in enumerate(texts) if not text.strip()]
        for i in holes:
            texts[i] = fallback[i]
        if holes:
            print(f"{len(holes)} versets sans {column} : "
                  f"repliés sur text_fr")
    return frame, texts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--basis", default="fr", choices=list(paths.BASES),
                        help="texte de référence de la carte (défaut : fr)")
    parser.add_argument("--text-column", default=None,
                        choices=["text_fr", "text_en", "text_orig"],
                        help="colonne à encoder ; déduite de --basis si absente")
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--limit", type=int, default=0,
                        help="n'encoder que les N premiers versets (banc d'essai)")
    parser.add_argument("--out", default=None,
                        help="chemin .npy de sortie (défaut : data/processed/)")
    args = parser.parse_args(argv)

    from sentence_transformers import SentenceTransformer

    column = args.text_column or paths.BASIS_COLUMN[args.basis]
    frame, texts = load_texts(column)
    if args.limit:
        texts = texts[: args.limit]

    print(f"Modèle       : {args.model}")
    print(f"Base         : {args.basis}")
    print(f"Colonne      : {column}")
    print(f"Versets      : {len(texts)}")

    started = time.perf_counter()
    model = SentenceTransformer(args.model, cache_folder=str(paths.MODELS))
    print(f"Chargé en {time.perf_counter() - started:.1f} s "
          f"(dimension {model.get_sentence_embedding_dimension()})")

    payload = ([E5_PREFIX + t for t in texts] if needs_e5_prefix(args.model)
               else texts)

    started = time.perf_counter()
    vectors = model.encode(
        payload,
        batch_size=args.batch_size,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,   # cosinus == produit scalaire par la suite
    ).astype(np.float32)
    elapsed = time.perf_counter() - started

    print(f"\nEncodé {len(texts)} versets en {elapsed:.1f} s "
          f"({len(texts) / elapsed:.1f} versets/s)")
    if args.limit:
        full = len(frame)
        print(f"Extrapolation sur {full} versets : "
              f"{full / (len(texts) / elapsed) / 60:.1f} min")

    # Les métadonnées suivent le fichier de vecteurs : une carte anglaise
    # écrasant embeddings.json ferait croire à `project` et à `serve` que le
    # corpus français a été ré-encodé.
    out = paths.embeddings(args.basis) if args.out is None else Path(args.out)
    meta_path = (paths.embeddings_meta(args.basis) if args.out is None
                 else out.with_suffix(".json"))
    if args.limit:
        print("\n(--limit actif : rien n'est écrit sur disque)")
        return 0

    np.save(out, vectors)
    meta = {
        "model": args.model,
        "basis": args.basis,
        "text_column": column,
        "dimension": int(vectors.shape[1]),
        "count": int(vectors.shape[0]),
        "normalized": True,
        "seconds": round(elapsed, 1),
    }
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False),
                         encoding="utf-8")
    print(f"\n{vectors.shape} -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

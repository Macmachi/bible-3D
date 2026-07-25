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

Les poids sont mis en cache dans ``data/models/``, jamais dans ``~/.cache``.
"""

from __future__ import annotations

import argparse
import json
import os
import time

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
    frame = pd.read_parquet(paths.VERSES)
    texts = frame[column].fillna("").astype(str).tolist()
    return frame, texts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--text-column", default="text_fr",
                        choices=["text_fr", "text_orig"])
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--limit", type=int, default=0,
                        help="n'encoder que les N premiers versets (banc d'essai)")
    parser.add_argument("--out", default=None,
                        help="chemin .npy de sortie (défaut : data/processed/)")
    args = parser.parse_args(argv)

    from sentence_transformers import SentenceTransformer

    frame, texts = load_texts(args.text_column)
    if args.limit:
        texts = texts[: args.limit]

    print(f"Modèle       : {args.model}")
    print(f"Colonne      : {args.text_column}")
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

    out = paths.EMBEDDINGS if args.out is None else __import__("pathlib").Path(args.out)
    if args.limit:
        print("\n(--limit actif : rien n'est écrit sur disque)")
        return 0

    np.save(out, vectors)
    meta = {
        "model": args.model,
        "text_column": args.text_column,
        "dimension": int(vectors.shape[1]),
        "count": int(vectors.shape[0]),
        "normalized": True,
        "seconds": round(elapsed, 1),
    }
    paths.EMBEDDINGS_META.write_text(json.dumps(meta, indent=2, ensure_ascii=False),
                                     encoding="utf-8")
    print(f"\n{vectors.shape} -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

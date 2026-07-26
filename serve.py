#!/usr/bin/env python3
# © 2026 Rymentz — Bible 3D, visualisation sémantique de la Bible.
# Distribué sous licence CC BY-NC 4.0 — usage non commercial, voir LICENSE.
"""Sert le visualiseur en local et ouvre le navigateur.

    python serve.py [--port 8000] [--no-browser]

Un serveur HTTP est nécessaire : ouvrir ``viewer/index.html`` directement avec
``file://`` échoue, les navigateurs refusant de charger les modules ES et les
fichiers de données depuis le système de fichiers.
"""

from __future__ import annotations

import argparse
import functools
import http.server
import io
import json
import os
import socketserver
import sys
import threading
import time
import traceback
import urllib.parse
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VIEWER = ROOT / "viewer"


class ThemeEngine:
    """Recherche par thème : encode une phrase et la compare aux 31 170 versets.

    Le modèle pèse deux gigaoctets et met environ une minute à se charger. On ne
    le charge donc qu'à la première requête, une seule fois, sous verrou — les
    requêtes suivantes répondent en une fraction de seconde.

    Si `sentence-transformers` n'est pas installé, ou si les vecteurs du corpus
    manquent, le service se déclare simplement indisponible : le reste du
    visualiseur continue de fonctionner sans lui.

    Une similarité n'a de sens que dans l'espace où elle est mesurée. Le
    visualiseur pouvant afficher deux cartes, chacune calculée sur son texte,
    la requête est comparée aux vecteurs de la carte regardée — et non à ceux
    du français quoi qu'il arrive, ce qui colorierait la carte anglaise avec
    des ressemblances établies ailleurs.
    """

    #: Une requête plus longue n'apporte rien et n'a pas à être encodée.
    MAX_QUERY = 200

    #: Fichier de vecteurs par base, tel que `bible_visu.embed` les nomme.
    FILES = {"fr": "embeddings", "en": "embeddings_en"}

    def __init__(self, root: Path) -> None:
        self.root = root
        self._lock = threading.Lock()
        self._model = None
        self._vectors: dict[str, object] = {}
        self._model_name = None
        self.error: str | None = None
        self.bases: list[str] = []

        processed = root / "data" / "processed"
        for basis, stem in self.FILES.items():
            meta_path = processed / f"{stem}.json"
            vectors_path = processed / f"{stem}.npy"
            if not (meta_path.exists() and vectors_path.exists()):
                continue
            try:
                name = json.loads(meta_path.read_text(encoding="utf-8"))["model"]
            except (OSError, ValueError, KeyError) as exc:
                # Le détail va sur la console, pas dans la réponse HTTP : le
                # message d'une OSError contient le chemin absolu du fichier,
                # donc le nom d'utilisateur et toute l'arborescence au-dessus
                # du projet.
                print(f"  {meta_path.name} illisible : {exc}", file=sys.stderr)
                continue
            # Un seul modèle est chargé en mémoire : deux bases encodées par
            # deux modèles différents ne se compareraient de toute façon pas.
            if self._model_name is None:
                self._model_name = name
            elif name != self._model_name:
                print(f"  base « {basis} » encodée par {name}, ignorée",
                      file=sys.stderr)
                continue
            self.bases.append(basis)

        if not self.bases:
            self.error = "vecteurs du corpus absents (lance `bible_visu.embed`)"

    @property
    def available(self) -> bool:
        return self.error is None

    def _ensure_loaded(self, basis: str) -> None:
        if self._model is None:
            # tout reste dans le projet, comme pour le reste du pipeline
            models = self.root / "data" / "models"
            os.environ.setdefault("HF_HOME", str(models))
            os.environ.setdefault("SENTENCE_TRANSFORMERS_HOME", str(models))
            from sentence_transformers import SentenceTransformer

            print(f"  chargement du modèle {self._model_name}… (une seule fois)")
            started = time.perf_counter()
            self._model = SentenceTransformer(self._model_name,
                                              cache_folder=str(models))
            print(f"  modèle prêt en {time.perf_counter() - started:.0f} s")

        if basis not in self._vectors:
            import numpy

            path = self.root / "data" / "processed" / f"{self.FILES[basis]}.npy"
            started = time.perf_counter()
            self._vectors[basis] = numpy.load(path)
            print(f"  vecteurs « {basis} » chargés en "
                  f"{time.perf_counter() - started:.1f} s "
                  f"({len(self._vectors[basis])} versets)")

    def similarities(self, query: str, basis: str = "fr") -> bytes:
        """Renvoie un Float32Array : une similarité cosinus par verset."""
        import numpy

        if basis not in self.bases:
            raise KeyError(basis)
        with self._lock:
            self._ensure_loaded(basis)
            # même préfixe et même normalisation que lors de l'encodage du
            # corpus, faute de quoi les similarités ne seraient pas comparables
            payload = (f"query: {query}"
                       if "e5" in (self._model_name or "").lower() else query)
            vector = self._model.encode([payload], convert_to_numpy=True,
                                        normalize_embeddings=True)[0]
            scores = (self._vectors[basis] @ vector).astype(numpy.float32)
        return scores.tobytes()


class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {
        **http.server.SimpleHTTPRequestHandler.extensions_map,
        ".js": "text/javascript",
        ".json": "application/json",
        ".bin": "application/octet-stream",
    }

    #: Injecté par main(). Aucun état global mutable dans le gestionnaire.
    theme_engine: ThemeEngine | None = None

    def do_GET(self) -> None:  # noqa: N802 (nom imposé par la classe de base)
        parsed = urllib.parse.urlsplit(self.path)
        if parsed.path == "/api/theme":
            self.handle_theme(parsed.query)
            return
        if parsed.path == "/api/status":
            engine = self.theme_engine
            self.send_json({"theme": bool(engine and engine.available),
                            "bases": engine.bases if engine else [],
                            "reason": engine.error if engine else "non configuré"})
            return
        super().do_GET()

    def send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def handle_theme(self, query_string: str) -> None:
        engine = self.theme_engine
        if engine is None or not engine.available:
            self.send_json({"error": engine.error if engine else "non configuré"},
                           503)
            return

        params = urllib.parse.parse_qs(query_string)
        query = (params.get("q") or [""])[0].strip()
        if not query:
            self.send_json({"error": "paramètre q vide"}, 400)
            return
        if len(query) > ThemeEngine.MAX_QUERY:
            self.send_json({"error": f"requête trop longue "
                                     f"(max {ThemeEngine.MAX_QUERY} caractères)"}, 413)
            return
        # Une base inconnue n'est pas rattrapée en silence : répondre avec les
        # similarités du français ferait colorier la carte anglaise par des
        # ressemblances mesurées ailleurs, sans que rien ne le signale.
        basis = (params.get("basis") or ["fr"])[0].strip() or "fr"
        if basis not in engine.bases:
            self.send_json({"error": f"base « {basis} » non encodée"}, 404)
            return

        try:
            payload = engine.similarities(query, basis)
        except Exception as exc:  # noqa: BLE001 — on ne tue pas le serveur
            # Même règle que plus haut : la trace complète reste locale. Une
            # erreur de chargement de modèle cite le dossier de cache, et ce
            # message finirait affiché dans l'interface — donc dans une capture
            # d'écran ou un rapport de bogue.
            traceback.print_exc()
            self.send_json({"error": "échec de l'encodage — voir la console "
                                     "du serveur"}, 500)
            return

        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def send_head(self):
        """Sert la version .gz quand elle existe et que le client l'accepte.

        `verses.json` pèse 21 Mo, sa version compressée 5,8 Mo. Le navigateur
        décompresse lui-même grâce à l'en-tête Content-Encoding, sans une ligne
        de JavaScript. Le fichier non compressé reste servi tel quel aux clients
        qui ne demandent pas gzip.
        """
        if "gzip" in self.headers.get("Accept-Encoding", ""):
            path = self.translate_path(self.path)
            packed = Path(path + ".gz")
            # `translate_path` a déjà neutralisé les remontées de répertoire
            if Path(path).is_file() and packed.is_file():
                try:
                    payload = packed.read_bytes()
                except OSError:
                    return super().send_head()
                self.send_response(200)
                self.send_header("Content-Type", self.guess_type(path))
                self.send_header("Content-Encoding", "gzip")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                return io.BytesIO(payload)
        return super().send_head()

    def end_headers(self) -> None:
        # les données changent à chaque relance du pipeline
        self.send_header("Cache-Control", "no-store")
        # durcissement : la page n'a besoin d'aucune ressource externe
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; connect-src 'self'; base-uri 'none'; "
            "form-action 'none'; frame-ancestors 'none'")
        super().end_headers()

    def log_message(self, fmt, *args) -> None:
        if "304" not in fmt % args:
            sys.stderr.write(f"  {fmt % args}\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args(argv)

    data = VIEWER / "data" / "verses.json"
    if not data.exists():
        print("Données absentes. Exécute d'abord :\n"
              "  python -m bible_visu.fetch\n"
              "  python -m bible_visu.corpus\n"
              "  python -m bible_visu.embed\n"
              "  python -m bible_visu.project\n"
              "  python -m bible_visu.crossrefs\n"
              "  python -m bible_visu.axes\n"
              "  python -m bible_visu.export", file=sys.stderr)
        return 1

    Handler.theme_engine = ThemeEngine(ROOT)
    if Handler.theme_engine.available:
        print("Recherche par thème : disponible "
              "(le modèle se charge à la première requête)")
    else:
        print(f"Recherche par thème : indisponible — {Handler.theme_engine.error}")

    handler = functools.partial(Handler, directory=str(VIEWER))
    # un serveur à fil unique se figerait pendant la minute de chargement du
    # modèle, y compris pour les fichiers statiques
    class Server(socketserver.ThreadingTCPServer):
        daemon_threads = True
        allow_reuse_address = True

    with Server(("127.0.0.1", args.port), handler) as httpd:
        url = f"http://127.0.0.1:{args.port}/"
        print(f"Visualiseur sur {url}   (Ctrl+C pour arrêter)")
        if not args.no_browser:
            threading.Timer(0.5, webbrowser.open, args=(url,)).start()
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nArrêté.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

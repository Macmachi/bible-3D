# © 2026 Rymentz — Bible 3D, visualisation sémantique de la Bible.
# Distribué sous licence CC BY-NC 4.0 — usage non commercial, voir LICENSE.
"""Étape 6 — axes thématiques nommés.

    python -m bible_visu.axes

La carte UMAP a un défaut irréductible : **ses axes ne signifient rien**. On peut
lire des voisinages, pas des positions. Ce module construit l'alternative : des
axes dont on choisit le sens à l'avance.

Le principe tient en trois lignes. Chaque pôle d'un axe est défini par une
poignée de phrases d'ancrage — non pas des mots isolés, mais des formulations
proches de celles de la Bible. On encode ces phrases avec le modèle qui a servi
au corpus, on prend la moyenne de chaque pôle, et **l'axe est la différence des
deux moyennes**. Chaque verset se projette dessus par un simple produit scalaire.

Cette soustraction n'est pas un détail : elle annule la composante commune à
toutes les phrases françaises — la langue, le registre, le style biblique — et ne
laisse que ce qui distingue un pôle de l'autre. C'est précisément ce qui manquait
aux amas, qui restent lexicaux parce que rien n'y soustrait le fond commun.

**À vérifier, pas à croire.** Un axe mal ancré produit un classement d'apparence
crédible mais vide de sens. Le script affiche donc, pour chaque axe, les versets
extrêmes de chaque pôle : si on ne reconnaît pas le thème en les lisant, l'axe
est mauvais et ses ancrages sont à revoir.
"""

from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd

from . import paths

#: Les ancrages sont en français, comme le texte qui a servi au calcul.
#: Chaque pôle vaut par la variété de ses formulations, pas par leur nombre.
AXES: tuple[dict, ...] = (
    {
        "id": "jugement_misericorde",
        "fr": "Jugement ↔ Miséricorde",
        "en": "Judgement ↔ Mercy",
        "neg_fr": "jugement", "neg_en": "judgement",
        "pos_fr": "miséricorde", "pos_en": "mercy",
        "neg": [
            "La colère de l'Éternel s'enflamma contre le peuple.",
            "Je les châtierai pour leurs iniquités et leurs péchés.",
            "Le jour de la colère, jour de détresse et d'angoisse.",
            "Il exercera la vengeance contre les nations rebelles.",
            "Vous serez livrés à l'épée et à la famine.",
            "Malheur à vous, car votre ruine est proche.",
        ],
        "pos": [
            "L'Éternel est miséricordieux et compatissant, lent à la colère.",
            "Il pardonne toutes tes iniquités et guérit toutes tes maladies.",
            "Sa bonté dure à toujours, sa compassion ne s'épuise pas.",
            "Je leur pardonnerai et ne me souviendrai plus de leur péché.",
            "Il a pitié du pauvre et relève celui qui est abattu.",
            "Que ta grâce soit sur nous, comme nous espérons en toi.",
        ],
    },
    {
        "id": "loi_grace",
        "fr": "Loi et commandement ↔ Grâce et don",
        "en": "Law and commandment ↔ Grace and gift",
        "neg_fr": "loi", "neg_en": "law",
        "pos_fr": "grâce", "pos_en": "grace",
        "neg": [
            "Tu observeras tous les commandements que je te prescris aujourd'hui.",
            "Voici les ordonnances et les statuts que vous mettrez en pratique.",
            "Quiconque transgressera cette loi sera retranché du peuple.",
            "Il est écrit dans la loi de Moïse : tu ne feras point cela.",
            "Vous garderez mes préceptes et vous les accomplirez.",
        ],
        # Premiers ancrages trop vagues : le pôle remontait n'importe quel verset
        # du Nouveau Testament, et l'axe doublait simplement le mode Testament.
        # Il faut nommer la grâce, pas seulement évoquer le contexte chrétien.
        "pos": [
            "C'est par la grâce que vous êtes sauvés, et cela ne vient pas de vous.",
            "Nous sommes justifiés gratuitement par sa grâce, sans les œuvres.",
            "Là où le péché a abondé, la grâce a surabondé bien davantage.",
            "Vous n'êtes plus sous la loi, mais sous la grâce.",
            "Le don gratuit de Dieu, c'est la vie éternelle, non un salaire.",
            "L'homme est justifié par la foi, sans les œuvres de la loi.",
        ],
    },
    {
        "id": "recit_doctrine",
        "fr": "Récit et événement ↔ Enseignement et doctrine",
        "en": "Narrative and event ↔ Teaching and doctrine",
        "neg_fr": "récit", "neg_en": "narrative",
        "pos_fr": "enseignement", "pos_en": "teaching",
        "neg": [
            "Il se leva de bon matin, sella son âne et partit.",
            "Ils campèrent près de la ville et y demeurèrent trois jours.",
            "Le roi envoya des messagers vers lui, et ils revinrent.",
            "Alors il entra dans la maison et s'assit à table.",
            "Ils marchèrent depuis ce lieu jusqu'à la vallée.",
        ],
        "pos": [
            "Car nous savons que toute chose concourt au bien de ceux qui aiment.",
            "Or la foi est une ferme assurance des choses qu'on espère.",
            "C'est pourquoi je vous exhorte à marcher d'une manière digne.",
            "Voici en quoi consiste l'amour : non que nous ayons aimé Dieu.",
            "Ainsi donc, il n'y a plus de condamnation pour ceux qui croient.",
        ],
    },
    {
        "id": "souffrance_louange",
        "fr": "Souffrance et plainte ↔ Louange et joie",
        "en": "Suffering and lament ↔ Praise and joy",
        "neg_fr": "plainte", "neg_en": "lament",
        "pos_fr": "louange", "pos_en": "praise",
        "neg": [
            "Jusques à quand, Éternel, m'oublieras-tu sans cesse ?",
            "Mes larmes sont ma nourriture le jour et la nuit.",
            "Mon âme est abattue au dedans de moi, je gémis.",
            "Pourquoi m'as-tu abandonné, et te tiens-tu loin de mon secours ?",
            "Je suis accablé de douleur, mes forces m'ont quitté.",
        ],
        # Ancrages resserrés sur le chant et l'acclamation : les premiers
        # laissaient remonter les salutations finales des épîtres, sémantiquement
        # proches d'une bénédiction mais qui ne sont pas de la louange.
        "pos": [
            "Louez l'Éternel, célébrez son nom, publiez ses hauts faits !",
            "Chantez à l'Éternel un cantique nouveau, jouez de la harpe.",
            "Poussez vers Dieu des cris de joie, toute la terre !",
            "Que tout ce qui respire loue l'Éternel ! Alléluia !",
            "Mon cœur est dans l'allégresse, ma langue chante ta justice.",
            "Je te célébrerai de tout mon cœur, je raconterai tes merveilles.",
        ],
    },
    {
        "id": "culte_justice",
        "fr": "Culte et rituel ↔ Justice envers autrui",
        "en": "Worship and ritual ↔ Justice toward others",
        "neg_fr": "rituel", "neg_en": "ritual",
        "pos_fr": "justice", "pos_en": "justice",
        "neg": [
            "Tu offriras un holocauste sans défaut sur l'autel.",
            "Le sacrificateur fera l'aspersion du sang tout autour.",
            "Il brûlera l'encens du parfum devant l'Éternel.",
            "Vous célébrerez cette fête au septième mois, selon l'ordonnance.",
            "L'agneau sera sans défaut, mâle, âgé d'un an.",
        ],
        "pos": [
            "Fais droit à l'orphelin, défends la cause de la veuve.",
            "Ne fais pas violence à l'étranger qui séjourne chez toi.",
            "Ce que je désire, c'est la bonté et non les sacrifices.",
            "Partage ton pain avec celui qui a faim, vêts celui qui est nu.",
            "Ne fais point d'injustice dans la mesure ni dans le poids.",
        ],
    },
    {
        "id": "present_eschatologie",
        "fr": "Temps présent ↔ Fin et espérance",
        "en": "Present time ↔ End and hope",
        "neg_fr": "présent", "neg_en": "present",
        "pos_fr": "fin des temps", "pos_en": "end times",
        "neg": [
            "En ce temps-là, il régnait sur le pays et sur tout le peuple.",
            "Aujourd'hui même, faites ce que je vous commande.",
            "Ils bâtirent la ville et l'habitèrent jusqu'à ce jour.",
            "Il vécut de nombreuses années et vit ses fils et ses petits-fils.",
        ],
        "pos": [
            "Il y aura de nouveaux cieux et une nouvelle terre.",
            "En ces jours-là, le soleil s'obscurcira et les étoiles tomberont.",
            "Les morts ressusciteront et la trompette sonnera.",
            "Je vis un trône dressé, et celui qui était assis dessus.",
            "Alors viendra la fin, quand toute domination sera anéantie.",
        ],
    },
    {
        "id": "individu_peuple",
        "fr": "Individu ↔ Peuple et nation",
        "en": "Individual ↔ People and nation",
        "neg_fr": "individu", "neg_en": "individual",
        "pos_fr": "peuple", "pos_en": "people",
        "neg": [
            "Mon âme, bénis l'Éternel, et n'oublie aucun de ses bienfaits.",
            "Sonde-moi, ô Dieu, et connais mon cœur.",
            "Il s'en alla seul dans la montagne pour prier.",
            "Que ferai-je, moi, pour hériter la vie éternelle ?",
        ],
        "pos": [
            "Toute l'assemblée d'Israël se rassembla comme un seul homme.",
            "Les nations se soulèveront contre les nations et les royaumes.",
            "Ainsi parle l'Éternel à la maison de Jacob et au peuple entier.",
            "Vous serez pour moi un royaume de sacrificateurs, une nation sainte.",
        ],
    },
    {
        "id": "guerre_paix",
        "fr": "Guerre et conflit ↔ Paix et réconciliation",
        "en": "War and conflict ↔ Peace and reconciliation",
        "neg_fr": "guerre", "neg_en": "war",
        "pos_fr": "paix", "pos_en": "peace",
        "neg": [
            "Ils sortirent en bataille contre l'ennemi et le frappèrent.",
            "L'épée dévora et le sang coula sur la terre.",
            "Prépare la guerre, réveille les vaillants hommes.",
            "La ville fut prise, ses murailles renversées et brûlées.",
        ],
        "pos": [
            "Ils forgeront de leurs épées des socs de charrue.",
            "Heureux ceux qui procurent la paix, car ils seront appelés fils de Dieu.",
            "Que la paix soit avec vous, je vous laisse ma paix.",
            "Ils se réconcilièrent et firent alliance ensemble.",
        ],
    },
)


def _self_check() -> None:
    ids = [a["id"] for a in AXES]
    assert len(ids) == len(set(ids)), "identifiants d'axes en double"
    for axis in AXES:
        assert len(axis["neg"]) >= 4 and len(axis["pos"]) >= 4, axis["id"]
        for key in ("fr", "en", "neg_fr", "pos_fr", "neg_en", "pos_en"):
            assert axis[key], (axis["id"], key)


_self_check()


def build(model_name: str, batch_size: int = 16) -> dict:
    from .embed import E5_PREFIX, needs_e5_prefix
    from sentence_transformers import SentenceTransformer

    frame = pd.read_parquet(paths.VERSES)
    embeddings = np.load(paths.EMBEDDINGS)
    if len(frame) != len(embeddings):
        raise SystemExit("verses.parquet et embeddings.npy sont désynchronisés.")

    print(f"Modèle : {model_name}")
    model = SentenceTransformer(model_name, cache_folder=str(paths.MODELS))

    sentences: list[str] = []
    for axis in AXES:
        sentences.extend(axis["neg"])
        sentences.extend(axis["pos"])
    payload = ([E5_PREFIX + s for s in sentences] if needs_e5_prefix(model_name)
               else sentences)
    print(f"Encodage de {len(sentences)} phrases d'ancrage…")
    anchors = model.encode(payload, batch_size=batch_size, convert_to_numpy=True,
                           normalize_embeddings=True).astype(np.float32)

    scores = np.zeros((len(frame), len(AXES)), dtype=np.float32)
    cursor = 0
    for column, axis in enumerate(AXES):
        n_neg, n_pos = len(axis["neg"]), len(axis["pos"])
        negative = anchors[cursor:cursor + n_neg].mean(axis=0)
        positive = anchors[cursor + n_neg:cursor + n_neg + n_pos].mean(axis=0)
        cursor += n_neg + n_pos

        # la différence des deux pôles annule ce qu'ils ont en commun :
        # la langue, le registre, le style biblique
        direction = positive - negative
        direction /= np.linalg.norm(direction)

        raw = embeddings @ direction
        # Échelle robuste : le 99,5e centile de la valeur absolue vaut 1. Un
        # centile plus bas saturerait des centaines de versets à ±1 et écraserait
        # la nuance là où elle est justement la plus intéressante.
        scale = np.percentile(np.abs(raw), 99.5) or 1.0
        scores[:, column] = np.clip(raw / scale, -1.0, 1.0)

    return {"frame": frame, "scores": scores}


def report(frame: pd.DataFrame, scores: np.ndarray, top: int = 4) -> None:
    """Affiche les versets extrêmes de chaque pôle — le contrôle qui compte."""
    for column, axis in enumerate(AXES):
        values = scores[:, column]
        print(f"\n{'═' * 76}\n{axis['fr']}")
        for label, order in ((axis["neg_fr"], np.argsort(values)),
                             (axis["pos_fr"], np.argsort(-values))):
            print(f"\n  ── pôle « {label} » ──")
            for i in order[:top]:
                print(f"    {values[i]:+.2f}  {frame.label[i]:<24} "
                      f"{frame.text_fr[i][:64]}")


def main(argv: list[str] | None = None) -> int:
    from .embed import DEFAULT_MODEL

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--top", type=int, default=4,
                        help="versets extrêmes affichés par pôle")
    args = parser.parse_args(argv)

    paths.ensure_dirs()
    built = build(args.model)
    frame, scores = built["frame"], built["scores"]

    np.savez_compressed(paths.AXES, scores=scores,
                        ids=np.array([a["id"] for a in AXES]))
    meta = [{k: a[k] for k in ("id", "fr", "en", "neg_fr", "pos_fr",
                               "neg_en", "pos_en")} for a in AXES]
    paths.AXES.with_suffix(".json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    report(frame, scores, args.top)
    print(f"\n{scores.shape[1]} axes × {scores.shape[0]} versets -> {paths.AXES}")
    print("\nLis les versets ci-dessus : si un pôle ne ressemble pas à son "
          "intitulé,\nl'axe est mal ancré — corrige ses phrases dans axes.py.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

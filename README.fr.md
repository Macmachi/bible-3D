# Bible 3D — visualisation sémantique

[English](README.md) · **Français**

### → [Ouvrir la carte en ligne](https://macmachi.github.io/bible-3D/)

*31 170 versets dans le navigateur, rien à installer. Fonctionne hors ligne une
fois chargée.*

Les **31 170 versets** de la Bible placés dans un espace tridimensionnel **selon
ce qu'ils veulent dire**, et non selon leur position dans le livre. Deux versets
voisins à l'écran parlent de la même chose, même s'ils sont séparés par mille
pages et deux langues.

Quatre textes en regard : **hébreu massorétique** (Westminster Leningrad Codex),
**grec** (SBLGNT), **français** (Louis Segond 1910) et **anglais** (World English
Bible). Interface en français et en anglais.

Aucune connaissance n'est donnée à la machine : elle ignore les livres, les
auteurs, les genres et la chronologie. Elle ne voit que du texte. Tout
regroupement visible a donc été **trouvé**, pas imposé.

![La carte sémantique : les 31 170 versets colorés par Testament, un verset
sélectionné avec ses voisins par le sens](docs/carte.png)

*Le bleu est l'Ancien Testament, le rouge le Nouveau. Là où les deux se mêlent,
les deux Testaments traitent du même sujet. Le verset consulté, Matthieu 6:12,
a été trouvé en décrivant une idée — « le pardon des offenses » — et non en
cherchant un mot.*

---

## Table des matières

- [Démarrage](#démarrage)
- [Ce que l'on voit](#ce-que-lon-voit)
- [Méthode : du texte aux coordonnées](#méthode--du-texte-aux-coordonnées)
- [Quatre décisions de méthode](#quatre-décisions-de-méthode)
- [Sortir du « proche de quoi ? »](#sortir-du--proche-de-quoi--)
- [Confronter la carte à la tradition](#confronter-la-carte-à-la-tradition)
- [Sur la recherche d'un code caché](#sur-la-recherche-dun-code-caché)
- [Organisation du code](#organisation-du-code)
- [Schéma des données](#schéma-des-données)
- [Ce qui est vérifié](#ce-qui-est-vérifié)
- [Limites connues](#limites-connues)
- [Dépannage](#dépannage)
- [Licences et copyright](#licences-et-copyright)

---

## Démarrage

Prérequis : Python 3.11 ou plus (testé en 3.14), ~5 Go de disque, aucune carte
graphique nécessaire.

```bash
python3 -m venv .venv
./.venv/bin/pip install torch --index-url https://download.pytorch.org/whl/cpu
./.venv/bin/pip install -r requirements.txt

export PYTHONPATH=src
./.venv/bin/python -m bible_visu.fetch      # ~55 Mo de textes sources
./.venv/bin/python -m bible_visu.corpus     # table de versets alignés
./.venv/bin/python -m bible_visu.embed      # le plus long — voir le tableau
./.venv/bin/python -m bible_visu.project    # UMAP 3D + amas + voisinage
./.venv/bin/python -m bible_visu.crossrefs  # renvois traditionnels
./.venv/bin/python -m bible_visu.axes       # axes thématiques nommés (~2 min)
./.venv/bin/python -m bible_visu.export     # données du visualiseur
./.venv/bin/python serve.py                 # ouvre http://127.0.0.1:8000
```

Tout reste dans le dossier du projet, **cache des modèles compris**
(`data/models/`, ~3 Go). Rien n'est écrit dans `~/.cache`, rien n'est installé
sur le système.

Chaque étape lit et écrit sur disque : on peut relancer la projection avec
d'autres réglages sans refaire l'encodage, qui est de loin le plus coûteux.
Les options de `bible_visu.project` qui changent le plus la carte :
`--n-neighbors` (petit : filaments, grand : grandes masses), `--min-dist`
(compacité des amas), `--min-cluster-size` (taille minimale d'un amas HDBSCAN),
`--abtt-neighbours` (débruitage du voisinage, 8 par défaut), `--seed`
(projection reproductible à graine égale). Les axes thématiques se modifient
dans la table `AXES` de `src/bible_visu/axes.py` — écrire quelques phrases par
pôle, relancer `bible_visu.axes` puis `bible_visu.export` — et les traductions
dans `corpus.py --translation darby --secondary kjv` (voir `TRANSLATIONS` dans
`sources.py`).

### Coût de l'encodage

Mesuré sur un portable récent, 22 cœurs, sans GPU :

| Modèle | Dimension | Débit | Corpus complet |
|---|---|---|---|
| `intfloat/multilingual-e5-base` | 768 | 22,2 versets/s | ~23 min *(extrapolé)* |
| `intfloat/multilingual-e5-large` *(défaut)* | 1024 | 7,1 versets/s | **72,7 min** *(mesuré)* |

Pour une première exploration, `--model intfloat/multilingual-e5-base` donne une
carte déjà très lisible en un tiers du temps. Les étapes suivantes sont rapides :
projection ~5 min, renvois ~2 min, axes ~2 min, export quelques secondes.

### Ce que produit une exécution complète

| | |
|---|---|
| Versets | 31 170 |
| Alignement avec le texte original | 31 031 (99,55 %) |
| Alignement avec l'anglais | 31 050 (99,62 %) |
| Amas trouvés | 71, plus 46,5 % de versets hors amas |
| Similarité médiane au plus proche voisin | 0,934 |
| Versets ayant un écho dans l'autre Testament | 12 401 (39,8 %) |
| Renvois traditionnels chargés | 548 109 liens |
| Accord avec la tradition | 81,8 % |
| Données du visualiseur | `positions.bin` 365 Ko · `axes.bin` 974 Ko · `verses.json` 20,1 Mo (5,7 Mo compressé) |

Le fort taux de « hors amas » n'est pas un défaut : HDBSCAN refuse d'affecter les
points situés en zone peu dense, plutôt que de les ranger de force quelque part.
Baisser `--min-cluster-size` en réduit la proportion.

---

## Ce que l'on voit

L'écran tient en quatre zones :

* **au centre en haut** — le nom, puis les deux seules décisions structurantes :
  la **disposition** (carte sémantique ou axes nommés) et la **recherche** ;
* **au centre en bas** — une légende posée **sur la carte**, qui rappelle en
  permanence ce que la vue en cours signifie. C'est la première chose à lire ;
* **à gauche** — la langue, l'encart « comment lire », puis les réglages :
  couleur, filtres, amas, affichage. Les trois sélecteurs d'axes n'y
  apparaissent qu'en disposition « axes nommés », puisqu'ailleurs ils ne
  servent à rien ;
* **à droite** — le verset consulté.

Les deux textes explicatifs — la légende du bas et l'encart « comment lire » —
**changent avec la disposition**, parce que ce qui est vrai de l'une est faux de
l'autre : sur la carte sémantique les directions ne signifient rien, sur les
axes nommés elles signifient tout.

Sur écran étroit (moins de 1100 px), les deux panneaux deviennent des tiroirs
fermés que l'on ouvre par les boutons **Réglages** et **Verset** : la carte
occupe alors tout l'écran, ce qui est son seul intérêt. Toucher un point ouvre
le tiroir du verset ; `Échap` referme.

<img src="docs/mobile.png" alt="L'application sur téléphone : en-tête
compact, tiroirs fermés, carte plein écran" width="300">


| Mode de couleur | Ce qu'il révèle |
|---|---|
| **Position dans le canon** *(défaut)* | où le texte se situe dans la Bible. Là où des couleurs éloignées se mélangent, deux passages très distants se ressemblent. |
| **Testament** | les zones où l'Ancien et le Nouveau se recouvrent. |
| **Genre littéraire** | la séparation entre loi, récit, poésie, prophétie, épître. |
| **Amas sémantique** | les groupes trouvés par la machine, sans qu'on lui dise que les livres existent. Seul mode sans liste de couleurs : 71 amas pour dix teintes, une pastille par amas mentirait. Choisir un amas affiche la sienne. |
| **Échos entre testaments** | les versets dont les plus proches parents sémantiques se trouvent dans l'autre Testament — les ponts. |
| **Proximité au thème** | apparaît après une recherche par thème : à quel point chaque verset se rapproche de l'idée décrite. |

Cliquer un point affiche le verset en hébreu ou en grec et ses deux
traductions, **chacun crédité de son édition** — on sait donc toujours si l'on
lit Segond ou Darby —, puis deux listes distinctes :

* **ses huit plus proches parents sémantiques** dans toute la Bible, avec la
  similarité chiffrée. ↔ marque un lien qui traverse les deux Testaments, ✓ un
  lien que la tradition relie aussi ;
* **ses renvois traditionnels**, indépendants de tout calcul.

**Navigation :** clic gauche glissé pour tourner, molette pour zoomer, clic droit
glissé pour déplacer. La recherche accepte une référence (`Ésaïe 53` comme
`Isaiah 53`), un mot français ou anglais, et le texte original — coller `אלהים`
ou `λόγος` isole tous les versets qui le contiennent. Accents, voyelles
hébraïques et esprits grecs sont ignorés : `esaie 53` et `logos` fonctionnent.

Tous les réglages — filtres, mode de couleur, disposition, taille des points,
rotation, langue — sont conservés d'une session à l'autre ; seule la recherche
en cours ne l'est pas, c'est un état de passage. La langue suit d'abord le choix de l'utilisateur, puis celle du
navigateur, et retombe sur l'anglais si aucune traduction ne correspond.

---

## Méthode : du texte aux coordonnées

Cette section explique la chaîne complète, en partant de zéro.

### 1. Aligner quatre textes sur une même grille

`corpus.py` produit une table d'une ligne par verset, portant côte à côte
l'hébreu, le grec, le français et l'anglais. C'est moins évident qu'il n'y
paraît : la versification massorétique n'est pas celle de Segond, et le texte
critique grec omet des passages que les traductions conservent. L'alignement est
donc **déclaré** verset par verset, jamais bricolé — 139 versets n'ont pas de
texte original et l'interface le dit.

### 2. Transformer chaque verset en un point de 1024 dimensions

C'est le cœur de la méthode. Un **modèle d'embedding de phrases** est un réseau
entraîné pour que deux phrases de sens proche produisent deux vecteurs proches,
et deux phrases sans rapport des vecteurs éloignés. Il ne compare pas des mots :
« pardonne-nous nos offenses » et « ne te souviens plus de mes fautes » n'ont
aucun mot commun et sortent pourtant presque au même endroit.

Le modèle retenu est **`intfloat/multilingual-e5-large`** :

* il produit un vecteur de **1024 nombres** par verset — le corpus entier tient
  dans une matrice de 31 170 × 1024 flottants, soit 128 Mo ;
* il est **multilingue**, ce qui compte moins pour l'encodage (fait sur le
  français, voir plus bas) que pour la recherche par thème, où une requête peut
  être formulée dans une autre langue que le corpus ;
* il exige le préfixe **`query: `** devant chaque texte, sans quoi les vecteurs
  produits ne sont pas dans le même repère que ceux de son entraînement. C'est
  une exigence du modèle, pas une convenance : `embed.py`, `axes.py` et
  `serve.py` l'appliquent tous les trois, sans quoi les similarités calculées à
  un endroit ne seraient pas comparables à celles calculées ailleurs.

Les vecteurs sont **normalisés** (ramenés à une longueur de 1). Le produit
scalaire de deux vecteurs normalisés est alors exactement leur **similarité
cosinus** : 1 pour deux textes identiques de sens, 0 pour deux textes sans
rapport. Toute la suite — voisinage, axes, recherche par thème — n'est qu'une
suite de produits scalaires sur cette matrice.

### 3. Chercher les voisins avant de réduire

Les huit plus proches voisins de chaque verset sont calculés **dans les 1024
dimensions**, jamais sur les coordonnées d'écran. C'est important : la réduction
à trois dimensions déforme, et deux points éloignés à l'écran peuvent être de
très proches parents. Les traits tracés depuis le verset sélectionné le montrent.

La matrice de similarité complète pèserait 31 170 × 31 170 flottants, soit près
de 4 Go ; `project.py` la calcule donc **par tranches**, en ne gardant de chaque
tranche que les huit meilleurs scores.

### 4. Aplatir en trois dimensions avec UMAP

**UMAP** cherche un placement en 3D qui préserve le voisinage : les points
proches dans l'espace d'origine restent proches, au prix des grandes distances.
Il travaille ici en **métrique cosinus**, cohérente avec la normalisation, après
une réduction préalable à 64 composantes principales qui accélère le calcul et
retire un peu de bruit.

Ce que fait UMAP, il faut le dire clairement : il **déforme**. Le voisinage
immédiat est fiable ; l'échelle globale ne l'est pas. C'est pourquoi les axes de
la carte n'ont volontairement aucune signification, et pourquoi la légende de
l'écran le répète.

### 5. Détecter les amas et les nommer

**HDBSCAN** regroupe les points selon la densité, et — c'est sa qualité
principale — **refuse de classer** ceux qui se trouvent en zone peu dense
plutôt que de les rattacher arbitrairement. D'où les 46,5 % de versets « hors
amas », qui sont une réponse honnête et non un échec.

Chaque amas est ensuite nommé par **TF-IDF** : les mots fréquents dans l'amas
*et* rares dans le reste du corpus. C'est une étiquette descriptive, pas un
titre : « travailla · enfanta · meschullam » désigne bien une famille de
généalogies.

### 6. Projeter sur des axes que l'on a nommés d'avance

Voir [Sortir du « proche de quoi ? »](#sortir-du--proche-de-quoi--) — c'est là
que la carte cesse d'être seulement un voisinage et devient lisible.

---

## Quatre décisions de méthode

### 1. Le sens est calculé sur le français, pas sur l'hébreu

C'est le point le plus important, et le plus contre-intuitif.

Aucun modèle d'embedding de phrases n'est entraîné sur l'hébreu biblique ou le
grec koinè. Les modèles multilingues disponibles connaissent l'hébreu et le grec
**modernes** — langues dont la morphologie, le lexique et la syntaxe diffèrent
profondément de leurs états anciens. Les appliquer directement au WLC produirait
un nuage d'apparence convaincante mais dont les regroupements ne voudraient rien
dire : le pire résultat possible, parce qu'il est indétectable à l'œil.

Les versets étant alignés 1:1 entre versions, le sens est donc calculé sur la
traduction, tandis que le texte original reste attaché à chaque point. Pour
vérifier ce choix plutôt que le croire :

```bash
./.venv/bin/python -m bible_visu.embed --text-column text_orig \
    --out data/processed/embeddings_orig.npy
```

### 2. Deux espaces vectoriels, parce que la mesure l'a imposé

Le débruitage *All-but-the-Top* (Mu & Viswanath, 2018) retire les quelques
directions communes à tout le corpus, qui encodent la langue et le style plutôt
que le contenu. `scripts/evaluate_abtt.py` le mesure sur un étalon de quinze
citations de l'Ancien Testament par le Nouveau, dont la correspondance ne fait
pas débat.

**Sur la recherche de voisins, le gain est net :**

| | sans débruitage | ABTT = 8 |
|---|---|---|
| Rang médian du vrai partenaire | 1 | 2 |
| Rang moyen | 41 | 3 |
| Dans les 10 premiers | 13/15 | 14/15 |
| Dans les 100 premiers | 13/15 | **15/15** |

Lévitique 19:18 ↔ Matthieu 22:39 (« ton prochain comme toi-même ») passe du
**rang 379 au rang 3** ; Osée 11:1 ↔ Matthieu 2:15 du **rang 207 au rang 12**.

**Sur la disposition, c'est un désastre :** appliqué avant UMAP, le même
traitement aplatit les différences de densité dont HDBSCAN se nourrit. Les
71 amas s'effondrent en **4**, dont un seul absorbe 94 % des versets.

D'où deux espaces : le brut pour dessiner la carte, le débruité pour dire qui
ressemble à qui. C'est réglable — `--abtt-neighbours` et `--abtt-layout`.

Une hypothèse de départ a d'ailleurs été **infirmée** : on attendait du
débruitage qu'il réduise la « gravité narrative », c'est-à-dire la tendance d'un
verset à n'avoir pour voisins que des versets de son propre livre. Mesure : cette
part passe de 36,4 % à 37,8 %. Elle ne baisse pas.

### 3. L'alignement est déclaré, jamais masqué

La versification massorétique diffère de celle de Segond (titres des Psaumes
comptés comme verset 1, découpage de Joël et de Malachie), et le SBLGNT omet les
passages absents des manuscrits les plus anciens (Marc 16:9-20, Jean 5:4, la
péricope de la femme adultère). 139 versets gardent donc leur traduction mais
n'ont pas de texte original ; `corpus.py` en imprime le détail par livre, et
l'interface le dit explicitement au lieu de faire semblant.

### 4. La couleur est vérifiée, pas choisie à l'œil

Un nuage de points met potentiellement chaque catégorie au contact de toutes les
autres. Dans ces conditions, mesures à l'appui, la palette de référence ne
garantit la lisibilité — y compris pour les daltonismes protan, deutan et
tritan — que jusqu'à **trois** teintes ; à huit, la pire paire tombe à ΔE 1,6,
c'est-à-dire strictement indistinguable.

D'où : le mode par défaut est **séquentiel**, le mode Testament n'utilise que les
deux créneaux validés, le mode Genre ne fait jamais reposer l'identité sur la
couleur seule — survoler une ligne de la légende isole son genre —, et les trois
axes thématiques n'emploient que trois teintes, exactement la limite validée.

Le rendu a aussi tranché une question de mélange : l'affichage **additif** est
plus joli mais additionne les couleurs, si bien qu'au cœur des amas la teinte
sature vers le blanc et ne code plus que la densité. Le mélange normal a été
retenu, avec un **ordre de dessin mélangé** par permutation fixe — sans quoi
l'Apocalypse serait systématiquement peinte par-dessus la Genèse et le Nouveau
Testament paraîtrait plus dense qu'il ne l'est.

---

## Sortir du « proche de quoi ? »

La carte UMAP répond à « qu'est-ce qui ressemble à quoi », mais pas à « où est
tel thème ». Deux fonctions comblent ce manque — et toutes deux contournent la
limite mesurée plus haut, à savoir que les amas restent lexicaux.

### Axes thématiques nommés

![Les axes thématiques : jugement ↔ miséricorde en X, récit ↔ enseignement en Y,
loi ↔ grâce en Z](docs/axes.png)

`bible_visu.axes` construit huit axes dont **on choisit le sens à l'avance** :
jugement ↔ miséricorde, loi ↔ grâce, récit ↔ enseignement, plainte ↔ louange,
rituel ↔ justice, présent ↔ eschatologie, individu ↔ peuple, guerre ↔ paix.

Chaque pôle est défini par une poignée de phrases d'ancrage ; l'axe est la
**différence** des moyennes des deux pôles. Cette soustraction annule ce que les
deux pôles ont en commun — la langue, le registre, le style biblique — et ne
laisse que ce qui les distingue. C'est exactement ce qui manque aux amas, où
rien ne retranche le fond commun. Chaque verset se projette ensuite sur l'axe
par un simple produit scalaire, puis l'échelle est fixée au 99,5ᵉ centile de la
valeur absolue : un centile plus bas saturerait des centaines de versets à ±1 et
écraserait la nuance là où elle est la plus intéressante.

En choisissant trois axes pour X, Y et Z, **une position devient lisible** : un
verset à droite penche vers le pôle nommé à droite. Les trois directions sont
tracées dans la scène et **les six pôles écrits à leurs extrémités**, chacun
dans le ton de son axe ; les étiquettes suivent la rotation et s'effacent dès
qu'elles empiéteraient sur un panneau. Premier constat immédiat en colorant par
Testament : le Nouveau se déplace nettement vers *miséricorde* et
*enseignement*, l'Ancien vers *jugement* et *récit*.

**Pourquoi le nuage est-il parfois plat ?** Parce que deux des trois axes
choisis se recouvrent. L'application mesure la corrélation entre les axes
sélectionnés et l'annonce : sur la capture ci-dessus, *jugement ↔ miséricorde*
et *loi ↔ grâce* se recouvrent à 48 %, il ne reste donc que deux directions
vraiment distinctes sur trois. Ce n'est pas un défaut d'affichage, c'est un
résultat : dans le texte, ces deux thèmes vont ensemble.

Le nuage est par ailleurs plus dense au centre que sur la carte UMAP. C'est
fidèle — sur un axe donné, la plupart des versets sont effectivement neutres.

**Un axe mal ancré est un piège**, car il produit un classement d'apparence
crédible et vide de sens. Le script affiche donc les versets extrêmes de chaque
pôle, à lire avant de faire confiance. Deux axes ont dû être réancrés à ce
titre : « grâce » remontait n'importe quel verset du Nouveau Testament — l'axe
doublait simplement le mode Testament — et « louange » remontait les salutations
finales des épîtres. Après correction, « grâce » remonte Galates 2:21 et
1 Pierre 2:19, « louange » des Psaumes d'allégresse.

### Recherche par thème en langage naturel

Décris une idée en toutes lettres ; la phrase est encodée par le modèle qui a
servi au corpus, et chaque verset est coloré selon sa proximité. **Ce n'est pas
une recherche de mots.** Pour « le pardon des offenses », les six premiers sont
Matthieu 6:12, Luc 11:4, Matthieu 6:14, Jean 20:23, Colossiens 1:14 et
Psaume 25:18 — dont trois ne partagent aucun mot avec la requête.

Les requêtes concrètes fonctionnent mieux que les abstraites : « prendre soin de
l'étranger et du pauvre » remonte Deutéronome 10:18 et Psaume 146:9, tandis
qu'une formulation à plusieurs propositions comme « la fidélité de Dieu malgré
l'infidélité de son peuple » se rabat sur le champ de la miséricorde et perd la
nuance d'opposition.

Techniquement, `serve.py` expose `/api/theme?q=…` et renvoie un `Float32Array`
d'une similarité par verset (125 Ko). Seul le décile supérieur est éclairé : les
similarités cosinus sont toutes élevées, et un dégradé sur toute l'étendue ne
montrerait rien. Le modèle est chargé à la première requête, une seule fois,
sous verrou ; le serveur est multi-fils pour que ce chargement ne fige pas le
reste. Si `sentence-transformers` est absent, le service se déclare indisponible
et le reste du visualiseur continue.

---

## Confronter la carte à la tradition

`bible_visu.crossrefs` charge les 344 799 renvois d'openbible.info — le jeu de
données qui a servi à la visualisation en arcs de Harrison & Römhild — et les
confronte au voisinage sémantique.

**Le principal résultat est un accord.** Sur les versets qui ont au moins un
renvoi, **81,8 %** ont au moins un voisin sémantique que la tradition relie
aussi. Une machine qui n'a lu que du texte retrouve une part substantielle de ce
que des générations d'éditeurs ont établi.

Trois cas de figure, et ce qu'ils valent :

* **confirmé** — proche sémantiquement *et* renvoi traditionnel. Ne surprend
  personne, mais valide la méthode ;
* **inédit** — très proche, jamais renvoyé. C'est là qu'il faut regarder si l'on
  cherche du non évident. **Mais** l'inspection des dix plus forts montre
  surtout des formules de surface : « trois jours », « douze hommes », « chacun
  s'en retourna dans sa maison ». Ce sont des pistes, pas des découvertes ;
* **renvoi sémantiquement lointain** — la tradition relie sur autre chose que la
  ressemblance du texte : une figure, un accomplissement, une doctrine. Ce n'est
  pas une erreur, c'est une dimension que le modèle ne voit pas.

**Une précaution indispensable :** openbible enregistre les renvois au niveau du
*passage*, pas du verset. Le lien de la Pentecôte y figure sous la forme
`Joël 2:30 → Actes 2:19-20`, jamais comme la paire exacte Joël 2:31 ↔ Actes 2:20.
Une comparaison verset à verset déclarait donc « inédite » l'une des citations
les plus connues de la Bible. La comparaison se fait à un verset près
(`--window`) ; l'écart entre les deux mesures est affiché (81,8 % contre 68,9 %
en comparaison stricte).

---

## Sur la recherche d'un code caché

Ce projet a été construit pour explorer si la Bible recèle une structure non
évidente. Il faut distinguer deux choses.

**Ce que cette carte montre, et qui est réel et mesurable :** des regroupements
thématiques qui traversent les livres et les siècles, des ponts entre Ancien et
Nouveau Testament, et un accord de 81,8 % avec deux mille ans de travail
éditorial obtenu sans aucune connaissance préalable.

**Ce qu'il faut aborder avec méthode :** les « codes bibliques » par séquences de
lettres équidistantes (ELS). Sur un texte assez long, on trouve *toujours* des
mots à un pas donné — c'est une propriété de la combinatoire, pas du texte. Les
travaux de Witztum, Rips et Rosenberg (1994) ont été testés puis réfutés par
McKay, Bar-Natan, Bar-Hillel et Kalai (*Statistical Science*, 1999) : les mêmes
« codes » ressortent d'une traduction hébraïque de *Guerre et Paix*.

C'est pourquoi le corpus stocke déjà, pour chaque verset, le texte réduit aux
22 consonnes hébraïques, formes finales normalisées (colonne `text_consonants`,
**1 191 314 lettres** au total — le compte massorétique attendu). Un module ELS
peut donc être branché dessus, à une condition : que chaque trouvaille soit
rejouée sur du texte permuté et sur un corpus témoin, et accompagnée de sa
p-valeur. Sans modèle nul, un scanner ELS ne mesure rien.

D'autres structures cachées tiennent statistiquement : les chiasmes,
repérables par similarité d'embeddings ; et la stylométrie, dont le regroupement
non supervisé du Pentateuque retrouve des signatures d'auteurs distinctes
(Koppel et coll., 2011).

---

## Organisation du code

```
src/bible_visu/
  sources.py    table des 66 livres (FR/EN), URL, autocontrôle au chargement
  paths.py      emplacements sur disque — tout dans le projet
  fetch.py      téléchargement             -> data/raw/
  corpus.py     parsing et alignement      -> data/processed/verses.parquet
  embed.py      vecteurs sémantiques       -> data/processed/embeddings.npy
  vectors.py    débruitage All-but-the-Top
  project.py    UMAP 3D, amas, voisinage   -> data/processed/points.parquet
  crossrefs.py  renvois et confrontation   -> data/processed/crossrefs.npz
  axes.py       axes thématiques nommés    -> data/processed/axes.npz
  export.py     export du visualiseur      -> viewer/data/
viewer/
  index.html    structure, styles, politique de sécurité en balise meta
  app.js        application Three.js (fichier séparé : la CSP interdit l'inline)
  vendor/       three.js vendorisé — aucun CDN, fonctionne hors ligne
  data/         sortie de `export` — versionnée, c'est le site publié
scripts/
  evaluate_abtt.py   mesure du débruitage sur un étalon de citations
docs/           captures d'écran du README
index.html      redirection vers viewer/ — point d'entrée de GitHub Pages
.nojekyll       désactive Jekyll sur Pages, qui n'a rien à faire ici
serve.py        serveur local, recherche par thème, en-têtes de sécurité
LICENSE         CC BY-NC 4.0 ; les textes bibliques gardent leur licence
```

Chaque fichier source porte l'en-tête `© 2026 Rymentz — CC BY-NC 4.0` et renvoie
à `LICENSE`.

---

## Schéma des données

**`data/processed/verses.parquet`** — une ligne par verset :

| Colonne | Contenu |
|---|---|
| `ref` · `label` | identifiant canonique `livre.chapitre.verset` et référence lisible |
| `book_id` · `book` · `osis` | 1–66, nom français, abréviation OSIS |
| `testament` · `genre` · `lang` | Ancien/Nouveau, famille littéraire, hébreu/grec |
| `chapter` · `verse` · `canon_pos` | position dans le livre et dans le canon entier |
| `text_fr` | Louis Segond 1910 — **base du calcul sémantique** |
| `text_en` | World English Bible — affichage seulement |
| `text_orig` | hébreu vocalisé ou grec, vide si non aligné |
| `text_consonants` | hébreu réduit aux 22 consonnes, sans espace (pour l'ELS) |
| `has_orig` · `has_en` · `n_words_fr` | drapeaux d'alignement et longueur |

**`data/processed/points.parquet`** ajoute `x` · `y` · `z`, `cluster`,
`cluster_label`, `neighbours`, `neighbour_sim` et `nn_cross_testament`.

Le voisinage est calculé sur les vecteurs **avant** réduction, donc sans la
distorsion du passage en trois dimensions. Deux points éloignés à l'écran peuvent
être de très proches parents ; les traits tracés depuis le verset sélectionné le
montrent.

---

## Ce qui est vérifié

- **Table des livres** : autocontrôle à l'import (66 livres, 39+27, identifiants
  contigus, noms français et anglais uniques, tables de traduction complètes).
- **Parsing** : contrôlé sur Genèse 1:1, le Shema, Psaume 23:1 et Jean 1:1 ; le
  total consonantique tombe sur le compte massorétique attendu.
- **Voisinage** : testé sur données synthétiques à groupes connus — voisins
  corrects, tri décroissant, aucun auto-voisin, résultat indépendant du découpage
  en blocs.
- **Débruitage** : mesuré sur un étalon de quinze citations, dans les deux sens
  d'usage (voisinage et disposition).
- **Axes thématiques** : chaque axe est contrôlé en lisant ses versets extrêmes ;
  deux axes ont été réancrés après ce contrôle.
- **Palette** : validée par mesure (bande de clarté, plancher de chroma,
  séparation CVD, contraste sur le fond réel), pas à l'œil.

---

## Limites connues

- **La carte dépend de la traduction.** C'est une carte du sens *tel que rendu
  par Segond*, pas une vérité indépendante du traducteur.
- **UMAP déforme.** Les distances à l'écran ne sont pas proportionnelles aux
  distances sémantiques ; seule la structure de voisinage est fiable.
- **Les étiquettes d'amas restent en français**, quelle que soit la langue de
  l'interface : elles sont extraites du corpus français qui sert au calcul.
- **Les amas ne sont pas une vérité.** Changer `--min-cluster-size` change leur
  nombre. Ce sont des indices d'exploration, pas une classification.
- **Les amas sont lexicaux autant que thématiques.** Les embeddings de phrases
  captent le sujet de surface — noms propres, lieux, style narratif — d'où des
  étiquettes comme « travailla · enfanta ». Le débruitage ne corrige pas ce
  point (mesuré, voir plus haut).
- **139 versets sans texte original**, 120 sans texte anglais.
- **Les axes valent ce que valent leurs ancrages.** Ils sont fixés à la main
  dans `axes.py` et n'ont rien d'universel ; les modifier change la carte.
- **La recherche par thème exige `serve.py`** et le modèle local. Sur un
  hébergement statique, la section reste simplement masquée.
- **De fins points parasites apparaissent sur certaines machines** : des pixels
  isolés, très lumineux, d'une couleur absente de la palette, groupés là où le
  nuage est dense. Non reproduit en rendu logiciel, à aucune résolution ni
  densité de pixels — donc dépendant du pilote graphique. Trois causes
  plausibles ont été écartées en les corrigeant sans effet sur le symptôme :
  un `smoothstep` aux bornes inversées (comportement indéfini selon la
  spécification GLSL), un plancher de taille exprimé en pixels de rendu plutôt
  qu'en pixels CSS, et un débordement possible en précision moyenne. Les trois
  corrections sont conservées — elles sont justes indépendamment. La cause
  reste inconnue ; l'affichage demeure lisible.

---

## Dépannage

**La page reste sur « Chargement… »** — l'interface affiche l'erreur réelle. La
cause la plus fréquente est un fichier manquant dans `viewer/vendor/` :
`three.module.js` réexporte depuis `three.core.js`, les deux sont nécessaires.

**Ouvrir `viewer/index.html` en double-cliquant ne marche pas** — c'est normal.
Les navigateurs refusent de charger des modules ES en `file://`. Utiliser
`serve.py`.

**`GET api/status 404` dans la console avec Live Server ou GitHub Pages** — c'est
attendu. Le visualiseur sonde le serveur pour savoir s'il sait encoder une
requête ; un hébergement statique répond 404, la section « recherche par thème »
reste alors masquée et tout le reste fonctionne. Le navigateur consigne quand
même ce 404 : ce n'est pas une erreur de l'application. À noter qu'un serveur
statique n'envoie ni les en-têtes de sécurité, ni la version compressée de
`verses.json` — 21 Mo transférés au lieu de 5,8. `serve.py` fait les deux.

**Des erreurs `contentscript.js` dans la console** — elles viennent d'une
extension du navigateur (portefeuille de cryptomonnaie, bloqueur…), pas du
projet : aucun fichier de ce nom n'existe ici. Pour vérifier, ouvrir la page en
navigation privée avec les extensions désactivées.

**L'encodage semble figé** — il n'affiche rien pendant plusieurs minutes au
démarrage (téléchargement du modèle, ~2 Go la première fois).

**Incohérence entre versets et vecteurs** — `project.py` refuse de tourner si les
tailles diffèrent ; relancer `embed` après toute modification de `corpus`.

---

## Licences et copyright

**© 2026 Rymentz — [CC BY-NC 4.0](LICENSE).** Le pipeline Python, le visualiseur
et cette documentation peuvent être repris, modifiés et rediffusés **à condition
de citer Rymentz avec un lien vers la source, d'indiquer les modifications
apportées, et de ne pas en faire un usage commercial**. Pour un usage
commercial, il faut une autorisation écrite.

« Non commercial » est défini par la licence comme un usage *« principalement
destiné à ou orienté vers un avantage commercial ou une compensation
monétaire »* (section 1(i)). Un site personnel, un cours, un travail de
recherche, une paroisse : oui. Un produit vendu, un service payant, une
plateforme monétisée par la publicité : non, sans accord préalable.

### Ce que cette licence ne couvre pas

Les textes bibliques et les bibliothèques gardent **leurs propres licences**,
toutes plus permissives que celle du projet. Elles ne peuvent pas être
restreintes par lui :

| Source | Contenu | Licence |
|---|---|---|
| [OSHB / morphhb](https://github.com/openscriptures/morphhb) | Texte hébreu, WLC | domaine public |
| [OSHB / morphhb](https://github.com/openscriptures/morphhb) | Lemmes et morphologie | CC BY 4.0 |
| [SBLGNT](https://sblgnt.com/license/) | Texte grec du Nouveau Testament | CC BY 4.0 |
| [MorphGNT](https://github.com/morphgnt/sblgnt) | Annotations morphologiques — *non utilisées ici* | CC BY-SA 3.0 |
| [getbible v2](https://getbible.net) | Segond 1910, World English Bible | domaine public |
| [openbible.info](https://www.openbible.info/labs/cross-references/) | 344 799 renvois | CC BY 4.0 |
| [three.js](https://threejs.org) | rendu 3D (vendorisé dans `viewer/vendor/`) | MIT |

/* © 2026 Rymentz — Bible 3D, visualisation sémantique de la Bible.
 * Distribué sous licence CC BY-NC 4.0 — usage non commercial, voir LICENSE.
 * three.js est vendorisé sous sa propre licence MIT (viewer/vendor/). */
/* Visualiseur 3D — module principal.
 *
 * Le code vit dans un fichier séparé et non dans une balise <script> en
 * ligne : la politique de sécurité du contenu servie par serve.py est
 * `script-src 'self'`, qui interdit tout script inline. Aucune exception
 * n'est accordée, pas même à un import map — d'où l'import relatif de
 * three.js ci-dessous plutôt qu'un alias 'three'.
 */
import * as THREE from './vendor/three.module.js';
import { OrbitControls } from './vendor/OrbitControls.js';

/* ------------------------------------------------------------------ palette */
const GENRE_COLORS = [
  '#3987e5', '#d95926', '#199e70', '#c98500', '#d55181',
  '#008300', '#9085e9', '#e66767', '#21a5b8', '#8a9a1e',
];
const TESTAMENT_COLORS = { 'Ancien': '#3987e5', 'Nouveau': '#d95926' };
const MUTED = '#4a4a47';
// Rampe séquentielle bleue, ordonnée du plus sombre (bas) au plus clair (haut).
// Sur fond noir, le pas le plus sombre est l'extrémité « proche de zéro ».
const RAMP_BLUE = ['#184f95', '#256abf', '#3987e5', '#5598e7', '#86b6ef', '#cde2fb'];
const RAMP_WARM = ['#6b3410', '#9c4c18', '#d95926', '#ef8a4f', '#f7b184', '#ffd9c0'];

const el = id => document.getElementById(id);
const cssColor = hex => new THREE.Color(hex);

/* ------------------------------------------------------------- sûreté HTML */
/* Tout ce qui est interpolé dans du innerHTML passe par ici. Les textes
   bibliques ne contiennent aujourd'hui aucun caractère sensible — c'est
   vérifié — mais la saisie de l'utilisateur, une autre traduction ou un
   fichier de données modifié en contiendraient. On échappe donc à la source
   plutôt que de dépendre d'une propriété du corpus. */
const HTML_ESCAPES = { '&': '&amp;', '<': '&lt;', '>': '&gt;',
                       '"': '&quot;', "'": '&#39;' };
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => HTML_ESCAPES[c]);

/* --------------------------------------------------------------- stockage */
/* Un navigateur en navigation privée, ou avec le stockage désactivé, lève sur
   localStorage. L'application doit continuer à fonctionner sans mémoire. */
const store = {
  get(key) {
    try { return localStorage.getItem(`bible3d.${key}`); } catch { return null; }
  },
  set(key, value) {
    try { localStorage.setItem(`bible3d.${key}`, value); } catch { /* ignoré */ }
  },
};

/* ------------------------------------------------------------------- langue */
const STRINGS = {
  fr: {
    'app.title': 'Bible 3D — visualisation sémantique de la Bible',
    'app.subtitle': 'La Bible cartographiée par le sens · {n} versets · {c} amas',
    'howto.title': 'Comment lire cette carte',
    'howto.titleAxes': 'Comment lire ces axes',
    'howto.p1': '<b>Un point = un verset.</b> Sa position vient du <em>sens</em> de son texte. Deux points côte à côte parlent de la même chose, même s\'ils sont séparés par mille pages et deux langues.',
    'howto.p2': '<b>Les axes ne signifient rien.</b> Haut, bas, gauche, droite n\'ont aucune valeur : seule la <em>proximité</em> compte. La carte peut être tournée dans tous les sens sans rien perdre.',
    'howto.p3': '<b>Les distances sont déformées.</b> Ramener 1024 dimensions à 3 tord forcément l\'espace. Le voisinage immédiat est fiable ; les grandes distances ne le sont pas. Les similarités exactes sont chiffrées dans le panneau de droite.',
    'howto.a1': '<b>Un point = un verset.</b> Sa position n\'est plus un voisinage : ce sont ses trois notes sur les trois axes choisis, chacun étant un thème nommé à ses deux bouts et écrit sur la carte.',
    'howto.a2': '<b>Ici, une direction veut dire quelque chose</b> — c\'est l\'inverse de la carte sémantique. Un verset placé du côté d\'un pôle penche vers ce pôle. Une position se lit donc comme une phrase.',
    'howto.a3': '<b>Le centre est dense, et parfois le nuage s\'aplatit.</b> Dense, parce que la plupart des versets sont neutres sur un thème donné. Plat, parce que deux des axes choisis se recouvrent — la légende du bas le mesure et le dit.',
    'howto.split': '<b>Deux natures de classification, à ne pas confondre :</b>',
    'howto.given': '<b>Testament</b> et <b>genre littéraire</b> sont la classification traditionnelle, attribuée au livre entier. La machine ne l\'a pas devinée, on la lui a fournie — elle sert à colorer et à filtrer.',
    'howto.found': '<b>Les amas sémantiques</b> sont découverts par la machine à partir du seul texte. Elle ignore les livres, les auteurs et les dates. Chaque amas est nommé par les mots qui lui sont le plus caractéristiques.',
    'howto.last': 'Un amas qui recoupe un livre entier est donc un <em>résultat</em>, pas une évidence : ce livre est thématiquement homogène. Un amas qui mélange plusieurs livres est encore plus intéressant.',
    'pill.given': 'donné', 'pill.found': 'trouvé',
    'search.h': 'Recherche',
    'search.ph': 'Ésaïe 53, אלהים, λόγος, berger…',
    'search.hint': 'Référence, mot français, anglais, hébreu ou grec.',
    'search.textOnly': 'Chercher par le sens demande <code>serve.py</code> en local.',
    'search.found': '{n} verset(s) contiennent « {q} ».',
    'color.h': 'Couleur',
    'color.canon': 'Position dans le canon (séquentiel)',
    'color.testament': 'Testament',
    'color.genre': 'Genre littéraire',
    'color.cluster': 'Amas sémantique',
    'color.cross': 'Échos entre testaments (séquentiel)',
    'legend.canon': 'La place du verset dans l\'ordre des livres, du premier au dernier. Partout où une couleur claire se mêle à une couleur sombre, deux passages très éloignés dans la Bible se ressemblent par le sens.',
    'legend.testament': 'La vue la plus lisible : deux couleurs seulement. Les endroits où elles se mêlent sont les zones où l\'Ancien et le Nouveau traitent du même sujet.',
    'legend.genre': 'Les dix familles littéraires traditionnelles, attribuées au livre entier. Dix teintes dépassent ce que l\'œil sait séparer, et rien ne les distingue pour un lecteur daltonien. <b>Survole une ligne de la liste ci-dessous pour isoler son genre</b> : c\'est le mode d\'emploi de cette vue.',
    'legend.cluster': 'Les groupes que la machine a détectés dans le texte seul, sans connaître les livres. <b>Pas de liste de couleurs ici</b> : 71 amas pour dix teintes, elles se répètent et ne servent qu\'à séparer les voisins — une pastille par amas mentirait. <b>Choisis un amas ci-dessous</b> : sa couleur à lui s\'affichera.',
    'legend.noise': 'hors amas',
    'legend.noiseHint': 'En gris, les versets situés en zone peu dense. L\'algorithme refuse de les rattacher de force à un groupe — c\'est un choix, pas un échec.',
    'legend.cross': 'Sur les 8 versets les plus proches par le sens, combien se trouvent dans <em>l\'autre</em> Testament. Les points clairs sont les ponts les plus francs entre Ancien et Nouveau.',
    'ramp.first': 'Genèse', 'ramp.last': 'Apocalypse',
    'ramp.none': 'aucun', 'ramp.all': 'les 8',
    'testament.h': 'Testament',
    'testament.Ancien': 'Ancien Testament', 'testament.Nouveau': 'Nouveau Testament',
    'genre.h': 'Genre littéraire',
    'genre.hint': 'Survole une ligne pour isoler son genre.',
    'cluster.h': 'Amas sémantique',
    'cluster.all': 'Tous les amas ({n})',
    'cluster.verses': 'versets', 'cluster.book': 'livre dominant',
    'cluster.share': 'part du corpus', 'cluster.unlabelled': 'sans étiquette',
    'cluster.hint': '{n} amas trouvés. Chacun est nommé par les mots qui y sont les plus caractéristiques : fréquents ici <em>et</em> rares ailleurs.',
    'cluster.cardHint': 'Si le livre dominant fait l\'essentiel de l\'amas, ce livre est thématiquement homogène ; si l\'amas puise dans plusieurs livres, il révèle un thème qui les traverse.',
    'display.h': 'Affichage',
    'display.onlyCross': 'Seulement les échos AT ↔ NT',
    'display.xrefs': 'Tracer aussi les renvois traditionnels',
    'display.spin': 'Rotation automatique',
    'display.size': 'Taille des points',
    'display.reset': 'Tout réafficher', 'display.recenter': 'Recentrer',
    'lang.h': 'Langue de l\'interface',
    'colophon.licence': 'CC BY-NC 4.0 — réutilisation libre hors usage commercial, avec citation.',
    'colophon.sources': 'Textes : OSHB (WLC), SBLGNT, getbible, openbible.info. Rendu : three.js.',
    'details.h': 'Verset',
    'details.sub': 'clique un point dans le nuage',
    'details.hidden': 'Ce verset est masqué par les filtres en cours : son repère et ses traits ne sont plus tracés dans le nuage. Son texte reste lisible ci-dessous.',
    'share.copy': 'Copier le lien',
    'share.copied': 'Lien copié',
    'share.failed': 'Copie refusée',
    'mapkey.map.h': 'Carte sémantique — la position vient du sens',
    'mapkey.map.p': 'Chaque point est un verset. Deux points côte à côte parlent de la même chose, même à mille pages d\'écart. <b>Les directions, elles, ne veulent rien dire</b> : ni haut, ni bas, ni gauche — seule la proximité compte. Le nuage a la forme irrégulière que le texte lui donne.',
    'mapkey.axes.h': 'Axes thématiques — ici, une position se lit',
    'mapkey.axes.p': 'Les trois directions portent chacune un thème choisi d\'avance, nommé à ses deux extrémités. Un verset placé du côté d\'un pôle penche vers ce pôle. <b>Le centre est dense parce que la plupart des versets sont neutres</b> sur un thème donné — c\'est ce que le texte dit, pas un défaut d\'affichage.',
    'mapkey.flat': 'Le nuage s\'aplatit en plan : {a} et {b} se recouvrent à {r} %. Ces deux thèmes vont ensemble dans le texte, il n\'en reste donc que deux directions distinctes sur trois.',
    'details.intro': 'Chaque point est un verset, placé selon le <em>sens</em> de son texte et non selon sa position dans le livre. Deux versets proches dans l\'espace parlent de la même chose, même s\'ils sont séparés par mille pages.',
    'details.noOrig': 'Pas de texte original aligné pour ce verset (versification différente, ou passage absent du texte critique).',
    'details.otherTexts': 'Autres langues',
    'basis.title': 'Texte sur lequel le sens est calculé. Changer de texte '
                 + 'change la carte : ce sont deux cartes, pas deux versions '
                 + 'd\'une même carte.',
    'mapkey.basis': 'Sens calculé sur : {edition}. Un autre texte donnerait '
                  + 'd\'autres voisinages.',
    'details.neighbours': 'Versets les plus proches par le sens',
    'details.neighboursHint': 'Similarité cosinus. Le signe ↔ marque un lien qui traverse les deux Testaments ; ✓ un lien que la tradition relie aussi.',
    'details.xrefs': 'Renvois traditionnels',
    'details.xrefsHint': 'Ce que des générations d\'éditeurs ont jugé lié — indépendamment du calcul. Source : openbible.info.',
    'details.noXrefs': 'Aucun renvoi traditionnel pour ce verset.',
    'status.shown': '{shown} / {total} versets affichés',
    'status.query': ' · « {q} » : {n}',
    'loading.title': 'Chargement de la carte…',
    'loading.data': 'textes et coordonnées',
    'loading.scene': 'construction de la scène',
    'layout.h': 'Axes affectés à X, Y et Z',
    'layout.map': 'Carte sémantique',
    'layout.axes': 'Axes nommés',
    'mob.controls': 'Réglages', 'mob.details': 'Verset',
    'mob.search': 'Recherche',
    'layout.mapNote': 'Les positions viennent d\u2019UMAP : les axes n\u2019ont aucune signification, seule la proximité en a une.',
    'layout.axesNote': 'Chaque axe est défini par des phrases d\u2019ancrage, et sa direction est la différence entre ses deux pôles. Ici, une position <em>se lit</em> : un verset à droite penche vers le pôle nommé à droite.',
    'theme.h': 'Recherche par thème',
    'theme.ph': 'le pardon des offenses, la fidélité de Dieu…',
    'theme.go': 'Chercher', 'theme.clear': 'Effacer',
    'theme.hint': 'Décris une idée en toutes lettres. Les versets seront colorés selon leur proximité à ce thème, même sans en contenir les mots.',
    'theme.loading': 'Encodage… le modèle se charge à la première recherche (~1 min).',
    'theme.done': 'Thème « {q} » — les points clairs sont les plus proches.',
    'theme.failed': 'Échec : {msg}',
    'theme.unavailable': 'Indisponible : {msg}',
    'color.theme': 'Proximité au thème (séquentiel)',
    'legend.theme': 'Proximité de chaque verset au thème demandé. Ce n\u2019est pas une recherche de mots : un verset peut être proche sans contenir aucun des termes saisis.',
    'ramp.far': 'éloigné', 'ramp.near': 'proche',
    'error.title': 'Le visualiseur n\'a pas pu démarrer',
    'error.hint': 'Vérifie que le pipeline a bien tourné jusqu\'au bout :',
  },
  en: {
    'app.title': 'Bible 3D — a semantic visualisation of the Bible',
    'app.subtitle': 'The Bible mapped by meaning · {n} verses · {c} clusters',
    'howto.title': 'How to read this map',
    'howto.titleAxes': 'How to read these axes',
    'howto.p1': '<b>One dot = one verse.</b> Its position comes from the <em>meaning</em> of its text. Two dots side by side are about the same thing, even if a thousand pages and two languages separate them.',
    'howto.p2': '<b>The axes mean nothing.</b> Up, down, left, right carry no value: only <em>proximity</em> counts. The map can be turned any way without losing anything.',
    'howto.p3': '<b>Distances are distorted.</b> Squeezing 1024 dimensions into 3 necessarily warps the space. Immediate neighbourhoods are reliable; large distances are not. Exact similarities are given in the right-hand panel.',
    'howto.a1': '<b>One dot = one verse.</b> Its position is no longer a neighbourhood: it is its three scores on the three chosen axes, each one a theme named at both ends and written on the map.',
    'howto.a2': '<b>Here a direction does mean something</b> — the opposite of the semantic map. A verse placed toward one pole leans toward that pole. A position therefore reads like a sentence.',
    'howto.a3': '<b>The centre is dense, and the cloud sometimes flattens.</b> Dense, because most verses are neutral on any given theme. Flat, because two of the chosen axes overlap — the legend below measures it and says so.',
    'howto.split': '<b>Two kinds of classification — don\'t confuse them:</b>',
    'howto.given': '<b>Testament</b> and <b>literary genre</b> are the traditional classification, assigned to the whole book. The machine did not infer it, we supplied it — it only colours and filters.',
    'howto.found': '<b>Semantic clusters</b> are discovered by the machine from the text alone. It knows nothing of books, authors or dates. Each cluster is named by the words most characteristic of it.',
    'howto.last': 'A cluster that lines up with a whole book is therefore a <em>result</em>, not a given: that book is thematically homogeneous. A cluster spanning several books is more interesting still.',
    'pill.given': 'given', 'pill.found': 'found',
    'search.h': 'Search',
    'search.ph': 'Isaiah 53, אלהים, λόγος, shepherd…',
    'search.hint': 'Reference, or a word in English, French, Hebrew or Greek.',
    'search.textOnly': 'Searching by meaning needs <code>serve.py</code>, run locally.',
    'search.found': '{n} verse(s) contain “{q}”.',
    'color.h': 'Colour',
    'color.canon': 'Position in the canon (sequential)',
    'color.testament': 'Testament',
    'color.genre': 'Literary genre',
    'color.cluster': 'Semantic cluster',
    'color.cross': 'Echoes across testaments (sequential)',
    'legend.canon': 'Where the verse sits in the order of books, first to last. Wherever a light colour mingles with a dark one, two far-apart passages resemble each other in meaning.',
    'legend.testament': 'The most legible view: two colours only. Where they mingle, Old and New treat the same subject.',
    'legend.genre': 'The ten traditional literary families, assigned to whole books. Ten hues exceed what the eye can separate, and nothing distinguishes them for a colour-blind reader. <b>Hover a row in the list below to isolate its genre</b> — that is how this view is meant to be used.',
    'legend.cluster': 'The groups the machine detected in the text alone, knowing nothing of books. <b>No colour list here</b>: 71 clusters for ten hues, which repeat and only serve to separate neighbours — one swatch per cluster would be a lie. <b>Pick a cluster below</b> and its own colour appears.',
    'legend.noise': 'unclustered',
    'legend.noiseHint': 'In grey, verses in low-density regions. The algorithm refuses to force them into a group — that is a choice, not a failure.',
    'legend.cross': 'Of the 8 nearest verses by meaning, how many lie in the <em>other</em> Testament. The lightest dots are the clearest bridges between Old and New.',
    'ramp.first': 'Genesis', 'ramp.last': 'Revelation',
    'ramp.none': 'none', 'ramp.all': 'all 8',
    'testament.h': 'Testament',
    'testament.Ancien': 'Old Testament', 'testament.Nouveau': 'New Testament',
    'genre.h': 'Literary genre',
    'genre.hint': 'Hover a row to isolate its genre.',
    'cluster.h': 'Semantic cluster',
    'cluster.all': 'All clusters ({n})',
    'cluster.verses': 'verses', 'cluster.book': 'dominant book',
    'cluster.share': 'share of corpus', 'cluster.unlabelled': 'unlabelled',
    'cluster.hint': '{n} clusters found. Each is named by the words most characteristic of it: frequent here <em>and</em> rare elsewhere.',
    'cluster.cardHint': 'If the dominant book makes up most of the cluster, that book is thematically homogeneous; if the cluster draws on several books, it reveals a theme running across them.',
    'display.h': 'Display',
    'display.onlyCross': 'Only OT ↔ NT echoes',
    'display.xrefs': 'Also draw traditional cross-references',
    'display.spin': 'Auto-rotate',
    'display.size': 'Dot size',
    'display.reset': 'Show everything', 'display.recenter': 'Recentre',
    'lang.h': 'Interface language',
    'colophon.licence': 'CC BY-NC 4.0 — free to reuse non-commercially, with credit.',
    'colophon.sources': 'Texts: OSHB (WLC), SBLGNT, getbible, openbible.info. Rendering: three.js.',
    'details.h': 'Verse',
    'details.sub': 'click a dot in the cloud',
    'details.hidden': 'This verse is hidden by the current filters: its marker and links are no longer drawn in the cloud. Its text remains readable below.',
    'share.copy': 'Copy link',
    'share.copied': 'Link copied',
    'share.failed': 'Copy refused',
    'mapkey.map.h': 'Semantic map — position comes from meaning',
    'mapkey.map.p': 'Each dot is a verse. Two dots side by side are about the same thing, even a thousand pages apart. <b>The directions themselves mean nothing</b>: not up, not down, not left — only proximity counts. The cloud has whatever shape the text gives it.',
    'mapkey.axes.h': 'Thematic axes — here a position can be read',
    'mapkey.axes.p': 'Each of the three directions carries a theme chosen in advance and named at both ends. A verse placed toward one pole leans toward that pole. <b>The centre is dense because most verses are neutral</b> on any given theme — that is what the text says, not a display flaw.',
    'mapkey.flat': 'The cloud flattens into a plane: {a} and {b} overlap by {r} %. Those two themes go together in the text, so only two of the three directions remain distinct.',
    'details.intro': 'Each dot is a verse, placed by the <em>meaning</em> of its text rather than its position in the book. Two verses close in space are about the same thing, even a thousand pages apart.',
    'details.noOrig': 'No aligned original text for this verse (different versification, or a passage absent from the critical text).',
    'details.otherTexts': 'Other languages',
    'basis.title': 'The text the meaning is computed on. Changing it changes '
                 + 'the map: these are two maps, not two versions of one.',
    'mapkey.basis': 'Meaning computed on: {edition}. Another text would give '
                  + 'other neighbourhoods.',
    'details.neighbours': 'Nearest verses by meaning',
    'details.neighboursHint': 'Cosine similarity. ↔ marks a link crossing the two Testaments; ✓ one the tradition also draws.',
    'details.xrefs': 'Traditional cross-references',
    'details.xrefsHint': 'What generations of editors judged to be linked — independently of any computation. Source: openbible.info.',
    'details.noXrefs': 'No traditional cross-reference for this verse.',
    'status.shown': '{shown} / {total} verses shown',
    'status.query': ' · “{q}”: {n}',
    'loading.title': 'Loading the map…',
    'loading.data': 'texts and coordinates',
    'loading.scene': 'building the scene',
    'layout.h': 'Axes assigned to X, Y and Z',
    'layout.map': 'Semantic map',
    'layout.axes': 'Named axes',
    'mob.controls': 'Settings', 'mob.details': 'Verse',
    'mob.search': 'Search',
    'layout.mapNote': 'Positions come from UMAP: the axes carry no meaning, only proximity does.',
    'layout.axesNote': 'Each axis is defined by anchor sentences, and its direction is the difference between its two poles. Here a position <em>can be read</em>: a verse on the right leans toward the pole named on the right.',
    'theme.h': 'Search by theme',
    'theme.ph': 'forgiveness of wrongs, God\u2019s faithfulness…',
    'theme.go': 'Search', 'theme.clear': 'Clear',
    'theme.hint': 'Describe an idea in plain words. Verses are coloured by closeness to that theme, even without containing the words.',
    'theme.loading': 'Encoding… the model loads on the first search (~1 min).',
    'theme.done': 'Theme “{q}” — the lightest dots are the closest.',
    'theme.failed': 'Failed: {msg}',
    'theme.unavailable': 'Unavailable: {msg}',
    'color.theme': 'Closeness to theme (sequential)',
    'legend.theme': 'How close each verse is to the requested theme. This is not a word search: a verse can be close without containing any of the words typed.',
    'ramp.far': 'far', 'ramp.near': 'close',
    'error.title': 'The viewer could not start',
    'error.hint': 'Check that the pipeline ran all the way through:',
  },
};

/* La langue est rangée dans le même bloc que les filtres, et doit donc être
   relue là — pas dans une clé séparée. Elle est nécessaire dès les premiers
   messages de chargement, bien avant `restoreState()`.

   Ordre : le choix explicite de l'utilisateur, puis la langue du navigateur,
   puis l'anglais. Ce dernier n'est pas une préférence, c'est le repli quand
   aucune traduction ne correspond à la langue du navigateur. */
const FALLBACK_LANG = 'en';

function pickLanguage() {
  let saved = null;
  try { saved = JSON.parse(store.get('state') || 'null'); } catch { /* ignoré */ }
  if (saved && STRINGS[saved.lang]) return saved.lang;
  for (const tag of (navigator.languages || [navigator.language || ''])) {
    const code = String(tag).slice(0, 2).toLowerCase();
    if (STRINGS[code]) return code;
  }
  return FALLBACK_LANG;
}

let lang = pickLanguage();

/** Traduit ``key``, en substituant ``{nom}`` par ``params.nom``. */
function t(key, params) {
  let text = (STRINGS[lang] && STRINGS[lang][key])
    ?? STRINGS[FALLBACK_LANG][key] ?? key;
  if (params) {
    for (const [name, value] of Object.entries(params)) {
      text = text.replaceAll(`{${name}}`, value);
    }
  }
  return text;
}

const nf = () => new Intl.NumberFormat(lang === 'fr' ? 'fr-FR' : 'en-GB');
const num = value => nf().format(value);

/* Une erreur au chargement doit se voir : sans cela la page resterait
   indéfiniment sur « Chargement de la carte… » sans rien expliquer. */
function showFatal(message) {
  const box = el('loading');
  if (!box) { console.error(message); return; }
  box.innerHTML = `
    <div style="max-width:520px;text-align:left">
      <div style="color:#e66767;font-weight:600;margin-bottom:8px">${
        esc(t('error.title'))}</div>
      <pre style="white-space:pre-wrap;color:#c3c2b7;font-size:12px;margin:0 0 12px">${
        esc(message)}</pre>
      <div style="color:#898781;font-size:12px">${esc(t('error.hint'))}<br>
        <code>python -m bible_visu.export</code>
      </div>
    </div>`;
}
addEventListener('error', event => showFatal(event.message || event.error));
addEventListener('unhandledrejection', event =>
  showFatal(event.reason?.stack || event.reason?.message || String(event.reason)));

/* Les paramètres ne s'appellent ni `ramp` ni `t` : ces noms désignent déjà la
   fonction de rendu de bandeau et celle de traduction. */
function rampColor(colors, position) {
  const clamped = Math.max(0, Math.min(1, position));
  const scaled = clamped * (colors.length - 1);
  const i = Math.min(Math.floor(scaled), colors.length - 2);
  return new THREE.Color(colors[i]).lerp(new THREE.Color(colors[i + 1]), scaled - i);
}

/* --------------------------------------------------------------- chargement */
/* L'écran de chargement parle déjà la langue retenue : elle est connue avant
   la première requête, il n'y a donc aucune raison d'afficher deux libellés
   côte à côte en attendant de savoir. */
document.documentElement.lang = lang;
el('loadtitle').textContent = t('loading.title');

const setProgress = (frac, msg) => {
  el('progress').style.width = `${Math.round(frac * 100)}%`;
  if (msg) el('loadmsg').textContent = msg;
};

const [positionsBuf, data] = await Promise.all([
  fetch('data/positions.bin').then(r => {
    if (!r.ok) throw new Error('positions.bin introuvable');
    setProgress(0.25, t('loading.data'));
    return r.arrayBuffer();
  }),
  fetch('data/verses.json').then(r => {
    if (!r.ok) throw new Error('verses.json introuvable');
    setProgress(0.55, t('loading.data'));
    return r.json();
  }),
]);

const N = data.count;
const positions = new Float32Array(positionsBuf);
if (positions.length !== N * 3) {
  throw new Error(`positions.bin (${positions.length / 3}) ≠ verses.json (${N})`);
}
setProgress(0.7, t('loading.scene'));

/* Ordre de dessin mélangé.

   Les points transparents se mélangent dans l'ordre où ils sont dessinés. Si on
   les laissait en ordre canonique, l'Apocalypse serait systématiquement peinte
   par-dessus la Genèse, et le Nouveau Testament paraîtrait plus dense qu'il ne
   l'est partout où les deux se recouvrent — un artefact qui se lirait comme un
   résultat. Une permutation fixe supprime ce biais sans rendre le nuage
   instable d'un chargement à l'autre.

   `order[emplacement] = index du verset`. */
const order = new Int32Array(N);
{
  for (let i = 0; i < N; i++) order[i] = i;
  let seed = 0x9e3779b9;                       // mulberry32, graine fixe
  const rand = () => {
    seed |= 0; seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  for (let i = N - 1; i > 0; i--) {            // mélange de Fisher-Yates
    const j = Math.floor(rand() * (i + 1));
    [order[i], order[j]] = [order[j], order[i]];
  }
}

/* `positions` reste en ordre canonique — c'est lui qu'on interroge pour placer
   le halo et les liens. Il devient mutable : changer de disposition déplace le
   nuage. `umapPositions` en garde la version d'origine, pour pouvoir y revenir.
   `drawPositions` est la copie permutée envoyée au GPU. */
const umapPositions = new Float32Array(positions);
const drawPositions = new Float32Array(N * 3);
for (let slot = 0; slot < N; slot++) {
  const i = order[slot];
  drawPositions[slot * 3] = positions[i * 3];
  drawPositions[slot * 3 + 1] = positions[i * 3 + 1];
  drawPositions[slot * 3 + 2] = positions[i * 3 + 2];
}

const bookById = new Map(data.books.map(b => [b.id, b]));
const genreIndex = new Map(data.genres.map((g, i) => [g, i]));
const clusterById = new Map(data.clusters.map(c => [c.id, c]));

/* Les textes sur lesquels une carte a pu être calculée. Le premier est celui
   que porte `verses.json` ; les autres arrivent à la demande. Un export qui
   n'en connaît qu'un — le cas de tout jeu de données antérieur — donne une
   liste d'un seul élément, et le sélecteur reste caché. */
const BASES = (Array.isArray(data.bases) && data.bases.length
  ? data.bases : ['fr']).filter(b => b === 'fr' || b === 'en');

/** L'édition qui a servi au calcul, telle qu'on la crédite sous un verset. */
const basisEdition = basis => (data.editions || {})[basis] || basis.toUpperCase();

/* ------------------------------------------------------------------- trois D */
const container = el('scene');
const scene = new THREE.Scene();
scene.fog = new THREE.FogExp2(0x0d0d0d, 0.0016);

/* `fov` de three.js est le champ *vertical*. En portrait, le champ horizontal
   s'en déduit par le rapport d'écran et devient très étroit : le nuage sortait
   de l'écran par les côtés pendant que le haut et le bas restaient vides. */
const BASE_FOV = 55;
const camera = new THREE.PerspectiveCamera(
  BASE_FOV, innerWidth / innerHeight, 0.5, 4000);
camera.position.set(0, 0, 260);

const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight);
renderer.setClearColor(0x0d0d0d, 1);
container.appendChild(renderer.domElement);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.06;
controls.rotateSpeed = 0.55;
controls.zoomSpeed = 0.9;
controls.autoRotateSpeed = 0.35;

/* Attributs par point : couleur, taille, opacité — le filtrage se fait ici,
   sans jamais reconstruire la géométrie. */
const colors = new Float32Array(N * 3);
const sizes = new Float32Array(N).fill(1);
const alphas = new Float32Array(N).fill(1);

const geometry = new THREE.BufferGeometry();
geometry.setAttribute('position', new THREE.BufferAttribute(drawPositions, 3));
geometry.setAttribute('aColor', new THREE.BufferAttribute(colors, 3));
geometry.setAttribute('aSize', new THREE.BufferAttribute(sizes, 1));
geometry.setAttribute('aAlpha', new THREE.BufferAttribute(alphas, 1));
geometry.computeBoundingSphere();

const material = new THREE.ShaderMaterial({
  uniforms: {
    uProj: { value: 1 },      // hauteur du canvas / (2·tan(fov/2))
    uScale: { value: 0.85 },  // curseur « taille des points »
    uOrbit: { value: 260 },   // distance caméra → cible, rafraîchie à chaque image
    uFloor: { value: 2.5 },   // plancher de taille : 2,5 px CSS × pixelRatio
  },
  /* Un verset lointain était dessiné exactement aussi opaque qu'un verset
     proche : seule sa taille diminuait. À deux ou trois pixels il ne restait
     de lui qu'une poussière nette et saturée, aussi présente à l'œil qu'un
     point du premier plan — et qui scintillait dès que la caméra bougeait,
     le disque passant d'un pixel à l'autre sans transition. D'où deux
     corrections, toutes deux dans le calcul de l'opacité :

     1. Plancher de taille. Sous 2,5 pixels le disque n'a plus de bord à
        adoucir : il tient entièrement dans le noyau plein du fragment shader,
        et c'est ce noyau tout-ou-rien qui clignote sur la grille de pixels.
        On cesse donc de rétrécir, et on rend en opacité la surface qu'on n'a
        pas retirée — la quantité d'encre reste juste, le scintillement part.

     2. Fondu de profondeur, relatif à la distance d'orbite et non absolu.
        Vu de loin, tout le nuage reste également lisible ; mais dès qu'on
        entre dedans pour examiner un voisinage, l'autre bout du nuage
        s'efface au lieu de cribler l'image. Le plancher de 0,18 est
        volontaire : le fond doit rester perceptible, sans quoi on perd le
        volume et la carte redevient plate.

     3. Fondu de proximité, symétrique du précédent. Un verset quasi collé à
        la caméra était projeté en un disque de plusieurs centaines de pixels,
        pâle et sans contour — une « bulle » claire qui balayait tout l'écran
        à la moindre rotation, car rien ne bouge plus vite à l'image que ce
        qui est près de l'œil. Ces versets-là sont derrière l'épaule du
        spectateur : on les efface avant qu'ils n'enflent.

     Le plancher de taille est en pixels CSS, convertis en pixels de rendu via
     le pixelRatio (uFloor, mis à jour dans resize) : sur un écran 2×, 2,5 px
     de rendu n'en feraient que 1,25 apparents et le scintillement des points
     d'un pixel reviendrait précisément sur les écrans les plus courants. */
  vertexShader: `
    precision highp float;

    attribute vec3 aColor;
    attribute float aSize;
    attribute float aAlpha;
    uniform float uProj;
    uniform float uScale;
    uniform float uOrbit;
    uniform float uFloor;
    varying vec3 vColor;
    varying float vAlpha;
    void main() {
      vec4 mv = modelViewMatrix * vec4(position, 1.0);
      float depth = max(-mv.z, 0.001);
      float orbit = max(uOrbit, 0.001);

      float want  = aSize * uScale * uProj / depth;
      float drawn = max(want, uFloor);
      gl_PointSize = aSize > 0.0 ? drawn : 0.0;

      /* Le rapport est calculé AVANT d'être élevé au carré.

         « want » est une taille en pixels : près de la caméra elle atteint
         couramment plusieurs milliers. En précision moyenne — la seule que
         GLSL ES garantisse sur bien des pilotes — le plus grand nombre
         représentable vaut 65 504, que « want * want » dépasserait dès qu'un
         point demande plus de 256 pixels : infini, puis infini / infini, donc
         NaN jusque dans l'opacité du fragment. Sous cette forme le rapport
         vaut au plus 1 et rien ne peut déborder.

         Précaution, pas diagnostic : ce débordement n'a jamais été observé
         ici, et le corriger n'a pas fait disparaître les points parasites
         signalés sur certaines machines — leur cause reste inconnue. */
      float ratio = min(1.0, want / max(drawn, 0.001));
      float ink   = ratio * ratio;

      float fade = clamp(orbit / depth, 0.18, 1.0);
      float near = smoothstep(0.10, 0.30, depth / orbit);

      vColor = aColor;
      vAlpha = aAlpha * ink * fade * near;
      gl_Position = projectionMatrix * mv;
    }`,
  fragmentShader: `
    varying vec3 vColor;
    varying float vAlpha;
    void main() {
      vec2 d = gl_PointCoord - 0.5;
      float r2 = dot(d, d);

      /* Bord adouci : le point est un disque, pas un carré.

         Écrit dans le sens croissant. smoothstep exige edge0 < edge1 ; la
         spécification GLSL déclare le résultat INDÉFINI dans le cas contraire.
         La version précédente, smoothstep(0.25, 0.06, r2), interpolait à
         l'envers : juste sur les pilotes qui appliquent la formule sans
         vérifier l'ordre, libre sur les autres. C'est précisément la sorte de
         construction qui rend proprement sur une machine et grésille sur une
         autre, sans que rien ne le signale. */
      float edge = 1.0 - smoothstep(0.06, 0.25, r2);
      float a = vAlpha * edge;

      /* Un seul rejet, et sur l'opacité seule. L'ancien code découpait le
         disque au ciseau, par un test sur le rayon : sur un point de un ou
         deux pixels, la découpe bascule d'un pixel entier d'un coup dès que la
         caméra bouge, et le point clignote. Ici la forme vient de l'alpha, qui
         se dégrade continûment ; on ne rejette plus que ce qui serait
         strictement invisible.

         Le test est écrit par la négative, et c'est délibéré : « a < 0.004 »
         est FAUX pour NaN, qui passerait donc au travers et serait peint avec
         une opacité indéfinie. « !(a >= 0.004) » est VRAI pour NaN. Le garde
         attrape ainsi tout NaN, d'où qu'il vienne. C'est une ceinture de
         sécurité, non le remède à un défaut constaté. */
      if (!(a >= 0.004)) discard;
      gl_FragColor = vec4(vColor, clamp(a, 0.0, 1.0));
    }`,
  transparent: true,
  depthWrite: false,
  /* Mélange normal, et non additif. L'additif est plus joli — un nuage
     stellaire — mais il additionne les couleurs : au cœur des amas, des
     centaines de points se superposent et la teinte sature vers le blanc. La
     couleur cesse alors de coder ce qu'on lui demande (le livre, le genre, la
     position dans le canon) pour ne plus coder que la densité locale. Ici la
     couleur porte du sens, donc elle doit survivre à l'empilement.
     La densité, elle, reste lisible par la concentration des points. */
  blending: THREE.NormalBlending,
});

const cloud = new THREE.Points(geometry, material);
scene.add(cloud);

/* Halo du verset sélectionné + liens vers ses voisins sémantiques */
const HALO_RADIUS = 2.6;   // rayon de la géométrie, en unités du monde
const HALO_PX = 30;        // rayon voulu à l'écran, en pixels CSS, quel que soit le zoom
const halo = new THREE.Mesh(
  // 20×14 segments dessinaient une grille plus fine que le repère lui-même :
  // à 60 px de large les fils se touchaient et moiraient. 12×8 suffit à lire
  // une sphère, et laisse voir les versets qu'elle entoure.
  new THREE.SphereGeometry(HALO_RADIUS, 12, 8),
  new THREE.MeshBasicMaterial({ color: 0xffffff, wireframe: true,
                                transparent: true, opacity: 0.85 }));
halo.visible = false;
scene.add(halo);

const linkGeometry = new THREE.BufferGeometry();
linkGeometry.setAttribute('position',
  new THREE.BufferAttribute(new Float32Array(data.nn[0].length * 6), 3));
const links = new THREE.LineSegments(linkGeometry, new THREE.LineBasicMaterial({
  color: 0xffffff, transparent: true, opacity: 0.45 }));
links.visible = false;
scene.add(links);

/* Bornes de la zone de scène réellement visible, entre les deux panneaux : les
   étiquettes d'axes s'y effacent en sortant. Les mesurer à chaque image serait
   un calcul de mise en page par image ; elles ne bougent qu'au
   redimensionnement. Déclarées ici, et non plus bas avec le reste du code des
   axes, parce que `resize()` s'exécute dès le chargement — un `let` déclaré
   après serait encore dans sa zone morte. */
let sceneLeft = 0;
let sceneRight = 0;
let sceneTop = 0;
let sceneBottom = 0;
function measureScene() {
  // un élément replié par une media query renvoie un rectangle nul : on
  // retombe alors sur une marge fixe plutôt que sur zéro
  const box = id => {
    const rect = el(id).getBoundingClientRect();
    return rect.height > 0 ? rect : null;
  };
  // un panneau ancré en haut mange de la largeur ; en tiroir, il monte du bas
  // et ne mange que de la hauteur
  const sideways = rect => rect && rect.top < innerHeight * 0.4;
  const controlsBox = box('controls');
  const detailsBox = box('details');

  sceneLeft = (sideways(controlsBox) ? controlsBox.right : 0) + 10;
  sceneRight = (sideways(detailsBox) ? detailsBox.left : innerWidth) - 10;
  sceneTop = (box('brand')?.bottom ?? 48) + 12;

  let floor = box('mapkey')?.top ?? innerHeight - 40;
  for (const rect of [controlsBox, detailsBox]) {
    if (rect && !sideways(rect)) floor = Math.min(floor, rect.top);
  }
  sceneBottom = floor - 12;
}

function resize() {
  camera.aspect = innerWidth / innerHeight;
  // en portrait, on élargit le champ vertical juste assez pour retrouver le
  // champ horizontal du paysage : la carte entière reste visible quelle que
  // soit l'orientation, au lieu d'être rognée à gauche et à droite
  camera.fov = camera.aspect >= 1 ? BASE_FOV : THREE.MathUtils.radToDeg(
    2 * Math.atan(Math.tan(THREE.MathUtils.degToRad(BASE_FOV) / 2) / camera.aspect));
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
  material.uniforms.uProj.value =
    renderer.domElement.height / (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2));
  material.uniforms.uFloor.value = 2.5 * renderer.getPixelRatio();
  measureScene();   // les étiquettes d'axes s'effacent hors de la zone visible
}
addEventListener('resize', resize);
resize();

/* ------------------------------------------------------------------- filtres */
const state = {
  colorMode: 'canon',
  testaments: new Set(['Ancien', 'Nouveau']),
  genres: new Set(data.genres),
  cluster: 'all',
  onlyCross: false,
  showXrefs: false,
  spin: false,
  pointSize: 0.85,
  layout: 'map',
  axisPick: [0, 1, 2],
  showAltTexts: true,   // dépliant des langues autres que celle de l'interface
  /* Le texte sur lequel la carte est calculée. Il suit la langue de
     l'interface tant que personne n'a choisi explicitement : lire en anglais
     et regarder la carte du Segond serait un décalage permanent entre le texte
     affiché et la géométrie qui le place. Mais un choix explicite l'emporte
     ensuite, et ne se fait plus déloger par une bascule de langue. */
  basis: lang === 'en' && BASES.includes('en') ? 'en' : 'fr',
  basisChosen: false,
  query: '',          // volontairement non mémorisée d'une session à l'autre
  isolatedGenre: null,
  selected: -1,
};

/* --------------------------------------------------- mémoire des réglages */
/* Les filtres et la langue survivent au rechargement ; la recherche en cours
   et le verset sélectionné non — ce sont des états de passage. */
function saveState() {
  store.set('state', JSON.stringify({
    colorMode: state.colorMode,
    testaments: [...state.testaments],
    genres: [...state.genres],
    cluster: state.cluster,
    onlyCross: state.onlyCross,
    showXrefs: state.showXrefs,
    spin: state.spin,
    pointSize: state.pointSize,
    layout: state.layout,
    axisPick: state.axisPick,
    showAltTexts: state.showAltTexts,
    // enregistrée seulement si elle a été choisie : sinon elle doit rester
    // libre de suivre la langue au prochain chargement
    basis: state.basisChosen ? state.basis : null,
    lang,
  }));
}

function restoreState() {
  let saved;
  try { saved = JSON.parse(store.get('state') || 'null'); } catch { return; }
  if (!saved || typeof saved !== 'object') return;

  const known = new Set(['canon', 'testament', 'genre', 'cluster', 'cross']);
  if (known.has(saved.colorMode)) state.colorMode = saved.colorMode;

  // on ne réintroduit que des valeurs présentes dans les données actuelles :
  // un jeu de données régénéré peut avoir d'autres genres ou d'autres amas
  // on vérifie la liste *après* filtrage : un réglage périmé ne doit pas
  // pouvoir aboutir à un ensemble vide, qui masquerait toute la Bible sans que
  // rien n'explique pourquoi
  if (Array.isArray(saved.testaments)) {
    const valid = saved.testaments.filter(x => x === 'Ancien' || x === 'Nouveau');
    if (valid.length) state.testaments = new Set(valid);
  }
  if (Array.isArray(saved.genres) && saved.genres.length) {
    const valid = saved.genres.filter(g => data.genres.includes(g));
    if (valid.length) state.genres = new Set(valid);
  }
  if (saved.cluster === 'all' || clusterById.has(Number(saved.cluster))) {
    state.cluster = saved.cluster;
  }
  state.onlyCross = !!saved.onlyCross;
  state.showXrefs = !!saved.showXrefs && !!data.xref;
  // seul un repli explicite est restauré : un réglage enregistré avant que ce
  // dépliant n'existe doit retrouver l'affichage complet, pas un panneau replié
  if (saved.showAltTexts === false) state.showAltTexts = false;
  if (typeof saved.basis === 'string' && BASES.includes(saved.basis)) {
    state.basis = saved.basis;
    state.basisChosen = true;
  }
  state.spin = !!saved.spin;
  const size = Number(saved.pointSize);
  if (Number.isFinite(size) && size >= 0.2 && size <= 3) state.pointSize = size;

  // les axes peuvent avoir changé de nombre depuis la dernière visite
  const axisCount = Array.isArray(data.axes) ? data.axes.length : 0;
  if (saved.layout === 'axes' && axisCount >= 3) state.layout = 'axes';
  if (Array.isArray(saved.axisPick) && saved.axisPick.length === 3 &&
      saved.axisPick.every(i => Number.isInteger(i) && i >= 0 && i < axisCount)) {
    state.axisPick = saved.axisPick;
  }
}

/* ------------------------------------------------------------- permaliens */
/* Un lien partagé encode ce que l'on regarde, jamais où se trouve la caméra.
   Sur la carte sémantique les directions ne signifient rien : un angle de vue
   n'est qu'une trace du chemin parcouru, et cinq flottants d'orientation dans
   l'URL n'apprendraient rien à personne. On encode donc l'intention — quel
   verset, quelle disposition, quels axes, quel mode de couleur — et
   l'application recompose la vue.
                                                                             |
   Ce qui est délibérément ABSENT :
                                                                             |
   * les filtres (testaments, genres, amas). Ils *masquent* des versets. Un
     lien qui cache la moitié de la Bible sans le dire ferait croire au
     destinataire qu'il voit tout ; rien à l'écran ne lui signalerait que la
     carte reçue est tronquée. On ne partage que du présentationnel ;
   * la langue. La référence OSIS est neutre : je partage `Matt.6.12`, vous le
     lisez en français si c'est votre langue. Imposer la sienne serait une
     régression pour celui qui reçoit ;
   * la recherche par thème. Elle exige `serve.py` et le modèle local ; le lien
     serait mort pour tout le monde sauf son auteur. */
const OSIS_BY_ID = new Map(data.books.map(b => [b.id, b.osis]));
const ID_BY_OSIS = new Map(data.books.map(b => [b.osis.toLowerCase(), b.id]));

const indexByRef = new Map();
for (let i = 0; i < N; i++) {
  indexByRef.set(`${data.bookId[i]}.${data.chapter[i]}.${data.verse[i]}`, i);
}

const osisRef = i =>
  `${OSIS_BY_ID.get(data.bookId[i])}.${data.chapter[i]}.${data.verse[i]}`;

/** Résout « Matt.6.12 » vers un indice, ou -1. Le fragment d'URL est une
 *  entrée non fiable comme une autre : tout est validé, rien n'est supposé. */
function indexOfOsis(ref) {
  const parts = /^([0-9A-Za-z]+)\.(\d+)\.(\d+)$/.exec(String(ref).trim());
  if (!parts) return -1;
  const book = ID_BY_OSIS.get(parts[1].toLowerCase());
  if (book === undefined) return -1;
  const hit = indexByRef.get(`${book}.${Number(parts[2])}.${Number(parts[3])}`);
  return hit === undefined ? -1 : hit;
}

const COLOR_MODES = new Set(['canon', 'testament', 'genre', 'cluster', 'cross']);

function permalink() {
  const parts = [];
  if (state.selected >= 0) parts.push(`v=${osisRef(state.selected)}`);
  if (state.layout === 'axes' && AXES.length >= 3) {
    parts.push('l=axes');
    parts.push(`a=${state.axisPick.map(i => AXES[i].id).join(',')}`);
  }
  if (state.colorMode !== 'canon') parts.push(`c=${state.colorMode}`);
  /* La carte voyage avec le lien, au même titre que la disposition. Les
     voisins d'un verset ne sont pas les mêmes d'un texte à l'autre : partager
     « regarde ses plus proches parents » sans dire dans quelle carte, ce
     serait partager une affirmation dont l'autre ne verrait pas la même
     preuve. Elle n'apparaît que si elle n'est pas la valeur d'origine. */
  if (state.basis !== 'fr' && BASES.includes(state.basis)) {
    parts.push(`b=${state.basis}`);
  }
  return parts.join('&');
}

/** Écrit l'état dans le fragment.
 *
 *  `replaceState` et non `pushState` : l'URL suit la sélection en continu, et
 *  empiler une entrée d'historique par verset cliqué rendrait le bouton Retour
 *  inutilisable au bout de quelques minutes d'exploration. */
function writePermalink() {
  const hash = permalink();
  if (location.hash.replace(/^#/, '') === hash) return;
  history.replaceState(null, '',
    location.pathname + location.search + (hash ? `#${hash}` : ''));
}

/** Lit le fragment. Ne renvoie que les clefs reconnues et valides : une clef
 *  inconnue est ignorée, une valeur invalide est ignorée, et un fragment
 *  entièrement malformé ouvre la carte par défaut. Une fois des liens en
 *  circulation, le format est un contrat — il doit se dégrader, jamais rompre. */
function readPermalink() {
  const raw = location.hash.replace(/^#/, '');
  if (!raw) return null;

  const found = new Map();
  for (const chunk of raw.split('&')) {
    const cut = chunk.indexOf('=');
    if (cut > 0) {
      try { found.set(chunk.slice(0, cut), decodeURIComponent(chunk.slice(cut + 1))); }
      catch { /* échappement invalide : on ignore ce morceau */ }
    }
  }

  const out = {};
  if (COLOR_MODES.has(found.get('c'))) out.colorMode = found.get('c');
  if (found.get('l') === 'map') out.layout = 'map';
  if (found.get('l') === 'axes' && AXES.length >= 3) out.layout = 'axes';

  const axes = found.get('a');
  if (axes) {
    const picks = axes.split(',').map(id => AXES.findIndex(a => a.id === id));
    if (picks.length === 3 && picks.every(i => i >= 0)) out.axisPick = picks;
  }

  if (BASES.includes(found.get('b'))) out.basis = found.get('b');

  const verse = found.get('v');
  if (verse) {
    const i = indexOfOsis(verse);
    if (i >= 0) out.selected = i;
  }
  return Object.keys(out).length ? out : null;
}

/** Applique au réglage courant ce qu'un lien décrit, et rien de plus.
 *
 *  Volontairement sans `saveState()` : ouvrir le lien de quelqu'un ne doit pas
 *  remplacer durablement ses propres réglages. Un lien partagé est une lentille
 *  posée le temps d'une visite ; la première action de l'utilisateur enregistre
 *  ensuite normalement. */
function applyShared(shared) {
  if (shared.colorMode) {
    state.colorMode = shared.colorMode;
    el('colormode').value = shared.colorMode;
  }
  if (shared.axisPick) state.axisPick = shared.axisPick;
  if (shared.layout) state.layout = shared.layout;
  /* La carte reçue s'impose pour la visite, sans être mémorisée : c'est le
     choix de l'expéditeur, pas une préférence du destinataire. `basisChosen`
     reste donc tel quel, et le prochain chargement sans lien retrouvera la
     carte que le lecteur suivait. */
  if (shared.basis) state.basis = shared.basis;
}

const visible = new Uint8Array(N).fill(1);
const matches = new Uint8Array(N).fill(1);

/* Le WLC est vocalisé : אֱלֹהִ֑ים porte voyelles et cantillation entre ses
   consonnes, et personne ne saisit cela au clavier. On retire donc les signes
   diacritiques des deux côtés de la comparaison — ce qui rend du même coup la
   recherche insensible aux accents en français (« Esaie » trouve « Ésaïe ») et
   aux esprits et accents en grec (« logos » trouve « λόγος »).

   NFD décompose les caractères précomposés ; la première plage couvre les
   marques combinantes latines et grecques, la seconde les points-voyelles et
   accents de cantillation hébreux. */
const DIACRITICS = /[\u0300-\u036f\u0591-\u05c7]/g;
const fold = text => text.normalize('NFD').replace(DIACRITICS, '').toLowerCase();

/* Clé de recherche pré-calculée : référence + traduction + texte original.
   Refaire 31 170 normalisations Unicode à chaque frappe se verrait ; une seule
   passe au chargement rend la recherche instantanée. */
/* La clé contient les deux langues d'interface, pour que « Isaiah 53 » et
   « Ésaïe 53 » trouvent la même chose quelle que soit la langue affichée. */
const searchKeys = Array.from({ length: N }, (_, i) => {
  const book = bookById.get(data.bookId[i]);
  const ref = `${data.chapter[i]}:${data.verse[i]}`;
  return fold([book.name, ref, book.nameEn, ref, data.fr[i],
               data.en ? data.en[i] : '', data.orig[i]].join(' '));
});

function applySearch() {
  const q = fold(state.query.trim());
  if (!q) { matches.fill(1); return N; }
  let count = 0;
  for (let i = 0; i < N; i++) {
    const hit = searchKeys[i].includes(q);
    matches[i] = hit ? 1 : 0;
    if (hit) count++;
  }
  return count;
}

function pointColor(i) {
  switch (state.colorMode) {
    case 'testament':
      return cssColor(TESTAMENT_COLORS[bookById.get(data.bookId[i]).testament]);
    case 'genre':
      return cssColor(GENRE_COLORS[genreIndex.get(bookById.get(data.bookId[i]).genre) % GENRE_COLORS.length]);
    case 'cluster': {
      const c = data.cluster[i];
      return c < 0 ? cssColor(MUTED)
                   : cssColor(GENRE_COLORS[c % GENRE_COLORS.length]);
    }
    case 'theme':
      return rampColor(RAMP_BLUE, themeIntensity(i));
    case 'cross':
      return rampColor(RAMP_WARM, data.crossT[i] / Math.max(1, data.nn[0].length));
    default:
      return rampColor(RAMP_BLUE, i / (N - 1));
  }
}

function refresh() {
  const found = applySearch();
  const colorAttr = geometry.getAttribute('aColor');
  const sizeAttr = geometry.getAttribute('aSize');
  const alphaAttr = geometry.getAttribute('aAlpha');
  let shown = 0;

  // on parcourt les emplacements de dessin ; `order` donne le verset concerné
  for (let slot = 0; slot < N; slot++) {
    const i = order[slot];
    const book = bookById.get(data.bookId[i]);
    let ok = state.testaments.has(book.testament) &&
             state.genres.has(book.genre) &&
             matches[i] === 1;
    if (ok && state.cluster !== 'all') ok = data.cluster[i] === Number(state.cluster);
    if (ok && state.onlyCross) ok = data.crossT[i] > 0;

    visible[i] = ok ? 1 : 0;
    const dimmed = state.isolatedGenre && book.genre !== state.isolatedGenre;
    const colour = ok && !dimmed ? pointColor(i) : cssColor(MUTED);

    colorAttr.array[slot * 3] = colour.r;
    colorAttr.array[slot * 3 + 1] = colour.g;
    colorAttr.array[slot * 3 + 2] = colour.b;
    alphaAttr.array[slot] = !ok ? 0 : (dimmed ? 0.15 : 0.62);
    sizeAttr.array[slot] = !ok ? 0 : (dimmed ? 0.6 : 1);
    if (ok) shown++;
  }
  colorAttr.needsUpdate = alphaAttr.needsUpdate = sizeAttr.needsUpdate = true;

  el('status').textContent =
    t('status.shown', { shown: num(shown), total: num(N) }) +
    (state.query ? t('status.query', { q: state.query, n: found }) : '');
  /* textContent, pas innerHTML : la saisie de l'utilisateur n'est jamais du
     balisage. Hors recherche, la ligne reste vide — elle est sous le titre, au
     milieu de l'écran, et n'a pas à y rester en permanence.
                                                                             |
     Sauf sur un hébergement statique, où le champ ne fait que de la
     correspondance de texte. Rien ne le dit dans le champ lui-même, et la
     section « recherche par thème » qui l'expliquerait est justement celle qui
     disparaît. Le lecteur tape une idée, n'obtient rien, et conclut que la
     carte ne sait pas la trouver — alors qu'elle sait, ailleurs. Une ligne
     l'annonce donc, précisément là où la question se pose. */
  const info = el('search-info');
  if (state.query) {
    info.textContent = t('search.found', { n: found, q: state.query });
  } else if (themeAvailable) {
    info.textContent = '';
  } else {
    // texte de l'application, jamais de donnée extérieure : le <code> est à nous
    info.innerHTML = t('search.textOnly');
  }

  // le repère 3D suit les filtres, jamais l'inverse
  syncSelection();
}

/* -------------------------------------------------------------------- légende */
/* Le genre reste identifié par son libellé français dans les données ; seul
   son affichage change de langue. */
const genreLabel = genre => {
  if (lang !== 'en' || !data.genresEn) return genre;
  const at = data.genres.indexOf(genre);
  return at >= 0 ? data.genresEn[at] : genre;
};
const clusterBook = c => (lang === 'en' && c.bookEn ? c.bookEn : c.book);

const pill = kind => `<span class="pill ${kind}">${esc(t(`pill.${kind}`))}</span>`;

function rampBar(colors, left, right) {
  return `<div class="ramp" style="background:linear-gradient(90deg,${
    colors.join(',')})"></div>
    <div class="ramp-ends"><span>${esc(left)}</span><span>${esc(right)}</span></div>`;
}

function swatchRow(colour, label) {
  return `<div class="row"><span class="swatch" style="background:${colour}"></span>
     <span class="name">${esc(label)}</span></div>`;
}

function renderLegend() {
  const box = el('legend');
  switch (state.colorMode) {
    case 'canon':
      box.innerHTML = rampBar(RAMP_BLUE, t('ramp.first'), t('ramp.last')) +
        `<p class="legend-note">${pill('given')} ${t('legend.canon')}</p>`;
      break;

    case 'testament':
      box.innerHTML =
        Object.entries(TESTAMENT_COLORS)
          .map(([key, colour]) => swatchRow(colour, t(`testament.${key}`))).join('') +
        `<p class="legend-note">${pill('given')} ${t('legend.testament')}</p>`;
      break;

    case 'genre':
      box.innerHTML =
        data.genres.map((g, i) => swatchRow(GENRE_COLORS[i], genreLabel(g))).join('') +
        `<p class="legend-note">${pill('given')} ${t('legend.genre')}</p>`;
      break;

    /* Seul mode sans liste de couleurs, et c'est délibéré : 71 amas pour dix
       teintes, une pastille par amas mentirait — deux amas voisins dans la
       liste porteraient la même. En revanche, dès qu'un amas est choisi, sa
       couleur à lui est montrée : c'est la seule affirmation vraie qu'on
       puisse faire ici. */
    case 'cluster': {
      const chosen = state.cluster === 'all'
        ? null : clusterById.get(Number(state.cluster));
      box.innerHTML =
        (chosen ? swatchRow(GENRE_COLORS[chosen.id % GENRE_COLORS.length],
                            chosen.label || t('cluster.unlabelled')) : '') +
        `<p class="legend-note">${pill('found')} ${t('legend.cluster')}</p>` +
        swatchRow(MUTED, t('legend.noise')) +
        `<p class="legend-note">${t('legend.noiseHint')}</p>`;
      break;
    }

    case 'theme':
      box.innerHTML = rampBar(RAMP_BLUE, t('ramp.far'), t('ramp.near')) +
        `<p class="legend-note">${pill('found')} ${t('legend.theme')}</p>`;
      break;

    case 'cross':
      box.innerHTML = rampBar(RAMP_WARM, t('ramp.none'), t('ramp.all')) +
        `<p class="legend-note">${pill('found')} ${t('legend.cross')}</p>`;
      break;
  }
}

/* Fiche descriptive de l'amas sélectionné : sans elle, une étiquette comme
   « travailla · enfanta · meschullam » reste incompréhensible. */
function renderClusterInfo() {
  const box = el('cluster-info');
  if (state.cluster === 'all') {
    box.innerHTML = `<p class="legend-note">${
      t('cluster.hint', { n: data.clusters.length })}</p>`;
    return;
  }
  const c = clusterById.get(Number(state.cluster));
  if (!c) { box.innerHTML = ''; return; }
  box.innerHTML = `
    <div class="cluster-card">
      <div class="terms">${esc(c.label || t('cluster.unlabelled'))}</div>
      <dl>
        <dt>${esc(t('cluster.verses'))}</dt><dd>${esc(num(c.size))}</dd>
        <dt>${esc(t('cluster.book'))}</dt><dd>${esc(clusterBook(c) || '—')}</dd>
        <dt>${esc(t('cluster.share'))}</dt><dd>${(100 * c.size / N).toFixed(1)} %</dd>
      </dl>
      <p class="legend-note">${t('cluster.cardHint')}</p>
    </div>`;
}

/* --------------------------------------------------------------- panneaux UI */
function countBy(fn) {
  const out = new Map();
  for (let i = 0; i < N; i++) {
    const k = fn(bookById.get(data.bookId[i]));
    out.set(k, (out.get(k) || 0) + 1);
  }
  return out;
}

const testamentCounts = countBy(b => b.testament);
const genreCounts = countBy(b => b.genre);

function renderPanels() {
  el('testaments').innerHTML = ['Ancien', 'Nouveau'].map(key =>
    `<label class="row"><input type="checkbox" data-testament="${key}"${
       state.testaments.has(key) ? ' checked' : ''}>
       <span class="swatch" style="background:${TESTAMENT_COLORS[key]}"></span>
       <span class="name">${esc(t(`testament.${key}`))}</span>
       <span class="count">${esc(num(testamentCounts.get(key) || 0))}</span>
     </label>`).join('');

  el('genres').innerHTML = data.genres.map((g, i) =>
    `<label class="row" data-genre="${esc(g)}">
       <input type="checkbox" data-genre-input="${esc(g)}"${
         state.genres.has(g) ? ' checked' : ''}>
       <span class="swatch" style="background:${GENRE_COLORS[i]}"></span>
       <span class="name">${esc(genreLabel(g))}</span>
       <span class="count">${esc(num(genreCounts.get(g) || 0))}</span>
     </label>`).join('');

  const select = el('cluster-select');
  select.innerHTML =
    `<option value="all">${esc(t('cluster.all', { n: data.clusters.length }))}</option>` +
    data.clusters.map(c =>
      `<option value="${c.id}">${esc(`${c.size} ${t('cluster.verses')} · ${
        clusterBook(c) || '?'} — ${c.label || t('cluster.unlabelled')}`)}</option>`
    ).join('');
  select.value = state.cluster;
}

/* ------------------------------------------------------------------ sélection */
const bookOf = i => bookById.get(data.bookId[i]);
const bookName = i => (lang === 'en' ? bookOf(i).nameEn : bookOf(i).name);

function verseLabel(i) {
  return `${bookName(i)} ${data.chapter[i]}:${data.verse[i]}`;
}

/** Extrait de traduction : la langue de l'interface d'abord, l'autre à défaut. */
function gloss(i) {
  const primary = lang === 'en' && data.en ? data.en[i] : data.fr[i];
  return primary || data.fr[i] || (data.en ? data.en[i] : '') || '';
}

const sectionTitle = label =>
  `<h2 style="font-size:10px;text-transform:uppercase;letter-spacing:.07em;
     color:var(--muted);margin:16px 0 8px;font-weight:600">${esc(label)}</h2>`;

/** Crédit de l'édition sous un texte : « Louis Segond 1910 », « WLC »… */
const EDITIONS = data.editions || {};
function edition(code) {
  const name = EDITIONS[code];
  return name ? `<p class="edition">${esc(name)}</p>` : '';
}

/** Le lien i–j est-il aussi un renvoi traditionnel ? */
function isTraditional(i, j) {
  return !!(data.xref && data.xref[i] && data.xref[i].includes(j));
}

function verseButton(i, j, similarity) {
  const cross = bookOf(j).testament !== bookOf(i).testament;
  const known = isTraditional(i, j);
  const score = similarity === null ? '' :
    `<span class="s">${similarity.toFixed(3)}</span>`;
  return `<button class="nb${cross ? ' cross' : ''}" data-goto="${j}">
      <span class="top"><span class="r">${esc(verseLabel(j))}${
        known ? ' <span class="known">✓</span>' : ''}</span>${score}</span>
      <span class="t">${esc(gloss(j))}</span></button>`;
}

function showDetails(i) {
  state.selected = i;
  const book = bookOf(i);
  const isHebrew = book.lang === 'hébreu';
  const cluster = clusterById.get(data.cluster[i]);

  el('det-sub').textContent = verseLabel(i);

  const origLang = isHebrew ? 'he' : 'grc';
  const orig = data.orig[i]
    ? `<p class="verse-orig" dir="${isHebrew ? 'rtl' : 'ltr'}"
          lang="${origLang}">${esc(data.orig[i])}</p>${edition(origLang)}`
    : `<p class="legend-note">${esc(t('details.noOrig'))}</p>`;

  /* Chaque texte est crédité de son édition : « Bouillonnant d'ardeur » ne se
     lit pas de la même façon selon qu'on sait que c'est Segond ou Darby.
                                                                             |
     Un seul texte reste en clair : celui de la langue de l'interface. Tout le
     reste — l'original, l'autre traduction — tient dans un dépliant. Le panneau
     devient assez court pour que les voisins et les renvois tiennent dans
     l'écran, ce qui est tout l'intérêt, et rien n'est effacé pour autant : le
     titre du dépliant dit que ces textes existent, un clic les rouvre.
                                                                             |
     Le texte qui a servi au calcul n'a pas à figurer ici en plus : le
     sélecteur de l'en-tête le nomme en permanence, et la légende du bas le
     répète. Le redoubler dans le panneau rallongerait tout pour redire ce qui
     est déjà à l'écran. */
  const texts = (pairs, muted) => pairs
    .filter(([, text]) => text)
    .map(([code, text], rank) =>
      `<p class="verse-fr${rank || muted ? ' verse-alt' : ''}">${esc(text)}</p>` +
      edition(code)).join('');

  const versions = { fr: data.fr[i], en: data.en ? data.en[i] : '' };
  const kept = lang === 'en' && versions.en ? 'en' : 'fr';
  const primary = [[kept, versions[kept]]];
  const secondary = orig
    + texts(['fr', 'en'].filter(code => code !== kept)
              .map(code => [code, versions[code]]), true);

  const neighbours = data.nn[i]
    .map((j, k) => verseButton(i, j, data.nnSim[i][k])).join('');

  const xrefs = data.xref && data.xref[i] && data.xref[i].length
    ? data.xref[i].map(j => verseButton(i, j, null)).join('')
    : `<p class="legend-note">${esc(t('details.noXrefs'))}</p>`;

  el('det-body').innerHTML = `
    ${texts(primary, false)}
    ${secondary ? `<details class="others"${state.showAltTexts ? ' open' : ''}>
      <summary>${esc(t('details.otherTexts'))}</summary>
      ${secondary}
    </details>` : ''}
    <p class="meta">
      <span class="tag">${esc(genreLabel(book.genre))}</span>
      <span class="tag">${esc(t(`testament.${book.testament}`))}</span>
      ${cluster ? `<span class="tag">${esc(cluster.label || cluster.id)}</span>` : ''}
    </p>
    ${sectionTitle(t('details.neighbours'))}
    <p class="legend-note" style="margin:0 0 8px">${t('details.neighboursHint')}</p>
    ${neighbours}
    ${sectionTitle(t('details.xrefs'))}
    <p class="legend-note" style="margin:0 0 8px">${t('details.xrefsHint')}</p>
    ${xrefs}`;

  /* Le choix vaut pour tous les versets, pas pour celui-ci seulement : le
     replier à chaque clic serait une corvée, pas un réglage. `toggle` ne
     remonte pas dans l'arbre, l'écouteur va donc sur l'élément lui-même, posé
     après l'écriture du panneau. */
  const others = el('det-body').querySelector('details.others');
  if (others) others.addEventListener('toggle', () => {
    state.showAltTexts = others.open;
    saveState();
  });

  halo.position.fromArray(positions, i * 3);
  syncSelection();
  el('copy-link').hidden = false;
  writePermalink();
}

/** Accorde le repère 3D à l'état des filtres.
 *
 *  Un verset consulté puis masqué par un filtre gardait son halo et ses traits
 *  au milieu du vide : le nuage désignait un point qu'il ne dessinait plus. Le
 *  panneau de droite, lui, reste rempli — le texte lu garde sa valeur — mais il
 *  annonce désormais que ce verset est hors filtre. */
function syncSelection() {
  const i = state.selected;
  const shown = i >= 0 && visible[i] === 1;
  halo.visible = shown;
  if (shown) halo.position.fromArray(positions, i * 3);
  if (i >= 0) drawLinks(i); else links.visible = false;
  el('det-hidden').hidden = !(i >= 0 && !shown);
}

/** Traits vers les voisins sémantiques, et si demandé vers les renvois.
 *
 *  Un trait ne part que d'un point dessiné et n'aboutit qu'à un point dessiné :
 *  un segment dont une extrémité est masquée par un filtre se termine dans le
 *  vide et se lit comme un lien vers rien. */
function drawLinks(i) {
  const semantic = data.nn[i];
  const traditional = state.showXrefs && data.xref ? (data.xref[i] || []) : [];
  const targets = visible[i]
    ? [...semantic, ...traditional].filter(j => visible[j])
    : [];

  const needed = targets.length * 6;
  let attribute = linkGeometry.getAttribute('position');
  if (attribute.array.length < needed) {
    attribute = new THREE.BufferAttribute(new Float32Array(needed), 3);
    linkGeometry.setAttribute('position', attribute);
  }
  const array = attribute.array;
  targets.forEach((j, k) => {
    array[k * 6 + 0] = positions[i * 3];
    array[k * 6 + 1] = positions[i * 3 + 1];
    array[k * 6 + 2] = positions[i * 3 + 2];
    array[k * 6 + 3] = positions[j * 3];
    array[k * 6 + 4] = positions[j * 3 + 1];
    array[k * 6 + 5] = positions[j * 3 + 2];
  });
  linkGeometry.setDrawRange(0, targets.length * 2);
  attribute.needsUpdate = true;
  links.visible = targets.length > 0;
}

/* Direction d'approche fixe, utilisée quand on arrive par un lien partagé.
   En navigation normale, on garde l'orientation courante : l'utilisateur vient
   de quelque part et perdrait ses repères si la caméra sautait. Mais deux
   personnes ouvrant la même URL doivent voir la même image, sinon le lien ne
   partage pas une vue — il partage une loterie. */
const CANONICAL_VIEW = new THREE.Vector3(0.35, 0.25, 1).normalize();

function flyTo(i, canonical = false) {
  const target = new THREE.Vector3().fromArray(positions, i * 3);
  const offset = (canonical
    ? CANONICAL_VIEW.clone()
    : camera.position.clone().sub(controls.target).normalize())
    .multiplyScalar(48);
  const from = { t: 0 };
  const startTarget = controls.target.clone();
  const startCam = camera.position.clone();
  const endCam = target.clone().add(offset);
  const step = () => {
    from.t = Math.min(1, from.t + 0.045);
    const e = 1 - Math.pow(1 - from.t, 3);   // ease-out cubique
    controls.target.lerpVectors(startTarget, target, e);
    camera.position.lerpVectors(startCam, endCam, e);
    if (from.t < 1) requestAnimationFrame(step);
  };
  step();
}

/* -------------------------------------------------------------- pointage 3D */
const raycaster = new THREE.Raycaster();
raycaster.params.Points.threshold = 1.6;
const pointer = new THREE.Vector2();
let hovered = -1;

function pick(event) {
  pointer.x = (event.clientX / innerWidth) * 2 - 1;
  pointer.y = -(event.clientY / innerHeight) * 2 + 1;
  raycaster.setFromCamera(pointer, camera);
  const hits = raycaster.intersectObject(cloud, false);
  for (const hit of hits) {
    // hit.index est un emplacement de dessin, pas un numéro de verset
    const i = order[hit.index];
    if (visible[i]) return i;                   // ignore les points filtrés
  }
  return -1;
}

renderer.domElement.addEventListener('pointermove', event => {
  const i = pick(event);
  const tip = el('tooltip');
  if (i === hovered) {
    if (i >= 0) { tip.style.left = `${event.clientX + 14}px`;
                  tip.style.top = `${event.clientY + 14}px`; }
    return;
  }
  hovered = i;
  if (i < 0) { tip.style.opacity = 0; renderer.domElement.style.cursor = ''; return; }
  const book = bookById.get(data.bookId[i]);
  tip.innerHTML = `<span class="ref">${esc(verseLabel(i))}</span>
                   <span class="txt">${esc(genreLabel(book.genre))}</span>
                   <span class="txt">${esc(gloss(i))}</span>`;
  tip.style.left = `${event.clientX + 14}px`;
  tip.style.top = `${event.clientY + 14}px`;
  tip.style.opacity = 1;
  renderer.domElement.style.cursor = 'pointer';
});

renderer.domElement.addEventListener('click', event => {
  const i = pick(event);
  if (i < 0) return;
  showDetails(i);
  // sur petit écran le panneau est un tiroir fermé : sans cela, toucher un
  // point n'afficherait rien
  if (isNarrow()) openDrawer('details');
});

el('details').addEventListener('click', event => {
  const button = event.target.closest('[data-goto]');
  if (!button) return;
  const j = Number(button.dataset.goto);
  showDetails(j);
  flyTo(j);
});

/* --------------------------------------------------------------- événements */
el('search').addEventListener('input', event => {
  state.query = event.target.value;
  refresh();
});
el('colormode').addEventListener('change', event => {
  state.colorMode = event.target.value;
  renderLegend();
  refresh();
  writePermalink();
});
el('testaments').addEventListener('change', event => {
  const key = event.target.dataset.testament;
  if (!key) return;
  event.target.checked ? state.testaments.add(key) : state.testaments.delete(key);
  refresh();
});
el('genres').addEventListener('change', event => {
  const g = event.target.dataset.genreInput;
  if (!g) return;
  event.target.checked ? state.genres.add(g) : state.genres.delete(g);
  refresh();
});
el('genres').addEventListener('pointerover', event => {
  const row = event.target.closest('[data-genre]');
  const g = row ? row.dataset.genre : null;
  if (g !== state.isolatedGenre) { state.isolatedGenre = g; refresh(); }
});
el('genres').addEventListener('pointerleave', () => {
  if (state.isolatedGenre) { state.isolatedGenre = null; refresh(); }
});
el('cluster-select').addEventListener('change', event => {
  state.cluster = event.target.value;
  renderClusterInfo();
  renderLegend();     // la légende montre la couleur de l'amas choisi
  refresh();
});
el('only-cross').addEventListener('change', event => {
  state.onlyCross = event.target.checked;
  refresh();
});
el('show-xrefs').addEventListener('change', event => {
  state.showXrefs = event.target.checked;
  if (state.selected >= 0) drawLinks(state.selected);
  saveState();
});
el('spin').addEventListener('change', event => {
  state.spin = event.target.checked;
  controls.autoRotate = state.spin;
  saveState();
});
el('psize').addEventListener('input', event => {
  state.pointSize = Number(event.target.value);
  material.uniforms.uScale.value = state.pointSize;
  saveState();
});
el('lang-select').addEventListener('change', event => setLanguage(event.target.value));
el('reset').addEventListener('click', () => {
  state.query = ''; el('search').value = '';
  state.cluster = 'all';
  state.onlyCross = false; el('only-cross').checked = false;
  state.testaments = new Set(['Ancien', 'Nouveau']);
  state.genres = new Set(data.genres);
  renderPanels();
  renderClusterInfo();
  refresh();
});
/* Recentrer ne touche qu'à la caméra. Le verset sélectionné, son halo et ses
   traits restent en place : on recentre justement pour retrouver ses repères
   autour de lui, et le panneau de droite continuerait de l'afficher de toute
   façon — l'effacer d'un côté seulement laissait les deux en désaccord. */
el('recenter').addEventListener('click', () => {
  controls.target.set(0, 0, 0);
  camera.position.set(0, 0, 260);
});

/* L'encart explicatif est ouvert à la première visite — c'est là qu'on apprend
   à lire la carte — mais il occupe toute la colonne. Une fois replié, il le
   reste : inutile de refaire lire la même chose à chaque chargement. */
{
  const howto = el('howto');
  if (store.get('howto') === 'ferme') howto.open = false;
  howto.addEventListener('toggle', () =>
    store.set('howto', howto.open ? 'ouvert' : 'ferme'));
}

/* ------------------------------------------------------------ tiroirs mobiles */
/* Sous 1000 px, deux colonnes flottantes ne laisseraient plus rien voir du
   nuage. Les panneaux deviennent des tiroirs fermés, ouverts à la demande, et
   jamais les deux à la fois : ils se recouvriraient. Le seuil est celui de la
   media query correspondante dans index.html. */
const DRAWER_WIDTH = 1100;
const isNarrow = () => innerWidth <= DRAWER_WIDTH;

function setDrawer(id, open) {
  el(id).classList.toggle('open', open);
  el(`open-${id}`).setAttribute('aria-expanded', String(open));
}

/* La classe sur <body> commande la légende de carte et les étiquettes d'axes :
   un tiroir ouvert recouvre le nuage, elles n'ont plus rien à désigner. */
function syncDrawers() {
  const open = ['controls', 'details']
    .some(id => el(id).classList.contains('open'));
  document.body.classList.toggle('drawer-open', open);
  measureScene();
}

function openDrawer(id) {
  for (const panel of ['controls', 'details']) setDrawer(panel, panel === id);
  syncDrawers();
}

function closeDrawers() {
  for (const panel of ['controls', 'details']) setDrawer(panel, false);
  syncDrawers();
}

// le tiroir glisse en 220 ms : mesuré à l'instant du clic, son rectangle est
// encore hors écran et les étiquettes d'axes croiraient la place libre
for (const id of ['controls', 'details']) {
  el(id).addEventListener('transitionend', measureScene);
}

for (const id of ['controls', 'details']) {
  el(`open-${id}`).addEventListener('click', () => {
    if (el(id).classList.contains('open')) closeDrawers();
    else openDrawer(id);
  });
}
for (const button of document.querySelectorAll('[data-close]')) {
  button.addEventListener('click', closeDrawers);
}

/* La loupe déplie le champ de recherche sur écran étroit.
                                                                             |
   Le refermer efface la requête, et ce n'est pas une commodité : une requête
   masque les versets qui ne lui correspondent pas. La laisser vivre derrière
   un champ invisible cacherait la moitié de la Bible sans que rien ne le dise,
   ce que ce projet refuse ailleurs — dans les permaliens, dans la légende. Un
   filtre qu'on ne voit pas ne doit pas pouvoir agir. */
el('open-search').addEventListener('click', () => {
  const box = el('topsearch');
  const open = !box.classList.contains('open');
  box.classList.toggle('open', open);
  el('open-search').setAttribute('aria-expanded', String(open));
  if (open) {
    el('search').focus();
  } else if (state.query) {
    state.query = '';
    el('search').value = '';
    refresh();
  }
  measureScene();
});
addEventListener('keydown', event => {
  if (event.key === 'Escape') closeDrawers();
});

/* ---------------------------------------------------------- axes thématiques */
/* La carte UMAP place bien, mais ne se lit pas : ses axes ne veulent rien dire.
   Ici, chaque axe est un thème choisi d'avance, et une position devient une
   affirmation lisible — « ce verset penche vers la miséricorde ». */
let axisScores = null;
const AXES = Array.isArray(data.axes) ? data.axes : [];

if (AXES.length) {
  try {
    const response = await fetch('data/axes.bin');
    if (response.ok) {
      const buffer = await response.arrayBuffer();
      if (buffer.byteLength === AXES.length * N * 4) {
        axisScores = new Float32Array(buffer);   // rangé axe par axe
      }
    }
  } catch { /* la carte reste utilisable sans les axes */ }
}

/* ------------------------------------------------------- les deux cartes */
/* Deux cartes, pas deux versions d'une carte. Le sens est calculé sur un texte
   précis : changer de texte change les voisinages, les amas et les échos entre
   Testaments. Deux versets côte à côte chez Segond peuvent se retrouver loin
   l'un de l'autre dans la World English Bible, et cet écart est le sujet, pas
   un défaut.
                                                                             |
   Ne changent pas : les versets eux-mêmes, les livres, les genres et les
   renvois traditionnels. Ils restent dans `verses.json`, chargé une fois. Une
   seconde carte ne coûte donc que sa géométrie, quelques mégaoctets, et n'est
   téléchargée que si on la demande. */
const geometries = new Map([['fr', {
  clusters: data.clusters, cluster: data.cluster, nn: data.nn,
  nnSim: data.nnSim, crossT: data.crossT,
  positions: new Float32Array(umapPositions), axes: axisScores,
}]]);

async function loadGeometry(basis) {
  if (geometries.has(basis)) return geometries.get(basis);

  const [buffer, geometry] = await Promise.all([
    fetch(`data/positions_${basis}.bin`).then(r => {
      if (!r.ok) throw new Error(`positions_${basis}.bin introuvable`);
      return r.arrayBuffer();
    }),
    fetch(`data/geometry_${basis}.json`).then(r => {
      if (!r.ok) throw new Error(`geometry_${basis}.json introuvable`);
      return r.json();
    }),
  ]);

  const coordinates = new Float32Array(buffer);
  if (coordinates.length !== N * 3 || geometry.cluster.length !== N) {
    throw new Error(`carte « ${basis} » désynchronisée du corpus`);
  }
  // Le tampon des liens de voisinage est dimensionné une fois pour toutes au
  // démarrage. Une carte calculée avec un autre `--neighbours` le déborderait.
  if (geometry.nn[0].length !== data.nn[0].length) {
    throw new Error(`carte « ${basis} » : ${geometry.nn[0].length} voisins `
      + `par verset au lieu de ${data.nn[0].length}`);
  }

  /* Les axes sont refaits sur la nouvelle base : les mêmes thèmes, mais
     projetés sur d'autres vecteurs. Leur absence n'est pas fatale, elle prive
     seulement cette carte de la disposition par axes. */
  let axes = null;
  if (AXES.length) {
    try {
      const response = await fetch(`data/axes_${basis}.bin`);
      if (response.ok) {
        const blob = await response.arrayBuffer();
        if (blob.byteLength === AXES.length * N * 4) axes = new Float32Array(blob);
      }
    } catch { /* la carte reste utilisable sans ses axes */ }
  }

  const entry = {
    clusters: geometry.clusters, cluster: geometry.cluster, nn: geometry.nn,
    nnSim: geometry.nnSim, crossT: geometry.crossT,
    positions: coordinates, axes,
  };
  geometries.set(basis, entry);
  return entry;
}

/** Bascule la carte sur un autre texte de calcul. */
async function setBasis(basis, { explicit = false, animate = true } = {}) {
  if (!BASES.includes(basis)) return false;
  if (basis === state.basis && geometries.has(basis)) {
    if (explicit) { state.basisChosen = true; saveState(); }
    renderBasisSeg();
    return true;
  }

  const seg = el('basis-seg');
  seg.classList.add('busy');
  let geometry;
  try {
    geometry = await loadGeometry(basis);
  } catch (error) {
    // Une carte annoncée mais absente ne doit pas laisser l'application dans un
    // état à moitié changé : on ne touche à rien et on le dit.
    seg.classList.remove('busy');
    seg.classList.add('failed');
    console.error(error);
    renderBasisSeg();
    return false;
  }
  seg.classList.remove('busy', 'failed');

  state.basis = basis;
  if (explicit) state.basisChosen = true;

  data.clusters = geometry.clusters;
  data.cluster = geometry.cluster;
  data.nn = geometry.nn;
  data.nnSim = geometry.nnSim;
  data.crossT = geometry.crossT;
  clusterById.clear();
  for (const cluster of geometry.clusters) clusterById.set(cluster.id, cluster);
  umapPositions.set(geometry.positions);
  axisScores = geometry.axes;

  // Un amas choisi n'a pas d'équivalent dans l'autre carte : ce ne sont pas les
  // mêmes groupes, seulement des numéros qui se ressemblent. Garder le filtre
  // masquerait la Bible au nom d'un amas qui n'existe plus.
  if (state.cluster !== 'all' && !clusterById.has(Number(state.cluster))) {
    state.cluster = 'all';
  }
  // Les scores de thème ont été calculés dans l'espace vectoriel de l'autre
  // texte. Les garder colorierait la nouvelle carte avec les similarités de
  // l'ancienne, ce qui serait faux sans en avoir l'air.
  if (themeScores) resetTheme();
  if (!axisScores && state.layout === 'axes') state.layout = 'map';
  el('layout-seg').hidden = !axisScores;

  /* `renderAll` pose la nouvelle carte d'un coup. On garde donc les positions
     de l'ancienne pour repartir d'elles : voir les points glisser d'un
     agencement à l'autre montre l'ampleur du désaccord entre les deux textes,
     là où un remplacement instantané donnerait deux images sans rapport. */
  const from = animate ? new Float32Array(positions) : null;
  renderAll();
  renderBasisSeg();
  if (from) {
    const goal = new Float32Array(positions);
    positions.set(from);
    moveTo(goal);
  }
  saveState();
  return true;
}

/** Met le sélecteur de carte à jour, et le cache s'il n'y a rien à choisir. */
function renderBasisSeg() {
  const seg = el('basis-seg');
  seg.hidden = BASES.length < 2;
  if (seg.hidden) return;
  seg.innerHTML = BASES.map(basis => {
    const name = esc(basisEdition(basis));
    return `<button data-basis="${basis}" title="${esc(t('basis.title'))}"
      aria-pressed="${basis === state.basis}">${name}</button>`;
  }).join('');
}

const axisName = axis => (lang === 'en' ? axis.en : axis.fr);
const poleNames = axis => (lang === 'en'
  ? [axis.neg_en, axis.pos_en] : [axis.neg_fr, axis.pos_fr]);

/** Coordonnées issues des trois axes choisis, à l'échelle du nuage UMAP. */
function axisPositions(picks) {
  const out = new Float32Array(N * 3);
  for (let a = 0; a < 3; a++) {
    const base = picks[a] * N;
    for (let i = 0; i < N; i++) out[i * 3 + a] = axisScores[base + i] * 90;
  }
  return out;
}

/* ------------------------------------------------ les axes, dessinés en 3D */
/* Nommer les axes dans le panneau de gauche ne suffit pas : au moment de
   regarder le nuage, on ne sait plus quelle direction porte quoi. Les trois
   directions sont donc tracées dans la scène, chacune avec son ton, et leurs
   pôles étiquetés à leurs extrémités — l'étiquette suit la rotation. */
const AXIS_REACH = 104;
const AXIS_TONES = ['#86b6ef', '#ef8a4f', '#5bbd94'];

const gizmoGeometry = new THREE.BufferGeometry();
{
  const points = [];
  const tones = [];
  for (let a = 0; a < 3; a++) {
    const tone = new THREE.Color(AXIS_TONES[a]);
    for (const sign of [-1, 1]) {
      const end = [0, 0, 0];
      end[a] = sign * AXIS_REACH;
      points.push(0, 0, 0, end[0], end[1], end[2]);
      // dégradé du centre vers le pôle : la direction se lit sans flèche
      tones.push(tone.r * 0.15, tone.g * 0.15, tone.b * 0.15,
                 tone.r, tone.g, tone.b);
    }
  }
  gizmoGeometry.setAttribute('position',
    new THREE.BufferAttribute(new Float32Array(points), 3));
  gizmoGeometry.setAttribute('color',
    new THREE.BufferAttribute(new Float32Array(tones), 3));
}
const axisGizmo = new THREE.LineSegments(gizmoGeometry,
  new THREE.LineBasicMaterial({ vertexColors: true, transparent: true,
                                opacity: 0.6 }));
axisGizmo.visible = false;
scene.add(axisGizmo);

const axisLabelNodes = [];
{
  const box = el('axis-labels');
  for (let a = 0; a < 3; a++) {
    for (const sign of [-1, 1]) {
      const node = document.createElement('div');
      node.className = `lab ${'xyz'[a]}`;
      box.appendChild(node);
      const world = new THREE.Vector3();
      world.setComponent(a, sign * (AXIS_REACH + 14));
      axisLabelNodes.push({ node, axis: a, sign, world });
    }
  }
}

const projected = new THREE.Vector3();
function updateAxisLabels() {
  if (!axisGizmo.visible) return;
  for (const label of axisLabelNodes) {
    projected.copy(label.world).project(camera);
    const x = (projected.x * 0.5 + 0.5) * innerWidth;
    const y = (-projected.y * 0.5 + 0.5) * innerHeight;
    // projected.z ≥ 1 : le pôle est passé derrière la caméra. Les bornes
    // écartent l'étiquette dès qu'elle empiéterait sur un panneau, sur le titre
    // ou sur la légende du bas — mieux vaut un pôle absent qu'illisible.
    const readable = projected.z < 1 && x > sceneLeft && x < sceneRight &&
                     y > sceneTop && y < sceneBottom;
    label.node.style.opacity = readable ? '1' : '0';
    if (readable) {
      label.node.style.transform =
        `translate(-50%, -50%) translate(${x.toFixed(1)}px, ${y.toFixed(1)}px)`;
    }
  }
}

function renderAxisLabels() {
  for (const label of axisLabelNodes) {
    const axis = AXES[state.axisPick[label.axis]];
    const poles = axis ? poleNames(axis) : ['', ''];
    label.node.textContent = label.sign < 0 ? poles[0] : poles[1];
  }
}

/** Corrélation de Pearson entre deux axes, sur les 31 170 versets. */
function axisCorrelation(a, b) {
  const baseA = a * N;
  const baseB = b * N;
  let sumA = 0;
  let sumB = 0;
  for (let i = 0; i < N; i++) {
    sumA += axisScores[baseA + i];
    sumB += axisScores[baseB + i];
  }
  const meanA = sumA / N;
  const meanB = sumB / N;
  let varA = 0;
  let varB = 0;
  let covariance = 0;
  for (let i = 0; i < N; i++) {
    const da = axisScores[baseA + i] - meanA;
    const db = axisScores[baseB + i] - meanB;
    varA += da * da;
    varB += db * db;
    covariance += da * db;
  }
  const spread = Math.sqrt(varA * varB);
  return spread ? covariance / spread : 0;
}

/* Légende posée sur la carte elle-même : elle répond à « qu'est-ce que je
   regarde », question que le panneau de réglages ne traite nulle part. */
/* L'encart « comment lire » décrit la vue en cours, pas la vue par défaut :
   « les axes ne signifient rien » est vrai de la carte UMAP et faux des axes
   nommés, où c'est exactement l'inverse. */
function renderHowto() {
  const useAxes = state.layout === 'axes' && axisScores;
  el('howto-title').textContent = t(useAxes ? 'howto.titleAxes' : 'howto.title');
  for (const rank of [1, 2, 3]) {
    el(`howto-${rank}`).innerHTML = t(`howto.${useAxes ? 'a' : 'p'}${rank}`);
  }
}

function renderMapKey() {
  const useAxes = state.layout === 'axes' && axisScores;
  const head = document.querySelector('#mapkey .mk-h');
  const body = document.querySelector('#mapkey .mk-p');
  head.textContent = t(useAxes ? 'mapkey.axes.h' : 'mapkey.map.h');
  body.innerHTML = t(useAxes ? 'mapkey.axes.p' : 'mapkey.map.p');
  /* Sur quel texte le sens a-t-il été calculé ? La question ne se pose pas
     tant qu'il n'y a qu'une réponse possible ; dès qu'il y en a deux, la
     légende doit la donner, sans quoi on lit une carte sans savoir de quoi
     elle est la carte. */
  if (BASES.length > 1) {
    body.innerHTML += `<br><span class="mk-basis">${esc(t('mapkey.basis',
      { edition: basisEdition(state.basis) }))}</span>`;
  }
  if (!useAxes) return;

  /* Deux axes fortement corrélés donnent un nuage aplati en plan — la
     question la plus fréquente devant cette vue. Ce n'est pas un artefact :
     c'est que les deux thèmes se recouvrent dans le texte. On le mesure donc
     et on le dit, plutôt que de laisser croire à un bogue d'affichage. */
  let worst = null;
  for (const [a, b] of [[0, 1], [0, 2], [1, 2]]) {
    const r = Math.abs(axisCorrelation(state.axisPick[a], state.axisPick[b]));
    if (!worst || r > worst.r) worst = { r, a, b };
  }
  if (worst && worst.r >= 0.45) {
    const named = [worst.a, worst.b].map(k => axisName(AXES[state.axisPick[k]]));
    body.innerHTML += `<br><span class="mk-flat">${esc(t('mapkey.flat', {
      a: named[0], b: named[1], r: Math.round(worst.r * 100) }))}</span>`;
  }
}

function syncDrawPositions() {
  for (let slot = 0; slot < N; slot++) {
    const i = order[slot];
    drawPositions[slot * 3] = positions[i * 3];
    drawPositions[slot * 3 + 1] = positions[i * 3 + 1];
    drawPositions[slot * 3 + 2] = positions[i * 3 + 2];
  }
  geometry.getAttribute('position').needsUpdate = true;
  geometry.computeBoundingSphere();   // sans quoi le pointage viserait à côté
}

let moving = null;
/** Glisse le nuage entier vers de nouvelles coordonnées, en douceur. */
function moveTo(goal) {
  if (moving) cancelAnimationFrame(moving);
  const from = new Float32Array(positions);
  let step = 0;
  const total = 40;
  const tick = () => {
    step += 1;
    const eased = 1 - Math.pow(1 - step / total, 3);
    for (let k = 0; k < positions.length; k++) {
      positions[k] = from[k] + (goal[k] - from[k]) * eased;
    }
    syncDrawPositions();
    syncSelection();
    moving = step < total ? requestAnimationFrame(tick) : null;
  };
  tick();
}

function renderAxisPickers() {
  for (const [slot, id] of [[0, 'axis-x'], [1, 'axis-y'], [2, 'axis-z']]) {
    const select = el(id);
    select.innerHTML = AXES.map((axis, i) =>
      `<option value="${i}">${esc(axisName(axis))}</option>`).join('');
    select.value = String(state.axisPick[slot]);
  }
}

function applyLayout(animate = true) {
  writePermalink();
  const useAxes = state.layout === 'axes' && axisScores;
  // le choix se fait dans l'en-tête ; le panneau ne montre les trois sélecteurs
  // d'axes que lorsqu'ils servent à quelque chose
  el('layout-sect').hidden = !useAxes;
  for (const button of document.querySelectorAll('#layout-seg button')) {
    button.setAttribute('aria-pressed',
      String(button.dataset.layout === (useAxes ? 'axes' : 'map')));
  }
  axisGizmo.visible = !!useAxes;
  if (useAxes) renderAxisLabels();
  else for (const label of axisLabelNodes) label.node.style.opacity = '0';
  // la légende du bas change de hauteur selon son contenu : on la mesure après
  // l'avoir écrite, sinon les étiquettes d'axes viendraient chevaucher son texte
  renderMapKey();
  renderHowto();
  measureScene();
  const note = el('layout-note');
  note.innerHTML = t(useAxes ? 'layout.axesNote' : 'layout.mapNote');
  if (useAxes) {
    const [x, y, z] = state.axisPick.map(i => poleNames(AXES[i]));
    note.innerHTML += `<br>X : ${esc(x[0])} → ${esc(x[1])}` +
      `<br>Y : ${esc(y[0])} → ${esc(y[1])}` +
      `<br>Z : ${esc(z[0])} → ${esc(z[1])}`;
  }
  const goal = useAxes ? axisPositions(state.axisPick) : umapPositions;
  if (animate) { moveTo(goal); }
  else { positions.set(goal); syncDrawPositions(); }
}

/* ------------------------------------------------------- recherche par thème */
/* Une recherche de mots ne trouve que ce qui contient les mots. Ici la phrase
   saisie est encodée par le même modèle que le corpus, et comparée à chaque
   verset : « le pardon des offenses » remonte des versets qui n'emploient
   aucun de ces trois mots. */
let themeScores = null;
let themeFloor = 0;
let themeCeil = 1;
/* Faux tant que le serveur n'a pas répondu qu'il sait encoder une phrase. La
   valeur de départ est la bonne : sur un hébergement statique, la sonde
   `api/status` n'aboutira jamais, et la ligne d'aide sous le champ doit être là
   dès le premier rendu plutôt que d'apparaître après coup. */
let themeAvailable = false;

function themeIntensity(i) {
  if (!themeScores) return 0;
  return Math.max(0, Math.min(1,
    (themeScores[i] - themeFloor) / (themeCeil - themeFloor || 1)));
}

function ensureThemeOption() {
  const select = el('colormode');
  if (select.querySelector('option[value="theme"]')) return;
  const option = document.createElement('option');
  option.value = 'theme';
  option.dataset.i18n = 'color.theme';
  option.textContent = t('color.theme');
  select.appendChild(option);
}

function renderThemeTop() {
  const box = el('theme-top');
  if (!themeScores) { box.innerHTML = ''; return; }
  const best = Array.from({ length: N }, (_, i) => i)
    .sort((a, b) => themeScores[b] - themeScores[a]).slice(0, 8);
  box.innerHTML = best.map(i =>
    `<button class="nb" data-goto="${i}">
       <span class="top"><span class="r">${esc(verseLabel(i))}</span>
       <span class="s">${themeScores[i].toFixed(3)}</span></span>
       <span class="t">${esc(gloss(i))}</span></button>`).join('');
}

async function searchTheme(query) {
  const status = el('theme-status');
  status.className = 'legend-note busy';
  status.textContent = t('theme.loading');
  try {
    // la base voyage avec la requête : une similarité ne vaut que dans
    // l'espace vectoriel de la carte que l'on regarde
    const response = await fetch(`api/theme?q=${encodeURIComponent(query)}`
      + `&basis=${encodeURIComponent(state.basis)}`);
    if (!response.ok) {
      const detail = await response.json().catch(() => ({}));
      throw new Error(detail.error || `HTTP ${response.status}`);
    }
    const buffer = await response.arrayBuffer();
    if (buffer.byteLength !== N * 4) {
      throw new Error(`réponse inattendue (${buffer.byteLength} octets)`);
    }
    themeScores = new Float32Array(buffer);

    // On n'éclaire que le haut du classement : les similarités cosinus sont
    // toutes élevées et un dégradé sur toute l'étendue ne montrerait rien.
    const sorted = Float32Array.from(themeScores).sort();
    themeFloor = sorted[Math.floor(sorted.length * 0.90)];
    themeCeil = sorted[sorted.length - 1];

    ensureThemeOption();
    state.colorMode = 'theme';
    el('colormode').value = 'theme';
    status.className = 'legend-note';
    status.textContent = t('theme.done', { q: query });
    renderThemeTop();
    renderLegend();
    refresh();
  } catch (error) {
    status.className = 'legend-note failed';
    status.textContent = t('theme.failed', { msg: error.message });
  }
}

el('theme-go').addEventListener('click', () => {
  const query = el('theme-input').value.trim();
  if (query) searchTheme(query);
});
el('theme-input').addEventListener('keydown', event => {
  if (event.key === 'Enter') el('theme-go').click();
});
/** Efface la recherche par thème et le mode de couleur qui en dépendait. */
function resetTheme() {
  themeScores = null;
  el('theme-input').value = '';
  el('theme-status').textContent = t('theme.hint');
  el('theme-status').className = 'legend-note';
  el('theme-top').innerHTML = '';
  const option = el('colormode').querySelector('option[value="theme"]');
  if (option) option.remove();
  if (state.colorMode === 'theme') {
    state.colorMode = 'canon';
    el('colormode').value = 'canon';
    renderLegend();
  }
  refresh();
}

el('theme-clear').addEventListener('click', resetTheme);
el('theme-top').addEventListener('click', event => {
  const button = event.target.closest('[data-goto]');
  if (!button) return;
  const i = Number(button.dataset.goto);
  showDetails(i);
  flyTo(i);
});

el('layout-seg').addEventListener('click', event => {
  const button = event.target.closest('[data-layout]');
  if (!button || button.dataset.layout === state.layout) return;
  state.layout = button.dataset.layout;
  applyLayout();
  saveState();
});

el('basis-seg').addEventListener('click', event => {
  const button = event.target.closest('[data-basis]');
  if (!button || button.dataset.basis === state.basis) return;
  setBasis(button.dataset.basis, { explicit: true });
});
for (const [slot, id] of [[0, 'axis-x'], [1, 'axis-y'], [2, 'axis-z']]) {
  el(id).addEventListener('change', event => {
    state.axisPick[slot] = Number(event.target.value);
    applyLayout();
    saveState();
  });
}

/* ------------------------------------------------------- copie du permalien */
el('copy-link').addEventListener('click', async () => {
  const button = el('copy-link');
  const url = location.href;
  let ok = false;
  try {
    // navigator.clipboard exige un contexte sécurisé : présent sur GitHub Pages
    // (HTTPS) et sur 127.0.0.1, absent d'un http:// distant. D'où le repli.
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(url);
      ok = true;
    } else {
      const field = document.createElement('textarea');
      field.value = url;
      field.setAttribute('readonly', '');
      field.style.cssText = 'position:fixed;top:-1000px;opacity:0';
      document.body.append(field);
      field.select();
      ok = document.execCommand('copy');
      field.remove();
    }
  } catch { ok = false; }

  // Un bouton qui ne répond rien laisse croire qu'il n'a pas été pressé.
  button.textContent = t(ok ? 'share.copied' : 'share.failed');
  button.classList.toggle('done', ok);
  setTimeout(() => {
    button.textContent = t('share.copy');
    button.classList.remove('done');
  }, 1800);
});

/* L'URL peut changer sans nous : bouton Précédent, lien collé dans la barre
   d'adresse, ancre cliquée. On réapplique alors ce que le fragment décrit. */
addEventListener('hashchange', () => {
  const shared = readPermalink();
  if (!shared) return;
  applyShared(shared);
  if (shared.selected >= 0 && shared.selected !== state.selected) {
    showDetails(shared.selected);
    flyTo(shared.selected, true);
  }
});

/* ------------------------------------------------------- application langue */
/** Renseigne tous les éléments porteurs d'un attribut `data-i18n*`. */
function applyStaticText() {
  document.documentElement.lang = lang;
  for (const node of document.querySelectorAll('[data-i18n]')) {
    node.textContent = t(node.dataset.i18n);
  }
  // `data-i18n-html` est réservé aux textes de l'application qui contiennent
  // du balisage de mise en forme (<b>, <em>) ; jamais à des données externes.
  for (const node of document.querySelectorAll('[data-i18n-html]')) {
    node.innerHTML = t(node.dataset.i18nHtml);
  }
  for (const node of document.querySelectorAll('[data-i18n-ph]')) {
    node.placeholder = t(node.dataset.i18nPh);
  }
  document.title = t('app.title');
  el('search').title = t('search.hint');
  // la loupe porte une icône, pas un mot : son libellé passe par l'attribut
  el('open-search').setAttribute('aria-label', t('mob.search'));
  el('open-search').title = t('mob.search');
  el('subtitle').textContent =
    t('app.subtitle', { n: num(N), c: data.clusters.length });
  el('det-sub').textContent = state.selected >= 0
    ? verseLabel(state.selected) : t('details.sub');
}

function renderAll() {
  applyStaticText();
  renderPanels();
  if (axisScores) { renderAxisPickers(); applyLayout(false); }
  else { renderMapKey(); renderHowto(); }   // les deux existent sans les axes
  renderLegend();
  renderClusterInfo();
  if (themeScores) renderThemeTop();
  else if (!el('theme-status').classList.contains('failed')) {
    el('theme-status').textContent = t('theme.hint');
  }
  if (state.selected >= 0) showDetails(state.selected);
  else el('det-body').innerHTML =
    `<p class="legend-note">${t('details.intro')}</p>`;
  refresh();
}

function setLanguage(code) {
  if (!STRINGS[code] || code === lang) return;
  lang = code;
  el('lang-select').value = code;
  renderAll();
  renderBasisSeg();
  saveState();
  /* Tant que la carte n'a pas été choisie explicitement, elle suit la langue :
     lire en anglais et regarder la géométrie du Segond serait un décalage
     permanent entre le texte affiché et ce qui le place. Le changement de
     langue, lui, ne l'attend pas — sa géométrie peut demander un aller-retour
     réseau, et l'interface n'a aucune raison de rester figée pendant ce
     temps. */
  const follows = code === 'en' && BASES.includes('en') ? 'en' : 'fr';
  if (!state.basisChosen && follows !== state.basis) setBasis(follows);
}

/* ------------------------------------------------------------------- départ */
restoreState();

/* Un lien partagé passe après les réglages mémorisés et l'emporte sur eux —
   mais seulement sur les clefs qu'il mentionne. Le reste de l'expérience du
   destinataire lui appartient. */
const sharedOnLoad = readPermalink();
if (sharedOnLoad) applyShared(sharedOnLoad);

el('colormode').value = state.colorMode;
el('only-cross').checked = state.onlyCross;
el('show-xrefs').checked = state.showXrefs;
el('spin').checked = state.spin;
controls.autoRotate = state.spin;
el('show-xrefs').closest('label').style.display = data.xref ? '' : 'none';
el('psize').value = state.pointSize;
material.uniforms.uScale.value = state.pointSize;
el('lang-select').value = lang;

/* La carte demandée, si ce n'est pas celle qu'apporte `verses.json`, est
   chargée avant le premier rendu : la faire apparaître puis se remplacer sous
   les yeux du visiteur donnerait à voir deux résultats là où il n'y en a
   qu'un. Un échec est sans gravité — on reste sur la carte française et le
   sélecteur le montre. */
if (state.basis !== 'fr') {
  setProgress(0.8, t('loading.scene'));
  const ok = await setBasis(state.basis, { animate: false });
  if (!ok) state.basis = 'fr';
}
renderBasisSeg();

// la disposition par axes n'a de sens que si `bible_visu.axes` a tourné
if (axisScores) {
  el('layout-seg').hidden = false;
  renderAxisPickers();
}

/* La recherche par thème dépend du serveur : on le sonde avant d'ouvrir la
   section. Servi par un hébergement statique (Live Server, GitHub Pages…),
   `api/status` répond 404 : la section reste masquée et le reste fonctionne.
   Le navigateur consigne ce 404 dans sa console — c'est attendu, pas une
   erreur de l'application. */
try {
  const status = await fetch('api/status').then(r => r.ok ? r.json() : null);
  if (status && status.theme) {
    el('theme-sect').hidden = false;
    themeAvailable = true;
  } else if (status) {
    el('theme-sect').hidden = false;
    el('theme-go').disabled = true;
    el('theme-input').disabled = true;
    el('theme-status').className = 'legend-note failed';
    el('theme-status').textContent = t('theme.unavailable', { msg: status.reason });
  }
} catch { /* servi par un hébergement statique : la section reste cachée */ }

// tout changement de filtre est mémorisé, sans avoir à le répéter partout
for (const id of ['colormode', 'testaments', 'genres', 'cluster-select', 'only-cross']) {
  el(id).addEventListener('change', saveState);
}

renderAll();
setProgress(1, 'ready');
el('loading').remove();

/* Le verset d'un lien s'ouvre après le premier rendu : la scène doit exister
   pour qu'on puisse y voler. Sur écran étroit on déplie aussi le tiroir — un
   lien vers un verset dont on ne verrait pas le texte ne tiendrait qu'à moitié
   sa promesse. */
if (sharedOnLoad && sharedOnLoad.selected >= 0) {
  showDetails(sharedOnLoad.selected);
  flyTo(sharedOnLoad.selected, true);
  if (isNarrow()) openDrawer('details');
}

renderer.setAnimationLoop(() => {
  controls.update();
  // le fondu de profondeur se mesure par rapport à ce que l'on regarde :
  // il faut donc la distance caméra → cible, qui change à chaque zoom
  material.uniforms.uOrbit.value = controls.getDistance();

  /* Le halo garde une taille fixe à l'écran, et non dans le monde. Avec un
     rayon figé en unités du monde il ne marquait plus rien : 17 px de large
     vue d'ensemble — on ne voyait pas le verset sélectionné — et 375 px une
     fois entré dans le nuage, où sa grille filaire recouvrait la carte et
     grouillait au moindre mouvement de caméra. Un repère de sélection doit
     avoir la même taille apparente partout ; c'est son rôle. */
  if (halo.visible) {
    const projCss = innerHeight /
      (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2));
    const distance = camera.position.distanceTo(halo.position);
    halo.scale.setScalar(HALO_PX * distance / (projCss * HALO_RADIUS));
  }

  updateAxisLabels();
  renderer.render(scene, camera);
});

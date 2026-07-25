# Bible 3D — a semantic map of the Bible

**English** · [Français](README.fr.md)

### → [Open the live map](https://macmachi.github.io/bible-3D/)

*31,170 verses in your browser, nothing to install. Works offline once loaded.*

The **31,170 verses** of the Bible placed in three-dimensional space **by what
they mean**, not by where they sit in the book. Two verses next to each other on
screen are about the same thing, even when a thousand pages and two languages
separate them.

Four texts side by side: **Masoretic Hebrew** (Westminster Leningrad Codex),
**Greek** (SBLGNT), **French** (Louis Segond 1910) and **English** (World English
Bible). The interface is available in French and English.

The machine is given no prior knowledge: it knows nothing of books, authors,
genres or chronology. It sees text and nothing else. Every grouping you can see
was therefore **found**, not imposed.

![The semantic map: all 31,170 verses coloured by Testament, with one verse
selected and its nearest neighbours in meaning](docs/carte.png)

*Blue is the Old Testament, red the New. Where the two mingle, both Testaments
are treating the same subject. The verse on display, Matthew 6:12, was found by
describing an idea — "forgiving those who wrong us" — not by searching for a
word.*

---

## Contents

- [Getting started](#getting-started)
- [What you are looking at](#what-you-are-looking-at)
- [Method: from text to coordinates](#method-from-text-to-coordinates)
- [Four decisions about method](#four-decisions-about-method)
- [Beyond "close to what?"](#beyond-close-to-what)
- [Testing the map against tradition](#testing-the-map-against-tradition)
- [On the search for a hidden code](#on-the-search-for-a-hidden-code)
- [Code layout](#code-layout)
- [Data schema](#data-schema)
- [What is verified](#what-is-verified)
- [Known limitations](#known-limitations)
- [Troubleshooting](#troubleshooting)
- [Licences and copyright](#licences-and-copyright)

---

## Getting started

Requirements: Python 3.11 or later (tested on 3.14), ~5 GB of disk, no graphics
card needed.

```bash
python3 -m venv .venv
./.venv/bin/pip install torch --index-url https://download.pytorch.org/whl/cpu
./.venv/bin/pip install -r requirements.txt

export PYTHONPATH=src
./.venv/bin/python -m bible_visu.fetch      # ~55 MB of source texts
./.venv/bin/python -m bible_visu.corpus     # aligned verse table
./.venv/bin/python -m bible_visu.embed      # the long one — see the table below
./.venv/bin/python -m bible_visu.project    # 3D UMAP + clusters + neighbours
./.venv/bin/python -m bible_visu.crossrefs  # traditional cross-references
./.venv/bin/python -m bible_visu.axes       # named thematic axes (~2 min)
./.venv/bin/python -m bible_visu.export     # viewer payload
./.venv/bin/python serve.py                 # opens http://127.0.0.1:8000
```

Everything stays inside the project folder, **model cache included**
(`data/models/`, ~3 GB). Nothing is written to `~/.cache`, nothing is installed
system-wide.

Each stage reads from and writes to disk, so you can re-run the projection with
different settings without redoing the embedding, which is by far the most
expensive step. The options of `bible_visu.project` that change the map most:
`--n-neighbors` (small: filaments, large: broad masses), `--min-dist` (how tight
the clusters are), `--min-cluster-size` (minimum HDBSCAN cluster size),
`--abtt-neighbours` (neighbour denoising, 8 by default), `--seed` (the
projection is reproducible for a given seed). Thematic axes live in the `AXES`
table of `src/bible_visu/axes.py` — write a few anchor sentences per pole, then
re-run `bible_visu.axes` and `bible_visu.export`. Other translations go through
`corpus.py --translation darby --secondary kjv` (see `TRANSLATIONS` in
`sources.py`).

### Cost of the embedding step

Measured on a recent laptop, 22 cores, no GPU:

| Model | Dimensions | Throughput | Full corpus |
|---|---|---|---|
| `intfloat/multilingual-e5-base` | 768 | 22.2 verses/s | ~23 min *(extrapolated)* |
| `intfloat/multilingual-e5-large` *(default)* | 1024 | 7.1 verses/s | **72.7 min** *(measured)* |

For a first exploration, `--model intfloat/multilingual-e5-base` already gives a
very readable map in a third of the time. The remaining stages are quick:
projection ~5 min, cross-references ~2 min, axes ~2 min, export a few seconds.

### What a full run produces

| | |
|---|---|
| Verses | 31,170 |
| Aligned with the original text | 31,031 (99.55%) |
| Aligned with English | 31,050 (99.62%) |
| Clusters found | 71, plus 46.5% of verses left unclustered |
| Median similarity to nearest neighbour | 0.934 |
| Verses echoed in the other Testament | 12,401 (39.8%) |
| Traditional cross-references loaded | 548,109 links |
| Agreement with tradition | 81.8% |
| Viewer payload | `positions.bin` 365 KB · `axes.bin` 974 KB · `verses.json` 20.1 MB (5.7 MB compressed) |

The high proportion of unclustered verses is not a flaw: HDBSCAN refuses to
assign points that lie in low-density regions rather than forcing them somewhere.
Lowering `--min-cluster-size` reduces that share.

---

## What you are looking at

The screen has four zones:

* **top centre** — the name, then the only two structural decisions: the
  **layout** (semantic map or named axes) and **search**;
* **bottom centre** — a legend laid **over the map**, permanently restating what
  the current view means. Read it first;
* **left** — language, the "how to read this map" panel, then the settings:
  colour, filters, clusters, display. The three axis pickers appear only in the
  "named axes" layout, since they serve no purpose elsewhere;
* **right** — the verse you clicked.

The two explanatory texts — the legend at the bottom and the "how to read"
panel — **change with the layout**, because what is true of one is false of the
other: on the semantic map directions mean nothing, on the named axes they mean
everything.

On a narrow screen (under 1100 px), both panels become closed drawers opened by
the **Settings** and **Verse** buttons: the map then fills the screen, which is
its whole point. Tapping a point opens the verse drawer; `Esc` closes it.

<img src="docs/mobile.png" alt="The app on a phone: compact header, drawers
closed, map full screen" width="300">

| Colour mode | What it reveals |
|---|---|
| **Position in the canon** *(default)* | where a text sits in the Bible. Wherever distant colours mingle, two far-apart passages resemble each other. |
| **Testament** | the regions where Old and New overlap. |
| **Literary genre** | the divide between law, narrative, poetry, prophecy, epistle. |
| **Semantic cluster** | the groups the machine found without being told books exist. The only mode with no colour list: 71 clusters for ten hues, so one swatch per cluster would be a lie. Selecting a cluster shows its own colour. |
| **Cross-Testament echoes** | verses whose closest relatives in meaning sit in the other Testament — the bridges. |
| **Closeness to a theme** | appears after a theme search: how near each verse is to the idea you described. |

Clicking a point shows the verse in Hebrew or Greek and both translations,
**each credited to its edition** — so you always know whether you are reading
Segond or Darby — then two separate lists:

* **its eight nearest relatives in meaning** across the whole Bible, with the
  similarity spelled out. ↔ marks a link crossing the two Testaments, ✓ a link
  that tradition also draws;
* **its traditional cross-references**, independent of any computation.

**Sharing.** Selecting a verse writes it into the address bar as
`#v=Matt.6.12`, and a *Copy link* button sits next to the reference. The link
carries what you are looking at — the verse, the layout, the three axes, the
colour mode — and deliberately **not** the filters: a link that quietly hid half
the Bible would leave the reader believing they saw all of it. It does not carry
your language either, since the OSIS reference is neutral, nor your camera
angle, which on the semantic map means nothing anyway. Opening someone's link
never overwrites your own saved settings.

**Navigation:** left-drag to rotate, wheel to zoom, right-drag to pan. Search
accepts a reference (`Ésaïe 53` as well as `Isaiah 53`), a French or English
word, and the original text — paste `אלהים` or `λόγος` to isolate every verse
containing it. Accents, Hebrew vowel points and Greek breathings are ignored, so
`esaie 53` and `logos` both work.

Every setting — filters, colour mode, layout, point size, rotation, language —
persists between sessions; only the current search does not, since it is a
passing state. Language follows the user's choice first, then the browser's, and
falls back to English when no translation matches.

---

## Method: from text to coordinates

This section walks the whole chain, from nothing.

### 1. Align four texts on a single grid

`corpus.py` produces a table with one row per verse, carrying Hebrew, Greek,
French and English side by side. This is less obvious than it sounds: Masoretic
versification is not Segond's, and the Greek critical text omits passages the
translations keep. Alignment is therefore **declared** verse by verse, never
improvised — 139 verses have no original text, and the interface says so.

### 2. Turn each verse into a point in 1024 dimensions

This is the heart of the method. A **sentence embedding model** is a network
trained so that two sentences close in meaning produce two nearby vectors, and
two unrelated sentences produce distant ones. It does not compare words:
"forgive us our trespasses" and "remember no more my faults" share no vocabulary
and still come out at almost the same place.

The chosen model is **`intfloat/multilingual-e5-large`**:

* it produces a vector of **1024 numbers** per verse — the whole corpus fits in a
  31,170 × 1024 matrix of floats, 128 MB;
* it is **multilingual**, which matters less for the embedding itself (done on
  French, see below) than for theme search, where a query may be phrased in a
  different language from the corpus;
* it requires the **`query: `** prefix before each text, without which the
  vectors produced do not share the frame of reference of its training. That is
  a requirement of the model, not a convention: `embed.py`, `axes.py` and
  `serve.py` all three apply it, otherwise similarities computed in one place
  would not be comparable to those computed in another.

The vectors are **normalised** (scaled to length 1). The dot product of two
normalised vectors is then exactly their **cosine similarity**: 1 for two texts
identical in meaning, 0 for two unrelated ones. Everything that follows —
neighbours, axes, theme search — is nothing but a series of dot products over
that matrix.

### 3. Find the neighbours before reducing

Each verse's eight nearest neighbours are computed **in the full 1024
dimensions**, never on screen coordinates. This matters: reduction to three
dimensions distorts, and two points far apart on screen can be very close
relatives. The lines drawn from the selected verse show exactly that.

The full similarity matrix would weigh 31,170 × 31,170 floats, close to 4 GB, so
`project.py` computes it **in slices**, keeping only the eight best scores from
each slice.

### 4. Flatten to three dimensions with UMAP

**UMAP** looks for a 3D placement that preserves neighbourhoods: points close in
the original space stay close, at the expense of large distances. It works here
in **cosine metric**, consistent with the normalisation, after a preliminary
reduction to 64 principal components that speeds up the computation and removes
a little noise.

What UMAP does must be said plainly: it **distorts**. The immediate neighbourhood
is trustworthy; the global scale is not. That is why the map's axes deliberately
mean nothing, and why the on-screen legend keeps saying so.

### 5. Detect the clusters and name them

**HDBSCAN** groups points by density and — this is its main virtue — **refuses
to classify** those in low-density regions rather than attaching them
arbitrarily. Hence the 46.5% of "unclustered" verses, which are an honest answer
rather than a failure.

Each cluster is then named by **TF-IDF**: the words frequent inside the cluster
*and* rare in the rest of the corpus. That is a descriptive label, not a title:
"travailla · enfanta · meschullam" does indeed pick out a family of genealogies.
Cluster labels stay in French, since they are extracted from the French corpus
used for the computation.

### 6. Project onto axes named in advance

See [Beyond "close to what?"](#beyond-close-to-what) — that is where the map
stops being merely a neighbourhood and becomes readable.

---

## Four decisions about method

### 1. Meaning is computed on the French, not the Hebrew

This is the most important point, and the most counter-intuitive.

No sentence embedding model is trained on Biblical Hebrew or Koine Greek. The
available multilingual models know **modern** Hebrew and Greek — languages whose
morphology, lexicon and syntax differ deeply from their ancient states. Applying
them directly to the WLC would produce a convincing-looking cloud whose groupings
meant nothing: the worst possible outcome, because it is undetectable by eye.

Since verses are aligned 1:1 across versions, meaning is therefore computed on
the translation, while the original text stays attached to each point. To check
this choice rather than take it on trust:

```bash
./.venv/bin/python -m bible_visu.embed --text-column text_orig \
    --out data/processed/embeddings_orig.npy
```

### 2. Two vector spaces, because measurement forced it

*All-but-the-Top* denoising (Mu & Viswanath, 2018) removes the few directions
common to the entire corpus, which encode language and style rather than content.
`scripts/evaluate_abtt.py` measures it against a benchmark of fifteen New
Testament quotations of the Old, whose correspondence is not in dispute.

**On neighbour search, the gain is clear:**

| | no denoising | ABTT = 8 |
|---|---|---|
| Median rank of the true partner | 1 | 2 |
| Mean rank | 41 | 3 |
| In the top 10 | 13/15 | 14/15 |
| In the top 100 | 13/15 | **15/15** |

Leviticus 19:18 ↔ Matthew 22:39 ("your neighbour as yourself") goes from **rank
379 to rank 3**; Hosea 11:1 ↔ Matthew 2:15 from **rank 207 to rank 12**.

**On the layout, it is a disaster:** applied before UMAP, the same treatment
flattens the density differences HDBSCAN feeds on. The 71 clusters collapse to
**4**, one of which swallows 94% of the verses.

Hence two spaces: the raw one to draw the map, the denoised one to say what
resembles what. Both are adjustable — `--abtt-neighbours` and `--abtt-layout`.

One starting hypothesis was in fact **disproved**: denoising was expected to
reduce "narrative gravity", the tendency of a verse to have neighbours only from
its own book. Measured: that share goes from 36.4% to 37.8%. It does not fall.

### 3. Alignment is declared, never hidden

Masoretic versification differs from Segond's (Psalm titles counted as verse 1,
the division of Joel and Malachi), and the SBLGNT omits the passages absent from
the oldest manuscripts (Mark 16:9-20, John 5:4, the pericope of the adulteress).
139 verses therefore keep their translation but have no original text;
`corpus.py` prints the breakdown per book, and the interface says so explicitly
instead of pretending otherwise.

### 4. Colour is verified, not chosen by eye

A scatter plot potentially puts every category in contact with every other. Under
those conditions, and by measurement, the reference palette guarantees legibility
— including for protan, deutan and tritan colour blindness — only up to **three**
hues; at eight, the worst pair falls to ΔE 1.6, which is strictly
indistinguishable.

Hence: the default mode is **sequential**, Testament mode uses only the two
validated slots, Genre mode never rests identity on colour alone — hovering a
legend row isolates that genre — and the three thematic axes use exactly three
hues, precisely the validated limit.

Rendering settled a blending question too: **additive** display is prettier but
adds colours together, so at the heart of a cluster the hue saturates towards
white and encodes nothing but density. Normal blending was chosen, with a **draw
order shuffled** by a fixed permutation — without which Revelation would always
be painted over Genesis and the New Testament would look denser than it is.

---

## Beyond "close to what?"

The UMAP map answers "what resembles what", but not "where is such-and-such a
theme". Two features fill that gap — and both sidestep the limitation measured
above, namely that clusters remain lexical.

### Named thematic axes

![The thematic axes: judgment ↔ mercy on X, narrative ↔ teaching on Y,
law ↔ grace on Z](docs/axes.png)

`bible_visu.axes` builds eight axes **whose meaning is chosen in advance**:
judgment ↔ mercy, law ↔ grace, narrative ↔ teaching, lament ↔ praise,
ritual ↔ justice, present ↔ eschatology, individual ↔ people, war ↔ peace.

Each pole is defined by a handful of anchor sentences; the axis is the
**difference** between the two poles' means. That subtraction cancels what the
two poles have in common — the language, the register, the Biblical style — and
leaves only what tells them apart. This is exactly what clusters lack, where
nothing subtracts the common ground. Each verse is then projected onto the axis
by a simple dot product, and the scale is fixed at the 99.5th percentile of the
absolute value: a lower percentile would saturate hundreds of verses at ±1 and
crush the nuance where it is most interesting.

By choosing three axes for X, Y and Z, **a position becomes readable**: a verse
on the right leans towards the pole named on the right. The three directions are
drawn in the scene and **the six poles written at their ends**, each in its
axis's own tone; the labels follow the rotation and fade out as soon as they
would overlap a panel. The first thing you notice when colouring by Testament:
the New moves markedly towards *mercy* and *teaching*, the Old towards *judgment*
and *narrative*.

**Why is the cloud sometimes flat?** Because two of the three chosen axes
overlap. The app measures the correlation between the selected axes and says so:
in the screenshot above, *judgment ↔ mercy* and *law ↔ grace* overlap by 48%, so
only two genuinely distinct directions remain out of three. That is not a display
defect, it is a result: in the text, those two themes go together.

The cloud is also denser at the centre than on the UMAP map. That is faithful —
on any given axis, most verses really are neutral.

**A badly anchored axis is a trap**, because it produces a ranking that looks
credible and means nothing. The script therefore prints the extreme verses of
each pole, to be read before trusting it. Two axes had to be re-anchored on that
basis: "grace" surfaced any New Testament verse whatsoever — the axis was simply
duplicating Testament mode — and "praise" surfaced the closing greetings of the
epistles. After correction, "grace" surfaces Galatians 2:21 and 1 Peter 2:19,
"praise" the Psalms of rejoicing.

### Natural-language theme search

Describe an idea in plain words; the sentence is encoded by the same model used
for the corpus, and each verse is coloured by its closeness. **This is not a word
search.** For "forgiving those who wrong us", the top six are Matthew 6:12,
Luke 11:4, Matthew 6:14, John 20:23, Colossians 1:14 and Psalm 25:18 — three of
which share no word with the query.

Concrete queries work better than abstract ones: "caring for the stranger and the
poor" surfaces Deuteronomy 10:18 and Psalm 146:9, whereas a multi-clause phrasing
such as "God's faithfulness despite his people's unfaithfulness" falls back on
the field of mercy and loses the contrastive nuance.

Technically, `serve.py` exposes `/api/theme?q=…` and returns a `Float32Array` of
one similarity per verse (125 KB). Only the top decile is lit: cosine
similarities are all high, and a gradient across the whole range would show
nothing. The model is loaded on the first request, once, under a lock; the server
is multi-threaded so that this loading does not freeze the rest. If
`sentence-transformers` is missing, the service declares itself unavailable and
the rest of the viewer carries on.

---

## Testing the map against tradition

`bible_visu.crossrefs` loads the 344,799 cross-references from openbible.info —
the dataset behind Harrison & Römhild's arc visualisation — and confronts them
with semantic neighbourhood.

**The headline result is agreement.** Among verses that have at least one
cross-reference, **81.8%** have at least one semantic neighbour that tradition
also links. A machine that has read nothing but text recovers a substantial part
of what generations of editors established.

Three cases, and what each is worth:

* **confirmed** — semantically close *and* traditionally cross-referenced.
  Surprises nobody, but validates the method;
* **unlinked** — very close, never cross-referenced. This is where to look if you
  are after the non-obvious. **But** inspecting the ten strongest shows mostly
  surface formulas: "three days", "twelve men", "each returned to his house".
  These are leads, not discoveries;
* **semantically distant cross-reference** — tradition links on something other
  than textual resemblance: a type, a fulfilment, a doctrine. That is not an
  error, it is a dimension the model does not see.

**One indispensable precaution:** openbible records cross-references at
*passage* level, not verse level. The Pentecost link appears there as
`Joel 2:30 → Acts 2:19-20`, never as the exact pair Joel 2:31 ↔ Acts 2:20. A
strict verse-to-verse comparison therefore declared one of the best-known
quotations in the Bible "unlinked". The comparison is made with a one-verse
window (`--window`), and the gap between the two measurements is displayed
(81.8% against 68.9% under strict comparison).

---

## On the search for a hidden code

This project was built to explore whether the Bible holds a non-obvious
structure. Two things must be kept apart.

**What this map shows, and what is real and measurable:** thematic groupings that
cut across books and centuries, bridges between Old and New Testament, and 81.8%
agreement with two thousand years of editorial work, obtained without any prior
knowledge.

**What must be approached with method:** the "Bible codes" based on equidistant
letter sequences (ELS). In any sufficiently long text you will *always* find
words at a given step — that is a property of combinatorics, not of the text. The
work of Witztum, Rips and Rosenberg (1994) was tested and then refuted by McKay,
Bar-Natan, Bar-Hillel and Kalai (*Statistical Science*, 1999): the same "codes"
come out of a Hebrew translation of *War and Peace*.

This is why the corpus already stores, for each verse, the text reduced to the
22 Hebrew consonants with final forms normalised (column `text_consonants`,
**1,191,314 letters** in total — the expected Masoretic count). An ELS module can
therefore be plugged onto it, on one condition: that every find be replayed
against permuted text and a control corpus, and reported with its p-value.
Without a null model, an ELS scanner measures nothing.

Other hidden structures do hold up statistically: chiasms, detectable by
embedding similarity; and stylometry, where unsupervised clustering of the
Pentateuch recovers distinct authorial signatures (Koppel et al., 2011).

---

## Code layout

```
src/bible_visu/
  sources.py    table of the 66 books (FR/EN), URLs, self-check on import
  paths.py      on-disk locations — everything inside the project
  fetch.py      downloading                -> data/raw/
  corpus.py     parsing and alignment      -> data/processed/verses.parquet
  embed.py      semantic vectors           -> data/processed/embeddings.npy
  vectors.py    All-but-the-Top denoising
  project.py    3D UMAP, clusters, neighbours -> data/processed/points.parquet
  crossrefs.py  cross-references and comparison -> data/processed/crossrefs.npz
  axes.py       named thematic axes        -> data/processed/axes.npz
  export.py     viewer export              -> viewer/data/
viewer/
  index.html    structure, styles, security policy in a meta tag
  app.js        Three.js application (separate file: the CSP forbids inline)
  vendor/       vendored three.js — no CDN, works offline
  data/         output of `export` — versioned, this is the published site
scripts/
  evaluate_abtt.py   measures denoising against a benchmark of quotations
docs/           README screenshots
index.html      redirect to viewer/ — the GitHub Pages entry point
.nojekyll       disables Jekyll on Pages, which has no business here
serve.py        local server, theme search, security headers
LICENSE         CC BY-NC 4.0; the Biblical texts keep their own licences
```

Every source file carries the header `© 2026 Rymentz — CC BY-NC 4.0` and points
to `LICENSE`.

---

## Data schema

**`data/processed/verses.parquet`** — one row per verse:

| Column | Contents |
|---|---|
| `ref` · `label` | canonical identifier `book.chapter.verse` and readable reference |
| `book_id` · `book` · `osis` | 1–66, French name, OSIS abbreviation |
| `testament` · `genre` · `lang` | Old/New, literary family, Hebrew/Greek |
| `chapter` · `verse` · `canon_pos` | position in the book and in the whole canon |
| `text_fr` | Louis Segond 1910 — **the basis of the semantic computation** |
| `text_en` | World English Bible — display only |
| `text_orig` | pointed Hebrew or Greek, empty when unaligned |
| `text_consonants` | Hebrew reduced to the 22 consonants, no spaces (for ELS) |
| `has_orig` · `has_en` · `n_words_fr` | alignment flags and length |

**`data/processed/points.parquet`** adds `x` · `y` · `z`, `cluster`,
`cluster_label`, `neighbours`, `neighbour_sim` and `nn_cross_testament`.

Neighbourhood is computed on the vectors **before** reduction, and therefore
without the distortion introduced by dropping to three dimensions. Two points far
apart on screen can be very close relatives; the lines drawn from the selected
verse show it.

---

## What is verified

- **Book table**: self-checked on import (66 books, 39+27, contiguous
  identifiers, unique French and English names, complete translation tables).
- **Parsing**: checked against Genesis 1:1, the Shema, Psalm 23:1 and John 1:1;
  the consonant total lands on the expected Masoretic count.
- **Neighbourhood**: tested on synthetic data with known groups — correct
  neighbours, descending order, no self-neighbour, result independent of block
  slicing.
- **Denoising**: measured against a benchmark of fifteen quotations, in both
  directions of use (neighbourhood and layout).
- **Thematic axes**: each axis is checked by reading its extreme verses; two axes
  were re-anchored after that check.
- **Palette**: validated by measurement (lightness band, chroma floor, CVD
  separation, contrast against the real background), not by eye.

---

## Known limitations

- **The map depends on the translation.** It is a map of meaning *as rendered by
  Segond*, not a truth independent of the translator.
- **UMAP distorts.** On-screen distances are not proportional to semantic
  distances; only the neighbourhood structure is reliable.
- **Cluster labels stay in French**, whatever the interface language: they are
  extracted from the French corpus used for the computation.
- **Clusters are not a truth.** Changing `--min-cluster-size` changes their
  number. They are exploration cues, not a classification.
- **Clusters are lexical as much as thematic.** Sentence embeddings capture the
  surface subject — proper nouns, places, narrative style — hence labels such as
  "travailla · enfanta". Denoising does not fix this (measured, see above).
- **139 verses without original text**, 120 without English text.
- **Axes are worth exactly what their anchors are worth.** They are set by hand
  in `axes.py` and are in no way universal; changing them changes the map.
- **Theme search requires `serve.py`** and the local model. On static hosting the
  section is simply hidden.
- **Fine stray points appear on some machines**: isolated, very bright pixels in
  a colour absent from the palette, grouped where the cloud is dense. Not
  reproduced in software rendering, at any resolution or pixel density —
  therefore driver-dependent. Three plausible causes were ruled out by fixing
  them without any effect on the symptom: a `smoothstep` with reversed bounds
  (undefined behaviour per the GLSL specification), a size floor expressed in
  render pixels rather than CSS pixels, and a possible overflow at medium
  precision. All three fixes are kept — they are correct independently. The cause
  remains unknown; the display stays readable.

---

## Troubleshooting

**The page stays on "Loading…"** — the interface displays the real error. The
most frequent cause is a missing file in `viewer/vendor/`: `three.module.js`
re-exports from `three.core.js`, and both are required.

**Double-clicking `viewer/index.html` does not work** — that is expected.
Browsers refuse to load ES modules over `file://`. Use `serve.py`.

**`GET api/status 404` in the console under Live Server or GitHub Pages** — also
expected. The viewer probes the server to find out whether it can encode a query;
static hosting answers 404, the "theme search" section then stays hidden and
everything else works. The browser logs that 404 anyway: it is not an application
error. Note that a static server sends neither the security headers nor the
compressed version of `verses.json` — 21 MB transferred instead of 5.8.
`serve.py` does both.

**`contentscript.js` errors in the console** — these come from a browser
extension (crypto wallet, ad blocker…), not from the project: no file by that
name exists here. To confirm, open the page in a private window with extensions
disabled.

**The embedding step seems stuck** — it shows nothing for several minutes at
startup while the model downloads (~2 GB the first time).

**Mismatch between verses and vectors** — `project.py` refuses to run if the
sizes differ; re-run `embed` after any change to `corpus`.

---

## Licences and copyright

**© 2026 Rymentz — [CC BY-NC 4.0](LICENSE).** The Python pipeline, the viewer and
this documentation may be reused, modified and redistributed **provided that you
credit Rymentz with a link to the source, state the changes you made, and make no
commercial use of it**. Commercial use requires written permission.

"Non-commercial" is defined by the licence as use *"primarily intended for or
directed towards commercial advantage or monetary compensation"* (section 1(i)).
A personal site, a course, a research project, a parish: yes. A product for sale,
a paid service, an ad-monetised platform: no, not without prior agreement.

### What this licence does not cover

The Biblical texts and the libraries keep **their own licences**, all more
permissive than the project's. It cannot restrict them:

| Source | Contents | Licence |
|---|---|---|
| [OSHB / morphhb](https://github.com/openscriptures/morphhb) | Hebrew text, WLC | public domain |
| [OSHB / morphhb](https://github.com/openscriptures/morphhb) | Lemmas and morphology | CC BY 4.0 |
| [SBLGNT](https://sblgnt.com/license/) | Greek New Testament text | CC BY 4.0 |
| [MorphGNT](https://github.com/morphgnt/sblgnt) | Morphological annotations — *not used here* | CC BY-SA 3.0 |
| [getbible v2](https://getbible.net) | Segond 1910, World English Bible | public domain |
| [openbible.info](https://www.openbible.info/labs/cross-references/) | 344,799 cross-references | CC BY 4.0 |
| [three.js](https://threejs.org) | 3D rendering (vendored in `viewer/vendor/`) | MIT |

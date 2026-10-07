# Naming styles and templates

[< Docs index](README.md)

Everything the Renamer lets you control about a name. The same list is available inside the app from **Names > Format guide**.
See [The tools](tools.md) for how the Renamer's cards and list work.

## How a template works

A template is text with `{tokens}`. Anything outside braces is copied as it is.

| Syntax | Meaning | Example |
|---|---|---|
| `{token}` | The value of a token | `{series}` gives `Batman` |
| `[ ... ]` | An optional group: it disappears when any token inside it is empty | `{series}[ #{issue}][ ({year})]` gives `Batman #007 (2016)`, or `Batman (2016)`, or `Batman` |
| `{a\|b}` | Fallback: the first token that has a value | `{issue\|volume}` gives the issue, or the volume when there is no issue |
| `{token:spec}` | Format one token (below) | `{issue:3}` gives `007` |
| `\[ \] \{ \}` | A literal bracket or brace | `{series} \[{year}\]` gives `Batman [2016]` |

The editor checks the template as you type: unbalanced `[ ]` or `{ }`, unknown tokens, unknown formats and templates with no tokens
are reported under it, and a live example shows the result for the selected file (or a sample).

## Tokens

| Token | Value |
|---|---|
| `{series}` | Series name |
| `{title}` | Story or book title |
| `{issue}` | Issue number, padded by **Issue number** (Text tab) |
| `{volume}` | Volume number; collected editions are padded by **Volume number** |
| `{year}` | Year (the first year of a span) |
| `{years}` | The year, or a span such as `1996-1997` |
| `{year_end}` | Last year of a span (empty for a single year) |
| `{count}` | The issue count: the 12 in `(of 12)` |
| `{range}` | The issues a collection covers, e.g. `1-12` |
| `{format}` | Collected-edition word: TPB, Hardcover, Omnibus, Compendium, Deluxe Edition, Library Edition, Epic Collection, Graphic Novel, Box Set, Collection |
| `{type}` | The type shown on the card: Issue, Annual, TPB… |
| `{publisher}` | Publisher from `ComicInfo.xml` (empty without it) |
| `{tags}` | Other bracketed text in the name, e.g. `Digital, Zone-Empire` |
| `{original}` | The original file name without its extension |

## Formatting one token: `{token:spec}`

| Spec | Effect | Example |
|---|---|---|
| a number | Zero-pad a number to that width (decimals kept) | `{issue:3}` → `007`, `12.5` → `012.5`; `{volume:2}` |
| `upper` / `lower` | UPPERCASE / lowercase | `{series:upper}` → `BATMAN BEYOND` |
| `title` / `sentence` | Title Case / Sentence case | `{series:title}`, `{title:sentence}` |
| `nospace` | Remove spaces | `BatmanBeyond` |
| `snake` / `dash` | Spaces to `_` / `-` | `Batman_Beyond`, `Batman-Beyond` |

## A format for each type

Each type has its own template. Pick a type in **Names**, then edit its template or start from a preset.

| Group | Types |
|---|---|
| Single issues | Issue, Annual, Special, One-Shot |
| Collected editions | Volume, TPB, Hardcover, Omnibus, Compendium, Deluxe Edition, Library Edition, Epic Collection, Graphic Novel, Box Set, Collection |

A file's type comes from its name (a format word, an issue range, a lone volume number) and can be changed on its card or in the list's
Type column. A file with no number and no format (type *Other*) uses the Issue template. **Copy this template to** copies the current
template to every single-issue type, every collected type, or every type.

Presets for single issues: `Series 001 (2016)` (the default), `Series #001 (2016)`, `Series v2 001 (2016)`, `Series Vol 2 #001 (2016)`,
`Series - 001 - Title (2016)`, `Series 001 - Title`, `Series (2016) 001`, `Series 001`.

Presets for collected editions: `Series - Title Format Vol 01 (Years)` (the default), `Series Format Vol 01 (Years)`,
`Series Vol 01 - Title (Years)`, `Series Format 01`.

| Collected preset | Example |
|---|---|
| `Series - Title Format Vol 01 (Years)` | `Batman - The Long Halloween TPB (1996)`, `Y The Last Man - Cycles TPB Vol 02 (2003)` |
| `Series Format Vol 01 (Years)` | `The Walking Dead Compendium Vol 01 (2009)` |
| `Series Vol 01 - Title (Years)` | `Saga Vol 03 - Title (2013)` |
| `Series Format 01` | `Sandman Omnibus 01` |

## Text options (Text tab, apply to every file)

| Option | Choices |
|---|---|
| Issue number | Keep as is, or pad to 2, 3 or 4 digits (the `{issue}` token) |
| Volume number | Keep as is, or pad to 2 or 3 digits (collected editions only) |
| Series / Title capitalisation | Keep as is, Title Case, UPPERCASE, lowercase, Sentence case |
| Leading “The” | Keep it, move it to the end (`Walking Dead, The`), or remove it |
| Word separator | Spaces, underscores, dots or dashes |
| Illegal characters | Colon to ` - ` and the rest to `_`; remove them; replace with `_`; replace with `-` |
| Extension | lowercase (`.cbz`), keep as is, UPPERCASE |
| Maximum length | Cuts a longer name (0 or empty = no limit); the end is cut, so put the important tokens first |
| Reading-order number | Keep a `01 - ` prefix written by the Reading Order tool (otherwise it is dropped) |

## Folders (Folders tab)

With **Move into folders** on, each file goes into a folder built from a **folder template**. It uses the same tokens, and `/` makes nested
folders. Presets: `Series`, `Series + volume`, `Series (Year)`, `Publisher / Series`, `Publisher / Series (Year)`. A collected edition's
`{volume}` is empty in the folder name, so a TPB never makes a `Saga v1` folder. **Collected editions** can go into a subfolder with a name you
choose (default `Collected Editions`). Folders that differ only by case or a leading *The* (`The Walking Dead` and `Walking Dead`) are
merged into the first spelling seen.

**When a name is taken:** *Flag it and skip the file* (the card or row shows *Exists* or *Duplicate* and nothing is overwritten), or
*Add a number* (`Name (2)`, status *Numbered*).

## How a name is read (Detect tab)

- **Years** are found inside any brackets: `(2016)`, `(Oct 2016)`, `(2016, DC)`, `(DC 2016)`, `(2016 Digital)`, `(2016-10-05)`, `(05-10-2016)`,
  `[2016]`, `(2016-2017)`, `(2016-)`, even with invisible characters. Outside brackets, a bare year next to an issue number counts
  (`Batman 001 2016`, `Batman 2016 001`, `Batman.001.2016`). Only years from 1900 to next year are accepted, so `Spider-Man 2099` is untouched.
- **A volume that is really a year** (`v2016`, `Vol 2016`, or `ComicInfo.xml` Volume 2016, which is common) is read as the year, never as a volume.
- **Collected editions** are recognised from a format word (TPB, trade paperback, hardcover/HC, omnibus, compendium, deluxe edition, library
  edition, epic collection, graphic novel/OGN/GN, box set, collection) or an issue range (`#1-12`, `001-012`, `Issues 1-6`). Their number
  is a **volume** (`Compendium 2`, `Vol 3`, `Book One`, `Vol. III`). Turn **Detect collected editions** off to treat everything as an issue.
- **A name with only “Vol 3”** could be a manga volume or a TPB. By default it is read as issue 3; set **A name with only “Vol 3” is** to
  *A volume* to treat it as a volume.
- `Series - Title TPB` splits at the dash into series and title. A colon is not split (`Batman: Year One` is one series).
- `Walking Dead, The` becomes `The Walking Dead`. Unbracketed `Digital`, `WebRip`, `c2c` and `Hybrid` at the end are dropped.
- Names that say nothing (`scan0001`, `IMG_0042`, `Untitled`, `Comics 12`) have no series and are marked *No series*.
- `ComicInfo.xml` overrides the filename for any field it has a value for (switch it off in Detect).

Annuals, specials and one-shots keep the word in the series name (`Batman Annual 003 (2016)`), so they stay apart from the main series;
their type is shown as Annual, Special or One-Shot and they have their own template.

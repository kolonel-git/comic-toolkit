"""Naming for the Renamer: templates per comic type, tokens, token formatters and every text option. No UI code.

A template is plain text with {tokens}. `[ ... ]` marks an optional group that disappears when any token inside it is
empty. `{a|b}` uses the first of several tokens that has a value. `{token:spec}` formats one token. The full list is
in FORMAT_GUIDE, which the Renamer shows from its Format guide button.
"""
import re

from comic_core import sanitize
from rename_core import COLLECTED_TYPES, SINGLE_TYPES, TYPE_KEYS

# ---------- templates ----------
ISSUE_PRESETS = {
    "Series 001 (2016)": "{series}[ {issue}][ ({year})]",
    "Series #001 (2016)": "{series}[ #{issue}][ ({year})]",
    "Series v2 001 (2016)": "{series}[ v{volume}][ {issue}][ ({year})]",
    "Series Vol 2 #001 (2016)": "{series}[ Vol {volume}][ #{issue}][ ({year})]",
    "Series - 001 - Title (2016)": "{series}[ - {issue}][ - {title}][ ({year})]",
    "Series 001 - Title": "{series}[ {issue}][ - {title}]",
    "Series (2016) 001": "{series}[ ({year})][ {issue}]",
    "Series 001": "{series}[ {issue}]",
}
COLLECTED_PRESETS = {
    "Series - Title Format Vol 01 (Years)": "{series}[ - {title}][ {format}][ Vol {volume}][ #{range}][ ({years})]",
    "Series Format Vol 01 (Years)": "{series}[ {format}][ Vol {volume}][ #{range}][ ({years})]",
    "Series Vol 01 - Title (Years)": "{series}[ Vol {volume}][ #{range}][ - {title}][ ({years})]",
    "Series Format 01": "{series}[ {format}][ {volume}][ #{range}]",
}
PRESETS = {**ISSUE_PRESETS, **COLLECTED_PRESETS}
DEFAULT_ISSUE = ISSUE_PRESETS["Series 001 (2016)"]
DEFAULT_COLLECTED = COLLECTED_PRESETS["Series - Title Format Vol 01 (Years)"]
DEFAULT_TEMPLATES = {t: DEFAULT_ISSUE for t in SINGLE_TYPES} | {t: DEFAULT_COLLECTED for t in COLLECTED_TYPES}


def slug(type_key):
    return re.sub(r"\W+", "_", type_key.lower()).strip("_")


# ---------- text options ----------
PADS = {"Keep as is": 0, "2 digits (01)": 2, "3 digits (001)": 3, "4 digits (0001)": 4}
VOLUME_PADS = {"Keep as is": 0, "2 digits (01)": 2, "3 digits (001)": 3}
CASE_MODES = ["Keep as is", "Title Case", "UPPERCASE", "lowercase", "Sentence case"]
ARTICLE_MODES = ["Keep it where it is", "Move to the end (Walking Dead, The)", "Remove it (Walking Dead)"]
SEPARATORS = {"Spaces": " ", "Underscores": "_", "Dots": ".", "Dashes": "-"}
ILLEGAL_MODES = ["Colon to “ - ”, others to “_”", "Remove them", "Replace with “_”", "Replace with “-”"]
EXT_CASES = ["lowercase (.cbz)", "Keep as is", "UPPERCASE (.CBZ)"]
CONFLICT_MODES = ["Flag it and skip the file", "Add a number: Name (2)"]
FOLDER_PRESETS = {
    "Series": "{series}",
    "Series + volume": "{series}[ v{volume}]",
    "Series (Year)": "{series}[ ({year})]",
    "Publisher / Series": "{publisher}/{series}",
    "Publisher / Series (Year)": "{publisher}/{series}[ ({year})]",
}
DEFAULT_OPTIONS = {"pad": "3 digits (001)", "vpad": "2 digits (01)", "series_case": CASE_MODES[0],
                   "title_case": CASE_MODES[0], "article": ARTICLE_MODES[0], "separator": "Spaces",
                   "illegal": ILLEGAL_MODES[0], "ext_case": EXT_CASES[0], "max_len": 0}

# ---------- tokens ----------
TOKENS = {  # token -> meaning (shown in the guide)
    "series": "Series name",
    "title": "Story or book title",
    "issue": "Issue number (padded by Issue number)",
    "volume": "Volume number (padded by Volume number for collected editions)",
    "year": "Year (first year when there is a span)",
    "years": "Year, or the span 1996-1997",
    "year_end": "Last year of a span (empty for a single year)",
    "count": "Issue count: the 12 in (of 12)",
    "range": "Issue range a collection covers: 1-12",
    "format": "Collected-edition word: TPB, Omnibus, Compendium...",
    "type": "The type shown in the Type column: Issue, Annual, TPB...",
    "publisher": "Publisher from ComicInfo.xml (needs ComicInfo on)",
    "tags": "Other bracketed text from the name, e.g. Digital, Zone-Empire",
    "original": "The original file name without its extension",
}
_TOKEN = re.compile(r"\{([a-z_]+(?:\|[a-z_]+)*)(?::([A-Za-z0-9]+))?\}")
_ANY_BRACES = re.compile(r"\{[^{}]*\}")
SPECS = ("upper", "lower", "title", "sentence", "nospace", "snake", "dash")  # plus a number for zero padding


# ---------- text helpers ----------
def title_case(s):
    return re.sub(r"[A-Za-z]+(?:'[A-Za-z]+)?", lambda m: m.group(0).capitalize(), s)


def sentence_case(s):
    s = s.lower()
    return s[:1].upper() + s[1:]


def apply_case(s, mode):
    if not s:
        return s
    return {"Title Case": title_case, "UPPERCASE": str.upper, "lowercase": str.lower,
            "Sentence case": sentence_case}.get(mode, lambda x: x)(s)


def apply_article(series, mode):
    m = re.match(r"^(the|a|an)\s+(.+)$", series or "", re.I)
    if not m:
        return series
    if mode == ARTICLE_MODES[1]:
        return f"{m.group(2)}, {m.group(1).capitalize()}"
    if mode == ARTICLE_MODES[2]:
        return m.group(2)
    return series


def format_number(text, width):
    """Zero-pad the whole-number part ('7' -> '007', '12.5' -> '012.5'); other text is left alone."""
    m = re.fullmatch(r"(\d+)(\.\d+)?", text or "")
    if not m or not width:
        return text or ""
    return str(int(m.group(1))).zfill(width) + (m.group(2) or "")


def _spec(text, spec):
    if not spec or not text:
        return text
    if spec.isdigit():
        return format_number(text, int(spec))
    return {"upper": text.upper(), "lower": text.lower(), "title": title_case(text), "sentence": sentence_case(text),
            "nospace": text.replace(" ", ""), "snake": text.replace(" ", "_"), "dash": text.replace(" ", "-")}.get(spec, text)


def _tokens_in(text):
    return [(m.group(1).split("|"), m.group(2)) for m in _TOKEN.finditer(text)]


def _pick(names, fields):
    return next((fields[n] for n in names if fields.get(n)), "")


# A backslash before [ ] { } makes it a literal character. Each is swapped for a private-use character while the
# template is parsed, then swapped back.
_ESCAPES = {"\\" + ch: chr(0xE000 + i) for i, ch in enumerate("[]{}")}


def _escape(text):
    for k, v in _ESCAPES.items():
        text = text.replace(k, v)
    return text


def _unescape(text):
    for k, v in _ESCAPES.items():
        text = text.replace(v, k[1])
    return text


def render(template, fields):
    """Fill a template. Optional [ ] groups vanish when any token inside has no value."""
    template = _escape(template)

    def sub(m):
        return _spec(_pick(m.group(1).split("|"), fields), m.group(2))

    def group(m):
        inner = m.group(1)
        if all(_pick(names, fields) for names, _ in _tokens_in(inner)):
            return _TOKEN.sub(sub, inner)
        return ""

    s = re.sub(r"\[([^\[\]]*)\]", group, template)
    s = _TOKEN.sub(sub, s)
    return re.sub(r"\s+", " ", _unescape(s)).strip(" -–")


def check_template(template):
    """Problems in a template, as short messages (empty list when it is fine)."""
    problems = []
    template = _escape(template)
    if template.count("[") != template.count("]"):
        problems.append("Unbalanced [ ] brackets")
    if template.count("{") != template.count("}"):
        problems.append("Unbalanced { } braces")
    for raw in _ANY_BRACES.findall(template):
        m = _TOKEN.fullmatch(raw)
        if not m:
            problems.append(f"{raw} is not a valid token")
            continue
        for n in m.group(1).split("|"):
            if n not in TOKENS:
                problems.append(f"Unknown token {{{n}}}")
        if m.group(2) and not (m.group(2).isdigit() or m.group(2) in SPECS):
            problems.append(f"Unknown format “{m.group(2)}” in {raw}")
    if not template.strip():
        problems.append("The template is empty")
    elif not _tokens_in(template):
        problems.append("No tokens: every file would get the same name")
    return problems


def safe_name(stem, mode=ILLEGAL_MODES[0]):
    """Make `stem` safe for Windows file names according to the illegal-characters option."""
    repl = {ILLEGAL_MODES[0]: "_", ILLEGAL_MODES[1]: "", ILLEGAL_MODES[2]: "_", ILLEGAL_MODES[3]: "-"}.get(mode, "_")
    if mode == ILLEGAL_MODES[0]:
        stem = re.sub(r"\s*:\s*", " - ", stem)
    stem = re.sub(r'[<>:"/\\|?*\x00-\x1f]', repl, stem)
    return re.sub(r"\s+", " ", stem).strip(" .") or "Untitled"


def prepare(fields, o):
    """Fields as the template sees them: text transforms, padding and the computed tokens."""
    f = dict(fields)
    if f.get("series"):
        f["series"] = apply_case(apply_article(f["series"], o["article"]), o["series_case"])
    if f.get("title"):
        f["title"] = apply_case(f["title"], o["title_case"])
    f["issue"] = format_number(f.get("issue"), PADS[o["pad"]])
    if f.get("collected") and f.get("volume") and VOLUME_PADS[o["vpad"]]:
        f["volume"] = format_number(f["volume"], VOLUME_PADS[o["vpad"]])
    f["type"] = f.get("kind") if f.get("kind") != "Other" else ""
    return {k: ("" if v is None else str(v)) for k, v in f.items() if not isinstance(v, (list, bool))} | \
           {"collected": bool(f.get("collected"))}


def build_name(fields, template, o):
    """File name (no extension) for `fields` from `template` and the text options `o`."""
    stem = safe_name(render(template, prepare(fields, o)), o["illegal"])
    sep = SEPARATORS.get(o["separator"], " ")
    if sep != " ":
        stem = stem.replace(" ", sep)
    n = int(o.get("max_len") or 0)
    if n and len(stem) > n:
        stem = stem[:n].rstrip(" -–._([") or stem[:n]
    return stem


def build_folder(fields, template, o):
    """Folder parts (a list of names) from a folder template; '/' in the template makes nested folders.
    A collected edition's volume is not a run, so {volume} is empty for it."""
    f = prepare(fields, o)
    if f.get("collected"):
        f["volume"] = ""
    text = render(template, f)
    return [sanitize(p.strip()) for p in re.split(r"[\\/]", text) if p.strip(" -–")]


def ext_text(suffix, mode):
    return suffix.upper() if mode == EXT_CASES[2] else suffix if mode == EXT_CASES[1] else suffix.lower()


def template_for(fields, templates):
    """The template for a file's type (Issue's when the type has none, e.g. 'Other')."""
    kind = fields.get("kind")
    return templates.get(kind if kind in TYPE_KEYS else "Issue") or templates["Issue"]


SAMPLE = {"series": "Batman", "title": "The Court of Owls", "issue": "7", "volume": "2", "year": "2016", "years": "2016",
          "year_end": None, "count": "12", "range": "1-6", "format": None, "kind": "Issue", "publisher": "DC Comics",
          "tags": "Digital", "original": "batman_v2_007_(2016)", "collected": False}


def sample_for(type_key):
    """Example fields for a type, used for the live example under a template."""
    f = dict(SAMPLE)
    if type_key in COLLECTED_TYPES:
        f.update(collected=True, kind=type_key, issue=None, format=None if type_key == "Volume" else type_key,
                 years="2016-2017", year_end="2017")
    else:
        f["kind"] = type_key
        if type_key == "Annual":
            f["series"] = "Batman Annual"
    return f


FORMAT_GUIDE = r"""NAMING GUIDE: every option the Renamer offers

HOW A TEMPLATE WORKS
  Type text and {tokens}. Anything outside braces is copied as it is.
  [ ... ]   An optional group. It disappears when any token inside it has no value.
            {series}[ #{issue}][ ({year})]   ->  Batman #007 (2016)   or   Batman (2016)   or   Batman
  {a|b}     Fallback: uses the first token that has a value.   {issue|volume}   ->  the issue, or the volume if there is none
  {x:spec}  Formats one token (see FORMATTING A TOKEN).
  \[ \] \{ \}   Literal brackets and braces:   {series} \[{year}\]   ->   Batman [2016]

TOKENS
""" + "\n".join(f"  {{{k}}}".ljust(14) + v for k, v in TOKENS.items()) + r"""

FORMATTING A TOKEN   {token:spec}
  {issue:3}      zero-pad a number to 3 digits (007; 12.5 becomes 012.5). Any width works: {volume:2}
  {series:upper} UPPERCASE        {series:lower} lowercase        {series:title} Title Case
  {title:sentence} Sentence case  {series:nospace} BatmanBeyond   {series:snake} Batman_Beyond   {series:dash} Batman-Beyond

A FORMAT PER TYPE
  Each type has its own template: Issue, Annual, Special, One-Shot, and the collected editions Volume, TPB, Hardcover,
  Omnibus, Compendium, Deluxe Edition, Library Edition, Epic Collection, Graphic Novel, Box Set, Collection.
  Pick a type in Names, edit its template, or start from a preset. Copy to group copies it to the types in the same group.
  Override a single file's type from its card or the Type column.

TEXT OPTIONS (apply to every file)
  Issue number         Keep, or pad to 2, 3 or 4 digits (the {issue} token).
  Volume number        Keep, or pad to 2 or 3 digits (collected editions only).
  Series capitalisation / Title capitalisation
                       Keep as is, Title Case, UPPERCASE, lowercase, Sentence case.
  Leading "The"        Keep it, move it to the end (Walking Dead, The), or remove it.
  Word separator       Spaces, underscores, dots or dashes between words in the whole name.
  Illegal characters   What to do with : < > " / \ | ? *: colon to " - " and the rest to "_", remove them, or replace with _ or -.
  Extension            lowercase (.cbz), keep as is, or UPPERCASE.
  Maximum length       Shortens long names (0 = no limit); the end is cut, so keep the important tokens first.
  Reading-order number Keep a 01 - prefix written by the Reading Order tool.

READING THE NAME (Detect)
  Include subfolders, include PDF and EPUB, use ComicInfo.xml (it overrides the filename where it has a value),
  detect collected editions (off: everything is treated as an issue), and how a name with only "Vol 3" is read.
  Years are found inside any brackets: (2016) (Oct 2016) (2016, DC) (DC 2016) (2016-10-05) (2016-2017) [2016].
  A volume that is really a year (v2016, Vol 2016, or ComicInfo Volume 2016) is read as the year.

FOLDERS
  Move into folders, with a folder template (same tokens; "/" makes nested folders, e.g. {publisher}/{series}).
  Collected editions can go in their own subfolder (name it, or leave it empty for none).
  If a name is taken: flag the file and skip it, or add a number: Name (2).

EXAMPLES
  {series}[ #{issue:3}][ ({year})]                              Batman #007 (2016)
  {series}[ v{volume}][ {issue}] - {title}                      Batman v2 007 - The Court of Owls
  [{publisher} - ]{series:title}[ {issue:4}]                    DC Comics - Batman 0007
  {series}[ - {title}][ {format}][ Vol {volume:2}][ ({years})]  Batman - The Long Halloween TPB (1996-1997)
"""

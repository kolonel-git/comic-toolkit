"""Filename parsing and ComicInfo.xml reading for the Renamer. No UI code.

`parse_filename` turns 'Saga Vol 1 TPB (Oct 2012) (Digital)' into series, volume, issue, year(s), title, count,
format, range, tags and a few flags. Naming (templates, text options) is in `name_format.py`.
"""
import datetime
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from comic_core import find_extractor, in_archive, natural_key

RENAME_EXT = {".cbz", ".cbr"}
OTHER_EXT = {".pdf", ".epub"}

# Every type a file can be shown as, and picked as an override. The collected ones have a volume, not an issue.
SINGLE_TYPES = ["Issue", "Annual", "Special", "One-Shot"]
COLLECTED_TYPES = ["Volume", "TPB", "Hardcover", "Omnibus", "Compendium", "Deluxe Edition", "Library Edition",
                   "Epic Collection", "Graphic Novel", "Box Set", "Collection"]
TYPE_KEYS = [*SINGLE_TYPES, *COLLECTED_TYPES]
AUTO_TYPE = "Auto (detected)"
TYPES = [AUTO_TYPE, *TYPE_KEYS]
EDIT_FIELDS = ("series", "title", "issue", "volume", "year", "year_end", "range", "count")
MAX_YEAR = datetime.date.today().year + 1

_YEAR_TOKEN = re.compile(r"(?<!\d)((?:19|20)\d{2})(?!\d)")
_YEAR_SPAN = re.compile(r"(?<!\d)((?:19|20)\d{2})\s*[-–]\s*((?:19|20)\d{2})(?!\d)")
_BRACKET = re.compile(r"\(([^()]*)\)|\[([^\[\]]*)\]")
_INVISIBLE = re.compile(r"[​-‏‪-‮⁠﻿]")
# A reading-order prefix as written by the Reading Order tool: '03 - Name' or '[03] Name'.
_ORDER = re.compile(r"^(?:\[(\d{2,4})\]\s+|(\d{2,4})\s+-\s+)(?=.*[A-Za-z])")
_COUNT = re.compile(r"[(\[]\s*(?:\d+\s*)?of\s*(\d+)\s*[)\]]", re.I)  # '(of 12)', '(3 of 12)'
_TAGS = re.compile(r"\([^)]*\)|\[[^\]]*\]")
_NUM_WORDS = {w: n for n, w in enumerate("one two three four five six seven eight nine ten eleven twelve thirteen "
                                         "fourteen fifteen sixteen seventeen eighteen nineteen twenty".split(), 1)}
_NUM_WORDS.update({r: n for n, r in enumerate("i ii iii iv v vi vii viii ix x xi xii xiii xiv xv xvi xvii xviii xix xx".split(), 1)})
_VOL = re.compile(r"(?<![A-Za-z])(?:vol(?:ume)?\.?|book|bk\.?|v)\s*(\d{1,4})(?![A-Za-z\d])", re.I)
_VOL_WORD = re.compile(r"(?<![A-Za-z])(?:vol(?:ume)?\.?|book)\s*(%s)(?![A-Za-z\d])"
                       % "|".join(sorted(_NUM_WORDS, key=len, reverse=True)), re.I)
_TITLE = re.compile(r"^(.*?\d)\s+[-–:]\s+(.+)$")
_ISSUE = re.compile(r"(?:(?:#|\b(?:issue|no|ch(?:apter)?)\.?)\s*)?(\d+(?:\.\d+)?)\s*$", re.I)
_RANGE = re.compile(r"(?:(?<![A-Za-z])issues?\s*)?#?\s*(\d{1,4})\s*[-–]\s*#?(\d{1,4})$", re.I)  # '1-6', '#1-12', 'Issues 1-6'
_TRAILING_YEAR = re.compile(r"\s(\d{1,4})\s+((?:19|20)\d{2})$")  # '001 2016': a number, then a bare year
_LEADING_YEAR = re.compile(r"\s((?:19|20)\d{2})\s+(\d{1,4}(?:\.\d+)?)$")  # '2016 001': a bare year, then a number
_JUNK_END = re.compile(r"(?:\s+(?:digital|webrip|c2c|hybrid))+$", re.I)
# Names that say nothing about the comic ('scan0001', 'IMG_0042', 'Untitled'): no series, so the user is asked.
_GENERIC = re.compile(r"^(?:scans?|img|imgs|images?|pages?|untitled|documents?|docs?|files?|comics?|unknown|new|temp|"
                      r"downloads?|output|export|covers?)(?:[\W_]|\d)*$", re.I)
_INVERTED_THE = re.compile(r"^(.+?),\s*(the|a|an)$", re.I)  # 'Walking Dead, The'
# Collected-edition words, most specific first. The first one found is the format; every one is removed from the series.
_FORMATS = [(name, re.compile(r"(?<![A-Za-z])(?:%s)(?![A-Za-z])" % pat, re.I)) for name, pat in (
    ("Epic Collection", r"epic\s+collection"),
    ("Library Edition", r"library\s+edition"),
    ("Deluxe Edition", r"deluxe(?:\s+edition)?"),
    ("TPB", r"tpb|trade\s+paperback|trade\s+pb"),
    ("Hardcover", r"hc|hard\s?cover|hardback"),
    ("Omnibus", r"omnibus"),
    ("Compendium", r"compendium"),
    ("Graphic Novel", r"graphic\s+novel|ogn|gn"),
    ("Box Set", r"box\s?set"),
    ("Collection", r"collected\s+edition|collection|collected"),
)]
_EXTRA_KINDS = [("Annual", re.compile(r"\bannuals?\b", re.I)), ("Special", re.compile(r"\bspecial\b", re.I)),
                ("One-Shot", re.compile(r"\bone[- ]?shot\b", re.I))]


def _clean(s):
    return re.sub(r"\s+", " ", s.replace("_", " ")).strip(" -–.#:,")


def split_order_prefix(stem):
    """'03 - Batman 05' -> ('03 - ', 'Batman 05'); ('', stem) when there is no reading-order prefix."""
    m = _ORDER.match(stem)
    return (m.group(0), stem[m.end():]) if m else ("", stem)


def valid_year(y):
    try:
        return 1900 <= int(y) <= MAX_YEAR
    except (TypeError, ValueError):
        return False


def _bracket_year(stem):
    """First year inside any (...) or [...] group, whatever else the group says: '(Oct 2016)', '(2016, DC)',
    '(DC 2016)', '(2016 Digital)', '(05-10-2016)', '(1/2016)', '(2016-)'. Returns (year, years, group text)."""
    for m in _BRACKET.finditer(stem):
        text = m.group(1) if m.group(1) is not None else m.group(2)
        if _COUNT.search(m.group(0)):
            continue
        sp = _YEAR_SPAN.search(text)
        if sp and valid_year(sp.group(1)) and valid_year(sp.group(2)) and int(sp.group(2)) > int(sp.group(1)):
            return sp.group(1), f"{sp.group(1)}-{sp.group(2)}", m.group(0)
        for y in _YEAR_TOKEN.findall(text):
            if valid_year(y):
                return y, y, m.group(0)
    return None, None, None


def _volume_number(s):
    """Find 'Vol 3', 'v3', 'Book 2', 'Volume Two', 'Vol. III' in `s`. Returns (number text, match) or (None, None)."""
    m = _VOL.search(s)
    if m:
        return str(int(m.group(1))), m
    m = _VOL_WORD.search(s)
    if m:
        return str(_NUM_WORDS[m.group(1).lower()]), m
    return None, None


def _split_number(s):
    """Trailing number off `s`: (rest, number or None)."""
    m = _ISSUE.search(s)
    return (s[:m.start()], m.group(1)) if m else (s, None)


def parse_filename(stem, volume_as_issue=True):
    """'Batman #012 - The Court (Oct 2016) (of 12)' -> a dict of series, volume, issue, year, years, year_end,
    title, count, format, range, tags, collected, kind, notes and original (None when absent).

    Collected editions are recognised: 'Saga TPB Vol 3 (2013)' gives format 'TPB', volume '3' and no issue, and
    'Batman #1-12 (Collected)' gives a range. `collected` is true for those. A volume that is really a year
    ('v2016', 'Vol 2016') is read as the year. With `volume_as_issue` (the default) a bare 'Vol 3' is issue 3, as for
    manga; with it off it is a volume and the file counts as collected."""
    original = stem
    notes = []
    stem = _INVISIBLE.sub("", stem).replace(" ", " ")
    order_prefix, stem = split_order_prefix(stem)
    if " " not in stem and stem.count(".") >= 2:  # Batman.001.2016.cbz -> spaces
        stem = stem.replace(".", " ")
    year, years, year_group = _bracket_year(stem)
    m = _COUNT.search(stem)
    count = str(int(m.group(1))) if m and int(m.group(1)) > 0 else None
    fmt = next((name for name, rx in _FORMATS if rx.search(stem)), None)
    tags = []  # bracketed text that is not a year, a count or a format
    for g in _BRACKET.finditer(stem):
        text = (g.group(1) if g.group(1) is not None else g.group(2)).strip()
        if text and g.group(0) != year_group and not _COUNT.search(g.group(0)) and \
                not any(rx.search(text) for _, rx in _FORMATS):
            tags.append(text)
    s = _JUNK_END.sub("", _clean(_TAGS.sub(" ", stem)))
    for _, rx in _FORMATS:
        s = rx.sub(" ", s)
    s = _clean(s)
    issue = title = rng = None
    if year is None:  # no bracketed year: '001 2016' or '2016 001'
        m = _TRAILING_YEAR.search(s)
        if m and valid_year(m.group(2)):
            year = years = m.group(2)
            s = _clean(s[:m.start()] + " " + m.group(1))
        else:
            m = _LEADING_YEAR.search(s)
            if m and valid_year(m.group(1)):
                year = years = m.group(1)
                s = _clean(s[:m.start()] + " " + m.group(2))
    volume, m = _volume_number(s)
    if m:
        s = _clean(s[:m.start()] + " " + s[m.end():])
        if volume and valid_year(volume):  # 'v2016' is the year the run began, not a volume
            notes.append(f"“{m.group(0).strip()}” looks like a year, so it was read as the year")
            if year is None:
                year = years = volume
            volume = None
    m = _RANGE.search(s)
    if m and int(m.group(2)) > int(m.group(1)) and int(m.group(1)) < 1900:
        rng, s = f"{int(m.group(1))}-{int(m.group(2))}", _clean(s[:m.start()])
        fmt = fmt or "Collection"
    if fmt:  # a collected edition: a trailing number is its volume, and 'Series - Title' splits at the dash
        s, num = _split_number(s)
        volume = volume or num
        parts = re.split(r"\s+[-–]\s+", s, maxsplit=1)
        if len(parts) == 2:
            s, title = parts[0], _clean(parts[1])
            s, num = _split_number(s)
            volume = volume or num
        else:
            m = _TITLE.match(s)
            if m:
                s, title = m.group(1), _clean(m.group(2))
    else:
        m = _TITLE.match(s)
        if m:
            s, title = m.group(1), _clean(m.group(2))
        elif volume:
            parts = re.split(r"\s+[-–]\s+", s, maxsplit=1)
            if len(parts) == 2 and not re.fullmatch(r"#?\d+(\.\d+)?", parts[1].strip()):
                s, title = parts[0], _clean(parts[1])
        m = _ISSUE.search(s)
        if m:
            issue, s = m.group(1), s[:m.start()]
        if issue is None and volume and volume_as_issue:  # manga-style 'Berserk Vol 3': the volume is the number
            issue, volume = volume, None
    series = _clean(s)
    m = _INVERTED_THE.match(series)
    if m:
        series = f"{m.group(2).capitalize()} {m.group(1)}"
    if _GENERIC.match(series):
        series = ""
    collected = bool(fmt) or (volume is not None and issue is None)
    extra = next((name for name, rx in _EXTRA_KINDS if rx.search(stem)), None)
    kind = fmt or extra or ("Volume" if collected else "Issue" if issue else "Other")
    return {"series": series or None, "volume": volume, "issue": issue, "year": year, "years": years,
            "year_end": years.split("-")[1] if years and "-" in years else None, "title": title, "count": count,
            "order_prefix": order_prefix, "format": fmt, "range": rng, "tags": ", ".join(tags) or None,
            "collected": collected, "kind": kind, "notes": notes, "original": original}


def _rar_member(path, member):
    exe = find_extractor()
    if not exe:
        return None
    tmp = Path(tempfile.mkdtemp(prefix="ci_"))
    try:
        name = Path(exe).stem.lower()
        if name.startswith("7z"):
            cmd = [exe, "e", "-y", f"-o{tmp}", str(path), member]
        elif name == "unrar":
            cmd = [exe, "e", "-y", str(path), member, str(tmp) + "\\"]
        else:
            cmd = [exe, "-xf", str(path), "-C", str(tmp), member]
        subprocess.run(cmd, capture_output=True, check=False, timeout=60)
        f = tmp / member
        return f.read_bytes() if f.exists() else None
    except (OSError, subprocess.SubprocessError):
        return None
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def read_comicinfo(path):
    """Fields from the archive's root ComicInfo.xml; {} when missing or unreadable. A Volume that is really a
    year (common in ComicInfo files: Volume 2016 for a run that began in 2016) is returned as the year instead."""
    path = Path(path)
    data = None
    try:
        if path.suffix.lower() in RENAME_EXT:
            if zipfile.is_zipfile(path):
                with zipfile.ZipFile(path) as z:
                    name = next((n for n in z.namelist() if n.lower() == "comicinfo.xml"), None)
                    data = z.read(name) if name else None
            elif path.suffix.lower() == ".cbr":
                data = _rar_member(path, "ComicInfo.xml")
        root = ET.fromstring(data.lstrip(b"\xef\xbb\xbf")) if data else None
    except (OSError, zipfile.BadZipFile, ET.ParseError):
        return {}
    if root is None:
        return {}

    def get(tag):
        el = root.find(tag)
        return (el.text or "").strip() if el is not None else ""

    def pos_int(tag):
        v = get(tag)
        return str(int(v)) if v.isdigit() and int(v) > 0 else None

    volume, year = pos_int("Volume"), pos_int("Year")
    if volume and valid_year(volume):
        volume, year = None, year or volume
    return {"series": get("Series") or None, "volume": volume,
            "issue": get("Number") or None, "year": year, "title": get("Title") or None,
            "count": pos_int("Count"), "publisher": get("Publisher") or None,
            "series_group": get("SeriesGroup") or None, "genre": get("Genre") or None,
            "alternate_series": get("AlternateSeries") or None, "alternate_number": get("AlternateNumber") or None,
            "alternate_count": pos_int("AlternateCount"), "story_arc": get("StoryArc") or None,
            "story_arc_number": get("StoryArcNumber") or None}


def apply_type(f, choice):
    """Force how one file is treated: any name in `TYPE_KEYS`. Anything else (including the auto choice) leaves the
    detected fields alone. Collected types move an issue number into the volume; single types do the reverse."""
    f = dict(f)
    if choice not in TYPE_KEYS:
        return f
    if choice in SINGLE_TYPES:
        f.update(format=None, collected=False, kind=choice, range=None)
        if not f.get("issue") and f.get("volume"):
            f["issue"], f["volume"] = f["volume"], None
        return f
    if f.get("issue") and not f.get("volume"):
        f["volume"], f["issue"] = f["issue"], None
    f.update(collected=True, format=None if choice == "Volume" else choice, kind=choice)
    return f


def apply_edits(f, edits):
    """Overlay values typed by hand (a dict of field -> text; an empty text clears the field)."""
    f = dict(f)
    if not edits:
        return f
    for k in EDIT_FIELDS:
        if k in edits:
            f[k] = (edits[k] or "").strip() or None
    if "year" in edits or "year_end" in edits:
        y, e = f.get("year"), f.get("year_end")
        f["years"] = f"{y}-{e}" if y and e else y
    return f


def merge(parsed, ci, use_ci):
    """Filename fields, overridden by ComicInfo.xml fields when allowed and present."""
    out = dict(parsed)
    if use_ci:
        out.update({k: v for k, v in ci.items() if v})
        if out.get("year") and "-" not in (out.get("years") or ""):
            out["years"] = out["year"]  # a ComicInfo year replaces a single filename year, but not a year range
        out["year_end"] = out["years"].split("-")[1] if out.get("years") and "-" in out["years"] else None
    return out


def find_files(folder, recursive, include_other):
    exts = RENAME_EXT | (OTHER_EXT if include_other else set())
    it = Path(folder).rglob("*") if recursive else Path(folder).iterdir()
    files = [p for p in it if p.is_file() and p.suffix.lower() in exts and not in_archive(p, folder)]
    return sorted(files, key=lambda p: natural_key(p.relative_to(folder)))


def do_rename(src, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if str(src).lower() == str(dest).lower():  # case-only change on a case-insensitive filesystem
        tmp = src.with_name(src.name + ".renametmp")
        src.rename(tmp)
        tmp.rename(dest)
    else:
        shutil.move(str(src), str(dest))

"""Filename parsing, ComicInfo.xml reading and name templating for the renamer. No UI code."""
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from comic_core import find_extractor, in_archive, natural_key, sanitize

RENAME_EXT = {".cbz", ".cbr"}
OTHER_EXT = {".pdf", ".epub"}

# Optional parts go in [ ]: the whole group is dropped when any token inside is empty.
CUSTOM = "Custom template…"
PRESETS = {
    "Series 001 (2016)": "{series}[ {issue}][ ({year})]",
    "Series #001 (2016)": "{series}[ #{issue}][ ({year})]",
    "Series v2 001 (2016)": "{series}[ v{volume}][ {issue}][ ({year})]",
    "Series Vol 2 #001 (2016)": "{series}[ Vol {volume}][ #{issue}][ ({year})]",
    "Series - 001 - Title (2016)": "{series}[ - {issue}][ - {title}][ ({year})]",
    "Series 001 - Title": "{series}[ {issue}][ - {title}]",
    "Series (2016) 001": "{series}[ ({year})][ {issue}]",
    "Series 001": "{series}[ {issue}]",
}
STYLES = [*PRESETS, CUSTOM]
DEFAULT_CUSTOM = "{series}[ #{issue}][ ({year})]"
PADS = {"Keep as is": 0, "2 digits (01)": 2, "3 digits (001)": 3, "4 digits (0001)": 4}
CASES = ["Keep as is", "Title Case"]
FOLDER_STYLES = ["Series", "Series + volume"]

_YEAR = re.compile(r"[(\[]\s*((?:19|20)\d{2})(?:[-./]\d{1,2})*\s*[)\]]")
# A reading-order prefix as written by the Reading Order tool: '03 - Name' or '[03] Name'.
_ORDER = re.compile(r"^(?:\[(\d{2,4})\]\s+|(\d{2,4})\s+-\s+)(?=.*[A-Za-z])")
_COUNT = re.compile(r"[(\[]\s*(?:\d+\s*)?of\s*(\d+)\s*[)\]]", re.I)  # '(of 12)', '(3 of 12)'
_TAGS = re.compile(r"\([^)]*\)|\[[^\]]*\]")
_VOL = re.compile(r"(?<![A-Za-z])(?:vol(?:ume)?\.?|v)\s*(\d{1,3})(?![A-Za-z\d])", re.I)
_TITLE = re.compile(r"^(.*?\d)\s+[-–:]\s+(.+)$")
_ISSUE = re.compile(r"(?:(?:#|\b(?:issue|no|ch(?:apter)?)\.?)\s*)?(\d+(?:\.\d+)?)\s*$", re.I)
_TOKEN = re.compile(r"\{(series|volume|issue|year|title)\}")
FIELDS = ("series", "volume", "issue", "year", "title")


def _clean(s):
    return re.sub(r"\s+", " ", s.replace("_", " ")).strip(" -–.#:,")


def split_order_prefix(stem):
    """'03 - Batman 05' -> ('03 - ', 'Batman 05'); ('', stem) when there is no reading-order prefix."""
    m = _ORDER.match(stem)
    return (m.group(0), stem[m.end():]) if m else ("", stem)


def parse_filename(stem):
    """'Batman #012 - The Court (2016) (of 12)' -> series/volume/issue/year/title/count (None when absent)."""
    order_prefix, stem = split_order_prefix(stem)
    m = _YEAR.search(stem)
    year = m.group(1) if m else None
    m = _COUNT.search(stem)
    count = str(int(m.group(1))) if m and int(m.group(1)) > 0 else None
    s = _clean(_TAGS.sub(" ", stem))
    volume = issue = title = None
    m = _VOL.search(s)
    if m:
        volume = str(int(m.group(1)))
        s = _clean(s[:m.start()] + " " + s[m.end():])
    m = _TITLE.match(s)
    if m:
        s, title = m.group(1), _clean(m.group(2))
    m = _ISSUE.search(s)
    if m:
        issue, s = m.group(1), s[:m.start()]
    if issue is None and volume:  # manga-style 'Berserk Vol 3': the volume is the number
        issue, volume = volume, None
    series = _clean(s)
    return {"series": series or None, "volume": volume, "issue": issue, "year": year, "title": title,
            "count": count, "order_prefix": order_prefix}


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
    """Fields from the archive's root ComicInfo.xml; {} when missing or unreadable."""
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

    return {"series": get("Series") or None, "volume": pos_int("Volume"),
            "issue": get("Number") or None, "year": pos_int("Year"), "title": get("Title") or None,
            "count": pos_int("Count"), "publisher": get("Publisher") or None,
            "series_group": get("SeriesGroup") or None, "genre": get("Genre") or None,
            "alternate_series": get("AlternateSeries") or None, "alternate_number": get("AlternateNumber") or None,
            "alternate_count": pos_int("AlternateCount"), "story_arc": get("StoryArc") or None,
            "story_arc_number": get("StoryArcNumber") or None}


def merge(parsed, ci, use_ci):
    """Filename fields, overridden by ComicInfo.xml fields when allowed and present."""
    out = dict(parsed)
    if use_ci:
        out.update({k: v for k, v in ci.items() if v})
    return out


def title_case(s):
    return re.sub(r"[A-Za-z]+(?:'[A-Za-z]+)?", lambda m: m.group(0).capitalize(), s)


def format_issue(issue, pad):
    m = re.fullmatch(r"(\d+)(\.\d+)?", issue or "")
    if not m or not pad:
        return issue or ""
    return str(int(m.group(1))).zfill(pad) + (m.group(2) or "")


def render(template, fields):
    def group(m):
        inner = m.group(1)
        if all(fields.get(t) for t in _TOKEN.findall(inner)):
            return _TOKEN.sub(lambda t: fields[t.group(1)], inner)
        return ""

    s = re.sub(r"\[([^\[\]]*)\]", group, template)
    s = _TOKEN.sub(lambda t: fields.get(t.group(1)) or "", s)
    return re.sub(r"\s+", " ", s).strip(" -–")


def safe_name(stem):
    return sanitize(re.sub(r"\s*:\s*", " - ", stem))


def build_stem(fields, template, pad, case):
    f = dict(fields)
    if f.get("series") and case == "Title Case":
        f["series"] = title_case(f["series"])
    f["issue"] = format_issue(f.get("issue"), PADS[pad])
    return render(template, f), f


def series_folder(f, style):
    name = f.get("series") or ""
    if style == FOLDER_STYLES[1] and f.get("volume"):
        name += f" v{f['volume']}"
    return sanitize(name)


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

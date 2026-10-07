"""Archive rewriting: CBR -> CBZ, clean-up, ComicInfo.xml stamping. No UI code.

Every write goes to a '.part' file, is verified, and only then swapped in, so a failure never
leaves a half-written archive where a comic used to be.
"""
import fnmatch
import shutil
import time
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from comic_core import ARCHIVE_DIR, Comic, is_page, natural_key, unique

KEEP_NAMES, SEQUENTIAL = "Keep as is", "Sequential (001.jpg)"
BACKUP, REPLACE = "Keep a backup in Archive folder", "Replace the original"
BACKUP_SUFFIX = ".bak"
CI_TAGS = {"series": "Series", "issue": "Number", "volume": "Volume", "year": "Year", "title": "Title",
           "count": "Count", "publisher": "Publisher", "series_group": "SeriesGroup", "genre": "Genre",
           "alternate_series": "AlternateSeries", "alternate_number": "AlternateNumber",
           "alternate_count": "AlternateCount", "story_arc": "StoryArc", "story_arc_number": "StoryArcNumber"}


def is_comicinfo(name):
    return Path(name).name.lower() == "comicinfo.xml"


def verify_zip(path, expected_pages):
    with zipfile.ZipFile(path) as z:
        bad = z.testzip()
        pages = sum(1 for n in z.namelist() if is_page(n))
    if bad:
        raise RuntimeError(f"Verification failed: {bad} is corrupt")
    if pages != expected_pages:
        raise RuntimeError(f"Verification failed: expected {expected_pages} pages, found {pages}")


def move_to_archive(path):
    """Move `path` into an 'Archive' folder next to it as '<name>.bak', so readers such as YACReader
    don't import it as a duplicate comic. Restoring is dropping the '.bak'. Returns the new location."""
    dest = unique(path.parent / ARCHIVE_DIR / (path.name + BACKUP_SUFFIX))
    dest.parent.mkdir(exist_ok=True)
    shutil.move(str(path), str(dest))
    return dest


def swap_in(part, target, backup):
    """Put the verified `part` file in place of `target`, optionally keeping the old one."""
    if not backup:
        part.replace(target)
        return
    saved = move_to_archive(target)
    try:
        part.replace(target)
    except OSError:
        shutil.move(str(saved), str(target))
        raise


# ---------- CBR -> CBZ ----------

def convert_to_cbz(src, dest):
    """Write a verified .cbz copy of `src` at `dest`. Returns the page count."""
    comic = Comic(src)
    part = dest.with_name(dest.name + ".part")
    try:
        comic.to_zip(part)
        verify_zip(part, len(comic.pages))
        part.replace(dest)
        return len(comic.pages)
    finally:
        part.unlink(missing_ok=True)
        comic.close()


KEEP, MOVE, DELETE = "Keep it", "Move to Archive folder", "Delete it"


def dispose_original(src, how):
    """What to do with the source after a successful conversion."""
    if how == MOVE:
        move_to_archive(src)
    elif how == "Delete it":
        src.unlink()


# ---------- rewriting zips ----------

def rewrite_zip(src, dest, order, extra=None):
    """Copy entries `order` = [(old_name, new_name)] into a new zip, then `extra` = {name: bytes}.
    Pages are stored (already compressed); everything else is deflated."""
    now = time.localtime()[:6]
    with zipfile.ZipFile(src) as zi, zipfile.ZipFile(dest, "w") as zo:
        for old, new in order:
            zinfo = zipfile.ZipInfo(new, date_time=zi.getinfo(old).date_time)
            zinfo.compress_type = zipfile.ZIP_STORED if is_page(old) else zipfile.ZIP_DEFLATED
            zo.writestr(zinfo, zi.read(old))
        for name, data in (extra or {}).items():
            zinfo = zipfile.ZipInfo(name, date_time=now)
            zinfo.compress_type = zipfile.ZIP_DEFLATED
            zo.writestr(zinfo, data)


def _files(path):
    with zipfile.ZipFile(path) as z:
        return [i.filename for i in z.infolist() if not i.is_dir()]


# ---------- clean-up ----------

def plan_cleanup(path, remove_junk, patterns, names):
    """What clean-up would do to one CBZ. Raises ValueError if it can't be cleaned safely."""
    if not zipfile.is_zipfile(path):
        raise ValueError("Not a zip-based archive (convert CBR to CBZ first)")
    pats = [p.strip().lower() for p in patterns.split(",") if p.strip()]
    pages, other, remove, info = [], [], [], None
    for n in _files(path):
        low = n.lower()
        if is_comicinfo(n):
            if info is None or ("/" not in n and "/" in info):  # prefer a root-level one
                info = n
            continue
        if any(fnmatch.fnmatch(Path(low).name, p) or fnmatch.fnmatch(low, p) for p in pats):
            remove.append(n)
        elif is_page(n):
            pages.append(n)
        elif remove_junk:
            remove.append(n)
        else:
            other.append(n)
    if not pages:
        raise ValueError("No pages would be left")
    pages.sort(key=natural_key)
    width = max(3, len(str(len(pages))))
    order, renames = [], 0
    for i, old in enumerate(pages, 1):
        new = f"{i:0{width}d}{Path(old).suffix.lower()}" if names == SEQUENTIAL else old
        renames += new != old
        order.append((old, new))
    if info:
        new = "ComicInfo.xml" if names == SEQUENTIAL else info
        renames += new != info
        order.append((info, new))
    order += [(n, n) for n in other]
    return {"order": order, "pages": len(pages), "remove": remove, "renames": renames,
            "changed": bool(remove or renames)}


def describe_cleanup(plan):
    bits = []
    if plan["remove"]:
        bits.append(f"remove {len(plan['remove'])} file{'s' if len(plan['remove']) != 1 else ''}")
    if plan["renames"]:
        bits.append(f"rename {plan['renames']}")
    return ", ".join(bits) or "already clean"


def apply_cleanup(path, plan, backup):
    part = path.with_name(path.name + ".part")
    try:
        rewrite_zip(path, part, plan["order"])
        verify_zip(part, plan["pages"])
        swap_in(part, path, backup)
    finally:
        part.unlink(missing_ok=True)


# ---------- ComicInfo.xml ----------

def read_comicinfo_raw(path):
    """(entry name, bytes) of the archive's root ComicInfo.xml, or (None, None)."""
    with zipfile.ZipFile(path) as z:
        name = next((n for n in z.namelist() if n.lower() == "comicinfo.xml"), None)
        return (name, z.read(name)) if name else (None, None)


def merge_comicinfo(raw, writes):
    """New ComicInfo.xml bytes: existing XML (if any) with the given {field: value} set.
    A value of None removes that field's tag instead."""
    if raw:
        try:
            root = ET.fromstring(raw.lstrip(b"\xef\xbb\xbf"))
        except ET.ParseError as e:
            raise ValueError(f"Existing ComicInfo.xml is malformed ({e})") from e
    else:
        root = ET.Element("ComicInfo")
    for field, value in writes.items():
        tag = CI_TAGS[field]
        if value is None:  # remove the tag altogether
            for el in root.findall(tag):
                root.remove(el)
            continue
        el = root.find(tag)
        if el is None:
            el = ET.SubElement(root, tag)
        el.text = str(value)
    ET.indent(root, space="  ")
    return ('<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(root, encoding="unicode")).encode("utf-8")


def apply_metadata(path, writes, backup):
    if not zipfile.is_zipfile(path):
        raise ValueError("Not a zip-based archive (convert CBR to CBZ first)")
    existing, raw = read_comicinfo_raw(path)
    xml = merge_comicinfo(raw, writes)
    names = _files(path)
    pages = sum(1 for n in names if is_page(n))
    part = path.with_name(path.name + ".part")
    try:
        rewrite_zip(path, part, [(n, n) for n in names if n != existing], {existing or "ComicInfo.xml": xml})
        verify_zip(part, pages)
        swap_in(part, path, backup)
    finally:
        part.unlink(missing_ok=True)

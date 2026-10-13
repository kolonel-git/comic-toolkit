"""Add-to-library pipeline (no UI): work out the new name and place for a comic, spot copies already in the Ready
folder, and run convert -> clean -> rename -> remove the original, verifying before anything is deleted.

Names come from the Renamer's own settings (templates, padding, case, folder template), so a comic added here is named
exactly as the Renamer would name it.
"""
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

import name_format as nf
from archive_tools import SEQUENTIAL, KEEP_NAMES, apply_cleanup, dispose_original, plan_cleanup, verify_zip
from comic_core import ARCHIVE_DIR, COMIC_EXT, Comic, find_comics, in_archive, natural_key, unique
from rename_core import apply_type, merge, parse_filename

VOL_ISSUE = "An issue (manga style)"  # the Renamer's first "a name with only Vol 3 is" choice (page_rename.VOL_MODES[0])
READY, DUPLICATE, EXISTS, NO_SERIES, IN_PLACE, DONE, FAILED = (
    "Ready", "Duplicate", "Exists", "No series", "In place", "Added", "Failed")
PROCESSABLE = (READY, DUPLICATE, EXISTS, NO_SERIES)  # statuses that can be run once ticked
_ARTICLE = re.compile(r"^(?:the|a|an)\s+")


@dataclass
class Item:
    src: Path
    ci: dict = None                   # ComicInfo.xml fields; None until read
    fields: dict = field(default_factory=dict)
    dest: Path = None
    status: str = ""
    note: str = ""
    error: str = ""                   # why the last run failed; cleared to try again
    checked: bool = True
    manual: bool = False              # the user ticked or unticked it, so a recompute keeps their choice
    steps: str = ""
    iid: str = field(default="", repr=False)


def rename_settings(saved=None):
    """The Renamer settings this tool needs: `saved` (a RenamePage.state() dict) over the Renamer's defaults."""
    s = {"use_ci": True, "detect_collected": True, "vol_mode": VOL_ISSUE, "keep_order": False,
         "folder_tpl": nf.FOLDER_PRESETS["Series"], "collected_sub": False, "collected_sub_name": "Collected Editions",
         **nf.DEFAULT_OPTIONS, **{f"t_{nf.slug(t)}": tpl for t, tpl in nf.DEFAULT_TEMPLATES.items()}}
    s.update({k: v for k, v in (saved or {}).items() if k in s})
    return s


def text_options(s):
    try:
        n = max(0, int(str(s["max_len"]).strip() or 0))
    except ValueError:
        n = 0
    return {k: s[k] for k in ("pad", "vpad", "series_case", "title_case", "article", "separator", "illegal",
                              "ext_case")} | {"max_len": n}


def templates(s):
    return {t: s[f"t_{nf.slug(t)}"] for t in nf.DEFAULT_TEMPLATES}


def _norm(text):
    return _ARTICLE.sub("", (text or "").lower().strip())


def dup_key(stem):
    """Identity of a comic from its name: series, volume, issue and (for collected editions) title."""
    p = parse_filename(stem)
    if not p.get("series"):
        return None
    title = _norm(p["title"]) if p["collected"] and not p["volume"] else ""
    issue = str(p["issue"] or "").lstrip("0") or ("0" if p["issue"] else "")
    return (_norm(p["series"]), str(p["volume"] or ""), issue, bool(p["collected"]), p["range"] or "", title)


def library_index(root):
    """{dup_key: [paths]} of the comics already under `root` (names only, so it is quick)."""
    out = {}
    root = Path(root)
    if root.is_dir():
        for p in root.rglob("*"):
            if p.is_file() and p.suffix.lower() in COMIC_EXT and not in_archive(p, root):
                k = dup_key(p.stem)
                if k:
                    out.setdefault(k, []).append(p)
    return out


def existing_folders(root):
    """{lowercase name without a leading The/A/An: real folder name} for the folders directly in `root`."""
    root = Path(root)
    if not root.is_dir():
        return {}
    return {_norm(d.name): d.name for d in root.iterdir() if d.is_dir() and d.name != ARCHIVE_DIR}


def name_for(src, ci, s, fallback_series=None):
    """(fields, stem) the Renamer would give this comic. stem is the file name without extension."""
    parsed = parse_filename(src.stem, volume_as_issue=s["vol_mode"] == VOL_ISSUE)
    f = merge(parsed, ci or {}, s["use_ci"])
    if not s["detect_collected"]:
        f = apply_type(f, "Issue")
    if not f.get("series") and fallback_series:
        f["series"] = fallback_series
    if not f.get("series"):
        return f, src.stem
    stem = nf.build_name(f, nf.template_for(f, templates(s)), text_options(s))
    if s["keep_order"] and parsed.get("order_prefix"):
        stem = parsed["order_prefix"] + stem
    return f, stem


def plan(items, ready, s, o, inbox=None):
    """Fill in dest, status and steps for every item. `o` has rename, folders, junk, pages (the page-name option).
    Items the user has not touched are ticked when Ready and unticked otherwise."""
    ready = Path(ready)
    index = library_index(ready)
    folders = existing_folders(ready) if o["folders"] else {}
    canon, claimed, keys = {}, {}, {}
    opts = text_options(s)
    for it in items:
        fallback = None
        if inbox and it.src.parent != Path(inbox) and it.src.parent.name:
            fallback = it.src.parent.name  # a file called just '012.cbz' inside a series folder
        if o["rename"]:
            it.fields, stem = name_for(it.src, it.ci, s, fallback)
        else:
            it.fields, stem = {}, it.src.stem
        name = nf.safe_name(stem, opts["illegal"]) + nf.ext_text(".cbz", opts["ext_case"])
        folder = ready
        if o["rename"] and o["folders"] and it.fields.get("series"):
            parts = nf.build_folder(it.fields, s["folder_tpl"], opts)
            if parts:
                key = "/".join(_norm(p) for p in parts)
                if len(parts) == 1 and _norm(parts[0]) in folders:
                    parts = [folders[_norm(parts[0])]]  # reuse The Walking Dead / Walking Dead as it already exists
                folder = ready.joinpath(*canon.setdefault(key, parts))
            if it.fields.get("collected") and s["collected_sub"] and s["collected_sub_name"].strip():
                folder = folder / nf.sanitize(s["collected_sub_name"].strip())
        it.dest = folder / name
        it.note = ""
        key = dup_key(it.dest.stem)
        same = [p for p in index.get(key, []) if str(p).lower() != str(it.src).lower()] if key else []
        if str(it.dest).lower() == str(it.src).lower():
            it.status = IN_PLACE
        elif o["rename"] and not it.fields.get("series"):
            it.status = NO_SERIES
        elif it.dest.exists():
            it.status, it.note = EXISTS, f"{it.dest.name} is already there"
        elif same:
            it.status, it.note = DUPLICATE, f"Looks like {same[0].name}"
        elif str(it.dest).lower() in claimed:
            it.status, it.note = DUPLICATE, f"Same name as {claimed[str(it.dest).lower()].src.name}"
        elif key and key in keys:
            it.status, it.note = DUPLICATE, f"Same comic as {keys[key].src.name}"
        else:
            it.status = READY
        if it.error:
            it.status, it.note = FAILED, it.error
        if it.status != IN_PLACE:
            claimed.setdefault(str(it.dest).lower(), it)
            if key:
                keys.setdefault(key, it)
        bits = []
        if not zipfile.is_zipfile(it.src):
            bits.append("convert")
        if o["junk"] or o["pages"]:
            bits.append("clean")
        if o["rename"] and it.dest.stem != it.src.stem:
            bits.append("rename")
        it.steps = " · ".join(bits) or "copy"
        if not it.manual:
            it.checked = it.status == READY
    return items


def add_comic(src, dest, junk=True, patterns="", sequential=False, original="Delete it"):
    """Make a verified, cleaned .cbz of `src` at `dest` (a free variant of the name if it is taken), then deal with
    the original. Nothing is touched until the new file has passed its checks. Returns a summary dict."""
    src, dest = Path(src), Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest = unique(dest)
    part = dest.with_name(dest.name + ".part")
    converted = not zipfile.is_zipfile(src)
    try:
        comic = Comic(src)
        try:
            pages = len(comic.pages)
            comic.to_zip(part)
        finally:
            comic.close()
        verify_zip(part, pages)
        removed = renamed = 0
        if junk or patterns.strip() or sequential:
            p = plan_cleanup(part, junk, patterns, SEQUENTIAL if sequential else KEEP_NAMES)
            if p["changed"]:
                apply_cleanup(part, p, backup=False)
                removed, renamed, pages = len(p["remove"]), p["renames"], p["pages"]
        verify_zip(part, pages)
        part.replace(dest)
    finally:
        part.unlink(missing_ok=True)
    dispose_original(src, original)
    return {"dest": dest, "pages": pages, "converted": converted, "removed": removed, "renamed": renamed}


def prune_empty(folder, stop):
    """Remove `folder` and its parents while they are empty, never `stop` itself or anything outside it."""
    folder, stop = Path(folder), Path(stop)
    while folder != stop and stop in folder.parents:
        try:
            folder.rmdir()
        except OSError:
            return
        folder = folder.parent


def find_sources(paths, recursive=True):
    """Comics among `paths` (files, or folders searched for comics), without repeats, in natural order."""
    seen, out = set(), []
    for p in map(Path, paths):
        if p.is_dir():
            found = find_comics(p, recursive)
        else:
            found = [p] if p.is_file() and p.suffix.lower() in COMIC_EXT else []
        for f in found:
            if str(f).lower() not in seen:
                seen.add(str(f).lower())
                out.append(f)
    return sorted(out, key=lambda p: natural_key(str(p)))

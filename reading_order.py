"""Reading Order logic: plan and apply an ordered list of issues as ComicInfo.xml metadata. No UI code.

The order lives inside each CBZ (`StoryArc` + `StoryArcNumber`, and/or `AlternateSeries` +
`AlternateNumber` + `AlternateCount`), so nothing has to be renamed. Optionally the filenames also get a
numeric prefix, and the issues can be copied into a new folder so the originals are never touched.
"""
from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

from archive_tools import CI_TAGS, apply_metadata
from comic_core import natural_key, sanitize, unique
from rename_core import do_rename, parse_filename, split_order_prefix

STORY, ALTERNATE, BOTH = "Story arc", "Alternate series", "Both"
STORES = [STORY, ALTERNATE, BOTH]
NUM_PLAIN, NUM_PADDED = "1, 2, 3", "01, 02, 03"
NUMBERINGS = [NUM_PLAIN, NUM_PADDED]
PREFIX_OFF, PREFIX_DASH, PREFIX_BRACKET = "Off (metadata only)", "01 - Name", "[01] Name"
PREFIXES = [PREFIX_OFF, PREFIX_DASH, PREFIX_BRACKET]


def width(total):
    return max(2, len(str(total)))


def number_text(n, total, numbering):
    return str(n).zfill(width(total)) if numbering == NUM_PADDED else str(n)


def prefix_text(n, total, style):
    num = str(n).zfill(width(total))
    return {PREFIX_DASH: f"{num} - ", PREFIX_BRACKET: f"[{num}] "}.get(style, "")


def writes_for(name, n, total, store, numbering, group=""):
    """The ComicInfo fields that give an issue position `n` of `total` in the reading order `name`."""
    w = {}
    if store in (STORY, BOTH):
        w["story_arc"] = name
        w["story_arc_number"] = number_text(n, total, numbering)
    if store in (ALTERNATE, BOTH):
        w["alternate_series"] = name
        w["alternate_number"] = str(n)
        w["alternate_count"] = str(total)
    if group:
        w["series_group"] = group
    return w


def current_arc(ci, store):
    """(name, number) this issue already has, for the storage choice in use."""
    if store == ALTERNATE:
        return ci.get("alternate_series"), ci.get("alternate_number")
    return ci.get("story_arc"), ci.get("story_arc_number")


def writable(path):
    """Why a file can't be written, or None. Only zip-based archives can be stamped."""
    path = Path(path)
    if not path.is_file():
        return "Missing"
    if not zipfile.is_zipfile(path):
        return "Convert to CBZ first" if path.suffix.lower() == ".cbr" else "Not a zip archive"
    return None


def suggest_key(path):
    """Sort key: series, volume, year, issue number; anything that can't be parsed goes last, by name."""
    f = parse_filename(Path(path).stem)

    def num(v):
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    issue = num(f.get("issue"))
    return (f.get("series") is None, (f.get("series") or "").lower(), num(f.get("volume")) or 0,
            num(f.get("year")) or 0, issue is None, issue or 0, natural_key(Path(path).name))


def plan_item(path, ci, n, total, o, why_not=None):
    """What would happen to one issue at position `n`. `o` holds name, store, numbering, group, prefix.
    Returns {'writes', 'new_name', 'status', 'blocked'}."""
    path = Path(path)
    if why_not:
        return {"writes": {}, "new_name": path.name, "status": why_not, "blocked": True}
    want = writes_for(o["name"], n, total, o["store"], o["numbering"], o["group"])
    writes = {k: v for k, v in want.items() if (ci.get(k) or "") != v}
    if o.get("drop_issue") and ci.get("issue"):
        writes["issue"] = None  # remove Number so the reader falls back to the filename
    new_name = path.name
    pre = prefix_text(n, total, o["prefix"])
    if pre:
        new_name = pre + split_order_prefix(path.stem)[1] + path.suffix
    old_name, old_num = current_arc(ci, o["store"])
    if not writes and new_name == path.name:
        status = "No change"
    elif old_name and old_name != o["name"]:
        status = f"Replaces “{old_name}”"
    else:
        status = "Update" if (old_name or ci) else "Add"
    return {"writes": writes, "new_name": new_name, "status": status, "blocked": False}


def apply_item(path, writes, new_name, backup, dest_dir=None):
    """Write one issue. With `dest_dir` the file is copied there first and only the copy is stamped.
    Returns the final path. Raises on failure (a copy that failed is removed)."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError("File not found (moved or deleted since it was added)")
    if dest_dir is not None:
        dest_dir = Path(dest_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = unique(dest_dir / sanitize_name(new_name))
        shutil.copy2(path, dest)
        try:
            if writes:
                apply_metadata(dest, writes, False)  # a fresh copy needs no backup
        except Exception:
            dest.unlink(missing_ok=True)
            raise
        return dest
    if writes:
        apply_metadata(path, writes, backup)
    if new_name != path.name:
        target = path.with_name(sanitize_name(new_name))
        if target.exists() and str(target).lower() != str(path).lower():
            raise FileExistsError(f"Metadata written, but {target.name} already exists so the file was not renamed")
        do_rename(path, target)
        return target
    return path


def sanitize_name(name):
    p = Path(name)
    return sanitize(p.stem) + p.suffix


def folder_name(arc):
    return sanitize(arc)


# ---------- moving several issues at once ----------

def move_block(order, selected, delta):
    """Shift every selected item one place up (delta -1) or down (+1), keeping their order relative to each
    other. Items already at the edge stay put, and the rest of the block still moves."""
    sel, out = set(selected), list(order)
    for i in (range(len(out)) if delta < 0 else range(len(out) - 1, -1, -1)):
        j = i + delta
        if out[i] in sel and 0 <= j < len(out) and out[j] not in sel:
            out[i], out[j] = out[j], out[i]
    return out


def send_to_edge(order, selected, top):
    """Move the selected items, as one block in their current order, to the very top (or bottom)."""
    sel = set(selected)
    items = [i for i in order if i in sel]
    rest = [i for i in order if i not in sel]
    return items + rest if top else rest + items


def drop_block(order, selected, target):
    """Move the selected items, as one block in their current order, to where `target` is: after it when
    dragging down, before it when dragging up. Dropping on a selected item changes nothing."""
    sel = set(selected)
    if target in sel or target not in order:
        return list(order)
    items = [i for i in order if i in sel]
    if not items:
        return list(order)
    rest = [i for i in order if i not in sel]
    at = rest.index(target) + (1 if order.index(target) > order.index(items[0]) else 0)
    return rest[:at] + items + rest[at:]


# ---------- preview ----------

def describe_item(path, ci, plan, store):
    """Plain-text lines saying what writing one issue would do. Nothing is touched."""
    path = Path(path)
    if plan["blocked"]:
        return [f"{path.name}", f"    skipped: {plan['status']}"]
    if plan["status"] == "No change":
        return [f"{path.name}", "    no change"]
    lines = [path.name if plan["new_name"] == path.name else f"{path.name}  ->  {plan['new_name']}"]
    for field, value in plan["writes"].items():
        lines.append(f"    {CI_TAGS[field]}: {ci.get(field) or '(none)'}  ->  {'(removed)' if value is None else value}")
    if plan["status"].startswith("Replaces"):
        lines.append(f"    note: {plan['status'].lower()}")
    return lines

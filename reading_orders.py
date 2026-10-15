"""The folders the user has marked as reading orders, and a guess at which other folders look like one. No UI code.

A reading-order folder holds copies of issues arranged for reading (`01 - Name`, `[02] Name`, or a story arc in
`ComicInfo.xml`). Those copies would be counted twice by the library stats and the duplicate check, so the user marks
the folders once and every tool leaves them out. The list is kept in settings.json (see `to_list` / `from_list`).
"""
from __future__ import annotations

import os
from pathlib import Path

from rename_core import split_order_prefix

MIN_COMICS = 3        # a folder needs at least this many comics before it can look like a reading order
LOOKS_LIKE = 0.6      # and at least this share of them must carry an order prefix or a story arc


def _norm(path):
    return os.path.normcase(os.path.abspath(str(path)))


class ReadingOrders:
    """The marked folders (and the suggestions the user turned down). Paths are compared case-insensitively."""

    def __init__(self, folders=(), dismissed=()):
        self._folders = {}    # normalised path -> path as the user gave it
        self._dismissed = {}
        for p in folders:
            self.add(p)
        for p in dismissed:
            self._dismissed[_norm(p)] = str(p)

    # --- the marked folders
    @property
    def folders(self):
        return sorted(self._folders.values(), key=str.lower)

    def add(self, folder):
        """Mark a folder. Returns False when it is already marked or sits inside a marked folder."""
        key = _norm(folder)
        if self.covers(folder):
            return False
        for k in [k for k in self._folders if _inside(k, key)]:   # a new parent replaces the folders under it
            del self._folders[k]
        self._folders[key] = str(folder)
        self._dismissed.pop(key, None)
        return True

    def remove(self, folder):
        return self._folders.pop(_norm(folder), None) is not None

    def covers(self, path):
        """True if `path` is a marked folder or lies inside one."""
        key = _norm(path)
        return any(key == k or _inside(key, k) for k in self._folders)

    def which(self, path):
        """The marked folder that holds `path` (as the user gave it), or None."""
        key = _norm(path)
        for k, folder in self._folders.items():
            if key == k or _inside(key, k):
                return folder
        return None

    def __len__(self):
        return len(self._folders)

    # --- suggestions the user said no to
    def dismiss(self, folder):
        self._dismissed[_norm(folder)] = str(folder)

    def dismissed(self, folder):
        return _norm(folder) in self._dismissed

    # --- saving
    def to_dict(self):
        return {"folders": self.folders, "dismissed": sorted(self._dismissed.values(), key=str.lower)}

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict):
            return cls()
        good = lambda v: [p for p in v if isinstance(p, str) and p] if isinstance(v, list) else []  # noqa: E731
        return cls(good(data.get("folders")), good(data.get("dismissed")))

    def split(self, issues):
        """(everything else, the comics inside marked folders)."""
        real, orders = [], []
        for i in issues:
            (orders if self.covers(i.path) else real).append(i)
        return real, orders


def _inside(key, parent):
    return key.startswith(parent.rstrip("\\/") + os.sep)


def _has_prefix(issue):
    return bool(split_order_prefix(issue.path.stem)[0])


def looks_like_reading_order(issues):
    """(True, reason) when most of these comics (all from one folder) carry a reading-order prefix or a story arc."""
    n = len(issues)
    if n < MIN_COMICS:
        return False, ""
    prefixed = sum(1 for i in issues if _has_prefix(i))
    arcs = sum(1 for i in issues if (i.ci or {}).get("story_arc"))
    if prefixed >= LOOKS_LIKE * n:
        return True, f"{prefixed} of {n} names start with a number"
    if arcs >= LOOKS_LIKE * n:
        return True, f"{arcs} of {n} have a story arc"
    return False, ""


def suggest(issues, orders, root):
    """Folders under `root` that look like reading orders and are not marked, covered or turned down:
    [(folder, comic count, reason)], biggest first. Only a comic's own folder is judged, not its parents."""
    by_folder = {}
    for i in issues:
        by_folder.setdefault(i.path.parent, []).append(i)
    out = []
    for folder, group in by_folder.items():
        if Path(folder) == Path(root) or orders.covers(folder) or orders.dismissed(folder):
            continue
        ok, reason = looks_like_reading_order(group)
        if ok:
            out.append((folder, len(group), reason))
    return sorted(out, key=lambda t: (-t[1], str(t[0]).lower()))

"""Editing the details stored inside comics: one `Row` per comic with the edits waiting to be saved, which comics lack
what, a fill from filenames, and suggestions for each field taken from the comics already in the library. No UI code.

Nothing here writes a file; `changes()` and `writes()` say what a save would do, and `archive_tools.apply_metadata`
does it.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from stats_core import series_key

MAIN = ("series", "issue", "volume", "year", "title", "publisher", "count")
EXTRA = ("series_group", "genre", "alternate_series", "story_arc")
FIELDS = MAIN + EXTRA
LABELS = {"series": "Series", "issue": "Issue number", "volume": "Volume", "year": "Year", "title": "Title",
          "publisher": "Publisher", "count": "Issue count", "series_group": "Series group", "genre": "Genre",
          "alternate_series": "Alternate series", "story_arc": "Story arc"}
FROM_NAME = ("series", "issue", "volume", "year", "title", "count")   # what a filename can supply
NEEDED = ("series", "issue", "year", "publisher")                      # a comic missing one of these needs attention
SHARED = ("publisher", "series_group", "genre")                         # worth offering to the rest of a series
PER_COMIC = ("issue", "title")                                          # differ from comic to comic: only the file name can suggest them
FILTERS = {"all": "All comics", "attention": "Needs attention", "no_series": "No series", "no_issue": "No issue number",
           "no_year": "No year", "no_publisher": "No publisher", "no_comicinfo": "No ComicInfo.xml"}


def clean(name, value):
    """Normalise a value before it is stored ('012' -> '12')."""
    value = (value or "").strip()
    if name == "issue":
        m = re.fullmatch(r"0*(\d+)(\.\d+)?", value)
        if m:
            return m.group(1) + (m.group(2) or "")
    return value


@dataclass
class Row:
    path: Path
    parsed: dict                                   # fields read from the filename
    ci: dict                                       # fields stored in ComicInfo.xml ({} when none)
    locked: bool = False                           # a .cbr cannot be written to
    pending: dict = field(default_factory=dict)    # field -> new value, or None to delete the tag

    def value(self, name):
        """What the comic will hold once saved."""
        if name in self.pending:
            return self.pending[name] or ""
        return self.ci.get(name) or ""

    @property
    def collected(self):
        return bool(self.parsed.get("collected"))

    def set(self, name, text):
        """Edit one field. Putting back what is stored removes the pending edit; emptying a stored value deletes it."""
        text = clean(name, text)
        old = clean(name, self.ci.get(name) or "")
        if text == old:
            self.pending.pop(name, None)
        elif not text:
            self.pending[name] = None
        else:
            self.pending[name] = text

    def discard(self):
        self.pending.clear()


# ---------- what is missing ----------

def missing(row, name):
    return not row.value(name)


def lacks(row):
    """The needed fields this comic does not have (issue number only matters for single issues)."""
    return [f for f in NEEDED if missing(row, f) and not (f == "issue" and row.collected)]


def needs_attention(row):
    return bool(lacks(row))


def matches(row, key):
    """Does the comic belong in the view `key` (see FILTERS)?"""
    if key == "attention":
        return needs_attention(row)
    if key == "no_series":
        return missing(row, "series")
    if key == "no_issue":
        return missing(row, "issue") and not row.collected
    if key == "no_year":
        return missing(row, "year")
    if key == "no_publisher":
        return missing(row, "publisher")
    if key == "no_comicinfo":
        return not row.ci and not row.locked
    return True


# ---------- edits ----------

def writes(row):
    """What to hand to `apply_metadata`: {field: value, or None to delete}."""
    return dict(row.pending)


def changes(rows):
    """[(row, field, old, new)] for every pending edit; `new` is '' for a deletion."""
    out = []
    for row in rows:
        for name in FIELDS:
            if name in row.pending:
                out.append((row, name, row.ci.get(name) or "", row.pending[name] or ""))
    return out


def fill_from_filename(row, root=None):
    """Fill the empty fields the filename can supply (and the series from the folder name when nothing else gives
    one). Returns how many fields were set."""
    n = 0
    for name in FROM_NAME:
        if row.value(name):
            continue
        value = clean(name, row.parsed.get(name) or "")
        if not value and name == "series" and root is not None and row.path.parent != Path(root):
            value = row.path.parent.name
        if value:
            row.set(name, value)
            n += 1
    return n


def same_series(rows, row):
    """The other editable comics in the same series as `row` (compared ignoring case, punctuation and a leading The)."""
    key = series_key(row.value("series") or row.parsed.get("series") or "")
    if not key:
        return []
    return [r for r in rows if r is not row and not r.locked
            and series_key(r.value("series") or r.parsed.get("series") or "") == key]


def others_lacking(rows, row, name):
    """Comics in the same series that have no `name` while `row` has one: who to offer the value to."""
    mine = row.value(name)
    if not mine:
        return []
    return [r for r in same_series(rows, row) if not r.value(name)]


# ---------- suggestions from the library ----------

class SuggestIndex:
    """Suggestions for a field of one comic, taken only from the other comics in the library: the same series first,
    then the same folder, then what the filename says, then the most used values in the whole library."""

    def __init__(self, rows):
        self.rows = list(rows)
        self.by_folder, self.by_series = {}, {}
        for r in self.rows:
            self.by_folder.setdefault(r.path.parent, []).append(r)
            key = series_key(r.ci.get("series") or r.parsed.get("series") or "")
            if key:
                self.by_series.setdefault(key, []).append(r)

    @staticmethod
    def _top(rows, name, skip):
        count = Counter(r.value(name) for r in rows if r is not skip and r.value(name))
        return [v for v, _n in count.most_common()]

    def for_field(self, row, name, limit=5):
        """[(value, where from)] with where from one of 'series', 'folder', 'name', 'library'; never the value the
        comic already holds."""
        out, seen = [], {row.value(name)}

        def add(values, source):
            for v in values:
                if v and v not in seen and len(out) < limit:
                    seen.add(v)
                    out.append((v, source))

        if name == "series":
            mine = series_key(row.value("series") or row.parsed.get("series") or row.path.parent.name)
            near = [r for k, rs in self.by_series.items() if mine and (k == mine or k.startswith(mine + " ") or mine.startswith(k + " "))
                    for r in rs]
            add(self._top(near, "series", row), "series")
            add(self._top(self.by_folder.get(row.path.parent, []), "series", row), "folder")
            add([clean(name, row.parsed.get("series") or "")], "name")
            return out
        if name not in PER_COMIC:
            series_rows = self.by_series.get(series_key(row.value("series") or row.parsed.get("series") or ""), [])
            add(self._top(series_rows, name, row), "series")
            add(self._top(self.by_folder.get(row.path.parent, []), name, row), "folder")
        if name in FROM_NAME:
            add([clean(name, row.parsed.get(name) or "")], "name")
        if name in ("publisher", "genre", "series_group", "alternate_series"):
            add(self._top(self.rows, name, row), "library")
        return out

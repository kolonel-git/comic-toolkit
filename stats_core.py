"""Library statistics: totals, groupings and metadata coverage over the records of `library_scan`. No UI code.

`compute_stats(issues)` is a pure function of a list of `Issue` records, so the dashboard, the Home summary line and the
tests all use the same numbers. Nothing here reads or changes a file.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field

UNKNOWN = "Unknown"
SECTIONS = ("Series", "Publishers", "Years", "Formats")
TOP = 15  # bars shown before the rest are lumped into "Other"


@dataclass
class StatRow:
    label: str
    count: int = 0
    bytes: int = 0
    issues: list = field(default_factory=list)


@dataclass
class Stats:
    comics: int = 0
    series: int = 0  # distinct series (an "Unknown" bucket is not counted)
    publishers: int = 0
    bytes: int = 0
    pages: int | None = None  # total page count, only when the scan read page counts
    sections: dict = field(default_factory=dict)  # section name -> [StatRow]
    coverage: dict = field(default_factory=dict)
    largest: list = field(default_factory=list)
    smallest: list = field(default_factory=list)
    split_volumes: bool = False
    decades: bool = False

    @property
    def average(self):
        return self.bytes // self.comics if self.comics else 0


# ---------- formatting ----------

def human_size(n):
    n = float(n)
    for unit, step in (("GB", 1e9), ("MB", 1e6)):
        if n >= step:
            return f"{n / step:.1f} {unit}"
    return f"{n / 1e3:.0f} KB"


def ago(when, now=None):
    """'just now', '5 minutes ago', '2 hours ago', '3 days ago'."""
    secs = max(0, (now if now is not None else time.time()) - when)
    for unit, size in (("day", 86400), ("hour", 3600), ("minute", 60)):
        if secs >= size:
            n = int(secs // size)
            return f"{n} {unit}{'s' if n != 1 else ''} ago"
    return "just now"


# ---------- grouping ----------

def series_key(name):
    """Case, punctuation and a leading 'The' do not split a series."""
    key = re.sub(r"[^a-z0-9]+", " ", (name or "").lower()).strip()
    return re.sub(r"^the ", "", key)


def _group(issues, key_label):
    """Group issues by key_label(issue) -> (key, label); the first label seen for a key is the one shown."""
    groups, labels = {}, {}
    for i in issues:
        key, label = key_label(i)
        labels.setdefault(key, label)
        groups.setdefault(key, []).append(i)
    rows = [StatRow(labels[k], len(v), sum(i.size for i in v), v) for k, v in groups.items()]
    return rows


def _by_count(rows):
    return sorted(rows, key=lambda r: (r.label == UNKNOWN, -r.count, r.label.lower()))


def top_n(rows, n=TOP):
    """The first `n` rows plus one 'Other' row for the rest (rows are expected in the order to keep)."""
    if len(rows) <= n:
        return list(rows)
    rest = rows[n:]
    other = StatRow(f"Other ({len(rest)} more)", sum(r.count for r in rest), sum(r.bytes for r in rest),
                    [i for r in rest for i in r.issues])
    return list(rows[:n]) + [other]


def _series_rows(issues, split_volumes):
    def key_label(i):
        f = i.info
        name = (f.get("series") or "").strip()
        if not name:
            return ("", UNKNOWN)
        vol = (f.get("volume") or "") if split_volumes else ""
        return (series_key(name) + "|" + vol, f"{name} v{vol}" if vol else name)
    return _by_count(_group(issues, key_label))


def _publisher_rows(issues):
    def key_label(i):
        name = (i.info.get("publisher") or "").strip()
        return (name.lower(), name) if name else ("", UNKNOWN)
    return _by_count(_group(issues, key_label))


def _year_rows(issues, decades):
    def key_label(i):
        y = str(i.info.get("year") or "")
        if not y.isdigit():
            return ("", UNKNOWN)
        label = f"{int(y) // 10 * 10}s" if decades else y
        return (label, label)
    return _group(issues, key_label)


def years_view(rows, show_all):
    """Years read left to right in time: when there are too many, keep the most populated ones, still in time order."""
    rows = sorted(rows, key=lambda r: (r.label == UNKNOWN, r.label))
    if show_all or len(rows) <= TOP:
        return rows
    keep = sorted(sorted(rows, key=lambda r: (-r.count, r.label))[:TOP], key=lambda r: (r.label == UNKNOWN, r.label))
    kept = {id(r) for r in keep}
    rest = [r for r in rows if id(r) not in kept]
    other = StatRow(f"Other ({len(rest)} more)", sum(r.count for r in rest), sum(r.bytes for r in rest),
                    [i for r in rest for i in r.issues])
    return keep + [other]


def _format_rows(issues):
    return _by_count(_group(issues, lambda i: (i.ext, i.ext.lstrip(".").upper() or UNKNOWN)))


# ---------- the numbers ----------

def compute_stats(issues, split_volumes=False, decades=False, keep=TOP):
    """Everything the dashboard shows. `keep` is how many largest and smallest files to list."""
    issues = list(issues)
    st = Stats(split_volumes=split_volumes, decades=decades)
    st.comics = len(issues)
    st.bytes = sum(i.size for i in issues)
    deep = [i for i in issues if i.deep and i.pages is not None]
    st.pages = sum(i.pages for i in deep) if deep else None
    series = _series_rows(issues, split_volumes)
    pubs = _publisher_rows(issues)
    st.sections = {"Series": series, "Publishers": pubs, "Years": _year_rows(issues, decades),
                   "Formats": _format_rows(issues)}
    st.series = len({r.label for r in series if r.label != UNKNOWN})
    st.publishers = len([r for r in pubs if r.label != UNKNOWN])

    read = [i for i in issues if i.ci_read]  # a RAR that was not opened says nothing about its ComicInfo.xml
    info = {id(i): i.info for i in issues}
    st.coverage = {
        "total": st.comics,
        "unread": st.comics - len(read),
        "with_comicinfo": sum(1 for i in read if any(v for v in i.ci.values())),
        "with_year": sum(1 for i in issues if str(info[id(i)].get("year") or "").isdigit()),
        "with_publisher": sum(1 for i in issues if info[id(i)].get("publisher")),
        "with_issue": sum(1 for i in issues if info[id(i)].get("issue")),
        "issues": sum(1 for i in issues if not info[id(i)].get("collected")),
        "collected": sum(1 for i in issues if info[id(i)].get("collected")),
    }
    by_size = sorted(issues, key=lambda i: (-i.size, i.rel.lower()))
    st.largest = by_size[:keep]
    st.smallest = list(reversed(by_size[-keep:])) if by_size else []
    return st


# ---------- text, tables and the Home snapshot ----------

def coverage_lines(st):
    """[(label, count, of)] for the coverage section; ComicInfo.xml is judged only over the files that were opened."""
    c = st.coverage
    return [("Have ComicInfo.xml", c["with_comicinfo"], c["total"] - c["unread"]),
            ("Have a year", c["with_year"], c["total"]),
            ("Have a publisher", c["with_publisher"], c["total"]),
            ("Have an issue number", c["with_issue"], c["total"]),
            ("Single issues", c["issues"], c["total"]),
            ("Collected editions", c["collected"], c["total"])]


def summary_text(st, root=None):
    lines = ["Comic library" + (f": {root}" if root else ""),
             f"{st.comics:,} comics · {st.series:,} series · {st.publishers:,} publishers · {human_size(st.bytes)} "
             f"(average {human_size(st.average)})"]
    if st.pages is not None:
        lines[-1] += f" · {st.pages:,} pages"
    for name in SECTIONS:
        rows = _by_count(st.sections[name]) if name != "Years" else years_view(st.sections[name], False)
        top = ", ".join(f"{r.label} {r.count}" for r in (rows[:5] if name != "Years" else rows))
        if top:
            lines.append(f"{name}: {top}")
    for label, n, of in coverage_lines(st):
        lines.append(f"{label}: {n:,} of {of:,}" + (f" ({100 * n // of}%)" if of else ""))
    return "\n".join(lines)


def section_table(st, name, show_all=True):
    """(header, rows) for the CSV export of one dashboard section."""
    if name in SECTIONS:
        rows = st.sections[name]
        rows = (_by_count(rows) if name != "Years" else years_view(rows, True)) if show_all else \
            (top_n(_by_count(rows)) if name != "Years" else years_view(rows, False))
        head = {"Series": "Series", "Publishers": "Publisher", "Years": "Year", "Formats": "Format"}[name]
        return [head, "Comics", "Bytes"], [[r.label, r.count, r.bytes] for r in rows]
    if name == "Coverage":
        return ["Measure", "Comics", "Out of"], [[label, n, of] for label, n, of in coverage_lines(st)]
    if name == "Largest":
        return ["File", "Bytes"], [[i.rel, i.size] for i in st.largest]
    raise KeyError(name)


def snapshot(st, root, when=None):
    """The few numbers the Home line shows; small enough to keep in settings.json."""
    return {"root": str(root), "comics": st.comics, "series": st.series, "bytes": st.bytes,
            "when": time.time() if when is None else when}


def snapshot_line(snap, now=None):
    return (f"{snap['comics']:,} comic{'s' if snap['comics'] != 1 else ''} · {snap['series']:,} series · "
            f"{human_size(snap['bytes'])} · scanned {ago(snap['when'], now)}")

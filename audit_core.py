"""Library audit logic: integrity checks, duplicates, missing issues, warnings, junk and CBR findings, and the fixes
for them. No UI code.

Everything here works on the `Issue` records from `library_scan`. The `find_*` and `build_findings` functions never
change a file; only `apply_fix` does, one file at a time, and only for a finding the user ticked.
"""
from __future__ import annotations

import io
import re
import subprocess
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image

from archive_tools import (DELETE, KEEP_NAMES, apply_cleanup, convert_to_cbz, dispose_original, move_to_archive,
                           plan_cleanup)
from comic_core import ARCHIVE_DIR, find_extractor, is_page, natural_key

# ---------- thresholds (documented in docs/tools.md) ----------
MIN_PAGES, MAX_PAGES = 10, 300
SMALL_BYTES, BIG_BYTES = 1_000_000, 500_000_000
LOW_COVER_HEIGHT = 800  # pixels
SIMILARITY = {"Strict (same cover)": 4, "Normal": 8, "Loose (more matches)": 12}
EXTRA_WORDS = re.compile(r"\b(annuals?|specials?|one[- ]?shots?|giant|king[- ]size)\b", re.I)


# ---------- 1. integrity ----------

def test_rar(path):
    """Run the extractor's own test command. Returns a list of problems (empty when it passes)."""
    exe = find_extractor()
    if not exe:
        return ["No RAR extractor found, so this file could not be tested"]
    name = Path(exe).stem.lower()
    if name.startswith("7z"):
        cmd = [exe, "t", "-y", str(path)]
    elif name == "unrar":
        cmd = [exe, "t", str(path)]
    else:
        cmd = [exe, "-tf", str(path)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=600)
    except (OSError, subprocess.SubprocessError) as e:
        return [f"Could not run the extractor ({type(e).__name__})"]
    if r.returncode != 0:
        tail = " ".join((r.stderr.strip() or r.stdout.strip()).split())[-120:]
        return [f"Archive test failed: {tail}" if tail else "Archive test failed"]
    return []


def check_integrity(path):
    """Full check of one comic: zip CRC test, at least one page, and cover/middle/last pages must decode.
    Real RAR files are checked with the extractor's test command. Returns a list of problems."""
    path = Path(path)
    if not zipfile.is_zipfile(path):
        if path.suffix.lower() == ".cbz":
            return ["Not a valid zip (may be a misnamed RAR)"]
        return test_rar(path)
    problems = []
    try:
        with zipfile.ZipFile(path) as z:
            bad = z.testzip()
            if bad:
                problems.append(f"Corrupt entry: {bad}")
            pages = sorted((n for n in z.namelist() if is_page(n)), key=natural_key)
            if not pages:
                problems.append("No images found")
            for idx in sorted({0, len(pages) // 2, len(pages) - 1} if pages else ()):
                try:
                    Image.open(io.BytesIO(z.read(pages[idx]))).load()
                except Exception:  # noqa: BLE001 - Pillow and zlib raise many things for damaged data
                    problems.append(f"Unreadable page: {pages[idx]}")
    except zipfile.BadZipFile:
        problems.append("Not a valid zip")
    except OSError as e:
        problems.append(f"Could not read the file ({e.__class__.__name__})")
    return problems


# ---------- 2. duplicates ----------

def _series_key(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def _issue_key(i):
    m = re.fullmatch(r"0*(\d+)(\.\d+)?", (i or "").strip())
    return m.group(1) + (m.group(2) or "") if m else (i or "").strip().lower()


def _collected(issue):
    return bool(issue.info.get("collected"))


def keeper_rank(i):
    """Sort key that puts the best copy first: more pages, then a taller cover, then the larger file."""
    return (-(i.pages or 0), -(i.cover_h or 0), -i.size, natural_key(i.rel))


@dataclass
class Group:
    tier: int  # 1 same series/volume/issue, 2 identical size, 3 similar cover
    why: str
    issues: list = field(default_factory=list)  # best copy (the one to keep) first


def _identity(issue):
    """What a comic is, for tier 1: a single issue is its series, volume, issue number and kind (so an Annual is
    not a copy of the issue with the same number); a collected edition is its series, volume, format and range.
    A single issue and a collected edition never share an identity, so a TPB is not a copy of its issues."""
    f = issue.info
    if not f.get("series"):
        return None
    if f.get("collected"):
        if not (f.get("volume") or f.get("range")):
            return None
        return ("c", _series_key(f["series"]), f.get("volume") or "", f.get("format") or f.get("kind") or "",
                f.get("range") or "")
    if not f.get("issue"):
        return None
    return ("i", _series_key(f["series"]), f.get("volume") or "", _issue_key(f["issue"]), f.get("kind") or "")


def _same_class(members):
    """Split `members` into all-singles and all-collected lists; drop lists of one."""
    singles = [m for m in members if not _collected(m)]
    coll = [m for m in members if _collected(m)]
    return [g for g in (singles, coll) if len(g) > 1]


def find_duplicates(issues, similar=False, threshold=8, orders=None):
    """Groups of probable duplicates, strongest evidence first. A group whose files are all already in an
    earlier group is dropped. Within a group the best copy (see `keeper_rank`) is listed first, except that a copy
    inside a reading-order folder (`orders`, see `reading_orders.py`) never outranks one outside: the outside copy is
    the original. A single issue and a collected edition are never grouped together."""
    groups = []
    by_id = {}
    for i in issues:
        key = _identity(i)
        if key:
            by_id.setdefault(key, []).append(i)
    groups += [Group(1, "Same series, volume and issue", v) for v in by_id.values() if len(v) > 1]

    by_size = {}
    for i in issues:
        if i.size > 0:
            by_size.setdefault(i.size, []).append(i)
    groups += [Group(2, "Identical file size", g) for v in by_size.values() for g in _same_class(v)]

    if similar:
        hashed = [i for i in issues if i.cover_hash]
        parent = list(range(len(hashed)))

        def root(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        vals = [int(i.cover_hash, 16) for i in hashed]
        worst = {}
        for a in range(len(hashed)):
            for b in range(a + 1, len(hashed)):
                if _collected(hashed[a]) != _collected(hashed[b]):
                    continue
                d = bin(vals[a] ^ vals[b]).count("1")
                if d <= threshold:
                    ra, rb = root(a), root(b)
                    if ra != rb:
                        parent[rb] = ra
                    worst[a] = max(worst.get(a, 0), d)
                    worst[b] = max(worst.get(b, 0), d)
        clusters = {}
        for k in range(len(hashed)):
            clusters.setdefault(root(k), []).append(k)
        for members in clusters.values():
            if len(members) > 1:
                far = max(worst.get(k, 0) for k in members)
                groups.append(Group(3, f"Similar cover ({far} of 64 bits differ at most)", [hashed[k] for k in members]))

    out, seen = [], []
    for g in groups:
        ids = {str(i.path).lower() for i in g.issues}
        if any(ids <= s for s in seen):
            continue
        seen.append(ids)
        g.issues.sort(key=lambda i: (bool(orders and orders.covers(i.path)),) + keeper_rank(i))
        out.append(g)
    return out


def duplicates_for(issues, orders, include=False, similar=False, threshold=8):
    """(groups, left_out): the duplicate groups, with the comics in marked reading-order folders left out unless
    `include` is set, and how many comics were left out. Reading-order folders hold deliberate copies, so by default
    they are not reported as duplicates of the real library."""
    if include or not orders or not len(orders):
        return find_duplicates(issues, similar, threshold, orders), 0
    real, copies = orders.split(issues)
    return find_duplicates(real, similar, threshold, orders), len(copies)


def reading_order_rows(issues, orders):
    """[(folder, members, elsewhere)] for every marked reading-order folder that holds comics: `elsewhere` counts the
    members that also exist outside any reading-order folder (same series, volume and issue)."""
    if not orders or not len(orders):
        return []
    real, copies = orders.split(issues)
    known = {k for k in map(_identity, real) if k}
    by_folder = {}
    for i in copies:
        by_folder.setdefault(orders.which(i.path), []).append(i)
    out = []
    for folder, members in by_folder.items():
        out.append((folder, members, sum(1 for m in members if _identity(m) in known)))
    return sorted(out, key=lambda t: str(t[0]).lower())


# ---------- 3. missing issues ----------

@dataclass
class Gap:
    series: str
    volume: str
    owned: int
    first: int
    last: int
    missing: list
    from_count: bool  # the end of the range came from ComicInfo Count
    kind: str = "Issue"  # "Issue" (issue numbers) or a collected format such as "TPB" (volume numbers)


def ranges(nums, prefix="#"):
    """[13, 27, 28, 29] -> '#13, #27-#29'; with prefix="" -> '13, 27-29'"""
    out, nums = [], sorted(nums)
    k = 0
    while k < len(nums):
        j = k
        while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
            j += 1
        out.append(f"{prefix}{nums[k]}" if j == k else f"{prefix}{nums[k]}-{prefix}{nums[j]}")
        k = j + 1
    return ", ".join(out)


def find_missing(issues, from_one=False):
    """Gaps in each series/volume (issue numbers) and in each series' collected editions of one format (volume
    numbers, e.g. TPB vols 3 and 5 when 1, 2, 4 and 6 are owned). Returns (gaps, ignored) where `ignored` counts
    files with nothing to track (specials, decimals, unparsed names, collected editions with no volume number).
    Annual/special/one-shot series are skipped as extras."""
    groups, vols, ignored = {}, {}, 0
    for i in issues:
        f = i.info
        if not f.get("series") or EXTRA_WORDS.search(f["series"]) or EXTRA_WORDS.search(i.path.stem):
            ignored += 1
            continue
        if f.get("collected"):
            num = (f.get("volume") or "").strip()
            if not re.fullmatch(r"\d+", num) or f.get("range"):
                ignored += 1
                continue
            kind = f.get("format") or f.get("kind") or "Volume"
            g = vols.setdefault((_series_key(f["series"]), kind), {"series": f["series"], "kind": kind, "nums": set()})
            g["nums"].add(int(num))
            continue
        num = (f.get("issue") or "").strip()
        if not re.fullmatch(r"\d+", num):
            ignored += 1
            continue
        key = (_series_key(f["series"]), f.get("volume") or "")
        g = groups.setdefault(key, {"series": f["series"], "volume": f.get("volume") or "", "nums": set(), "count": 0})
        g["nums"].add(int(num))
        try:
            g["count"] = max(g["count"], int(f.get("count") or 0))
        except ValueError:
            pass
    gaps = []
    for g in groups.values():
        nums = g["nums"]
        first = 1 if from_one else min(nums)
        last = max(max(nums), g["count"])
        missing = [n for n in range(first, last + 1) if n not in nums and n > 0]
        if missing:
            gaps.append(Gap(g["series"], g["volume"], len(nums), first, last, missing, g["count"] > max(nums)))
    for g in vols.values():
        nums = g["nums"]
        first = 1 if from_one else min(nums)
        missing = [n for n in range(first, max(nums) + 1) if n not in nums and n > 0]
        if missing:
            gaps.append(Gap(g["series"], "", len(nums), first, max(nums), missing, False, g["kind"]))
    gaps.sort(key=lambda g: (natural_key(g.series + g.volume), g.kind != "Issue", g.kind))
    return gaps, ignored


def gap_name(g):
    return g.series + (f" v{g.volume}" if g.volume else "")


def gap_text(g, skip=()):
    """'Issues: #13, #27-#29' or 'TPB vols: 3, 5'; numbers in `skip` (ignored ones) are left out. '' if none left."""
    nums = [n for n in g.missing if n not in skip]
    if not nums:
        return ""
    if g.kind == "Issue":
        return f"Issues{f' (v{g.volume})' if g.volume else ''}: {ranges(nums)}"
    return f"{g.kind} vols: {ranges(nums, '')}"


def missing_by_series(gaps, skip=lambda g: ()):
    """[(series, [gap, ...])] with one entry per series, in order. `skip(gap)` gives numbers to leave out."""
    out = {}
    for g in gaps:
        if gap_text(g, skip(g)):
            out.setdefault(_series_key(g.series), (g.series, []))[1].append(g)
    return list(out.values())


def wishlist_lines(gaps):
    return [f"{gap_name(g)} #{n}" if g.kind == "Issue" else f"{g.series} {g.kind} vol {n}"
            for g in gaps for n in g.missing]


# ---------- 4. warnings (quality), junk and CBR ----------

DEFAULT_LIMITS = {"min_pages": MIN_PAGES, "max_pages": MAX_PAGES, "small_mb": SMALL_BYTES / 1_000_000,
                  "big_mb": BIG_BYTES / 1_000_000, "low_cover": LOW_COVER_HEIGHT}


def limits_from(o):
    """Warning limits from option values (text or numbers); anything unreadable falls back to the default."""
    out = {}
    for k, d in DEFAULT_LIMITS.items():
        try:
            v = float(str(o.get(k, d)).strip())
            out[k] = v if v >= 0 else d
        except ValueError:
            out[k] = d
    return out


def quality_flags(issue, limits=None):
    lim = {**DEFAULT_LIMITS, **(limits or {})}
    small, big = lim["small_mb"] * 1_000_000, lim["big_mb"] * 1_000_000
    flags = []
    if issue.pages is not None and issue.pages > 0:
        if issue.pages < lim["min_pages"]:
            flags.append(f"Only {issue.pages} pages")
        elif issue.pages > lim["max_pages"]:
            flags.append(f"{issue.pages} pages")
    if 0 < issue.size < small:
        flags.append(f"Very small file ({issue.size / 1e6:.1f} MB)")
    elif big and issue.size > big:
        flags.append(f"Very large file ({issue.size / 1e6:.0f} MB)")
    if issue.cover_h and issue.cover_h < lim["low_cover"]:
        flags.append(f"Low-res cover ({issue.cover_w}x{issue.cover_h})")
    return flags


def find_quality(issues, limits=None):
    return [(i, f) for i in issues if (f := quality_flags(i, limits))]


def find_junk(issues):
    """[(issue, [junk file names])] for zip-based comics that hold non-image files other than ComicInfo.xml."""
    return [(i, i.junk) for i in issues if i.junk]


def find_cbr(issues):
    return [i for i in issues if i.ext == ".cbr"]


def size_text(n):
    return f"{n / 1e6:.1f} MB" if n >= 1e6 else f"{n / 1e3:.0f} KB"


# ---------- 5. findings: one list for the page ----------

BROKEN, DUPLICATE, MISSING, JUNK, CBR, WARNING = "Broken", "Duplicate", "Missing", "Junk", "CBR", "Warning"
ORDER = "Reading order"   # folders of reading-order copies: shown for information, nothing to fix
KINDS = [BROKEN, DUPLICATE, MISSING, JUNK, CBR, WARNING, ORDER]
ARCHIVE, CLEAN, CONVERT = "archive", "clean", "convert"  # what fixing a finding does


@dataclass
class Finding:
    kind: str
    title: str  # the file, or the series for Missing
    detail: str
    key: str  # what Ignore remembers
    label: str  # how an ignored finding is described when reviewing the ignore list
    path: Path = None
    fix: str = None  # ARCHIVE | CLEAN | CONVERT, or None when there is nothing to do automatically
    checked: bool = False
    group: int = 0
    keep: bool = False  # the best copy of a duplicate group: shown, never moved
    gaps: list = field(default_factory=list)  # Missing: the gaps shown on this row (for the wishlist)
    keys: list = field(default_factory=list)  # every ignore key this row stands for (Missing: one per number)
    count: int = 1  # how many comics the row stands for (Reading order: the comics in the folder)


def _pkey(prefix, path):
    return f"{prefix}|{str(path).lower()}"


def missing_key(g, n):
    return f"missing|{_series_key(g.series)}|{g.volume}|{g.kind}|{n}"


def build_findings(data, ignored=()):
    """Findings from the scan results `data` ({broken, dups, gaps, junk, cbr, quality}), without those whose key is
    in `ignored`. Junk and CBR findings come pre-ticked; everything else waits for a deliberate tick."""
    ignored = set(ignored)
    out = []
    for i, problems in data["broken"]:
        k = _pkey("broken", i.path)
        if k not in ignored:
            out.append(Finding(BROKEN, i.rel, "; ".join(problems), k, f"Broken: {i.rel}", i.path, ARCHIVE, keys=[k]))
    for gi, g in enumerate(data["dups"], 1):
        k = "dup|" + "|".join(sorted(str(i.path).lower() for i in g.issues))
        if k in ignored:
            continue
        best = g.issues[0]
        for n, i in enumerate(g.issues):
            detail = f"Group {gi} · {g.why} · " + ("best copy, kept" if n == 0 else f"copy of {best.path.name}")
            out.append(Finding(DUPLICATE, i.rel, detail, k, f"Duplicates: {best.rel} and {len(g.issues) - 1} more",
                               i.path, None if n == 0 else ARCHIVE, False, gi, keep=n == 0, keys=[k]))

    def skip(g):
        return {n for n in g.missing if missing_key(g, n) in ignored}

    for series, gs in missing_by_series(data["gaps"], skip):
        parts = [gap_text(g, skip(g)) for g in gs]
        keys = [missing_key(g, n) for g in gs for n in g.missing if n not in skip(g)]
        out.append(Finding(MISSING, series, " · ".join(p for p in parts if p), keys[0],
                           f"Missing from {series}: " + " · ".join(p for p in parts if p), gaps=gs, keys=keys))
    for i, names in data.get("junk", []):
        k = _pkey("junk", i.path)
        if k not in ignored:
            shown = ", ".join(names[:3]) + (f" and {len(names) - 3} more" if len(names) > 3 else "")
            out.append(Finding(JUNK, i.rel, f"{len(names)} junk file{'s' if len(names) != 1 else ''}: {shown}", k,
                               f"Junk files in {i.rel}", i.path, CLEAN, True, keys=[k]))
    for i in data.get("cbr", []):
        k = _pkey("cbr", i.path)
        if k not in ignored:
            out.append(Finding(CBR, i.rel, "RAR comic: convert to CBZ so every reader opens it", k,
                               f"CBR left as is: {i.rel}", i.path, CONVERT, True, keys=[k]))
    for i, flags in data.get("quality", []):
        k = _pkey("warn", i.path)
        if k not in ignored:
            out.append(Finding(WARNING, i.rel, " · ".join(flags), k, f"Warning: {i.rel}", i.path, keys=[k]))
    for folder, members, elsewhere in data.get("orders", []):
        k = _pkey("order", folder)
        if k not in ignored:
            detail = f"{len(members)} comic{'s' if len(members) != 1 else ''}"
            detail += (f" · {elsewhere} also in your library outside it" if elsewhere else " · none of them elsewhere in your library")
            out.append(Finding(ORDER, str(folder), detail, k, f"Reading order folder: {folder}", Path(folder), keys=[k],
                               count=len(members)))
    return out


def plan_fixes(findings):
    """[(path, action, [findings])] for the ticked findings. One action per file, strongest first: moving a file to
    Archive beats converting it, and converting it already cleans it."""
    by_path = {}
    for f in findings:
        if f.checked and f.fix and f.path:
            by_path.setdefault(str(f.path).lower(), (f.path, {}))[1].setdefault(f.fix, []).append(f)
    out = []
    for path, actions in by_path.values():
        for action in (ARCHIVE, CONVERT, CLEAN):
            if action in actions:
                out.append((path, action, [f for fs in actions.values() for f in fs]))
                break
    return out


def plan_lines(plan):
    """The summary lines for a fix plan [(path, action, findings)]: what will happen, by kind."""
    n = {a: sum(1 for _, x, _ in plan if x == a) for a in (CLEAN, CONVERT, ARCHIVE)}
    plural = lambda k, w: f"{k} {w}{'s' if k != 1 else ''}"  # noqa: E731
    lines = []
    if n[CLEAN]:
        lines.append(f"Remove junk files from {plural(n[CLEAN], 'comic')}")
    if n[CONVERT]:
        lines.append(f"Convert {plural(n[CONVERT], 'CBR file')} to CBZ (each .cbr is deleted once its CBZ has been verified)")
    if n[ARCHIVE]:
        lines.append(f"Move {plural(n[ARCHIVE], 'file')} to Archive folders (as .bak)")
    return lines


def describe_plan(plan, root=None):
    """[(file, where it goes, can it be undone)] for every file in a fix plan, for the confirmation's details."""
    out = []
    for path, action, _ in plan:
        path = Path(path)
        name = str(path.relative_to(root)) if root and Path(root) in path.parents else path.name
        if action == ARCHIVE:
            out.append((name, f"moved to {ARCHIVE_DIR}\\{path.name}.bak", True))
        elif action == CONVERT:
            out.append((name, f"becomes {path.with_suffix('.cbz').name}; the .cbr is deleted after the check", False))
        else:
            out.append((name, "junk files removed, rewritten in place", False))
    return out


def apply_fix(path, action):
    """Do one fix on one file. Returns a short description; raises on failure (the file is then left as it was)."""
    path = Path(path)
    if action == ARCHIVE:
        move_to_archive(path)
        return f"{path.name} moved to Archive"
    if action == CLEAN:
        plan = plan_cleanup(path, True, "", KEEP_NAMES)
        if plan["changed"]:
            apply_cleanup(path, plan, backup=False)
        return f"{path.name} cleaned ({len(plan['remove'])} removed)"
    if action == CONVERT:
        dest = path.with_suffix(".cbz")
        if dest.exists():
            raise RuntimeError(f"{dest.name} already exists")
        convert_to_cbz(path, dest)
        try:  # the new file gets its junk removed too
            plan = plan_cleanup(dest, True, "", KEEP_NAMES)
            if plan["changed"]:
                apply_cleanup(dest, plan, backup=False)
        except ValueError:
            pass
        dispose_original(path, DELETE)  # only reached once the new file has been verified
        return f"{path.name} converted to {dest.name}"
    raise ValueError(f"Unknown fix: {action}")


# ---------- 6. the Archive folders ----------

def archive_files(root):
    """Every file inside the Archive folders under `root`, as [(path, size)]."""
    out = []
    for d in Path(root).rglob(ARCHIVE_DIR):
        if d.is_dir():
            out += [(p, p.stat().st_size) for p in d.rglob("*") if p.is_file()]
    return sorted(out, key=lambda t: natural_key(str(t[0])))


def purge_archive(paths):
    """Permanently delete `paths`, then any Archive folder left empty. Returns (deleted, [errors])."""
    done, errors, dirs = 0, [], set()
    for p in map(Path, paths):
        try:
            p.unlink()
            done += 1
            dirs.add(p.parent)
        except OSError as e:
            errors.append(f"{p.name}: {e}")
    for d in dirs:
        try:
            d.rmdir()
        except OSError:
            pass
    return done, errors


# ---------- 7. the details panel ----------

def build_details(res, counts, ignored=0, with_orders=False, checks=None):
    """What the Details panel shows, as plain data. `res` is a scan result of the audit page, `counts` the number of
    findings per kind ({kind: n}), `checks` the kinds that are switched on. Returns
    {"scan": [(label, text)], "found": [{kind, title, text, actions: [(button, action)]}]}; the page decides what
    each action does ("show:<kind>" selects that list, "tool:<page>[:<view>]" opens another tool)."""
    checks = set(KINDS if checks is None else checks)
    issues = res["issues"]
    n = len(issues)
    scan = [("Comics scanned", f"{n:,} in {res['seconds']:.1f}s" + (f" ({res['cache_hits']:,} from cache)" if res.get("cache_hits") else "")
             + (" · stopped early, so this is partial" if res.get("stopped") else ""))]
    scan.append(("Checks on", ", ".join(k for k in (BROKEN, DUPLICATE, MISSING, JUNK, CBR, WARNING) if k in checks) or "none"))
    scan.append(("Integrity test", "on: every file was read completely" if res.get("integrity")
                 else "off: only problems the scan noticed (a bad zip, no images, an unreadable cover)"))
    raw = sum(1 for i in issues if i.ext == ".cbr" and not i.ci_read)
    if raw:
        scan.append(("Real .cbr files", f"{raw:,} not opened (they count as CBR files but are not checked for junk or pages)"))
    left = res.get("left_out", 0)
    scan.append(("Reading orders", f"{left:,} comic{'s' if left != 1 else ''} left out of Duplicates" if left else
                 ("included in Duplicates" if with_orders else "none left out")))
    scan.append(("Ignored by you", f"{ignored:,} finding{'s' if ignored != 1 else ''}"))

    def many(k, one, more=None):
        return f"{k:,} {one if k == 1 else (more or one + 's')}"

    found = []
    if BROKEN in checks:
        found.append({"kind": BROKEN, "title": many(counts[BROKEN], "broken file"),
                      "text": "Files that would not open or failed the test. Fixing one moves it to an Archive folder as .bak; it is not deleted.",
                      "actions": [("Show in list", "show:" + BROKEN)]})
    if DUPLICATE in checks:
        found.append({"kind": DUPLICATE, "title": many(counts[DUPLICATE], "group of duplicates", "groups of duplicates"),
                      "text": "The best copy of each group is kept; tick the others to move them to Archive as .bak. "
                              "To mark folders of deliberate copies so they are left out, use Library stats.",
                      "actions": [("Show in list", "show:" + DUPLICATE), ("Mark reading orders", "tool:stats")]})
    if MISSING in checks:
        found.append({"kind": MISSING, "title": many(counts[MISSING], "series with gaps", "series with gaps"),
                      "text": "Numbers missing between the lowest and highest you own. The wishlist copies or saves them.",
                      "actions": [("Show in list", "show:" + MISSING)]})
    if JUNK in checks:
        found.append({"kind": JUNK, "title": many(counts[JUNK], "comic with junk", "comics with junk"),
                      "text": "Thumbs.db, .nfo, __MACOSX and the like inside the archive. Fixing rewrites the archive without them.",
                      "actions": [("Show in list", "show:" + JUNK)]})
    if CBR in checks:
        found.append({"kind": CBR, "title": many(counts[CBR], "CBR file"),
                      "text": "RAR comics. Converting makes a verified CBZ every reader opens; the CBR tool does it in bulk.",
                      "actions": [("Show in list", "show:" + CBR), ("Convert in bulk", "tool:convert")]})
    if WARNING in checks:
        found.append({"kind": WARNING, "title": many(counts[WARNING], "warning"),
                      "text": "Unusual page counts, sizes or cover heights. Nothing to fix automatically.",
                      "actions": [("Show in list", "show:" + WARNING), ("View stats", "tool:stats")]})
    no_series = sum(1 for i in issues if not i.info.get("series"))
    no_issue = sum(1 for i in issues if i.info.get("series") and not i.info.get("collected") and not i.info.get("issue"))
    if no_series or no_issue:
        acts = ([("Comics with no series", "tool:metadata:no_series")] if no_series else []) + \
               ([("Comics with no issue number", "tool:metadata:no_issue")] if no_issue else [])
        found.append({"kind": "Metadata", "title": f"{no_series:,} with no series · {no_issue:,} with no issue number",
                      "text": "The audit cannot judge duplicates or gaps for these. Fill them in with the Metadata tool.",
                      "actions": acts})
    return {"scan": scan, "found": found}

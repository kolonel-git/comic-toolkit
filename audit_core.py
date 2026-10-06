"""Library audit logic: integrity checks, duplicates, missing issues and quality flags. No UI code.

Everything here works on the `Issue` records from `library_scan`. Nothing in this module changes
a file: the audit tool decides what to do with a report.
"""
from __future__ import annotations

import io
import re
import subprocess
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image

from comic_core import find_extractor, is_page, natural_key

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


@dataclass
class Group:
    tier: int  # 1 same series/volume/issue, 2 identical size, 3 similar cover
    why: str
    issues: list = field(default_factory=list)


def find_duplicates(issues, similar=False, threshold=8):
    """Groups of probable duplicates, strongest evidence first. A group whose files are all already in an
    earlier group is dropped. Within a group the biggest file is listed first."""
    groups = []
    by_id = {}
    for i in issues:
        f = i.info
        if f.get("series") and f.get("issue"):
            by_id.setdefault((_series_key(f["series"]), f.get("volume") or "", _issue_key(f["issue"])), []).append(i)
    groups += [Group(1, "Same series, volume and issue", v) for v in by_id.values() if len(v) > 1]

    by_size = {}
    for i in issues:
        if i.size > 0:
            by_size.setdefault(i.size, []).append(i)
    groups += [Group(2, "Identical file size", v) for v in by_size.values() if len(v) > 1]

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
        g.issues.sort(key=lambda i: (-i.size, natural_key(i.rel)))
        out.append(g)
    return out


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


def ranges(nums):
    """[13, 27, 28, 29] -> '#13, #27-#29'"""
    out, nums = [], sorted(nums)
    k = 0
    while k < len(nums):
        j = k
        while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
            j += 1
        out.append(f"#{nums[k]}" if j == k else f"#{nums[k]}-#{nums[j]}")
        k = j + 1
    return ", ".join(out)


def find_missing(issues, from_one=False):
    """Gaps in each series/volume. Returns (gaps, ignored) where `ignored` counts files with no whole issue
    number (specials, decimals, unparsed names). Annual/special/one-shot series are skipped as extras."""
    groups, ignored = {}, 0
    for i in issues:
        f = i.info
        if not f.get("series") or EXTRA_WORDS.search(f["series"]) or EXTRA_WORDS.search(i.path.stem):
            ignored += 1
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
    gaps.sort(key=lambda g: natural_key(g.series + g.volume))
    return gaps, ignored


def gap_name(g):
    return g.series + (f" v{g.volume}" if g.volume else "")


def wishlist_lines(gaps):
    return [f"{gap_name(g)} #{n}" for g in gaps for n in g.missing]


# ---------- 4. quality ----------

def quality_flags(issue, min_pages=MIN_PAGES, max_pages=MAX_PAGES):
    flags = []
    if issue.pages is not None and issue.pages > 0:
        if issue.pages < min_pages:
            flags.append(f"Only {issue.pages} pages")
        elif issue.pages > max_pages:
            flags.append(f"{issue.pages} pages")
    if 0 < issue.size < SMALL_BYTES:
        flags.append(f"Very small file ({issue.size / 1e6:.1f} MB)")
    elif issue.size > BIG_BYTES:
        flags.append(f"Very large file ({issue.size / 1e6:.0f} MB)")
    if issue.cover_h and issue.cover_h < LOW_COVER_HEIGHT:
        flags.append(f"Low-resolution cover ({issue.cover_w}x{issue.cover_h})")
    return flags


def find_quality(issues):
    return [(i, f) for i in issues if (f := quality_flags(i))]


def size_text(n):
    return f"{n / 1e6:.1f} MB" if n >= 1e6 else f"{n / 1e3:.0f} KB"

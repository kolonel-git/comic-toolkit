"""Shared library scan: walk a folder and describe every comic in it. No UI code.

One pass produces an `Issue` per file: path, size, modified time, fields parsed from the filename,
`ComicInfo.xml` fields, and (in deep mode) page count, cover size and a cover hash. Later tools
(audit, stats, browser, watcher) read these records instead of each walking the library themselves.

Results are cached in `%APPDATA%\\ComicToolkit\\cache.json`, keyed by path and checked against size and
modified time. The cache is disposable: deleting it only makes the next scan slower, and nothing is ever
read from it that the file itself contradicts. Run `python library_scan.py FOLDER` for a text report.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import sys
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image

from comic_core import Comic, is_page, natural_key
from rename_core import find_files, merge, parse_filename, read_comicinfo

CACHE_VERSION = 1
HASH_SIZE = 8  # dHash: 8x8 comparisons -> 64 bits -> 16 hex characters


def default_cache_path():
    base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    return Path(base) / "ComicToolkit" / "cache.json"


@dataclass
class Issue:
    path: Path
    rel: str  # path relative to the scanned root, forward slashes
    size: int
    mtime: float
    parsed: dict  # from the filename
    ci: dict = field(default_factory=dict)  # from ComicInfo.xml ({} when missing or not read)
    ci_read: bool = False  # False when a RAR was skipped, so an empty `ci` means "unknown"
    deep: bool = False  # page count / cover info were read
    pages: int | None = None
    cover_w: int | None = None
    cover_h: int | None = None
    cover_hash: str | None = None
    error: str | None = None  # why deep reading failed (no images, bad cover, ...)

    @property
    def info(self):
        """Filename fields overridden by `ComicInfo.xml` fields where present."""
        return merge(self.parsed, self.ci, True)

    @property
    def ext(self):
        return self.path.suffix.lower()


@dataclass
class ScanResult:
    root: Path
    issues: list
    cache_hits: int = 0
    read: int = 0  # files actually opened this run
    stopped: bool = False
    seconds: float = 0.0


# ---------- cover hash ----------

def cover_hash(img):
    """Difference hash of a PIL image: robust to resizing and re-compression."""
    if hasattr(img, "draft"):
        img.draft("L", (64, 64))  # JPEG: decode small, much faster
    px = list(img.convert("L").resize((HASH_SIZE + 1, HASH_SIZE), Image.LANCZOS).getdata())
    bits = 0
    for row in range(HASH_SIZE):
        for col in range(HASH_SIZE):
            bits = (bits << 1) | (px[row * (HASH_SIZE + 1) + col] > px[row * (HASH_SIZE + 1) + col + 1])
    return f"{bits:016x}"


def hash_distance(a, b):
    """Number of differing bits between two cover hashes (0 = identical; under ~10 = likely the same cover)."""
    return bin(int(a, 16) ^ int(b, 16)).count("1")


def _cover_info(data):
    img = Image.open(io.BytesIO(data))
    w, h = img.size
    return w, h, cover_hash(img)


# ---------- reading one file ----------

def _deep_read(issue, deep_cbr):
    """Fill pages / cover fields. Zip-based files are read in place; real RAR only when `deep_cbr`."""
    try:
        if zipfile.is_zipfile(issue.path):
            with zipfile.ZipFile(issue.path) as z:
                pages = sorted((n for n in z.namelist() if is_page(n)), key=natural_key)
                data = z.read(pages[0]) if pages else None
        elif deep_cbr:
            comic = Comic(issue.path)
            try:
                pages, data = comic.pages, comic.read(comic.pages[0])
            finally:
                comic.close()
        elif issue.ext == ".cbz":
            raise zipfile.BadZipFile  # a .cbz that isn't a zip is wrong (or a misnamed RAR): flag it
        else:
            return  # .cbr that is a real RAR, and not asked to open it: leave everything unknown
        issue.deep = True
        issue.pages = len(pages)
        if not pages:
            issue.error = "No images found"
            return
        try:
            issue.cover_w, issue.cover_h, issue.cover_hash = _cover_info(data)
        except Exception as e:  # noqa: BLE001 - Pillow raises many things for bad images
            issue.error = f"Cover unreadable ({type(e).__name__})"
    except zipfile.BadZipFile:
        issue.deep, issue.error = True, "Not a valid zip"
    except Exception as e:  # noqa: BLE001 - corrupt or unreadable archives fail in many ways
        issue.deep, issue.error = True, " ".join(str(e).split()) or type(e).__name__  # one line, for tables and CSV


def _read_file(path, root, deep, deep_cbr):
    st = path.stat()
    issue = Issue(path, path.relative_to(root).as_posix(), st.st_size, st.st_mtime, parse_filename(path.stem))
    if path.suffix.lower() in {".cbz", ".cbr"}:
        if zipfile.is_zipfile(path):
            issue.ci, issue.ci_read = read_comicinfo(path), True
        elif deep_cbr:  # real RAR: reading ComicInfo.xml spawns the extractor, so only when asked
            issue.ci, issue.ci_read = read_comicinfo(path), True
    if deep and path.suffix.lower() in {".cbz", ".cbr"}:
        _deep_read(issue, deep_cbr)
    return issue


# ---------- cache ----------

def _load_cache(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return data["entries"] if data.get("version") == CACHE_VERSION else {}
    except (OSError, ValueError, KeyError, AttributeError):
        return {}


def _save_cache(path, entries):
    path = Path(path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(json.dumps({"version": CACHE_VERSION, "entries": entries}), encoding="utf-8")
        tmp.replace(path)
    except OSError:
        pass  # a cache that can't be written is just a slower next scan


def _key(p):
    return str(p).lower()


def _from_cache(entry, issue):
    issue.ci, issue.ci_read = entry["ci"], entry["ci_read"]
    issue.deep, issue.pages, issue.error = entry["deep"], entry["pages"], entry["error"]
    issue.cover_w, issue.cover_h, issue.cover_hash = entry["cover_w"], entry["cover_h"], entry["cover_hash"]


def _to_cache(issue):
    return {"size": issue.size, "mtime": issue.mtime, "ci": issue.ci, "ci_read": issue.ci_read,
            "deep": issue.deep, "pages": issue.pages, "error": issue.error, "cover_w": issue.cover_w,
            "cover_h": issue.cover_h, "cover_hash": issue.cover_hash}


def _usable(entry, st, issue_path, deep, deep_cbr):
    """A cached entry is reused only if the file is unchanged and it holds at least what is being asked for."""
    if entry.get("size") != st.st_size or entry.get("mtime") != st.st_mtime:
        return False
    if deep and not entry.get("deep") and issue_path.suffix.lower() in {".cbz", ".cbr"}:
        # a light entry can't answer a deep question, unless it is a real-RAR .cbr that deep mode would skip anyway
        if deep_cbr or issue_path.suffix.lower() == ".cbz" or zipfile.is_zipfile(issue_path):
            return False
    if deep_cbr and not entry.get("ci_read") and not zipfile.is_zipfile(issue_path):
        return False
    return True


# ---------- the scan ----------

def scan_library(root, recursive=True, deep=False, deep_cbr=False, include_other=False,
                 use_cache=True, cache_path=None, progress=None, stop=None):
    """Scan `root` and return a ScanResult. Safe to call from a worker thread (no UI calls).

    deep      also read page count, cover size and cover hash (CBZ and zip-backed CBR)
    deep_cbr  with deep, also open real RAR files (slow: the whole archive is extracted)
    progress  optional callback(done, total, issue)
    stop      optional threading.Event; set it to end the scan early (partial result, `stopped=True`)
    """
    t0 = time.time()
    root = Path(root)
    cache_path = Path(cache_path) if cache_path else default_cache_path()
    entries = _load_cache(cache_path) if use_cache else {}
    files = find_files(root, recursive, include_other)
    result = ScanResult(root, [])
    seen = set()
    for k, p in enumerate(files):
        if stop is not None and stop.is_set():
            result.stopped = True
            break
        try:
            st = p.stat()
            entry = entries.get(_key(p))
            if entry and _usable(entry, st, p, deep, deep_cbr):
                issue = Issue(p, p.relative_to(root).as_posix(), st.st_size, st.st_mtime, parse_filename(p.stem))
                _from_cache(entry, issue)
                result.cache_hits += 1
            else:
                issue = _read_file(p, root, deep, deep_cbr)
                result.read += 1
                entries[_key(p)] = _to_cache(issue)
        except OSError as e:  # vanished or locked mid-scan
            issue = Issue(p, p.relative_to(root).as_posix(), 0, 0.0, parse_filename(p.stem), error=str(e))
        seen.add(_key(p))
        result.issues.append(issue)
        if progress:
            progress(k + 1, len(files), issue)
    if use_cache:
        if not result.stopped:  # forget files that no longer exist under this root
            prefix = _key(root).rstrip("\\/") + os.sep  # the separator stops "Comics" matching "Comics Old"
            entries = {k: v for k, v in entries.items() if not k.startswith(prefix) or k in seen}
        _save_cache(cache_path, entries)
    result.seconds = time.time() - t0
    return result


# ---------- command line ----------

def _cell(v):
    return "" if v is None else str(v)


def _rows(issues):
    for i in issues:
        f = i.info
        yield [i.rel, i.size, f.get("series"), f.get("volume"), f.get("issue"), f.get("year"), f.get("count"),
               i.pages, f"{i.cover_w}x{i.cover_h}" if i.cover_w else None, i.cover_hash, i.error]


HEADER = ["file", "bytes", "series", "volume", "issue", "year", "count", "pages", "cover", "cover_hash", "error"]


def main(argv=None):
    ap = argparse.ArgumentParser(description="Scan a comic library and report what was found.")
    ap.add_argument("folder")
    ap.add_argument("--deep", action="store_true", help="read page counts and cover hashes")
    ap.add_argument("--deep-cbr", action="store_true", help="with --deep, also open real RAR files (slow)")
    ap.add_argument("--no-recursive", action="store_true")
    ap.add_argument("--no-cache", action="store_true", help="ignore and do not write the cache")
    ap.add_argument("--cache-file", help="use this cache file instead of the default")
    ap.add_argument("--csv", metavar="FILE", help="also write the full table to a CSV file")
    ap.add_argument("--limit", type=int, default=40, help="rows to print (default 40; 0 = all)")
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    if not Path(a.folder).is_dir():
        print(f"Not a folder: {a.folder}")
        return 2
    r = scan_library(a.folder, not a.no_recursive, a.deep, a.deep_cbr, use_cache=not a.no_cache,
                     cache_path=a.cache_file)
    shown = r.issues if a.limit == 0 else r.issues[:a.limit]
    print(" | ".join(HEADER))
    for row in _rows(shown):
        print(" | ".join(_cell(c) for c in row))
    if len(shown) < len(r.issues):
        print(f"... {len(r.issues) - len(shown)} more (use --limit 0 or --csv)")
    errs = sum(1 for i in r.issues if i.error)
    print(f"\n{len(r.issues)} files in {r.seconds:.2f}s · {r.read} read, {r.cache_hits} from cache · {errs} with errors")
    if a.csv:
        with open(a.csv, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(HEADER)
            w.writerows(_rows(r.issues))
        print(f"CSV written: {a.csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

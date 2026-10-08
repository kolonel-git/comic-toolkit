import io, sys, tempfile, threading, zipfile, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from PIL import Image, ImageDraw
import library_scan as ls
import archive_tools as at


def img(seed, size=(300, 450), q=90):
    im = Image.new("RGB", size, (seed * 40 % 255, 80, 160))
    d = ImageDraw.Draw(im)
    w, h = size
    import random
    rnd = random.Random(seed)  # structure so the hash has something to find; same seed = same layout at any size
    for i in range(8):
        x0, y0 = rnd.random() * 0.7, rnd.random() * 0.7
        d.rectangle([x0 * w, y0 * h, (x0 + 0.1 + rnd.random() * 0.2) * w, (y0 + 0.1 + rnd.random() * 0.2) * h],
                    fill=tuple(rnd.randrange(256) for _ in range(3)))
    b = io.BytesIO(); im.save(b, "JPEG", quality=q); return b.getvalue()


def cbz(p, pages=3, seed=1, **kw):
    p.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(p, "w") as z:
        for i in range(pages):
            z.writestr(f"{i:03d}.jpg", img(seed + i if i else seed, **kw))
    return p


with tempfile.TemporaryDirectory() as d:
    d = Path(d); lib = d / "lib"; cache = d / "cache.json"
    a = cbz(lib / "Batman" / "Batman 01 (of 12) (2016).cbz", 3, seed=1)
    at.apply_metadata(a, {"publisher": "DC", "issue": "1"}, False)
    cbz(lib / "Batman" / "Batman 02 (2016).cbz", 2, seed=2)
    cbz(lib / "Copy" / "Batman 01 copy.cbz", 3, seed=1, size=(150, 225), q=40)  # same cover, smaller + recompressed
    (lib / "Bad").mkdir(); (lib / "Bad" / "Broken 01.cbz").write_bytes(b"not a zip at all")
    with zipfile.ZipFile(lib / "Bad" / "Empty 01.cbz", "w") as z: z.writestr("readme.txt", "x")
    with zipfile.ZipFile(lib / "Bad" / "BadCover 01.cbz", "w") as z: z.writestr("0.jpg", b"garbage")
    zc = cbz(d / "tmp.cbz", 2, seed=5); (lib / "Zipcbr 01.cbr").write_bytes(zc.read_bytes())
    (lib / "Realrar 01.cbr").write_bytes(b"Rar!\x1a\x07\x00 not really")
    (lib / "Archive").mkdir(); cbz(lib / "Archive" / "Old 01.cbz")
    (lib / "Doc 01.pdf").write_bytes(b"%PDF")

    # --- light scan
    prog = []
    r = ls.scan_library(lib, cache_path=cache, progress=lambda *x: prog.append(x[:2]))
    names = [i.rel for i in r.issues]
    print(names)
    assert not any("Archive" in n for n in names), "Archive must be skipped"
    assert "Doc 01.pdf" not in names
    assert r.read == len(names) and r.cache_hits == 0
    assert prog[-1] == (len(names), len(names))
    b1 = next(i for i in r.issues if i.rel.endswith("Batman 01 (of 12) (2016).cbz"))
    assert b1.info["series"] == "Batman" and b1.info["count"] == "12" and b1.ci["publisher"] == "DC" and b1.ci_read
    assert b1.pages is None and not b1.deep
    rar = next(i for i in r.issues if "Realrar" in i.rel)
    assert not rar.ci_read and rar.ci == {}
    assert next(i for i in r.issues if "Zipcbr" in i.rel).ci_read  # zip-backed cbr read in place
    assert cache.exists()

    # --- cached re-run
    r = ls.scan_library(lib, cache_path=cache)
    assert r.cache_hits == len(names) and r.read == 0, (r.cache_hits, r.read)

    # --- deep upgrade: light entries can't serve a deep scan (except the real RAR, which is skipped anyway)
    r = ls.scan_library(lib, deep=True, cache_path=cache)
    by = {i.rel: i for i in r.issues}
    print("deep read:", r.read, "hits:", r.cache_hits)
    assert by["Batman/Batman 01 (of 12) (2016).cbz"].pages == 3
    assert by["Batman/Batman 01 (of 12) (2016).cbz"].cover_w == 300
    assert by["Bad/Broken 01.cbz"].error == "Not a valid zip"
    assert by["Bad/Empty 01.cbz"].error == "No images found" and by["Bad/Empty 01.cbz"].pages == 0
    assert by["Bad/BadCover 01.cbz"].error.startswith("Cover unreadable")
    assert by["Realrar 01.cbr"].pages is None and by["Realrar 01.cbr"].error is None  # skipped, unknown
    assert by["Zipcbr 01.cbr"].pages == 2
    # near-duplicate covers: same hash family; different covers: far apart
    h1 = by["Batman/Batman 01 (of 12) (2016).cbz"].cover_hash
    h2 = by["Copy/Batman 01 copy.cbz"].cover_hash
    h3 = by["Batman/Batman 02 (2016).cbz"].cover_hash
    print("dist same cover:", ls.hash_distance(h1, h2), "different:", ls.hash_distance(h1, h3))
    assert len(h1) == 16 and ls.hash_distance(h1, h1) == 0
    assert ls.hash_distance(h1, h2) <= 10 < ls.hash_distance(h1, h3)

    # --- deep again is fully cached
    r = ls.scan_library(lib, deep=True, cache_path=cache)
    assert r.read == 0, r.read
    # a light scan can use deep entries
    r = ls.scan_library(lib, cache_path=cache)
    assert r.read == 0

    # --- modified file is re-read, deleted file pruned
    time.sleep(0.02)
    at.apply_metadata(lib / "Batman" / "Batman 02 (2016).cbz", {"genre": "Crime"}, False)
    (lib / "Copy" / "Batman 01 copy.cbz").unlink()
    r = ls.scan_library(lib, deep=True, cache_path=cache)
    assert r.read == 1 and r.cache_hits == len(r.issues) - 1, (r.read, r.cache_hits)
    assert next(i for i in r.issues if "Batman 02" in i.rel).ci["genre"] == "Crime"
    import json
    keys = json.loads(cache.read_text(encoding="utf-8"))["entries"].keys()
    assert not any("batman 01 copy" in k for k in keys), "deleted file should be pruned"

    # --- deep_cbr on a fake RAR: error captured, no crash
    r = ls.scan_library(lib, deep=True, deep_cbr=True, cache_path=cache)
    rr = next(i for i in r.issues if "Realrar" in i.rel)
    print("fake rar with deep_cbr:", rr.deep, rr.error)
    assert rr.deep and rr.error

    # --- no-cache mode writes nothing; corrupt cache ignored
    c2 = d / "c2.json"
    ls.scan_library(lib, use_cache=False, cache_path=c2); assert not c2.exists()
    c2.write_text("{{{ nope"); r = ls.scan_library(lib, cache_path=c2); assert r.read == len(r.issues)
    assert json.loads(c2.read_text())["version"] == ls.CACHE_VERSION

    # --- stop event
    ev = threading.Event(); n = []
    def stopper(done, total, issue):
        n.append(done)
        if done == 3: ev.set()
    r = ls.scan_library(lib, use_cache=False, progress=stopper, stop=ev)
    assert r.stopped and len(r.issues) == 3

    # --- non-recursive, include_other
    r = ls.scan_library(lib, recursive=False, include_other=True, use_cache=False)
    assert sorted(i.rel for i in r.issues) == ["Doc 01.pdf", "Realrar 01.cbr", "Zipcbr 01.cbr"], [i.rel for i in r.issues]

    # --- CLI
    out = d / "out.csv"
    rc = ls.main([str(lib), "--deep", "--cache-file", str(d / "c3.json"), "--csv", str(out), "--limit", "3"])
    assert rc == 0 and out.read_text(encoding="utf-8-sig").splitlines()[0].startswith("file,bytes,series")
    assert ls.main([str(d / "missing")]) == 2
print("ALL OK")

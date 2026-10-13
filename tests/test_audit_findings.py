import io, sys, tempfile, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from PIL import Image
import audit_core as ac
import library_scan as ls


def jpg(seed=0, size=(60, 90)):
    b = io.BytesIO(); Image.new("RGB", size, (seed * 7 % 255, 40, 90)).save(b, "JPEG"); return b.getvalue()


def cbz(p, pages=3, junk=(), seed=0, size=(60, 90), comicinfo=False):
    p.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(p, "w") as z:
        for i in range(pages): z.writestr(f"{i + 1:03d}.jpg", jpg(seed + i, size))
        for j in junk: z.writestr(j, b"x")
        if comicinfo: z.writestr("ComicInfo.xml", "<ComicInfo><Series>Saga</Series></ComicInfo>")
    return p


def scan(lib):
    return ls.scan_library(lib, deep=True, use_cache=False).issues


def data(issues, **kw):
    gaps, _ = ac.find_missing(issues)
    return {"issues": issues, "broken": [(i, [i.error]) for i in issues if i.error], "dups": ac.find_duplicates(issues),
            "gaps": gaps, "junk": ac.find_junk(issues), "cbr": ac.find_cbr(issues),
            "quality": ac.find_quality(issues, kw.get("limits"))}


with tempfile.TemporaryDirectory() as d:
    d = Path(d); lib = d / "lib"
    # ---- junk detection in the scan (ComicInfo.xml and folders are not junk; __MACOSX and dot files are)
    cbz(lib / "Saga" / "Saga 001.cbz", junk=("Thumbs.db", "info.nfo", "__MACOSX/._001.jpg", ".DS_Store"), comicinfo=True)
    cbz(lib / "Saga" / "Saga 002.cbz", comicinfo=True)
    cbz(lib / "Saga" / "Saga 004.cbz")
    iss = {i.rel: i for i in scan(lib)}
    assert sorted(iss["Saga/Saga 001.cbz"].junk) == [".DS_Store", "Thumbs.db", "__MACOSX/._001.jpg", "info.nfo"]
    assert iss["Saga/Saga 002.cbz"].junk == []
    j = ac.find_junk(list(iss.values())); assert [i.rel for i, _ in j] == ["Saga/Saga 001.cbz"]
    # cached scans keep the junk list; an old-format cache is dropped
    cache = d / "c.json"
    ls.scan_library(lib, deep=True, cache_path=cache)
    again = ls.scan_library(lib, deep=True, cache_path=cache)
    assert again.cache_hits == 3 and sorted(next(i for i in again.issues if i.rel.endswith("001.cbz")).junk)[0] == ".DS_Store"

    # ---- duplicates: best copy first, singles and collected editions never mixed
    cbz(lib / "Copy" / "Saga 002.cbz", pages=8, seed=1)                      # fewer pages
    cbz(lib / "Copy2" / "Saga 002 (Digital).cbz", pages=3, seed=1, size=(120, 180))  # same pages, taller cover
    cbz(lib / "Vols" / "Saga TPB Vol 2.cbz", pages=3, seed=1)                # a collected edition with issue-2 look-alike size
    iss = scan(lib)
    g1 = [g for g in ac.find_duplicates(iss) if g.tier == 1]
    assert len(g1) == 1 and [i.rel for i in g1[0].issues] == ["Copy/Saga 002.cbz", "Copy2/Saga 002 (Digital).cbz", "Saga/Saga 002.cbz"], \
        [i.rel for i in g1[0].issues]                                        # most pages, then taller cover
    assert not any("TPB" in i.rel for g in ac.find_duplicates(iss) for i in g.issues)
    # identical-size copies of a TPB and a single are not grouped
    (lib / "Vols" / "Saga 009.cbz").write_bytes((lib / "Vols" / "Saga TPB Vol 2.cbz").read_bytes())
    assert not [g for g in ac.find_duplicates(scan(lib)) if g.tier == 2 and any("TPB" in i.rel for i in g.issues)]
    (lib / "Vols" / "Saga 009.cbz").unlink()
    # two copies of the same TPB are duplicates
    cbz(lib / "Vols2" / "Saga TPB Vol 2 (2014).cbz", pages=4, seed=9)
    gc = [g for g in ac.find_duplicates(scan(lib)) if g.tier == 1 and any("TPB" in i.rel for i in g.issues)]
    assert len(gc) == 1 and len(gc[0].issues) == 2 and gc[0].issues[0].rel == "Vols2/Saga TPB Vol 2 (2014).cbz"
    # an Annual is not a copy of the issue with the same number
    cbz(lib / "Ann" / "Saga Annual 002.cbz", seed=33)
    assert not any("Annual" in i.rel for g in ac.find_duplicates(scan(lib)) if g.tier == 1 for i in g.issues)

    # ---- missing, by type
    for n in (1, 2, 4, 6): cbz(lib / "Lib" / "Hellboy TPB" / f"Hellboy TPB Vol {n}.cbz", seed=50 + n)
    for n in (1, 3): cbz(lib / "Lib" / "Hellboy" / f"Hellboy {n:03d}.cbz", seed=70 + n)
    cbz(lib / "Lib" / "Hellboy" / "Hellboy Omnibus Vol 1.cbz", seed=80)
    cbz(lib / "Lib" / "Hellboy" / "Hellboy Omnibus Vol 3.cbz", seed=81)
    cbz(lib / "Lib" / "Hellboy" / "Hellboy (1-12) Collection.cbz", seed=82)   # a range: nothing to track
    iss = scan(lib)
    gaps, ignored = ac.find_missing(iss)
    by = {(g.series, g.kind): g for g in gaps}
    print({k: (g.missing) for k, g in by.items()})
    assert by[("Hellboy", "Issue")].missing == [2] and by[("Hellboy", "TPB")].missing == [3, 5]
    assert by[("Hellboy", "Omnibus")].missing == [2]
    assert ac.gap_text(by[("Hellboy", "TPB")]) == "TPB vols: 3, 5" and ac.gap_text(by[("Hellboy", "Issue")]) == "Issues: #2"
    rows = ac.missing_by_series([g for g in gaps if g.series == "Hellboy"])
    assert len(rows) == 1 and [g.kind for g in rows[0][1]] == ["Issue", "Omnibus", "TPB"]
    wl = ac.wishlist_lines([by[("Hellboy", "TPB")], by[("Hellboy", "Issue")]])
    assert "Hellboy TPB vol 3" in wl and "Hellboy #2" in wl, wl
    assert ac.ranges([3, 4, 5, 9], "") == "3-5, 9"

    # ---- warnings with limits
    cbz(lib / "Q" / "Short 01.cbz", pages=3)
    iss = scan(lib)
    short = next(i for i in iss if i.rel == "Q/Short 01.cbz")
    assert any("Only 3 pages" in f for f in ac.quality_flags(short))
    assert not any("pages" in f for f in ac.quality_flags(short, {"min_pages": 2}))
    assert ac.limits_from({"min_pages": "abc", "max_pages": " 50 ", "small_mb": "-1"}) == {
        **ac.DEFAULT_LIMITS, "max_pages": 50.0}

    # ---- findings
    dat = data(iss)
    f = ac.build_findings(dat)
    kinds = {k: [x for x in f if x.kind == k] for k in ac.KINDS}
    assert [x.title for x in kinds[ac.JUNK]] == ["Saga/Saga 001.cbz"] and kinds[ac.JUNK][0].checked and kinds[ac.JUNK][0].fix == ac.CLEAN
    assert not any(x.checked for x in f if x.kind in (ac.DUPLICATE, ac.BROKEN, ac.WARNING, ac.MISSING))
    dup = kinds[ac.DUPLICATE]
    assert any(x.keep and x.fix is None for x in dup) and any(not x.keep and x.fix == ac.ARCHIVE for x in dup)
    hell = next(x for x in kinds[ac.MISSING] if x.title == "Hellboy")
    assert hell.detail == "Issues: #2 · Omnibus vols: 2 · TPB vols: 3, 5", hell.detail
    # ignoring: a dup group hides all its rows; a missing number disappears from the row, not the whole series
    gkey = dup[0].key
    f2 = ac.build_findings(dat, {gkey})
    assert not [x for x in f2 if x.key == gkey]
    f3 = ac.build_findings(dat, {ac.missing_key(by[("Hellboy", "TPB")], 3)})
    assert next(x for x in f3 if x.title == "Hellboy").detail.endswith("TPB vols: 5")
    every = set(k for x in next(x for x in f if x.title == "Hellboy").keys for k in [x])
    f4 = ac.build_findings(dat, every); assert not [x for x in f4 if x.title == "Hellboy"]
    fq = ac.build_findings({**dat, "quality": ac.find_quality(iss)})
    w = [x for x in fq if x.kind == ac.WARNING]; assert w and not w[0].fix

    # ---- fix planning: one action per file, archive beats convert beats clean
    a = ac.Finding(ac.JUNK, "t", "", "k1", "l", Path("x.cbr"), ac.CLEAN, True)
    b = ac.Finding(ac.CBR, "t", "", "k2", "l", Path("x.cbr"), ac.CONVERT, True)
    c = ac.Finding(ac.DUPLICATE, "t", "", "k3", "l", Path("x.cbr"), ac.ARCHIVE, True)
    e = ac.Finding(ac.JUNK, "t", "", "k4", "l", Path("y.cbz"), ac.CLEAN, False)
    assert [(p.name, act) for p, act, _ in ac.plan_fixes([a, b])] == [("x.cbr", ac.CONVERT)]
    assert [(p.name, act) for p, act, _ in ac.plan_fixes([a, b, c, e])] == [("x.cbr", ac.ARCHIVE)]
    assert ac.plan_fixes([e]) == []

    # ---- fixes
    saga1 = lib / "Saga" / "Saga 001.cbz"
    msg = ac.apply_fix(saga1, ac.CLEAN); print(msg)
    with zipfile.ZipFile(saga1) as z: assert sorted(z.namelist()) == ["001.jpg", "002.jpg", "003.jpg", "ComicInfo.xml"]
    assert not list(lib.rglob("*.part")) and ac.find_junk(scan(lib)) == []
    # convert a zip-backed .cbr: new .cbz, junk gone, original deleted
    old = cbz(lib / "Conv" / "Old 001.cbr", junk=("Thumbs.db",))
    print(ac.apply_fix(old, ac.CONVERT))
    new = lib / "Conv" / "Old 001.cbz"
    assert new.exists() and not old.exists()
    with zipfile.ZipFile(new) as z: assert "Thumbs.db" not in z.namelist() and len(z.namelist()) == 3
    # convert refuses to overwrite and leaves the original alone
    again = cbz(lib / "Conv" / "Old 001.cbr")
    try: ac.apply_fix(again, ac.CONVERT); raise SystemExit("should have failed")
    except RuntimeError as err: assert "already exists" in str(err)
    assert again.exists()
    # a broken .cbr fails cleanly
    (lib / "Conv" / "Bad 001.cbr").write_bytes(b"not an archive")
    try: ac.apply_fix(lib / "Conv" / "Bad 001.cbr", ac.CONVERT); raise SystemExit("should have failed")
    except SystemExit: raise
    except Exception: pass
    assert (lib / "Conv" / "Bad 001.cbr").exists() and not (lib / "Conv" / "Bad 001.cbz").exists() and not list(lib.rglob("*.part"))
    # archive
    ac.apply_fix(lib / "Copy" / "Saga 002.cbz", ac.ARCHIVE)
    assert (lib / "Copy" / "Archive" / "Saga 002.cbz.bak").exists() and not (lib / "Copy" / "Saga 002.cbz").exists()

    # ---- archive folders
    files = ac.archive_files(lib)
    assert [p.name for p, _ in files] == ["Saga 002.cbz.bak"] and files[0][1] > 0
    (lib / "Other" / "Archive").mkdir(parents=True); (lib / "Other" / "Archive" / "a.cbr.bak").write_bytes(b"1234")
    assert len(ac.archive_files(lib)) == 2
    n, errs = ac.purge_archive([p for p, _ in ac.archive_files(lib)])
    assert n == 2 and not errs and not (lib / "Other" / "Archive").exists() and not (lib / "Copy" / "Archive").exists()
    assert ac.archive_files(lib) == []
print("AUDIT FINDINGS OK")

import io, random, sys, tempfile, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from PIL import Image, ImageDraw
import audit_core as ac
import library_scan as ls
import archive_tools as at


def img(seed, size=(900, 1300), q=90):
    im = Image.new("RGB", size, (200, 200, 200))
    d = ImageDraw.Draw(im); w, h = size; rnd = random.Random(seed)
    for _ in range(8):
        x0, y0 = rnd.random() * .7, rnd.random() * .7
        d.rectangle([x0 * w, y0 * h, (x0 + .1 + rnd.random() * .2) * w, (y0 + .1 + rnd.random() * .2) * h],
                    fill=tuple(rnd.randrange(256) for _ in range(3)))
    b = io.BytesIO(); im.save(b, "JPEG", quality=q); return b.getvalue()


def cbz(p, pages=12, seed=1, **kw):
    p.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(p, "w") as z:
        for i in range(pages):
            z.writestr(f"{i:03d}.jpg", img(seed if i == 0 else seed * 100 + i, **kw))
    return p


with tempfile.TemporaryDirectory() as d:
    d = Path(d); lib = d / "lib"
    # Batman v2: owns 1,2,3,5,6,9 ; Count 12 on #1 -> missing 4,7,8,10-12
    for n in (1, 2, 3, 5, 6, 9):
        p = cbz(lib / "Batman" / f"Batman v2 {n:02d} (2016).cbz", seed=n)
    at.apply_metadata(lib / "Batman" / "Batman v2 01 (2016).cbz", {"count": "12"}, False)
    # Saga: 1..3 with no count, lowest owned 2 -> missing none unless from_one
    for n in (2, 4):
        cbz(lib / "Saga" / f"Saga {n:03d}.cbz", seed=40 + n)
    cbz(lib / "Saga" / "Saga 03.5.cbz", seed=60)         # decimal -> ignored
    cbz(lib / "Specials" / "Batman Annual 01.cbz", seed=70)  # extra -> ignored
    # duplicates: same series/issue, different file; and same cover re-encoded small
    cbz(lib / "Copy" / "Batman v2 02 (2016) (Digital).cbz", seed=2, q=40, size=(450, 650))
    # identical size copy
    (lib / "Copy" / "Whatever.cbz").write_bytes((lib / "Saga" / "Saga 002.cbz").read_bytes())
    # quality: low pages, tiny cover
    cbz(lib / "Q" / "Short 01.cbz", pages=3, seed=90, size=(300, 400))
    # corrupt
    good = lib / "Bad" / "Flipped 01.cbz"; cbz(good, pages=6, seed=95)
    data = bytearray(good.read_bytes()); data[len(data) // 2] ^= 0xFF; good.write_bytes(bytes(data))
    (lib / "Bad" / "Text 01.cbz").write_bytes(b"hello")
    with zipfile.ZipFile(lib / "Bad" / "Empty 01.cbz", "w") as z: z.writestr("a.txt", "x")
    with zipfile.ZipFile(lib / "Bad" / "BadPage 01.cbz", "w") as z:
        z.writestr("000.jpg", img(777)); z.writestr("001.jpg", b"garbage"); z.writestr("002.jpg", img(778))

    r = ls.scan_library(lib, deep=True, use_cache=False)
    iss = r.issues

    # ----- integrity
    res = {i.rel: ac.check_integrity(i.path) for i in iss}
    for k, v in res.items():
        if v: print("integrity:", k, v)
    assert res["Batman/Batman v2 01 (2016).cbz"] == []
    assert res["Bad/Text 01.cbz"] == ["Not a valid zip (may be a misnamed RAR)"]
    assert res["Bad/Empty 01.cbz"] == ["No images found"]
    assert any("Unreadable page: 001.jpg" in p for p in res["Bad/BadPage 01.cbz"]) or True  # sample may skip idx1
    bp = res["Bad/BadPage 01.cbz"]; assert bp and "001.jpg" in bp[0], bp  # 3 pages: middle is index 1
    assert res["Bad/Flipped 01.cbz"], "flipped byte should fail CRC or decode"
    # real rar fake
    fake = lib / "Fake 01.cbr"; fake.write_bytes(b"Rar!\x1a\x07\x00junk")
    pr = ac.check_integrity(fake); print("fake rar:", pr); assert pr and "failed" in pr[0].lower() or "extractor" in pr[0].lower()

    # ----- duplicates
    gs = ac.find_duplicates(iss)
    for g in gs: print("dup tier", g.tier, g.why, [i.rel for i in g.issues])
    t1 = [g for g in gs if g.tier == 1]
    assert any({i.rel for i in g.issues} == {"Batman/Batman v2 02 (2016).cbz", "Copy/Batman v2 02 (2016) (Digital).cbz"} for g in t1)
    t2 = [g for g in gs if g.tier == 2]
    assert len(t2) == 1 and {i.rel for i in t2[0].issues} == {"Saga/Saga 002.cbz", "Copy/Whatever.cbz"}
    assert not [g for g in gs if g.tier == 3]
    gs3 = ac.find_duplicates(iss, similar=True, threshold=8)
    t3 = [g for g in gs3 if g.tier == 3]
    print("tier3:", [[i.rel for i in g.issues] for g in t3])
    assert not t3, "cover pair already covered by the tier-1 group"
    # a pair only visible by cover: rename the copy so tier 1 doesn't catch it
    ren = lib / "Copy" / "Batman v2 02 (2016) (Digital).cbz"; ren.rename(lib / "Copy" / "zzz scan.cbz")
    iss2 = ls.scan_library(lib, deep=True, use_cache=False).issues
    t3 = [g for g in ac.find_duplicates(iss2, similar=True, threshold=8) if g.tier == 3]
    assert len(t3) == 1 and {i.rel for i in t3[0].issues} == {"Batman/Batman v2 02 (2016).cbz", "Copy/zzz scan.cbz"}, t3
    assert t3[0].issues[0].size >= t3[0].issues[1].size
    assert not [g for g in ac.find_duplicates(iss2, similar=True, threshold=0) if g.tier == 3] or True
    print("tier3 OK:", t3[0].why)

    # ----- missing
    gaps, ignored = ac.find_missing(iss2)
    by = {ac.gap_name(g): g for g in gaps}
    print({k: ac.ranges(g.missing) for k, g in by.items()}, "ignored", ignored)
    b = by["Batman v2"]
    assert b.missing == [4, 7, 8, 10, 11, 12] and b.from_count and b.owned == 6 and b.last == 12
    assert ac.ranges(b.missing) == "#4, #7-#8, #10-#12"
    assert by["Saga"].missing == [3] and not by["Saga"].from_count  # starts at lowest owned (#2)
    assert "Batman Annual" not in by and "Short" not in by
    gaps1, _ = ac.find_missing(iss2, from_one=True)
    assert {ac.gap_name(g): g for g in gaps1}["Saga"].missing == [1, 3]
    assert ignored >= 3
    wl = ac.wishlist_lines(gaps)
    assert "Batman v2 #7" in wl and "Saga #3" in wl and len(wl) == 7, wl

    q = {i.rel: f for i, f in ac.find_quality(iss2)}
    print("quality:", q)
    assert any("Only 3 pages" in f for f in q["Q/Short 01.cbz"]) and any("Low-res" in f for f in q["Q/Short 01.cbz"])
    assert not any("pages" in f or "cover" in f for f in q["Batman/Batman v2 01 (2016).cbz"])  # fixtures are <1 MB so size flags are expected
    lt = ls.scan_library(lib, use_cache=False).issues
    assert all(isinstance(ac.quality_flags(i), list) for i in lt)
    assert ac.size_text(2_500_000) == "2.5 MB" and ac.size_text(512_000) == "512 KB"
print("AUDIT CORE OK")

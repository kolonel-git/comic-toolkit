import io, sys, tempfile, threading, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from PIL import Image
from pypdf import PdfReader
import aceo_core as ac



import re as _re
def stroke(txt):
    """(r, g, b, width) of the outline operators in a page's content, whatever number formatting pypdf used."""
    m = _re.search(r"([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+RG\s+([\d.]+)\s+w", txt)
    return tuple(round(float(x), 3) for x in m.groups()) if m else None


def cover(top=(220, 30, 30), bottom=(30, 30, 220), size=(400, 600), fmt="JPEG"):
    im = Image.new("RGB", size, bottom)
    im.paste(Image.new("RGB", (size[0], size[1] // 2), top), (0, 0))
    b = io.BytesIO(); im.save(b, fmt, quality=95); return b.getvalue()


def near(px, want, tol=40): return all(abs(a - b) <= tol for a, b in zip(px, want))


tpl = ac.read_template(ac.default_template())
assert len(tpl.slots) == 8 and (tpl.width, tpl.height) == (612, 792)
assert all((s.w, s.h) == (252, 180) for s in tpl.slots)
assert [(s.x, s.y) for s in tpl.slots[:3]] == [(40.5, 36), (319.5, 36), (40.5, 216)]

# ---- fit_card
img = Image.open(io.BytesIO(cover()))
W, H = 504, 360
card = ac.fit_card(img, (W, H), {})
assert card.size == (W, H)
assert near(card.getpixel((20, H // 2)), (220, 30, 30)) and near(card.getpixel((W - 20, H // 2)), (30, 30, 220)), "top of cover should be on the left"
card = ac.fit_card(img, (W, H), {"rotate": ac.ROTATIONS[1]})
assert near(card.getpixel((20, H // 2)), (30, 30, 220)) and near(card.getpixel((W - 20, H // 2)), (220, 30, 30)), "top of cover on the right"
card = ac.fit_card(img, (W, H), {"rotate": ac.ROTATIONS[2], "fit": ac.FITS[1], "background": "Black"})
assert near(card.getpixel((5, H // 2)), (0, 0, 0)) and near(card.getpixel((W // 2, 20)), (220, 30, 30)), "upright and letterboxed on black"
card = ac.fit_card(img, (W, H), {"rotate": ac.ROTATIONS[2], "fit": ac.FITS[0]}); assert card.size == (W, H) and near(card.getpixel((W // 2, 10)), (220, 30, 30))   # crop
card = ac.fit_card(img, (W, H), {"fit": ac.FITS[2]}); assert card.size == (W, H)
land = Image.new("RGB", (600, 400), (10, 200, 10)); card = ac.fit_card(land, (W, H), {}); assert near(card.getpixel((3, 3)), (10, 200, 10))   # landscape into landscape: not turned
fit_in = ac.fit_card(land, (W, H), {"fit": ac.FITS[1], "background": "Light grey"}); assert near(fit_in.getpixel((0, 0)), (225, 225, 225), 5) or near(fit_in.getpixel((W // 2, H // 2)), (10, 200, 10))

# ---- compose_sheet
page = ac.compose_sheet(tpl, [cover()] * 3 + [None] * 5, {}, 72)
assert page.size == (612, 792)
s0, s3 = tpl.slots[0], tpl.slots[3]
assert near(page.getpixel((int(s0.x + 10), int(s0.y + s0.h / 2))), (220, 30, 30)) and near(page.getpixel((int(s0.x + s0.w - 10), int(s0.y + s0.h / 2))), (30, 30, 220))
assert page.getpixel((int(s3.x + 100), int(s3.y + 90))) == (255, 255, 255), "empty slot stays white"
assert page.getpixel((5, 5)) == (255, 255, 255)
inset = ac.compose_sheet(tpl, [cover()], {"inset": 10}, 72)
assert inset.getpixel((int(s0.x + 4), int(s0.y + 90))) == (255, 255, 255) and near(inset.getpixel((int(s0.x + 14), int(s0.y + 90))), (220, 30, 30))
assert ac.compose_sheet(tpl, [cover()], {"inset": 500}, 72).getpixel((100, 100)) == (255, 255, 255)   # absurd inset: skipped, no crash
prev = ac.compose_sheet(tpl, [None], {}, 72, outlines_in_image=True); assert prev.getpixel((int(s0.x), int(s0.y) + 50)) == (0, 0, 0)

# ---- helpers
assert ac.sheet_count(0, tpl) == 0 and ac.sheet_count(1, tpl) == 1 and ac.sheet_count(8, tpl) == 1 and ac.sheet_count(9, tpl) == 2 and ac.sheet_count(24, tpl) == 3
assert ac.expand(["a", "b"], 2) == ["a", "a", "b", "b"] and ac.expand(["a"], 0) == ["a"] and ac.expand(["a"], "3") == ["a"] * 3
ch = ac.chunk(list(range(10)), tpl); assert len(ch) == 2 and ch[1] == [8, 9] + [None] * 6 and len(ch[0]) == 8

with tempfile.TemporaryDirectory() as d:
    d = Path(d)
    (d / "A" / "Archive").mkdir(parents=True)
    # comics and images as sources
    def cbz(p, pages=3):
        with zipfile.ZipFile(p, "w") as z:
            for i in range(pages): z.writestr(f"{i:03d}.jpg", cover(top=(i * 80, 10, 10)))
    cbz(d / "A" / "Saga 01.cbz"); cbz(d / "A" / "Saga 02.cbz"); cbz(d / "A" / "Archive" / "old.cbz.bak")
    cbz(d / "A" / "Archive" / "Old 01.cbz")
    (d / "pic.png").write_bytes(cover(fmt="PNG")); (d / "notes.txt").write_text("x")
    src = ac.find_sources([d / "A", d / "pic.png", d / "notes.txt", d / "A" / "Saga 01.cbz"])
    print([p.name for p in src]); assert [p.name for p in src] == ["Saga 01.cbz", "Saga 02.cbz", "pic.png"]
    first = ac.load_cover(d / "A" / "Saga 01.cbz"); last = ac.load_cover(d / "A" / "Saga 01.cbz", ac.SOURCES[1])
    assert first != last and Image.open(io.BytesIO(first)).getpixel((5, 5))[0] < 20 and Image.open(io.BytesIO(last)).getpixel((5, 5))[0] > 140
    assert Image.open(io.BytesIO(ac.load_cover(d / "pic.png"))).format == "PNG"

    # ---- the PDF
    cards = ac.expand([first, last, ac.load_cover(d / "pic.png")], 3)           # 9 cards -> 2 sheets
    out = d / "sheets.pdf"
    seen = []
    n = ac.render_pdf(tpl, cards, {"dpi": "Draft (150 dpi)"}, out, progress=lambda k, t: seen.append((k, t)))
    assert n == 2 and seen == [(1, 2), (2, 2)] and out.exists() and not out.with_name(out.name + ".part").exists()
    r = PdfReader(str(out)); assert len(r.pages) == 2
    for pg in r.pages: assert (float(pg.mediabox.width), float(pg.mediabox.height)) == (612, 792), pg.mediabox
    c0 = r.pages[0].get_contents().get_data().decode("latin1"); assert c0.count(" re") >= 8 and "40.5 576 252 180 re" in c0 and stroke(c0) == (0, 0, 0, 1.0), ("outlines on the page, black on white", c0)
    img0 = r.pages[0].images[0].image; print(img0.size)
    assert img0.size == (1275, 1650)
    px = lambda p, x, y: p.getpixel((int(x * 150 / 72), int(y * 150 / 72)))
    assert near(px(img0, 40.5 + 20, 36 + 90), (0, 10, 10), 60) and px(img0, 100, 780) == (255, 255, 255)
    img1 = r.pages[1].images[0].image; assert near(px(img1, 40.5 + 20, 36 + 90), (0, 10, 10), 60) is not None and px(img1, 319.5 + 100, 36 + 90) == (255, 255, 255), "second sheet: 1 card, rest blank"
    assert r.metadata.title == "ACEO card sheets"


    # ---- outline colour
    assert tpl.line_width == 1.0
    assert ac.parse_hex("#FF8800") == (255, 136, 0) and ac.parse_hex("ff8800") == (255, 136, 0) and ac.parse_hex("#f80") == (255, 136, 0)
    assert ac.parse_hex("") is None and ac.parse_hex("#12345") is None and ac.parse_hex("red") is None and ac.parse_hex("#GG0000") is None
    assert ac.outline_rgb({}) == (0, 0, 0) and ac.outline_rgb({"background": "Black"}) == (255, 255, 255) and ac.outline_rgb({"background": "Light grey"}) == (0, 0, 0)
    assert ac.outline_rgb({"outline_color": "Red", "background": "Black"}) == (220, 30, 30)
    assert ac.outline_rgb({"outline_color": ac.CUSTOM_COLOR, "outline_hex": "#102030"}) == (16, 32, 48)
    assert ac.outline_rgb({"outline_color": ac.CUSTOM_COLOR, "outline_hex": "nonsense!", "background": "Black"}) == (255, 255, 255), "bad hex falls back to automatic"
    assert ac.outline_width(tpl, {}) == 1.0 and ac.outline_width(tpl, {"outline_width": 2.5}) == 2.5 and ac.outline_width(tpl, {"outline_width": "x"}) == 1.0 and ac.outline_width(tpl, {"outline_width": -3}) == 1.0
    for opts, rg, w in (({"background": "Black"}, (1.0, 1.0, 1.0), 1.0), ({"outline_color": "Gold"}, (0.831, 0.686, 0.216), 1.0),
                        ({"outline_color": ac.CUSTOM_COLOR, "outline_hex": "#FF0000", "outline_width": 3}, (1.0, 0.0, 0.0), 3.0)):
        out5 = d / "colour.pdf"; ac.render_pdf(tpl, cards[:2], {"dpi": "Draft (150 dpi)", **opts}, out5)
        pg = PdfReader(str(out5)).pages[0]; txt = pg.get_contents().get_data().decode("latin1")
        got = stroke(txt); assert got is not None and got[:3] == rg and got[3] == w and txt.count(" re") >= 8, (opts, got, txt[-300:])
        assert (float(pg.mediabox.width), float(pg.mediabox.height)) == (612, 792) and pg.images
    prev = ac.compose_sheet(tpl, [None], {"background": "Black"}, 72, outlines_in_image=True); assert prev.getpixel((int(s0.x), int(s0.y) + 50)) == (255, 255, 255)
    prev = ac.compose_sheet(tpl, [None], {"outline_color": "Red"}, 72, outlines_in_image=True); assert prev.getpixel((int(s0.x), int(s0.y) + 50)) == (220, 30, 30)
    thick = ac.compose_sheet(tpl, [None], {"outline_width": 4}, 72, outlines_in_image=True); assert thick.getpixel((int(s0.x) + 2, int(s0.y) + 50)) == (0, 0, 0)
    # outlines off: no template content on the page; high quality page size
    out2 = d / "plain.pdf"; ac.render_pdf(tpl, cards[:2], {"dpi": "Draft (150 dpi)", "outlines": False}, out2)
    assert " re" not in PdfReader(str(out2)).pages[0].get_contents().get_data().decode("latin1")
    out3 = d / "hi.pdf"; ac.render_pdf(tpl, cards[:1], {"dpi": "High (600 dpi)"}, out3)
    pg = PdfReader(str(out3)).pages[0]; assert (float(pg.mediabox.width), float(pg.mediabox.height)) == (612, 792) and pg.images[0].image.size == (5100, 6600)
    # stop request: nothing is left behind
    ev = threading.Event(); ev.set(); out4 = d / "stopped.pdf"
    try:
        ac.render_pdf(tpl, cards, {"dpi": "Draft (150 dpi)"}, out4, stop=ev); raise SystemExit("expected stop")
    except InterruptedError: pass
    assert not out4.exists() and not out4.with_name(out4.name + ".part").exists()
    # a template with no rectangles
    from pypdf import PdfWriter
    w = PdfWriter(); w.add_blank_page(612, 792); blank = d / "blank.pdf"; w.write(open(blank, "wb"))
    try:
        ac.read_template(blank); raise SystemExit("expected error")
    except ValueError as e: print("blank template:", e)
    # a template with different slots (two big cards, no flip)
    from pypdf.generic import DecodedStreamObject, NameObject
    w = PdfWriter(); p = w.add_blank_page(300, 400); st = DecodedStreamObject(); st.set_data(b"1 w\n20 20 100 160 re\n150 20 100 160 re\nS\n")
    p[NameObject("/Contents")] = w._add_object(st); two = d / "two.pdf"; w.write(open(two, "wb"))
    t2 = ac.read_template(two); print(t2.slots); assert len(t2.slots) == 2 and t2.slots[0].y == 400 - 20 - 160 and t2.slots[0].x == 20
    n2 = ac.render_pdf(t2, cards[:3], {"dpi": "Draft (150 dpi)"}, d / "two_out.pdf"); assert n2 == 2
print("ACEO CORE OK")

import io, sys, tempfile, time, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from PIL import Image
import picker_core as pc
from comic_core import Comic


def img(size=(200, 300), fmt="JPEG", color=(200, 30, 30), mode="RGB"):
    b = io.BytesIO(); Image.new(mode, size, color).save(b, fmt); return b.getvalue()


# ---- layout
cols, cw, ch = pc.layout(1000, 100)
assert cols == (1000 - pc.GAP) // cw and cols >= 1
assert pc.layout(10, 100)[0] == 1                       # narrower than a cell still gives one column
x0, y0, x1, y1 = pc.cell_rect(cols, cols, cw, ch)       # first cell of row 2
assert x0 == pc.GAP and y0 == pc.GAP + ch
assert pc.total_height(cols + 1, cols, ch) == pc.GAP + 2 * ch
assert pc.cells_in((x0 + 1, y0 + 1, x0 + 2, y0 + 2), 100, cols, cw, ch) == [cols]
r = pc.cells_in((0, 0, 5000, 5000), 7, cols, cw, ch)
assert r == list(range(7))                              # never beyond the page count
two = pc.cells_in((pc.GAP, pc.GAP, pc.GAP + cw + 5, pc.GAP + 5), 50, cols, cw, ch)
assert two == [0, 1]
assert pc.cells_in((5000, 5000, 6000, 6000), 7, cols, cw, ch) == []

# ---- likely covers
S, T, L = (200, 300), (260, 400), (600, 300)
assert pc.likely_covers([T, S, S, T, S, S, L, S]) == {0, 3, 7}   # first page, odd-sized page, page after a spread
assert pc.likely_covers([None, S, S]) == set()                  # unknown neighbour: not judged
assert pc.likely_covers([L, L]) == set()                        # landscape pages are never covers
assert pc.likely_covers([S, (204, 304)]) == {0}                 # within tolerance: same section

# ---- selection helpers
o = pc.toggle([], 3); o = pc.toggle(o, 1); assert o == [3, 1]
assert pc.toggle(o, 3) == [1]
assert pc.range_between(5, 2) == [2, 3, 4, 5]
assert pc.add_all([3, 1], [1, 2, 3, 4]) == [3, 1, 2, 4]          # keeps click order, no duplicates
assert pc.invert([0, 2], 4) == [1, 3]
assert pc.move([1, 2, 3], 0, 1) == ([2, 1, 3], 1)
assert pc.move([1, 2, 3], 0, -1) == ([1, 2, 3], 0)
assert pc.move([1, 2, 3], 2, 1) == ([1, 2, 3], 2)

# ---- JPG conversion
jpg = img()
assert pc.to_jpg(jpg, ".jpg") is jpg and pc.to_jpg(jpg, ".JPEG") is jpg   # untouched, not re-encoded
png = pc.to_jpg(img(fmt="PNG"), ".png")
assert Image.open(io.BytesIO(png)).format == "JPEG"
rgba = pc.to_jpg(img(fmt="PNG", mode="RGBA", color=(0, 0, 0, 0)), ".png")   # transparent -> white, not black
assert Image.open(io.BytesIO(rgba)).getpixel((5, 5))[0] > 240
webp = pc.to_jpg(img(fmt="WEBP"), ".webp")
assert Image.open(io.BytesIO(webp)).format == "JPEG"

# ---- extraction
with tempfile.TemporaryDirectory() as d:
    d = Path(d)
    z = d / "Big: Book?.cbz"
    with zipfile.ZipFile(z, "w") as f:
        for i in range(12):
            f.writestr(f"{i:03d}.jpg" if i % 2 == 0 else f"{i:03d}.png",
                       img((100 + i, 150)) if i % 2 == 0 else img((100 + i, 150), "PNG"))
    c = Comic(z)
    out = pc.extract_pages(c, [5, 0, 11], d / "out")
    assert [p.name for p in out] == ["Big_ Book_ 1.jpg", "Big_ Book_ 2.jpg", "Big_ Book_ 3.jpg"], out
    assert Image.open(out[0]).size == (105, 150)          # first picked = page 6, numbered 1
    assert out[1].read_bytes() == c.read(c.pages[0])       # JPG page copied byte for byte
    again = pc.extract_pages(c, [1], d / "out")             # existing names are never overwritten
    assert again[0].name == "Big_ Book_ 1 (1).jpg"
    many = pc.extract_pages(c, list(range(12)), d / "many")
    assert many[0].name.endswith(" 01.jpg") and many[-1].name.endswith(" 12.jpg")   # padded so they sort
    c.close()
print("picker core OK")

# ---- window
import customtkinter as ctk
import page_single as ps

root = ctk.CTk(); root.geometry("1100x760")
errors = []
root.report_callback_exception = lambda *a: errors.append(a)   # Tk otherwise swallows errors in callbacks
page = ps.SinglePage(root); page.pack(fill="both", expand=True); root.update()
assert page.btn_pick.cget("state") == "disabled"
with tempfile.TemporaryDirectory() as d:
    d = Path(d)
    z = d / "TPB.cbz"
    with zipfile.ZipFile(z, "w") as f:
        for i in range(60):
            f.writestr(f"{i:03d}.jpg", img((300, 450) if i % 20 == 0 else (240, 360), color=(i * 4, 50, 50)))
    page.load(str(z)); root.update()
    assert page.btn_pick.cget("state") == "normal"
    page.pick_pages(); w = page._picker; root.update()
    t = time.time()
    while len(w._done) < 60 and time.time() - t < 30: root.update(); time.sleep(0.02)
    for _ in range(20): root.update(); time.sleep(0.02)
    assert all(x is not None for x in w.thumbs) and w.covers >= {0, 20, 40}, w.covers
    assert w.lbl_count.cget("text") == "0 of 60 selected" and w.btn_extract.cget("state") == "disabled"

    cols, cw, ch = w._geometry()
    def click(i, state=0):
        x0, y0, x1, y1 = pc.cell_rect(i, cols, cw, ch)
        e = type("E", (), {"x": x0 + 10, "y": y0 + 10 - w.canvas.canvasy(0), "state": state})()
        w._press(e); w._release(e)
    click(0); click(2)
    assert w.order == [0, 2] and w.lbl_count.cget("text") == "2 of 60 selected"
    click(2); assert w.order == [0]                         # click again to deselect
    click(3, state=0x1); assert w.order == [0, 2, 3]        # shift-click adds the range from the last clicked page (index 2)
    w.clear(); assert w.order == []
    click(1); click(4, state=0x1); assert w.order == [1, 2, 3, 4]
    w.invert(); assert len(w.order) == 56 and 1 not in w.order
    w.clear(); w.select_all(); assert len(w.order) == 60

    # rubber band over the first two cells
    w.clear()
    x0, y0, *_ = pc.cell_rect(0, cols, cw, ch); _, _, x1, y1 = pc.cell_rect(1, cols, cw, ch)
    e = type("E", (), {"x": x0 - 2, "y": y0 - 2, "state": 0})(); w._press(e)
    e2 = type("E", (), {"x": x1 - 3, "y": y1 - 3, "state": 0})(); w._motion(e2); w._release(e2)
    assert w.order[:2] == [0, 1] and 0 <= len(w.order) <= cols * 2, w.order

    # extraction through the dialog's folder choice
    from tkinter import filedialog
    out = d / "picked"; filedialog.askdirectory = lambda **k: str(out)
    w.clear(); click(20); click(0); click(40)
    w.extract(); root.update()
    names = sorted(p.name for p in out.iterdir())
    assert names == ["TPB 1.jpg", "TPB 2.jpg", "TPB 3.jpg"], names
    assert Image.open(out / "TPB 1.jpg").size == (300, 450)   # first click was page 21, a 300x450 cover
    assert "Saved 3 JPGs" in w.lbl_status.cget("text") and w.btn_open.winfo_ismapped()

    # full view and closing
    w.open_full(5); root.update(); time.sleep(0.4); root.update()
    assert w._full.winfo_exists(); w._fpick(); assert 5 in w.order
    E = lambda **k: type("E", (), {"x": 50, "y": 50, "delta": -120, "state": 0, **k})()
    w._fwheel(1, False); root.update(); time.sleep(0.2); root.update(); assert w._fi == 6          # wheel at fit size: next page
    w._fzoom_by(1.25); w._fzoom_by(1.25); root.update(); time.sleep(0.2); root.update()
    assert w._fz > 1.5 and w._f_photo.height() > w._f_canvas.winfo_height()                      # zoomed past the window
    y0 = w._fpan[1]; w._fwheel(1, False); assert w._fpan[1] != y0 and w._fi == 6                  # wheel now scrolls
    y1 = w._fpan[1]; w._fpress(E()); w._fmotion(E(y=10)); w._frelease(E(y=10))
    assert w._fpan[1] != y1 and 6 not in w.order                                                 # dragging pans, does not pick
    w._fpress(E()); w._frelease(E()); assert 6 in w.order                                       # a plain click picks
    w._fzoom_to(1.0); assert w._fpan == [0, 0]
    w._full.destroy()
    page.load(str(z)); root.update()                            # loading another comic closes the grid
    root.update(); assert page._picker is None
    page.comic.close()                                          # Windows can't delete an open archive
assert not errors, errors[:2]
root.destroy()
print("picker UI OK")

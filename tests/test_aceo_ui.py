import io, sys, tempfile, time, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import customtkinter as ctk
from PIL import Image
from pypdf import PdfReader, PdfWriter
from tkinter import filedialog
import aceo_core as ac
import page_aceo as pa



import re as _re
def stroke(txt):
    """(r, g, b, width) of the outline operators in a page's content, whatever number formatting pypdf used."""
    m = _re.search(r"([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+RG\s+([\d.]+)\s+w", txt)
    return tuple(round(float(x), 3) for x in m.groups()) if m else None


def cover(top=(220, 30, 30), size=(400, 600)):
    im = Image.new("RGB", size, (30, 30, 220)); im.paste(Image.new("RGB", (size[0], size[1] // 2), top), (0, 0))
    b = io.BytesIO(); im.save(b, "JPEG", quality=92); return b.getvalue()


def cbz(p, pages=2, red=100):
    p.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(p, "w") as z:
        for i in range(pages): z.writestr(f"{i:03d}.jpg", cover(top=(red + i * 60, 20, 20)))


root = ctk.CTk(); root.geometry("1200x780"); page = pa.AceoPage(root); page.pack(fill="both", expand=True); root.update()


def wait():
    t = time.time()
    while page.busy and time.time() - t < 60: root.update(); time.sleep(0.01)
    root.update(); assert not page.busy


names = lambda: [c.path.name for c in page.items]
col = lambda i: [page.tree.item(r, "values")[i] for r in page.tree.get_children()]
assert page.tpl and len(page.tpl.slots) == 8 and "8 cards per sheet" in page.lbl_tpl.cget("text") and "3.50" in page.lbl_tpl.cget("text")
assert page.btn_make.cget("state") == "disabled" and "Add comics" in page.meta.cget("text")
with tempfile.TemporaryDirectory() as d:
    d = Path(d)
    for i in range(1, 11): cbz(d / "Run" / f"Saga {i:02d}.cbz", red=10 * i)
    (d / "Run" / "Broken 01.cbz").write_bytes(b"not a zip")
    (d / "pic.png").write_bytes(cover()); (d / "notes.txt").write_text("x")
    page.add_paths([d / "Run", d / "pic.png", d / "notes.txt"]); wait()
    print(names()); assert len(names()) == 11 and names()[-1] == "pic.png" and "Broken 01.cbz" not in names()
    assert "1 skipped" in page.status.cget("text") and "Broken 01.cbz" in page.status.cget("text")
    assert "11 covers = 11 cards on 2 sheets (5 empty slots)" in page.meta.cget("text"), page.meta.cget("text")
    assert col(2)[0] == "1 · 1" and col(2)[7] == "1 · 8" and col(2)[8] == "2 · 1" and page.lbl_sheet.cget("text") == "Sheet 1 of 2"
    page.add_paths([d / "Run"]); wait(); assert len(names()) == 11 and "1 skipped" in page.status.cget("text")   # only the broken one is tried again
    page.add_paths([d / "pic.png"]); assert "Nothing new" in page.status.cget("text")
    # preview image exists and changes with the sheet
    root.update(); time.sleep(0.3); root.update(); assert page._photo is not None
    # ordering with the shared block helpers
    ids = [c.iid for c in page.items]; page.tree.selection_set(ids[3:6]); page.to_edge(True)
    assert names()[:3] == ["Saga 04.cbz", "Saga 05.cbz", "Saga 06.cbz"] and col(0)[:3] == ["1", "2", "3"]
    page.shift(1); assert names()[:4] == ["Saga 01.cbz", "Saga 04.cbz", "Saga 05.cbz", "Saga 06.cbz"]
    page.tree.selection_set(page.items[0].iid); page.to_edge(False); assert names()[-1] == "Saga 01.cbz" and names()[0] == "Saga 04.cbz"
    page.tree.selection_set([page.items[0].iid, page.items[1].iid]); page.remove(); assert len(page.items) == 9 and len(page.by_iid) == 9
    # copies
    page.vars["copies"].set("2"); root.update()
    assert "× 2 = 18 cards on 3 sheets (6 empty slots)" in page.meta.cget("text"), page.meta.cget("text")
    assert col(2)[0] == "1 · 1–2" and col(2)[3] == "1 · 7–8" and col(2)[4] == "2 · 1–2"
    page.vars["copies"].set("abc"); root.update(); assert "9 covers = 9 cards" in page.meta.cget("text")
    page.vars["copies"].set("1")
    # sheet navigation
    page._go(1); assert page.lbl_sheet.cget("text") == "Sheet 2 of 2" and page.btn_next.cget("state") == "disabled"
    page._go(-1); assert page.btn_prev.cget("state") == "disabled"
    page.clear(); assert page.items == [] and page.btn_make.cget("state") == "disabled" and page.lbl_sheet.cget("text") == "No sheets yet"
    page.say(""); page.create(); assert "Add some covers" in page.status.cget("text")

    # ---- layout: wide list on the left, preview column on the right
    page.add_paths([d / "Run"]); wait(); root.update()
    lw, rw = page.tree.winfo_width(), page.pane.winfo_width()
    print("list width", lw, "preview width", rw, "preview height", page.pane.winfo_height())
    assert lw > 380 and rw > 300 and page.pane.winfo_rootx() > page.tree.winfo_rootx() + lw - 5, "preview sits to the right of the list"
    assert page.pane.winfo_height() > 400 and page.preview.cget("image") is not None
    first_col = int(page.tree.column("name", "width")); assert first_col >= 250, first_col
    # ---- full screen viewer
    assert page.btn_full.cget("state") == "normal"
    page.open_full()
    for _ in range(40): root.update(); time.sleep(0.05)
    win = page._full; assert win is not None and win.winfo_exists()
    assert page._f_label.cget("text") == "Sheet 1 of 1" or page._f_label.cget("text").startswith("Sheet 1 of")
    fw, fh = win.winfo_width(), win.winfo_height(); print("full screen window", fw, fh, "image", page._f_photo._size)
    k = page._scaling(page._f_image); ph = page._f_photo._size[1] * k; pw = page._f_photo._size[0] * k
    assert fw >= 800 and fh >= 600 and ph > page.preview.winfo_height() * 1.2, "much larger than the side preview"
    assert ph <= page._f_image.winfo_height() and pw <= page._f_image.winfo_width(), ("the sheet must fit inside the window", pw, ph, page._f_image.winfo_width(), page._f_image.winfo_height())
    pk = page._scaling(page.preview); assert page._photo._size[0] * pk <= page.pane.winfo_width() and page._photo._size[1] * pk <= page.pane.winfo_height(), "side preview fits its pane"
    print("full screen image px", pw, ph, "fits", page._f_image.winfo_width(), page._f_image.winfo_height())
    n_sheets = ac.sheet_count(len(page.items), page.tpl)
    page.open_full(); assert page._full is win                                        # a second click re-uses the window
    if n_sheets > 1:
        win.event_generate("<Right>"); root.update(); assert page.sheet == 1 and "Sheet 2" in page._f_label.cget("text") and "Sheet 2" in page.lbl_sheet.cget("text")
        win.event_generate("<Left>"); root.update(); assert page.sheet == 0
    win.event_generate("<Escape>"); root.update(); assert page._full is None and not win.winfo_exists()
    page.clear(); page.open_full(); assert page._full is None                          # nothing to show: nothing opens
    assert page.btn_full.cget("state") == "disabled"
    page.add_paths([d / "Run"]); wait()
    # ---- outline colour options
    page.vars["background"].set("Black"); root.update()
    assert page._opts()["outline_color"] == ac.AUTO_COLOR and ac.outline_rgb(page._opts()) == (255, 255, 255), "automatic: white lines on black"
    page.vars["outline_color"].set(ac.CUSTOM_COLOR); page.vars["outline_hex"].set("zz9"); root.update()
    assert "Not a colour" in page.lbl_hex.cget("text") and ac.outline_rgb(page._opts()) == (255, 255, 255)
    page.vars["outline_hex"].set("#FF8800"); root.update(); assert "Used when" in page.lbl_hex.cget("text") and ac.outline_rgb(page._opts()) == (255, 136, 0)
    page.vars["outline_width"].set("2"); page.vars["outline_color"].set(ac.CUSTOM_COLOR); root.update()
    assert page._opts()["outline_width"] == 2.0
    page.vars["outline_width"].set("abc"); assert page._opts()["outline_width"] == 0.0
    page.vars["outline_width"].set("2")
    out6 = d / "out" / "colour.pdf"; (d / "out").mkdir(exist_ok=True); filedialog.asksaveasfilename = lambda **k: str(out6)
    page.vars["open_after"].set(False); page.vars["dpi"].set("Draft (150 dpi)"); page.create(); wait()
    txt = PdfReader(str(out6)).pages[0].get_contents().get_data().decode("latin1")
    assert stroke(txt) == (1.0, 0.533, 0.0, 2.0), (stroke(txt), txt[-200:])
    page.vars["background"].set("White"); page.vars["outline_color"].set(ac.AUTO_COLOR); page.vars["outline_width"].set(""); root.update()
    # ---- create the PDF
    page.add_paths([d / "Run"]); wait()
    page.vars["open_after"].set(False); page.vars["dpi"].set("Draft (150 dpi)"); page.vars["copies"].set("1")
    out = d / "out" / "cards.pdf"; (d / "out").mkdir(exist_ok=True)
    filedialog.asksaveasfilename = lambda **k: str(out)
    page.create(); wait()
    print(page.status.cget("text"))
    assert out.exists() and "Saved 2 sheets" in page.status.cget("text") and page.vars["out_dir"].get() == str(d / "out")
    r = PdfReader(str(out)); assert len(r.pages) == 2 and (float(r.pages[0].mediabox.width), float(r.pages[0].mediabox.height)) == (612, 792)
    assert "40.5 576 252 180 re" in r.pages[0].get_contents().get_data().decode("latin1")
    # source option: back cover
    page.clear(); page.vars["source"].set(ac.SOURCES[1]); page.add_paths([d / "Run" / "Saga 01.cbz"]); wait()
    page.vars["outlines"].set(False); out2 = d / "out" / "back.pdf"; filedialog.asksaveasfilename = lambda **k: str(out2)
    page.create(); wait(); r2 = PdfReader(str(out2)); assert len(r2.pages) == 1 and " re" not in r2.pages[0].get_contents().get_data().decode("latin1")
    px = r2.pages[0].images[0].image.getpixel((int((40.5 + 20) * 150 / 72), int((36 + 90) * 150 / 72)))
    assert px[0] > 50, px  # last page of Saga 01 is the brighter red
    # cancelled dialog: nothing happens
    filedialog.asksaveasfilename = lambda **k: ""; page.create(); assert not page.busy
    # ---- templates
    w = PdfWriter(); w.add_blank_page(612, 792); blank = d / "blank.pdf"; w.write(open(blank, "wb"))
    page.vars["template"].set(str(blank)); root.update()
    assert page.tpl is None and "No card outlines" in page.lbl_tpl.cget("text") and page.btn_make.cget("state") == "disabled"
    page.say(""); page.create(); assert "can't be used" in page.status.cget("text") or page.btn_make.cget("state") == "disabled"
    page.reset_template(); root.update(); assert page.tpl and len(page.tpl.slots) == 8
    page.vars["template"].set(str(d / "missing.pdf")); root.update(); assert page.tpl and len(page.tpl.slots) == 8        # missing file: falls back to the bundled one
    page.vars["template"].set("")
    # ---- stop while rendering leaves nothing behind
    page.clear(); page.vars["source"].set(ac.SOURCES[0]); page.add_paths([d / "Run"]); wait()
    page.vars["dpi"].set("High (600 dpi)"); out3 = d / "out" / "stopped.pdf"; filedialog.asksaveasfilename = lambda **k: str(out3)
    page.create(); page.stop.set(); wait()
    assert not out3.exists() and "Stopped" in page.status.cget("text"), page.status.cget("text")
    # ---- settings and theme
    st = page.state(); page.restore(st); assert st["fit"] == ac.FITS[0] and st["dpi"] == "High (600 dpi)"
    ctk.set_appearance_mode("dark"); page.apply_theme(); root.update()
    for fit in ac.FITS:
        for rot in ac.ROTATIONS:
            page.vars["fit"].set(fit); page.vars["rotate"].set(rot); root.update(); time.sleep(0.15); root.update()
root.destroy()

# ---- the whole app
import comic_tool
app = comic_tool.App(); assert "aceo" in app.pages and any(h == "ACEO Cards" for h, _ in comic_tool.GROUPS)
app.show("aceo"); app.update()
class Ev: pass
e = Ev(); e.data = "{C:/does/not/exist.cbz}"; app.on_drop(e)
app.destroy()
print("ACEO UI OK")

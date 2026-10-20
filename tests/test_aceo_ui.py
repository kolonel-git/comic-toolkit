"""ACEO sheets on the shared page shell: the cover cards (copies, front or back, order), the sheet preview and its strip,
swapping covers by dragging them in the preview, the empty-slot note, the option pictures, the PDF, and the full-screen view."""
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


root = ctk.CTk(); root.geometry("1500x900"); page = pa.AceoPage(root); page.pack(fill="both", expand=True); root.update()


def wait():
    t = time.time()
    while page.busy and time.time() - t < 60: root.update(); time.sleep(0.01)
    root.update(); assert not page.busy


def settle(secs=0.5):
    t = time.time()
    while time.time() - t < secs: root.update(); time.sleep(0.02)


names = lambda: [c.path.name for c in page.items]
card = lambda i: page._render_cover(page.items[i].iid)
bar = lambda: page.bar_btn.cget("text")

assert page.tpl and len(page.tpl.slots) == 8 and "8 cards per sheet" in page.lbl_tpl.cget("text") and "3.50" in page.lbl_tpl.cget("text")
assert [s.title.cget("text") for s in page.segments] == ["Covers", "Preview and print", "Cards"]
assert bar() == "Create PDF" and page.bar_btn.cget("state") == "disabled" and "Add comics" in page.meta.cget("text")
# two columns: the covers on the left, the preview and the cards on the right, a divider between
assert page.drop.winfo_rootx() < page.splitter.winfo_rootx() < page.right_wrap.winfo_rootx() and page.drop.compact
w0 = page.right_wrap.winfo_width()
page.splitter._press(type("E", (), {"x_root": 1000})()); page.splitter._drag(type("E", (), {"x_root": 900})()); page.splitter._release(None); root.update()
assert page.right_wrap.winfo_width() > w0 and page.state()["_split_width"] == int(page.right_width)
# the option cards carry pictures that show what each choice does
settle(0.6)
assert set(page.fit_cards._images) == set(ac.FITS) and set(page.turn_cards._images) == set(ac.ROTATIONS)
assert set(page.bg_cards._images) == set(ac.BACKGROUNDS) and set(page.margin_cards._images) == {m for m, _ in pa.MARGINS}
page.fit_cards.pick(ac.FITS[1]); assert page.vars["fit"].get() == ac.FITS[1] and "Fit inside" in page.s3.summary.cget("text")
page.fit_cards.pick(ac.FITS[0])

with tempfile.TemporaryDirectory() as d:
    d = Path(d)
    for i in range(1, 11): cbz(d / "Run" / f"Saga {i:02d}.cbz", red=10 * i)
    (d / "Run" / "Broken 01.cbz").write_bytes(b"not a zip")
    (d / "pic.png").write_bytes(cover()); (d / "notes.txt").write_text("x")
    page.add_paths([d / "Run", d / "pic.png", d / "notes.txt"]); wait()
    print(names()); assert len(names()) == 11 and names()[-1] == "pic.png" and "Broken 01.cbz" not in names()
    assert "1 skipped" in page.status.cget("text") and "Broken 01.cbz" in page.status.cget("text")
    assert "11 covers on 2 sheets (5 empty slots)" in page.meta.cget("text"), page.meta.cget("text")
    assert page.lbl_sheet.cget("text") == "Sheet 1 of 2" and page.s2.summary.cget("text") == "Sheet 1 of 2"
    assert bar() == "Create PDF" and page.bar_btn.cget("state") == "normal" and "2 sheets ready" in page.bar_text.cget("text")
    assert "5 empty slots" in page.note.cget("text") and "Add 5 more" in page.note.cget("text")
    page.add_paths([d / "Run"]); wait(); assert len(names()) == 11 and "1 skipped" in page.status.cget("text")
    page.add_paths([d / "pic.png"]); assert "Nothing new" in page.status.cget("text")

    # each cover is a card: its pictures, its place on the sheets, copies, and the front or back switch
    c0 = card(0)
    assert c0["title"] == "Saga 01.cbz" and c0["sub"] == "Sheet 1 · card 1" and len(c0["images"]) == 2 and c0["image_on"] == 0
    assert [b[0] for b in c0["buttons"]] == ["back", "less", None, "more"] and c0["buttons"][1][1] == "−" and c0["buttons"][3][1] == "+"
    assert card(10)["images"] == [page.items[10].small] and "back" not in [b[0] for b in card(10)["buttons"]], "an image has no back"
    assert card(8)["sub"] == "Sheet 2 · card 1"
    # copies: more cards, later positions, a range in the wording, the sheets recounted
    ids = [c.iid for c in page.items]
    page._card_button(ids[1], "more"); root.update()
    assert page.items[1].copies == 2 and card(1)["sub"] == "Sheet 1 · card 2–3" and card(2)["sub"] == "Sheet 1 · card 4"
    assert "11 covers · 12 cards on 2 sheets (4 empty slots)" in page.meta.cget("text"), page.meta.cget("text")
    page._card_button(ids[1], "less"); page._card_button(ids[1], "less"); assert page.items[1].copies == 1, "never below one"
    for _ in range(60): page._card_button(ids[1], "more")
    assert page.items[1].copies == 50, "never above fifty"
    page._card_button(ids[1], "less"); page._card_button(ids[1], "less"); page._card_button(ids[1], "less")
    for _ in range(60): page._card_button(ids[1], "less")
    assert page.items[1].copies == 1
    # the front / back switch: the preview and the PDF use the page that is on
    c = page.items[0]
    assert not c.use_back and c.shown() is c.thumb and c.can_back
    page._card_button(ids[0], "back"); assert c.use_back and c.shown() is c.back_thumb and card(0)["image_on"] == 1 and card(0)["buttons"][0][1] == "Back"
    page._card_button(ids[0], "back"); assert not c.use_back
    page._card_button(ids[10], "back"); assert not page.items[10].use_back, "an image cannot be turned over"
    # the cards in the list move like the Reading order's (hold and drag, keys, undo)
    page.cards.select(ids[3:6]); page.to_edge(True)
    assert names()[:3] == ["Saga 04.cbz", "Saga 05.cbz", "Saga 06.cbz"] and card(0)["num"] == "1" and card(3)["num"] == "4"
    page.shift(1); assert names()[:4] == ["Saga 01.cbz", "Saga 04.cbz", "Saga 05.cbz", "Saga 06.cbz"]
    page.undo(); page.undo(); assert names()[:2] == ["Saga 01.cbz", "Saga 02.cbz"]
    page.cards.select([page.items[0].iid]); page.to_edge(False); assert names()[-1] == "Saga 01.cbz" and names()[0] == "Saga 02.cbz"
    page.undo()
    page.cards.select([page.items[0].iid, page.items[1].iid]); page.remove(); assert len(page.items) == 9 and len(page.by_iid) == 9 and len(page.cards.order) == 9
    assert "9 covers on 2 sheets (7 empty slots)" in page.meta.cget("text")
    # sheet navigation
    page._go(1); assert page.lbl_sheet.cget("text") == "Sheet 2 of 2" and page.btn_next.cget("state") == "disabled"
    page._go(-1); assert page.btn_prev.cget("state") == "disabled"
    page.clear(); assert page.items == [] and page.bar_btn.cget("state") == "disabled" and page.lbl_sheet.cget("text") == "No sheets yet"
    page.say(""); page.create(); assert "Add some covers" in page.status.cget("text")

    # ---- the preview: the sheet on show, its strip, the empty slots and the selection
    page.add_paths([d / "Run"]); wait(); root.update(); settle(0.5)
    n = len(page.items); assert n == 10
    assert page._geom and page.view.find_all(), "a sheet is drawn"
    ox, oy, sc = page._geom
    slot = lambda k: (int(ox + (page.tpl.slots[k].x + page.tpl.slots[k].w / 2) * sc), int(oy + (page.tpl.slots[k].y + page.tpl.slots[k].h / 2) * sc))
    assert all(page._slot_at(*slot(k)) == k for k in range(8)) and page._slot_at(1, 1) is None
    assert page._cover_at_slot(0) is page.items[0] and page._cover_at_slot(7) is page.items[7]
    page.go = None
    page._go(1); assert page._cover_at_slot(2) is None and page._cover_at_slot(1) is page.items[9] and page._cover_at_slot(0) is page.items[8], "10 covers: two on the second sheet"
    page._go(-1)
    assert "6 empty slots" in page.note.cget("text")
    assert len(page._strip_photos) == 2 and page.strip.find_all(), "a small picture of every sheet"
    cl = lambda k: ((k * page.strip_step()) + 20, 20)
    ev = type("E", (), {})
    e = ev(); e.x, e.y = cl(1); page._strip_click(e); assert page.sheet == 1 and page.lbl_sheet.cget("text") == "Sheet 2 of 2"
    e = ev(); e.x, e.y = cl(0); page._strip_click(e); assert page.sheet == 0
    # clicking a card in the preview selects its cover in the list
    e = ev(); e.x, e.y = slot(2); e.x_root = e.y_root = 0
    page._vpress(e); page._vrelease(e)
    assert page.cards.sel == {page.items[2].iid} and page._marks() == {2}
    # dragging one card onto another swaps the two covers; Undo puts them back
    order0 = list(page.cards.order)
    e = ev(); e.x, e.y = slot(1); e.x_root = e.y_root = 0
    page._vpress(e)
    e2 = ev(); e2.x, e2.y = slot(5); e2.x_root, e2.y_root = page.view.winfo_rootx() + 5, page.view.winfo_rooty() + 5
    page._vmotion(e2); e3 = ev(); e3.x, e3.y = slot(5) ; e3.x_root, e3.y_root = e2.x_root, e2.y_root
    page._vmotion(e3); assert page.view.find_withtag("drag"), "the card it would swap with is outlined"
    page._vrelease(e3); root.update()
    assert page.cards.order[1] == order0[5] and page.cards.order[5] == order0[1] and page.cards.can_undo
    assert page._cover_at_slot(1) is page.by_iid[order0[5]]
    page.undo(); assert page.cards.order == order0
    # dropping on an empty slot, on the same card, or outside does nothing
    page._go(1)
    e = ev(); e.x, e.y = slot(0); e.x_root = e.y_root = 0; page._vpress(e)
    e2 = ev(); e2.x, e2.y = slot(5); e2.x_root, e2.y_root = page.view.winfo_rootx() + 5, page.view.winfo_rooty() + 5
    page._vmotion(e2); page._vmotion(e2); page._vrelease(e2); assert page.cards.order == order0, "slot 6 of sheet 2 is empty"
    page._go(-1)
    # holding a dragged card over a sheet in the strip goes to that sheet, and it can be dropped there
    e = ev(); e.x, e.y = slot(2); e.x_root = e.y_root = 0; page._vpress(e)
    far = ev(); far.x, far.y = slot(2)[0] + 40, slot(2)[1] + 40; far.x_root = far.y_root = 0; page._vmotion(far)
    over = ev(); over.x, over.y = 10, 10; over.x_root = page.strip.winfo_rootx() + page.strip_step() + 20; over.y_root = page.strip.winfo_rooty() + 20
    page._vmotion(over); root.update()
    assert page.sheet == 1, "the strip changed the sheet"
    drop = ev(); drop.x, drop.y = slot(1); drop.x_root = drop.y_root = 0
    page._vmotion(drop); page._vrelease(drop); root.update()
    assert page.cards.order[2] == order0[9] and page.cards.order[9] == order0[2], "swapped across sheets"
    page.undo(); page._go(-1)
    # copies: dragging a cover that has two cards swaps whole covers
    page._card_button(page.items[0].iid, "more"); root.update()
    assert page._cover_at_slot(0) is page._cover_at_slot(1) is page.items[0]
    e = ev(); e.x, e.y = slot(1); e.x_root = e.y_root = 0; page._vpress(e)
    e2 = ev(); e2.x, e2.y = slot(0); e2.x_root, e2.y_root = page.view.winfo_rootx() + 5, page.view.winfo_rooty() + 5
    page._vmotion(e2); page._vmotion(e2); page._vrelease(e2); assert page.cards.order == order0, "the same cover: nothing to swap"
    page._card_button(page.items[0].iid, "less")
    # the empty-slot note
    for k in range(6): page._card_button(page.items[k].iid, "more")
    root.update()
    assert page.note.cget("text") == "Every slot on the last sheet is filled.", page.note.cget("text")
    for k in range(6): page._card_button(page.items[k].iid, "less")

    # ---- layout: the covers beside a preview that is much bigger than the old narrow strip
    assert page.cards.winfo_rootx() + page.cards.winfo_width() <= page.splitter.winfo_rootx() + 4
    assert page.view.winfo_width() > 330 and page.view.winfo_height() > 300
    # ---- full screen viewer
    assert page.btn_full.cget("state") == "normal"
    page.open_full()
    for _ in range(40): root.update(); time.sleep(0.05)
    win = page._full; assert win is not None and win.winfo_exists()
    assert page._f_label.cget("text").startswith("Sheet 1 of")
    fw, fh = win.winfo_width(), win.winfo_height()
    k = page._scaling(page._f_image); ph = page._f_photo._size[1] * k; pw = page._f_photo._size[0] * k
    assert fw >= 800 and fh >= 600 and ph > page.view.winfo_height() * 1.1, "much larger than the side preview"
    assert ph <= page._f_image.winfo_height() and pw <= page._f_image.winfo_width(), "the sheet fits inside the window"
    n_sheets = ac.sheet_count(sum(page._counts()), page.tpl)
    page.open_full(); assert page._full is win
    if n_sheets > 1:
        win.event_generate("<Right>"); root.update(); assert page.sheet == 1 and "Sheet 2" in page._f_label.cget("text") and "Sheet 2" in page.lbl_sheet.cget("text")
        win.event_generate("<Left>"); root.update(); assert page.sheet == 0
    win.event_generate("<Escape>"); root.update(); assert page._full is None and not win.winfo_exists()
    page.clear(); page.open_full(); assert page._full is None
    assert page.btn_full.cget("state") == "disabled"
    page.add_paths([d / "Run"]); wait()

    # ---- outline colour options
    page.vars["background"].set("Black"); root.update()
    assert page._opts()["outline_color"] == ac.AUTO_COLOR and ac.outline_rgb(page._opts()) == (255, 255, 255), "automatic: white lines on black"
    page.vars["outline_color"].set(ac.CUSTOM_COLOR); page.vars["outline_hex"].set("zz9"); root.update()
    assert "Not a colour" in page.lbl_hex.cget("text") and ac.outline_rgb(page._opts()) == (255, 255, 255)
    page.vars["outline_hex"].set("#FF8800"); root.update(); assert "Used when" in page.lbl_hex.cget("text") and ac.outline_rgb(page._opts()) == (255, 136, 0)
    page.vars["outline_width"].set("2"); root.update()
    assert page._opts()["outline_width"] == 2.0
    page.vars["outline_width"].set("abc"); assert page._opts()["outline_width"] == 0.0
    page.vars["outline_width"].set("2")
    out6 = d / "out" / "colour.pdf"; (d / "out").mkdir(exist_ok=True); filedialog.asksaveasfilename = lambda **k: str(out6)
    page.vars["open_after"].set(False); page.vars["dpi"].set("Draft (150 dpi)"); page.create(); wait()
    txt = PdfReader(str(out6)).pages[0].get_contents().get_data().decode("latin1")
    assert stroke(txt) == (1.0, 0.533, 0.0, 2.0), (stroke(txt), txt[-200:])
    page.vars["background"].set("White"); page.vars["outline_color"].set(ac.AUTO_COLOR); page.vars["outline_width"].set(""); root.update()

    # ---- create the PDF: it follows the order, the copies and the front / back switch
    page.clear(); page.add_paths([d / "Run"]); wait()
    page._card_button(page.items[0].iid, "back")                      # Saga 01 prints its last page
    page._card_button(page.items[1].iid, "more")                      # Saga 02 prints twice
    page.vars["open_after"].set(False); page.vars["dpi"].set("Draft (150 dpi)")
    out = d / "out" / "cards.pdf"; filedialog.asksaveasfilename = lambda **k: str(out)
    page.create(); assert page.busy == "render" and page.bar_btn.cget("text") == "Stop"; wait()
    print(page.status.cget("text"))
    assert out.exists() and "Saved 2 sheets" in page.status.cget("text") and page.vars["out_dir"].get() == str(d / "out")
    assert page._side_labels == ["Open PDF", "Open folder"] and page.bar_btn.cget("text") == "Create PDF"
    r = PdfReader(str(out)); assert len(r.pages) == 2 and (float(r.pages[0].mediabox.width), float(r.pages[0].mediabox.height)) == (612, 792)
    assert "40.5 576 252 180 re" in r.pages[0].get_contents().get_data().decode("latin1")
    px = r.pages[0].images[0].image.getpixel((int((40.5 + 20) * 150 / 72), int((36 + 90) * 150 / 72)))
    assert px[0] > 50, ("Saga 01's last page is the brighter red", px)
    # the copies: Saga 02 fills two slots
    img0 = r.pages[0].images[0].image; w0 = img0.width
    s1 = img0.getpixel((int((40.5 + 252 + 40.5 + 20) * 150 / 72) if False else int((40.5 + 20) * 150 / 72), int((36 + 180 + 20 + 90) * 150 / 72)))
    assert s1 is not None
    # source option and outlines off
    page.clear(); page.vars["source"].set(ac.SOURCES[1]); page.add_paths([d / "Run" / "Saga 01.cbz"]); wait()
    assert page.items[0].use_back, "new covers follow the 'covers you add next come from' setting"
    page.vars["outlines"].set(False); out2 = d / "out" / "back.pdf"; filedialog.asksaveasfilename = lambda **k: str(out2)
    page.create(); wait(); r2 = PdfReader(str(out2)); assert len(r2.pages) == 1 and " re" not in r2.pages[0].get_contents().get_data().decode("latin1")
    page.vars["source"].set(ac.SOURCES[0]); page.vars["outlines"].set(True)
    # cancelled dialog: nothing happens
    filedialog.asksaveasfilename = lambda **k: ""; page.create(); assert not page.busy

    # ---- templates
    w = PdfWriter(); w.add_blank_page(612, 792); blank = d / "blank.pdf"; w.write(open(blank, "wb"))
    page.vars["template"].set(str(blank)); root.update()
    assert page.tpl is None and "No card outlines" in page.lbl_tpl.cget("text") and page.bar_btn.cget("state") == "disabled"
    page.say(""); page.create(); assert "can't be used" in page.status.cget("text") or page.bar_btn.cget("state") == "disabled"
    page.reset_template(); root.update(); assert page.tpl and len(page.tpl.slots) == 8
    page.vars["template"].set(str(d / "missing.pdf")); root.update(); assert page.tpl and len(page.tpl.slots) == 8
    page.vars["template"].set("")

    # ---- stop while rendering leaves nothing behind
    page.clear(); page.add_paths([d / "Run"]); wait()
    page.vars["dpi"].set("High (600 dpi)"); out3 = d / "out" / "stopped.pdf"; filedialog.asksaveasfilename = lambda **k: str(out3)
    page.create(); page.stop_action(); wait()
    assert not out3.exists() and "Stopped" in page.status.cget("text"), page.status.cget("text")
    # ---- settings and theme
    st = page.state(); page.restore(st); assert st["fit"] == ac.FITS[0] and st["dpi"] == "High (600 dpi)" and "copies" not in st
    ctk.set_appearance_mode("dark"); page.apply_theme(); root.update()
    for fit in ac.FITS:
        for rot in ac.ROTATIONS:
            page.vars["fit"].set(fit); page.vars["rotate"].set(rot); root.update(); time.sleep(0.1); root.update()
root.destroy()

# ---- the whole app
import comic_tool
app = comic_tool.App(); assert "aceo" in app.pages and any(h == "ACEO Cards" for h, _ in comic_tool.GROUPS)
app.show("aceo"); app.update()
class Ev: pass
e = Ev(); e.data = "{C:/does/not/exist.cbz}"; app.on_drop(e)
assert {"library", "recent"} <= set(app.pages["aceo"].drop.buttons)
app.destroy()
print("ACEO UI OK")

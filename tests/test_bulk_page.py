"""Bulk folder on the shared page shell: segments with summaries and auto-advance, the Advanced block, the lazy
table, the review (counts, statuses, dry run, retry), the footer, scrolling, hovering, restore."""
import io, sys, tempfile, time, types, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import customtkinter as ctk
from PIL import Image

import flow_kit as fk
import page_bulk as pb
import ui_kit as uk
from comic_core import ORG_FLAT, ORG_SERIES, WHERE_BESIDE, WHERE_CUSTOM, WHERE_SUB


def cbz(p, pages=2):
    p.parent.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO(); Image.new("RGB", (40, 60), "red").save(buf, "JPEG")
    with zipfile.ZipFile(p, "w") as z:
        for i in range(pages): z.writestr(f"{i}.jpg", buf.getvalue())
    return p


def settle(win, cond, secs=20):
    t = time.time()
    while not cond() and time.time() - t < secs:
        win.update()
    win.update(); assert cond(), "timed out"


root = ctk.CTk(); root.geometry("1200x780")
pg = pb.BulkPage(root); pg.pack(fill="both", expand=True); root.update()
d = Path(tempfile.mkdtemp())
for s in ("Saga", "Batman"):
    for n in (1, 2, 3):
        cbz(d / s / f"{s} 00{n} (2012).cbz")

def states(): return [c.state for c in pg.segments]
def bar(): return pg.bar_btn.cget("text")
def statuses(): return [pg.review.tree.item(i)["values"][2] for i in pg.review.tree.get_children()]

# nothing chosen yet: Comics is the only thing to do, the footer button says why it cannot be pressed
assert states() == ["active", "locked", "locked"] and pg.bar_btn.cget("state") == "disabled"
assert bar() == "Choose comics first" and "begin" in pg.bar_text.cget("text")
assert not pg.s2.body.winfo_ismapped(), "locked segments stay shut"
assert [s.title.cget("text") for s in pg.segments] == ["Comics", "Covers", "Review"], "labels name the job, no step numbers"

# choosing comics: Comics folds to a summary and Covers opens by itself
pg.set_folder(d); root.update()
assert states() == ["done", "active", "idle"] and bar() == "Extract 6 covers" and pg.bar_btn.cget("state") == "normal"
assert not pg.s1.body.winfo_ismapped() and pg.s2.body.winfo_ismapped(), "auto-advance folds the finished segment"
assert pg.s1.summary.cget("text").startswith("6 comics · 2 series") and str(d) in pg.s1.summary.cget("text")
kids = pg.comics.tree.get_children()
assert len(kids) == 6 and pg.comics.tree.item(kids[0])["values"][0].startswith("Batman 001")
assert pg.s2.summary.cget("text") == "One covers folder · Original · replace existing"
pg.s1.toggle(); root.update(); assert pg.s1.body.winfo_ismapped() and len(pg.files) == 6, "a folded segment opens again"

# the Review: counts in plain words, one row per comic with a status
settle(root, lambda: pg.checking is None)
assert pg.headline.cget("text") == "Will save 6 covers", pg.headline.cget("text")
assert "Saved in:" in pg.subline.cget("text") and "Covers" in pg.subline.cget("text")
assert statuses() == ["New"] * 6 and len(pg.review.tree.get_children()) == 6
assert pg.exist_label.cget("text") == "" and not pg.details_btn.winfo_ismapped()
assert pg.s3.summary.cget("text") == "6 covers to write"

# the cards set the real settings, and the advanced menus move the cards
pg.recipe.set("series"); root.update()
assert (pg.vars["where"].get(), pg.vars["organize"].get()) == (WHERE_SUB, ORG_SERIES)
pg.recipe.set("beside"); root.update()
assert pg.vars["where"].get() == WHERE_BESIDE and "Next to each comic" in pg.subline.cget("text")
pg.recipe.set("choose"); root.update()
assert pg.vars["where"].get() == WHERE_CUSTOM and pg.choose_row.winfo_ismapped()
pg.vars["where"].set(WHERE_SUB); pg.vars["organize"].set(ORG_FLAT); root.update()
assert pg.recipe.get() == "folder" and not pg.choose_row.winfo_ismapped()
pg.vars["organize"].set("Mirror folder structure"); root.update()
assert pg.recipe.get() == "" and pg.custom_note.winfo_ismapped(), "a layout only the advanced menus make has no card"
pg.vars["organize"].set(ORG_FLAT); root.update()
assert pg.cards.cards["series"][2].cget("text").startswith("e.g. ") and "Batman" in pg.cards.cards["series"][2].cget("text")

# Advanced options: shut by default, counts what differs from the defaults
assert not pg.adv.opened and pg.adv.changed == 0 and pg.adv.head.cget("text").strip().endswith("Advanced options")
pg.vars["format"].set("JPG"); root.update()
assert pg.adv.changed == 1 and "1 changed" in pg.adv.head.cget("text")
pg.vars["quality"].set(80); root.update(); assert pg.adv.changed == 2
pg.vars["format"].set("Original"); pg.vars["quality"].set(90); root.update(); assert pg.adv.changed == 0
pg.adv.toggle(); root.update(); assert pg.adv.body.winfo_ismapped(); pg.adv.toggle()
pg.vars["format"].set("JPG"); root.update()
assert pg.review.tree.item(pg.review.tree.get_children()[0])["values"][1].endswith(".jpg")
assert "JPG" in pg.s2.summary.cget("text")

# a custom folder without a path stays put with a plain message
pg.recipe.set("choose"); root.update()
pg.start(); root.update()
assert pg.q is None and "Choose a folder" in pg.status.cget("text")
pg.recipe.set("folder"); pg.vars["format"].set("Original"); root.update()

# Review the covers folds Covers and opens Review
pg.go_review(); root.update()
assert states() == ["done", "done", "active"] and pg.s3.body.winfo_ismapped() and not pg.s2.body.winfo_ismapped()
assert pg.problems.winfo_height() <= 10, "an empty problems list takes no room (an empty frame is 200 px tall by default)"

# dry run: statuses say what would happen, nothing is written
pg.dry_run(); root.update()
assert pg.headline.cget("text").startswith("Dry run") and set(statuses()) == {"Would save"}
assert not (d / "Covers").exists() and "Back to normal" in [b.cget("text") for b in pg.side_row.winfo_children()]
pg.leave_dry(); root.update(); assert set(statuses()) == {"New"}

# run: Stop shows while working, then the result appears
pg.start()   # (no update here: six tiny files would finish at once)
assert pg.q is not None and bar() == "Stop" and states()[1] == "done" and states()[2] == "active"
settle(root, lambda: pg.q is None)
assert pg.result == {"saved": 6, "skipped": 0, "failed": 0, "stopped": False}
assert states() == ["done", "done", "done"] and pg.result_box.winfo_ismapped()
assert bar() == "Open the covers folder" and pg.bar_btn.cget("state") == "normal" and "6 covers saved" in pg.bar_text.cget("text")
assert "6 covers saved" in pg.result_title.cget("text") and "Nothing went wrong" in pg.result_sub.cget("text")
assert sorted(p.name for p in (d / "Covers").glob("*.jpg")) == sorted(p.stem + ".jpg" for p in d.rglob("*.cbz"))
assert set(statuses()) == {"Exists"} and pg.exist_label.cget("text") == "Existing covers: 6" and pg.details_btn.winfo_ismapped()
assert pg.log.winfo_ismapped() and pg.log_label.winfo_ismapped()
side = [b.cget("text") for b in pg.side_row.winfo_children()]
assert "Extract again" in side and "Do another folder" in side and "Retry" not in " ".join(side)

# running again: skipped covers are explained, and Dry run says what each will do
pg.vars["conflict"].set("Skip"); pg.again(); root.update()
assert bar() == "Extract 6 covers" and pg.result is None
assert "6 already exist and stay as they are" in pg.headline.cget("text")
pg.dry_run(); root.update(); assert set(statuses()) == {"Would skip"}; pg.leave_dry()
pg.start(); settle(root, lambda: pg.q is None)
assert pg.result["skipped"] == 6 and "already existed" in pg.result_sub.cget("text")

# the Details window lists the covers that exist and what happens to each
pg.show_existing(); root.update()
top = [w for w in pg.winfo_children() if isinstance(w, ctk.CTkToplevel)][-1]
table = [w for w in top.winfo_children() if isinstance(w, fk.LazyTable)][0]
assert len(table.all) == 6 and table.all[0][2] == "Left alone"
top.destroy()

# Do another folder starts over
pg.reset(); root.update()
assert states() == ["active", "locked", "locked"] and pg.files == [] and pg.folder is None and bar() == "Choose comics first"

# an unreadable comic is found before the run, named in plain words, and Retry runs only it
bad = d / "Broken" / "Broken 001.cbz"; bad.parent.mkdir()
with zipfile.ZipFile(bad, "w") as z: z.writestr("notes.txt", "no pages in here")  # a zip, but nothing to use as a cover
pg.vars["conflict"].set("Overwrite")
pg.set_folder(d / "Broken"); root.update(); settle(root, lambda: pg.checking is None)
assert "1 unreadable" in pg.headline.cget("text") and statuses() == ["Unreadable"]
assert any("Broken 001.cbz" in w.cget("text") for w in pg.problems.winfo_children())
pg.start(); settle(root, lambda: pg.q is None)
assert pg.result["failed"] == 1 and len(pg.failed) == 1 and "Retry 1 failed" in [b.cget("text") for b in pg.side_row.winfo_children()]
pg.retry(); settle(root, lambda: pg.q is None); assert pg.result["failed"] == 1 and pg.result["saved"] == 0

# picked files and per-folder settings
pg.reset(); one = cbz(d / "Solo" / "Solo 001.cbz"); two = cbz(d / "Solo" / "Solo 002.cbz")
pg.set_files([one, two, d / "Solo" / "notes.txt"]); root.update()
assert pg.s1.summary.cget("text").startswith("2 comics") and "comics you picked" in pg.s1.summary.cget("text") and bar() == "Extract 2 covers"
assert pg.primary_action() is True; settle(root, lambda: pg.q is None)
pg.reset(); pg.set_folder(d); pg.vars["format"].set("PNG"); root.update()
pg.reset(); pg.set_folder(d / "Solo"); pg.vars["format"].set("WebP"); root.update()
pg.reset(); pg.set_folder(d); root.update()
assert pg.vars["format"].get() == "PNG", "each folder remembers the settings last used with it"
saved = pg.state(); assert saved["format"] == "PNG" and str(d) in saved["_by_folder"] and saved["_auto_advance"] is True

# auto-advance can be switched off: finished segments stay open and nothing opens by itself
pg.reset(); pg.auto.set(False); pg.set_folder(d); root.update()
assert pg.s1.state == "done" and pg.s1.opened and pg.s1.body.winfo_ismapped(), "off: nothing folds"
pg.auto.set(True)

# restore keeps known settings and ignores unknown ones
pg.restore({"format": "WebP", "where": "nonsense", "organize": ORG_SERIES, "_auto_advance": False, "_by_folder": {"x": {"format": "PNG"}}})
root.update()
assert pg.vars["format"].get() == "WebP" and pg.vars["where"].get() != "nonsense" and pg.auto.get() is False and "x" in pg.memory
pg.auto.set(True)

# show covers: small pictures load in the background for the rows that are drawn
pg.reset(); pg.set_folder(d); root.update(); settle(root, lambda: pg.checking is None)
pg.covers_on.set(True)
first = pg.review.tree.get_children()[0]
settle(root, lambda: bool(pg.review.tree.item(first, "image")), 20)
assert pg.review.tree.column("#0", "width") > 0
pg.covers_on.set(False); root.update(); assert pg.review.tree.column("#0", "width") == 0

# the lazy table: a long list opens at once and loads more as you scroll; the filter searches every column
lt = fk.LazyTable(root, [("a", "Name", 200, True), ("b", "Kind", 100, False)], rows=6)
lt.pack(); big = [(f"Comic {i:04d}", "even" if i % 2 == 0 else "odd") for i in range(1200)]
lt.set_rows(big); root.update()
assert len(lt.tree.get_children()) == fk.CHUNK and lt.count.cget("text") == "1200"
lt.tree.yview_moveto(1.0); settle(root, lambda: len(lt.tree.get_children()) > fk.CHUNK, 5)
def scroll_down():
    lt.tree.yview_moveto(1.0)  # the user keeps scrolling to the bottom; each time more rows arrive
    return len(lt.tree.get_children()) == 1200
settle(root, scroll_down, 15)
lt.query.set("0042"); root.update()
assert [lt.tree.item(i)["values"][0] for i in lt.tree.get_children()] == ["Comic 0042"] and lt.count.cget("text") == "1 of 1200"
lt.query.set("odd"); root.update()
assert len(lt.view) == 600 and len(lt.tree.get_children()) == fk.CHUNK, "a long filtered list is still loaded in chunks"
lt.query.set(""); lt.set_rows(big[:10]); root.update(); assert len(lt.tree.get_children()) == 10, "short lists are drawn whole"
lt.destroy()

# scrolling works: the scroll region is set, the page is taller than the window, the wheel moves it
pg.reset(); pg.set_folder(d); root.update(); root.update()
for s in pg.segments: s.set_open(True)
root.update()
canvas = pg.scroll._parent_canvas
assert canvas.cget("scrollregion"), "an empty scroll region means the wheel does nothing"
assert canvas.yview() != (0.0, 1.0), canvas.yview()
canvas.yview_moveto(0); root.update()
child = pg.cards.cards["series"][0]
assert pg.scroll._check_if_valid_scroll(child) and pg.scroll._check_if_valid_scroll(pg.review.tree)
before = canvas.yview()[0]
pg.scroll._mouse_wheel_all(types.SimpleNamespace(widget=child, delta=-120, num=0)); root.update()
assert canvas.yview()[0] > before, "the mouse wheel moves the page"
pg.reveal(pg.s3); root.update(); assert canvas.yview()[0] > 0
pg.reveal(pg.s1); root.update(); assert canvas.yview()[0] == 0.0
# the footer stays visible whatever the scroll position
assert pg.footer.winfo_ismapped() and pg.footer.winfo_rooty() + pg.footer.winfo_height() <= root.winfo_rooty() + root.winfo_height() + 2

# hovering: controls find their hover hooks through the pointer check, and sliding keeps the scaled layout
btn = pg.bar_btn
target, hooks = uk._hover_target(btn.inner._text_label)
assert target is btn and hooks
rest = btn.slot.grid_info()["padx"]
hooks[0](); root.update(); assert btn.slot.grid_info()["padx"] != rest and btn._hot
hooks[1](); root.update(); assert btn.slot.grid_info()["padx"] == rest and not btn._hot, "cooling restores the exact padding"
card = pg.cards.cards["beside"][0]
t2, h2 = uk._hover_target(pg.cards.cards["beside"][1])
assert t2 is card
h2[0](); assert str(card.cget("fg_color")) != str(uk.RAISED), "an unchosen card lifts under the pointer"
h2[1](); assert card.cget("fg_color") == uk.RAISED
chosen = pg.cards.cards[pg.recipe.get()][0]
assert chosen.cget("fg_color") == uk.PINK
uk._hover_target(pg.s2.title)[1][0](); assert pg.s2.inner.cget("border_color") == uk.PINK
uk._hover_target(pg.s1.title)[1][1]()
root.destroy()
print("bulk page OK")

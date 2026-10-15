"""Bulk folder as three steps with everything visible: the comics found, settings beside a live preview, a review and
the run; the pinned action bar, scrolling, hovering, recipes, results, restore."""
import io, sys, tempfile, time, types, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import customtkinter as ctk
from PIL import Image

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

def states(): return [(c.state) for c in pg.steps]
def bar(): return pg.bar_btn.cget("text")

# nothing chosen yet: step 1 is the only thing to do, the pinned button says why it cannot be pressed
assert states() == ["active", "locked", "locked"] and pg.bar_btn.cget("state") == "disabled"
assert bar() == "Choose comics first" and pg.steps[0].state_tag == "Start here"
assert not pg.s2.body.winfo_ismapped(), "locked steps stay shut"

# choosing comics shows what was found, moves you to step 2, and the pinned button names the count
pg.set_folder(d); root.update()
assert states() == ["done", "active", "idle"] and bar() == "Extract 6 covers" and pg.bar_btn.cget("state") == "normal"
assert "6 comics found" in pg.meta.cget("text")
assert pg.found["Comics"].cget("text") == "6" and pg.found["Series"].cget("text") == "2" and ".cbz" in pg.found["File types"].cget("text")
assert len(pg.table.get_children()) == 6 and pg.table.item(pg.table.get_children()[0])["values"][0].startswith("Batman 001")
assert all(s.body.winfo_ismapped() for s in pg.steps), "every step shows its details at once"
assert pg.bar_text.cget("text").startswith("Step 2 of 3") and "preview" in pg.bar_text.cget("text") and pg.bar_btn.cget("text") == "Extract 6 covers"
# every step says in one line what to do in it, and step 3 says nothing happens until the bar button is pressed
assert "Everything that was found" in pg.s1.hint.cget("text") and "preview" in pg.s2.hint.cget("text")
assert "yellow button" in pg.s3.hint.cget("text") and pg.s2.state_tag == "You are here" and pg.s3.state_tag == "Next"
# step 3 before a run lists what will happen and reassures that comics are not changed
assert pg.ready.winfo_ismapped() and "6 covers will be saved" in pg.checks[0].cget("text")
assert any("never changed" in c.cget("text") for c in pg.checks) and not any("⚠" in c.cget("text") for c in pg.checks)
assert not pg.log.winfo_ismapped() and not pg.progress.winfo_ismapped(), "the file list and progress wait for a run"
assert {pg.preview.item(i)["values"][2] for i in pg.preview.get_children()} == {"New"}

# clicking a step's header folds and unfolds it (nothing is lost)
pg.s1.toggle(); root.update()
assert not pg.s1.body.winfo_ismapped() and len(pg.files) == 6
pg.s1.toggle(); root.update(); assert pg.s1.body.winfo_ismapped()

# the live preview: where each cover goes, how many, and what already exists
assert len(pg.preview.get_children()) == 6 and pg.plan_facts["Covers"].cget("text") == "6"
assert pg.plan_facts["Already there"].cget("text") == "None"
assert "Covers" in pg.plan_facts["Saved in"].cget("text")

# the cards set the real settings, and the advanced menus move the cards
pg.recipe.set("series"); root.update()
assert (pg.vars["where"].get(), pg.vars["organize"].get()) == (WHERE_SUB, ORG_SERIES)
pg.recipe.set("beside"); root.update()
assert pg.vars["where"].get() == WHERE_BESIDE and pg.plan_facts["Saved in"].cget("text") == "Next to each comic"
pg.recipe.set("choose"); root.update()
assert pg.vars["where"].get() == WHERE_CUSTOM and pg.choose_row.winfo_ismapped()
pg.vars["where"].set(WHERE_SUB); pg.vars["organize"].set(ORG_FLAT); root.update()
assert pg.recipe.get() == "folder" and not pg.choose_row.winfo_ismapped()
pg.vars["organize"].set("Mirror folder structure"); root.update()
assert pg.recipe.get() == "" and pg.custom_note.winfo_ismapped(), "a layout only the advanced menus make has no card"
pg.vars["organize"].set(ORG_FLAT); root.update()
assert pg.cards.cards["series"][2].cget("text").startswith("e.g. ") and "Batman" in pg.cards.cards["series"][2].cget("text")
pg.vars["format"].set("JPG"); root.update()
assert "JPG" in pg._sentence() and "JPG" in pg.checks[0].cget("text") and "quality" in pg.checks[0].cget("text")
assert pg.preview.item(pg.preview.get_children()[0])["values"][1].endswith(".jpg")

# a custom folder without a path stays on step 2 with a plain message
pg.recipe.set("choose"); root.update()
pg.start(); root.update()
assert pg.q is None and "Choose a folder" in pg.status.cget("text")
pg.recipe.set("folder"); pg.vars["format"].set("Original"); root.update()

# run: Stop shows while working, then the result and the next step appear
pg.start()   # (no update here: six tiny files would finish at once)
assert pg.q is not None and bar() == "Stop" and states()[1] == "done" and pg.steps[2].state_tag == "Working"
settle(root, lambda: pg.q is None)
assert pg.result == {"saved": 6, "skipped": 0, "failed": 0, "stopped": False}
assert pg.steps[2].state_tag == "Finished" and pg.result_box.winfo_ismapped()
assert bar() == "Open the covers folder" and pg.bar_btn.cget("state") == "normal" and "6 covers saved" in pg.bar_text.cget("text")
assert "6 covers saved" in pg.result_title.cget("text") and "Nothing went wrong" in pg.result_sub.cget("text")
assert sorted(p.name for p in (d / "Covers").glob("*.jpg")) == sorted(p.stem + ".jpg" for p in d.rglob("*.cbz"))
assert pg.plan_facts["Already there"].cget("text").startswith("6 of 6"), "the preview now sees the saved covers"
assert {pg.preview.item(i)["values"][2] for i in pg.preview.get_children()} == {"Replaces"}
assert pg.log.winfo_ismapped() and pg.log_label.winfo_ismapped() and not pg.ready.winfo_ismapped()

# running again over the same files: skipped covers are explained in plain words
pg.vars["conflict"].set("Skip"); pg.again(); root.update()
assert bar() == "Extract 6 covers" and pg.result is None
assert any("⚠" in c.cget("text") and "6 of 6" in c.cget("text") and "left alone" in c.cget("text") for c in pg.checks), "a warning before the run"
assert {pg.preview.item(i)["values"][2] for i in pg.preview.get_children()} == {"Skipped"}
pg.start(); settle(root, lambda: pg.q is None)
assert pg.result["skipped"] == 6 and "already existed" in pg.result_sub.cget("text")

# Do another folder starts over
pg.reset(); root.update()
assert states() == ["active", "locked", "locked"] and pg.files == [] and pg.folder is None and bar() == "Choose comics first"

# picked files, shortcuts and settings
one = cbz(d / "Solo" / "Solo 001.cbz"); two = cbz(d / "Solo" / "Solo 002.cbz")
pg.set_files([one, two, d / "Solo" / "notes.txt"]); root.update()
assert "2 comics chosen" in pg.meta.cget("text") and bar() == "Extract 2 covers"
assert "comics you picked" in pg.found["From"].cget("text")
assert pg.primary_action() is True; settle(root, lambda: pg.q is None)
saved = pg.state(); assert saved["format"] == "Original" and "_side_width" not in saved
pg.restore({"format": "PNG", "where": "nonsense", "organize": ORG_SERIES}); root.update()
assert pg.vars["format"].get() == "PNG" and pg.vars["where"].get() != "nonsense"

# scrolling works: the scroll region is set, the page is taller than the window, the wheel moves it
pg.reset(); pg.set_folder(d); root.update(); root.update()
canvas = pg.scroll._parent_canvas
assert canvas.cget("scrollregion"), "an empty scroll region means the wheel does nothing"
assert canvas.yview() != (0.0, 1.0), canvas.yview()
canvas.yview_moveto(0); root.update()
child = pg.cards.cards["series"][0]
assert pg.scroll._check_if_valid_scroll(child) and pg.scroll._check_if_valid_scroll(pg.preview)
before = canvas.yview()[0]
pg.scroll._mouse_wheel_all(types.SimpleNamespace(widget=child, delta=-120, num=0)); root.update()
assert canvas.yview()[0] > before, "the mouse wheel moves the page"
pg.reveal(pg.s3); root.update(); assert canvas.yview()[0] > 0
pg.reveal(pg.s1); root.update(); assert canvas.yview()[0] == 0.0
# the pinned bar stays visible whatever the scroll position
assert pg.bar.winfo_ismapped() and pg.bar.winfo_rooty() + pg.bar.winfo_height() <= root.winfo_rooty() + root.winfo_height() + 2

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

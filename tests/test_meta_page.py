"""The Metadata repair editor on the page shell, in two columns (comics on the left, the fields of the selection and the
list of pending changes on the right; the footer only scrolls to the changes, nothing is written until Confirm, and typing
does not redraw the page): the table of what each comic holds, the one-comic and many-comics forms (automatic and manual),
suggestions, the offer to the rest of a series, fill from file names, removing issue numbers, the live list of pending
changes, saving after a confirmation, locked .cbr files, and opening it from another tool."""
import io, sys, tempfile, time, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import customtkinter as ctk
from PIL import Image

import archive_tools as at
import page_metadata as pm
from rename_core import read_comicinfo


def cbz(p, ci=None):
    p.parent.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO(); Image.new("RGB", (40, 60), "blue").save(buf, "JPEG")
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("0.jpg", buf.getvalue())
    if ci:
        at.apply_metadata(p, ci, False)
    return p


def settle(win, cond, secs=20):
    t = time.time()
    while not cond() and time.time() - t < secs:
        win.update()
    win.update(); assert cond(), "timed out"


root = ctk.CTk(); root.geometry("1250x900")
pg = pm.MetadataPage(root); pg.pack(fill="both", expand=True); root.update()
d = Path(tempfile.mkdtemp())
b1 = cbz(d / "DC" / "Batman 001 (2016).cbz", {"series": "Batman", "issue": "1", "year": "2016"})
b2 = cbz(d / "DC" / "Batman 002 (2016).cbz")
b3 = cbz(d / "DC" / "Batman 003 (2016).cbz")
x1 = cbz(d / "Marvel" / "X-Men 001 (1991).cbz", {"series": "X-Men", "issue": "1", "year": "1991", "publisher": "Marvel"})
old = d / "Old" / "Real 01.cbr"; old.parent.mkdir(); cbz(old)

def summary(): return pg.left_summary.cget("text")
def foot(): return pg.bar_btn.cget("text")
def side(): return [b.cget("text") for b in pg.side_row.winfo_children()]
def select(*idx):
    pg.comics.tree.selection_set([str(i) for i in idx]); root.update()
def table(): return [pg.comics.tree.item(i, "values") for i in pg.comics.tree.get_children()]

# nothing chosen: two columns side by side, the footer says why it cannot save
assert not pg.segments and pg.scroll is None, "no scrolling column of segments"
assert pg.comics.winfo_ismapped() and pg.right.winfo_ismapped() and pg.comics.winfo_rootx() < pg.right.winfo_rootx(), "comics left, fields right"
assert pg.changes_box.winfo_ismapped() and pg.review_head.cget("text") == "No changes yet", "the changes list is part of the right column"
assert pg.empty.winfo_ismapped() and "Choose a folder" in pg.empty.cget("text") and pg.mode.get() == pm.AUTO
assert foot() == "Review changes" and pg.bar_btn.cget("state") == "disabled"
assert int(pg.bar_btn.cget("height")) == 32 and pg.footer.winfo_height() / pg._get_widget_scaling() <= 52, "a slim footer"

# choosing a folder lists every comic with what it holds; a .cbr is listed but locked
pg.set_folder(d); settle(pg, lambda: not pg.busy and len(pg.rows) == 5)
assert [r.path for r in pg.rows] == [b1, b2, b3, x1, old] and [r.locked for r in pg.rows] == [False] * 4 + [True]
rows = table()
assert rows[0][1] == "Batman 001 (2016).cbz" and rows[0][2] == "Batman" and rows[0][3] == "1" and rows[0][6] == pm.DASH, rows[0]
assert rows[0][0] == "!" and rows[3][0] == "✓" and rows[4][0] == "·" and rows[4][7] == "Locked (.cbr)"
assert summary() == "5 comics · 3 need attention", summary()
assert pg.cbr_note.winfo_ismapped() and "1 .cbr file" in pg.cbr_label.cget("text")
assert pg.empty.winfo_ismapped() and "Select a comic on the left" in pg.empty.cget("text")
assert pg.comics.winfo_height() > 250, "the list uses the height of the page"

# the Show menu narrows the table without losing the comics
pg.vars["view"].set("No publisher"); root.update()
assert [r.path.name for r in pg.shown] == [b1.name, b2.name, b3.name, old.name] and len(table()) == 4
assert summary() == "4 of 5 · No publisher"
pg.vars["view"].set("All comics"); root.update(); assert len(pg.shown) == 5

# one comic selected: the one-comic form fills in, with a cover, its place in the list and suggestions taken from the library
select(1)
assert pg.one.winfo_ismapped() and not pg.many.winfo_ismapped() and not pg.empty.winfo_ismapped(), "the form follows the selection at once"
assert pg.one.winfo_rooty() < pg.changes_box.winfo_rooty(), "the form sits above the changes"
pg.mode.set(pm.ONE); root.update()
assert pg.one.winfo_ismapped() and not pg.many.winfo_ismapped() and pg.target_label.cget("text") == "Editing one comic"
assert pg.vars_one["series"].get() == "" and pg.vars_one["year"].get() == "", "Batman 002 has no ComicInfo.xml yet"
assert pg.file_label.cget("text") == "Batman 002 (2016).cbz" and pg.position.cget("text") == "2 of 5" and pg.cover_image is not None
chips = [w.cget("text") for w in pg.chip_boxes[(False, "publisher")].winfo_children()]
assert chips == ["Marvel"], chips            # the only publisher in the library
names = [w.cget("text") for w in pg.chip_boxes[(False, "series")].winfo_children()]
assert "Batman" in names, names               # from the same folder and the file name
issue_chips = [w.cget("text") for w in pg.chip_boxes[(False, "issue")].winfo_children()]
assert issue_chips == ["2"], issue_chips      # read from the file name
pg.chip_boxes[(False, "issue")].winfo_children()[0].invoke(); root.update()
assert pg.vars_one["issue"].get() == "2" and pg.shown[1].pending == {"issue": "2"}, "a chip fills the field and records the edit"
assert table()[1][3] == "2" and table()[1][7] == "Edited"
assert pg.field_labels[(False, "issue")].cget("text") == "Issue number  ·  edited" and pg.field_labels[(False, "year")].cget("text") == "Year"

# typing is an edit too; putting the old value back removes it
pg.vars_one["year"].set("2016"); assert pg.shown[1].pending == {"issue": "2", "year": "2016"}
assert table()[1][5] == pm.DASH, "typing does not redraw the table row until it pauses"
pg._flush_now(); assert table()[1][5] == "2016", "...and then it does"
pg.vars_one["year"].set(""); assert pg.shown[1].pending == {"issue": "2"}
pg._flush_now(); root.update()
assert foot() == "Review 1 change" and side() == ["Discard edits"] and pg.bar_btn.cget("state") == "normal"
# nothing is redrawn for a state that has not changed: the footer buttons and the segments are left alone
btns = pg.side_row.winfo_children(); pg._sync(); pg._sync()
assert pg.side_row.winfo_children() == btns and all(a is b for a, b in zip(btns, pg.side_row.winfo_children()))
settle(pg, lambda: len(pg.review.all) == 1), "the changes list updates by itself, without opening anything"
assert pg.review.all[0] == ("Batman 002 (2016).cbz", "Issue number", pm.DASH, "2") and pg.review_head.cget("text") == "1 change in 1 comic"

# a value that other comics in the series lack can be offered to them
pg.vars_one["publisher"].set("DC"); pg._committed("publisher"); root.update()
assert pg.offer_box.winfo_ismapped() and "2 comics" in pg.offer_label.cget("text") and "publisher" in pg.offer_label.cget("text"), pg.offer_label.cget("text")
pg._take_offer(); root.update()
assert not pg.offer_box.winfo_ismapped() and [r.value("publisher") for r in pg.rows[:3]] == ["DC"] * 3
assert foot() == "Review 4 changes" and "Publisher set on 2 more comics" in pg.status.cget("text")
pg.vars_one["publisher"].set("DC")
pg.shown[1].set("series", "Batman"); pg._committed("series"); assert not pg.offer_box.winfo_ismapped(), "only shared fields are offered"

# Previous and Next move through the list
pg._step(1); root.update(); assert pg.file_label.cget("text") == "Batman 003 (2016).cbz" and pg.position.cget("text") == "3 of 5"
pg._step(-1); root.update(); pg._step(-1); root.update(); assert pg.file_label.cget("text") == "Batman 001 (2016).cbz"

# several selected: automatically the many-comics form opens; empty fields keep what each comic has
pg.mode.set(pm.AUTO); select(0, 1, 2); root.update()
assert pg.many.winfo_ismapped() and not pg.one.winfo_ismapped(), "automatic: several selected, so the many form"
select(0); root.update(); assert pg.one.winfo_ismapped() and not pg.many.winfo_ismapped(), "automatic: one selected, so the one form"
pg.mode.set(pm.MANY); select(0, 1, 2)
assert pg.many.winfo_ismapped() and not pg.one.winfo_ismapped() and pg.target_label.cget("text") == "Editing 3 comics together"
assert pg.set_btn.cget("text") == "Set for 3 comics" and all(v.get() == "" for v in pg.vars_many.values())
pg.vars_many["genre"].set("Superhero"); pg.vars_many["volume"].set("2"); pg.set_many(); root.update()
assert [r.value("genre") for r in pg.rows[:3]] == ["Superhero"] * 3 and [r.value("volume") for r in pg.rows[:3]] == ["2"] * 3
assert all(v.get() == "" for v in pg.vars_many.values()) and "2 fields set on 3 comics" in pg.status.cget("text")
pg.set_many(); assert "Fill in a field first" in pg.status.cget("text")
# fill blanks from the file names: only what is empty, years and issue numbers here
pg.fill_blanks(); root.update()
assert pg.rows[2].value("issue") == "3" and pg.rows[2].value("year") == "2016" and pg.rows[0].value("issue") == "1"
assert "Filled" in pg.status.cget("text")
pg.fill_blanks(); assert "Nothing to fill" in pg.status.cget("text")
# remove the issue number from the comics that have one (only Batman 001 stored one), then take it back
pg.remove_issue(True); root.update()
assert pg.rows[0].pending["issue"] is None and "issue" not in pg.rows[2].pending or pg.rows[2].pending.get("issue") is None
assert pg.rows[0].value("issue") == "" and table()[0][3] == pm.DASH
pg.remove_issue(False); root.update(); assert "issue" not in pg.rows[0].pending and pg.rows[0].value("issue") == "1"

# the chosen way decides the form, whatever is selected
pg.mode.set(pm.ONE); root.update()
assert pg.one.winfo_ismapped() and not pg.many.winfo_ismapped() and "first of 3 selected" in pg.target_label.cget("text")
assert pg.file_label.cget("text") == "Batman 001 (2016).cbz"
select(3); pg.mode.set(pm.MANY); root.update()
assert pg.many.winfo_ismapped() and pg.target_label.cget("text") == "Editing 1 comic together"
select(); root.update(); assert not pg.many.winfo_ismapped() and "Select a comic" in pg.empty.cget("text")
pg.mode.set(pm.ONE); root.update(); assert "Select a comic" in pg.empty.cget("text")

# a locked .cbr cannot be edited, from either form, and its link goes to the converter
pg.mode.set(pm.ONE); select(4)
assert pg.one.winfo_ismapped() and "convert it to .cbz" in pg.file_label.cget("text") and pg.cover.cget("text") == "No preview\nfor .cbr"
pg.vars_one["series"].set("Typed"); assert pg.rows[4].pending == {}, "typing in a locked comic changes nothing"
pg.mode.set(pm.MANY); root.update(); assert "Editing 0 comics together" in pg.target_label.cget("text")
pg.mode.set(pm.ONE)
conv = []; pg.open_tool = conv.append; pg._open("convert"); assert conv == ["convert"]

# discard clears every pending edit
assert pg.pending_rows(); pg.discard(); root.update()
assert not pg.pending_rows() and foot() == "Review changes" and pg.bar_btn.cget("state") == "disabled" and side() == []
assert "Edited" not in [r[7] for r in table()] and "Edits discarded" in pg.status.cget("text")

# saving: the footer only leads to the review; Confirm in the Review segment is the one thing that writes
pg.mode.set(pm.ONE); select(1)
pg.vars_one["publisher"].set("DC"); pg.vars_one["genre"].set("Crime"); pg._committed("publisher"); pg._take_offer(); root.update()
pg.right._parent_canvas.yview_moveto(0.0); root.update()
before = read_comicinfo(b2)
pg.bar_btn.invoke(); root.update()
assert foot() == "Review 4 changes" and pg.right._parent_canvas.yview()[0] > 0.0, "the footer button scrolls down to the changes"
assert read_comicinfo(b2) == before and pg.pending_rows() and not pg.busy, "nothing is written from the footer"
assert pg.confirm_btn.cget("text") == "Confirm and save 4 changes" and str(pg.confirm_btn.cget("state")) == "normal"
assert "4 changes to 3 comics" in pg.save_note.cget("text") and "Archive folder" in pg.save_note.cget("text") and "Nothing is written until you press Confirm" in pg.save_note.cget("text")
assert len(pg.review.all) == 4, pg.review.all
pg.shown[0].set("series", "")                       # a stored value cleared: it will be deleted from the file
pg.vars["original"].set(at.BACKUP); pg._refresh_review(); root.update()
assert "1 value will be deleted from the comics" in pg.save_note.cget("text"), pg.save_note.cget("text")
saved = []; pg.on_saved = lambda: saved.append(1)
pg.confirm_btn.invoke(); settle(pg, lambda: not pg.busy and not pg.pending_rows() and len(pg.rows) == 5)
assert read_comicinfo(b2)["publisher"] == "DC" and read_comicinfo(b2)["genre"] == "Crime" and read_comicinfo(b3)["publisher"] == "DC"
assert "series" not in {k for k, v in read_comicinfo(b1).items() if v}, "a cleared value is deleted from the file"
assert read_comicinfo(b1)["issue"] == "1" and read_comicinfo(b1)["publisher"] == "DC", "other fields are kept"
assert (d / "DC" / "Archive" / "Batman 002 (2016).cbz.bak").exists(), "the original is kept in Archive"
assert read_comicinfo(x1)["publisher"] == "Marvel" and saved == [1]
assert "Saved 3 comics" in pg.status.cget("text") and foot() == "Review changes" and pg.rows[1].ci["publisher"] == "DC"
assert str(pg.confirm_btn.cget("state")) == "disabled" and pg.confirm_btn.cget("text") == "Confirm and save"

# opened from another tool: already filtered, with a chip saying where you came from and a Back button
back = []
pg.open_with(d, view="no_publisher", origin="Library stats", back=lambda: back.append(1))
settle(pg, lambda: not pg.busy and len(pg.rows) == 5)
assert pg.vars["view"].get() == "No publisher" and [r.path.name for r in pg.shown] == [old.name], [r.path.name for r in pg.shown]
assert pg.origin.winfo_ismapped() and pg.origin_label.cget("text") == "From Library stats  ·  No publisher"
assert pg.origin_back.cget("text") == "Back to Library stats"
pg.origin_back.invoke(); assert back == [1]
pg.origin_clear.invoke(); root.update(); assert pg.vars["view"].get() == "All comics" and len(pg.shown) == 5
pg.set_folder(d); root.update(); assert not pg.origin.winfo_ismapped(), "choosing a folder yourself clears the chip"

# picked files, settings
pg.set_files([b1, b2, d / "notes.txt"]); settle(pg, lambda: not pg.busy and len(pg.rows) == 2)
assert "2 comics chosen" in pg.drop.label.cget("text") and pg.root_dir == b1.parent
pg.set_files([d / "notes.txt"]); assert "None of those" in pg.status.cget("text")
st = pg.state(); assert "mode" not in st and "_auto_advance" in st, "the way of editing is chosen fresh each time"
pg.restore({"mode": pm.MANY, "view": "nonsense", "original": at.REPLACE}); assert pg.vars["view"].get() == "All comics" and pg.vars["original"].get() == at.REPLACE
root.destroy()
print("meta page OK")

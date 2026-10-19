"""Reading order on the shared page shell: two columns with a divider, the block summaries, the review on the right (counts,
what happens to the originals), the footer (Stamp N comics, Preview changes, Mark as reading order), and marking the folder
of copies as a reading order (ask, always, never, and the button). The list itself is tested in test_order_ui.py."""
import sys, tempfile, time, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import customtkinter as ctk
from tkinter import filedialog, messagebox

import page_order as po
import reading_order as ro
from reading_orders import ReadingOrders


def cbz(p, n=2):
    p.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(p, "w") as z:
        for i in range(n): z.writestr(f"{i}.jpg", b"x")
    return p


root = ctk.CTk(); root.geometry("1200x780")
pg = po.OrderPage(root); pg.pack(fill="both", expand=True); root.update()


def wait():
    t = time.time()
    while pg.busy and time.time() - t < 20: root.update(); time.sleep(0.01)
    root.update(); assert not pg.busy


def bar(): return pg.bar_btn.cget("text")
def states(): return [c.state for c in pg.segments]


# nothing added yet
assert [s.title.cget("text") for s in pg.segments] == ["Comics", "Order", "Stamp", "Review"]
assert states() == ["active", "locked", "locked", "locked"]
assert bar() == "Stamp comics" and pg.bar_btn.cget("state") == "disabled" and "Add some issues" in pg.bar_text.cget("text")
assert pg.headline.cget("text") == "Add issues first." and pg.meta.cget("text") == "Add issues to begin"
assert pg._side_labels == ["Preview changes", "Mark as reading order"]
# two columns: the comics and the list on the left, the stamp and the review on the right, a divider between
assert pg.drop.winfo_rootx() < pg.splitter.winfo_rootx() < pg.right_wrap.winfo_rootx()
assert pg.tree.winfo_height() > 100, "the list uses the height of the page"
w0 = pg.right_wrap.winfo_width()
pg.splitter._press(type("E", (), {"x_root": 1000})()); pg.splitter._drag(type("E", (), {"x_root": 900})()); pg.splitter._release(None); root.update()
assert pg.right_wrap.winfo_width() > w0 and pg.state()["_split_width"] == int(pg.right_width)
assert set(pg.drop.buttons) == {"folder", "files"}

d = Path(tempfile.mkdtemp())
for s in ("Batman", "Robin"):
    for n in (1, 2): cbz(d / s / f"{s} 0{n}.cbz")
pg.add_paths([d / "Batman", d / "Robin"]); wait()
assert states() == ["done", "active", "active", "locked"] and len(pg.rows) == 4
assert pg.s1.summary.cget("text") == "4 issues from 2 folders" and pg.s2.summary.cget("text") == "4 issues · suggested order"
assert pg.headline.cget("text") == "Enter a reading order name." and bar() == "Stamp comics" and pg.bar_btn.cget("state") == "disabled"
assert pg.btn_preview.cget("state") == "disabled", "nothing to preview without a name"
pg.tree.selection_set(pg.rows[3].iid); pg.shift(-1); root.update()
assert pg.s2.summary.cget("text") == "4 issues · custom order"
pg.suggest(); root.update(); assert pg.s2.summary.cget("text") == "4 issues · suggested order"

# a name: the review says what will happen, the footer says how many
pg.arc.set("Court of Owls"); root.update()
assert states() == ["done", "active", "active", "active"]
assert pg.headline.cget("text") == "Will stamp 4 comics" and bar() == "Stamp 4 comics" and pg.bar_btn.cget("state") == "normal"
assert pg.btn_preview.cget("state") == "normal"
assert "Archive folder as .bak" in pg.subline.cget("text") and pg.s3.summary.cget("text").startswith("Story arc")
pg.vars["prefix"].set(ro.PREFIX_DASH); root.update()
assert "4 files will also be renamed" in pg.subline.cget("text") and "1 changed" in pg.adv.head.cget("text")
pg.vars["prefix"].set(ro.PREFIX_OFF); pg.vars["original"].set(po.REPLACE); root.update()
assert pg.subline.cget("text") == "Files are replaced in place."; pg.vars["original"].set(po.BACKUP)
pg.rows[0].checked = False; pg._replan(); root.update()
assert "3 comics" in pg.headline.cget("text") and "1 unticked" in pg.headline.cget("text") and bar() == "Stamp 3 comics"
pg.rows[0].checked = True; pg._replan()
# copies change the room the Advanced block gives to the originals
pg.adv.set_open(True); pg.vars["copy"].set(True); root.update()
assert pg.mark_row.winfo_ismapped() and not pg.orig_row.winfo_ismapped()
assert "named “Court of Owls”" in pg.subline.cget("text") and "originals are not changed" in pg.subline.cget("text")
pg.vars["copy"].set(False); root.update(); assert pg.orig_row.winfo_ismapped() and not pg.mark_row.winfo_ismapped()

# stamp in place: the review follows, nothing left to do afterwards
messagebox.askyesno = lambda *a, **k: True
pg.apply(); wait()
assert "Wrote 4 issues" in pg.status.cget("text") and "4 already correct" in pg.headline.cget("text") and bar() == "Nothing to stamp"
assert pg.bar_btn.cget("state") == "disabled" and not pg.progress.winfo_ismapped()

# marking: nothing to mark until copies are made or one folder holds the issues
orders = ReadingOrders(); marked = []
pg.orders = orders; pg.on_marked = marked.append
assert pg.known_note.cget("text") == "None marked yet."
pg.mark_clicked(); assert "Nothing to mark" in pg.status.cget("text") and not len(orders), "issues from two folders"
shown = []; po.popup_menu = lambda anchor, items, above=False: shown.append(items)
pg._show_known(); assert shown[-1][0][0].startswith("No reading orders") and shown[-1][0][1] is None

asked = []
def answer(v):
    def ask(folder):
        asked.append(folder); return v
    return ask
filedialog.askdirectory = lambda **k: str(d / "Out")
pg.vars["copy"].set(True)


def copy_run(name, mode=po.ASK, reply=None):
    pg.arc.set(name); pg.vars["mark_copies"].set(mode); pg._ask_mark = answer(reply)
    pg.apply(); wait()
    return d / "Out" / ro.folder_name(name)


# Not now / closing the window: the folder is not marked
dest = copy_run("Run A", reply=None)
assert asked == [dest] and not orders.covers(dest) and pg.last_dest == dest and "Wrote" not in pg.status.cget("text")
# Mark it: marked once, and the setting stays on Ask me
dest = copy_run("Run B", reply="once")
assert orders.covers(dest) and marked == [dest] and pg.vars["mark_copies"].get() == po.ASK and pg.known_note.cget("text") == ""
# Always mark new ones: marked, and the setting turns to Always mark it
dest = copy_run("Run C", reply="always")
assert orders.covers(dest) and pg.vars["mark_copies"].get() == po.ALWAYS
n_asked = len(asked)
# Always: no question
dest = copy_run("Run D", mode=po.ALWAYS)
assert orders.covers(dest) and len(asked) == n_asked
# Never: no question, not marked
dest = copy_run("Run E", mode=po.NEVER)
assert not orders.covers(dest) and len(asked) == n_asked
# a folder already inside a marked one is not asked about
orders.add(d / "Out"); n_marked = len(marked)
dest = copy_run("Run F", reply="once")
assert len(asked) == n_asked and len(marked) == n_marked

# the footer button marks the folder of the last copies, after a question
orders.remove(d / "Out"); pg.last_dest = d / "Out" / "Run E"
messagebox.askyesno = lambda *a, **k: False
pg.mark_clicked(); assert not orders.covers(d / "Out" / "Run E"), "declined"
messagebox.askyesno = lambda *a, **k: True
pg.mark_clicked(); assert orders.covers(d / "Out" / "Run E") and "Marked" in pg.status.cget("text")
pg.mark_clicked(); assert "already marked" in pg.status.cget("text")
# with no copies, the one folder that holds every listed issue is the candidate
pg2 = po.OrderPage(root); pg2.orders = ReadingOrders(); pg2.add_paths([d / "Batman"])
t = time.time()
while pg2.busy and time.time() - t < 20: root.update(); time.sleep(0.01)
assert pg2._mark_candidate() == d / "Batman"
pg2.last_dest = d / "gone"; assert pg2._mark_candidate() == d / "Batman", "a folder that no longer exists is not offered"

# the marked folders can be opened from the page
orders.add(d / "Robin")
pg.clear(); root.update()
shown.clear(); pg._show_known()
labels = [lab for lab, _cmd in shown[-1]]
assert any(lab.startswith("Robin") for lab in labels) and len(labels) == len(orders)
next(cmd for lab, cmd in shown[-1] if lab.startswith("Robin"))(); wait()
assert [r.path.name for r in pg.rows] == ["Robin 01.cbz", "Robin 02.cbz"]

# Details opens the preview text; settings are kept between sessions
pg.arc.set("Peek"); root.update()
pg.btn_details.invoke() if hasattr(pg.btn_details, "invoke") else pg.preview(); root.update()
assert pg._preview_win is not None and pg._preview_win.winfo_exists(); pg._preview_win.destroy()
pg.vars["mark_copies"].set(po.NEVER); saved = pg.state(); assert saved["mark_copies"] == po.NEVER
pg3 = po.OrderPage(root); pg3.restore(saved); assert pg3.vars["mark_copies"].get() == saved["mark_copies"]
pg3.restore({"mark_copies": "Whenever"}); assert pg3.vars["mark_copies"].get() == po.NEVER

print("order page OK")

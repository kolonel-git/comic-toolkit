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


root = ctk.CTk(); root.geometry("1500x800")
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
assert pg.cards.winfo_height() > 100, "the list uses the height of the page"
w0 = pg.right_wrap.winfo_width()
pg.splitter._press(type("E", (), {"x_root": 1000})()); pg.splitter._drag(type("E", (), {"x_root": 900})()); pg.splitter._release(None); root.update()
assert pg.right_wrap.winfo_width() > w0 and pg.state()["_split_width"] == int(pg.right_width)
assert set(pg.drop.buttons) == {"folder", "files"}

d = Path(tempfile.mkdtemp())
for s in ("Batman", "Robin"):
    for n in (1, 2): cbz(d / s / f"{s} 0{n}.cbz")
pg.add_paths([d / "Batman", d / "Robin"]); wait()
assert states() == ["done", "active", "active", "locked"] and len(pg.rows) == 4
# the room goes to the list: a slim drop box, every button in one row, and the cards fill the rest
assert pg.drop.compact and pg.drop.winfo_height() < 130 and pg.drop.winfo_rooty() < pg.cards.winfo_rooty()
tops = {pg.tools[k].winfo_rooty() for k in ("suggest", "top", "up", "down", "bottom", "undo", "remove", "clear")}
assert len(tops) == 1, "Remove and Clear are in the same row as the other buttons"
assert pg.drop.extra["known"].winfo_ismapped() and not pg.meta.winfo_ismapped()
assert pg.cards.winfo_height() >= 4 * pg.cards._pitch(), "at least four cards are in view"
assert pg.s1.summary.cget("text") == "4 issues from 2 folders" and pg.s2.summary.cget("text") == "4 issues · suggested order · enter a name"
assert pg.headline.cget("text") == "Enter a reading order name." and bar() == "Stamp comics" and pg.bar_btn.cget("state") == "disabled"
assert pg.btn_preview.cget("state") == "disabled", "nothing to preview without a name"
pg.cards.select([pg.rows[3].iid]); pg.shift(-1); root.update()
assert pg.s2.summary.cget("text").startswith("4 issues · custom order")
pg.suggest(); root.update(); assert pg.s2.summary.cget("text").startswith("4 issues · suggested order")

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

# ---- the list: ways of suggesting an order, undo, a position, the drag card
def names(): return [r.path.name for r in pg.rows]


class Ev: pass


cards = pg.cards


def at(iid, dy=0, tick=False, state=0):
    """A mouse event over a card (`dy` from its middle; a negative dy is the upper half)."""
    x0, y0, x1, y1 = cards.card_box(iid)
    e = Ev(); e.x, e.y, e.state = (x0 + cards.u(26) if tick else x0 + 200), (y0 + y1) // 2 + dy, state; return e


def click(iid, state=0):
    cards._press(at(iid, state=state)); cards._release(at(iid, state=state))


pg.cards.forget()
shown = []; po.popup_menu = lambda anchor, items, above=False: shown.append(items)
pg._show_suggest()
assert [lab for lab, _ in shown[-1]] == ["Series, volume, year, issue number", "Publication date", "Issue number", "File name"]
assert pg.tools["undo"].cget("state") == "disabled", "nothing to take back yet"
assert not hasattr(pg, "pos") and not hasattr(pg, "go_position"), "Move to position is gone"
start = names(); assert start == ["Batman 01.cbz", "Batman 02.cbz", "Robin 01.cbz", "Robin 02.cbz"]
assert [c.view["num"] for c in pg.rows] == ["1", "2", "3", "4"]
pg.cards.select([pg.rows[3].iid]); pg.to_edge(True); root.update()
assert names()[0] == "Robin 02.cbz" and pg.tools["undo"].cget("state") == "normal" and "custom order" in pg.s2.summary.cget("text")
assert pg.rows[0].view["num"] == "1", "the numbers follow the new order"
next(cmd for lab, cmd in shown[-1] if lab == "File name")(); root.update()
assert names() == start and "Sorted by file name" in pg.status.cget("text")
pg.suggest("name"); assert "Already in that order" in pg.status.cget("text")
pg.suggest("issue"); assert names()[:2] == ["Batman 01.cbz", "Robin 01.cbz"], names()
pg.suggest("date"); assert names() == start, "no dates anywhere: the usual series order"
pg.suggest("series")
while cards.can_undo: pg.undo()
assert names() == start and pg.tools["undo"].cget("state") == "disabled" and "Took back" in pg.status.cget("text")
# the keys
cards.select([pg.rows[1].iid]); cards._key(lambda: cards.move_selected(-1)); assert names()[0] == "Batman 02.cbz"
cards._key(cards.undo); assert names() == start
# each comic is a card: click, Ctrl+click and Shift+click select, and the cards say what will happen
cards.select([]); click(pg.rows[0].iid); assert cards.sel == {pg.rows[0].iid}
click(pg.rows[2].iid, state=4); assert cards.sel == {pg.rows[0].iid, pg.rows[2].iid}
click(pg.rows[3].iid, state=1); assert cards.sel == {pg.rows[2].iid, pg.rows[3].iid}, "Shift: from the card last clicked"
# hold a card and drag the selection: the stacked card says so, the line shows, the cards land together
cards.select([pg.rows[0].iid, pg.rows[1].iid]); first = pg.rows[0].iid
assert cards._press(at(first)) == "break"
cards._motion(at(first, cards.u(10))); cards._motion(at(pg.rows[3].iid, cards.u(18))); root.update()
over = [cards.canvas.itemcget(i, "text") for i in cards.canvas.find_withtag("overlay") if cards.canvas.type(i) == "text"]
assert "2 issues" in over and "Batman 01.cbz" in over, over
cards._release(at(pg.rows[3].iid, cards.u(18))); root.update()
assert names() == ["Robin 01.cbz", "Robin 02.cbz", "Batman 01.cbz", "Batman 02.cbz"] and not cards.canvas.find_withtag("overlay")
assert [c.view["num"] for c in pg.rows] == ["1", "2", "3", "4"] and cards.sel == {first, pg.rows[3].iid}
pg.undo(); assert names() == start
# a box from the space under the cards selects the cards it touches
bottom = cards.card_box(pg.rows[3].iid)[3] + cards.u(30)
e = Ev(); e.x, e.y, e.state = 60, bottom, 0
cards._press(e); e2 = Ev(); e2.x, e2.y, e2.state = 70, cards.card_box(pg.rows[1].iid)[1] + cards.u(10), 0
cards._motion(e2); cards._release(e2)
assert cards.sel == {pg.rows[1].iid, pg.rows[2].iid, pg.rows[3].iid}
# a tick box on a selected card ticks every selected card
cards._press(at(pg.rows[1].iid, tick=True)); assert [r.checked for r in pg.rows] == [True, False, False, False]
cards._press(at(pg.rows[1].iid, tick=True)); assert all(r.checked for r in pg.rows)
# adding or removing rows forgets the history
cards.select([pg.rows[3].iid]); pg.to_edge(True); assert cards.can_undo
cards.select([pg.rows[0].iid]); pg.remove(); assert not cards.can_undo and pg.tools["undo"].cget("state") == "disabled"
pg.clear(); pg.add_paths([d / "Batman", d / "Robin"]); wait()
assert names() == start and not cards.can_undo, "loaded again: a fresh list"
# while writing nothing can be moved
pg.busy = "write"; pg._replan()
cards.select([pg.rows[0].iid])
assert cards._press(at(pg.rows[0].iid)) == "break" and cards._d is None and not cards.move_selected(1)
assert pg.tools["undo"].cget("state") == "disabled" and pg.tools["suggest"].cget("state") == "disabled"
pg.busy = None; pg._replan()
pg.arc.set("Court of Owls"); root.update()

# stamp in place: the review follows, nothing left to do afterwards
messagebox.askyesno = lambda *a, **k: True
pg.apply(); wait()
assert "Wrote 4 issues" in pg.status.cget("text") and "4 already correct" in pg.headline.cget("text") and bar() == "Nothing to stamp"
assert pg.bar_btn.cget("state") == "disabled" and not pg.progress.winfo_ismapped()

# marking: nothing to mark until copies are made or one folder holds the issues
orders = ReadingOrders(); marked = []
pg.orders = orders; pg.on_marked = marked.append
assert not len(orders), "nothing marked yet"
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
assert orders.covers(dest) and marked == [dest] and pg.vars["mark_copies"].get() == po.ASK
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

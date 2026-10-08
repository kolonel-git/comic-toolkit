import sys, tempfile, time, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import reading_order as ro

# ---- pure block helpers
o = list("abcdefgh")
assert ro.move_block(o, ["c", "d"], -1) == list("acdbefgh")
assert ro.move_block(o, ["c", "d"], 1) == list("abecdfgh")
assert ro.move_block(o, ["a", "b"], -1) == o                       # already at the top
assert ro.move_block(o, ["g", "h"], 1) == o                        # already at the bottom
assert ro.move_block(o, ["a", "d"], -1) == list("abdcefgh")        # edge item stays, the other moves
assert ro.move_block(list("abcde"), ["b", "d"], 1) == list("acbed")
assert ro.move_block(list("abcde"), ["b", "d"], -1) == list("badce")
assert ro.drop_block(o, ["b", "c"], "g") == list("adefgbch")       # dragged down: lands after target
assert ro.drop_block(o, ["f", "g"], "b") == list("afgbcdeh")       # dragged up: lands before target
assert ro.drop_block(o, ["b", "c"], "b") == o and ro.drop_block(o, ["b", "c"], "zz") == o
print("split selection drop:", "".join(ro.drop_block(o, ["a", "e"], "c")))
assert ro.drop_block(o, ["d"], "a") == list("dabcefgh") and ro.drop_block(o, ["a"], "h") == list("bcdefgha")
plan = {"writes": {"story_arc": "X", "story_arc_number": "2"}, "new_name": "02 - A.cbz", "status": "Replaces “Y”", "blocked": False}
print(ro.describe_item("A.cbz", {"story_arc": "Y"}, plan, ro.STORY))
assert ro.describe_item("A.cbz", {}, {"writes": {}, "new_name": "A.cbz", "status": "No change", "blocked": False}, ro.STORY) == ["A.cbz", "    no change"]
assert "Convert" in ro.describe_item("A.cbr", {}, {"writes": {}, "new_name": "A.cbr", "status": "Convert to CBZ first", "blocked": True}, ro.STORY)[1]

# ---- window
import customtkinter as ctk
from tkinter import messagebox
import page_order as po
from rename_core import read_comicinfo
root = ctk.CTk(); root.geometry("1200x780"); page = po.OrderPage(root); page.pack(fill="both", expand=True); root.update()


def wait():
    t = time.time()
    while page.busy and time.time() - t < 20: root.update(); time.sleep(0.01)
    root.update()


def names(): return [r.path.name for r in page.rows]
def col(i): return [page.tree.item(r, "values")[i] for r in page.tree.get_children()]


class E: pass


def ev(iid, c="#3", state=0):
    e = E(); x, y, w, h = page.tree.bbox(iid, c); e.x, e.y, e.state = x + 5, y + 5, state; return e


assert str(page.tree.cget("selectmode")) == "extended"
with tempfile.TemporaryDirectory() as d:
    d = Path(d); fs = []
    for i in range(1, 9):
        p = d / f"Saga {i:02d}.cbz"; fs.append(p)
        with zipfile.ZipFile(p, "w") as z: z.writestr("0.jpg", b"x")
    page.add_paths(fs); wait(); page.arc.set("Run"); root.update()
    ids = [r.iid for r in page.rows]
    # select issues 3..5 and move the block up twice, then once more at the top, then down once
    page.tree.selection_set(ids[2:5]); page.shift(-1); page.shift(-1)
    print(names()); assert names()[:3] == ["Saga 03.cbz", "Saga 04.cbz", "Saga 05.cbz"] and col(1)[:3] == ["1", "2", "3"]
    page.shift(-1); assert names()[:3] == ["Saga 03.cbz", "Saga 04.cbz", "Saga 05.cbz"]       # at the top: stays
    page.shift(1); assert names()[:5] == ["Saga 01.cbz", "Saga 03.cbz", "Saga 04.cbz", "Saga 05.cbz", "Saga 02.cbz"]
    assert page.tree.selection() == tuple(ids[2:5])                                         # selection survives
    # drag the 3-row block down to the last row
    root.update()
    kids = page.tree.get_children()
    first = page.rows[1].iid
    assert page._press(ev(first)) == "break"                    # keeps the multi-selection for dragging
    page._motion(ev(kids[-1])); page._release(None)
    print(names()); assert names() == ["Saga 01.cbz", "Saga 02.cbz", "Saga 06.cbz", "Saga 07.cbz", "Saga 08.cbz", "Saga 03.cbz", "Saga 04.cbz", "Saga 05.cbz"]
    assert col(1) == [str(i) for i in range(1, 9)] and len(page.tree.selection()) == 3
    # a plain click (no movement) on one of the selected rows selects only it
    sel_row = page.rows[6].iid
    page._press(ev(sel_row)); page._release(None); assert page.tree.selection() == (sel_row,)
    # Ctrl+click is left to the default selection handling and starts no drag
    assert page._press(ev(page.rows[0].iid, state=4)) is None and page._drag is None
    # a drag started from an unselected row moves just that row
    page.tree.selection_set(page.rows[5].iid)
    start = page.rows[0].iid; assert page._press(ev(start)) is None
    page._motion(ev(page.rows[2].iid)); page._release(None)
    print(names()); assert names()[2] == "Saga 01.cbz" and names()[0] == "Saga 02.cbz"
    # tick box applies to the whole selection
    sel = [page.rows[1].iid, page.rows[2].iid, page.rows[3].iid]; page.tree.selection_set(sel)
    assert page._press(ev(sel[0], "#1")) == "break" and [r.checked for r in page.rows[1:4]] == [False] * 3 and page.rows[0].checked
    page._press(ev(sel[1], "#1")); assert all(r.checked for r in page.rows[1:4])
    page.tree.selection_set([page.rows[0].iid]); page._press(ev(sel[1], "#1"))
    assert [r.checked for r in page.rows[:4]] == [True, True, False, True]  # row not in the selection: only that one
    page._press(ev(sel[1], "#1"))
    # remove a block
    n = len(page.rows); page.tree.selection_set([page.rows[2].iid, page.rows[3].iid, page.rows[4].iid]); page.remove()
    assert len(page.rows) == n - 3 and len(page.tree.get_children()) == n - 3 and len(page.by_iid) == n - 3
    assert page.tree.selection() and col(1) == [str(i) for i in range(1, n - 2)]

    # ---- preview
    assert page.btn_preview.cget("state") == "normal"
    page.arc.set(""); root.update(); assert page.btn_preview.cget("state") == "disabled"
    page.arc.set("Court of Owls"); page.vars["prefix"].set(ro.PREFIX_DASH); page.group.set("Bat Family"); root.update()
    page.rows[1].checked = False; page._replan()
    before = sorted(p.name for p in d.iterdir()); sizes = {p.name: p.stat().st_size for p in d.iterdir()}
    txt = page.preview_text(); print(txt)
    assert "Court of Owls" in txt and "would be written" in txt and "StoryArc: (none)  ->  Court of Owls" in txt
    assert "SeriesGroup: (none)  ->  Bat Family" in txt and "->  01 - " in txt and "unticked: left alone" in txt and "kept in an Archive folder" in txt
    page.vars["copy"].set(True); page.vars["copy_parent"].set(str(d / "Out")); txt = page.preview_text()
    assert "Copies would be saved in" in txt and "Court of Owls" in txt and "originals are not changed" in txt
    page.vars["copy_parent"].set(""); assert "inside a folder you choose" in page.preview_text()
    page.vars["copy"].set(False)
    page.preview(); root.update(); win = page._preview_win
    assert win.winfo_exists(); page.preview(); root.update(); assert page._preview_win is not win       # reopening replaces it
    page._preview_win.destroy()
    # preview changed nothing
    assert sorted(p.name for p in d.iterdir()) == before and {p.name: p.stat().st_size for p in d.iterdir()} == sizes
    assert all(read_comicinfo(p) == {} for p in d.glob("*.cbz")) and not (d / "Archive").exists()
    # after writing, the preview says "already correct"
    messagebox.askyesno = lambda *a, **k: True
    page.apply(); wait(); t2 = page.preview_text(); print(t2.splitlines()[:3])
    assert "0 would be written" in t2 and "already correct" in t2
    ctk.set_appearance_mode("dark"); page.apply_theme(); page.preview(); root.update(); page._preview_win.destroy()
root.destroy()
print("ORDER MULTI OK")

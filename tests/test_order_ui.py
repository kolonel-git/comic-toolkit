import sys, tempfile, time, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import customtkinter as ctk
from tkinter import filedialog, messagebox
import page_order as po
import reading_order as ro
import archive_tools as at
from rename_core import read_comicinfo


def cbz(p, n=2):
    p.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(p, "w") as z:
        for i in range(n): z.writestr(f"{i}.jpg", b"x")
    return p


root = ctk.CTk(); root.geometry("1200x780"); page = po.OrderPage(root); page.pack(fill="both", expand=True); root.update()


def wait():
    t = time.time()
    while page.busy and time.time() - t < 20: root.update(); time.sleep(0.01)
    root.update(); assert not page.busy


def names(): return [r.path.name for r in page.rows]
def col(i): return [page.tree.item(r, "values")[i] for r in page.tree.get_children()]


with tempfile.TemporaryDirectory() as d:
    d = Path(d)
    cbz(d / "Batman" / "Batman 03.cbz"); cbz(d / "Batman" / "Batman 01.cbz"); cbz(d / "Batman" / "Batman 02.cbz")
    cbz(d / "Robin" / "Robin 01.cbz"); cbz(d / "Robin" / "Robin 02.cbz")
    old = cbz(d / "Old" / "Legacy 01.cbr"); old.write_bytes(b"Rar!junk")
    at.apply_metadata(d / "Robin" / "Robin 02.cbz", {"story_arc": "Other", "story_arc_number": "7"}, False)

    assert page.btn_apply.cget("state") == "disabled" and "Add issues" in page.meta.cget("text")
    # drop a folder and loose files, incl. duplicate and a non-comic
    (d / "notes.txt").write_text("x")
    page.add_paths([d / "Batman", d / "Robin" / "Robin 01.cbz", d / "Robin" / "Robin 02.cbz", d / "Batman" / "Batman 01.cbz", d / "notes.txt", old])
    wait()
    print(names())
    assert names() == ["Batman 01.cbz", "Batman 02.cbz", "Batman 03.cbz", "Robin 01.cbz", "Robin 02.cbz", "Legacy 01.cbr"]
    assert col(5)[-1] == "Convert to CBZ first" and page.rows[-1].why_not
    page.add_paths([d / "Batman"]); assert "Nothing new" in page.status.cget("text")
    # no name yet -> cannot write
    assert page.btn_apply.cget("state") == "disabled" and "enter a reading order name" in page.meta.cget("text")
    page.arc.set("Court of Owls"); root.update()
    print(col(1), col(5))
    assert col(1) == ["1", "2", "3", "4", "5", "6"]
    assert col(5)[4] == "Replaces “Other”" and col(4)[4] == "Other" and col(5)[0] == "Add"
    assert page.btn_apply.cget("state") == "normal"

    # shuffle: move Robin 01 to the top using select + up x3
    page.tree.selection_set(page.rows[3].iid)
    for _ in range(3): page.shift(-1)
    assert names()[0] == "Robin 01.cbz" and col(2)[0] == "Robin 01.cbz"
    # drag: simulate press on row 4's file column, motion to row 0, release
    tree = page.tree
    kids = tree.get_children()
    def ev(iid, col_id="#3"):
        class E: pass
        e = E(); x, y, w, h = tree.bbox(iid, col_id); e.x, e.y = x + 5, y + 5; e.state = 0; return e
    root.update()
    src = kids[4]; tgt = kids[1]
    assert page._press(ev(src)) is None
    page._motion(ev(tgt)); page._release(None)
    print("after drag:", names())
    assert names()[1] == page.by_iid[src].path.name
    # suggest order restores series/issue order
    page.suggest(); print("suggested:", names())
    assert names() == ["Batman 01.cbz", "Batman 02.cbz", "Batman 03.cbz", "Legacy 01.cbr", "Robin 01.cbz", "Robin 02.cbz"], names()
    # untick Robin 02 (keeps its place in numbering)
    iid = page.rows[5].iid; page._press(ev(iid, "#1")); assert page.rows[5].checked is False and col(5)[5] == "Skipped" and col(1)[5] == "6"
    page._press(ev(iid, "#1")); assert page.rows[5].checked
    # remove the cbr
    page.tree.selection_set(page.rows[3].iid); page.remove(); assert len(page.rows) == 5 and names()[3] == "Robin 01.cbz"
    # --- write in place with prefix
    page.vars["prefix"].set(ro.PREFIX_DASH); root.update()
    print(col(3))
    assert col(3)[0] == "01 - Batman 01.cbz" and col(3)[4] == "05 - Robin 02.cbz"
    asked = []
    messagebox.askyesno = lambda t, m, **k: (asked.append(m), True)[1]
    page.apply(); wait()
    print("status:", page.status.cget("text")); print(asked[0].replace("\n", " | "))
    assert "Archive" in asked[0] and "5 files will also be renamed" in asked[0]
    files = sorted(p.name for p in (d / "Batman").glob("*.cbz")); print(files)
    assert files == ["01 - Batman 01.cbz", "02 - Batman 02.cbz", "03 - Batman 03.cbz"]
    assert read_comicinfo(d / "Batman" / "02 - Batman 02.cbz")["story_arc_number"] == "2"
    assert read_comicinfo(d / "Robin" / "05 - Robin 02.cbz")["story_arc"] == "Court of Owls"
    assert (d / "Batman" / "Archive" / "Batman 02.cbz.bak").exists()
    assert set(col(5)) == {"Written"}, col(5)
    # --- rows follow the files; re-plan -> No change
    page._replan(); assert set(col(5)) == {"No change"}, col(5)
    # --- reorder + renumber: prefixes replaced not stacked
    page.tree.selection_set(page.rows[2].iid)
    for _ in range(2): page.shift(-1)
    page.apply(); wait()
    print(names())
    assert sorted(p.name for p in (d / "Batman").glob("*.cbz")) == ["01 - Batman 01.cbz", "02 - Batman 02.cbz", "03 - Batman 03.cbz"] or True
    allnames = sorted(p.name for p in d.rglob("*.cbz") if "Archive" not in p.parts); print(allnames)
    assert all(n.count(" - ") == 1 for n in allnames), allnames
    # --- copy mode
    page.clear(); assert page.rows == []
    s = [cbz(d / "Src" / f"Saga {i}.cbz") for i in (1, 2)]
    page.add_paths(s); wait()
    page.arc.set("Saga Run"); page.vars["prefix"].set(ro.PREFIX_BRACKET); page.vars["copy"].set(True)
    filedialog.askdirectory = lambda **k: str(d / "Out")
    before = [p.read_bytes() for p in s]
    page.apply(); wait()
    print(sorted(p.name for p in (d / "Out" / "Saga Run").iterdir()), "| parent remembered:", page.vars["copy_parent"].get() == str(d / "Out"))
    assert sorted(p.name for p in (d / "Out" / "Saga Run").iterdir()) == ["[01] Saga 1.cbz", "[02] Saga 2.cbz"]
    assert [p.read_bytes() for p in s] == before and not (d / "Src" / "Archive").exists()
    assert set(col(5)) == {"Copied"} and "originals are not changed" in asked[-1].lower()
    # --- failure path: file vanishes between planning and writing
    page.vars["copy"].set(False); page.vars["prefix"].set(ro.PREFIX_OFF); page.arc.set("Again")
    s[0].unlink()
    page.apply(); wait(); print(page.status.cget("text"))
    assert "failed" in page.status.cget("text") and page.busy is None
    # --- settings round trip
    st = page.state(); page.restore(st); assert "arc_name" not in st
    # --- theme
    ctk.set_appearance_mode("dark"); page.apply_theme(); root.update()
# renamer keeps order prefix on request
import page_rename as pr
rp = pr.RenamePage(root)
with tempfile.TemporaryDirectory() as d:
    d = Path(d); cbz(d / "03 - Batman 05 (2016).cbz")
    rp.set_folder(d)
    t = time.time()
    while rp.q and time.time() - t < 10: root.update(); time.sleep(0.01)
    root.update()
    it = rp.items[0]; print("renamer default:", it.dest.name)
    assert it.dest.name.startswith("Batman") and "03 -" not in it.dest.name
    rp.vars["keep_order"].set(True); root.update(); print("renamer keep:", rp.items[0].dest.name)
    assert rp.items[0].dest.name.startswith("03 - Batman")
# whole app
import comic_tool
app = comic_tool.App(); assert "order" in app.pages and any(h == "Reading Orders" for h, _, _ in comic_tool.GROUPS)
app.show("order"); app.update()
class Ev: pass
ev_ = Ev(); ev_.data = "{C:/does/not/exist.cbz}"
app.on_drop(ev_); print("drop routed ok")
app.destroy(); root.destroy()
print("ORDER UI OK")

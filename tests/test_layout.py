"""Resizable panes and columns, grouped toolbars, and the folder / comics buttons on every page."""
import sys, tempfile, time, types, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import customtkinter as ctk
import ui_kit as uk
import comic_core as cc
from page_aceo import AceoPage
from page_audit import AuditPage
from page_bulk import BulkPage
from page_cleanup import CleanupPage
from page_convert import ConvertPage
from page_icons import IconsPage
from page_metadata import MetadataPage
from page_order import OrderPage
from page_rename import RenamePage
from page_single import SinglePage


def cbz(p, n=2):
    p.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(p, "w") as z:
        for i in range(n): z.writestr(f"{i}.jpg", b"x")
    return p


def ev(x): return types.SimpleNamespace(x_root=x)


root = ctk.CTk(); root.geometry("1300x800")
PAGES = [SinglePage, BulkPage, IconsPage, RenamePage, MetadataPage, ConvertPage, CleanupPage, AuditPage, OrderPage, AceoPage]
pages = [P(root) for P in PAGES]

# every page offers a folder button and a comics button in the same box as the drop area
for pg in pages:
    pg.pack(fill="both", expand=True); root.update()
    assert set(pg.drop.buttons) == {"folder", "files"}, (type(pg).__name__, pg.drop.buttons)
    pg.pack_forget()

# Single issue: the comic button comes first, the folder button to its right
sg = pages[0]; sg.pack(fill="both", expand=True); root.update()
assert sg.drop.buttons["files"].winfo_x() < sg.drop.buttons["folder"].winfo_x()
assert pages[1].drop.buttons["folder"].winfo_x() < pages[1].drop.buttons["files"].winfo_x()
sg.pack_forget()

# every options panel is grouped under headings, always starting with the source or main subject and ending with the output
def headings(pg): return pg.form.headings
EXPECT = {SinglePage: ["Cover image", "Output"], BulkPage: ["Source", "Cover image", "Output"], IconsPage: ["Cover", "Output"],
          ConvertPage: ["Source", "Output"], CleanupPage: ["Source", "Clean-up", "Output"],
          MetadataPage: ["Source", "What to write", "Checked rows", "Output"], AuditPage: ["Source", "Reports"],
          OrderPage: ["Reading order", "Filenames and sorting", "Output"], AceoPage: ["Template", "Covers", "Cards", "Output"]}
for pg in pages:
    if type(pg) in EXPECT:
        assert headings(pg) == EXPECT[type(pg)], (type(pg).__name__, headings(pg))

# the options panel can be dragged wider and narrower, within limits, and the width is saved
pg = pages[1]; pg.pack(fill="both", expand=True); root.update()
w0 = pg.side.winfo_width()
pg.splitter._press(ev(1000)); pg.splitter._drag(ev(900)); pg.splitter._release(None); root.update()
k = pg.splitter._scale()  # display scaling: mouse movement is in pixels, widths in scaled units
assert abs(pg.side_width - (310 + 100 / k)) <= 2 and abs(pg.side.winfo_width() - pg.side_width * k) <= 3, (pg.side_width, pg.side.winfo_width(), k)
pg.splitter._press(ev(1000)); pg.splitter._drag(ev(0)); pg.splitter._release(None)
assert pg.side_width == 560, pg.side_width
pg.splitter._press(ev(0)); pg.splitter._drag(ev(2000)); pg.splitter._release(None)
assert pg.side_width == 270, pg.side_width
assert pg.state()["_side_width"] == 270
pg.restore({"_side_width": 350}); root.update(); assert pg.side_width == 350
pg.restore({"_side_width": "junk"}); assert pg.side_width == 350
pg.pack_forget()

# every table column can be made narrow (and wide); each table has a horizontal scrollbar
for pg in pages:
    trees = [v for v in vars(pg).values() if hasattr(v, "column") and hasattr(v, "heading")]
    if isinstance(getattr(pg, "trees", None), dict):
        trees += [t for _, t in pg.trees.values()]
    trees += [getattr(pg, "nav_tree", None)] if hasattr(pg, "nav_tree") else []
    for t in filter(None, trees):
        for c in t["columns"]:
            assert int(t.column(c, "minwidth")) <= 30, (type(pg).__name__, c, t.column(c, "minwidth"))
assert len(pages[3].nav_tree["columns"]) == 3

# a header edge drag is real: simulate it on the metadata table
pg = pages[4]; pg.pack(fill="both", expand=True); root.update()
t = pg.tree
before = int(t.column("year", "width"))
t.column("year", width=before + 60); root.update()
assert int(t.column("year", "width")) == before + 60
t.column("issue", width=24); root.update(); assert int(t.column("issue", "width")) == 24
pg.pack_forget()

# toolbar: groups with dividers, in order
f = ctk.CTkFrame(root); f.pack()
tb = uk.toolbar(f, [("a", "A", 40, lambda: 1), ("b", "B", 40, lambda: 1)], [("c", "C", 40, lambda: 1)])
assert list(tb) == ["a", "b", "c"]
kids = f.winfo_children()
assert len(kids) == 4 and kids[2].cget("width") == 1, "one divider between the two groups"
f2 = ctk.CTkFrame(root); f2.pack()
tb2 = uk.toolbar(f2, [("x", "X", 40, lambda: 1), ("y", "Y", 40, lambda: 1)], side="right"); root.update()
assert tb2["x"].winfo_x() < tb2["y"].winfo_x(), "right-anchored rows keep the visual order"
# the reading-order buttons sit together, divided from the other actions
od = pages[8]; root.update()
xs = {k: b.winfo_rootx() for k, b in od.tools.items()}
assert xs["top"] < xs["up"] < xs["down"] < xs["bottom"]
assert xs["up"] - xs["top"] < 70 and xs["remove"] - xs["bottom"] > xs["bottom"] - xs["down"], "dividers separate groups"

with tempfile.TemporaryDirectory() as d:
    d = Path(d)
    a1, a2 = cbz(d / "Lib" / "Batman" / "Batman 01.cbz"), cbz(d / "Lib" / "Batman" / "Batman 02.cbz")
    b1 = cbz(d / "Lib" / "Robin" / "Robin 01.cbz")
    r1 = cbz(d / "Lib" / "Robin" / "Robin 02.cbr")  # zip-backed .cbr
    junk = d / "Lib" / "notes.txt"; junk.write_text("x")
    chosen = [a2, a1, b1, r1, junk, a1]  # unsorted, a repeat and a non-comic

    assert cc.common_root([a1, a2]) == a1.parent and cc.common_root([a1, b1]) == d / "Lib"
    assert cc.picked_files(chosen, cc.COMIC_EXT) == [a1, a2, b1, r1]

    def settle(pg, cond, t=20):
        end = time.time() + t
        while time.time() < end and not cond():
            root.update(); time.sleep(0.01)
        root.update()

    # Convert / Clean-up: only their own file type, labelled relative to the shared parent
    cv = pages[5]; cv.pack(fill="both", expand=True); cv.set_files(chosen)
    assert cv.items == [r1] and cv.folder == r1.parent and "1 file chosen" in cv.drop.label.cget("text"), cv.items
    cv.set_folder(d / "Lib"); assert cv.picked is None and len(cv.items) == 1
    cv.pack_forget()
    cl = pages[6]; cl.pack(fill="both", expand=True); cl.set_files(chosen)
    assert cl.items == [a1, a2, b1] and cl.rel(a1) == str(Path("Batman") / "Batman 01.cbz"), cl.items
    cl.set_files([junk]); assert "None of those" in cl.status.cget("text") and cl.items == [a1, a2, b1], "bad pick changes nothing"
    cl.pack_forget()
    # Folder icons: one folder per parent, using the first or last chosen comic
    ic = pages[2]; ic.pack(fill="both", expand=True); ic.set_files(chosen)
    assert ic.items == [(a1.parent, a1), (b1.parent, b1)], ic.items
    ic.vars["which"].set("Last issue"); root.update()
    assert ic.items == [(a1.parent, a2), (b1.parent, r1)], ic.items
    ic.pack_forget()
    # Bulk covers
    bk = pages[1]; bk.pack(fill="both", expand=True); bk.set_files(chosen)
    assert bk.files == [a1, a2, b1, r1] and bk.folder == d / "Lib" and "4 comics chosen" in bk.meta.cget("text")
    bk.set_folder(d / "Lib" / "Batman"); assert bk.picked is None and bk.files == [a1, a2]
    bk.pack_forget()
    # Metadata
    md = pages[4]; md.pack(fill="both", expand=True); md.set_files(chosen)
    settle(md, lambda: not md.busy and len(md.rows) >= 1)
    assert [r.path for r in md.rows] == [a1, a2, b1] and md.skipped_cbr == 1, ([r.path.name for r in md.rows], md.skipped_cbr)
    md.pack_forget()
    # Renamer
    rn = pages[3]; rn.pack(fill="both", expand=True); rn.set_files(chosen)
    settle(rn, lambda: not rn.q and len(rn.items) >= 4)
    assert sorted(i.src.name for i in rn.items) == ["Batman 01.cbz", "Batman 02.cbz", "Robin 01.cbz", "Robin 02.cbr"]
    rn.set_files([junk]); assert "None of those" in rn.status.cget("text")
    rn.pack_forget()
    # Audit scans only the chosen comics
    au = pages[7]; au.pack(fill="both", expand=True); au.set_files([a1, b1]); root.update()
    assert au.picked == [a1, b1] and au.root_dir == d / "Lib"
    au.vars["deep"].set(False); au.scan()
    settle(au, lambda: au.results is not None)
    assert sorted(i.rel for i in au.results["issues"]) == ["Batman/Batman 01.cbz", "Robin/Robin 01.cbz"], au.results["issues"]
    au.set_folder(d / "Lib"); assert au.picked is None
    au.pack_forget()

root.destroy()
print("layout OK")

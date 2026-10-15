"""The Library audit page on the page shell, in two columns with a divider you can drag (the library and the findings on the
left, the checks on the right): Library folds after the first scan, the strip of counts, the chips, the Checks toggles, the
Details panel over the right half with its pointers to other tools, the reading-order folders left out of Duplicates, the
confirmation before fixing, fixing, ignoring, wishlists and the Archive folders."""
import csv, io, random, sys, tempfile, time, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from PIL import Image, ImageDraw
import archive_tools as at
import audit_core as ac
import customtkinter as ctk
from tkinter import filedialog, messagebox
import library_scan as ls
import page_audit as pa
from reading_orders import ReadingOrders


def img(seed, size=(900, 1300), q=90):
    im = Image.new("RGB", size, (200, 200, 200)); d = ImageDraw.Draw(im); w, h = size; rnd = random.Random(seed)
    for _ in range(8):
        x0, y0 = rnd.random() * .7, rnd.random() * .7
        d.rectangle([x0 * w, y0 * h, (x0 + .1 + rnd.random() * .2) * w, (y0 + .1 + rnd.random() * .2) * h],
                    fill=tuple(rnd.randrange(256) for _ in range(3)))
    b = io.BytesIO(); im.save(b, "JPEG", quality=q); return b.getvalue()


def cbz(p, pages=12, seed=1, junk=(), **kw):
    p.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(p, "w") as z:
        for i in range(pages):
            z.writestr(f"{i:03d}.jpg", img(seed if i == 0 else seed * 100 + i, **kw))
        for j in junk: z.writestr(j, b"x")


root = ctk.CTk(); root.geometry("1300x900")
errors = []; root.report_callback_exception = lambda *a: errors.append(a)
page = pa.AuditPage(root); page.pack(fill="both", expand=True); root.update()


def wait(t=60):
    t0 = time.time()
    while page.q and time.time() - t0 < t: root.update(); time.sleep(0.01)
    root.update(); assert not page.q, "did not finish"


def rows():
    return [page.tree.item(i, "values") for i in page.tree.get_children()]


def show(kind):
    page.vars["filter"].set(kind); page._refresh(); root.update()


def click_sel(iid):
    page.tree.update(); x, y, w, h = page.tree.bbox(iid, "sel")
    e = type("E", (), {"x": x + 3, "y": y + 3})(); return page._click(e)


def foot(): return page.bar_btn.cget("text")
def side(): return [b.cget("text") for b in page.side_row.winfo_children()]
def strip(): return " ".join(w.cget("text") for w in page.strip_box.winfo_children())


with tempfile.TemporaryDirectory() as d:
    d = Path(d); lib = d / "lib"
    for n in (1, 2, 5): cbz(lib / "Batman" / f"Batman v2 {n:02d} (2016).cbz", seed=n)
    cbz(lib / "Batman" / "Batman v2 03 (2016).cbz", seed=3, junk=("Thumbs.db", "info.nfo"))
    cbz(lib / "Copy" / "Batman v2 02 (2016) (Digital).cbz", seed=2, q=40, size=(450, 650))
    (lib / "Bad").mkdir(); (lib / "Bad" / "Text 01.cbz").write_bytes(b"hello")
    cbz(lib / "Q" / "Short 01.cbz", pages=3, seed=90, size=(300, 400))
    cbz(lib / "Old" / "Old 001.cbr", pages=12, seed=120)                      # a zip-backed .cbr
    at.apply_metadata(lib / "Batman" / "Batman v2 01 (2016).cbz", {"count": "6"}, False)

    cache_file = d / "cache.json"; orig = ls.scan_library
    pa.scan_library = lambda *a, **k: orig(*a, cache_path=cache_file, **k)

    # ---- before anything: the library and findings on the left, the checks on the right with a divider between them
    assert [s.title.cget("text") for s in page.segments] == ["Library", "Findings", "Checks"]
    assert [s.state for s in page.segments] == ["active", "locked", "idle"]
    assert page.scroll is None and page.table.winfo_rootx() < page.splitter.winfo_rootx() < page.right_wrap.winfo_rootx()
    assert page.s2.body.winfo_ismapped() and page.table.winfo_height() > 100, "the checks are always in view; the list uses the height"
    w0 = page.right_wrap.winfo_width(); k = page.splitter._scale()
    page.splitter._press(type("E", (), {"x_root": 1000})()); page.splitter._drag(type("E", (), {"x_root": 880})()); page.splitter._release(None); root.update()
    assert page.right_wrap.winfo_width() > w0 and abs(page.right_width - (420 + 120 / k)) <= 2, "dragging the divider left widens the checks"
    assert page.state()["_split_width"] == int(page.right_width) and page.left.winfo_width() / k >= page.left_min - 5
    page.restore({"_split_width": 3000}); root.update()
    assert page.left.winfo_width() / k >= page.left_min - 5, "the left column keeps its minimum width"
    page.restore({"_split_width": 420}); root.update()
    assert foot() == "Scan library" and page.bar_btn.cget("state") == "disabled"
    assert page.s1.opened and "Nothing scanned yet" in strip()
    page.set_folder(lib); assert page.bar_btn.cget("state") == "normal"
    page.show_details(); assert not page.panel_open and "Scan the library first" in page.status.cget("text")
    page.say("")
    page.scan(); wait()
    print("status:", page.status.cget("text"), "| meta:", page.meta.cget("text"))
    assert len(page.results["issues"]) == 8

    # ---- the first scan folds Library (the checks stay in their column); a later scan leaves it alone
    assert not page.s1.opened and page.s2.body.winfo_ismapped() and page.s3.body.winfo_ismapped()
    assert page.s1.state == "done" and page.s2.state == "done" and page.s3.state == "active"
    assert page.s2.summary.cget("text") == "6 checks", page.s2.summary.cget("text")
    page.s1.set_open(True); page.scan(); wait(); assert page.s1.opened, "a rescan does not fold it again"
    page.s1.set_open(False)

    # ---- the strip of counts and the chips (All leaves warnings and reading orders out)
    counts = page._counts()
    print(counts)
    assert counts[ac.BROKEN] == 1 and counts[ac.DUPLICATE] == 1 and counts[ac.MISSING] == 1
    assert counts[ac.JUNK] == 1 and counts[ac.CBR] == 1 and counts[ac.WARNING] >= 1 and counts[ac.ORDER] == 0
    assert counts[pa.ALL] == sum(counts[k] for k in (ac.BROKEN, ac.DUPLICATE, ac.MISSING, ac.JUNK, ac.CBR))
    s = strip(); assert s.startswith("1 broken file") and "1 group of duplicates" in s and "1 series with gaps" in s and "1 CBR file" in s, s
    page.strip_labels[ac.JUNK]._label.event_generate("<Button-1>"); root.update()
    assert page.vars["filter"].get() == ac.JUNK, "a count in the strip selects its list"
    assert "Junk 1" in page.chips[ac.JUNK].cget("text") and "Warnings" in page.chips[ac.WARNING].cget("text")
    assert not page.chips[ac.ORDER].winfo_ismapped(), "no reading-order folder is marked, so no chip"
    show(pa.ALL)
    assert not any(r[1] == "Warning" for r in rows())
    assert {r[1] for r in rows()} == {"Broken", "Duplicate", "Missing", "Junk", "CBR"}
    # safe fixes come pre-ticked, nothing else does; the footer's main button counts them
    ticked = {r[1] for r in rows() if r[0] == "☑"}
    assert ticked == {"Junk", "CBR"}, ticked
    assert foot() == "Fix 2 checked" and page.bar_btn.cget("state") == "normal"
    assert side() == ["Rescan", "Ignored…", "Archive…"], side()

    # ---- the Checks toggles decide which kinds are listed and counted
    page.vars["check_junk"].set(False); page._refresh(); root.update()
    assert not page.chips[ac.JUNK].winfo_ismapped() and "junk" not in strip() and ac.JUNK not in {r[1] for r in rows()}
    assert foot() == "Fix 1 checked", foot()
    page.vars["filter"].set(ac.JUNK); page._refresh()
    assert page.vars["filter"].get() == pa.ALL, "a list whose check is off falls back to All"
    page.vars["check_junk"].set(True); page._refresh(); root.update()
    assert page.chips[ac.JUNK].winfo_ismapped() and foot() == "Fix 2 checked"

    # ---- duplicates: best copy kept (no tick box), the copy is offered
    show(ac.DUPLICATE)
    dr = rows(); assert len(dr) == 2 and dr[0][0] == "" and dr[1][0] == "☐" and "best copy" in dr[0][3], dr
    assert "Batman v2 02 (2016).cbz" in dr[0][2] and "Digital" in dr[1][2]
    assert page.bar_btn.cget("state") == "disabled" and foot() == "Fix checked"
    iid = page.tree.get_children()[0]; assert click_sel(iid) is None            # the kept copy cannot be ticked
    iid = page.tree.get_children()[1]; r_ = click_sel(iid); assert r_ == "break" and rows()[1][0] == "☑"
    assert page.bar_btn.cget("state") == "normal" and foot() == "Fix 1 checked"
    click_sel(iid); assert rows()[1][0] == "☐"                                  # untick again for the next steps
    # ---- broken, missing, warnings
    show(ac.BROKEN); assert [r[2] for r in rows()] == ["Bad/Text 01.cbz"] and rows()[0][0] == "☐"
    show(ac.MISSING); mr = rows()
    assert len(mr) == 1 and mr[0][2] == "Batman" and mr[0][3] == "Issues (v2): #4, #6", mr
    assert page.btn_copy.winfo_ismapped() and page.btn_copy.cget("state") == "normal" and not page.btn_convert.winfo_ismapped()
    page.copy_wishlist(); assert "Batman v2 #4" in root.clipboard_get()
    filedialog.asksaveasfilename = lambda **k: str(d / "wish.csv")
    page.save_wishlist(); assert list(csv.reader(open(d / "wish.csv", encoding="utf-8-sig")))[0] == ["Series", "Volume", "Type", "Number"]
    show(ac.WARNING); assert any(r[2] == "Q/Short 01.cbz" and "Only 3 pages" in r[3] for r in rows())
    assert not page.btn_copy.winfo_ismapped()
    page.vars["min_pages"].set("2"); page._refresh()                      # limits are editable without rescanning
    assert not any("Only 3 pages" in r[3] for r in rows())
    page.vars["min_pages"].set("10"); page._refresh()
    show(ac.CBR); assert page.btn_convert.winfo_ismapped() and not page.btn_copy.winfo_ismapped()

    # ---- the Details panel: over the right half, down to the footer, with a pointer to the tool that fixes each kind
    opened = []; page.open_tool = lambda key, view=None: opened.append((key, view))
    show(pa.ALL)
    page.toggle_details(); root.update()
    assert page.panel_open and page.panel.winfo_ismapped()
    pw, ww = page.panel.winfo_width(), page.winfo_width()
    assert abs(pw - ww / 2) <= 4, (pw, ww)
    assert page.panel.winfo_rootx() >= page.winfo_rootx() + ww / 2 - 6, "it sits over the right half"
    assert page.panel.winfo_rooty() + page.panel.winfo_height() <= page.footer.winfo_rooty() + 2, "and stops at the footer"
    assert (ac.CBR, "tool:convert") in page.actions and (ac.DUPLICATE, "tool:stats") in page.actions and (ac.JUNK, "show:" + ac.JUNK) in page.actions
    page.actions[(ac.CBR, "tool:convert")].invoke(); root.update()
    assert opened == [("convert", None)] and not page.panel_open, "the pointer opens the tool and closes the panel"
    page.toggle_details(); root.update()
    page.actions[(ac.DUPLICATE, "tool:stats")].invoke(); assert opened[-1] == ("stats", None)
    page.toggle_details(); root.update()
    page.actions[(ac.BROKEN, "show:" + ac.BROKEN)].invoke(); root.update()
    assert page.vars["filter"].get() == ac.BROKEN and not page.panel_open, "Show in list selects that list"
    page.toggle_details(); page.toggle_details(); assert not page.panel_open
    show(pa.ALL)

    # ---- fixing: the confirmation first (lines for each kind, and a Details button listing every file)
    plan = ac.plan_fixes(page.visible())
    results = []
    def press(details_first):
        def go():
            dlg = page._fix_dialog
            if details_first:
                dlg["details"].invoke(); root.update()
                assert dlg["box"].winfo_ismapped() and len(dlg["tree"].get_children()) == len(plan)
                vals = [dlg["tree"].item(i, "values") for i in dlg["tree"].get_children()]
                assert {v[2] for v in vals} == {"no"} and any("Old 001.cbz" in v[1] for v in vals), vals
                dlg["ok"].invoke()
            else:
                dlg["cancel"].invoke()
        return go
    root.after(300, press(True)); results.append(page._confirm_fix(plan))
    root.after(300, press(False)); results.append(page._confirm_fix(plan))
    assert results == [True, False] and "Convert 1 CBR file" in page._fix_dialog["lines"][1]
    # declined: nothing happens
    page._confirm_fix = lambda plan: False
    show(ac.JUNK); page.fix_checked(); wait()
    assert zipfile.ZipFile(lib / "Batman" / "Batman v2 03 (2016).cbz").namelist().count("Thumbs.db") == 1   # declined
    msgs = []
    page._confirm_fix = lambda plan: (msgs.append("\n".join(ac.plan_lines(plan))), True)[1]
    page.fix_checked(); wait()
    assert "Remove junk files from 1 comic" in msgs[0] and "Convert" not in msgs[0]
    assert "Thumbs.db" not in zipfile.ZipFile(lib / "Batman" / "Batman v2 03 (2016).cbz").namelist()
    assert (lib / "Old" / "Old 001.cbr").exists()                          # the CBR was out of view, so untouched
    assert page.results is not None and page._counts()[ac.JUNK] == 0, page._counts()    # rescanned afterwards
    print("status after junk fix:", page.status.cget("text"))
    assert "Fixed 1 file" in page.status.cget("text")
    show(ac.CBR); page.fix_checked(); wait()
    assert "Convert 1 CBR file" in msgs[-1] and "deleted once its CBZ has been verified" in msgs[-1]
    assert (lib / "Old" / "Old 001.cbz").exists() and not (lib / "Old" / "Old 001.cbr").exists() and page._counts()[ac.CBR] == 0
    # duplicates: tick the copy, archive it
    show(ac.DUPLICATE); iid = page.tree.get_children()[1]; click_sel(iid)
    page.fix_checked(); wait()
    assert (lib / "Copy" / "Archive" / "Batman v2 02 (2016) (Digital).cbz.bak").exists() and not (lib / "Copy" / "Batman v2 02 (2016) (Digital).cbz").exists()
    assert page._counts()[ac.DUPLICATE] == 0 and "No duplicates" in page.meta.cget("text")
    # a failing fix is reported and kept in the row
    (lib / "Old" / "New 001.cbr").write_bytes(b"not an archive")
    page.scan(); wait(); show(ac.CBR)
    page.fix_checked(); wait()
    fr = [r for r in rows() if "New 001" in r[2]]
    assert fr and "Fix failed" in fr[0][3] and "1 failed" in page.status.cget("text") and (lib / "Old" / "New 001.cbr").exists()
    (lib / "Old" / "New 001.cbr").unlink(); page.scan(); wait()

    # ---- ignore, review, restore, and persistence
    show(ac.MISSING); iid = page.tree.get_children()[0]; page.tree.selection_set(iid); page._sync_buttons()
    assert page.btn_ignore.cget("state") == "normal"
    page.ignore_selected(); root.update()
    assert rows() == [] and page._counts()[ac.MISSING] == 0
    saved = page.state(); assert saved["ignored"] and "Batman" in saved["ignored"]
    page.restore(saved); page._refresh(); assert rows() == []
    page.scan(); wait(); show(ac.MISSING); assert rows() == [], "an ignored gap stays hidden after a rescan"
    page.show_ignored(); root.update()
    ui = page._ignored_ui; assert ui["labels"] == ["Missing from Batman: Issues (v2): #4, #6"], ui["labels"]
    ui["box"].selection_set(0); ui["restore"](True); root.update()
    assert page.ignored() == {} and len(rows()) == 1
    page._ignored_win.destroy()
    # a broken file can be ignored too
    show(ac.BROKEN); page.tree.selection_set(page.tree.get_children()[0]); page.ignore_selected()
    assert rows() == [] and page.ignored()

    # ---- the Archive folders
    page.show_archive(); root.update()
    a = page._archive
    assert "1 file in Archive folders" in a["info"].cget("text"), a["info"].cget("text")
    messagebox.askyesno = lambda *a_, **k: False
    a["ticked"].update(a["rows"].values()); a["purge"](); assert (lib / "Copy" / "Archive").exists()   # declined
    messagebox.askyesno = lambda *a_, **k: True
    a["purge"](); root.update()
    assert not (lib / "Copy" / "Archive").exists() and "empty" in a["info"].cget("text") and "Purged 1 file" in page.status.cget("text")
    page._archive_win.destroy()

    # ---- reading orders: marked folders are left out of Duplicates, shown in their own list, and can be brought back
    lib2 = d / "lib2"
    cbz(lib2 / "Sam" / "Sam 01 (2020).cbz", seed=7, pages=14); cbz(lib2 / "Sam" / "Sam 02 (2020).cbz", seed=8)
    cbz(lib2 / "Arcs" / "Pick" / "01 - Sam 01 (2020).cbz", seed=7, pages=40)     # a bigger copy of Sam 01, inside a reading order
    cbz(lib2 / "Arcs" / "Pick" / "02 - Sam 02 (2020).cbz", seed=8)
    page.orders = ReadingOrders([str(lib2 / "Arcs")])
    page.vars["filter"].set(pa.ALL); page.set_folder(lib2); page.scan(); wait()
    c2 = page._counts()
    assert c2[ac.DUPLICATE] == 0, "reading-order copies are not duplicates of the real comics"
    assert c2[ac.ORDER] == 2 and page.chips[ac.ORDER].winfo_ismapped() and "Reading orders 2" in page.chips[ac.ORDER].cget("text")
    assert page.results["left_out"] == 2 and "2 comics left out of Duplicates" in page.orders_note.cget("text")
    show(ac.ORDER); orow = rows()
    assert len(orow) == 1 and orow[0][1] == "Reading order" and orow[0][0] == "" and "2 comics" in orow[0][3] and "2 also in your library" in orow[0][3], orow
    assert "reading order" not in strip()
    page.show_details(); root.update()
    assert any("2 comics left out of Duplicates" in w.cget("text") for w in page.panel_body.winfo_children()[1].winfo_children()), "the panel says what was left out"
    page.close_details()
    page.vars["with_orders"].set(True); root.update()
    assert "Rescan" in page.status.cget("text"), page.status.cget("text")
    page.scan(); wait(); show(ac.DUPLICATE)
    dr = rows(); assert page._counts()[ac.DUPLICATE] == 2, "now the copies are compared too"
    keepers = [r for r in dr if "best copy" in r[3]]
    assert len(keepers) == 2 and all(not r[2].startswith("Arcs") for r in keepers), "the original outside the folder is kept, although the copy is bigger"
    page.vars["with_orders"].set(False)

    # ---- theme, settings round-trip, folder change
    ctk.set_appearance_mode("dark"); page.apply_theme(); root.update()
    saved = page.state(); page.restore(saved)
    assert saved["filter"] == ac.DUPLICATE and saved["check_junk"] is True and "with_orders" in saved
    page.set_folder(d); assert page.results is None and rows() == [] and page.s1.opened and page.s3.state == "locked"
    assert not errors, errors[:2]
# ---- the whole app has the page, and Clean-up is gone; the audit links go to the right tools
import comic_tool
app = comic_tool.App()
assert "audit" in app.pages and "cleanup" not in app.pages and "cleanup" not in comic_tool.TOOLS
assert any(h == "Library Audit" for h, _ in comic_tool.GROUPS)
assert app.pages["audit"].orders is app.orders and app.pages["audit"].open_tool is not None
app.show("audit"); app.update()
with tempfile.TemporaryDirectory() as t:
    t = Path(t); cbz(t / "A 01.cbz", pages=3)
    app.pages["audit"].set_folder(t)
    seen = []
    app.pages["metadata"].open_with = lambda folder, view=None, origin=None, back=None: seen.append((Path(folder), view, origin, bool(back)))
    app._open_from_audit("metadata", "no_series"); app.update()
    assert seen == [(t, "no_series", "Library audit", True)] and app.current == "metadata"
    folders = []
    app.pages["convert"].set_folder = lambda p, *a, **k: folders.append(Path(p))
    app._open_from_audit("convert"); assert folders == [t] and app.current == "convert"
    app._open_from_audit("stats"); assert app.current == "stats"
app.destroy(); root.destroy()
print("AUDIT UI OK")

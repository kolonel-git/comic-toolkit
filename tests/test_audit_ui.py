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


root = ctk.CTk(); root.geometry("1300x800")
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
    page.tree.update(); x, y, w, h = page.tree.bbox(iid, "#1")
    e = type("E", (), {"x": x + 3, "y": y + 3})(); return page._click(e)


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
    assert page.btn_scan.cget("state") == "disabled" and page.btn_fix.cget("state") == "disabled"
    page.set_folder(lib); assert page.btn_scan.cget("state") == "normal"
    page.scan(); wait()
    print("status:", page.status.cget("text"), "| meta:", page.meta.cget("text"))
    assert len(page.results["issues"]) == 8

    # ---- the chips count each type; All leaves warnings out
    counts = page._counts()
    print(counts)
    assert counts[ac.BROKEN] == 1 and counts[ac.DUPLICATE] == 1 and counts[ac.MISSING] == 1
    assert counts[ac.JUNK] == 1 and counts[ac.CBR] == 1 and counts[ac.WARNING] >= 1
    assert counts[pa.ALL] == sum(counts[k] for k in (ac.BROKEN, ac.DUPLICATE, ac.MISSING, ac.JUNK, ac.CBR))
    assert "Junk 1" in page.chips[ac.JUNK].cget("text") and "Warnings" in page.chips[ac.WARNING].cget("text")
    show(pa.ALL)
    assert not any(r[1] == "Warning" for r in rows())
    assert {r[1] for r in rows()} == {"Broken", "Duplicate", "Missing", "Junk", "CBR"}
    # safe fixes come pre-ticked, nothing else does
    ticked = {r[1] for r in rows() if r[0] == "☑"}
    assert ticked == {"Junk", "CBR"}, ticked
    assert page.btn_fix.cget("state") == "normal"

    # ---- duplicates: best copy kept (no tick box), the copy is offered
    show(ac.DUPLICATE)
    dr = rows(); assert len(dr) == 2 and dr[0][0] == "" and dr[1][0] == "☐" and "best copy" in dr[0][3], dr
    assert "Batman v2 02 (2016).cbz" in dr[0][2] and "Digital" in dr[1][2]
    assert page.btn_fix.cget("state") == "disabled"
    iid = page.tree.get_children()[0]; assert click_sel(iid) is None            # the kept copy cannot be ticked
    iid = page.tree.get_children()[1]; assert click_sel(iid) == "break" and rows()[1][0] == "☑"
    assert page.btn_fix.cget("state") == "normal"
    click_sel(iid); assert rows()[1][0] == "☐"                                  # untick again for the next steps
    # ---- broken, missing, warnings
    show(ac.BROKEN); assert [r[2] for r in rows()] == ["Bad/Text 01.cbz"] and rows()[0][0] == "☐"
    show(ac.MISSING); mr = rows()
    assert len(mr) == 1 and mr[0][2] == "Batman" and mr[0][3] == "Issues (v2): #4, #6", mr
    assert page.wish_row.winfo_ismapped() and page.btn_copy.cget("state") == "normal"
    page.copy_wishlist(); assert "Batman v2 #4" in root.clipboard_get()
    filedialog.asksaveasfilename = lambda **k: str(d / "wish.csv")
    page.save_wishlist(); assert list(csv.reader(open(d / "wish.csv", encoding="utf-8-sig")))[0] == ["Series", "Volume", "Type", "Number"]
    show(ac.WARNING); assert any(r[2] == "Q/Short 01.cbz" and "Only 3 pages" in r[3] for r in rows())
    assert not page.wish_row.winfo_ismapped()
    page.vars["min_pages"].set("2"); page._refresh()                      # limits are editable without rescanning
    assert not any("Only 3 pages" in r[3] for r in rows())
    page.vars["min_pages"].set("10"); page._refresh()
    # ---- fixing is limited to the list you are looking at
    messagebox.askyesno = lambda *a, **k: False
    show(ac.JUNK); page.fix_checked(); wait()
    assert zipfile.ZipFile(lib / "Batman" / "Batman v2 03 (2016).cbz").namelist().count("Thumbs.db") == 1   # declined
    msgs = []
    messagebox.askyesno = lambda title, text, **k: (msgs.append(text), True)[1]
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
    assert rows() == [] and page._counts()[ac.MISSING] == 0 and page.btn_ignored.cget("state") == "normal"
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

    # ---- theme, settings round-trip, folder change
    ctk.set_appearance_mode("dark"); page.apply_theme(); root.update()
    saved = page.state(); page.restore(saved)
    assert saved["filter"] == ac.BROKEN
    page.set_folder(d); assert page.results is None and rows() == []
    assert not errors, errors[:2]
# ---- the whole app has the page, and Clean-up is gone
import comic_tool
app = comic_tool.App()
assert "audit" in app.pages and "cleanup" not in app.pages and "cleanup" not in comic_tool.TOOLS
assert any(h == "Library Audit" for h, _ in comic_tool.GROUPS)
app.show("audit"); app.update()
app.destroy(); root.destroy()
print("AUDIT UI OK")

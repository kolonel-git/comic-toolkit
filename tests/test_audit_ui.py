import csv, io, random, sys, tempfile, time, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from PIL import Image, ImageDraw
import archive_tools as at
import customtkinter as ctk
from tkinter import filedialog, messagebox
import page_audit as pa


def img(seed, size=(900, 1300), q=90):
    im = Image.new("RGB", size, (200, 200, 200)); d = ImageDraw.Draw(im); w, h = size; rnd = random.Random(seed)
    for _ in range(8):
        x0, y0 = rnd.random() * .7, rnd.random() * .7
        d.rectangle([x0 * w, y0 * h, (x0 + .1 + rnd.random() * .2) * w, (y0 + .1 + rnd.random() * .2) * h],
                    fill=tuple(rnd.randrange(256) for _ in range(3)))
    b = io.BytesIO(); im.save(b, "JPEG", quality=q); return b.getvalue()


def cbz(p, pages=12, seed=1, **kw):
    p.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(p, "w") as z:
        for i in range(pages):
            z.writestr(f"{i:03d}.jpg", img(seed if i == 0 else seed * 100 + i, **kw))


def wait(root, page, t=60):
    t0 = time.time()
    while page.q and time.time() - t0 < t:
        root.update(); time.sleep(0.01)
    root.update()
    assert not page.q, "scan did not finish"


root = ctk.CTk()
page = pa.AuditPage(root)
page.pack(fill="both", expand=True)
root.update()
with tempfile.TemporaryDirectory() as d:
    d = Path(d); lib = d / "lib"
    for n in (1, 2, 3, 5):
        cbz(lib / "Batman" / f"Batman v2 {n:02d} (2016).cbz", seed=n)
    cbz(lib / "Copy" / "Batman v2 02 (2016) (Digital).cbz", seed=2, q=40, size=(450, 650))
    (lib / "Bad").mkdir(); (lib / "Bad" / "Text 01.cbz").write_bytes(b"hello")
    cbz(lib / "Q" / "Short 01.cbz", pages=3, seed=90, size=(300, 400))
    at.apply_metadata(lib / "Batman" / "Batman v2 01 (2016).cbz", {"count": "6"}, False)
    page.drop.set  # exists
    # no folder yet
    assert page.btn_scan.cget("state") == "disabled"
    page.set_folder(lib)
    assert page.btn_scan.cget("state") == "normal"
    page.vars["report"].set("Broken")
    # --- quick scan
    cache_file = d / "cache.json"
    import library_scan as ls
    orig = ls.scan_library
    pa.scan_library = lambda *a, **k: orig(*a, cache_path=cache_file, **k)
    page.scan(); wait(root, page)
    r = page.results
    print("status:", page.status.cget("text"), "| meta:", page.meta.cget("text"))
    assert len(r["issues"]) == 7
    tree = page.trees["Broken"][1]
    rows = [tree.item(i, "values") for i in tree.get_children()]
    print("broken rows:", rows)
    assert any(v[0] == "Bad/Text 01.cbz" for v in rows)
    # --- integrity on
    page.vars["integrity"].set(True); page.scan(); wait(root, page)
    rows = [page.trees["Broken"][1].item(i, "values") for i in page.trees["Broken"][1].get_children()]
    assert any("Not a valid zip" in v[1] for v in rows), rows
    # --- reports switch
    page.vars["report"].set("Duplicates"); root.update()
    dt = page.trees["Duplicates"][1]
    drows = [dt.item(i, "values") for i in dt.get_children()]
    print("dup rows:", drows)
    assert len(drows) == 2 and drows[0][0] == "☐" and drows[1][0] == "☑", "biggest left unticked"
    assert page.btn_move.cget("state") == "normal"
    # toggle checkbox via click handler on the second row
    iid = dt.get_children()[1]
    x, y, w, h = dt.bbox(iid, "#1")
    class E: pass
    e = E(); e.x, e.y = x + 3, y + 3
    assert page._click(e) == "break" and dt.set(iid, "sel") == "☐" and page.btn_move.cget("state") == "disabled"
    page._click(e); assert dt.set(iid, "sel") == "☑"
    # --- move to archive (decline, then accept)
    messagebox.askyesno = lambda *a, **k: False
    page.move_checked(); assert len(list((lib / "Copy").glob("*.cbz"))) == 1
    messagebox.askyesno = lambda *a, **k: True
    page.move_checked()
    assert not list((lib / "Copy").glob("*.cbz")) and (lib / "Copy" / "Archive" / "Batman v2 02 (2016) (Digital).cbz.bak").exists()
    assert page.results["dups"] == [] and "No duplicates" in page.meta.cget("text"), page.meta.cget("text")
    print("after move:", page.status.cget("text"))
    # --- missing
    page.vars["report"].set("Missing"); root.update()
    mt = page.trees["Missing"][1]
    mrows = [mt.item(i, "values") for i in mt.get_children()]
    print("missing rows:", mrows)
    assert mrows and mrows[0][0] == "Batman" and "#4" in mrows[0][3] and "#6" in mrows[0][3], mrows
    assert page.btn_copy.cget("state") == "normal"
    page.copy_wishlist(); clip = root.clipboard_get(); print("clipboard:", clip.splitlines())
    assert "Batman v2 #4" in clip
    filedialog.asksaveasfilename = lambda **k: str(d / "wish.txt")
    page.save_wishlist(); assert "Batman v2 #6" in (d / "wish.txt").read_text(encoding="utf-8")
    filedialog.asksaveasfilename = lambda **k: str(d / "wish.csv")
    page.save_wishlist(); assert list(csv.reader(open(d / "wish.csv", encoding="utf-8-sig")))[0] == ["Series", "Volume", "Issue"]
    # --- quality
    page.vars["report"].set("Quality"); root.update()
    qt = page.trees["Quality"][1]
    qrows = [qt.item(i, "values") for i in qt.get_children()]
    assert any(v[0] == "Q/Short 01.cbz" and "Only 3 pages" in v[1] for v in qrows), qrows
    # --- csv export for each report
    for rep in pa.REPORTS:
        page.vars["report"].set(rep); out = d / f"{rep}.csv"
        filedialog.asksaveasfilename = lambda **k: str(out)
        page.export_csv()
        data = list(csv.reader(open(out, encoding="utf-8-sig")))
        print(rep, "csv rows:", len(data) - 1)
        assert len(data) >= 1
    # --- similar-cover scan + stop
    page.vars["similar"].set(True); page.vars["deep"].set(False)
    page.scan(); page.stop.set(); wait(root, page)
    assert page.results is not None
    page.stop.clear()
    # --- cache used on re-scan
    page.scan(); wait(root, page); assert page.results["cache_hits"] > 0
    # --- theme + settings round-trip
    ctk.set_appearance_mode("dark"); page.apply_theme(); root.update()
    saved = page.state(); page.restore(saved)
    assert saved["report"] == "Quality"
    # --- folder change clears results
    page.set_folder(d); assert page.results is None
# --- whole app registers the page
import comic_tool
app = comic_tool.App()
assert "audit" in app.pages and any(h == "Library Audit" for h, _ in comic_tool.GROUPS)
app.show("audit"); app.update()
app.destroy(); root.destroy()
print("AUDIT UI OK")

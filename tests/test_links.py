"""Links between tools: the Next steps row, the app's goto (a folder or files already loaded, a chip saying where it came from)
and the links a finished run offers."""
import io, sys, tempfile, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from PIL import Image
import comic_tool as ct

ct.SETTINGS = Path(tempfile.mkdtemp()) / "settings.json"   # never read or write the real settings
app = ct.App(); app.update()


def cbz(p):
    p.parent.mkdir(parents=True, exist_ok=True)
    b = io.BytesIO(); Image.new("RGB", (60, 90), (9, 9, 9)).save(b, "JPEG")
    with zipfile.ZipFile(p, "w") as z:
        for i in range(3): z.writestr(f"{i + 1:03d}.jpg", b.getvalue())
    return p


def labels(page):
    return [b.cget("text") for b in page._next_items]


with tempfile.TemporaryDirectory() as d:
    d = Path(d); lib = d / "Lib"
    a = cbz(lib / "Batman" / "Batman 001 (2016).cbz")
    # every page can be reached with a goto, every shell page has the row
    assert all(callable(pg.goto) for pg in app.pages.values())
    bulk, aceo, rename = app.pages["bulk"], app.pages["aceo"], app.pages["rename"]
    assert bulk.next_bar.winfo_manager() == ""
    # the row shows its links, replaces them, and clears
    calls = []
    bulk.show_next([("One", lambda: calls.append(1)), ("Two", lambda: calls.append(2))]); app.update()
    assert labels(bulk) == ["One", "Two"] and bulk.next_bar.winfo_manager() == "pack"
    bulk._next_items[1].inner.invoke(); assert calls == [2]
    bulk.show_next([("Three", lambda: 0)]); assert labels(bulk) == ["Three"]
    bulk.clear_next(); assert labels(bulk) == [] and bulk.next_bar.winfo_manager() == ""
    # goto opens the tool with the folder loaded and a chip saying where it came from, with Back
    app.show("bulk"); app.update()
    bulk.link("icons", folder=lib)(); app.update()
    assert app.current == "icons" and app.pages["icons"].folder == lib
    assert "From Bulk folder" in app.pages["icons"].origin_label.cget("text") and app.pages["icons"].origin.winfo_manager() == "pack"
    app.pages["icons"].origin_back.inner.invoke()
    app.update(); assert app.current == "bulk"
    # files go to a page that takes paths
    app.pages["bulk"].link("aceo", folder=a.parent)(); app.update()
    assert app.current == "aceo"
    # leaving a page clears its row
    aceo.show_next([("x", lambda: 0)]); app.show("home"); assert labels(aceo) == []
    # the empty ACEO list offers a way to get covers
    assert "covers" in aceo.drop.extra
    aceo.drop.extra["covers"].inner.invoke(); app.update()
    assert app.current == "bulk"
    # the Renamer offers the next tools after a real apply
    from tkinter import messagebox
    import time
    messagebox.askyesno = lambda *a, **k: True
    cbz(lib / "Saga" / "saga 3 (2012).cbz")
    app.show("rename"); app.update()
    rename.set_folder(lib / "Saga")
    t = time.time()
    while rename.q and time.time() - t < 30: app.update(); time.sleep(0.02)
    app.update(); assert rename.items and rename.items[0].checked
    rename.apply(); app.update()
    assert labels(rename) == ["Update the metadata from the new names", "Check the library for duplicates"], labels(rename)
    rename._next_items[0].inner.invoke(); app.update()
    assert app.current == "metadata" and app.pages["metadata"].root_dir == lib / "Saga"
    assert "From Renamer" in app.pages["metadata"].origin_label.cget("text")
app.destroy()
print("links OK")

"""Single issue on the shared page shell: two columns, the strip of first and last pages and its browse tile, the footer
that changes with the picks, saving a cover (live file line, conflicts, custom folder), extracting picked pages, the ZIP
shortcut, and one selection shared with the page picker window."""
import io, sys, tempfile, time, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import customtkinter as ctk
from PIL import Image

import page_single as ps
from comic_core import WHERE_BESIDE, WHERE_CUSTOM


def cbz(p, pages=8):
    p.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(p, "w") as z:
        for i in range(pages):
            buf = io.BytesIO(); Image.new("RGB", (40 + i, 60), "red").save(buf, "JPEG")
            z.writestr(f"{i + 1:02d}.jpg", buf.getvalue())
    return p


def settle(win, cond, secs=20):
    t = time.time()
    while not cond() and time.time() - t < secs:
        win.update()
    win.update(); assert cond(), "timed out"


root = ctk.CTk(); root.geometry("1200x780")
pg = ps.SinglePage(root); pg.pack(fill="both", expand=True); root.update()
d = Path(tempfile.mkdtemp())
comic = cbz(d / "Lib" / "Batman 012 (2020).cbz")

def states(): return [c.state for c in pg.segments]
def bar(): return pg.bar_btn.cget("text")
def caps(): return [pg._caps[i].cget("text") for i in sorted(pg._caps)]

# nothing chosen: only the drop box is live, and the footer says why Save cover cannot be pressed
assert [s.title.cget("text") for s in pg.segments] == ["Comic", "Pages", "Save"]
assert states() == ["active", "locked", "locked"] and bar() == "Save cover" and pg.bar_btn.cget("state") == "disabled"
assert "begin" in pg.bar_text.cget("text") and pg.empty.winfo_ismapped() and not pg.strip.winfo_ismapped()
# the comic and the pages are on the left, the save settings on the right, with a divider between
assert pg.drop.winfo_rootx() < pg.splitter.winfo_rootx() < pg.right_wrap.winfo_rootx()
assert set(pg.drop.buttons) == {"folder", "files"} and pg.drop.buttons["files"].winfo_x() < pg.drop.buttons["folder"].winfo_x()
w0 = pg.right_wrap.winfo_width()
pg.splitter._press(type("E", (), {"x_root": 1000})()); pg.splitter._drag(type("E", (), {"x_root": 900})()); pg.splitter._release(None); root.update()
assert pg.right_wrap.winfo_width() > w0 and pg.state()["_split_width"] == int(pg.right_width)

# a comic: the first 3 and the last 2 pages, then the browse tile
pg.load(comic); root.update()
assert states() == ["done", "active", "active"] and not pg.empty.winfo_ismapped() and pg.strip.winfo_ismapped()
assert len(pg._cells) == 6 and caps() == ["Cover", "Page 2", "Page 3", "Page 7", "Page 8"], caps()
tile = pg._cells[-1]
assert "Browse all" in tile.winfo_children()[0].cget("text") and "8 pages" in tile.winfo_children()[0].cget("text")
assert "Batman 012" in pg.s1.summary.cget("text") and "8 pages" in pg.s1.summary.cget("text") and pg.s2.summary.cget("text") == "Cover"
xs = {c.winfo_rootx() for c in pg._cells}
assert len(xs) >= 2 and all(c.winfo_rootx() + c.winfo_width() <= pg.left.winfo_rootx() + pg.left.winfo_width() + 4 for c in pg._cells), "the strip wraps inside its column"
assert bar() == "Save cover" and pg.bar_btn.cget("state") == "normal" and pg._side_labels == ["Save all pages as ZIP"]
assert "Batman 012 (2020) - cover.jpg" in pg.target.cget("text") and pg.target.cget("text").startswith("Will save:")
# a few pages: all of them, no more
few = cbz(d / "Few" / "Short 01.cbz", pages=4); pg.load(few); root.update()
assert caps() == ["Cover", "Page 2", "Page 3", "Page 4"] and len(pg._cells) == 5
five = cbz(d / "Few" / "Five 01.cbz", pages=5); pg.load(five); root.update()
assert len(caps()) == 5 and len(pg._cells) == 6
pg.load(comic); root.update()

# the file that will be written follows the settings
pg.vars["format"].set("PNG"); root.update(); assert pg.target.cget("text").endswith("- cover.png")
pg.vars["name"].set(ps.NAMES[0]); root.update(); assert pg.target.cget("text").endswith("Batman 012 (2020).png")
pg.vars["format"].set("Original"); pg.vars["name"].set(ps.NAMES[1]); root.update()

# save the cover; saving again keeps both, or skips, or replaces
pg.save_cover(); root.update()
cover = d / "Lib" / "Batman 012 (2020) - cover.jpg"
assert cover.exists() and "Saved" in pg.status.cget("text") and "Open folder" in pg._side_labels
assert "it exists, so a number is added" in pg.target.cget("text")
pg.save_cover(); assert (d / "Lib" / "Batman 012 (2020) - cover (1).jpg").exists()
pg.vars["conflict"].set("Skip"); root.update(); pg.save_cover()
assert "Skipped" in pg.status.cget("text") and not (d / "Lib" / "Batman 012 (2020) - cover (2).jpg").exists()
pg.vars["conflict"].set("Keep both")

# a folder of your own: asks for one until it is set
pg.adv.set_open(True); pg.vars["where"].set(WHERE_CUSTOM); root.update()
assert pg.custom_row.winfo_ismapped() and "Choose a folder" in pg.target.cget("text")
pg.save_cover(); assert pg.status.cget("text") == "Choose a folder to save to."
out = d / "Covers"
pg.vars["custom"].set(str(out)); root.update(); pg.save_cover()
assert (out / "Batman 012 (2020) - cover.jpg").exists() and pg.saved_dir == out
pg.vars["where"].set(WHERE_BESIDE); root.update(); assert not pg.custom_row.winfo_ismapped()

# picked pages: the footer turns into Extract, the strip shows ticks, Clear picks goes back
pg.set_picked([2, 0]); root.update()
assert bar() == "Extract 2 pages" and "2 pages picked" in pg.bar_text.cget("text") and pg.s2.summary.cget("text") == "2 pages picked"
assert caps()[0].startswith("✓ Cover") and caps()[0].endswith("#2") and caps()[2].endswith("#1") and caps()[1] == "Page 2"
assert pg._side_labels[:2] == ["Clear picks", "Save all pages as ZIP"] and "JPG files named" in pg.target.cget("text")
pg.set_picked([4]); root.update(); assert bar() == "Extract 1 page"
pg.clear_picks(); root.update(); assert bar() == "Save cover" and caps()[0] == "Cover"

# extracting asks for a folder and writes numbered JPGs
ps.filedialog.askdirectory = lambda **k: str(d / "Pages")
pg.set_picked([5, 1, 3]); pg.extract(); root.update()
got = sorted(p.name for p in (d / "Pages").glob("*.jpg"))
assert got == ["Batman 012 (2020) 1.jpg", "Batman 012 (2020) 2.jpg", "Batman 012 (2020) 3.jpg"], got
assert "Saved 3 JPGs" in pg.status.cget("text") and pg.saved_dir == d / "Pages"
ps.filedialog.askdirectory = lambda **k: ""
pg.extract(); assert "Saved 3 JPGs" in pg.status.cget("text"), "cancelling the folder dialog changes nothing"
pg.clear_picks()

# every page in a ZIP
pg.convert(); root.update()
z = d / "Lib" / "Batman 012 (2020).zip"
assert z.exists() and len(zipfile.ZipFile(z).namelist()) == 8 and pg.saved_dir == d / "Lib"

# one selection shared with the picker window
pg.pick_pages(); root.update(); win = pg._picker
assert win is not None and win.winfo_exists()
pg.pick_pages(); assert pg._picker is win, "a second press brings the same window forward"
win.order = [1, 4]; root.update()
assert pg.picked == [1, 4] and bar() == "Extract 2 pages" and caps()[1].startswith("✓ Page 2"), "picks in the window reach the page"
pg.clear_picks(); root.update(); assert win.order == [] and win.lbl_count.cget("text").startswith("0 of 8")
pg.set_picked([3]); win.set_order([3]); root.update(); assert win.lbl_count.cget("text").startswith("1 of 8")
win.select_all(); root.update(); assert len(pg.picked) == 8
win.clear(); root.update(); assert pg.picked == [] and bar() == "Save cover"
# a page of the strip opens the full-size view, where a click or Space picks it
pg.open_page(2); root.update()
assert win._full is not None and win._full.winfo_exists() and win._fi == 2
win._fpick(); root.update(); assert pg.picked == [2] and caps()[2].startswith("✓ Page 3")
win._fpick(); root.update(); assert pg.picked == []
win._full.destroy()
pg._close_picker(); root.update()
# the picker keeps working on its own, with no page behind it
import picker_window as pw
from comic_core import Comic
c2 = Comic(comic); alone = pw.PickerWindow(root, c2); alone.order = [0]; alone.select_all(); root.update()
assert alone.order == list(range(8)); alone.close(); c2.close()

# loading another comic forgets the picks and the saved folder, and closes the window
pg.set_picked([1]); pg.pick_pages(); root.update(); win = pg._picker
pg.load(few); root.update()
assert pg.picked == [] and pg.saved_dir is None and not win.winfo_exists() and "Open folder" not in pg._side_labels

# a file that cannot be read
bad = d / "Bad.cbz"; bad.write_bytes(b"not a zip")
pg.load(bad); root.update()
assert pg.comic is None and pg.status.cget("text") and states() == ["active", "locked", "locked"] and pg.bar_btn.cget("state") == "disabled"

# settings are kept between sessions
pg.vars["format"].set("WebP"); saved = pg.state()
pg2 = ps.SinglePage(root); pg2.restore(saved); assert pg2.vars["format"].get() == "WebP"
pg2.restore({"format": "TIFF", "where": 5}); assert pg2.vars["format"].get() == "WebP"

print("single page OK")

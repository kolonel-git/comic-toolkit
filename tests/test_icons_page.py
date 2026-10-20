"""Folder icons on the shared page shell: two columns, the table that doubles as the dry run (with a picture of the icon each
folder would get), the three style cards with pictures, the example folder, a picture of your own, the run itself (real
icons in a temporary library), removing icons, and the footer. Windows only, like the tool."""
import io, shutil, sys, tempfile, time, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import customtkinter as ctk
from PIL import Image
from tkinter import filedialog

import folder_icons as fi
import page_icons as pi

if not fi.supported():
    print("ICONS PAGE skipped (not Windows)")
    sys.exit(0)


def cover(c=(200, 40, 40)):
    b = io.BytesIO(); im = Image.new("RGB", (300, 450), c); im.paste(Image.new("RGB", (300, 150), (40, 40, 200)), (0, 0)); im.save(b, "JPEG")
    return b.getvalue()


def cbz(p):
    p.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(p, "w") as z: z.writestr("0.jpg", cover())
    return p


filedialog.askdirectory = lambda **k: ""      # (a real dialog would wait for a click)
filedialog.askopenfilename = lambda **k: ""
root = ctk.CTk(); root.geometry("1500x900")
pg = pi.IconsPage(root); pg.pack(fill="both", expand=True); root.update()


def settle(cond, secs=20):
    t = time.time()
    while not cond() and time.time() - t < secs: root.update(); time.sleep(0.02)
    root.update(); assert cond(), "timed out"


def rows(t=None): t = t or pg.table.tree; return [t.item(i)["values"] for i in t.get_children()]
bar = lambda: pg.bar_btn.cget("text")


# nothing chosen yet
assert [s.title.cget("text") for s in pg.segments] == ["Folders", "Icon style", "Review"]
assert bar() == "Make icons" and pg.bar_btn.cget("state") == "disabled" and pg.headline.cget("text") == "Choose some folders first."
assert pg._side_labels == ["Remove icons", "Refresh Explorer"]
assert pg.drop.winfo_rootx() < pg.splitter.winfo_rootx() < pg.right_wrap.winfo_rootx() and pg.drop.compact
w0 = pg.right_wrap.winfo_width()
pg.splitter._press(type("E", (), {"x_root": 1000})()); pg.splitter._drag(type("E", (), {"x_root": 900})()); pg.splitter._release(None); root.update()
assert pg.right_wrap.winfo_width() > w0 and pg.state()["_split_width"] == int(pg.right_width)
# the style cards carry pictures even with no folder (a made-up cover), and the example says so
settle(lambda: set(pg.style_cards._images) == set(fi.STYLES))
assert "made-up" in pg.example_name.cget("text") and pg._photo is not None

lib = Path(tempfile.mkdtemp())
for name in ("Batman", "Saga", "Robin"):
    for n in (1, 2): cbz(lib / "DC" / name / f"{name} {n:02d}.cbz")
cbz(lib / "DC" / "Archive" / "Old 01.cbz")
(lib / "DC" / "Empty").mkdir()
fi.write_icon(lib / "DC" / "Robin", cover())          # Robin has an icon already
pg.set_folder(lib / "DC")
settle(lambda: len(pg.plan) == 3)
v = rows(); print(v)
assert [r[0] for r in v] == ["Batman", "Robin", "Saga"] and [r[1] for r in v] == ["Batman 01.cbz", "Robin 01.cbz", "Saga 01.cbz"]
assert [r[2] for r in v] == ["New", "Has one: replaced", "New"]
assert pg.s1.summary.cget("text") == "3 series folders · 1 already have icons" and bar() == "Make 3 icons" and pg.bar_btn.cget("state") == "normal"
assert pg.headline.cget("text") == "Will make 3 icons  ·  1 replace an icon" and "folder.ico and desktop.ini, folder.jpg" in pg.subline.cget("text")
assert "Archive" not in str(pg.plan) and "Empty" not in str(pg.plan)
# the picture on each row is the icon it would get
settle(lambda: len(pg.table._photos) >= 3)
assert pg.table.keys[0][3] == (fi.STYLES[0], "Manila", "Medium", False)
# example folder: which cover the big picture is drawn from
assert pg.example_name.cget("text") == "Batman" and pg.example_note.cget("text") == "Example 1 of 3"
pg.next_example(); settle(lambda: pg.example_name.cget("text") == "Robin" and pg.example_note.cget("text") == "Example 2 of 3")
pg.next_example(); pg.next_example(); settle(lambda: pg.example_name.cget("text") == "Batman"), "it wraps round"
# options: style, colour, badge reach the table's pictures and the preview
before = pg._photo
pg.vars["style"].set(fi.STYLE_TAB); pg.vars["color"].set("Blue"); pg.vars["badge"].set(True); root.update()
assert pg.table.keys[0][3] == (fi.STYLE_TAB, "Blue", "Medium", True) and "Folder tab" in pg.s2.summary.cget("text")
settle(lambda: pg._photo is not before)
assert "3 changed" in pg.adv.head.cget("text") or "2 changed" in pg.adv.head.cget("text")
pg.vars["style"].set(fi.STYLES[0]); pg.vars["color"].set("Manila"); pg.vars["badge"].set(False)
# skip folders that already have one
pg.vars["existing"].set("Skip"); root.update()
assert [r[2] for r in rows()] == ["New", "Has one: kept", "New"] and bar() == "Make 2 icons" and "1 kept" in pg.headline.cget("text")
pg.vars["existing"].set("Replace")
# last issue
pg.vars["which"].set("Last issue"); root.update()
assert [r[1] for r in rows()] == ["Batman 02.cbz", "Robin 02.cbz", "Saga 02.cbz"]
pg.vars["which"].set("First issue")
# subfolders off: only the folder itself counts, and DC holds no comics
pg.vars["recursive"].set(False); root.update()
assert pg.plan == [] and bar() == "Make icons" and pg.bar_btn.cget("state") == "disabled"
pg.vars["recursive"].set(True); root.update(); assert len(pg.plan) == 3
# nothing to write
pg.vars["ico"].set(False); pg.vars["jpg"].set(False); root.update()
assert "Turn on a folder icon" in pg.headline.cget("text") and pg.bar_btn.cget("state") == "disabled"
pg.vars["ico"].set(True); pg.vars["jpg"].set(True)

# a picture of your own: for the selected rows, or for any folder with no comics
png = lib / "mine.png"; Image.new("RGB", (200, 300), (30, 160, 60)).save(png)
filedialog.askopenfilename = lambda **k: str(png)
pg.table.select([0]); root.update(); pg.custom_image(); root.update()
assert rows()[0][1] == "Your image" and rows()[0][2] == "Custom image" and pg.btn_again.cget("state") == "normal"
assert "1 folder will use mine.png" in pg.status.cget("text")
(lib / "bad.png").write_bytes(b"not an image"); filedialog.askopenfilename = lambda **k: str(lib / "bad.png")
pg.custom_image(); assert "Couldn't use that image" in pg.status.cget("text") and len(pg.images) == 1
filedialog.askopenfilename = lambda **k: str(png)
pg.table.tree.selection_set(()); filedialog.askdirectory = lambda **k: str(lib / "DC" / "Empty")
pg.custom_image(); root.update()
assert len(rows()) == 4 and rows()[-1][0] == "Empty" and rows()[-1][2] == "Custom image" and bar() == "Make 4 icons"
pg.use_cover_again(); root.update(); assert pg.images == {} and len(rows()) == 3
pg.table.select([0]); pg.custom_image(); assert len(pg.images) == 1

# the run: real icons, in the style chosen
pg.vars["style"].set(fi.STYLE_POCKET)
pg.start(); root.update()
settle(lambda: pg.result is not None)
assert pg.result == {"ok": 3, "skipped": 0, "failed": 0, "stopped": False}, pg.result
for n in ("Batman", "Saga", "Robin"):
    f = lib / "DC" / n
    assert fi.has_icon(f) and (f / "folder.jpg").exists()
with Image.open(lib / "DC" / "Batman" / "folder.ico") as im:
    assert im.size == (256, 256)
assert [r[2] for r in rows()] == ["Made"] * 3 and pg.result_text() == "3 icons made"
assert bar() == "Refresh Explorer" and "Done" in pg.bar_text.cget("text") and "Batman" in pg.log.get("1.0", "end") and pg.result_box.winfo_ismapped()
assert pg._side_labels[:3] == ["Make them again", "Do another folder", "Remove icons"]
# making them again with Skip keeps what is there
pg.again(); pg.vars["existing"].set("Skip"); root.update()
assert [r[2] for r in rows()] == ["Has one: kept"] * 3 and pg.bar_btn.cget("state") == "disabled" and bar() == "Make 0 icons"
pg.start(); assert "Nothing to make" in pg.status.cget("text")
pg.vars["existing"].set("Replace"); root.update()
# a folder whose comic has gone fails, and only it is retried
(lib / "DC" / "Saga" / "Saga 01.cbz").unlink()
pg.start(); settle(lambda: pg.result is not None)
assert pg.result["failed"] == 1 and pg.result["ok"] == 2 and "Retry 1 failed" in pg._side_labels and "Saga" in pg.result_sub.cget("text")
cbz(lib / "DC" / "Saga" / "Saga 01.cbz")
pg.retry(); settle(lambda: pg.result is not None); assert pg.result["ok"] == 1 and pg.result["failed"] == 0
# stop
pg.again(); pg.start(); pg.stop_action(); settle(lambda: pg.result is not None)
assert pg.result["stopped"] in (True, False) and pg.result["ok"] + pg.result["skipped"] + pg.result["failed"] <= 3

# remove icons: asks, names how many, keeps folder.jpg
asked = []
import tkinter.messagebox as mb
mb.askyesno = lambda *a, **k: asked.append(a[1]) or False
pi.messagebox.askyesno = mb.askyesno
pg.again(); pg.remove_icons(); assert "3 folders" in asked[0] and fi.has_icon(lib / "DC" / "Batman"), "declined"
pi.messagebox.askyesno = lambda *a, **k: True
pg.remove_icons(); root.update()
assert not any(fi.has_icon(lib / "DC" / n) for n in ("Batman", "Saga", "Robin")) and (lib / "DC" / "Batman" / "folder.jpg").exists()
assert "Removed 3 icons" in pg.status.cget("text")
pg.remove_icons(); assert "None of these folders" in pg.status.cget("text")
# refresh explorer
fi.refresh_explorer = lambda: True
pg.refresh_explorer(); assert "redraw" in pg.status.cget("text")
fi.refresh_explorer = lambda: False
pg.refresh_explorer(); assert "Couldn't" in pg.status.cget("text")

# comics picked one by one: one icon per folder, from the first or last of the picked comics
pg.reset(); root.update()
assert pg.plan == [] and bar() == "Make icons" and pg.bar_btn.cget("state") == "disabled"
a1, a2, s1 = lib / "DC" / "Batman" / "Batman 01.cbz", lib / "DC" / "Batman" / "Batman 02.cbz", lib / "DC" / "Saga" / "Saga 02.cbz"
pg.set_files([a2, a1, s1, lib / "mine.png"]); root.update()
assert [(f.name, c.name) for f, c in pg.plan] == [("Batman", "Batman 01.cbz"), ("Saga", "Saga 02.cbz")] and "3 comics chosen" in pg.drop.label.cget("text")
pg.vars["which"].set("Last issue"); root.update(); assert pg.plan[0][1].name == "Batman 02.cbz"
pg.set_files([png]); assert "None of those" in pg.status.cget("text")
pg.add_paths([lib / "DC"]); root.update(); assert pg.picked is None and len(pg.plan) == 3
# not on Windows: said plainly
real = fi.supported
fi.supported = lambda: False
pg.refresh(); assert pg.headline.cget("text") == "Folder icons only work on Windows." and pg.bar_btn.cget("state") == "disabled"
pg.start(); assert "only work on Windows" in pg.status.cget("text")
fi.supported = real; pg.refresh()
# settings and the whole app
st = pg.state(); pg.restore(st); assert st["style"] == fi.STYLES[0] and "images" not in st
pg.restore({"style": "Nonsense", "color": "Mauve"}); assert pg.vars["style"].get() == fi.STYLES[0]
ctk.set_appearance_mode("dark"); pg.apply_theme(); root.update()
for f in (lib / "DC").iterdir():
    if f.is_dir():
        for n in ("desktop.ini", "folder.ico"):
            if (f / n).exists(): fi._set_attrs(f / n, 0x80)
        fi._set_attrs(f, 0x10)
root.destroy()
shutil.rmtree(lib, ignore_errors=True)

import comic_tool
app = comic_tool.App(); assert "icons" in app.pages
app.show("icons"); app.update()
assert {"library", "recent"} <= set(app.pages["icons"].drop.buttons)
class Ev: pass
e = Ev(); e.data = "{C:/does/not/exist}"; app.on_drop(e)
app.destroy()
print("ICONS PAGE OK")

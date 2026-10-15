"""CBR to CBZ on the shared page shell: two columns, the .cbr list and its background check, the review (counts,
statuses, dry run), the three things that can happen to the original, an existing .cbz, the tidy-up options, a failing
file, the Delete confirmation, the link from the Library audit, and the footer."""
import io, sys, tempfile, time, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import customtkinter as ctk
from PIL import Image

import archive_tools as at
import page_convert as pc
from comic_core import find_extractor


def cbr(p, pages=3, extra=()):
    """A .cbr that is really a zip (the converter treats it like any other archive)."""
    p.parent.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO(); Image.new("RGB", (40, 60), "red").save(buf, "JPEG")
    with zipfile.ZipFile(p, "w") as z:
        for i in range(pages): z.writestr(f"p{i + 1}.jpg", buf.getvalue())
        for n in extra: z.writestr(n, b"x")
    return p


def settle(win, cond, secs=20):
    t = time.time()
    while not cond() and time.time() - t < secs:
        win.update()
    win.update(); assert cond(), "timed out"


def names(p):
    with zipfile.ZipFile(p) as z: return sorted(z.namelist())


root = ctk.CTk(); root.geometry("1200x780")
pg = pc.ConvertPage(root); pg.pack(fill="both", expand=True); root.update()
d = Path(tempfile.mkdtemp())
for n in (1, 2, 3):
    cbr(d / "Lib" / f"Saga {n:02d}.cbr")
cbr(d / "Lib" / "Archive" / "Old.cbr")                       # inside an Archive folder: ignored
cbr(d / "Lib" / "Deep" / "Batman 01.cbr", extra=("Thumbs.db",))
(d / "Lib" / "Saga 02.cbz").write_bytes(b"already here")     # an existing .cbz for one of them

def states(): return [c.state for c in pg.segments]
def bar(): return pg.bar_btn.cget("text")
def rows(t=None): t = t or pg.review.tree; return [t.item(i)["values"] for i in t.get_children()]

# nothing chosen: the footer says why it cannot be pressed
assert states() == ["active", "locked", "locked"] and pg.bar_btn.cget("state") == "disabled"
assert bar() == "Choose files first" and "begin" in pg.bar_text.cget("text")
assert [s.title.cget("text") for s in pg.segments] == ["Comics", "Convert", "Review"]
# two columns with a divider that can be dragged
assert pg.comics.winfo_rootx() < pg.splitter.winfo_rootx() < pg.right_wrap.winfo_rootx()
w0 = pg.right_wrap.winfo_width()
pg.splitter._press(type("E", (), {"x_root": 1000})()); pg.splitter._drag(type("E", (), {"x_root": 900})()); pg.splitter._release(None); root.update()
assert pg.right_wrap.winfo_width() > w0 and pg.state()["_split_width"] == int(pg.right_width)

# a folder: only .cbr files outside Archive, and the page checks them in the background
pg.set_folder(d / "Lib"); root.update()
assert sorted(p.name for p in pg.files) == ["Batman 01.cbr", "Saga 01.cbr", "Saga 02.cbr", "Saga 03.cbr"], pg.files
assert states() == ["done", "active", "idle"]
settle(pg, lambda: pg.checking is None)
assert all(pg.kind[p] == "ZIP" for p in pg.files), "zip-backed .cbr files are spotted"
assert {r[2] for r in rows(pg.comics.tree)} == {"ZIP inside"} and "4 .cbr files" in pg.s1.summary.cget("text")
assert bar() == "Convert 4 files" and pg.bar_btn.cget("state") == "normal"

# review, Skip: Saga 02 already has a .cbz
st = dict((r[0], r[2]) for r in rows())
assert st["Saga 02"] == "Skipped" and st["Saga 01"] == "New" and "Will convert 3 files" in pg.headline.cget("text")
assert "1 already have a .cbz" in pg.headline.cget("text") and "verified" in pg.verified.cget("text")
pg.vars["exists"].set(pc.BOTH); root.update()
st = dict((r[0], (r[1], r[2])) for r in rows())
assert st["Saga 02"] == ("Saga 02 (1).cbz", "Gets a number") and "Will convert 4 files" in pg.headline.cget("text")
pg.vars["exists"].set(pc.OVER); root.update()
assert dict((r[0], r[2]) for r in rows())["Saga 02"] == "Replaces it" and "1 replace a .cbz" in pg.headline.cget("text")
pg.vars["exists"].set(pc.SKIP); root.update()

# dry run writes nothing
pg.dry_run(); root.update()
assert dict((r[0], r[2]) for r in rows())["Saga 02"] == "Would skip" and "Dry run" in pg.headline.cget("text")
assert not (d / "Lib" / "Saga 01.cbz").exists() and bar() == "Convert 4 files"
pg.leave_dry(); root.update()

# run: originals moved to Archive, the verified .cbz take their place, the existing one is left alone
pg.start(); root.update()
settle(pg, lambda: pg.result is not None)
assert pg.result == {"ok": 3, "skipped": 1, "failed": 0, "stopped": False}, pg.result
assert pg.result_text() == "3 converted, 1 skipped"
for n in ("Saga 01", "Saga 03"):
    assert (d / "Lib" / f"{n}.cbz").exists() and not (d / "Lib" / f"{n}.cbr").exists()
    assert (d / "Lib" / "Archive" / f"{n}.cbr.bak").exists()
assert (d / "Lib" / "Saga 02.cbz").read_bytes() == b"already here" and (d / "Lib" / "Saga 02.cbr").exists()
assert states() == ["done", "done", "done"] and bar() == "Open the folder" and "Done" in pg.bar_text.cget("text")
assert "Saga 01.cbr" in pg.log.get("1.0", "end") and pg.result_box.winfo_ismapped()
# the tidy-up options are off by default: the junk file stays inside the converted Batman comic
assert "Thumbs.db" in names(d / "Lib" / "Deep" / "Batman 01.cbz")

# Keep it with Replace: the original stays and the old .cbz is overwritten
pg.again(); root.update()
assert [p.name for p in pg.files] == ["Saga 02.cbr"], "converted comics are gone from the list; only Saga 02 is left"
pg.vars["original"].set(pc.KEEP); pg.vars["exists"].set(pc.OVER); root.update()
pg.start(); settle(pg, lambda: pg.result is not None)
assert pg.result["ok"] == 1 and (d / "Lib" / "Saga 02.cbr").exists() and zipfile.is_zipfile(d / "Lib" / "Saga 02.cbz")

# junk and page names are tidied when asked
cbr(d / "Lib2" / "Tidy 01.cbr", pages=12, extra=("Thumbs.db", "readme.txt"))
pg.set_folder(d / "Lib2"); settle(pg, lambda: pg.checking is None)
pg.vars["original"].set(pc.KEEP); pg.vars["junk"].set(True); pg.vars["rename"].set(True); root.update()
assert "2 changed" in pg.adv.head.cget("text")
pg.start(); settle(pg, lambda: pg.result is not None)
got = names(d / "Lib2" / "Tidy 01.cbz")
assert got == [f"{i:03d}.jpg" for i in range(1, 13)], got

# a file that cannot be converted: reported, nothing created, the original untouched
bad = d / "Lib3" / "Broken 01.cbr"; bad.parent.mkdir(); bad.write_bytes(b"this is not a rar")
cbr(d / "Lib3" / "Fine 01.cbr")
pg.vars["original"].set(pc.MOVE); pg.vars["junk"].set(False); pg.vars["rename"].set(False)
pg.set_folder(d / "Lib3"); settle(pg, lambda: pg.checking is None)
if find_extractor() is None:
    assert bad in pg.bad and "extractor" in pg.bad[bad]
    assert dict((r[0], r[2]) for r in rows())["Broken 01"] == "Unreadable" and "1 unreadable" in pg.headline.cget("text")
    pg.start(); settle(pg, lambda: pg.result is not None)
    assert pg.result["ok"] == 1 and pg.result["failed"] == 0, "unreadable files are left out of the run"
else:
    pg.start(); settle(pg, lambda: pg.result is not None)
    assert pg.result["ok"] == 1 and pg.result["failed"] == 1 and pg.failed[0][0] == bad, pg.result
    assert "Retry 1 failed" in pg._side_labels
assert bad.exists() and not (d / "Lib3" / "Broken 01.cbz").exists() and not list((d / "Lib3").glob("*.part"))

# Delete it: asks first, and a "no" leaves everything alone
cbr(d / "Lib4" / "Gone 01.cbr")
pg.set_folder(d / "Lib4"); settle(pg, lambda: pg.checking is None)
pg.vars["original"].set(pc.DELETE); root.update()
assert "deleted for good" in " ".join(w.cget("text") for w in pg.problems.winfo_children())
asked = []
pc.messagebox.askyesno = lambda *a, **k: asked.append(a) or False
pg.start(); root.update()
assert asked and pg.q is None and pg.result is None and (d / "Lib4" / "Gone 01.cbr").exists()
pc.messagebox.askyesno = lambda *a, **k: True
pg.start(); settle(pg, lambda: pg.result is not None)
assert pg.result["ok"] == 1 and not (d / "Lib4" / "Gone 01.cbr").exists() and (d / "Lib4" / "Gone 01.cbz").exists()
assert not (d / "Lib4" / "Archive").exists(), "nothing is kept when the original is deleted"

# the Library audit opens this page on its folder with a chip and a Back button
backs = []
cbr(d / "Lib5" / "A 01.cbr")
pg.open_with(d / "Lib5", origin="Library audit", back=lambda: backs.append(1)); root.update()
assert pg.origin.winfo_ismapped() and "From Library audit" in pg.origin_label.cget("text") and "1 .cbr file" in pg.origin_label.cget("text")
assert pg.origin_back.cget("text") == "Back to Library audit"
pg.origin_back.invoke(); assert backs == [1]
pg.set_folder(d / "Lib5"); root.update(); assert not pg.origin.winfo_ismapped(), "choosing a folder yourself clears the chip"

# comics picked one by one: only .cbr files count; dropping a folder or files works
a = cbr(d / "Pick" / "X 01.cbr"); b = cbr(d / "Pick" / "X 02.cbr"); z = d / "Pick" / "X 03.cbz"; z.write_bytes(b"z")
pg.set_files([b, a, z, a]); root.update()
assert pg.files == [a, b] and pg.folder == a.parent and "2 .cbr files chosen" in pg.drop.label.cget("text")
pg.set_files([z]); assert "None of those" in pg.status.cget("text") and pg.files == [a, b]
pg.add_paths([d / "Pick"]); root.update(); assert pg.picked is None and len(pg.files) == 2
pg.add_paths([a]); root.update(); assert pg.picked == [a]

# do another folder, and the settings are kept between sessions
pg.reset(); root.update()
assert pg.files == [] and states() == ["active", "locked", "locked"] and bar() == "Choose files first"
pg.vars["original"].set(pc.KEEP); saved = pg.state()
pg2 = pc.ConvertPage(root); pg2.restore(saved); assert pg2.vars["original"].get() == pc.KEEP
pg2.restore({"original": "junk", "exists": 5}); assert pg2.vars["original"].get() == pc.KEEP

# the core call, on its own: an existing .cbz survives a failed tidy-up
tmp = Path(tempfile.mkdtemp()); src = cbr(tmp / "Only.cbr", extra=("Thumbs.db",)); dest = tmp / "Only.cbz"
dest.write_bytes(b"keep me")
real = at.plan_cleanup
at.plan_cleanup = lambda *a, **k: (_ for _ in ()).throw(ValueError("boom"))
try:
    at.convert_one(src, dest, remove_junk=True)
    raise SystemExit("convert_one should have failed")
except ValueError:
    pass
finally:
    at.plan_cleanup = real
assert dest.read_bytes() == b"keep me" and not list(tmp.glob("*.part")) and src.exists()

print("convert page OK")

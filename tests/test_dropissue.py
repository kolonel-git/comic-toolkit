import sys, tempfile, time, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import archive_tools as at
import reading_order as ro
from rename_core import read_comicinfo
from tkinter import messagebox


def cbz(p):
    p.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(p, "w") as z: z.writestr("0.jpg", b"x")
    return p


# ---- core: None removes the tag, others kept, missing tag is a no-op, valid XML stays valid
raw = b'<?xml version="1.0"?><ComicInfo><Series>Saga</Series><Number>5</Number><Number>6</Number><Genre>x</Genre></ComicInfo>'
out = at.merge_comicinfo(raw, {"issue": None, "year": "2012"}).decode()
print(out)
assert "<Number" not in out and "<Series>Saga</Series>" in out and "<Genre>x</Genre>" in out and "<Year>2012</Year>" in out
assert "<Number" not in at.merge_comicinfo(None, {"issue": None}).decode()
assert at.merge_comicinfo(b"<ComicInfo/>", {"issue": None, "count": None}).decode().count("<") >= 1

with tempfile.TemporaryDirectory() as d:
    d = Path(d)
    a = cbz(d / "A" / "Saga 05 (2012).cbz")
    at.apply_metadata(a, {"series": "Saga", "issue": "5", "year": "2012"}, False)
    assert read_comicinfo(a)["issue"] == "5"
    at.apply_metadata(a, {"issue": None}, True)
    ci = read_comicinfo(a); assert ci["issue"] is None and ci["series"] == "Saga" and ci["year"] == "2012"
    assert (d / "A" / "Archive" / "Saga 05 (2012).cbz.bak").exists()
    # a file with no ComicInfo at all: removal creates nothing harmful
    b = cbz(d / "A" / "Plain 01.cbz"); at.apply_metadata(b, {"issue": None}, False); assert read_comicinfo(b).get("issue") is None

    # ---- reading order plan
    c = cbz(d / "B" / "Robin 02.cbz"); at.apply_metadata(c, {"series": "Robin", "issue": "2"}, False)
    o = {"name": "Run", "store": ro.STORY, "numbering": ro.NUM_PLAIN, "group": "", "prefix": ro.PREFIX_DASH, "drop_issue": True}
    p = ro.plan_item(c, read_comicinfo(c), 1, 3, o)
    assert p["writes"]["issue"] is None and p["writes"]["story_arc"] == "Run", p
    assert "Number: 2  ->  (removed)" in "\n".join(ro.describe_item(c, read_comicinfo(c), p, ro.STORY))
    p2 = ro.plan_item(a, read_comicinfo(a), 2, 3, o); assert "issue" not in p2["writes"]          # nothing to remove
    off = dict(o, drop_issue=False); assert "issue" not in ro.plan_item(c, read_comicinfo(c), 1, 3, off)["writes"]
    new = ro.apply_item(c, p["writes"], p["new_name"], False)
    ci = read_comicinfo(new); assert new.name == "01 - Robin 02.cbz" and ci["issue"] is None and ci["story_arc_number"] == "1" and ci["series"] == "Robin"
    p3 = ro.plan_item(new, ci, 1, 3, o); assert p3["status"] == "No change", p3                    # idempotent

    # ---- windows
    import customtkinter as ctk
    import page_metadata as pm
    import page_order as po
    root = ctk.CTk(); root.geometry("1200x780")
    def wait(pg):
        t = time.time()
        while getattr(pg, "busy", None) and time.time() - t < 15: root.update(); time.sleep(0.01)
        root.update()
    mp = pm.MetadataPage(root); mp.pack(fill="both", expand=True); root.update()
    lib = d / "M"
    for n in (1, 2, 3):
        x = cbz(lib / f"Saga {n:02d} (2012).cbz"); at.apply_metadata(x, {"series": "Saga", "issue": str(n)}, False)
    cbz(lib / "Noinfo 04.cbz")
    mp.set_folder(lib); wait(mp)
    rows = {r.path.name: r for r in mp.rows}
    assert mp.bar_btn.cget("state") == "disabled", "nothing to save yet"
    # nothing selected: removing an issue number touches nothing
    mp.remove_issue(True); assert not mp.pending_rows()
    # select the three Saga comics and remove their issue numbers; the comic with no stored number is left alone
    mp.comics.tree.selection_set([str(i) for i in range(4)]); root.update()
    mp.remove_issue(True); print(mp.status.cget("text"))
    saga = [r for r in mp.rows if r.path.name.startswith("Saga")]
    assert len(saga) == 3 and all(r.pending == {"issue": None} and r.value("issue") == "" for r in saga)
    nf = rows["Noinfo 04.cbz"]; assert nf.pending == {}, "it had no number stored, so there is nothing to remove"
    assert "Issue number will be removed from 3 of 4 comics" in mp.status.cget("text")
    mp.mode.set("One at a time"); mp.go_review(); root.update()
    assert "3 values will be deleted" in mp.save_note.cget("text"), mp.save_note.cget("text")
    mp.apply(); wait(mp)
    for n in (1, 2, 3): assert read_comicinfo(lib / f"Saga {n:02d} (2012).cbz")["issue"] is None
    assert read_comicinfo(lib / "Saga 01 (2012).cbz")["series"] == "Saga"
    assert read_comicinfo(lib / "Noinfo 04.cbz").get("issue") is None
    # after the save the list is re-read: nothing pending, and taking the removal back finds nothing to undo
    assert not mp.pending_rows() and all(not r.value("issue") for r in mp.rows)
    mp.comics.tree.selection_set(["0"]); root.update()
    mp.remove_issue(False); assert not mp.pending_rows()
    mp.destroy()

    op = po.OrderPage(root); op.pack(fill="both", expand=True); root.update()
    ol = d / "O"; fs = []
    for n in (1, 2, 3):
        x = cbz(ol / f"Saga {n:02d}.cbz"); at.apply_metadata(x, {"series": "Saga", "issue": str(n)}, False); fs.append(x)
    op.add_paths(fs); wait(op); op.arc.set("Run"); op.vars["prefix"].set(ro.PREFIX_DASH); root.update()
    txt = op.preview_text(); assert "removed" not in txt
    op.vars["drop_issue"].set(True); root.update()
    txt = op.preview_text(); print(txt)
    assert "Issue numbers would be removed" in txt and "Number: 1  ->  (removed)" in txt and "no filename prefix" not in txt
    op.vars["prefix"].set(ro.PREFIX_OFF); root.update(); assert "no filename prefix is on" in op.preview_text()
    op.vars["prefix"].set(ro.PREFIX_DASH); root.update()
    messagebox.askyesno = lambda *a, **k: True
    op.apply(); wait(op)
    names = sorted(p.name for p in ol.glob("*.cbz")); print(names)
    assert names == ["01 - Saga 01.cbz", "02 - Saga 02.cbz", "03 - Saga 03.cbz"]
    assert all(read_comicinfo(p)["issue"] is None and read_comicinfo(p)["story_arc"] == "Run" for p in ol.glob("*.cbz"))
    assert op.state()["drop_issue"] is True
    op.destroy(); root.destroy()
print("DROP ISSUE OK")

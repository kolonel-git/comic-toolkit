import io, sys, tempfile, time, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import customtkinter as ctk
from PIL import Image
from tkinter import messagebox, simpledialog
import intake_core as ic
import page_intake as pi
from archive_tools import read_comicinfo_raw


def jpg():
    b = io.BytesIO(); Image.new("RGB", (60, 90), (9, 9, 9)).save(b, "JPEG"); return b.getvalue()


def cbz(p, junk=False):
    p.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(p, "w") as z:
        for i in range(3): z.writestr(f"{i + 1:03d}.jpg", jpg())
        if junk: z.writestr("Thumbs.db", b"x")


root = ctk.CTk(); root.geometry("1300x800")
errors = []; root.report_callback_exception = lambda *a: errors.append(a)
page = pi.IntakePage(root); page.pack(fill="both", expand=True); root.update()
by_name = lambda: {it.src.name: it for it in page.items}
order = lambda: [page.by_iid[i].src.name for i in page.cards.order]
footer = lambda: (str(page.bar_btn.cget("text")), str(page.bar_btn.cget("state")), str(page.bar_text.cget("text")))


def wait():
    t = time.time()
    while page.busy and time.time() - t < 60: root.update(); time.sleep(0.01)
    root.update(); assert not page.busy


assert footer()[1] == "disabled" and "begin" in footer()[2]
with tempfile.TemporaryDirectory() as d:
    d = Path(d); inbox, ready = d / "in", d / "ready"
    cbz(inbox / "batman 12 (2016).cbz", junk=True); cbz(inbox / "Saga" / "saga 003.cbz"); cbz(inbox / "012.cbz")
    cbz(ready / "Batman" / "Batman 013 (2016).cbz")
    page.vars["inbox"].set(str(inbox))
    page.scan_inbox(); wait()
    assert len(page.items) == 3 and "3 comics" in page.meta.cget("text")
    assert all(it.status == "" for it in page.items)                      # no Ready folder yet: nothing planned
    assert "Ready folder" in footer()[2] and footer()[1] == "disabled"
    page.vars["ready"].set(str(ready)); page.recompute(); root.update()
    b = by_name()
    assert b["batman 12 (2016).cbz"].dest.name == "batman 012 (2016).cbz" and b["batman 12 (2016).cbz"].status == ic.READY
    assert b["batman 12 (2016).cbz"].checked and "clean" in b["batman 12 (2016).cbz"].steps
    assert b["012.cbz"].status == ic.NO_SERIES and not b["012.cbz"].checked
    assert order()[0] == "012.cbz"                                        # the one that needs a look comes first
    assert "2 to add" in page.meta.cget("text") and "need a look" in page.meta.cget("text")
    assert footer()[0] == "Add 2 comics" and footer()[1] == "normal"
    r = page._render(b["012.cbz"].iid)
    assert r["tone"] == "bad" and [x[0] for x in r["buttons"]] == ["series"] and r["checked"] is False
    assert page.add_paths([inbox]) == 0                                    # nothing new the second time
    # tick and untick by the card's box
    page._tick(b["saga 003.cbz"].iid); assert not b["saga 003.cbz"].checked and footer()[0] == "Add 1 comic"
    page._tick(b["saga 003.cbz"].iid); assert b["saga 003.cbz"].checked
    # Set series… names the no-series comic (and it is then ready)
    simpledialog.askstring = lambda *a, **k: "Hellboy"
    page._fix(b["012.cbz"].iid, "series")
    assert b["012.cbz"].status == ic.READY and b["012.cbz"].dest.parent.name == "Hellboy" and b["012.cbz"].checked
    # a copy already in the library: Add anyway ticks it, Skip unticks it
    cbz(inbox / "Batman 013 (2016).cbz")
    page.scan_inbox(); wait()
    dup = by_name()["Batman 013 (2016).cbz"]
    assert dup.status == ic.EXISTS and not dup.checked and order()[0] == dup.src.name
    assert [x[0] for x in page._render(dup.iid)["buttons"]] == ["anyway"]
    page._fix(dup.iid, "anyway"); assert dup.checked and [x[0] for x in page._render(dup.iid)["buttons"]] == ["skip"]
    page._fix(dup.iid, "skip"); assert not dup.checked
    # run, declining first
    messagebox.askyesno = lambda *a, **k: False
    page.apply(); assert not page.busy and (inbox / "batman 12 (2016).cbz").exists()
    messagebox.askyesno = lambda *a, **k: True
    page.select_all(False)
    for n in ("batman 12 (2016).cbz", "saga 003.cbz", "012.cbz"): page._tick(by_name()[n].iid)
    assert footer()[0] == "Add 3 comics"
    page.apply(); assert footer()[0] == "Stop"; wait(); root.update()
    assert (ready / "batman" / "batman 012 (2016).cbz").exists() and (ready / "Saga" / "saga 003.cbz").exists()
    assert (ready / "Hellboy" / "012.cbz").exists() or list((ready / "Hellboy").glob("*.cbz"))
    name, raw = read_comicinfo_raw(next((ready / "Hellboy").glob("*.cbz")))
    assert raw and b"<Series>Hellboy</Series>" in raw                      # the series typed by hand is in ComicInfo.xml too
    assert not (inbox / "batman 12 (2016).cbz").exists() and not (inbox / "Saga").exists()
    assert "Added 3 comics" in page.status.cget("text") and [it.src.name for it in page.items] == ["Batman 013 (2016).cbz"]
    # a broken file reports its error, can be retried from the footer, and stays in the inbox
    (inbox / "Broken 001.cbz").write_bytes(b"nope")
    page.scan_inbox(); wait()
    br = by_name()["Broken 001.cbz"]; assert br.checked
    page._tick(by_name()["Batman 013 (2016).cbz"].iid)
    page.apply(); wait(); root.update()
    br = by_name()["Broken 001.cbz"]
    assert br.status == ic.FAILED and br.note and "1 failed" in page.status.cget("text") and (inbox / "Broken 001.cbz").exists()
    assert page._render(br.iid)["tone"] == "bad" and "Retry 1 failed" in page._side_labels
    # Stop: the run ends after the comic in hand
    page.clear(); assert page.items == []
    for i in range(3): cbz(inbox / f"Spawn {i + 1:03d}.cbz")
    page.vars["rename"].set(True); page.scan_inbox(); wait()
    n0 = len(page.items); assert n0 == 4 or n0 == 3
    page.apply(); page.stop(); wait(); root.update()
    assert "Stopped" in page.status.cget("text") or "Added" in page.status.cget("text")
    # Keep the originals: the watch must not list them again
    page.clear(); page.vars["original"].set("Keep it")
    # watching the inbox lists a settled file once, and never adds anything by itself
    for f in inbox.glob("*.cbz"): f.unlink()
    pi.WATCH_MS = 40
    page.vars["watch"].set(True); root.update()
    assert page._watch_id is not None and "Watching" in page.lbl_watch.cget("text")
    cbz(inbox / "Watched 001.cbz")
    t = time.time()
    while not page.items and time.time() - t < 5: root.update(); time.sleep(0.02)
    wait()
    assert [it.src.name for it in page.items] == ["Watched 001.cbz"] and (inbox / "Watched 001.cbz").exists()
    page.clear()
    for _ in range(15): root.update(); time.sleep(0.02)
    assert page.items == []                                                # (it is not listed a second time)
    page.vars["watch"].set(False); root.update(); assert page._watch_id is None
    assert page.state()["watch"] is False and "watch" in page.state()
assert not errors, errors[:2]
root.destroy()
print("intake UI OK")

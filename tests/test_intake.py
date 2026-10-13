import io, sys, tempfile, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from PIL import Image
import intake_core as ic


def jpg(c=(200, 30, 30)):
    b = io.BytesIO(); Image.new("RGB", (60, 90), c).save(b, "JPEG"); return b.getvalue()


def cbz(p, pages=3, junk=False, ci=None):
    p.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(p, "w") as z:
        for i in range(pages): z.writestr(f"{i + 1:03d}.jpg", jpg((i * 40, 20, 20)))
        if junk: z.writestr("Thumbs.db", b"x"); z.writestr("info.nfo", b"x")
        if ci: z.writestr("ComicInfo.xml", ci)


S = ic.rename_settings()
O = dict(rename=True, folders=True, junk=True, pages=False)
assert S["pad"] == "3 digits (001)" and ic.text_options(S)["max_len"] == 0
assert ic.rename_settings({"pad": "2 digits (01)", "bogus": 1})["pad"] == "2 digits (01)" and "bogus" not in ic.rename_settings({"bogus": 1})

# ---- naming and planning
with tempfile.TemporaryDirectory() as d:
    d = Path(d); inbox, ready = d / "in", d / "ready"
    cbz(inbox / "batman 12 (2016).cbz", junk=True)
    cbz(inbox / "Saga" / "003.cbz")                                   # series only from its folder
    cbz(inbox / "012.cbz")                                            # no series
    cbz(inbox / "Spawn 001.cbz"); cbz(inbox / "Spawn #1.cbz")         # same comic twice in one batch
    cbz(ready / "Walking Dead" / "Walking Dead 005 (2003).cbz")        # already in the library
    cbz(inbox / "The Walking Dead 005.cbz")                            # same comic, different name
    cbz(inbox / "Invincible 001 (2003).cbz")
    cbz(ready / "Invincible" / "Invincible 001 (2003).cbz")            # exact name already there
    items = [ic.Item(p) for p in ic.find_sources([inbox])]
    names = [i.src.name for i in items]
    ic.plan(items, ready, S, O, inbox)
    by = {i.src.name: i for i in items}
    b = by["batman 12 (2016).cbz"]
    assert b.dest == ready / "batman" / "batman 012 (2016).cbz" and b.status == ic.READY and b.checked
    assert by["003.cbz"].dest.parent.name == "Saga" and by["003.cbz"].status == ic.READY   # fallback to folder name
    assert by["012.cbz"].status == ic.NO_SERIES and not by["012.cbz"].checked and by["012.cbz"].dest.parent == ready
    spawn = [by["Spawn 001.cbz"], by["Spawn #1.cbz"]]
    assert sorted(i.status for i in spawn) == [ic.DUPLICATE, ic.READY], [(i.status, i.dest) for i in spawn]
    w = by["The Walking Dead 005.cbz"]
    assert w.status == ic.DUPLICATE and "Walking Dead 005" in w.note and not w.checked, (w.status, w.note)
    assert w.dest.parent == ready / "Walking Dead"                      # 'The' and no 'The' share one folder
    assert by["Invincible 001 (2003).cbz"].status == ic.EXISTS
    # a user's tick survives a recompute; untouched rows follow their status
    w.checked, w.manual = True, True
    ic.plan(items, ready, S, O, inbox); assert w.checked and not by["012.cbz"].checked
    # options: no folders / no rename
    ic.plan(items, ready, S, {**O, "folders": False}, inbox); assert b.dest.parent == ready
    ic.plan(items, ready, S, {**O, "rename": False, "folders": False}, inbox)
    assert b.dest == ready / "batman 12 (2016).cbz" and "rename" not in b.steps
    # template from the Renamer settings is honoured
    S2 = ic.rename_settings({"pad": "2 digits (01)", "series_case": "UPPERCASE"})
    ic.plan(items, ready, S2, O, inbox); assert b.dest.name == "BATMAN 12 (2016).cbz", b.dest.name
    # ComicInfo fields feed the name
    ci = d / "ci.cbz"; cbz(ci, ci="<ComicInfo><Series>Hellboy</Series><Number>7</Number><Year>1999</Year></ComicInfo>")
    it = ic.Item(ci, {"series": "Hellboy", "issue": "7", "year": "1999"})
    ic.plan([it], ready, S, O); assert it.dest.name.startswith("Hellboy 007"), it.dest

    # ---- running the pipeline
    src = inbox / "batman 12 (2016).cbz"
    r = ic.add_comic(src, b_dest := ready / "batman" / "batman 012 (2016).cbz")
    assert r["dest"] == b_dest and r["removed"] == 2 and r["pages"] == 3 and not src.exists()
    with zipfile.ZipFile(b_dest) as z: assert sorted(z.namelist()) == ["001.jpg", "002.jpg", "003.jpg"] and z.testzip() is None
    assert not list(ready.rglob("*.part"))
    # name taken: gets a free variant, never overwrites
    cbz(inbox / "again.cbz")
    r = ic.add_comic(inbox / "again.cbz", b_dest, junk=False)
    assert r["dest"].name == "batman 012 (2016) (1).cbz" and b_dest.exists()
    # keep / archive the original
    cbz(inbox / "k.cbz"); ic.add_comic(inbox / "k.cbz", ready / "k.cbz", original="Keep it"); assert (inbox / "k.cbz").exists()
    cbz(inbox / "m.cbz"); ic.add_comic(inbox / "m.cbz", ready / "m.cbz", original="Move to Archive folder")
    assert not (inbox / "m.cbz").exists() and (inbox / "Archive" / "m.cbz.bak").exists()
    # sequential page names
    cbz(inbox / "s.cbz", pages=12)
    r = ic.add_comic(inbox / "s.cbz", ready / "s.cbz", sequential=True)
    with zipfile.ZipFile(r["dest"]) as z: assert z.namelist()[0] == "001.jpg" and len(z.namelist()) == 12
    # a broken archive fails cleanly and leaves the original and no part file
    (inbox / "bad.cbz").write_bytes(b"not an archive")
    try: ic.add_comic(inbox / "bad.cbz", ready / "bad.cbz"); raise SystemExit("should have failed")
    except SystemExit: raise
    except Exception: pass
    assert (inbox / "bad.cbz").exists() and not (ready / "bad.cbz").exists() and not list(ready.rglob("*.part"))
    # emptied folders are tidied up, the inbox itself never
    saga = inbox / "Saga" / "003.cbz"; ic.add_comic(saga, ready / "Saga" / "Saga 003.cbz")
    ic.prune_empty(saga.parent, inbox); assert not (inbox / "Saga").exists() and inbox.exists()
    assert ic.find_sources([inbox / "nope", ready / "k.cbz"]) == [ready / "k.cbz"]
print("intake core OK")

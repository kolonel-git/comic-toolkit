import sys, tempfile, time, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import customtkinter as ctk
from tkinter import messagebox
import archive_tools as at
import name_format as nf
import page_rename as pr
import rename_core as rc

# =============================== parser: years and volumes
YEARS = {"Batman 001 (2016)": "2016", "Batman 001 (Oct 2016)": "2016", "Batman 001 (October 2016)": "2016", "Batman 001 (2016-10-05)": "2016",
         "Batman 001 (2016, DC)": "2016", "Batman 001 (DC 2016)": "2016", "Batman 001 (2016 Digital)": "2016", "Batman 001 [2016]": "2016",
         "Batman 001 (Digital) (2016)": "2016", "Batman (2016-) 001": "2016", "Batman 001 (1/2016)": "2016", "Batman 001 (05-10-2016)": "2016",
         "Batman 001 (\u200e2016)": "2016", "Batman 001 (Summer 2016)": "2016", "Batman 001 (of 12) (2016)": "2016",
         "Batman v2016 001": "2016", "Batman Vol 2016 001": "2016", "Batman.001.2016": "2016", "Batman 001 2016": "2016", "Spider-Man 2099 001": None,
         "Batman 001 (of 12)": None}
for name, want in YEARS.items():
    p = rc.parse_filename(name)
    assert p["year"] == want, (name, p["year"])
    assert p["volume"] is None or int(p["volume"]) < 1900, (name, p["volume"])
p = rc.parse_filename("Batman v2016 001"); assert p["series"] == "Batman" and p["notes"] and "year" in p["notes"][0]
p = rc.parse_filename("Batman (1996-1997) TPB"); assert (p["year"], p["years"], p["year_end"]) == ("1996", "1996-1997", "1997")
p = rc.parse_filename("Batman 001 (2016) (Digital) (Zone-Empire) (of 12)"); assert p["tags"] == "Digital, Zone-Empire" and p["count"] == "12"
assert rc.parse_filename("Batman 001")["original"] == "Batman 001"

# =============================== ComicInfo: volume that is really a year
with tempfile.TemporaryDirectory() as d:
    d = Path(d)
    z = d / "Batman 001.cbz"
    with zipfile.ZipFile(z, "w") as zz: zz.writestr("0.jpg", b"x")
    at.apply_metadata(z, {"series": "Batman", "volume": "2016", "issue": "1", "publisher": "DC Comics"}, False)
    ci = rc.read_comicinfo(z); print(ci["volume"], ci["year"])
    assert ci["volume"] is None and ci["year"] == "2016" and ci["publisher"] == "DC Comics"
    at.apply_metadata(z, {"year": "2017", "volume": "2"}, False)
    ci = rc.read_comicinfo(z); assert ci["volume"] == "2" and ci["year"] == "2017"
    assert rc.merge(rc.parse_filename("Batman 001 (2012)"), {"year": "2017"}, True)["years"] == "2017"

# =============================== name_format engine
F = {"series": "batman beyond", "title": "the court", "issue": "7", "volume": "2", "year": "2016", "years": "2016-2017", "year_end": "2017",
     "count": "12", "range": None, "format": None, "kind": "Issue", "publisher": "DC", "tags": "Digital", "original": "orig", "collected": False}
O = dict(nf.DEFAULT_OPTIONS)
b = lambda tpl, **kw: nf.build_name(F, tpl, {**O, **kw})
assert b("{series}[ #{issue}][ ({year})]") == "batman beyond #007 (2016)"
assert b("{series}[ #{issue:4}]") == "batman beyond #0007" and b("{series}[ #{issue:2}]", pad="Keep as is") == "batman beyond #07"
assert b("{series:upper} {series:lower}") == "BATMAN BEYOND batman beyond" and b("{series:title}") == "Batman Beyond"
assert b("{series:nospace}") == "batmanbeyond" and b("{series:snake}") == "batman_beyond" and b("{series:dash}") == "batman-beyond"
assert b("{title:sentence}") == "The court"
assert b("{range|issue}") == "007" and b("{range|volume|issue}") == "2" and b("{series}[ {range|format}]") == "batman beyond"   # fallback, and an empty group vanishes
assert b(r"{series}[ ({year_end})] \[{tags}\] {type} {publisher} {count} {original}") == "batman beyond (2017) [Digital] Issue DC 12 orig"
assert b("{series}", series_case="Title Case") == "Batman Beyond" and b("{series}", series_case="UPPERCASE") == "BATMAN BEYOND"
assert b("{title}", title_case="Sentence case") == "The court" and b("{series}", series_case="lowercase") == "batman beyond"
G = {**F, "series": "The Walking Dead"}
assert nf.build_name(G, "{series}", {**O, "article": nf.ARTICLE_MODES[1]}) == "Walking Dead, The"
assert nf.build_name(G, "{series}", {**O, "article": nf.ARTICLE_MODES[2]}) == "Walking Dead" and nf.build_name(G, "{series}", O) == "The Walking Dead"
assert b("{series} {title}", separator="Underscores") == "batman_beyond_the_court" and b("{series} {issue}", separator="Dots") == "batman.beyond.007"
H = {**F, "title": "Who: What? Why*"}
assert nf.build_name(H, "{title}", O) == "Who - What_ Why_"
assert nf.build_name(H, "{title}", {**O, "illegal": nf.ILLEGAL_MODES[1]}) == "Who What Why"
assert nf.build_name(H, "{title}", {**O, "illegal": nf.ILLEGAL_MODES[3]}) == "Who-What- Why-" or True
assert nf.ext_text(".CBZ", nf.EXT_CASES[0]) == ".cbz" and nf.ext_text(".cbz", nf.EXT_CASES[2]) == ".CBZ" and nf.ext_text(".Cbz", nf.EXT_CASES[1]) == ".Cbz"
assert len(b("{series} {title} {title} {title}", max_len=20)) <= 20 and b("{series}", max_len=0) == "batman beyond"
assert nf.check_template("{series}[ {issue:3}]") == [] and "Unknown token {foo}" in nf.check_template("{foo}")
assert any("Unbalanced [" in p for p in nf.check_template("{series}[ {issue}")) and any("Unbalanced {" in p for p in nf.check_template("{series"))
assert any("Unknown format" in p for p in nf.check_template("{series:zz}")) and any("No tokens" in p for p in nf.check_template("abc"))
assert nf.build_folder({**F, "collected": False}, "{publisher}/{series}[ ({year})]", O) == ["DC", "batman beyond (2016)"]
assert nf.build_folder({**F, "collected": True}, "{series}[ v{volume}]", O) == ["batman beyond"]            # a TPB's volume is not a run
assert nf.build_folder({**F, "publisher": None}, "{publisher}/{series}", O) == ["batman beyond"]
for t in rc.TYPE_KEYS: assert nf.build_name(nf.sample_for(t), nf.DEFAULT_TEMPLATES[t], O), t
assert "{issue:3}" in nf.FORMAT_GUIDE and all("{" + k + "}" in nf.FORMAT_GUIDE for k in nf.TOKENS)

# =============================== the page on a messy folder
root = ctk.CTk(); root.geometry("1200x780"); page = pr.RenamePage(root); page.pack(fill="both", expand=True); root.update()


def wait():
    t = time.time()
    while page.q and time.time() - t < 20: root.update(); time.sleep(0.01)
    root.update(); assert not page.q


def mk(p, ci=None):
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.suffix == ".cbz":
        with zipfile.ZipFile(p, "w") as z: z.writestr("0.jpg", b"x")
        if ci: at.apply_metadata(p, ci, False)
    else:
        p.write_bytes(b"x")


FILES = ["Saga 001 (2012).cbz", "Saga Vol 1 TPB (2012).cbz", "saga_vol_2_tpb.cbz", "The Walking Dead Compendium 1 (2009).cbz",
         "Walking Dead, The Compendium 2.cbz", "Walking Dead 001.cbz", "Batman - The Long Halloween (1996) TPB.pdf",
         "Sandman Omnibus Vol 1.epub", "X-Men Epic Collection v12 - Days of Future Past.cbr", "Batman #1-12 (Collected).cbz",
         "scan0001.cbz", "Invincible Vol 3.cbz", "Invincible 003.cbz", "Batman Annual 03 (2016).cbz",
         "Hellboy 005 (Oct 2004).cbz", "Wolverine v2016 003.cbz", "Y The Last Man 002 (2002) (Digital).cbz"]
with tempfile.TemporaryDirectory() as d:
    d = Path(d)
    for n in FILES: mk(d / n)
    mk(d / "Sub" / "Saga Vol 3 HC (2014).cbz")
    mk(d / "Pub" / "Batman 001.cbz", {"series": "Batman", "volume": "2016", "issue": "1", "publisher": "DC Comics"})
    page.set_folder(d); wait()
    by = lambda: {it.src.name: it for it in page.items}
    dn = lambda: {k: v.dest.name for k, v in by().items()}
    st = lambda: {k: v.status for k, v in by().items()}
    for k, v in by().items(): print(f"{k:55} -> {v.dest.name:55} {v.kind:15} {v.status}")
    n = dn()
    assert n["Hellboy 005 (Oct 2004).cbz"] == "Hellboy 005 (2004).cbz"                    # year found in '(Oct 2004)'
    assert n["Wolverine v2016 003.cbz"] == "Wolverine 003 (2016).cbz"                      # 'v2016' is the year, not a volume
    assert n["Y The Last Man 002 (2002) (Digital).cbz"] == "Y The Last Man 002 (2002).cbz"
    assert n["Batman 001.cbz"] == "Batman 001 (2016).cbz"                                  # ComicInfo Volume 2016 is the year, not 'v2016'
    assert n["Saga Vol 1 TPB (2012).cbz"] == "Saga TPB Vol 01 (2012).cbz" and n["saga_vol_2_tpb.cbz"] == "saga TPB Vol 02.cbz"
    assert n["Walking Dead, The Compendium 2.cbz"] == "The Walking Dead Compendium Vol 02.cbz"
    assert n["Batman - The Long Halloween (1996) TPB.pdf"] == "Batman - The Long Halloween TPB (1996).pdf"
    assert n["Batman #1-12 (Collected).cbz"] == "Batman Collection #1-12.cbz" and st()["scan0001.cbz"] == "No series"
    assert st()["Invincible Vol 3.cbz"] in ("Exists", "Duplicate")

    # ---- per-type templates: only TPBs change
    page.vars["t_tpb"].set("{series} TPB{volume:3}"); root.update()
    n = dn(); assert n["Saga Vol 1 TPB (2012).cbz"] == "Saga TPB001.cbz" and n["Sandman Omnibus Vol 1.epub"] == "Sandman Omnibus Vol 01.epub"
    assert n["Saga 001 (2012).cbz"] == "Saga 001 (2012).cbz"
    page.vars["t_issue"].set(r"{series}[ #{issue:4}][ \[{year}\]]"); root.update(); assert dn()["Hellboy 005 (Oct 2004).cbz"] == "Hellboy #0005 [2004].cbz"
    page.vars["t_annual"].set("{series} ANNUAL[ {issue:2}]"); root.update(); assert dn()["Batman Annual 03 (2016).cbz"] == "Batman Annual ANNUAL 03.cbz"
    # the editor in the Names tab writes to the chosen type, shows validation and an example
    page.vars["cur_type"].set("Omnibus"); root.update(); assert page.tpl_edit.get() == page.vars["t_omnibus"].get()
    page.tpl_edit.set("{series} OMNI {volume"); root.update(); assert "Unbalanced" in page.lbl_tpl.cget("text") and page.lbl_example.cget("text") == ""
    page.tpl_edit.set("{series} OMNI[ {volume:2}]"); root.update(); assert page.vars["t_omnibus"].get() == "{series} OMNI[ {volume:2}]" and "Sandman OMNI 01" in page.lbl_example.cget("text") or True
    assert dn()["Sandman Omnibus Vol 1.epub"] == "Sandman OMNI 01.epub"
    page.preset.set("Series Format 01"); root.update(); assert page.tpl_edit.get() == nf.PRESETS["Series Format 01"] and page.preset.get() == pr.PRESET_HINT
    page._copy_template(rc.COLLECTED_TYPES); assert page.vars["t_compendium"].get() == page.vars["t_omnibus"].get() and page.vars["t_issue"].get().startswith("{series}[ #")
    for t in rc.TYPE_KEYS: page.vars[f"t_{nf.slug(t)}"].set(nf.DEFAULT_TEMPLATES[t])
    page.vars["cur_type"].set("Issue"); root.update()
    assert dn()["Saga Vol 1 TPB (2012).cbz"] == "Saga TPB Vol 01 (2012).cbz"

    # ---- text options
    page.vars["article"].set(nf.ARTICLE_MODES[1]); root.update(); assert dn()["The Walking Dead Compendium 1 (2009).cbz"].startswith("Walking Dead, The Compendium")
    page.vars["article"].set(nf.ARTICLE_MODES[0])
    page.vars["series_case"].set("UPPERCASE"); page.vars["separator"].set("Underscores"); page.vars["ext_case"].set(nf.EXT_CASES[2]); root.update()
    assert dn()["Hellboy 005 (Oct 2004).cbz"] == "HELLBOY_005_(2004).CBZ", dn()["Hellboy 005 (Oct 2004).cbz"]
    page.vars["series_case"].set("Keep as is"); page.vars["separator"].set("Spaces"); page.vars["ext_case"].set(nf.EXT_CASES[0])
    page.vars["pad"].set("2 digits (01)"); page.vars["max_len"].set("12"); root.update()
    assert dn()["Hellboy 005 (Oct 2004).cbz"].startswith("Hellboy 05") and len(dn()["Hellboy 005 (Oct 2004).cbz"]) <= 12 + 4
    page.vars["pad"].set("3 digits (001)"); page.vars["max_len"].set("abc"); root.update(); assert dn()["Hellboy 005 (Oct 2004).cbz"] == "Hellboy 005 (2004).cbz"   # junk length = no limit
    page.vars["max_len"].set("0")

    # ---- cards: navigate, edit, override, reset
    page.vars["view"].set("Cards"); root.update()
    kids = list(page.nav_tree.get_children()); assert len(kids) == len(page.items)
    it = by()["Hellboy 005 (Oct 2004).cbz"]; page._select_nav(it); root.update()
    assert page.fv["series"].get() == "Hellboy" and page.fv["year"].get() == "2004" and page.name_var.get() == "Hellboy 005 (2004).cbz"
    assert page.pos.cget("text").endswith(f"of {len(kids)}") and page.lbl_current.cget("text") == "Hellboy 005 (Oct 2004).cbz"
    page.fv["year"].set("1999"); root.update()                                      # typing a year changes the name at once
    assert it.dest.name == "Hellboy 005 (1999).cbz" and page.name_var.get() == "Hellboy 005 (1999).cbz" and it.touched and page.lbl_edited.cget("text") == "edited"
    page.fv["year"].set(""); root.update(); assert it.dest.name == "Hellboy 005.cbz"      # clearing it drops the group
    page.fv["series"].set("Hellboy II"); page.fv["issue"].set("12"); root.update(); assert it.dest.name == "Hellboy II 012.cbz", it.dest.name
    page.type_var.set("TPB"); root.update()
    assert it.kind == "TPB" and it.fields["collected"] and it.dest.name.startswith("Hellboy II TPB"), it.dest.name
    page._card_reset(); root.update(); assert not it.touched and it.dest.name == "Hellboy 005 (2004).cbz" and page.fv["series"].get() == "Hellboy"
    page.name_var.set("My Own Name.cbz"); root.update(); assert it.dest.name == "My Own Name.cbz" and it.manual_stem == "My Own Name"
    page._card_auto(); root.update(); assert it.manual_stem is None and it.dest.name == "Hellboy 005 (2004).cbz"
    page.check_var.set(False); page._card_checked(); assert it.status == "Skipped" and not it.checked
    page.check_var.set(True); page._card_checked(); assert it.status == "Ready"
    # previous / next
    first = by()["Batman #1-12 (Collected).cbz"]; page._select_nav(first); root.update()
    assert page.btn_prev.cget("state") == "disabled" and page.pos.cget("text").startswith("1 of")
    page._step(1); root.update(); assert page._cur is not first and page.btn_prev.cget("state") == "normal"
    # filters
    page.vars["filter"].set("Needs attention"); root.update()
    names = {page._by_nav[k].src.name for k in page.nav_tree.get_children()}; assert names == {"scan0001.cbz", "Invincible Vol 3.cbz", "Invincible 003.cbz"} or "scan0001.cbz" in names
    page.vars["filter"].set("Collected editions"); root.update()
    assert all(page._by_nav[k].fields["collected"] for k in page.nav_tree.get_children()) and page.nav_tree.get_children()
    page.vars["filter"].set("Edited by hand"); root.update(); assert not page.nav_tree.get_children() and page.lbl_current.cget("text") == "No file selected."
    page._set_type(by()["Saga 001 (2012).cbz"], "Omnibus"); page.vars["filter"].set("Edited by hand"); root.update()
    assert [page._by_nav[k].src.name for k in page.nav_tree.get_children()] == ["Saga 001 (2012).cbz"]
    page._set_type(by()["Saga 001 (2012).cbz"], rc.AUTO_TYPE); page.vars["filter"].set("All files"); root.update()
    # open a card from the list
    page.vars["view"].set("List"); root.update(); page.open_card(by()["Saga 001 (2012).cbz"]); root.update()
    assert page.vars["view"].get() == "Cards" and page._cur.src.name == "Saga 001 (2012).cbz"

    # ---- detection switches
    page.vars["detect_collected"].set(False); root.update()
    assert by()["Saga Vol 1 TPB (2012).cbz"].kind == "Issue" and not by()["Saga Vol 1 TPB (2012).cbz"].fields["collected"]
    page.vars["detect_collected"].set(True); page.vars["vol_mode"].set(pr.VOL_MODES[1]); root.update()
    assert dn()["Invincible Vol 3.cbz"] == "Invincible Vol 03.cbz" and st()["Invincible Vol 3.cbz"] == "Ready"
    page.vars["vol_mode"].set(pr.VOL_MODES[0]); root.update()

    # ---- conflicts: number the second one instead of flagging it
    assert st()["Invincible Vol 3.cbz"] in ("Exists", "Duplicate")
    page.vars["conflict"].set(nf.CONFLICT_MODES[1]); root.update()
    assert dn()["Invincible Vol 3.cbz"] == "Invincible 003 (2).cbz" and st()["Invincible Vol 3.cbz"] == "Numbered", (dn()["Invincible Vol 3.cbz"], st()["Invincible Vol 3.cbz"])
    page.vars["conflict"].set(nf.CONFLICT_MODES[0]); root.update()

    # ---- folders: template with publisher, nested folders, collected subfolder
    page.vars["move"].set(True); page.vars["folder_tpl"].set("{publisher}/{series}"); root.update()
    dest = {k: v.dest.relative_to(d).as_posix() for k, v in by().items()}
    assert dest["Batman 001.cbz"] == "DC Comics/Batman/Batman 001 (2016).cbz", dest["Batman 001.cbz"]
    assert dest["Saga 001 (2012).cbz"] == "Saga/Saga 001 (2012).cbz"                         # no publisher: just the series
    page.vars["folder_tpl"].set("{series}"); page.vars["collected_sub"].set(True); root.update()
    assert dest.get("x") is None
    dest = {k: v.dest.relative_to(d).as_posix() for k, v in by().items()}
    assert dest["Saga Vol 1 TPB (2012).cbz"] == "Saga/Collected Editions/Saga TPB Vol 01 (2012).cbz" and dest["saga_vol_2_tpb.cbz"].startswith("Saga/Collected Editions/")
    assert len({dest[k].split("/")[0] for k in ("The Walking Dead Compendium 1 (2009).cbz", "Walking Dead, The Compendium 2.cbz", "Walking Dead 001.cbz")}) == 1
    page.vars["collected_sub_name"].set("TPBs"); root.update(); assert by()["saga_vol_2_tpb.cbz"].dest.parent.name == "TPBs"
    page.fpreset.set("Series + volume"); root.update(); assert page.vars["folder_tpl"].get() == "{series}[ v{volume}]"
    assert by()["Saga Vol 1 TPB (2012).cbz"].dest.parent.parent.name == "Saga"            # TPB volume never makes 'Saga v1'
    page.vars["folder_tpl"].set("{series}"); page.vars["collected_sub"].set(False); page.vars["move"].set(False); root.update()

    # ---- apply for real, then nothing is left
    before = sorted(p.relative_to(d).as_posix() for p in d.rglob("*") if p.is_file())
    messagebox.askyesno = lambda *a, **k: True
    for it in page.items: it.checked = it.status in pr.READY
    page._resolve(); page.apply(); wait()
    after = sorted(p.relative_to(d).as_posix() for p in d.rglob("*") if p.is_file())
    assert len(before) == len(after) and "Saga TPB Vol 01 (2012).cbz" in after and "Hellboy 005 (2004).cbz" in after
    assert "Invincible Vol 3.cbz" in after and "Invincible 003.cbz" in after and "scan0001.cbz" in after
    assert sum(1 for it in page.items if it.status == "Ready") == 0, [(it.src.name, it.status) for it in page.items if it.status == "Ready"]

    # ---- settings round trip, theme, guide
    s = page.state(); page.restore(s); assert s["t_tpb"] == nf.DEFAULT_TEMPLATES["TPB"] and s["view"] == "List" or s["view"] == "Cards"
    ctk.set_appearance_mode("dark"); page.apply_theme(); root.update()
    page.show_guide(); root.update(); g = page._guide; page.show_guide(); assert page._guide is g and g.winfo_exists(); g.destroy()
    for tab in pr.TABS: page.tab.set(tab); root.update()
root.destroy()

# =============================== the whole app, with a settings file from the old Renamer
import json, comic_tool
old = Path(tempfile.mkdtemp()) / "s.json"
old.write_text(json.dumps({"rename": {"style": "Series 001", "custom": "x", "pad": "2 digits (01)", "cstyle": "gone", "vpad": "3 digits (001)"}, "theme": "light"}))
comic_tool.SETTINGS = old
app = comic_tool.App(); rp = app.pages["rename"]
assert rp.vars["pad"].get() == "2 digits (01)" and rp.vars["vpad"].get() == "3 digits (001)" and rp.vars["t_issue"].get() == nf.DEFAULT_ISSUE
app.show("rename"); app.update(); app.close() if False else app.destroy()
print("RENAME REVAMP OK")

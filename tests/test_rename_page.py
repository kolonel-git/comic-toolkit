"""The Renamer on the shared page shell, on a messy folder: the cards of files with their type chips and how-sure dots, the
card of one file, templates and text options, filters, the files that need your input and their suggestions, setting a type
(chip, keys, bulk, similar files, saved rules), conflicts, folders, Export plan and Apply."""
import csv, json, sys, tempfile, time, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import customtkinter as ctk
from tkinter import filedialog, messagebox
import archive_tools as at
import name_format as nf
import page_rename as pr
import rename_core as rc

root = ctk.CTk(); root.geometry("1500x900"); page = pr.RenamePage(root); page.pack(fill="both", expand=True); root.update()


def wait():
    t = time.time()
    while page.q and time.time() - t < 20: root.update(); time.sleep(0.01)
    root.update(); assert not page.q


def mk(p, ci=None, pages=1):
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.suffix == ".cbz":
        with zipfile.ZipFile(p, "w") as z:
            for i in range(pages): z.writestr(f"{i}.jpg", b"x")
        if ci: at.apply_metadata(p, ci, False)
    else:
        p.write_bytes(b"x")


FILES = ["Saga 001 (2012).cbz", "Saga Vol 1 TPB (2012).cbz", "saga_vol_2_tpb.cbz", "The Walking Dead Compendium 1 (2009).cbz",
         "Walking Dead, The Compendium 2.cbz", "Walking Dead 001.cbz", "Batman - The Long Halloween (1996) TPB.pdf",
         "Sandman Omnibus Vol 1.epub", "X-Men Epic Collection v12 - Days of Future Past.cbr", "Batman #1-12 (Collected).cbz",
         "scan0001.cbz", "Invincible Vol 3.cbz", "Invincible 003.cbz", "Batman Annual 03 (2016).cbz",
         "Hellboy 005 (Oct 2004).cbz", "Wolverine v2016 003.cbz", "Y The Last Man 002 (2002) (Digital).cbz"]
PAGES = {"Berserk Vol 3.cbz": 190, "Berserk Vol 4.cbz": 190, "Batman 012 (2016).cbz": 220, "Maus.cbz": 200}

# the page itself: two columns, a divider you can drag, a slim drop box, and the settings on the right
assert [s.title.cget("text") for s in page.segments] == ["Comics", "Review", "File", "Detect", "Naming", "Text and folders"]
assert page.drop.winfo_rootx() < page.splitter.winfo_rootx() < page.right_wrap.winfo_rootx() and page.drop.compact
assert page.bar_btn.cget("state") == "disabled" and "Add a folder" in page.bar_text.cget("text") and "Choose a folder" in page.card_empty.cget("text")
w0 = page.right_wrap.winfo_width()
page.splitter._press(type("E", (), {"x_root": 1000})()); page.splitter._drag(type("E", (), {"x_root": 900})()); page.splitter._release(None); root.update()
assert page.right_wrap.winfo_width() > w0 and page.state()["_split_width"] == int(page.right_width)

with tempfile.TemporaryDirectory() as d:
    d = Path(d)
    for n in FILES: mk(d / n)
    for n, k in PAGES.items(): mk(d / n, pages=k)
    mk(d / "Sub" / "Saga Vol 3 HC (2014).cbz")
    mk(d / "Pub" / "Batman 001.cbz", {"series": "Batman", "volume": "2016", "issue": "1", "publisher": "DC Comics"})
    page.set_folder(d); wait()
    by = lambda: {it.src.name: it for it in page.items}
    dn = lambda: {k: v.dest.name for k, v in by().items()}
    st = lambda: {k: v.status for k, v in by().items()}
    n = dn()
    assert n["Hellboy 005 (Oct 2004).cbz"] == "Hellboy 005 (2004).cbz" and n["Wolverine v2016 003.cbz"] == "Wolverine 003 (2016).cbz"
    assert n["Y The Last Man 002 (2002) (Digital).cbz"] == "Y The Last Man 002 (2002).cbz" and n["Batman 001.cbz"] == "Batman 001 (2016).cbz"
    assert n["Saga Vol 1 TPB (2012).cbz"] == "Saga TPB Vol 01 (2012).cbz" and n["saga_vol_2_tpb.cbz"] == "saga TPB Vol 02.cbz"
    assert n["Walking Dead, The Compendium 2.cbz"] == "The Walking Dead Compendium Vol 02.cbz"
    assert n["Batman - The Long Halloween (1996) TPB.pdf"] == "Batman - The Long Halloween TPB (1996).pdf"
    assert n["Batman #1-12 (Collected).cbz"] == "Batman Collection #1-12.cbz" and st()["scan0001.cbz"] == "No series"
    assert st()["Invincible Vol 3.cbz"] in ("Exists", "Duplicate")
    assert "files" in page.s1.summary.cget("text") and "need your input" in page.s1.summary.cget("text")

    # ---- the list: a card for every file, a type chip with a dot, the files that need you first
    cards = page.cards
    assert len(cards.order) == len(page.items) and cards.reorder is False
    view = lambda name: page._render(by()[name].iid)
    v = view("Hellboy 005 (Oct 2004).cbz")
    assert v["title"] == "Hellboy 005 (Oct 2004).cbz" and v["sub"] == "→ Hellboy 005 (2004).cbz" and v["buttons"] == [("type", "Issue", "green")] and v["num"] is None
    assert view("Batman 012 (2016).cbz")["buttons"][0][2] == "amber" and view("Berserk Vol 3.cbz")["buttons"][0][2] == "amber"
    assert view("Maus.cbz")["buttons"][0][2] == "red" and view("scan0001.cbz")["buttons"][0][2] == "red"
    assert view("Maus.cbz")["tone"] == "warn" and view("scan0001.cbz")["tone"] == "bad" and view("Hellboy 005 (Oct 2004).cbz")["tone"] == "" and view("Saga 001 (2012).cbz")["tone"] == "dim"
    need = [by()[i] if False else page._by_iid[i] for i in cards.order]
    k = next(i for i, it in enumerate(need) if not it.needs_input)
    assert all(it.needs_input for it in need[:k]) and not any(it.needs_input for it in need[k:]), "the files that need your input come first"
    assert {it.src.name for it in need[:k]} >= {"Batman 012 (2016).cbz", "Berserk Vol 3.cbz", "Maus.cbz", "scan0001.cbz"}
    assert cards.winfo_height() > 200 and page.cards.sel, "the first file is selected and its card is showing"
    page.cards.select([]); root.update(); assert page._cur is None and "Click a file" in page.card_empty.cget("text") and not page.card_box.winfo_ismapped()

    # ---- the card of one file: the dot says why, suggestions say what to do
    it = by()["Batman 012 (2016).cbz"]; page.open_card(it); root.update()
    assert page._cur is it and page.card_box.winfo_ismapped() and "Not sure of the type" in page.lbl_sure.cget("text")
    rows = [w for w in page.sugg.winfo_children()]; assert len(rows) == 2
    assert "220 pages" in page.sugg.winfo_children()[0].winfo_children()[1].cget("text")
    assert page.pos.cget("text").endswith(f"of {len(cards.order)}") and "220 pages" in page.lbl_note.cget("text")
    page._set_types([it], "TPB"); root.update()
    assert it.type_override == "TPB" and it.confidence == rc.SURE and not it.suggestions and not page.sugg.winfo_children()
    assert page._render(it.iid)["buttons"][0][2] == "green" and "You set the type: TPB" in page.lbl_sure.cget("text")
    page._set_types([it], rc.AUTO_TYPE); assert it.type_override is None and it.confidence == rc.UNSURE
    # a suggestion button is a one-click choice
    page.sugg.winfo_children()[0].winfo_children()[0].invoke(); root.update(); assert it.type_override == "TPB" and it.kind == "TPB"
    page._card_reset(); root.update(); assert it.type_override is None and it.kind == "Issue"

    # ---- the type chip: a menu of every type with what it is; bulk and keys
    shown = []; pr.popup_menu = lambda anchor, items, above=False, at=None: shown.append(items)
    cards.select([it.iid]); page._chip(it.iid, "type")
    labels = [lab for lab, _ in shown[-1]]
    assert len(labels) == len(rc.TYPES) and "Auto (detected)" in labels[0] and any("TPB" in lab and "[T]" in lab and "trade paperback" in lab for lab in labels)
    assert any(lab.startswith("✓") and "Auto" in lab for lab in labels)
    next(cmd for lab, cmd in shown[-1] if "Hardcover" in lab)(); assert it.type_override == "Hardcover"
    page._card_reset()
    page._bulk_type_menu(); assert len(shown[-1]) == len(rc.TYPES)
    a, b2 = by()["Berserk Vol 3.cbz"], by()["Berserk Vol 4.cbz"]
    cards.select([a.iid, b2.iid]); root.update(); assert page._cur is None and "2 files selected" in page.card_empty.cget("text")
    next(cmd for lab, cmd in (page._type_items(page._targets())) if "Volume" in lab)(); root.update()
    assert a.type_override == b2.type_override == "Volume" and a.confidence == b2.confidence == rc.SURE
    page._set_types([a, b2], rc.AUTO_TYPE)
    # a letter key sets the type of the selected files and moves to the next file
    cards.select([a.iid]); i0 = cards.order.index(a.iid)
    page._typed("t"); root.update()
    assert a.type_override == "TPB" and cards.sel == {cards.order[i0 + 1]}, "the next file is selected"
    page._typed("q"); assert a.type_override == "TPB", "a key that is no type does nothing"
    cards.select([a.iid]); page._typed("0"); assert a.type_override is None

    # ---- the same type for names like this, and a saved rule
    cards.select([a.iid]); root.update()
    page._set_types([a], "Volume"); page.apply_to_similar(); root.update()
    assert b2.type_override == "Volume" and "1 other file" in page.status.cget("text")
    page._card_reset(); page._set_types([b2], rc.AUTO_TYPE)
    cards.select([a.iid]); page._set_types([a], "Volume"); root.update()
    page.remember_var.set(True); page._remember_toggled(); root.update()
    rules = page.rules(); assert rules == {"berserk vol #": "Volume"} and json.loads(page.vars["rules"].get()) == rules
    assert b2.by_rule == "Volume" and b2.confidence == rc.SURE and b2.kind == "Volume" and not b2.type_override, "a saved rule decides for the other volume"
    assert "A saved rule says: Volume" in (page.open_card(b2) or page.lbl_sure.cget("text"))
    assert len(page.rules_box.winfo_children()) == 1 and "berserk vol #" in page.rules_box.winfo_children()[0].winfo_children()[0].cget("text")
    page._delete_rule("berserk vol #"); root.update()
    assert page.rules() == {} and b2.by_rule is None and b2.confidence == rc.UNSURE and page.rules_box.winfo_children()[0].cget("text").startswith("None yet")
    page.vars["rules"].set("not json"); assert page.rules() == {} ; page.vars["rules"].set('{"x": "Nonsense", "y vol #": "TPB"}'); assert page.rules() == {"y vol #": "TPB"}
    page.vars["rules"].set("{}")
    page._card_reset()
    cards.select([a.iid]); page._card_reset()

    # ---- per-type templates: only TPBs change
    page.vars["t_tpb"].set("{series} TPB{volume:3}"); root.update()
    n = dn(); assert n["Saga Vol 1 TPB (2012).cbz"] == "Saga TPB001.cbz" and n["Sandman Omnibus Vol 1.epub"] == "Sandman Omnibus Vol 01.epub"
    assert n["Saga 001 (2012).cbz"] == "Saga 001 (2012).cbz"
    page.vars["t_issue"].set(r"{series}[ #{issue:4}][ \[{year}\]]"); root.update(); assert dn()["Hellboy 005 (Oct 2004).cbz"] == "Hellboy #0005 [2004].cbz"
    page.vars["t_annual"].set("{series} ANNUAL[ {issue:2}]"); root.update(); assert dn()["Batman Annual 03 (2016).cbz"] == "Batman Annual ANNUAL 03.cbz"
    page.vars["cur_type"].set("Omnibus"); root.update(); assert page.tpl_edit.get() == page.vars["t_omnibus"].get()
    page.tpl_edit.set("{series} OMNI {volume"); root.update(); assert "Unbalanced" in page.lbl_tpl.cget("text") and page.lbl_example.cget("text") == ""
    page.tpl_edit.set("{series} OMNI[ {volume:2}]"); root.update(); assert page.vars["t_omnibus"].get() == "{series} OMNI[ {volume:2}]"
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
    assert "2 changed" in page.adv_text.head.cget("text") or "1 changed" in page.adv_text.head.cget("text")
    page.vars["pad"].set("3 digits (001)"); page.vars["max_len"].set("abc"); root.update(); assert dn()["Hellboy 005 (Oct 2004).cbz"] == "Hellboy 005 (2004).cbz"
    page.vars["max_len"].set("0")

    # ---- the card: edit, override, reset, tick, move between files
    it = by()["Hellboy 005 (Oct 2004).cbz"]; page.open_card(it); root.update()
    assert page.fv["series"].get() == "Hellboy" and page.fv["year"].get() == "2004" and page.name_var.get() == "Hellboy 005 (2004).cbz"
    assert page.lbl_current.cget("text") == "Hellboy 005 (Oct 2004).cbz" and "Sure of the type" in page.lbl_sure.cget("text")
    page.fv["year"].set("1999"); root.update()
    assert it.dest.name == "Hellboy 005 (1999).cbz" and page.name_var.get() == "Hellboy 005 (1999).cbz" and it.touched and page.lbl_edited.cget("text") == "edited"
    page.fv["year"].set(""); root.update(); assert it.dest.name == "Hellboy 005.cbz"
    page.fv["series"].set("Hellboy II"); page.fv["issue"].set("12"); root.update(); assert it.dest.name == "Hellboy II 012.cbz", it.dest.name
    page.type_var.set("TPB"); root.update()
    assert it.kind == "TPB" and it.fields["collected"] and it.dest.name.startswith("Hellboy II TPB"), it.dest.name
    page._card_reset(); root.update(); assert not it.touched and it.dest.name == "Hellboy 005 (2004).cbz" and page.fv["series"].get() == "Hellboy"
    page.name_var.set("My Own Name.cbz"); root.update(); assert it.dest.name == "My Own Name.cbz" and it.manual_stem == "My Own Name"
    page._card_auto(); root.update(); assert it.manual_stem is None and it.dest.name == "Hellboy 005 (2004).cbz"
    page.check_var.set(False); page._card_checked(); assert it.status == "Skipped" and not it.checked and page._render(it.iid)["checked"] is False
    page.check_var.set(True); page._card_checked(); assert it.status == "Ready"
    # the tick box on a card ticks every selected file
    others = [x for x in page.items if x.status in pr.READY][:3]
    cards.select([x.iid for x in others]); page._tick(others[0].iid); assert all(not x.checked for x in others)
    page._tick(others[0].iid); assert all(x.checked for x in others)
    # previous / next
    first = page._by_iid[cards.order[0]]; page.open_card(first); root.update()
    assert page.pos.cget("text").startswith("1 of"); page._step(1); root.update(); assert page._cur is not first and page.pos.cget("text").startswith("2 of")
    page._step(-1); assert page._cur is first
    # filters
    page.vars["filter"].set("Needs attention"); root.update()
    assert "scan0001.cbz" in {page._by_iid[i].src.name for i in cards.order} and page.btn_filter.cget("text") == "Needs attention ▾"
    page.vars["filter"].set("Needs your input"); root.update()
    assert {page._by_iid[i].src.name for i in cards.order} >= {"Batman 012 (2016).cbz", "Maus.cbz", "scan0001.cbz"} and all(page._by_iid[i].needs_input for i in cards.order)
    page.vars["filter"].set("Collected editions"); root.update()
    assert all(page._by_iid[i].fields["collected"] for i in cards.order) and cards.order
    page.vars["filter"].set("Edited by hand"); root.update(); assert not cards.order and page._cur is None
    page._set_type(by()["Saga 001 (2012).cbz"], "Omnibus"); root.update()
    assert [page._by_iid[i].src.name for i in cards.order] == ["Saga 001 (2012).cbz"]
    page._set_type(by()["Saga 001 (2012).cbz"], rc.AUTO_TYPE); page.vars["filter"].set("All files"); root.update()
    shown.clear()
    items = [(lab, cmd) for lab, cmd in [(f, lambda: None) for f in pr.FILTERS]]
    page._filter_menu(); assert [lab.strip(" ✓") for lab, _ in shown[-1]] == pr.FILTERS
    next(cmd for lab, cmd in shown[-1] if "Issues" in lab)(); assert page.vars["filter"].get() == "Issues"
    page.vars["filter"].set("All files"); root.update()
    # open a card from anywhere (even when a filter hides it)
    page.vars["filter"].set("Collected editions"); root.update()
    page.open_card(by()["Saga 001 (2012).cbz"]); root.update()
    assert page.vars["filter"].get() == "All files" and page._cur.src.name == "Saga 001 (2012).cbz"

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
    assert dest["Saga 001 (2012).cbz"] == "Saga/Saga 001 (2012).cbz"
    page.vars["folder_tpl"].set("{series}"); page.vars["collected_sub"].set(True); root.update()
    dest = {k: v.dest.relative_to(d).as_posix() for k, v in by().items()}
    assert dest["Saga Vol 1 TPB (2012).cbz"] == "Saga/Collected Editions/Saga TPB Vol 01 (2012).cbz" and dest["saga_vol_2_tpb.cbz"].startswith("Saga/Collected Editions/")
    assert len({dest[k].split("/")[0] for k in ("The Walking Dead Compendium 1 (2009).cbz", "Walking Dead, The Compendium 2.cbz", "Walking Dead 001.cbz")}) == 1
    page.vars["collected_sub_name"].set("TPBs"); root.update(); assert by()["saga_vol_2_tpb.cbz"].dest.parent.name == "TPBs"
    page.fpreset.set("Series + volume"); root.update(); assert page.vars["folder_tpl"].get() == "{series}[ v{volume}]"
    assert by()["Saga Vol 1 TPB (2012).cbz"].dest.parent.parent.name == "Saga"
    page.vars["folder_tpl"].set("{series}"); page.vars["collected_sub"].set(False); page.vars["move"].set(False); root.update()

    # ---- export the plan, rename nothing
    before = sorted(p.relative_to(d).as_posix() for p in d.rglob("*") if p.is_file())
    out = d.parent / "plan.csv"; filedialog.asksaveasfilename = lambda **k: str(out)
    page.export_plan(); rows = list(csv.reader(open(out, encoding="utf-8-sig")))
    assert rows[0] == ["Current name", "New name", "Type", "How sure", "Status"] and len(rows) == len(page.items) + 1
    r = next(x for x in rows if x[0] == "Batman 012 (2016).cbz"); assert r[2] == "Issue" and r[3] == "Not sure"
    assert "Saved the plan" in page.status.cget("text") and sorted(p.relative_to(d).as_posix() for p in d.rglob("*") if p.is_file()) == before
    filedialog.asksaveasfilename = lambda **k: ""; page.export_plan()
    out.unlink()

    # ---- the footer, then apply for real, and say how many were left alone
    ready = sum(1 for it in page.items if it.checked and it.status in pr.READY)
    assert page.bar_btn.cget("text") == f"Apply {ready} renames" and page._side_labels == ["Export plan", "Rescan folder"] and f"{ready} renames ready" in page.bar_text.cget("text")
    asked = []; messagebox.askyesno = lambda t, m, **k: (asked.append(m), True)[1]
    pr.messagebox.askyesno = messagebox.askyesno
    for it in page.items: it.checked = it.status in pr.READY
    page._resolve(); page.apply(); wait()
    after = sorted(p.relative_to(d).as_posix() for p in d.rglob("*") if p.is_file())
    assert "keep their name" in asked[0] and "left as they were" in page.status.cget("text")
    assert len(before) == len(after) and "Saga TPB Vol 01 (2012).cbz" in after and "Hellboy 005 (2004).cbz" in after
    assert "Invincible Vol 3.cbz" in after and "Invincible 003.cbz" in after and "scan0001.cbz" in after
    assert sum(1 for it in page.items if it.status == "Ready") == 0, [(it.src.name, it.status) for it in page.items if it.status == "Ready"]
    assert page.bar_btn.cget("state") == "disabled"

    # ---- settings round trip, theme, guide
    s = page.state(); page.restore(s); assert s["t_tpb"] == nf.DEFAULT_TEMPLATES["TPB"] and s["rules"] == "{}" and "view" not in s
    ctk.set_appearance_mode("dark"); page.apply_theme(); root.update()
    page.show_guide(); root.update(); g = page._guide; page.show_guide(); assert page._guide is g and g.winfo_exists(); g.destroy()
    # picking files one by one, and dropping them
    page.set_files([d / "Hellboy 005 (2004).cbz", d / "nothing.txt"]); wait()
    assert [it.src.name for it in page.items] == ["Hellboy 005 (2004).cbz"] and "1 file chosen" in page.drop.label.cget("text")
    page.set_files([d / "nothing.txt"]); assert "None of those" in page.status.cget("text")
    page.add_paths([d]); wait(); assert page.picked is None and len(page.items) > 10
root.destroy()

# =============================== the whole app, with a settings file from the old Renamer
import comic_tool
old = Path(tempfile.mkdtemp()) / "s.json"
old.write_text(json.dumps({"rename": {"style": "Series 001", "custom": "x", "pad": "2 digits (01)", "cstyle": "gone", "vpad": "3 digits (001)",
                                      "view": "List", "rules": 5}, "theme": "light"}))
comic_tool.SETTINGS = old
app = comic_tool.App(); rp = app.pages["rename"]
assert rp.vars["pad"].get() == "2 digits (01)" and rp.vars["vpad"].get() == "3 digits (001)" and rp.vars["t_issue"].get() == nf.DEFAULT_ISSUE
assert rp.rules() == {} and {"library", "recent"} <= set(rp.drop.buttons)
app.show("rename"); app.update(); app.destroy()
print("RENAME PAGE OK")

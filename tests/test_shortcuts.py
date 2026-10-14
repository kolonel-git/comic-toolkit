"""Shared folders (My library, Recent) and the keyboard: Ctrl+K palette, Ctrl+O, Ctrl+Enter, Esc, focusable controls."""
import sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import tkinter as tk
import comic_tool as ct
import ui_kit as uk

def tk_frame_cget(w): return tk.Frame.cget(w, "takefocus")


tmp = Path(tempfile.mkdtemp())
ct.SETTINGS = tmp / "settings.json"  # never touch the real settings
lib, other = tmp / "Library", tmp / "Other"
lib.mkdir(); other.mkdir()
app = ct.App(); app.update()

# every folder a tool opens is remembered, newest first, without duplicates, at most 8
rename = app.pages["rename"]
rename.set_folder(lib); rename.set_folder(other); rename.set_folder(lib)
assert app.recent[:2] == [str(lib), str(other)], app.recent
for i in range(10):
    app.note_folder(tmp / f"f{i}")
assert len(app.recent) == 8
assert app.recent_dirs() == [], "folders that no longer exist are not offered"
app.recent = [str(lib), str(other), str(tmp / "gone")]
assert app.recent_dirs() == [str(lib), str(other)]

# tools with a drop box get My library and Recent next to Add folder; Single issue, Stats, Home do not
for key in ("bulk", "icons", "convert", "rename", "metadata", "audit", "order", "aceo"):
    assert {"library", "recent"} <= set(app.pages[key].drop.buttons), key
assert "library" not in app.pages["single"].drop.buttons

# My library uses the library folder (the one Library stats scans)
app.pages["stats"].set_folder(str(lib), scan=False)
assert app.library_root() == lib
opened = []
app.pages["bulk"].set_folder = lambda p, *a, **k: opened.append(Path(p))
app._open_library(app.pages["bulk"])
assert opened == [lib]

# Ctrl+K search bar: results filter as you type (names first, then descriptions), Enter opens the page
app.show("home"); app.update()
app.open_palette(); app.update()
pal = app._palette
assert len(pal.titles()) >= 12 and len(pal.visible()) == 7, "an empty search lists everything, seven rows at a time"
pal.query.set("renam"); app.update()
assert pal.titles()[0] == "Renamer" and len(pal.visible()) == len(pal.titles())
pal.query.set("zzzz"); app.update()
assert pal.titles() == [] and len(pal.visible()) == 1, "one row explains that nothing matches"
pal.query.set("stats"); app.update()
assert pal.titles()[0] == "Library stats", pal.titles()
pal.query.set("convert"); app.update()   # found through the description of Add to library
assert "Add to library" in pal.titles()
pal.query.set("renam"); app.update()
assert pal.winfo_rootx() > app.winfo_rootx() and pal.winfo_rooty() < app.winfo_rooty() + app.winfo_height() / 2
assert abs((pal.winfo_rootx() + (pal.winfo_width() - 7) / 2) - (app.winfo_rootx() + app.winfo_width() / 2)) < 12, "centred"
pal.go(); app.update()
assert app.current == "rename" and not pal.winfo_exists()
app.open_palette(); app.update(); app.open_palette(); app.update()   # Ctrl+K again closes it
assert not app._palette.winfo_exists()

# Ctrl+1 / Ctrl+2 and the run and stop shortcuts
app.focus_force(); app.update(); app.event_generate("<Control-Key-2>"); app.update()
assert app.current == "stats"
app.event_generate("<Control-Key-1>"); app.update()
assert app.current == "home"

pressed = []
page = app.pages["metadata"]
app.show("metadata"); app.update()
page.btn_apply.configure(command=lambda: pressed.append("run"))
page.btn_apply.configure(state="disabled"); page.primary_action(); assert pressed == []
page.btn_apply.configure(state="normal"); assert page.primary_action() and pressed == ["run"]

# buttons can be reached with Tab and pressed with Enter or Space; the ring shows while focused
b = uk.button(page.footer, "Test", lambda: pressed.append("enter"))
b.pack(); app.update()
assert str(tk_frame_cget(b.slot)) in ("1", "True")
b.slot.event_generate("<FocusIn>"); app.update()
assert b.inner.cget("border_color") == uk.FOCUS
assert tk.Frame.bind(b.slot, "<Return>") and tk.Frame.bind(b.slot, "<space>")  # keys are bound on the frame that takes focus
b._fire(); b._fire(); assert pressed.count("enter") == 2
b.slot.event_generate("<FocusOut>"); app.update()
assert b.inner.cget("border_color") == uk.BORDER

# the switch and the slider take keyboard input
var = ct.ctk.BooleanVar(value=False)
t = uk.Toggle(page.footer, text="x", variable=var); t.pack(); app.update()
assert t.cv.bind("<space>") and t.cv.bind("<Return>"); t.toggle(); app.update()
assert var.get() is True
num = ct.ctk.DoubleVar(value=50)
s = uk.slider(page.footer, from_=0, to=100, number_of_steps=10, variable=num, width=200); s.pack(); app.update()
assert s.bind("<Left>") and s.bind("<Right>")
s._nudge(1); app.update()
assert abs(num.get() - 60) < 1e-6
s._nudge(-1); s._nudge(-1); app.update()
assert abs(num.get() - 40) < 1e-6

# pop-up list (Recent): square rows, a greyed line, Down and Enter, Esc closes
hits = []
pop = uk.popup_menu(app.pages["metadata"].drop.buttons["recent"], [("One", lambda: hits.append(1)), ("Note", None), ("Two", lambda: hits.append(2))])
app.update()
assert len(pop.popup_rows) == 3 and pop.winfo_exists()
pop.event_generate("<Down>"); pop.event_generate("<Down>"); pop.event_generate("<Return>"); app.update()
if not hits:  # key events need real window focus; a click does not
    pop2 = uk.popup_menu(app.pages["metadata"].drop.buttons["recent"], [("One", lambda: hits.append(1))]); app.update()
    pop2.popup_rows[0][0].event_generate("<Button-1>"); app.update()
    assert hits == [1] and not pop2.winfo_exists()
else:
    assert hits == [2] and not pop.winfo_exists()

# menus, segmented controls and text fields show the focus ring too
m = uk.menu(page.footer, ct.ctk.StringVar(value="a"), ["a", "b"]); m.pack(); app.update()
m.slot.event_generate("<FocusIn>"); app.update()
assert m.slot.cget("fg_color") == uk.FOCUS
m.slot.event_generate("<FocusOut>"); app.update()
assert m.slot.cget("fg_color") == uk.INK
sv = ct.ctk.StringVar(value="PNG")
sg = uk.segmented(page.footer, sv, ["Original", "JPG", "PNG", "WebP"]); sg.pack(); app.update()
sg.slot.event_generate("<FocusIn>"); app.update()
assert sg.inner.cget("fg_color") == uk.FOCUS
assert tk.Frame.bind(sg.slot, "<Left>") and tk.Frame.bind(sg.slot, "<Right>")
sg._fire(); assert sv.get() == "WebP"
sg._fire(); assert sv.get() == "Original"
ev = uk.entry(page.footer, ct.ctk.StringVar()); ev.pack(); app.update()
ev.inner._entry.event_generate("<FocusIn>"); app.update()
assert ev.inner.cget("border_color") == uk.FOCUS
ev.inner._entry.event_generate("<FocusOut>"); app.update()
assert ev.inner.cget("border_color") == uk.BORDER

# the library folder can be chosen from Home (and re-scans); the drop box button is named for what it opens
assert app.pages["rename"].drop.buttons["library"].cget("text") == "Library folder"
asked = []
ct.filedialog.askdirectory = lambda **kw: (asked.append(kw), str(other))[1]
scanned = []
app.pages["stats"].scan = lambda: scanned.append(1)
app.choose_library()
assert app.library_root() == other and scanned == [1] and asked[0]["title"] == "Choose your library folder"

# recents are saved on close
app.recent = [str(lib)]
app.close()
import json
assert json.loads(ct.SETTINGS.read_text(encoding="utf-8"))["recent"] == [str(lib)]
print("shortcuts OK")

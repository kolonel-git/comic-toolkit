"""Comic Toolkit: a home screen with cards linking to the tools.

  Comic Cover Extractor
    Single issue  - preview first/last pages, save the cover, convert to ZIP
    Bulk folder   - pull covers from every CBZ/CBR in a folder, organised how you like
    Folder icons  - show each series' cover as its Explorer folder icon
  Comic Renamer
    Renamer       - standardise file names across a folder (ComicInfo.xml aware)
  Metadata
    Metadata      - stamp series/issue/year from filenames into ComicInfo.xml
  Archive Tools
    CBR to CBZ    - repack RAR comics as verified ZIPs
    Clean-up      - strip junk files, normalise page names
  Library Audit
    Library audit - broken files, duplicates, missing issues, quality flags
  Reading Orders
    Reading order - arrange issues in reading order and record it in ComicInfo.xml
  ACEO Cards
    ACEO sheets   - fill pages of 8 ACEO cards with covers and save a PDF

Light and dark mode: toggle in the sidebar; first launch follows Windows.

pip install customtkinter tkinterdnd2 pillow pypdf
CBR support needs 7-Zip, unrar, or Windows 11's built-in tar.exe (reads RAR).
"""
import json
import tkinter as tk
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk
from tkinterdnd2 import DND_FILES, TkinterDnD

from page_aceo import AceoPage
from page_audit import AuditPage
from page_bulk import BulkPage
from page_convert import ConvertPage
from page_icons import IconsPage
from page_intake import IntakePage
from page_metadata import MetadataPage
from page_order import OrderPage
from page_rename import RenamePage
from page_single import SinglePage
from page_stats import StatsPage
from stats_core import snapshot_line
from ui_kit import (Toggle, spotlight, tooltip, ACCENT, BG, BORDER, CYAN, DANGER, WELL, EDGE, FONT, HEAD, HOVER, MUTED, ON_ACCENT, PANEL, PINK,
                    TEXT, YELLOW, AbstractStrip, DropZone, IconTile, Logo, NavItem, Shadow, Splitter, pick, refresh_strips, switch_style,
                    tool_button)
from ui_kit import button  # noqa: F401 - used by strip_button

SETTINGS = Path(__file__).with_name("settings.json")

# (light, dark) tint of the card icon tiles: one soft accent wash for every tool
TINT = ("#F1D9C9", "#4F3626")
TINT_BLUE = TINT_YELLOW = TINT_PURPLE = TINT_GREEN = TINT_PINK = TINT_ORANGE = TINT_GREY = TINT

TOOLS = {  # key -> glyph, tint, title, description
    "single": ("▭", TINT_BLUE, "Single issue",
               "Preview pages, save a cover, or convert one issue to ZIP."),
    "bulk": ("▦", TINT_YELLOW, "Bulk folder",
             "Extract covers from a whole folder, sorted into series folders."),
    "icons": ("▣", TINT_GREEN, "Folder icons",
              "Use each series' cover as its Explorer folder icon."),
    "rename": ("Aa", TINT_PURPLE, "Renamer",
               "Give your collection one consistent name pattern."),
    "metadata": ("{ }", TINT_PINK, "Metadata",
                 "Write series, issue and year from filenames into ComicInfo.xml."),
    "convert": ("⇄", TINT_ORANGE, "CBR to CBZ",
                "Repack RAR comics as verified ZIPs, in bulk."),
    "audit": ("✓", TINT_BLUE, "Library audit",
              "Scan for broken files, duplicates, gaps and junk, then fix them."),
    "order": ("1·2", TINT_PURPLE, "Reading order",
              "Put issues in reading order and record it inside each comic."),
    "aceo": ("▤", TINT_YELLOW, "ACEO sheets",
             "Fill full pages of 8 ACEO cards with covers and save a PDF."),
    "intake": ("＋", TINT_GREEN, "Add to library",
               "Convert, clean and rename new comics into your Ready folder."),
}
GROUPS = [  # header, tool keys
    ("Comic Cover Extractor", ["single", "bulk", "icons"]),
    ("Comic Renamer", ["rename"]),
    ("Metadata", ["metadata"]),
    ("Archive Tools", ["convert"]),
    ("Library Audit", ["audit"]),
    ("Reading Orders", ["order"]),
    ("ACEO Cards", ["aceo"]),
    ("Add to Library", ["intake"]),
]
HOME_COLS, HOME_GAPS = 4, 2  # every row has the same number of card columns and group gaps, so cards line up


def ordered_groups(order):
    """GROUPS in the user's saved order (a list of headers). Unknown headers are ignored; new groups go last."""
    by_header = {h: (h, keys) for h, keys in GROUPS}
    out = [by_header[h] for h in dict.fromkeys(order or []) if h in by_header]
    return out + [g for g in GROUPS if g[0] not in {h for h, _ in out}]


def home_rows(groups):
    """Pack groups into Home rows in order: at most HOME_COLS cards and HOME_GAPS + 1 groups to a row."""
    rows = []
    for g in groups:
        if rows and sum(len(k) for _, k in rows[-1]) + len(g[1]) <= HOME_COLS and len(rows[-1]) <= HOME_GAPS:
            rows[-1].append(g)
        else:
            rows.append([g])
    return rows
GAP = 28  # width of the gap between two groups (a hairline runs down its middle); cards inside a group are 8 apart


class Card(Shadow):
    """A tool card: a white icon tile and the title on one line, a short description under it, an arrow, all on the
    colour of its group. It has a hard shadow; the face slides toward it on hover and sinks into it when pressed."""

    def __init__(self, parent, glyph, color, title, text, command):
        def build(p):
            face = ctk.CTkFrame(p, fg_color=color, border_color=BORDER, border_width=EDGE, corner_radius=0,
                                height=108, cursor="hand2")
            face.pack_propagate(False)
            head = ctk.CTkFrame(face, fg_color="transparent")
            head.pack(fill="x", padx=12, pady=(10, 6))
            IconTile(head, glyph, color).pack(side="left")
            ctk.CTkLabel(head, text=title.upper(), font=(HEAD, 12), text_color=ON_ACCENT,
                         anchor="w").pack(side="left", padx=(10, 0))
            ctk.CTkLabel(head, text="→", font=(FONT, 16, "bold"), text_color=ON_ACCENT).pack(side="right")
            self.desc = ctk.CTkLabel(face, text=text, font=(FONT, 12), text_color="#1A1A1A", anchor="nw",
                                     justify="left", wraplength=170)
            self.desc.pack(fill="x", padx=12)
            return face

        super().__init__(parent, build, depth=6, motion=True)
        self._command = command
        self.make_focusable(lambda: self._command())
        self.inner.bind("<Configure>", lambda e: self.desc.configure(
            wraplength=max(90, int(e.width / self._get_widget_scaling()) - 30)))
        self._bind_click(self.inner)

    def _bind_click(self, w):
        w.bind("<Button-1>", lambda _: self._command(), add="+")
        for c in w.winfo_children():
            self._bind_click(c)


def strip_button(parent, text, command, primary=False, width=None):
    """The larger buttons of the Home summary line: filled accent for the main action, outlined otherwise."""
    b = button(parent, text, command, primary=primary, width=width or 120)
    b.configure(height=44)
    return b


class HomePage(ctk.CTkFrame):
    """Every tool on one screen: each row is a soft band holding one to three groups, separated by hairlines, with the
    tool cards inside (the same width in every row)."""

    def __init__(self, parent, open_tool, open_stats=None, scan=None, choose=None):
        super().__init__(parent, fg_color=BG)
        self.open_stats, self.scan, self.choose = open_stats, scan, choose
        wrap = ctk.CTkFrame(self, fg_color=BG)
        wrap.pack(fill="both", expand=True, padx=(32, 24), pady=(26, 14))
        Shadow(wrap, lambda p: AbstractStrip(p, seed="home", height=72, title="COMIC TOOLKIT",
                                             subtitle="Choose a tool to get started.", fill=YELLOW),
               depth=6).pack(fill="x", padx=(4, 10))
        self._build_summary(wrap)
        self.open_tool = open_tool
        self.bands = ctk.CTkFrame(wrap, fg_color=BG)
        self.bands.pack(fill="x")
        self.set_groups(GROUPS)
        ctk.CTkLabel(wrap, text="Tip: press Ctrl+K to jump to any page. Drop a comic file anywhere to open it in Single "
                                "issue, or a folder onto any folder tool. From Home, a dropped folder opens Bulk folder.", font=(FONT, 12),
                     text_color=MUTED, anchor="w", justify="left", wraplength=800).pack(fill="x", side="bottom")

    def set_groups(self, groups):
        """(Re)build the bands of tool cards, with the groups in this order."""
        open_tool = self.open_tool
        for w in self.bands.winfo_children():
            w.destroy()
        colors, gi = (YELLOW, PINK, CYAN), 0  # one saturated colour per group, rotating
        for ri, row_groups in enumerate(home_rows(groups)):
            band = ctk.CTkFrame(self.bands, fg_color="transparent")
            band.pack(fill="x", pady=(6, 0))
            row = ctk.CTkFrame(band, fg_color="transparent")
            row.pack(fill="x", padx=0, pady=(2, 6))
            col, gaps, cards = 0, 0, 0
            for header, keys in row_groups:
                if col:  # a gap column with a hairline between this group and the one before
                    row.columnconfigure(col, minsize=GAP, weight=0)
                    ctk.CTkFrame(row, width=EDGE, height=1, fg_color=BORDER, corner_radius=0).grid(
                        row=0, column=col, rowspan=2, sticky="ns", pady=2)
                    col, gaps = col + 1, gaps + 1
                start = col
                ctk.CTkLabel(row, text=header.upper(), font=(HEAD, 10), text_color=TEXT, anchor="w").grid(
                    row=0, column=start, columnspan=len(keys), sticky="ew", padx=4, pady=(0, 6))
                color = colors[gi % len(colors)]
                gi += 1
                for key in keys:
                    row.columnconfigure(col, weight=1, uniform=f"cards{ri}")  # equal cards within a row, each row fills its width
                    _glyph, _tint, title, text = TOOLS[key]
                    Card(row, key, color, title, text, lambda k=key: open_tool(k)).grid(
                        row=1, column=col, sticky="ew", padx=(4, 8), pady=(0, 2))  
                    col += 1
                    cards += 1

    # ---- the library summary line (numbers come from the last scan of the Library stats page)
    def _build_summary(self, parent):
        self.strip = Shadow(parent, lambda p: ctk.CTkFrame(p, fg_color=WELL, corner_radius=0, border_color=BORDER,
                                                           border_width=EDGE, height=86), depth=7)
        self.strip.pack(fill="x", padx=(4, 10), pady=(14, 0))
        box = self.strip.inner
        box.pack_propagate(False)
        IconTile(box, "stats", PINK).pack(side="left", padx=(16, 0))
        self.line = ctk.CTkLabel(box, text="", font=(FONT, 18, "bold"), text_color=TEXT, anchor="w")
        self.line.pack(side="left", padx=18)
        self.strip_buttons = ctk.CTkFrame(box, fg_color="transparent")
        self.strip_buttons.pack(side="right", padx=16)
        self.show_summary(None)

    def show_summary(self, snap, scanning=None, error=None, has_root=False):
        """One of four lines: nothing scanned yet, scanning (done, total), the numbers of the last scan, or a failure."""
        for w in self.strip_buttons.winfo_children():
            w.destroy()
        if scanning:
            done, total = scanning
            self.line.configure(text="Scanning your library…" + (f" {done:,} of {total:,}" if total else ""), text_color=TEXT)
            return
        rescan = lambda: self.scan and self.scan()  # noqa: E731
        if error:
            self.line.configure(text=f"The library scan failed: {error}", text_color=DANGER)
            strip_button(self.strip_buttons, "Try again", rescan, primary=True, width=110).pack(side="left")
        elif snap:
            self.line.configure(text=snapshot_line(snap), text_color=TEXT)
            strip_button(self.strip_buttons, "Open Stats", lambda: self.open_stats and self.open_stats(),
                         primary=True, width=140).pack(side="left", padx=(0, 6))
            again = strip_button(self.strip_buttons, "↻", rescan, width=34)
            again.pack(side="left", padx=(0, 6))
            tooltip(again, "Scan the library again")
            folder = strip_button(self.strip_buttons, "Library folder…", lambda: self.choose and self.choose(), width=140)
            folder.pack(side="left")
            tooltip(folder, "Choose which folder is your library")
        else:
            self.line.configure(text="No library scanned yet.", text_color=MUTED)
            strip_button(self.strip_buttons, "Scan your library" if has_root else "Choose your library folder and scan it",
                         rescan, primary=True, width=150 if has_root else 270).pack(side="left")


class App(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self):
        super().__init__()
        self.TkdndVersion = TkinterDnD._require(self)
        saved = self._load_settings()
        order, shut = saved.get("group_order"), saved.get("collapsed")
        self.group_order = [h for h in order if isinstance(h, str)] if isinstance(order, list) else []
        self.collapsed = {h for h in shut if isinstance(h, str)} if isinstance(shut, list) else set()
        recent = saved.get("recent")
        self.recent = [p for p in recent if isinstance(p, str)][:8] if isinstance(recent, list) else []
        self.theme = saved.get("theme", "system")  # light | dark | system
        ctk.set_appearance_mode(self.theme)
        self.title("Comic Toolkit")
        self.geometry("1200x780")
        self.minsize(1040, 720)
        self.configure(fg_color=BG)

        side = ctk.CTkFrame(self, fg_color=PANEL, width=190, corner_radius=0)
        side.pack(side="left", fill="y")  # the splitter beside it is the rail's thick black border
        side.pack_propagate(False)
        self.sidebar_width = 190
        self.splitter = Splitter(self, side, side="left", lo=150, hi=360, on_change=self._sidebar_changed)
        self.splitter.pack(side="left", fill="y")
        if isinstance(saved.get("sidebar"), (int, float)):
            self.splitter.set_width(saved["sidebar"])
        content = ctk.CTkFrame(self, fg_color=BG)
        content.pack(side="left", fill="both", expand=True)

        self.pages = {"home": HomePage(content, self.show, lambda: self.show("stats"), self.home_scan, self.choose_library),
                      "stats": StatsPage(content), "single": SinglePage(content),
                      "bulk": BulkPage(content), "icons": IconsPage(content),
                      "rename": RenamePage(content), "metadata": MetadataPage(content),
                      "convert": ConvertPage(content),
                      "audit": AuditPage(content), "order": OrderPage(content),
                      "aceo": AceoPage(content), "intake": IntakePage(content)}
        self.pages["intake"].rename_source = self.pages["rename"].state  # names follow the Renamer's settings
        self.nav = {}
        self.current = None
        Logo(side, lambda: self.show("home")).pack(fill="x", padx=(12, 8), pady=(14, 8))
        self._nav_item(side, "home", "Home", big=True)
        self._nav_item(side, "stats", "Library stats", big=True)
        ctk.CTkFrame(side, height=EDGE, fg_color=BORDER, corner_radius=0).pack(fill="x", padx=12, pady=(14, 0))
        ctk.CTkLabel(side, text="TOOLS", font=(HEAD, 10), text_color=MUTED, anchor="w").pack(fill="x", padx=14, pady=(8, 0))

        bottom = ctk.CTkFrame(side, fg_color=PANEL)  # pinned under the scrolling list
        bottom.pack(side="bottom", fill="x")
        self.dark = ctk.BooleanVar(value=ctk.get_appearance_mode() == "Dark")
        Toggle(bottom, text="Dark mode", variable=self.dark, command=self.toggle_theme,
                      **switch_style()).pack(side="bottom", anchor="w", padx=18, pady=(8, 20))
        ctk.CTkLabel(bottom, text="Ctrl+K  jump to a tool", font=(FONT, 11), text_color=MUTED,
                     anchor="w").pack(side="bottom", fill="x", padx=18, pady=(0, 10))
        tool_button(bottom, "Reorder sections…", self.reorder_dialog).pack(side="bottom", fill="x", padx=(14, 18), pady=(10, 0))
        self.nav_scroll = ctk.CTkScrollableFrame(side, fg_color=PANEL, corner_radius=0)
        self.nav_scroll.pack(fill="both", expand=True)
        self._build_nav()
        self.pages["home"].set_groups(ordered_groups(self.group_order))

        for k, page in self.pages.items():
            if hasattr(page, "restore"):
                page.restore(saved.get(k))
        self._wire_folders()
        for seq, fn in (("<Control-k>", self.open_palette), ("<Control-Key-1>", lambda: self.show("home")),
                        ("<Control-Key-2>", lambda: self.show("stats")), ("<Control-o>", self._shortcut_add),
                        ("<Control-Return>", self._shortcut_run), ("<Escape>", self._shortcut_stop)):
            self.bind_all(seq, lambda _, fn=fn: fn())
        snap = saved.get("stats_snapshot")
        self.snapshot = snap if isinstance(snap, dict) and {"comics", "series", "bytes", "when"} <= set(snap) else None
        stats = self.pages["stats"]
        stats.on_progress = lambda d, t: self.pages["home"].show_summary(None, scanning=(d, t))
        stats.on_scanned = self._scanned
        stats.on_error = lambda e: self.pages["home"].show_summary(None, error=e)
        self.current = None
        self.show("home")
        self._home_summary()

        self.drop_target_register(DND_FILES)
        self.dnd_bind("<<Drop>>", self.on_drop)
        self.protocol("WM_DELETE_WINDOW", self.close)

    # ---- folders: one library folder and the recent ones, shared by every tool
    def library_root(self):
        return self.pages["stats"].root()

    def note_folder(self, folder):
        p = str(Path(folder))
        self.recent = [p] + [q for q in self.recent if q != p]
        self.recent = self.recent[:8]

    def recent_dirs(self):
        return [p for p in self.recent if Path(p).is_dir()]

    def _open_path(self, page, path):
        if hasattr(page, "set_folder"):
            page.set_folder(path)
        else:
            page.add_paths([Path(path)])

    def _open_library(self, page):
        root = self.library_root()
        if root is None:  # first use: ask once, then every tool can use it
            folder = filedialog.askdirectory(title="Choose your library folder")
            if not folder:
                return
            self.pages["stats"].set_folder(folder, scan=False)
            root = Path(folder)
        self._open_path(page, root)

    def _wire_folders(self):
        """Every folder a tool opens is remembered; tools with a drop box get My library and Recent buttons."""
        for key, page in self.pages.items():
            if key != "home" and hasattr(page, "set_folder"):
                orig = page.set_folder

                def wrapped(folder, *a, _orig=orig, **k):
                    self.note_folder(folder)
                    return _orig(folder, *a, **k)
                page.set_folder = wrapped
            drop = getattr(page, "drop", None)
            if key not in ("home", "stats", "single", "intake") and isinstance(drop, DropZone):
                drop.add_shortcuts(lambda p=page: self._open_library(p), self.recent_dirs,
                                   lambda path, p=page: self._open_path(p, path))

    # ---- keyboard
    def _shortcut_add(self):
        drop = getattr(self.pages[self.current], "drop", None)
        if isinstance(drop, DropZone) and drop.buttons:
            next(iter(drop.buttons.values())).invoke()

    def _shortcut_run(self):
        page = self.pages[self.current]
        if hasattr(page, "primary_action"):
            page.primary_action()

    def _shortcut_stop(self):
        page = self.pages[self.current]
        if hasattr(page, "stop_action"):
            page.stop_action()

    def open_palette(self):
        """Ctrl+K: a floating search bar; type a few letters of a page or action and press Enter."""
        old = getattr(self, "_palette", None)
        if old is not None and old.winfo_exists():
            old.destroy()
            return
        entries = [("home", "Home", "Every tool on one screen", "Page"),
                   ("stats", "Library stats", "Numbers about your whole collection", "Page")]
        entries += [(k, TOOLS[k][2], TOOLS[k][3], "Page") for _, keys in ordered_groups(self.group_order) for k in keys]
        entries += [("__theme__", "Switch light and dark mode", "Change the look of the whole app", "Action"),
                    ("__library__", "Choose the library folder", "The folder Library stats scans and every tool offers", "Action")]

        def pick_it(key):
            if key == "__theme__":
                self.dark.set(not self.dark.get())
                self.toggle_theme()
            elif key == "__library__":
                self.choose_library()
            else:
                self.show(key)
        self._palette = spotlight(self, entries, pick_it)

    def _sidebar_changed(self, width):
        self.sidebar_width = width

    def _home_summary(self):
        self.pages["home"].show_summary(self.snapshot, has_root=self.pages["stats"].root() is not None)

    def _scanned(self, snap):
        if snap:  # None: the scan was stopped, so the old numbers stay
            self.snapshot = snap
        self._home_summary()

    def home_scan(self):
        """Home's scan button: ask for the library folder the first time, then rescan the saved one."""
        stats = self.pages["stats"]
        if stats.q:
            return
        if stats.root() is None:
            folder = filedialog.askdirectory(title="Choose your library folder")
            if not folder:
                return
            stats.set_folder(folder)
        else:
            stats.scan()
        if stats.q:
            self.pages["home"].show_summary(None, scanning=(0, 0))

    def choose_library(self):
        """Pick the library folder (the one Library stats scans and every tool's Library folder button opens)."""
        stats = self.pages["stats"]
        if stats.q:
            return
        folder = filedialog.askdirectory(title="Choose your library folder",
                                         initialdir=str(stats.root()) if stats.root() else None)
        if folder:
            stats.set_folder(folder)
            if stats.q:
                self.pages["home"].show_summary(None, scanning=(0, 0))

    def _nav_item(self, parent, key, label, big=False):
        b = NavItem(parent, key, label, lambda: self.show(key), big=big, active_color=ACCENT if big else PINK)
        b.pack(fill="x", padx=(10, 14), pady=(6, 4) if big else 2)
        self.nav[key] = b

    def _build_nav(self):
        """The scrolling list of tool groups, in the saved order; a group's heading folds and unfolds it."""
        for w in self.nav_scroll.winfo_children():
            w.destroy()
        for k in [k for k in self.nav if k not in ("home", "stats")]:
            del self.nav[k]
        self.group_heads = {}
        for header, keys in ordered_groups(self.group_order):
            shut = header in self.collapsed
            arrow = "▸" if shut else "▾"
            head = ctk.CTkButton(self.nav_scroll, text=f"{arrow}  {header.upper()}", anchor="w", height=26,
                                 corner_radius=0, font=(FONT, 11, "bold"), fg_color="transparent", hover_color=HOVER,
                                 text_color=MUTED, command=lambda h=header: self.toggle_group(h))
            head.pack(fill="x", padx=10, pady=(12, 2))
            self.group_heads[header] = head
            if not shut:
                for key in keys:
                    self._nav_item(self.nav_scroll, key, TOOLS[key][2])
        self._mark_current()

    def toggle_group(self, header):
        self.collapsed ^= {header}
        self._build_nav()

    def set_group_order(self, order):
        """Use this order of group headings in the sidebar and on Home."""
        self.group_order = list(order)
        self._build_nav()
        self.pages["home"].set_groups(ordered_groups(self.group_order))

    def move_group(self, header, delta):
        order = [h for h, _ in ordered_groups(self.group_order)]
        i = order.index(header)
        if 0 <= i + delta < len(order):
            order[i], order[i + delta] = order[i + delta], order[i]
            self.set_group_order(order)

    def reorder_dialog(self):
        """A small window to move the groups up and down; the sidebar and Home follow as you go."""
        win = ctk.CTkToplevel(self)
        win.title("Reorder sections")
        win.geometry("340x430")
        win.configure(fg_color=BG)
        win.transient(self)
        ctk.CTkLabel(win, text="Order of the headings in the sidebar and on Home.", font=(FONT, 12), text_color=MUTED,
                     anchor="w").pack(fill="x", padx=14, pady=(12, 6))
        box = tk.Listbox(win, activestyle="none", exportselection=False, font=(FONT, 12), bd=0, highlightthickness=1,
                         bg=pick(BG), fg=pick(TEXT), selectbackground=pick(ACCENT), highlightbackground=pick(BORDER))
        box.pack(fill="both", expand=True, padx=14)

        def fill(sel=None):
            box.delete(0, "end")
            for h, _ in ordered_groups(self.group_order):
                box.insert("end", h)
            if sel is not None:
                box.selection_set(sel)
                box.see(sel)

        def shift(d):
            cur = box.curselection()
            if cur:
                self.move_group(box.get(cur[0]), d)
                fill(max(0, min(box.size() - 1, cur[0] + d)))

        def reset():
            self.set_group_order([])
            fill()

        row = ctk.CTkFrame(win, fg_color=BG)
        row.pack(fill="x", padx=14, pady=10)
        for text, fn, w in (("Up", lambda: shift(-1), 60), ("Down", lambda: shift(1), 70), ("Reset", reset, 70)):
            tool_button(row, text, fn, w).pack(side="left", padx=(0, 6))
        tool_button(row, "Done", win.destroy, 70).pack(side="right")
        fill()
        self._reorder_win = win
        self._reorder_ui = {"box": box, "shift": shift, "reset": reset}

    def toggle_theme(self):
        self.theme = "dark" if self.dark.get() else "light"
        ctk.set_appearance_mode(self.theme)
        refresh_strips()
        for page in self.pages.values():
            if hasattr(page, "apply_theme"):
                page.apply_theme()

    def show(self, key):
        if self.current:
            self.pages[self.current].pack_forget()
        self.current = key
        self.pages[key].pack(fill="both", expand=True)
        if hasattr(self.pages[key], "on_show"):
            self.pages[key].on_show()
        self._mark_current()

    def _mark_current(self):
        for k, b in self.nav.items():
            b.set_active(k == self.current)  # the open page: a coloured block with a border and a hard shadow

    def on_drop(self, event):
        files = self.tk.splitlist(event.data)
        if not files:
            return
        page = self.pages[self.current]
        if hasattr(page, "add_paths"):  # pages that take several files or folders at once
            page.add_paths([Path(f) for f in files])
            return
        p = Path(files[0])
        if p.is_dir():
            key = self.current if hasattr(self.pages[self.current], "set_folder") else "bulk"
            self.show(key)
            self.pages[key].set_folder(p)
        else:
            self.show("single")
            self.pages["single"].load(p)

    def _load_settings(self):
        try:
            return json.loads(SETTINGS.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def close(self):
        data = {k: p.state() for k, p in self.pages.items() if hasattr(p, "state")}
        data["theme"] = self.theme
        data["recent"] = self.recent
        data["sidebar"] = self.sidebar_width
        data["group_order"] = self.group_order
        data["collapsed"] = sorted(self.collapsed)
        data["stats_snapshot"] = self.snapshot
        try:
            SETTINGS.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except OSError:
            pass
        self.destroy()


if __name__ == "__main__":
    App().mainloop()

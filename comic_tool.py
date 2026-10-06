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

Light and dark mode: toggle in the sidebar; first launch follows Windows.

pip install customtkinter tkinterdnd2 pillow
CBR support needs 7-Zip, unrar, or Windows 11's built-in tar.exe (reads RAR).
"""
import json
from pathlib import Path

import customtkinter as ctk
from tkinterdnd2 import DND_FILES, TkinterDnD

from page_audit import AuditPage
from page_bulk import BulkPage
from page_cleanup import CleanupPage
from page_convert import ConvertPage
from page_icons import IconsPage
from page_metadata import MetadataPage
from page_rename import RenamePage
from page_single import SinglePage
from ui_kit import ACCENT, BG, BORDER, FONT, HOVER, MUTED, PANEL, TEXT

SETTINGS = Path(__file__).with_name("settings.json")

# (light, dark) tints for the card icon tiles
TINT_BLUE, TINT_YELLOW, TINT_PURPLE = ("#E7F3F8", "#1F3138"), ("#FBF3DB", "#3A3322"), ("#EAE4F2", "#2E2740")
TINT_GREEN, TINT_PINK = ("#E4F1EA", "#1F3228"), ("#F8E8EE", "#3A2430")
TINT_ORANGE, TINT_GREY = ("#FBEBDD", "#3A2B1F"), ("#EDECE9", "#2C2C2B")

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
    "cleanup": ("✂", TINT_GREY, "Clean-up",
                "Remove junk files and tidy page names in CBZ archives."),
    "audit": ("✓", TINT_BLUE, "Library audit",
              "Find broken files, duplicates, missing issues and low quality."),
}
GROUPS = [  # header, blurb, tool keys
    ("Comic Cover Extractor", "Pull cover images out of CBZ and CBR files.", ["single", "bulk", "icons"]),
    ("Comic Renamer", "Keep file names consistent across your collection.", ["rename"]),
    ("Metadata", "Fix the information stored inside your comics.", ["metadata"]),
    ("Archive Tools", "Repack and tidy the archives themselves.", ["convert", "cleanup"]),
    ("Library Audit", "Check the whole collection for problems.", ["audit"]),
]


class Card(ctk.CTkFrame):
    def __init__(self, parent, glyph, tint, title, text, command):
        super().__init__(parent, fg_color=BG, border_color=BORDER, border_width=1, corner_radius=10,
                         height=138, cursor="hand2")
        self.pack_propagate(False)
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x", padx=18, pady=(16, 8))
        tile = ctk.CTkFrame(head, width=36, height=36, fg_color=tint, corner_radius=8)
        tile.pack(side="left")
        tile.pack_propagate(False)
        ctk.CTkLabel(tile, text=glyph, font=(FONT, 15, "bold"), text_color=TEXT).pack(expand=True)
        ctk.CTkLabel(head, text=title, font=(FONT, 16, "bold"), text_color=TEXT,
                     anchor="w").pack(side="left", padx=(12, 0))
        ctk.CTkLabel(self, text=text, font=(FONT, 13), text_color=MUTED, anchor="nw", justify="left",
                     wraplength=250).pack(fill="x", padx=18)
        ctk.CTkLabel(self, text="Open  →", font=(FONT, 13), text_color=ACCENT,
                     anchor="w").pack(side="bottom", fill="x", padx=18, pady=(0, 12))
        self._command = command
        self._bind_all(self)

    def _bind_all(self, w):
        w.bind("<Button-1>", lambda _: self._command(), add="+")
        w.bind("<Enter>", lambda _: self.configure(fg_color=PANEL, border_color=ACCENT), add="+")
        w.bind("<Leave>", self._leave, add="+")
        for c in w.winfo_children():
            self._bind_all(c)

    def _leave(self, _):
        under = self.winfo_containing(*self.winfo_pointerxy())
        while under is not None:  # moving onto a child of this card is not leaving it
            if under is self:
                return
            under = under.master
        self.configure(fg_color=BG, border_color=BORDER)


class HomePage(ctk.CTkFrame):
    def __init__(self, parent, open_tool):
        super().__init__(parent, fg_color=BG)
        wrap = ctk.CTkScrollableFrame(self, fg_color=BG, scrollbar_button_color=BORDER,
                                      scrollbar_button_hover_color=MUTED)
        wrap.pack(fill="both", expand=True, padx=(40, 24), pady=(30, 20))
        self.scroller = wrap
        ctk.CTkLabel(wrap, text="Comic Toolkit", font=(FONT, 32, "bold"), text_color=TEXT,
                     anchor="w").pack(fill="x")
        ctk.CTkLabel(wrap, text="Choose a tool to get started.", font=(FONT, 15), text_color=MUTED,
                     anchor="w").pack(fill="x", pady=(4, 8))
        for header, blurb, keys in GROUPS:
            ctk.CTkLabel(wrap, text=header, font=(FONT, 18, "bold"), text_color=TEXT,
                         anchor="w").pack(fill="x", pady=(22, 0))
            ctk.CTkLabel(wrap, text=blurb, font=(FONT, 13), text_color=MUTED,
                         anchor="w").pack(fill="x", pady=(2, 10))
            grid = ctk.CTkFrame(wrap, fg_color=BG)
            grid.pack(fill="x")
            for i in range(3):  # same card width in every group
                grid.columnconfigure(i, weight=1, uniform="cards")
            for i, key in enumerate(keys):
                glyph, tint, title, text = TOOLS[key]
                Card(grid, glyph, tint, title, text, lambda k=key: open_tool(k)).grid(
                    row=0, column=i, sticky="ew", padx=(0 if i == 0 else 8, 8))
        ctk.CTkLabel(wrap, text="Tip: drop a comic file anywhere to open it in Single issue, or a folder onto any "
                                "folder tool. From Home, a dropped folder opens Bulk folder.", font=(FONT, 13), text_color=MUTED,
                     anchor="w").pack(fill="x", pady=(30, 0))


class App(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self):
        super().__init__()
        self.TkdndVersion = TkinterDnD._require(self)
        saved = self._load_settings()
        self.theme = saved.get("theme", "system")  # light | dark | system
        ctk.set_appearance_mode(self.theme)
        self.title("Comic Toolkit")
        self.geometry("1200x780")
        self.minsize(1040, 720)
        self.configure(fg_color=BG)

        side = ctk.CTkFrame(self, fg_color=PANEL, width=190, corner_radius=0)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        ctk.CTkFrame(self, width=1, fg_color=BORDER, corner_radius=0).pack(side="left", fill="y")
        content = ctk.CTkFrame(self, fg_color=BG)
        content.pack(side="left", fill="both", expand=True)

        self.pages = {"home": HomePage(content, self.show), "single": SinglePage(content),
                      "bulk": BulkPage(content), "icons": IconsPage(content),
                      "rename": RenamePage(content), "metadata": MetadataPage(content),
                      "convert": ConvertPage(content), "cleanup": CleanupPage(content),
                      "audit": AuditPage(content)}
        self.nav = {}
        ctk.CTkLabel(side, text="Comic Toolkit", font=(FONT, 15, "bold"), text_color=TEXT,
                     anchor="w").pack(fill="x", padx=18, pady=(24, 14))
        self._nav_item(side, "home", "Home")
        for header, _, keys in GROUPS:
            ctk.CTkLabel(side, text=header.upper(), font=(FONT, 11, "bold"), text_color=MUTED,
                         anchor="w").pack(fill="x", padx=18, pady=(14, 4))
            for key in keys:
                self._nav_item(side, key, TOOLS[key][2])

        self.dark = ctk.BooleanVar(value=ctk.get_appearance_mode() == "Dark")
        ctk.CTkSwitch(side, text="Dark mode", variable=self.dark, command=self.toggle_theme,
                      font=(FONT, 13), text_color=TEXT, progress_color=ACCENT,
                      fg_color=("#CFCDC7", "#4A4A4A"), button_color="#FFFFFF",
                      button_hover_color="#F4F4F4").pack(side="bottom", anchor="w", padx=18, pady=20)

        for k, page in self.pages.items():
            if hasattr(page, "restore"):
                page.restore(saved.get(k))
        self.current = None
        self.show("home")

        self.drop_target_register(DND_FILES)
        self.dnd_bind("<<Drop>>", self.on_drop)
        self.protocol("WM_DELETE_WINDOW", self.close)

    def _nav_item(self, parent, key, label):
        b = ctk.CTkButton(parent, text=label, anchor="w", height=34, corner_radius=6, font=(FONT, 13),
                          fg_color="transparent", hover_color=HOVER, text_color=TEXT,
                          command=lambda: self.show(key))
        b.pack(fill="x", padx=10, pady=1)
        self.nav[key] = b

    def toggle_theme(self):
        self.theme = "dark" if self.dark.get() else "light"
        ctk.set_appearance_mode(self.theme)
        for page in self.pages.values():
            if hasattr(page, "apply_theme"):
                page.apply_theme()

    def show(self, key):
        if self.current:
            self.pages[self.current].pack_forget()
        self.current = key
        self.pages[key].pack(fill="both", expand=True)
        if key == "home":
            self.pages["home"].scroller._parent_canvas.yview_moveto(0)
        for k, b in self.nav.items():
            b.configure(fg_color=BORDER if k == key else "transparent")

    def on_drop(self, event):
        files = self.tk.splitlist(event.data)
        if not files:
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
        try:
            SETTINGS.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except OSError:
            pass
        self.destroy()


if __name__ == "__main__":
    App().mainloop()

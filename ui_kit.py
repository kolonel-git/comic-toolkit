"""Shared look and widgets: palette, styled controls, form rows, drop zone, page scaffold."""
from tkinter import filedialog, ttk

import customtkinter as ctk

from comic_core import FORMATS, HEIGHTS

# Notion-ish palette. Each colour is (light, dark): customtkinter swaps them when the mode changes.
BG = ("#FFFFFF", "#191919")
PANEL = ("#F7F6F3", "#202020")
BORDER = ("#E9E9E7", "#2F2F2F")
HOVER = ("#EFEFED", "#2B2B2B")
TEXT = ("#37352F", "#E6E6E4")
MUTED = ("#9B9A97", "#8B8B88")
ACCENT = ("#2383E2", "#2F8BEA")
ACCENT_HOVER = ("#1B6EC2", "#2478CC")
DANGER = ("#E03E3E", "#EB5757")
SEG_ON = ("#FFFFFF", "#3A3A3A")        # selected segment
SWITCH_OFF = ("#CFCDC7", "#4A4A4A")
SELECT_BG = ("#E8F0FE", "#26364D")     # selected table row
FONT = "Segoe UI"


def pick(color):
    """Resolve a (light, dark) pair for widgets that don't understand tuples (ttk, tk)."""
    return color[1] if ctk.get_appearance_mode() == "Dark" else color[0]


def switch_style():
    return dict(font=(FONT, 13), text_color=TEXT, progress_color=ACCENT, fg_color=SWITCH_OFF,
                button_color="#FFFFFF", button_hover_color="#F4F4F4")


# ---------- small styled widgets ----------

def button(parent, text, command, primary=False, width=260):
    return ctk.CTkButton(
        parent, text=text, command=command, width=width, height=36, corner_radius=6,
        font=(FONT, 13, "bold" if primary else "normal"),
        fg_color=ACCENT if primary else BG, hover_color=ACCENT_HOVER if primary else HOVER,
        text_color="#FFFFFF" if primary else TEXT, text_color_disabled=MUTED,
        border_width=0 if primary else 1, border_color=BORDER)


def menu(parent, var, values, width=260):
    return ctk.CTkOptionMenu(
        parent, variable=var, values=values, width=width, height=32, corner_radius=6, anchor="w",
        font=(FONT, 13), dropdown_font=(FONT, 13), fg_color=BG, button_color=BG,
        button_hover_color=HOVER, text_color=TEXT, dropdown_fg_color=BG,
        dropdown_text_color=TEXT, dropdown_hover_color=PANEL)


def segmented(parent, var, values, width=260):
    return ctk.CTkSegmentedButton(
        parent, variable=var, values=values, width=width, height=30, corner_radius=6,
        font=(FONT, 12), fg_color=BORDER, unselected_color=BORDER, unselected_hover_color=HOVER,
        selected_color=SEG_ON, selected_hover_color=SEG_ON, text_color=TEXT)


def entry(parent, var, **kw):
    return ctk.CTkEntry(parent, textvariable=var, height=32, corner_radius=6, font=(FONT, 13),
                        fg_color=BG, border_color=BORDER, border_width=1, text_color=TEXT, **kw)


class Form(ctk.CTkScrollableFrame):
    """Stacked label-over-control rows. Rows can be hidden and shown."""

    def __init__(self, parent):
        super().__init__(parent, fg_color=PANEL, corner_radius=0,
                         scrollbar_button_color=BORDER, scrollbar_button_hover_color=MUTED)
        self.grid_columnconfigure(0, weight=1)
        self._row = 0

    def add(self, text):
        lbl = ctk.CTkLabel(self, text=text, font=(FONT, 12), text_color=MUTED, anchor="w")
        lbl.grid(row=self._row, column=0, sticky="ew", pady=(14, 4))
        cell = ctk.CTkFrame(self, fg_color=PANEL)
        cell.grid(row=self._row + 1, column=0, sticky="ew")
        cell.label = lbl
        self._row += 2
        return cell

    def heading(self, text):
        """A bold group title with a rule under it. Hide and show it like any other row."""
        box = ctk.CTkFrame(self, fg_color=PANEL)
        box.grid(row=self._row, column=0, sticky="ew", pady=(20, 0))
        ctk.CTkLabel(box, text=text, font=(FONT, 13, "bold"), text_color=TEXT, anchor="w").pack(fill="x")
        ctk.CTkFrame(box, height=1, fg_color=BORDER, corner_radius=0).pack(fill="x", pady=(4, 0))
        box.label = box
        self._row += 1
        return box

    @staticmethod
    def show(cell, on):
        for w in (cell.label, cell):
            w.grid() if on else w.grid_remove()


class DropZone(ctk.CTkFrame):
    def __init__(self, parent, prompt, on_click):
        super().__init__(parent, fg_color=PANEL, border_color=BORDER, border_width=1,
                         corner_radius=8, height=84)
        self.pack_propagate(False)
        self.prompt = prompt
        self.label = ctk.CTkLabel(self, text=prompt, font=(FONT, 14), text_color=MUTED)
        self.label.pack(expand=True)
        for w in (self, self.label):
            w.bind("<Button-1>", lambda _: on_click())
            w.bind("<Enter>", lambda _: self.configure(border_color=ACCENT))
            w.bind("<Leave>", lambda _: self.configure(border_color=BORDER))

    def set(self, text=None):
        self.label.configure(text=text or self.prompt, text_color=TEXT if text else MUTED)


def title_block(parent, title, subtitle):
    ctk.CTkLabel(parent, text=title, font=(FONT, 26, "bold"), text_color=TEXT, anchor="w").pack(fill="x")
    ctk.CTkLabel(parent, text=subtitle, font=(FONT, 13), text_color=MUTED,
                 anchor="w").pack(fill="x", pady=(2, 16))


class Page(ctk.CTkFrame):
    """Left: main area. Right: options inspector with a pinned footer."""
    defaults = {}
    choices = {}

    def __init__(self, parent):
        super().__init__(parent, fg_color=BG)
        self.vars = {}
        for k, v in self.defaults.items():
            self.vars[k] = ctk.BooleanVar(value=v) if isinstance(v, bool) else \
                ctk.DoubleVar(value=v) if isinstance(v, (int, float)) else ctk.StringVar(value=v)

        side = ctk.CTkFrame(self, fg_color=PANEL, width=310, corner_radius=0)
        side.pack(side="right", fill="y")
        side.pack_propagate(False)
        ctk.CTkFrame(self, width=1, fg_color=BORDER, corner_radius=0).pack(side="right", fill="y")
        self.footer = ctk.CTkFrame(side, fg_color=PANEL)
        self.footer.pack(side="bottom", fill="x", padx=20, pady=(8, 20))
        self.form = Form(side)
        self.form.pack(fill="both", expand=True, padx=(8, 0), pady=(14, 0))
        self.main = ctk.CTkFrame(self, fg_color=BG)
        self.main.pack(side="left", fill="both", expand=True, padx=(36, 28), pady=32)

        self.status = ctk.CTkLabel(self.footer, text="", font=(FONT, 12), text_color=MUTED,
                                   anchor="w", justify="left", wraplength=260)
        self.status.pack(fill="x", pady=(0, 8))

    def say(self, msg, err=False):
        self.status.configure(text=msg, text_color=DANGER if err else MUTED)

    def watch(self, *names, callback):
        for n in names:
            self.vars[n].trace_add("write", lambda *_: callback())

    def state(self):
        out = {}
        for k, v in self.vars.items():
            out[k] = v.get()
        return out

    def restore(self, saved):
        for k, v in (saved or {}).items():
            if k in self.vars and (k not in self.choices or v in self.choices[k]):
                try:
                    self.vars[k].set(v)
                except (ValueError, TypeError):
                    pass

    # shared option rows -------------------------------------------------
    def add_image_rows(self):
        v = self.vars
        segmented(self.form.add("Image format"), v["format"], FORMATS).pack(fill="x")
        q = self.form.add("Quality")
        ctk.CTkSlider(q, from_=50, to=100, number_of_steps=50, variable=v["quality"], width=200,
                      button_color=ACCENT, button_hover_color=ACCENT_HOVER, progress_color=ACCENT,
                      fg_color=BORDER).pack(side="left")
        qval = ctk.CTkLabel(q, text="", font=(FONT, 12), text_color=TEXT, width=40)
        qval.pack(side="left", padx=(8, 0))
        v["quality"].trace_add("write", lambda *_: qval.configure(text=str(int(v["quality"].get()))))
        qval.configure(text=str(int(v["quality"].get())))
        self.quality_row = q
        menu(self.form.add("Size"), v["height"], list(HEIGHTS)).pack(fill="x")

    def refresh_quality(self):
        Form.show(self.quality_row, self.vars["format"].get() in ("JPG", "WebP"))

    def pick_folder(self, var, title):
        d = filedialog.askdirectory(title=title)
        if d:
            var.set(d)

    def path_row(self, cell, var, title):
        entry(cell, var).pack(side="left", fill="x", expand=True)
        b = button(cell, "Browse", lambda: self.pick_folder(var, title), width=72)
        b.configure(height=32)
        b.pack(side="left", padx=(6, 0))


# ---------- tables ----------

TREE_STYLE = "Comics.Treeview"


def build_tree(parent, columns, selectmode="browse"):
    """Bordered ttk table with a themed scrollbar. columns: (id, heading, width, stretch)."""
    st = ttk.Style()
    st.theme_use("clam")
    st.layout(TREE_STYLE, [("Treeview.treearea", {"sticky": "nswe"})])
    wrap = ctk.CTkFrame(parent, fg_color=BG, border_color=BORDER, border_width=1, corner_radius=8)
    tree = ttk.Treeview(wrap, style=TREE_STYLE, show="headings", selectmode=selectmode,
                        columns=[c[0] for c in columns])
    for col, text, w, stretch in columns:
        tree.heading(col, text=text, anchor="w")
        tree.column(col, width=w, minwidth=w if not stretch else 60, stretch=stretch, anchor="w")
    sb = ctk.CTkScrollbar(wrap, command=tree.yview, button_color=BORDER, button_hover_color=MUTED)
    tree.configure(yscrollcommand=sb.set)
    sb.pack(side="right", fill="y", padx=(0, 2), pady=4)
    tree.pack(side="left", fill="both", expand=True, padx=4, pady=4)
    apply_tree_theme(tree)
    return wrap, tree


def apply_tree_theme(tree):
    """ttk widgets don't follow customtkinter's mode, so restyle them by hand."""
    st = ttk.Style()
    st.configure(TREE_STYLE, background=pick(BG), fieldbackground=pick(BG), foreground=pick(TEXT),
                 rowheight=30, borderwidth=0, font=(FONT, 11))
    st.configure(TREE_STYLE + ".Heading", background=pick(PANEL), foreground=pick(MUTED), relief="flat",
                 font=(FONT, 10, "bold"), padding=(8, 6))
    st.map(TREE_STYLE, background=[("selected", pick(SELECT_BG))], foreground=[("selected", pick(TEXT))])
    tree.tag_configure("bad", foreground=pick(DANGER))
    tree.tag_configure("dim", foreground=pick(MUTED))

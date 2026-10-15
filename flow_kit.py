"""The shared page shell: a Header, a column of collapsible Segments, and a Footer that holds the main action.

    SegmentPage  the page: header (title, one line of purpose), segments, pinned footer; keeps the small interface the
                 rest of the app expects of a page (vars, state, restore, watch, say, primary_action)
    Segment      one titled section. Finished sections fold to a one-line summary; click the title to open or close
    Advanced     a bordered, collapsed block of rarely needed settings inside a segment, with a count of changed ones
    LazyTable    a scrollable, filterable table that loads rows as you scroll, with optional small pictures per row
    ChoiceCards  pick one of a few options by clicking a card

Built on the widgets of ui_kit; the type scale (TYPE_SEGMENT, TYPE_BODY, TYPE_HINT) lives there."""
import queue
import threading
import tkinter as tk
from tkinter import filedialog

import customtkinter as ctk

from comic_core import FORMATS, HEIGHTS
from ui_kit import (ACCENT, BG, BORDER, CYAN, DANGER, EDGE, FOCUS, FONT, HEAD, HOVER, MUTED, ON_ACCENT, PANEL, PINK, RAISED,
                    SCROLL, SWITCH_OFF, TEXT, TYPE_BODY, TYPE_HINT, TYPE_SEGMENT, WELL, Shadow, Toggle, _TOGGLES,
                    apply_tree_theme, build_tree, button, ensure_hover, entry, menu, pick, refresh_strips, segmented,
                    slider, switch_style, tool_button)

LAZY_OVER = 500   # a table with more rows than this loads them as you scroll
CHUNK = 200       # rows added each time


# ---------- small pieces ----------

def choose_folder(var, title):
    d = filedialog.askdirectory(title=title)
    if d:
        var.set(d)


def path_row(parent, var, title):
    """A folder path field with a Browse button."""
    row = ctk.CTkFrame(parent, fg_color="transparent")
    entry(row, var).pack(side="left", fill="x", expand=True)
    b = button(row, "Browse", lambda: choose_folder(var, title), width=76)
    b.configure(height=32)
    b.pack(side="left", padx=(8, 0))
    return row


def labelled(parent, text):
    """A label over an empty cell, for one setting; returns the cell."""
    box = ctk.CTkFrame(parent, fg_color="transparent")
    ctk.CTkLabel(box, text=text, font=(FONT, 12, "bold"), text_color=MUTED, anchor="w").pack(fill="x", pady=(0, 4))
    cell = ctk.CTkFrame(box, fg_color="transparent")
    cell.pack(fill="x")
    box.cell = cell
    return box


def section(parent, text):
    """A small heading with a rule under it, to group settings inside a segment."""
    box = ctk.CTkFrame(parent, fg_color="transparent")
    ctk.CTkLabel(box, text=text, font=TYPE_SEGMENT, text_color=TEXT, anchor="w").pack(fill="x")
    ctk.CTkFrame(box, height=EDGE, fg_color=BORDER, corner_radius=0).pack(fill="x", pady=(3, 0))
    return box


def facts(parent, pairs, wrap=620):
    """A two-column list of 'label: value' lines; returns {label: value label} so the values can be updated."""
    grid = ctk.CTkFrame(parent, fg_color="transparent")
    grid.grid_columnconfigure(1, weight=1)
    out = {}
    for n, key in enumerate(pairs):
        ctk.CTkLabel(grid, text=key, font=(FONT, 12, "bold"), text_color=MUTED, anchor="w", width=130).grid(
            row=n, column=0, sticky="nw", pady=2)
        out[key] = ctk.CTkLabel(grid, text="", font=TYPE_BODY, text_color=TEXT, anchor="w", justify="left", wraplength=wrap)
        out[key].grid(row=n, column=1, sticky="ew", padx=(10, 0), pady=2)
    out["_grid"] = grid
    return out


class ChoiceCards(ctk.CTkFrame):
    """Pick one of a few options by clicking a card (a title and a line saying what you get). The chosen card is
    pink and the one under the pointer lifts. Tab reaches the cards, Space or Enter picks one, arrows move."""

    def __init__(self, parent, var, options, columns=2, on_pick=None):
        super().__init__(parent, fg_color="transparent")
        self.var, self.options, self.on_pick = var, options, on_pick
        self.cards = {}
        for c in range(columns):
            self.grid_columnconfigure(c, weight=1, uniform="choice")
        for n, (value, title, desc) in enumerate(options):
            card = ctk.CTkFrame(self, fg_color=RAISED, border_color=BORDER, border_width=EDGE, corner_radius=0,
                                cursor="hand2")
            card.grid(row=n // columns, column=n % columns, sticky="nsew",
                      padx=(0, 8) if n % columns != columns - 1 else (0, 0), pady=(0, 8))
            name = ctk.CTkLabel(card, text=title, font=(FONT, 13, "bold"), anchor="w", justify="left")
            name.pack(fill="x", padx=12, pady=(9, 0))
            sub = ctk.CTkLabel(card, text=desc, font=TYPE_HINT, anchor="w", justify="left", wraplength=250)
            sub.pack(fill="x", padx=12, pady=(2, 9))
            for w in (card, name, sub):
                w.bind("<Button-1>", lambda _, v=value: self.pick(v))
            card.__dict__["_hover_hooks"] = (lambda v=value: self._hover(v, True), lambda v=value: self._hover(v, False))
            tk.Frame.configure(card, takefocus=1)
            tk.Frame.bind(card, "<Return>", lambda _, v=value: self.pick(v), "+")
            tk.Frame.bind(card, "<space>", lambda _, v=value: self.pick(v), "+")
            tk.Frame.bind(card, "<Right>", lambda _: self._step(1), "+")
            tk.Frame.bind(card, "<Down>", lambda _: self._step(columns), "+")
            tk.Frame.bind(card, "<Left>", lambda _: self._step(-1), "+")
            tk.Frame.bind(card, "<Up>", lambda _: self._step(-columns), "+")
            tk.Frame.bind(card, "<FocusIn>", lambda _, c=card: c.configure(border_color=FOCUS), "+")
            tk.Frame.bind(card, "<FocusOut>", lambda _, c=card: c.configure(border_color=BORDER), "+")
            self.cards[value] = (card, name, sub)
        var.trace_add("write", lambda *_: self.paint())
        ensure_hover(self)
        self.paint()

    def _hover(self, value, on):
        card = self.cards[value][0]
        if value != self.var.get():
            card.configure(fg_color=HOVER if on else RAISED)

    def pick(self, value):
        self.var.set(value)
        if self.on_pick:
            self.on_pick(value)

    def _step(self, d):
        values = [o[0] for o in self.options]
        cur = values.index(self.var.get()) if self.var.get() in values else -1
        nxt = cur + d
        if 0 <= nxt < len(values):
            self.pick(values[nxt])
            tk.Frame.focus_set(self.cards[values[nxt]][0])
        return "break"

    def describe(self, value, text):
        self.cards[value][2].configure(text=text)

    def paint(self):
        for value, (card, name, sub) in self.cards.items():
            on = value == self.var.get()
            card.configure(fg_color=PINK if on else RAISED)
            name.configure(text_color=ON_ACCENT if on else TEXT)
            sub.configure(text_color="#2B2B2B" if on else MUTED)


# ---------- the advanced block ----------

class Advanced(ctk.CTkFrame):
    """A bordered, tinted block of rarely needed settings, shut by default. The title shows how many of its settings
    differ from their defaults ("Advanced options · 2 changed"). Put the settings in `.body`; call `track(vars,
    defaults)` once to keep the count up to date."""

    def __init__(self, parent, title="Advanced options", open=False):
        super().__init__(parent, fg_color=PANEL, border_color=BORDER, border_width=EDGE, corner_radius=0)
        self.title, self.opened, self.changed = title, open, 0
        self.head = ctk.CTkLabel(self, text="", font=(FONT, 13, "bold"), text_color=TEXT, anchor="w", cursor="hand2")
        self.head.pack(fill="x", padx=12, pady=8)
        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.head.bind("<Button-1>", lambda _: self.toggle())
        self.head.__dict__["_hover_hooks"] = (lambda: self.head.configure(text_color=FOCUS), lambda: self.head.configure(text_color=TEXT))
        ensure_hover(self)
        self._paint()

    def toggle(self):
        self.opened = not self.opened
        self._paint()

    def set_open(self, on):
        self.opened = on
        self._paint()

    def _paint(self):
        extra = f"  ·  {self.changed} changed" if self.changed else ""
        self.head.configure(text=("▾  " if self.opened else "▸  ") + self.title + extra)
        if self.opened:
            self.body.pack(fill="x", padx=12, pady=(0, 12))
        else:
            self.body.pack_forget()

    def track(self, variables, defaults):
        """Count the settings in `variables` that differ from `defaults` (both dicts by name) and keep the title current."""
        def recount():
            n = 0
            for k, default in defaults.items():
                try:
                    if variables[k].get() != default:
                        n += 1
                except (KeyError, tk.TclError):
                    pass
            self.changed = n
            self._paint()
        for k in defaults:
            if k in variables:
                variables[k].trace_add("write", lambda *_: recount())
        recount()


# ---------- the segment ----------

class Segment(Shadow):
    """One titled section of a page. States: "active" (pink edge: do this now), "done" (ticked marker), "idle" and
    "locked" (greyed and shut until an earlier section is done). Click the title to open or close it. A short
    `summary` of what the section holds or did sits on the right; put the section's controls in `.body`."""

    def __init__(self, parent, title):
        def build(p):
            face = ctk.CTkFrame(p, fg_color=WELL, border_color=BORDER, border_width=EDGE, corner_radius=0)
            self.head = ctk.CTkFrame(face, fg_color="transparent", cursor="hand2")
            self.head.pack(fill="x", padx=14, pady=(12, 10))
            self.marker = tk.Canvas(self.head, width=26, height=26, highlightthickness=0, bd=0)
            self.marker.pack(side="left")
            self.title = ctk.CTkLabel(self.head, text=title, font=TYPE_SEGMENT, anchor="w")
            self.title.pack(side="left", padx=(12, 0))
            self.chevron = ctk.CTkLabel(self.head, text="", font=(FONT, 14, "bold"), text_color=MUTED, width=24)
            self.summary = ctk.CTkLabel(self.head, text="", font=TYPE_BODY, text_color=MUTED, anchor="e", justify="right",
                                        wraplength=560)
            self.body = ctk.CTkFrame(face, fg_color="transparent")
            return face

        super().__init__(parent, build, depth=5)
        self.state, self.opened = "idle", True
        for w in (self.head, self.marker, self.title, self.summary, self.chevron):
            w.bind("<Button-1>", lambda _: self.toggle())
        self.head.__dict__["_hover_hooks"] = (lambda: self._hover(True), lambda: self._hover(False))
        ensure_hover(self)
        _TOGGLES.add(self)
        self.set_state("idle")

    def _hover(self, on):
        if self.state != "locked":
            self.chevron.configure(text_color=TEXT if on else MUTED)
            self.inner.configure(border_color=PINK if (on or self.state == "active") else BORDER)

    def toggle(self):
        if self.state != "locked":
            self.opened = not self.opened
            self._layout()

    def set_open(self, on):
        self.opened = on
        self._layout()

    def set_summary(self, text):
        self.summary.configure(text=text)

    def set_state(self, state):
        self.state = state
        self.inner.configure(border_color=PINK if state == "active" else BORDER)
        self.title.configure(text_color=MUTED if state == "locked" else TEXT)
        self._layout()
        self.redraw()

    def _layout(self):
        for w in (self.chevron, self.summary):
            w.pack_forget()
        locked = self.state == "locked"
        if not locked:
            self.chevron.configure(text="▾" if self.opened else "▸")
            self.chevron.pack(side="right")
        self.summary.pack(side="right", padx=(8, 8), fill="x", expand=True)
        self.body.pack_forget()
        if not locked and self.opened:
            self.body.pack(fill="x", padx=14, pady=(0, 14))

    def redraw(self):
        c = self.marker
        c.configure(bg=pick(WELL))
        c.delete("all")
        ink = pick(BORDER)
        fill = {"done": CYAN, "active": PINK, "locked": SWITCH_OFF}.get(self.state, ACCENT)
        c.create_rectangle(4, 4, 26, 26, fill=ink, outline=ink)  # the marker's own hard shadow
        c.create_rectangle(1.5, 1.5, 22, 22, fill=pick(fill), outline=ink, width=3)
        if self.state == "done":
            c.create_line(6, 12, 10, 17, 18, 6, fill="#111111", width=3, joinstyle="miter")


# ---------- the table ----------

class LazyTable(ctk.CTkFrame):
    """A scrollable table for lists of any length: pass plain tuples of values to set_rows(). Above LAZY_OVER rows only
    the first CHUNK are drawn and more are added as you scroll down, so a big library opens at once. A search box
    filters on any column. `show_pictures(loader)` adds a small picture to each row, loaded in the background for
    the rows that are drawn (`loader(key)` returns a PIL image or None)."""
    _count = 0

    def __init__(self, parent, columns, rows=8, empty="", filterable=True, selectmode="extended"):
        super().__init__(parent, fg_color="transparent")
        LazyTable._count += 1
        self.style = f"Lazy{LazyTable._count}.Treeview"
        self.all, self.keys, self.tags, self.view = [], [], [], []
        self.shown = 0
        self.loader = None
        self._photos, self._cache = {}, {}
        self._want = queue.Queue()
        self._got = queue.Queue()
        self._worker = None
        self.top = ctk.CTkFrame(self, fg_color="transparent")
        self.query = ctk.StringVar()
        self.count = ctk.CTkLabel(self.top, text="", font=TYPE_HINT, text_color=MUTED, anchor="e")
        if filterable:
            self.top.pack(fill="x", pady=(0, 6))
            ctk.CTkLabel(self.top, text="Filter", font=TYPE_HINT, text_color=MUTED).pack(side="left", padx=(0, 8))
            self.search = entry(self.top, self.query)
            self.search.pack(side="left", fill="x", expand=True)
            self.count.pack(side="right", padx=(10, 0))
            self.query.trace_add("write", lambda *_: self._refilter())
        self.box, self.tree = build_tree(self, columns, selectmode=selectmode, empty=empty, style=self.style, picture=True)
        self.tree.configure(height=rows)
        self.box.pack(fill="x", padx=(0, 6))
        self._tick()

    # --- data
    def set_rows(self, rows, keys=None, tags=None):
        """Replace the rows. `keys` identifies each row (used for pictures); `tags` is a ttk tag per row (or None)."""
        rows = list(rows)
        if rows == self.all and (tags is None or list(tags) == self.tags):
            return  # nothing changed: keep the scroll position and the selection
        self.all = rows
        self.keys = list(keys) if keys is not None else [None] * len(self.all)
        self.tags = list(tags) if tags is not None else [()] * len(self.all)
        self._refilter()

    def _refilter(self):
        q = self.query.get().strip().lower()
        if q:
            self.view = [i for i, r in enumerate(self.all) if q in " ".join(str(v) for v in r).lower()]
        else:
            self.view = list(range(len(self.all)))
        self.tree.delete(*self.tree.get_children())
        self.shown = 0
        self._more(CHUNK if len(self.view) > LAZY_OVER else len(self.view))
        n, total = len(self.view), len(self.all)
        self.count.configure(text=f"{n} of {total}" if q else (f"{total}" if total else ""))

    def _more(self, n=CHUNK):
        stop = min(len(self.view), self.shown + n)
        for pos in range(self.shown, stop):
            i = self.view[pos]
            self.tree.insert("", "end", iid=str(i), values=self.all[i], tags=self.tags[i])
            self._wish(i)
        self.shown = stop

    def selected(self):
        """Indexes (into the rows given to set_rows) of the selected rows."""
        return [int(i) for i in self.tree.selection()]

    # --- loading more while you scroll
    def _tick(self):
        try:
            if self.shown < len(self.view) and self.tree.yview()[1] >= 0.9:
                self._more()
            self._deliver()
            self.after(120, self._tick)
        except tk.TclError:
            pass  # the table is gone

    # --- pictures
    def show_pictures(self, loader, on=True):
        """Show (or hide) a small picture on each row. `loader(key)` is called off the main thread."""
        self.loader = loader if on else None
        height = 58 if on else 30
        self.tree.__dict__["_rowheight"] = height
        self.tree.column("#0", width=46 if on else 0, minwidth=0, stretch=False)
        apply_tree_theme(self.tree)
        if on:
            for i in self.view[:self.shown]:
                self._wish(i)
            if self._worker is None:
                self._worker = threading.Thread(target=self._load_pictures, daemon=True)
                self._worker.start()
        else:
            for iid in self.tree.get_children():
                self.tree.item(iid, image="")

    def _wish(self, i):
        key = self.keys[i]
        if self.loader is None or key is None:
            return
        if key in self._cache:
            self._put(str(i), self._cache[key])
        else:
            self._want.put((str(i), key))

    def _load_pictures(self):
        while True:
            iid, key = self._want.get()
            loader = self.loader
            if loader is None:
                continue
            try:
                img = loader(key)
            except Exception:  # noqa: BLE001 - a broken file just gets no picture
                img = None
            self._got.put((iid, key, img))

    def _deliver(self):
        for _ in range(12):
            try:
                iid, key, img = self._got.get_nowait()
            except queue.Empty:
                return
            self._cache[key] = img
            self._put(iid, img)

    def _put(self, iid, img):
        if img is None or self.loader is None or not self.tree.exists(iid):
            return
        from PIL import ImageTk
        photo = ImageTk.PhotoImage(img)
        self._photos[iid] = photo  # keep a reference or Tk drops the picture
        self.tree.item(iid, image=photo)

    def apply_theme(self):
        apply_tree_theme(self.tree)


# ---------- the page ----------

_AUTO = {"var": None}


def auto_advance_var():
    """The one 'open the next section for me' switch every page shares."""
    if _AUTO["var"] is None:
        _AUTO["var"] = ctk.BooleanVar(value=True)
    return _AUTO["var"]


class SegmentPage(ctk.CTkFrame):
    """A page made of a Header, a scrolling column of Segments and a pinned Footer. Subclasses call add_segment() for
    each section and fill its body, then set_footer() to say what the main button does. It keeps the same small
    interface as the options-panel pages (vars, state, restore, watch, say) so the rest of the app treats it alike."""
    title = subtitle = ""
    defaults = {}
    choices = {}
    max_width = 1100

    def __init__(self, parent):
        super().__init__(parent, fg_color=BG)
        self.vars = {}
        for k, v in self.defaults.items():
            self.vars[k] = ctk.BooleanVar(value=v) if isinstance(v, bool) else \
                ctk.DoubleVar(value=v) if isinstance(v, (int, float)) else ctk.StringVar(value=v)
        self.status = None
        self.auto = auto_advance_var()
        # the footer comes first so it keeps its place at the bottom
        self.footer = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=0)
        self.footer.pack(side="bottom", fill="x")
        ctk.CTkFrame(self.footer, height=EDGE, fg_color=BORDER, corner_radius=0).pack(fill="x")
        row = ctk.CTkFrame(self.footer, fg_color="transparent")
        row.pack(fill="x", padx=28, pady=12)
        self.bar_btn = button(row, "", None, primary=True, width=280)
        self.bar_btn.configure(height=50, font=(FONT, 15, "bold"))
        self.bar_btn.pack(side="right")
        self.side_row = ctk.CTkFrame(row, fg_color="transparent")
        self.side_row.pack(side="left")
        self.bar_text = ctk.CTkLabel(row, text="", font=(FONT, 14, "bold"), text_color=TEXT, anchor="w", justify="left",
                                     wraplength=520)
        self.bar_text.pack(side="left", fill="x", expand=True, padx=(0, 12))
        self.scroll = ctk.CTkScrollableFrame(self, fg_color=BG, corner_radius=0, scrollbar_button_color=SCROLL,
                                             scrollbar_button_hover_color=MUTED)
        self.scroll.pack(fill="both", expand=True)
        self.col = ctk.CTkFrame(self.scroll, fg_color=BG)
        self.col.pack(fill="x", padx=40, pady=(24, 24))
        # (never bind <Configure> on the scrollable frame itself: it replaces the binding that keeps its scroll
        # region up to date and scrolling stops working)
        self.bind("<Configure>", self._centre)
        self._header()
        self.segments = []

    def _header(self):
        head = ctk.CTkFrame(self.col, fg_color="transparent")
        head.pack(fill="x", pady=(0, 16))
        words = ctk.CTkFrame(head, fg_color="transparent")
        words.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(words, text=self.title.upper(), font=(HEAD, 22), text_color=TEXT, anchor="w").pack(fill="x")
        ctk.CTkLabel(words, text=self.subtitle, font=TYPE_BODY, text_color=MUTED, anchor="w").pack(fill="x", pady=(2, 0))
        Toggle(head, text="Open the next section for me", variable=self.auto, **switch_style()).pack(
            side="right", anchor="n", pady=(6, 0))

    def _centre(self, e):
        """Keep the column at most `max_width` wide and centred however wide the window is."""
        scale = self._get_widget_scaling()
        pad = max(28, int((e.width / scale - self.max_width) / 2))
        self.col.pack_configure(padx=(pad, pad))

    def add_segment(self, title):
        seg = Segment(self.col, title)
        seg.pack(fill="x", pady=(0, 18), padx=(0, 6))
        self.segments.append(seg)
        return seg

    def advance(self, seg):
        """`seg` is finished: fold it and open the next section that is not done (when the switch is on)."""
        if not self.auto.get():
            return
        seg.set_open(False)
        later = self.segments[self.segments.index(seg) + 1:]
        nxt = next((s for s in later if s.state != "locked"), None)
        if nxt is not None:
            nxt.set_open(True)
            self.update_idletasks()
            self.reveal(nxt)

    def reveal(self, seg):
        """Scroll so `seg` is in view."""
        canvas = self.scroll._parent_canvas
        total = max(1, self.col.winfo_height())
        canvas.yview_moveto(0.0 if seg is self.segments[0] else max(0.0, min(1.0, (seg.winfo_y() - 16) / total)))

    def set_footer(self, text, label, command=None, enabled=True, secondary=()):
        """What the footer says and does: a line of status text, the main button, and any number of secondary buttons
        (label, command) on the left."""
        self.bar_text.configure(text=text)
        self.bar_btn.configure(text=label, state="normal" if enabled else "disabled")
        if command is not None:
            self.bar_btn.configure(command=command)
        for w in self.side_row.winfo_children():
            w.destroy()
        for lab, cmd in secondary:
            tool_button(self.side_row, lab, cmd, max(100, 28 + 8 * len(lab))).pack(side="left", padx=(0, 8))

    @property
    def btn_run(self):
        return self.bar_btn

    def primary_action(self):
        """Ctrl+Enter: press the main button if it can be used."""
        if str(self.bar_btn.cget("state")) != "disabled":
            self.bar_btn.invoke()
        return True

    def say(self, msg, err=False):
        if self.status is not None:
            self.status.configure(text=msg, text_color=DANGER if err else MUTED)

    def watch(self, *names, callback):
        for n in names:
            self.vars[n].trace_add("write", lambda *_: callback())

    def state(self):
        out = {k: v.get() for k, v in self.vars.items()}
        out["_auto_advance"] = bool(self.auto.get())
        return out

    def restore(self, saved):
        saved = saved or {}
        if isinstance(saved.get("_auto_advance"), bool):
            self.auto.set(saved["_auto_advance"])
        for k, v in saved.items():
            if k in self.vars and (k not in self.choices or v in self.choices[k]):
                try:
                    self.vars[k].set(v)
                except (ValueError, TypeError):
                    pass

    # shared settings rows ---------------------------------------------------
    def image_options(self, parent):
        """Format, quality and size of a saved cover image in one block; returns a function that shows the quality row
        only when the format has a quality."""
        v = self.vars
        fmt = labelled(parent, "Image format")
        segmented(fmt.cell, v["format"], FORMATS).pack(fill="x")
        fmt.pack(fill="x", pady=(0, 10))
        q = labelled(parent, "Quality")
        slider(q.cell, from_=50, to=100, number_of_steps=50, variable=v["quality"], width=200).pack(side="left")
        qval = ctk.CTkLabel(q.cell, text="", font=(FONT, 12, "bold"), text_color=TEXT, width=40)
        qval.pack(side="left", padx=(8, 0))
        v["quality"].trace_add("write", lambda *_: qval.configure(text=str(int(v["quality"].get()))))
        qval.configure(text=str(int(v["quality"].get())))
        size = labelled(parent, "Size")
        menu(size.cell, v["height"], list(HEIGHTS)).pack(fill="x")

        def refresh():
            if v["format"].get() in ("JPG", "WebP"):
                q.pack(fill="x", pady=(0, 10), before=size)
            else:
                q.pack_forget()
        size.pack(fill="x", pady=(0, 10))
        v["format"].trace_add("write", lambda *_: refresh())
        refresh()
        return refresh

    def apply_theme(self):
        refresh_strips()
        for seg in self.segments:
            seg.redraw()

"""Guided pages: a column of numbered step cards (choose, check, run) with everything you need on screen, and the main
action pinned in a bar at the bottom. A page tells you where you are and what to press next, but never hides the
information behind it: every step shows its details, and a step can be folded by clicking its header. Built on the
widgets of ui_kit."""
import tkinter as tk
from tkinter import filedialog

import customtkinter as ctk

from comic_core import FORMATS, HEIGHTS
from ui_kit import (ACCENT, ACCENT_TEXT, BG, BORDER, CYAN, DANGER, EDGE, FOCUS, FONT, HEAD, HOVER, MUTED, ON_ACCENT, PANEL, PINK,
                    RAISED, SCROLL, SWITCH_OFF, TEXT, WELL, Shadow, _TOGGLES, build_tree, button, ensure_hover, entry,
                    menu, pick, refresh_strips, segmented, slider, title_block, tool_button)


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
    """A small heading with a rule under it, to group settings inside a step."""
    box = ctk.CTkFrame(parent, fg_color="transparent")
    ctk.CTkLabel(box, text=text.upper(), font=(HEAD, 10), text_color=TEXT, anchor="w").pack(fill="x")
    ctk.CTkFrame(box, height=EDGE, fg_color=BORDER, corner_radius=0).pack(fill="x", pady=(3, 0))
    return box


def mini_table(parent, columns, rows=6, empty=""):
    """A bordered table with a fixed number of visible rows (see ui_kit.build_tree for the column spec)."""
    box, tree = build_tree(parent, columns)
    tree.configure(height=rows)
    if empty:
        box.set_empty(empty)
    return box, tree


def facts(parent, pairs, wrap=620):
    """A two-column list of 'label: value' lines; returns {label: value label} so the values can be updated."""
    grid = ctk.CTkFrame(parent, fg_color="transparent")
    grid.grid_columnconfigure(1, weight=1)
    out = {}
    for n, key in enumerate(pairs):
        ctk.CTkLabel(grid, text=key, font=(FONT, 12, "bold"), text_color=MUTED, anchor="w", width=130).grid(
            row=n, column=0, sticky="nw", pady=2)
        out[key] = ctk.CTkLabel(grid, text="", font=(FONT, 13), text_color=TEXT, anchor="w", justify="left", wraplength=wrap)
        out[key].grid(row=n, column=1, sticky="ew", padx=(10, 0), pady=2)
    out["_grid"] = grid
    return out


class Disclosure(ctk.CTkFrame):
    """A link that unfolds more settings; `body` is where they go."""

    def __init__(self, parent, text, open=False):
        super().__init__(parent, fg_color="transparent")
        self.text, self.opened = text, open
        self.head = ctk.CTkLabel(self, text="", font=ctk.CTkFont(family=FONT, size=13, weight="bold", underline=True),
                                 text_color=TEXT, anchor="w", cursor="hand2")
        self.head.pack(fill="x")
        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.head.bind("<Button-1>", lambda _: self.toggle())
        self.head.__dict__["_hover_hooks"] = (lambda: self.head.configure(text_color=ACCENT_TEXT), lambda: self.head.configure(text_color=TEXT))
        ensure_hover(self)
        self._paint()

    def toggle(self):
        self.opened = not self.opened
        self._paint()

    def _paint(self):
        self.head.configure(text=("▾ " if self.opened else "▸ ") + self.text)
        if self.opened:
            self.body.pack(fill="x", pady=(10, 0))
        else:
            self.body.pack_forget()



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
                      padx=(0, 8) if n % columns == 0 and columns > 1 else (0, 0), pady=(0, 8))
            name = ctk.CTkLabel(card, text=title, font=(FONT, 13, "bold"), anchor="w", justify="left")
            name.pack(fill="x", padx=12, pady=(9, 0))
            sub = ctk.CTkLabel(card, text=desc, font=(FONT, 11), anchor="w", justify="left", wraplength=250)
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


class StepCard(Shadow):
    """One numbered step. States: "active" (pink edge and a label saying where you are), "done" (ticked badge),
    "idle" (no highlight) and "locked" (greyed and closed until an earlier step is done). Every open step shows all
    of its controls; click the header to fold or unfold it. Put the step's controls in `.body`."""

    def __init__(self, parent, number, title):
        def build(p):
            face = ctk.CTkFrame(p, fg_color=WELL, border_color=BORDER, border_width=EDGE, corner_radius=0)
            self.head = ctk.CTkFrame(face, fg_color="transparent", cursor="hand2")
            self.head.pack(fill="x", padx=14, pady=(12, 10))
            self.badge = tk.Canvas(self.head, width=38, height=38, highlightthickness=0, bd=0)
            self.badge.pack(side="left")
            self.title = ctk.CTkLabel(self.head, text=title.upper(), font=(HEAD, 13), anchor="w")
            self.title.pack(side="left", padx=(12, 0))
            self.tag = ctk.CTkLabel(self.head, text="", font=(FONT, 10, "bold"), text_color=ON_ACCENT, fg_color=PINK,
                                    corner_radius=0, padx=8, pady=2)
            self.chevron = ctk.CTkLabel(self.head, text="", font=(FONT, 14, "bold"), text_color=MUTED, width=24)
            self.summary = ctk.CTkLabel(self.head, text="", font=(FONT, 12), text_color=MUTED, anchor="e", justify="right",
                                        wraplength=520)
            self.hint = ctk.CTkLabel(face, text="", font=(FONT, 13), text_color=MUTED, anchor="w", justify="left",
                                     wraplength=900)
            self.body = ctk.CTkFrame(face, fg_color="transparent")
            return face

        super().__init__(parent, build, depth=5)
        self.number = number
        self.state, self.state_tag, self.opened = "idle", "", True
        for w in (self.head, self.badge, self.title, self.summary, self.chevron, self.tag):
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

    def set_hint(self, text):
        """One line under the header saying what to do in this step (or what is happening in it)."""
        self.hint.configure(text=text)
        self._layout()

    def set_state(self, state, tag=""):
        self.state, self.state_tag = state, tag
        self.inner.configure(border_color=PINK if state == "active" else BORDER)
        self.title.configure(text_color=MUTED if state == "locked" else TEXT)
        self._layout()
        self.redraw()

    def _layout(self):
        for w in (self.tag, self.chevron, self.summary):
            w.pack_forget()
        locked = self.state == "locked"
        if self.state_tag and self.state != "done":
            self.tag.configure(text=self.state_tag.upper())
            self.tag.pack(side="left", padx=(12, 0))
        if not locked:
            self.chevron.configure(text="▾" if self.opened else "▸")
            self.chevron.pack(side="right")
        self.summary.pack(side="right", padx=(8, 8), fill="x", expand=True)
        self.hint.pack_forget()
        self.body.pack_forget()
        if not (locked or not self.opened):
            if self.hint.cget("text"):
                self.hint.pack(fill="x", padx=16, pady=(0, 12))
            self.body.pack(fill="x", padx=14, pady=(0, 14))

    def redraw(self):
        c = self.badge
        c.configure(bg=pick(WELL))
        c.delete("all")
        ink = pick(BORDER)
        fill = {"done": CYAN, "active": PINK, "locked": SWITCH_OFF}.get(self.state, ACCENT)
        c.create_rectangle(4, 4, 38, 38, fill=ink, outline=ink)  # the badge's own hard shadow
        c.create_rectangle(1.5, 1.5, 34, 34, fill=pick(fill), outline=ink, width=3)
        if self.state == "done":
            c.create_line(9, 18, 15, 25, 27, 10, fill="#111111", width=4, joinstyle="miter")
        else:
            c.create_text(17.5, 18, text=str(self.number), font=(HEAD, 14), fill="#111111")


# ---------- the page ----------

class StepPage(ctk.CTkFrame):
    """A page that is a scrolling column of StepCards with a pinned action bar. Subclasses call add_step() for each step
    and fill its body, and set_bar() to say what the main button does. It keeps the same small interface as the
    options-panel pages (vars, state, restore, watch, say) so the rest of the app treats it alike."""
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
        # the pinned bar comes first so it keeps its place at the bottom
        self.bar = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=0)
        self.bar.pack(side="bottom", fill="x")
        ctk.CTkFrame(self.bar, height=EDGE, fg_color=BORDER, corner_radius=0).pack(fill="x")
        row = ctk.CTkFrame(self.bar, fg_color="transparent")
        row.pack(fill="x", padx=28, pady=12)
        self.bar_btn = button(row, "", None, primary=True, width=280)
        self.bar_btn.configure(height=50, font=(FONT, 15, "bold"))
        self.bar_btn.pack(side="right")
        self.bar_alt = tool_button(row, "", None, 130)
        self.bar_text = ctk.CTkLabel(row, text="", font=(FONT, 14, "bold"), text_color=TEXT, anchor="w", justify="left",
                                     wraplength=520)
        self.bar_text.pack(side="left", fill="x", expand=True)
        self.scroll = ctk.CTkScrollableFrame(self, fg_color=BG, corner_radius=0, scrollbar_button_color=SCROLL,
                                             scrollbar_button_hover_color=MUTED)
        self.scroll.pack(fill="both", expand=True)
        self.col = ctk.CTkFrame(self.scroll, fg_color=BG)
        self.col.pack(fill="x", padx=40, pady=(24, 24))
        # (never bind <Configure> on the scrollable frame itself: it replaces the binding that keeps its scroll
        # region up to date and scrolling stops working)
        self.bind("<Configure>", self._centre)
        title_block(self.col, self.title, self.subtitle, strip=False)
        self.steps = []

    def _centre(self, e):
        """Keep the column at most `max_width` wide and centred however wide the window is."""
        scale = self._get_widget_scaling()
        pad = max(28, int((e.width / scale - self.max_width) / 2))
        self.col.pack_configure(padx=(pad, pad))

    def add_step(self, title):
        card = StepCard(self.col, len(self.steps) + 1, title)
        card.pack(fill="x", pady=(0, 18), padx=(0, 6))
        self.steps.append(card)
        return card

    def set_bar(self, text, label, command=None, enabled=True, alt=None):
        """What the pinned bar says and does: a line of text, the main button, and optionally a second button
        (label, command)."""
        self.bar_text.configure(text=text)
        self.bar_btn.configure(text=label, state="normal" if enabled else "disabled")
        if command is not None:
            self.bar_btn.configure(command=command)
        self.bar_alt.pack_forget()
        if alt:
            self.bar_alt.configure(text=alt[0], command=alt[1], width=max(100, 24 + 8 * len(alt[0])))
            self.bar_alt.pack(side="right", padx=(0, 14))

    @property
    def btn_run(self):
        return self.bar_btn

    def primary_action(self):
        """Ctrl+Enter: press the pinned button if it can be used."""
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
        return {k: v.get() for k, v in self.vars.items()}

    def restore(self, saved):
        for k, v in (saved or {}).items():
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
        fmt.pack(fill="x", pady=(10, 10))
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

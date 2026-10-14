"""Shared look and widgets: palette, styled controls, form rows, drop zone, page scaffold."""
import random
import tkinter as tk
import weakref
from tkinter import filedialog, ttk

import customtkinter as ctk

from comic_core import FORMATS, HEIGHTS

# Neo-brutalist palette. Each colour is (light, dark): customtkinter swaps them when the mode changes.
# Light: cream canvas, white surfaces, black ink. Dark: black canvas, dark surfaces, white ink and shadows.
BG = ("#D9D2FA", "#25252E")             # canvas: lilac in light mode
PANEL = ("#EFEBFF", "#353542")          # panels (the options inspector, the sidebar): pale lilac
RAISED = ("#FFFFFF", "#353542")         # buttons and cards
WELL = ("#FFFFFF", "#353542")           # inputs, tables, logs: white paper to write on
INK = ("#111111", "#08080C")            # borders and hard shadows: black in both modes (dark mode lifts the
BORDER = INK                            # canvas to a dusky slate so black edges and shadows still show)
HOVER = ("#FFD3EA", "#4B4B5E")
TEXT = ("#111111", "#F6F6FA")
MUTED = ("#4A4A4A", "#C6C6D4")
DISABLED_FILL = ("#CFCAE6", "#4A4A5C")    # fill of a main button that cannot be used yet
SCROLL = ("#111111", "#9A9AAE")         # scrollbar thumbs (black would vanish on dark panels)
YELLOW = ("#FFD60A", "#FFD60A")
PINK = ("#FF4FA3", "#FF5CAB")
CYAN = ("#37C8F0", "#2BB6DE")
ACCENT = YELLOW
ACCENT_HOVER = ("#FFC300", "#FFE066")
ACCENT_TEXT = ("#C2005F", "#FF8CC6")    # accent as a text colour (yellow is unreadable as text)
ON_ACCENT = "#111111"                   # text on any saturated fill, in both modes
DANGER = ("#D90429", "#FF6B81")
SEG_ON = YELLOW                         # selected segment
SEG_OFF = ("#FFFFFF", "#EDEDED")        # unselected segment (dark text in both modes)
SWITCH_OFF = ("#BDBDBD", "#9A9AB0")
SELECT_BG = ("#7BE0FF", "#1B6F8E")      # selected table row
FONT = "Segoe UI"
HEAD = "Arial Black"                    # loud display face for titles (ships with Windows)
R_CARD = R_CTRL = 0                     # square corners everywhere
EDGE = 3                                # border thickness


def pick(color):
    """Resolve a (light, dark) pair for widgets that don't understand tuples (ttk, tk)."""
    if isinstance(color, str):
        return color
    return color[1] if ctk.get_appearance_mode() == "Dark" else color[0]


def switch_style():
    return dict(font=(FONT, 13), text_color=TEXT, progress_color=ACCENT, fg_color=SWITCH_OFF,
                button_color=INK, button_hover_color=INK, corner_radius=0, switch_width=46, switch_height=24,
                button_length=14, border_width=3)


class Slider(tk.Canvas):
    """A square slider: a black-edged track filled with yellow up to a pink block handle. Takes the arguments of a
    customtkinter slider that this app uses (from_, to, number_of_steps, variable, width, command)."""

    H, KNOB = 26, 16

    def __init__(self, parent, from_=0, to=100, number_of_steps=None, variable=None, width=200, command=None, **_):
        super().__init__(parent, width=width, height=self.H, highlightthickness=0, bd=0, cursor="hand2")
        self.lo, self.hi, self.steps, self.command = from_, to, number_of_steps, command
        self.var = variable if variable is not None else tk.DoubleVar(value=from_)
        self.bind("<Configure>", lambda _: self.redraw())
        self.bind("<Button-1>", self._move)
        self.bind("<B1-Motion>", self._move)
        self.var.trace_add("write", lambda *_: self.redraw())
        _TOGGLES.add(self)

    def _move(self, e):
        k = self.KNOB
        span = max(1, self.winfo_width() - k - 4)
        frac = min(1.0, max(0.0, (e.x - k / 2 - 2) / span))
        val = self.lo + frac * (self.hi - self.lo)
        if self.steps:
            step = (self.hi - self.lo) / self.steps
            val = self.lo + round((val - self.lo) / step) * step
        self.var.set(val)
        if self.command:
            self.command(val)

    def redraw(self):
        w, h, k = self.winfo_width(), self.H, self.KNOB
        if w < 20:
            return
        try:
            val = float(self.var.get())
        except (tk.TclError, ValueError):
            val = self.lo
        frac = 0 if self.hi == self.lo else min(1.0, max(0.0, (val - self.lo) / (self.hi - self.lo)))
        ink = pick(INK)
        try:
            self.configure(bg=pick(self.master.cget("fg_color")))
        except (tk.TclError, ValueError, AttributeError):
            self.configure(bg=pick(PANEL))
        self.delete("all")
        x = 2 + frac * (w - k - 4)
        top, bot = h / 2 - 6, h / 2 + 6
        self.create_rectangle(2, top, w - 2, bot, fill=pick(WELL), outline=ink, width=3)
        if x > 4:
            self.create_rectangle(4, top + 2, x + k / 2, bot - 2, fill=pick(PINK), outline=pick(PINK))
        self.create_rectangle(x + 3, 6, x + k + 3, h - 1, fill=ink, outline=ink)  # hard shadow of the handle
        self.create_rectangle(x, 3, x + k, h - 4, fill=pick(ACCENT), outline=ink, width=3)


def slider(parent, **kw):
    return Slider(parent, **kw)


# ---------- the hard shadow ----------

class Shadow(ctk.CTkFrame):
    """Wraps one widget with a solid offset block behind it: the neo-brutalist drop shadow. The wrapper is what gets
    packed or gridded; configure, cget, bind, focus and every other method not defined here go to the wrapped widget,
    so it can be used like the widget itself. With motion the face slides toward its shadow on hover and sinks
    into it while pressed. `edge` adds a black frame round widgets that have no border of their own."""

    def __init__(self, parent, build, depth=4, motion=False, edge=0):
        super().__init__(parent, fg_color="transparent", corner_radius=0)
        self.depth, self.motion, self._off, self._hot = depth, motion, 0, False
        self.block = ctk.CTkFrame(self, fg_color=INK, corner_radius=0, width=1, height=1)
        self.block.grid(row=0, column=0, sticky="nsew", padx=(depth, 0), pady=(depth, 0))
        self.slot = ctk.CTkFrame(self, fg_color=INK if edge else "transparent", corner_radius=0)
        self.slot.grid(row=0, column=0, sticky="nsew", padx=(0, depth), pady=(0, depth))
        self.inner = build(self.slot)
        if edge:
            self.inner.pack(fill="both", expand=True, padx=edge, pady=edge)
        else:
            self.inner.pack(fill="both", expand=True)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        if motion:
            self._bind_motion(self)

    # -- shadow and motion
    def show_shadow(self, on):
        """Show or hide the shadow block (the open item of the sidebar has one, the others don't)."""
        self.block.grid() if on else self.block.grid_remove()

    def _shift(self, n):
        self._off = n
        self.slot.grid_configure(padx=(n, self.depth - n), pady=(n, self.depth - n))

    def _disabled(self):
        try:
            return str(self.inner.cget("state")) == "disabled"
        except (tk.TclError, ValueError, AttributeError):
            return False

    def _bind_motion(self, w):
        w.bind("<Enter>", self._enter, add="+")
        w.bind("<Leave>", self._leave, add="+")
        w.bind("<ButtonPress-1>", self._press, add="+")
        w.bind("<ButtonRelease-1>", self._release, add="+")
        for c in w.winfo_children():
            self._bind_motion(c)

    def _alive(self):
        try:
            return bool(self.winfo_exists())
        except tk.TclError:
            return False

    def _enter(self, _=None):
        if self._alive() and not self._disabled():
            self._hot = True
            self._shift(max(1, self.depth // 2))

    def _leave(self, _=None):
        if not self._alive():
            return
        under = self.winfo_containing(*self.winfo_pointerxy())
        while under is not None:  # moving onto a child of the wrapper is not leaving it
            if under is self:
                return
            under = under.master
        self._hot = False
        self._shift(0)

    def _press(self, _=None):
        if self._alive() and not self._disabled():
            self._shift(self.depth)

    def _release(self, _=None):
        if self._alive():
            self._shift(max(1, self.depth // 2) if self._hot else 0)

    # -- act like the wrapped widget
    def configure(self, require_redraw=False, **kw):
        if "inner" not in self.__dict__:  # still being built: customtkinter configures the frame itself
            return super().configure(require_redraw=require_redraw, **kw)
        dim = self.__dict__.get("dim")
        if dim and "state" in kw:  # a disabled main button greys out instead of staying bright yellow
            kw.setdefault("fg_color", dim[0] if str(kw["state"]) == "normal" else dim[1])
        return self.inner.configure(**kw)

    config = configure

    def cget(self, key):
        if "inner" not in self.__dict__:
            return super().cget(key)
        return self.inner.cget(key)

    def bind(self, sequence=None, command=None, add=None):
        if "inner" not in self.__dict__:
            return super().bind(sequence, command, add)
        return self.inner.bind(sequence, command, add)

    def focus(self):
        return self.inner.focus()

    focus_set = focus

    def __getattr__(self, name):
        if name == "inner":
            raise AttributeError(name)
        return getattr(self.inner, name)


# ---------- small styled widgets ----------

def button(parent, text, command, primary=False, width=260, color=None):
    """A square button with a hard shadow. primary is yellow; color gives any other saturated fill."""
    fill = color or (ACCENT if primary else RAISED)
    loud = primary or color is not None
    sh = Shadow(parent, lambda p: ctk.CTkButton(
        p, text=text, command=command, width=width, height=44 if primary else 38, corner_radius=0,
        font=(FONT, 13, "bold" if primary else "normal"),
        fg_color=fill, hover_color=ACCENT_HOVER if primary else HOVER,
        text_color=ON_ACCENT if loud else TEXT, text_color_disabled=MUTED if not loud else ("#5A5A66", "#9A9AAE"),
        border_width=EDGE, border_color=BORDER), depth=4, motion=True)
    if loud:
        sh.dim = (fill, DISABLED_FILL)
    return sh


def menu(parent, var, values, width=260):
    return Shadow(parent, lambda p: ctk.CTkOptionMenu(
        p, variable=var, values=values, width=width, height=32, corner_radius=0, anchor="w",
        font=(FONT, 13), dropdown_font=(FONT, 13), fg_color=RAISED, button_color=ACCENT,
        button_hover_color=ACCENT_HOVER, text_color=TEXT, dropdown_fg_color=RAISED,
        dropdown_text_color=TEXT, dropdown_hover_color=HOVER), depth=3, edge=EDGE)


def segmented(parent, var, values, width=260):
    return Shadow(parent, lambda p: ctk.CTkSegmentedButton(
        p, variable=var, values=values, width=width, height=30, corner_radius=0, border_width=EDGE,
        font=(FONT, 12, "bold"), fg_color=INK, unselected_color=SEG_OFF, unselected_hover_color=HOVER,
        selected_color=SEG_ON, selected_hover_color=SEG_ON, text_color=ON_ACCENT), depth=3)


def entry(parent, var, **kw):
    return Shadow(parent, lambda p: ctk.CTkEntry(
        p, textvariable=var, height=34, corner_radius=0, font=(FONT, 13),
        fg_color=WELL, border_color=BORDER, border_width=EDGE, text_color=TEXT, **kw), depth=3)


def textbox(parent, **kw):
    """A read-only style text area (logs, previews): white, thick border, hard shadow."""
    opts = dict(font=("Consolas", 12), fg_color=WELL, text_color=TEXT, border_color=BORDER, border_width=EDGE,
                corner_radius=0, wrap="none")
    opts.update(kw)
    return Shadow(parent, lambda p: ctk.CTkTextbox(p, **opts), depth=5)


def tool_button(parent, text, command, width=None):
    """A small bordered button for toolbars."""
    return Shadow(parent, lambda p: ctk.CTkButton(
        p, text=text, command=command, width=width or max(48, 14 + 8 * len(text)), height=28,
        corner_radius=0, font=(FONT, 12, "bold"), fg_color=RAISED, hover_color=HOVER, text_color=TEXT,
        text_color_disabled=MUTED, border_width=2, border_color=BORDER), depth=3, motion=True)


class Form(ctk.CTkScrollableFrame):
    """Stacked label-over-control rows. Rows can be hidden and shown, and a heading can fold the rows under it
    (heading(..., collapsible=True, open=False)) so the settings people need every time come first."""

    def __init__(self, parent):
        super().__init__(parent, fg_color=PANEL, corner_radius=0,
                         scrollbar_button_color=SCROLL, scrollbar_button_hover_color=MUTED)
        self.grid_columnconfigure(0, weight=1)
        self._row = 0
        self._section = None  # the open collapsible section new rows belong to
        self.headings = []  # titles of the groups, in order

    def add(self, text):
        lbl = ctk.CTkLabel(self, text=text, font=(FONT, 12, "bold"), text_color=MUTED, anchor="w")
        lbl.grid(row=self._row, column=0, sticky="ew", pady=(14, 4))
        cell = ctk.CTkFrame(self, fg_color=PANEL)
        cell.grid(row=self._row + 1, column=0, sticky="ew", padx=(0, 4))
        cell.label = lbl
        cell._sec, cell._want = self._section, True
        if self._section is not None:
            self._section["cells"].append(cell)
            self._apply(cell)
        self._row += 2
        return cell

    def heading(self, text, collapsible=False, open=True):
        """A bold group title on a bar. With collapsible=True a click on the bar folds or unfolds the rows under it."""
        box = ctk.CTkFrame(self, fg_color=PANEL)
        box.grid(row=self._row, column=0, sticky="ew", pady=(4 if self._row == 0 else 20, 0))
        bar = ctk.CTkFrame(box, fg_color=ACCENT if open or not collapsible else RAISED, corner_radius=0,
                           border_width=EDGE, border_color=BORDER)
        bar.pack(fill="x", padx=(0, 4))
        mark = "▾ " if open else "▸ "
        lab = ctk.CTkLabel(bar, text=(mark if collapsible else "") + text.upper(), font=(HEAD, 11),
                           text_color=ON_ACCENT if open or not collapsible else TEXT, anchor="w")
        lab.pack(fill="x", padx=8, pady=3)
        box.label = box
        box._sec, box._want = None, True
        self.headings.append(text)
        self._section = None
        if collapsible:
            sec = {"open": open, "cells": []}
            self._section = sec

            def toggle(_=None):
                sec["open"] = not sec["open"]
                bar.configure(fg_color=ACCENT if sec["open"] else RAISED)
                lab.configure(text=("▾ " if sec["open"] else "▸ ") + text.upper(),
                              text_color=ON_ACCENT if sec["open"] else TEXT)
                for c in sec["cells"]:
                    self._apply(c)
            for w in (bar, lab):
                w.bind("<Button-1>", toggle)
                w.configure(cursor="hand2")
        self._row += 1
        return box

    @staticmethod
    def _apply(cell):
        sec = getattr(cell, "_sec", None)
        on = getattr(cell, "_want", True) and (sec is None or sec["open"])
        for w in (cell.label, cell):
            w.grid() if on else w.grid_remove()

    @staticmethod
    def show(cell, on):
        cell._want = on
        Form._apply(cell)


def divider(parent, vertical=True):
    """A thick rule between groups of buttons."""
    if vertical:
        return ctk.CTkFrame(parent, width=EDGE, height=18, fg_color=BORDER, corner_radius=0)
    return ctk.CTkFrame(parent, height=EDGE, fg_color=BORDER, corner_radius=0)


def toolbar(parent, *groups, side="left"):
    """Lay out groups of small buttons in a row, with a divider between the groups.
    Each group is a list of (key, text, width, command); returns {key: button}. side="right" keeps the same
    visual order but anchors the row to the right edge."""
    out = {}
    first = True
    for group in (reversed(groups) if side == "right" else groups):
        if not group:
            continue
        if not first:
            divider(parent).pack(side=side, padx=(8, 8))
        first = False
        for key, text, width, cmd in (reversed(group) if side == "right" else group):
            b = tool_button(parent, text, cmd, width)
            b.pack(side=side, padx=(0, 6) if side == "left" else (6, 0))
            out[key] = b
    return out


class DropZone(Shadow):
    """The 'add your comics' box. With on_folder / on_files it also carries an Add folder and a Choose comics button,
    so every page offers both in the same place."""

    def __init__(self, parent, prompt, on_click, on_folder=None, on_files=None,
                 folder_text="Add folder…", files_text="Choose comics…", files_first=False):
        pair = [("folder", folder_text, on_folder), ("files", files_text, on_files)]
        buttons = [(k, t, None, c) for k, t, c in (pair[::-1] if files_first else pair) if c]
        super().__init__(parent, lambda p: ctk.CTkFrame(
            p, fg_color=WELL, border_color=BORDER, border_width=EDGE, corner_radius=0,
            height=104 if buttons else 88), depth=5)
        box = self.inner
        box.pack_propagate(False)
        self.prompt = prompt
        self.label = ctk.CTkLabel(box, text=prompt, font=(FONT, 14, "bold"), text_color=MUTED)
        self.buttons = {}
        if buttons:
            row = ctk.CTkFrame(box, fg_color="transparent")
            row.pack(side="bottom", pady=(0, 12))
            self.buttons = toolbar(row, *[[b] for b in buttons])
            first = next(iter(self.buttons.values()))
            first.configure(fg_color=ACCENT, text_color=ON_ACCENT, hover_color=ACCENT_HOVER)  # the main way in
            self.label.pack(expand=True, pady=(8, 0))
        else:
            self.label.pack(expand=True)
        for w in (box, self.label):
            w.bind("<Button-1>", lambda _: on_click())
            w.bind("<Enter>", lambda _: box.configure(fg_color=HOVER))
            w.bind("<Leave>", lambda _: box.configure(fg_color=WELL))

    def set(self, text=None):
        self.label.configure(text=text or self.prompt, text_color=TEXT if text else MUTED)


class Toggle(ctk.CTkFrame):
    """An on/off switch drawn as a black-edged block: the track is yellow with ON when set, grey with OFF when not,
    and a black square knob sits at the end. Same arguments as a customtkinter switch (text, variable, command);
    styling arguments are ignored."""

    W, H = 58, 28

    def __init__(self, parent, text="", variable=None, command=None, font=(FONT, 13), text_color=TEXT, **_):
        super().__init__(parent, fg_color="transparent", corner_radius=0)
        self.var = variable if variable is not None else tk.BooleanVar(value=False)
        self.command = command
        self.cv = tk.Canvas(self, width=self.W, height=self.H, highlightthickness=0, bd=0, cursor="hand2",
                            takefocus=1)
        self.cv.pack(side="left")
        self.label = ctk.CTkLabel(self, text=text, font=font, text_color=text_color, anchor="w", cursor="hand2")
        self.label.pack(side="left", padx=(10, 0))
        for w in (self, self.cv, self.label):
            w.bind("<Button-1>", self.toggle, add="+")
        self.cv.bind("<space>", self.toggle, add="+")
        self.var.trace_add("write", lambda *_: self.redraw())
        _TOGGLES.add(self)
        self.redraw()

    def toggle(self, _=None):
        self.var.set(not self.var.get())
        if self.command:
            self.command()

    def redraw(self):
        try:
            on = bool(self.var.get())
        except tk.TclError:
            on = False
        c, ink = self.cv, pick(INK)
        try:
            c.configure(bg=pick(self.master.cget("fg_color")))
        except (tk.TclError, ValueError, AttributeError):
            c.configure(bg=pick(PANEL))
        c.delete("all")
        w, h = self.W, self.H
        c.create_rectangle(4, 4, w - 1, h - 1, fill=ink, outline=ink)  # hard shadow
        c.create_rectangle(2, 2, w - 4, h - 4, fill=pick(PINK if on else SWITCH_OFF), outline=ink, width=3)
        knob = 16
        x = w - 4 - 3 - knob - 1 if on else 2 + 3 + 1
        c.create_rectangle(x, 2 + 3 + 1, x + knob, h - 4 - 3 - 1, fill=ink, outline=ink)
        tx = w * .30 if on else w * .64
        c.create_text(tx, (h - 2) / 2, text="ON" if on else "OFF", font=(FONT, 8, "bold"), fill=ON_ACCENT)


class Splitter(ctk.CTkFrame):
    """A thick divider you drag to resize `target`, a frame that keeps a fixed width (pack_propagate(False)).
    It is also the black border between a side panel and the content. side is where the target sits relative to
    the divider: "left" or "right"."""

    def __init__(self, parent, target, side="left", lo=160, hi=520, on_change=None):
        super().__init__(parent, width=EDGE + 4, fg_color="transparent", corner_radius=0, cursor="sb_h_double_arrow")
        self.target, self.side, self.lo, self.hi, self.on_change = target, side, lo, hi, on_change
        self.line = ctk.CTkFrame(self, width=EDGE, fg_color=BORDER, corner_radius=0, cursor="sb_h_double_arrow")
        self.line.place(relx=0.5, rely=0, relheight=1, anchor="n")
        self._start = None
        for w in (self, self.line):
            w.bind("<ButtonPress-1>", self._press)
            w.bind("<B1-Motion>", self._drag)
            w.bind("<ButtonRelease-1>", self._release)
            w.bind("<Enter>", lambda _: self.line.configure(fg_color=PINK))
            w.bind("<Leave>", lambda _: self._start is None and self.line.configure(fg_color=BORDER))

    def _scale(self):
        try:
            return float(self.target._get_widget_scaling())
        except Exception:  # noqa: BLE001 - older customtkinter
            return 1.0

    def _press(self, e):
        self._start = (e.x_root, self.target.winfo_width() / self._scale())

    def _drag(self, e):
        if self._start is None:
            return
        dx = (e.x_root - self._start[0]) / self._scale()
        self.set_width(self._start[1] + (dx if self.side == "left" else -dx))

    def _release(self, _):
        self._start = None
        self.line.configure(fg_color=BORDER)

    def set_width(self, width):
        width = int(max(self.lo, min(self.hi, width)))
        self.target.configure(width=width)
        if self.on_change:
            self.on_change(width)


# ---------- tool icons ----------

def draw_icon(c, key, cx, cy, size, ink, fill):
    """Draw the line icon of a page, centred on (cx, cy) in a box of `size` pixels. Shapes use `fill`, strokes `ink`."""
    k = size / 48
    lw = max(2, round(3 * k))

    def o(dx, dy):
        return cx + dx * k, cy + dy * k

    def rect(x0, y0, x1, y1):
        c.create_rectangle(*o(x0, y0), *o(x1, y1), fill=fill, outline=ink, width=lw)

    def poly(*pts):
        flat = [v for n in range(0, len(pts), 2) for v in o(pts[n], pts[n + 1])]
        c.create_polygon(*flat, fill=fill, outline=ink, width=lw)

    def line(*pts, w=3, **kw):
        flat = [v for n in range(0, len(pts), 2) for v in o(pts[n], pts[n + 1])]
        c.create_line(*flat, fill=ink, width=max(2, round(w * k)), **kw)

    def text(t, font, dy=1):
        c.create_text(*o(0, dy), text=t, font=(font[0], max(7, round(font[1] * k)), *font[2:]), fill=ink)

    if key == "home":
        poly(-17, -1, 0, -16, 17, -1)
        rect(-11, -1, 11, 14)
        line(0, 14, 0, 5, w=4)
    elif key == "stats":
        rect(-15, 2, -6, 14)
        rect(-4, -6, 5, 14)
        rect(7, -14, 16, 14)
    elif key == "single":
        rect(-9, -13, 9, 13)
        line(-4, -5, 4, -5)
    elif key == "bulk":
        for dx in (-12, 2):
            for dy in (-12, 2):
                rect(dx, dy, dx + 10, dy + 10)
    elif key == "icons":
        poly(-14, -8, -14, -13, -4, -13, -1, -8)
        rect(-14, -8, 14, 12)
    elif key == "rename":
        text("Aa", (HEAD, 17))
    elif key == "metadata":
        text("{ }", ("Consolas", 19, "bold"), dy=0)
    elif key == "convert":
        line(-13, -6, 12, -6, arrow=tk.LAST, arrowshape=(max(4, 9 * k), max(4, 10 * k), max(2, 4 * k)))
        line(13, 7, -12, 7, arrow=tk.LAST, arrowshape=(max(4, 9 * k), max(4, 10 * k), max(2, 4 * k)))
    elif key == "audit":
        line(-13, 1, -4, 10, 14, -11, w=5, joinstyle="miter")
    elif key == "order":
        text("1·2", (HEAD, 15))
    elif key == "aceo":
        for dx in (-14, 2):
            for dy in (-14, -4, 6):
                rect(dx, dy, dx + 12, dy + 8)
    elif key == "intake":
        line(0, -13, 0, 13, w=6)
        line(-13, 0, 13, 0, w=6)
    else:
        text(str(key)[:2], (HEAD, 15))


class IconTile(tk.Canvas):
    """A white square with a thick border and a line icon at its exact centre, used on the Home cards. The shapes
    are filled with the colour of the card they sit on."""
    SIZE = 48

    def __init__(self, parent, key, color):
        s = self.SIZE
        super().__init__(parent, width=s, height=s, bg="#FFFFFF", highlightthickness=0, bd=0)
        draw_icon(self, key, s / 2, s / 2, 46, "#111111", pick(color))
        self.create_rectangle(1.5, 1.5, s - 1.5, s - 1.5, outline="#111111", width=3)


class NavItem(Shadow):
    """One sidebar entry: a line icon and a label. `big` entries (Home, Library stats) are white blocks that always
    carry a hard shadow; tool entries are flat and only get the block, the colour and the shadow while open."""

    def __init__(self, parent, key, text, command, big=False, active_color=ACCENT):
        def build(p):
            frame = ctk.CTkFrame(p, fg_color="transparent", corner_radius=0, border_color=BORDER, border_width=0,
                                 width=10, height=48 if big else 34)
            frame.pack_propagate(False)
            self.size = 32
            self.icon = None
            if big:
                self.icon = tk.Canvas(frame, width=self.size, height=self.size, highlightthickness=0, bd=0)
                self.icon.pack(side="left", padx=(10, 8))
            self.label = ctk.CTkLabel(frame, text=text, anchor="w", font=(FONT, 14 if big else 12, "bold" if big else "normal"))
            self.label.pack(side="left", fill="x", expand=True, padx=(0 if big else 14, 0))
            return frame

        super().__init__(parent, build, depth=4 if big else 3)
        self.key, self.big, self.active_color, self.command = key, big, active_color, command
        self.active = self.hot = False
        for w in [self.inner, *self.inner.winfo_children()]:  # icon and label
            w.bind("<Button-1>", lambda _: self.command(), add="+")
            w.bind("<Enter>", self._enter, add="+")
            w.bind("<Leave>", self._leave, add="+")
        self.inner.configure(cursor="hand2")
        _TOGGLES.add(self)
        self.redraw()

    def _enter(self, _=None):
        self.hot = True
        self.redraw()

    def _leave(self, _=None):
        under = self.winfo_containing(*self.winfo_pointerxy())
        while under is not None:  # moving onto the icon or the label is not leaving the entry
            if under is self:
                return
            under = under.master
        self.hot = False
        self.redraw()

    def set_active(self, on):
        self.active = on
        self.redraw()

    def redraw(self):
        fill = self.active_color if self.active else HOVER if self.hot else RAISED if self.big else None
        bg = pick(fill if fill else PANEL)
        self.inner.configure(fg_color=fill or "transparent", border_width=EDGE if (self.active or self.big) else 0)
        self.label.configure(text_color=ON_ACCENT if self.active else TEXT)
        ink = "#111111" if self.active else pick(TEXT)
        if self.icon is not None:
            self.icon.configure(bg=bg)
            self.icon.delete("all")
            draw_icon(self.icon, self.key, self.size / 2, self.size / 2, self.size - 4, ink, pick(YELLOW))
        self.show_shadow(self.big or self.active)


class Logo(tk.Canvas):
    """The sidebar title: a yellow block with a hard shadow, an abstract mark (square, circle, triangle) and a two-line
    wordmark. Clicking it runs `command` (the usual way home)."""
    H = 82

    def __init__(self, parent, command=None):
        super().__init__(parent, height=self.H, highlightthickness=0, bd=0, cursor="hand2")
        self.command = command
        self.bind("<Configure>", lambda _: self.redraw())
        self.bind("<Button-1>", lambda _: self.command and self.command())
        _TOGGLES.add(self)

    def redraw(self):
        w, h = self.winfo_width(), self.H
        if w < 40:
            return
        ink = pick(INK)
        self.configure(bg=pick(PANEL))
        self.delete("all")
        self.create_rectangle(9, 9, w - 4, h - 4, fill=ink, outline=ink)  # hard shadow
        self.create_rectangle(3, 3, w - 10, h - 10, fill=pick(YELLOW), outline=ink, width=3)
        cy = (h - 7) / 2
        self.create_rectangle(16, cy - 6, 42, cy + 20, fill="#FFFFFF", outline=ink, width=3)
        self.create_polygon(38, cy + 20, 58, cy + 20, 48, cy + 2, fill=pick(CYAN), outline=ink, width=3)
        self.create_oval(14, cy - 22, 40, cy + 4, fill=pick(PINK), outline=ink, width=3)
        self.create_text(68, cy - 11, text="COMIC", anchor="w", font=(HEAD, 15), fill="#111111")
        self.create_text(68, cy + 11, text="TOOLKIT", anchor="w", font=(HEAD, 15), fill="#111111")


# ---------- abstract shapes ----------

_STRIPS = weakref.WeakSet()
_TOGGLES = weakref.WeakSet()
_SHAPE_FILLS = (YELLOW, PINK, CYAN, ("#FFFFFF", "#FFFFFF"), INK)


def _shape(c, kind, x, y, s, fill, ink):
    """One abstract shape in the box (x, y, s, s)."""
    kw = dict(fill=fill, outline=ink, width=EDGE)
    if kind == 0:
        c.create_oval(x, y, x + s, y + s, **kw)
    elif kind == 1:
        c.create_rectangle(x, y, x + s, y + s, **kw)
    elif kind == 2:
        c.create_polygon(x + s / 2, y, x + s, y + s, x, y + s, **kw)
    elif kind == 3:
        c.create_arc(x, y, x + s, y + s * 2, start=0, extent=180, style="pieslice", **kw)
    elif kind == 4:
        pts = []
        for i in range(6):
            pts += [x + i * s / 5, y + (s if i % 2 else 0)]
        c.create_line(*pts, fill=ink, width=EDGE + 1, joinstyle="miter")
    elif kind == 5:
        for i in range(4):
            c.create_rectangle(x + i * s / 4, y, x + i * s / 4 + s / 8, y + s, fill=ink, outline=ink)
    elif kind == 6:
        t = s / 3
        c.create_polygon(x + t, y, x + 2 * t, y, x + 2 * t, y + t, x + s, y + t, x + s, y + 2 * t, x + 2 * t, y + 2 * t,
                         x + 2 * t, y + s, x + t, y + s, x + t, y + 2 * t, x, y + 2 * t, x, y + t, x + t, y + t, **kw)
    else:
        c.create_oval(x, y, x + s, y + s, fill=ink, outline=ink)
        c.create_oval(x + s * .3, y + s * .3, x + s * .7, y + s * .7, fill=fill, outline=fill)


class AbstractStrip(tk.Canvas):
    """A band of abstract shapes (circles, triangles, zigzags, stripes, crosses) with a thick border. The pattern is
    fixed by `seed`, so a page always shows the same one. With a title it is a banner: the text sits on the left
    and the shapes fill the rest."""

    def __init__(self, parent, seed, height=40, title=None, subtitle=None, fill=None):
        super().__init__(parent, height=height, highlightthickness=0, bd=0)
        self.seed, self.title, self.subtitle, self.fill = seed, title, subtitle, fill
        _STRIPS.add(self)
        self.bind("<Configure>", lambda _: self.redraw())

    def redraw(self):
        c = self
        w, h = c.winfo_width(), int(c.cget("height"))
        c.delete("all")
        ink = pick(INK)
        c.configure(bg=pick(self.fill or PANEL))
        rnd = random.Random(self.seed)
        left = 24
        if self.title:
            c.create_text(left, h * .36, text=self.title, anchor="w", font=(HEAD, 28), fill=ON_ACCENT)
            c.create_text(left + 2, h * .74, text=self.subtitle or "", anchor="w", font=(FONT, 13, "bold"),
                          fill="#2B2B2B")
            left = max(left + 380, w * .45)
        s = h - 20
        x = left if self.title else 8
        while x + s < w - 8:
            kind = rnd.randrange(8)
            size = s if kind != 4 else s * 1.6
            fill = pick(rnd.choice(_SHAPE_FILLS))
            if fill == ink:
                fill = pick(PINK)
            _shape(c, kind, x, 10, s if kind != 4 else s * .9, fill, ink)
            x += size + rnd.randrange(8, 26)
        c.create_rectangle(EDGE / 2, EDGE / 2, w - EDGE / 2, h - EDGE / 2, outline=ink, width=EDGE)


def refresh_strips():
    """Redraw every strip (after the light/dark mode changes)."""
    for w in list(_STRIPS) + list(_TOGGLES):
        try:
            w.redraw()
        except tk.TclError:
            pass


def title_block(parent, title, subtitle):
    AbstractStrip(parent, seed=title, height=36).pack(fill="x", pady=(0, 14), padx=(0, 5))
    ctk.CTkLabel(parent, text=title.upper(), font=(HEAD, 22), text_color=TEXT, anchor="w").pack(fill="x")
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

        self.side_width = 310
        side = ctk.CTkFrame(self, fg_color=PANEL, width=self.side_width, corner_radius=0)
        side.pack(side="right", fill="y")
        side.pack_propagate(False)
        self.side = side
        self.splitter = Splitter(self, side, side="right", lo=270, hi=560, on_change=self._side_changed)
        self.splitter.pack(side="right", fill="y")
        self.footer = ctk.CTkFrame(side, fg_color=PANEL)
        self.footer.pack(side="bottom", fill="x", padx=20, pady=(8, 20))
        self.form = Form(side)
        self.form.pack(fill="both", expand=True, padx=(8, 0), pady=(14, 0))
        self.main = ctk.CTkFrame(self, fg_color=BG)
        self.main.pack(side="left", fill="both", expand=True, padx=(36, 28), pady=32)

        self.status = ctk.CTkLabel(self.footer, text="", font=(FONT, 12), text_color=MUTED,
                                   anchor="w", justify="left", wraplength=260)
        self.status.pack(fill="x", pady=(0, 8))

    def _side_changed(self, width):
        self.side_width = width

    def say(self, msg, err=False):
        self.status.configure(text=msg, text_color=DANGER if err else MUTED)

    def watch(self, *names, callback):
        for n in names:
            self.vars[n].trace_add("write", lambda *_: callback())

    def state(self):
        out = {}
        for k, v in self.vars.items():
            out[k] = v.get()
        out["_side_width"] = self.side_width
        return out

    def restore(self, saved):
        width = (saved or {}).get("_side_width")
        if isinstance(width, (int, float)):
            self.splitter.set_width(width)
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
        slider(q, from_=50, to=100, number_of_steps=50, variable=v["quality"], width=200).pack(side="left")
        qval = ctk.CTkLabel(q, text="", font=(FONT, 12, "bold"), text_color=TEXT, width=40)
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
        b.pack(side="left", padx=(8, 0))


# ---------- tables ----------

TREE_STYLE = "Comics.Treeview"


def build_tree(parent, columns, selectmode="browse", empty=None):
    """Bordered ttk table with a hard shadow and themed scrollbars. columns: (id, heading, width, stretch). Every
    column can be resized by dragging the edge of its heading."""
    st = ttk.Style()
    st.theme_use("clam")
    st.layout(TREE_STYLE, [("Treeview.treearea", {"sticky": "nswe"})])
    box = Shadow(parent, lambda p: ctk.CTkFrame(p, fg_color=WELL, border_color=BORDER, border_width=EDGE,
                                                corner_radius=0), depth=5)
    wrap = box.inner
    tree = ttk.Treeview(wrap, style=TREE_STYLE, show="headings", selectmode=selectmode,
                        columns=[c[0] for c in columns])
    for col, text, w, stretch in columns:
        tree.heading(col, text=text, anchor="w")
        tree.column(col, width=w, minwidth=24, stretch=stretch, anchor="w")  # drag a heading's edge to resize
    sb = ctk.CTkScrollbar(wrap, command=tree.yview, button_color=SCROLL, button_hover_color=MUTED, corner_radius=0)
    hsb = ctk.CTkScrollbar(wrap, command=tree.xview, orientation="horizontal", height=12,
                           button_color=SCROLL, button_hover_color=MUTED, corner_radius=0)
    tree.configure(yscrollcommand=sb.set, xscrollcommand=hsb.set)
    sb.pack(side="right", fill="y", padx=(0, 2), pady=4)
    hsb.pack(side="bottom", fill="x", padx=4, pady=(0, 2))
    tree.pack(side="left", fill="both", expand=True, padx=4, pady=4)
    apply_tree_theme(tree)
    hint = ctk.CTkLabel(wrap, text=empty or "", font=(FONT, 14, "bold"), text_color=MUTED, fg_color=WELL,
                        wraplength=420, justify="center")

    def check():
        """Show the hint while the table has no rows."""
        try:
            if hint.cget("text") and not tree.get_children():
                hint.place(relx=0.5, rely=0.45, anchor="center")
            else:
                hint.place_forget()
            tree.after(350, check)
        except tk.TclError:
            pass  # the table is gone

    def set_empty(text):
        hint.configure(text=text)
    box.set_empty = set_empty
    check()
    return box, tree


def apply_tree_theme(tree):
    """ttk widgets don't follow customtkinter's mode, so restyle them by hand."""
    st = ttk.Style()
    st.configure(TREE_STYLE, background=pick(WELL), fieldbackground=pick(WELL), foreground=pick(TEXT),
                 rowheight=30, borderwidth=0, font=(FONT, 11))
    st.configure(TREE_STYLE + ".Heading", background=pick(ACCENT), foreground=ON_ACCENT, relief="flat",
                 font=(FONT, 10, "bold"), padding=(8, 6))
    st.map(TREE_STYLE, background=[("selected", pick(SELECT_BG))], foreground=[("selected", pick(TEXT))])
    tree.tag_configure("bad", foreground=pick(DANGER))
    tree.tag_configure("dim", foreground=pick(MUTED))

"""Shared look and widgets: palette, styled controls, form rows, drop zone, page scaffold."""
import random
import sys
import time
import tkinter as tk
import traceback
from pathlib import Path
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
FOCUS = ("#1F4FFF", "#7FE0FF")                # the keyboard focus ring
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
TYPE_SEGMENT = (FONT, 15, "bold")       # type scale: page title is HEAD 22; then these
TYPE_BODY = (FONT, 13)
TYPE_HINT = (FONT, 11)
TYPE_MONO = ("Consolas", 12)            # paths and templates only
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
        self.configure(takefocus=1)
        self.focused = False
        self.bind("<FocusIn>", lambda _: self._focus(True), add="+")
        self.bind("<FocusOut>", lambda _: self._focus(False), add="+")
        self.bind("<Left>", lambda _: self._nudge(-1))
        self.bind("<Right>", lambda _: self._nudge(1))
        self.var.trace_add("write", lambda *_: self.redraw())
        _TOGGLES.add(self)

    def _focus(self, on):
        self.focused = on
        self.redraw()

    def _nudge(self, direction):
        """Arrow keys move the handle one step."""
        step = (self.hi - self.lo) / (self.steps or 20)
        val = min(self.hi, max(self.lo, float(self.var.get()) + direction * step))
        self.var.set(val)
        if self.command:
            self.command(val)

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
        self.create_rectangle(x, 3, x + k, h - 4, fill=pick(ACCENT), outline=pick(FOCUS) if self.focused else ink, width=3)


def slider(parent, **kw):
    return Slider(parent, **kw)


# ---------- hints and run feedback ----------

class _Tip:
    """A small yellow label that appears under a control after the pointer rests on it."""

    def __init__(self, widget, text):
        self.widget, self.text, self.win, self._job = widget, text, None, None
        widget.bind("<Enter>", self._later, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress-1>", self._hide, add="+")

    def _later(self, _=None):
        self._hide()
        self._job = self.widget.after(550, self._show)

    def _show(self):
        self._job = None
        try:
            x, y = self.widget.winfo_rootx(), self.widget.winfo_rooty() + self.widget.winfo_height() + 6
            self.win = tk.Toplevel(self.widget)
            self.win.wm_overrideredirect(True)
            self.win.wm_geometry(f"+{x}+{y}")
            tk.Label(self.win, text=self.text, font=(FONT, 10, "bold"), bg=pick(YELLOW), fg="#111111", bd=0,
                     padx=8, pady=3, highlightthickness=2, highlightbackground=pick(INK)).pack()
        except tk.TclError:
            self.win = None

    def _hide(self, _=None):
        if self._job is not None:
            try:
                self.widget.after_cancel(self._job)
            except tk.TclError:
                pass
            self._job = None
        if self.win is not None:
            try:
                self.win.destroy()
            except tk.TclError:
                pass
            self.win = None


def popup_menu(anchor, items, above=False, at=None):
    """A square, bordered pop-up list with a hard shadow under `anchor` (over it with above=True, for buttons at the
    bottom of a window), in place of the native Windows menu. items is a list of (label, command); a command of None
    makes a greyed, unclickable line. It closes on a click, Esc or when focus leaves; Up, Down and Enter work too.
    `at=(x, y)` (screen coordinates) opens it at that point instead of under `anchor`."""
    top = tk.Toplevel(anchor)
    top.wm_overrideredirect(True)
    top.attributes("-topmost", True)
    key = "#010203"
    top.configure(bg=key)
    try:
        top.attributes("-transparentcolor", key)  # Windows: the corner outside the shadow stays see-through
    except tk.TclError:
        pass
    ink, depth = pick(INK), 5
    tk.Frame(top, bg=ink).place(x=depth, y=depth, relwidth=1, relheight=1, width=-depth, height=-depth)
    body = tk.Frame(top, bg=pick(PANEL), highlightthickness=EDGE, highlightbackground=ink, bd=0)
    body.place(x=0, y=0, relwidth=1, relheight=1, width=-depth, height=-depth)
    rows, state = [], {"i": -1}

    def close(_=None):
        try:
            top.destroy()
        except tk.TclError:
            pass

    def paint():
        for n, (lab, cmd) in enumerate(rows):
            on = n == state["i"] and cmd is not None
            lab.configure(bg=pick(PINK) if on else pick(PANEL), fg="#111111" if on else (pick(TEXT) if cmd else pick(MUTED)))

    def run(n):
        cmd = items[n][1]
        if cmd is not None:
            close()
            cmd()

    for n, (text, cmd) in enumerate(items):
        lab = tk.Label(body, text=text, anchor="w", font=(FONT, 11), padx=14, pady=7, bd=0,
                       cursor="hand2" if cmd else "arrow")
        lab.pack(fill="x", padx=EDGE, pady=(EDGE if n == 0 else 0, EDGE if n == len(items) - 1 else 0))
        lab.bind("<Enter>", lambda _, n=n: (state.update(i=n), paint()))
        lab.bind("<Button-1>", lambda _, n=n: run(n))
        rows.append((lab, cmd))
    paint()

    def move(d):
        usable = [n for n, (_, c) in enumerate(items) if c is not None]
        if usable:
            cur = usable.index(state["i"]) if state["i"] in usable else (-1 if d > 0 else 0)
            state["i"] = usable[(cur + d) % len(usable)]
            paint()
        return "break"
    top.bind("<Up>", lambda _: move(-1))
    top.bind("<Down>", lambda _: move(1))
    top.bind("<Return>", lambda _: run(state["i"]) if state["i"] >= 0 else None)
    top.bind("<Escape>", close)
    top.update_idletasks()
    # the pieces are placed, not packed, so the window does not size itself: add the rows up
    w = max(max(lab.winfo_reqwidth() for lab, _ in rows) + 2 * EDGE, 0 if at else anchor.winfo_width())
    h = sum(lab.winfo_reqheight() for lab, _ in rows) + 2 * EDGE
    if at:
        x, y = at[0], min(at[1], max(0, top.winfo_screenheight() - h - depth - 40))
        x = min(x, max(0, top.winfo_screenwidth() - w - depth - 10))
    else:
        x = anchor.winfo_rootx()
        y = anchor.winfo_rooty() - h - depth - 4 if above else anchor.winfo_rooty() + anchor.winfo_height() + 4
    top.geometry(f"{w + depth}x{h + depth}+{x}+{y}")
    top.focus_force()
    top.after(150, lambda: top.bind("<FocusOut>", close))  # not at once: opening may move focus around
    top.popup_rows = rows  # for tests
    return top


def _result_icon(c, key, size=38):
    """The small white tile in front of a search result: the page's line icon, or a plain symbol for actions."""
    ink = "#111111"
    c.delete("all")
    c.create_rectangle(0, 0, size, size, fill="#FFFFFF", outline="#FFFFFF")  # a white tile, whatever the row colour
    mid = size / 2
    if key == "__theme__":
        c.create_oval(mid - 11, mid - 11, mid + 11, mid + 11, fill="#FFFFFF", outline=ink, width=3)
        c.create_arc(mid - 11, mid - 11, mid + 11, mid + 11, start=90, extent=180, fill=ink, outline=ink)
    elif key == "__library__":
        draw_icon(c, "icons", mid, mid, size - 10, ink, pick(YELLOW))
    else:
        draw_icon(c, key, mid, mid, size - 10, ink, pick(YELLOW))
    c.create_rectangle(1.5, 1.5, size - 1.5, size - 1.5, outline=ink, width=3)


def spotlight(app, entries, on_pick, placeholder="Search pages and actions"):
    """A floating search bar in the upper middle of the app with results under it, each a bold title over a smaller
    description. entries: (key, title, description, kind). Type to filter, Up and Down to move, Enter to open,
    Esc or a click elsewhere to close. on_pick(key) runs after it closes."""
    W, DEPTH, ROWS, ROW_H = 660, 7, 7, 60
    top = tk.Toplevel(app)
    top.wm_overrideredirect(True)
    top.attributes("-topmost", True)
    keycolor = "#010203"
    top.configure(bg=keycolor)
    try:
        top.attributes("-transparentcolor", keycolor)
    except tk.TclError:
        pass
    ink = pick(INK)
    tk.Frame(top, bg=ink).place(x=DEPTH, y=DEPTH, relwidth=1, relheight=1, width=-DEPTH, height=-DEPTH)
    body = tk.Frame(top, bg=pick(PANEL), highlightthickness=EDGE, highlightbackground=ink, bd=0)
    body.place(x=0, y=0, relwidth=1, relheight=1, width=-DEPTH, height=-DEPTH)

    # the search bar
    bar = tk.Frame(body, bg=pick(WELL))
    bar.pack(fill="x", padx=EDGE, pady=(EDGE, 0))
    glass = tk.Canvas(bar, width=34, height=34, bg=pick(WELL), highlightthickness=0, bd=0)
    glass.pack(side="left", padx=(20, 4), pady=14)
    glass.create_oval(5, 5, 21, 21, outline=pick(TEXT), width=3)
    glass.create_line(19, 19, 29, 29, fill=pick(TEXT), width=4)
    query = tk.StringVar()
    box = tk.Entry(bar, textvariable=query, font=(FONT, 20), bd=0, highlightthickness=0, bg=pick(WELL), fg=pick(TEXT),
                   insertbackground=pick(TEXT), insertwidth=3)
    box.pack(side="left", fill="x", expand=True, padx=(8, 20), pady=14, ipady=4)
    tk.Frame(body, bg=ink, height=EDGE).pack(fill="x", padx=EDGE)
    holder = tk.Frame(body, bg=pick(PANEL))
    holder.pack(fill="x", padx=EDGE)
    foot = tk.Label(body, font=(FONT, 10), bg=pick(PANEL), fg=pick(MUTED), anchor="w", padx=18, pady=7,
                    text="Up and Down to move  ·  Enter to open  ·  Esc to close")
    foot.pack(fill="x", padx=EDGE, pady=(0, EDGE))

    # a fixed set of result rows, filled in as you type
    rows = []
    for n in range(ROWS):
        row = tk.Frame(holder, height=ROW_H, bd=0)
        row.pack_propagate(False)
        icon = tk.Canvas(row, width=38, height=38, highlightthickness=0, bd=0)
        icon.pack(side="left", padx=(18, 14))
        words = tk.Frame(row, bd=0)
        words.pack(side="left", fill="x", expand=True)
        title = tk.Label(words, font=(FONT, 13, "bold"), anchor="w", bd=0)
        title.pack(fill="x", pady=(10, 0))
        sub = tk.Label(words, font=(FONT, 11), anchor="w", bd=0)
        sub.pack(fill="x")
        kind = tk.Label(row, font=(FONT, 10, "bold"), bd=0, padx=18)
        kind.pack(side="right")
        parts = (row, icon, words, title, sub, kind)
        for w in parts:
            w.bind("<Enter>", lambda _, n=n: select(n))
            w.bind("<Button-1>", lambda _, n=n: go(n))
        rows.append(dict(row=row, icon=icon, words=words, title=title, sub=sub, kind=kind))
    state = {"shown": [], "first": 0, "sel": 0}

    def match(text):
        text = text.strip().lower()
        if not text:
            return list(entries)
        scored = []
        for e in entries:
            t, d = e[1].lower(), e[2].lower()
            if t.startswith(text):
                scored.append((0, e))
            elif text in t:
                scored.append((1, e))
            elif text in d:
                scored.append((2, e))
        return [e for _, e in sorted(scored, key=lambda s: s[0])]

    def paint():
        shown, first, sel = state["shown"], state["first"], state["sel"]
        for n, r in enumerate(rows):
            i = first + n
            if i >= len(shown):
                r["row"].pack_forget()
                continue
            key, name, desc, kind = shown[i]
            on = i == sel
            bg = pick(PINK) if on else pick(PANEL)
            fg, sub = ("#111111", "#2B2B2B") if on else (pick(TEXT), pick(MUTED))
            r["row"].pack(fill="x")
            for w in (r["row"], r["words"]):
                w.configure(bg=bg)
            r["icon"].configure(bg=bg)
            _result_icon(r["icon"], key)
            r["title"].configure(text=name, bg=bg, fg=fg)
            r["sub"].configure(text=desc, bg=bg, fg=sub)
            r["kind"].configure(text=kind.upper(), bg=bg, fg=sub)
        if not shown:  # nothing matches: say so in the first row
            r = rows[0]
            r["row"].pack(fill="x")
            for w in (r["row"], r["words"], r["icon"]):
                w.configure(bg=pick(PANEL))
            r["icon"].delete("all")
            r["title"].configure(text=f"No match for “{query.get().strip()}”", bg=pick(PANEL), fg=pick(TEXT))
            r["sub"].configure(text="Try part of a page name, such as rename or stats", bg=pick(PANEL), fg=pick(MUTED))
            r["kind"].configure(text="", bg=pick(PANEL))
        top.update_idletasks()
        height = body.winfo_reqheight()
        top.geometry(f"{W + DEPTH}x{height + DEPTH}+{top.winfo_x()}+{top.winfo_y()}")

    def refresh(*_):
        state.update(shown=match(query.get()), first=0, sel=0)
        paint()

    def select(n):
        i = state["first"] + n
        if i < len(state["shown"]) and i != state["sel"]:
            state["sel"] = i
            paint()

    def move(d):
        count = len(state["shown"])
        if count:
            sel = (state["sel"] + d) % count
            state["sel"] = sel
            if sel < state["first"]:
                state["first"] = sel
            elif sel >= state["first"] + ROWS:
                state["first"] = sel - ROWS + 1
            paint()
        return "break"

    def close(_=None):
        try:
            top.destroy()
        except tk.TclError:
            pass

    def go(n=None):
        i = state["sel"] if n is None else state["first"] + n
        if i < len(state["shown"]):
            key = state["shown"][i][0]
            close()
            on_pick(key)

    def focus_lost(_=None):
        top.after(150, lambda: close() if top.winfo_exists() and top.focus_displayof() is None else None)

    query.trace_add("write", refresh)
    box.bind("<Down>", lambda _: move(1))
    box.bind("<Up>", lambda _: move(-1))
    box.bind("<Return>", lambda _: go())
    box.bind("<Escape>", close)
    top.bind("<Escape>", close)
    x = app.winfo_rootx() + (app.winfo_width() - W) // 2
    y = app.winfo_rooty() + int(app.winfo_height() * 0.2)
    top.geometry(f"+{x}+{y}")
    refresh()
    top.focus_force()
    box.focus_set()
    top.after(250, lambda: top.bind("<FocusOut>", focus_lost))
    top.query, top.entry, top.go = query, box, go  # for tests
    top.titles = lambda: [e[1] for e in state["shown"]]
    top.visible = lambda: [r for r in rows if r["row"].winfo_manager()]
    return top


def tooltip(widget, text):
    """Name a control that only shows an icon or a symbol."""
    return _Tip(widget, text)


def eta_text(done, total, started):
    """'37 of 120, about 40s left'. The estimate waits for a few items so it is not wild."""
    elapsed = time.time() - started
    if done < 3 or elapsed < 2 or total <= done:
        return f"{done} of {total}"
    left = elapsed / done * (total - done)
    return f"{done} of {total}, about " + (f"{int(left)}s" if left < 90 else f"{round(left / 60)} min") + " left"


def flash_taskbar(window):
    """Make the app's taskbar button flash until it is clicked (a long run has finished). Windows only."""
    if sys.platform != "win32":
        return

    import ctypes

    class FLASHWINFO(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_uint), ("hwnd", ctypes.c_void_p), ("dwFlags", ctypes.c_uint),
                    ("uCount", ctypes.c_uint), ("dwTimeout", ctypes.c_uint)]
    try:
        info = FLASHWINFO(ctypes.sizeof(FLASHWINFO), int(window.wm_frame(), 16), 3 | 12, 0, 0)  # all, until focused
        ctypes.windll.user32.FlashWindowEx(ctypes.byref(info))
    except (OSError, ValueError, AttributeError, tk.TclError):
        pass


# ---------- hovering ----------
# Enter and Leave events are unreliable on customtkinter widgets (several canvases and labels sit on top of each
# other, and a control that slides under the pointer fires them in pairs). Instead one timer asks Tk which widget is
# under the pointer and tells the nearest control that registered a `_hover` pair (warm, cool) about it.
_HOVER = {"root": None, "now": None}


def _hover_target(widget):
    while widget is not None:
        hooks = widget.__dict__.get("_hover_hooks")
        if hooks:
            return widget, hooks
        widget = getattr(widget, "master", None)
    return None, None


def _hover_tick(root):
    try:
        x, y = root.winfo_pointerxy()
        try:
            under = root.winfo_containing(x, y)
        except (tk.TclError, KeyError):  # a pop-up list's window is not one we know
            under = None
        target, hooks = _hover_target(under)
        prev = _HOVER["now"]
        if target is not prev:
            try:
                if prev is not None:
                    prev.__dict__["_hover_hooks"][1]()
            except (tk.TclError, KeyError):
                pass  # the control that lost the pointer is gone
            except Exception:  # noqa: BLE001 - one broken hook must not stop every other hover for good
                traceback.print_exc()
            _HOVER["now"] = target
            try:
                if hooks:
                    hooks[0]()
            except tk.TclError:
                pass
            except Exception:  # noqa: BLE001
                traceback.print_exc()
        root.after(40, lambda: _hover_tick(root))
    except tk.TclError:  # the window is gone: the next control to register starts a new timer
        _HOVER["root"] = _HOVER["now"] = None


def ensure_hover(widget):
    """Start the hover timer for this widget's window if it is not running."""
    root = widget.winfo_toplevel()
    if _HOVER["root"] is None or _HOVER["root"] is not root:
        try:
            if _HOVER["root"] is not None and _HOVER["root"].winfo_exists():
                return  # one window at a time is enough: pop-ups share the main window's pointer
        except tk.TclError:
            pass
        _HOVER["root"] = root
        root.after(60, lambda: _hover_tick(root))


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
            self.__dict__["_hover_hooks"] = (self._warm, self._cool)
            ensure_hover(self)

    # -- keyboard
    def make_focusable(self, on_activate=None, ring="border"):
        """Let Tab reach this control. A blue ring shows while it has focus; Enter or Space presses it (the wrapped
        widget's invoke(), or on_activate). ring says what turns blue: the widget's "border", the black frame round it
        ("slot"), or its fill ("fg")."""
        tk.Frame.configure(self.slot, takefocus=1)
        self.__dict__["_activate"] = on_activate
        self.__dict__["_ring_mode"] = ring
        # CTkFrame.bind binds its inner canvas; the frame itself is what takes the focus
        tk.Frame.bind(self.slot, "<FocusIn>", lambda _: self._ring(True), "+")
        tk.Frame.bind(self.slot, "<FocusOut>", lambda _: self._ring(False), "+")
        for key in ("<Return>", "<space>"):
            tk.Frame.bind(self.slot, key, self._fire, "+")
        return self

    def _ring(self, on):
        mode = self.__dict__.get("_ring_mode", "border")
        try:
            if mode == "slot":
                self.slot.configure(fg_color=FOCUS if on else INK)
            elif mode == "fg":
                self.inner.configure(fg_color=FOCUS if on else INK)
            else:
                self.inner.configure(border_color=FOCUS if on else BORDER)
        except (tk.TclError, ValueError):
            pass

    def _fire(self, _=None):
        if self._disabled():
            return "break"
        act = self.__dict__.get("_activate")
        if act:
            act()
        else:
            self.inner.invoke()
        return "break"

    # -- shadow and motion
    def show_shadow(self, on):
        """Show or hide the shadow block (the open item of the sidebar has one, the others don't)."""
        self.block.grid() if on else self.block.grid_remove()

    def _shift(self, n):
        self._off = n
        k = self._get_widget_scaling()  # the first layout went through customtkinter's scaling, so this must too
        pad = (int(n * k), int((self.depth - n) * k))  # int() like customtkinter, so rest and cool match exactly
        self.slot.grid_configure(padx=pad, pady=pad)

    def _disabled(self):
        try:
            return str(self.inner.cget("state")) == "disabled"
        except (tk.TclError, ValueError, AttributeError):
            return False

    def _bind_motion(self, w):
        """Press and release come from the widgets themselves; hovering is found by ensure_hover()'s pointer check."""
        w.bind("<ButtonPress-1>", self._press, add="+")
        w.bind("<ButtonRelease-1>", self._release, add="+")
        for c in w.winfo_children():
            self._bind_motion(c)

    def _alive(self):
        try:
            return bool(self.winfo_exists())
        except tk.TclError:
            return False

    def _warm(self):
        """The pointer is over this control: the face slides half way toward its shadow."""
        if self._alive() and not self._disabled():
            self._hot = True
            self._shift(max(1, self.depth // 2))

    def _cool(self):
        if self._alive():
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
    return sh.make_focusable()


def menu(parent, var, values, width=260):
    sh = Shadow(parent, lambda p: ctk.CTkOptionMenu(
        p, variable=var, values=values, width=width, height=32, corner_radius=0, anchor="w",
        font=(FONT, 13), dropdown_font=(FONT, 13), fg_color=RAISED, button_color=ACCENT,
        button_hover_color=ACCENT_HOVER, text_color=TEXT, dropdown_fg_color=RAISED,
        dropdown_text_color=TEXT, dropdown_hover_color=HOVER), depth=3, edge=EDGE)
    # Tab reaches it; Enter or Space opens the list
    return sh.make_focusable(lambda: sh.inner._open_dropdown_menu(), ring="slot")


def segmented(parent, var, values, width=260):
    sh = Shadow(parent, lambda p: ctk.CTkSegmentedButton(
        p, variable=var, values=values, width=width, height=30, corner_radius=0, border_width=EDGE,
        font=(FONT, 12, "bold"), fg_color=INK, unselected_color=SEG_OFF, unselected_hover_color=HOVER,
        selected_color=SEG_ON, selected_hover_color=SEG_ON, text_color=ON_ACCENT), depth=3)

    def step(d):
        vals = list(values)
        cur = vals.index(var.get()) if var.get() in vals else 0
        var.set(vals[(cur + d) % len(vals)])
    sh.make_focusable(lambda: step(1), ring="fg")  # Enter or Space: next choice; Left and Right: previous and next
    tk.Frame.bind(sh.slot, "<Left>", lambda _: step(-1), "+")
    tk.Frame.bind(sh.slot, "<Right>", lambda _: step(1), "+")
    return sh


def entry(parent, var, **kw):
    sh = Shadow(parent, lambda p: ctk.CTkEntry(
        p, textvariable=var, height=34, corner_radius=0, font=(FONT, 13),
        fg_color=WELL, border_color=BORDER, border_width=EDGE, text_color=TEXT, **kw), depth=3)
    sh.inner.bind("<FocusIn>", lambda _: sh.inner.configure(border_color=FOCUS), add="+")
    sh.inner.bind("<FocusOut>", lambda _: sh.inner.configure(border_color=BORDER), add="+")
    return sh


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
        text_color_disabled=MUTED, border_width=2, border_color=BORDER), depth=3, motion=True).make_focusable()


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


class FlowRow(ctk.CTkFrame):
    """A row of widgets that wraps onto more rows when the room is too narrow, so nothing is cut off. `add(widget)` puts the
    next one in; `add(divider, divider=True)` is a rule between groups, which is never left at the start or end of a line."""

    def __init__(self, parent, gap=6):
        super().__init__(parent, fg_color="transparent")
        self.items = []     # (widget, is_divider)
        self.gap = gap
        self._width = 0
        self._pending = None
        self.bind("<Configure>", self._configured)

    def add(self, widget, divider=False):
        self.items.append((widget, divider))
        self._schedule()

    def _configured(self, e):
        if e.width != self._width:
            self._width = e.width
            self._schedule()

    def _schedule(self):
        if self._pending is None:
            self._pending = self.after_idle(self.layout)

    def layout(self):
        self._pending = None
        self.update_idletasks()   # (the buttons settle on their real size first)
        scale = self._get_widget_scaling()
        gap = max(1, round(self.gap * scale))
        room = self._width if self._width > 40 else 10 ** 6   # not laid out yet: one row
        lines, line, used = [], [], 0
        for w, div in self.items:
            need = w.winfo_reqwidth() + gap
            if line and used + need > room:
                lines.append(line)
                line, used = [], 0
            line.append((w, div))
            used += need
        if line:
            lines.append(line)
        shown = set()
        y = 0
        for line in lines:
            while line and line[0][1]:    # no rule at the start of a line
                line = line[1:]
            while line and line[-1][1]:   # nor at the end
                line = line[:-1]
            if not line:
                continue
            x, tall = 0, max(w.winfo_reqheight() for w, _ in line)
            for w, _ in line:
                k = scale if hasattr(w, "_apply_widget_scaling") else 1   # (customtkinter widgets scale what they are placed at)
                w.place(x=x / k, y=(y + (tall - w.winfo_reqheight()) // 2) / k)   # one by one: wrapped rows must not share columns
                shown.add(w)
                x += w.winfo_reqwidth() + gap
            y += tall + gap
        for w, _ in self.items:
            if w not in shown:
                w.place_forget()
        self.configure(height=max(1, (y - gap) / scale))


class DropZone(Shadow):
    """The 'add your comics' box. With on_folder / on_files it also carries an Add folder and a Choose comics button,
    so every page offers both in the same place."""

    def __init__(self, parent, prompt, on_click, on_folder=None, on_files=None,
                 folder_text="Add folder…", files_text="Choose comics…", files_first=False, compact=False):
        """`compact`: a slim box for pages whose list needs the room: the prompt in one line and every button (the app adds
        Library folder and Recent, a page may add its own with `add_extra`) in one wrapping row."""
        pair = [("folder", folder_text, on_folder), ("files", files_text, on_files)]
        buttons = [(k, t, None, c) for k, t, c in (pair[::-1] if files_first else pair) if c]
        super().__init__(parent, lambda p: ctk.CTkFrame(
            p, fg_color=WELL, border_color=BORDER, border_width=EDGE, corner_radius=0,
            height=104 if buttons else 88), depth=5)
        box = self.inner
        self.compact = compact
        if not compact:
            box.pack_propagate(False)
        self._row = None
        self.prompt = prompt
        self.buttons = {}
        if compact:
            self.label = ctk.CTkLabel(box, text=prompt, font=(FONT, 12, "bold"), text_color=MUTED, anchor="w")
            self.label.pack(fill="x", padx=12, pady=(8, 4))
            self.flow = FlowRow(box)
            self.flow.pack(fill="x", padx=10, pady=(0, 2))
            self._row = self.flow
            for k, t, _w, c in buttons:
                self.buttons[k] = tool_button(self.flow, t, c, None)
                self.flow.add(self.buttons[k])
            if self.buttons:
                next(iter(self.buttons.values())).configure(fg_color=ACCENT, text_color=ON_ACCENT, hover_color=ACCENT_HOVER)
        else:
            self.label = ctk.CTkLabel(box, text=prompt, font=(FONT, 14, "bold"), text_color=MUTED)
        if compact:
            pass
        elif buttons:
            row = ctk.CTkFrame(box, fg_color="transparent")
            row.pack(side="bottom", pady=(0, 12))
            self._row = row
            self.buttons = toolbar(row, *[[b] for b in buttons])
            first = next(iter(self.buttons.values()))
            first.configure(fg_color=ACCENT, text_color=ON_ACCENT, hover_color=ACCENT_HOVER)  # the main way in
            self.label.pack(expand=True, pady=(8, 0))
        else:
            self.label.pack(expand=True)
        for w in (box, self.label):
            w.bind("<Button-1>", lambda _: on_click())
        self.__dict__["_hover_hooks"] = (lambda: box.configure(fg_color=HOVER), lambda: box.configure(fg_color=WELL))
        ensure_hover(self)

    def set(self, text=None):
        self.label.configure(text=text or self.prompt, text_color=TEXT if text else MUTED)

    def add_extra(self, key, text, command, width=None):
        """A button of the page's own at the end of a compact box's row (not counted among `buttons`)."""
        if not self.compact:
            return None
        self.extra = getattr(self, "extra", {})
        self.extra[key] = tool_button(self.flow, text, command, width)
        self.flow.add(self.extra[key])
        return self.extra[key]

    def add_shortcuts(self, on_library, get_recent, on_open):
        """Two quick ways in on a line under Add folder: *Library folder* (the folder Library stats scans) and *Recent*, a menu of the folders
        used lately. get_recent() returns folder paths; on_open(path) uses one."""
        if self._row is None:
            return

        def show_recent():
            def where(p):  # the folder's parent, shortened from the left so the list stays narrow
                text = str(Path(p).parent)
                return text if len(text) <= 42 else "…" + text[-41:]
            items = [(f"{Path(p).name}    {where(p)}", lambda p=p: on_open(p)) for p in get_recent()]
            popup_menu(self.buttons["recent"], items or [("No recent folders yet", None)])
        if self.compact:   # in the one row, before the page's own buttons
            self.buttons["library"] = tool_button(self.flow, "Library folder", on_library, 116)
            self.buttons["recent"] = tool_button(self.flow, "Recent ▾", show_recent, 88)
            mine = list(getattr(self, "extra", {}).values())
            for w in mine:
                self.flow.items = [it for it in self.flow.items if it[0] is not w]
            self.flow.add(self.buttons["library"])
            self.flow.add(self.buttons["recent"])
            for w in mine:
                self.flow.add(w)
            return
        row = ctk.CTkFrame(self.inner, fg_color="transparent")  # a second, smaller line under the main buttons
        row.pack(side="bottom", pady=(0, 8), before=self._row)
        self.inner.configure(height=140)
        self.buttons["library"] = tool_button(row, "Library folder", on_library, 116)
        self.buttons["library"].pack(side="left", padx=(0, 6))
        self.buttons["recent"] = tool_button(row, "Recent ▾", show_recent, 88)
        self.buttons["recent"].pack(side="left")


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
        self.focused = False
        for key in ("<space>", "<Return>"):
            self.cv.bind(key, self.toggle, add="+")
        self.cv.bind("<FocusIn>", lambda _: self._focus(True), add="+")
        self.cv.bind("<FocusOut>", lambda _: self._focus(False), add="+")
        self.var.trace_add("write", lambda *_: self.redraw())
        _TOGGLES.add(self)
        self.redraw()

    def _focus(self, on):
        self.focused = on
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
        c.create_rectangle(2, 2, w - 4, h - 4, fill=pick(PINK if on else SWITCH_OFF),
                        outline=pick(FOCUS) if self.focused else ink, width=3)
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
        self.__dict__["_hover_hooks"] = (self._enter, self._leave)
        ensure_hover(self)
        self.inner.configure(cursor="hand2")
        self.focused = False
        tk.Frame.configure(self.inner, takefocus=1)
        tk.Frame.bind(self.inner, "<FocusIn>", lambda _: self._focus(True), "+")
        tk.Frame.bind(self.inner, "<FocusOut>", lambda _: self._focus(False), "+")
        for key in ("<Return>", "<space>"):
            tk.Frame.bind(self.inner, key, lambda _: self.command(), "+")
        _TOGGLES.add(self)
        self.redraw()

    def _focus(self, on):
        self.focused = on
        self.redraw()

    def _enter(self, _=None):
        self.hot = True
        self.redraw()

    def _leave(self, _=None):
        self.hot = False
        self.redraw()

    def set_active(self, on):
        self.active = on
        self.redraw()

    def redraw(self):
        fill = self.active_color if self.active else HOVER if self.hot else RAISED if self.big else None
        bg = pick(fill if fill else PANEL)
        self.inner.configure(fg_color=fill or "transparent", border_width=EDGE if (self.active or self.big or self.focused) else 0,
                             border_color=FOCUS if self.focused else BORDER)
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


def title_block(parent, title, subtitle, strip=True):
    if strip:
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

    def primary_action(self):
        """Press the page's main (yellow) button if it can be used: the Ctrl+Enter shortcut."""
        for w in self.footer.winfo_children():
            dim = w.__dict__.get("dim")
            if dim and dim[0] == ACCENT:
                if str(w.cget("state")) != "disabled":
                    w.invoke()
                return True
        return False

    def stop_action(self):
        """Press Stop while a run is going: the Esc shortcut."""
        b = getattr(self, "btn_stop", None)
        if b is not None and b.winfo_ismapped() and str(b.cget("state")) != "disabled":
            b.invoke()

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


def build_tree(parent, columns, selectmode="browse", empty=None, style=TREE_STYLE, picture=False):
    """Bordered ttk table with a hard shadow and themed scrollbars. columns: (id, heading, width, stretch). Every
    column can be resized by dragging the edge of its heading. `style` gives a table its own ttk style (so its row
    height can differ); `picture` adds a first column, hidden until its width is set, that can hold a small image."""
    st = ttk.Style()
    st.theme_use("clam")
    st.layout(style, [("Treeview.treearea", {"sticky": "nswe"})])
    box = Shadow(parent, lambda p: ctk.CTkFrame(p, fg_color=WELL, border_color=BORDER, border_width=EDGE,
                                                corner_radius=0), depth=5)
    wrap = box.inner
    tree = ttk.Treeview(wrap, style=style, show=("tree", "headings") if picture else "headings", selectmode=selectmode,
                        columns=[c[0] for c in columns])
    if picture:
        tree.column("#0", width=0, minwidth=0, stretch=False)
        tree.heading("#0", text="")
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
    style = str(tree.cget("style")) or TREE_STYLE
    st.configure(style, background=pick(WELL), fieldbackground=pick(WELL), foreground=pick(TEXT),
                 rowheight=tree.__dict__.get("_rowheight", 30), borderwidth=0, font=(FONT, 11))
    st.configure(style + ".Heading", background=pick(ACCENT), foreground=ON_ACCENT, relief="flat",
                 font=(FONT, 10, "bold"), padding=(8, 6))
    st.map(style, background=[("selected", pick(SELECT_BG))], foreground=[("selected", pick(TEXT))])
    tree.tag_configure("bad", foreground=pick(DANGER))
    tree.tag_configure("dim", foreground=pick(MUTED))

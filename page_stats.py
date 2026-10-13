"""Library stats page: scan a library once and see it as a dashboard (totals, bars per series, publisher, year and format,
metadata coverage, the biggest files). Click a bar to list the comics behind it. Nothing here changes a file."""
import csv
import os
import queue
import threading
import tkinter as tk
from dataclasses import dataclass, field
from pathlib import Path
from tkinter import filedialog, font as tkfont

import customtkinter as ctk

import stats_core as sc
from library_scan import scan_library
from ui_kit import (ACCENT, BG, BORDER, FONT, MUTED, PANEL, SELECT_BG, TEXT, Page, apply_tree_theme,
                    build_tree, button, divider, menu, pick, switch_style, title_block, tool_button)

EXPORTS = ["Series", "Publishers", "Years", "Formats", "Coverage", "Largest"]
ROW = 26  # height of one bar row, in pixels


@dataclass
class Item:
    """One bar: its label, how long it is (0 to 1), the text at its end and the comics behind it."""
    label: str
    frac: float
    text: str
    issues: list = field(default_factory=list)


def row_items(rows):
    # an "Other (n more)" bar lumps many rows together, so it must not set the scale for the real ones
    top = max((r.count for r in rows if not r.label.startswith("Other (")), default=0) or max((r.count for r in rows), default=1)
    return [Item(r.label, min(1.0, r.count / top), f"{r.count:,}  ·  {sc.human_size(r.bytes)}", r.issues) for r in rows]


def _run(q, root, o, stop):
    """Worker: scan the library. No Tk calls; any failure is reported instead of leaving the page waiting."""
    try:
        res = scan_library(root, o["recursive"], deep=o["deep"], include_other=False,
                           progress=lambda d, t, i: q.put(("prog", d, t)), stop=stop)
        q.put(("result", res))
    except Exception as e:  # noqa: BLE001
        q.put(("error", f"{type(e).__name__}: {e}"))


class BarChart(ctk.CTkFrame):
    """Horizontal bars on a canvas: label, bar, value. Clicking a bar that has comics behind it calls on_pick(item)."""

    def __init__(self, parent, on_pick=None):
        super().__init__(parent, fg_color=BG)
        self.canvas = tk.Canvas(self, height=ROW, highlightthickness=0, bd=0, cursor="arrow")
        self.canvas.pack(fill="x")
        self.items, self.on_pick, self.selected, self.hover = [], on_pick, None, None
        self._job = None
        self._font = None
        self.canvas.bind("<Configure>", lambda _: self._schedule())
        self.canvas.bind("<Motion>", self._motion)
        self.canvas.bind("<Leave>", lambda _: self._set_hover(None))
        self.canvas.bind("<Button-1>", self._click)

    def set_items(self, items, selected=None):
        self.items, self.selected = items, selected
        self.draw()

    def _schedule(self):
        if self._job:
            self.after_cancel(self._job)
        self._job = self.after(60, self.draw)

    def _fit(self, text, width):
        if self._font is None:
            self._font = tkfont.Font(family=FONT, size=10)
        if self._font.measure(text) <= width:
            return text
        while text and self._font.measure(text + "…") > width:
            text = text[:-1]
        return text + "…"

    def draw(self):
        self._job = None
        c = self.canvas
        c.delete("all")
        c.configure(bg=pick(BG), height=max(ROW, len(self.items) * ROW))
        w = max(c.winfo_width(), 320)
        label_w, value_w = min(240, int(w * 0.30)), min(190, int(w * 0.28))
        x0, x1 = label_w + 14, w - value_w - 8
        if not self.items:
            c.create_text(6, ROW // 2, text="Nothing to show.", anchor="w", fill=pick(MUTED), font=(FONT, 10))
            return
        for i, it in enumerate(self.items):
            y = i * ROW
            if i == self.selected:
                c.create_rectangle(0, y, w, y + ROW, fill=pick(SELECT_BG), outline="")
            elif i == self.hover:
                c.create_rectangle(0, y, w, y + ROW, fill=pick(PANEL), outline="")
            c.create_text(6, y + ROW // 2, text=self._fit(it.label, label_w - 6), anchor="w", fill=pick(TEXT),
                          font=(FONT, 10))
            c.create_rectangle(x0, y + 6, x0 + max(3, int((x1 - x0) * it.frac)), y + ROW - 6, fill=pick(ACCENT), outline="")
            c.create_text(w - 6, y + ROW // 2, text=it.text, anchor="e", fill=pick(MUTED), font=(FONT, 10))

    def _index(self, e):
        i = e.y // ROW
        return i if 0 <= i < len(self.items) else None

    def _clickable(self, i):
        return i is not None and self.on_pick is not None and bool(self.items[i].issues)

    def _motion(self, e):
        i = self._index(e)
        self._set_hover(i if self._clickable(i) else None)

    def _set_hover(self, i):
        if i != self.hover:
            self.hover = i
            self.canvas.configure(cursor="hand2" if i is not None else "arrow")
            self.draw()

    def _click(self, e):
        i = self._index(e)
        if self._clickable(i):
            self.selected = i
            self.draw()
            self.on_pick(self, self.items[i])


class FolderBar(ctk.CTkFrame):
    """A slim one-line strip for the library folder: its path in small text and a Change button. Dropping a folder on
    the page works too."""

    def __init__(self, parent, on_change):
        super().__init__(parent, fg_color=PANEL, corner_radius=8, height=36)
        self.pack_propagate(False)
        self.prompt = "No library folder chosen"
        ctk.CTkLabel(self, text="Library", font=(FONT, 11, "bold"), text_color=MUTED).pack(side="left", padx=(12, 8))
        self.label = ctk.CTkLabel(self, text=self.prompt, font=(FONT, 12), text_color=MUTED, anchor="w")
        self.label.pack(side="left", fill="x", expand=True)
        self.button = tool_button(self, "Change…", on_change, 76)
        self.button.pack(side="right", padx=(0, 5))

    def set(self, text=None):
        if text and len(text) > 100:
            text = "…" + text[-99:]  # keep the end of a long path, which is the part that tells folders apart
        self.label.configure(text=text or self.prompt, text_color=TEXT if text else MUTED)


class Tile(ctk.CTkFrame):
    def __init__(self, parent, caption):
        super().__init__(parent, fg_color=BG, border_color=BORDER, border_width=1, corner_radius=10)
        self.value = ctk.CTkLabel(self, text="–", font=(FONT, 22, "bold"), text_color=TEXT, anchor="w")
        self.value.pack(fill="x", padx=14, pady=(10, 0))
        ctk.CTkLabel(self, text=caption, font=(FONT, 12), text_color=MUTED, anchor="w").pack(fill="x", padx=14, pady=(0, 10))

    def set(self, text):
        self.value.configure(text=text)


class StatsPage(Page):
    defaults = {"root": "", "recursive": True, "deep": False, "split": False, "decades": False, "show_all": False,
                "export": EXPORTS[0]}
    choices = {"export": EXPORTS}

    def __init__(self, parent):
        super().__init__(parent)
        self.issues, self.stats, self.last = [], None, None
        self.q = None
        self.stop = threading.Event()
        self.on_scanned = self.on_progress = self.on_error = None  # the app listens (Home summary line)
        self.charts, self.sections = {}, {}
        self.drill_from = None

        title_block(self.main, "Library stats", "See your whole collection at a glance. Nothing is changed.")
        self.drop = FolderBar(self.main, self.browse)
        self.drop.pack(fill="x", pady=(0, 10))
        self.meta = ctk.CTkLabel(self.main, text="", font=(FONT, 13), text_color=TEXT, anchor="w")
        self.meta.pack(fill="x", pady=(0, 6))
        self.progress = ctk.CTkProgressBar(self.main, height=3, corner_radius=2, fg_color=BORDER, progress_color=ACCENT)
        self.progress.set(0)
        self.progress.pack(fill="x", pady=(0, 8))
        self.dash = ctk.CTkScrollableFrame(self.main, fg_color=BG, scrollbar_button_color=BORDER,
                                           scrollbar_button_hover_color=MUTED)
        self.dash.pack(fill="both", expand=True)
        self._build_dashboard()

        v = self.vars
        sw = switch_style()
        self.form.heading("Source")
        box = self.form.add("Scan")
        ctk.CTkSwitch(box, text="Include subfolders", variable=v["recursive"], **sw).pack(anchor="w")
        ctk.CTkSwitch(box, text="Read page counts (slower)", variable=v["deep"], **sw).pack(anchor="w", pady=(8, 0))
        ctk.CTkLabel(box, text="Adds total pages. Without it nothing inside an archive is opened except ComicInfo.xml.",
                     font=(FONT, 11), text_color=MUTED, anchor="w", justify="left", wraplength=260).pack(fill="x", pady=(4, 0))
        self.form.heading("Display")
        box = self.form.add("Charts")
        ctk.CTkSwitch(box, text="Split series into volumes", variable=v["split"], **sw).pack(anchor="w")
        ctk.CTkSwitch(box, text="Group years into decades", variable=v["decades"], **sw).pack(anchor="w", pady=(8, 0))
        ctk.CTkSwitch(box, text="Show every bar (not just the top 15)", variable=v["show_all"], **sw).pack(anchor="w", pady=(8, 0))
        self.form.heading("Output")
        menu(self.form.add("Section to export"), v["export"], EXPORTS).pack(fill="x")
        box = self.form.add("Export")
        self.btn_csv = button(box, "Export CSV…", self.export_csv)
        self.btn_csv.pack(fill="x")
        self.btn_copy = button(box, "Copy summary", self.copy_summary)
        self.btn_copy.pack(fill="x", pady=(8, 0))

        self.btn_scan = button(self.footer, "Scan library", self.scan, primary=True)
        self.btn_scan.pack(pady=(0, 8))
        divider(self.footer, vertical=False).pack(fill="x", pady=(2, 10))
        self.btn_open = button(self.footer, "Open library folder", self.open_root)
        self.btn_open.pack()
        self.btn_stop = button(self.footer, "Stop", self.stop.set)
        self.watch("split", "decades", callback=self._recompute)
        self.watch("show_all", callback=self.render)
        self.watch("root", callback=self._root_changed)
        self._root_changed()
        self._idle()
        self.render()

    # ------------------------------------------------------------------ dashboard
    def _build_dashboard(self):
        tiles = ctk.CTkFrame(self.dash, fg_color=BG)
        tiles.pack(fill="x", pady=(0, 4))
        self.tiles = {}
        for i, (key, caption) in enumerate((("comics", "Comics"), ("series", "Series"), ("publishers", "Publishers"),
                                            ("bytes", "On disk"), ("average", "Average size"), ("pages", "Pages"))):
            tiles.columnconfigure(i, weight=1, uniform="tiles")
            t = Tile(tiles, caption)
            t.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 4, 0 if i == 5 else 4))
            self.tiles[key] = t
        for name, title in (("Series", "Comics per series"), ("Publishers", "Comics per publisher"),
                            ("Years", "Comics per year"), ("Formats", "File formats"),
                            ("Coverage", "How complete the metadata is")):
            box = self._section(title, name)
            chart = BarChart(box, self._pick if name != "Coverage" else None)
            chart.pack(fill="x", pady=(6, 0))
            self.charts[name] = chart
        box = self._section("Largest files", "Largest")
        wrap, self.big = build_tree(box, [("file", "File", 460, True), ("size", "Size", 90, False),
                                          ("pages", "Pages", 70, False)])
        self.big.configure(height=8)
        wrap.pack(fill="x", pady=(6, 0))
        self.drill = ctk.CTkFrame(self.dash, fg_color=PANEL, corner_radius=10, border_color=BORDER, border_width=1)
        self.drill_title = ctk.CTkLabel(self.drill, text="", font=(FONT, 14, "bold"), text_color=TEXT, anchor="w")
        bar = ctk.CTkFrame(self.drill, fg_color="transparent")
        bar.pack(fill="x", padx=12, pady=(10, 0))
        self.drill_title.pack(in_=bar, side="left")
        tool_button(bar, "Close", self._close_drill, 60).pack(side="right")
        tool_button(bar, "Open folder", self._open_drilled, 96).pack(side="right", padx=(0, 6))
        wrap, self.table = build_tree(self.drill, [("file", "File", 360, True), ("series", "Series", 150, True),
                                                   ("year", "Year", 56, False), ("size", "Size", 80, False),
                                                   ("pages", "Pages", 56, False)])
        self.table.configure(height=9)
        wrap.pack(fill="x", padx=12, pady=10)
        self.drill_issues = {}

    def _section(self, title, name):
        box = ctk.CTkFrame(self.dash, fg_color=BG)
        box.pack(fill="x", pady=(22, 0))
        head = ctk.CTkFrame(box, fg_color=BG)
        head.pack(fill="x")
        ctk.CTkLabel(head, text=title, font=(FONT, 15, "bold"), text_color=TEXT, anchor="w").pack(side="left")
        cap = ctk.CTkLabel(head, text="", font=(FONT, 12), text_color=MUTED, anchor="e")
        cap.pack(side="right")
        self.sections[name] = (box, cap)
        return box

    def apply_theme(self):
        for chart in self.charts.values():
            chart.draw()
        for tree in (self.big, self.table):
            apply_tree_theme(tree)

    # ------------------------------------------------------------------ folder and scan
    def browse(self):
        d = filedialog.askdirectory(title="Library folder")
        if d:
            self.set_folder(d)

    def set_folder(self, folder, scan=True):
        """Make this the library root (saved with the settings) and scan it."""
        if self.q:
            return
        self.vars["root"].set(str(folder))
        if scan:
            self.scan()

    def root(self):
        r = self.vars["root"].get().strip()
        return Path(r) if r and Path(r).is_dir() else None

    def _root_changed(self):
        r = self.vars["root"].get().strip()
        self.drop.set(r or None)
        self._idle()

    def _idle(self):
        busy = bool(self.q)
        self.btn_scan.configure(state="normal" if self.root() and not busy else "disabled",
                                text="Rescan library" if self.stats else "Scan library")
        self.btn_open.configure(state="normal" if self.root() else "disabled")
        have = self.stats is not None and not busy
        self.btn_csv.configure(state="normal" if have else "disabled")
        self.btn_copy.configure(state="normal" if have else "disabled")
        self.btn_stop.pack_forget()
        if busy:
            self.btn_stop.pack(pady=(8, 0))

    def scan(self):
        root = self.root()
        if self.q:
            return
        if not root:
            self.say("Choose a library folder first.", err=True)
            return
        self.stop.clear()
        self.q = queue.Queue()
        self.progress.set(0)
        self.say("")
        self.meta.configure(text="Scanning…")
        self._idle()
        threading.Thread(target=_run, args=(self.q, root, self.state(), self.stop), daemon=True).start()
        self._poll()

    def _poll(self):
        try:
            for _ in range(100):
                msg = self.q.get_nowait()
                if msg[0] == "prog":
                    self.progress.set(msg[1] / max(1, msg[2]))
                    self.meta.configure(text=f"Scanning {msg[1]:,} of {msg[2]:,}…")
                    if self.on_progress:
                        self.on_progress(msg[1], msg[2])
                elif msg[0] == "error":
                    self.q = None
                    self.progress.set(0)
                    self.meta.configure(text="")
                    self._idle()
                    self.say(f"Scan failed: {msg[1]}", err=True)
                    if self.on_error:
                        self.on_error(msg[1])
                    return
                else:
                    self._finish(msg[1])
                    return
        except queue.Empty:
            pass
        self.after(60, self._poll)

    def _finish(self, res):
        self.q = None
        self.issues = res.issues
        self.progress.set(0 if res.stopped else 1)
        o = self.state()
        self.stats = sc.compute_stats(self.issues, o["split"], o["decades"])
        self.render()
        note = f"{len(res.issues):,} comics in {res.seconds:.1f}s" + (f" ({res.cache_hits:,} from cache)" if res.cache_hits else "")
        self.say(("Stopped, partial result · " if res.stopped else "Done · ") + note)
        self._idle()
        if not res.stopped:
            self.last = sc.snapshot(self.stats, self.root())
        if self.on_scanned:
            self.on_scanned(None if res.stopped else self.last)

    # ------------------------------------------------------------------ drawing the numbers
    def _recompute(self):
        if self.q or self.stats is None:  # nothing scanned yet (or a scan is running): nothing to regroup
            self.render()
            return
        o = self.state()
        self.stats = sc.compute_stats(self.issues, o["split"], o["decades"])
        self.render()

    def render(self):
        st = self.stats
        self._close_drill()
        if st is None:
            self.meta.configure(text="Choose your library folder, then press Scan library." if not self.root()
                                else "Press Scan library to begin.")
            for t in self.tiles.values():
                t.set("–")
            for name, chart in self.charts.items():
                chart.set_items([])
                self.sections[name][1].configure(text="")
            self.big.delete(*self.big.get_children())
            self._idle()
            return
        all_bars = self.vars["show_all"].get()
        self.tiles["comics"].set(f"{st.comics:,}")
        self.tiles["series"].set(f"{st.series:,}")
        self.tiles["publishers"].set(f"{st.publishers:,}")
        self.tiles["bytes"].set(sc.human_size(st.bytes))
        self.tiles["average"].set(sc.human_size(st.average))
        self.tiles["pages"].set(f"{st.pages:,}" if st.pages is not None else "not read")
        for name in sc.SECTIONS:
            rows = st.sections[name]
            if name == "Years":
                shown = sc.years_view(rows, all_bars)
            else:
                ordered = sc._by_count(rows)
                shown = ordered if all_bars else sc.top_n(ordered)
            self.charts[name].set_items(row_items(shown))
            n = len([r for r in rows if r.label != sc.UNKNOWN])
            self.sections[name][1].configure(
                text=f"{n:,} in all" + ("" if all_bars or len(shown) == len(rows) else " · top 15 shown (Display: show every bar)"))
        cov = [Item(label, (n / of) if of else 0, f"{n:,} of {of:,}" + (f"  ·  {100 * n // of}%" if of else ""))
               for label, n, of in sc.coverage_lines(st)]
        self.charts["Coverage"].set_items(cov)
        unread = st.coverage["unread"]
        self.sections["Coverage"][1].configure(
            text=f"{unread:,} real .cbr file{'s' if unread != 1 else ''} not opened" if unread else "")
        self.big.delete(*self.big.get_children())
        for i in st.largest:
            self.big.insert("", "end", values=(i.rel, sc.human_size(i.size), i.pages if i.pages is not None else ""))
        self.meta.configure(text=f"{st.comics:,} comics · {sc.human_size(st.bytes)} in {self.root() or self.vars['root'].get()}")
        self._idle()

    # ------------------------------------------------------------------ drilling into a bar
    def _pick(self, chart, item):
        for other in self.charts.values():
            if other is not chart:
                other.selected = None
                other.draw()
        self.drill_from = chart
        self.table.delete(*self.table.get_children())
        self.drill_issues = {}
        for i in sorted(item.issues, key=lambda i: i.rel.lower()):
            f = i.info
            iid = self.table.insert("", "end", values=(i.rel, f.get("series") or "", f.get("year") or "",
                                                        sc.human_size(i.size), i.pages if i.pages is not None else ""))
            self.drill_issues[iid] = i
        self.drill_title.configure(text=f"{item.label} · {len(item.issues):,} comic{'s' if len(item.issues) != 1 else ''}")
        for name, (box, _) in self.sections.items():
            if self.charts.get(name) is chart:
                self.drill.pack(after=box, fill="x", pady=(10, 0))

    def _close_drill(self):
        self.drill.pack_forget()
        if self.drill_from is not None:
            self.drill_from.selected = None
            self.drill_from.draw()
            self.drill_from = None

    def _open_drilled(self):
        sel = self.table.selection()
        issue = self.drill_issues.get(sel[0]) if sel else next(iter(self.drill_issues.values()), None)
        if issue and issue.path.parent.exists():
            os.startfile(issue.path.parent)  # Windows

    def open_root(self):
        if self.root():
            os.startfile(self.root())  # Windows

    # ------------------------------------------------------------------ output
    def export_csv(self):
        if not self.stats:
            return
        name = self.vars["export"].get()
        path = filedialog.asksaveasfilename(title=f"Export {name}", defaultextension=".csv",
                                            initialfile=f"stats-{name.lower()}.csv", filetypes=[("CSV", "*.csv")])
        if not path:
            return
        header, rows = sc.section_table(self.stats, name)
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f)
                w.writerow(header)
                w.writerows(rows)
            self.say(f"Exported {len(rows)} row{'s' if len(rows) != 1 else ''}.")
        except OSError as e:
            self.say(f"Could not save: {e}", err=True)

    def copy_summary(self):
        if not self.stats:
            return
        self.clipboard_clear()
        self.clipboard_append(sc.summary_text(self.stats, self.root()))
        self.say("Summary copied. Paste it anywhere.")


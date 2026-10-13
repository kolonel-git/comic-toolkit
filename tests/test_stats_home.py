"""The Home summary line and the app wiring of the Library stats page (settings are kept in a temporary file)."""
import json, sys, tempfile, time, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import comic_tool as ct


def cbz(p):
    p.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("0.jpg", b"x" * 500)


def settle(app, cond, t=30):
    end = time.time() + t
    while time.time() < end and not cond():
        app.update(); time.sleep(0.01)
    app.update(); assert cond(), "timed out"


def buttons(home): return [b.cget("text") for b in home.strip_buttons.winfo_children()]


with tempfile.TemporaryDirectory() as d:
    d = Path(d)
    ct.SETTINGS = d / "settings.json"  # never touch the real settings
    lib = d / "Lib"
    for n in range(1, 4): cbz(lib / "Batman" / f"Batman {n:03d} (2016).cbz")
    cbz(lib / "Saga" / "Saga 001 (2012).cbz")

    app = ct.App(); app.update()
    home, stats = app.pages["home"], app.pages["stats"]
    assert "stats" in app.nav and app.snapshot is None and stats.root() is None
    assert home.line.cget("text") == "No library scanned yet." and buttons(home) == ["Choose your library folder and scan it"]

    # one click: asks for the folder, scans in the background, then shows the numbers with Open Stats (first, larger) and a refresh icon
    asked = []
    ct.filedialog.askdirectory = lambda **k: asked.append(k) or str(lib)
    app.home_scan()
    assert asked and stats.vars["root"].get() == str(lib)
    assert "Scanning your library" in home.line.cget("text") and buttons(home) == []
    settle(app, lambda: not stats.q)
    line = home.line.cget("text")
    assert line.startswith("4 comics · 2 series · ") and line.endswith("scanned just now"), line
    app.update()
    stats_btn, refresh_btn = home.strip_buttons.winfo_children()
    assert stats_btn.winfo_x() < refresh_btn.winfo_x() and stats_btn.winfo_width() > 2 * refresh_btn.winfo_width(), "Open Stats is first and bigger"
    assert buttons(home) == ["Open Stats", "↻"] and app.snapshot["comics"] == 4 and app.snapshot["root"] == str(lib)

    # Refresh rescans the saved folder without asking again; Open Stats opens the page
    cbz(lib / "Saga" / "Saga 002 (2012).cbz")
    asked.clear()
    home.strip_buttons.winfo_children()[1].invoke()  # the refresh icon
    settle(app, lambda: not stats.q and "5 comics" in home.line.cget("text"))
    assert not asked
    home.strip_buttons.winfo_children()[0].invoke(); app.update()
    assert app.current == "stats" and stats.tiles["comics"].value.cget("text") == "5"
    app.show("home")

    # a stopped scan keeps the old numbers; a failed one says so
    stats.scan(); stats.stop.set(); settle(app, lambda: not stats.q)
    assert "comics" in home.line.cget("text") and app.snapshot["comics"] in (4, 5)
    home.show_summary(None, error="boom")
    assert "failed: boom" in home.line.cget("text") and buttons(home) == ["Try again"]

    # a scan started from the Stats page itself updates Home too
    app.show("stats"); stats.scan()
    assert "Scanning your library" in home.line.cget("text") or stats.q
    settle(app, lambda: not stats.q)
    assert "5 comics" in home.line.cget("text")

    # the numbers and the folder survive a restart
    app.close()
    saved = json.loads(ct.SETTINGS.read_text(encoding="utf-8"))
    assert saved["stats_snapshot"]["comics"] == 5 and saved["stats"]["root"] == str(lib)
    app = ct.App(); app.update()
    line = app.pages["home"].line.cget("text")
    assert line.startswith("5 comics · 2 series") and buttons(app.pages["home"]) == ["Open Stats", "↻"], line
    assert app.pages["stats"].root() == lib

    # saved numbers that are damaged are ignored
    app.destroy()
    ct.SETTINGS.write_text(json.dumps({"stats_snapshot": {"comics": 1}}), encoding="utf-8")
    app = ct.App(); app.update()
    assert app.snapshot is None and app.pages["home"].line.cget("text") == "No library scanned yet."
    # with a saved folder but no numbers the button just scans
    app.destroy()
    ct.SETTINGS.write_text(json.dumps({"stats": {"root": str(lib)}}), encoding="utf-8")
    app = ct.App(); app.update()
    assert buttons(app.pages["home"]) == ["Scan your library"]
    app.destroy()
print("stats home OK")

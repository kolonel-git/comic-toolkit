# Tests

Plain scripts that assert and print a final `... OK` line. They build their own temporary files and never touch a real library.

```
python tests/run_all.py            run every script (about 90 seconds)
python tests/run_all.py order      only scripts whose name contains "order"
python tests/test_scan.py          run one script on its own
```

The `*_ui.py`, `test_layout*.py`, `test_stats_*.py`, `test_renamer.py` and `test_aceo_ui.py` scripts open real windows briefly: run them on a desktop session and leave the mouse alone.
Each script finds the project folder from its own location, so run them from anywhere.

| Script | Covers |
|---|---|
| `test_audit.py`, `test_audit_findings.py`, `test_audit_ui.py`, `test_fixes.py` | audit logic (integrity, duplicates, gaps); findings, ignore keys, fix planning and the fixes themselves, junk and Archive purge; the audit page end to end |
| `test_archive.py`, `test_bak.py` | verified archive rewriting, clean-up, `.bak` backups |
| `test_icons.py` | Windows folder icons |
| `test_meta.py`, `test_dropissue.py` | metadata fields, set-for-rows, issue-number removal |
| `test_scan.py`, `test_fixes.py` | library scan and cache; audit page failure handling |
| `test_audit.py`, `test_audit_ui.py` | audit logic and window |
| `test_order.py`, `test_order_multi.py`, `test_edge.py`, `test_order_ui.py` | reading order logic, multi-select moves, top/bottom, window |
| `test_renamer.py` | parser (years, volumes, collected editions), naming engine, renamer window on a messy folder |
| `test_intake.py`, `test_intake_ui.py` | Add to library: naming, folders, duplicate flags, the convert / clean / verify / dispose pipeline and failure handling; the page (inbox scan, review table, ticking, confirmation, running, retry) |
| `test_picker.py` | page picker: grid maths, cover guessing, selection helpers, JPG extraction, and the window (lazy thumbnails, click / shift / box selection, extract, full view) |
| `test_stats.py`, `test_stats_ui.py`, `test_stats_home.py` | library statistics logic, the Library stats page (scan, bars, drill-down, export), the Home summary line and its saved numbers |
| `test_layout.py`, `test_layout_app.py` | resizable panels and sidebar, table column sizes, grouped buttons, Add folder / Choose comics on every page |
| `test_aceo_core.py`, `test_aceo_ui.py` | ACEO template slots, fitting, PDF output, outline colour, window and full-screen view |

What no script can check is listed in `docs/manual-tests.md`.

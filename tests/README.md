# Tests

Plain scripts that assert and print a final `... OK` line. They build their own temporary files and never touch a real library.

```
python tests/run_all.py            run every script (about two minutes)
python tests/run_all.py order      only scripts whose name contains "order"
python tests/test_scan.py          run one script on its own
```

The `*_ui.py`, `test_layout*.py`, `test_stats_*.py`, `test_bulk_page.py`, `test_meta_page.py`, `test_audit_ui.py`, `test_shortcuts.py`, `test_dropissue.py`, `test_renamer.py` and `test_aceo_ui.py` scripts open real windows briefly: run them on a desktop session and leave the mouse alone.
Each script finds the project folder from its own location, so run them from anywhere.

| Script | Covers |
|---|---|
| `test_audit.py`, `test_audit_findings.py`, `test_audit_orders.py`, `test_audit_ui.py`, `test_fixes.py` | audit logic (integrity, duplicates, gaps); findings, ignore keys, fix planning and the fixes themselves, junk and Archive purge; reading-order copies left out of Duplicates, the Reading orders finding, the fix confirmation text and the Details data; the audit page end to end (folding sections, strip, Checks switches, Details panel and its pointers, confirmation, reading orders) |
| `test_archive.py`, `test_bak.py` | verified archive rewriting, clean-up, `.bak` backups |
| `test_icons.py` | Windows folder icons |
| `test_meta.py`, `test_metadata_core.py` | metadata fields, `ComicInfo.xml` writing, the editing logic (`Row`, what is missing, fill from file names, the offer to a series, suggestions) |
| `test_meta_page.py` | the Metadata page: two columns, the form following the selection (automatic and forced), suggestions, the offer, fill and remove issue number, the live list of changes, saving after Confirm, locked `.cbr`, opening from Library stats |
| `test_single_page.py` | the Single issue page: two columns, the strip of first and last pages and its browse tile, the footer changing with the picks, saving a cover (the live file line, conflicts, a folder of your own), extracting picked pages, the ZIP shortcut, and one selection shared with the picker window |
| `test_convert_page.py` | the CBR to CBZ page: two columns, the background check, review counts and statuses, dry run, the three fates of the original, an existing `.cbz`, junk and page-name tidy-up, a failing file, the Delete confirmation, the link from the Library audit, and `convert_one` leaving an existing `.cbz` alone when the tidy-up fails |
| `test_bulk_page.py` | the Bulk folder page on the shell: segments, review, dry run, running, retry |
| `test_dropissue.py`, `test_shortcuts.py` | dropping files on pages, the keyboard layer and Ctrl+K |
| `test_reading_orders.py` | the marked reading-order folders and the suggestion guess |
| `test_scan.py`, `test_fixes.py` | library scan and cache; audit page failure handling |
| `test_audit.py`, `test_audit_ui.py` | audit logic and window |
| `test_order.py`, `test_order_multi.py`, `test_edge.py`, `test_order_ui.py` | reading order logic, multi-select moves, top/bottom, the list and the write |
| `test_order_page.py` | the Reading order page on the shell: two columns, block summaries, the review and the footer, and marking the folder of copies (ask, always, never, the button, the menu of marked folders) |
| `test_renamer.py` | parser (years, volumes, collected editions), naming engine, renamer window on a messy folder |
| `test_intake.py`, `test_intake_ui.py` | Add to library: naming, folders, duplicate flags, the convert / clean / verify / dispose pipeline and failure handling; the page (inbox scan, review table, ticking, confirmation, running, retry) |
| `test_picker.py` | page picker: grid maths, cover guessing, selection helpers, JPG extraction, and the window (lazy thumbnails, click / shift / box selection, extract, full view) |
| `test_stats.py`, `test_stats_ui.py`, `test_stats_home.py` | library statistics logic, the Library stats page (scan, bars, drill-down, export), the Home summary line and its saved numbers |
| `test_layout.py`, `test_layout_app.py` | resizable panels and sidebar (the two-column pages' dividers are checked in their own page tests), table column sizes, grouped buttons, Add folder / Choose comics on every page |
| `test_aceo_core.py`, `test_aceo_ui.py` | ACEO template slots, fitting, PDF output, outline colour, window and full-screen view |

What no script can check is listed in `docs/manual-tests.md`.

# Changelog

Technical record of every working session on Comic Toolkit, newest first. Each session is one timestamped block.

**Conventions**
- Times are local (UTC+11:00), date format `YYYY-MM-DD HH:MM`.
- Blocks dated before 2026-10-06 20:43 were written retroactively. Their times are reconstructed from file creation and
  modification timestamps and are approximate (marked `~`); where nothing could be reconstructed it says so.
- Each block lists: summary, decisions, changes by file, technical notes, bugs found and fixed, verification, and known
  issues. "Verification" only claims what was actually run.
- Maintenance rule: add a new block at the top at the end of every session, and update the docs (see `docs/README.md`) to match.

---

## 2026-10-08 16:55 +11:00 · Session 34: options panels regrouped, one-screen Home

**Summary:** Every page's options panel now reads in the same order under the same kind of headings, the Home page was rebuilt as a compact grid that shows every tool without scrolling, and Single issue's folder button moved to the right of the comic button.

**Decisions**
- Options panels follow one pattern: **Source** (what to read, such as subfolders) then the tool's own groups, then **Output** (where results go, what happens to originals). Rows inside a group keep their label-over-control style and the grey hint text under them.
  - Single issue: Cover image | Output. Bulk folder: Source | Cover image | Output (the image options now come before the save options). Folder icons: Cover | Output. CBR to CBZ: Source | Output. Clean-up: Source | Clean-up | Output (the subfolder switch is no longer mixed in with the junk switch). Metadata: Source | What to write | Checked rows | Output (*Original file* moved from the middle to the end, after the bulk edits). Library audit: Source | Reports. Reading order: Reading order | Filenames and sorting | Output. ACEO sheets already had Template | Covers | Cards | Output. The Renamer keeps its four tabs; its first group is now called *Source*.
- Footers follow one pattern: the main action (and its preview variant) at the top, a divider, then utility buttons (Rescan folder, Open folder).
- Home: groups sit side by side in three rows (Cover Extractor and Renamer; Metadata, Archive Tools and Library Audit; Reading Orders and ACEO Cards) with compact cards (icon, title, one short description). Cards inside a group are 8 px apart, groups 34 px; every card has the same width in every row, and the cards resize with the window, so nothing scrolls. The blurb under each group name was dropped to save space.
- Single issue's folder button now sits to the right of *Choose comic…* (the drop box takes `files_first=True`).

**Changes by file**
- `comic_tool.py`: new `Card` (compact) and `HomePage` (grid, no scroll frame); `GROUPS` entries are now `(header, tool keys)` and `HOME_ROWS` says which groups share a row.
- `ui_kit.py`: `DropZone(files_first=...)`; `Form.headings` records the group titles; the first heading in a panel has less space above it.
- `page_single.py`, `page_bulk.py`, `page_icons.py`, `page_convert.py`, `page_cleanup.py`, `page_metadata.py`, `page_audit.py`, `page_order.py`, `page_rename.py`: option groups and footers as above.
- Tests: `tests/test_layout.py` (panel headings per page, button order on Single and Bulk), `tests/test_layout_app.py` (Home fits without scrolling at the narrowest and widest sidebar, equal card widths, wider gaps between groups, a card opens its tool); the three window tests that read `GROUPS` were updated for the new shape.
- Docs: `tools.md`, `manual-tests.md` (H8 to H10).

**Verification:** `python tests/run_all.py` ran all 18 scripts and every one passed, and `ruff --select F,E9` was clean. The new checks cover: the heading list of every panel; Single's button order; on Home, all ten cards present, equal width in every row, inside the page and above its bottom edge (so no scrolling) with the sidebar at its narrowest and widest, group gaps wider than card gaps, and a click opening its tool. **Not verified:** how the panels and the Home page look on screen (no screenshot was taken because the screen grab captures whichever window is in front), and the Home page at other window sizes than the two tested widths. See [manual tests](manual-tests.md), H8 to H10.

**Known issues:** the Home card height is fixed, so a long description on a very narrow card could be cut off (not checked on screen).

---

## 2026-10-08 16:36 +11:00 · Session 33: resizable panes and columns, grouped buttons, folder and comics buttons

**Summary:** Quality-of-life pass over every page. Panes and table columns can be dragged to any size, related buttons are grouped with small dividers, and every page now has an **Add folder** and a **Choose comics** button in the same box as the drop area. Two stale facts in `README.md` and `HANDOFF.md` (version and session count) were also corrected.

**Decisions**
- Resizing uses a small draggable divider (`Splitter`) rather than a fixed split: the app sidebar, each page's options panel, the Renamer's file list beside its card, and the ACEO cover list beside its preview. The sidebar and panel widths are saved with the settings.
- Table columns: every column of every table can be dragged from its heading edge (they previously could not be made narrower than their starting width), and each table gets a horizontal scrollbar for when the columns are wider than the table.
- Buttons are grouped by purpose with a thin divider between groups: Reading order is *Suggest order* | *Top ▲ ▼ Bottom* | *Remove Clear*; ACEO is *Top ▲ ▼ Bottom* | *Remove Clear*; *Select all / Select none* sit together; the run buttons in side-panel footers are divided from *Open folder* (Bulk folder, the batch tools, Library audit).
- *Add folder* moved from the Reading order and ACEO toolbars into the drop box, next to *Choose comics*, so all pages work the same way.
- On the folder tools *Choose comics…* works on just the files picked: the other files in their folder are left alone, and the root used for relative names and the Archive check is the nearest folder that contains them all. Library audit then judges duplicates and gaps among the picked comics only. Folder icons uses one folder per parent, taking its cover from the first (or last) picked comic in it. On **Single issue**, which handles one comic, the folder button hands the folder to Bulk folder, as dropping a folder there already did.

**Changes by file**
- `ui_kit.py`: `Splitter`, `tool_button`, `divider`, `toolbar` (groups of buttons with dividers, left or right anchored); `DropZone` takes `on_folder` / `on_files` and shows the two buttons; `Page` has a resizable options panel and saves its width (`_side_width` in the page state); `build_tree` columns have a small minimum width and a horizontal scrollbar.
- `comic_core.py`: `picked_files` and `common_root`. `library_scan.py`: `scan_library(only=...)` scans a given list of files and leaves the cache entries of other files alone.
- `comic_tool.py`: sidebar `Splitter`, width saved as `sidebar` in `settings.json`.
- `batch_page.py` (with `page_convert.py`, `page_cleanup.py`, `page_icons.py`): `set_files`, `browse_files`, `pick_items`, a footer divider. `page_bulk.py`, `page_metadata.py`, `page_rename.py`, `page_audit.py`: `set_files` with a `picked` list; `page_single.py`: folder button; `page_order.py`, `page_aceo.py`: grouped toolbars, drop-box buttons, and (ACEO) a draggable divider before the preview; `page_rename.py`: a divider between the file list and the card.
- `tests/test_layout.py`, `tests/test_layout_app.py` (new), `tests/README.md`.
- Docs: `tools.md`, `architecture.md`, `known-limitations.md`, `manual-tests.md` (section H), both READMEs.

**Technical notes**
- Mouse movement is in pixels but widget widths are in scaled units, so the divider divides by the widget's display scaling before resizing (a scaled display was the case that caught this in testing).
- `picked_files` filters by each tool's own file types, so choosing a mix keeps only what the tool can use; the shared root is worked out from the files that remain.

**Verification:** `python tests/run_all.py` ran all 18 scripts and every one passed, and `ruff --select F,E9` was clean. The new tests cover: all ten pages have both drop-box buttons; the options-panel divider (drag, both limits, saved and restored width, junk ignored); the sidebar divider and its limits; every table column's minimum width and resizing a column; button grouping and order (including the Reading order buttons); and *Choose comics* on Convert, Clean-up, Folder icons, Bulk folder, Metadata, Renamer and Library audit (types filtered, relative names, a bad pick changing nothing, switching back to a folder, the audit scanning only the picked files). **Not verified:** how any of this looks on screen (a screenshot attempt captured another window, so none was checked), real mouse dragging of the dividers and of heading edges, and the Single issue folder button (hands over to Bulk; only the presence of the drop-box buttons was tested). See [manual tests](manual-tests.md), section H.

**Known issues:** column widths are not remembered between runs (the panel and sidebar widths are).

---

## 2026-10-08 16:20 +11:00 · Session 32: tests folder

**Summary:** The test scripts, which had only existed outside the repository, were moved into `tests/` with a runner. No application code changed.

**Changes**
- `tests/` (new): 16 scripts (archive tools, backups, icons, metadata, issue-number removal, scan, audit logic and window, reading order logic and window, renamer and parser, ACEO core and window), `run_all.py` (runs each in its own process and reports pass or fail) and `README.md`. The old renamer test was replaced by `test_renamer.py`; one stale print-only script was dropped. Scripts now find the project from their own location instead of a fixed path.
- `docs/versioning.md`: lists the tags that exist (including that `v0.4.1` was skipped and `v0.5.0` went to ACEO sheets) and moves the planned versions for the Stats dashboard, watcher and packaging up by one.
- `docs/architecture.md`, `README.md`: mention the tests folder.

**Verification:** `python tests/run_all.py` ran all 16 scripts and every one passed (about 75 seconds), and `ruff --select F,E9` was clean. The manual tests in [manual-tests.md](manual-tests.md) are still entirely unrun (68 checks, sections A to G).

---

## 2026-10-07 22:04 +11:00 · Session 31: ACEO outline colour and thickness

**Summary:** The card outlines on the ACEO sheets can now be given a colour (so they stay visible on a black background) and a thickness.

**Decisions**
- The default colour is automatic: black on a white or light background, white on a black one, so a black background works without touching anything. Black, white, light grey, grey, red, gold and a custom hex colour are also offered.
- The thickness defaults to the template's own (read from its `w` operator, 1 point for the bundled file); an empty or invalid value keeps it.
- An invalid custom colour falls back to automatic and the page says so under the box.

**Changes by file**
- `aceo_core.py`: `OUTLINE_COLORS`, `parse_hex`, `outline_rgb`, `outline_width`; `read_template` also reads the template's line width; `outline_overlay` builds a transparent page with the template's rectangles stroked in the chosen colour and width and `render_pdf` merges that instead of the template page; the preview outlines use the same colour and width.
- `page_aceo.py`: **Outline colour** menu, **Custom colour (#RRGGBB)** box with validation message, **Outline thickness** box; all re-draw the preview.
- Docs: `tools.md`, `architecture.md`, `manual-tests.md` (G4).

**Technical notes**
- The overlay uses the template's rectangles (converted to PDF coordinates), not the template page itself, which is why the colour can change; with the default settings the result is the same black 1 point lines as before.
- pypdf rewrites the number formatting when it merges pages, so tests read the stroke colour and width with a pattern instead of an exact string.

**Verification:** scripted tests ran and passed: hex parsing (6 and 3 digits, with and without `#`, bad input), automatic contrast for white, black and light grey backgrounds, named and custom colours, a bad hex falling back, thickness parsing; PDFs created with automatic colour on black (white lines), gold, and custom red at thickness 3, each with the right stroke colour, width and eight rectangles on a Letter page with its picture; the preview drawn in white, red and thick; and in the window the automatic colour on a black background, the invalid-colour message and its clearing, thickness parsing, and a PDF made with a custom colour and thickness 2. Earlier ACEO, renamer, order, audit, scan and metadata tests and `ruff --select F,E9` still passed. A screenshot of the new options and the preview on a black background was checked in dark mode; the PDF itself was not opened in a viewer, so the line colour in a real viewer or print is unconfirmed (manual test G4).

**Known issues:** unchanged.

---

## 2026-10-07 21:50 +11:00 · Session 30: ACEO sheets layout and full-screen preview

**Summary:** The ACEO sheets page was rearranged so the cover list gets most of the room and the sheet preview sits at the right edge, and a **Full screen** button shows the sheet as large as the screen allows.

**Changes by file**
- `page_aceo.py`: the cover list now expands to fill the space (the file name column is wider and the Sheet · card column is always visible); the preview moved to a fixed-width column at the right edge and sizes the sheet to the height available; the side panel is grouped under Template, Covers, Cards and Output headings; new **Full screen** button and viewer (`open_full`, `close_full`, `_full_draw`) with ◀ ▶, Left/Right keys, **Close** and Esc, which redraws from the original cover bytes at the window's size.
- Docs: `tools.md`, `manual-tests.md` (G1b).

**Bugs found and fixed:** the first rearranged version showed only part of the sheet because the pane size (pixels) was multiplied by the display scaling a second time before drawing; sizes are now taken in pixels and converted once. Found in a screenshot and covered by a new test.

**Technical notes**
- The preview is drawn from the in-memory cover copies at the pane's pixel size; the full-screen view decodes the original cover bytes at the size of the window, so it is sharper. Both are re-drawn when the window or pane changes size (debounced).
- The viewer shares the page's current sheet number, so moving in either one moves both.

**Verification:** the scripted ACEO tests were extended and passed: the list is wider than the preview and the preview sits to its right; the sheet fits inside the side pane and inside the full-screen window (checked in pixels after display scaling); the viewer opens, shows "Sheet n of m", moves with the Right and Left keys and keeps the page's sheet in step, reuses its window on a second click, closes with Esc, and does not open when there are no covers; the earlier ACEO, renamer, order, audit, scan, metadata, backup and archive tests and `ruff --select F,E9` still passed. A screenshot of the page at 1200 × 780 in dark mode was checked (list columns, preview position and full sheet visible). The full-screen view was not captured as a screenshot, so how it looks on your screen is unconfirmed (manual test G1b).

**Known issues:** unchanged.

---

## 2026-10-07 21:33 +11:00 · Session 29: ACEO sheets tool

**Summary:** New Home group **ACEO Cards** with the **ACEO sheets** tool: it reads the card slots from the blank template PDF in the project (`ACEO - Full Page BLANK.pdf`), fits the covers you choose into them, eight to a page, and writes a print-ready PDF. A preview shows each sheet before it is made.

**What the template is:** a Letter page (612 × 792 pt) containing eight 252 × 180 pt rectangles (3.5" × 2.5", landscape) drawn as outlines, in two columns of four, rows touching. The tool reads those rectangles from the page itself, so another template with plain rectangles works too.

**Decisions**
- A portrait cover is turned 90° by default to fill the landscape card (top of the cover on the left, so the sheet is turned clockwise to read it); this can be changed or switched off, and the cover can instead be fitted whole or stretched.
- Pages are rendered as pictures with Pillow at 150, 300 (default) or 600 dpi and written with `pypdf`, then the template's own vector outlines are merged back on top, so the cut lines stay crisp. This avoids adding a PDF-drawing dependency; the cost is that the PDF has no selectable text.
- Comics give their first page (or last page); loose images are used as they are. Archive folders are skipped when adding a folder.
- `pypdf` is a new dependency (only for this tool).
- Not done: card text or labels, rounded corners, bleed and crop marks, other layouts than the template's.

**Changes by file**
- `aceo_core.py` (new): `read_template` (finds `x y w h re` rectangles through the page's `cm` transforms and returns slots in reading order), `find_sources`, `load_cover`, `decode`, `fit_card` (fill, fit, stretch; turning; background), `compose_sheet`, `expand` (copies), `chunk`, `render_pdf` (one page at a time, outlines merged, `.part` file then replace, stop support).
- `page_aceo.py` (new): `AceoPage` with drop and add buttons, a cover list with ▲ ▼ Top Bottom Remove Clear (reusing the Reading Order block helpers), a live sheet preview with navigation, options, a template chooser, a render worker with progress and Stop, and "open when done".
- `comic_tool.py`: registers the page, the `aceo` card and the "ACEO Cards" group; the install line gains `pypdf`.
- Docs: `tools.md`, `architecture.md`, `getting-started.md`, `known-limitations.md`, `manual-tests.md` (section G), both READMEs.

**Technical notes**
- Slot positions come from the template's content stream, converted to a top-left origin; a rectangle smaller than 10 pt is ignored. For the bundled file the content stream flips the page with `1 0 0 -1 0 792 cm`, which the reader applies.
- One real bug was found while building: `page.get_contents()` is falsy for a valid content stream, so the first version found no slots; it now compares with `None`.
- The page image is saved by Pillow with `resolution=dpi`, which makes the PDF page exactly the template's size (612 × 792 pt at every quality).
- The preview uses small in-memory copies of each cover; the PDF is made from the original image bytes.

**Verification:** scripted tests ran and passed. *Core:* the template read as 8 slots of 252 × 180 pt in the right order; cover fitting (top on the left or right, upright and letterboxed on black, crop, stretch, landscape left unturned); sheets with empty slots, a margin and an absurd margin; sheet counting, copies and chunking; folders and images as sources with Archive skipped; first and last page covers; a two-sheet PDF at 150 dpi with the right page size, outline operators on the page, pixel colours in the first card and blank empty slots, outlines off, a 600 dpi page of 5100 × 6600 pixels, a stop request leaving nothing behind, a template with no rectangles rejected, and a different two-slot template read and rendered. *Window (headless):* adding a folder with a broken comic, a PNG and a text file (broken one skipped with a message); counts and sheet/card positions; ordering and removal; copies; sheet navigation; creating a PDF through the save dialog (two sheets, outlines); last-page covers with outlines off; a cancelled dialog; a bad template, a missing template path falling back to the bundled one; stop during a 600 dpi render; settings round trip, theme and every fit/turn combination in the preview; the whole app registering the page. Earlier tests and `ruff --select F,E9` still passed. A screenshot of the page showed the list, the preview and the options correctly in dark mode. Not run: printing a sheet and measuring it, opening the PDF in other viewers, real comic covers at scale (manual tests G1 to G8).

**Known issues:** see [Known limitations](known-limitations.md).

---

## 2026-10-07 20:40 +11:00 · Session 28: Renamer revamp (cards, a format per type, full formatting options, year fixes)

**Summary:** Two bugs reported against the Renamer (years not found even in clear brackets; a year used as the volume) were reproduced and fixed, and the tool was rebuilt around reviewing one file at a time on a card, a naming format per comic type, and a complete set of formatting options grouped under four settings tabs.

**Bugs reproduced and fixed**
- *Year not found:* only plain `(2016)`-style groups worked. `(Oct 2016)`, `(October 2016)`, `(2016, DC)`, `(DC 2016)`, `(2016 Digital)`, `(2016-)`, `(05-10-2016)`, `(1/2016)`, `(Summer 2016)` and a group starting with an invisible character all returned no year (34 test names now pass). A year is now taken from inside any bracket group (not an "(of 12)" count), and a bare year next to an issue number (`Batman 001 2016`, `Batman 2016 001`, `Batman.001.2016`) also counts. Years are limited to 1900 to next year, so `Spider-Man 2099` is untouched.
- *Year used as the volume:* `read_comicinfo` accepted any positive `Volume`, and ComicInfo files very often store the start year there (Volume 2016), so names and folders got `v2016`. A year-like Volume is now returned as the year; the same applies to `v2016` / `Vol 2016` in a filename, with a note shown on the card.

**Decisions**
- Review is a card per file plus a list view; both edit the same data and nothing touches disk until Apply.
- A template per type (15 types), each editable, instead of one for issues and one for collected editions; presets only fill a template.
- Formatting is a small template language (optional groups, fallbacks, escapes, per-token formats) plus text options, so every choice is visible and documented rather than hidden in presets.
- The old Renamer settings are not migrated (the option set changed shape); new per-type templates start at the old defaults.
- Not done: saving hand edits between runs, writing the detected format into ComicInfo, per-field "source" badges on the card.

**Changes by file**
- `rename_core.py` (rewritten parser): year detection in any bracket, year spans, year-like volumes, `tags`, `original`, `year_end`, `notes`; `apply_type` for all 15 types; `apply_edits` for values typed on a card; `merge` keeps `year_end` in step; `read_comicinfo` turns a year-like Volume into the year. Single-issue parsing was checked against a snapshot of 23 earlier results (no change).
- `name_format.py` (new): `DEFAULT_TEMPLATES` for every type, issue and collected presets, tokens (`series title issue volume year years year_end count range format type publisher tags original`), token formats (`{issue:3}`, `upper lower title sentence nospace snake dash`), fallbacks `{a|b}`, optional `[ ]` groups, escapes `\[ \] \{ \}`, `check_template`, text options (padding, case modes, leading article, separators, illegal characters, extension case, maximum length), `build_name`, `build_folder` (nested folders), `FORMAT_GUIDE`.
- `page_rename.py` (rewritten): Cards view (file list with filters and status, card with Type, Series, Title, Issue, Volume, Issue range, Year, Year end, Issue count, live New name, destination, notes, Reset, Automatic name, Rename switch) and List view; Detect, Names, Text and Folders tabs; template editor with validation, a live example, preset fill, copy-to-group and a format guide window; folder template and presets; collected subfolder name; conflict mode "Add a number"; re-parsing on every option change.
- `ui_kit.py`: `Form.heading` (group title with a rule).
- Docs: `renamer-templates.md` (rewritten: every option), `tools.md`, `architecture.md`, `known-limitations.md`, `manual-tests.md` (section F replaced), both READMEs.

**Technical notes**
- A card edit goes into `Item.edits`; the name is rebuilt from detected fields, then the type override, then the edits, so clearing a field removes its optional group. Typing a name by hand sets `manual_stem`, which survives option changes until the card is reset or the name returned to automatic.
- Statuses: Ready, Unchanged, Skipped, Numbered, Exists, Duplicate, No series. "Add a number" assigns `Name (2)` etc. to checked colliding files in list order, and treats unticked or unchanged files as occupying their current names.
- The Library audit and the duplicate checks use the same parser, so TPBs have a volume, not an issue, and a year-like volume no longer groups series wrongly.

**Verification:** a scripted test ran and passed. *Parser:* 21 year/volume forms including every reported failure, spans, tags and the original name; a CBZ with ComicInfo Volume 2016 read as year 2016 and no volume, and a real volume kept; a 23-name snapshot of single-issue parsing unchanged. *Engine:* padding, case, fallbacks, group dropping, literal brackets, article modes, separators, illegal-character modes, extension case, maximum length, template validation (unbalanced, unknown token, unknown format, no tokens), folder templates (nested, empty publisher, collected volume), every type's default template, and the guide listing every token. *Window (headless):* a messy folder of 19 files across `.cbz`, `.cbr`, `.pdf` and `.epub` with the expected names and statuses (including `(Oct 2004)`, `v2016` and the ComicInfo year-volume); per-type templates changing only their type; the Names editor writing to the chosen type with validation and an example; presets and copy-to-group; each text option; card navigation, editing, type override, reset, manual name, skip, Previous/Next and the four filters; opening a card from the list; detection switches; conflict numbering; folder templates with publisher, nested folders and the collected subfolder; a real apply that lost nothing and was idempotent on rescan; settings round trip, an old-format settings file loading without errors, theme switch, the guide window and every tab. Earlier scan, audit, metadata, order, backup and archive tests and `ruff --select F,E9` still passed. Screenshots of the card and the Names tab were checked in dark mode and led to moving the new name to the top of the card, shortening the toggle, and widening the status column; the Text and Folders tabs and light mode were not viewed. Not run: a real, untidy library (manual tests F1 to F9).

**Known issues:** see [Known limitations](known-limitations.md).

---

## 2026-10-07 17:43 +11:00 · Session 27: Renamer for TPBs, compendiums and messy folders

**Summary:** The Renamer was built around single issues, so TPBs and compendiums were mis-named (a `Vol 3` became issue 3, `Batman #1-12` became issue 12, format words were lost or left in the series name). The parser now recognises collected editions, and the Renamer names them with their own templates, shows a Type for every file, and handles the mess that comes with mixed folders.

**Decisions**
- Collected editions get a separate template and padding, so the single-issue styles behave exactly as before. A snapshot of 23 existing filenames parsed identically before and after the parser change.
- A bare `Vol 3` stays an issue by default (manga convention, no change in behaviour); a setting switches it to a volume, and a per-file Type override covers the rest.
- Annuals, specials and one-shots keep the word in the series name rather than becoming a format.
- Series spelling is only unified for case and a leading *The*; no alias database.
- Not done: filtering the table by type, and writing the detected format into `ComicInfo.xml`.

**Changes by file**
- `rename_core.py`: `parse_filename(stem, volume_as_issue=True)` now also returns `format`, `range`, `years`, `collected` and `kind`. New detection: format words (TPB/trade paperback, hardcover/HC, omnibus, compendium, deluxe edition, library edition, epic collection, graphic novel/OGN/GN, box set, collection), issue ranges (`#1-12`, `001-012`, `Issues 1-6`), year spans (`1996-1997`), volume words and numerals (`Book One`, `Volume Two`, `Vol. III`), `Series - Title` splitting, `Walking Dead, The` inversion, dotted names, a trailing bare year, unbracketed `Digital`/`WebRip`/`c2c`/`Hybrid`, and generic junk names (`scan0001`, `IMG_0042`, `Untitled`) treated as having no series. New: `COLLECTED_PRESETS`, `COLLECTED_STYLES`, `VOLUME_PADS`, `COLLECTED_FOLDERS`, `VOLUME_MODES`, `TYPES`, `apply_type`; `build_stem` takes a volume padding; `merge` keeps `years` in step with a ComicInfo year; `series_folder` ignores a collected volume.
- `page_rename.py`: a **Type** column (double-click or right-click to override), the collected-editions options (style, custom template, `Vol 3` interpretation, volume padding, subfolder), re-parsing on option change, series-folder grouping that ignores a leading *The* and case, and a count of collected files in the summary.
- Docs: `renamer-templates.md` (collected editions section), `tools.md`, `architecture.md`, `known-limitations.md`, `manual-tests.md` (section F), `README.md`.

**Technical notes**
- Format detection searches the whole name (including brackets, so `[TPB]` counts) and removes every format word from the series text; the first match in the specificity order decides the format. With a format present, a trailing number is the volume and a ` - ` splits series and title; without one, the old issue logic runs untouched.
- A range needs both ends to be 1 to 4 digits, the second larger than the first, and the first below 1900, so `Wolverine 2000-2001` is not read as issues.
- Because a TPB now has a volume but no issue, the Library audit no longer counts it as a gap-filling issue and the duplicate check no longer pairs `Saga Vol 3` TPB with `Saga 003`.
- Overrides: *Issue* turns a lone volume back into an issue; any other choice makes the file collected and moves an issue number into the volume.

**Bugs found and fixed:** `scan0001.cbz` was parsed as series `scan` and offered the name `scan 001`; generic names now have no series. `Saga, Vol. 03 - Title` left `Saga, - Title` as the series; the title is now split off. `Batman.001.2016` read 2016 as the issue; a trailing bare year is now the year. All were caught by the scripted tests and fixed before finishing.

**Verification:** scripted tests ran and passed. *Parser:* a 23-name snapshot of existing behaviour unchanged; about 35 TPB-style names checked by eye and the important ones asserted (formats, volumes, ranges, year spans, word and roman numerals, inverted *The*, dotted names, junk endings, annuals). *Window (headless):* a messy folder of 15 files across `.cbz`, `.cbr`, `.pdf` and `.epub` (issues, TPBs, hardcover, omnibus, compendiums, epic collection, a range, an annual, a junk name and a nested file) with the expected new names, types and statuses; the bare-`Vol 3` collision flagged *Exists* and then resolved by the volume setting; per-file overrides in both directions and back to auto; all four collected styles, a custom template and volume padding; series folders with and without the `Collected Editions` subfolder and the *Series + volume* style; *The* and case grouping; an apply that changed only ready files, lost nothing and was idempotent on rescan; settings round-trip and theme. The earlier scan, audit, metadata, order, backup and archive tests and `ruff --select F,E9` still passed. A screenshot of the Renamer was checked in dark mode, which led to a wider Type column. Not run: a real, untidy library, so detection quality on real names is unmeasured (manual tests F1 to F7).

**Known issues:** see [Known limitations](known-limitations.md).

---

## 2026-10-07 17:20 +11:00 · Session 26: removing the issue number so YACReader sorts by filename

**Summary:** YACReader sorts by issue number before filename, so a comic's `Number` tag can override the order you want. The Metadata and Reading order tools can now delete that tag, which makes YACReader fall back to the filename.

**Decisions**
- Only the issue number (`Number`) is removed. `Count`, `Volume`, the story arc and everything else stay.
- Metadata gets a per-row action (consistent with *Set for checked rows*); Reading order gets a switch that applies to every issue in the list.
- Removal is a normal verified write with the usual `.bak` backup.

**Changes by file**
- `archive_tools.py`: `merge_comicinfo` treats a value of `None` as "remove this tag" (all matching elements; a missing tag is a no-op).
- `page_metadata.py`: new *Issue number* section with **Remove from checked rows** and **Keep it again**; `Row.removes`; removal overrides a filename-derived issue write, shows a blank in the **#** column, and typing a value replaces it; the write confirmation says how many files lose their number.
- `reading_order.py`: `plan_item` adds an `issue: None` write when the option is on and the file has a number; `describe_item` prints `Number: 5  ->  (removed)`.
- `page_order.py`: new **Remove issue numbers** switch (saved with the page settings), part of the plan, and a line in the preview that warns when no filename prefix is on.
- Docs: `tools.md`, `reading-order.md`, `known-limitations.md`, `manual-tests.md` (B9, E13).

**Technical notes**
- In Metadata, removal on a file that has no number also cancels the number the filename would have added, so the row ends up with no issue-number write. After a real write and rescan, the file has no number, so the filename would add it again unless **Issue number** is unticked under *Fields to write*; the hint says so.
- Both tools reuse the same write path (`apply_metadata`), so verification and backups are unchanged.

**Bugs found and fixed:** none in the shipped code; test-script expectations (row order, a typo) were corrected.

**Verification:** a scripted test ran and passed: the XML merge removing one and several `Number` tags while keeping other fields, a missing tag and a file with no `ComicInfo.xml`; an in-place removal with a `.bak` backup; reading-order plans with the option on and off, an idempotent re-plan, and a write that removed the number and renamed; the Metadata window (nothing checked message, blank **#** column, status, a filename-derived add cancelled, the confirmation text, files written, rescan, undo, and an inline edit replacing a pending removal); and the Reading order window (preview text with and without a prefix, a write removing numbers, and the setting saved). Earlier metadata, archive, order, audit, scan and renamer tests and `ruff --select F,E9` still passed. Not run: YACReader itself, so whether it then sorts by filename is unconfirmed (manual tests B9 and E13).

**Known issues:** see [Known limitations](known-limitations.md).

---

## 2026-10-07 16:45 +11:00 · Session 25: Reading Order Top and Bottom buttons

**Summary:** The Reading order toolbar gained **Top** and **Bottom** buttons that send the selected issue or issues to the very start or end of the list, next to ▲ and ▼.

**Changes by file**
- `reading_order.py`: `send_to_edge(order, selected, top)` moves the selection, as one block in its existing order, to the top or bottom.
- `page_order.py`: `to_edge`, two new buttons, and enable/disable handling with the other list tools. The toolbar was rearranged so it fits: the issue count sits on its own line above, and the buttons run left to right as Add folder, Suggest order, Top, ▲, ▼, Bottom, Remove, Clear.
- Docs: `reading-order.md`, `tools.md`, `architecture.md`, `manual-tests.md` (E2b).

**Technical notes**
- A scattered selection is gathered into one block: rows keep their relative list order, not the order they were clicked.
- Sending a block that is already at the edge, or nothing at all, changes nothing.

**Bugs found and fixed:** the first layout (all buttons beside the count, packed from the right) clipped the Add folder label once two more buttons were added; found in a screenshot and fixed by moving the count to its own line.

**Verification:** a scripted test ran and passed: the pure helper for single and scattered selections, both edges, an already-placed block and an empty selection; in the window, one row sent to the top, two scattered rows to the bottom, a three-row block to the top, the **#** column renumbering each time, selection kept, nothing selected doing nothing, and both buttons disabled when the list is cleared. The earlier order tests and `ruff --select F,E9` still passed, and a screenshot confirmed the toolbar fits in dark mode (light mode not viewed). Not run: use by a person with real comics (manual test E2b).

**Known issues:** unchanged.

---

## 2026-10-07 16:28 +11:00 · Session 24: Reading Order, multi-select moves and Preview changes

**Summary:** Two changes to the Reading order page requested before committing it: several issues can be selected and moved together, and a **Preview changes** button shows what a write would do without writing anything.

**Changes by file**
- `ui_kit.py`: `build_tree` takes a `selectmode` argument (default `"browse"`, so other tables are unchanged).
- `reading_order.py`: `move_block` (shift a selection one place up or down as a block), `drop_block` (drop a selection onto a target row), `describe_item` (plain-text lines for one issue's planned change).
- `page_order.py`: the table uses extended selection. ▲ ▼ move every selected row together; dragging a selected row drags the whole selection; a click on an unselected row, Ctrl+click and Shift+click behave normally; a tick-box click applies to all selected rows; Remove takes out all selected rows. New **Preview changes** button and window (`preview_text`, `preview`).
- Docs: `reading-order.md`, `tools.md`, `architecture.md`, `manual-tests.md` (E2b, E2c).

**Technical notes**
- Block moves keep the selection's relative order. At an edge, items that can't move stay and the rest still move. Dragging down puts the block after the target row and dragging up puts it before, which matches the old single-row behaviour.
- To drag a multi-selection, a press on an already-selected row (with several selected) returns `"break"` so Tk's default handling doesn't collapse the selection. If the mouse is released without moving, the selection collapses to that row, which is what a plain click normally does. Shift and Ctrl presses are left to the default and start no drag.
- Preview text lists, in order: counts (to write, already correct, unticked, blocked), how the order is recorded, where originals or copies go, how many files would be renamed, then each issue with `old -> new` per ComicInfo field. In copy mode it shows the remembered destination, or says the folder is chosen when writing.
- Preview reads only the in-memory plan, so it touches no file; reopening it replaces the previous window.

**Bugs found and fixed:** the first version of the preview code had mangled escape sequences in two string literals (a syntax error caught by `ruff` before anything ran); fixed.

**Verification:** a scripted test ran and passed. *Logic:* block moves up and down including edges and scattered selections; block drops above and below a target, onto a selected row and onto an unknown row; preview lines for changed, unchanged and blocked issues. *Window (headless):* extended selection mode; a 3-row block moved up twice, stopping at the top and moving down once with the selection kept; a block dragged to the bottom (press, motion, release) renumbering rows; a plain click on one of several selected rows selecting only it; Ctrl+click starting no drag; dragging an unselected row moving only that row; tick boxes applying to the selection or to just the clicked row; removing a 3-row block; the Preview button disabled without a name; preview text in place, copy (with and without a remembered parent) and with a group, unticked row and prefix; the preview window opening, being replaced on reopen, and following a theme switch; the folder and files unchanged after previews; and the preview saying "0 would be written, 4 already correct" after a real write. The earlier order, scan, audit, metadata, backup and renamer tests and `ruff --select F,E9` still passed. A screenshot showed a selected block moved together with the highlight intact; the preview window itself was not captured. Not run: real mouse dragging by a person, real comics, or YACReader, which are in [manual-tests.md](manual-tests.md) (E2b, E2c).

**Known issues:** unchanged; see [Known limitations](known-limitations.md).

---

## 2026-10-07 15:35 +11:00 · Session 23: Reading Order tool (roadmap item 4)

**Summary:** New Home group **Reading Orders** with the **Reading order** tool. Issues from one or several folders are arranged in the order you want to read them, and that order is written into each CBZ's `ComicInfo.xml`. Optional filename prefixes and a "copy to a new folder" mode are included. The spec in `docs/reading-order.md` was rewritten from "planned" to a description of what was built.

**Decisions** (the spec left these open; each can be changed)
- Storage choice is a menu: *Story arc* (`StoryArc` + `StoryArcNumber`, the default), *Alternate series* (`AlternateSeries` + `AlternateNumber` + `AlternateCount`) or *Both*, so YACReader can be tested with each.
- Arc numbers can be plain or zero-padded (width follows the total, at least two digits), in case YACReader sorts the number as text. Plain is the default until tested.
- Filename prefix is a menu (`Off`, `01 - Name`, `[01] Name`), off by default.
- Issues already in another arc are shown as *Replaces “name”*, ticked by default; unticking skips that issue, which still keeps its place in the numbering.
- "Copy to a new folder" asks for the parent folder at write time, names the folder after the reading order, remembers the last parent, and stamps only the copies (no backup needed).
- Not built: cover thumbnails, a saved order file, undo (the table is text-only to keep the page light).

**Changes by file**
- `reading_order.py` (new): `suggest_key`, `writes_for`, `plan_item`, `apply_item`, `writable`, `current_arc`, number and prefix helpers, store/numbering/prefix constants. `apply_item` writes in place (metadata, then rename) or copies first and stamps the copy; a refused rename after a successful write raises a message saying so; a missing file raises "File not found".
- `page_order.py` (new): `OrderPage` with a drop area, Add folder, Suggest order, ▲ ▼, Remove, Clear, drag-to-reorder and tick boxes in the table, live plan preview (new number, new filename, current arc, status), a load worker and a write worker reporting through queues, and a YACReader import reminder.
- `rename_core.py`: `split_order_prefix`; `parse_filename` strips a reading-order prefix first and returns `order_prefix`; `read_comicinfo` also returns `story_arc`, `story_arc_number`, `alternate_number`, `alternate_count`.
- `archive_tools.py`: `CI_TAGS` gains `story_arc`, `story_arc_number`, `alternate_number`, `alternate_count` (no change to the writer, as planned in item 1).
- `page_rename.py`: new **Keep the number at the start** switch; without it the Renamer drops the prefix as it renames.
- `comic_tool.py`: registers the page, the `order` card, the "Reading Orders" group; a drop on a page with `add_paths` passes every dropped item to it (several files or folders at once).
- Docs: `reading-order.md` (rewritten), `tools.md`, `architecture.md`, `known-limitations.md`, `safety.md`, `roadmap.md` (item 4 done), `manual-tests.md` (section E, 12 checks), both READMEs and the docs index.

**Technical notes**
- Prefix recogniser: `^(\[\d{2,4}\]\s+|\d{2,4}\s+-\s+)` followed by text containing a letter. It is deliberately narrow, but a real name such as `100 - Bullets 05` would be misread.
- Position `n` is the row's place in the whole list, including unticked and blocked rows, so numbers never shift when an issue is skipped.
- Plans only list fields whose value differs from what the file has, so re-running an unchanged order shows *No change* and rewrites nothing.
- Renumbering replaces an existing prefix (`split_order_prefix`) instead of stacking another one.
- Drag-reorder moves the row live with `Treeview.move` and re-syncs the list on mouse release; the tick box is column 1 and starts no drag.
- The method name `_options` collided with a Tk internal (as in an earlier session), so the page uses `_plan_options`.

**Bugs found and fixed:** the first run of the page crashed on that `_options` collision. A write to a file deleted after it was added gave the misleading message "Not a zip-based archive"; `apply_item` now says the file was not found. Both were caught by the scripted tests.

**Verification:** scripted tests ran and passed. *Logic:* number and prefix helpers; the three storage forms; parser recognition of `03 - Name` and `[012] Name` while `2000 AD 01` is left alone; suggested order; blocked `.cbr`; plans for new and replaced arcs; an in-place write with backup and rename; re-planning giving *No change* and a renumber replacing the prefix; a rename collision reporting that metadata was written; copy mode with unique names, untouched originals and no `Archive` folder; reading back `AlternateSeries/Number/Count`. *Window* (headless): adding a folder, loose files, a duplicate, a text file and a `.cbr`; the arc-name requirement; ▲, drag and Suggest order; tick boxes; Remove and Clear; a write with prefixes confirmed by the dialog text, files, metadata and `Archive` backups; a second write after reordering with no stacked prefixes; copy mode with a remembered parent; a failing file leaving the page usable; settings round-trip without the arc name; theme switch; the Renamer with and without **Keep the number at the start**; the whole app registering the page and routing a drop to it. The earlier scan, audit, metadata, backup, archive and renamer tests and `ruff --select F,E9` still passed, and all doc links resolved. A screenshot of the page was checked in dark mode and led to a wider Status column; light mode and the final widths were not viewed.
Not run: real comics, YACReader (sorting and display of the arc fields), a large list, or any of the manual tests in section E of [manual-tests.md](manual-tests.md).

**Known issues:** see [Known limitations](known-limitations.md): no thumbnails, no saved order, YACReader behaviour untested.

---

## 2026-10-07 00:37 +11:00 · Session 22: review pass over everything built so far

**Summary:** A check of the whole project before starting Reading Order: every scripted test rerun, a lint pass, a visual check of the new pages, and a read-through of the new code. It found and fixed four bugs and three layout problems. No features were added.

**Bugs found and fixed**
- `library_scan.py`: pruning the cache after a scan matched on a path prefix, so scanning `D:\Comics` also dropped cache entries for `D:\Comics Old`. The prefix now ends with a path separator. Only cost was a slower later scan.
- `page_audit.py`: if the scan worker raised (for example an unreadable folder), nothing was ever posted back and the page showed a Stop button forever. The worker now catches errors and reports "Scan failed: …", and the page returns to idle.
- `page_audit.py`: with both **Read page counts and covers** and **Full integrity test** off, the Broken report said "No broken files found" although nothing had been checked. It now says "Nothing was checked." with a hint on what to turn on.
- `docs/roadmap.md`: leftover "Health" wording replaced by "Library audit" / "the audit".

**Layout fixes (from screenshots of the real window)**
- Duplicates table: the "Why" column cut off "Same series, volume and issue"; widened.
- Broken and Quality tables: the Flags / Problem column was the one that got squeezed; the File column is now fixed width and the text column takes the spare room. The low-resolution flag text was shortened to "Low-res cover (WxH)".
- Footer: the report-specific buttons sat in an empty frame that kept its old height after being hidden, leaving a gap above Export CSV on the Broken and Quality tabs. The buttons are now packed straight into the footer.

**Checked and left alone**
- Duplicate cover comparison is quadratic in file count. Timed on random hashes: 2,000 files in 0.3 s, 5,000 in 1.9 s, so about 8 s for 10,000.
- The Metadata page's "Set for checked rows" section sits below the fold at the default window size and is reached by scrolling the side panel. It works; it is just not visible at first glance.
- Full `ruff` reports 41 style items (mutable class attributes, import order, regex flag aliases and similar); none are bugs. The error-level checks (`--select F,E9`) are clean.

**Verification:** these scripted tests were run and passed: archive tools (including `.bak` backups), icons, renamer and parser, backup naming, metadata (core and page), library scan, audit logic, audit window, and a new test for the three fixes above (sibling-folder cache entries kept, deleted-file entries still pruned, "Nothing was checked", and a failing worker releasing the page). The icons test needed an update because it called `write_icon` with an old argument name; the app's own callers were already correct. Screenshots of the Home page, Metadata, and all four audit reports were checked in dark mode before and after the layout fixes; the final capture of the Quality tab was partly covered by an unrelated window from the desktop, but the footer change was visible. Light mode was not re-checked after the fixes. Not run: any real RAR file, real comic collections, YACReader, or the manual tests in [manual-tests.md](manual-tests.md).

**Known issues:** unchanged; see [Known limitations](known-limitations.md).

---

## 2026-10-07 00:15 +11:00 · Session 21: Library Audit tool (roadmap item 3)

**Summary:** New Home group **Library Audit** with one tool, *Library audit*: scan a folder once, then switch between four reports (Broken, Duplicates, Missing, Quality). Built on the shared scan from Session 20. Logic lives in `audit_core.py`, the window in `page_audit.py`.

**Decisions**
- The report the roadmap called "Corrupt or broken" is shown as **Broken**, and the group is "Library Audit" (the earlier name "Library Health" was dropped).
- The full CRC/decode integrity test is a switch, off by default, because it reads every file completely. The quick scan already reports files that are not valid zips, have no images or have an unreadable cover.
- Duplicate cover comparison is a switch with three levels, Strict (4 of 64 hash bits), Normal (8), Loose (12). Defaults are untested on real covers.
- The only action that touches files is *Move checked to Archive*; it asks first, pre-ticks every copy except the biggest in each group, and moves as `.bak` (Session 18), never deleting.
- Missing issues are checked from the lowest owned issue by default; **Expect issues from #1** is a switch. The wishlist is export or copy only, with no stored state.
- Quality limits (10 to 300 pages, 1 MB to 500 MB, cover under 800 px tall) are fixed constants, not options.

**Changes by file**
- `audit_core.py` (new): `check_integrity` and `test_rar`; `find_duplicates` returning `Group` objects (tier 1 series+volume+issue, tier 2 identical size, tier 3 cover hash clusters via union-find, groups wholly contained in an earlier group dropped, biggest file first); `find_missing` returning `Gap` objects plus an ignored count, `ranges`, `gap_name`, `wishlist_lines`; `quality_flags`, `find_quality`, `size_text`; `SIMILARITY` levels and the threshold constants.
- `page_audit.py` (new): `AuditPage` with a scan worker thread reporting through a queue, four themed tables behind a segmented switch, Stop, per-report buttons (Move checked to Archive, Copy wishlist, Save wishlist, Export CSV), tick boxes in the Duplicates table, and a hint line explaining each report.
- `comic_tool.py`: registers the page, adds the `audit` card and the "Library Audit" group, updates the module docstring.
- Docs: `tools.md` (new section), `architecture.md`, `known-limitations.md`, `safety.md`, `roadmap.md` (item 3 done), `manual-tests.md` (new section D, 12 checks), both READMEs.

**Technical notes**
- Without the integrity switch the Broken report is simply the scan's `Issue.error` values. With it, `check_integrity` runs per CBZ: `ZipFile.testzip`, at least one image, and the cover, middle and last pages decoded fully with Pillow. A `.cbz` that is not a zip is reported as "Not a valid zip (may be a misnamed RAR)". Real RAR files use `7z t`, `unrar t` or `tar -tf`, whichever extractor was found, and only when **Open real .cbr files** is on.
- Series and issue matching normalise case and punctuation, strip leading zeros from issue numbers, and compare the volume as text.
- Cover clustering compares every pair of hashes (quadratic); fine for thousands of files, not yet measured on a very large library.
- A missing-issue range ends at the larger of the highest owned issue and the largest `Count` seen in that series. Annual/special/one-shot/giant/king-size names, decimal issue numbers and files without a whole issue number are counted as ignored, not as gaps.
- Moving duplicates removes the moved files from the in-memory results and re-draws the table; the scan cache entries for them are dropped at the next scan.
- Results exist only in memory for the session; the scan cache is the only thing stored.

**Bugs found and fixed:** none in the shipped code during this session. Test-script mistakes (an off-by-one file count, a fixture whose cover coincided with another, a console encoding error printing check-box glyphs) were fixed in the tests.

**Verification:** scripted tests ran and passed. *Logic* (generated library): healthy CBZ passes; a text file named `.cbz`, a zip with no images, a zip with an undecodable middle page and a CBZ with a flipped byte are all reported; a fake RAR fails the extractor test; duplicates found by name and by identical size; a re-encoded, resized copy of a cover clustered at 1 bit apart and not reported when already grouped by name; missing issues `#4, #7-#8, #10-#12` with the end taken from `Count`; start-at-lowest versus from-#1; annuals and decimals ignored; wishlist lines; page-count, size and cover-height flags. *Window* (headless, real widgets): scan with progress; all four tables filled; the full integrity switch; tick boxes (pre-ticked smaller copy, toggling, Move button enabling); Move to Archive declined then accepted, producing `Archive/<name>.bak` and updating the table; clipboard wishlist and saved `.txt` and `.csv`; CSV export for each report; a similarity scan stopped part-way; cache hits on a repeat scan; theme switch and settings round-trip; changing folder clearing results; the whole app starting with the new page registered. `ruff --select F,E9` was clean, the earlier scan, metadata and logic tests still passed, and every doc link resolved.
Not run: real comics or real RAR files, a large library, YACReader, or a visual check of the page. Those are manual tests D1 to D12.

**Known issues:** see [Known limitations](known-limitations.md): similarity levels, quality limits and missing-issue rules are untested on real data.

---

## 2026-10-06 23:27 +11:00 · Session 20: shared library scan (roadmap item 2) and manual test plan

**Summary:** New `library_scan.py` gives every future tool one way to read a library: an `Issue` record per comic, optional deep reading, and a disposable cache. It has no window yet; a command-line report exists so it can be checked by hand. A manual test plan covering items 0 to 2 was added.

**Decisions**
- No UI this session, as the roadmap said. A CLI (`python library_scan.py FOLDER`) was added so there is something a person can run and check.
- Deep mode reads page count, cover size and cover hash from the first page only. A full CRC test is left to the Audit tool.
- A `.cbz` that is not a zip is an error (`Not a valid zip`); a `.cbr` that is a real RAR is "unknown" unless `--deep-cbr` is given.
- Parsed filename fields are not cached, so parser changes apply immediately.

**Changes by file**
- `library_scan.py` (new): `Issue` and `ScanResult` dataclasses, `scan_library(...)`, `cover_hash` (64-bit difference hash via Pillow), `hash_distance`,
  cache load/save, `default_cache_path`, and `main()` for the command line (`--deep`, `--deep-cbr`, `--no-recursive`, `--no-cache`, `--cache-file`, `--csv`, `--limit`).
- `docs/manual-tests.md` (new): hands-on checks A (backups), B (metadata extensions) and C (library scan), each with an expected result.
- `docs/architecture.md` (new section "The library scan"), `docs/getting-started.md` (cache location, command-line use), `docs/known-limitations.md`,
  `docs/roadmap.md` (item 2 marked done), `docs/README.md` and the root `README.md` (link to manual tests).

**Technical notes**
- File discovery reuses `rename_core.find_files`, so `Archive` folders are skipped and `include_other` adds `.pdf` / `.epub` as light records.
- Cache file: `{"version": 1, "entries": {<lower-cased path>: {size, mtime, ci, ci_read, deep, pages, error, cover_w, cover_h, cover_hash}}}`.
  An entry is reused only when size and mtime match and it holds what is asked (light entries never serve a deep scan, except real-RAR `.cbr` files that deep mode skips anyway).
  Entries for deleted files under the scanned root are pruned after a complete scan (not after a stopped one). Writes go through a temp file and replace.
- JPEG covers are decoded with `Image.draft` at about 64 px, which keeps the hash cheap.
- `from __future__ import annotations` keeps `int | None` annotations valid on Python 3.9, the documented minimum.
- A scan error on one file (locked, vanished) yields an `Issue` with `error` set instead of aborting the scan.

**Bugs found and fixed:** the first version treated any non-zip `.cbz` as an unreadable-RAR "unknown" instead of an error, and reused light cache entries for it
in deep mode. The test caught it; deep mode now flags it and the cache rule was adjusted. Extractor errors were multi-line; they are now collapsed to one line for tables and CSV.

**Verification:** a scripted test with a generated library ran and passed: the Archive folder skipped; `.pdf` excluded unless asked; light-scan fields from names and `ComicInfo.xml` (including `Count` and `Publisher`); a zip-backed `.cbr` read in place and a fake RAR left unknown; the progress callback; a second run served entirely from cache;
a deep scan after a light one re-reading as needed and then fully cached; page counts and cover sizes; `Not a valid zip`, `No images found` and `Cover unreadable` errors;
a fake RAR with `--deep-cbr` giving a captured extraction error; a modified file re-read alone and a deleted file pruned from the cache; a corrupt cache file ignored and rewritten;
`use_cache=False` writing nothing; the stop event ending a scan after three files; non-recursive and `include_other` listings; and the CLI writing a CSV and returning 2 for a missing folder.
Cover hashes: the same generated cover re-encoded smaller and at lower quality differed by 1 bit; a different cover by 33. `ruff --select F,E9` was clean and every doc link resolved.
Not run: any real RAR file, real comic covers, a large library for timing, or the GUI. Those are in [manual-tests.md](manual-tests.md).

**Known issues:** the similarity threshold and scan speed are untested on real data; the scan has no window yet.

---

## 2026-10-06 23:20 +11:00 · Session 19: metadata extensions (roadmap item 1)

**Summary:** The Metadata tool now handles issue count, reads more `ComicInfo.xml` fields, and can set fixed values (Series Group, Genre, Alternate series, Publisher) on the checked rows.

**Decisions**
- Publisher is settable as well as read; a read-only Publisher had no use. This goes slightly beyond the roadmap wording.
- "Selected rows" means checked rows, matching how the table already works.
- Only the "(of N)" / "(n of N)" forms are parsed as a count.

**Changes by file**
- `rename_core.py`: `_COUNT` regex; `parse_filename` returns a `count` key (None when absent or 0); `read_comicinfo` also returns `count`,
  `publisher`, `series_group`, `genre`, `alternate_series`.
- `archive_tools.py`: `CI_TAGS` gains `count`, `publisher`, `series_group`, `genre`, `alternate_series`. `merge_comicinfo` was already generic, so it writes them unchanged.
- `page_metadata.py`: `count` added to `FIELDS` / `LABELS` / `EDITABLE`, new "Of" column, `w_count` switch, `Row.sets`, `SET_FIELDS`, a
  "Set for checked rows" form section (field menu, value entry, button), `set_selected()`, and a YACReader reminder note under the table.

**Technical notes**
- `_compute` applies `row.sets` after the filename fields, so a set value is written whenever it differs from what the file has, regardless of the
  Fill / Overwrite choice. Sets live on the row and vanish on rescan.
- Count regex: `[(\[]\s*(?:\d+\s*)?of\s*(\d+)\s*[)\]]`. The existing `_TAGS` bracket stripping is unchanged, so the series and issue parse is unaffected.
- The Renamer's `merge` now carries the extra keys but templates only use the original five tokens, so renaming is unchanged.
- The reminder note is on the Metadata page only; Clean-up writes no metadata.

**Verification:** a scripted test ran and passed. Count parsing: five filenames (round and square brackets, with and without the issue number, a zero count ignored). The Renamer preset output was unchanged. `apply_metadata` wrote all five new fields, `read_comicinfo` read them back, and a second write kept them. The page was instantiated headless against two temp CBZs: the count was proposed as `2`, "Set value" applied Genre to the checked row only, an empty value cancelled it, a write went through with a `.bak` backup, and the table row showed the count. `ruff --select F,E9` was clean. I did not look at the page visually, and YACReader's display of the new fields is untested.

**Known issues:** see [Known limitations](known-limitations.md): bare "(3/12)" isn't parsed, and the new fields have no table columns or Renamer tokens.

---

## 2026-10-06 23:10 +11:00 · Session 18: backups stored as `.bak` (roadmap item 0)

**Summary:** Backups and converted originals in `Archive` folders are now renamed with a `.bak` suffix, so YACReader should not import them as duplicate comics.

**Changes**
- `archive_tools.py`: new constant `BACKUP_SUFFIX = ".bak"`; `move_to_archive` now targets `Archive/<name>.bak` (docstring updated).
  Both callers pick it up: `swap_in` (Clean-up and Metadata backups) and `dispose_original` (CBR to CBZ "Move to Archive folder").
- Docs: `safety.md`, `known-limitations.md`, `tools.md`, `roadmap.md` (item 0 marked done) and the root `README.md` describe the `.bak` behaviour.

**Technical notes**
- Name collisions go through the existing `unique()`: a second backup of `Batman 01.cbz` becomes `Batman 01.cbz (1).bak`.
  Restoring means moving the file back and deleting `.bak` (and the ` (1)` if present).
- Backups made before this change keep their real extensions and are not migrated.
- Scans skip `Archive` folders as before, so nothing else changed.
- No restore button or log note was added; the roadmap says so.

**Verification:** a scripted test in a temp directory ran `swap_in` with backup twice and `dispose_original` with the Move option. It confirmed
backups landed as `Batman 01.cbz.bak` and `Batman 01.cbz (1).bak`, the moved `.cbr` became `X 01.cbr.bak`, no backup carries a comic extension,
the live file stayed in place, a backup opens as a valid zip, and `find_comics` lists only the live file. The GUI was not launched, and
YACReader's handling of `.bak` files is untested.

**Known issues:** older `Archive` backups with real extensions may still be imported by YACReader.

---

## 2026-10-06 22:12 +11:00 · Session 17: documentation split into a docs folder

**Summary:** The single README had grown to about 270 lines. It is now a short overview, and the detail lives in topic files under `docs/`.

**Changes**
- `README.md` (rewritten, root): overview, quick start, a table of the tool groups, safety at a glance, and links into `docs/`.
- `docs/` (new): `README.md` (index plus how the docs are kept current), `getting-started.md` (install, RAR extractor, settings),
  `tools.md`, `renamer-templates.md`, `safety.md`, `architecture.md`, `known-limitations.md`, `roadmap.md`, `reading-order.md`,
  `versioning.md`, and this changelog (moved from the project root).
- `CHANGELOG.md` moved to `docs/CHANGELOG.md`; the maintenance-rule line in its conventions now points at `docs/README.md`.

**Technical notes**
- The split was done programmatically by heading, so the text of each section is unchanged. Edits were limited to: section headings
  promoted to page titles (and sub-headings demoted a level), a navigation link back to the docs index on every page, the naming presets
  and template syntax carved out of the tools page into `renamer-templates.md`, and cross-links (for example "see Roadmap item 0" now links
  to `roadmap.md`, and "spec below" links to `reading-order.md`).
- Earlier changelog entries still say "README" for text that now lives in `docs/`. They are historical and were not rewritten.
- Remaining planned work is unchanged.

**Verification:** every relative link in the root README and in `docs/` was checked to resolve to an existing file. Every non-empty line of the previous README was compared against the new files: 24 lines differ, all of them the intentional edits listed above (headings, retargeted links, the replaced overview and quick-start wording, the maintenance text). That comparison caught one mistake of mine, a sentence turned into a heading in `renamer-templates.md`, which was fixed. The application code was not touched, so no tests were run.

---

## 2026-10-06 22:07 +11:00 · Session 16: changelog scrub and repository fix

**Summary:** Removed references to development tooling from earlier entries, then corrected the published repository so it contains only the
cleaned file.

**Changes**
- `CHANGELOG.md`: removed the lines in Sessions 6-15 that referred to development tooling, and the note in Session 15 about them. No
  technical content about the project itself was removed.

**Technical notes**
- The repository already held 17 commits on `main` and the `v0.1.0` tag, all pushed to `origin`. Only the last commit (`docs: add CHANGELOG`)
  contains this file, so the fix is to amend that commit, move the `v0.1.0` tag onto the amended commit, and force-update `main` and the tag
  on `origin` (`--force-with-lease` for the branch). The amended commit gets a new hash; the 16 earlier commits are unchanged.

**Verification:** a search of `CHANGELOG.md` and `README.md` for the removed terms returns nothing. Git steps are listed for the user to run.

---

## 2026-10-06 22:02 +11:00 · Session 15: commit messages rewritten, versioning scheme

**Summary:** Rewrote the commit series for the initial import and defined how releases are tagged. Docs only.

**Decisions (from the user)**
- Commit messages describe each file **as it is now**, not as earlier versions of it.
- **No co-author trailers** in the messages; the user adds their own trailer in their own format.
- Tags follow `vMAJOR.MINOR.PATCH` and stay at `v0.x.y` until a public release. For now the project is added to git as a series of
  feature commits; the user commits changes periodically afterwards.

**Technical notes**
- The series is 17 commits in dependency order (`.gitignore`, core, UI kit, Single issue, Bulk folder, Renamer logic and page, archive tools,
  folder icons, batch scaffold, the Convert, Clean-up, Folder icons and Metadata pages, the app shell, README, CHANGELOG). Because files are
  committed in their current state and the app shell imports every page, the app first runs at the app-shell commit.
- Only one tag, `v0.1.0`, is created for the initial import, placed on the last commit. Earlier commits are not tagged because they are not
  runnable on their own. A planned tag per roadmap milestone is documented in the README's Versioning section.

**Changes:** `README.md` (new "Versioning" section with the scheme and planned tags). No code touched.

**Verification:** documentation only; `git status` and `git log` were checked (no commits existed yet at the time).

---

## 2026-10-06 21:52 +11:00 · Session 14: group rename and git repository preparation

**Summary:** Renamed the planned Health tool's Home group and prepared the project for its first git history and a GitHub remote.

**Decisions**
- The planned Home group **"Library Health" is renamed "Library Audit"** (user did not like the first name). Alternatives offered:
  "Collection Checkup", "Quality Control". Session 13's text keeps the old name as a record of that session; this entry supersedes it.
- The project is published to GitHub with a **dependency-ordered commit series**: shared core and UI first, then each tool in the order it
  was introduced, then the app shell, then the docs. Files are committed in their current state, so the series shows when each feature was
  introduced rather than every intermediate edit; this changelog holds the per-session detail.

**Changes**
- `.gitignore` (new): Python caches, virtual environments, `settings.json` (per-user, holds local paths), `*.part` / `*.renametmp`
  temporaries, PyInstaller output (`build/`, `dist/`, `*.spec`), editor and OS files.
- `README.md`: roadmap item 3 group name changed to "Library Audit".

**Repository state observed (read-only checks):** branch `main`; nothing committed yet; `gh` CLI not installed; global git identity is set to a
university email, which would be public on GitHub, so a repo-local identity (GitHub noreply address) was recommended before the first commit.

**Verification:** `git status` reviewed; no code changed, so no tests run.

---

## 2026-10-06 21:44 +11:00 · Session 13: roadmap review and rewrite (no code)

**Summary:** Reviewed every planned feature against what has been learned about YACReader, the existing code and Windows packaging. Found one
problem in already-built behaviour, reworked several plans, and re-ordered the build list. Docs only.

**Findings**
1. **`Archive` backups likely appear in YACReader.** The web search showed YACReader supports cbz/cbr/zip/rar/7z/pdf and displays sub-folders
   of the library; no folder-exclusion option was found. Backups and converted `.cbr` files are stored as ordinary `.cbz` / `.cbr` files in
   `Archive` subfolders, so YACReader would probably import them as duplicates. **Inference, not tested.** *Convert to ZIP* in Single issue
   also writes a `.zip` that YACReader supports.
2. **ComicInfo import is opt-in and update-driven in YACReader** (off by default since 9.10), so every metadata write needs a reminder.
3. **Reading Order** must stay metadata-based: YACReader keeps story-arc fields as plain text, has no reading-list import, and keeps Reading
   Lists in `library.ydb`.
4. **Overlapping scanners:** Health, Stats, folder browser and pipeline all need the same scan. Four separate walkers would duplicate parsing,
   `ComicInfo.xml` reads and (slow) RAR extraction.
5. **Pipeline safety and reach:** automatic unreviewed writes to a library are risky; a watcher inside the app only works while it is open.
6. **Packaging:** `Path(__file__).with_name("settings.json")` in `comic_tool.py` points into a temporary or internal folder in a PyInstaller
   build, so settings would be lost; `tkinterdnd2` and `customtkinter` need their data files bundled.
7. **Parser gap:** `rename_core._TAGS` strips bracketed text, so "(of 12)" is discarded even though YACReader has an "Issue count" field.

**Rewrites to the plan**
- New **item 0**: store backups as `<name>.bak` inside `Archive` so readers ignore them (proposed; needs the user's sign-off before changing
  `archive_tools.move_to_archive`).
- **Metadata extension** narrowed to fields YACReader exposes: parse `Count`, read `Publisher`, add "Set for selected rows" for `SeriesGroup`,
  `Genre`, `AlternateSeries`; `CI_TAGS` / `merge_comicinfo` become a generic writer shared with Reading Order.
- New **shared scan layer** (`library_scan.py`) with a disposable cache (path + size + mtime) inserted before Health; Stats, browser and pipeline
  reuse it. Cache is explicitly not a database of record.
- **Health** gets concrete methods: CRC test, extractor test for CBR, sampled-page checks, three duplicate tiers (cover-hash optional via
  Pillow), gap detection against the highest owned number or `Count`, wishlist as `.txt` / `.csv` / clipboard, report-only actions (move to
  `Archive`, never delete). New Home group "Library Health" proposed.
- **Folder browser** repositioned as a launcher into the other tools rather than a YACReader-style library view.
- **Pipeline** order fixed (convert, clean-up, metadata, rename, move), review-by-default staging, in-app polling watcher with size-stability
  check, CLI mode deferred.
- **Packaging** specified as a folder build with settings in `%APPDATA%\ComicToolkit` and optional bundled `7za.exe`.
- **Build order:** 0 backup fix, 1 metadata extensions, 2 scan layer, 3 Health, 4 Reading Order, 5 Stats, 6 folder browser, 7 pipeline/watcher,
  8 packaging.

**Changes:** `README.md` (Roadmap rewritten with a findings table and a numbered build order; Reading Order section gained dependency and
reminder notes; two new known limitations: `Archive` folders and the YACReader ComicInfo setting). No code touched.

**Verification:** documentation only. One web search was run in this session (YACReader formats and folder handling); the code facts
(`_TAGS` regex, `settings.json` path, `Archive` handling) were confirmed by grepping the source.

---

## 2026-10-06 21:38 +11:00 · Session 12: YACReader editable-field list recorded (no code)

**Summary:** The user supplied the complete list of per-issue fields YACReader can edit. Recorded and analysed against the Metadata and
Reading Order plans. Docs only.

**Input (user-supplied list):** Series, Title; Issue number, Issue count, Volume; Story arc, Arc number, Arc count; Alternate series,
Alt. number, Alt. count; Series Group, Genre.

**Analysis**
- Most fields map to standard `ComicInfo.xml` tags: `Series`, `Title`, `Number`, `Count`, `Volume`, `StoryArc`, `StoryArcNumber`,
  `AlternateSeries`, `AlternateNumber`, `AlternateCount`, `SeriesGroup`, `Genre`. The mapping is inferred from names, not read from
  YACReader's source.
- **Arc count has no standard ComicInfo tag**, so it may not be importable from XML. This explains the open "(n/count)" question from
  Session 10: the count shown by YACReader may be blank for imported files.
- The **Alternate series** trio (`AlternateSeries`, `AlternateNumber`, `AlternateCount`) is a complete name/position/total set, which could
  carry a reading order with a total, unlike `StoryArc`/`StoryArcNumber`.
- The list contains no Year field in the editor; the Metadata tool still writes `Year` (harmless, kept in the file for other readers).
- The Metadata tool could additionally write `Count` (the filename parser currently discards "(of N)"), `SeriesGroup`, `Genre`,
  `AlternateSeries`.

**Changes:** `README.md` (editable-fields list, storage options to test, Metadata-extension candidates). No code touched.

**Open items for the build:** test in the real YACReader (a) whether `StoryArc`/`StoryArcNumber` or the Alternate trio is imported and shown
better, (b) whether Arc count imports from any tag, (c) arc/alt number sorting (numeric vs text).

**Verification:** documentation only; no behaviour was tested against YACReader.

---

## 2026-10-06 21:35 +11:00 · Session 11: Reading Order spec refined with the user's YACReader research (no code)

**Summary:** The user supplied research on how YACReader handles multi-value story arcs; combined with a changelog check, it sharpened the
Reading Order spec. Docs only.

**Input (user research, unverified by me beyond the points marked)**
- YACReader stores `StoryArc` as one literal string; a comma-separated value is not split into separate arcs (matches the source excerpt
  reviewed in Session 10).
- Search is a substring match on that string; sorting by the Story arc column groups alphabetically by arc name, so a multi-arc issue sorts
  under the first arc's name. (Not independently verified.)
- YACReader's **Reading Lists** are the intended way to mix comics from several folders. A web search indicated lists live in the
  `library.ydb` SQLite database and found no import file format for them (forum threads there mention users requesting export).

**Findings from my own check:** the YACReader 9.14.1 changelog lists new table columns Series, Volume and Story arc and does not mention an
arc-number column. This raised the concern that position inside an arc might not be sortable in the table.

**Resolution:** the user checked their YACReader (9.14+): the table view **does have an Arc number column**. So metadata alone can show and
sort the order.

**Decisions (from the user)**
- Approach: **write `StoryArc` + `StoryArcNumber` metadata and keep the filename prefix as a first-class option; test first.** At build time,
  test in the real YACReader whether the arc number column sorts numerically or as text and set the prefix default accordingly.
- Multi-arc issues: keep the Session 10 rule (single arc string only; ask per issue to replace or skip).
- Not pursued: writing YACReader Reading Lists by editing `library.ydb` (risky, version-dependent, needs YACReader closed). It stays a
  research-only idea, not on the build list.

**Changes:** `README.md` (YACReader notes and display strategy in "Planned: Reading Order"). No code touched.

**Technical considerations recorded:** arc-number sort behaviour (numeric vs text) decides zero-padding of `StoryArcNumber`; unverified items
from Session 10 (tag-to-field mapping, source of the "(n/count)" count) remain open and should be checked with a real test archive.

**Verification:** documentation only. The user's Arc number column check is the only first-hand confirmation; web findings are from search
and fetch results.

---

## 2026-10-06 21:05 +11:00 · Session 10: Reading Order spec revised to use ComicInfo.xml (no code)

**Summary:** Replaced the filename-prefix and `.cbl` parts of the Reading Order spec with metadata stored in `ComicInfo.xml`, after
checking what YACReader actually supports. Docs only.

**Decisions (from the user)**
- Reading Order gets **its own Home group** ("Reading Orders").
- `.cbl` export dropped: YACReader doesn't support it. Use embedded **ComicInfo.xml** instead.
- Show the order via metadata rather than renaming. Filename prefix kept only as an **optional switch, off by default** (for Explorer
  browsing), with the Renamer-strips-prefix behaviour from Session 9 retained for that case.
- Multi-folder orders: **optional "also gather copies" switch** (off by default); when on, only the copies are stamped.
- YACReader version is **9.14 or newer**.
- Issues already in another arc: "check whether YACReader supports multiple arcs, otherwise ask per issue". Result of the check below:
  it doesn't, so the review table asks per issue (replace or skip).

**Research (web; results summarised)**
- `ComicInfo.xml` (Anansi Project schema) has `StoryArc` and `StoryArcNumber`; the docs say they are used for reading orders across
  multiple series, and that multiple comma-separated values are accepted. One source notes that if the two lists have different
  lengths the extras are ignored and any invalid value voids the pair.
- YACReader changelog: 9.9.0 legacy XML info import; 9.10 ComicInfo.xml import made **optional and off by default** (Settings > General);
  9.13 "improves compatibility with ComicInfo.xml"; 9.14.0 story arc metadata in grid view headers; 9.14.1 a menu to choose table
  columns including **Story arc**, and `number` / `arcNumber` migrated to TEXT; 10.3.0 unified string-based universal number sorting.
- YACReader source (`common/comic_db.cpp`, as returned by a fetch): `storyArc` is stored as a single string with no comma splitting;
  `getStoryArcInfoString()` shows `"(arcNumber/arcCount) storyArc"`. Fields `arcNumber` and `arcCount` exist. The XML parsing code that
  maps ComicInfo tags to these fields was not located, so the tag mapping and the source of `arcCount` are **unverified**.

**Changes:** `README.md` ("Planned: Reading Order" rewritten, roadmap bullet updated). No code touched.

**Technical considerations recorded for the build**
- Reuse `archive_tools.apply_metadata` / `merge_comicinfo` (needs `StoryArc` and `StoryArcNumber` added to `CI_TAGS`), the Metadata page's
  table and threading pattern, and `swap_in` / `Archive` backups.
- Write a single arc name per issue; never the comma-separated form, since YACReader would show it as one string.
- Zero-padding `StoryArcNumber` depends on whether YACReader sorts it as text; test with real files in the user's YACReader before deciding.
- The optional filename prefix still needs the parser change from Session 9 (recognise only the tool's own padded-number-plus-separator
  pattern, so titles like "100 Bullets" aren't mis-stripped) and two-phase renaming to avoid collisions.
- Copy mode reuses the safe-write approach and stamps copies only.
- Home needs a new group "Reading Orders" in `comic_tool.GROUPS` / `TOOLS`.

**Verification:** documentation only. The research claims above come from the cited pages; nothing was run against YACReader.

---

## 2026-10-06 20:55 +11:00 · Session 9: Reading Order tool specified (no code)

**Summary:** Refined a new future feature through two rounds of questions and added it to the roadmap. Nothing was implemented.

**Feature:** a "Reading Order" tool. The user drags a series' issues into the order they want to read them and the tool prefixes each
filename with a number so the next issue is always first in the folder.

**Decisions (from the user)**
- Prefix style chosen **per run** in the window (style, separator, padding).
- Scope: **one folder** (rename in place) **or multiple folders**; for multiple folders, a new folder is created and the issues are
  **copied** into it with the numbered names. Parent location and folder name are **asked each time**; last parent remembered.
- Also export a **`.cbl` reading list** (ComicRack format, importable by YACReader).
- Changing the order later **renumbers everything automatically** (recognise existing prefixes, replace them, close gaps).
- Window: drag to reorder plus up/down buttons, **Suggest starting order**, **live preview of new names**.
- Interplay: parsers **recognise and ignore** the prefix; the **Renamer strips it** unless "keep reading-order number" is ticked.
- Not chosen, so out of scope: read/unread progress, ComicInfo `StoryArc` fields, a saved `reading_order.json`, undo, a dedicated
  "remove numbering" action (the Renamer strip covers part of that).

**Changes:** `README.md` (roadmap bullet and a "Planned: Reading Order" section). No code touched.

**Technical considerations recorded for the build**
- `rename_core.parse_filename` and `comic_core.series_name` must learn to drop a leading reading-order number. To avoid mis-stripping
  titles that start with a number (e.g. "100 Bullets 12", "2000 AD 2100"), only treat a leading number as a prefix when it matches the
  tool's own pattern (padded number plus the chosen separator).
- Renumbering in place needs a two-phase rename (temporary names first) because new names can collide with existing ones mid-run.
- Copying to a new folder reuses the safe-write approach (`.part`, verify, swap) and the existing conflict handling.
- The exact `.cbl` structure (books referenced by file name, series and number; whether YACReader needs paths) must be checked against
  a real file before implementing.
- Likely home: the "Comic Renamer" group on the Home page (open to change).

**Verification:** documentation only; the spec text in the README was checked against the answers above.

---

## 2026-10-06 20:43 +11:00 · Session 8: README and CHANGELOG

**Summary:** Added project documentation and set the policy that both files are updated every session.

**Changes**
- `README.md` (new): overview of every tool, naming presets and template syntax, safety model, settings, project layout,
  known limitations, roadmap, maintenance note.
- `CHANGELOG.md` (new): this file, including retroactive blocks for sessions 1-7.

**Technical notes**
- Retroactive timestamps come from `CreationTime` / `LastWriteTime` of the project files (earliest module file created
  19:06; latest feature files 20:28-20:36). The very first version of `comic_tool.py` was overwritten repeatedly, so its
  original creation time is lost.
- No code changes in this session.

**Verification:** documents read back against the code for tool names, options and file roles. No tests run (no code touched).

---

## 2026-10-06 20:28-20:42 +11:00 · Session 7: roadmap items 1-4 (CBR to CBZ, Clean-up, Metadata, Folder icons)

**Summary:** Built four tools from the roadmap's "extensions of existing code" group. Core logic first and tested, then a
shared batch-page scaffold, then the pages, then Home wiring.

**Decisions (from the user)**
- Backups and converted originals go to an **`Archive`** folder in the same folder as the file (not "Originals").
- Defaults: clean-up and metadata keep a backup in `Archive`; CBR to CBZ moves the `.cbr` to `Archive`.
- Home has **four groups**: Comic Cover Extractor (Single issue, Bulk folder, Folder icons), Comic Renamer (Renamer),
  Metadata (Metadata), Archive Tools (CBR to CBZ, Clean-up).
- Folder icons: Windows `folder.ico` + `desktop.ini`, plus `folder.jpg`, plus a **custom image** option for folders with
  no comics of their own (DC, Marvel). Not chosen, so not built: a "Remove icons" button and parent-folder inheritance.

**New files**
- `archive_tools.py`: constants `KEEP_NAMES`, `SEQUENTIAL`, `BACKUP`, `REPLACE`, `KEEP`, `MOVE`, `DELETE`, `CI_TAGS`.
  Functions `is_comicinfo`, `verify_zip`, `move_to_archive`, `swap_in`, `convert_to_cbz`, `dispose_original`,
  `rewrite_zip`, `plan_cleanup`, `describe_cleanup`, `apply_cleanup`, `read_comicinfo_raw`, `merge_comicinfo`,
  `apply_metadata`.
- `folder_icons.py`: `supported`, `make_ico`, `has_icon`, `write_icon`, `comics_in`, `plan_folders`, plus attribute and
  shell-notify helpers.
- `batch_page.py`: `BatchPage` base class and `_worker`. Subclasses implement `scan`, `label`, `work`, optional `validate`
  and `found_text`.
- `page_convert.py`, `page_cleanup.py`, `page_icons.py`, `page_metadata.py`.

**Modified files**
- `comic_core.py`: `ARCHIVE_DIR = "Archive"`, `in_archive()`; `find_comics()` now skips Archive folders.
- `rename_core.py`: `find_files()` skips Archive folders.
- `ui_kit.py`: added `ttk` import, `TREE_STYLE`, `build_tree()` and `apply_tree_theme()` (shared by Renamer and Metadata).
- `page_rename.py`: table and theme code replaced by the shared helpers (removed local `TREE_STYLE`, `ttk` import, inline styling).
- `comic_tool.py`: `TOOLS` dict + `GROUPS` list drive both the Home cards and the sidebar; four new pages registered; Home is a
  `CTkScrollableFrame`; `Card` redesigned compact (icon tile beside title, 138 px high); Home scroll resets to top on show;
  folder drops route to the current page when it has `set_folder`, else Bulk folder; new tints for the card tiles.

**Technical notes**
- *Write pattern:* every archive rewrite writes `<name>.part`, runs `verify_zip` (zip test + count of image pages), then
  `swap_in` replaces the target. With backup on, the original is first moved to `Archive/` (collision-safe via `unique()`),
  and restored if the swap fails. `.part` is always removed in `finally`.
- *Zip copying:* `rewrite_zip` preserves each entry's `date_time`; pages are `ZIP_STORED` (already compressed), everything
  else `ZIP_DEFLATED`.
- *Clean-up rules (`plan_cleanup`):* ComicInfo.xml is always kept (a root-level one is preferred). Pattern matches (fnmatch on
  basename or full path, case-insensitive) are removed even if they are images. Non-image files are removed only when "Remove
  non-image files" is on. `is_page` excludes `__MACOSX` and dot-files, so those count as junk. Sequential naming sorts pages
  naturally and uses width `max(3, len(str(page_count)))`, lowercases extensions, flattens folders and moves ComicInfo.xml to
  the archive root. Plans raise `ValueError` for non-zip files or when no pages would remain. "Changed" is true only if
  something is removed or renamed, so a second run reports "already clean".
- *Metadata:* `merge_comicinfo` parses the existing XML with ElementTree, sets/creates `Series`, `Number`, `Volume`, `Year`,
  `Title`, indents, and writes a UTF-8 declaration. Existing unrelated elements are preserved; XML namespace declarations are
  not. Malformed existing XML raises `ValueError` and that file is skipped. Issue numbers are normalised (`012` becomes `12`,
  `012.5` becomes `12.5`). Table values show the *resulting* ComicInfo value; status is Add / Update / No change. A manual cell
  edit always overrides, even in "fill missing only" mode. `.cbr` files are excluded from the table and counted in the header.
- *Folder icons:* cover is letterboxed onto a transparent 256x256 RGBA canvas and saved as multi-size ICO (16-256). `desktop.ini`
  is read with `configparser` (tries UTF-16, UTF-8-BOM, cp1252), `IconResource=folder.ico,0` is set in `[.ShellClassInfo]` (other
  keys such as `InfoTip` are preserved) and written as UTF-16 with BOM. Attributes: HIDDEN|SYSTEM on `desktop.ini` and
  `folder.ico`; READONLY on the folder (Explorer ignores `desktop.ini` otherwise). Files are reset to NORMAL before overwriting
  because hidden/system files can't be opened for write. `SHChangeNotify` is called to refresh Explorer. `folder.jpg` is kept if
  it exists unless "Replace" is chosen.
- *Threading:* `BatchPage` runs `work()` on a worker thread and reports through a `queue.Queue` polled with `after()`; no Tk calls
  in workers. A Stop `threading.Event` is checked between items.

**Bugs found and fixed during the session**
- `plan_cleanup` ComicInfo selection had a confusing duplicated condition; simplified to "first found, replaced by a root-level
  one".
- Home cards clipped the "Open" link when descriptions wrapped to three lines. Cards redesigned and copy shortened.
- Home kept its previous scroll offset after switching pages; now reset on show.
- `placeholder_text` on the clean-up pattern entry never displayed (entry bound to a `textvariable`); replaced by a hint label.
- Screenshots occasionally came back black after theme changes (CustomTkinter withdraws/re-shows the window to recolour the title
  bar). Test-harness issue, not an app bug; harness re-raises the window before each capture.
- A test cleanup failed to delete `folder.ico` because the test itself still held it open via `Image.open`. Test artefact.

**Verification (all run)**
- `test_archive` script: sequential clean-up plan and apply, backup into `Archive`, idempotent second run, `find_comics` skipping
  `Archive`, keep-names vs junk-removal plans, "No pages would be left" error, metadata merge into existing and fresh archives,
  malformed-XML error, no `.part` files left, zip-backed CBR conversion and move to `Archive`.
- `test_icons` script: planning (first/last issue, `Archive` skipped), `desktop.ini` merge keeps `InfoTip`, UTF-16 BOM, attributes
  `0x6` on files and `0x11` on the folder, ICO sizes, rewrite.
- End-to-end UI script (`smoke4`) through each page: Convert preview then run; Clean-up preview, run, re-run; Metadata scan, fill vs
  overwrite statuses, manual edit, apply, rescan shows 0 to update; Icons preview, run, custom icon on a parent folder.
- Regression of Single issue, Bulk folder and Renamer (`smoke3`) passed. `ruff check --select F,E9` clean.
- Screenshots reviewed: Home (light and dark), Metadata, Clean-up, Folder icons.

**Known issues / not verified**
- Real RAR (`.cbr`) extraction through 7-Zip / unrar / tar was not tested; only zip-backed `.cbr` files were.
- Folder icons were verified by file contents and attributes, not by viewing a folder in Explorer.
- Opening a CBR for the icon/cover extracts the whole archive.

---

## 2026-10-06 20:04 +11:00 · Session 6: feature brainstorm

**Summary:** Ten questions to shape the roadmap; answers recorded.

**Outcome:** YACReader user; folder-tree browsing (no database); metadata fix from filename in bulk; health checks (duplicates,
missing issues, corrupt archives, quality report); CBR to CBZ and archive clean-up; wishlist of missing issues; stats dashboard;
folder icons; downloads watcher and a one-click pipeline; double-click `.exe`. Not wanted: built-in reader, online metadata,
recompression, PDF/EPUB to CBZ, read-status or ratings.

**Changes:** none to code. Proposed build order was 1-4 first (done in session 7), then health checks, pipeline/watcher, dashboard, tree
browser, `.exe`.

---

## 2026-10-06 ~19:50-20:02 +11:00 · Session 5: dark mode and Home grouping

**Summary:** Whole-app dark mode; Home page gained a group header; sidebar grouped to match.

**Changes by file**
- `ui_kit.py`: palette constants became `(light, dark)` tuples (`BG`, `PANEL`, `BORDER`, `HOVER`, `TEXT`, `MUTED`, `ACCENT`,
  `ACCENT_HOVER`, `DANGER`, plus new `SEG_ON`, `SWITCH_OFF`, `SELECT_BG`). Added `pick()` (resolves a pair for non-CustomTkinter
  widgets) and `switch_style()` (shared switch look).
- `page_rename.py`: ttk `Treeview` styling moved into an `apply_theme()` method (ttk and tk widgets ignore CustomTkinter's mode);
  tag colours and the inline editor entry use `pick()`.
- `page_bulk.py`: switch styling via `switch_style()`.
- `comic_tool.py`: theme loaded from settings before widgets are built (`"system"` on first launch); sidebar **Dark mode** switch
  calls `ctk.set_appearance_mode()` then each page's `apply_theme()`; `theme` saved in `settings.json`; Home split into
  "Comic Cover Extractor" (Single issue, Bulk folder) and "Comic Renamer" (Renamer); sidebar uses the same headings.

**Technical notes:** CustomTkinter accepts `(light, dark)` tuples for colour arguments and switches live, so most widgets needed no
change. Only ttk (`Treeview`, headings, selection colours, row tags) and the plain `tk.Entry` cell editor needed manual theming.

**Verification:** screenshots of Home, Renamer and Bulk folder in dark mode, live toggle checked (including the ttk table); regression
run of Single issue, Bulk folder and Renamer passed. The Single issue page was not viewed in dark.

---

## 2026-10-06 ~19:21-19:45 +11:00 · Session 4: Renamer, module split, Home page

**Summary:** Added a comic renamer as a separate tool, split the code into modules, and added a Home page of tool cards.

**Decisions (from the user):** naming pattern chosen inside the tool (many presets plus a custom template); metadata from filename plus
`ComicInfo.xml`; preview table with editing before apply; optional move into series folders; scope CBZ/CBR/PDF/EPUB with optional
subfolders. Undo was not selected and not built.

**New files**
- `rename_core.py`: `parse_filename`, `read_comicinfo` (zip directly; RAR via `_rar_member` using 7z/unrar/tar), `merge`, `title_case`,
  `format_issue`, `render`, `safe_name`, `build_stem`, `series_folder`, `find_files`, `do_rename`, `PRESETS`, `PADS`, `CASES`.
- `page_rename.py`: `RenamePage`, `Item` dataclass, scan thread, Treeview with inline editing, conflict resolution, apply.
- `ui_kit.py`, `page_single.py`, `page_bulk.py`: produced by slicing the old monolithic `comic_tool.py` at its section markers.
- `comic_tool.py`: rewritten as app shell with `HomePage` and `Card` (three ungrouped cards; window title and Home header "Comic Toolkit").

**Technical notes**
- *Parsing order:* year from `(YYYY)` / `[YYYY]` (also `YYYY-MM`) found first; bracketed tags stripped; volume (`v2`, `Vol. 2`) extracted;
  optional ` - Title` split when the text before the dash ends in a digit; trailing number becomes the issue; `Vol N` with no issue
  becomes the issue (manga style). Series falls back to the parent folder name when the filename has none (not the scanned root).
- *Templates:* `[ ... ]` groups render only if every token inside has a value; leftover separators trimmed; `:` becomes ` - `, then
  Windows-illegal characters are sanitised.
- *Statuses:* Ready / Unchanged / Exists (destination already on disk) / Duplicate (two checked rows map to one path) / No series. Only
  Ready rows are applied. Case-only renames use a two-step temp rename (case-insensitive filesystem). Manually edited names survive
  option changes until the next rescan. Series folder casing is merged (first spelling seen wins).
- *ComicInfo precedence:* when "Use ComicInfo.xml" is on, non-empty ComicInfo fields override filename fields.
- *Home cards:* hover handling checks whether the pointer is still inside the card before resetting, to avoid flicker when moving over
  child widgets.

**Bugs found and fixed**
- Missing imports after the module split (`ORG_FLAT`, `MUTED`, `BG`) found by running `ruff --select F`.
- Introducing series-folder canonicalisation shadowed the local `name` variable with the folder name, producing extension-less
  destination names (caught by the test, in a temp folder, before any real use); renamed to `sname`.
- Single issue preview clipped the last caption at 780 px window height; thumbnails reduced to 120x165.

**Verification:** scripted run on a generated folder: default style, `#01` style with Title Case, duplicate detection then manual fix,
apply, move into series folders, idempotent re-run; ComicInfo override verified on a zip; parser exercised on 14 filename shapes;
Single issue / Bulk folder regression; screenshots of Home, Renamer, Single issue.

---

## 2026-10-06 ~19:06-19:20 +11:00 · Session 3: split into two tools with customisation

**Summary:** Single-issue and bulk extraction became two separate pages in one window with an options inspector, and extraction gained
many options.

**New files:** `comic_core.py` (no UI): `Comic`, `render_cover`, `plan_dest`, `export_cover`, `series_name`, `sanitize`, `unique`,
`find_comics`, option label constants. `comic_tool.py` rewritten with `Page`, `Form`, `DropZone`, `SinglePage`, `BulkPage`, `App`.

**Features:** image format (Original/JPG/PNG/WebP), quality slider (JPG/WebP), max height, save location (subfolder of source / chosen
folder / beside each comic), organise (flat / mirror folders / group by series), file name (`Name` or `Name - cover`), if-exists
(Keep both / Overwrite / Skip), include subfolders, live example path, per-file log, Stop button, settings saved to `settings.json`,
drag and drop routing (file to Single issue, folder to Bulk folder).

**Technical notes**
- `series_name` strips bracketed groups, then one trailing issue number (optionally with `#`, `issue`, `vol`, `v`, `no`, `ch`), then one
  trailing volume marker; falls back to the full stem. Checked on seven filename shapes.
- Colliding output names in one run are never overwritten (`unique()` also checks names already claimed this run).
- Worker threads report through a `queue.Queue`; Tk is only touched on the main thread.

**Bugs found and fixed**
- A `_options` method on the single-issue page collided with Tkinter's internal `_options`, raising `TypeError` at widget creation;
  renamed `_opts`.
- The test script crashed printing the `✗` log marker on the Windows console (cp1252); fixed in the test by forcing UTF-8 output. The app
  itself was unaffected.

**Verification:** scripted batch over a generated library covering flat/series/mirror layouts, non-recursive scan, custom destination,
Skip on re-run, "beside each comic", a corrupt file reported as failed while the rest completed; settings file written on close.

---

## 2026-10-06 (before 19:06, time not recorded) · Session 2: first/last page preview and bulk folder covers

**Summary:** Preview changed to the first 3 and last 3 pages; added extraction of covers for a whole folder into a `Covers` subfolder.

**Changes (in the then single-file `comic_tool.py`):** preview shows 3 + 3 pages with a `⋯` gap (all pages when 6 or fewer); "Extract folder
covers…" button and folder drop; covers named after each comic with the cover's own extension; progress bar and status line.

**Bug found and fixed:** the first version updated the UI from a worker thread via `after()`, which raised `RuntimeError: main thread is
not in main loop` in tests. Replaced with a `queue.Queue` polled from the main thread.

**Verification:** generated folder with a duplicate stem and a corrupt file: 3 covers saved, corrupt file reported; thumbnails verified for
12-page and 4-page comics.

---

## 2026-10-06 (before 19:06, time not recorded) · Session 1: initial single-issue tool

**Summary:** Chose the stack and built the first script: drop in a CBZ/CBR, convert to ZIP, preview pages, extract the cover.

**Decisions:** Python with CustomTkinter (modern look), `tkinterdnd2` (drag and drop), Pillow (images). CBZ is already a zip; CBR is RAR and
must be extracted and repacked, so renaming alone is not enough.

**Technical notes**
- `Comic` class gives a uniform view over zip and RAR: sorted page names plus a byte reader; zip detection uses `zipfile.is_zipfile` so a
  `.cbr` that is really a zip needs no extractor.
- RAR extraction shells out to 7-Zip, unrar or Windows `tar.exe` (bsdtar reads RAR). `rarfile` was installed early but is not used by the
  final code.
- Natural sort for page order; non-image and `__MACOSX` entries ignored; output names never overwrite (`unique()` appends ` (1)`).
- Notion-inspired palette and Segoe UI typography.

**Verification:** a generated CBZ was converted, previewed and its cover saved; page ordering confirmed (`p1, p2, p3, p10`). CBR was not
tested (no RAR available in that session).

---

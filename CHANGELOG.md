# Changelog

Technical record of every working session on Comic Toolkit, newest first. Each session is one timestamped block.

**Conventions**
- Times are local (UTC+11:00), date format `YYYY-MM-DD HH:MM`.
- Blocks dated before 2026-10-06 20:43 were written retroactively. Their times are reconstructed from file creation and
  modification timestamps and are approximate (marked `~`); where nothing could be reconstructed it says so.
- Each block lists: summary, decisions, changes by file, technical notes, bugs found and fixed, verification, and known
  issues. "Verification" only claims what was actually run.
- Maintenance rule: add a new block at the top at the end of every session, and update `README.md` to match.

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

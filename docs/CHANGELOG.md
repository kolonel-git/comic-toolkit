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

## 2026-10-15 17:30 +11:00 · Session 54: shared page shell and Bulk folder on it (roadmap Phase 0 and Phase 1, step 1)

**Summary:** Built the shell every page will use (header, collapsible segments, footer) and moved Bulk folder onto it, following the [UI revamp plan](ui-revamp-plan.md). The downloads watcher was folded into the Add to library plan (a *Watch this folder* switch) in the roadmap and plan.

**What changed for the user**
- Bulk folder is now three segments: **Comics**, **Covers**, **Review**. No step numbers. A finished segment folds to a one-line summary and the next opens by itself (a switch at the top right turns that off; it is shared by every page).
- Covers: the four "where" cards, three "if a cover exists" cards (Skip, Replace, Keep both) and a shut **Advanced options** block that says how many of its settings you changed.
- Review: a plain-words headline, destination, estimated size and a low-disk-space warning, unreadable comics and name clashes named before the run, a filterable table with a status per comic, **Details** for existing covers, a **Show covers** switch (small cover pictures), **Dry run**, and **Retry failed** after a run with failures.
- Long comic lists load as you scroll. The footer holds the one main action plus a few secondary buttons. Settings are remembered per folder.

**Changes by file**
- `flow_kit.py`: rewritten around `SegmentPage`, `Segment`, `Advanced`, `LazyTable` (replaces `StepPage`, `StepCard`, `Disclosure`, `mini_table`); `ChoiceCards`, `facts`, `section` kept.
- `page_bulk.py`: rebuilt on the shell; a background check finds unreadable comics and samples cover sizes before the run.
- `ui_kit.py`: type tokens (`TYPE_SEGMENT`, `TYPE_BODY`, `TYPE_HINT`, `TYPE_MONO`); `build_tree` takes a `style` and a `picture` column; `apply_tree_theme` follows the table's own style.
- `tests/test_bulk_page.py` rewritten for the new page; `tests/test_layout.py` follows the new summary text.
- `docs/tools.md`, `docs/architecture.md`, `docs/roadmap.md`, `docs/ui-revamp-plan.md`: updated.

**Technical notes:** an empty `CTkFrame` is 200 px tall unless given `height=0` (it left a gap in Review). `Comic` objects are not opened for the pre-run check: zip files are inspected directly, and real RAR files are only checked for an installed extractor, so an unreadable RAR shows up at run time.

**Verification:** `ruff check --select F,E9 .` passes. `python tests/run_all.py`: 27 of 27 passed on the first full run. A later full run had `test_aceo_ui.py` fail on a key event (focus dependent, another window was in front); it passed on three separate reruns and that page is untouched. Screen captures of the page were looked at in light and dark mode for the Comics, Covers and Review segments; the dark Review capture came out black (a known capture problem) and the light one picked up another application, so the Review layout is covered by the test instead.

**Known issues:** other tools still use the old layout; the shared "open the next section" switch is saved with each page's settings, so it can differ until every page uses the shell; `Library folder` and `Recent` sit under the drop box's buttons rather than beside a folder field; `docs/manual-tests.md` has no checks yet for the new Bulk folder layout (real RAR files, a very large library, thumbnails on a slow disk).

---

## 2026-10-15 15:55 +11:00 · Session 53: UI revamp plan written, roadmap and versioning rebuilt around it

**Summary:** Went through every tool with the owner and wrote down the agreed redesign, then rebuilt the roadmap, versioning and handoff around it. No app code changed.

**Decisions:** every page becomes Header, collapsible Segments (finished ones fold to a one-line summary, the next opens by itself) and Footer; Advanced options sit in a collapsed block inside their segment; no step numbers; one type scale (Arial Black for the page title only); folder-opening tools get `Library` and `Recent` beside the folder control; reading-order folders are marked by the user (with suggestions) and kept out of stats and duplicate checks; Metadata becomes a manual repair editor with local-library suggestions; Single issue loses *Convert to ZIP*; Bulk folder and Folder icons gain dry-run reviews; Renamer gets type prompts, suggestions and saved rules; undo is future work.

**Changes by file**
- `docs/ui-revamp-plan.md` (new): one section per tool, future work, and a table of links between tools. Trimmed after review: per-section status lines, duplicated future-work lists and a broken table were removed.
- `docs/roadmap.md`: rewritten. The UI revamp is the build order (Phases 0 to 5, one branch per feature); finished items 0 to 5 are one summary paragraph; the folder browser, downloads watcher and other unscheduled ideas moved to *Future implementations*.
- `docs/versioning.md`: added the tags that exist (`v0.5.1`, `v0.6.0`, `v0.7.0`); replaced the planned tags tied to the old roadmap items with one release per phase (`v0.8.0` to `v0.12.0`, then `v1.0.0`).
- `HANDOFF.md`: tags, session count, test count, open work and start-of-session steps updated; working agreements now say one feature per branch, PR title and summary after the work, and no mention of any assistant or agent in commits, PR text, code or docs.
- `README.md`: status line now `v0.7.0`, link to the plan.
- `docs/README.md`: index rows for the plan, roadmap and versioning.

**Decisions taken while rebuilding the roadmap (owner may change):** tools are converted one at a time; the downloads watcher is folded into Add to library as a *Watch this folder* switch; one tag per phase; Renamer sits in Phase 4.

**Verification:** documentation only; no tests were run.

---

## 2026-10-15 22:00 +11:00 · Session 52: Bulk folder steps 2 and 3 made clearer

**Summary:** Feedback on Session 51: the workflow in the second and third cards was still confusing; the bottom bar was liked and kept.

**What was confusing, and the change**
- Step 3 repeated every setting from step 2, so it looked like a second form with nothing to do in it. It now lists only what is about to happen: how many covers and in what format, where they go, a warning line if covers already exist ("6 of 6 covers already exist and will be replaced"), and the reassurance that comics are never changed. During a run it shows progress and live counts; the file list and the result appear only once there is something to show.
- Every step has a one-line hint under its header saying what to do in it (`StepCard.set_hint`), and step 3 says that nothing happens until the yellow button in the bar is pressed. Step labels are shorter: *Start here*, *You are here*, *Next*, *Working*, *Finished*.
- The pinned bar says which step you are on ("Step 2 of 3 · Check the preview, then extract.", "Step 3 of 3 · 3 of 6, about 10s left · 3 saved"), then the result with *Open the covers folder* as the one next step and *Extract again* beside it.
- Step 2 is titled *Set up the covers* and its groups are questions: where do the covers go, what do they look like, what are they called. The preview table has a Status column (New, Replaces, Skipped, Numbered) so a conflict is visible on the very row it affects.

**Verification:** `ruff check --select F,E9 .` passes; `python tests/run_all.py`: 27 of 27 pass. Captured in dark mode before and after a run; the final column-width tweak to the preview was not looked at again.

**Known issues:** the page is long at the default window height (the pinned bar hides the bottom of it until you scroll); other tools still use the old layout.

---

## 2026-10-15 20:30 +11:00 · Session 51: Bulk folder shows everything, scrolling and hovering fixed

**Summary:** Feedback on Session 50: the guided page was too simplified, the page would not scroll, and hovering on buttons and cards did not behave. All three fixed.

**Balance of guidance and information (`flow_kit.py`, `page_bulk.py`)**
- Steps no longer collapse on their own; all three stay open and show their details (click a header to fold one). The guidance stays: numbered badges, a pink *where you are* label, locked steps, the page scrolls to the next step when something is chosen, and the main button is pinned in a bar at the bottom (`StepPage.set_bar`): *Extract N covers*, then *Stop*, then *Open the covers folder*.
- Step 1 now has a facts panel (comics, series, size on disk, file types, where from) and a table of every comic found. Step 2 puts every setting (cards, format, quality, size, file name, if a cover exists, plus *Advanced*) beside a live preview of the covers you will get, with how many already exist and what happens to them. Step 3 lists every setting that will apply, then progress, the result and every file. Content is up to 1100 px wide. New helpers `section`, `facts`, `mini_table`.

**Scrolling:** binding `<Configure>` on a `CTkScrollableFrame` replaces the binding that keeps its scroll region up to date, so the page never got a scroll region and the wheel did nothing. The page now binds its own frame instead (note in `flow_kit.py`).

**Hovering (`ui_kit.py`):** Enter and Leave events are unreliable on customtkinter widgets, so a single timer (`ensure_hover`, every 40 ms) asks Tk which widget is under the pointer and calls the `_hover_hooks` of the nearest control (shadowed buttons and cards, sidebar entries, drop boxes, choice cards, step headers, *More options* links). The slide toward the shadow also used unscaled padding, so at 125 % scaling a button's shadow changed size after the first hover; it now uses the same scaling as the first layout. While writing the timer, `_hover` clashed with customtkinter's own `CTkButton._hover` flag; the hook is named `_hover_hooks`, and a broken hook can no longer stop the timer.

**Tests:** `tests/test_bulk_page.py` rewritten (steps, found facts, preview, bar, scrolling region and wheel, hover hooks).

**Verification:** `ruff check --select F,E9 .` passes; `python tests/run_all.py`: 27 of 27 pass. Hover was also checked once with the real pointer (warped over a Home card and a sidebar entry and away): both warmed and cooled. The redesigned page was captured in dark mode and looked right; light mode and a real library were not tried.

**Known issues:** at the default window height the pinned bar covers the bottom of the page, so the last step is reached by scrolling; the preview table truncates long names in the middle of a path rather than with an ellipsis; other tools still use the old layout.

---

## 2026-10-15 18:00 +11:00 · Session 50: Guided steps, starting with Bulk folder

**Summary:** The first tool reworked in the new guided layout: a short column of three numbered step cards instead of a main area beside a long options panel. Planned for low cognitive load (the owner has ADHD and expects many users do): one obvious next step, few visible choices, plain-language results.

**Decisions (owner's answers):** guided steps for every tool, Bulk folder first; pain points to design for: too many options at once, not sure what to do next, losing my place, unclear whether it worked. Remaining tools follow one at a time.

**Changes**
- New `flow_kit.py`: `StepPage`, `StepCard` (badge with number or tick, title, a label saying where you are, a one-line summary and Change button once done, greyed while it waits for an earlier step), `ChoiceCards` (cards with arrow-key and Tab support), `Disclosure`, `path_row`, `labelled`.
- `page_bulk.py` rewritten on it: step 1 comics (drop box, Library folder and Recent, *Include comics in subfolders* next to where it matters); step 2 four recipe cards for where covers go with a live example path each, the image format up front, *More options* for the rest (all old settings are still there, the two advanced menus keep the cards in sync); step 3 one big button that reads *Extract N covers* (or *Choose comics first*, greyed), progress with time left, then a result card instead of the button. The run logic (`_worker`, options, file naming) is unchanged.
- `ui_kit.title_block(strip=False)` skips the decorative shape strip on guided pages.
- Tests: new `tests/test_bulk_page.py`; `test_layout.py` no longer treats Bulk folder as an options-panel page.

**Verification:** `ruff check --select F,E9 .` passes; `python tests/run_all.py`: 27 of 27 pass. The page was captured in dark mode (empty, comics chosen, finished) and the layout looked as intended; the light-mode capture was taken but not looked at, and the page was not tried with a real library.

**Known issues:** at the minimum window height the Extract button sits at the very bottom edge, so a short window scrolls; the page persists no state for the card choice itself (it follows the where and layout settings, which are saved); the other tools still use the old layout, so the app is temporarily in two styles.

---

## 2026-10-15 14:30 +11:00 · Session 49: Ctrl+K as a floating search bar

**Summary:** The Ctrl+K window is now a Spotlight-style search bar: a large field at the top middle of the app with results listed under it, each a bold title over a smaller description.

**Changes**
- `ui_kit.spotlight`: borderless window (thick border, hard shadow), centred across the app and about a fifth of the way down; a 20 pt search field with a magnifier; seven result rows, each with a white icon tile, a bold title, a description line and a small *Page* or *Action* tag on the right; the chosen row is pink. Names that start with what you typed come first, then names that contain it, then descriptions. An empty search lists everything; no match gets a one-line explanation; Up and Down scroll past seven results; hovering selects; Enter or a click opens; Esc, Ctrl+K again or clicking elsewhere closes it. The old list-in-a-window version is gone.
- `comic_tool.App.open_palette` builds the entries (pages with their descriptions from the Home cards, plus *Switch light and dark mode* and *Choose the library folder*) and calls it.
- `tests/test_shortcuts.py`: filter order, description matches, the empty and no-match states, centring and Ctrl+K toggling.

**Verification:** `ruff check --select F,E9 .` passes; `python tests/run_all.py`: 26 of 26 pass. The window was captured in light and dark mode and looked as intended; the dark icons first sat on a dark row and were hard to see, so the tiles are now always white.

**Known issues:** the window uses a transparent colour for the shadow corner, which only Windows honours; results are not grouped under headings (the tag on each row says Page or Action).

---

## 2026-10-15 13:10 +11:00 · Session 48: Styled pop-ups, focus on every control, library folder naming, Ctrl+K hint

**Summary:** Four follow-ups from the Session 47 review.

**Changes**
- `ui_kit.popup_menu`: the Recent list is now a square pop-up with a thick border and a hard shadow (Up, Down, Enter, Esc, click, closes when focus leaves) instead of the native Windows menu; long folder paths are shortened from the left. The Ctrl+K list is wrapped in a `Shadow` too.
- Focus ring on drop-down lists (`menu`: Tab, Enter or Space opens), format pickers (`segmented`: Enter or Space and Left or Right change the choice) and text fields (`entry`): `Shadow.make_focusable(ring=...)` can turn the widget's border, the black frame round it, or its fill blue.
- The *My library* button is now *Library folder*. The folder can be chosen from Home (*Library folder…* beside the scan buttons, `App.choose_library`, which also rescans), from Ctrl+K (*Choose the library folder*), and on Library stats (the strip is labelled *Library folder*).
- Home tip now starts with *press Ctrl+K to jump to any page*.
- Tests: `test_shortcuts.py` covers the pop-up, the new focus rings, the segmented keys and `choose_library`; `test_stats_home.py` expects the third strip button.

**Verification:** `ruff check --select F,E9 .` passes; `python tests/run_all.py`: 26 of 26 pass. The Recent pop-up was captured in dark mode and looked right after its width was fixed (it first cut long paths off); the Ctrl+K window and the focus rings were checked by tests only, not by eye.

**Known issues:** pop-up Up, Down and Enter need real window focus and were not exercised by hand; the pop-up uses a transparent colour for its shadow corner, which only Windows honours.

---

## 2026-10-15 11:30 +11:00 · Session 47: Shared folders, keyboard, run feedback

**Summary:** First batch of the UX review: one library folder and a recent-folder list shared by every tool, a keyboard layer with visible focus, time-left estimates, a taskbar flash and tooltips. Also two test and layout problems found on the way.

**Changes**
- `comic_tool.py`: `App.library_root` (the folder Library stats scans), `note_folder` / `recent_dirs` (last eight folders, saved as `recent` in `settings.json`), `_wire_folders` wraps every page's `set_folder` to remember folders and gives eight tools a *My library* and *Recent* line under *Add folder* (`DropZone.add_shortcuts`). Ctrl+K command palette (`open_palette`), Ctrl+1/2, Ctrl+O, Ctrl+Enter (`Page.primary_action`), Esc (`Page.stop_action`). Sidebar hint *Ctrl+K jump to a tool*.
- `ui_kit.py`: `Shadow.make_focusable` (Tab reaches buttons and cards, blue `FOCUS` ring, Enter or Space presses), focus ring and keys on `Toggle` (Space or Enter), `Slider` (arrow keys), `NavItem`; `tooltip()`, `eta_text()`, `flash_taskbar()`. CTkFrame binds its inner canvas, so focus and key bindings on a frame use `tk.Frame.bind`.
- `batch_page.py`: status shows *37 of 120, about 40s left*; the taskbar flashes when a run longer than 5 s ends. Tooltips on the up and down arrows (Reading order, ACEO) and on the Home rescan icon.
- Home is shorter (banner 72, stats card 86, tool cards 108 px, tighter rows): at the app's own minimum size (1040 x 720) the last row of cards was cut off with the default section order.
- `tests/test_layout_app.py` read the owner's real `settings.json`, so it compared against the saved section order and always failed on the default-order check; it now uses a temporary settings file and passes. New `tests/test_shortcuts.py`.

**Verification:** `ruff check --select F,E9 .` passes; `python tests/run_all.py`: 26 of 26 pass. Keys are tested by calling the same handlers (key events need real window focus); the Ctrl shortcuts and the visual look of the new drop-box line were not checked by hand.

**Known issues:** the blue focus ring is only drawn on buttons, cards, switches, sliders and sidebar entries (menus, segmented controls and entries use their own look). The taskbar flash and the Recent menu need a manual check.

---

## 2026-10-14 22:30 +11:00 · Session 46: Home rows fill their width

**Summary:** Home tool cards stretch to fill each row instead of leaving blank columns.

**Changes (`comic_tool.py`)**: `HomePage.set_groups` no longer pads short rows with empty card columns or extra gaps; each row uses its own equal-width card columns (`uniform` per row), so a row of one group has wider cards than a row of four cards. Gaps between groups are only drawn where two groups meet. `tests/test_layout_app.py`: cards must match in width within a row and every row must reach the same right edge.

**Verification:** `ruff check --select F,E9 .` passes; `tests/test_stats_home.py` passes; `tests/test_layout_app.py` now passes its Home layout checks and still stops at the default-group-order assertion that failed before this work. The full suite and a screenshot were not re-run.

---

## 2026-10-14 22:00 +11:00 · Session 45: Pink replaces green, plainer sidebar, a clearer page-by-page flow

**Summary:** Pink takes green's place as the colour that follows yellow; the sidebar title is redrawn and only Home and Library stats keep icons; every tool page now leads with the settings and the empty state that help most.

**Colour**
- Green is gone. Yellow is the main colour (main buttons, headings, the first way in). Pink marks state and secondary emphasis: the open tool in the sidebar, ON switches, slider fill, the selected filter chip, *Fix checked*. Home cards rotate yellow, pink, cyan. Hover tint is light pink.

**Sidebar (`ui_kit.py`, `comic_tool.py`)**
- New `Logo` canvas: yellow block with a hard shadow, an abstract mark (square, circle, triangle) and a two-line *COMIC TOOLKIT* wordmark; clicking it opens Home. Tool entries lost their icons (`NavItem` draws an icon only for the large Home and Library stats entries).

**Usability changes, shared by all pages (`ui_kit.py`, `batch_page.py`)**
- Main actions are bigger targets (44 px) and a main button that cannot be used yet greys out (`Shadow.dim`, `DISABLED_FILL`) instead of staying bright yellow.
- The first button in every drop box (Add folder, or Choose comic on Single issue) is yellow, the other is plain.
- Options panels can fold: `Form.heading(text, collapsible=True, open=False)`. Rarely needed groups start folded: Audit *Warnings*, Metadata *Checked rows*, Reading order *Filenames and sorting*, ACEO *Cards*, Library stats *Display* and *Output*. Folding respects rows that a page hides on purpose (`Form.show`).
- Empty states say what to do: `build_tree(..., ).set_empty(text)` shows a message over an empty table (ACEO, Audit, Add to library, Metadata, Reading order, Renamer list and cards); tool pages with a log show *Getting started 1 2 3* in the empty log; Single issue explains its empty preview.
- Library audit: *Scan library* is the only yellow button, *Fix checked* is pink; filter chips are wide enough for their labels and the selected chip is pink.

**Verification:** `ruff check --select F,E9 .` passes; `python tests/run_all.py`: 24 of 25 pass (`test_layout_app.py` fails at the default-group-order assertion, as before this work; its active-tool check now expects `PINK`). Screenshots of Home (light), Library audit (light), Single issue (light) and Reading order (dark) were looked at. Two later captures picked up a Windows task-switcher overlay, so the ACEO and Library stats pages were not checked visually, and the folded sections of ACEO, Metadata and Stats were only checked through the tests.

**Known issues:** the audit options panel is tall enough that its *Warnings* group is reached by scrolling; no page was reordered beyond folding.

---

## 2026-10-14 20:30 +11:00 · Session 44: Light palette, neon green, sidebar icons and hierarchy

**Summary:** The light mode got its own palette instead of cream and white, neon green joined the colours, the Home stats card grew, and the sidebar now has icons and a clear two-level hierarchy.

**Changes (`ui_kit.py`, `comic_tool.py`)**
- Light palette: lilac canvas (`BG` #D9D2FA), pale lilac panels (`PANEL` #EFEBFF), white only where you write or read (`WELL`: inputs, tables, logs; `RAISED`: secondary buttons). New `GREEN` (#A6FF5C) is the fourth Home card colour (yellow, pink, cyan, green), the ON colour of switches, the fill of sliders, the active colour of tool entries in the sidebar and the hover tint. Dark mode is unchanged apart from the new `WELL`/`RAISED` pair.
- Home stats card: 96 px tall (was about 60), a stats icon tile, 18 px bold text, 44 px buttons, white with a thick border and a larger shadow.
- Sidebar: `draw_icon()` (scalable line icons for every page, plus new home and stats icons) and `NavItem` (icon, label, hover colour, active colour, shadow). Home and Library stats are large white blocks that always carry a shadow and turn yellow when open; below a rule and a *Tools* label, the tool entries are smaller, flat and indented under their group heading, and turn green with a border and shadow when open. `IconTile` (Home cards) now uses `draw_icon`.
- Test: the active-tool colour assertion in `test_layout_app.py` expects `GREEN`.

**Verification:** `ruff check --select F,E9 .` passes; `python tests/run_all.py`: 24 of 25 pass (`test_layout_app.py` fails at the default-group-order assertion, as before this work). Screenshots of Home (light), the Renamer (light) and Library stats (light) were looked at; Home in dark mode and the remaining pages were not re-viewed after this change.

**Known issues:** the stats tiles on the Library stats page cut some labels ("Average siz"); this predates this session and was not touched.

---

## 2026-10-14 19:20 +11:00 · Session 43: Neo-brutalist refinements (switches, sliders, card icons, dark-mode shadows)

**Summary:** Four fixes to the Session 42 look, after the owner found the sliders odd, the Home card icons small and off-centre, and white shadows poor in dark mode.

**Changes (`ui_kit.py`, `comic_tool.py`, pages)**
- Dark mode: shadows and borders stay black in both modes; the dark canvas is lifted to a dusky slate (`BG` #25252E, `PANEL` #353542) so black edges and hard shadows read. `INK` and `TEXT` are now separate colours (black ink, light text in dark mode); new `SCROLL` colour for scrollbar thumbs; hover, muted and selected-row colours retuned for the slate.
- Switches: new `Toggle` widget (canvas) replaces every `ctk.CTkSwitch`: a black-edged block with a hard shadow, yellow `ON` with the knob at the right, grey `OFF` with the knob at the left. Same arguments (`text`, `variable`, `command`); styling arguments are ignored. Clicking the track, the text or Space toggles it.
- Sliders: new `Slider` widget (canvas) replaces `ctk.CTkSlider` (`slider()` kept as the factory): black-edged track, yellow fill, pink square handle with its own shadow. Used by the cover Quality row and the page picker size slider.
- Home cards: new `IconTile` draws a 48 px white tile with a line icon per tool (plus, grid, folder, Aa, braces, arrows, check, 1·2, card grid, page) centred exactly, filled with the card's colour; `Card` takes the tool key instead of a glyph. Cards are 118 px tall.
- `Toggle` and `Slider` redraw with `refresh_strips()` when the mode changes.

**Verification:** `ruff check --select F,E9 .` passes; `python tests/run_all.py`: 24 of 25 pass (`test_layout_app.py` fails at the default-group-order assertion, as before this work). Screenshots of the app window and of the new switch, slider and segmented control in light and dark mode were looked at and matched the intent; the light-mode Home, the Renamer and the other tool pages were not re-viewed after these changes.

**Known issues:** the slider track is thin next to the other controls; keyboard control of the slider is not implemented (the switch responds to Space only when focused).

---

## 2026-10-14 18:10 +11:00 · Session 42: Neo-brutalist UI replaces the clay skin

**Summary:** The Session 41 clay look was rejected and replaced by a neo-brutalist one: square corners, thick black borders, saturated yellow / pink / cyan on a cream canvas, hard offset shadows and abstract shape bands. Light and dark modes both kept (dark: black canvas, white ink and shadows). Behaviour is unchanged.

**Decisions (from the owner's answers):** offset-block shadows on all raised items; yellow + hot pink + cyan on cream; dark mode kept with ink and paper swapped; Arial Black headings with Segoe UI body; fully square corners; abstract shapes on a Home banner and on every tool page title strip; full-height sidebar rail with a thick right border and a yellow active block with shadow; Home tiles coloured per group, rotating yellow / pink / cyan; hover slides an item toward its shadow and press sinks it into it; white fill, thick border and hard shadow for tables, logs, inputs and other containers.

**Changes**
- `ui_kit.py` (rewritten): palette (`BG`, `PANEL`, `INK`, `YELLOW`, `PINK`, `CYAN`, `ACCENT`, `ACCENT_TEXT`, `ON_ACCENT`, ...), `HEAD` = Arial Black, `EDGE` = 3 px border, radii all 0. New `Shadow` wrapper: a frame holding a black offset block and the real widget; it forwards `configure`, `cget`, `bind`, `focus` and every other attribute to the wrapped widget, so `button`, `tool_button`, `menu`, `segmented`, `entry`, `textbox`, `DropZone` and `build_tree` (which now returns the wrapper) are used as before. With `motion=True` the face slides toward its shadow on hover and sinks into it while pressed; `show_shadow(False)` hides the block. New `AbstractStrip` (seeded canvas of circles, triangles, crosses, zigzags and stripes) used by `title_block` and the Home banner, redrawn by `refresh_strips()` when the mode changes. `Splitter` is a 3 px black line that also serves as the border of the sidebar and the options panel. Tables get a yellow header and a cyan selected row.
- `comic_tool.py`: full-height sidebar rail, yellow `COMIC TOOLKIT` block, nav items are shadow wrappers with the shadow shown only on the open tool, Home banner, summary strip, `Card` is now a `Shadow` with a per-group colour (`Card(parent, glyph, color, title, text, command)`), dark-mode switch uses `switch_style()`.
- `batch_page.py`, `page_bulk.py`, `page_order.py`, `page_rename.py`: logs and text areas use `textbox()`; `page_rename.py` uses `ACCENT_TEXT` for its accent label. All pages: square corners, 3 px borders, thick square progress bars.
- Tests: `test_layout_app.py` active-nav colour is `ACCENT`; `test_layout.py` divider width 3 and a wider Up-to-Top gap allowance (80); `test_aceo_ui.py` preview height threshold 350 (the title strip uses about 50 px).

**Verification:** `ruff check --select F,E9 .` passes. `python tests/run_all.py`: 24 of 25 pass; `test_layout_app.py` still fails at the default-group-order assertion (line 89), which also failed before any of the UI work (checked in Session 41 by stashing). Screenshots of the app window were taken in light and dark mode for Home and in light mode for the Renamer and looked as intended; the Bulk folder page and other tool pages were not viewed.

**Known issues:** three-line card descriptions were cut off at the old card height, so cards are 110 px tall; the switch knob is a plain black block (customtkinter has no knob radius option); `Shadow` adds a frame or two per control, so very large pages build slightly slower.

---

## 2026-10-14 16:30 +11:00 · Session 41: Clay UI revamp

**Summary:** The Notion-style look is replaced by a subtle claymorphism skin: earthy sand/terracotta palette, medium rounded corners, raised surfaces, recessed wells, a floating sidebar and inspector. Behaviour and layouts are unchanged apart from a little extra spacing.

**Decisions (from the owner's answers):** subtle clay (large radii, thicker soft edges, tonal fills, no rendered shadow images); muted earthy palette; light and dark both clay; Segoe UI body with a chunky heading face; medium radius; floating sidebar; uniform Home tiles with one accent; press-in on click and lift on hover; inset wells for dense areas; high-contrast text; strong accent on primary actions.

**Changes**
- `ui_kit.py`: new palette (`BG` canvas, `PANEL`, `RAISED` for buttons and cards, `WELL` for inputs, tables and logs, terracotta `ACCENT`), `HEAD` ("Segoe UI Black") for titles, radii `R_CARD` 16 and `R_CTRL` 12, `press_feedback` (buttons sink into a darker fill while held). Buttons, menus, segmented controls, entries, slider, drop zone and tables restyled; the options inspector is a floating rounded panel.
- `comic_tool.py`: floating sidebar, active tool is a raised pill with an accent edge, one soft tint for every Home tile, raised cards that lift on hover, home summary strip as a well, `strip_button` now wraps `ui_kit.button`.
- `batch_page.py`, `page_bulk.py`, `page_order.py`, `page_rename.py`, `page_aceo.py`, `page_stats.py`: larger radii, wells for logs and previews, raised stats tiles, thicker progress bars.
- `tests/test_layout_app.py`: active-nav colour assertion follows the new `RAISED` fill.

**Verification:** `ruff check --select F,E9 .` passes. `python tests/run_all.py`: 24 of 25 pass. `test_layout_app.py` fails at the default-group-order assertion; it fails identically on the code from before this session (checked by stashing), so it is not caused by the restyle. No visual check was done by me: a screenshot attempt captured the wrong window and was discarded, so please look through the app in light and dark mode.

**Known issues:** the Windows font "Segoe UI Black" is assumed present. Rendered shadows (full clay) were not built; say if you want them.

---

## 2026-10-14 09:40 +11:00 · Session 40: Sidebar scrolls and folds, sections can be reordered

**Summary:** The sidebar tool list scrolls, each section heading folds and unfolds, and the section order (shared by the sidebar and Home) can be changed.

**Changes (`comic_tool.py`)**
- Sidebar: *Comic Toolkit*, *Home* and *Library stats* are pinned at the top; the groups sit in a `CTkScrollableFrame`; *Reorder sections…* and the dark-mode switch are pinned at the bottom. Headings are buttons (▾ open, ▸ folded) that rebuild the list (`_build_nav`, `toggle_group`); the highlight for the current page is kept (`_mark_current`).
- Order: `ordered_groups(order)` applies a saved list of headings (unknown ones ignored, new groups last); `home_rows(groups)` packs groups into Home rows in order (at most 4 cards and 3 groups per row) in place of the fixed `HOME_ROWS`; `HomePage.set_groups` rebuilds the bands; `App.set_group_order` / `move_group` / `reorder_dialog` drive both. Saved as `group_order` and `collapsed` in `settings.json`.
- With the default order the rows are exactly what they were before.

**Verification:** `python tests/run_all.py` all pass. `test_layout_app.py` now checks the scrolling frame and pinned bottom, folding and unfolding (and the highlight), reordering in the sidebar and on Home, the Up / Down / Reset buttons, a reversed order, unknown headings, and re-runs the Home fit checks (equal card widths, gaps, no scrolling at both sidebar widths) for the reordered layouts. **Not verified:** how it looks and feels on screen (mouse-wheel scrolling over the pinned areas, the fold arrows' glyphs in other fonts) and a drag-to-reorder (not built; Up / Down buttons only).

---

## 2026-10-14 08:30 +11:00 · Session 39: Library audit revamp (Clean-up merged in)

**Summary:** The Library audit and Clean-up pages overlapped (one found junk-like problems, the other fixed archives), so they are now one tool: a scan, one findings list, and fixes. Decided in a 20-question round with the user.

**Decisions:** one list with type chips instead of report tabs; keep Broken, Duplicates (with cover comparison) and Missing; Quality becomes a hidden-by-default Warnings type with editable limits; Missing is tracked per type (issues, and each collected format by volume); a single issue and a collected edition are never duplicates; the duplicate keeper is the copy with the most pages, then the taller cover, then the larger file; fixes are junk removal, CBR conversion (original deleted once verified) and move to Archive (`.bak`), applied with **Fix checked** and a confirmation, only on the list in view; only junk and CBR are pre-ticked; Ignore list kept between sessions with a restore screen; an Archive manager that purges `.bak` files; summary chips with counts. Dropped: custom removal patterns, renaming pages to `001.jpg`, CSV export (wishlist copy/save stays), rescanning only what changed (a quick cached full rescan runs after fixing). CBR to CBZ stays as its own bulk tool.

**Changes**
- `library_scan.py`: `Issue.junk` (non-image files in a zip-based archive, ComicInfo.xml excluded), stored in the cache; `CACHE_VERSION` 2 (old caches are dropped and rebuilt).
- `audit_core.py` rewritten around findings: `_identity` (type-aware duplicate identity), `keeper_rank`, `Gap.kind`, `gap_text`, `missing_by_series`, `limits_from` / `quality_flags(limits)`, `find_junk`, `find_cbr`, `Finding`, `build_findings(data, ignored)`, `plan_fixes`, `apply_fix` (archive, clean, convert), `archive_files`, `purge_archive`.
- `page_audit.py` rewritten: chips, one table, tick and Fix checked, Ignore / Ignored…, Archive…, wishlist, editable warning limits.
- `page_cleanup.py` deleted; `comic_tool.py` loses the Clean-up tool and card. `archive_tools.py` keeps the clean-up engine (used by the audit fixes and Add to library).
- Tests: `tests/test_audit_findings.py` (new), `test_audit_ui.py` rewritten, `test_fixes.py`, `test_layout.py`, `test_layout_app.py` updated. Docs: `tools.md`, `safety.md`, `architecture.md`, `known-limitations.md`, `manual-tests.md` (section D rewritten), `roadmap.md`, `tests/README.md`, `README.md`, `HANDOFF.md`.

**Technical notes:** an ignored Missing row stores one key per number it showed, so later gaps still appear; a duplicate group is ignored by its exact file set. The ignore list is kept as JSON in the page's `ignored` setting. A file with several ticked fixes gets one: Archive, then Convert (which also cleans), then Clean. A fix that fails leaves the original untouched and is noted in the row.

**Verification:** `python tests/run_all.py`: 25 of 25 pass; `ruff --select F,E9` clean. New tests cover junk detection and the cache, best-copy ordering, singles versus collected editions in duplicates, per-type gaps and wishlist lines, warning limits, findings and ignore keys, fix planning, each fix (clean, convert, archive, failures leaving no `.part`), the Archive folders, and the page end to end (chips, ticking, scoped fixes, rescan, failure notes, ignore and restore, Archive purge, settings round trip). **Not verified:** how the page looks on screen (the footer now holds more buttons), speed on a very large library, real RAR `.cbr` conversion (tests use zip-backed files), and the quality of the best-copy choice on real duplicates (manual tests D4 and D8).

---

## 2026-10-14 05:10 +11:00 · Session 38: Add to library (new comics: convert, clean, rename, file)

**Summary:** New tool that takes new comics from an Inbox folder or a drop, shows a preview table, then converts to a verified CBZ, removes junk, names with the Renamer's settings, files into series folders in a Ready folder and deletes the original after verification.

**Decisions (from a question round with the user):** intake by drop and by a remembered Inbox folder with a manual *Scan inbox* button (no live watching); preview first, one Apply; steps are convert, clean junk and rename (metadata writing was not chosen); output is a Ready folder the user picks; originals are deleted once verified (menu also offers Archive and Keep); duplicates are flagged and skipped by default. Placing comics into the existing library by matching series was deliberately postponed ("a few other features first").

**Changes**
- `intake_core.py` (new): `rename_settings`, `plan` (name, folder, status, steps for each item), `dup_key` / `library_index` (series + volume + issue + collected title, from names only), `add_comic` (copy or repack to `.part`, verify, clean with the Clean-up code, verify, swap in, then dispose of the original), `prune_empty`, `find_sources`.
- `page_intake.py` (new): the page. ComicInfo.xml is read in a thread, planning is on the UI thread, the run is a worker thread with a queue.
- `comic_tool.py`: tool card, group *Add to Library* (third Home row), `IntakePage` wired to the Renamer's `state()`, and an optional `on_show()` hook so a page can refresh when opened.
- Tests: `tests/test_intake.py`, `tests/test_intake_ui.py`; `test_layout_app.py` expects 11 tools. Docs: `tools.md`, `architecture.md`, `manual-tests.md` (H12), `tests/README.md`.

**Technical notes:** a comic is only deleted after `verify_zip` passes on the finished file; a failure removes the `.part` and leaves the original. Names that exist get a free variant instead of being overwritten. Name building mirrors the Renamer (`name_for` / `plan` follow `_compute` / `_place`), so a change to one should be made in both. Folder name matching reuses an existing top-level folder when only a leading The/A/An differs.

**Verification:** `python tests/run_all.py`: 24 of 24 pass; `ruff --select F,E9` clean. The new tests cover naming from the filename and ComicInfo, the folder-name fallback, duplicate and exists flags, ticks surviving a recompute, the pipeline (junk removal, name collisions, keep / archive / delete, sequential page names, a corrupt archive failing cleanly), and the page end to end (scan, plan, decline then accept, files in place, originals and empty folders gone, failure and retry). **Not verified:** how the page looks on screen, behaviour on a real inbox of hundreds of comics, `.cbr` files that need the external extractor (tests use zip content), and drag-and-drop onto the page.

---

## 2026-10-14 03:20 +11:00 · Session 37: Pick pages from a comic (TPB / compendium covers)

**Summary:** Single issue gets a **Pick pages…** button: every page of the loaded comic as a thumbnail, pick any, save them as JPGs. Aimed at collected editions where the covers of the original issues sit inside one archive. Purely additive; Save cover and Convert to ZIP are unchanged.

**Decisions (from a 15-question round with the user):** lives in Single issue; scrollable grid with a size slider; click, shift-click range and rubber-band selection; double-click for a full-screen view; files named `<comic name> <n>` in numbering order (not page number); folder asked on every extract; JPG pages copied untouched, other formats converted to JPG; thumbnails load lazily in a background thread; page number on each thumbnail plus a likely-cover highlight; one archive at a time; Select all / Clear / Invert, count, Reorder; "Open folder" after extracting; tests and docs. Not built (not chosen): page-range text box, keyboard shortcuts in the grid, remembered thumbnail size, PDF support.

**Changes**
- `picker_core.py` (new): `layout` / `cell_rect` / `cells_in` grid maths, `likely_covers` (portrait page that is first, follows a double-page spread, or differs in size from both neighbours), selection helpers (`toggle`, `add_all`, `invert`, `range_between`, `move`), `to_jpg`, `extract_pages`.
- `picker_window.py` (new): `PickerWindow`, a canvas grid that draws only visible cells; a loader thread (visible pages first) feeds a queue polled by the UI; reorder dialog; full-view window.
- `page_single.py`: **Pick pages…** button; the grid closes when another comic is loaded.
- `tests/test_picker.py` (new).
- **Full view revised (same session):** the page is on a canvas that can be zoomed (Ctrl+wheel, +/−, buttons; Fit resets) and dragged, the wheel scrolls when zoomed and turns pages at fit size, and clicking the page picks or unpicks it (a drag does not). A blue border shows a picked page. Reported by the user: the first version could not be scrolled. Test extended.

**Technical notes:** transparent PNG/WebP pages are flattened on white before JPEG encoding. Extra names never overwrite (`unique`). Numbers are zero-padded to the picked count so they sort.

**Bugs found and fixed:** raw Tk canvas/listbox options were given the (light, dark) colour tuple and raised `TclError` inside Tk callbacks, which Tk swallows; the first test run still passed. Fixed with `pick()`, and the test now records callback errors and fails on any.

**Verification:** `python tests/run_all.py`: 22 of 22 pass, including the new `test_picker.py` (grid maths, cover guessing, selection, JPG pass-through and conversion, naming, window with 60 pages: lazy load, click, shift, box select, invert, extract through a stubbed folder dialog, full view, closing on load). **Not verified:** how it looks and feels on screen, speed on a real 500-page CBR, and how well cover guessing works on real compendiums (manual test H11).

---

## 2026-10-08 22:40 +11:00 · Session 36: Home summary line, slim stats folder strip, nicer Home grid

**Summary:** Three polish items on the new Library stats work.

**Changes**
- **Home summary line:** *Open Stats* is now a larger, filled accent button on the left, and *Refresh* is a small square icon button (↻) to its right. The other states use the same larger buttons (*Scan your library*, *Choose your library folder and scan it*, *Try again*).
- **Library stats page:** the big drop box is gone. The library folder is a slim one-line strip right under the title (the word *Library*, the path in small text, a small **Change…** button); the *Library folder* row was removed from the options panel (the *Source* group keeps the scan switches). Dropping a folder anywhere on the page still sets and scans it.
- **Home grid:** each row is now a soft rounded band holding one to three groups. The group names are small capitals at the top, a hairline separates neighbouring groups, and the cards (white, rounded, a larger tinted icon tile, title and description, an arrow that turns blue on hover) sit inside the band. Cards are still the same width in every row and nothing scrolls.

**Files:** `comic_tool.py` (`Card`, `strip_button`, `HomePage`), `page_stats.py` (`FolderBar` replaces the drop box), tests `test_stats_home.py`, `test_stats_ui.py`, docs `tools.md`, `manual-tests.md` (H8, I1, I7).

**Bugs found and fixed:** the first version of the hairline between groups was a frame with the default height of 200 pixels, which stretched every row of the Home grid so the last row ran off the page. The Home fit test caught it; the divider now has a height of 1 and stretches with the row.

**Verification:** `python tests/run_all.py` ran all 21 scripts and every one passed, and `ruff --select F,E9` was clean. The tests now check that *Open Stats* comes before the refresh icon and is more than twice as wide, that the folder strip is slim (under 50 px) and shows the path, and the earlier Home checks still hold (all ten cards, equal widths, group gaps wider than card gaps, no scrolling at the narrowest and widest sidebar). Measured once on a 125% display: the last card ends at 806 of 975 px of the Home page. **Not verified:** how any of it looks on screen (a screenshot would capture whichever window is in front), and the ↻ glyph in other fonts or Windows versions.

---

## 2026-10-08 18:44 +11:00 · Session 35: Library stats dashboard (roadmap item 5)

**Summary:** A read-only dashboard for the whole collection, and a one-line summary of it at the top of Home. It is not a tool (it changes nothing): it has its own page, **Library stats**, reached from the sidebar or from the Home line.

**Scope (agreed in 15 questions before building)**
- One saved library folder, set on the Stats page (drop it, or Browse); other tools keep their own pickers. Choosing a folder scans it at once.
- Only `.cbz` and `.cbr` are counted (as in the Audit); `Archive` folders are skipped. The scan is light by default (names, sizes and `ComicInfo.xml`); **Read page counts** adds total pages.
- One scrolling page: tiles (comics, series, publishers, size on disk, average size, pages), then bars for series, publishers, years and formats, a metadata-coverage section, and the largest files.
- Bars show the top 15 plus an *Other* bar (**Show every bar** expands them). Series volumes are merged (**Split series into volumes** separates them); years are per year (**Group years into decades**). Missing values are in *Unknown*.
- **Click a bar** to list the comics behind it in a table under that chart, with **Open folder** and **Close**.
- Output: **Export CSV** for one chosen section and **Copy summary** (plain text on the clipboard).
- Home shows `4,210 comics · 86 series · 48.2 GB · scanned 2 days ago` with **Refresh** and **Open Stats**. The numbers are saved with the settings, so the line appears at launch without scanning. Before anything is scanned it offers *Choose your library folder and scan it* (a folder dialog, then a background scan with progress in the line).

**Changes by file**
- `stats_core.py` (new, no UI): `compute_stats` (totals, grouped rows per series, publisher, year and format, coverage, largest and smallest files), `top_n`, `years_view`, `coverage_lines`, `summary_text`, `section_table` (CSV rows), `snapshot` / `snapshot_line`, `human_size`, `ago`.
- `page_stats.py` (new): `StatsPage` (options panel *Source | Display | Output*, scan worker with Stop, dashboard), `BarChart` (bars drawn on a canvas in the theme colours, hover, click), `Tile`.
- `comic_tool.py`: the page and a *Library stats* sidebar item; the Home summary line (four states: nothing scanned, scanning, last numbers, failed); `stats_snapshot` saved in `settings.json`; the page's folder is saved with its other settings.
- Tests (new): `tests/test_stats.py`, `tests/test_stats_ui.py`, `tests/test_stats_home.py`; `tests/test_layout_app.py` now runs with the summary line on Home.
- Docs: `tools.md`, `architecture.md`, `roadmap.md`, `known-limitations.md`, `manual-tests.md` (section I), `versioning.md`, `tests/README.md`, both READMEs.

**Technical notes**
- A series is one bar per name ignoring case, punctuation and a leading *The*; the first spelling seen is the one shown. Publisher and year come from `ComicInfo.xml` where present, else from the filename (publisher only exists in `ComicInfo.xml`, so many comics land in *Unknown*).
- Real RAR `.cbr` files are not opened by the light scan, so their `ComicInfo.xml` is unknown: they are left out of the "Have ComicInfo.xml" count and the section says how many were not opened.
- An *Other (n more)* bar must not set the scale for the real bars (it lumps many rows), so bars are scaled to the biggest real row.
- Settings from a damaged `stats_snapshot` are ignored.

**Bugs found and fixed:** scanning an empty folder first showed the previous library's numbers (the page regrouped only when the scan returned comics). Found by the new test.

**Verification:** `python tests/run_all.py` ran all 21 scripts and every one passed, and `ruff --select F,E9` was clean. The new tests cover: every grouping (merged and split volumes, a leading *The*, publishers, years and decades, formats), *Unknown* last, top 15 plus *Other* and Show every bar, coverage with an unopened RAR, largest and smallest files, empty libraries, the summary text, CSV tables for all six sections, human sizes and ages; through the real page, scanning a generated library (an `Archive` folder ignored, a RAR, ComicInfo publishers and years), every tile, bar clicks listing the right comics, the table under the clicked chart, Close, CSV export (and a cancelled dialog), Copy summary, page counts, a stopped scan, the theme switch, state restore and an empty folder; and in the app, the Home line in all four states, the one-click scan, Refresh, Open Stats, a scan started from the Stats page updating Home, and the numbers and folder surviving a restart (with settings kept in a temporary file). **Not verified:** how the dashboard and the Home line look on screen (the bars, spacing and colours in light and dark), clicking with a real mouse, and speed on a real library of thousands of comics. See [manual tests](manual-tests.md), section I.

**Known issues:** see [Known limitations](known-limitations.md).

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

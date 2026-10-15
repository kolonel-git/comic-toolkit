# Roadmap

[< Docs index](README.md)

Scope: stay stateless (no database of record), YACReader-friendly, no built-in reader, no online metadata lookups, Windows desktop.
Last revised 2026-10-15 (Session 58) around the [UI revamp plan](ui-revamp-plan.md), which now drives the build order.

## How work is done

- **One feature per branch.** Each step below is one branch, one commit series and one pull request. Tools are converted one at
  a time, so old and new page layouts coexist until the revamp reaches them.
- **Each phase ends in a tagged release** (see [Versioning](versioning.md)). A phase is shippable on its own.
- Docs and tests are updated inside the same branch as the code.

## What earlier reviews found (still true)

| Finding | Effect |
|---|---|
| YACReader imports `ComicInfo.xml` only when enabled, and only on a library update | Every tool that writes metadata shows a reminder. |
| YACReader supports cbz/cbr/zip/rar/7z/pdf and shows library sub-folders; no ignore option found | `Archive` backups are stored as `.bak` so readers ignore them (inference, untested). |
| YACReader stores story-arc fields as plain text, has no reading-list import, and keeps Reading Lists in its own database | Reading Order is metadata-based (with an optional filename prefix). No `.cbl`, no database writes. |
| YACReader's editable fields are a fixed list (Series, Title, Issue number/count, Volume, Story arc/number/count, Alternate series/number/count, Series Group, Genre) | The Metadata editor is limited to fields YACReader shows. |
| Audit, Stats and the pipeline need the same library scan | One shared scan layer with a disposable cache (`library_scan.py`). |
| Unreviewed automatic writes are risky | Every write tool previews first and asks for confirmation. |
| A PyInstaller build would lose `settings.json` and must bundle drag-and-drop and theme assets | Settings move to `%APPDATA%\ComicToolkit`; the app is built as a folder, not a single file. |

## Built so far

Backup `.bak` safety fix, metadata extensions, shared library scan, Library audit (with Clean-up merged in), Reading order,
Library stats, Renamer revamp (cards and a template per type), ACEO sheets, Add to library, page picker, shared library folder,
recent folders, keyboard layer and Ctrl+K search, and the neo-brutalist UI. Details are in [The tools](tools.md) and the
[Changelog](CHANGELOG.md). From the revamp below: the shared page shell, Bulk folder, Library stats and the Metadata repair editor (two columns) and the Library audit are built.
**Where we are:** Phases 0, 1 and 2 are finished and tagged (`v0.8.0`, `v0.9.0`). Phase 3 is under way: Single issue is on the shell (step 6a); its page picker is next (6b).

## Build order: the UI revamp

Every page becomes a Header, two resizable columns and a Footer (Library stats keeps collapsible segments; see the Session 60 decision in the plan). The full design for each tool is in the
[UI revamp plan](ui-revamp-plan.md). Each numbered line is one branch.

**Phase 0: shared parts** (small and invisible on their own; built with Bulk folder)
- 0a. Shell kit: Header, Segment (summary and auto-advance), Advanced options block, Footer, folder row with `Library` and
  `Recent`, and the type scale (extends `flow_kit.py` and `ui_kit.py`). **Done** with Bulk folder (the folder row reuses the
  drop box, which already carries `Library` and `Recent`).
- 0b. Lazy scrollable table with filters. **Done** (`LazyTable`).
- 0c. Reading-order folder list (persisted, with the suggestion scan), shared by Stats, Audit and Reading order. **Done** (`reading_orders.py`; Stats uses it now, Audit and Reading order will).
- 0d. Local suggestion index (normalised series and publisher names) for Metadata, Renamer and Add to library. **Done** for Metadata (`SuggestIndex` in `metadata_core.py`); the Renamer and Add to library will reuse it.
- 0e. Link context: open a page preloaded, with a "From X" chip and a Back link. **Done** (`SegmentPage.show_origin`; Library stats to Metadata uses it, the other tools will).

**Phase 1: prove the shell** (`v0.8.0`, finished and tagged)
1. Bulk folder on the new shell (includes 0a and 0b). **Done**, and moved to two columns in Session 60.
2. Library stats: segments, Needs attention cards, reading-order toggle and section (includes 0c). **Done.**

**Phase 2: the repair loop** (`v0.9.0`, finished and tagged)
3. Metadata repair editor (includes 0d and 0e). **Done.** Built as two columns (comics left; fields and the live list of changes right) rather than three stacked segments; see the [plan](ui-revamp-plan.md#metadata-repair-editor).
4. Library audit: summary strip, Details panel, reading-order exclusion. **Done.**
5. CBR to CBZ. **Done.** Two columns (the `.cbr` list on the left; what happens to the original and to an existing `.cbz`, then the review and the run on the right), a dry run, a Delete confirmation, and the link from the Library audit's CBR chip with a Back chip.

**Phase 3: standalone tools** (`v0.10.0`)
6. Single issue, in two branches. **6a, the page on the shell: done** (two columns; a strip of the first 3 and last 2 pages with a Browse all tile; Save cover or Extract N pages in the footer; one selection shared with the picker window). **6b, the page picker: next** (a toolbar with a visible numbering-order control in place of *Reorder…*, a hint about the gestures, a legend for the orange outline).
7. Folder icons (needs the folder-shape template art first).
8. Reading order (builds the multi-drag list).
9. ACEO sheets (reuses the multi-drag list; new preview).

**Phase 4: the heavy ones** (`v0.11.0`)
10. Renamer: type prompts, suggestions, saved rules.
11. Add to library: five segments, *Set series…*, uses the Renamer's rules, and a **Watch this folder** switch that picks up new
    files in the inbox while the app is open (this replaces the former separate downloads watcher).

**Phase 5: finish** (`v0.12.0`, then `v1.0.0`)
12. Links pass for anything not yet wired, documentation clean-up, and the manual-test debt.
13. Packaging: PyInstaller **folder build** (less antivirus noise than a single file) with a shortcut and icon; bundle the
    `customtkinter` assets and the `tkinterdnd2` files; move `settings.json` to `%APPDATA%\ComicToolkit`; optionally ship 7-Zip's
    `7za.exe` so CBR works without a separate install (check its licence terms first).

## Future implementations

Not scheduled. Listed so they are not lost.

- **Undo** for the Renamer (last rename) and Metadata (last save). Needs a log or backup of old names and `ComicInfo.xml`.
- **Folder tree browser.** A lazily loaded tree with a cover and counts for the selected folder, acting as a launcher into the
  other tools. A navigation hub, not a reader.
- **Add to library:** place comics into the existing library by matching series; write fuller `ComicInfo.xml` data on the way in;
  accept PDF, EPUB and 7z.
- **Folder icons:** collage icon for parent folders such as `DC` (from four series covers); a user-supplied folder template.
- **Reading order:** replace copies with links so no real duplicates exist (not decided).
- **Command-line mode** for processing (for Task Scheduler).
- **Smaller ideas:** filter the Renamer list by type, write the detected format into `ComicInfo.xml`, ACEO bleed and crop marks,
  card labels and rounded corners, a restore button for `.bak` backups, per-field "source" badges on cards.

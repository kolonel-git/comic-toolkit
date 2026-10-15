# The tools

[< Docs index](README.md)

The Home page groups the tools as cards; the sidebar mirrors the same groups. A **Dark mode** switch sits at the bottom of
the sidebar (first launch follows Windows; your choice is remembered). Home shows every tool on one screen: soft bands, each holding one to three groups divided by a hairline, with the tool cards inside.

## On every page

- **Adding comics.** Each page has the same box at the top: drop comics or a folder on it, or use **Add folder…** or **Choose comics…**
  inside it. On the folder tools (Bulk folder, Folder icons, Renamer, Metadata, CBR to CBZ, Library audit) *Choose comics…* works on
  just the files you pick, not the rest of their folder; choosing a folder again goes back to the whole folder. (Library audit then judges
  duplicates and gaps among the picked comics only; Folder icons uses one folder per parent, with the first or last picked comic as its cover.)
  Reading order and ACEO sheets add whatever you give them to their list. **Single issue** takes one comic; its folder button opens the folder in Bulk folder.
- **The sidebar and Home sections.** The tool list in the sidebar scrolls when the window is short; *Home* and *Library stats* stay at the top, and the *Reorder sections…* button and the dark-mode switch stay pinned at the bottom. Click a section heading (▾ / ▸) to fold or unfold its tools. **Reorder sections…** opens a small window to move the headings up and down (or Reset); the sidebar and the Home bands follow immediately, and Home repacks the groups into rows so every tool still fits on one screen. The order and which sections are folded are remembered.
- **Resizing.** Drag the thin divider to resize the sidebar, a page's options panel, the Renamer's file list (beside the card) and the ACEO cover list (beside the
  preview). Drag the edge of any table heading to resize that column, and use the scrollbar under a table when its columns are wider than the window.
  The sidebar and panel widths are remembered; column widths are not.
- **Options panels** read in the same order on every page: *Source* (what to read), the tool's own groups, then *Output* (where results go and what happens to originals). The main button of a page sits at the bottom of the panel, with utility buttons (Rescan, Open folder) below a divider.
- **Buttons are grouped** by what they do, with a small divider between groups (for example Reading order: *Suggest order* | *Top ▲ ▼ Bottom* | *Remove Clear*).

## Library stats

| Tool | What it does |
|---|---|
| **Library stats** | Scan your library once and see it at a glance. Open it from the sidebar, or from the summary line at the top of Home (`4,210 comics · 86 series · 48.2 GB · scanned 2 days ago`, with a large **Open Stats** button and a small refresh icon (↻) beside it; before anything has been scanned the line offers *Choose your library folder and scan it*). Nothing is changed. |

The page has three segments (the shared layout; a finished segment folds to a one-line summary and the next opens by itself).

**Library.** Choose the library folder by dropping it on the page, with **Change…** in the strip, or from **Recent ▾** (it is remembered and scanned straight away). A shut *Advanced options* block holds *Include subfolders* and **Read page counts** (slower, adds total pages). The footer's **Rescan library** repeats the scan, which is quick for an unchanged library because of the cache; while scanning it reads **Stop**. Only `.cbz` and `.cbr` are counted, and `Archive` folders are skipped.

**Overview.** Tiles (comics, series, publishers, size on disk, average size, pages), then bars in three groups. *Collection*: **comics per series**, **per publisher**, **per year** (in time order) and **file formats**. *Health*: how complete the **metadata** is (ComicInfo.xml, year, publisher, issue number; single issues versus collected editions); a row with something missing has a **Fix these** link that opens the Metadata tool on the library. *Space*: the **largest files**. Every bar uses the one accent colour. Click a bar to list the comics behind it in a drawer at the right edge of the page (filterable, with **Open folder** and **Close**). *Chart options* (shut) holds **Split series into volumes**, **Group years into decades** and **Show every bar** (otherwise the top 15 and an *Other* bar). Missing values are shown as *Unknown*. The footer's **Export CSV…** offers every section; **Copy summary** puts a short text summary on the clipboard.

**Reading orders.** Folders of reading-order copies would be counted twice, so you mark them once and every tool leaves them out. The **Reading orders** section (shut by default) lists the marked folders with their comic counts and sizes, with **Mark a folder…** and **Unmark selected**. After a scan, a folder where most comics start with a number (`01 - Name`, `[02] Name`) or have a story arc is *suggested* on a Needs attention card: **Mark them** or **Not these** (a no is remembered). Marked folders are left out of every number on the page and of the Home line; the switch **Include reading orders in stats** (top of Overview, off by default) brings them back, and says how many comics are left out or included. The marked folders are saved with the settings.

**Needs attention.** Each card has a bold title with the count, a plain description of what the problem means and what its button does, and (for missing metadata) a few example file names. The cards: folders that look like reading orders, comics with no publisher, no year or no issue number (**Fix metadata**), and groups of possible duplicates with the same series, volume and issue (**Open Library audit**). The Home line shows how many comics need attention.

## Comic Cover Extractor

| Tool | What it does |
|---|---|
| **Single issue** | Drop in one comic. Preview the cover and first 3 pages and the last 3 pages. Save the cover (format, quality, max height, destination, file name, conflict handling), or convert the comic to a ZIP. **Pick pages…** opens a window with every page as a thumbnail (size slider, loaded in the background so a 500-page compendium opens at once); click to pick, shift-click for a range, drag a box to pick several, double-click to view a page full screen (click the page to pick it; mouse wheel changes page, or scrolls when zoomed; Ctrl+wheel or +/− zoom; drag to move; Fit resets). Pages that look like covers (first page, a page after a double-page spread, or one whose size differs from its neighbours) get an orange outline. **Select all / Clear / Invert**, a "n of N selected" count and **Reorder…** (sets the numbering order). **Extract as JPG…** asks for a folder each time and saves `<comic name> 1.jpg`, `2.jpg`… (JPG pages are copied untouched, PNG/WebP/other pages are converted at quality 95), then offers **Open folder**. |
| **Bulk folder** | Extract the cover from every CBZ/CBR in a folder. The page is a header, three collapsible segments and a footer (the layout every page will share; see the [UI revamp plan](ui-revamp-plan.md)). A finished segment folds to a one-line summary, click its title to open it again, and the next one opens by itself (the **Open the next section for me** switch at the top right turns that off). **Comics**: drop box with *Library folder* and *Recent*, *Include comics in subfolders*, and a filterable table of every comic found (long lists load as you scroll). **Covers**: four cards for where the covers go (each showing the path the first cover would get), three cards for what to do if a cover already exists (Skip, Replace, Keep both), and a shut *Advanced options* block (image format, quality, size, file name, covers folder name, the where and layout menus) whose title counts the settings you changed. **Review the covers** moves on. **Review**: a headline in plain words ("Will save 380 covers · 38 already exist and stay as they are · 3 unreadable"), where they are saved, an estimated size and a warning if the drive looks too small, the unreadable comics and any two comics that would write the same name, then a filterable table with one row per comic and a status (New, Exists, Unreadable, Name taken). *Details* lists the existing covers and what happens to each; *Show covers* adds a small picture of each cover to the rows (loaded in the background). *Dry run* shows the review as if it had run ("Would save", "Would skip"…) without writing anything. While it runs the footer shows progress with the time left; afterwards it reads *Open the covers folder* with *Extract again*, *Do another folder* and, if some failed, *Retry N failed*. The settings last used with each folder are remembered. |
| **Folder icons** | Make each series folder show its cover in Windows Explorer: builds `folder.ico`, writes `desktop.ini`, sets the Windows attributes Explorer needs, and optionally saves `folder.jpg`. Cover from first or last issue. **Custom image for a folder…** lets you pick any folder (e.g. a `DC` or `Marvel` parent) and any image. Windows only. |

## Comic Renamer

| Tool | What it does |
|---|---|
| **Renamer** | Standardise file names across a folder (CBZ, CBR, PDF, EPUB; subfolders optional). Each file is read from its name and, optionally, `ComicInfo.xml`, then shown as a **card** (one file at a time: correct its type, series, title, issue, volume, years, range and count, and see the new name, destination and status update live) or in a **list** (everything at once; double-click a name to type one, a Type to change it). A file list beside the card has filters (needs attention, issues, collected editions, edited by hand) and Previous / Next. Nothing changes on disk until **Apply renames**. The settings are in four tabs: **Detect** (what to read and how), **Names** (a naming template for each type: Issue, Annual, Special, One-Shot, Volume, TPB, Hardcover, Omnibus, Compendium, Deluxe, Library, Epic Collection, Graphic Novel, Box Set, Collection, with presets, validation, a live example and a format guide), **Text** (number padding, capitalisation, leading “The”, separators, illegal characters, extension case, maximum length) and **Folders** (folder template, collected-editions subfolder, and what to do when a name is taken). Years in any brackets are found, and a volume that is really a year is read as the year. A reading-order number written by the Reading Order tool (`01 - Name`) is dropped when renaming unless **Keep the number at the start** is on. Every option is listed in [Naming styles and templates](renamer-templates.md). |

See [Naming styles and templates](renamer-templates.md) for the eight presets and the custom template syntax.

## Metadata

| Tool | What it does |
|---|---|
| **Metadata** | Repair the details stored inside your comics (`ComicInfo.xml`, the file YACReader and most readers use) by hand, with suggestions from the rest of your library. Nothing is written until you save. |

The page is two columns side by side. **Left, the comics**: drop box with *Library folder* and *Recent*, *Include subfolders*, a **Show** menu (All comics, Needs attention, No series, No issue number, No year, No publisher, No ComicInfo.xml) and a tall, filterable table with a mark for each comic (`✓` complete, `!` needs attention, `·` locked), its series, issue, volume, year and publisher (a dash where one is missing) and whether it has been edited. A `.cbr` is listed but locked, because a RAR cannot be written to; a note offers **Convert them…** (the CBR to CBZ tool, opened on the same folder). **Select all shown** picks every comic in the table. **Right, what you can edit** (it scrolls on its own and follows the selection at once): a switch chooses *Automatic* (one comic selected gives the one-comic form, several give the many-comics form), *One at a time* or *Several at once*. *One at a time* shows the cover, the comic's place in the list with **Previous** and **Next**, and every field (series, issue number, volume, year, title, publisher, issue count; series group, genre, alternate series and story arc under *Advanced options*); a field you have changed says "edited" beside its name. Under each field are **suggestion buttons** taken only from your own library: values used in the same series, in the same folder, read from the file name, or used elsewhere (hover a button to see which). One click fills the field. Setting a publisher, series group or genre offers to apply it to the other comics in the same series that have none. *Several at once* edits only the fields you fill in (an empty field keeps what each comic has): **Set for N comics**, **Fill blanks from file names**, and under *Advanced options* **Remove issue number** (YACReader sorts by issue number before file name, so removing it makes it use the file name) and **Keep it again**. **Scroll down in the right column to the changes**: every pending change as comic, field, what it was and what it becomes, kept current as you edit. A note says how many comics change, how many values are deleted and what happens to the originals (*Advanced options* chooses a backup in an `Archive` folder or replacing the file), and **Confirm and save N changes** is the only thing that writes. The slim footer holds **Review N changes** (it scrolls to the list and writes nothing) with **Discard edits** beside it. Other fields already in the XML are kept. The links on Library stats (**Fix these**, **Fix metadata**) open this page already filtered, with a chip saying where you came from and a **Back** button; saving re-scans Library stats.

## Archive Tools

| Tool | What it does |
|---|---|
| **CBR to CBZ** | Repack RAR comics as ZIP in bulk. Each result is verified (zip integrity and matching page count) before the original is touched. Afterwards the `.cbr` is moved to `Archive` (as `.cbr.bak`), kept, or deleted. |

## Library Audit

| Tool | What it does |
|---|---|
| **Library audit** | Scans a library folder once and lists everything that needs attention in one table. Nothing changes until you tick findings and press **Fix checked**. It replaces the old Library audit and Clean-up pages. |

**Options.** *Scan:* include subfolders; **Open real .cbr files** (slow, because a RAR is extracted whole). *Checks:* **Full integrity test** (slow, reads every file completely); **Compare cover images** with Strict / Normal / Loose; **Expect issues from #1**. *Warnings:* the limits for pages, file size and cover height. `Archive` folders are skipped. A repeat scan of an unchanged library is fast, because results are cached (see [Architecture](architecture.md#the-library-scan)). Pages, covers and junk files are always read.

**The list.** Chips above the table filter it and show a count each: **All** (every type except Warnings), **Broken**, **Duplicates** (counted in groups), **Missing** (counted in series), **Junk**, **CBR** and **Warnings**. Click the box at the left of a row to tick it; **Tick all / Untick all** work on the rows you can see.

- **Broken.** Without the integrity test: files the scan notices (not a valid zip, no images, a cover that won't open). With it: the zip CRC test and the cover, middle and last pages must decode; real RAR files are checked with the extractor's own test command. Fix: move to `Archive` as `.bak`.
- **Duplicates.** Groups of probable copies, strongest evidence first: same series, volume and issue number (a single issue is never a copy of an Annual with the same number); identical file size; and, if **Compare cover images** is on, covers that look alike. A single issue and a collected edition are never grouped together, so a TPB is not a duplicate of its issues. Two copies of the same TPB (same series, volume and format) are. The **best copy** is kept: most pages, then the taller cover, then the larger file; it has no tick box. Fix: tick the others to move them to `Archive` as `.bak`.
- **Missing.** One row per series with a line per type, such as `Issues (v2): #13, #27-#29 · TPB vols: 3, 5`. Issues are checked from the lowest number you own (or #1 with *Expect issues from #1*) up to the highest you own or the issue count in `ComicInfo.xml`. Collected editions are tracked separately for each format (TPB, Hardcover, Omnibus, …) by volume number. Annuals, specials, one-shots, decimals, ranges (`#1-12`) and files with no number are not tracked. **Copy wishlist** and **Save wishlist** (`.txt` or `.csv`) appear on this chip: `Batman v2 #13`, `Hellboy TPB vol 3`.
- **Junk.** Zip-based comics holding files other than pages and `ComicInfo.xml` (Thumbs.db, `.nfo`, `__MACOSX`, …). Pre-ticked. Fix: rewrite the archive without them (verified before it replaces the original).
- **CBR.** Every `.cbr`. Pre-ticked. Fix: convert to a verified `.cbz`, remove its junk, then delete the `.cbr`.
- **Warnings.** Fewer than 10 or more than 300 pages, under 1 MB or over 500 MB, a cover under 800 px tall (change the limits under *Warnings*; the list updates without a rescan). Hidden from **All**; nothing to fix automatically.

**Fixing.** **Fix checked** acts on the ticked rows of the list you are looking at, after a confirmation that spells out what will happen (junk removed, CBR files converted and their originals deleted once verified, files moved to Archive). A file with several fixes gets one: Archive beats convert, convert already cleans. Failures are shown in the row and the status, the original is left alone, and the list rescans afterwards (quick, thanks to the cache).

**Ignore.** Select rows and press **Ignore** to hide them from every scan. **Ignored…** lists what you've hidden and restores it. The list is remembered between sessions. Ignoring a Missing row hides the numbers it shows; numbers that go missing later still appear.

**Archive…** shows every file in the `Archive` folders under the library, with sizes. Tick files and **Purge ticked…** deletes them permanently (after a confirmation; they do not go to the Recycle Bin).

## Reading Orders

| Tool | What it does |
|---|---|
| **Reading order** | Arrange issues (from one or several folders) in the order you want to read them and record it in each CBZ's `ComicInfo.xml` as a story arc, an alternate series, or both. Select several issues and drag, ▲ ▼ or Top / Bottom them together, **Suggest order** pre-sorts, untick to skip an issue, and a table previews the new number, filename and any arc being replaced. **Preview changes** lists every field that would change, without writing anything. Optional filename prefixes (`01 - Name`, `[01] Name`), **Remove issue numbers** (deletes `Number` from each issue so YACReader sorts by filename, best paired with the prefix), and an option to stamp copies in a new folder instead of the originals. See [Reading Order](reading-order.md). |

## Add to Library

| Tool | What it does |
|---|---|
| **Add to library** | Take new comics from an **Inbox** folder (press *Scan inbox*) or anything you drop on the page, show what each one will become, and on **Add to library** run the whole chain: save as a verified `.cbz` (CBR/RAR repacked, CBZ copied), remove junk files, name it with the Renamer's current settings, file it into a series folder in your **Ready** folder, then deal with the original. Only `.cbz` and `.cbr` are taken. |

The table shows each comic, what it **Becomes** (path inside the Ready folder), its **Steps** (convert, clean, rename) and a **Status**: *Ready* (ticked), or flagged and unticked: *Duplicate* (a comic with the same series, volume and issue is already in the Ready folder, or earlier in the same batch), *Exists* (that exact file name is taken) and *No series* (nothing to name it from, so it would keep its own name). Tick a flagged row to add it anyway; a taken name gets a free variant, so nothing is overwritten. *In place* means the comic already is where it belongs. Click a row to read the reason under the table. A comic that fails (not a real archive, a page count that does not match) is marked *Failed* with the reason, and its original is left alone; tick it to try again.

Options: **Inbox folder** and *Include subfolders*; **Ready folder** and *File into series folders* (uses the Renamer's folder template and *Collected Editions* subfolder setting, and reuses an existing folder when only "The" differs); *Rename like the Renamer* (off keeps each file's own name); *Remove junk files*, *Also remove files matching* patterns, *Rename pages 001.jpg…*; and **The original comic** after adding: *Delete it* (default, only after the new file passes its checks), *Move to Archive folder* (`.bak`) or *Keep it*. A confirmation spells out what happens to the originals. Folders in the inbox left empty are removed. The names follow the Renamer's settings as they are when you open the page or press the button, so set those up first. Not done yet: placing comics into the existing library by matching series, ComicInfo.xml writing, PDF/EPUB/7z.

## ACEO Cards

| Tool | What it does |
|---|---|
| **ACEO sheets** | Fills full pages of ACEO trading cards with the covers you choose and saves a print-ready PDF. Drop comics, folders or cover images on the page (or use **Add folder…**); the first page of each comic is its cover (or pick the last page for a back cover). The sheets are laid out from the blank template PDF, `ACEO - Full Page BLANK.pdf` (a Letter page with eight 3.5" × 2.5" cards), the cover list takes most of the page, and a preview of each sheet as it will print sits at the right edge, with Previous and Next and a **Full screen** button that shows the sheet as large as the screen allows (arrow keys move between sheets, Esc closes it). Reorder with ▲ ▼ Top Bottom, remove or clear covers, and print several of each with **Copies of each cover**. |

The options sit in the side panel under four headings (Template, Covers, Cards, Output): **Fit the cover** (fill the card and crop the edges, fit the whole cover inside, or stretch); **Turn the cover** (a portrait cover is turned 90° to fill a landscape card, top on the left or right, or never turned);
**Behind the cover** (white, black or light grey, seen when the whole cover is fitted inside); **Margin inside each card** (points); **Card outlines** (draws the template's card rectangles over the covers as crisp lines) with an **Outline colour** (automatic, which is black on a white or light background and white on black; black, white, light grey, grey, red, gold, or a custom `#RRGGBB`) and an **Outline thickness** (empty keeps the template's, 1 point for the bundled one); **Print quality** (150, 300 or 600 dpi);
**Choose…** another template PDF (any PDF whose card slots are drawn as rectangles; the slot count and size are read from it); **Open the PDF** when done. A last sheet with fewer covers leaves its other slots blank.
The page shows a summary like "10 covers = 10 cards on 2 sheets (6 empty slots)" and the sheet and card each cover lands on. Originals are never changed.


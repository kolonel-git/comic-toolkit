# The tools

[< Docs index](README.md)

The Home page groups the tools as cards; the sidebar mirrors the same groups. A **Dark mode** switch sits at the bottom of
the sidebar (first launch follows Windows; your choice is remembered). Home shows every tool on one screen, the groups side by side with a wider gap between groups than between cards.

## On every page

- **Adding comics.** Each page has the same box at the top: drop comics or a folder on it, or use **Add folder…** or **Choose comics…**
  inside it. On the folder tools (Bulk folder, Folder icons, Renamer, Metadata, CBR to CBZ, Clean-up, Library audit) *Choose comics…* works on
  just the files you pick, not the rest of their folder; choosing a folder again goes back to the whole folder. (Library audit then judges
  duplicates and gaps among the picked comics only; Folder icons uses one folder per parent, with the first or last picked comic as its cover.)
  Reading order and ACEO sheets add whatever you give them to their list. **Single issue** takes one comic; its folder button opens the folder in Bulk folder.
- **Resizing.** Drag the thin divider to resize the sidebar, a page's options panel, the Renamer's file list (beside the card) and the ACEO cover list (beside the
  preview). Drag the edge of any table heading to resize that column, and use the scrollbar under a table when its columns are wider than the window.
  The sidebar and panel widths are remembered; column widths are not.
- **Options panels** read in the same order on every page: *Source* (what to read), the tool's own groups, then *Output* (where results go and what happens to originals). The main button of a page sits at the bottom of the panel, with utility buttons (Rescan, Open folder) below a divider.
- **Buttons are grouped** by what they do, with a small divider between groups (for example Reading order: *Suggest order* | *Top ▲ ▼ Bottom* | *Remove Clear*).

## Comic Cover Extractor

| Tool | What it does |
|---|---|
| **Single issue** | Drop in one comic. Preview the cover and first 3 pages and the last 3 pages. Save the cover (format, quality, max height, destination, file name, conflict handling), or convert the comic to a ZIP. |
| **Bulk folder** | Extract the cover from every CBZ/CBR in a folder. Choose subfolders on or off; save into a named subfolder, a folder you choose, or beside each comic; organise as one folder, mirrored folders, or grouped by series name; JPG/PNG/WebP/original, quality, size, file name, overwrite/skip/keep-both. Shows a live example path, progress, a per-file log, and a Stop button. |
| **Folder icons** | Make each series folder show its cover in Windows Explorer: builds `folder.ico`, writes `desktop.ini`, sets the Windows attributes Explorer needs, and optionally saves `folder.jpg`. Cover from first or last issue. **Custom image for a folder…** lets you pick any folder (e.g. a `DC` or `Marvel` parent) and any image. Windows only. |

## Comic Renamer

| Tool | What it does |
|---|---|
| **Renamer** | Standardise file names across a folder (CBZ, CBR, PDF, EPUB; subfolders optional). Each file is read from its name and, optionally, `ComicInfo.xml`, then shown as a **card** (one file at a time: correct its type, series, title, issue, volume, years, range and count, and see the new name, destination and status update live) or in a **list** (everything at once; double-click a name to type one, a Type to change it). A file list beside the card has filters (needs attention, issues, collected editions, edited by hand) and Previous / Next. Nothing changes on disk until **Apply renames**. The settings are in four tabs: **Detect** (what to read and how), **Names** (a naming template for each type: Issue, Annual, Special, One-Shot, Volume, TPB, Hardcover, Omnibus, Compendium, Deluxe, Library, Epic Collection, Graphic Novel, Box Set, Collection, with presets, validation, a live example and a format guide), **Text** (number padding, capitalisation, leading “The”, separators, illegal characters, extension case, maximum length) and **Folders** (folder template, collected-editions subfolder, and what to do when a name is taken). Years in any brackets are found, and a volume that is really a year is read as the year. A reading-order number written by the Reading Order tool (`01 - Name`) is dropped when renaming unless **Keep the number at the start** is on. Every option is listed in [Naming styles and templates](renamer-templates.md). |

See [Naming styles and templates](renamer-templates.md) for the eight presets and the custom template syntax.

## Metadata

| Tool | What it does |
|---|---|
| **Metadata** | Stamp series, issue number, volume, year, title and issue count from filenames into each CBZ's `ComicInfo.xml` (the file YACReader and most readers use). The count is read from "(of 12)" or "(3 of 12)" (round or square brackets) and written as `Count`, YACReader's "Issue count". Review table with inline editing of Series, #, Vol, Year and Of; choose which fields to write; **Set for checked rows** applies one fixed value (Series Group, Genre, Alternate series or Publisher) to every checked row, which no filename can supply (an empty value cancels a pending one; Genre takes a comma-separated list); a note on the page reminds you that YACReader shows ComicInfo data only after you enable import and update the library; fill only missing fields or overwrite existing values; fall back to the folder name when the filename has no series. **Remove from checked rows** (under *Issue number*) deletes the `Number` tag from the checked files instead, so YACReader, which sorts by issue number before filename, falls back to the filename; **Keep it again** undoes that before writing, and typing a value in the table replaces a pending removal. Untick **Issue number** under *Fields to write* so a later run doesn't add it back from the filename. Other fields already in the XML are preserved. `.cbr` files can't be written to and are skipped with a note. |

## Archive Tools

| Tool | What it does |
|---|---|
| **CBR to CBZ** | Repack RAR comics as ZIP in bulk. Each result is verified (zip integrity and matching page count) before the original is touched. Afterwards the `.cbr` is moved to `Archive` (as `.cbr.bak`), kept, or deleted. |
| **Clean-up** | Remove non-image junk (Thumbs.db, `.nfo`, `__MACOSX`, …) and files matching patterns you type (e.g. `zzz*`); optionally rename pages to `001.jpg`, `002.jpg`, … (this also flattens folders inside the archive). `ComicInfo.xml` is always kept. |

## Library Audit

| Tool | What it does |
|---|---|
| **Library audit** | Scans a library folder once, then shows four reports you switch between at the top of the page. Nothing is changed by scanning, and every report exports to CSV. |

Options: include subfolders; **Read page counts and covers** (on by default, needed for the quality checks and cover comparison);
**Open real .cbr files** (slow, because a RAR is extracted whole); **Full integrity test** (slow, reads every file completely). `Archive` folders are skipped.
A repeat scan of an unchanged library is fast, because results are cached (see [Architecture](architecture.md#the-library-scan)).

- **Broken.** Without the integrity test: files the quick scan notices (not a valid zip, no images, a cover that won't open). With it: the zip CRC test
  and the cover, middle and last pages must decode; real RAR files are checked with the extractor's own test command.
- **Duplicates.** Groups of probable copies, strongest evidence first: same series, volume and issue number (from `ComicInfo.xml` or the filename);
  identical file size; and, if **Compare cover images** is on, covers that look alike (Strict, Normal or Loose). The biggest file in each group is left
  unticked and the others are pre-ticked. **Move checked to Archive** moves ticked files into an `Archive` folder as `.bak`, after a confirmation; nothing is deleted.
- **Missing.** For each series and volume, the issue numbers you don't own, such as `Batman v2: #13, #27-#29`. A series is checked from the lowest issue you own
  (or from #1 with **Expect issues from #1**) up to the highest issue you own or the issue count in `ComicInfo.xml`, whichever is larger. Annuals, specials,
  one-shots, decimal numbers and files with no issue number are ignored. **Copy wishlist** and **Save wishlist** (`.txt` or `.csv`) give one line per missing issue.
  Nothing is remembered between runs.
- **Quality.** Flags files with fewer than 10 or more than 300 pages, a size under 1 MB or over 500 MB, or a cover under 800 px tall. These limits are fixed.

## Reading Orders

| Tool | What it does |
|---|---|
| **Reading order** | Arrange issues (from one or several folders) in the order you want to read them and record it in each CBZ's `ComicInfo.xml` as a story arc, an alternate series, or both. Select several issues and drag, ▲ ▼ or Top / Bottom them together, **Suggest order** pre-sorts, untick to skip an issue, and a table previews the new number, filename and any arc being replaced. **Preview changes** lists every field that would change, without writing anything. Optional filename prefixes (`01 - Name`, `[01] Name`), **Remove issue numbers** (deletes `Number` from each issue so YACReader sorts by filename, best paired with the prefix), and an option to stamp copies in a new folder instead of the originals. See [Reading Order](reading-order.md). |

## ACEO Cards

| Tool | What it does |
|---|---|
| **ACEO sheets** | Fills full pages of ACEO trading cards with the covers you choose and saves a print-ready PDF. Drop comics, folders or cover images on the page (or use **Add folder…**); the first page of each comic is its cover (or pick the last page for a back cover). The sheets are laid out from the blank template PDF, `ACEO - Full Page BLANK.pdf` (a Letter page with eight 3.5" × 2.5" cards), the cover list takes most of the page, and a preview of each sheet as it will print sits at the right edge, with Previous and Next and a **Full screen** button that shows the sheet as large as the screen allows (arrow keys move between sheets, Esc closes it). Reorder with ▲ ▼ Top Bottom, remove or clear covers, and print several of each with **Copies of each cover**. |

The options sit in the side panel under four headings (Template, Covers, Cards, Output): **Fit the cover** (fill the card and crop the edges, fit the whole cover inside, or stretch); **Turn the cover** (a portrait cover is turned 90° to fill a landscape card, top on the left or right, or never turned);
**Behind the cover** (white, black or light grey, seen when the whole cover is fitted inside); **Margin inside each card** (points); **Card outlines** (draws the template's card rectangles over the covers as crisp lines) with an **Outline colour** (automatic, which is black on a white or light background and white on black; black, white, light grey, grey, red, gold, or a custom `#RRGGBB`) and an **Outline thickness** (empty keeps the template's, 1 point for the bundled one); **Print quality** (150, 300 or 600 dpi);
**Choose…** another template PDF (any PDF whose card slots are drawn as rectangles; the slot count and size are read from it); **Open the PDF** when done. A last sheet with fewer covers leaves its other slots blank.
The page shows a summary like "10 covers = 10 cards on 2 sheets (6 empty slots)" and the sheet and card each cover lands on. Originals are never changed.


# UI revamp plan

[< Docs index](README.md)

Working report on the planned redesign of every page. One section per feature: current state, owner's suggestions, proposed
design. The status column below says what is built; [The tools](tools.md) describes the app as it is today, and the
[roadmap](roadmap.md) gives the build order.

| Section | Status |
|---|---|
| Global shell and segmented pages | agreed |
| Library scan / stats | agreed, built |
| Single issue | agreed, built (two columns, and the page picker) |
| Bulk folder | agreed, built (two columns) |
| Folder icons | agreed, built (two columns; collage deferred) |
| Metadata (repair editor) | agreed, built (two columns) |
| CBR to CBZ | agreed, built (two columns) |
| Library audit | agreed, built (two columns) |
| Reading order | agreed, built (two columns, and the multi-drag list) |
| Add to library | agreed, built |
| ACEO sheets | agreed, built (two columns) |
| Renamer | agreed, built |
| Future work (all tools) | agreed |
| Links between tools | agreed, built (a Next steps row; Library stats and audit links were already there) |

## Global shell and segmented pages

**Current:** left options panel plus main area on most pages; Bulk folder is the first page converted to the shell. Many options sit in one
panel. Type uses about ten sizes (8 to 28 pt), Segoe UI plus Arial Black headings plus Consolas, and several accent colours.

**Owner's decision (Session 60): two columns.** Every page except Library stats is laid out as **two resizable columns** under the header, with the footer below: what you choose (the folder, the list of comics) on the left, and what you can set and the review of what will happen on the right, which scrolls on its own. The divider between the columns is dragged to the width you like (and remembered), and every table column is resizable too. Library stats keeps the stack of segments. Bulk folder, Metadata, Library audit, CBR to CBZ, Single issue, Reading order, ACEO sheets and Folder icons are built this way; ACEO sheets, the Renamer and Add to library follow when their turn comes (they already have a main area and a draggable options panel, so for them it is mostly regrouping the options into titled blocks and putting the review and the run under them). The per-tool sections below still describe what each part holds; read "segment" as "block of a column" for every page except Library stats.

**Owner's decisions (the original segment design, still true for Library stats)**
- Every tool is a stack of **collapsible segments**. A finished segment folds to a short summary of what it did or holds.
- Every tool has the **same three parts**: Header, Segments, Footer. Footer holds only the main action and a few other buttons.
- **Advanced options** sit in a clearly marked collapsed section *inside* its segment.
- **No step numbers.** Segment labels say what the segment is for.
- **No persistent library bar.** Tools that open a folder put *Library folder* and *Recent* buttons next to the folder control.
- **One type hierarchy** across the app: no stray fonts or colours.

**Proposed design**
1. *Header*: tool name plus one sentence of purpose. Nothing else.
2. *Segment*: title row (name, one-line summary when collapsed, chevron). Open segment shows its controls only.
   Opening one segment does not force others shut; the next unfinished segment opens by itself when the current one completes.
3. *Advanced*: a bordered, tinted sub-block titled "Advanced options" with a chevron and a count of non-default settings
   ("Advanced · 2 changed"), collapsed by default.
4. *Footer*: main action right (one primary colour), secondary actions left (Rescan, Open folder), status text in the middle.
5. *Folder picker row*: drop zone or path, then `Library` and `Recent ▾` buttons directly beside it.
6. *Drag and drop* always has button and keyboard equivalents (WCAG 2.2 dragging movements).
7. *Type scale* (agreed): Page title Arial Black 22 (the only use of Arial Black); Segment title Segoe UI 15 bold; Body 13;
   Hint/caption 11 muted; Consolas 12 only for paths and templates. Colour roles: text, muted, accent (primary action and
   focus only), danger, success. Pink accent text stays for links only.
8. *Auto-advance* (agreed): finishing a segment collapses it to its summary and opens the next unfinished one. A setting
   turns this off. Review and Run share one segment; the footer button is the only "go" control.

## Library scan / stats

**Current:** pick a library folder, scan, see tiles and bar charts (series, publisher, year, formats, metadata
completeness, largest files); click a bar to list comics; CSV export and text summary. Only `Archive` folders are skipped, so
reading-order copies inflate every count.

**Owner's suggestions:** exclude duplicates caused by reading-order folders; fill in missing metadata manually, entered via
the "how complete is the metadata" chart.

**Proposed design**
- *Segments:*
  1. **Library**: folder picker with `Library` and `Recent` buttons beside it. Collapsed summary: "412 comics · scanned 2 days
     ago". Scan options under *Advanced options*.
  2. **Overview**: tiles, then charts grouped *Collection* (series, publishers, years, formats), *Health* (metadata
     completeness) and *Space* (largest files). Bar click opens the comic list in a side drawer.
  3. **Needs attention**: actionable cards with counts and a button ("63 comics have no publisher: Fix metadata", "Possible
     duplicates: Open Library audit").
- *Reading-order folders (agreed: option A with B suggestions):*
  - The user marks folders (or a parent such as `Reading Orders`) as **Reading orders**. The list is remembered between
    sessions and is shared by Library stats, Library audit and Reading order.
  - The scan suggests folders that look like reading orders: most files start with `01 - ` or `[01] `, or have a story arc set
    in `ComicInfo.xml`. A suggestion is only a prompt ("Mark as reading order?"); nothing is excluded until the user accepts.
  - Wherever the user adds or marks a folder, the existing reading-order folders are listed so they can pick from them.
  - Reading-order comics get their own **Reading orders** section, collapsed by default, with its own counts.
  - A visible toggle, **Include reading orders in stats**, sits in the Overview header. Off by default, so totals count real
    comics once. The choice is remembered.
- *Charts:* one accent colour for all bars.
- *Missing metadata:* each field row in the Health chart gets **Fix these**, which opens the Metadata repair editor filtered to
  the comics missing that field. The Needs attention cards use the same entry.
- *Home:* the summary line gets a "needs attention" count.

## Single issue

**Current:** drop one comic; preview of the cover, first 3 and last 3 pages; save the cover (format, quality, max height,
destination, file name, conflict handling) or convert the comic to a ZIP. *Pick pages…* opens a thumbnail grid (click,
shift-click, box select, full-screen viewer with zoom, cover-page outlines, Select all / Clear / Invert, Reorder,
Extract as JPG).

**Owner's suggestions:** make *Pick pages* clearer and more visible; strip shows the first 3 pages and last 2; take in all
suggested changes; remove features that overlap other tools; footer changes with the user's choice.

**Proposed design**
- *Segments:*
  1. **Comic**: drop box with `Library` and `Recent` beside it. Summary: "Batman 012 · 32 pages · CBZ".
  2. **Pages**: a strip of the first 3 pages and the last 2, with a large **Browse all N pages…** tile at the end. Clicking a
     strip thumbnail opens the full-screen viewer. Picked pages show a tick. Summary: "Cover" or "5 pages picked".
  3. **Save**: format, quality, max height, plus a live line showing the file name that will be written. Destination, file
     name and conflict handling sit under *Advanced options*.
- *Footer (changes with the choice):* nothing picked gives **Save cover**; pages picked gives **Extract N pages**. Secondary
  buttons: **Save all pages as ZIP** (a pages shortcut, not a conversion) and Open folder after a save.
- *Page picker:* one selection shared with the strip (no second selection). A toolbar holds Select all / Clear / Invert and a
  visible **Numbering order** control in place of *Reorder…*. A one-line hint explains the gestures ("Shift-click for a range,
  drag a box to pick several, double-click to enlarge"). The orange outline gets a legend, "Looks like a cover".
- *Removed:* **Convert to ZIP** (overlaps CBR to CBZ and Add to library).

**As built (Session 62, step 6a):** two columns. Left: Comic (the drop box; its folder button still opens the folder in Bulk folder) and Pages (the strip: cover, pages 2 and 3, and the last two pages, wrapping to the width of the column, then the **Browse all N pages…** tile). Right: Save (format, quality, size, the live line naming the file that will be written, and the result of the last save) with *Advanced options* for where to save, the file name and what to do when the file exists. Clicking a page of the strip opens the picker window straight on that page in its full-size view, where a click or Space picks it; a tick and its number then show under the page. The picks are one list shared by the page and the picker window (`PickerWindow(order=, on_change=)`, `set_order`). The footer reads **Save cover** until pages are picked and **Extract N pages** after, with **Save all pages as ZIP**, **Clear picks** and, after a save, **Open folder** beside it. Extracting still asks for a folder each time, as the picker's own button does. The `Library` and `Recent` buttons are not on this page (it takes one comic, not a folder).

**As built (Session 63, step 6b):** the picker window's toolbar has two rows and a line under them. Row 1: Select all, Clear, Invert, the count, Extract as JPG…. Row 2: **Numbering**, a switch between *In the order picked* and *By page number*, then **Arrange…** and the size slider. The line: the gestures on the left and the orange swatch with *Looks like a cover* on the right, always shown (it used to appear in the status line only once loading finished, and was replaced by any message). *By page number* keeps the picks sorted whenever they change; going back to *In the order picked* leaves them as they are. Difference from the plan: the plan replaces *Reorder…* outright; I kept the move up and down window, renamed **Arrange…**, because the switch alone cannot make an order that is neither the picking order nor page order. It is off while *By page number* is on.

## Bulk folder

**Current:** its own three-step layout (Choose your comics, Choose what you get, Review and extract) that differs from the
other pages; step headings explain the obvious; step 2 shows about ten decisions at once; facts panel, preview panel and
settings cards each use their own style.

**Owner's suggestions:** bigger UI/UX revamp; drop the labels that talk down to the user; make the flow uniform with every
other page, not a special case.

**Proposed design** (global shell: Header, Segments, Footer; see top)
- *Header:* "Bulk folder" and one sentence: "Save the cover of every comic in a folder."
- *Segments:*
  1. **Comics**: drop box with `Library` and `Recent` beside it, plus *Include subfolders*. Summary: "412 comics in 86
     series · D:\Comics". The comics are shown in a scrollable, filterable table. Above a set size (about 500 rows) rows
     are loaded lazily as the user scrolls, so a large library opens at once.
  2. **Covers**: the tool's own settings, in the same order as other tools (what, then where, then conflicts).
     - *Where to save*: cards (Beside each comic / One covers folder / Inside each series folder / Somewhere else…), each
       with a real example path.
     - *If a cover exists*: Skip / Replace / Keep both.
     - *Advanced options* (collapsed): image format, quality, max height, file name pattern, covers folder name.
     Summary: "JPG · beside each comic · skip existing".
  3. **Review**: same table logic as Comics (scrollable, filterable, lazy-loaded above about 500 rows), one row per comic:
     comic, cover file name, status (New, Exists, Unreadable). Above the table, a headline of counts in plain words: "Will
     save 412 covers · 38 already exist · 3 unreadable", with the estimated size ("about 96 MB") and a warning if the
     destination drive is short of space. Problems (unreadable files, two comics writing the same file name) are listed first.
     Existing covers show as a count; a **Details** button opens the per-row list and how each will be handled. A **Show
     covers** toggle loads small thumbnails lazily for visible rows only (off by default). While running: progress with time
     left and the table updates live. After: "Saved 380 · Skipped 38 · Failed 3", each count filters the table; failures give
     the reason in plain words.
- *Footer:* main action **Extract N covers** (then **Stop**, then **Open covers folder**); secondary: **Dry run**, and
  **Retry failed** after a run with failures.
- *Wording:* no "Step N" headings or lecture text. Each control says what it is and shows an example underneath.
- *Auto-advance:* completing Comics opens Covers; completing Covers opens Review.
- *Remembered:* last settings per library folder.
- **Dry run** opens Review with every row marked "would write"; nothing is created.

## Folder icons

**Current:** builds `folder.ico`, writes `desktop.ini`, sets Explorer attributes, optionally saves `folder.jpg`. Cover from
the first or last issue. *Custom image for a folder…* for any folder. Windows only. The icon is a flat cover, so it does not
read as a folder.

**Owner's suggestions:** put the cover on a folder-shaped template so it reads as a folder; offer all three styles, shown on
one example folder first, then the user decides; add a dry run or preview before any change.

**Proposed design** (Comics > tool segment > Review spine)
- *Header:* "Folder icons" and one line: "Make each series folder show its cover in Explorer."
- *Segments:*
  1. **Folders**: drop box with `Library` and `Recent` beside it, plus *Include subfolders*. Lists series folders, not
     comics, in a scrollable lazy-loaded table. Summary: "86 series folders · 12 already have icons".
  2. **Icon style**: a live preview built from the first folder in the list (name shown; a *Try another folder* control
     swaps the example). Three style cards, each rendered with that folder's cover:
     - *Folder with cover*: folder shape, cover sticking out of the front pocket, slightly tilted.
     - *Folder tab*: flat folder with the cover as its front face.
     - *Cover only*: today's flat cover.
     Below the cards: **Cover from** (first issue / last issue). *Advanced options*: folder colour, series-name badge, cover
     scale, also save `folder.jpg`. Summary: "Folder with cover · first issue".
  3. **Review**: the dry run. Same table logic as Bulk folder: folder, issue used, thumbnail of the finished icon, status
     (New, Has icon, No comics found). Headline counts: "Will make 74 icons · 12 have icons (replace) · 2 have no comics".
     A **Show icons** toggle is on by default here (thumbnails are the point), loaded lazily. *Use a different image…* on any
     row replaces the old "Custom image for a folder" button. Nothing is written until the footer button is pressed.
- *Footer:* main action **Make N icons**; secondary: **Remove icons** (restores the default folder look for the folders in the
  list, after a confirmation that names how many) and **Refresh Explorer** (clears the Windows icon cache so changes show).
- *Style, bundled templates:* two or three bundled folder-shape images with transparent areas; no user template yet.

**As built (Session 67, step 7):** two columns. Left: **Folders**, a compact drop box, *Include subfolders* and one table that is both the list and the dry run (a lazy-loaded picture of the finished icon on every row, the folder, the comic its cover comes from, the status); *Use a different image…* and *Use the cover again* sit above it. Right: **Icon style** (a big picture for an example folder with **Try another folder**, three style cards each drawn with that folder's cover, **Cover from** first or last issue, and *Advanced options*) and **Review**. Footer: **Make N icons**, **Remove icons**, **Refresh Explorer**. The folder shapes are drawn in code (`folder_icons.render_icon`: back panel and tab, the cover tilted 7° and framed above the front pocket, or the cover as the folder's face, in six colours, with an optional series-name label), which is why the plan's "bundled template images" were not needed. Differences from the plan: the plan's separate **Folders** and **Review** tables are one table; the status of a folder that already has an icon follows *If a folder already has one*; *Use a different image…* works on the selected rows and, with none selected, asks for any folder and an image (the old "Custom image for a folder…" button); **Remove icons** only removes icons this tool made (the ones that point at `folder.ico`). The column of the table that holds the picture is the table's own picture column, so the pictures are 42 px.

**Deferred:** collage icon for parent folders (for example `DC`, from four series covers). To be decided later.

## Metadata (repair editor)

**Current:** reads filenames and writes series, issue, volume, year, title and count into each CBZ's `ComicInfo.xml`; review
table with inline editing; *Set for checked rows* for fixed values (Series Group, Genre, Alternate series, Publisher);
`Number` tag removal; fill-missing or overwrite modes; folder-name fallback; `.cbr` skipped.

**Owner's suggestions:** change to a manual editing tool for data repair; entered from Library scan's metadata completeness
chart; edit each comic individually with suggestions from other comics for each field; bulk edit by selecting many comics.

**Layout change (Session 57, owner request):** built as two columns instead of three stacked segments. Left: the Comics table
(tall, filterable). Right (scrolls on its own): the Fix form, which follows the selection at once (Automatic, with a switch
to force *One at a time* or *Several at once*), and under it the Review table of pending changes, always current, with the
save controls. The footer button scrolls to that list. The segment descriptions below still say what each part holds.

**Proposed design** (Comics > Fix > Review spine)
- *Header:* "Metadata" and one line: "Fill in and correct the details stored inside your comics."
- *Segments:*
  1. **Comics**: scrollable, filterable, lazy-loaded table with `Library` and `Recent` beside the folder control. Columns:
     file, series, #, volume, year, publisher, completeness dot; missing cells are highlighted. When opened from Library
     scan the table arrives pre-filtered ("Missing publisher · 63 comics") with a removable filter chip. `.cbr` rows are
     visible and locked, with a link to CBR to CBZ. Summary: "63 comics need attention".
  2. **Fix**: the edit form. It **switches automatically** with the selection (one row selected: single form; several rows:
     bulk form) and has a **manual switch** (One at a time / Many at once) to override.
     - *One at a time:* cover thumbnail, fields for series, issue, volume, year, title, publisher, count; *Advanced
       options* for Series Group, Genre, Alternate series, story arc, writer and other fields. Each field shows **suggestion
       chips**; one click fills it. Previous / Next move through the filtered list.
     - *Many at once:* edit only the fields to change; every field defaults to *Keep existing*; button **Set for N comics**.
       Fixed-value fields (Series Group, Genre, Alternate series, Publisher) live here. *Remove issue number* sits under
       *Advanced options*. **Fill blanks from filenames** is a quick first-pass shortcut for the selection.
  3. **Review**: the pending edits as a table (comic, field, old value to new value). Nothing is written until the footer.
- *Footer:* main action **Save N changes**, after a confirmation that states how many comics and fields change;
  secondary: **Discard edits**. (No undo; the confirmation is the safeguard.)
- *Suggestions:* from the local library only: other comics in the same folder, comics with a similar series name (names
  normalised so "The Amazing Spider-Man" matches "Amazing Spider-Man"), and the filename. No online sources.
- *After fixing one comic:* offer "Apply to the other N comics in this series?".
- *Library scan link:* after saving, Library scan's numbers refresh without a full rescan. Other fields already in the XML are
  preserved.

## CBR to CBZ

**Current:** repacks RAR comics as ZIP in bulk; each result is verified (zip integrity and matching page count) before the
original is touched; the `.cbr` is moved to `Archive` as `.cbr.bak`, kept or deleted. Overlaps with the Library audit CBR chip
and with Add to library, which both convert as a side effect.

**Owner's decision:** keep it as a small standalone tool (option A), with the extra items below.

**Proposed design** (Comics > Convert > Review spine)
- *Header:* "CBR to CBZ" and one line: "Repack RAR comics as ZIP, checked before anything is replaced."
- *Segments:*
  1. **Comics**: drop box with `Library` and `Recent` beside it, plus *Include subfolders*. The scrollable lazy-loaded table
     lists only `.cbr` files (size, pages, whether it is a real RAR). Summary: "38 CBR files · 2.1 GB".
  2. **Convert**: **What happens to the original**: Move to Archive (`.bak`) / Keep it / Delete it, with each option stating
     the consequence. *Advanced options*: remove junk files, rename pages `001.jpg…`.
     Summary: "Original moved to Archive".
  3. **Review**: same table logic as the other tools: file, result, status. Headline: "Will convert 38 files · 2.1 GB →
     about 1.9 GB (saves about 200 MB)", plus a plain-words **Converted only if verified** note: each new file must open,
     have the same page count and pass the zip test before the original is touched. Progress with time left while running;
     after: "Converted 36 · Failed 2", failures with the reason; originals of failed files are never touched.
- *Footer:* main action **Convert N files**, then **Stop**, then **Open folder**; secondary: **Retry failed**.
- *Link:* the Library audit CBR chip offers "Convert in bulk" which opens this page with the files preloaded.

**As built (Session 61):** two columns, following the Session 60 decision. Left: Comics, a filterable table of the `.cbr` files (file, folder, kind: *RAR* or *ZIP inside*, size), the kind found by a background check. Right: Convert (the cards for the original and for an existing `.cbz`, *Advanced options* with the junk and page-name switches) and Review. Differences from the proposal: the headline gives the size to convert and says the new files are about the same size, because pages are stored as they are (no "saves about 200 MB" promise, which could not be true); the page count is not shown in the list, because counting a RAR's pages means extracting it. The tidy-up runs on the `.part` file before it takes its place, so a failure leaves the old `.cbz` and the original untouched. **Delete it** asks once before the run starts.

## Library audit

**Current:** one scan, one table, chips (All, Broken, Duplicates, Missing, Junk, CBR, Warnings), grouped options (Scan,
Checks, Warnings), **Fix checked** after a confirmation, Ignore list, Archive browser with purge, wishlist copy and save.
Reading-order copies show up as duplicates.

**Owner's suggestions:** ignore reading-order copies; add a summary strip of counts with a details button; add links between
tools (see *Links between tools*).

**As built (Sessions 59 and 60, owner decisions):** the **Details** button opens a panel over the right half of the page (not a separate window) which also points to the tool that fixes each kind of problem (Metadata for comics with no series or issue number, CBR to CBZ for `.cbr` files, Library stats for reading orders). The page is two columns: the library and the findings on the left (Library folds to a one-line summary after the first scan of a folder), the Checks always in view in the right column. The strip's counts select their chips; a **Reading orders** chip lists the marked folders; the Checks switches decide which kinds are listed and fixed.

**Proposed design** (Library > Checks > Findings spine)
- *Header:* "Library audit" and one line: "Find broken, duplicate, missing and untidy comics, then fix them."
- *Segments:*
  1. **Library**: folder picker with `Library` and `Recent`, plus *Include subfolders*. Summary: "412 comics scanned".
  2. **Checks**: plain toggles for Broken, Duplicates, Missing, Junk, CBR and Warnings. *Advanced options*: full integrity
     test, open real `.cbr` files, cover comparison (Strict / Normal / Loose), "Expect issues from #1", warning limits.
     Summary: "6 checks · normal". Collapses after the first scan so a repeat scan starts with one click.
  3. **Findings**: a **summary strip** above the table with counts ("3 broken · 12 duplicate groups · 4 series with gaps ·
     9 junk · 38 CBR"). Each count selects its chip. A **Details** button opens the breakdown for the strip. Then the
     existing table and chips, plus a **Reading orders** chip.
- *Reading orders:* folders come from the shared reading-order list set in Library stats. They are left out of Duplicates by
  default. A visible toggle, **Include reading orders in duplicates**, mirrors the one in Library stats, and the chip shows how
  many comics were left out. A duplicate group with one copy inside a reading-order folder and one outside treats the outside
  copy as the original.
- *Footer:* main action **Fix N checked**, after a confirmation of counts with a **Details** button that lists each file and
  where it goes (Archive moves can be reversed; deletes cannot, and it says so). Secondary: **Rescan**, **Ignored…**,
  **Archive…**; **Copy wishlist** and **Save wishlist** appear on the Missing chip only.
- *Links:* see *Links between tools*.

## Reading order

**Current:** arrange issues from one or several folders; record the order in `ComicInfo.xml` as a story arc, an alternate
series or both; move items by drag, ▲ ▼ or Top / Bottom (several at once); *Suggest order*; untick to skip; a preview table
and *Preview changes*; optional filename prefixes, *Remove issue numbers*, and stamping copies into a new folder.

**Owner's suggestions:** make selecting and moving clearer in a drag-and-drop style. Several selected files collapse into one
movable item; on release they show again, in the same order, at the new place.

**Proposed design** (Comics > Order > Stamp > Review spine)
- *Header:* "Reading order" and one line: "Put issues in the order you want to read them and save it in each comic."
- *Segments:*
  1. **Comics**: add issues from one or several folders, with `Library` and `Recent` beside the folder control and the
     existing reading orders listed. Summary: "42 issues from 3 folders".
  2. **Order**: a list with a drag handle on every row.
     - *Selecting:* click, Ctrl-click, Shift-click, or drag a box.
     - *Multi-drag:* the selection collapses into one stacked card with a count badge ("5 issues"). A thick insertion line
       shows the drop spot and the list scrolls itself near its edges. On release the cards expand in their original order
       at the new spot with a short highlight.
     - *Buttons and keys (never drag only):* ▲ ▼ Top Bottom, Alt+↑ / Alt+↓, and **Ctrl+Z** to
       undo list moves.
     - *Suggest order*: by publication date, issue number or file name.
     Summary: "42 issues · custom order".
  3. **Stamp**: how the order is recorded: story arc name, alternate series, or both. *Advanced options*: filename prefix
     style (`01 - Name`, `[01] Name`), remove issue numbers, stamp copies in a new folder instead of the originals.
  4. **Review**: changed fields as old to new, with a **Details** button. Nothing is written before the footer.
- *Footer:* main action **Stamp N comics**; secondary: **Preview changes**, **Mark as reading order**.
- *Reading-order folders:* when the stamp makes copies in a new folder, the user is asked once, "Mark this folder as a reading
  order so it stays out of your stats and duplicate checks?" with an *Always do this* choice. After that, new folders are marked
  automatically. A setting turns it off. The marking uses the shared list from Library stats.
- *Links:* see *Links between tools*.

**As built (Session 64, step 8a):** two columns. Left: Comics (the drop box, with *Library* and *Recent* added by the app, and **Open a reading order ▾**, a menu of the marked reading-order folders that adds their comics) and Order (the table as before, with the summary "42 issues · custom order" or "suggested order"). Right: Stamp (name, how to record, arc numbers, series group; *Advanced options* for the filename prefix, Remove issue numbers, copy to a new folder, the original file, and the marking habit) and Review (a headline of counts, what happens to the originals, the YACReader reminder, **Details** for the old preview text). Footer: **Stamp N comics**, **Preview changes**, **Mark as reading order**. Marking: after copies are made the page asks once (*Mark it*, *Always mark new ones*, *Not now*), or follows the setting *Ask me / Always mark it / Never*; **Mark as reading order** marks the folder of the last copies, or the one folder every listed issue sits in. The marked list is the one shared with Library stats and the Library audit. Differences from the plan: Review is a headline and a **Details** button, not a second table (the list on the left already shows each issue's new number, name and status); **Suggest order** keeps its single behaviour (series, volume, year, issue number) and the stamp's *Order* summary is not a block of its own. The *Metadata* link after stamping is left for the links pass.

**As built (Session 65, step 8b):** the list is a list of cards (`CardList`, `cardlist.py`; the maths in `blocks.py`), so ACEO can use it as it is. Each comic is a card drawn on a canvas (only the cards in view are drawn): a tick box, a yellow number badge, the file name, a muted line saying what it will become and the arc it is in now, and a status at the right. Hold a card anywhere and drag it. A click selects, Ctrl+click adds or removes one, Shift+click selects a range from the card last clicked (Ctrl+Shift adds the range), and dragging a box from the space between or under the cards selects the cards it touches (Ctrl keeps the old selection). Pressing a selected card keeps the selection so it can be dragged; a click that does not move selects just that card. The selected cards collapse into a stack of up to three carrying the name of the first and a pink count ("5 issues"); a thick blue line marks the gap they will land in (the half of a card the pointer is in decides before or after it); within about 26 px of the top or bottom edge the list scrolls by itself while the pointer stays; on release the cards arrive together, in their old order, and are tinted for 0.7 s. Escape cancels. Keys and buttons: ▲ ▼ Top Bottom, Alt+Up and Alt+Down, the arrow keys, Home, End, Ctrl+A, Space (tick), **Undo** and Ctrl+Z (50 moves; the history is dropped when issues are added or removed). **Suggest order ▾** is a menu: series, volume, year and issue number (as before), publication date, issue number, file name; each can be undone. Room: the list gets the height the page can give it. The drop box is slim (`DropZone(compact=True)`: one line of prompt, then every button in one wrapping row, with the app's Library folder and Recent and the page's own *Open a reading order ▾*); all the list's buttons, *Remove* and *Clear* too, are one row (`FlowRow`, which wraps only when the column is too narrow); the line "N issues · K to write" is in the Order block's summary; the hint is two lines and the status line shows only while it has something to say. Differences from the plan: no drag handle (a card is picked up anywhere, which was the owner's request after the first version, a table with a grip column); no **Move to position…** box (removed at the owner's request); the "short highlight" is a tint, not an animation.

## Add to library

**As built (Session 69, step 11):** two columns instead of five segments. Left: **Inbox** (compact drop box with *Scan inbox*, the inbox folder, *Include subfolders*, **Watch this folder**) and **Review** (a `CardList`, `reorder=False`; flagged comics first with a red stripe and *Set series…*, *Add anyway* or *Skip*; the full path under the list). Right: **Destination** (Ready folder, filing, naming line, **Naming settings** opens the Renamer) and **Clean-up** (junk, page names, **The original comic** as three cards that state the consequence, extra junk patterns under Advanced options). Footer: **Add N comics**, **Stop**, **Open Ready folder**, **Retry N failed**. *Set series…* sets `Item.series`, which wins over the name and ComicInfo, and writes `Series` into the new comic's `ComicInfo.xml` afterwards. The watch (`intake_core.Settling`) lists a comic once its size is the same on two looks three seconds apart. Differences from the plan: the Review table's Steps are written as text on the card, not icons; *Add anyway* on an *Exists* comic adds it under a numbered name; suggestions for *Set series…* from the local library are not built (the dialog is a plain box); the *Summary* lines of the segments are not shown.

**Current (before the revamp):** takes comics from an Inbox folder or a drop; one button runs the chain (verified `.cbz`, junk removed, renamed
with the Renamer's settings, filed into a series folder in the Ready folder, original handled). The table shows
Becomes / Steps / Status (Ready, Duplicate, Exists, No series, Failed); flagged rows start unticked.

**Owner's suggestions:** better UX, segmented; list the unbuilt items as future work.

**Proposed design** (Inbox > Destination > Clean-up > Review > Run)
- *Header:* "Add to library" and one line: "Bring new comics in, checked, cleaned, named and filed."
- *Segments:*
  1. **Inbox**: drop box or inbox folder with `Library` and `Recent` beside it. Summary: "14 new comics in D:\Inbox".
     **Watch this folder** (a switch, off by default) replaces the old idea of a separate downloads watcher: while the app is
     open it checks the inbox every few seconds, waits for each file's size to stop changing, and adds new comics to the list
     for review. It never runs the chain by itself; the user still presses **Add N comics**. The watched folder is remembered.
  2. **Destination**: Ready folder, *File into series folders* (uses the Renamer's folder template). A read-only line states
     the naming rules, with a **Naming settings** link to the Renamer. Summary: "D:\Library · series folders · Renamer naming".
  3. **Clean-up**: plain toggles for convert CBR, remove junk, rename pages `001.jpg…`. *Advanced options*: extra junk
     patterns. **The original comic**: Delete it (after checks) / Move to Archive / Keep it, each stating the consequence.
  4. **Review**: scrollable table of comic, becomes, status; Steps shown as small icons. Flagged rows are grouped on top
     (Duplicate, Exists, No series), each with a count and a one-line fix: *Add anyway*, *Set series…*, *Skip*. Clicking a row
     shows its full final path under the table.
  5. **Run**: progress with time left, then a plain result with a **Details** button.
- *Fixing flagged rows:* **Set series…** edits everything: the file name, the series folder, and the comic's `ComicInfo.xml`
  series. Suggestions come from the local library only (same source as Metadata).
- *Footer:* main action **Add N comics**, then **Stop**, then **Open Ready folder**; secondary: **Retry failed**.
- *Links:* see *Links between tools*.

## ACEO sheets

**Current:** fills Letter pages of eight 3.5" x 2.5" cards with chosen covers and saves a print-ready PDF. Drop comics, folders
or images; first page is the cover (or the last page for a back cover). A cover list takes most of the page with a narrow
sheet preview at the right edge (Previous / Next, Full screen). Reorder with buttons, remove, clear, copies of each. Options
(Template, Covers, Cards, Output): fit mode, rotation, background, margin, card outlines (colour, thickness), 150/300/600 dpi,
custom template PDF. Summary line such as "10 covers = 10 cards on 2 sheets (6 empty slots)".

**Owner's suggestions:** revamp the preview pane; swap cards directly in the preview; show the number of empty slots on the
last sheet.

**Proposed design** (Covers > Cards > Preview and print spine)
- *Header:* "ACEO sheets" and one line: "Lay covers out as trading cards on printable sheets."
- *Segments:*
  1. **Covers**: drop box with `Library` and `Recent` beside it; cover list with sized thumbnails. Reordering uses the same
     multi-drag stacking as Reading order, plus ▲ ▼ Top Bottom and keys. A **Copies** stepper on each row. Per-cover switch
     **Use last page** (back cover) with both thumbnails shown. Summary: "10 covers · 2 sheets".
  2. **Cards**: fit, rotation, background and margin as small visual cards showing the effect on a sample cover (crop / fit /
     stretch, turned / not turned), not bare dropdowns. *Advanced options*: card outlines, outline colour and thickness,
     custom template PDF. Summary: "Fill and crop · outlines on".
  3. **Preview and print**: the revamped pane, now the centre of the page.
     - Large sheet view at print appearance, Previous / Next, and a **sheet strip** of small thumbnails underneath for quick
       jumps. Redraws live while options change (low resolution first, sharp when idle). **Full screen** stays (arrow keys, Esc).
     - **Swap cards in the preview:** click a card to select its cover in the list; drag one card onto another to swap them,
       including across sheets via the strip. A button alternative: select a card, then *Move to slot…*.
     - **Empty slots** are drawn as dashed cards. A hint above the sheet reads, for example, "Last sheet has 6 empty slots. Add
       6 more covers to fill it." The same count appears in the Covers summary.
     - Print quality (150 / 300 / 600 dpi) and *Open the PDF when done* sit here, with a hint to print at 100% scale.
- *Footer:* main action **Create PDF**; secondary: **Open PDF**, **Open folder**.
- *Links:* empty state links to Bulk folder and Single issue to get covers.

**As built (Session 66, step 9):** two columns. Left: **Covers**, a compact drop box and the card list (`CardList`, which learned to draw small pictures and buttons on a card: `images`, `image_on` and `buttons` in what `render` returns, `on_button`); each cover card has its front picture and, for a comic with more than one page, its back picture, a **Front / Back** switch, and a **− ×N +** stepper; the cover's pictures are made while it is read (the back at 360 px, the original of the last page only when the PDF or the full-screen view needs it). Right: **Preview and print** first (so it stays in view while you change the options) and **Cards** below it. The preview is a canvas: the sheet at print appearance with empty slots dashed (`compose_sheet(empty_style="dashed", marks=…)`), a quick low-resolution draw and the sharp one 180 ms later, ◀ ▶, **Full screen**, and a strip of every sheet (cached by what is on the sheet and the options). A click on a card selects its cover in the list; a drag onto another card swaps the two covers (they keep their own copies); holding the dragged card over a sheet in the strip switches to that sheet, so covers can be swapped across sheets. The option cards are `ChoiceCards` with a picture (`picture=(w, h)`, `set_picture`): `card_picture` draws one card with the cover fitted, turned, backed and inset the way that choice says. Differences from the plan: the global *Copies of each cover* option is gone (copies are per cover); there is no **Move to slot…** button (the owner removed *Move to position* from Reading order; the list's keys and buttons, and the swap, do the same job); *Image from each comic* is now "Covers you add next come from" under Advanced options, because each cover has its own switch; Preview and print is above Cards on the page.

## Renamer

**As built (Session 68, step 10):** two columns instead of the five-segment spine. Left: **Comics** and **Review**, where Review is a `CardList` (`reorder=False`: cards are selected, not moved) with a type chip and a green/amber/red dot on each card, unsure files first, a filter menu, Select all/none, **Set type** and single-letter keys. Right: **File** (the card with suggestions and reasons), **Detect** (with Saved rules under Advanced options), **Naming** and **Text and folders**. Footer: **Apply N renames**, **Export plan**, **Rescan folder**. The confidence logic is `rename_core.assess`; a decided type or a saved rule (keyed by `rename_core.shape`) is always green. Differences from the plan: the separate Card/List views are gone (the list is the card list; the card is the File block); files are never guessed silently, they sit in the needs-input group until a type is chosen or the tool is sure; undo stays out, as agreed.

**Current (before the revamp):** standardises names for CBZ, CBR, PDF and EPUB (subfolders optional). Each file is read from its name and
optionally `ComicInfo.xml`. Card view (one file) and list view (all). A file list with filters (needs attention, issues,
collected editions, edited by hand). Four settings tabs: Detect, Names, Text, Folders. Nothing changes until *Apply renames*.

**Owner's suggestions:** make it easier to set the comic's type by hand after the filename was read; prompt the user on any
ambiguity; add saved rules; suggest options for unresolved files and let the user decide; leave out undo for now.

**Proposed design** (Comics > Detect > Naming > Text and folders > Review spine)
- *Header:* "Renamer" and one line: "Give every comic a clean, consistent name."
- *Segments:*
  1. **Comics**: drop box with `Library` and `Recent` beside it, plus *Include subfolders*. Summary: "412 files · 31 need your
     input".
  2. **Detect**: what to read (filename, `ComicInfo.xml`) and how. *Advanced options*: year and volume rules, and **Saved
     rules**: the list of "treat names like this as TPB" decisions, with edit and delete.
  3. **Naming**: a template per type (Issue, Annual, Special, One-Shot, Volume, TPB, Hardcover, Omnibus, Compendium, Deluxe,
     Library, Epic Collection, Graphic Novel, Box Set, Collection) with presets, a live example and validation. *Advanced
     options*: full template syntax and format guide.
  4. **Text and folders**: number padding, capitalisation, leading "The", separators, illegal characters, extension case,
     maximum length; folder template, collected-editions subfolder, what to do when a name is taken.
  5. **Review**: card and list views with the file list and filters.
     - *Type chip:* every row shows its type as a chip with a confidence dot (green / amber / red). Clicking it opens a menu
       of all types, each with a one-line description and an example ("TPB: a collected edition, one volume").
     - *Needs your input:* files detection is unsure about are grouped at the top. Each shows ranked **suggestions** with the
       reason ("Contains 'Vol. 2' but only 24 pages") as buttons; the user picks one, or chooses another type. Nothing is
       guessed silently.
     - *Bulk:* select rows and set a type for all, or **Apply to similar files** (same pattern).
     - *Saved rules:* a choice offers "Always treat names like this as TPB". Saved rules apply on later runs and are managed in
       Detect > Advanced options > Saved rules.
     - *Keyboard:* in the card view, the type's first letter or number keys set the type and move to the next file.
     - Files still unresolved at apply time keep their current name; **Apply** renames the rest and says how many were left.
- *Footer:* main action **Apply N renames**; secondary: **Export plan**. (No undo for now.)
- *Links:* see *Links between tools*.

## Future work (all tools)

- **Undo** for Renamer (last rename) and Metadata (last save). Needs a backup or log of the old names and `ComicInfo.xml`;
  both tools use a confirmation instead for now.
- **Add to library:** place comics into the existing library by matching series; write fuller `ComicInfo.xml` data on the way
  in (beyond the series set by *Set series…*); accept PDF, EPUB and 7z (only `.cbz` and `.cbr` today).
- **Folder icons:** collage icon for parent folders (for example `DC`, from four series covers).
- **Folder browser** (roadmap item 6).
- **Reading order:** replace copies with links so no real duplicates exist (not decided).

## Links between tools

**Mechanism.** Links carry context: the target page opens with the files or filter already loaded, and shows a removable
chip such as "From Library audit · 38 CBR files" with a **Back** link. Each tool's result area has a **Next steps** row of one
to three contextual links. Empty states link to the tool that creates what is missing.

| From | To | Link |
|---|---|---|
| Library stats | Metadata | **Fix these** on each completeness row and each Needs attention card; opens pre-filtered |
| Library stats | Library audit | Needs attention cards for duplicates, gaps and broken files |
| Library stats | Reading orders list | Mark / unmark folders; shared with Audit and Reading order |
| Library stats | Bulk folder | "Save covers for this library" |
| Library audit | CBR to CBZ | **Convert in bulk** on the CBR chip, files preloaded |
| Library audit | Metadata | Rows with missing series or issue number |
| Library audit | Library stats | **View stats** after a rescan |
| Metadata | CBR to CBZ | Locked `.cbr` rows |
| Metadata | Renamer | After saving: "Rename these files to match" |
| Metadata | Library stats | **Back** after saving, refreshed |
| Renamer | Metadata | After applying: "Update metadata from the new names" |
| Renamer | Library audit | After applying: "Check the library for duplicates" |
| Add to library | Renamer | **Naming settings** (its rules apply here) |
| Add to library | Metadata | Comics flagged *No series* |
| Add to library | Library audit | After adding: duplicates |
| Reading order | Metadata | After stamping: "Check the story arc fields" |
| Reading order | Reading orders list | Mark the folder as a reading order |
| Bulk folder | Folder icons | After a run: "Make folder icons from these covers" |
| Bulk folder | ACEO sheets | "Put these covers on a sheet" |
| Single issue | Bulk folder | "Do the whole folder" |
| Single issue | ACEO sheets | "Add this cover to a sheet" |
| Folder icons | Bulk folder | When no covers exist yet |
| ACEO sheets | Bulk folder / Single issue | Empty state: "Get covers" |
| CBR to CBZ | Library audit | After converting: rescan |
| Reading order | Library audit / Library stats | After stamping: the reading-order folder is left out of their counts |
| Single issue / Bulk folder | Library stats | Empty state when no library folder is set |

**As built (Session 70, step 12).** `SegmentPage.show_next(links)` draws a **Next steps** row under the header (`clear_next()`; the app clears it when the page is left) and `SegmentPage.link(key, folder=…, paths=…)` makes a command that calls the app's `goto`, which opens that tool with the folder or files loaded and a chip "From <tool>" with a Back button. Built: Bulk folder to Folder icons and ACEO sheets (after a run); Single issue to Bulk folder and ACEO sheets (after saving a cover); Renamer to Metadata and Library audit (after applying); Metadata to Renamer (after saving); Reading order to Metadata (after writing); Add to library to Library audit and Metadata (after adding); CBR to CBZ to Library audit (after converting); ACEO's drop box has **Get covers…** (Bulk folder). The links from Library stats and Library audit (Fix these, Convert in bulk, Metadata) and **Naming settings** on Add to library were built earlier. Not built: Library stats links on the empty states of Single issue and Bulk folder, Reading order to Library audit / stats (they follow the reading-order marking, which is already shared), Add to library to Metadata for *No series* comics (Set series… fixes them on the card), Folder icons to Bulk folder (Folder icons reads the comics itself, so it needs no covers).

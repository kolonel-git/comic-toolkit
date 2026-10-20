# Reading Order

[< Docs index](README.md)

Part of the [roadmap](roadmap.md) (item 4). Found on Home under **Reading Orders**.

For a series or event (a crossover, a story arc) you open one page, put the issues in the order you want to read them, and the tool
records that order **inside each comic's `ComicInfo.xml`**, so no file has to be renamed. Optionally it also numbers the filenames, or
copies the issues into a new folder so the originals are never touched.

## Using it

The page is two columns with a divider you can drag. On the left, **Comics** (adding issues) and **Order** (the list); on the right, scrolling on its own, **Stamp** (how the order is recorded) and **Review** (what will happen). The footer holds the main button, **Stamp N comics**, with **Preview changes** and **Mark as reading order** beside it.

1. **Add issues:** drop comics or folders on the page (or anywhere on the window while the page is open), click the drop area to pick files,
   or use **Add folder…** (the app adds *Library folder* and *Recent* under it). **Open a reading order ▾** lists the folders you marked as reading orders and adds the comics of the one you choose. Folders are searched including subfolders, and issues can come from several folders. Duplicates and non-comics are ignored.
2. **Order them:** each comic is a card. Hold a card and drag it to move it. Click a card to select it, Ctrl+click to add or remove one, Shift+click to select
   a range, or drag a box from the space between or under the cards to select the ones it touches; then drag any selected card and they all move. They
   collapse into one stacked card with a count ("5 issues") that follows the pointer, a thick line shows where they will land, the list scrolls itself when
   you hold the pointer near its top or bottom edge, and on release the cards arrive together, in the order they had, and flash for a moment. Escape during
   a drag cancels it. Moving is never drag-only: ▲ ▼ move the selection one place at a time (so do **Alt+Up** and **Alt+Down**), **Top** and **Bottom** send it
   to the very start or end, the arrow keys, Home and End move the selection, Ctrl+A selects every card, and Space ticks the card. **Undo** (or **Ctrl+Z**)
   takes back the last moves, one at a time. **Suggest order ▾** sorts by series, volume, year and issue number (the filename parser; anything unparseable
   goes last), by publication date (ComicInfo year, month and day, else the year in the file name; undated issues last), by issue number, or by file name
   (numbers compare as numbers). Untick a card to leave that issue alone; it keeps its place in the numbering. Clicking a tick box while several cards are
   selected ticks or unticks all of them. **Remove** takes out every selected card.
3. **Name the order** (for example "Court of Owls") and choose how to record it. The table shows each issue's arc number, its new filename when
   prefixing is on, the arc it already has, and a status (*Add*, *Update*, *Replaces “old arc”*, *No change*, *Skipped*).
4. **Review** (on the right) says in plain words how many comics will be stamped, how many are already correct, unticked or cannot be stamped, and what happens to the originals. **Preview changes** (optional, or **Details** in the Review) opens a window listing, for every issue in order, the new filename and each field that would change from what it is now
   (for example `StoryArc: (none) -> Court of Owls`), plus unticked, unchanged and blocked issues and where originals or copies would go.
   It changes nothing and can be reopened after any edit.
5. **Stamp N comics.** A confirmation says what will happen, then each file is rewritten and verified.
6. **Marking.** When copies were made in a new folder, the page asks once whether to mark that folder as a reading order, which leaves it out of Library stats and the duplicate check (*Mark it*, *Always mark new ones* or *Not now*). **Mark as reading order** in the footer does the same for the folder of the last copies, or for the one folder that holds every listed issue.

Re-running renumbers the whole list from 1 (gaps closed), because positions are just metadata. A file already in a different arc is shown
as *Replaces “…”*; untick it to skip it.

## Options

| Option | Effect |
|---|---|
| **Record the order as** | *Story arc*: `StoryArc` (the name) and `StoryArcNumber` (the position). *Alternate series*: `AlternateSeries`, `AlternateNumber` and `AlternateCount` (name, position, total). *Both*. |
| **Arc numbers** | `1, 2, 3` or zero-padded `01, 02, 03` (width follows the total, minimum two digits). Padding is there in case YACReader sorts the arc number as text. |
| **Series group** | Optionally also sets `SeriesGroup` on every issue, e.g. the event name. |
| **Also number the filenames** | `01 - Name` or `[01] Name`, for browsing in Explorer, where metadata isn't visible. Off by default. Renumbering replaces the old prefix instead of stacking a new one. |
| **Remove issue numbers** | Also deletes the `Number` tag (the issue number) from every issue that has one. YACReader sorts by issue number before filename, so with the number gone it falls back to the filename, which the prefix has put in reading order. Off by default. Shown in the preview as `Number: 5 -> (removed)`; the preview warns if no filename prefix is on. |
| **Copy to a new folder instead of changing the originals** | Asks where each time, creates a folder named after the reading order, copies the issues into it (name collisions get `(1)`), and stamps only the copies. The last parent folder is remembered. Originals are not changed and no backup is needed. |
| **Original file** | For in-place writes: keep a `.bak` backup in `Archive`, or replace the file. |
| **Mark the folder of copies as a reading order** | Shown with *Copy to a new folder*. *Ask me* (the default), *Always mark it* or *Never*. |

`.cbr` files can't be written to and are shown as *Convert to CBZ first* (use CBR to CBZ).

## How YACReader treats it

- Importing `ComicInfo.xml` is **off by default**: turn it on in Settings > General, then update the library. A note on the page says so.
- YACReader 9.14+ shows **Story arc** and **Arc number** columns in the table view (right-click the header to enable them).
- `StoryArc` is stored and searched as one plain text string (no splitting on commas); sorting by Story arc groups alphabetically by arc name,
  so the arc number is what orders issues inside an arc. That is why an issue in two arcs can't be expressed: the tool replaces, or you skip.
- YACReader's own **Reading Lists** (stored in its `library.ydb`) are the native way to mix comics from several folders. This tool does not
  write to that database and does not export `.cbl` files, which YACReader doesn't support.
- There is no standard tag for an arc *count*, so only the *Alternate series* form carries a total.

## Filename prefixes elsewhere in the app

- The filename parser recognises `01 - Name` and `[01] Name` (two to four digits, followed by text) and ignores the number, so the
  Metadata and Renamer tools and the audit still see the real series and issue. A name like `100 - Bullets 05` would be misread as a prefix.
- The Renamer drops the prefix when it renames, unless **Keep the number at the start** (under *Reading-order numbers*) is on.

## Not built

- Cover thumbnails in the list (the table is text only).
- A saved order file, undo, read/unread tracking (YACReader does that), and `.cbl` export.
- Writing `.cbr` files, and any change to YACReader's database.

## Still to verify in the real YACReader

See [manual tests](manual-tests.md), section E: whether the arc number sorts numerically or as text (decides whether to default to zero-padding),
whether *Story arc* or *Alternate series* shows and sorts better, and that the arc appears for CBZ files after a library update.

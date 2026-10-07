# Reading Order

[< Docs index](README.md)

Part of the [roadmap](roadmap.md) (item 4). Found on Home under **Reading Orders**.

For a series or event (a crossover, a story arc) you open one window, put the issues in the order you want to read them, and the tool
records that order **inside each comic's `ComicInfo.xml`**, so no file has to be renamed. Optionally it also numbers the filenames, or
copies the issues into a new folder so the originals are never touched.

## Using it

1. **Add issues:** drop comics or folders on the page (or anywhere on the window while the page is open), click the drop area to pick files,
   or use **Add folder…**. Folders are searched including subfolders, and issues can come from several folders. Duplicates and non-comics are ignored.
2. **Order them:** select one row, or several with Ctrl+click and Shift+click, then drag them (they move as one block, keeping their order) or
   use ▲ ▼ to move the whole selection one place at a time, or **Top** and **Bottom** to send it to the very start or end of the list
   (the rows keep their order among themselves). A block already at the top or bottom stays put. **Suggest order** sorts by series,
   volume, year and issue number (the filename parser; anything unparseable goes last). Untick a row to leave that issue alone; it keeps its
   place in the numbering. Clicking a tick box while several rows are selected ticks or unticks all of them. **Remove** takes out every selected row.
3. **Name the order** (for example "Court of Owls") and choose how to record it. The table shows each issue's arc number, its new filename when
   prefixing is on, the arc it already has, and a status (*Add*, *Update*, *Replaces “old arc”*, *No change*, *Skipped*).
4. **Preview changes** (optional) opens a window listing, for every issue in order, the new filename and each field that would change from what it is now
   (for example `StoryArc: (none) -> Court of Owls`), plus unticked, unchanged and blocked issues and where originals or copies would go.
   It changes nothing and can be reopened after any edit.
5. **Write reading order.** A confirmation says what will happen, then each file is rewritten and verified.

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
| **Copy to a new folder instead** | Asks where each time, creates a folder named after the reading order, copies the issues into it (name collisions get `(1)`), and stamps only the copies. The last parent folder is remembered. Originals are not changed and no backup is needed. |
| **Original file** | For in-place writes: keep a `.bak` backup in `Archive`, or replace the file. |

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

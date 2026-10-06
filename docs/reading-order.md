# Reading Order (planned, not built)

[< Docs index](README.md)

Part of the [roadmap](roadmap.md) (item 4).

Its own group on the Home page ("Reading Orders"). For a series or event (e.g. a crossover) you open one window, put the issues
in the order you want to read them, and the tool records that order **inside each comic's `ComicInfo.xml`**, so no file has to be
renamed.

- **How the order is stored:** `StoryArc` (the reading order's name, e.g. "Court of Owls") and `StoryArcNumber` (the issue's
  position, 1, 2, 3, ...). These are standard `ComicInfo.xml` fields (Anansi Project schema) and are what readers use for reading
  orders. YACReader 9.14+ shows them in a **Story arc** column (right-click the table header to enable it) and lists the arc as
  "(number/count) name".
- **YACReader setup:** importing `ComicInfo.xml` is **off by default**: turn it on in Settings > General, then update the library.
  The table view has an **Arc number** column (confirmed on the user's install), so position within an arc can be shown and sorted.
- **YACReader behaviour to design around** (user research plus source/changelog review): `StoryArc` is stored and searched as one
  plain text string (no splitting on commas; search is a substring match); sorting by the Story arc column groups alphabetically by arc
  name, so the arc number column is what orders issues inside an arc. YACReader's own **Reading Lists** (stored in its `library.ydb`
  database, built by hand in the app) are the native way to mix comics from several folders; the tool does not write to that database.
- **Input:** one folder, or issues dragged in from several folders.
- **Window:** list with cover thumbnails; drag to reorder plus up/down buttons; **Suggest order** pre-sorts by series, issue number
  and year (using the existing filename parser); live preview of the arc name and number each row will get.
- **Reordering later:** re-running renumbers the whole arc (position 1...n, gaps closed), because positions are just metadata.
- **Issues already in another arc:** YACReader keeps `StoryArc` as one plain string and does not split comma-separated values, so the
  multi-arc form (`Arc A,Arc B`) would just display as one long name. Instead, the review table shows each issue's current arc and
  you choose per issue: replace it or skip it.
- **Shared engine:** reuses the Metadata tool's generic `ComicInfo.xml` field writer (roadmap item 1), its review-table pattern and the
  verified-write path, so it is mostly a new page and ordering window.
- **YACReader reminder:** after writing, update the library in YACReader (with ComicInfo import enabled) to see the new order.
- **Safety:** same as the Metadata tool: originals are kept in `Archive` (or replaced, your choice) and every write is verified.
  `.cbr` files can't be written to and are skipped (convert them first).
- **Fields YACReader lets you edit per issue** (user-supplied list): Series, Title; Issue number, Issue count, Volume; Story arc,
  Arc number, Arc count; Alternate series, Alt. number, Alt. count; Series Group, Genre. Most correspond to standard `ComicInfo.xml`
  tags (`Series`, `Title`, `Number`, `Count`, `Volume`, `StoryArc`, `StoryArcNumber`, `AlternateSeries`, `AlternateNumber`,
  `AlternateCount`, `SeriesGroup`, `Genre`). There is **no standard tag for Arc count**, so it may not import from `ComicInfo.xml`.
- **Where to store the order (to test at build time):** either *Story arc* (`StoryArc` + `StoryArcNumber`; no count) or *Alternate
  series* (`AlternateSeries` + `AlternateNumber` + `AlternateCount`, a complete name/position/total triple that YACReader also exposes).
  Test which one YACReader imports and shows best; the tool may offer both as a choice. `SeriesGroup` could additionally label an
  event or crossover.
- **Display strategy (decided, to be confirmed by testing at build time):** write the metadata always; offer the filename prefix as
  a first-class option. Test with real files in YACReader whether the arc number column sorts numerically or as text, then set the
  prefix default accordingly (metadata alone if sorting is numeric and reliable).
- **Optional extras (both off by default until tested):**
  - *Also gather copies:* copy the ordered issues into a new folder you name (parent location asked each time, last parent
    remembered) and stamp **only the copies**, so the originals are never modified.
  - *Filename prefix:* also number the filenames (`01 - `, `001 - `, `[01] ` ...; style, separator and padding chosen per run) for
    browsing in Explorer, where metadata isn't visible. The Renamer, Metadata and series detection would recognise and ignore this
    prefix, and the Renamer would strip it unless "keep reading-order number" is ticked.
- **Dropped from the original idea:** the `.cbl` reading-list export (YACReader does not support it), read/unread tracking (YACReader
  does that), a saved order file, undo.
- **To verify when built, in the real YACReader:** whether `StoryArcNumber` sorts numerically or as text (decides whether to
  zero-pad, e.g. `01`), where the "(n/count)" count comes from, and that the arc shows up for CBZ files after a library update.

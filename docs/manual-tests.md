# Manual tests

[< Docs index](README.md)

Checks that need a person: real comics, the real window, real RAR files, or YACReader. Scripted tests cover the logic; these cover what a
script can't see. Work on a **copy** of some comics, never your only copy. Tick each box and note anything odd in the Result line.

Setup used by most tests: make a folder `Test Library` with a copy of 6 to 10 real comics, including at least one `.cbr` that is a real
RAR, one issue that is a near-duplicate of another (same cover, different file), and a series with a gap in its numbering.

## A. Backups stored as `.bak` (roadmap item 0)

- [ ] **A1. Backup naming.** Metadata tool on `Test Library`, "Original file: Keep a backup", write metadata to one file.
  *Expect:* `Archive/<name>.cbz.bak` appears next to the file, the live `.cbz` is intact and opens.
  Result:
- [ ] **A2. Restore.** Move a `.bak` out of `Archive`, delete the `.bak` from its name, open it in YACReader or any zip tool.
  *Expect:* it opens as the original comic.
  Result:
- [ ] **A3. Second backup.** Write metadata to the same file again.
  *Expect:* a second backup named `<name>.cbz (1).bak`, no overwrite of the first.
  Result:
- [ ] **A4. CBR to CBZ.** CBR to CBZ tool, "Move to Archive folder".
  *Expect:* `Archive/<name>.cbr.bak`, a new verified `.cbz` beside where the `.cbr` was.
  Result:
- [ ] **A5. YACReader ignores `.bak` (the point of the change).** Put `Test Library` (with its `Archive` folders) in YACReader and run Update Library.
  *Expect:* each comic appears once; nothing from `Archive` is listed. If `.bak` files do appear, tell me, because the fix would need rethinking.
  Result:

## B. Metadata extensions (roadmap item 1)

Run these in the Metadata page (comics on the left, fields on the right). Section J covers the rest of that page.

- [ ] **B1. Count parsing.** Rename a copy to `Test 03 (of 12) (2020).cbz`, open the Metadata tool on its folder and select that comic.
  *Expect:* the **Issue count** field offers `12` as a suggestion (read from the file name), the Series suggestion is `Test`, Issue number `3`, Year `2020`. Try `(3 of 12)` and `[of 12]` too.
  Result:
- [ ] **B2. Count survives into the file.** Press the suggestion for Issue count, then **Review 1 change**, **Confirm and save**, and check `ComicInfo.xml` inside the CBZ (open the zip, read the file).
  *Expect:* `<Count>12</Count>` present.
  Result:
- [ ] **B3. Typing a value.** Click the comic, type `24` in Issue count.
  *Expect:* the field says "edited", the comic's row says Edited and the changes list shows Issue count becoming `24`; clearing the box back to the stored value removes the change.
  Result:
- [ ] **B4. Several at once.** Select two comics (Ctrl-click). Fill in Genre `Superhero, Crime` and press **Set for 2 comics**. Repeat for Series group, Alternate series and Publisher (under *Advanced options* where shown).
  *Expect:* a line in the status saying how many fields were set on how many comics, both comics show Edited, others are unchanged, and the changes list shows each field.
  Result:
- [ ] **B5. Nothing to set.** With several comics selected leave every box empty and press **Set for N comics**.
  *Expect:* a red "Fill in a field first"; nothing changes. **Discard edits** clears everything pending.
  Result:
- [ ] **B6. Nothing selected.** Select no comic.
  *Expect:* the right column says to select a comic on the left; nothing can be edited.
  Result:
- [ ] **B7. YACReader shows the fields.** Save, turn on ComicInfo import (Settings > General), Update Library, open the comic's info.
  *Expect:* Issue count, Series Group, Genre, Alternate series, Publisher match what you wrote.
  If any field is blank, note which. That tells me which tags YACReader does not read.
  Result:
- [ ] **B9. Removing the issue number.** Select a few comics (include one with no `ComicInfo.xml`), choose *Several at once*, open *Advanced options* and press **Remove issue number**, then save. Then update the YACReader library and sort the folder.
  *Expect:* the **#** column goes blank for the comics that had one and the changes list shows the number becoming "(removed)"; the confirmation note counts the values deleted; afterwards `ComicInfo.xml` has no `<Number>` but keeps its other fields, and YACReader sorts those comics by filename. **Tell me whether the sort really follows the filename.** Also try **Keep it again** before saving.
  Result:
- [ ] **B8. Layout.** Look at the Metadata page in light and dark mode, and at a narrow window.
  *Expect:* both columns readable, the reminder under the table visible, nothing clipped.
  Result:

## C. Shared library scan (roadmap item 2)

The scan has no window yet. It runs from a terminal in the project folder: `python library_scan.py "<path to Test Library>"`.

- [ ] **C1. Basic scan.** Run it with no options.
  *Expect:* a table with one line per comic (series, issue, year parsed from the name), a summary line, and no `Archive` files listed.
  Result:
- [ ] **C2. Deep scan.** Add `--deep`.
  *Expect:* page counts, a cover size like `1988x3056`, and a 16-character cover hash for each CBZ. The numbers match what you see opening the comic.
  Result:
- [ ] **C3. Cache.** Run the same command twice.
  *Expect:* the second summary says `0 read, N from cache` and is faster. Touch one comic (write metadata to it) and run again: exactly that one is re-read.
  Result:
- [ ] **C4. Cache is disposable.** Delete `%APPDATA%\ComicToolkit\cache.json` and run again.
  *Expect:* everything is re-read, results are identical, the file is recreated.
  Result:
- [ ] **C5. Real RAR files.** Run `--deep`, then `--deep --deep-cbr`.
  *Expect:* without `--deep-cbr` real `.cbr` files show no page count and no error (unknown). With it they show pages and a cover, slower. Needs 7-Zip or Windows `tar.exe`.
  Result:
- [ ] **C6. Broken files.** Add a renamed text file `Broken 01.cbz` and an empty zip.
  *Expect:* errors `Not a valid zip` and `No images found`; the scan finishes without crashing.
  Result:
- [ ] **C7. Duplicate covers.** Run `--deep --csv out.csv`, open the CSV in Excel, and compare `cover_hash` of your near-duplicate pair against two unrelated comics.
  *Expect:* the pair's hashes differ in only a few hex digits. Tell me how similar they look; this decides the duplicate threshold for the audit tool.
  Result:
- [ ] **C8. Speed on your real library.** Point it at a large folder (hundreds of files) with `--deep`, note the time, then run it again.
  *Expect:* the first run is acceptable for a one-off; the second is a few seconds. Report both times and the file count.
  Result:
- [ ] **C9. Odd names.** Include files with unusual characters (accents, `#`, brackets) in the name and a very deep subfolder.
  *Expect:* all are listed with sensible series and issue values; the CSV opens in Excel without garbled characters.
  Result:

## D. Library audit (roadmap item 3, revamped in Session 39)

Open **Library audit** from Home (or drop a folder on it). Use `Test Library` from the setup above, plus the extra files named in each test. Make a copy of the folder first: these tests fix and delete things.

- [ ] **D1. Scan.** Choose the folder, leave the defaults, press **Scan library**.
  *Expect:* a progress bar and "Scanning n of N" (also in the footer, whose button reads **Stop**), then "Done · N files in …s". The window stays responsive. Library folds to a one-line summary (the Checks stay in the right column) and the Findings show a strip of counts; the chips show counts; **All** excludes Warnings and Reading orders; switching chips is instant.
  Result:
- [ ] **D2. Broken files.** Add a text file renamed `Broken 01.cbz` and a truncated copy of a CBZ. Scan, then tick **Full integrity test** (Checks > *Advanced options*) and scan again.
  *Expect:* `Broken 01.cbz` is listed in both scans; the truncated file shows only with the full test (or as not a valid zip). Healthy comics are never listed.
  Result:
- [ ] **D3. Real RAR files.** With real `.cbr` files present, run the full integrity test with and without **Open real .cbr files**.
  *Expect:* without it, real RAR files are not tested; with it they are, and a healthy RAR is not listed under Broken. Needs 7-Zip or Windows `tar.exe`.
  Result:
- [ ] **D4. Duplicates.** Copy a comic into another folder and rename the copy slightly (add " (Digital)"). Also copy a TPB.
  *Expect:* the copy and the original are one group; the one with more pages or the taller cover is marked "best copy" with no tick box; the other is unticked. A single issue and the TPB it belongs to are not paired; two copies of the same TPB are.
  Result:
- [ ] **D5. Duplicates by cover.** Rename a copy completely, turn on **Compare cover images**, scan. Include two *different* issues of one series.
  *Expect:* the renamed copy is found as "Similar cover"; the two different issues are not paired. Try Strict, Normal and Loose and tell me which is right for your collection.
  Result:
- [ ] **D6. Missing, per type.** Use a series where you know what you own: some single issues, some TPB volumes, an omnibus.
  *Expect:* one row for the series reading like `Issues: #13, #27-#29 · TPB vols: 3, 5`; each format tracked on its own; annuals, specials and ranges not reported. Try **Expect issues from #1**. **Copy wishlist** and **Save wishlist…** (`.txt` and `.csv`) match what you see.
  Result:
- [ ] **D7. Junk and CBR fixes.** Make sure some CBZ files hold Thumbs.db or `.nfo`, and some `.cbr` files exist. Look at the Junk and CBR chips, then press the footer's **Fix N checked** on each.
  *Expect:* both start ticked; the confirmation lists what will happen and only covers the chip you are on (its **Details** button lists each file and says whether it can be undone); afterwards the files are clean / converted (the `.cbr` is gone once its `.cbz` exists), the list rescans, and a comic still opens in your reader.
  Result:
- [ ] **D8. Archive a duplicate.** On Duplicates, tick the extra copy, **Fix N checked**, confirm.
  *Expect:* the file moves to `Archive/<name>.bak` next to where it was; the group disappears; declining changes nothing; the kept copy cannot be ticked.
  Result:
- [ ] **D9. Ignore.** Select a Missing row and press **Ignore**; rescan; open **Ignored…**.
  *Expect:* the row stays hidden after the rescan and after restarting the app; **Ignored…** lists it and **Restore selected** brings it back.
  Result:
- [ ] **D10. Warnings.** Open the Warnings chip and change the limits.
  *Expect:* very short books, tiny or huge files and low-resolution covers are flagged; the list changes as soon as you edit a limit. Tell me if the defaults (10 to 300 pages, 1 MB to 500 MB, 800 px) flag too much or too little.
  Result:
- [ ] **D11. Archive manager.** Press **Archive…** after a few fixes.
  *Expect:* the `.bak` files with sizes and a total; ticking some and pressing **Purge ticked…** deletes them after a confirmation; empty Archive folders disappear.
  Result:
- [ ] **D12. Stop and cache.** Scan a large folder with **Full integrity test** on and press **Stop** part-way; then scan again without it.
  *Expect:* Stop ends the scan quickly with "Stopped" and a "(partial …)" note; a later scan of unchanged files is much faster ("from cache").
  Result:
- [ ] **D13. Look and feel.** View the page in light and dark mode, with the window narrow, and with hundreds of rows.
  *Expect:* the table is readable in both themes, the footer buttons are not clipped, scrolling is smooth. Switching theme while results are shown keeps them.
  Result:
- [ ] **D14. Details panel.** After a scan press **Details**. Press **Show in list** on a kind, then reopen it and try **Convert in bulk** (needs `.cbr` files), **Mark reading orders** and, if some comics have no series or issue number, **Comics with no series**.
  *Expect:* the panel covers the right half of the page down to the footer and says what was scanned, which checks ran and what was left out; each button either selects that list or opens the right tool on this folder (Metadata already filtered, with a "From Library audit" chip and a Back button). Tell me if the wording or the half-page size is wrong for your screen.
  Result:
- [ ] **D15. Reading orders.** In Library stats mark a folder of reading-order copies (for example `01 - Name`), then audit the library.
  *Expect:* the copies are not listed under Duplicates; a **Reading orders** chip lists the folder with how many of its comics also exist elsewhere; turning on **Include reading orders in duplicates** and rescanning pairs them, with the original outside the folder kept.
  Result:
- [ ] **D16. Checks and folding.** Switch a check off (for example Junk files), then open Library again.
  *Expect:* the kind disappears from the strip, chips, list and the fix count at once; Library stays folded after a rescan until you open it yourself, and the first scan of a new folder folds it again.
  Result:

## E. Reading order (roadmap item 4)

Use copies of real issues from at least two series (6 to 10 files) plus one `.cbr`. Open **Reading order** from Home.

- [ ] **E1. Adding.** Drop a folder, then drop two loose files from another folder, then use **Add folder…** and the drop-area click.
  *Expect:* every comic appears once, in a sensible order; adding the same file again does nothing ("Nothing new to add"); a text file is ignored; the `.cbr` shows "Convert to CBZ first" in red.
  Result:
- [ ] **E2. Ordering.** Click **Suggest order**, then drag a row to a new place, then use ▲ ▼ on a selected row. Untick one row.
  *Expect:* suggest groups by series then issue number; dragging and the arrows renumber the **#** column instantly; the unticked row shows "Skipped" but keeps its number.
- [ ] **E2b. Moving several at once.** Select 5 rows (click the first, Shift+click the fifth; also try Ctrl+click for a scattered selection), drag them to another place, and use ▲ ▼, **Top** and **Bottom** with the selection. Click a tick box while several are selected. Click one selected row without dragging. Press **Remove** with several selected.
  *Expect:* the whole selection moves as one block in its existing order and stays highlighted; at the top or bottom the block stops; Top and Bottom send the whole selection (even scattered rows) to the very start or end, keeping their order; the tick box ticks or unticks all selected rows; a plain click on one of several selected rows leaves just that row selected; Remove deletes them all; numbers update after every change. Tell me if dragging feels jumpy or picks the wrong drop position.
  Result:
- [ ] **E2c. Preview changes.** With a name entered, press **Preview changes** (try in-place, with a filename prefix, in copy mode, with an unticked row and with a `.cbr`).
  *Expect:* a window lists each issue in order with its new filename and each changed field (old -> new), marks unticked and blocked issues, says whether originals are backed up, replaced or copied, and nothing on disk changes (compare the folder before and after). After writing, a new preview says the issues are already correct.
  Result:
  Result:
- [ ] **E3. Writing metadata.** Name the order, choose **Story arc**, write. Open one result in a zip tool and read `ComicInfo.xml`.
  *Expect:* `<StoryArc>` is the name and `<StoryArcNumber>` is the position; other fields are intact; a `.bak` of the original is in `Archive`; the table shows "Written".
  Result:
- [ ] **E4. YACReader, story arc.** Enable ComicInfo import (Settings > General), update the library, turn on the **Story arc** and **Arc number** columns, and sort by Arc number.
  *Expect:* the arc name shows on every issue and the issues sort in your order. **Report whether it sorts 1, 2, 10 correctly or as text (1, 10, 2).** If as text, tell me and I will default to zero-padded numbers.
  Result:
- [ ] **E5. YACReader, alternate series.** Re-write the same list choosing **Alternate series** (or **Both**), update the library.
  *Expect:* the alternate series, its number and its count appear. Tell me which of the two reads better in YACReader for finding "what's next".
  Result:
- [ ] **E6. Renumbering.** Move one issue, write again.
  *Expect:* all numbers update (1 to n); with a filename prefix on, each file is renamed with the new number and prefixes never stack (`02 - 01 - Name` must not happen).
  Result:
- [ ] **E7. Filename prefix.** Choose `01 - Name`, then `[01] Name`, write, and look in Explorer.
  *Expect:* files sort in reading order by name; the confirmation said how many would be renamed; the issue still shows correctly in the Metadata and Library audit tools (prefix ignored).
  Result:
- [ ] **E8. Existing arc.** Include an issue that already has a different story arc (write one with the tool first).
  *Expect:* status "Replaces “old name”"; unticking it leaves its arc untouched; ticking it overwrites it.
  Result:
- [ ] **E9. Copy mode.** Switch on **Copy to a new folder instead**, write, and pick a destination.
  *Expect:* a folder named after the order appears there with prefixed, stamped copies; the originals are byte-for-byte unchanged and no `Archive` folder was created for them; the next time the dialog opens in the same parent.
  Result:
- [ ] **E10. Renamer interaction.** Run the Renamer on a folder of prefixed files with and without **Keep the number at the start**.
  *Expect:* off, the prefix disappears; on, `01 - ` stays in front of the new name.
  Result:
- [ ] **E11. Name collision and a bad file.** Put a file named like the target (`01 - Name.cbz`) in the folder first, and delete one listed file before writing.
  *Expect:* the collision is reported ("already exists so the file was not renamed") with the metadata still written; the deleted file reports "File not found"; the rest are written and the page recovers.
  Result:
- [ ] **E13. Remove issue numbers.** Switch on **Remove issue numbers** with the `01 - Name` prefix, preview, then write. Update the YACReader library.
  *Expect:* the preview shows `Number: n -> (removed)` for each issue and a warning if the prefix is off; afterwards the comics sort in reading order by filename in YACReader. **Tell me if YACReader still sorts them by issue.**
  Result:
- [ ] **E12. Look and feel.** Light and dark mode, narrow window, 100+ rows.
  *Expect:* readable, no clipping of the Status column, drag stays smooth, the side panel scrolls to every option.
  Result:

- [ ] **E10. The page layout.** Open Reading order, add a folder, drag the divider, and make the window narrow and wide.
  *Expect:* the drop box and the list on the left, Stamp and Review on the right (scrolling on their own); the footer reads **Stamp N comics** with **Preview changes** and **Mark as reading order** beside it; nothing is cut off that you cannot reach.
  Result:
- [ ] **E11. Marking.** Stamp copies into a new folder. In the question that follows try *Not now*, then *Mark it*, then *Always mark new ones*; afterwards open Library stats.
  *Expect:* a marked folder is left out of the stats and the duplicate check, **Open a reading order ▾** lists it and adds its comics, and the Advanced setting shows *Always mark it* after the last choice.
  Result:
- [ ] **E12. Mark as reading order.** Open one folder that holds an existing reading order (for example `01 - Name` copies) and press **Mark as reading order**.
  *Expect:* a question naming the folder; after *Yes* the folder is marked (Library stats lists it under Reading orders).
  Result:

- [ ] **E13. Dragging cards.** Add 20 or more issues. Hold one card and drag it to a new place; then select five (Ctrl+click, Shift+click, or drag a box from the space between or under the cards) and drag any one of them.
  *Expect:* a single card moves as it is; five collapse into one stacked card with "5 issues" that follows the pointer, a thick line shows where they will land, the list scrolls when you hold the pointer near its top or bottom edge, and on release they arrive together in their old order and flash. Escape during the drag puts nothing in motion. A click on one of several selected cards selects just that card.
  Result:
- [ ] **E14. Keys and buttons.** With cards selected, try ▲ ▼ Top Bottom, Alt+Up, Alt+Down, the arrow keys with and without Shift, Home, End, Ctrl+A, Space on a card, then **Undo** and Ctrl+Z several times.
  *Expect:* the block moves as one and keeps its order; the arrow keys move and extend the selection; Space ticks the card; each Undo takes back one move, and the button is greyed when there is nothing to take back or after issues are added or removed.
  Result:
- [ ] **E15. Suggest order.** Open **Suggest order ▾** and try each of the four ways, then Undo.
  *Expect:* the list is sorted as the entry says (publication date uses ComicInfo year, month and day, then the year in the name; issues without one go last), and the status line says how.
  Result:
- [ ] **E16. Look.** Drag in light and dark mode and with a narrow left column.
  *Expect:* the card, the line and the tint are visible in both modes and the cards are not cramped in a narrow window. Tell me what feels wrong.
  Result:

## F. Renamer: cards, formats and messy folders

*The page was rebuilt in Session 68: where a test below says Cards or List, use the card list on the left and the File block on the right.*

Make a deliberately messy folder of copies: single issues, TPBs, hardcovers, omnibuses, compendiums, a `.cbr`, a `.pdf`, an `.epub`, `scan0001.cbz`, names written in
different styles (`Saga Vol 1 TPB (2012)`, `saga_vol_2_tpb`, `Walking Dead, The Compendium 2`, `Batman #1-12 (Collected)`, `X-Men Epic Collection v12 - Title`), and the cases that
used to go wrong: `Batman 001 (Oct 2016)`, `Batman 001 (2016, DC)`, `Wolverine v2016 003`, and a CBZ whose `ComicInfo.xml` has `Volume` set to a year.

- [ ] **F1. Years.** Open the folder and look at the New name of each year case above.
  *Expect:* every year is found (`(Oct 2016)`, `(2016, DC)`, `(2016-10-05)`, `(2016-2017)`), and no name contains `v2016` or a year as a volume. Send me any year it still misses, with the exact name.
  Result:
- [ ] **F2. Cards.** In **Cards**, step through files with Previous / Next and by clicking the file list. On a card change Series, Issue, Year, Title and Type.
  *Expect:* the New name and "Goes to" update as you type, the status chip changes, the file list row follows, **Reset this card** puts it back, typing in New name sets a name by hand and **Automatic name** undoes it, and the **Rename** switch skips the file. Nothing on disk changes yet.
  Result:
- [ ] **F3. List and filters.** Switch to **List**, double-click a name, a Type and a Current name; use the card filters (Needs attention, Issues, Collected editions, Edited by hand).
  *Expect:* the name edits in place, the Type menu appears, the current-name double-click opens its card, and each filter shows the right files with sensible Previous / Next.
  Result:
- [ ] **F4. Detection.** Read the Type of every file (Names are in the card header and the list).
  *Expect:* issues say Issue, annuals Annual, and TPBs, hardcovers, omnibuses, compendiums, deluxe and library editions, epic collections, graphic novels, box sets and ranges show their format. Tell me any file the tool gets wrong.
  Result:
- [ ] **F5. A format per type.** In **Names**, pick TPB and change its template, then Issue, then Annual; try a preset, **Copy this template to**, an invalid template (missing `]` or `}`, an unknown `{token}`), and tokens such as `{issue:4}`, `{series:upper}`, `{issue|volume}`, `\[{year}\]`, `{publisher}` and `{tags}`.
  *Expect:* only files of that type change, validation messages appear for the bad templates, the example under the box matches the card, and the Format guide lists every token and option. Tell me any token or formatting option you wish existed.
  Result:
- [ ] **F6. Text options.** In **Text** try each option: padding, capitalisation, leading “The”, separator, illegal characters, extension case and maximum length.
  *Expect:* every option visibly changes the names it should, and a non-number in Maximum length is ignored.
  Result:
- [ ] **F7. Folders and conflicts.** In **Folders** switch on **Move into folders**; try each folder preset, a custom template such as `{publisher}/{series}`, the collected subfolder (rename it, or empty it), and both conflict choices with `Saga 003` plus `Saga Vol 3` present.
  *Expect:* folders match the template (nested with `/`), `The Walking Dead` and `Walking Dead` share a folder, a TPB never makes `Saga v1`, and *Add a number* gives `Name (2)` instead of flagging the second file.
  Result:
- [ ] **F8. Apply and repeat.** Apply, then rescan.
  *Expect:* only ticked, Ready (or Numbered) files change, no file is lost or overwritten, PDF/EPUB/CBR rename too, and a second scan shows nothing left to rename.
  Result:
- [ ] **F9. Real library sample.** Point the Renamer at 100+ files from your real, untidy library and use Cards with the *Needs attention* filter.
  *Expect:* few wrong types, years or series; send me the names it gets wrong so detection can be improved. Also tell me whether the card layout is comfortable at your window size and in light mode.
  Result:
- [ ] **F10. Dots and suggestions.** Add a folder with `Berserk Vol 3.cbz`, a 300-page `Saga 001.cbz` that is really a book, and `Hellboy.cbz` with no number. Look at the dots and click each file.
  *Expect:* the unsure files are listed first with amber or red dots; each card offers suggestions with a reason (page count, “Vol”, no issue number); picking one turns the dot green and updates the new name.
  Result:
- [ ] **F11. Set type and saved rules.** Select several files and use **Set type**, then press a letter (T, then 0). On one card turn on *Always treat names like this as …*, press **Apply to similar**, then look under Detect > Advanced options > Saved rules and delete the rule.
  *Expect:* the chosen type is applied to all selected files; the letter keys work; similar names follow the rule and turn green; deleting the rule returns them to their detected type.
  Result:
- [ ] **F12. Export plan.** Press **Export plan**.
  *Expect:* a file listing each planned rename (old name, new name, folder) is written where you choose; nothing in the folder changes.
  Result:

## Folder icons (Windows)

- [ ] **N1. Choose and compare.** Open Folder icons on a library with a few series folders. Look at the table and the three style cards, press **Try another folder**, and click each style, then a few colours, the cover size and the series name under Advanced options.
  *Expect:* every row shows a picture of the icon it would get; the big picture and the style cards use the example folder's own cover and follow your choices; nothing is written yet.
  Result:
- [ ] **N2. Make the icons.** Press **Make N icons**, then open the library in Explorer (large icons) and press **Refresh Explorer** if a folder still shows its old picture.
  *Expect:* each folder shows its icon in the chosen style (the folder with the cover sticking out of the pocket, the folder with the cover as its face, or the flat cover); `folder.jpg` is beside it; the result lists every folder.
  Result:
- [ ] **N3. Already have one.** Make the icons again with *If a folder already has one* on Replace and on Skip.
  *Expect:* the table says "Has one: replaced" or "Has one: kept" before you press the button, and the run does what it said.
  Result:
- [ ] **N4. An image of your own.** Select a row and press **Use a different image…**, then with nothing selected choose a parent folder with no comics (such as `DC`) and an image.
  *Expect:* the row says "Your image" and "Custom image" and its picture changes; the parent folder gets a row and an icon; **Use the cover again** takes the image back.
  Result:
- [ ] **N5. Remove icons.** Press **Remove icons** and confirm.
  *Expect:* the question names how many folders; afterwards they show the ordinary folder icon (after a refresh), `folder.jpg` is still there, and a folder whose icon some other program set is left alone.
  Result:

## G. ACEO sheets

Use 10 to 20 real comics (plus one loose cover image), the bundled `ACEO - Full Page BLANK.pdf`, and a printer or a PDF viewer with a ruler.

- [ ] **G1. Adding and ordering.** Drop a folder of comics, then a loose `.jpg`, then add the same folder again. Hold a cover and drag it to a new place, select several (Ctrl+click, Shift+click) and drag them, use ▲ ▼ Top Bottom, Alt+Up / Alt+Down and Undo, remove one, and look at the "Sheet · card" line on each cover.
  *Expect:* every comic gives one cover, a comic that can't be read is skipped with a message, repeated adds don't duplicate, the numbers and sheet positions follow your order, and the preview changes with them.
  Result:
- [ ] **G1b. Layout and full screen.** Look at the page at your usual window size, drag the divider, then press **Full screen** on the preview.
  *Expect:* the covers on the left with their pictures and buttons, the preview, the strip of sheets and the option pictures on the right (scrolling on their own); the whole sheet is shown with nothing cut off, and **Full screen** fills the screen with a much larger sheet (arrow keys change sheet, Esc closes).
  Result:
- [ ] **G1c. Copies, front and back.** On a few covers press **+** and **−**, and on a comic press **Front / Back**.
  *Expect:* the count and the "Sheet · card" range change, the empty-slot note and the sheet count follow, the picture in use is outlined, and the preview and the PDF use that page. A loose image has no Front / Back switch.
  Result:
- [ ] **G1d. Swapping in the preview.** Click a card in the preview, then drag one card onto another, and hold a dragged card over another sheet in the strip before dropping it.
  *Expect:* the click selects that cover in the list; the drop swaps the two covers (also across sheets); Undo puts them back; dropping on an empty slot does nothing.
  Result:
- [ ] **G2. The PDF.** Press **Create PDF** with the defaults and open the result.
  *Expect:* a Letter PDF with 8 cards per page in the template's slots, the covers filling their cards (turned so the top is on the left), outlines drawn, and the last page blank where covers ran out. Tell me if the cards sit in the wrong place, are cropped too much or look soft.
  Result:
- [ ] **G3. Size on paper.** Print one sheet at 100% (no scaling to fit) and measure a card.
  *Expect:* each card is 3.5" × 2.5" (88.9 × 63.5 mm) and the outlines line up with where you will cut. Tell me if anything is off.
  Result:
- [ ] **G4. Options.** Click each picture under **Cards**: every fit, turning, background colour and margin; then under Advanced options turn the outlines off, try each **Outline colour** (automatic should give white lines on black), a custom `#FF8800` and a thickness of 2 or more, and type a bad colour such as `#12`.
  *Expect:* each picture shows what its choice does on your first cover, the sheet preview and the PDF do the same, and a bad colour is called out and the automatic colour is used instead.
  Result:
- [ ] **G5. Quality and size.** Create a Draft, Standard and High PDF of 3 sheets and compare them.
  *Expect:* Draft is small and acceptable on screen, Standard looks sharp in print, High is sharper but large (and slower); note the file sizes and times for me.
  Result:
- [ ] **G6. Back covers and images.** Set **Covers you add next come from** (under Advanced options) to the last page and add comics, then use a cover's **Front / Back** switch, and add loose cover images (jpg, png, webp).
  *Expect:* the back pages or images appear on the cards instead.
  Result:
- [ ] **G7. A different template.** Choose another PDF template (or one you edit), then **Use the bundled one**.
  *Expect:* the slot count and size shown for the template match it, the preview and PDF use it, and a PDF with no rectangles is rejected with a clear message.
  Result:
- [ ] **G8. Stop.** Create a High-quality PDF of many sheets and press **Stop**.
  *Expect:* it stops quickly, says no file was written, and leaves no partial PDF.
  Result:

## H. Layout: resizing, grouped buttons, adding comics

- [ ] **H1. Sidebar.** Drag the thin divider at the right edge of the sidebar, then close and reopen the app.
  *Expect:* the sidebar gets wider and narrower (limits about 150 to 360), the cursor changes over the divider, and the width is remembered.
  Result:
- [ ] **H2. Options panel.** On a few pages, drag the divider at the left edge of the right-hand options panel, including at a high display scaling (125% or 150%).
  *Expect:* the panel follows the mouse exactly, stops at a sensible minimum and maximum, nothing in it is clipped, and the width is remembered per page.
  Result:
- [ ] **H3. Columns.** On the Renamer list, Metadata, Reading order, ACEO, Audit and the Renamer's file list, drag the edge of several headings to make columns much narrower and wider; widen past the table and use the scrollbar under it.
  *Expect:* every column, including the tick-box and number columns, resizes; text in a narrow column is cut off cleanly; the horizontal scrollbar appears and works; ticking, dragging rows (Reading order) and double-click editing still work afterwards.
  Result:
- [ ] **H4. Panes inside a page.** In the Renamer's Cards view drag the divider between the file list and the card; in ACEO drag the divider between the cover list and the preview (then look at the preview and press Full screen).
  *Expect:* both resize smoothly; the ACEO preview redraws to fit its new width and still shows the whole sheet.
  Result:
- [ ] **H5. Grouped buttons.** Look at the button rows on Reading order, ACEO, Metadata and the Renamer, and the footers of Bulk folder, CBR to CBZ and Library audit, in light and dark mode.
  *Expect:* related buttons sit together with a thin divider between groups (Reading order: Suggest order | Top ▲ ▼ Bottom | Remove Clear), nothing is clipped, and the dividers are visible in both themes. Tell me if a grouping feels wrong.
  Result:
- [ ] **H6. Add folder / Choose comics.** On every page, use **Add folder…** and **Choose comics…** in the box at the top (on Single issue the folder button should open Bulk folder).
  *Expect:* the folder button behaves like dropping a folder; Choose comics opens a file picker and the page works on just the files chosen (the summary says "N chosen"); picking a folder afterwards goes back to the whole folder. On Library audit the duplicates and gaps cover only the chosen comics.
  Result:
- [ ] **H7. Choose comics, real files.** Choose a handful of comics from different subfolders in the Renamer and Metadata, then apply a rename and a metadata write.
  *Expect:* only the chosen files change; their names in the table are relative to the folder they share; Rescan reads the same chosen files.
  Result:

- [ ] **H8. Home.** Open Home at your usual window size, then resize the window and the sidebar.
  *Expect:* all ten tools are visible without scrolling, the cards in each row are the same width, the rows are soft bands with the group names in small capitals and a hairline between groups, the gap between groups is clearly larger than between cards of one group, the arrow on a card turns blue on hover, and the text in the cards is not cut off. Tell me if any description is clipped or a card looks too small to read.
  Result:
- [ ] **H9. Options panels.** Open each page and read its options panel from top to bottom, in light and dark mode.
  *Expect:* every panel runs Source (or the tool's main subject) then its own groups then Output; related options sit together, nothing is out of place, and the panels look like one family. Tell me about any option you would expect somewhere else.
  Result:
- [ ] **H10. Single issue buttons.** Open Single issue.
  *Expect:* the folder button (Open folder in Bulk…) is to the right of Choose comic….
  Result:
- [ ] **H11. Pick pages.** Load a TPB or compendium (hundreds of pages) in Single issue and press the **Browse all N pages…** tile.
  *Expect:* the window opens straight away and thumbnails fill in (the ones on screen first) without freezing; the size slider resizes the grid; click, shift-click and a dragged box pick pages; double-click shows a page full screen (click picks, wheel turns pages or scrolls when zoomed, Ctrl+wheel zooms, drag moves, arrows move, Space picks, Esc closes); likely covers have an orange outline; the **Numbering** switch (in the order picked, or by page number) and **Arrange…** change the numbering; **Extract as JPG…** asks for a folder and saves `<name> 1.jpg`, `2.jpg`… in the order shown; **Open folder** opens it. Tell me how many real covers the orange outline misses or wrongly marks.
  Result:

- [ ] **H12. Add to library.** Put 5 to 10 new comics (a mix of `.cbr` and `.cbz`, one with junk files, one named oddly, one you already own) in a test inbox. In Add to library choose the inbox and an empty Ready folder, press *Scan inbox*.
  *Expect:* every card shows the right new name and folder, the one you already own is flagged *Duplicate* or *Exists* and unticked and listed first, the oddly named one is *No series*. Press **Add N comics** and accept the prompt: the Ready folder gets verified `.cbz` files, the originals are gone (with the default), empty inbox folders are removed, and the status line says how many were added. Open one in your reader. Tell me about any name that is wrong and any duplicate that was missed.
  Result:
- [ ] **H12b. Fixing flagged comics.** On the *No series* card press **Set series…** and type a series; on the duplicate press **Add anyway**, then **Skip**.
  *Expect:* the series card gets a new name and series folder and turns Ready; after adding, its `ComicInfo.xml` (open it in your reader or the Metadata page) has that series; *Add anyway* ticks the card and *Skip* unticks it.
  Result:
- [ ] **H12c. Watch, Stop and Retry.** Turn on **Watch this folder**, then copy a large comic into the inbox. Add a few comics and press **Stop** during the run; make one comic unreadable and use **Retry N failed**.
  *Expect:* the comic appears in the list a few seconds after the copy finishes (not while it is still growing) and is not added by itself; Stop ends after the comic in hand; Retry only runs the failed one. After restarting the app the switch keeps its setting.
  Result:

- [ ] **H13. Sidebar sections.** Shrink the window height until the sidebar is full. Scroll the sidebar with the mouse wheel. Click a section heading, then click it again. Press **Reorder sections…**, move a few headings with Up and Down, press Reset.
  *Expect:* the tool list scrolls while Home, Library stats, Reorder sections… and Dark mode stay put; a heading folds and unfolds its tools (▸ / ▾) and the tool you are on stays highlighted; the sidebar and Home both follow the new order at once, Home still shows every tool without scrolling, and the order and folded sections are still there after you close and reopen the app.
  Result:

## I. Library stats and the Home summary line

Use your real library (hundreds of comics if you can) for I1 to I3 and I6.

- [ ] **I1. First scan from Home.** With no saved numbers (delete `stats_snapshot` and the `stats` entry from `settings.json`, or start on a fresh copy), open Home and click *Choose your library folder and scan it*.
  *Expect:* a folder dialog, then the line counts up ("Scanning your library… n of N") while the window stays responsive, then shows comics, series, size and "scanned just now" with a large Open Stats button and a small refresh icon (↻) to its right. Tell me how long a scan of your library takes, and again after pressing Refresh (it should be much quicker).
  Result:
- [ ] **I2. The numbers.** Open Library stats and compare the tiles with what you know (Explorer's folder size, a count of files, a series you know the issue count of).
  *Expect:* comics, size on disk and the series bar for a known series match; `Archive` folders are not counted; a real `.cbr` is counted. Tell me anything that is off.
  Result:
- [ ] **I3. Charts.** Look at the series, publisher, year, format and metadata bars in light and dark mode; resize the window and the options panel.
  *Expect:* labels, bars and values are readable and not clipped, bars redraw to the new width, the hover highlight follows the mouse and the pointer becomes a hand on clickable bars, and the Show every bar, Split series into volumes and Group years into decades switches each change the charts at once. Tell me if the page feels long, cramped or confusing.
  Result:
- [ ] **I4. Drill-down.** Click a bar in each chart; click another bar; press Open folder and Close.
  *Expect:* a table of that bar's comics opens right under the chart, the clicked bar stays highlighted, clicking a bar in another chart moves the table there, Open folder opens the folder of the selected (or first) comic, Close hides it. The metadata-coverage bars are not clickable.
  Result:
- [ ] **I5. Export.** Export CSV for each section, open one in Excel; press Copy summary and paste it into Notepad.
  *Expect:* the CSV has the section's rows with sensible headings and opens without garbled characters; the summary is short and correct.
  Result:
- [ ] **I6. Page counts and a changed library.** Turn on Read page counts and rescan; then add, remove or rename a few comics and rescan, and press Refresh on Home.
  *Expect:* the Pages tile shows a total; the numbers follow your changes; Home's line updates ("scanned just now").
  Result:
- [ ] **I9. Folder strip.** Open Library stats.
  *Expect:* the library folder is a slim strip right under the title (path in small text, a Change… button), not a big box; Change… picks a folder and scans it; dropping a folder on the page does the same; a very long path shows its end.
  Result:
- [ ] **I7. Restart.** Close and reopen the app.
  *Expect:* Home shows the last numbers straight away (without scanning), and the Stats page remembers the folder and switches. Tell me if the numbers look stale in a way that confuses you.
  Result:
- [ ] **I8. Publisher and metadata.** Use the Metadata tool to set Publisher on a few series, rescan, and look at the publisher and coverage bars.
  *Expect:* the publisher bar grows from *Unknown*, and "Have a publisher" and "Have ComicInfo.xml" go up. (Real RAR files stay out of the ComicInfo.xml figure.)
  Result:

## J. Metadata repair editor

- [ ] **J1. Open from Library stats.** Scan a library, then on a Health row with something missing press **Fix these** (and a Needs attention card's **Fix metadata**).
  *Expect:* the Metadata page opens on the library, already showing only the comics that lack that field, with a chip "From Library stats · No publisher" and **Back to Library stats** / **Show all comics** buttons.
  Result:
- [ ] **J2. One comic.** Click one comic. Type a publisher, then press a suggestion button on another field.
  *Expect:* the right column shows the cover and the comic's place in the list straight away (no card to choose first); the field you changed says "edited"; the table row says Edited; scrolling down the right column shows the change in the list under the fields, and the footer count updates; a publisher offers to apply to the rest of the series. Also check the two columns look right at your window size: nothing clipped, the list tall enough, the fields readable.
  Result:
- [ ] **J3. Many comics.** Select several (Ctrl-click or Shift-click), fill in a genre and a volume, press **Set for N comics**, then **Fill blanks from file names**.
  *Expect:* only the fields you filled change; empty fields keep each comic's own value; with *Automatic* the form switched by itself (one comic gives the one-comic form, several give the many form). Try *One at a time* and *Several at once* with one and with several comics selected: the chosen way wins.
  Result:
- [ ] **J4. Save.** Press the footer's **Review N changes**, look at the list, then press **Confirm and save N changes** under it.
  *Expect:* the footer button writes nothing and only scrolls the right column down to the changes; Confirm writes only the edited comics, keeps the originals in an `Archive` folder, and Library stats (if scanned) refreshes. Open one comic in a zip tool and read `ComicInfo.xml`.
  Result:
- [ ] **J5. A real .cbr and a big folder.** Open a folder with a real RAR `.cbr`, then one with a few thousand comics.
  *Expect:* the `.cbr` is listed, greyed and cannot be edited, and **Convert them…** opens CBR to CBZ on that folder; the big folder shows progress while reading and then scrolls smoothly.
  Result:

## K. Two-column pages

- [ ] **K1. Drag the divider.** On Bulk folder, Metadata, Library audit and CBR to CBZ, drag the thin divider between the columns left and right, then close and reopen the app.
  *Expect:* the right column gets wider and narrower smoothly, the left column stops at a usable width, text in the right column re-wraps, and the width is the same after reopening.
  Result:
- [ ] **K2. Small and large windows.** Make the window narrow, then very wide, on each of the four pages.
  *Expect:* nothing is cut off that you cannot reach (each column scrolls or wraps), the footer stays visible, and the lists use the height of the page.
  Result:
- [ ] **K3. Look.** Compare the four pages in light and dark mode.
  *Expect:* the same header, divider, headings and spacing on all four. Tell me what feels cramped or wasted.
  Result:

## L. CBR to CBZ

- [ ] **L1. A real RAR.** Put a few genuine RAR `.cbr` files (not zips renamed) in a folder, add it to CBR to CBZ and watch the *Kind* column.
  *Expect:* *RAR* for the real ones (or *Unreadable*, with the reason in the Review, if 7-Zip and unrar are not installed); *ZIP inside* for a renamed zip.
  Result:
- [ ] **L2. Run it.** Choose **Move to Archive**, press **Dry run**, then **Convert N files**.
  *Expect:* the dry run shows "Would convert" and changes nothing; the run shows progress with time left, then "Done"; each `.cbz` opens in YACReader with the same pages; each original is in `Archive` as `.cbr.bak`.
  Result:
- [ ] **L3. Existing `.cbz`.** Put a `.cbz` beside a `.cbr` of the same name and try Skip, Keep both and Replace.
  *Expect:* the Review table and its headline follow each choice before you run, and the run does what they said.
  Result:
- [ ] **L4. Delete it.** Choose **Delete it** and press **Convert**.
  *Expect:* a warning explains the originals are deleted for good once verified; **No** leaves everything as it was.
  Result:
- [ ] **L5. Tidy-up.** Turn on **Remove junk files** and **Rename pages** under Advanced options and convert a comic that holds `Thumbs.db`.
  *Expect:* "Advanced options · 2 changed"; the `.cbz` has no junk and its pages are `001.jpg`, `002.jpg`… in the right order.
  Result:
- [ ] **L6. From the Library audit.** Scan a library with `.cbr` files, then press **Convert in bulk** on the CBR chip.
  *Expect:* CBR to CBZ opens on the same folder with a "From Library audit" chip; **Back to Library audit** returns.
  Result:
- [ ] **L7. Look.** Drag the divider and compare the page with Bulk folder in light and dark mode, in a small and a large window.
  *Expect:* the same header, divider, headings and spacing; nothing is cut off that you cannot reach.
  Result:

## M. Single issue

- [ ] **M1. The strip.** Load a normal comic, a short one (4 or 5 pages) and a TPB in Single issue. Make the window narrow, then wide, and drag the divider.
  *Expect:* the cover, pages 2 and 3 and the last two pages (every page of a short comic), then the Browse tile; the strip wraps to the width of the left column; nothing is cut off.
  Result:
- [ ] **M2. Save cover.** Press **Save cover**, then again, with *If the file exists* on Keep both, Skip and Overwrite; try a PNG format and the other file name; then choose *A folder I choose* under Advanced options.
  *Expect:* the line under Save names the file before you press the button and says when it already exists; the file appears there; **Open folder** shows it.
  Result:
- [ ] **M3. Pick from the strip.** Click a page of the strip, then press Space or click the page to pick it, step to other pages with the arrow keys, and close the view with Esc.
  *Expect:* a tick and its number show under each picked page; the footer reads **Extract N pages**; **Clear picks** brings back **Save cover**.
  Result:
- [ ] **M4. One selection.** Press the Browse tile, pick and unpick pages in the window (click, shift-click, a dragged box, Select all), and watch the page behind it.
  *Expect:* the ticks and the footer follow every change, and **Clear picks** on the page empties the window's selection too.
  Result:
- [ ] **M5. Extract and ZIP.** Pick a few pages out of order and press **Extract N pages**; then press **Save all pages as ZIP**.
  *Expect:* the JPG files are numbered in the order you picked and open correctly; the ZIP holds every page and opens in a reader.
  Result:
- [ ] **M6. Look.** Compare the page with Bulk folder and CBR to CBZ in light and dark mode.
  *Expect:* the same header, divider, headings and spacing. Tell me what feels cramped or wasted.
  Result:

- [ ] **M7. Picker toolbar.** Open Browse all pages on a long comic. Pick pages out of order, then switch **Numbering** to *By page number* and back; try **Arrange…**.
  *Expect:* the Numbering switch, the line of gestures and the orange *Looks like a cover* legend are always visible and fit at the narrowest window width; *By page number* sorts the picks (and the ticks on the Single issue page follow); **Arrange…** is greyed in that mode and works in the other; the saved files are numbered in the order shown.
  Result:

## O. Links between tools

- [ ] **O1. Next steps.** Finish a run on Bulk folder, then Renamer (apply on a test folder), Metadata (save), Reading order (write), Add to library (add) and CBR to CBZ (convert).
  *Expect:* each page shows a **Next steps** row under its header with the links named in the tools list; the row goes away when you leave the page.
  Result:
- [ ] **O2. The link opens the next tool ready.** Press each link once.
  *Expect:* the next tool opens with the same folder already loaded, a chip "From <tool>" and a **Back to <tool>** button that returns to where you were.
  Result:
- [ ] **O3. Get covers.** Open ACEO sheets with an empty list and press **Get covers…**.
  *Expect:* Bulk folder opens.
  Result:

## P. Packaged build

- [ ] **P1. Build and start.** Run `.\packaging\build.ps1 -Shortcut`, then start the program from the desktop shortcut (best on a computer or user without Python on the PATH).
  *Expect:* the window opens with the Comic Toolkit icon in the title bar and the taskbar, Home shows every tool, and dragging a folder onto a page works.
  Result:
- [ ] **P2. Settings.** Change the theme, close the program, start it again. Look in `%APPDATA%\ComicToolkit`.
  *Expect:* the theme is remembered and `settings.json` is there (and no `settings.json` is written beside the `.exe`). If you had one beside the source, your old options are carried over the first time.
  Result:
- [ ] **P3. Every tool starts.** Open each tool once, including ACEO sheets (press Save with a few covers) and a `.cbr` in CBR to CBZ.
  *Expect:* no tool fails to open; ACEO sheets makes its PDF; the `.cbr` is read once you put `7z.exe` and `7z.dll` (or `unrar.exe`) in `dist\ComicToolkit\tools`, or have 7-Zip installed.
  Result:

## When you're done

Send me the failed items with what you saw (a screenshot or the exact message helps). Passing results can be summarised in one line.

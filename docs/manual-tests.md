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

- [ ] **B1. Count parsing.** Rename a copy to `Test 03 (of 12) (2020).cbz`, open the Metadata tool on its folder.
  *Expect:* the **Of** column shows `12`, Series `Test`, # `03`, Year `2020`. Try `(3 of 12)` and `[of 12]` too.
  Result:
- [ ] **B2. Count survives into the file.** Write the metadata, then check `ComicInfo.xml` inside the CBZ (open the zip, read the file).
  *Expect:* `<Count>12</Count>` present.
  Result:
- [ ] **B3. Inline edit of Of.** Double-click the Of cell, type `24`, press Enter.
  *Expect:* the row shows `24` and status Update/Add; Escape cancels an edit.
  Result:
- [ ] **B4. Set for checked rows.** Tick two rows, untick the rest. In "Set for checked rows" choose Genre, type `Superhero, Crime`, click Set value.
  *Expect:* a confirmation line under the buttons, the two rows show Update, others unchanged. Repeat for Series Group, Alternate series and Publisher.
  Result:
- [ ] **B5. Cancel.** Choose Genre again, leave the box empty, click Set value.
  *Expect:* the pending Genre disappears from those rows.
  Result:
- [ ] **B6. Nothing checked.** Untick everything and click Set value.
  *Expect:* a red message asking you to check a row; nothing changes.
  Result:
- [ ] **B7. YACReader shows the fields.** Turn on ComicInfo import (Settings > General), Update Library, open the comic's info.
  *Expect:* Issue count, Series Group, Genre, Alternate series, Publisher match what you wrote.
  If any field is blank, note which. That tells me which tags YACReader does not read.
  Result:
- [ ] **B8. Layout.** Look at the Metadata page in light and dark mode, and at a narrow window.
  *Expect:* the new side-panel section and the reminder under the table are readable, nothing clipped.
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

## D. Library audit (roadmap item 3)

Open **Library audit** from Home (or drop a folder on it). Use `Test Library` from the setup above, plus the extra files named in each test.

- [ ] **D1. Quick scan.** Choose the folder, leave the defaults, press **Scan library**.
  *Expect:* a progress bar and "Scanning n of N", then "Done · N files in …s". The window stays responsive; switching between the four report tabs is instant.
  Result:
- [ ] **D2. Broken files.** Add a text file renamed `Broken 01.cbz`, and copy a CBZ then damage it (open the copy in a hex editor or just truncate it by cutting the file in half). Scan, then tick **Full integrity test** and scan again.
  *Expect:* `Broken 01.cbz` is listed as "Not a valid zip" in both scans; the truncated file shows only with the full test (or as not a valid zip). Healthy comics are never listed.
  Result:
- [ ] **D3. Real RAR files.** With real `.cbr` files present, run the full integrity test with and without **Open real .cbr files**.
  *Expect:* without it, `.cbr` files are not tested or listed; with it they are tested, and a healthy RAR is not listed. Needs 7-Zip or Windows `tar.exe`.
  Result:
- [ ] **D4. Duplicates by name.** Copy a comic into another folder and rename the copy slightly (e.g. add " (Digital)").
  *Expect:* both show in one group, the bigger file unticked and the smaller ticked.
  Result:
- [ ] **D5. Duplicates by cover.** Make a copy of a comic and change its name completely (so the name no longer matches), then turn on **Compare cover images** and scan. Also include two *different* issues of the same series.
  *Expect:* the renamed copy is found as "Similar cover"; the two different issues are not paired. Try Strict, Normal and Loose and tell me which gives the right answers on your real collection.
  Result:
- [ ] **D6. Move to Archive.** Tick a file, press **Move checked to Archive**, confirm.
  *Expect:* a confirmation dialog naming the count; the file moves to `Archive/<name>.bak` next to where it was; the row disappears; declining the dialog changes nothing. Untick a row and check that it is not moved.
  Result:
- [ ] **D7. Missing issues.** Use a series where you know which issues you own, ideally one with a `(of N)` count. Open the **Missing** tab.
  *Expect:* the gaps match what you know, written like `#13, #27-#29`; with a count, missing issues after your highest one are listed too. Try **Expect issues from #1**. Annuals and specials should not produce gaps.
  Result:
- [ ] **D8. Wishlist.** Press **Copy wishlist** and paste into Notepad; press **Save wishlist…** as `.txt` and as `.csv` and open both.
  *Expect:* one line per missing issue (`Batman v2 #13`); the CSV opens in Excel with Series, Volume and Issue columns.
  Result:
- [ ] **D9. Quality.** Open the **Quality** tab.
  *Expect:* very short books, tiny or huge files and low-resolution covers are flagged and the flags make sense. Tell me if the limits (10 to 300 pages, 1 MB to 500 MB, 800 px) flag too much or too little in your library.
  Result:
- [ ] **D10. CSV export.** Press **Export CSV…** on each tab.
  *Expect:* a CSV that opens in Excel without garbled characters and matches what the table shows.
  Result:
- [ ] **D11. Stop and cache.** Scan a large folder with **Full integrity test** on and press **Stop** part-way; then scan again without it.
  *Expect:* Stop ends the scan quickly with "Stopped" and a "(partial …)" note; a later scan of unchanged files is much faster ("from cache").
  Result:
- [ ] **D12. Look and feel.** View the page in light and dark mode, with the window narrow, and with hundreds of rows.
  *Expect:* tables readable in both themes, buttons not clipped, scrolling smooth. Switching theme while results are shown keeps them.
  Result:

## When you're done

Send me the failed items with what you saw (a screenshot or the exact message helps). Passing results can be summarised in one line.

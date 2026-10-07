# Safety model

[< Docs index](README.md)

- **Preview before change.** Renamer and Metadata show a review table. CBR to CBZ, Clean-up and Folder icons have **Preview changes**, which logs what would happen without writing anything.
- **Verified writes.** Archive rewrites go to a `.part` file, are verified (zip test plus page count), and only then swapped in. A failure never leaves a half-written comic.
- **The `Archive` folder.** Backups of modified comics and converted `.cbr` files are moved into an `Archive` folder next to the file and renamed with a `.bak` suffix (`Batman 01.cbz.bak`) so comic readers ignore them. To restore one, move it back and delete the `.bak`. All folder scans in the app skip any folder named `Archive`. Don't name a real library folder `Archive`.
- **Audit never edits.** The Library audit only reads. Its one action, *Move checked to Archive*, asks first, pre-ticks nothing but the smaller copies, and moves files as `.bak` rather than deleting them.
- **Reading order writes like Metadata does.** The same verified write and `.bak` backup apply, a confirmation precedes every write, a filename that would collide is not renamed, and the copy option leaves originals untouched.
- **No overwrites by surprise.** Conflicting names are flagged (Renamer: *Exists* / *Duplicate*, skipped on apply) or resolved by your Skip / Keep both / Overwrite choice.
- **Delete is opt-in.** Deleting an original after conversion is an explicit option and only happens after verification.
- **Stop buttons** on the batch tools halt between files.

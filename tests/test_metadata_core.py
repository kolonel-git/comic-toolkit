"""Metadata editing logic: pending edits, what is missing, filters, fill from filenames, the rest of a series, and
suggestions taken from the library."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import metadata_core as mc
from rename_core import parse_filename

lib = Path("C:/Library")


def row(rel, ci=None, locked=False):
    p = lib / rel
    return mc.Row(p, parse_filename(p.stem), dict(ci or {}), locked)


# edits: set, restore, clear, normalise
r = row("DC/Batman 012 (2016).cbz", {"series": "Batman", "issue": "12", "publisher": "DC"})
assert r.value("publisher") == "DC" and r.value("year") == ""
r.set("year", " 2016 "); assert r.pending == {"year": "2016"} and r.value("year") == "2016"
r.set("year", ""); assert r.pending == {}, "emptying a field that had nothing leaves no edit"
r.set("publisher", ""); assert r.pending == {"publisher": None} and r.value("publisher") == "", "emptying a stored value deletes it"
r.set("publisher", "DC"); assert r.pending == {}, "putting the stored value back drops the edit"
r.set("issue", "012"); assert r.pending == {}, "012 is the stored 12"
r.set("issue", "13"); assert mc.writes(r) == {"issue": "13"}
r.discard(); assert r.pending == {}

# what is missing; a collected edition does not need an issue number
a = row("DC/Batman 012 (2016).cbz", {"series": "Batman", "issue": "12"})
assert mc.lacks(a) == ["year", "publisher"] and mc.needs_attention(a)
a.set("year", "2016"); a.set("publisher", "DC"); assert mc.lacks(a) == [] and not mc.needs_attention(a)
tpb = row("DC/Batman Vol 2 TPB.cbz", {"series": "Batman", "year": "2012", "publisher": "DC"})
assert tpb.collected and mc.lacks(tpb) == [], mc.lacks(tpb)

# filters
rows = [row("A/Saga 001 (2012).cbz", {"series": "Saga", "issue": "1", "year": "2012", "publisher": "Image"}),
        row("A/Saga 002.cbz"), row("B/Old Tales TPB.cbz", locked=True), tpb]
assert [mc.matches(x, "all") for x in rows] == [True] * 4
assert [mc.matches(x, "attention") for x in rows] == [False, True, True, False]
assert [mc.matches(x, "no_publisher") for x in rows] == [False, True, True, False]
assert [mc.matches(x, "no_issue") for x in rows] == [False, True, False, False], "collected editions are not missing an issue number"
assert [mc.matches(x, "no_year") for x in rows] == [False, True, True, False]
assert [mc.matches(x, "no_comicinfo") for x in rows] == [False, True, False, False], "a locked .cbr is not offered for ComicInfo"
assert set(mc.FILTERS) == {"all", "attention", "no_series", "no_issue", "no_year", "no_publisher", "no_comicinfo"}

# fill from the filename: only blanks, the series falls back to the folder name
b = row("Saga/Saga 002 (of 54) (2012).cbz", {"publisher": "Image"})
n = mc.fill_from_filename(b, lib)
assert n >= 4 and b.value("series") == "Saga" and b.value("issue") == "2" and b.value("year") == "2012" and b.value("count") == "54"
assert "publisher" not in b.pending
b.set("year", "1999"); mc.fill_from_filename(b, lib); assert b.value("year") == "1999", "an edit is not overwritten"
c = row("Hellboy/002.cbz"); mc.fill_from_filename(c, lib); assert c.value("series") == "Hellboy", "series from the folder"
d = row("002.cbz"); mc.fill_from_filename(d, lib); assert d.value("series") == "", "the library folder itself is not a series"

# the changes a save would make
x, y = row("S/Saga 001.cbz", {"publisher": "Old"}), row("S/Saga 002.cbz")
x.set("publisher", "Image"); x.set("year", "2012"); y.set("publisher", "Image")
ch = mc.changes([x, y])
assert [(c_[1], c_[2], c_[3]) for c_ in ch if c_[0] is x] == [("year", "", "2012"), ("publisher", "Old", "Image")]
assert len(ch) == 3
x.set("publisher", ""); assert [c_ for c_ in mc.changes([x]) if c_[1] == "publisher"][0][3] == "", "a deletion shows as empty"

# the rest of a series: matches ignore case, punctuation and a leading The; locked comics are left alone
s1, s2 = row("D/The Amazing Spider-Man 001.cbz"), row("D/Amazing Spider Man 002.cbz")
s3, s4 = row("D/Amazing Spider-Man 003.cbz", locked=True), row("D/Batman 001.cbz")
for q in (s1, s2, s3, s4): q.ci = {"series": q.parsed["series"]}
everyone = [s1, s2, s3, s4]
s1.set("publisher", "Marvel")
assert mc.same_series(everyone, s1) == [s2], "a locked .cbr is not offered an edit"
assert mc.others_lacking(everyone, s1, "publisher") == [s2]
s2.set("publisher", "Marvel"); assert mc.others_lacking(everyone, s1, "publisher") == []
assert mc.others_lacking(everyone, s4, "publisher") == [], "nothing to offer when the comic itself has no value"

# suggestions: from the same series, then the folder, then the name, then the library; never the current value
lib_rows = [row("Marvel/Spider-Man 001.cbz", {"series": "Spider-Man", "publisher": "Marvel", "genre": "Superhero"}),
            row("Marvel/Spider-Man 002.cbz", {"series": "Spider-Man", "publisher": "Marvel"}),
            row("Marvel/Hulk 001.cbz", {"series": "Hulk", "publisher": "Marvel Comics"}),
            row("Marvel/Spider-Man 003.cbz"),
            row("Image/Saga 001.cbz", {"series": "Saga", "publisher": "Image"}),
            row("Image/Saga 002.cbz")]
idx = mc.SuggestIndex(lib_rows)
target = lib_rows[3]
pub = idx.for_field(target, "publisher")
assert pub[0] == ("Marvel", "series") and ("Marvel Comics", "folder") in pub and ("Image", "library") in pub, pub
assert all(v != target.value("publisher") for v, _s in pub)
assert [s for _v, s in pub] == sorted([s for _v, s in pub], key=["series", "folder", "name", "library"].index), "ordered by where from"
saga = lib_rows[5]
assert idx.for_field(saga, "publisher")[0] == ("Image", "series")
assert idx.for_field(target, "genre")[0] == ("Superhero", "series")
assert idx.for_field(target, "issue") == [("3", "name")], "an issue number is never suggested from other comics"
target.set("publisher", "Marvel"); assert "Marvel" not in [v for v, _s in idx.for_field(target, "publisher")], "not the value it holds"
# series names: near matches in the library, spelled the way most of them are
odd = row("Marvel/Spiderman 004.cbz")
ser = idx.for_field(odd, "series")
assert ("Spider-Man", "folder") in ser or ("Spider-Man", "series") in ser, ser
assert len(idx.for_field(target, "publisher", limit=1)) == 1
print("metadata core OK")

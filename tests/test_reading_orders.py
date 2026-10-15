"""The marked reading-order folders, the guess at which folders look like one, and the needs-attention counts."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import stats_core as sc
from library_scan import Issue
from reading_orders import ReadingOrders, looks_like_reading_order, suggest
from rename_core import parse_filename


def issue(path, ci=None, size=100):
    p = Path(path)
    return Issue(path=p, rel=p.name, size=size, mtime=0.0, parsed=parse_filename(p.stem), ci=ci or {}, ci_read=True)


lib = Path("C:/Library")

# marking: case-insensitive, a folder inside a marked one is already covered, a new parent replaces its children
ro = ReadingOrders()
assert ro.add(lib / "Reading Orders" / "Event") and len(ro) == 1
assert not ro.add(str(lib / "reading orders" / "EVENT")), "same folder, different case"
assert ro.covers(lib / "Reading Orders" / "Event" / "Part 1" / "x.cbz") and not ro.covers(lib / "Reading Orders" / "Other" / "x.cbz")
assert not ro.covers(lib / "Reading Orders" / "Event Extra" / "x.cbz"), "a folder that only starts with the same letters is not inside"
assert not ro.add(lib / "Reading Orders" / "Event" / "Part 1"), "inside a marked folder"
assert ro.add(lib / "Reading Orders") and ro.folders == [str(lib / "Reading Orders")], ro.folders
assert ro.which(lib / "Reading Orders" / "Event" / "a.cbz") == str(lib / "Reading Orders")
assert ro.remove(lib / "Reading Orders") and not ro.remove(lib / "Reading Orders") and len(ro) == 0

# saving and loading: round trip, damaged data is ignored
ro.add(lib / "A"); ro.dismiss(lib / "B")
back = ReadingOrders.from_dict(ro.to_dict())
assert back.folders == ro.folders and back.dismissed(lib / "B") and not back.dismissed(lib / "A")
for bad in (None, 5, {"folders": "x"}, {"folders": [3, None, "C:/Z"], "dismissed": {"a": 1}}):
    r = ReadingOrders.from_dict(bad)
    assert isinstance(r.folders, list)
assert ReadingOrders.from_dict({"folders": [3, None, "C:/Z"]}).folders == ["C:/Z"]
ro.add(lib / "B"); assert not ro.dismissed(lib / "B"), "marking a folder clears an earlier no"

# splitting real comics from reading-order copies
ro = ReadingOrders([lib / "Orders"])
real, copies = ro.split([issue(lib / "DC" / "Batman 001 (2016).cbz"), issue(lib / "Orders" / "Event" / "01 - Batman 001.cbz")])
assert [i.path.name for i in real] == ["Batman 001 (2016).cbz"] and [i.path.name for i in copies] == ["01 - Batman 001.cbz"]

# what looks like a reading order: numbered names or story arcs in most files, at least three comics
numbered = [issue(lib / "Event" / f"{n:02d} - Saga {n:03d}.cbz") for n in range(1, 5)]
assert looks_like_reading_order(numbered)[0] and "4 of 4 names start with a number" == looks_like_reading_order(numbered)[1]
assert not looks_like_reading_order(numbered[:2])[0], "two comics are too few to say"
bracket = [issue(lib / "E2" / f"[{n:02d}] Saga {n:03d}.cbz") for n in range(1, 4)]
assert looks_like_reading_order(bracket)[0]
arcs = [issue(lib / "E3" / f"Saga {n:03d}.cbz", ci={"story_arc": "War"}) for n in range(1, 5)]
assert looks_like_reading_order(arcs) == (True, "4 of 4 have a story arc")
plain = [issue(lib / "Saga" / f"Saga {n:03d}.cbz") for n in range(1, 6)]
assert not looks_like_reading_order(plain)[0]
mixed = numbered[:2] + plain[:3]   # 2 of 5 numbered: under the share
assert not looks_like_reading_order(mixed)[0]

# suggestions: only unmarked, not dismissed folders under the library, biggest first; never the library folder itself
everything = numbered + bracket + arcs + plain + [issue(lib / f"01 - Loose {n}.cbz") for n in range(4)]
got = suggest(everything, ReadingOrders(), lib)
assert [f.name for f, _n, _w in got] == ["E3", "Event", "E2"], got
ro = ReadingOrders([lib / "Event"]); ro.dismiss(lib / "E3")
assert [f.name for f, _n, _w in suggest(everything, ro, lib)] == ["E2"]

# needs-attention counts leave out what the caller leaves out, and count duplicates once per group
def meta(path, **ci):
    return issue(path, ci=ci)
rows = [meta(lib / "DC" / "Batman 001 (2016).cbz", publisher="DC", year="2016", series="Batman"),
        issue(lib / "Backup" / "Batman 001 (2016).cbz"),
        issue(lib / "Saga" / "Saga 001.cbz"), issue(lib / "Saga" / "Saga 002.cbz"),
        issue(lib / "Misc" / "Old Tales TPB.cbz")]
a = sc.attention(rows)
assert a["no_publisher"] == 4 and a["any_missing"] >= 4 and a["no_year"] >= 3
assert a["duplicate_groups"] == 1 and sc.attention([])["any_missing"] == 0
single = issue(lib / "X" / "Thing 005 (2020).cbz")
assert sc.attention([single]) == {"no_publisher": 1, "no_year": 0, "no_issue": 0, "any_missing": 1, "duplicate_groups": 0}
print("reading orders OK")

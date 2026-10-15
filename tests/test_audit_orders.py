"""Library audit and reading orders: copies in a marked reading-order folder are left out of Duplicates (unless asked for),
an outside copy is always the original, the Reading order finding, the confirmation's description of a fix plan and the
data behind the Details panel. No windows."""
import sys
from pathlib import Path
from types import SimpleNamespace as NS
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import audit_core as ac
from reading_orders import ReadingOrders

LIB = Path("C:/Comics")


def issue(rel, series="Batman", issue_no="1", size=1000, pages=20, cover_h=1200, **kw):
    info = {"series": series, "issue": issue_no, "volume": "", "kind": "", "collected": False}
    info.update(kw)
    return NS(path=LIB / rel, rel=rel, info=info, size=size, pages=pages, cover_h=cover_h, cover_hash="", ext=Path(rel).suffix,
              ci_read=True, junk=[], error="", ci={})


real = issue("Batman/Batman 01.cbz", size=5000, pages=22)
copy = issue("Batman/Batman 01 (scan).cbz", size=4000, pages=18)
arc1 = issue("Arcs/Knightfall/01 - Batman 01.cbz", size=6000, pages=40, cover_h=2000)   # bigger, but a reading-order copy
arc2 = issue("Arcs/Knightfall/02 - Batman 02.cbz", issue_no="2", size=3000)
other = issue("Saga/Saga 01.cbz", series="Saga", size=2500)
allx = [real, copy, arc1, arc2, other]

orders = ReadingOrders([str(LIB / "Arcs")])

# by default the reading-order copies are left out, and counted
groups, left = ac.duplicates_for(allx, orders)
assert left == 2 and len(groups) == 1 and [i.rel for i in groups[0].issues] == [real.rel, copy.rel], (left, groups)
# with the switch on they are compared too, but the copy outside the folder is still the one kept
groups, left = ac.duplicates_for(allx, orders, include=True)
assert left == 0 and len(groups) == 1
assert groups[0].issues[0].rel == real.rel, "an outside copy is the original even when the reading-order copy is bigger"
assert {i.rel for i in groups[0].issues} == {real.rel, copy.rel, arc1.rel}
# no reading orders marked: nothing changes
groups, left = ac.duplicates_for(allx, ReadingOrders())
assert left == 0 and groups[0].issues[0].rel == arc1.rel, "without the marking, the biggest copy wins as before"
# a group made only of reading-order copies is not reported when they are left out
twin = issue("Arcs/Knightfall/03 - Batman 02 again.cbz", issue_no="2", size=3001)
groups, left = ac.duplicates_for([arc2, twin, other], orders)
assert groups == [] and left == 2

# the Reading order rows: one per marked folder, with how many exist outside it
rows = ac.reading_order_rows(allx, orders)
assert len(rows) == 1 and rows[0][0] == str(LIB / "Arcs") and len(rows[0][1]) == 2 and rows[0][2] == 1, rows
assert ac.reading_order_rows(allx, ReadingOrders()) == []

data = {"broken": [], "dups": [], "gaps": [], "junk": [], "cbr": [], "quality": [], "orders": rows}
fs = ac.build_findings(data)
assert [f.kind for f in fs] == [ac.ORDER] and fs[0].count == 2 and fs[0].fix is None
assert "2 comics" in fs[0].detail and "1 also in your library" in fs[0].detail
assert ac.build_findings(data, ignored=[fs[0].key]) == [], "a reading-order row can be ignored"

# the confirmation: summary lines and a line per file saying where it goes and whether it can be undone
a, c, j = LIB / "a.cbz", LIB / "x" / "b.cbr", LIB / "j.cbz"
plan = [(a, ac.ARCHIVE, []), (c, ac.CONVERT, []), (j, ac.CLEAN, [])]
lines = ac.plan_lines(plan)
assert lines == ["Remove junk files from 1 comic",
                 "Convert 1 CBR file to CBZ (each .cbr is deleted once its CBZ has been verified)",
                 "Move 1 file to Archive folders (as .bak)"], lines
desc = ac.describe_plan(plan, LIB)
assert desc[0][0] == "a.cbz" and ".bak" in desc[0][1] and desc[0][2] is True, "an Archive move can be undone"
assert desc[1][0].replace("\\", "/") == "x/b.cbr" and "b.cbz" in desc[1][1] and desc[1][2] is False, "a deleted .cbr cannot"
assert desc[2][2] is False

# the data behind the Details panel
res = {"issues": allx, "seconds": 1.5, "cache_hits": 3, "stopped": False, "integrity": False, "left_out": 2}
counts = {k: 0 for k in ac.KINDS}
counts[ac.DUPLICATE] = 1
d = ac.build_details(res, counts, ignored=4, with_orders=False)
scan = dict(d["scan"])
assert scan["Comics scanned"].startswith("5 in 1.5s") and "3 from cache" in scan["Comics scanned"]
assert "2 comics left out of Duplicates" in scan["Reading orders"] and scan["Ignored by you"] == "4 findings"
assert "off" in scan["Integrity test"]
kinds = [f["kind"] for f in d["found"]]
assert kinds == [ac.BROKEN, ac.DUPLICATE, ac.MISSING, ac.JUNK, ac.CBR, ac.WARNING], kinds    # nobody lacks a series or issue here
dup = next(f for f in d["found"] if f["kind"] == ac.DUPLICATE)
assert dup["title"] == "1 group of duplicates" and ("Mark reading orders", "tool:stats") in dup["actions"]
cbr = next(f for f in d["found"] if f["kind"] == ac.CBR)
assert ("Convert in bulk", "tool:convert") in cbr["actions"] and ("Show in list", "show:CBR") in cbr["actions"]
# a check switched off is not described; comics with no series or issue number point to Metadata
nameless = issue("Misc/untitled.cbz", series="")
noissue = issue("Misc/Thing.cbz", series="Thing", issue_no="")
res2 = {**res, "issues": allx + [nameless, noissue], "left_out": 0}
d2 = ac.build_details(res2, counts, with_orders=True, checks=[ac.BROKEN, ac.CBR])
assert [f["kind"] for f in d2["found"]] == [ac.BROKEN, ac.CBR, "Metadata"]
meta = d2["found"][-1]
assert meta["title"] == "1 with no series · 1 with no issue number"
assert ("Comics with no series", "tool:metadata:no_series") in meta["actions"] and ("Comics with no issue number", "tool:metadata:no_issue") in meta["actions"]
assert dict(d2["scan"])["Reading orders"] == "included in Duplicates" and dict(d2["scan"])["Checks on"] == "Broken, CBR"
print("AUDIT ORDERS OK")

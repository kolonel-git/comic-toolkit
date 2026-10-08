import sys, tempfile, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import reading_order as ro
import archive_tools as at
from rename_core import parse_filename, read_comicinfo, split_order_prefix


def cbz(p, n=2):
    p.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(p, "w") as z:
        for i in range(n): z.writestr(f"{i}.jpg", b"x")
    return p


# --- helpers
assert ro.number_text(3, 12, ro.NUM_PADDED) == "03" and ro.number_text(3, 120, ro.NUM_PADDED) == "003" and ro.number_text(3, 12, ro.NUM_PLAIN) == "3"
assert ro.prefix_text(3, 12, ro.PREFIX_DASH) == "03 - " and ro.prefix_text(3, 12, ro.PREFIX_BRACKET) == "[03] " and ro.prefix_text(3, 12, ro.PREFIX_OFF) == ""
assert ro.writes_for("Court", 2, 5, ro.STORY, ro.NUM_PLAIN) == {"story_arc": "Court", "story_arc_number": "2"}
alt = ro.writes_for("Court", 2, 5, ro.ALTERNATE, ro.NUM_PLAIN, "Bat Family")
assert alt == {"alternate_series": "Court", "alternate_number": "2", "alternate_count": "5", "series_group": "Bat Family"}, alt
assert set(ro.writes_for("C", 1, 3, ro.BOTH, ro.NUM_PLAIN)) == {"story_arc", "story_arc_number", "alternate_series", "alternate_number", "alternate_count"}

# --- prefix recognition in the parser
for stem, series, issue, pre in [("03 - Batman 05 (2016)", "Batman", "05", "03 - "), ("[012] Saga #7", "Saga", "7", "[012] "),
                                 ("Batman 05 (2016)", "Batman", "05", ""), ("2000 AD 01", "2000 AD", "01", "")]:
    p = parse_filename(stem)
    print(stem, "->", p["series"], p["issue"], repr(p["order_prefix"]))
    assert (p["series"], p["issue"], p["order_prefix"]) == (series, issue, pre), (stem, p)
assert split_order_prefix("07 - Name")[1] == "Name"

# --- suggest order
names = ["Batman 10 (2016).cbz", "Batman 2 (2016).cbz", "Aquaman 05.cbz", "zzz notes.cbz", "Batman 02 (2011).cbz", "Batman v2 01.cbz"]
got = [Path(n).name for n in sorted(names, key=ro.suggest_key)]
print(got)
assert got[0] == "Aquaman 05.cbz" and got[-1] == "zzz notes.cbz" and got.index("Batman 02 (2011).cbz") < got.index("Batman 2 (2016).cbz") < got.index("Batman 10 (2016).cbz")

with tempfile.TemporaryDirectory() as d:
    d = Path(d)
    a = cbz(d / "A" / "Batman 05.cbz"); b = cbz(d / "B" / "Robin 01.cbz"); c = cbz(d / "A" / "Old 01.cbr")
    c.write_bytes(b"Rar!junk")
    at.apply_metadata(b, {"story_arc": "Other Arc", "story_arc_number": "9"}, False)
    o = {"name": "Court of Owls", "store": ro.STORY, "numbering": ro.NUM_PADDED, "group": "", "prefix": ro.PREFIX_DASH}

    # blocked
    assert ro.writable(c) == "Convert to CBZ first" and ro.writable(a) is None and ro.writable(d / "nope.cbz") == "Missing"
    pc = ro.plan_item(c, {}, 3, 12, o, ro.writable(c)); assert pc["blocked"] and pc["status"] == "Convert to CBZ first"
    # plans
    pa = ro.plan_item(a, read_comicinfo(a), 1, 12, o); print(pa)
    assert pa["writes"] == {"story_arc": "Court of Owls", "story_arc_number": "01"} and pa["new_name"] == "01 - Batman 05.cbz" and pa["status"] == "Add"
    pb = ro.plan_item(b, read_comicinfo(b), 2, 12, o); print(pb)
    assert pb["status"] == "Replaces “Other Arc”" and pb["new_name"] == "02 - Robin 01.cbz"
    # in place with backup + prefix
    na = ro.apply_item(a, pa["writes"], pa["new_name"], True)
    assert na.name == "01 - Batman 05.cbz" and na.exists() and not a.exists()
    ci = read_comicinfo(na); assert ci["story_arc"] == "Court of Owls" and ci["story_arc_number"] == "01"
    assert (d / "A" / "Archive" / "Batman 05.cbz.bak").exists()
    # re-plan on the renamed file: no change, and prefix isn't doubled
    p2 = ro.plan_item(na, ci, 1, 12, o); assert p2["status"] == "No change" and p2["new_name"] == na.name, p2
    # renumber: position changes -> prefix is replaced, not stacked
    p3 = ro.plan_item(na, ci, 4, 12, o); assert p3["new_name"] == "04 - Batman 05.cbz" and p3["writes"]["story_arc_number"] == "04"
    nb = ro.apply_item(na, p3["writes"], p3["new_name"], False)
    assert nb.name == "04 - Batman 05.cbz" and read_comicinfo(nb)["story_arc_number"] == "04"
    # rename conflict: metadata is written, rename refused, message says so
    cbz(d / "A" / "01 - Batman 05.cbz")
    try:
        ro.apply_item(nb, {"story_arc_number": "01"}, "01 - Batman 05.cbz", False); raise SystemExit("expected conflict")
    except FileExistsError as e:
        print("conflict:", e)
    assert read_comicinfo(nb)["story_arc_number"] == "01" and nb.exists()
    # prefix off: metadata only, name untouched
    off = dict(o, prefix=ro.PREFIX_OFF)
    pr = ro.plan_item(b, read_comicinfo(b), 2, 12, off); assert pr["new_name"] == b.name
    nb2 = ro.apply_item(b, pr["writes"], pr["new_name"], False); assert nb2 == b and read_comicinfo(b)["story_arc"] == "Court of Owls"
    # copy mode: originals untouched, copies stamped & prefixed, name collisions made unique
    src = cbz(d / "S" / "Saga 01.cbz"); before = src.read_bytes()
    dest = d / "Copies" / "Court of Owls"
    cp = ro.plan_item(src, {}, 1, 2, o)
    r1 = ro.apply_item(src, cp["writes"], cp["new_name"], True, dest)
    r2 = ro.apply_item(src, cp["writes"], cp["new_name"], True, dest)
    print([p.name for p in dest.iterdir()])
    assert r1.name == "01 - Saga 01.cbz" and r2.name == "01 - Saga 01 (1).cbz"
    assert src.read_bytes() == before and not (src.parent / "Archive").exists()
    assert read_comicinfo(r1)["story_arc"] == "Court of Owls"
    # alternate store reads back through current_arc
    ao = dict(o, store=ro.ALTERNATE, prefix=ro.PREFIX_OFF)
    pw = ro.plan_item(src, {}, 2, 5, ao); at.apply_metadata(src, pw["writes"], False)
    assert ro.current_arc(read_comicinfo(src), ro.ALTERNATE) == ("Court of Owls", "2")
    ci = read_comicinfo(src); assert ci["alternate_count"] == "5" and ci["alternate_number"] == "2"
print("ORDER CORE OK")

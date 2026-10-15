import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import stats_core as sc
from library_scan import Issue
from rename_core import parse_filename


def mk(rel, size, ci=None, ci_read=True, pages=None):
    p = Path("C:/lib") / rel
    return Issue(p, rel, size, 0.0, parse_filename(p.stem), ci or {}, ci_read, pages is not None, pages)


MB = 1_000_000
issues = [
    mk("Batman/Batman v1 001 (1940).cbz", 10 * MB, {"publisher": "DC", "year": "1940"}, pages=20),
    mk("Batman/Batman v1 002 (1940).cbz", 12 * MB, {"publisher": "DC"}, pages=22),
    mk("Batman/Batman v2 001 (2011).cbz", 30 * MB, {"publisher": "DC", "series": "Batman", "volume": "2"}, pages=30),
    mk("The Walking Dead 001 (2003).cbz", 8 * MB, {"publisher": "Image"}),
    mk("Walking Dead 002 (2003).cbz", 9 * MB),  # same series, other spelling, no ComicInfo
    mk("Saga TPB Vol 1 (2012).cbr", 50 * MB, ci_read=False),  # a real RAR: ComicInfo unknown
    mk("scan0001.cbz", 1 * MB),  # no series, no year
]

st = sc.compute_stats(issues)
assert st.comics == 7 and st.bytes == 120 * MB and st.average == 120 * MB // 7
assert st.pages == 72, st.pages
assert st.series == 3, [r.label for r in st.sections["Series"]]  # Batman (volumes merged), Walking Dead, Saga
ser = {r.label: r for r in st.sections["Series"]}
assert ser["Batman"].count == 3 and ser["Batman"].bytes == 52 * MB
assert ser["The Walking Dead"].count == 2, "a leading The and case do not split a series"
assert sc.UNKNOWN in ser and ser[sc.UNKNOWN].count == 1 and st.sections["Series"][-1].label == sc.UNKNOWN, "Unknown goes last"

sp = {r.label: r.count for r in sc.compute_stats(issues, split_volumes=True).sections["Series"]}
assert sp["Batman v1"] == 2 and sp["Batman v2"] == 1 and "Batman" not in sp, sp

pub = {r.label: r.count for r in st.sections["Publishers"]}
assert pub == {"DC": 3, "Image": 1, sc.UNKNOWN: 3} and st.publishers == 2, pub

yrs = {r.label: r.count for r in st.sections["Years"]}
assert yrs == {"1940": 2, "2011": 1, "2003": 2, "2012": 1, sc.UNKNOWN: 1}, yrs
assert [r.label for r in sc.years_view(st.sections["Years"], False)] == ["1940", "2003", "2011", "2012", sc.UNKNOWN], "time order"
dec = {r.label: r.count for r in sc.compute_stats(issues, decades=True).sections["Years"]}
assert dec == {"1940s": 2, "2010s": 2, "2000s": 2, sc.UNKNOWN: 1}, dec

fm = {r.label: r.count for r in st.sections["Formats"]}
assert fm == {"CBZ": 6, "CBR": 1}

c = st.coverage
assert c["total"] == 7 and c["unread"] == 1 and c["with_comicinfo"] == 4, c  # RAR not counted either way
assert c["with_year"] == 6 and c["with_publisher"] == 4 and c["collected"] == 1 and c["issues"] == 6, c
lines = {l: (n, of) for l, n, of in sc.coverage_lines(st)}
assert lines["Have ComicInfo.xml"] == (4, 6), "judged only over files that were opened"

assert [i.rel for i in st.largest[:2]] == ["Saga TPB Vol 1 (2012).cbr", "Batman/Batman v2 001 (2011).cbz"]
assert st.smallest[0].rel == "scan0001.cbz" and len(st.largest) == 7
assert sc.compute_stats(issues, keep=3).largest.__len__() == 3

# top-N with an Other row
many = [mk(f"S{n:02d}/S{n:02d} 001.cbz", MB) for n in range(20)] + [mk("S00/S00 002.cbz", MB)]
rows = sc.compute_stats(many).sections["Series"]
assert len(rows) == 20 and rows[0].label == "S00" and rows[0].count == 2
cut = sc.top_n(rows)
assert len(cut) == 16 and cut[-1].label == "Other (5 more)" and cut[-1].count == 5 and len(cut[-1].issues) == 5
assert sum(r.count for r in cut) == 21 and sc.top_n(rows[:10]) == rows[:10]
ymany = [mk(f"A {n}.cbz", MB, {"year": str(1990 + n)}) for n in range(20)]
yv = sc.years_view(sc.compute_stats(ymany).sections["Years"], False)
assert len(yv) == 16 and yv[-1].label.startswith("Other") and [r.label for r in yv[:-1]] == sorted(r.label for r in yv[:-1])
assert len(sc.years_view(sc.compute_stats(ymany).sections["Years"], True)) == 20

# empty library and no page counts
e = sc.compute_stats([])
assert e.comics == 0 and e.average == 0 and e.pages is None and e.series == 0 and e.largest == [] and e.smallest == []
assert sc.compute_stats(issues[3:]).pages is None

# text, tables, snapshot
txt = sc.summary_text(st, "C:/lib")
assert "7 comics · 3 series · 2 publishers · 120.0 MB" in txt and "72 pages" in txt and "Have ComicInfo.xml: 4 of 6 (66%)" in txt, txt
assert txt.startswith("Comic library: C:/lib")
h, r = sc.section_table(st, "Series")
assert h == ["Series", "Comics", "Bytes"] and r[0] == ["Batman", 3, 52 * MB]
assert sc.section_table(st, "Years")[1][0][0] == "1940"
assert sc.section_table(st, "Coverage")[1][0] == ["Have ComicInfo.xml", 4, 6]
assert sc.section_table(st, "Largest")[1][0] == ["Saga TPB Vol 1 (2012).cbr", 50 * MB]
assert len(sc.section_table(compute := sc.compute_stats(many), "Series", show_all=False)[1]) == 16
assert len(sc.section_table(compute, "Series", show_all=True)[1]) == 20
try:
    sc.section_table(st, "Nope"); raise SystemExit("expected KeyError")
except KeyError:
    pass

assert sc.human_size(48.2e9) == "48.2 GB" and sc.human_size(1.5e6) == "1.5 MB" and sc.human_size(2500) == "2 KB"
assert [sc.ago(0, n) for n in (10, 120, 7200, 3 * 86400, 86400)] == ["just now", "2 minutes ago", "2 hours ago", "3 days ago", "1 day ago"]
snap = sc.snapshot(st, "C:/lib", when=1000.0)
assert snap == {"root": "C:/lib", "comics": 7, "series": 3, "bytes": 120 * MB, "when": 1000.0, "attention": 0}
assert sc.snapshot_line(snap, now=1000.0 + 2 * 86400) == "7 comics · 3 series · 120.0 MB · scanned 2 days ago"
assert sc.snapshot_line({**snap, "comics": 1}, now=1000.0).startswith("1 comic ·")
# the number of comics that need attention shows before "scanned"; an old saved snapshot without it still reads fine
snap2 = sc.snapshot(st, "C:/lib", when=1000.0, attention_count=63)
assert sc.snapshot_line(snap2, now=1000.0) == "7 comics · 3 series · 120.0 MB · 63 need attention · scanned just now"
old = {k: v for k, v in snap.items() if k != "attention"}
assert sc.snapshot_line(old, now=1000.0) == "7 comics · 3 series · 120.0 MB · scanned just now"
print("stats core OK")

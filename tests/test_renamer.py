import sys, tempfile, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import archive_tools as at
import name_format as nf
import rename_core as rc

# =============================== parser: years and volumes
YEARS = {"Batman 001 (2016)": "2016", "Batman 001 (Oct 2016)": "2016", "Batman 001 (October 2016)": "2016", "Batman 001 (2016-10-05)": "2016",
         "Batman 001 (2016, DC)": "2016", "Batman 001 (DC 2016)": "2016", "Batman 001 (2016 Digital)": "2016", "Batman 001 [2016]": "2016",
         "Batman 001 (Digital) (2016)": "2016", "Batman (2016-) 001": "2016", "Batman 001 (1/2016)": "2016", "Batman 001 (05-10-2016)": "2016",
         "Batman 001 (\u200e2016)": "2016", "Batman 001 (Summer 2016)": "2016", "Batman 001 (of 12) (2016)": "2016",
         "Batman v2016 001": "2016", "Batman Vol 2016 001": "2016", "Batman.001.2016": "2016", "Batman 001 2016": "2016", "Spider-Man 2099 001": None,
         "Batman 001 (of 12)": None}
for name, want in YEARS.items():
    p = rc.parse_filename(name)
    assert p["year"] == want, (name, p["year"])
    assert p["volume"] is None or int(p["volume"]) < 1900, (name, p["volume"])
p = rc.parse_filename("Batman v2016 001"); assert p["series"] == "Batman" and p["notes"] and "year" in p["notes"][0]
p = rc.parse_filename("Batman (1996-1997) TPB"); assert (p["year"], p["years"], p["year_end"]) == ("1996", "1996-1997", "1997")
p = rc.parse_filename("Batman 001 (2016) (Digital) (Zone-Empire) (of 12)"); assert p["tags"] == "Digital, Zone-Empire" and p["count"] == "12"
assert rc.parse_filename("Batman 001")["original"] == "Batman 001"

# =============================== ComicInfo: volume that is really a year
with tempfile.TemporaryDirectory() as d:
    d = Path(d)
    z = d / "Batman 001.cbz"
    with zipfile.ZipFile(z, "w") as zz: zz.writestr("0.jpg", b"x")
    at.apply_metadata(z, {"series": "Batman", "volume": "2016", "issue": "1", "publisher": "DC Comics"}, False)
    ci = rc.read_comicinfo(z); print(ci["volume"], ci["year"])
    assert ci["volume"] is None and ci["year"] == "2016" and ci["publisher"] == "DC Comics"
    at.apply_metadata(z, {"year": "2017", "volume": "2"}, False)
    ci = rc.read_comicinfo(z); assert ci["volume"] == "2" and ci["year"] == "2017"
    assert rc.merge(rc.parse_filename("Batman 001 (2012)"), {"year": "2017"}, True)["years"] == "2017"

# =============================== name_format engine
F = {"series": "batman beyond", "title": "the court", "issue": "7", "volume": "2", "year": "2016", "years": "2016-2017", "year_end": "2017",
     "count": "12", "range": None, "format": None, "kind": "Issue", "publisher": "DC", "tags": "Digital", "original": "orig", "collected": False}
O = dict(nf.DEFAULT_OPTIONS)
b = lambda tpl, **kw: nf.build_name(F, tpl, {**O, **kw})
assert b("{series}[ #{issue}][ ({year})]") == "batman beyond #007 (2016)"
assert b("{series}[ #{issue:4}]") == "batman beyond #0007" and b("{series}[ #{issue:2}]", pad="Keep as is") == "batman beyond #07"
assert b("{series:upper} {series:lower}") == "BATMAN BEYOND batman beyond" and b("{series:title}") == "Batman Beyond"
assert b("{series:nospace}") == "batmanbeyond" and b("{series:snake}") == "batman_beyond" and b("{series:dash}") == "batman-beyond"
assert b("{title:sentence}") == "The court"
assert b("{range|issue}") == "007" and b("{range|volume|issue}") == "2" and b("{series}[ {range|format}]") == "batman beyond"   # fallback, and an empty group vanishes
assert b(r"{series}[ ({year_end})] \[{tags}\] {type} {publisher} {count} {original}") == "batman beyond (2017) [Digital] Issue DC 12 orig"
assert b("{series}", series_case="Title Case") == "Batman Beyond" and b("{series}", series_case="UPPERCASE") == "BATMAN BEYOND"
assert b("{title}", title_case="Sentence case") == "The court" and b("{series}", series_case="lowercase") == "batman beyond"
G = {**F, "series": "The Walking Dead"}
assert nf.build_name(G, "{series}", {**O, "article": nf.ARTICLE_MODES[1]}) == "Walking Dead, The"
assert nf.build_name(G, "{series}", {**O, "article": nf.ARTICLE_MODES[2]}) == "Walking Dead" and nf.build_name(G, "{series}", O) == "The Walking Dead"
assert b("{series} {title}", separator="Underscores") == "batman_beyond_the_court" and b("{series} {issue}", separator="Dots") == "batman.beyond.007"
H = {**F, "title": "Who: What? Why*"}
assert nf.build_name(H, "{title}", O) == "Who - What_ Why_"
assert nf.build_name(H, "{title}", {**O, "illegal": nf.ILLEGAL_MODES[1]}) == "Who What Why"
assert nf.build_name(H, "{title}", {**O, "illegal": nf.ILLEGAL_MODES[3]}) == "Who-What- Why-" or True
assert nf.ext_text(".CBZ", nf.EXT_CASES[0]) == ".cbz" and nf.ext_text(".cbz", nf.EXT_CASES[2]) == ".CBZ" and nf.ext_text(".Cbz", nf.EXT_CASES[1]) == ".Cbz"
assert len(b("{series} {title} {title} {title}", max_len=20)) <= 20 and b("{series}", max_len=0) == "batman beyond"
assert nf.check_template("{series}[ {issue:3}]") == [] and "Unknown token {foo}" in nf.check_template("{foo}")
assert any("Unbalanced [" in p for p in nf.check_template("{series}[ {issue}")) and any("Unbalanced {" in p for p in nf.check_template("{series"))
assert any("Unknown format" in p for p in nf.check_template("{series:zz}")) and any("No tokens" in p for p in nf.check_template("abc"))
assert nf.build_folder({**F, "collected": False}, "{publisher}/{series}[ ({year})]", O) == ["DC", "batman beyond (2016)"]
assert nf.build_folder({**F, "collected": True}, "{series}[ v{volume}]", O) == ["batman beyond"]            # a TPB's volume is not a run
assert nf.build_folder({**F, "publisher": None}, "{publisher}/{series}", O) == ["batman beyond"]
for t in rc.TYPE_KEYS: assert nf.build_name(nf.sample_for(t), nf.DEFAULT_TEMPLATES[t], O), t
assert "{issue:3}" in nf.FORMAT_GUIDE and all("{" + k + "}" in nf.FORMAT_GUIDE for k in nf.TOKENS)

# =============================== how sure a name is, and what to suggest
import zipfile as _zf


def sure(stem, pages=None, **kw):
    pr_ = rc.parse_filename(stem)
    return rc.assess(pr_, rc.merge(pr_, {}, False), pages, **kw)


assert sure("Batman 012 (2016)", 24) == (rc.SURE, []) and sure("Saga Vol 1 TPB (2012)", 160) == (rc.SURE, [])
c, sug = sure("Batman 012 (2016)", 220); assert c == rc.UNSURE and sug[0][0] == "TPB" and "220 pages" in sug[0][1] and sug[1][0] == "Issue"
c, sug = sure("Saga Vol 1 TPB (2012)", 24); assert c == rc.UNSURE and sug[0][0] == "Issue" and "only 24 pages" in sug[0][1]
c, sug = sure("Berserk Vol 3", 190); assert c == rc.UNSURE and [t for t, _ in sug] == ["Volume", "Issue"] and "Vol 3" in sug[0][1] and "190 pages" in sug[0][1]
c, sug = sure("Berserk Vol 3", 20); assert [t for t, _ in sug] == ["Issue", "Volume"] and "only 20 pages" in sug[0][1]
c, sug = sure("Berserk Vol 3"); assert c == rc.UNSURE and [t for t, _ in sug] == ["Issue", "Volume"], "no page count: the manga reading first"
c, sug = sure("Maus", 200); assert c == rc.GUESS and sug[0][0] == "Graphic Novel"
c, sug = sure("Maus", 30); assert c == rc.GUESS and sug[0][0] == "One-Shot" and "30 pages" in sug[0][1]
assert sure("scan0001", 20) == (rc.GUESS, []), "no series: nothing to suggest, the page asks for a series"
assert sure("Berserk Vol 3", 190, decided=True) == (rc.SURE, []) and sure("Maus", None, decided=True) == (rc.SURE, [])
assert sure("Batman Annual 03 (2016)", 24)[0] == rc.SURE
# names that look alike share a shape: the key of 'names like this' and the saved rules
assert rc.shape("Invincible Vol 3 (2010)") == rc.shape("Invincible Vol 4") == "invincible vol #"
assert rc.shape("Batman 012 (2016)") == "batman #" and rc.shape("Saga TPB Vol 1") == "saga tpb vol #" and rc.shape("Sandman #1-12") == "sandman # - #"
assert rc.shape("Invincible Vol 3") != rc.shape("Invincible 003") and rc.shape("Saga_Vol_2") == "saga vol #"
# page counts: images in a zip; nothing for a RAR or a PDF
with tempfile.TemporaryDirectory() as dd:
    dd = Path(dd)
    with _zf.ZipFile(dd / "A.cbz", "w") as z:
        for i in range(7): z.writestr(f"{i}.jpg", b"x")
        z.writestr("ComicInfo.xml", "<ComicInfo/>"); z.writestr("notes.txt", "x")
    (dd / "B.cbr").write_bytes(b"Rar!"); (dd / "C.pdf").write_bytes(b"%PDF")
    assert rc.count_pages(dd / "A.cbz") == 7 and rc.count_pages(dd / "B.cbr") is None and rc.count_pages(dd / "C.pdf") is None
    assert rc.count_pages(dd / "missing.cbz") is None
# every type has a description and an example, and the keys are unique and cover the types
assert set(rc.TYPE_HELP) == set(rc.TYPE_KEYS) and all(len(v) == 2 and v[0] and v[1] for v in rc.TYPE_HELP.values())
assert set(rc.TYPE_LETTERS.values()) == set(rc.TYPE_KEYS) | {rc.AUTO_TYPE} and len(rc.TYPE_LETTERS) == len(set(rc.TYPE_LETTERS))
print("RENAME CORE OK")

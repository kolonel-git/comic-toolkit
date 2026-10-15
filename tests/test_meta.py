import sys, tempfile, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from rename_core import parse_filename, read_comicinfo
import name_format as nf
import archive_tools as at

cases = {
    "Batman 03 (of 12) (2016)": ("03", "12", "2016"),
    "Saga #3 (3 of 54)": ("3", "54", None),
    "Watchmen 05 [of 12]": ("05", "12", None),
    "Saga 012 (2012) (Digital)": ("012", None, "2012"),
    "X (of 0) 01": ("01", None, None),
}
for stem, (issue, count, year) in cases.items():
    p = parse_filename(stem)
    assert (p["issue"], p["count"], p["year"]) == (issue, count, year), (stem, p)
    print("ok", stem, "->", p["series"], p["issue"], p["count"], p["year"])

# renamer unaffected by the new key
f = parse_filename("Batman 03 (of 12) (2016)")
print(nf.build_name(f, nf.PRESETS["Series #001 (2016)"], nf.DEFAULT_OPTIONS))

with tempfile.TemporaryDirectory() as d:
    d = Path(d)
    z = d / "a.cbz"
    with zipfile.ZipFile(z, "w") as zz:
        for i in range(3):
            zz.writestr(f"{i}.jpg", b"x")
    at.apply_metadata(z, {"series": "Batman", "count": "12", "genre": "Superhero, Crime",
                          "series_group": "Bat Family", "alternate_series": "Court", "publisher": "DC"}, False)
    ci = read_comicinfo(z)
    print(ci)
    assert ci["count"] == "12" and ci["genre"] == "Superhero, Crime" and ci["series_group"] == "Bat Family"
    assert ci["alternate_series"] == "Court" and ci["publisher"] == "DC" and ci["series"] == "Batman"
    # second write keeps earlier fields
    at.apply_metadata(z, {"issue": "3"}, False)
    ci = read_comicinfo(z)
    assert ci["issue"] == "3" and ci["publisher"] == "DC"
print("core OK")

print("meta OK")

"""End-to-end tests for scripts/parse_takeout_maps.py --dedupe.

Stdlib only: run with `python3 -m unittest discover tests`.
"""
import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "parse_takeout_maps.py"

# CID 0x52963a5addd52a99 == 5951008119559891609
FTID_URL = ("https://www.google.com/maps/place/Bocca/data=!4m2!3m1!1s"
            "0x48761b2d1a5b8e71:0x52963a5addd52a99")
CID_URL = "http://maps.google.com/?cid=5951008119559891609"


def _write_csv(path: Path, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows([("Title", "Note", "URL", "Comment"), *rows])


def _run(folder: Path, *flags):
    out = subprocess.run([sys.executable, "-I", str(SCRIPT), str(folder), *flags],
                         check=True, capture_output=True, text=True)
    return json.loads(out.stdout)


class DedupeTest(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        root = Path(self._td.name)
        _write_csv(root / "Starred places.csv", [
            ("Bocca", "pasta", FTID_URL, ""),
            # Different venue, same name, different city.
            ("Dishoom", "", "https://www.google.com/maps/place/Dishoom/@51.5246,-0.0769,17z", ""),
        ])
        _write_csv(root / "Want to go.csv", [
            ("Bocca", "", FTID_URL, ""),
            ("Dishoom", "", "https://www.google.com/maps/place/Dishoom/@55.9533,-3.1883,17z", ""),
            # Same venue as the Starred Dishoom, URL differs but coords match.
            ("Dishoom", "breakfast", "https://www.google.com/maps/place/Dishoom/@51.52461,-0.07688,15z", ""),
        ])
        (root / "Saved Places.json").write_text(json.dumps({
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [-0.1337, 51.5101]},
                "properties": {"google_maps_url": CID_URL,
                               "location": {"name": "Bocca", "address": "1 Soho Sq"}},
            }],
        }), encoding="utf-8")
        self.root = root

    def tearDown(self):
        self._td.cleanup()

    def test_without_dedupe_keeps_every_row(self):
        self.assertEqual(len(_run(self.root)), 6)

    def test_merges_same_venue_across_lists_and_keeps_coords(self):
        bocca = [p for p in _run(self.root, "--dedupe") if p["name"] == "Bocca"]
        self.assertEqual(len(bocca), 1)
        b = bocca[0]
        self.assertEqual(sorted(b["source_lists"]),
                         ["Saved Places", "Starred places", "Want to go"])
        self.assertEqual((b["lat"], b["lng"]), (51.5101, -0.1337))
        self.assertEqual(b["address"], "1 Soho Sq")
        self.assertEqual(b["note"], "pasta")

    def test_keeps_different_venues_that_share_a_name(self):
        dishoom = [p for p in _run(self.root, "--dedupe") if p["name"] == "Dishoom"]
        self.assertEqual(len(dishoom), 2)
        london = next(p for p in dishoom if round(p["lat"]) == 52)
        self.assertEqual(sorted(london["source_lists"]), ["Starred places", "Want to go"])
        self.assertEqual(london["note"], "breakfast")

    def test_different_place_ids_never_merge(self):
        feats = [  # 22 m apart, same name, distinct CIDs
            ("?cid=1", [-0.1, 51.5]), ("?cid=2", [-0.1, 51.5002]),
            # Takeout's "no location" placeholder is [0, 0], not a real point.
            ("?cid=3", [0, 0]), ("?cid=4", [0, 0]),
        ]
        (self.root / "Saved Places.json").write_text(json.dumps({
            "type": "FeatureCollection",
            "features": [{"type": "Feature",
                          "geometry": {"type": "Point", "coordinates": c},
                          "properties": {"google_maps_url": "http://maps.google.com/" + q,
                                         "location": {"name": "Pret"}}}
                         for q, c in feats],
        }), encoding="utf-8")
        pret = [p for p in _run(self.root, "--dedupe") if p["name"] == "Pret"]
        self.assertEqual(len(pret), 4)
        self.assertEqual(sum(p["lat"] is None for p in pret), 2)

    def test_no_list_membership_or_coords_lost(self):
        raw, merged = _run(self.root), _run(self.root, "--dedupe")
        pairs = lambda ps, key: {(p["name"], lst) for p in ps for lst in key(p)}
        self.assertEqual(pairs(raw, lambda p: [p["source_list"]]),
                         pairs(merged, lambda p: p["source_lists"]))
        self.assertEqual({p["name"] for p in raw if p["lat"] is not None},
                         {p["name"] for p in merged if p["lat"] is not None})


if __name__ == "__main__":
    unittest.main()

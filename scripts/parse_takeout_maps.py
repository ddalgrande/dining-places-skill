#!/usr/bin/env python3
"""Parse a Google Takeout Maps / Saved export into a normalized places list.

Google Takeout "Saved" gives ONE CSV per list (Favourites, Want to go,
Starred places, and any custom lists) with columns roughly:
    Title, Note, URL, Comment            (no coordinates)
"Maps (your places)" / labelled places come as a GeoJSON FeatureCollection
that DOES carry coordinates + address.

This script globs an extracted Takeout folder, merges everything into one
clean list, and (optionally) extracts coordinates from the maps URL when
present. Cuisine / rating / opening hours are NOT in Takeout — enrich those
at advice-time with the places_search tool.

Usage:
    python3 parse_takeout_maps.py <folder> [--out saved_places.json] [--dedupe]

<folder> = path to the extracted Takeout export, or any folder that
contains the .csv / .json export files (it searches recursively).
"""
import argparse
import csv
import json
import math
import re
import sys
import tempfile
import zipfile
from pathlib import Path

# Coordinate patterns occasionally embedded in Google Maps URLs
_RE_3D4D = re.compile(r"!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)")
_RE_AT = re.compile(r"@(-?\d+\.\d+),(-?\d+\.\d+)")


# Google place identity: `?cid=<decimal>` (GeoJSON) or a feature id
# `0x<hex>:0x<cid-hex>` (Saved CSV URLs). Both reduce to the same CID.
_RE_CID = re.compile(r"[?&]cid=(\d+)")
_RE_FTID = re.compile(r"(?:!1s|ftid=)0x[0-9a-fA-F]+:0x([0-9a-fA-F]+)")

# Same-name records closer than this are treated as one venue.
_SAME_VENUE_METRES = 50


def coords_from_url(url: str):
    if not url:
        return None, None
    m = _RE_3D4D.search(url) or _RE_AT.search(url)
    if m:
        return float(m.group(1)), float(m.group(2))
    return None, None


def cid_from_url(url: str):
    if not url:
        return None
    m = _RE_CID.search(url)
    if m:
        return int(m.group(1))
    m = _RE_FTID.search(url)
    if m and int(m.group(1), 16):
        return int(m.group(1), 16)
    return None


def _metres_apart(a, b):
    dlat = (a["lat"] - b["lat"]) * 111_320
    dlng = (a["lng"] - b["lng"]) * 111_320 * math.cos(math.radians(a["lat"]))
    return math.hypot(dlat, dlng)


def merge_duplicates(places):
    """Merge records that are the same venue, keeping every list membership.

    Two records are the same venue when they share a Google place CID, the
    exact same maps URL, or the same name within _SAME_VENUE_METRES. A name
    match alone is never enough: different venues can share a name.
    """
    parent = list(range(len(places)))
    # A group holds at most one CID; distinct CIDs prove distinct venues.
    group_cid = [cid_from_url(p["maps_url"]) for p in places]

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        ri, rj = find(i), find(j)
        if ri == rj:
            return
        lo, hi = min(ri, rj), max(ri, rj)
        parent[hi] = lo
        group_cid[lo] = group_cid[lo] or group_cid[hi]

    def cids_conflict(i, j):
        ci, cj = group_cid[find(i)], group_cid[find(j)]
        return bool(ci and cj and ci != cj)

    first_by_key = {}
    by_name = {}
    for i, p in enumerate(places):
        cid = group_cid[i]
        keys = ([("cid", cid)] if cid else []) + (
            [("url", p["maps_url"].strip())] if p["maps_url"].strip() else [])
        for k in keys:
            if k in first_by_key:
                union(first_by_key[k], i)
            else:
                first_by_key[k] = i
        if p["lat"] is not None and p["lng"] is not None:
            by_name.setdefault(p["name"].strip().lower(), []).append(i)
    for idxs in by_name.values():
        for a, i in enumerate(idxs):
            for j in idxs[a + 1:]:
                if (_metres_apart(places[i], places[j]) <= _SAME_VENUE_METRES
                        and not cids_conflict(i, j)):
                    union(i, j)

    groups = {}
    for i in range(len(places)):
        groups.setdefault(find(i), []).append(places[i])
    merged = []
    for recs in groups.values():  # dict order == first-seen order
        m = dict(recs[0])
        m["source_lists"] = list(dict.fromkeys(r["source_list"] for r in recs))
        m["note"] = " | ".join(dict.fromkeys(r["note"] for r in recs if r["note"]))
        m["address"] = next((r["address"] for r in recs if r["address"]), "")
        # GeoJSON coords (they come with an address) beat URL viewport coords.
        with_coords = (next((r for r in recs if r["lat"] is not None and r["address"]), None)
                       or next((r for r in recs if r["lat"] is not None), None))
        if with_coords:
            m["lat"], m["lng"] = with_coords["lat"], with_coords["lng"]
        m["maps_url"] = next((r["maps_url"] for r in recs if r["maps_url"]), "")
        merged.append(m)
    return merged


def parse_csv(path: Path):
    """One Takeout 'Saved' list = one CSV. Filename (minus .csv) is the list name."""
    out = []
    list_name = path.stem
    def _flat(v):
        # DictReader puts overflow columns (e.g. unquoted commas in a URL)
        # into a list under restkey; rejoin so we never choke on a list.
        if isinstance(v, list):
            return ",".join(x for x in v if x)
        return (v or "").strip()

    try:
        with path.open(newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f, restkey="_overflow")
            for raw in reader:
                r = {(k or "").strip().lower(): _flat(v) for k, v in raw.items()}
                name = r.get("title") or r.get("name") or ""
                if not name:
                    continue
                url = r.get("url") or ""
                if r.get("_overflow"):  # stitch a comma-split URL back together
                    url = f"{url},{r['_overflow']}" if url else r["_overflow"]
                lat, lng = coords_from_url(url)
                out.append({
                    "name": name,
                    "source_list": list_name,
                    "note": r.get("note") or r.get("comment") or "",
                    "address": "",
                    "lat": lat,
                    "lng": lng,
                    "maps_url": url,
                })
    except Exception as e:  # noqa: BLE001
        print(f"  ! skipped {path.name}: {e}", file=sys.stderr)
    return out


def parse_geojson(path: Path):
    """Labelled / saved places GeoJSON FeatureCollection (carries coordinates)."""
    out = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        print(f"  ! skipped {path.name}: {e}", file=sys.stderr)
        return out
    feats = data.get("features") if isinstance(data, dict) else None
    if not feats:
        return out
    for ft in feats:
        props = ft.get("properties", {}) or {}
        geom = ft.get("geometry", {}) or {}
        coords = (geom.get("coordinates") or [None, None]) + [None, None]
        lng, lat = coords[0], coords[1]
        if lat == 0 and lng == 0:  # Takeout's "no location available" placeholder
            lat = lng = None
        # Support both the current (lowercase) and legacy (Title-case) schemas
        loc = props.get("location") or props.get("Location") or {}
        name = (props.get("Title") or props.get("name")
                or loc.get("name") or loc.get("Business Name") or "")
        if not name:
            continue
        out.append({
            "name": name,
            "source_list": path.stem,
            "note": props.get("Comment") or props.get("comment") or "",
            "address": loc.get("address") or loc.get("Address") or "",
            "lat": lat,
            "lng": lng,
            "maps_url": (props.get("google_maps_url")
                         or props.get("Google Maps URL")
                         or loc.get("Google Maps URL") or ""),
        })
    return out


def gather_search_roots(path: Path, tmp: Path):
    """Return folders to search for CSV/JSON.

    Accepts any of:
      - a single .zip  (e.g. takeout-...-001.zip)
      - a folder containing one or more .zip files (My Drive/Takeout)
      - an already-extracted folder
    Every .zip found is extracted into `tmp` and included in the search roots,
    so partial/split Takeout archives all get merged.
    """
    roots = []
    zips = []
    if path.is_file() and path.suffix.lower() == ".zip":
        zips = [path]
    else:
        roots.append(path)                       # search loose files too
        zips = sorted(path.rglob("*.zip"))
    for i, z in enumerate(zips):
        dest = tmp / f"zip_{i}_{z.stem}"
        dest.mkdir(parents=True, exist_ok=True)
        try:
            with zipfile.ZipFile(z) as zf:
                zf.extractall(dest)
            roots.append(dest)
            print(f"  extracted {z.name}", file=sys.stderr)
        except Exception as e:  # noqa: BLE001
            print(f"  ! could not extract {z.name}: {e}", file=sys.stderr)
    return roots


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder",
                    help="A Takeout .zip, a folder of zips (My Drive/Takeout), "
                         "or an already-extracted folder (searched recursively)")
    ap.add_argument("--out", help="Write normalized JSON here (default: stdout)")
    ap.add_argument("--dedupe", action="store_true",
                    help="Merge records of the same venue (same place ID, URL, or "
                         "name within 50 m); keeps every source list")
    args = ap.parse_args()

    root = Path(args.folder)
    if not root.exists():
        sys.exit(f"Path not found: {root}")

    places = []
    with tempfile.TemporaryDirectory() as td:
        search_roots = gather_search_roots(root, Path(td))
        for sr in search_roots:
            for csv_path in sorted(sr.rglob("*.csv")):
                places += parse_csv(csv_path)
            for js in sorted(set(list(sr.rglob("*abelled*.json"))
                                 + list(sr.rglob("*aved*laces*.json")))):
                places += parse_geojson(js)

    for p in places:
        p["source_lists"] = [p["source_list"]]
    if args.dedupe:
        before = len(places)
        places = merge_duplicates(places)
        print(f"  merged {before} records into {len(places)} places", file=sys.stderr)

    blob = json.dumps(places, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(blob, encoding="utf-8")
        by_list: dict[str, int] = {}
        for p in places:
            for lst in p["source_lists"]:
                by_list[lst] = by_list.get(lst, 0) + 1
        print(f"Parsed {len(places)} places across {len(by_list)} lists -> {args.out}")
        for k, v in sorted(by_list.items(), key=lambda x: -x[1]):
            print(f"  {v:4d}  {k}")
    else:
        print(blob)


if __name__ == "__main__":
    main()

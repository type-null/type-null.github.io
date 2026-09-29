#!/usr/bin/env python3
"""Import the original timeline without guessing missing releases or dates.

Uses only the Python standard library. Comments are ignored by HTMLParser;
the original position of an image in its year/month cell is authoritative.
"""

import argparse
from collections import Counter
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlparse


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/legacy-timeline.html.txt"
DESTINATION = ROOT / "content/_data/card-sets.json"
ERA_LABELS = {
    "original": "Original Series", "neo": "Neo", "VS": "VS", "Web": "Web",
    "e": "e-Card", "ADV": "ADV", "PCG": "PCG", "DP": "Diamond & Pearl",
    "DPt": "Platinum", "LEGEND": "LEGEND", "BW": "Black & White",
    "XY": "XY", "SM": "Sun & Moon", "S": "Sword & Shield",
    "SV": "Scarlet & Violet", "M": "Mega Evolution",
}


class TimelineParser(HTMLParser):
    """Read table cells; intentionally ignore images outside the release table."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self.images = []
        self.stylesheets = []
        self.in_table = False
        self.table_count = 0
        self.row = None
        self.cell = None
        self.link = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "img":
            self.images.append(attrs)
        if tag == "link" and "stylesheet" in attrs.get("rel", "").split():
            self.stylesheets.append(attrs["href"])
        if tag == "table" and "m-tbl-nml" in attrs.get("class", "").split():
            if self.in_table:
                raise ValueError("Nested timeline table")
            self.in_table = True
            self.table_count += 1
        if not self.in_table:
            return
        if tag == "tr":
            if self.row is not None:
                raise ValueError("Unclosed timeline row")
            self.row = []
        elif tag in ("td", "th"):
            if self.row is None or self.cell is not None:
                raise ValueError("Malformed timeline cell")
            if any(attrs.get(key, "1") != "1" for key in ("colspan", "rowspan")):
                raise ValueError("Merged timeline cells need an explicit month mapping")
            self.cell = {"text": "", "images": []}
            self.row.append(self.cell)
        elif tag == "a":
            self.link = attrs.get("href")
        elif tag == "img" and self.cell is not None:
            self.cell["images"].append({**attrs, "href": self.link})

    def handle_endtag(self, tag):
        if not self.in_table:
            return
        if tag == "table":
            self.in_table = False
        elif tag == "tr":
            if self.row is None:
                raise ValueError("Unexpected row close")
            self.rows.append(self.row)
            self.row = None
        elif tag in ("td", "th"):
            self.cell = None
        elif tag == "a":
            self.link = None

    def handle_data(self, data):
        if self.cell is not None:
            self.cell["text"] += data


def parse_timeline(html):
    parser = TimelineParser()
    parser.feed(html)
    parser.close()
    if parser.table_count != 1 or parser.in_table or parser.row is not None:
        raise ValueError("Expected exactly one complete timeline table")
    sets, years, ids = [], [], set()
    for row in parser.rows:
        year_text = row[0]["text"].strip() if row else ""
        if not re.fullmatch(r"\d{4}", year_text):
            if any(cell["images"] for cell in row):
                raise ValueError("Release images in a row without a year")
            continue  # Month header.
        year = int(year_text)
        if year in years:
            raise ValueError(f"Duplicate year row: {year}")
        years.append(year)
        if len(row) != 13:
            raise ValueError(f"{year}: expected 12 months, found {len(row) - 1}")
        if row[0]["images"]:
            raise ValueError(f"{year}: release image is in the year cell")
        for month, cell in enumerate(row[1:], start=1):
            for image in cell["images"]:
                path = Path(image.get("src", ""))
                if not str(path).startswith("/assets/images/card/set-package-jp/"):
                    raise ValueError(f"Unexpected package image: {path}")
                era = path.parent.name
                if era not in ERA_LABELS:
                    raise ValueError(f"Unknown era: {era}")
                name = image.get("alt", "").strip()
                if not name:
                    raise ValueError(f"Missing release name: {path}")
                code = re.sub(r"-key$", "", path.stem)
                key = re.sub(r"[^a-z0-9]+", "-", f"{era}-{code}".lower()).strip("-")
                identifier = f"{year}-{month:02d}-{key}"
                if identifier in ids:
                    raise ValueError(f"Duplicate release identity: {identifier}")
                ids.add(identifier)
                url = (image.get("href") or "").strip()
                if url in ("", "#"):
                    url = None
                elif urlparse(url).scheme not in ("http", "https"):
                    raise ValueError(f"Unsafe or non-absolute release URL: {url}")
                sets.append({
                    "id": identifier, "year": year, "month": month,
                    "name": name, "era": era, "code": code,
                    "image": str(path), "url": url,
                })
    if not sets:
        raise ValueError("Timeline has no releases")
    dates = [f"{item['year']}-{item['month']:02d}" for item in sets]
    present_eras = {item["era"] for item in sets}
    return {
        "metadata": {
            "title": "Japanese Pokémon card release archive",
            "description": "An author-maintained snapshot of Japanese booster releases, imported from the original timeline.",
            "coverageStart": min(dates), "coverageEnd": max(dates),
            "source": "/card/2024/02/timeline.html",
            "archivedSource": "docs/legacy-timeline.html.txt",
            "precision": "month", "recordCount": len(sets),
            "datePolicy": "Year and month preserve the original table cells; official release dates have not been independently verified.",
            "codePolicy": "Codes are original image filename stems with a trailing -key removed, not verified product identifiers.",
            "coverageNote": "This is an incomplete historical snapshot, not a live release calendar. Empty months mean no entry was recorded; they do not establish that no product was released. The final year is partial.",
            "notes": [
                "Paired releases remain individual entries in the same month.",
                "Placeholder links are null; original images and Japanese names are preserved.",
                "The 2025 August cell contains Mega Brave and Mega Symphonia, so an archive-wide claim that August is always empty would be false.",
                "VS and Web images exist in the repository but have no actual entries in the original table; they are not silently added.",
            ],
        },
        "eras": [{"id": era, "label": label} for era, label in ERA_LABELS.items() if era in present_eras],
        "years": sorted(years),
        "sets": sets,
    }, parser


def audit(source, parser, data):
    def asset_path(url, base=ROOT):
        parsed = urlparse(url)
        if parsed.scheme or parsed.netloc:
            return None
        path = (ROOT if parsed.path.startswith("/") else base) / unquote(parsed.path).lstrip("/")
        if path.is_file():
            return path
        # Historical chrome moved out of the published assets tree. Its bytes
        # still belong in the reproducible baseline of the original page.
        try:
            archived = ROOT / "archive/original-assets" / path.resolve().relative_to(ROOT.resolve())
        except ValueError:
            return path
        return archived if archived.is_file() else path

    image_urls = sorted({item.get("src", "") for item in parser.images})
    image_paths = [(url, asset_path(url)) for url in image_urls]
    css_paths = [(url, asset_path(url)) for url in parser.stylesheets]
    css_urls = set()
    for _, path in css_paths:
        if path and path.is_file():
            css_urls.update(re.findall(r"url\(\s*[\"']?([^\)\"']+)", path.read_text()))
    css_assets = [(url, asset_path(url, ROOT / "assets/css")) for url in sorted(css_urls)]
    local_css_assets = [(url, path) for url, path in css_assets if path is not None]
    return {
        "htmlBytes": source.stat().st_size,
        "stylesheetBytes": sum(path.stat().st_size for _, path in css_paths if path and path.is_file()),
        "yearRows": len(data["years"]), "releaseEntries": len(data["sets"]),
        "imageTags": len(parser.images), "uniqueImages": len(image_urls),
        "referencedImageBytes": sum(path.stat().st_size for _, path in image_paths if path and path.is_file()),
        "missingImages": [url for url, path in image_paths if not path or not path.is_file()],
        "imageAttributes": {key: dict(Counter(item.get(key, "missing") for item in parser.images)) for key in ("loading", "decoding", "width", "height")},
        "cssUniqueAssetReferences": len(css_urls),
        "cssAvailableAssetBytes": sum(path.stat().st_size for _, path in local_css_assets if path.is_file()),
        "cssMissingAssets": [url for url, path in local_css_assets if not path.is_file()],
        "entriesByEra": dict(Counter(item["era"] for item in data["sets"])),
        "linkedEntries": sum(item["url"] is not None for item in data["sets"]),
        "occupiedMonths": len({(item["year"], item["month"]) for item in data["sets"]}),
    }


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--source", type=Path, default=SOURCE)
    cli.add_argument("--output", type=Path, default=DESTINATION)
    cli.add_argument("--audit", action="store_true", help="Print measurements without rewriting data")
    args = cli.parse_args()
    data, parser = parse_timeline(args.source.read_text(encoding="utf-8"))
    if args.audit:
        print(json.dumps(audit(args.source, parser, data), indent=2, ensure_ascii=False))
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Imported {len(data['sets'])} releases into {args.output}")


if __name__ == "__main__":
    main()

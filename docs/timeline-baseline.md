# Timeline baseline and data migration

The preserved input is [`legacy-timeline.html.txt`](legacy-timeline.html.txt), copied byte-for-byte from `card/2024/02/timeline.html` before renovation. The original route remains `/card/2024/02/timeline.html`. Its SHA-256 is `5a87f1c25d7a5fe528514a19093602e4c0cfc53405f16e6170adac63f20983de`.

## Reproduce the baseline

```sh
python3 scripts/import-timeline.py --audit
python3 -m unittest discover -s tests -p 'test_timeline_import.py' -v
```

The audit measures local, uncompressed resource sizes and actual parsed HTML elements. It is **not** a measured browser load time or compressed network transfer; actual CSS asset requests depend on which selectors apply. The parser excludes HTML comments, including the commented-out 2027 row.

| Baseline | Measurement |
| --- | ---: |
| Timeline HTML | 93,391 bytes |
| Shared `style.css` | 689,124 bytes |
| Actual year rows | 31 (1996–2026) |
| Actual release entries | 186 |
| Occupied year/month cells | 153 |
| Single / pair / triple cells | 121 / 31 / 1 |
| Image tags / unique image paths | 191 / 190 |
| Unique referenced image source bytes | 192,957,452 (184.0 MiB) |
| Missing HTML image files | 0 |
| Images with `loading`, `decoding`, `width`, or `height` attributes | 0 for each attribute |
| Unique CSS `url()` references | 32 |
| Missing local files referenced by CSS | 25 |
| Available CSS-referenced local files | 6 (20,037 bytes) |
| Inline CSS data URLs | 1 |
| Release links / placeholder links | 39 / 147 |

This explains a concrete source of slowness: the HTML eagerly references approximately 184 MiB of source images and gives the browser no intrinsic dimensions. The 13-column table preserves month alignment well but couples pattern recognition to the dimensions and loading cost of the package artwork. The renovated view should retain year/month alignment while making full-size artwork optional and generating small derivatives for browsing.

The inherited CSS contains missing icons, image backgrounds, and product-menu imagery from the original site's paths. Those references are measurable defects, but this audit does not claim every absent file was requested on this page. The legacy HTML also contains 15 `dataLayer` references without any script tags defining it; new navigation should not depend on those inherited click handlers.

## Data contract

`content/_data/card-sets.json` contains:

- `metadata`: title, description, `coverageStart`, `coverageEnd`, `precision: "month"`, original route and archived source, record count, and explicit coverage/date/code caveats.
- `eras`: chronological `{id, label}` pairs for represented eras.
- `years`: ascending integer year values, including the source's empty months.
- `sets`: individual `{id, year, month, name, era, code, image, url}` records in the source's descending-year, ascending-month order.

Names, images, year/month placement, and actual URLs are preserved. Empty or `#` links become JSON `null`. `code` is the original image filename stem with a trailing `-key` removed; it is an archive label, **not** an independently verified official product identifier. IDs combine year/month, era, and normalized image code and are validated as unique. The site build may add optimized-thumbnail fields without changing source data.

The importer uses Python's standard-library HTML parser, requires exactly 12 cells after each year label, preserves paired and triple releases individually, ignores commented markup, rejects malformed/merged cells and unsafe URLs, and never infers missing releases from files in the assets directory.

## Coverage and anomalies

The earliest recorded cell is October 1996 and the latest September 2026. This is the existing author's curated historical snapshot. Importing it does not independently establish official release dates, completeness, or that a blank cell means no release. The 2026 row has January, March, May, and September entries; it is partial. A coverage end is not a claim that everything up to that month is represented.

The original narrative's broad August observation must not be generalized across the archive: August has entries for 2002 (e-Card), 2018 and 2019 (Sun & Moon), and the Mega Brave / Mega Symphonia pair in 2025 (Mega Evolution). Any seasonal observation should identify its era and be described as an observation of recorded entries.

The repository contains VS and Web package assets, but the original table contains no actual entries in those eras. They remain absent from the imported dataset. There are no duplicate package paths and no missing package image files in the recorded entries.

| Era | Entries |
| --- | ---: |
| Original | 6 |
| Neo | 4 |
| e-Card | 5 |
| ADV | 5 |
| PCG | 9 |
| Diamond & Pearl | 9 |
| Platinum | 4 |
| LEGEND | 5 |
| Black & White | 17 |
| XY | 23 |
| Sun & Moon | 36 |
| Sword & Shield | 30 |
| Scarlet & Violet | 25 |
| Mega Evolution | 8 |

## Preservation checks

The regression suite pins a digest of **all** 186 original year/month/name/image/URL tuples, verifies the import command is reproducible, checks package file existence, and checks the exact month-occupancy distribution. Targeted adversarial cases cover comments, unrelated decoration, paired releases, HTML entity decoding, missing/merged month cells, duplicate records, unsafe links, unknown eras, missing names, and incomplete tables. The initial committed JSON matches this import exactly; the archive tests remain independent of future editorial additions to the live dataset.

Regenerate the snapshot only when intentionally re-importing historical HTML:

```sh
python3 scripts/import-timeline.py
```

For ongoing editorial updates, edit the JSON dataset directly. Re-importing the archive intentionally restores the original snapshot and overwrites those edits. Keep the archived HTML unchanged so historical preservation checks remain meaningful.

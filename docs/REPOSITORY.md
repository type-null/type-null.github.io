# Repository map

Write posts in `content/`. The HTML visible in the browser is generated from those sources and shared templates.

| Location | Purpose |
| --- | --- |
| `content/<topic>/<post>/index.md` | Post metadata and Markdown; keep the post's images, PDFs, and videos in the same folder. |
| `content/<topic>/_topic.yml` | Optional topic name, order, color, icon, and description. |
| `content/_data/card-sets.json` | Timeline records; their original artwork remains under `assets/images/card/set-package-jp/`. |
| `templates/` | Shared page layouts and components. |
| `assets/` | Active styles, scripts, local fonts, artwork, and default covers. |
| `legacy/` | Maintained source HTML for the three standalone tools and the minimal map page. |
| `archive/legacy-pages/` | Frozen original homepage, 404, résumé, timeline, and soccer pages. These are historical records, not build inputs, and are excluded from the generated website. |
| `examples/` | Copyable Markdown templates with metadata. |
| `scripts/` | Build, import, and verification tools. |
| `tests/` | Regression tests and small local media fixtures. |
| `_site/` | Generated deployment artifact; rebuild rather than edit. |
| `docs/reference/` | Official Pokémon homepage screenshots used for visual comparison. |
| `docs/qa/` | Local screenshots and measurements from verification. |
| `archive/original-assets/` | Unused original materials, preserved locally with an integrity manifest. Excluded from the generated deployment artifact. |

Start with [Writing a post](WRITING.md). Creating a topic/post folder and saving `index.md` supplies the source; running the build updates the rendered pages and their navigation links. Folder changes still require a build.

The standalone tool sources are `legacy/card/toolkit.html` and the two game pages in `legacy/sports/2025/`. The minimal `legacy/florida/map.html` is retained to preserve its existing URL. Those are the four maintained legacy pages the builder can publish.

The original résumé HTML is preserved under `archive/legacy-pages/resume/2025/`; its complete current page is generated from `content/notes/about/index.md` and stays unlisted. The other frozen original pages also live under `archive/legacy-pages/`. Removing a migrated Markdown post cannot cause one of these snapshots to reappear on the website, because that archive is not a source for published pages. The former HTTP preview helper is preserved under `archive/developer-tools/` but is not needed for local browsing.

Publication and writing history live with the post in frontmatter: `date` is its publication day, `created` is first written, and `updated` is last revised. The optional history fields accept dates or timestamps with explicit time zones and default to `date`. Rebuilding does not infer dates from Git or file modification times. See the [writing-date tutorial](WRITING.md#record-first-writing-and-later-revisions).

## Asset cleanup and preservation

The original active asset tree contained **606 files / 363,680,649 bytes**. A reference audit covered rendered HTML, Markdown metadata, template defaults, timeline JSON, JavaScript references, CSS imports and font URLs. It identified unused materials that can be retained outside the runtime tree.

**252 files / 164,399,576 bytes** moved to `archive/original-assets/`; the active source asset tree decreased to approximately **199.3 MB** before later generated assets. The archive preserves original paths and SHA-256 hashes. This removes approximately **164.4 MB** from each build's otherwise unconditional asset copy without discarding any unique artwork.

The active tree still contains all 186 original timeline images, the complete résumé and portrait, default covers, current editorial source art, and locally served fonts with their licenses. Timeline thumbnails are generated separately for fast browsing; original artwork stays available locally for detailed views.

Use `python3 scripts/check-archive.py` to verify the archived files and timeline originals. [Archive instructions](../archive/original-assets/README.md) explain how to reuse one image or restore the full collection.

Python bytecode and macOS `.DS_Store` files are disposable local caches and are ignored. The `_site/` directory is reproducible build output. Keep original content and the local archive when making a backup.

The original timeline performance audit also checks `archive/original-assets/` when historical header images or stylesheets have moved there. Its baseline remains reproducible: relocating unused chrome does not silently reduce the measured original page size.

# Renovation decisions and verification

## What this project needed

The old homepage was a handful of links. Articles duplicated a large site shell, navigation linked to nonexistent categories, and the timeline mixed historical data into 93,391 bytes of HTML. The timeline's 191 eager image tags referenced 192,957,452 bytes of image files; its stylesheet alone was 689,124 bytes. See `timeline-baseline.md` for the reproducible resource audit and its limits. These are local resource sizes, not a fabricated network timing benchmark.

Acceptance criteria:

- Preserve all 186 real archive entries, their year/month cells, paired releases, images, and recorded source links.
- Keep pack artwork visible directly in the year-by-month calendar, including separate images for paired releases. Filtering and no-JavaScript use must preserve this visual comparison.
- Use optimized local artwork previews and retain original images for closer inspection. Measure requests, transfer, and layout against this artwork-visible design; the earlier image-free acceptance criterion is superseded.
- Topic folders automatically drive navigation and landing pages. Markdown produces complete articles, galleries, features, and tool pages; post-local media and supported embeds work.
- Show the newest six listed posts on the homepage and all listed posts in a complete news index. Add substantive new writing based on actual archive data and checked calculations.
- Deploy static files to GitHub Pages only; no application server, database, external runtime assets, or other hosting target.
- Preserve known public URLs. Generate a homepage, themed 404, metadata, feed, sitemap, search, and sharing controls.
- New layouts must fit 320, 390, 768, and 1440 pixel viewports without page-level overflow. The timeline itself may scroll, keeping the shared month columns intact.
- Test real input data, errors and boundary conditions; generated links must resolve locally. Keep factual uncertainty separate from software validation.

## Design research

The visual target is the actual [Pokémon homepage](https://www.pokemon.co.jp/) UI: its navigation, prominent image links, page framing, and editorial hierarchy. The live homepage was inspected at desktop and mobile sizes; exact values and reference screenshots are recorded in [pokemon-reference.md](pokemon-reference.md). The [news index](https://www.pokemon.co.jp/info/) and [card landing page](https://www.pokemon.co.jp/card/) also inform the reusable writing layouts. Restore this site's existing custom Type Null logo and use its local artwork archive. All runtime materials remain local.

Pack artwork is part of the archive's information: it lets readers recognize sets and see patterns immediately. The calendar therefore shows artwork in every occupied month cell, rather than requiring a detail action to reveal it. Keep the month columns aligned across years and retain each image in paired releases. Mobile should preserve that comparison with scrolling contained inside the calendar. Apply the same shared page shell to the homepage, archive, articles, and tools.

## Architecture choice

Jekyll could publish Markdown directly through GitHub Pages but would need custom tooling for folder-derived navigation and the archive's image pipeline. Eleventy or Astro would also work, but add a JavaScript toolchain that was absent in this environment. This site needs no client framework or server application. A small Python build combines established Markdown, YAML, Jinja, and Pillow libraries; a GitHub Actions workflow publishes ordinary static files.

Source content lives in `content/`, shared presentation in `templates/` and `assets/`, and generated output in `_site/`. The build stages output atomically, validates local generated references, and keeps the last successful output when a build fails. It validates malformed front matter, duplicate paths, missing media, unsafe URL schemes, and traversal. The original archive assets remain available for preserved routes.

## Accuracy and discovered defects

The historical card data records months, not exact release days. Dates were preserved, not independently certified. Missing cells do not prove no release; 2026 is partial. The old August claim had counterexamples in the supplied data and is now qualified. The original soccer article was an unfinished scaffold containing unrelated sample copy; its actual research questions are retained without invented findings.

The existing probability tools had broken external integrations and mathematical defects. The repaired tools use exact distributions and native charts, run locally, validate inputs, and require no remote service. Trading Suits explicitly states the deck model inherited from the original final code; correctness conditional on that model is tested, not evidence that the model matches unknown external game rules. Probability Parlay keeps scores in the current browser, with a graceful fallback when storage is unavailable.

## Scope limits

The supported deployment is the domain root (`type-null.github.io`), not a GitHub project subdirectory. Folder renames generate new default routes; stable `permalink` values preserve old addresses. Handwritten links to intentionally changed addresses must be updated. External websites can refuse embedding. The build checks local generated links, not historical fact accuracy or external website availability. The content-less Florida stub is retained as an archive URL.

This workspace is an extracted directory without Git metadata. Renovation and local verification can be completed here; publishing requires pushing these files to the actual repository and selecting GitHub Actions in Pages settings.

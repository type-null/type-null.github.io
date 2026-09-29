# Verification record

Verified locally on September 29, 2026 using Chrome, including direct `file://` navigation without a server or browser security bypasses. The repository-root `index.html` and `_site/index.html` are identical generated homepages. `_site/` is the clean GitHub Pages artifact. Temporary HTTP compatibility fixtures shut down after testing; no preview server runs. Publication uses isolated Git checkouts. The three companion repositories have successful Pages deployments, and their actual live controls have been verified inside the articles.

## Acceptance and the direct-file baseline

The required behavior is a real root homepage; portable nested navigation, artwork, styles, fonts, search, tools and local media; six newest listed posts; an unlisted complete résumé; responsive layouts; and a clean GitHub Pages artifact. Source-folder renames must update both generated copies without deleting authored files or resurrecting archived pages. Writing/revision dates must survive rebuilding and copying independently of Git or filesystem timestamps.

The homepage follow-up also requires consistent reference-proportioned artwork/captions, left-aligned partial rows, visibly different topic compositions, and scroll-triggered pastel panels. Content must remain available without animation, JavaScript, or IntersectionObserver; reduced-motion changes must settle the design immediately. New sections must use real listed posts and local assets at 320–1440 px, with no horizontal document overflow.

Earlier HTTP-only tests missed the direct-file failure. Reproducing the user's actual opening method found that the old root `index.html` had **zero post cards, zero loaded stylesheets, and one failed resource**. The then-generated `_site/index.html` had six cards but **zero of 29 images decoded, zero loaded stylesheets, and 20 failed resources**. Both fell back to Times. Those are recorded browser observations, not inferred failures.

## Results

| Check | Result |
| --- | --- |
| Checked production build | 24 generated pages; 18 posts (17 listed, 1 unlisted); 3 topics; 1,427 local references resolved; root pages synchronized |
| Python regression suite | Final publishing integration: all 181 tests passed in 60.488 seconds, including Chrome checks. The earlier homepage baseline passed 152 tests; pack-preview and interactive-tool follow-ups are recorded below. |
| Live project embeds | Seven browser tests cover offline/no-JavaScript fallbacks, one article screenshot, independent website/source links, explicit loading from files, hosted visibility loading, ready-message sender/origin checks, modal controls, and intercepted 404 timeout/retry. Actual deployed apps were additionally used at 1440/390 px. |
| Florida research placeholder | Pinned first in the homepage INFORMATION strip, featured in the carousel, and indexed in Notes/search. The old `florida/map.html` links to the introduction. Three targeted tests verify generic announcement ordering and offline/no-JavaScript navigation. Substantive research-site work is paused; no research results were published. |
| Interactive article follow-up | 45 build tests and 2 media browser tests passed. After the final tool theme, all 9 strict direct-file tests, 3 tool UI tests and 7 game tests passed; this was targeted verification, not a rerun of the earlier full suite. |
| JavaScript timeline regressions | 17 groups passed against the actual dataset |
| Homepage | Exactly the newest six listed posts, in publication-date order; complete `/posts/` index; archive included in sitemap |
| Design comparison | Live Pokémon desktop/mobile homepage inspected; local fonts, original logo, header, asymmetric news grid, caption strips, and category labels compared visually; reference geometry checked in browser tests |
| Topic showcases and motion | Cards gallery, Sports feature/previews, and Notes dated rows use real listed posts; eight direct-file browser tests cover layout, links, one-shot masks/slides, offscreen gradient pausing, resize thresholds, reduced-motion changes, and static fallbacks; six build tests cover metadata, empty/new/renamed topics, selection limits and unpublished exclusion |
| Timeline preservation | All 186 original entries retained in their original month/year cells; 31 years; separate artwork for paired/triple entries; no visible set-code labels |
| Artwork browser workflow | All 186 previews decoded; natural page scrolling; filters, history, Japanese input, original-image dialog, sharing, print, mobile sticky labels, and legacy query URLs passed |
| No JavaScript | Homepage/news links and mobile menu remain usable; all 186 timeline images and 31 year rows present |
| Direct files | Root homepage, `_site`, and a complete copy in a folder containing spaces and Unicode exercised through `file://`; search, nested navigation, archive, 404 recovery, fonts, artwork, tools, and media work |
| Offline resources | Nine strict direct-file tests reject outside network requests and check failures, console errors, JavaScript errors, decoded images, loaded fonts, and requests escaping the copied package; HTTP compatibility checks also cover all generated routes |
| Responsive layouts | Actual routes fit 320, 390, 768, and 1440 px without document overflow; timeline scroll stays within its own horizontal region |
| Authoring tutorial | Exact minimal Markdown example built with actual templates; post automatically appears in discovery outputs; renaming a topic updates routes/navigation; generated output contains no Python or Markdown source |
| Root publication | Ownership-hash tests protect author edits, source files and symlinks; a complete build/rename/removal experiment checks stale pages and media disappear from both outputs while unrelated files remain |
| Writing dates | All seven templates show first-written/last-revised dates; explicit timezone offsets survive in HTML/search/sitemap; chronology and malformed offsets are rejected; touching a source and rebuilding leaves recorded dates unchanged |
| Cleanup | 252 original files / 164,399,576 bytes archived locally with verified hashes; every timeline original retained; deployment package reduced from about 351 MiB to 194 MiB |
| New writing | Earlier six essays retained, with archive counts checked against JSON and numerical examples checked independently. Added three project introductions and the explicitly unfinished Florida research placeholder. |
| Résumé | Complete biography, portrait, contact and research links retained at original URL; excluded from nav, homepage, news/topic indexes, related suggestions, search, RSS, and sitemap; noindex present |
| Real media | Actual local VP8 video decoded at 160 × 90 and played through `file://`; PDF frame navigation and complete fallback-file bytes verified; all three local interactive tool frames work |
| Embedded tools and new tabs | All three tools have a visible, keyboard-accessible new-tab button above the frame. Eighteen real popup workflows cover root, deployment and copied Unicode/space paths with and without JavaScript; interactive tests preserve parent state and verify independent popup inputs. Buttons fit at 320 and 390 px. |
| Native PDF appearance | Delivery/navigation checked; browser-native PDF rendering is not claimed visually verified |

The live reference has different campaign artwork and a seven-item news snapshot. This personal site retains its own content and shows six posts as requested. Visual comparison and measured component geometry do not establish pixel identity with those changing official campaigns.

Screenshots: [direct-file homepage](qa/home-desktop.png), [direct-file homepage mobile](qa/home-mobile.png), [direct-file timeline desktop](qa/timeline-desktop.png), and [direct-file timeline mobile](qa/timeline-mobile.png). The homepage [before/reference/after geometry](qa/home-layout-results.json) and standalone timeline [measurement JSON](qa/timeline-results.json) are retained alongside them. Homepage screenshots show the final static appearance with reduced motion.

The interactive article follow-up uses the shared blue pill button and aligns all three tool interiors with the site's white surfaces, quiet borders, dotted separators and local Noto Sans JP/Lato fonts. Before the change, the tools used system fonts with teal/navy styling. Final Chrome inspection at 1440, 390 and 320 px confirmed both local font faces loaded, no inner or outer horizontal overflow, and no external requests or JavaScript errors across all nine tool/viewport combinations. The [desktop calculator](qa/embed-desktop.png), [mobile calculator](qa/embed-mobile.png) and [before/after measurements](qa/embed-results.json) record the result. This is an adaptation of the shared site aesthetic, not a claim to reproduce an official calculator page. The complete `embeds` example in the writing guide was also built as an ordinary article using actual source discovery and templates.

## Independent project websites

Each application stays in its own repository. The blog owns Markdown and one offline preview per project article; each project owns its static website and Pages workflow. A source push rebuilds and deploys the app at the same URL, so the blog shows the current published version without copying app files or synchronizing repositories. Article layouts retain covers for listings without repeating an unlinked hero above the preview.

Hosted previews load when visible. Direct-file pages make no automatic project request; readers can choose **Use in this article** when online. Without JavaScript, the local screenshot and normal website/source links remain available. The frame replaces the screenshot only after a ready response from the expected origin and actual frame window. Hosted 404s and missing replies retain the screenshot and offer retry. Modal focus notices use the same origin/window check; these messages carry no research data.

Before removing the earlier blog copies, their runtime files were compared byte-for-byte with the sibling exports. Removing them eliminated **11,542,173 bytes** from content sources; the checked build also removed the root and `_site` copies. The unused importer was removed. Existing local calculators and games remain embedded as before.

The final parent run passed **181 blog tests**. The **17 timeline JavaScript groups** and independent probability oracle (**37,599 checks, 286 hands, 6,200 prize cases**) also passed. Archive verification matches all 252 preserved originals. Deterministic embed tests intercept remote fixtures; the separate [live measurements](qa/live-projects.json) use actual GitHub Pages applications and real filters at 1440/390 px. They recorded zero page errors, failed resources, unexpected remote hosts, or inner/outer horizontal overflow. See the [live database embed](qa/live-database-1440.png), [mobile calendar](qa/live-calendar-390.png), and [interactive regression results](qa/interactive-project-results.json). Ready times are individual local-browser samples, not general internet performance guarantees.

| Separate repository | Verified edition and limits | Successful remote deployment |
| --- | --- | --- |
| Calendar | 29 championship events; 85 repository regressions plus fresh-checkout and browser checks passed. Acquisition remains September 29, 2026 at 18:58:51 UTC. The store feed returned HTTP 403 without a saved cache, so partial-data status is explicit. Source builds preserve data freshness. | [Actions run](https://github.com/type-null/PTCG-calendar/actions/runs/36623048865) |
| Database | 48 English cards, all 48 local pictures. Fifteen build/export tests and five browser tests passed. Source builds update the viewer using its saved edition; updating the selected data is a deliberate export. This is not the complete collection. | [Actions run](https://github.com/type-null/PTCG-database/actions/runs/36623059052) |
| Squirrel exhibit | 3,023 observations; twelve parser/export/artifact tests and standalone browser checks passed. All repeated IDs and unknowns retained. Later park boundaries provide context rather than reconstructing the 2018 survey. Source builds regenerate the static exhibit. | [Actions run](https://github.com/type-null/Website-central-park-squirrel-tracker/actions/runs/36623067986) |

The workflows rebuild, check, and deploy only their own `site/` folder using official Pages actions. All three ordinary Pages URLs returned their real apps and passed live browser checks. The [publishing guide](PROJECTS.md) explains future updates. The Florida research task is paused, its study repository remains private, and its public blog placeholder contains no research results.

## Resource measurements

The homepage follow-up baseline had widths 500 / 310 / 310 / 310 / 310 / **230 px** at a 1440 px viewport. Its second-row horizontal gaps were **175 px**, and the sixth card started 36 px below its neighbors. The copied rules were designed for seven cards, while this site publishes six. The corrected second row uses three 310 px cards, regular 40 px gaps, and aligned top edges. Separate two-item topic, related, and filtered rows now keep their normal left-hand positions. The 1024 px lead figure shrank from 410 × 236.8 to **410 × 224.47 px**, matching the reference's responsive caption strip; mobile figures are 350 × 207 px at a 390 px viewport.

At the earlier homepage-only baseline, loading **every** image, including normally lazy images, referenced 561,950 bytes of unique local image files. That inventory predates the project articles. It is a disk-file inventory, not a network transfer or image-decoding memory measurement. Decorative reveals use transform transitions and two observers instead of a continuous JavaScript scroll loop. Gradient animation pauses while its panel is offscreen. Browser checks verify the 70%-viewport trigger after resizing, row-mask delays of 300/400/500 ms, final transforms, and one-shot reveals. The added sections need no network requests or external libraries.

The original timeline HTML references **184.0 MiB of unique images** and a **689,124-byte stylesheet**. That is a reproducible local-file inventory, not a production network benchmark.

The generated 186 WebP previews total **1,762,376 bytes**, compared with **192,625,909 bytes** for their original pack images (99.1% smaller). Original files remain available on request from the artwork dialog or direct image links.

The August 2025 pair and September pack arrived as 680 × 680 transparent canvases around narrow artwork. Before normalization, their visible desktop heights were 49.33 px and 54 px beside 88 px neighboring packs. Thumbnail generation now trims only fully transparent outer padding before resizing, preserving all nonzero-alpha pixels and leaving original files unchanged. The affected desktop packs now measure 88 px tall. At 390 px, August's paired packs measure 76.16/76.93 px beside June's 73.94 px pair, with natural proportions intact and no document overflow. The [before/after measurements](qa/timeline-pack-size-results.json) record both viewport sizes. Tests cover real assets, opaque borders, palette/grayscale transparency, faint edges, EXIF orientation, and empty transparent images; the browser suite also compares August/June and September/November at both widths.

A Chrome HTTP test before the direct-file repair, at 1440 × 1000, recorded:

- 186 artwork elements; 151 thumbnails prefetched by Chrome's native lazy loader; **zero original pack-image requests** before opening a detail.
- Initial resource transfer **1,939,695 bytes**, plus **177,654 bytes** for HTML, about **2.02 MiB combined**.
- Local DOMContentLoaded **312 ms** in that run. Local host/hardware timing is not an internet speed guarantee.
- Calendar height **3,260 px**, with no nested vertical scroll area. Desktop cells preserve three separate side-by-side images in April 2019.
- At 390 px mobile width, the 1,120 px calendar scrolls inside a 364 px region; the document remains 390 px wide. Month labels and the year column remain aligned during scrolling.

After the pack-preview repair, the final standalone Chrome `file://` run decoded all 186 images and recorded **155.2 ms DOMContentLoaded**, 146 thumbnail requests and zero original pack requests before opening details. The calendar remained 3,260 px tall with the same contained mobile scrolling; all interaction checks passed without page errors. This is one local-disk timing sample. File-resource transfer sizes are reported as zero by the browser and are not evidence of zero bytes or an internet bandwidth measurement. Browser lazy-loading distances and timings vary.

## Failures found and resolved

- A seven-card news rule shrank and offset the sixth card, while `space-between` pushed sparse rows to opposite edges. Six-card sizing and explicit gutters now have browser regressions at five widths.
- The full news figure includes a caption below its 500:240 artwork area. Treating the strip as a fixed 40 px on every desktop width made medium-width cards too tall. Tests separately measure artwork, strip, and whole-figure dimensions.
- Adding the motion-ready class initially transitioned slide backgrounds backwards into their hidden positions. Slide transitions now apply only when revealed; a browser regression checks that below-fold panels start hidden immediately.
- Transparent source-image margins made several timeline packs look smaller despite identical CSS boxes. Preview generation now fits visible artwork while preserving source files and opaque borders; all 186 entries remain in their original calendar cells.

- A stale root homepage, root-relative resources, directory-only links, JSON fetching, and ES-module loading broke double-click browsing. The root now receives generated pages; output URLs are relative with explicit index files; search and timeline use local classic scripts.
- Recopying generated root pages as legacy sources could resurrect removed posts. Maintained tools and frozen original pages now live in separate source/archive directories, with an end-to-end deletion regression.
- Case-insensitive stylesheet declarations, extensionless CSS imports, and mixed data/local image candidates exposed path-rewriting defects. Targeted cases now cover them alongside Unicode filenames and preserved SVG/script data.
- A nested hosted 404 initially triggered incorrect speculative resource requests even after its base path was corrected. Its resource template now waits for the base decision; direct-file and hosted recovery are tested separately.
- PyYAML normalized malformed timezone offsets before validation. Front matter now retains raw timestamp strings for explicit validation.
- Hiding set artwork removed the calendar's visual recognition. Every occupied month now contains the corresponding local pack previews in build-generated HTML.
- A closed mobile `<details>` element concealed desktop navigation. The shared navigation is now independent of the toggle, with desktop/mobile/no-JavaScript regression coverage.
- Lazy artwork initially lacked stable image boxes. Explicit image dimensions and object fitting now preserve layout before decoding.
- A sticky-header test centered an early row while the native header was still visible. The corrected test scrolls far enough to exercise the floating header; production visibility logic was correct.
- Native dialog cleanup runs after the close event. Tests now wait for focus restoration and image removal instead of racing that event.
- The minimal real-template tutorial exposed an optional footer setting with no fallback. It now has a default, and a homepage without featured posts clears the fixed header.
- The original August release claim has counterexamples in the supplied archive. The calendar and new posts distinguish recorded months from verified product dates and missing entries from confirmed gaps.
- Legacy tool dependencies and probability errors were repaired; independent exact calculations and input/settlement boundary tests cover them.
- Build checks reject invalid metadata, duplicate/reserved routes, missing media, unsafe paths, unpublished related links, and remote runtime dependencies in offline mode.

## Reproduce

```sh
pip install -r requirements-dev.txt
python -m playwright install chromium
python scripts/build.py --check
python scripts/check-archive.py
python -m unittest discover -s tests -v
node tests/timeline.test.mjs
python scripts/test-timeline-browser.py --output /tmp/type-null-timeline-qa
```

The nine `test_file_ui.py` cases never start an HTTP server. To run the longer timeline interaction suite against files too, pass `--url file:///absolute/path/to/_site`; use a correctly escaped absolute file URL for your own folder. The default standalone timeline command above uses a temporary HTTP fixture for hosting compatibility.

Node 22 is used for the JavaScript tests; publishing itself has no Node runtime. An installed Chromium can be selected with `PLAYWRIGHT_CHROMIUM_EXECUTABLE`. Test HTTP fixtures are temporary and close afterward. GitHub Actions installs dependencies, runs these checks, and deploys the resulting static artifact using the official Pages actions.

Browser verification uses desktop Chrome and mobile viewport emulation, not physical devices or every browser engine. The deeply nested hosted custom-404 base correction requires JavaScript; direct-file 404 recovery and ordinary homepage/article/timeline navigation also work without JavaScript. External product/source links intentionally require internet when followed. Historical archive source files are retained as records, not claimed to be a second working website.

The deployment configuration follows [GitHub's custom Pages workflow documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages). To activate publishing in the real repository, select **Settings → Pages → Source → GitHub Actions**, then push to `main` or `master`.

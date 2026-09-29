# Type Null

A personal static blog for Pokémon cards, interactive projects, and field notes. The shared page shell follows the [Pokémon homepage](https://www.pokemon.co.jp/): its topic navigation, prominent image links, and clear editorial hierarchy, with this site's existing custom Type Null logo restored and a smaller set of reusable templates.

Write Markdown and keep images beside each post. A small Python build creates the homepage, full news index, topic pages, article pages, sharing metadata, and the card timeline. The homepage shows the newest six listed posts, followed by topic sections with distinct layouts; `/posts/` contains the full collection. The generated website opens directly from `index.html` on your computer and also runs on GitHub Pages.

Start with the short [folder-and-Markdown publishing tutorial](docs/WRITING.md). A post needs only `content/<topic>/<post>/index.md`; the build supplies a default layout and cover, then creates its links across the site.

## Open the website offline

Double-click **`index.html` in the repository folder** to open the homepage. You can also open **`_site/index.html`** directly: `_site/` is the same portable website in a clean folder. Navigation, search, and the card timeline are included in the generated files. Browsing them requires neither Python nor a web server.

Keep the surrounding folders with the HTML files so their local images, styles, scripts, and fonts remain available. Internal navigation uses relative links with explicit `index.html` targets for directory pages, so it also works through `file://` when the folder is moved or copied. External source links still need internet when opened.

Creating or renaming a Markdown file changes the source. Run the build locally, or let GitHub Actions build after a push, to turn those changes into website pages. The browser does not render a newly added Markdown file automatically.

## Publish to GitHub.io

The deployment target is **GitHub Pages only**. The published site contains static HTML, CSS, JavaScript, fonts, and media. Python runs during the build in GitHub Actions; it is not a website server. There is no database, cloud application host, or background service.

1. Put this source in the `type-null.github.io` repository.
2. Set **Settings → Pages → Build and deployment → Source → GitHub Actions** once.
3. Add or edit a post folder, then commit and push to `main` or `master`.

The included workflow validates the content, runs checks, builds `_site/`, and publishes that static folder to `https://type-null.github.io/`. GitHub Pages uses the artifact's `index.html` as its homepage. No local setup is required to write and publish. You can also edit Markdown directly on GitHub.

Both `_site/` and the public HTML pages in the repository root are generated output. Edit `content/`, `templates/`, and source assets; do not hand-edit the generated `index.html` or article pages. Essential fonts, scripts, styles, artwork, screenshots and local tools are stored in the repository. Optional live project previews load from their own websites on the hosted blog; direct-file browsing keeps local previews until the reader requests the online app.

### Build changes on your computer

For local authoring, install the build requirements once using Python 3.12 or newer. The first installation normally needs internet access:

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/build.py --check
```

The build creates `_site/`, checks its local references, and refreshes the generated public pages in the repository root. Open or refresh the root `index.html` to see the changes; no server starts. On later edits, activate the environment and rerun `python scripts/build.py --check`.

Once dependencies are installed, building works offline. Opening an already generated website needs no build dependencies at all: double-click `index.html` and browse the local files.

## Write a post

Create a folder under a topic, copy a starting file from `examples/`, and name it `index.md`:

```text
content/
  notes/
    _topic.yml
    my-new-post/
      index.md
      cover.jpg
      detail.jpg
```

For example:

```sh
mkdir -p content/notes/my-new-post
cp examples/article.md content/notes/my-new-post/index.md
```

Edit the title, date, description, and body. The examples start with `draft: true`; remove that line or set it to `false` when the post is ready to publish.

```md
---
title: A title with something to say
date: 2026-09-29
description: A short, specific introduction for the homepage and link previews.
template: article
featured: false
tags: [Cards, Notes]
---

Start with a paragraph. Markdown handles **emphasis**, [links](/card/), and lists.

## A useful heading

More of the story goes here.
```

After a build, the folder above becomes `/notes/my-new-post/` on the published site and `notes/my-new-post/index.html` in the generated folders. Only `title` and `date` are required; add `description` for useful cards and link previews. The default layout is `article`, and a local cover is provided when you do not specify one. `date` is a publication date in `YYYY-MM-DD` format; use the actual original date for migrated writing. Quotes around text containing `:` or `#` avoid YAML ambiguity.

`featured: true` makes a post eligible for prominent placement. `description` and `cover` power its link card and social preview. A **1000 × 480** cover matches the news artwork's **500:240** proportions. Other sizes fit within the frame without cropping; existing images can stay as they are. Write useful image descriptions in the body and galleries.

### Keep publication and writing dates separate

`date` is the publication day and controls article ordering. `created` records when you first wrote the piece; `updated` records its last published revision. These values live in the Markdown file, so they work without Git, a revision database, or filesystem timestamps.

```yaml
created: 2026-09-28T20:30:00-04:00
date: 2026-09-29
updated: 2026-09-29T14:00:00-04:00
```

In this example, writing began at 8:30 p.m. on September 28 in UTC−04:00, the publication day is September 29, and the last revision was at 2 p.m. on September 29 in that same offset. Replace the sample values with your own known dates.

`created` and `updated` accept either a date (`YYYY-MM-DD`) or an ISO 8601 timestamp with an explicit offset, such as `-04:00`, or `Z` for UTC. A timestamp without an offset is rejected because its time zone is ambiguous. Keep the first-written day on or before publication and the last-revised day on or after it. A date-only value records a whole day rather than midnight; an exact time on that same day is valid. When two timestamps are compared, their offsets are taken into account.

If `created` or `updated` is omitted, it defaults to `date`. That fallback does not reconstruct an unknown first draft. Supply a known `created` value when importing older writing, and use date-only precision when the time is unknown. Change `updated` when you publish a revision. Rebuilding alone never advances these dates or infers them from Git or file modification times.

## Choose a template

| Value | Use it for | Starting file |
| --- | --- | --- |
| `article` | Essays, research notes, announcements | `examples/article.md` |
| `feature` | A visual introduction or headline story | `examples/feature.md` |
| `gallery` | A collection of captioned images | `examples/gallery.md` |
| `tool` | Interactive projects and embedded media | `examples/tool.md` |
| `landing` | A project introduction with facts and clear next steps | `examples/landing.md` |
| `review` | A structured review with scope, evidence, and conclusions | `examples/review.md` |
| `timeline` | The existing card archive, with pack artwork arranged by year and month | `content/card/timeline/index.md` |

The first six templates are reusable for new posts. The timeline template uses this site's shared card-release dataset; it is not a generic chronology builder. All templates share the same header, topic navigation, footer, metadata, and article sharing controls.

For writing about an app developed in another repository, start with `examples/project.md`. The [project article guide](docs/WRITING.md#write-about-a-project-from-another-repository) adds a live app preview, a local fallback screenshot, a circular GitHub button, and an **Open website** button. Use `template: article` to avoid repeating the cover above the preview.

The [companion-project guide](docs/PROJECTS.md) explains how source pushes automatically build and deploy each app at its own stable GitHub Pages address. The blog links and embeds follow those updates without copying app files. Local screenshots and writing remain available offline; live previews require internet and load automatically only on the hosted blog.

The timeline keeps pack artwork directly in the calendar's occupied month cells. Aligned month columns make releases comparable across years, and paired releases keep their individual images. Filters narrow this artwork calendar; opening a release adds details and source links. The artwork should remain visible without JavaScript, too.

## Page information reference

These settings go between the opening `---` lines. Start small and add only the fields a page needs.

| Field | Format and purpose |
| --- | --- |
| `title` | Required page title. |
| `date` | Required publication day, `YYYY-MM-DD`; controls article ordering. |
| `created` | First-written date or timestamp with an explicit time zone. Defaults to `date` when omitted. |
| `description` | Short introduction used for cards and default social metadata. |
| `template` | `article`, `feature`, `gallery`, `tool`, `landing`, `review`, or the shared `timeline`. Defaults to `article`. |
| `subtitle`, `eyebrow` | An optional supporting title line and short heading label. |
| `author` | Author name for this post; otherwise the site's author is used. |
| `updated` | Last published revision date or timestamp with an explicit time zone. Defaults to `date`; update it when publishing a revision. |
| `lang` | Page language tag, such as `en`, `ja`, or `zh-CN`. |
| `cover` | Local image filename or site-root image path. A default is supplied if omitted. |
| `cover_images` | Optional list of up to six local image paths for an artwork montage in a reusable cover or banner. Defaults to an empty list; `cover` remains the single-image fallback. |
| `hero_image`, `hero_mobile_image` | Optional authored campaign banners for desktop and mobile. Use local paths; the homepage banner proportions are 1920 × 923 and 750 × 920 respectively. |
| `cover_alt`, `cover_caption` | Accessible description and optional caption or attribution. |
| `tags` | List of text labels, for example `[Cards, Notes]`. |
| `toc` | `true` adds a table of contents from the article headings. |
| `featured` | `true` makes a listed post eligible for the homepage featured image carousel. |
| `draft` | `true` omits the page from the build. |
| `unlisted` | `true` keeps the direct page but omits it from homepage, topic listings, search, feed, and sitemap. It does not make a page private. |
| `permalink` | Explicit public address, useful when moving or renaming a post. |
| `links` | Button list, with `label`, `url`, and `style` (`primary` or `secondary`) for each item. |
| `facts` | List of `label` and `value` pairs. Values can be text or finite numbers; use text for units, such as `value: 60 cards`. |
| `related` | List of local URLs for existing listed posts. Missing, draft, or unlisted destinations are rejected. |
| `seo` | Optional map with `title`, `description`, and local `image` overrides for page metadata. |
| `gallery`, `embeds` | Media lists; formats are shown below. |

For example, this metadata uses real local destinations and requires no additional images:

```yaml
subtitle: A closer look at the collection
eyebrow: Field guide
toc: true
links:
  - label: Explore the timeline
    url: /card/2024/02/timeline.html
    style: primary
facts:
  - label: Format
    value: Personal notebook
related:
  - /card/pack-art/
seo:
  title: A closer look · Type Null
  description: A short description for search and sharing.
```

## Organize topics with folders

Every top-level folder under `content/` is a topic and gets navigation and a landing page, even while it is empty. Create or rename a folder and rebuild to change the sections; there is no header HTML to edit. Folder names beginning with `_` or `.` are ignored. Draft posts remain unpublished, but their topic can still appear.

The optional `_topic.yml` controls how the section appears:

```yaml
label: Field Notes
description: Thoughts, observations, and things worth keeping.
color: "#438fcb"
icon: notebook
order: 3
home_layout: journal
```

Existing icon choices are `cards`, `ball`, and `notebook`. Copy `examples/_topic.yml` to get started. Keep color values quoted because an unquoted `#` starts a YAML comment.

`home_layout` controls this topic's homepage presentation; it does not change the post templates:

- `gallery` (default): up to six recent posts in an image grid, becoming image-and-title rows on small screens.
- `feature`: one large link to the latest `tool` or `landing` post, followed by up to two other recent posts. The latest article leads when neither type exists.
- `journal`: up to four dated thumbnail rows with article introductions.

The current Cards, Sports, and Notes topics use `gallery`, `feature`, and `journal` respectively. Each section fills itself from that topic's listed posts in publication order. Empty topics keep a working topic link; drafts and unlisted pages stay out. The separate NEWS section still shows exactly the newest six posts when six or more are available.

- **Rename only the navigation label:** edit `label` in `_topic.yml`.
- **Change the topic and default URL:** rename its folder and rebuild.
- **Move or rename a published post without breaking its address:** set an explicit `permalink` before moving it.

```yaml
permalink: /card/2024/02/timeline.html
```

A `permalink` may be an old `.html` address or a directory address ending in `/`. It must be unique. A clean build removes stale generated routes after folder renames, so update handwritten links to any address you intentionally change. The build does not automatically create redirects for every previous folder name.

## Add images, video, PDFs, and websites

Store media next to `index.md` and use relative filenames. Shared images can use site-root paths such as `/assets/images/example.jpg`. Keep filenames simple when convenient; the build also handles spaces and Unicode in local media paths. The repository's `offline: true` setting rejects direct remote image, video, PDF, `website` and YouTube embeds. A `project` embed with a local screenshot and `interactive: true` provides a separate optional live preview without changing that setting; direct-file pages load it only when requested. Use ordinary outbound links for other external sources.

You can keep convenient site-root paths such as `/card/` in Markdown and page settings. The build rewrites internal navigation and local resource references for each generated page, so you do not need to calculate `../` paths for direct-file browsing.

For a gallery, add this to the page information:

```yaml
template: gallery
gallery:
  - src: detail.jpg
    alt: A close view of the detail discussed in the article
    caption: A short caption with context or attribution.
  - src: another-view.jpg
    alt: The same object from another angle
    caption: A second view.
```

For embeds, use an `embeds` list. Save your real `clip.mp4` and `notes.pdf` beside `index.md` before using this example. The website entry uses an existing local tool:

```yaml
embeds:
  - type: video
    url: clip.mp4
    title: A short demonstration
  - type: pdf
    url: notes.pdf
    title: Downloadable notes
  - type: website
    url: /card/toolkit.html
    title: Prize Card Odds calculator
```

Place `[[embed:1]]` on its own line in the Markdown body for the first item, `[[embed:2]]` for the second, and so on. Unplaced embeds are appended after the text. `examples/tool.md` uses the real local calculator and can be copied without obtaining media files. A website embed can also include `repository: https://github.com/owner/repo` to show a circular GitHub source button beside **Open in new tab**; both links work without JavaScript.

A `website` embed lets readers use a calculator or game inside the article and automatically adds an **Open in new tab** button above it. All six writing layouts support embeds, including ordinary `article` posts. The [writing tutorial](docs/WRITING.md#put-a-calculator-or-game-inside-a-post) includes a complete copyable post using `/card/toolkit.html`.

To embed your own tool, save `calculator.html` beside the post's `index.md` and set its embed URL to `calculator.html`. Keep its CSS, classic JavaScript, and media local, then rebuild. Its frame and new-tab button use portable local paths for both direct-file browsing and GitHub Pages.

PDF frames retain a direct file link. Video format support depends on the browser. Keep local PDFs and videos reasonably sized because GitHub Pages serves the complete files.

To reference a YouTube video without loading a remote player, write an ordinary Markdown link to its watch page. If you deliberately change `site.yml` to `offline: false`, the engine also accepts remote materials and the `youtube` embed type with a YouTube watch or short URL. That mode requires internet for those materials, and external websites may refuse framing. The included site and examples use the local mode.

## Site settings and sharing

Edit `site.yml` for the site name, description, author, canonical URL, and footer text. Keep `url` set to the deployed origin so canonical URLs, social image URLs, the sitemap, and sharing links point to the right site.

The default canonical origin is `https://type-null.github.io`. `site.url` currently accepts an HTTP(S) origin without a path. Generated relative navigation remains portable when the output folder moves; canonical URLs, sitemap addresses, and social metadata continue to use that configured published origin.

Post metadata becomes page titles, descriptions, and social preview data. Sharing and copy-link controls use the canonical published page URL, including when the page is opened locally; they do not share a private `file://` path. Browser support determines whether native sharing is available. A public host must be able to fetch the page and cover image before a social service can render its preview.

## Publish with GitHub Pages

The repository includes a GitHub Actions workflow that installs the build requirements, generates `_site/`, and deploys that folder to GitHub Pages.

1. Push the repository and your content to GitHub.
2. In **Settings → Pages**, set **Source** to **GitHub Actions**.
3. Check the Pages workflow run after pushing to the configured deployment branch. A manual workflow run is also available.

The workflow publishes generated files. The source Markdown, templates, scripts, and local virtual environment are not website content. No application server or database is needed.

## Repository map

```text
content/                 Markdown posts, topic settings, and post media
examples/                Copyable authoring starters; not published
site.yml                 Site-wide identity and offline settings
templates/               Shared page layouts
assets/                  Shared CSS, JavaScript, images, and archive data
scripts/                 Build, migration, and verification utilities
tests/                   Targeted build and interaction regressions
legacy/                  Maintained standalone tool and map HTML sources
archive/legacy-pages/    Frozen original pages; never copied into the website
index.html               Generated homepage; open directly, do not hand-edit
card/, sports/, ...      Generated public pages at their preserved addresses
_site/                   Clean portable copy of the generated website
```

The root `card/`, `sports/`, `resume/`, and `florida/` pages are generated public output. `legacy/` contains the maintained sources for the three standalone tools and the minimal map page. Frozen copies of the original homepage, 404, timeline, résumé, and soccer page live in `archive/legacy-pages/`, outside the build's source-page inputs. Removing a migrated Markdown post therefore does not republish its old HTML snapshot. Existing public tool, map, and résumé addresses are retained while their current source pages exist.

The old soccer page was an unfinished scaffold: its soccer research description was followed by unrelated sample product copy and missing images. The migrated page preserves the research questions and explains the gap instead of inventing results. The timeline preserves the original displayed publication date, while its imported release data is explicitly labeled as an archive rather than a verified live schedule.

The author profile preserves its complete February 10, 2025 biography at its original address, with `unlisted: true` to keep it out of site discovery. Unlisted pages are still publicly accessible by direct URL; this is an organizational setting, not access control. The old Florida page links to the [Florida research introduction](content/notes/florida-power-systems/index.md), which is pinned in the homepage INFORMATION strip and ready for the study and independent website links; it contains no research results yet.

The three interactive tools now use local code and assets rather than remote chart, styling, or account services. Prize-card odds use the complete hypergeometric distribution; Trading Suits exposes its assumed deck compositions; Probability Parlay calculates chances from its stated game rules and stores records in the browser. These behavior changes do not establish that an archived game model matches an external rulebook.

Legacy images and fonts remain available for archived pages. New articles should use the shared templates and save their own media with their Markdown, without copying old page shells or external analytics snippets.

## Project history

- March 2021: initial site concept, logo, and the soccer research scaffold.
- February 2024: date shown on the original Pokémon card timeline.
- February 2025: résumé page work noted in the original README.
- June 14, 2025: Trading Suits project, recorded in the original README as made with Gemini.
- September 2026: Markdown publishing, shared templates, an actual homepage, and the compact card archive.

The blog is independent and is not affiliated with The Pokémon Company. Existing Pokémon artwork remains the property of its respective owners; the site's original code is covered by `LICENSE`.

## Browser verification

For the full regression suite, including desktop/mobile layouts and interactions:

```sh
pip install -r requirements-dev.txt
python -m playwright install chromium
python scripts/build.py --check
python -m unittest discover -s tests -v
```

If Chromium is already installed, you can set `PLAYWRIGHT_CHROMIUM_EXECUTABLE` to its executable path instead of downloading it. The browser tests are skipped when Playwright is not installed; the Pages workflow installs it and runs the full suite. The pure JavaScript timeline checks can also run with `node tests/timeline.test.mjs` (Node 22 is provided in CI).

The shared editorial covers have editable SVG sources beside their WebP versions in `assets/images/editorial/`. Pack artwork uses optimized local images; gallery previews and timeline thumbnails are produced automatically during the build. Timeline previews are visible in the calendar, while original artwork remains available for a closer look. Clicking a gallery image still opens its original. Current verification status is recorded in [docs/verification.md](docs/verification.md).

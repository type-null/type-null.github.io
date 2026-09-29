# Publish with a folder and a Markdown file

A post needs only its folder and `index.md`. The build adds links to the news index, topic page, search, RSS feed, and sitemap automatically. The newest six listed posts appear on the homepage. You do not edit HTML or maintain those link lists.

Posts inherit the shared Pokémon homepage-style shell, topic navigation, and the site's existing custom Type Null logo. Choose a layout for the kind of writing you are publishing; your content and images stay beside one Markdown file.

To read the existing site, double-click the repository's `index.html` or `_site/index.html`. Both open directly from disk with local navigation, search, and timeline controls. No server or Python installation is needed for browsing an already generated copy.

## 1. Create a post

Create `content/notes/my-first-post/index.md` and paste:

```md
---
title: My first post
date: 2026-09-29
description: A short introduction to what this post is about.
---

Here is the first paragraph of my post.

## A little more

Write ordinary Markdown, including **emphasis**, lists, and links.
```

Change the title, date, introduction, and body. No cover image or template setting is required: the site supplies a default cover and the `article` layout.

After a build, this post's published address is `/notes/my-first-post/`; its local page is `notes/my-first-post/index.html`. Adding the Markdown file alone does not update the generated website.

## 2. Build and open locally

After installing the build requirements once using the [README](../README.md), run:

```sh
source .venv/bin/activate
python scripts/build.py --check
```

The build writes the complete website to `_site/` and refreshes the generated public pages in the repository root. Double-click the root **`index.html`**, or **`_site/index.html`**, and refresh the browser after rebuilding. No web server is needed.

Keep the website's folders together. Internal links are relative and point to explicit `index.html` files where needed, so navigation works through `file://`. Images, fonts, styles, scripts, and interactive tools stay local. The first dependency installation normally needs internet; later builds and direct-file browsing work offline.

Creating, editing, or renaming a post requires another build. Edit the Markdown and source media rather than the generated root HTML or files in `_site/`.

## 3. Publish to GitHub Pages

Commit and push the content folder to the repository's `main` or `master` branch. With **Settings → Pages → Source** set to **GitHub Actions**, the included workflow builds and deploys the static site automatically. GitHub Pages uses `_site/index.html` from the deployed artifact as its homepage. You do not install a server or upload `_site/` by hand.

The published post is linked from the full news index (`/posts/`), its topic page, search, RSS, and the sitemap. The homepage displays the newest six listed posts, ordered by publication date; same-date ties use the URL. Its topic sections also select recent posts automatically. Draft and unlisted pages are excluded from those discovery surfaces.

You can create and edit the files directly in GitHub's web interface. There is no local software requirement for publishing. Python is only a build tool used by the workflow; visitors receive ordinary static files.

Sharing buttons use the configured published URL even when a page is opened from disk. A copied link therefore points to the public site, not a private path on your computer.

## Record first writing and later revisions

Keep these dates in the opening page-information block:

```yaml
created: 2026-09-28T20:30:00-04:00
date: 2026-09-29
updated: 2026-09-29T14:00:00-04:00
```

- `created` is when you first wrote the piece: 8:30 p.m. on September 28 in UTC−04:00 in this example.
- `date` is the publication day and controls ordering on the homepage and article indexes.
- `updated` is the last published revision: 2 p.m. on September 29 in UTC−04:00 here. Change it when you publish a revision.

Replace these sample values with your real dates. `created` and `updated` can also be plain dates such as `2026-09-29` when you do not know the time. If you include a time, include its offset (`-04:00`, `+09:00`, or `Z` for UTC); a timestamp with no time zone is rejected. The first-written day must be on or before publication, and the last-revised day on or after it. A date-only value and a time on the same day are compatible; two exact timestamps are compared using their offsets.

Omitted `created` and `updated` values default to `date`. This fallback does not recover an unrecorded first draft, so supply a known first-written date when importing older work. No Git history, filesystem modification time, or revision database is consulted. Rebuilding does not change the dates you wrote.

## Add a topic

Use another top-level folder: `content/travel/my-first-post/index.md` creates a **Travel** section and a `/travel/` landing page. Rename the topic folder and rebuild to change its default name and address. Every topic folder gets navigation, even while empty; names beginning with `_` or `.` are ignored.

Choose a topic name that does not collide with the site's own folders. Names such as `assets`, `content`, `templates`, `scripts`, `tests`, `docs`, `legacy`, `archive`, `examples`, and `posts` are reserved; the build reports a conflict rather than overwriting them.

To change only the displayed name, add `content/travel/_topic.yml`:

```yaml
label: Out and About
description: Notes from elsewhere.
color: "#438fcb"
icon: notebook
order: 4
home_layout: journal
```

This keeps the `/travel/` address while displaying **Out and About** in navigation. There is no menu HTML to edit.

`home_layout` chooses the topic's homepage section, independently of each post's `template`:

| Value | Homepage presentation |
| --- | --- |
| `gallery` | Up to six latest posts in an image grid; compact image-and-title rows on small screens. This is the default. |
| `feature` | A large featured link to the latest `tool` or `landing` post, plus up to two other recent posts. Without a tool or landing post, the latest article leads. |
| `journal` | Up to four recent posts in dated rows with a thumbnail and introduction. |

Cards, Sports, and Notes currently use these three formats respectively. A new topic works without `_topic.yml`; add it only to customize these defaults. Its settings stay with the folder if you rename it. Empty topics keep their navigation link and show a short message until you publish a post.

`order` controls the topic's position in both navigation and the homepage (lower numbers first). Topic sections always follow the featured area, update strip, and NEWS. Changing `home_layout` changes the presentation inside that section while preserving the shared page hierarchy, headings, spacing, and buttons. The [design reference](pokemon-reference.md#homepage-hierarchy-to-preserve) records that structure.

## Add an image or choose a layout

Save `photo.jpg` beside the post's `index.md`, then add this in the body:

```md
![Describe the image](photo.jpg)
```

To use it for the homepage card and social preview, add `cover: photo.jpg` inside the opening `---` block. The file must exist when you run a checked build. For a new cover, **1000 × 480 pixels** matches the news artwork's **500:240** proportions. Other image sizes fit inside the consistent frame without cropping; existing images do not need to be replaced. Topic gallery and feature sections use their own consistent image proportions.

For an artwork montage, add `cover_images: [pack-one.png, pack-two.png]` with up to six local images. For a finished campaign banner, use `hero_image: desktop.jpg` and optionally `hero_mobile_image: mobile.jpg`; the homepage uses 1920 × 923 desktop and 750 × 920 mobile proportions. Save these files beside `index.md` too. These options are optional; an ordinary post still needs only its title, date, and writing.

For another layout, choose `feature`, `gallery`, `tool`, `landing`, or `review` in the `template` field. Copyable starting files live in `examples/`; they begin as drafts.

The separate `timeline` layout serves the existing shared card archive. It presents pack artwork directly in aligned year-and-month cells, including paired releases. Use one of the six reusable writing layouts for a new ordinary post.

Save images, videos, and PDFs beside `index.md`. Embed a local website from this same site, such as `/card/toolkit.html`. The site's default offline mode rejects remote material URLs; use ordinary Markdown links for external websites and YouTube videos. The [README media section](../README.md#add-images-video-pdfs-and-websites) has copyable local-media examples.

## Put a calculator or game inside a post

Copy this complete example into a new post's `index.md`:

```md
---
title: Try the prize card calculator
date: 2026-09-29
description: Explore the odds while reading the explanation.
template: article
embeds:
  - type: website
    url: /card/toolkit.html
    title: Prize Card Odds calculator
---

Change the deck size, copies, and prize cards to explore the distribution.

[[embed:1]]

The calculator assumes a random selection of prizes without replacement.
```

The calculator is playable inside the article. An **Open in new tab** button is generated above it automatically, so readers can also use it in a separate tab. All six writing layouts (`article`, `feature`, `gallery`, `tool`, `landing`, and `review`) support this. An ordinary `article` works without choosing the `tool` layout.

For your own tool, save a standalone file such as `calculator.html` beside `index.md`, keep its CSS, classic JavaScript, and images local, and change the embed URL to `calculator.html`. Rebuild after adding or editing those files. The generated frame and new-tab link follow the local paths when the site is opened directly from disk or published to GitHub Pages.

## Write about a project from another repository

Keep the app in its own repository and publish it through that repository's GitHub Pages workflow. Your blog post can show the live app and offer **Open website** for its complete independent interface, plus a circular GitHub source button.

Create `content/card/my-calendar-project/index.md`, or copy [the project starter](../examples/project.md). Save a screenshot as `cover.png` beside it; **1000 × 480** matches the news artwork proportions. Use `template: article` so the cover appears on the homepage without a duplicate image above the preview:

```md
---
title: Building the PTCG calendar
date: 2026-09-29
description: How the calendar works and what I learned while building it.
template: article
cover: cover.png
embeds:
  - type: project
    title: PTCG calendar
    image: cover.png
    repository: https://github.com/type-null/PTCG-calendar
    url: https://type-null.github.io/PTCG-calendar/
    interactive: true
---

Explain what the project does and what readers can explore.

[[embed:1]]

Describe the design choices and lessons from building it.
```

On the hosted blog, the live preview loads when it comes into view. A directly opened local article initially keeps its screenshot and makes no automatic project request; click **Use in this article** while online to load the app. The saved screenshot remains until the app confirms it is ready, so an unavailable website leaves a useful preview and a retry option. Without JavaScript, the screenshot, website and GitHub links still open separately.

Omit `interactive` for a screenshot link only. If the website is not ready, omit both `url` and `interactive`; the screenshot then opens GitHub. Live previews require the readiness response already included in these three apps; see [the companion-project guide](PROJECTS.md).

Each app's source pushes rebuild and deploy its own stable Pages address automatically. No app files are copied or synchronized into the blog. Refresh the article's screenshot and explanation manually when needed, update `updated`, and rebuild the blog. Interface updates do not imply newer event, card or research data.

The article and screenshot remain readable offline; live previews and external links need internet. Each project's downloaded `site/` folder can be used independently offline. The existing local calculator/game embeds above remain available for tools maintained in this blog.

## Useful page settings

Add these optional lines inside the opening page-information block:

| Setting | Result |
| --- | --- |
| `draft: true` | Do not generate or publish the page. |
| `unlisted: true` | Keep the direct address working; omit the page from homepage, topic listings, search, RSS, and sitemap. This is not access control: anyone with the address can open it. |
| `featured: true` | Make a listed post eligible for the homepage’s featured image carousel. |
| `announcement: true` | Prioritize a listed post in the two-link INFORMATION strip, without changing NEWS ordering. Multiple announcements follow publication order. |
| `template: feature` | Use the visual feature layout. |
| `created: 2026-09-28` | Record a known first-written day independently of publication. |
| `updated: 2026-09-29` | Record the last published revision; update it yourself when revising. |
| `tags: [Notes, Travel]` | Add tags to the article. |
| `permalink: /notes/my-first-post/` | Keep this published address when you later move or rename the folder. |

Keep an explicit `permalink` before moving an established post. Otherwise, folder renames change its URL and you must update any handwritten links to the old address. Automatic navigation and listings always follow the current build.

## Add detail when it helps

You can add a `subtitle`, `eyebrow`, per-post `author`, or `lang` alongside the writing dates above. A `toc: true` line creates a table of contents. Richer templates accept labeled `facts`, button `links`, and a `related` list of existing post URLs. Local cover images have `cover_alt` and `cover_caption`; an optional `seo` map overrides search and sharing metadata.

These fields are optional. See the [complete metadata reference](../README.md#page-information-reference) and the commented `examples/feature.md`, `examples/landing.md`, and `examples/review.md` starters when you need more than the minimal post.

---
title: A little guide to writing here
date: 2026-09-29
updated: 2026-09-29
description: One folder, one Markdown file, and your images. A practical guide to publishing on Type Null.
template: feature
subtitle: From a blank folder to a post linked across the site.
eyebrow: The publishing notebook
toc: true
cover: /assets/images/editorial/notes.webp
featured: true
tags: [Site guide, Markdown, Publishing]
---

This is the site's authoring guide. **One folder and one Markdown file are enough for a new post.** The build creates its news-index card, topic listing, search entry, RSS item, and sitemap entry automatically. The newest six listed posts appear on the homepage.

To browse an existing copy, open the repository's `index.html` or `_site/index.html` directly. Navigation, search, and the card timeline are included in the generated website, so no web server is needed.

## Start with a folder

Create a folder such as `content/notes/my-next-story/`. Inside it, add `index.md`. Images are optional. The first folder under `content/` is the topic; each story gets its own folder inside that topic.

```text
content/
  notes/
    _topic.yml
    my-next-story/
      index.md
```

Begin the Markdown file with a small block of page information:

```yaml
---
title: A title for the next story
date: 2026-09-29
description: One clear sentence for the homepage card.
---
```

Then write ordinary Markdown: paragraphs, headings, lists, and links. The site supplies the default article layout and cover; you do not need to create an image to publish. To add one later, save `photo.jpg` beside the post and insert `![A useful description](photo.jpg)` in the body. Add `cover: photo.jpg` to the opening information block to use it for the page's card.

Creating or renaming files changes the source. A build turns those changes into the actual website; a browser does not automatically convert newly added Markdown.

## Keep a small record of the writing

Publication and revision are different moments. `date` is the publication day and controls article ordering. Add `created` for when you first wrote the piece and `updated` for its last published revision:

```yaml
created: 2026-09-28T20:30:00-04:00
date: 2026-09-29
updated: 2026-09-29T14:00:00-04:00
```

Here, writing began at 8:30 p.m. on September 28 in UTC−04:00, publication was on September 29, and the last revision was at 2 p.m. on September 29 in the same offset. Replace the example values with dates you actually know.

Use a plain date when the time is unknown. If you record a time, include an explicit offset or `Z` for UTC; a timestamp without a time zone is rejected. Keep the first-written day on or before publication and the last-revised day on or after it. A day-level date does not imply midnight, so a more precise time on that same day is valid. Two exact timestamps are compared using their offsets.

Both optional fields default to `date`. That fallback cannot recover an unrecorded first draft. When importing old writing, supply a known first-written date if you have one. Change `updated` when publishing a revision; rebuilding leaves the author-supplied dates alone. This works without Git or filesystem date inference.

## Choose a shape for the story

| Template | A good fit |
| --- | --- |
| `article` | Essays, research notes, and everyday posts |
| `feature` | A visual introduction or longer headline story |
| `gallery` | An image-led collection with individual captions |
| `tool` | A calculator, game, video, or embedded project |
| `landing` | A project introduction with useful links and facts |
| `review` | A structured record of observations and conclusions |
| `timeline` | The site's Pokémon card release archive |

The templates share the same navigation, topic colors, and article controls. The repository's `examples/` folder contains starting files you can copy without publishing the examples themselves.

Optional fields let you add a `subtitle`, `eyebrow`, author, writing dates, cover description and caption, table of contents, facts, button links, and related posts. The commented starters show these fields in context; the README has a complete reference. They are conveniences, not requirements for an ordinary post.

## Make a topic your own

Topic folders create navigation automatically, even before the first post is published. Folder names beginning with `_` or `.` are ignored. Add a `_topic.yml` file to choose a display label, description, color, icon, and order. For example, the folder `sports` is displayed as **Sports** here.

Changing a topic folder name changes its default address. If a story already has readers, keep its `permalink` to preserve the published address. Changing only the topic's display label is the simplest way to rename a navigation item without changing links.

## Bring the media with you

Local images can live beside the post. Galleries use a `gallery` list in the page information, with `src`, `alt`, and `caption` for each image.

Save videos and PDFs beside the Markdown file and use their filenames in an `embeds` list. Same-site projects such as `/card/toolkit.html` can use a `website` embed. Each item has a `type`, `url`, and `title`. Put the marker shown below on a line of its own to place the first embed in the article; without a marker, embeds appear after the text.

```text
[[embed:1]]
```

The site keeps its required materials in the repository. Generated internal links are relative and use explicit `index.html` targets for directory pages, so the same files can be opened directly from disk or published on GitHub Pages. Keep the surrounding folders with the HTML files. The default offline setting rejects remote images, players, PDFs, and website frames. Use ordinary Markdown links to refer readers to YouTube or other external sources; those links only need internet when someone chooses to open them.

## Build and open the homepage

After installing the build requirements from the README once, run `python scripts/build.py --check`. The command builds `_site/` and refreshes the generated public pages in the repository root. Open the root `index.html`, or `_site/index.html`, directly and refresh it after rebuilding. It does not require an HTTP server.

The first dependency installation normally needs internet access. Later builds work offline, and browsing an already generated copy needs no Python dependencies at all. Edit the Markdown, templates, and source assets; generated root HTML and `_site/` are outputs that the next build replaces.

## Publish to GitHub Pages

Commit and push your changes to `main` or `master`. With **Settings → Pages → Source** set to **GitHub Actions**, the included workflow builds and publishes the static `_site/` folder automatically. The deployed artifact's `index.html` is the GitHub Pages homepage. You can also edit Markdown directly on GitHub. No Python server, database, or separate hosting service is required.

Set `draft: true` in the page information to keep a work in progress out of the published site. A push can trigger the required build through GitHub Actions instead of building locally.

Each listed article gets links from the full news index, its topic page, search, RSS, and the sitemap, along with metadata and sharing controls. The homepage shows the newest six listed articles. Add `featured: true` to make it eligible for the homepage’s featured image carousel.

An archived page can use `unlisted: true` to keep its direct URL working while omitting it from those discovery surfaces. This is not access control: anyone with its address can still open it.

The source of a story remains its Markdown file. Python and the template engine run only when generating the site; the website is ordinary static content. Sharing and copy-link controls use the canonical published address even while browsing locally, so they do not expose a private file path.

The repository README includes the initial setup, complete media examples, and the details of preserving older links.

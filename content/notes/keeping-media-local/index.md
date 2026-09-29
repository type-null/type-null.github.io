---
title: Keep the pictures with the story
date: 2026-09-29
updated: 2026-09-29
description: A practical workflow for Markdown posts whose images, videos, PDFs, and interactive examples remain portable and easy to preview offline.
template: article
subtitle: One post folder can hold the writing and the material that explains it.
eyebrow: The publishing notebook
cover: /assets/images/editorial/notes.webp
cover_alt: A field-notes notebook and yellow pencil on a pale yellow background.
toc: true
tags: [Markdown, Media, Site guide]
facts:
  - label: Source
    value: Markdown and local files
  - label: Output
    value: Static HTML and media
  - label: Default mode
    value: Offline materials
links:
  - label: Start with the writing guide
    url: /notes/writing-here/
    style: primary
  - label: See a local interactive page
    url: /card/prize-card-odds/
    style: secondary
related:
  - /notes/writing-here/
  - /card/pack-art/
  - /card/prize-card-odds/
---

A post is easier to maintain when its illustrations travel with its words. Instead of scattering uploads across services, keep the files beside the Markdown that explains them. Moving or backing up the story then means working with one folder.

This repository's default `offline: true` setting supports that approach. It rejects remote embedded materials, while ordinary outbound links still work when a reader chooses to follow them. The generated pages use local styles, scripts, fonts, and artwork.

## Start with a small folder

A media-rich post might look like this:

```text
content/notes/a-small-experiment/
  index.md
  cover.webp
  detail.webp
  demonstration.mp4
  observations.pdf
```

These filenames illustrate the structure; create the actual files before referencing them in a published post. Add `cover: cover.webp` to the page information for its link-card image. In the body, ordinary Markdown displays an illustration:

```md
![The measurement marks discussed in this paragraph](detail.webp)
```

Write the description around the information that matters, rather than just naming the file. A caption can supply context or attribution; alternative text should help someone understand the image when they cannot see it.

## Choose a presentation for each kind of material

An inline image works well when the surrounding paragraph explains one detail. A `gallery` template groups several pictures using entries with `src`, `alt`, and `caption`. The [pack-art collection](/card/pack-art/) is an existing example of image-led reading.

Video, PDF, and website entries use a different list in the page information:

```yaml
embeds:
  - type: video
    url: demonstration.mp4
    title: A short demonstration
  - type: pdf
    url: observations.pdf
    title: Downloadable observations
  - type: website
    url: /card/toolkit.html
    title: Prize Card Odds calculator
```

Place the first item by putting the following marker on a line of its own:

```text
[[embed:1]]
```

The second and third items use `[[embed:2]]` and `[[embed:3]]`. Items without placement markers appear after the article text. The website entry above points to a real local tool; its scripts and styles remain local too. PDF and website frames also provide direct source links.

## Keep the reading experience deliberate

A cover needs room for a wide crop, while an explanatory figure needs legible details. Check both uses rather than assuming one export fits every placement. Resize oversized images before saving them, and keep videos and PDFs reasonably sized: the static host serves the files you provide.

Video playback depends on the reader's browser and the file's encoding. Preview the actual file. For an external source or YouTube video, a normal link is often sufficient; it introduces no remote player into the article.

## Verify the folder, then the rendered page

The GitHub Pages workflow builds and checks local links, media references, and anchors when you push. On your own computer, run `python scripts/build.py --check` after editing. It builds `_site/` and refreshes the generated public pages in the repository root. Open the root `index.html`, or `_site/index.html`, directly and inspect the result at both wide and narrow screen sizes. No preview server is needed.

Keep the generated folders together when copying the website. Relative links and explicit `index.html` targets make the same HTML, CSS, JavaScript, and media usable through `file://` or on GitHub Pages. Building after the first dependency installation works offline; opening an already generated copy needs no Python installation.

Edit the source folder when something needs correcting, then rebuild and refresh the browser. The rendered site is the output; the story and its media stay together in their original folder. Sharing controls keep using the public canonical address when the page is opened locally, rather than copying a private file path.

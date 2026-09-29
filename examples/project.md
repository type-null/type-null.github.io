---
title: Building the PTCG calendar
# Replace these sample dates with the publication and writing dates you know.
date: 2026-09-29
# created: 2026-09-28
# updated: 2026-09-29
description: Replace this with what the project does and why you built it.
# article keeps the homepage cover without repeating it above the preview.
template: article
cover: /assets/images/editorial/toolkit.webp
# Save a screenshot as cover.png beside index.md (1000 × 480 recommended),
# then replace both cover above and image below with cover.png.
draft: true
tags: [Pokémon, Projects]
embeds:
  - type: project
    title: PTCG calendar
    image: /assets/images/editorial/toolkit.webp
    repository: https://github.com/type-null/PTCG-calendar
    url: https://type-null.github.io/PTCG-calendar/
    interactive: true
# Verify the app's deployment before publishing this article.
# Omit interactive for a screenshot link only.
# Until a website is available, omit both url and interactive to link to GitHub.
# For another project, change title, image, repository and url together.
# Optional labeled details:
# facts:
#   - label: Built with
#     value: Describe the project's tools
---

Explain the problem this project solves and what readers can explore. Its app stays in its own repository and has its own shareable website address.

[[embed:1]]

## What it does

Describe the useful features and what to try first. Readers can use the live preview or choose **Open website** for the complete independent interface. The circular GitHub button opens the source repository.

The hosted article loads the preview when it comes into view. Opening this article directly from disk keeps the local screenshot until **Use in this article** is requested while online. If the app is unavailable, the screenshot remains and readers can retry.

## How I built it

Explain the data, design choices, and useful implementation details. Source pushes rebuild and deploy the app at the same address, so this article needs no app-file synchronization. Refresh the screenshot and writing when useful, update `updated`, and rebuild the blog.

Live previews and external links need internet; this article and its screenshot remain readable offline. Remove `draft: true` when ready to publish. See the source checkout's `docs/PROJECTS.md` for the setup and the readiness response required by future embedded apps.

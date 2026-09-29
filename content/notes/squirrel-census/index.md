---
title: Central Park, through 3,023 squirrel sightings
date: 2026-09-29
created: 2026-09-29
updated: 2026-09-29
description: An interactive field guide to the 2018 Central Park Squirrel Census, revived from a student project and preserved as an offline exhibit.
template: article
eyebrow: Archived project
cover: cover.png
cover_alt: The Central Park squirrel field guide, with an illustrated squirrel and archive introduction.
tags: [Field notes, Projects, Maps, Data]
facts:
  - label: Observations
    value: "3,023 source rows"
  - label: Recorded
    value: October 6–20, 2018
  - label: Original project
    value: Weihang Ren and Zhongyu Zhang
  - label: Edition
    value: Archived exhibit — no live tracking
embeds:
  - type: project
    image: cover.png
    url: https://type-null.github.io/Website-central-park-squirrel-tracker/
    interactive: true
    title: Central Park squirrel field guide
    repository: https://github.com/type-null/Website-central-park-squirrel-tracker
---

A familiar park looks different when you explore it one observation at a time. The **2018 Central Park Squirrel Census** recorded where squirrels were seen, what they looked like, and what they were doing. This exhibit turns those observations into a map and field guide you can explore without a server.

The original Squirrel Tracker was a Tools for Analytics project by **Weihang Ren and Zhongyu Zhang**. Its web application supported importing records, browsing a map, viewing statistics, and editing sightings. This edition preserves the historical dataset as a read-only interactive exhibit.

The exhibit has its own website design and repository. Explore it below or open it independently; the circular GitHub button links to its source. This blog keeps the introduction and an offline preview while the application stays in its own repository.

## Explore the observations

Use the map and filters to investigate a question: where were cinnamon-colored squirrels recorded, which observations describe climbing, or how do morning and afternoon records differ? Open an observation to read its recorded details. A searchable list provides another way to explore the same records.

[[embed:1]]

## Read the patterns carefully

The exhibit contains **3,023 observations from October 6–20, 2018**, across 11 recorded dates. These are sighting records, not a count of unique animals or an estimate of today's squirrel population.

Some fields were left blank, so the filters keep unknown values visible. Five sighting IDs appear more than once with different coordinates; every source row is preserved. Activity flags can overlap: a single observation can describe both climbing and eating, for example. Counts for separate activities should not be added as if they were exclusive groups.

The park outline supplies geographic context. It comes from a later NYC Parks dataset and is not a reconstruction of the 2018 survey boundary. Recorded points remain at their original coordinates, including a small number just beyond that outline.

## An exhibit that can stay still

The map, records, styling, and fonts are saved in the exhibit's own repository. Its prepared `site/` folder works directly from disk and can be published through that repository's GitHub Pages. There is no live wildlife tracking or update schedule; this article is an invitation to explore an archived project and its data.

Data: [2018 Central Park Squirrel Census on NYC Open Data](https://data.cityofnewyork.us/Environment/2018-Central-Park-Squirrel-Census-Squirrel-Data/vfnx-vebw), collected by [The Squirrel Census](https://2019.thesquirrelcensus.com/about). Map context: [NYC Parks Properties](https://data.cityofnewyork.us/Recreation/Parks-Properties/enfh-gkve). The [original project repository](https://github.com/type-null/Website-central-park-squirrel-tracker) preserves the earlier application and its source data.

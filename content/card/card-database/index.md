---
title: Explore the Pokémon card database
date: 2026-09-29
created: 2026-09-29
updated: 2026-09-29
description: Search a small, illustrated selection from PTCG-database and open a card to explore its stored details.
template: article
eyebrow: Project notebook
cover: cover.png
cover_alt: A searchable gallery of Pokémon card artwork from the database.
tags: [Pokémon TCG, Projects, Data]
embeds:
  - type: project
    image: cover.png
    url: https://type-null.github.io/PTCG-database/
    interactive: true
    repository: https://github.com/type-null/PTCG-database
    title: Pokémon card database preview
---

A folder of card records is useful for analysis. A visual browser makes those records easier to explore: find a familiar card, compare its attributes, and open the details without leaving the gallery.

**PTCG-database** stores card information from multiple sources and languages. Its website offers a focused **48-card English preview**, with the selected artwork saved in that repository. It is a sample of the project, not a complete catalogue. Explore it below or open the independent website. The circular GitHub button links to the source.

## Start with the artwork

Search for **Pikachu** or **Mew**, then try the type and set filters. Select a card to see its stored fields. The preview includes Pokémon, Trainers, and Energy cards, so the details reflect the kind of card you opened.

[[embed:1]]

## What a card record can tell you

The browser shows the fields actually stored for each card, including its name, set, number, rarity, and available gameplay text. Records from different sources do not always contain the same information; a missing field is not evidence that the underlying attribute does not exist.

The full project also keeps identity keys for comparing printings. The preview's small selection only links records included in that edition. Source-page links remain available when you want to investigate beyond the local snapshot.

## Keeping the preview portable

The standalone browser carries its selected data and pictures with it. Searching and opening card details work directly from disk, as well as on the project's own GitHub Pages site. There is no live API or remote image dependency in the prepared preview.

Development and publishing stay in [PTCG-database](https://github.com/type-null/PTCG-database). This blog keeps the article and screenshot; the card records, artwork, and application remain in their own repository. Downloading that project's `site/` folder provides the independent offline browser.

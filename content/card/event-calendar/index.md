---
title: Play! Pokémon events, in one calendar
date: 2026-09-29
created: 2026-09-29
updated: 2026-09-29
description: A standalone Play! Pokémon calendar with month and list views, filters, and calendar export.
template: article
eyebrow: Project notebook
cover: cover.png
cover_alt: The Pokémon event calendar with month navigation and event filters.
tags: [Pokémon, Projects, Events]
embeds:
  - type: project
    image: cover.png
    url: https://type-null.github.io/PTCG-calendar/
    interactive: true
    repository: https://github.com/type-null/PTCG-calendar
    title: Play! Pokémon event calendar
---

A month view makes it easier to see which weekends are busy, which events overlap, and where a trip might fit. **PTCG-calendar** brings the Play! Pokémon Event Locator and Championship Series into one calendar that you can keep on your own computer.

Use the calendar below, or open its independent website for more room. The circular GitHub button opens the source repository. When you read this article offline, a saved screenshot remains available.

## Explore the calendar

Switch between **Month** and **List**, move to another month, and narrow the events with the search and game filters. Open an event for its venue and details. **Export .ics** saves the filtered events for another calendar application.

[[embed:1]]

## The edition shown here

The prepared calendar contains **29 Championship Series events**. The championship feed was retrieved on **September 29, 2026 at 18:58 UTC**. The nearby-store feed returned an error, so there are no store events in this edition; the calendar shows that partial-data status explicitly. Its “within 50 miles of Charlotte” setting applies to nearby store searches, while championship events can be farther away. This describes the edition used for this article, rather than promising a continuously refreshed schedule.

## Where the dates come from

The project reads two sources: nearby store events from the Event Locator and larger Championship Series events. A generated snapshot keeps the event data inside the page, so looking through it does not request a fresh feed or require a server.

Times are venue-local. The calendar keeps store listings and championship events distinguishable, and shows the source status so a partial snapshot does not look like a complete schedule. Confirm a date with its organizer before making travel plans.

## A separate home for the calendar

The application and its data stay in [PTCG-calendar](https://github.com/type-null/PTCG-calendar), which can publish its own GitHub Pages website. This article keeps only the introduction and screenshot. The project's prepared `site/index.html` also opens directly from disk when downloaded with its local assets.

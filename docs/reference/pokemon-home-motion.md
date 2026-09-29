# Pokémon homepage motion and section reference

Inspected the live [official homepage](https://www.pokemon.co.jp/) on 2026-09-29 using Chrome at 1440 × 1000 and 390 × 844. Sources: the page DOM, [official stylesheet](https://www.pokemon.co.jp/css/style.css?v=20260724), and [official script](https://www.pokemon.co.jp/js/script.js). Browser measurements are retained in [pokemon-home-motion.json](pokemon-home-motion.json). These are observations of the reference, not claims about this repository's implementation.

## Scroll behavior

The colored backgrounds reveal once when scrolling down; they are not scroll-position parallax. The reference adds a `run` class at a waypoint and then removes that waypoint.

| Area | Initial state → revealed state | Timing | Trigger |
| --- | --- | --- | --- |
| NEWS | Three white vertical strips shrink horizontally, exposing the background | 700 ms; all delayed 300 ms | Background top crosses 70% of viewport height |
| GOODS | Three white horizontal strips shrink horizontally in sequence | 700 ms; delays 300, 400, 500 ms | Background top crosses 70% |
| MOVIE main | Entire colored panel translates from one panel-width left to its resting position | 500 ms, no delay | Background top crosses 70% |
| MOVIE thumbnails | Entire colored panel translates from one panel-width right to its resting position | 500 ms, no delay | Background top enters viewport |
| EVENT | Background is already present | No entrance animation | None |

All entrance transitions use `cubic-bezier(.97,0,.1,1.01)`. NEWS strips start at 0%, 34%, and 68% from the left and occupy 34% width and full height. GOODS strips occupy full width and 34% height, starting at 0%, 34%, and 68% from the top. Their left edges stay fixed as their widths approach zero.

Colored panels also contain a slow, continuously moving pastel gradient: pink, yellow, cream, cyan, lavender, and pale pink, followed by repeated pink/yellow/cream stops to continue the sequence across the loop. The background is 700% wide and moves horizontally from 0% to 86% over eight seconds, repeating linearly. Computed styles showed that this continues under the reference site's reduced-motion setting. Our recreation explicitly stops decorative motion for that preference.

## Background dimensions

| Area | Desktop, 1440 px viewport | Mobile, 390 px viewport |
| --- | --- | --- |
| NEWS | 1224 × 500; left aligned; vertically centered in section | 290 × 795; left aligned, 16 px from section top |
| GOODS | 979.19 × 500; right aligned; top 63 px | 260 × 704; right aligned; top 16 px |
| MOVIE main | 1120 × 500; left aligned | 285 × 285; left aligned |
| MOVIE thumbnail strip | 1160 × 100; right aligned | 350 × 70; right aligned |
| EVENT | Full width, extends below content; begins 200 px below section top | Full width; begins 25 px below section top |

## Different content compositions

- **NEWS:** A prominent first article, offset smaller cards, then a second row; detailed geometry is documented separately. The mobile version is a single column.
- **GOODS:** A compact three-column image grid occupies the left block; a separate ranking panel occupies the right. Actual desktop thumbnails measured 204.33 × 136.22 px. Mobile changes to a single column of horizontal rows, with approximately half the row reserved for the image and half for the title/date. It does not retain a two-column tile grid.
- **MOVIE:** A wide central 16:9 feature, title/date beneath, and a separate row of small selectable previews. The feature is 970 px wide in a 1050 px desktop wrapper. On mobile it spans the viewport and previews scroll horizontally.
- **EVENT:** A left-aligned heading and a row of four dated image cards above a large calendar. Mobile hides that pickup row and keeps the calendar. The dated cards are not a sidebar.

For this personal blog, the reference supports a compact Cards image gallery, a Sports lead feature with smaller previews, and a Notes reading list that emphasizes dates. Those are content adaptations: we should not invent popularity statistics, video controls for ordinary articles, or calendar events merely to duplicate the official site's commercial content.

## Recreation and verification notes

Keep article links and content visible independently of animation. Use local CSS gradients instead of downloaded background images. Add entrance behavior only when JavaScript and the observer are available; use a static final appearance for reduced motion and no JavaScript. Animate transforms rather than repeatedly laying out width changes when the visual result is equivalent.

For an IntersectionObserver-based 70%-height trigger, calculate the bottom margin in pixels from viewport height. Percentage root margins are based on root width, so a literal `-30%` bottom margin would move the trigger inconsistently between desktop and mobile.

The measurement file contains three scroll states per section: just before the trigger, 500 ms after crossing it, and after a further 1300 ms. The main MOVIE samples intentionally leave the desktop thumbnail background below the viewport; its first-entry trigger was confirmed in source and in the mobile measurements. Temporary screenshots of these exact positions are in `/tmp/pokemon-motion-reference/`; no official JavaScript, tracking code, or runtime assets were added to this website.

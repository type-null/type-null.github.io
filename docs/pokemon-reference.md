# Pokémon homepage visual reference

Inspected the fully loaded [official homepage](https://www.pokemon.co.jp/) on September 29, 2026, at desktop (1440 × 1000) and mobile (390 × 844) sizes. The source was the [homepage stylesheet](https://www.pokemon.co.jp/css/style.css?v=20260724), compared with the earlier Pokémon stylesheet already retained in `archive/original-assets/assets/css/style.css`.

Reference captures: [desktop news](reference/pokemon-news-desktop.png) and [mobile homepage](reference/pokemon-home-mobile.png). The live page was scrolled to load artwork and complete its entrance animations before inspecting news layout.

## Shared visual system

| Component | Reference values used |
| --- | --- |
| Body | White; text `#404248`; Noto Sans JP, 16 px desktop / 14 px mobile |
| Headings and dates | Lato; NEWS 50 px desktop / 32 px mobile |
| Header | 80 px desktop / 60 px mobile; fixed, white on scroll; original illustrated personal logo |
| Desktop navigation | Bold 16 px text, category underline, square utility links |
| Mobile navigation | Left menu toggle, centered logo, right search; blue gradient menu |
| Hero | Full-width campaign panel, 1920:923 desktop / 750:920 mobile; progress bars and right-edge blue link |
| News container | 1240 px including 20 px side padding; 1200 px usable width |
| First news row | 500 / 310 / 310 px at desktop; heading beside the leading image |
| News images | Artwork area 500:240, whole-image containment; caption adds height below; 10 px corners; `0 0 15px rgba(0,0,0,.15)` shadow |
| Captions | Desktop strip `min(40px, 2.8vw)`, text `min(15px, 1.1vw)`; mobile 40 px / 15 px; 1 px seam overlap |
| News metadata | Vertical category label; title and date indented 50 px; date 12 px |
| Mobile news | Single column; 350 px images at 390 px viewport; 20 px outer gutters |
| News background | 500 px tall pastel band at 85% viewport width; broad gradient with 700% background sizing |
| Buttons | `#489fe6` to `#84c3f6` gradient, round ends, white text and arrow |
| Card category | Purple `#5969df`; sports maps to green `#00c879`; notes uses blue `#489fe6` |
| Article title | 34 px desktop / 24 px mobile; original news/detail structure and dotted separators |

## Homepage hierarchy to preserve

Keep the approved desktop and mobile compositions as the baseline for later changes. The reference's variety works within a clear sequence, and this site follows that sequence:

| Level | Role on this homepage |
| --- | --- |
| Header and featured campaign | Orient the reader and provide one main visual entry point; the carousel occupies a single shared area. |
| INFORMATION | A compact, quieter update strip between the campaign and the article index. |
| NEWS | The primary browsing section: the six newest posts, with one leading card and a link to the complete index. |
| Topic destinations | Cards, Sports, then Notes: bounded previews that lead to their own topic pages. Their order also matches the main navigation. |
| Footer | Quiet utility links and site attribution. |

Topic formats vary inside this structure. Cards emphasizes a gallery, Sports uses a lead feature and smaller supporting links, and Notes finishes with compact dated rows. Each keeps the shared heading scale, typography, outer gutters, button style, and section spacing. The wide Sports feature belongs to its topic; the campaign remains the single introductory feature area.

Keep color panels behind the content and let their motion mark section arrivals. Artwork, titles, dates, and links stay stable and readable. Mobile preserves the same reading order while rearranging each section's contents for the available width.

For new topics, `home_layout` selects an existing composition and `order` controls both navigation and homepage position. Keep the existing preview limits (gallery six, feature one plus two, journal four) and use the topic page for the complete collection. Check future changes against the [desktop](qa/home-desktop.png) and [mobile](qa/home-mobile.png) captures as whole pages, as well as inspecting individual components.

## Content and functional adaptations

The site retains its own logo, writing, artwork, and folder-derived topics. Official advertisements, analytics, social trackers, and external runtime dependencies are not copied. The homepage shows **six** latest articles, as requested; the reference snapshot contained seven. The complete article index is generated at `/posts/`.

The hero uses local featured-post artwork, with optional separately authored desktop/mobile banners. News cards use the blog's own cover images. These content differences mean the screenshots are not pixel-identical to the official site's current campaigns. The layout and styling follow the inspected components, rather than an unrelated blog theme.

The six-post adaptation uses 500 / 310 / 310 px in the first row and three equal 310 px cards in the second, with 40 px gaps at a 1440 px viewport. The reference's last two cards are 230 px wide to fit its seven-item layout; applying that rule to our sixth card made it unexpectedly small. Sparse rows now use fixed gutters and start at the left in news, topic, related-post, and filtered archive lists.

Measured full figures (art plus caption) are now 500 × 279 px for the lead and 310 × 187.8 px for regular desktop cards. At a 390 px viewport, all figures are 350 × 207 px. At 1024 px, the lead is 410 × 224.47 px. Covers of other proportions remain completely visible; 1000 × 480 artwork fills the news frame.

Below NEWS, topic metadata selects a Cards image gallery, Sports feature with smaller previews, or Notes dated reading list. The gallery changes to horizontal image/text rows on phones. These follow the reference's GOODS, MOVIE, and dated-event compositions while using real local blog entries. See the [scroll-motion research](reference/pokemon-home-motion.md) for measured timing, trigger positions, and background dimensions.

NEWS reveals three vertical strips; gallery sections reveal three staggered horizontal strips; feature and journal sections slide their color panels from opposite sides. Slow pastel drift pauses offscreen. The decorations settle immediately for reduced motion and remain visible without JavaScript or IntersectionObserver. The official EVENT background is static; the journal entrance is an intentional adaptation.

The original résumé content remains accessible at its existing URL, with the same shared article styling and no listing links. The card calendar preserves month alignment while displaying every pack image, using smaller local previews instead of hiding artwork.

## Interactive articles

Website embeds use a compact title and the shared blue pill-shaped **Open in new tab** button above a thin frame. The toolbar belongs to the article's content column and wraps on phones. It uses an ordinary link, so opening the standalone tool also works without page JavaScript.

Companion projects use a lighter portal: a locally saved, 1000 × 480 screenshot that opens the project's own website, plus a circular 44-pixel GitHub source control and an optional blue **Open website** button. Before a website is published, the screenshot opens its repository. There is no remote player or copied application in these articles. The buttons use ordinary links and an inline SVG icon, with keyboard focus and no-JavaScript support.

The [official card search](https://www.pokemon-card.com/card-search/), [Pokédex](https://zukan.pokemon.co.jp/), and [homepage calendar](https://www.pokemon.co.jp/) were inspected as companion-site references. Their task-specific layouts informed the separate calendar, card browser, and squirrel exhibit: compact filters, contained artwork, clear date hierarchy, and readable mobile layouts. A research site can use a completely independent visual identity while its introductory post retains this blog's shared shell.

The three local tools follow the same visual system inside the frame and in standalone tabs: local Noto Sans JP and Lato, white backgrounds, `#404248` text, restrained gray surfaces, modest 10 px panel corners, dotted separators, and the site's blue primary buttons. Secondary actions use quieter outlined buttons. Numeric results and game outcomes retain their own readable emphasis. Tool layouts are adaptations of the site's shared styling, not copies of an official Pokémon calculator.

## Local fonts

`assets/fonts/pokemon-fonts.css` loads local Lato and Noto Sans JP files. Unicode subsets allow Japanese text without downloading the entire font on every page. Both SIL Open Font Licenses are included. No Google Fonts or other CDN request is required at runtime.

Desktop/mobile geometry, navigation visibility, six-post ordering, image decoding, search, and no-JavaScript behavior are covered by `tests/test_site_ui.py`. Visual comparison is a separate manual check; passing geometry tests does not imply pixel identity.

---
title: Why the second draw changes the odds
date: 2026-09-29
updated: 2026-09-29
description: Two copies, six prizes, and the small dependency that makes an exact card calculation different from repeated coin flips.
template: article
subtitle: Counting cards without putting them back.
eyebrow: Probability notebook
cover: /assets/images/editorial/toolkit.webp
cover_alt: Six face-down prize cards numbered one through six on a mint background.
toc: true
tags: [Probability, Cards, Mathematics]
facts:
  - label: Worked example
    value: 60 cards · 2 copies · 6 prizes
  - label: Both copies prized
    value: 0.84746%
  - label: Model
    value: Uniform draw without replacement
links:
  - label: Try the prize calculator
    url: /card/prize-card-odds/
    style: primary
related:
  - /card/prize-card-odds/
  - /sports/trading-suits/
---

A shuffled deck looks random, but its draws are connected. Once a card leaves the deck, the next draw comes from a smaller collection. That small change matters when the question is whether several copies of one card land in the same group.

The [prize-card calculator](/card/prize-card-odds/) makes a useful example. It samples six prizes uniformly from a 60-card deck containing two copies of a particular card. This is a sampling model, before conditioning on an opening hand or other information.

## One copy is easy; two copies share the deck

A particular card occupies one of 60 positions. Six positions are prizes, so its chance of being prized is `6 / 60 = 10%`.

It is tempting to multiply `10% × 10%` for both copies and obtain 1%. But after locating the first copy in a prize position, only five prize positions remain among the other 59 positions. The correct calculation is:

```text
P(both copies prized) = (6 / 60) × (5 / 59)
                      = 0.84746%
```

The second copy has a slightly smaller conditional chance. That is why treating the copies as independent overstates this particular event.

## Count groups instead of drawing every sequence

For a deck of `N` cards, containing `C` copies, with `P` prizes, the probability of exactly `k` copies in prizes is:

```text
C(C, k) × C(N − C, P − k) / C(N, P)
```

Here `C(n, r)` means “choose r objects from n”; the repeated letter does not mean multiplication. The numerator chooses the desired copies and the other cards needed to complete the prizes. The denominator counts every possible prize group.

For the default example, the complete distribution is:

| Copies prized | Probability |
| --- | --- |
| 0 | 80.84746% |
| 1 | 18.30508% |
| 2 | 0.84746% |

Subtracting the final row from 100% gives **99.15254%**: at least one copy is not prized. That wording includes a copy in the opening hand; it does not promise that a copy remains in the draw deck.

## Impossible outcomes belong outside the table

The possible count starts at `max(0, P − (N − C))` and ends at `min(C, P)`. For example, an eight-card deck with six copies and three prizes cannot have zero copies prized: there are only two other cards available.

Its possible counts are one, two, and three, with probabilities **10.71429%, 53.57143%, and 35.71429%**. Bounds are part of the model, not merely input formatting.

Try those values in the calculator, then try zero prizes. If at least one copy exists, zero prizes makes “at least one not prized” certain. With zero copies, that event is impossible. These simple boundary cases are useful checks on both the arithmetic and the meaning of the result.

---
title: What a ten-card hand can tell you
date: 2026-09-29
updated: 2026-09-29
description: Follow one real Trading Suits input from equal prior probabilities to a conditional result, and see where the model's certainty ends.
template: article
subtitle: A probability is a statement about a model as well as a hand.
eyebrow: Probability notebook
cover: /assets/images/editorial/sports.webp
cover_alt: The ace of spades and ace of hearts on a lavender background.
toc: true
tags: [Probability, Games, Models]
facts:
  - label: Candidate decks
    value: Four equally likely compositions
  - label: Sample
    value: Ten cards without replacement
  - label: Example leader
    value: Clubs · 52.3%
links:
  - label: Explore the hand assessor
    url: /sports/trading-suits/
    style: primary
related:
  - /sports/trading-suits/
  - /card/prize-card-odds/
---

A hand of five spades, three clubs, one heart, and one diamond contains more spades than anything else. Does that make spades the most likely gold suit? In this site's [Trading Suits model](/sports/trading-suits/), the answer is no. The result depends on how each possible gold suit is connected to the composition of the deck.

That distinction is the useful part of the exercise: visible frequency is evidence, while the interpretation of that evidence comes from stated assumptions.

## Begin with the candidate decks

The assessor uses these four 40-card decks:

| Gold suit | Spades | Clubs | Hearts | Diamonds |
| --- | --- | --- | --- | --- |
| Spades | 10 | 12 | 10 | 8 |
| Clubs | 12 | 10 | 10 | 8 |
| Hearts | 8 | 10 | 10 | 12 |
| Diamonds | 10 | 8 | 12 | 10 |

Each row starts with a 25% prior probability. Ten cards are drawn uniformly without replacement. Those are the assumptions needed to interpret the input.

The original playbook contained conflicting gold-suit mappings. The current tool preserves its final active composition table and displays it explicitly. These calculations verify the behavior of that model; they do not establish that the table matches an independently checked rulebook.

## Ask which deck could produce the hand

For the hand `5, 3, 1, 1`, count the ways each candidate deck can supply those suit counts. For the Clubs-gold row, that count is:

```text
C(12, 5) × C(10, 3) × C(10, 1) × C(8, 1)
= 7,603,200
```

The corresponding counts for Spades, Hearts, and Diamonds gold are 4,435,200, 806,400, and 1,693,440. Each count shares the same denominator, `C(40, 10)`. Because the four priors are also equal, normalizing these counts gives the posterior probabilities directly.

| Gold suit | Before seeing the hand | After seeing the hand |
| --- | --- | --- |
| Spades | 25% | 30.507% |
| Clubs | 25% | 52.298% |
| Hearts | 25% | 5.547% |
| Diamonds | 25% | 11.648% |

Clubs leads because its candidate deck contains twelve spades. The tool's example button enters this hand and displays the same result rounded to one decimal place.

## A lead is not a conclusion

Now enter two spades, two clubs, three hearts, and three diamonds. The result is **18.75%, 18.75%, 31.25%, 31.25%** in the same order. Hearts and Diamonds tie. The tool should report that tie rather than choose whichever label happens to appear first.

Neither example identifies a gold suit with certainty. A posterior is conditional on the candidate decks, their priors, and the sampling process. If the actual rules differ, or the hand was selected rather than randomly dealt, the interpretation changes.

A useful habit is to read the assumptions before the largest percentage. Then change one input and compare the full distribution. That shows what the evidence changed, and how much uncertainty remains.

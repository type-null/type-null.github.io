/* Small, dependency-free probability models shared by the retained tools. */
(function (global) {
  'use strict';
  const SUITS = ['Spades', 'Clubs', 'Hearts', 'Diamonds'];
  // Preserve the final active model in the original playbook. Display these
  // assumptions beside the calculator so the result is never a hidden rule.
  const GOLD_DECKS = [
    [10, 12, 10, 8],
    [12, 10, 10, 8],
    [8, 10, 10, 12],
    [10, 8, 12, 10]
  ];
  function logChoose(n, k) {
    if (!Number.isInteger(n) || !Number.isInteger(k) || n < 0 || k < 0 || k > n) return -Infinity;
    let result = 0;
    for (let i = 1; i <= Math.min(k, n - k); i++) result += Math.log(n - i + 1) - Math.log(i);
    return result;
  }
  function normalizeLogs(logs) {
    const max = Math.max(...logs);
    if (!Number.isFinite(max)) throw new RangeError('This observation is impossible under every model.');
    const weights = logs.map(value => Math.exp(value - max));
    const sum = weights.reduce((a, b) => a + b, 0);
    return weights.map(value => value / sum);
  }
  function goldProbabilities(hand) {
    if (!Array.isArray(hand) || hand.length !== 4 || hand.some(n => !Number.isInteger(n) || n < 0 || n > 10) || hand.reduce((a, b) => a + b, 0) !== 10) {
      throw new RangeError('Enter four whole-number counts from 0 to 10, totaling 10 cards.');
    }
    // Equal priors and the common C(40, 10) denominator cancel. A single
    // multivariate hypergeometric likelihood avoids conditional-size mistakes.
    return normalizeLogs(GOLD_DECKS.map(deck => deck.reduce((sum, n, i) => sum + logChoose(n, hand[i]), 0)));
  }
  function prizeDistribution(deck, copies, prizes) {
    if (![deck, copies, prizes].every(Number.isInteger) || deck < 1 || deck > 500 || copies < 0 || prizes < 0 || copies > deck || prizes > deck) {
      throw new RangeError('Use a deck of 1–500 cards; copies and prizes must be whole numbers between 0 and the deck size.');
    }
    const lower = Math.max(0, prizes - (deck - copies));
    const upper = Math.min(copies, prizes);
    const counts = Array.from({length: upper - lower + 1}, (_, i) => lower + i);
    const probabilities = normalizeLogs(counts.map(k => logChoose(copies, k) + logChoose(deck - copies, prizes - k)));
    const distribution = counts.map((prized, i) => ({prized, probability: probabilities[i]}));
    const available = distribution.reduce((sum, item) => sum + (item.prized < copies ? item.probability : 0), 0);
    return {distribution, available};
  }
  global.ToolProbability = Object.freeze({SUITS, GOLD_DECKS, logChoose, goldProbabilities, prizeDistribution});
})(globalThis);

/* Run with: node tests/tool_probability.test.js
 * Kept free of a test framework so the same checks can run in a browser/V8 harness.
 */
function runProbabilityTests(model) {
  let checks = 0;
  function assert(condition, message) {checks++; if (!condition) throw new Error(message);}
  function close(actual, expected, message) {assert(Math.abs(actual - expected) < 1e-11, `${message}: ${actual} vs ${expected}`);}
  function choose(n, k) {
    if (k < 0 || k > n) return 0;
    let result = 1;
    for (let i = 1; i <= k; i++) result = result * (n - i + 1) / i;
    return result;
  }
  function rejects(callback, message) {let rejected = false; try {callback();} catch (error) {rejected = error instanceof RangeError;} assert(rejected, message);}
  // Exhaustive comparison against a separately implemented combinatorial oracle.
  let hands = 0;
  for (let s = 0; s <= 10; s++) for (let c = 0; c <= 10 - s; c++) for (let h = 0; h <= 10 - s - c; h++) {
    const hand = [s, c, h, 10 - s - c - h];
    const likelihoods = model.GOLD_DECKS.map(deck => deck.reduce((p, n, i) => p * choose(n, hand[i]), 1));
    const total = likelihoods.reduce((a, b) => a + b, 0);
    const actual = model.goldProbabilities(hand);
    actual.forEach((value, i) => close(value, likelihoods[i] / total, `Posterior for ${hand}, suit ${i}`));
    close(actual.reduce((a, b) => a + b, 0), 1, 'Posterior normalization'); hands++;
  }
  // Regression: previous conditional-population arithmetic gave Clubs 45.1967%.
  close(model.goldProbabilities([5, 3, 1, 1])[1], 0.5229793977812994, 'Known likelihood regression');
  [[-1, 5, 3, 3], [1.5, 2.5, 3, 3], [10, 1, 0, 0], [NaN, 0, 0, 0], [Infinity, 0, 0, 0], [1, 2, 3], [11, -1, 0, 0]].forEach(hand => rejects(() => model.goldProbabilities(hand), 'Invalid hand rejected'));
  const normal = model.prizeDistribution(60, 2, 6);
  close(normal.available, 1 - 1 / 118, 'Two copies in six prizes');
  close(normal.distribution[2].probability, 1 / 118, 'All copies prized');
  let prizeCases = 0;
  // Degenerate inputs and non-standard decks exercise the whole support range.
  for (let deck = 1; deck <= 25; deck++) for (let copies = 0; copies <= deck; copies++) for (let prizes = 0; prizes <= deck; prizes++) {
    const result = model.prizeDistribution(deck, copies, prizes);
    let expectedAvailable = 0;
    result.distribution.forEach(item => {
      const expected = choose(copies, item.prized) * choose(deck - copies, prizes - item.prized) / choose(deck, prizes);
      close(item.probability, expected, 'Prize combinatorial oracle');
      if (item.prized < copies) expectedAvailable += expected;
    });
    close(result.available, expectedAvailable, 'Available probability');
    close(result.distribution.reduce((sum, item) => sum + item.probability, 0), 1, 'Prize normalization'); prizeCases++;
  }
  const large = model.prizeDistribution(500, 250, 250);
  close(large.distribution.reduce((sum, item) => sum + item.probability, 0), 1, 'Large-deck numerical stability');
  assert(large.distribution.every(item => Number.isFinite(item.probability)), 'No numerical overflow');
  [[0, 0, 0], [501, 2, 6], [60, 61, 6], [60, 2, 61], [60, -1, 6], [60, 2.5, 6], [NaN, 1, 1]].forEach(args => rejects(() => model.prizeDistribution(...args), 'Invalid prize input rejected'));
  return {checks, hands, prizeCases};
}
if (typeof module !== 'undefined' && module.exports) {
  require('../assets/js/tools/probability.js');
  console.log(JSON.stringify(runProbabilityTests(globalThis.ToolProbability)));
}

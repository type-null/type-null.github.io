'use strict';
const prizeFields = ['deckSize', 'copies', 'prizeCards'];
function prizeValues() {
  return prizeFields.map(id => {const value = document.getElementById(id).value; return value === '' ? NaN : Number(value);});
}
function calculate() {
  try {
    const [deck, copies, prizes] = prizeValues();
    const result = ToolProbability.prizeDistribution(deck, copies, prizes);
    document.getElementById('prize-error').textContent = '';
    document.getElementById('copies').max = deck;
    document.getElementById('prizeCards').max = deck;
    document.getElementById('atLeastOne').textContent = `${(result.available * 100).toFixed(2)}%`;
    document.getElementById('result-summary').textContent = `${copies} ${copies === 1 ? 'copy' : 'copies'} · ${prizes} prizes · ${deck}-card deck`;
    const table = document.getElementById('distribution'); table.replaceChildren();
    result.distribution.forEach(item => {
      const row = document.createElement('tr');
      const count = document.createElement('th'); count.scope = 'row'; count.textContent = item.prized;
      const chance = document.createElement('td'); chance.textContent = item.probability > 0 && item.probability < .0001 ? '<0.01%' : `${(item.probability * 100).toFixed(2)}%`;
      row.append(count, chance); table.append(row);
    });
    document.querySelectorAll('[data-field]').forEach(button => {
      const index = prizeFields.indexOf(button.dataset.field);
      const delta = Number(button.dataset.delta);
      const lower = index === 0 ? Math.max(1, copies, prizes) : 0;
      const upper = index === 0 ? 500 : deck;
      button.disabled = delta < 0 ? prizeValues()[index] <= lower : prizeValues()[index] >= upper;
    });
  } catch (error) {
    document.getElementById('prize-error').textContent = error.message;
    document.getElementById('atLeastOne').textContent = '—';
    document.getElementById('result-summary').textContent = 'Correct the inputs to calculate your odds.';
    document.getElementById('distribution').replaceChildren();
    document.querySelectorAll('[data-field]').forEach(button => button.disabled = false);
  }
}
function updateValue(field, delta) {
  const [deck, copies, prizes] = prizeValues();
  const input = document.getElementById(field);
  const lower = field === 'deckSize' ? Math.max(1, copies || 0, prizes || 0) : 0;
  const upper = field === 'deckSize' ? 500 : deck;
  input.value = Math.min(upper, Math.max(lower, (Number(input.value) || 0) + delta));
  calculate();
}
document.getElementById('prize-form').addEventListener('submit', event => event.preventDefault());
prizeFields.forEach(id => document.getElementById(id).addEventListener('input', calculate));
document.querySelectorAll('[data-field]').forEach(button => button.addEventListener('click', () => updateValue(button.dataset.field, Number(button.dataset.delta))));
document.getElementById('reset-prizes').addEventListener('click', () => {prizeFields.forEach((id, i) => document.getElementById(id).value = [60, 2, 6][i]); calculate();});
calculate();

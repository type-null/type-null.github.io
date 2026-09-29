'use strict';
const app = {
  archetypeData: {
    rock: {name: 'The Rock', icon: '🪨', description: 'Trades infrequently and looks for strong evidence.', strategy: 'Notice which suits attract their rare bids. Their actions may carry information.', defense: 'Do not assume silence proves they have a weak hand.'},
    maniac: {name: 'The Adventurer', icon: '⚡', description: 'Trades frequently and tolerates large swings.', strategy: 'Compare offered prices with your own hand estimate before responding.', defense: 'Frequent activity does not necessarily mean useful private information.'},
    calculator: {name: 'The Calculator', icon: '⌘', description: 'Uses consistent rules and adjusts carefully.', strategy: 'Observe the conditions that change their bids; update your model as evidence arrives.', defense: 'Remember that they are also learning from your visible behavior.'},
    follower: {name: 'The Follower', icon: '🐑', description: 'Waits for other players to establish a direction.', strategy: 'Separate independent signals from trades that repeat an existing trend.', defense: 'Several players following one signal do not provide several independent observations.'}
  },
  init() {
    document.querySelectorAll('[data-section]').forEach(button => button.addEventListener('click', () => this.showSection(button.dataset.section)));
    document.querySelectorAll('.card-input').forEach(input => input.addEventListener('input', () => this.updateTotalCards()));
    document.getElementById('hand-form').addEventListener('submit', event => {event.preventDefault(); this.calculateProbabilities();});
    document.getElementById('example-hand').addEventListener('click', () => {document.querySelectorAll('.card-input').forEach((input, i) => input.value = [5, 3, 1, 1][i]); this.updateTotalCards(); this.calculateProbabilities();});
    document.getElementById('bankroll').addEventListener('input', () => this.updateBudget());
    document.querySelectorAll('[name=confidence]').forEach(input => input.addEventListener('change', () => this.updateBudget()));
    this.updateChart([.25, .25, .25, .25]);
    this.populateArchetypes(); this.showArchetype('rock'); this.updateBudget();
  },
  showSection(id) {
    document.querySelectorAll('main > section').forEach(section => section.hidden = section.id !== id);
    document.querySelectorAll('[data-section]').forEach(button => button.setAttribute('aria-pressed', button.dataset.section === id));
  },
  hand() {return [...document.querySelectorAll('.card-input')].map(input => input.value === '' ? NaN : Number(input.value));},
  updateTotalCards() {
    const hand = this.hand();
    const whole = hand.every(n => Number.isInteger(n) && n >= 0 && n <= 10);
    const total = hand.reduce((a, b) => a + b, 0);
    document.getElementById('total-cards').textContent = Number.isFinite(total) ? total : '—';
    document.getElementById('calculate-btn').disabled = !whole || total !== 10;
    document.getElementById('hand-error').textContent = !whole ? 'Use whole-number counts from 0 to 10.' : total !== 10 ? 'The four counts must add up to ten.' : '';
    document.getElementById('assessor-interpretation').textContent = 'Hand changed. Calculate to update the probabilities below.';
  },
  calculateProbabilities() {
    try {
      const values = ToolProbability.goldProbabilities(this.hand());
      this.updateChart(values);
      const max = Math.max(...values);
      const leaders = values.map((v, i) => Math.abs(v - max) < 1e-10 ? ToolProbability.SUITS[i] : null).filter(Boolean);
      document.getElementById('assessor-interpretation').textContent = leaders.length > 1 ? `${leaders.join(' and ')} are tied at ${(max * 100).toFixed(1)}% each under the stated model.` : `${leaders[0]} is the most likely gold suit: ${(max * 100).toFixed(1)}% under the stated model.`;
      document.getElementById('hand-error').textContent = '';
    } catch (error) {document.getElementById('hand-error').textContent = error.message;}
  },
  updateChart(values) {
    const chart = document.getElementById('probabilityChart'); chart.replaceChildren();
    values.forEach((value, index) => {
      const row = document.createElement('div'); row.className = 'bar';
      const heading = document.createElement('div'); heading.className = 'bar-heading';
      const label = document.createElement('span'); label.textContent = ToolProbability.SUITS[index];
      const amount = document.createElement('span'); amount.textContent = `${(value * 100).toFixed(1)}%`;
      heading.append(label, amount);
      const track = document.createElement('div'); track.className = 'bar-track'; track.setAttribute('aria-hidden', 'true');
      const bar = document.createElement('div'); bar.className = 'bar-fill'; bar.style.width = `${value * 100}%`;
      track.append(bar); row.append(heading, track); chart.append(row);
    });
  },
  populateArchetypes() {
    const parent = document.getElementById('archetype-selector');
    Object.entries(this.archetypeData).forEach(([key, item]) => {
      const button = document.createElement('button'); button.type = 'button'; button.className = 'chip'; button.dataset.archetype = key; button.textContent = `${item.icon} ${item.name}`; button.addEventListener('click', () => this.showArchetype(key)); parent.append(button);
    });
  },
  showArchetype(key) {
    const item = this.archetypeData[key];
    document.querySelectorAll('[data-archetype]').forEach(button => button.setAttribute('aria-pressed', button.dataset.archetype === key));
    const parent = document.getElementById('archetype-display'); parent.replaceChildren();
    for (const [tag, text] of [['h3', item.name], ['p', item.description], ['h3', 'Look for'], ['p', item.strategy], ['h3', 'Keep in mind'], ['p', item.defense]]) {const node = document.createElement(tag); node.textContent = text; parent.append(node);}
  },
  updateBudget() {
    const balance = Number(document.getElementById('bankroll').value);
    const confidence = document.querySelector('[name=confidence]:checked').value;
    const fraction = {low: 1 / 8, medium: 1 / 4, high: 1 / 2}[confidence];
    const lower = Math.round(balance * fraction * .1 / 5) * 5;
    const upper = Math.round(balance * fraction * .16 / 5) * 5;
    document.getElementById('bankroll-value').textContent = `${balance.toLocaleString()} credits`;
    document.getElementById('budget-recommendation').textContent = `${lower}–${upper} credits`;
    document.getElementById('budget-rule').textContent = `${(fraction * 10).toFixed(2)}–${(fraction * 16).toFixed(2)}% of the game balance, rounded to five credits.`;
  }
};
app.init();

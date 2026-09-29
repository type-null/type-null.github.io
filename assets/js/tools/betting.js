/* Probability Parlay: pure rules first, browser UI below. No remote services. */
(function (root) {
  'use strict';
  const sum = values => values.reduce((a, b) => a + b, 0);
  const createDeck = () => ['♥', '♦', '♣', '♠'].flatMap(suit =>
    ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A'].map(rank =>
      ({suit, rank, value: rank === 'A' ? 11 : ['J', 'Q', 'K'].includes(rank) ? 10 : Number(rank)})));
  const diceEvents = [
    ['Sum 2 or 3', d => [2, 3].includes(sum(d))], ['Sum 4', d => sum(d) === 4],
    ['Sum 5', d => sum(d) === 5], ['Sum 9', d => sum(d) === 9], ['Sum 10', d => sum(d) === 10],
    ['Sum 6, 7 or 8', d => [6, 7, 8].includes(sum(d))], ['Sum 11 or 12', d => sum(d) >= 11],
    ['Even sum', d => sum(d) % 2 === 0], ['Odd sum', d => sum(d) % 2 === 1],
    ['Product > 30', d => d[0] * d[1] > 30], ['Doubles', d => d[0] === d[1]]
  ].map(([text, test], index) => ({id: `dice-${index}`, text, test, group: 'dice'}));
  const coinEvents = [
    ['All identical', c => new Set(c).size === 1], ['More heads than tails', c => c.filter(x => x === 'H').length > 1],
    ['Three heads', c => c.every(x => x === 'H')], ['Three tails', c => c.every(x => x === 'T')],
    ['Exactly two heads', c => c.filter(x => x === 'H').length === 2],
    ['Exactly one head', c => c.filter(x => x === 'H').length === 1],
    ['At least one head', c => c.includes('H')], ['At least one tail', c => c.includes('T')],
    ['First and last match', c => c[0] === c[2]]
  ].map(([text, test], index) => ({id: `coin-${index}`, text, test, group: 'coin'}));
  const product = h => h[0].value * h[1].value;
  const cardEvents = [
    ['Product > 100', h => product(h) > 100], ['Even product', h => product(h) % 2 === 0],
    ['Product < 20', h => product(h) < 20], ['Product > 75', h => product(h) > 75],
    ['Product 40–60', h => product(h) >= 40 && product(h) <= 60],
    ['Perfect-square product', h => Number.isInteger(Math.sqrt(product(h)))],
    ['Product ends in 0', h => product(h) % 10 === 0],
    ['Both face cards', h => h.every(c => ['J', 'Q', 'K'].includes(c.rank))],
    ['Same value', h => h[0].value === h[1].value]
  ].map(([text, test], index) => ({id: `card-${index}`, text, test, group: 'card'}));
  const deck = createDeck();
  const diceSpace = Array.from({length: 36}, (_, i) => [Math.floor(i / 6) + 1, i % 6 + 1]);
  const coinSpace = Array.from({length: 8}, (_, i) => [0, 1, 2].map(bit => i & (1 << bit) ? 'H' : 'T'));
  const cardSpace = deck.flatMap((a, i) => deck.flatMap((b, j) => i === j ? [] : [[a, b]]));
  for (const [events, space] of [[diceEvents, diceSpace], [coinEvents, coinSpace], [cardEvents, cardSpace]]) {
    for (const event of events) event.probability = space.filter(event.test).length / space.length;
  }
  // Every unordered three-card hand is equally likely; cache its sum distribution.
  const cardSums = new Map();
  for (let i = 0; i < 50; i++) for (let j = i + 1; j < 51; j++) for (let k = j + 1; k < 52; k++) {
    const value = deck[i].value + deck[j].value + deck[k].value;
    cardSums.set(value, (cardSums.get(value) || 0) + 1);
  }
  const shuffled = (items, random = Math.random) => {
    const result = [...items];
    for (let i = result.length - 1; i > 0; i--) {
      const j = Math.floor(random() * (i + 1));
      [result[i], result[j]] = [result[j], result[i]];
    }
    return result;
  };
  function makeEvents(random = Math.random) {
    const events = [[diceEvents, 5], [coinEvents, 5], [cardEvents, 4]].flatMap(([pool, count]) =>
      shuffled(pool, random).slice(0, count).map(event => ({...event,
        profitHundredths: Math.floor((1 / event.probability - 1) * (0.75 + random() * 0.23) * 100)})));
    const midpoint = 22 + Math.floor(random() * 6);
    for (const direction of ['below', 'above']) {
      const threshold = midpoint + (direction === 'below' ? -1 : 1);
      const compare = value => direction === 'below' ? value < threshold : value > threshold;
      events.push({id: `sum-${direction}`, group: 'sum', text: `Sum ${direction} ${threshold}`,
        probability: [...cardSums].reduce((n, [value, count]) => n + (compare(value) ? count : 0), 0) / 22100,
        profitHundredths: 100, test: cards => compare(sum(cards.map(c => c.value)))});
    }
    return events;
  }
  function parseWager(value) {
    const text = String(value).trim();
    if (text === '') return 0;
    if (!/^(?:\d+(?:\.\d{0,2})?|\.\d{1,2})$/.test(text)) return null;
    const [whole, fraction = ''] = text.split('.');
    const cents = Number(whole || 0) * 100 + Number(fraction.padEnd(2, '0'));
    return Number.isSafeInteger(cents) ? cents : null;
  }
  function settle(bankroll, events, wagers, outcome) {
    if (!Number.isSafeInteger(bankroll) || bankroll < 0) throw new Error('Invalid credit balance.');
    const bets = events.map(event => Object.hasOwn(wagers, event.id) ? wagers[event.id] : 0);
    if (bets.some(bet => !Number.isSafeInteger(bet) || bet < 0)) throw new Error('Use nonnegative wagers with at most two decimal places.');
    if (events.some(event => !Number.isSafeInteger(event.profitHundredths) || event.profitHundredths < 0)) throw new Error('Invalid payout multiplier.');
    const total = sum(bets);
    if (!Number.isSafeInteger(total) || total > bankroll) throw new Error('Total wagers exceed your available credits.');
    if (total === 0) throw new Error('Enter at least one wager to play.');
    let returned = 0n;
    const results = events.map((event, i) => {
      const cards = event.group === 'card' ? outcome.cards.slice(0, 2) : outcome.cards;
      const won = Boolean(event.test(event.group === 'dice' ? outcome.dice : event.group === 'coin' ? outcome.coins : cards));
      // Exact cent rounding also holds near JavaScript's safe-integer limit.
      const profit = (BigInt(bets[i]) * BigInt(event.profitHundredths) + 50n) / 100n;
      const payout = won ? BigInt(bets[i]) + profit : 0n;
      returned += payout;
      return {id: event.id, wager: bets[i], won, payout: Number(payout)};
    });
    const balance = BigInt(bankroll) - BigInt(total) + returned;
    if (balance > BigInt(Number.MAX_SAFE_INTEGER)) throw new Error('This wager would exceed the supported credit limit.');
    return {balance: Number(balance), change: Number(returned - BigInt(total)), total, results};
  }
  root.ParlayEngine = {createDeck, diceEvents, coinEvents, cardEvents, makeEvents, shuffled, parseWager, settle};
  if (typeof document === 'undefined') return;

  const byId = id => document.getElementById(id);
  const format = cents => (cents / 100).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
  const storageKey = 'type-null.parlay.records.v1';
  let state = null;
  const inputNodes = () => [...document.querySelectorAll('.bet-input')];
  const message = text => { byId('round-message').textContent = text; };
  function readWagers() {
    const wagers = {};
    let invalid = false;
    for (const input of inputNodes()) {
      const amount = parseWager(input.value);
      input.setAttribute('aria-invalid', String(amount === null));
      invalid ||= amount === null;
      wagers[input.dataset.event] = amount;
    }
    return {wagers, invalid, total: invalid ? null : sum(Object.values(wagers))};
  }
  function updateStats() {
    byId('round-number').textContent = state.round;
    byId('bankroll').textContent = format(state.balance);
    byId('peak').textContent = format(state.peak);
    const {total} = readWagers();
    byId('total-bet').textContent = total === null ? 'Check wagers' : format(total);
  }
  function renderChart() {
    const values = state.history;
    const max = Math.max(...values, 1);
    const points = values.map((value, index) => `${40 + index * 545 / Math.max(1, values.length - 1)},${140 - value / max * 115}`);
    byId('bankroll-chart').innerHTML = `<path d="M40 15V140H585" fill="none" stroke="#dce4e9"/><polyline points="${points.join(' ')}" fill="none" stroke="#00899f" stroke-width="3" stroke-linejoin="round"/><circle cx="${points.at(-1).split(',')[0]}" cy="${points.at(-1).split(',')[1]}" r="4" fill="#7254ad"/><text x="40" y="162" fill="#647180" font-size="12">Start</text><text x="585" y="162" text-anchor="end" fill="#647180" font-size="12">Round ${values.length - 1}</text><text x="40" y="13" fill="#647180" font-size="12">${format(max)} credits</text>`;
    byId('bankroll-chart').setAttribute('aria-label', `Credit history: started at ${format(values[0])}; now ${format(values.at(-1))} after ${values.length - 1} rounds. Full balances follow.`);
    byId('balance-history').replaceChildren(...values.map((value, i) => {
      const item = document.createElement('li'); item.textContent = `${i === 0 ? 'Start' : `Round ${i}`}: ${format(value)}`; return item;
    }));
  }
  function startRound() {
    state.events = makeEvents(); state.played = false;
    for (const group of ['dice', 'coin', 'card', 'sum']) byId(`${group}-betting-table`).replaceChildren();
    for (const event of state.events) {
      const row = document.createElement('tr'); row.id = `row-${event.id}`;
      const label = document.createElement('td');
      label.innerHTML = `<label for="bet-${event.id}">${event.text}</label><small>${(event.probability * 100).toFixed(1)}% chance</small><span class="result-marker"></span>`;
      const payout = document.createElement('td'); payout.className = 'payout'; payout.textContent = `×${(event.profitHundredths / 100).toFixed(2)}`;
      const cell = document.createElement('td');
      const input = document.createElement('input'); input.id = `bet-${event.id}`; input.className = 'bet-input'; input.dataset.event = event.id;
      // Text plus decimal input mode preserves invalid text for explicit validation.
      input.type = 'text'; input.inputMode = 'decimal'; input.placeholder = '0.00'; input.autocomplete = 'off'; input.maxLength = 16;
      input.setAttribute('aria-label', `Wager on ${event.text}`);
      input.addEventListener('input', () => {updateStats(); const read = readWagers(); message(read.invalid ? 'Use nonnegative numbers with at most two decimal places.' : read.total > state.balance ? 'Total wagers exceed your available credits.' : '');});
      cell.append(input); row.append(label, payout, cell); byId(`${event.group}-betting-table`).append(row);
    }
    byId('play-button').hidden = false; byId('next-round-button').hidden = true; byId('clear-button').disabled = false;
    byId('results-display').innerHTML = '<p class="muted">Place a wager to reveal this round.</p>';
    message(''); updateStats(); renderChart();
  }
  function reveal(outcome) {
    const display = byId('results-display'); display.replaceChildren();
    const sections = [
      ['Dice', outcome.dice, '', `Sum ${sum(outcome.dice)}`],
      ['Coins', outcome.coins, 'coin', `${outcome.coins.filter(x => x === 'H').length} heads`],
      ['Cards', outcome.cards.map(card => `${card.rank}${card.suit}`), 'card', `Sum ${sum(outcome.cards.map(c => c.value))} · First-two product ${product(outcome.cards)}`]
    ];
    for (const [name, values, kind, caption] of sections) {
      const label = document.createElement('p'); label.className = 'muted'; label.textContent = `${name} · ${caption}`;
      const row = document.createElement('div'); row.className = 'result-pieces';
      for (const value of values) {const piece = document.createElement('span'); piece.className = `piece ${kind}${/[♥♦]/.test(String(value)) ? ' red' : ''}`; piece.textContent = value; row.append(piece);}
      display.append(label, row);
    }
  }
  function finish() {
    if (!state || state.finished) return;
    state.finished = true; inputNodes().forEach(input => {input.disabled = true;});
    byId('play-button').hidden = true; byId('next-round-button').hidden = true; byId('clear-button').disabled = true; byId('finish-button').disabled = true;
    byId('session-end').hidden = false; byId('save-form').hidden = false; byId('save-message').textContent = '';
    byId('end-title').textContent = state.balance === 0 ? 'Out of credits' : 'Session complete';
    byId('end-message').textContent = `${state.history.length - 1} rounds played. Final balance: ${format(state.balance)} credits. Session peak: ${format(state.peak)}.`;
    byId('start-button').hidden = false; byId('start-button').textContent = 'Start a new session';
  }
  byId('start-button').addEventListener('click', () => {
    state = {balance: 100000, peak: 100000, round: 1, history: [100000], events: [], played: false, finished: false};
    byId('game').hidden = false; byId('session-end').hidden = true; byId('start-button').hidden = true; byId('finish-button').disabled = false;
    startRound(); byId('play-button').focus();
  });
  byId('play-button').addEventListener('click', () => {
    if (!state || state.played || state.finished) return;
    const {wagers, invalid} = readWagers();
    if (invalid) {message('Use nonnegative numbers with at most two decimal places.'); return;}
    const outcome = {dice: Array.from({length: 2}, () => Math.floor(Math.random() * 6) + 1), coins: Array.from({length: 3}, () => Math.random() < 0.5 ? 'H' : 'T'), cards: shuffled(createDeck()).slice(0, 3)};
    let result;
    try {result = settle(state.balance, state.events, wagers, outcome);} catch (error) {message(error.message); return;}
    state.balance = result.balance; state.peak = Math.max(state.peak, state.balance); state.history.push(state.balance); state.played = true;
    inputNodes().forEach(input => {input.disabled = true;});
    for (const record of result.results) if (record.wager > 0) {
      const row = byId(`row-${record.id}`); row.classList.add(record.won ? 'win' : 'loss');
      row.querySelector('.result-marker').textContent = record.won ? `Won · ${format(record.payout)} returned` : 'Lost';
    }
    reveal(outcome); updateStats(); renderChart();
    message(result.change > 0 ? `This round: +${format(result.change)} credits.` : result.change < 0 ? `This round: −${format(-result.change)} credits.` : 'This round: even.');
    byId('play-button').hidden = true; byId('next-round-button').hidden = false; byId('clear-button').disabled = true;
    if (state.balance === 0) finish(); else byId('next-round-button').focus();
  });
  byId('next-round-button').addEventListener('click', () => {if (state?.played && !state.finished) {state.round++; startRound(); byId('play-button').focus();}});
  byId('clear-button').addEventListener('click', () => {if (state && !state.played && !state.finished) {inputNodes().forEach(input => {input.value = '';}); updateStats(); message('');}});
  byId('finish-button').addEventListener('click', finish);
  function readRecords() {
    const parsed = JSON.parse(localStorage.getItem(storageKey) || '[]');
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(row => row && typeof row.name === 'string' && Number.isSafeInteger(row.peak) && row.peak >= 0 && Number.isInteger(row.rounds) && row.rounds >= 0 && typeof row.date === 'string').sort((a, b) => b.peak - a.peak).slice(0, 10);
  }
  byId('save-form').addEventListener('submit', event => {
    event.preventDefault();
    const name = byId('player-name').value.trim().slice(0, 24);
    if (!state?.finished || !name) {byId('save-message').textContent = 'Enter a name to save this record.'; return;}
    try {
      let records; try {records = readRecords();} catch (error) {if (!(error instanceof SyntaxError)) throw error; records = [];}
      records.push({name, peak: state.peak, rounds: state.history.length - 1, date: new Date().toISOString().slice(0, 10)});
      localStorage.setItem(storageKey, JSON.stringify(records.sort((a, b) => b.peak - a.peak).slice(0, 10)));
      byId('save-message').textContent = 'Saved on this browser. Local records keep the 10 highest session peaks.'; byId('save-form').hidden = true;
    } catch {byId('save-message').textContent = 'This browser has blocked local storage. You can keep playing, but this record could not be saved.';}
  });
  byId('leaderboard-button').addEventListener('click', () => {
    const content = byId('leaderboard-content'); content.replaceChildren();
    try {
      const records = readRecords();
      if (!records.length) content.textContent = 'No saved sessions yet.';
      else {const list = document.createElement('ol'); list.className = 'score-list'; records.forEach(record => {const item = document.createElement('li'); const title = document.createElement('strong'); title.textContent = `${record.name} · ${format(record.peak)} credits`; const note = document.createElement('small'); note.textContent = `${record.rounds} rounds · ${record.date}`; item.append(title, note); list.append(item);}); content.append(list);}
    } catch {content.textContent = 'Saved records are unavailable or unreadable in this browser. Playing still works.';}
    byId('leaderboard-dialog').showModal();
  });
  byId('close-leaderboard').addEventListener('click', () => byId('leaderboard-dialog').close());
})(typeof window === 'undefined' ? globalThis : window);

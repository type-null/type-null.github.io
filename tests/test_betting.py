"""Browser regressions for the standalone probability game.

Run with a Python environment containing Playwright and its Chromium browser:
    python -m unittest discover -s tests -p test_betting.py -v
Set PLAYWRIGHT_CHROMIUM_EXECUTABLE to use an existing Chromium binary.
"""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from itertools import permutations
from pathlib import Path
import os
import threading
import unittest

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


class BettingStaticTests(unittest.TestCase):
    def test_no_remote_runtime_or_embedded_credentials(self):
        page = (ROOT / 'sports/2025/betting_game.html').read_text()
        script = (ROOT / 'assets/js/tools/betting.js').read_text()
        self.assertNotIn('https://', page)
        for removed in ('firebase', 'apiKey', 'new Chart(', 'fetch('):
            self.assertNotIn(removed, script)
        self.assertIn('Local records', page)


@unittest.skipUnless(sync_playwright, 'Install Playwright to run browser regressions')
class BettingBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(ROOT)))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f'http://127.0.0.1:{cls.server.server_port}/sports/2025/betting_game.html'
        cls.playwright = sync_playwright().start()
        kwargs = {'headless': True}
        if os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE'):
            kwargs['executable_path'] = os.environ['PLAYWRIGHT_CHROMIUM_EXECUTABLE']
        cls.browser = cls.playwright.chromium.launch(**kwargs)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def setUp(self):
        self.context = self.browser.new_context(viewport={'width': 1280, 'height': 1000})
        self.page = self.context.new_page()
        self.errors, self.remote_requests = [], []
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))
        self.page.on('request', lambda request: self.remote_requests.append(request.url)
                     if not request.url.startswith(self.url.split('/sports')[0]) else None)
        self.page.goto(self.url)
        self.page.locator('#start-button').click()

    def tearDown(self):
        self.context.close()
        self.assertEqual(self.errors, [], 'JavaScript errors')
        self.assertEqual(self.remote_requests, [], 'Unexpected network dependencies')

    def test_input_validation_and_round_lifecycle(self):
        wager = self.page.locator('.bet-input').first
        self.assertEqual(self.page.locator('.bet-input').count(), 16)
        for invalid in ('-5', '1e3', '1.234', 'Infinity'):
            wager.fill(invalid)
            self.page.locator('#play-button').click()
            self.assertEqual(wager.input_value(), invalid)
            self.assertEqual(wager.get_attribute('aria-invalid'), 'true')
            self.assertEqual(self.page.locator('#bankroll').inner_text(), '1,000.00')
            self.assertEqual(self.page.locator('#balance-history li').count(), 1)
        wager.fill('1000.01')
        self.page.locator('#play-button').click()
        self.assertIn('exceed', self.page.locator('#round-message').inner_text())
        wager.fill('1.50')
        self.assertEqual(self.page.locator('#total-bet').inner_text(), '1.50')
        self.page.locator('#play-button').click()
        self.assertEqual(self.page.locator('#balance-history li').count(), 2)
        self.assertEqual(self.page.locator('#results-display .piece').count(), 8)
        self.assertTrue(wager.is_disabled())
        self.page.locator('#next-round-button').click()
        self.assertEqual(self.page.locator('#round-number').inner_text(), '2')
        self.assertEqual(self.page.locator('#total-bet').inner_text(), '0.00')
        self.assertTrue(self.page.locator('.bet-input').first.is_enabled())

    def test_decimal_bankroll_and_rejected_settlements(self):
        result = self.page.evaluate("""() => {
          const e = ParlayEngine;
          const events = [{id:'win',group:'dice',profitHundredths:50,test:()=>true},
                          {id:'lose',group:'coin',profitHundredths:100,test:()=>false}];
          const outcome = {dice:[1,1],coins:['H','T','T'],cards:e.createDeck().slice(0,3)};
          const result = e.settle(101,events,{win:1,lose:100},outcome);
          const rejected = [-1,NaN,Infinity,1.1,null,102,0].map(value => {
            try { e.settle(101,events,{win:value},outcome); return false; }
            catch { return true; }
          });
          const large=e.settle(600479950316060,[{id:'large',group:'dice',profitHundredths:1373,test:()=>true}],{large:600479950316060},outcome);
          return {large:large.balance,remainder:result.balance,zero:e.settle(result.balance,events,{lose:2},outcome).balance,
                  rejected,parsed:['1.5','.50','0.01','0.29','-5','1e3','1.234'].map(e.parseWager)};
        }""")
        self.assertEqual(result['remainder'], 2)
        self.assertEqual(result['zero'], 0)
        self.assertEqual(result['large'], 8845069668155564)
        self.assertTrue(all(result['rejected']))
        self.assertEqual(result['parsed'], [150, 50, 1, 29, None, None, None])

    def test_exact_probabilities_and_face_card_definition(self):
        actual = self.page.evaluate("""() => ({
          dice:ParlayEngine.diceEvents.map(x=>x.probability),
          coins:ParlayEngine.coinEvents.map(x=>x.probability),
          cards:ParlayEngine.cardEvents.map(x=>x.probability),
          tenIsFace:ParlayEngine.cardEvents.find(x=>x.text==='Both face cards').test([{rank:'10',value:10},{rank:'J',value:10}])
        })""")
        self.assertEqual(actual['dice'], [n / 36 for n in (3, 3, 4, 4, 3, 16, 3, 18, 18, 1, 6)])
        self.assertEqual(actual['coins'], [n / 8 for n in (2, 4, 1, 1, 3, 3, 7, 7, 4)])
        deck = [(rank, min(rank, 10) if rank != 14 else 11) for _ in range(4) for rank in range(2, 15)]
        pairs = list(permutations(deck, 2))
        predicates = [lambda a,b:a*b>100, lambda a,b:a*b%2==0, lambda a,b:a*b<20,
                      lambda a,b:a*b>75, lambda a,b:40<=a*b<=60,
                      lambda a,b:int((a*b)**.5)**2==a*b, lambda a,b:a*b%10==0]
        expected = [sum(predicate(a[1], b[1]) for a,b in pairs)/2652 for predicate in predicates]
        expected += [12*11/2652, sum(a[1]==b[1] for a,b in pairs)/2652]
        for measured, probability in zip(actual['cards'], expected):
            self.assertAlmostEqual(measured, probability, places=12)
        self.assertFalse(actual['tenIsFace'])

    def test_local_scores_escape_names_and_recover_corrupt_data(self):
        self.page.evaluate("localStorage.setItem('type-null.parlay.records.v1', '{bad json')")
        self.page.locator('#leaderboard-button').click()
        self.assertIn('unreadable', self.page.locator('#leaderboard-content').inner_text())
        self.page.locator('#close-leaderboard').click()
        self.page.locator('#finish-button').click()
        self.page.locator('#player-name').fill('<b>Alice</b>')
        self.page.locator('#save-score').click()
        self.assertIn('Saved on this browser', self.page.locator('#save-message').inner_text())
        self.page.locator('#leaderboard-button').click()
        self.assertIn('<b>Alice</b>', self.page.locator('#leaderboard-content').inner_text())
        self.assertEqual(self.page.locator('#leaderboard-content b').count(), 0)
        self.page.keyboard.press('Escape')
        self.assertFalse(self.page.locator('#leaderboard-dialog').is_visible())

    def test_storage_failure_does_not_break_play(self):
        self.page.evaluate("() => { Storage.prototype.setItem = () => { throw new Error('Storage blocked') }; }")
        self.page.locator('#finish-button').click()
        self.page.locator('#player-name').fill('Offline')
        self.page.locator('#save-score').click()
        self.assertIn('blocked local storage', self.page.locator('#save-message').inner_text())
        self.page.locator('#start-button').click()
        self.page.locator('.bet-input').first.fill('0.01')
        self.page.locator('#play-button').click()
        self.assertEqual(self.page.locator('#balance-history li').count(), 2)

    def test_mobile_has_no_horizontal_overflow(self):
        for width in (320, 390, 768, 1280):
            self.page.set_viewport_size({'width': width, 'height': 900})
            self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'), width,
                                 f'Horizontal overflow at {width}px')


if __name__ == '__main__':
    unittest.main()

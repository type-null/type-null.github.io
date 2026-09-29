"""Browser checks for the prize calculator and Trading Suits playbook."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
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


@unittest.skipUnless(sync_playwright, 'Install Playwright to run browser regressions')
class ToolBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(ROOT)))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f'http://127.0.0.1:{cls.server.server_port}'
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
        self.context = self.browser.new_context(viewport={'width': 1100, 'height': 900})
        self.page = self.context.new_page()
        self.errors, self.remote_requests = [], []
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))
        self.page.on('request', lambda request: self.remote_requests.append(request.url)
                     if not request.url.startswith(self.url) else None)

    def tearDown(self):
        self.context.close()
        self.assertEqual(self.errors, [])
        self.assertEqual(self.remote_requests, [])

    def test_prize_controls_validation_and_boundary_cases(self):
        self.page.goto(self.url + '/card/toolkit.html')
        self.assertEqual(self.page.locator('#atLeastOne').inner_text(), '99.15%')
        self.assertEqual(self.page.locator('#distribution tr').count(), 3)
        self.page.get_by_role('button', name='Add one copy', exact=True).click()
        self.assertEqual(self.page.locator('#copies').input_value(), '3')
        self.page.locator('#copies').fill('0')
        self.assertEqual(self.page.locator('#atLeastOne').inner_text(), '0.00%')
        self.assertEqual(self.page.locator('#distribution tr').count(), 1)
        self.page.locator('#reset-prizes').click()
        self.page.locator('#prizeCards').fill('60')
        self.assertEqual(self.page.locator('#atLeastOne').inner_text(), '0.00%')
        self.page.locator('#prizeCards').fill('0')
        self.assertEqual(self.page.locator('#atLeastOne').inner_text(), '100.00%')
        for invalid in ('-1', '1.5', '501', ''):
            self.page.locator('#deckSize').fill(invalid)
            self.assertEqual(self.page.locator('#atLeastOne').inner_text(), '—')
            self.assertTrue(self.page.locator('#prize-error').inner_text())
        self.page.locator('#reset-prizes').click()
        self.assertEqual(self.page.locator('#atLeastOne').inner_text(), '99.15%')

    def test_trading_model_controls_and_navigation(self):
        self.page.goto(self.url + '/sports/2025/trading_suits.html')
        self.assertTrue(self.page.locator('#calculate-btn').is_disabled())
        self.page.locator('#example-hand').click()
        self.assertIn('Clubs', self.page.locator('#assessor-interpretation').inner_text())
        self.assertIn('52.3%', self.page.locator('#assessor-interpretation').inner_text())
        self.page.locator('#spades').fill('-1')
        self.page.locator('#clubs').fill('9')
        self.assertEqual(self.page.locator('#total-cards').inner_text(), '10')
        self.assertTrue(self.page.locator('#calculate-btn').is_disabled())
        self.page.locator('#spades').fill('1.5')
        self.assertTrue(self.page.locator('#calculate-btn').is_disabled())
        self.page.locator('#example-hand').click()
        self.page.get_by_role('button', name='Player styles', exact=True).click()
        self.assertTrue(self.page.locator('#market').is_visible())
        self.assertFalse(self.page.locator('#assessor').is_visible())
        self.page.get_by_role('button', name='The Calculator', exact=False).click()
        self.assertIn('Uses consistent rules', self.page.locator('#archetype-display').inner_text())
        self.page.get_by_role('button', name='Round budget', exact=True).click()
        self.page.locator('#bankroll').fill('5000')
        self.page.get_by_label('High', exact=True).check()
        self.assertEqual(self.page.locator('#budget-recommendation').inner_text(), '250–400 credits')

    def test_mobile_layout(self):
        for path in ('/card/toolkit.html', '/sports/2025/trading_suits.html'):
            self.page.goto(self.url + path)
            for width in (320, 390, 768, 1280):
                self.page.set_viewport_size({'width': width, 'height': 900})
                self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'), width,
                                     f'{path}: overflow at {width}px')


if __name__ == '__main__':
    unittest.main()

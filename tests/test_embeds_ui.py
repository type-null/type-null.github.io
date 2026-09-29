"""Exercise real front-matter media in a browser, using tiny local fixtures only."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import math
import os
from pathlib import Path
import shutil
import sys
import tempfile
import threading
import unittest

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build import discover


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass


@unittest.skipUnless(sync_playwright, 'Install requirements-dev.txt for browser checks')
class EmbedBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        root = Path(cls.temporary.name)
        for filename in ('sample.webm', 'sample.pdf'):
            shutil.copy2(ROOT / 'tests/fixtures' / filename, root / filename)
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(root)))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f'http://127.0.0.1:{cls.server.server_port}'
        (root / 'tool.html').write_text('''<!doctype html><title>Local tool fixture</title>
<button onclick="localStorage.setItem('embed-test', 'saved'); this.textContent='Saved locally'">Save</button>''')
        (root / 'external.html').write_text('''<!doctype html><title>External website fixture</title><p id="status">Script did not run</p><script>
try { localStorage.setItem('external-test', 'leak'); document.querySelector('#status').textContent='Unexpected storage access'; }
catch { document.querySelector('#status').textContent='Scripts work; storage isolated'; }
</script>''')
        source = root / 'content/notes/media/index.md'
        source.parent.mkdir(parents=True)
        source.write_text(f'''---
title: Real media check
date: 2026-09-29
embeds:
  - type: video
    url: /sample.webm
    title: Synthetic animation
  - type: pdf
    url: /sample.pdf
    title: Sample document
  - type: website
    url: /tool.html
    title: First-party tool
  - type: website
    url: {cls.url}/external.html
    title: External website
---
A post with real, local fixtures.
''')
        _, posts = discover(root)
        (root / 'index.html').write_text('<!doctype html><title>Embed test</title><style>figure{margin:12px}video{width:320px}iframe{width:420px;height:160px}</style>' + str(posts[0]['html']) + str(posts[0]['embeds_html']))
        cls.runtime = sync_playwright().start()
        kwargs = {'headless': True}
        if os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE'):
            kwargs['executable_path'] = os.environ['PLAYWRIGHT_CHROMIUM_EXECUTABLE']
        cls.browser = cls.runtime.chromium.launch(**kwargs)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.runtime.stop()
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
        cls.temporary.cleanup()

    def setUp(self):
        self.context = self.browser.new_context(viewport={'width': 900, 'height': 1100})
        self.page = self.context.new_page()
        self.errors = []
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))
        self.page.goto(self.url, wait_until='domcontentloaded')

    def tearDown(self):
        self.context.close()
        self.assertEqual(self.errors, [])

    def test_real_video_decodes_plays_and_pdf_frame_loads_document(self):
        self.page.wait_for_function('document.querySelector("video").readyState >= 2')
        metadata = self.page.locator('video').evaluate('(video) => ({duration: video.duration, width: video.videoWidth, height: video.videoHeight})')
        self.assertTrue(math.isfinite(metadata['duration']))
        self.assertGreater(metadata['duration'], 0)
        self.assertEqual((metadata['width'], metadata['height']), (160, 90))
        self.page.locator('video').evaluate('(video) => video.play()')
        self.page.wait_for_function('document.querySelector("video").currentTime > 0.15')
        decoded = self.page.locator('video').evaluate('''video => {
          video.pause(); const canvas = document.createElement('canvas'); canvas.width=160; canvas.height=90;
          const context = canvas.getContext('2d'); context.drawImage(video, 0, 0);
          return {paused:video.paused, time:video.currentTime, pixel:Array.from(context.getImageData(150, 10, 1, 1).data)};
        }''')
        self.assertTrue(decoded['paused'])
        self.assertGreater(decoded['time'], 0.15)
        self.assertGreaterEqual(decoded['pixel'][3], 250)
        self.assertGreater(max(decoded['pixel'][:3]), 100)
        pdf_frame = self.page.locator('iframe[title="Sample document"]')
        pdf_frame.scroll_into_view_if_needed()
        self.assertEqual(pdf_frame.get_attribute('src'), '/sample.pdf')
        # Native PDF viewer internals vary in headless browsers; verify its actual
        # document navigation and the independent, accessible download fallback.
        # Changing the query forces a fresh navigation even if the lazy iframe
        # already loaded, or Chromium's PDF viewer retained the first response.
        pdf_url = self.url + '/sample.pdf?embed-navigation-check=1'
        with self.page.expect_response(
            lambda response: response.url == pdf_url
            and response.request.is_navigation_request()
        ) as response:
            pdf_frame.evaluate('(frame, url) => { frame.loading="eager"; frame.src=url; }', pdf_url)
        self.assertEqual(response.value.status, 200)
        self.assertIn('application/pdf', response.value.headers['content-type'])
        fallback = self.page.get_by_role('link', name='Sample document', exact=False)
        document = self.context.request.get(self.url + fallback.get_attribute('href'))
        self.assertEqual(document.status, 200)
        self.assertIn('application/pdf', document.headers['content-type'])
        self.assertEqual(document.body(), (ROOT / 'tests/fixtures/sample.pdf').read_bytes())
        self.assertTrue(document.body().startswith(b'%PDF-1.4'))
        self.assertTrue(document.body().rstrip().endswith(b'%%EOF'))

    def test_first_party_storage_and_external_website_sandbox(self):
        local = self.page.locator('iframe[title="First-party tool"]')
        local.scroll_into_view_if_needed()
        self.assertIsNone(local.get_attribute('sandbox'))
        frame = self.page.frame_locator('iframe[title="First-party tool"]')
        frame.get_by_role('button', name='Save', exact=True).click()
        self.assertEqual(frame.get_by_role('button').inner_text(), 'Saved locally')
        self.assertEqual(self.page.evaluate('localStorage.getItem("embed-test")'), 'saved')
        external = self.page.locator('iframe[title="External website"]')
        external.scroll_into_view_if_needed()
        self.assertEqual(external.get_attribute('sandbox'), 'allow-scripts allow-forms allow-popups')
        external_frame = self.page.frame_locator('iframe[title="External website"]')
        self.assertEqual(external_frame.locator('#status').inner_text(), 'Scripts work; storage isolated')
        self.assertIsNone(self.page.evaluate('localStorage.getItem("external-test")'))


if __name__ == '__main__':
    unittest.main()

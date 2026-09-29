"""True file:// regressions for the built site; no HTTP server or browser bypasses.

Build first, then run:
  PLAYWRIGHT_CHROMIUM_EXECUTABLE='/path/to/chrome' python -m unittest discover -s tests -p test_file_ui.py -v
The executable override is optional when Playwright's Chromium is installed.
"""
from pathlib import Path
from urllib.parse import unquote, urlsplit
import json
import math
import os
import shutil
import sys
import tempfile
import unittest

try:
    from playwright.sync_api import sync_playwright, expect
except ImportError:
    sync_playwright = None

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = Path(tempfile.gettempdir()) / 'type-null-file-final'


def file_path(url):
    parsed = urlsplit(url)
    if parsed.scheme != 'file':
        raise AssertionError(f'Expected a file URL, got {url}')
    return Path(unquote(parsed.path)).resolve()


def route_file(base, route):
    path = base / urlsplit(route).path.lstrip('/')
    return path / 'index.html' if route.endswith('/') else path


@unittest.skipUnless(sync_playwright, 'Install requirements-dev.txt for browser checks')
class FileBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.built = ROOT / '_site'
        if not (cls.built / 'index.html').is_file():
            raise RuntimeError('Run python scripts/build.py --check before file browser tests')
        cls.posts = json.loads((cls.built / 'search-index.json').read_text())
        cls.sets = json.loads((ROOT / 'content/_data/card-sets.json').read_text())['sets']
        cls.temporary = tempfile.TemporaryDirectory(prefix='type-null-file-')
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.moved = (Path(cls.temporary.name) / 'Folder with spaces 中文' / 'portable site').resolve()
        shutil.copytree(cls.built, cls.moved)
        cls.bases = (cls.built, cls.moved)
        # Exercise the real Markdown -> embed renderer -> portable-path pass
        # using 9 KB of valid media, without another full-site copy.
        sys.path.insert(0, str(ROOT / 'scripts'))
        from build import discover, copy_post_media
        from portable import make_portable
        fixture = (Path(cls.temporary.name) / 'Media authoring fixture 文档').resolve()
        source = fixture / 'content/notes/media/index.md'
        source.parent.mkdir(parents=True)
        shutil.copy2(ROOT / 'tests/fixtures/sample.webm', source.parent / 'demo animation.webm')
        shutil.copy2(ROOT / 'tests/fixtures/sample.pdf', source.parent / 'sample notes.pdf')
        source.write_text('''---
title: Local media fixture
date: 2026-09-29
embeds:
  - type: video
    url: demo animation.webm
    title: Synthetic animation
  - type: pdf
    url: sample notes.pdf
    title: Sample document
---
Video and PDF produced from actual post metadata.
''')
        _, media_posts = discover(fixture)
        post = media_posts[0]
        cls.media_base = fixture / 'published files'
        copy_post_media(post, cls.media_base)
        cls.media_page = cls.media_base / 'notes/media/index.html'
        cls.media_page.write_text('<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Local media fixture</title>'
                                 '<style>body{font:16px sans-serif;margin:24px}figure{margin:16px 0}video{width:320px}iframe{width:480px;height:240px}</style>'
                                 '</head><body><h1>Local media fixture</h1>' + str(post['html']) + str(post['embeds_html']) + '</body></html>')
        make_portable(cls.media_base)
        cls.runtime = sync_playwright().start()
        cls.addClassCleanup(cls.runtime.stop)
        kwargs = {'headless': True}
        if os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE'):
            kwargs['executable_path'] = os.environ['PLAYWRIGHT_CHROMIUM_EXECUTABLE']
        cls.browser = cls.runtime.chromium.launch(**kwargs)
        cls.addClassCleanup(cls.browser.close)
        ARTIFACTS.mkdir(parents=True, exist_ok=True)

    def setUp(self):
        self.errors, self.failed, self.remote, self.console_errors, self.requests, self.outside = [], [], [], [], [], []
        self.active_base = ROOT
        self.contexts = []
        self.context = self.new_context()
        self.page = self.context.new_page()

    def new_context(self, **kwargs):
        context = self.browser.new_context(**{'viewport': {'width': 1440, 'height': 1000}, **kwargs})
        context.set_default_timeout(10000)
        self.contexts.append(context)
        # Observe actual loads, and prevent accidental internet access during tests.
        def block_network(route):
            route.abort()
        context.route('http://**/*', block_network)
        context.route('https://**/*', block_network)
        def request_seen(request):
            self.requests.append(request.url)
            if urlsplit(request.url).scheme in ('http', 'https', 'ws', 'wss'):
                self.remote.append(request.url)
            if urlsplit(request.url).scheme == 'file' and not file_path(request.url).is_relative_to(self.active_base):
                self.outside.append({'url': request.url, 'expectedRoot': str(self.active_base)})
        context.on('request', request_seen)
        context.on('requestfailed', lambda request: self.failed.append({'url': request.url, 'failure': request.failure}))
        def watch_page(page):
            page.on('pageerror', lambda error: self.errors.append(str(error)))
            page.on('console', lambda message: self.console_errors.append(message.text) if message.type == 'error' else None)
        context.on('page', watch_page)
        return context

    def tearDown(self):
        report = {'test': self.id(), 'pageErrors': self.errors, 'failedRequests': self.failed,
                  'networkRequests': self.remote, 'consoleErrors': self.console_errors,
                  'requestsOutsidePackage': self.outside, 'requests': self.requests}
        (ARTIFACTS / f'{self._testMethodName}.json').write_text(json.dumps(report, indent=2, ensure_ascii=False))
        # Finish assertions before closing contexts so deliberate teardown cannot
        # be mistaken for an application resource failure.
        try:
            self.assertEqual(self.errors, [], 'JavaScript exception under file://')
            self.assertEqual(self.failed, [], 'Failed file resource')
            self.assertEqual(self.remote, [], 'Unexpected network dependency')
            self.assertEqual(self.outside, [], 'A relocated page reached outside its copied package')
            self.assertEqual(self.console_errors, [], 'Browser console error')
        finally:
            for context in self.contexts:
                context.close()

    def settle(self, page=None):
        page = page or self.page
        page.locator('img').evaluate_all('(images)=>images.forEach(image=>image.loading="eager")')
        page.wait_for_function('Array.from(document.images).every(image=>image.complete)')
        self.assertEqual(page.locator('img').evaluate_all('(images)=>images.filter(image=>!image.naturalWidth).map(image=>image.src)'), [])
        page.evaluate('() => document.fonts.ready.then(() => true)')

    def goto(self, path, page=None):
        page = page or self.page
        self.active_base = next((base for base in (*self.bases, self.media_base) if path.resolve().is_relative_to(base)), ROOT)
        page.goto(path.as_uri(), wait_until='load')
        self.settle(page)

    def assert_home(self, page=None):
        page = page or self.page
        cards = page.locator('.home-news .post-card')
        expect(cards).to_have_count(min(6, len(self.posts)))
        self.settle(page)
        self.assertEqual(cards.locator('.news-list__title').all_text_contents(), [post['title'] for post in self.posts[:6]])
        links = cards.locator('.post-card-link').evaluate_all('(links)=>links.map(link=>link.href)')
        for actual, post in zip(links, self.posts[:6]):
            actual_path = file_path(actual)
            self.assertTrue(actual_path.is_file(), actual)
            suffix = route_file(Path('/'), post['url']).as_posix()
            self.assertTrue(actual_path.as_posix().endswith(suffix), actual)
        self.assertGreater(page.locator('.site-header').bounding_box()['height'], 50)
        self.assertIn('Noto Sans JP', page.locator('body').evaluate('(element)=>getComputedStyle(element).fontFamily'))
        fonts = page.evaluate('() => [...document.fonts].filter(font=>font.status === "loaded").map(font=>font.family.replaceAll(/^[\'"]|[\'"]$/g,""))')
        self.assertIn('Noto Sans JP', fonts, 'Local Noto font must actually load; CSS family naming is insufficient')
        self.assertIn('Lato', fonts, 'The heading font must also load from local files')
        # The shipped Unicode subsets overlap. FontFaceSet.check can be false
        # for unloaded overlapping subsets even when the rendered Latin face
        # is already loaded. Explicitly request the sample before checking it.
        page.evaluate('() => document.fonts.load(\'16px "Noto Sans JP"\', "Type Null")')
        self.assertTrue(page.evaluate('document.fonts.check(\'16px "Noto Sans JP"\', "Type Null")'))

    def test_root_entry_opens_the_complete_homepage(self):
        self.page.goto((ROOT / 'index.html').as_uri(), wait_until='load')
        self.assert_home()
        self.page.screenshot(path=str(ARTIFACTS / 'root-home-file.png'), full_page=True)

    def test_built_and_relocated_home_have_six_newest_posts_and_local_assets(self):
        for base in self.bases:
            with self.subTest(base=base):
                self.goto(base / 'index.html')
                self.assert_home()
                expected = [route_file(base, post['url']).resolve() for post in self.posts[:6]]
                actual = [file_path(url) for url in self.page.locator('.home-news .post-card-link').evaluate_all('(links)=>links.map(link=>link.href)')]
                self.assertEqual(actual, expected)
                if base == self.built:
                    self.page.screenshot(path=str(ARTIFACTS / 'built-home-file.png'), full_page=True)
                self.page.get_by_role('link', name='More articles', exact=False).click()
                self.settle()
                self.assertEqual(file_path(self.page.url), base / 'posts/index.html')
                self.assertEqual(self.page.locator('.post-card').count(), len(self.posts))
                self.goto(base / '404.html')
                expect(self.page.locator('h1')).to_have_text('404 Not Found')
                self.assertGreater(self.page.locator('.site-header').bounding_box()['height'], 50)
                self.assertIn('Noto Sans JP', self.page.locator('body').evaluate('(element)=>getComputedStyle(element).fontFamily'))
                self.page.get_by_role('link', name='Back to TOP', exact=True).click()
                self.assertEqual(file_path(self.page.url), base / 'index.html')
                self.assert_home()

    def test_search_navigates_nested_files_and_returns_home_after_relocation(self):
        for base in self.bases:
            with self.subTest(base=base):
                self.goto(base / 'index.html')
                self.page.get_by_role('button', name='Search this site').click()
                field = self.page.get_by_role('searchbox', name='Search articles')
                field.fill('Keep the pictures with the story')
                result = self.page.locator('.search-result')
                expect(result).to_have_count(1)
                result.click()
                self.settle()
                self.assertEqual(file_path(self.page.url), base / 'notes/keeping-media-local/index.html')
                self.assertEqual(self.page.locator('h1').inner_text(), 'Keep the pictures with the story')
                self.page.get_by_role('button', name='Search this site').click()
                self.page.get_by_role('searchbox', name='Search articles').fill('Prize card odds')
                self.page.locator('.search-result').filter(has=self.page.get_by_text('Prize card odds', exact=True)).click()
                self.settle()
                self.assertEqual(file_path(self.page.url), base / 'card/prize-card-odds/index.html')
                # Finish the lazy child document before immediately navigating
                # away; otherwise our own rapid click cancels its valid assets.
                self.page.locator('iframe').scroll_into_view_if_needed()
                expect(self.page.frame_locator('iframe').locator('#distribution tr')).to_have_count(3)
                self.page.locator('.header__logo').click()
                self.settle()
                self.assertEqual(file_path(self.page.url), base / 'index.html')
                self.assert_home()

    def test_timeline_decodes_all_art_filters_and_opens_original_files(self):
        for base in self.bases:
            with self.subTest(base=base):
                self.goto(base / 'card/2024/02/timeline.html')
                self.assertEqual(self.page.locator('.set-art').count(), 186)
                self.assertEqual(self.page.locator('.set-art img').count(), len(self.sets))
                self.assertEqual(self.page.locator('.set-art img').evaluate_all('(images)=>images.filter(image=>image.naturalWidth>0).length'), 186)
                era = self.page.locator('.timeline-filters select[name="era"]')
                expect(era).to_be_visible()
                era.select_option('SV')
                expect(self.page.locator('.set-art:visible')).to_have_count(sum(item['era'] == 'SV' for item in self.sets))
                self.assertIn('era=SV', self.page.url)
                self.page.locator('.timeline-search input').fill('unmatched-archive-query-xyz')
                expect(self.page.locator('[data-timeline-empty]')).to_be_visible()
                self.page.locator('[data-reset-filters]').click()
                expect(self.page.locator('.set-art:visible')).to_have_count(len(self.sets))
                first = self.page.locator('.set-art').first
                identifier = first.get_attribute('data-set-id')
                record = next(item for item in self.sets if item['id'] == identifier)
                first.click()
                expect(self.page.locator('[data-set-dialog]')).to_be_visible()
                original = self.page.locator('[data-dialog-art] img')
                self.page.wait_for_function('document.querySelector("[data-dialog-art] img").naturalWidth > 0')
                self.assertEqual(file_path(original.get_attribute('src')), base / record['image'].lstrip('/'))
                with self.context.expect_page() as opened:
                    self.page.locator('[data-dialog-original]').click()
                popup = opened.value
                popup.wait_for_load_state()
                self.assertEqual(file_path(popup.url), base / record['image'].lstrip('/'))
                self.assertTrue(popup.locator('img').evaluate('(image)=>image.naturalWidth>0'))
                popup.close()
                self.page.get_by_role('button', name='Close set details').click()
                if base == self.built:
                    self.page.screenshot(path=str(ARTIFACTS / 'timeline-file.png'), full_page=False)

    def open_embed_popup(self, base, route, page=None):
        page = page or self.page
        parent_url = page.url
        button = page.locator('.embed-open')
        iframe_title = page.locator('.embed--website iframe').get_attribute('title')
        expect(button).to_have_attribute('aria-label', f'Open {iframe_title} in a new tab')
        expect(button).to_have_attribute('target', '_blank')
        self.assertTrue({'noopener', 'noreferrer'}.issubset(set(button.get_attribute('rel').split())))
        self.assertEqual(file_path(button.evaluate('(element)=>element.href')), route_file(base, route))
        self.assertTrue(page.locator('.embed--website').evaluate('(element)=>element.firstElementChild.matches("figcaption.embed-toolbar")'))
        for width in (320, 390):
            page.set_viewport_size({'width': width, 'height': 900})
            button.scroll_into_view_if_needed()
            expect(button).to_be_visible()
            expect(button).to_contain_text('Open in new tab')
            bounds = button.bounding_box()
            self.assertGreaterEqual(bounds['x'], 0)
            self.assertLessEqual(bounds['x'] + bounds['width'], width)
            self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth'), width)
        with page.context.expect_page() as opened:
            button.click()
        popup = opened.value
        popup.wait_for_load_state()
        self.settle(popup)
        self.assertEqual(file_path(popup.url), route_file(base, route))
        self.assertTrue(popup.evaluate('window.opener === null'))
        self.assertEqual(page.url, parent_url)
        return popup

    def test_local_tool_embeds_and_new_tabs_preserve_parent_state_in_all_locations(self):
        for base in (ROOT, *self.bases):
            with self.subTest(base=base):
                self.goto(base / 'card/prize-card-odds/index.html')
                self.page.locator('iframe').scroll_into_view_if_needed()
                frame = self.page.frame_locator('iframe')
                expect(frame.locator('#atLeastOne')).to_have_text('99.15%')
                frame.locator('#copies').fill('0')
                expect(frame.locator('#atLeastOne')).to_have_text('0.00%')
                popup = self.open_embed_popup(base, '/card/toolkit.html')
                expect(popup.locator('#distribution tr')).to_have_count(3)
                expect(popup.locator('#copies')).to_have_value('2')
                popup.locator('#copies').fill('1')
                expect(popup.locator('#atLeastOne')).to_have_text('90.00%')
                popup.close()
                expect(frame.locator('#copies')).to_have_value('0')
                expect(frame.locator('#atLeastOne')).to_have_text('0.00%')
                self.goto(base / 'sports/trading-suits/index.html')
                self.page.locator('iframe').scroll_into_view_if_needed()
                frame = self.page.frame_locator('iframe')
                frame.locator('#example-hand').click()
                expect(frame.locator('#assessor-interpretation')).to_contain_text('52.3%')
                frame.locator('#spades').fill('4')
                frame.locator('#clubs').fill('4')
                frame.locator('#calculate-btn').click()
                interpretation = frame.locator('#assessor-interpretation').inner_text()
                popup = self.open_embed_popup(base, '/sports/2025/trading_suits.html')
                popup.locator('#example-hand').click()
                expect(popup.locator('#assessor-interpretation')).to_contain_text('52.3%')
                popup.close()
                expect(frame.locator('#spades')).to_have_value('4')
                expect(frame.locator('#clubs')).to_have_value('4')
                expect(frame.locator('#assessor-interpretation')).to_have_text(interpretation)
                self.goto(base / 'sports/betting-game/index.html')
                self.page.locator('iframe').scroll_into_view_if_needed()
                frame = self.page.frame_locator('iframe')
                frame.locator('#start-button').click()
                expect(frame.locator('.bet-input')).to_have_count(16)
                frame.locator('.bet-input').first.fill('0.37')
                popup = self.open_embed_popup(base, '/sports/2025/betting_game.html')
                popup.locator('#start-button').click()
                expect(popup.locator('.bet-input')).to_have_count(16)
                popup.locator('.bet-input').first.fill('0.01')
                popup.locator('#play-button').click()
                expect(popup.locator('#balance-history li')).to_have_count(2)
                popup.close()
                expect(frame.locator('.bet-input').first).to_have_value('0.37')
                expect(frame.locator('#balance-history li')).to_have_count(1)
                expect(frame.locator('#bankroll')).to_have_text('1,000.00')
                frame.locator('#play-button').click()
                expect(frame.locator('#balance-history li')).to_have_count(2)

    def test_no_javascript_tool_links_still_open_local_new_tabs(self):
        page = self.new_context(java_script_enabled=False).new_page()
        tools = (
            ('/card/prize-card-odds/', '/card/toolkit.html'),
            ('/sports/trading-suits/', '/sports/2025/trading_suits.html'),
            ('/sports/betting-game/', '/sports/2025/betting_game.html'),
        )
        for base in (ROOT, *self.bases):
            for article, tool in tools:
                with self.subTest(base=base, tool=tool):
                    self.goto(route_file(base, article), page)
                    page.locator('iframe').scroll_into_view_if_needed()
                    # Wait for the complete static child before opening another
                    # document; no JavaScript functionality is claimed here.
                    expect(page.frame_locator('iframe').locator('h1')).to_be_visible()
                    popup = self.open_embed_popup(base, tool, page)
                    expect(popup.locator('h1')).to_be_visible()
                    popup.close()
                    self.assertEqual(file_path(page.url), route_file(base, article))

    def test_mobile_navigation_and_document_overflow_under_file_protocol(self):
        for base in self.bases:
            with self.subTest(base=base):
                self.goto(base / 'index.html')
                for width in (320, 390, 768, 1440):
                    self.page.set_viewport_size({'width': width, 'height': 900})
                    self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'), width)
                self.page.set_viewport_size({'width': 390, 'height': 900})
                navigation = self.page.get_by_role('navigation', name='Main navigation')
                expect(navigation).not_to_be_visible()
                self.page.get_by_label('Toggle navigation').click()
                expect(navigation).to_be_visible()
                navigation.locator('a[href$="card/index.html"]').click()
                self.settle()
                self.assertEqual(file_path(self.page.url), base / 'card/index.html')
                self.goto(base / 'card/2024/02/timeline.html')
                for width in (320, 390, 768):
                    self.page.set_viewport_size({'width': width, 'height': 900})
                    self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'), width)
                if base == self.built:
                    # A fresh mobile surface avoids Chromium compositor residue
                    # from repeatedly resizing a desktop page with fixed layers.
                    mobile = self.new_context(viewport={'width': 390, 'height': 900}).new_page()
                    self.goto(base / 'card/2024/02/timeline.html', mobile)
                    self.assertLessEqual(mobile.evaluate('document.documentElement.scrollWidth'), 390)
                    mobile.screenshot(path=str(ARTIFACTS / 'timeline-mobile-file.png'), full_page=False)

    def test_authored_video_decodes_plays_and_pdf_has_a_local_file_fallback(self):
        self.goto(self.media_page)
        self.page.wait_for_function('document.querySelector("video").readyState >= 2')
        video = self.page.locator('video')
        metadata = video.evaluate('(element)=>({duration:element.duration,width:element.videoWidth,height:element.videoHeight,source:element.currentSrc})')
        self.assertTrue(math.isfinite(metadata['duration']))
        self.assertGreater(metadata['duration'], 0)
        self.assertEqual((metadata['width'], metadata['height']), (160, 90))
        self.assertEqual(file_path(metadata['source']), self.media_page.parent / 'demo animation.webm')
        video.evaluate('(element)=>element.play()')
        self.page.wait_for_function('document.querySelector("video").currentTime > .15')
        video.evaluate('(element)=>element.pause()')
        self.assertGreater(video.evaluate('(element)=>element.currentTime'), .15)
        pdf_path = self.media_page.parent / 'sample notes.pdf'
        frame = self.page.locator('iframe[title="Sample document"]')
        frame.scroll_into_view_if_needed()
        self.assertEqual(file_path(frame.evaluate('(element)=>element.src')), pdf_path)
        # Native PDF viewer internals differ by browser. Verify that the actual
        # iframe requests the local PDF, and that its independent link targets
        # the complete fixture bytes; do not claim PDF rendering fidelity.
        with self.context.expect_event('request', predicate=lambda request: request.url.startswith('file:') and file_path(request.url) == pdf_path) as requested:
            frame.evaluate('(element,url)=>{element.loading="eager";element.src=url}', pdf_path.as_uri() + '?file-navigation-check=1')
        self.assertTrue(requested.value.is_navigation_request())
        fallback = self.page.get_by_role('link', name='Sample document', exact=False)
        self.assertEqual(file_path(fallback.evaluate('(element)=>element.href')), pdf_path)
        self.assertEqual(pdf_path.read_bytes(), (ROOT / 'tests/fixtures/sample.pdf').read_bytes())
        self.assertTrue(pdf_path.read_bytes().startswith(b'%PDF-1.4'))
        self.assertTrue(pdf_path.read_bytes().rstrip().endswith(b'%%EOF'))
        self.page.screenshot(path=str(ARTIFACTS / 'authored-media-file.png'), full_page=True)

    def test_no_javascript_preserves_file_navigation_and_all_186_images(self):
        context = self.new_context(java_script_enabled=False)
        page = context.new_page()
        page.goto((ROOT / 'index.html').as_uri(), wait_until='load')
        self.assert_home(page)
        for base in self.bases:
            with self.subTest(base=base):
                self.goto(base / 'index.html', page)
                self.assert_home(page)
                self.assertFalse(page.locator('[data-search-open]').is_visible())
                page.set_viewport_size({'width': 390, 'height': 900})
                navigation = page.get_by_role('navigation', name='Main navigation')
                expect(navigation).not_to_be_visible()
                page.get_by_label('Toggle navigation').click()
                expect(navigation).to_be_visible()
                navigation.locator('a[href$="card/index.html"]').click()
                self.settle(page)
                self.assertEqual(file_path(page.url), base / 'card/index.html')
                self.goto(base / 'card/2024/02/timeline.html', page)
                self.assertEqual(page.locator('.set-art img').count(), 186)
                self.assertEqual(page.locator('.set-art img').evaluate_all('(images)=>images.filter(image=>image.naturalWidth>0).length'), 186)
                link = page.locator('.set-art').first
                original = file_path(link.evaluate('(element)=>element.href'))
                link.click()
                page.wait_for_load_state()
                self.assertEqual(file_path(page.url), original)
                self.assertTrue(page.locator('img').evaluate('(image)=>image.naturalWidth>0'))
                self.goto(base / '404.html', page)
                self.assertIn('Noto Sans JP', page.locator('body').evaluate('(element)=>getComputedStyle(element).fontFamily'))
                page.get_by_role('link', name='Back to TOP', exact=True).click()
                self.assert_home(page)
                self.assertEqual(file_path(page.url), base / 'index.html')


if __name__ == '__main__':
    unittest.main()

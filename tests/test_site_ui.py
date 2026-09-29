"""Integration checks against the actual built site. Build before running."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import os
import threading
import unittest
from urllib.parse import urlsplit
try:
    from playwright.sync_api import sync_playwright, expect
except ImportError:
    sync_playwright = None

ROOT = Path(__file__).resolve().parents[1]


def emitted_path(route):
    path = urlsplit(route).path
    return path + 'index.html' if path.endswith('/') else path


def link_paths(scope):
    return scope.locator('a').evaluate_all('(links)=>links.map(link=>new URL(link.href).pathname)')


def link_to(scope, path):
    matches = [link for link in scope.locator('a').all() if link.evaluate('(link)=>new URL(link.href).pathname') == path]
    if len(matches) != 1:
        raise AssertionError(f'Expected one link to {path}, found {len(matches)}')
    return matches[0]


class QuietHandler(SimpleHTTPRequestHandler):
    def copyfile(self, source, outputfile):
        try:
            super().copyfile(source, outputfile)
        except (BrokenPipeError, ConnectionResetError):
            pass  # Closing a page can cancel a still-loading lazy image.

    def log_message(self, *_):
        pass

@unittest.skipUnless(sync_playwright, 'Install requirements-dev.txt for browser checks')
class SiteBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (ROOT / '_site/index.html').exists():
            raise RuntimeError('Run python scripts/build.py --check before browser tests')
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(ROOT / '_site')))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f'http://127.0.0.1:{cls.server.server_port}'
        cls.runtime = sync_playwright().start()
        kwargs = {'headless': True}
        if os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE'):
            kwargs['executable_path'] = os.environ['PLAYWRIGHT_CHROMIUM_EXECUTABLE']
        cls.browser = cls.runtime.chromium.launch(**kwargs)
        cls.posts = json.loads((ROOT / '_site/search-index.json').read_text())
        cls.sets = json.loads((ROOT / 'content/_data/card-sets.json').read_text())['sets']

    @classmethod
    def tearDownClass(cls):
        cls.browser.close(); cls.runtime.stop()
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join(timeout=5)

    def setUp(self):
        self.context = self.browser.new_context(viewport={'width': 1440, 'height': 1000})
        self.page = self.context.new_page()
        self.errors = []; self.failed = []; self.remote = []
        self.expected_http_errors = set()
        def local_only(route):
            if route.request.url.startswith(self.url + '/'):
                route.continue_()
            else:
                self.remote.append(route.request.url)
                route.abort()
        self.context.route('**/*', local_only)
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))
        self.page.on('response', lambda response: self.failed.append(response.url) if response.status >= 400 and (response.url, response.status) not in self.expected_http_errors else None)

    def tearDown(self):
        self.context.close()
        self.assertEqual(self.errors, [])
        self.assertEqual(self.failed, [])
        self.assertEqual(self.remote, [], 'Page attempted to request the outside internet')

    def test_home_filters_search_and_safe_empty_results(self):
        self.page.goto(self.url)
        self.assertEqual(self.page.locator('.post-card').count(), min(6, len(self.posts)))
        self.assertEqual(self.page.locator('.post-card-link').evaluate_all('(links)=>links.map(link=>new URL(link.href).pathname)'), [emitted_path(post['url']) for post in self.posts[:6]])
        self.page.get_by_role('link', name='More articles', exact=False).click()
        self.assertEqual(urlsplit(self.page.url).path, '/posts/index.html')
        self.assertEqual(self.page.locator('.post-card').count(), len(self.posts))
        self.page.locator('[data-filter="card"]').click()
        self.assertEqual(self.page.locator('.post-card:visible').count(), sum(post['url'].startswith('/card/') for post in self.posts))
        self.page.locator('[data-filter="all"]').click()
        self.assertEqual(self.page.locator('.post-card:visible').count(), len(self.posts))
        self.page.get_by_role('button', name='Search this site').click()
        field = self.page.get_by_role('searchbox', name='Search articles')
        field.fill('prize')
        self.page.locator('.search-result').first.wait_for()
        self.assertIn('Prize card odds', self.page.locator('#search-results').inner_text())
        expected_results = [emitted_path(post['url']) for post in self.posts if 'prize' in f"{post['title']} {post.get('description', '')} {post.get('topic', '')} {post.get('tags', [])} {post.get('text', '')}".lower()]
        self.assertEqual(self.page.locator('.search-result').evaluate_all('(links)=>links.map(link=>new URL(link.href).pathname)'), expected_results)
        field.fill('without replacement')
        self.assertIn('Probability Parlay', self.page.locator('#search-results').inner_text())
        field.fill('<img src=x onerror=alert(1)>')
        self.assertEqual(self.page.locator('#search-results img').count(), 0)
        self.assertIn('No matches', self.page.locator('.search-status').inner_text())
        self.page.keyboard.press('Escape')
        expect(self.page.get_by_role('button', name='Search this site')).to_be_focused()

    def test_shared_header_mobile_menu_and_featured_panels(self):
        self.page.emulate_media(reduced_motion='reduce')
        self.page.goto(self.url)
        nav = self.page.get_by_role('navigation', name='Main navigation')
        expect(nav).to_be_visible()
        for link in nav.locator('a').all():
            expect(link).to_be_visible()
        self.assertEqual(self.page.locator('.site-header').bounding_box()['height'], 80)
        self.assertEqual(self.page.locator('.header__logo').bounding_box()['width'], 145)
        selectors = self.page.locator('[data-slide-to]')
        self.assertGreater(selectors.count(), 1)
        expect(self.page.get_by_label('Play featured slideshow', exact=True)).to_be_visible()
        selectors.nth(1).click()
        expect(self.page.locator('[data-slide="1"]')).to_be_visible()
        expect(self.page.locator('[data-slide="0"]')).not_to_be_visible()
        expect(selectors.nth(1)).to_have_attribute('aria-pressed', 'true')
        self.page.set_viewport_size({'width': 390, 'height': 900})
        self.assertEqual(self.page.locator('.site-header').bounding_box()['height'], 60)
        expect(nav).not_to_be_visible()
        toggle = self.page.get_by_label('Toggle navigation')
        toggle.click()
        expect(nav).to_be_visible()
        self.page.keyboard.press('Escape')
        expect(nav).not_to_be_visible()
        expect(toggle).to_be_focused()
        toggle.click()
        link_to(nav, '/card/index.html').click()
        self.assertEqual(urlsplit(self.page.url).path, '/card/index.html')
        expect(self.page.locator('.gnav')).not_to_be_visible()

    def test_home_news_matches_reference_geometry(self):
        self.page.goto(self.url)
        cards = self.page.locator('.home-news .post-card')
        self.assertEqual(cards.count(), min(6, len(self.posts)))
        boxes = [card.bounding_box() for card in cards.all()]
        self.assertEqual([round(box['width']) for box in boxes], [500, 310, 310, 310, 310, 310][:len(boxes)])
        for row in (boxes[:3], boxes[3:]):
            for previous, current in zip(row, row[1:]):
                self.assertAlmostEqual(current['x'] - previous['x'] - previous['width'], 40, delta=0.1)
        if len(boxes) == 6:
            self.assertAlmostEqual(boxes[3]['x'], boxes[0]['x'], delta=0.1)
            self.assertLess(max(box['y'] for box in boxes[3:]) - min(box['y'] for box in boxes[3:]), 0.1)
        self.assertEqual(self.page.locator('.home-news .heading-home>span').evaluate('(element)=>getComputedStyle(element).fontSize'), '50px')
        self.page.set_viewport_size({'width': 390, 'height': 900})
        for card in cards.all():
            self.assertEqual(round(card.bounding_box()['width']), 350)
        self.assertEqual(self.page.locator('.home-news .heading-home>span').evaluate('(element)=>getComputedStyle(element).fontSize'), '32px')

    def assert_card_image_frames(self, cards):
        viewport_width = self.page.viewport_size['width']
        strip_height = 40 if viewport_width < 768 else min(40, viewport_width * 0.028)
        for card in cards.all():
            label = card.locator('h3').inner_text()
            figure = card.locator('.news-list__th').bounding_box()
            artwork = card.locator('.news-list__img').bounding_box()
            caption = card.locator('.news-list__caption').bounding_box()
            self.assertAlmostEqual(figure['width'], card.bounding_box()['width'], delta=0.1, msg=label)
            self.assertAlmostEqual(artwork['height'], artwork['width'] * 240 / 500, delta=0.1, msg=label)
            for dimension in ('x', 'y', 'width'):
                self.assertAlmostEqual(artwork[dimension], figure[dimension], delta=0.1, msg=f'{label}: {dimension}')
            # The live reference adds a responsive strip below the 500:240 artwork, overlapping its edge by 1px.
            self.assertAlmostEqual(figure['height'], artwork['height'] + strip_height - 1, delta=0.1, msg=label)
            self.assertGreaterEqual(caption['y'], figure['y'])
            self.assertAlmostEqual(caption['y'] + caption['height'], figure['y'] + figure['height'], delta=0.1, msg=label)
            self.assertAlmostEqual(caption['width'], figure['width'], delta=0.1, msg=label)
            for image in card.locator('.news-list__img img').all():
                self.assertEqual(image.evaluate('(image)=>getComputedStyle(image).objectFit'), 'contain', label)

    def test_news_image_frames_scale_consistently(self):
        self.page.goto(self.url)
        cards = self.page.locator('.home-news .post-card')
        for width in (1440, 1024, 768, 390, 320):
            with self.subTest(width=width):
                self.page.set_viewport_size({'width': width, 'height': 900})
                self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'), width)
                self.assert_card_image_frames(cards)
                if width < 768:
                    boxes = [card.bounding_box() for card in cards.all()]
                    self.assertTrue(all(round(box['width']) == width - 40 for box in boxes))
                    self.assertTrue(all(abs(box['x'] - boxes[0]['x']) < 0.1 for box in boxes))
        # Both ordinary covers and pack montages must fit even when newer posts move them off the homepage.
        self.page.goto(self.url + '/card/index.html')
        cards = self.page.locator('.topic-posts .post-card')
        self.assertGreater(cards.locator('.cover-image').count(), 0)
        self.assertGreater(cards.locator('.cover-art').count(), 0)
        for width in (1440, 390):
            self.page.set_viewport_size({'width': width, 'height': 900})
            self.assert_card_image_frames(cards)

    def test_sparse_article_rows_stay_left_aligned(self):
        cases = (
            ('/notes/index.html', '.topic-posts', None),
            ('/sports/index.html', '.topic-posts', None),
            ('/sports/drawing-without-replacement/index.html', '.related-posts .post-grid', None),
            ('/posts/index.html', '#post-grid', 'notes'),
        )
        for route, selector, topic_filter in cases:
            with self.subTest(route=route):
                self.page.set_viewport_size({'width': 1440, 'height': 900})
                self.page.goto(self.url + route)
                if topic_filter:
                    self.page.locator(f'[data-filter="{topic_filter}"]').click()
                grid = self.page.locator(selector)
                cards = grid.locator('.post-card:visible')
                self.assertGreater(cards.count(), 0)
                boxes = [card.bounding_box() for card in cards.all()]
                container = grid.bounding_box()
                for index, box in enumerate(boxes):
                    column = index % 3
                    expected_width = (container['width'] - 80) / 3
                    self.assertAlmostEqual(box['width'], expected_width, delta=0.1)
                    self.assertAlmostEqual(box['x'], container['x'] + column * (expected_width + 40), delta=0.1)
                self.assert_card_image_frames(cards)
                if cards.count() >= 2:
                    # Preserve a two-result regression case as the real post collection grows.
                    cards.evaluate_all('(cards)=>cards.forEach((card,index)=>card.hidden=index>=2)')
                    first, second = [card.bounding_box() for card in grid.locator('.post-card:visible').all()]
                    self.assertAlmostEqual(second['x'] - first['x'] - first['width'], 40, delta=0.1)
                self.page.set_viewport_size({'width': 390, 'height': 900})
                self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'), 390)
                for card in cards.all():
                    self.assertAlmostEqual(card.bounding_box()['width'], grid.bounding_box()['width'], delta=0.1)
                self.assert_card_image_frames(cards)

    def test_nested_http_404_resolves_assets_search_and_home_navigation(self):
        missing_url = self.url + '/missing/deep/page'
        self.expected_http_errors.add((missing_url, 404))
        self.page.route(missing_url, lambda route: route.fulfill(status=404, content_type='text/html', body=(ROOT / '_site/404.html').read_text()))
        response = self.page.goto(missing_url, wait_until='networkidle')
        self.assertEqual(response.status, 404)
        expect(self.page.get_by_role('heading', level=1)).to_have_text('404 Not Found')
        self.assertEqual(self.page.evaluate('document.baseURI'), self.url + '/')
        self.assertEqual(self.page.locator('.site-header').bounding_box()['height'], 80)
        self.assertTrue(self.page.locator('link[rel=stylesheet]').evaluate_all('(links)=>links.length>0 && links.every(link=>link.sheet && link.sheet.cssRules.length>0)'))
        self.page.wait_for_function('Array.from(document.images).every(image=>image.complete && image.naturalWidth>0)')
        self.page.get_by_role('button', name='Search this site').click()
        self.page.get_by_role('searchbox', name='Search articles').fill('prize')
        self.page.locator('.search-result').first.wait_for()
        expect(link_to(self.page.locator('#search-results'), '/card/prize-card-odds/index.html')).to_be_visible()
        self.page.keyboard.press('Escape')
        self.page.get_by_role('link', name='Back to TOP', exact=True).click()
        self.assertEqual(self.page.url, self.url + '/index.html')
        self.assertEqual(self.page.locator('.post-card').count(), min(6, len(self.posts)))

    def test_real_routes_images_and_responsive_layouts(self):
        routes = ['/', '/posts/', '/card/', '/sports/', '/notes/', '/404.html', '/resume/2025/resume.html'] + [post['url'] for post in self.posts]
        for route in routes:
            self.page.goto(self.url + route)
            self.assertEqual(self.page.locator('h1').count(), 1, route)
            self.assertTrue(self.page.locator('link[rel="canonical"]').get_attribute('href').startswith('https://type-null.github.io/'))
            for width in (320, 390, 768, 1440):
                self.page.set_viewport_size({'width': width, 'height': 900})
                self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'), width, f'{route} at {width}px')
            # Load ordinary cover/thumbnail images, including lazy ones, then inspect their actual decode result.
            self.page.locator('img').evaluate_all('(images)=>images.forEach(image=>image.loading="eager")')
            self.page.wait_for_function('Array.from(document.images).every(image=>image.complete)')
            self.assertEqual(self.page.locator('img').evaluate_all('(images)=>images.filter(image=>!image.naturalWidth).map(image=>image.src)'), [], route)

    def test_article_sharing_gallery_and_first_party_embed(self):
        self.context.grant_permissions(['clipboard-read', 'clipboard-write'])
        self.page.goto(self.url + '/card/prize-card-odds/')
        self.page.get_by_role('button', name='Copy link', exact=False).click()
        self.assertEqual(self.page.evaluate('navigator.clipboard.readText()'), 'https://type-null.github.io/card/prize-card-odds/')
        frame = self.page.frame_locator('iframe')
        self.assertEqual(frame.locator('#atLeastOne').inner_text(), '99.15%')
        frame.locator('#copies').fill('0')
        self.assertEqual(frame.locator('#atLeastOne').inner_text(), '0.00%')
        self.page.goto(self.url + '/card/pack-art/')
        self.assertEqual(self.page.locator('.article-gallery figure').count(), 6)
        first = self.page.locator('.article-gallery figure').first
        self.assertIn('/generated/', first.locator('img').evaluate('(image)=>new URL(image.src).pathname'))
        self.assertIn('/set-package-jp/', first.locator('a').evaluate('(link)=>new URL(link.href).pathname'))

    def test_no_javascript_preserves_navigation_and_archive(self):
        context = self.browser.new_context(java_script_enabled=False)
        page = context.new_page()
        page.goto(self.url)
        self.assertEqual(page.locator('.post-card').count(), min(6, len(self.posts)))
        self.assertFalse(page.locator('[data-search-open]').is_visible())
        self.assertEqual(page.locator('.topic-filter').count(), 0)
        expect(page.locator('.gnav')).to_be_visible()
        page.set_viewport_size({'width': 390, 'height': 900})
        expect(page.locator('.gnav')).not_to_be_visible()
        page.get_by_label('Toggle navigation').click()
        expect(page.locator('.gnav')).to_be_visible()
        link_to(page.locator('.gnav'), '/card/index.html').click()
        self.assertEqual(urlsplit(page.url).path, '/card/index.html')
        page.goto(self.url + '/card/2024/02/timeline.html')
        self.assertEqual(page.locator('.timeline-table tbody tr').count(), len({entry['year'] for entry in self.sets}))
        self.assertEqual(page.locator('.set-art').count(), len(self.sets))
        self.assertEqual(page.locator('.timeline-chart .timeline-table img').count(), len(self.sets))
        context.close()

    def test_complete_resume_remains_unlisted(self):
        archive = '/resume/2025/resume.html'
        self.assertFalse(any(post['url'] == archive for post in self.posts))
        for path in ('index.html', 'notes/index.html'):
            self.page.goto(self.url + '/' + path)
            self.assertNotIn(archive, link_paths(self.page), path)
        for path in ('search-index.json', 'sitemap.xml', 'feed.xml'):
            self.assertNotIn(archive, (ROOT / '_site' / path).read_text(), path)
        self.page.goto(self.url + archive)
        self.assertIn('noindex', self.page.locator('meta[name="robots"]').get_attribute('content'))
        self.assertGreater(len(self.page.locator('.article-body').inner_text()), 700)
        self.assertGreaterEqual(self.page.locator('.article-body a').count(), 6)
        self.assertIn('Contact', self.page.locator('.article-body').inner_text())
        self.assertGreater(self.page.locator('.article-body img').count(), 0)
        self.page.goto(self.url)
        self.assertNotIn(archive, link_paths(self.page))

    def test_filtered_timeline_share_uses_current_query(self):
        self.context.grant_permissions(['clipboard-read', 'clipboard-write'])
        self.page.goto(self.url + '/card/2024/02/timeline.html?era=SV')
        self.page.locator('[data-copy-link]').click()
        copied = self.page.evaluate('navigator.clipboard.readText()')
        self.assertIn('https://type-null.github.io/card/2024/02/timeline.html?', copied)
        self.assertIn('era=SV', copied)

if __name__ == '__main__':
    unittest.main()

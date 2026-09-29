"""Homepage topic compositions and decorative motion, opened directly from disk."""
from pathlib import Path
from urllib.parse import unquote, urlsplit
import json
import os
import re
import unittest

import yaml

try:
    from playwright.sync_api import sync_playwright, expect
except ImportError:
    sync_playwright = None


ROOT = Path(__file__).resolve().parents[1]


def local_path(url):
    parsed = urlsplit(url)
    if parsed.scheme != 'file':
        raise AssertionError(f'Expected a portable file link, got {url}')
    return Path(unquote(parsed.path)).resolve()


def post_path(base, route):
    path = base / urlsplit(route).path.lstrip('/')
    return path / 'index.html' if route.endswith('/') else path


@unittest.skipUnless(sync_playwright, 'Install requirements-dev.txt for browser checks')
class HomeShowcaseBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.built = ROOT / '_site'
        if not (cls.built / 'index.html').is_file():
            raise RuntimeError('Run python scripts/build.py --check before browser checks')
        cls.posts = json.loads((cls.built / 'search-index.json').read_text())
        cls.topics = {path.parent.name: yaml.safe_load(path.read_text())
                      for path in (ROOT / 'content').glob('*/_topic.yml')}
        cls.runtime = sync_playwright().start()
        cls.addClassCleanup(cls.runtime.stop)
        kwargs = {'headless': True}
        if os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE'):
            kwargs['executable_path'] = os.environ['PLAYWRIGHT_CHROMIUM_EXECUTABLE']
        cls.browser = cls.runtime.chromium.launch(**kwargs)
        cls.addClassCleanup(cls.browser.close)

    def setUp(self):
        self.contexts = []
        self.errors, self.failed, self.remote = [], [], []

    def tearDown(self):
        try:
            self.assertEqual(self.errors, [], 'Homepage JavaScript or console error')
            self.assertEqual(self.failed, [], 'A homepage file failed to load')
            self.assertEqual(self.remote, [], 'Homepage must work without internet access')
        finally:
            for context in self.contexts:
                context.close()

    def home(self, width=1440, height=1000, init_script=None, **kwargs):
        context = self.browser.new_context(viewport={'width': width, 'height': height}, **kwargs)
        context.set_default_timeout(10000)
        if init_script:
            context.add_init_script(init_script)
        self.contexts.append(context)
        context.route('http://**/*', lambda route: route.abort())
        context.route('https://**/*', lambda route: route.abort())
        context.on('request', lambda request: self.remote.append(request.url)
                   if urlsplit(request.url).scheme in ('http', 'https', 'ws', 'wss') else None)
        context.on('requestfailed', lambda request: self.failed.append((request.url, request.failure)))
        page = context.new_page()
        page.on('pageerror', lambda error: self.errors.append(str(error)))
        page.on('console', lambda message: self.errors.append(message.text) if message.type == 'error' else None)
        page.goto((self.built / 'index.html').as_uri(), wait_until='load')
        page.locator('img').evaluate_all('(images)=>images.forEach(image=>image.loading="eager")')
        page.wait_for_function('Array.from(document.images).every(image=>image.complete)')
        self.assertEqual(page.locator('img').evaluate_all('(images)=>images.filter(image=>!image.naturalWidth).map(image=>image.src)'), [])
        page.evaluate('() => document.fonts.ready.then(() => true)')
        return page

    def topic_links(self, page):
        return page.locator('.topic-showcase-link').evaluate_all('(links)=>links.map(link=>link.href)')

    def assert_content_available(self, page):
        for link in page.locator('.topic-showcase-link').all():
            expect(link).to_be_visible()
            self.assertEqual(link.evaluate('(link)=>getComputedStyle(link).opacity'), '1')
            self.assertTrue(local_path(link.evaluate('(link)=>link.href')).is_file())

    def position_panel(self, page, panel, fraction):
        panel.evaluate('''(element, fraction) => {
            document.documentElement.style.scrollBehavior = 'auto';
            window.scrollTo(0, window.scrollY + element.getBoundingClientRect().top - innerHeight * fraction);
        }''', fraction)
        page.wait_for_function('''({selector, fraction}) =>
            Math.abs(document.querySelector(selector).getBoundingClientRect().top - innerHeight * fraction) < 2
        ''', arg={'selector': f'[data-color-reveal="{panel.get_attribute("data-color-reveal")}"]', 'fraction': fraction})

    def reveal_state(self, panel):
        return panel.evaluate('''element => {
            const style = getComputedStyle(element, '::before');
            const matrix = new DOMMatrix(style.transform);
            return {x: matrix.e, y: matrix.f, scaleX: matrix.a, scaleY: matrix.d,
                gradient: style.backgroundImage, duration: style.animationDuration,
                playState: style.animationPlayState,
                spans: [...element.children].map(child => {
                    const mask = getComputedStyle(child);
                    const transform = new DOMMatrix(mask.transform);
                    return {x: transform.a, y: transform.d, display: mask.display, opacity: mask.opacity};
                })};
        }''')

    def assert_decorations_static_and_visible(self, page):
        for panel in page.locator('[data-color-reveal]').all():
            state = self.reveal_state(panel)
            self.assertNotEqual(state['gradient'], 'none')
            self.assertAlmostEqual(state['x'], 0, delta=0.1)
            self.assertAlmostEqual(state['y'], 0, delta=0.1)
            self.assertEqual(state['duration'], '0s')
            if panel.get_attribute('data-color-reveal') in ('columns', 'rows'):
                self.assertTrue(all(mask['display'] == 'none' or mask['opacity'] == '0'
                                    or abs(mask['x']) < 0.01 or abs(mask['y']) < 0.01 for mask in state['spans']))

    def add_scroll_room(self, page):
        # Extra space permits exact trigger positions near the final section;
        # the real backgrounds, content and observer are unchanged.
        page.evaluate('''() => {
            const spacer = document.createElement('div');
            spacer.style.height = '2000px';
            document.body.append(spacer);
        }''')

    def test_topics_use_real_listed_posts_and_preserve_six_newest_news(self):
        page = self.home(reduced_motion='reduce')
        news = page.locator('.home-news .post-card-link')
        expected = [post_path(self.built, post['url']).resolve() for post in self.posts[:6]]
        self.assertEqual([local_path(url) for url in news.evaluate_all('(links)=>links.map(link=>link.href)')], expected)
        sections = page.locator('.home-topic')
        self.assertEqual(set(sections.evaluate_all('(sections)=>sections.map(section=>section.dataset.topic)')), set(self.topics))
        self.assertTrue({'gallery', 'feature', 'journal'}.issubset(set(sections.evaluate_all('(sections)=>sections.map(section=>section.dataset.layout)'))))
        all_listed = {post_path(self.built, post['url']).resolve() for post in self.posts}
        for section in sections.all():
            slug = section.get_attribute('data-topic')
            self.assertEqual(section.get_attribute('data-layout'), self.topics[slug]['home_layout'])
            links = [local_path(url) for url in section.locator('.topic-showcase-link').evaluate_all('(links)=>links.map(link=>link.href)')]
            self.assertTrue(links, f'{slug} should expose actual posts')
            self.assertEqual(len(links), len(set(links)), f'{slug} repeats a preview')
            self.assertTrue(set(links).issubset(all_listed), f'{slug} contains an unlisted or nonexistent post')
            self.assertTrue(all(path.is_relative_to(self.built / slug) for path in links))
            expect(section.locator('.topic-preview__art')).to_have_count(len(links))
        self.assertEqual(page.locator('a[href*="resume/"]').count(), 0)
        self.assert_content_available(page)
        # Topic previews are real local navigation, not JavaScript-only tiles.
        first = page.locator('.topic-showcase-link').first
        destination = local_path(first.evaluate('(link)=>link.href'))
        first.click()
        self.assertEqual(local_path(page.url), destination)
        expect(page.locator('h1')).to_be_visible()

    def test_responsive_topic_compositions_remain_distinct_without_overflow(self):
        for width in (320, 390, 768, 1440):
            with self.subTest(width=width):
                page = self.home(width=width, reduced_motion='reduce')
                self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth'), width)
                self.assert_content_available(page)
                for section in page.locator('.home-topic').all():
                    bounds = section.bounding_box()
                    self.assertGreater(bounds['height'], 100)
                    for link in section.locator('.topic-showcase-link').all():
                        box = link.bounding_box()
                        self.assertGreaterEqual(box['x'], -0.5)
                        self.assertLessEqual(box['x'] + box['width'], width + 0.5)
                    for preview in section.locator('.topic-preview').all():
                        frame = preview.locator('.topic-preview__art').bounding_box()
                        classes = preview.get_attribute('class').split()
                        ratio = 16 / 9 if any(value in classes for value in ('topic-preview--lead', 'topic-preview--small')) else 3 / 2
                        self.assertAlmostEqual(frame['height'], frame['width'] / ratio, delta=0.2)
                gallery = page.locator('.topic-gallery .topic-preview')
                journal = page.locator('.topic-journal .topic-preview')
                lead = page.locator('.topic-feature .topic-preview--lead')
                small = page.locator('.topic-feature .topic-preview--small')
                if width == 1440:
                    first, second = gallery.nth(0).bounding_box(), gallery.nth(1).bounding_box()
                    self.assertAlmostEqual(first['y'], second['y'], delta=1)
                    self.assertGreater(second['x'], first['x'] + first['width'])
                    self.assertGreater(lead.bounding_box()['width'], small.first.bounding_box()['width'] * 1.4)
                first, second = journal.nth(0).bounding_box(), journal.nth(1).bounding_box()
                self.assertAlmostEqual(first['x'], second['x'], delta=1)
                self.assertGreaterEqual(second['y'], first['y'] + first['height'])
                expect(page.locator('.topic-preview__date')).to_have_count(journal.count())

    def test_two_gallery_items_keep_the_same_left_aligned_slots(self):
        page = self.home(reduced_motion='reduce')
        gallery = page.locator('.topic-gallery').first
        items = gallery.locator('.topic-preview')
        self.assertGreaterEqual(items.count(), 3)
        before = [item.bounding_box() for item in items.all()[:2]]
        items.evaluate_all('(items)=>items.slice(2).forEach(item=>item.remove())')
        after = [item.bounding_box() for item in items.all()]
        self.assertEqual(len(after), 2)
        for original, reduced in zip(before, after):
            for dimension in ('x', 'width', 'y'):
                self.assertAlmostEqual(reduced[dimension], original[dimension], delta=0.1)
        self.assertAlmostEqual(after[0]['x'], gallery.bounding_box()['x'], delta=0.1)
        # The feature section naturally has two supporting articles. Their gap
        # must be the declared gutter, without stretching across an empty slot.
        previews = page.locator('.topic-feature__previews').first
        first, second = [item.bounding_box() for item in previews.locator('.topic-preview').all()]
        gutter = previews.evaluate('(element)=>parseFloat(getComputedStyle(element).columnGap)')
        self.assertAlmostEqual(first['x'], previews.bounding_box()['x'], delta=0.1)
        self.assertAlmostEqual(second['x'] - first['x'] - first['width'], gutter, delta=0.1)

    def test_scroll_reveals_only_decoration_and_does_not_replay(self):
        page = self.home(reduced_motion='no-preference')
        expect(page.locator('html')).to_have_class(re.compile(r'\bhome-motion-ready\b'))
        panel = page.locator('[data-color-reveal="from-right"]')
        expect(panel).not_to_have_class(re.compile(r'\bis-revealed\b'))
        self.assertGreater(abs(self.reveal_state(panel)['x']), 1)
        for kind, delays in (('columns', [0.3, 0.3, 0.3]), ('rows', [0.3, 0.4, 0.5])):
            masks = page.locator(f'[data-color-reveal="{kind}"]>span')
            expect(masks).to_have_count(3)
            self.assertEqual(masks.evaluate_all('(masks)=>masks.map(mask=>parseFloat(getComputedStyle(mask).transitionDelay))'), delays)
            self.assertEqual(masks.evaluate_all('(masks)=>masks.map(mask=>parseFloat(getComputedStyle(mask).transitionDuration))'), [0.7] * 3)
        self.assert_content_available(page)
        self.add_scroll_room(page)
        self.position_panel(page, panel, 0.75)
        page.wait_for_timeout(150)
        expect(panel).not_to_have_class(re.compile(r'\bis-revealed\b'))
        self.position_panel(page, panel, 0.65)
        expect(panel).to_have_class(re.compile(r'\bis-revealed\b'))
        expect(panel).to_have_class(re.compile(r'\bis-on-screen\b'))
        page.wait_for_function('''() => Math.abs(new DOMMatrix(getComputedStyle(
            document.querySelector('[data-color-reveal="from-right"]'), '::before').transform).e) < 0.1''')
        state = self.reveal_state(panel)
        self.assertEqual(state['duration'], '8s')
        self.assertEqual(state['playState'], 'running')
        page.evaluate('window.scrollTo(0, 0)')
        expect(panel).not_to_have_class(re.compile(r'\bis-on-screen\b'))
        expect(panel).to_have_class(re.compile(r'\bis-revealed\b'))
        self.assertEqual(self.reveal_state(panel)['playState'], 'paused')
        self.position_panel(page, panel, 0.65)
        expect(panel).to_have_class(re.compile(r'\bis-on-screen\b'))
        self.assertAlmostEqual(self.reveal_state(panel)['x'], 0, delta=0.1,
                               msg='Returning to a revealed block must not restart its entrance')
        # Jumping directly to the last section can skip the earlier blocks
        # without intersecting them. Visit both mask patterns explicitly.
        for kind in ('columns', 'rows'):
            masked = page.locator(f'[data-color-reveal="{kind}"]')
            self.position_panel(page, masked, 0.65)
            expect(masked).to_have_class(re.compile(r'\bis-revealed\b'))
            page.wait_for_function('''kind => [...document.querySelector(
                `[data-color-reveal="${kind}"]`).children]
                .every(mask=>Math.abs(new DOMMatrix(getComputedStyle(mask).transform).a) < 0.01)''', arg=kind)

    def test_reveal_threshold_tracks_viewport_height_after_resize(self):
        page = self.home(width=390, height=1000, reduced_motion='no-preference')
        self.add_scroll_room(page)
        panel = page.locator('[data-color-reveal="from-right"]')
        self.position_panel(page, panel, 0.75)
        page.wait_for_timeout(150)
        expect(panel).not_to_have_class(re.compile(r'\bis-revealed\b'))
        page.set_viewport_size({'width': 390, 'height': 800})
        # Correct trigger: 70% of 800 = 560px. A stale -300px margin leaves
        # only 500px and fails to reveal this panel at 540px.
        self.position_panel(page, panel, 0.675)
        expect(panel).to_have_class(re.compile(r'\bis-revealed\b'))

    def test_reduced_motion_initial_and_changed_preference_keep_colors_visible(self):
        reduced = self.home(reduced_motion='reduce')
        self.assert_content_available(reduced)
        self.assert_decorations_static_and_visible(reduced)
        changed = self.home(reduced_motion='no-preference')
        panel = changed.locator('[data-color-reveal="from-right"]')
        self.assertGreater(abs(self.reveal_state(panel)['x']), 1)
        changed.emulate_media(reduced_motion='reduce')
        self.assert_decorations_static_and_visible(changed)
        self.assert_content_available(changed)
        changed.emulate_media(reduced_motion='no-preference')
        # A user preference change must not hide an already revealed panel.
        self.assertAlmostEqual(self.reveal_state(panel)['x'], 0, delta=0.1)

    def test_without_javascript_the_topics_and_color_blocks_still_render(self):
        page = self.home(java_script_enabled=False)
        self.assert_content_available(page)
        self.assert_decorations_static_and_visible(page)
        expect(page.locator('.home-news .post-card-link')).to_have_count(min(6, len(self.posts)))
        first = page.locator('.topic-showcase-link').first
        destination = local_path(first.evaluate('(link)=>link.href'))
        first.click()
        self.assertEqual(local_path(page.url), destination)
        expect(page.locator('h1')).to_be_visible()

    def test_browser_without_intersection_observer_keeps_the_static_fallback(self):
        page = self.home(init_script='delete window.IntersectionObserver')
        expect(page.locator('html')).not_to_have_class(re.compile(r'\bhome-motion-ready\b'))
        self.assert_content_available(page)
        self.assert_decorations_static_and_visible(page)

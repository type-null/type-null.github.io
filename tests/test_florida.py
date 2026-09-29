"""Florida stays findable without changing the news chronology or needing JS."""
from html.parser import HTMLParser
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from urllib.parse import unquote, urljoin, urlsplit

import jinja2

try:
    from playwright.sync_api import sync_playwright, expect
except ImportError:
    sync_playwright = None

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build import discover
from portable import make_portable

FLORIDA = '/notes/florida-power-systems/'


class HomeLinks(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.links = []
        self.feed(source)

    def handle_starttag(self, tag, attributes):
        if tag == 'a':
            self.links.append(dict(attributes))

    def matching(self, class_name):
        return [link for link in self.links if class_name in link.get('class', '').split()]


def homepage(topics, posts):
    # Render the production content blocks without unrelated site-shell metadata.
    env = jinja2.Environment(
        loader=jinja2.ChoiceLoader([
            jinja2.DictLoader({'base.html': '<!doctype html><main>{% block content %}{% endblock %}</main>'}),
            jinja2.FileSystemLoader(ROOT / 'templates'),
        ]),
        autoescape=True, undefined=jinja2.StrictUndefined,
    )
    listed = [post for post in posts if not post['unlisted']]
    return HomeLinks(env.get_template('home.html').render(
        site={'title': 'Type Null', 'description': 'A personal journal'},
        topics=topics, posts=listed, all_posts=listed,
        featured_posts=[post for post in listed if post['featured']],
    ))


class FloridaDiscoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.topics, cls.posts = discover(ROOT)

    def test_florida_is_first_information_link_without_changing_latest_six(self):
        florida = next(post for post in self.posts if post['url'] == FLORIDA)
        self.assertTrue(florida['announcement'])
        self.assertTrue(florida['featured'])
        self.assertFalse(florida['unlisted'])
        self.assertEqual(florida['date'], '2026-09-29')
        links = homepage(self.topics, self.posts)
        notices = links.matching('home-notice__list-links')
        self.assertEqual(notices[0]['href'], FLORIDA)
        self.assertNotIn('hidden', notices[0])
        self.assertEqual(len(notices), 2)
        listed = [post for post in self.posts if not post['unlisted']]
        self.assertEqual([link['href'] for link in links.matching('post-card-link')],
                         [post['url'] for post in listed[:6]])
        hero = links.matching('home-hero__slide')
        self.assertEqual(hero[0]['href'], '/card/2024/02/timeline.html')
        self.assertTrue(any(link['href'] == FLORIDA for link in hero))

    def test_announcement_selection_is_generic_deduplicated_and_excludes_unlisted(self):
        posts = [{**post, 'announcement': False} for post in self.posts]
        listed = [post for post in posts if not post['unlisted']]
        picked = listed[-1]
        picked['announcement'] = True
        for post in posts:
            if post['unlisted']:
                post['announcement'] = True
        links = homepage(self.topics, posts)
        self.assertEqual([link['href'] for link in links.matching('home-notice__list-links')],
                         [picked['url'], listed[0]['url']])
        picked['announcement'] = False
        listed[0]['announcement'] = True
        links = homepage(self.topics, posts)
        self.assertEqual([link['href'] for link in links.matching('home-notice__list-links')],
                         [post['url'] for post in listed[:2]])
        for post in posts:
            post.pop('announcement', None)
        links = homepage(self.topics, posts)
        self.assertEqual([link['href'] for link in links.matching('home-notice__list-links')],
                         [post['url'] for post in listed[:2]])


@unittest.skipUnless(sync_playwright, 'Install requirements-dev.txt for browser checks')
class FloridaLegacyFileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='florida-navigation-')
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.site = Path(cls.temporary.name) / 'Copied site with spaces 中文'
        (cls.site / 'florida').mkdir(parents=True)
        shutil.copy2(ROOT / 'legacy/florida/map.html', cls.site / 'florida/map.html')
        shutil.copytree(ROOT / 'assets/fonts', cls.site / 'assets/fonts')
        (cls.site / 'assets/css').mkdir()
        shutil.copy2(ROOT / 'assets/css/site.css', cls.site / 'assets/css/site.css')
        _, posts = discover(ROOT)
        florida = next(post for post in posts if post['url'] == FLORIDA)
        article = cls.site / FLORIDA.lstrip('/') / 'index.html'
        article.parent.mkdir(parents=True)
        article.write_text('<!doctype html><html lang="en"><meta charset="utf-8">'
                           '<title>Florida research</title><h1>' + florida['title'] + '</h1>'
                           + str(florida['html']) + '</html>', encoding='utf-8')
        (cls.site / 'index.html').write_text('<!doctype html><h1>Blog home</h1>', encoding='utf-8')
        make_portable(cls.site)
        cls.runtime = sync_playwright().start()
        cls.addClassCleanup(cls.runtime.stop)
        options = {'headless': True}
        if os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE'):
            options['executable_path'] = os.environ['PLAYWRIGHT_CHROMIUM_EXECUTABLE']
        cls.browser = cls.runtime.chromium.launch(**options)
        cls.addClassCleanup(cls.browser.close)

    def test_legacy_address_opens_real_intro_without_javascript_or_network(self):
        for width in (1440, 390, 320):
            with self.subTest(width=width):
                errors, remote, failed = [], [], []
                context = self.browser.new_context(java_script_enabled=False,
                                                   viewport={'width': width, 'height': 900})
                try:
                    def local_only(route):
                        if urlsplit(route.request.url).scheme == 'file':
                            route.continue_()
                        else:
                            remote.append(route.request.url)
                            route.abort()
                    context.route('**/*', local_only)
                    page = context.new_page()
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    page.on('requestfailed', lambda request: failed.append(request.url))
                    page.goto((self.site / 'florida/map.html').as_uri())
                    link = page.get_by_role('link', name='Read the project introduction')
                    expect(link).to_be_visible()
                    self.assertFalse(page.evaluate('document.documentElement.scrollWidth > innerWidth'))
                    destination = urljoin(page.url, link.get_attribute('href'))
                    self.assertEqual(Path(unquote(urlsplit(destination).path)),
                                     self.site / FLORIDA.lstrip('/') / 'index.html')
                    link.click()
                    expect(page.get_by_role('heading', level=1)).to_have_text('Florida power systems research')
                    self.assertEqual(page.url, destination)
                    self.assertEqual((errors, remote, failed), ([], [], []))
                finally:
                    context.close()


if __name__ == '__main__':
    unittest.main()

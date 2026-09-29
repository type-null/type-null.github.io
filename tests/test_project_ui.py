"""Offline project portals: local previews, with external links only on request.

Build first with scripts/build.py --check. Set PLAYWRIGHT_CHROMIUM_EXECUTABLE
when using an installed Chrome instead of Playwright's bundled browser.
Outbound navigation is intercepted locally; these tests do not verify deployment.
"""
from pathlib import Path
from urllib.parse import unquote, urlsplit
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import shutil
import sys
import tempfile
import threading
import unittest

try:
    from playwright.sync_api import sync_playwright, expect
except ImportError:
    sync_playwright = None


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = Path(tempfile.gettempdir()) / 'type-null-project-portals'
PROJECTS = (
    ('card/event-calendar', 'https://github.com/type-null/PTCG-calendar'),
    ('card/card-database', 'https://github.com/type-null/PTCG-database'),
    ('notes/squirrel-census', 'https://github.com/type-null/Website-central-park-squirrel-tracker'),
)
FIXTURE_REPOSITORY = 'https://github.com/type-null/example-project'
FIXTURE_WEBSITE = 'https://type-null.github.io/example-project/?view=cards#featured'
INTERACTIVE_WEBSITE = 'https://projects.example.test/interactive/'
PROJECT_APP = '''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Independent project fixture</title><link rel="icon" href="data:,">
<style>body{margin:16px;font:16px sans-serif}input,button{min-height:44px;max-width:100%;box-sizing:border-box}dialog{max-width:70%;max-height:70%;overflow:auto}</style>
</head><body><label>Project note <input id="note" value="Original note"></label>
<button id="details" type="button">Open details</button>
<dialog id="detail"><button id="close" type="button">Close</button><p>Project details</p></dialog>
<script>
let parentRequest;
window.announceReady = () => {
  if (parentRequest) parentRequest.source.postMessage({type:'type-null:embed-ready'}, parentRequest.origin === 'null' ? '*' : parentRequest.origin);
};
addEventListener('message', event => {
  if (event.source !== parent || event.data?.type !== 'type-null:embed-ping') return;
  parentRequest = event;
  if (!window.holdReady) window.announceReady();
});
document.getElementById('details').onclick = () => {
  document.getElementById('detail').showModal();
  parent.postMessage({type:'type-null:focus-embed'}, '*');
};
document.getElementById('close').onclick = () => document.getElementById('detail').close();
</script></body></html>'''


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass


def file_path(url):
    parsed = urlsplit(url)
    if parsed.scheme != 'file':
        raise AssertionError(f'Expected a local file, got {url}')
    return Path(unquote(parsed.path)).resolve()


@unittest.skipUnless(sync_playwright, 'Install requirements-dev.txt for browser checks')
class ProjectBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.built = ROOT / '_site'
        for route, _ in PROJECTS:
            if not (cls.built / route / 'index.html').is_file():
                raise RuntimeError(f'Build the complete site first; missing {route}/index.html')
        cls.temporary = tempfile.TemporaryDirectory(prefix='type-null-project-portals-')
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.moved = (Path(cls.temporary.name) / 'Projects with spaces 展示' / 'portable site').resolve()
        shutil.copytree(cls.built, cls.moved)
        cls.locations = ((ROOT, 1440), (cls.built, 390), (cls.moved, 320))
        cls.create_linked_fixture()
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(cls.moved)))
        cls.hosted_url = f'http://127.0.0.1:{cls.server.server_port}'
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        cls.addClassCleanup(cls.stop_server)
        cls.runtime = sync_playwright().start()
        cls.addClassCleanup(cls.runtime.stop)
        options = {'headless': True}
        if os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE'):
            options['executable_path'] = os.environ['PLAYWRIGHT_CHROMIUM_EXECUTABLE']
        cls.browser = cls.runtime.chromium.launch(**options)
        cls.addClassCleanup(cls.browser.close)
        ARTIFACTS.mkdir(parents=True, exist_ok=True)

    @classmethod
    def stop_server(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.server_thread.join(timeout=5)

    @classmethod
    def create_linked_fixture(cls):
        # Use real Markdown metadata and portable-media production code. The
        # synthetic destinations below test behavior, not live deployment.
        sys.path.insert(0, str(ROOT / 'scripts'))
        from build import discover, copy_post_media
        from portable import make_portable
        source_root = Path(cls.temporary.name) / 'Authored project fixture'
        for slug, website, interactive in (
                ('linked-project', FIXTURE_WEBSITE, False),
                ('interactive-project', INTERACTIVE_WEBSITE, True)):
            source = source_root / f'content/notes/{slug}/index.md'
            source.parent.mkdir(parents=True)
            shutil.copy2(ROOT / 'content/card/card-database/cover.png', source.parent / 'Preview with spaces 展示.png')
            source.write_text(f'''---
title: A linked project
date: 2026-09-29
embeds:
  - type: project
    title: Card browser project
    image: Preview with spaces 展示.png
    repository: {FIXTURE_REPOSITORY}
    url: {website}
    interactive: {str(interactive).lower()}
---
The article introduces the project.

[[embed:1]]

The article continues after the preview.
''')
        _, posts = discover(source_root)
        for post in posts:
            copy_post_media(post, cls.moved)
            target = cls.moved / post['url'].strip('/') / 'index.html'
            spacer = '<div class="portal-spacer" aria-hidden="true"></div>' if 'interactive-project' in post['url'] else ''
            target.write_text(
                '<!doctype html><html lang="en"><head><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width, initial-scale=1">'
                '<title>Linked project fixture</title><link rel="stylesheet" href="/assets/css/site.css">'
                '<link rel="icon" href="data:,"><style>.portal-spacer{height:150vh}'
                '.site-header{position:fixed;inset:0 0 auto;height:80px;z-index:90;background:white}</style>'
                '<script src="/assets/js/site.js" defer></script>'
                '</head><body><header class="site-header">Article navigation</header>'
                '<main class="section-wrap article-wrap"><article class="news-body">'
                '<div class="page-parag__inr"><div class="article-body prose">' + spacer
                + str(post['html']) + str(post['embeds_html'])
                + '</div></div></article></main></body></html>')
        cls.fixture_page = cls.moved / 'notes/linked-project/index.html'
        cls.interactive_page = cls.moved / 'notes/interactive-project/index.html'
        make_portable(cls.moved)

    def setUp(self):
        self.errors, self.failed, self.remote, self.outside = [], [], [], []
        self.intercepted = []
        self.embedded = []
        self.embedded_responses = {}
        self.expected_http_status = {}
        self.expected_http_console = []
        self.expected_navigation = None
        self.contexts = []

    def tearDown(self):
        report = {'test': self.id(), 'errors': self.errors, 'failedResources': self.failed,
                  'unexpectedNetworkAttempts': self.remote, 'outsidePackage': self.outside,
                  'interceptedOutboundNavigations': self.intercepted,
                  'interceptedProjectLoads': self.embedded,
                  'expectedHttpErrors': self.expected_http_console}
        (ARTIFACTS / f'{self._testMethodName}.json').write_text(json.dumps(report, indent=2))
        try:
            self.assertEqual(self.errors, [], 'JavaScript or console errors')
            self.assertEqual(self.failed, [], 'Failed local resources')
            self.assertEqual(self.remote, [], 'A project made an unapproved network request')
            self.assertEqual(self.outside, [], 'A moved article reached outside its package')
        finally:
            for context in self.contexts:
                context.close()

    def context_for(self, base, width, hosted=False, **kwargs):
        height = 1000 if width == 1440 else (667 if width == 390 else 568)
        context = self.browser.new_context(viewport={'width': width, 'height': height}, **kwargs)
        context.set_default_timeout(10000)
        self.contexts.append(context)

        def permitted_navigation(request):
            # Fragments belong to the destination URL, not the HTTP request.
            return (self.expected_navigation is not None and request.is_navigation_request()
                    and request.url == self.expected_navigation.split('#', 1)[0])

        def project_navigation(request):
            return request.is_navigation_request() and request.url in self.embedded_responses

        def intercept_network(route):
            if permitted_navigation(route.request):
                route.fulfill(status=200, content_type='text/html', body=(
                    '<!doctype html><title>Intercepted destination</title>'
                    '<link rel="icon" href="data:,">'
                    '<p>External navigation intercepted locally for this test.</p>'))
            elif project_navigation(route.request):
                status, body = self.embedded_responses[route.request.url]
                if status >= 400:
                    self.expected_http_status[route.request.url] = status
                route.fulfill(status=status, content_type='text/html', body=body)
            elif hosted and route.request.url.startswith(self.hosted_url + '/'):
                route.continue_()
            else:
                route.abort()

        def requested(request):
            scheme = urlsplit(request.url).scheme
            if scheme in ('http', 'https', 'ws', 'wss'):
                if permitted_navigation(request):
                    self.intercepted.append(request.url)
                elif project_navigation(request):
                    self.embedded.append(request.url)
                elif not (hosted and request.url.startswith(self.hosted_url + '/')):
                    self.remote.append(request.url)
            elif scheme == 'file' and not file_path(request.url).is_relative_to(base.resolve()):
                self.outside.append(request.url)

        def watch_page(page):
            page.on('pageerror', lambda error: self.errors.append(str(error)))
            def console_message(message):
                if message.type != 'error':
                    return
                status = self.expected_http_status.get(message.location.get('url'))
                if status == 404 and '404' in message.text:
                    self.expected_http_console.append(message.text)
                else:
                    self.errors.append(message.text)
            page.on('console', console_message)

        context.route('http://**/*', intercept_network)
        context.route('https://**/*', intercept_network)
        context.on('request', requested)
        context.on('requestfailed', lambda request: self.failed.append({'url': request.url, 'failure': request.failure}))
        context.on('page', watch_page)
        return context

    def settle_images(self, page):
        page.locator('img').evaluate_all('(images) => images.forEach(image => image.loading = "eager")')
        page.wait_for_function('Array.from(document.images).every(image => image.complete)')
        broken = page.locator('img').evaluate_all('(images) => images.filter(image => !image.naturalWidth).map(image => image.src)')
        self.assertEqual(broken, [], 'Every article illustration must decode offline')
        page.evaluate('() => document.fonts.ready.then(() => true)')

    def portal(self, page, width, repository, website=None):
        expect(page.locator('iframe')).to_have_count(0)
        expect(page.locator('.article-cover')).to_have_count(0)
        portal = page.locator('.embed--project')
        expect(portal).to_have_count(1)
        preview = portal.locator('.project-preview')
        expect(preview).to_have_attribute('href', website or repository)
        expect(preview).to_have_attribute('target', '_blank')
        expect(preview).to_have_attribute('rel', 'noopener noreferrer')
        expect(preview.locator('img')).to_have_count(1)
        self.assertTrue(preview.locator('img').get_attribute('alt'))
        self.assertTrue(file_path(preview.locator('img').evaluate('(image) => image.src')).is_file())
        source = portal.locator('.embed-repository')
        expect(source).to_have_attribute('href', repository)
        self.assertIn('GitHub', source.get_attribute('aria-label'))
        self.assertIn('new tab', source.get_attribute('aria-label'))
        links = [source]
        if website:
            open_link = portal.locator('.embed-open')
            expect(open_link).to_have_attribute('href', website)
            links.append(open_link)
        else:
            expect(portal.locator('.embed-open')).to_have_count(0)
        for link in links:
            expect(link).to_have_attribute('target', '_blank')
            expect(link).to_have_attribute('rel', 'noopener noreferrer')
            self.assertNotEqual(link.get_attribute('tabindex'), '-1')
            link.scroll_into_view_if_needed()
            box = link.bounding_box()
            self.assertGreaterEqual(box['height'], 44)
            self.assertGreaterEqual(box['width'], 44)
            self.assertGreaterEqual(box['x'], 0)
            self.assertLessEqual(box['x'] + box['width'], width + 1)
        box = source.bounding_box()
        self.assertAlmostEqual(box['width'], box['height'], delta=1)
        self.assertEqual(source.evaluate('(link) => getComputedStyle(link).borderRadius'), '50%')
        self.assertTrue(page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), 'Horizontal article overflow')
        return portal

    def open_intercepted_tab(self, page, link, destination):
        initial_url = page.url
        self.expected_navigation = destination
        link.focus()
        expect(link).to_be_focused()
        with page.expect_popup() as opened:
            page.keyboard.press('Enter')
        popup = opened.value
        popup.wait_for_load_state('load')
        self.assertEqual(popup.url, destination)
        expect(popup).to_have_title('Intercepted destination')
        self.assertTrue(popup.evaluate('window.opener === null'))
        self.assertEqual(page.url, initial_url, 'The article remains open after following a project link')
        popup.close()
        self.expected_navigation = None

    def test_project_previews_are_local_portable_and_link_to_their_own_repositories(self):
        for base, width in self.locations:
            for route, repository in PROJECTS:
                with self.subTest(location=base, width=width, project=route):
                    self.assertFalse((base / route / 'app').exists(), 'Project application payloads belong in their own repositories')
                    page = self.context_for(base, width).new_page()
                    page.goto((base / route / 'index.html').as_uri(), wait_until='load')
                    self.settle_images(page)
                    website = f"https://type-null.github.io/{repository.rsplit('/', 1)[1]}/"
                    portal = self.portal(page, width, repository, website)
                    self.open_intercepted_tab(page, portal.locator('.embed-repository'), repository)
                    page.close()

    def test_project_previews_and_keyboard_links_work_without_javascript(self):
        for route, repository in PROJECTS:
            with self.subTest(project=route):
                page = self.context_for(self.moved, 320, java_script_enabled=False).new_page()
                page.goto((self.moved / route / 'index.html').as_uri(), wait_until='load')
                self.settle_images(page)
                website = f"https://type-null.github.io/{repository.rsplit('/', 1)[1]}/"
                portal = self.portal(page, 320, repository, website)
                expect(portal.locator('[data-project-load]:visible')).to_have_count(0)
                self.open_intercepted_tab(page, portal.locator('.project-preview'), website)
                page.close()

    def test_configured_website_uses_preview_and_open_button_without_loading_it_early(self):
        for width, javascript in ((1440, True), (320, False)):
            with self.subTest(width=width, javascript=javascript):
                page = self.context_for(self.moved, width, java_script_enabled=javascript).new_page()
                page.goto(self.fixture_page.as_uri(), wait_until='load')
                self.settle_images(page)
                portal = self.portal(page, width, FIXTURE_REPOSITORY, FIXTURE_WEBSITE)
                expect(page.locator('.article-body')).to_contain_text('The article continues after the preview.')
                self.assertEqual(self.remote, [], 'A configured URL must remain only a link until activated')
                for selector, destination in (('.project-preview', FIXTURE_WEBSITE),
                                              ('.embed-open', FIXTURE_WEBSITE),
                                              ('.embed-repository', FIXTURE_REPOSITORY)):
                    self.open_intercepted_tab(page, portal.locator(selector), destination)
                page.close()

    def test_file_reader_explicitly_loads_ready_project_and_keeps_state_when_opening_a_tab(self):
        for width in (1440, 320):
            with self.subTest(width=width):
                before_requests = len(self.embedded)
                page = self.context_for(self.moved, width).new_page()
                page.goto(self.interactive_page.as_uri(), wait_until='load')
                self.settle_images(page)
                portal = self.portal(page, width, FIXTURE_REPOSITORY, INTERACTIVE_WEBSITE)
                self.assertEqual(len(self.embedded), before_requests)
                page.context.set_offline(True)
                portal.locator('[data-project-load]').click()
                expect(portal.locator('iframe')).to_have_count(0)
                expect(portal.locator('[data-project-status]')).to_contain_text('offline')
                page.context.set_offline(False)
                # The child intentionally waits for its data before responding
                # to the readiness ping. A load event alone is not success.
                self.embedded_responses[INTERACTIVE_WEBSITE] = (
                    200, PROJECT_APP.replace('let parentRequest;', 'window.holdReady = true; let parentRequest;'))
                portal.locator('[data-project-load]').click()
                frame_element = portal.locator('iframe.project-frame')
                expect(frame_element).to_have_count(1)
                child = frame_element.element_handle().content_frame()
                child.wait_for_url(INTERACTIVE_WEBSITE)
                child.wait_for_function("typeof announceReady === 'function' && !!parentRequest")
                self.assertEqual(len(self.embedded), before_requests + 1)
                expect(portal.locator('.project-preview')).to_be_visible()
                expect(frame_element).to_be_hidden()
                # Neither the right origin with the wrong sender nor the
                # right sender with the wrong origin may replace the preview.
                for source, origin in (('window', 'https://projects.example.test'),
                                       ('frame', 'https://unrelated.example.test')):
                    page.evaluate('''({source, origin}) => dispatchEvent(new MessageEvent('message', {
                        data: {type:'type-null:embed-ready'}, origin,
                        source: source === 'frame' ? document.querySelector('.project-frame').contentWindow : window
                    }))''', {'source': source, 'origin': origin})
                    expect(frame_element).to_be_hidden()
                    expect(portal.locator('.project-preview')).to_be_visible()
                child.evaluate('announceReady()')
                expect(frame_element).to_be_visible()
                expect(portal.locator('.project-preview')).to_be_hidden()
                child.locator('#note').fill('Keep this draft in the article')
                self.open_intercepted_tab(page, portal.locator('.embed-open'), INTERACTIVE_WEBSITE)
                expect(child.locator('#note')).to_have_value('Keep this draft in the article')
                page.evaluate("scrollTo({top:0, behavior:'instant'})")
                before, after = page.evaluate('''() => {
                    const before = scrollY;
                    dispatchEvent(new MessageEvent('message', {
                        data: {type:'type-null:focus-embed'}, origin:'https://unrelated.example.test',
                        source: document.querySelector('.project-frame').contentWindow
                    }));
                    return [before, scrollY];
                }''')
                self.assertEqual(after, before, 'An unrelated origin must not move the article')
                child.locator('#details').click()
                expect(child.get_by_role('dialog')).to_be_visible()
                page.wait_for_function('''() => {
                    const frame = document.querySelector('.project-frame').getBoundingClientRect();
                    const header = document.querySelector('.site-header').getBoundingClientRect();
                    return frame.top >= header.bottom && frame.top <= header.bottom + 30;
                }''')
                child.get_by_role('button', name='Close', exact=True).click()
                expect(child.get_by_role('dialog')).to_be_hidden()
                self.assertTrue(page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'))
                self.assertTrue(child.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'))
                close_preview = portal.locator('[data-project-close]')
                close_preview.scroll_into_view_if_needed()
                close_preview.click()
                expect(portal.locator('iframe')).to_have_count(0)
                expect(portal.locator('.project-preview')).to_be_visible()
                page.close()

    def test_hosted_article_loads_independent_project_when_preview_enters_view(self):
        self.embedded_responses[INTERACTIVE_WEBSITE] = (200, PROJECT_APP)
        page = self.context_for(self.moved, 390, hosted=True).new_page()
        page.goto(self.hosted_url + '/notes/interactive-project/index.html', wait_until='load')
        self.settle_images(page)
        # The authored fixture has introductory content before its project.
        # Visibility, rather than initial document load, starts the remote app.
        page.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
        expect(page.locator('iframe')).to_have_count(0)
        self.assertEqual(self.embedded, [])
        page.locator('.project-stage').scroll_into_view_if_needed()
        frame = page.locator('iframe.project-frame')
        expect(frame).to_be_visible()
        child = frame.element_handle().content_frame()
        expect(child.locator('#note')).to_have_value('Original note')
        self.assertEqual(self.embedded, [INTERACTIVE_WEBSITE])
        expect(page.locator('.project-preview')).to_be_hidden()
        page.close()

    def test_hosted_404_cannot_replace_saved_preview_and_can_be_retried(self):
        self.embedded_responses[INTERACTIVE_WEBSITE] = (
            404, '<!doctype html><title>Site not found</title><link rel="icon" href="data:,"><h1>No GitHub Pages site here.</h1>')
        page = self.context_for(self.moved, 390).new_page()
        page.clock.install()
        page.goto(self.interactive_page.as_uri(), wait_until='load')
        self.settle_images(page)
        page.locator('[data-project-load]').click()
        frame = page.locator('iframe.project-frame')
        expect(frame).to_have_count(1)
        child = frame.element_handle().content_frame()
        child.wait_for_url(INTERACTIVE_WEBSITE)
        child.wait_for_load_state('load')
        expect(child.locator('h1')).to_have_text('No GitHub Pages site here.')
        expect(frame).to_be_hidden()
        expect(page.locator('.project-preview')).to_be_visible()
        page.clock.run_for(8100)
        expect(page.locator('iframe')).to_have_count(0)
        expect(page.locator('[data-project-status]')).to_contain_text('unavailable')
        retry = page.get_by_role('button', name='Try again', exact=True)
        expect(retry).to_be_enabled()
        self.embedded_responses[INTERACTIVE_WEBSITE] = (200, PROJECT_APP)
        retry.click()
        expect(page.locator('iframe.project-frame')).to_be_visible()
        expect(page.locator('.project-preview')).to_be_hidden()
        page.close()

    def test_florida_research_placeholder_is_discoverable_without_invented_destinations(self):
        route = 'notes/florida-power-systems'
        for base, width in self.locations:
            with self.subTest(location=base, width=width):
                posts = json.loads((base / 'search-index.json').read_text())
                self.assertEqual(sum(post['url'] == f'/{route}/' for post in posts), 1)
                page = self.context_for(base, width).new_page()
                page.goto((base / 'index.html').as_uri(), wait_until='load')
                self.settle_images(page)
                # The information link is always visible, including while the
                # campaign carousel is showing a different project.
                link = page.locator(f'.home-notice a[href$="{route}/index.html"]')
                expect(link).to_have_count(1)
                link.click()
                self.settle_images(page)
                self.assertEqual(file_path(page.url), base / route / 'index.html')
                expect(page.locator('h1')).to_have_text('Florida power systems research')
                expect(page.locator('.article-cover img')).to_have_count(1)
                expect(page.locator('.article-body')).to_contain_text('Coming later:')
                expect(page.get_by_text('Project introduction forthcoming', exact=True)).to_be_visible()
                expect(page.locator('iframe, .embed--project, .post-actions a, .article-body a[href]')).to_have_count(0)
                self.assertNotIn('YOUR-VERIFIED', page.content())
                self.assertTrue(page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'))
                page.close()


if __name__ == '__main__':
    unittest.main()

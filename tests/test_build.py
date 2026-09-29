"""Regression tests for the authoring contract; no browser/network is needed."""
import contextlib
from html.parser import HTMLParser
import io
import json
import shutil
from pathlib import Path
import sys
import tempfile
import unittest
from urllib.parse import unquote, urljoin, urlsplit, urlunsplit

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from build import BuildError, build, discover, render_embed, safe_url


def emitted_route(route):
    """Expected file destination, independently of the build URL rewriter."""
    parsed = urlsplit(route)
    path = parsed.path + 'index.html' if parsed.path.endswith('/') else parsed.path
    return urlunsplit(('', '', path, parsed.query, parsed.fragment))


class References(HTMLParser):
    def __init__(self, tag, attribute):
        super().__init__()
        self.tag, self.attribute, self.values = tag, attribute, []

    def handle_starttag(self, tag, attrs):
        value = dict(attrs).get(self.attribute)
        if tag == self.tag and value is not None:
            self.values.append(value)


class BuildTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / 'repo'
        self.root.mkdir()
        self.output = self.root / '_site'
        templates = self.root / 'templates'
        templates.mkdir()
        shell = '<!doctype html><html><head><title>{{ page.title }}</title></head><body><nav>{% for topic in topics %}<a href="{{ topic.url }}">{{ topic.label }}</a>{% endfor %}</nav>'
        (templates / 'home.html').write_text(shell + '{% for post in posts %}<a href="{{ post.url }}">{{ post.title }}</a>{% endfor %}</body></html>')
        (templates / 'topic.html').write_text((templates / 'home.html').read_text())
        (templates / 'archive.html').write_text((templates / 'home.html').read_text())
        (templates / 'article.html').write_text(shell + '<img src="{{ post.cover }}" alt="">{{ post.html }}{{ post.embeds_html }}{% for item in post.gallery %}<img src="{{ item.src }}" alt="{{ item.alt }}">{% endfor %}</body></html>')
        (templates / 'timeline.html').write_text(shell + '{% for item in timeline.sets %}<img src="{{ item.thumbnail }}" alt="{{ item.name }}">{% endfor %}</body></html>')
        (templates / '404.html').write_text(shell + '</body></html>')
        assets = self.root / 'assets/images'
        assets.mkdir(parents=True)
        Image.new('RGB', (32, 32), '#ee3344').save(assets / 'type-null.png')
        (self.root / 'content').mkdir()

    def tearDown(self):
        self.temporary.cleanup()

    def post(self, relative='cards/first/index.md', front='', body='Hello, **world**.'):
        target = self.root / 'content' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('---\ntitle: First field note\ndate: 2025-04-05\n' + front + '\n---\n' + body, encoding='utf-8')
        return target

    def run_build(self, **kwargs):
        with contextlib.redirect_stdout(io.StringIO()):
            return build(self.root, self.output, check=True, **kwargs)

    def resolved_references(self, relative, tag='a', attribute='href'):
        parser = References(tag, attribute)
        parser.feed((self.output / relative).read_text())
        origin = 'https://output.test'
        result = []
        for value in parser.values:
            resolved = urlsplit(urljoin(origin + '/' + relative, value))
            if resolved.netloc == 'output.test':
                result.append(urlunsplit(('', '', unquote(resolved.path), resolved.query, resolved.fragment)))
        return result

    def test_minimal_tutorial_with_actual_templates_and_static_output(self):
        repository = Path(__file__).resolve().parents[1]
        shutil.copytree(repository / 'templates', self.root / 'templates', dirs_exist_ok=True)
        shutil.copytree(repository / 'assets/fonts', self.root / 'assets/fonts')
        for relative in ('assets/css/site.css', 'assets/js/site.js',
                         'assets/css/home-sections.css', 'assets/css/home-motion.css',
                         'assets/js/home-motion.js',
                         'assets/images/logo_arceus_en.png', 'assets/images/favicon.svg'):
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(repository / relative, target)
        tutorial = (repository / 'docs/WRITING.md').read_text()
        example = tutorial.split('```md\n', 1)[1].split('```', 1)[0]
        source = self.root / 'content/notes/my-first-post/index.md'
        source.parent.mkdir(parents=True)
        source.write_text(example)
        self.run_build()
        route = '/notes/my-first-post/'
        self.assertIn('<h1 class="m-ttl-top">My first post</h1>', (self.output / 'notes/my-first-post/index.html').read_text())
        for relative in ('index.html', 'posts/index.html', 'notes/index.html'):
            self.assertIn(emitted_route(route), self.resolved_references(relative), relative)
        for relative in ('search-index.json', 'feed.xml', 'sitemap.xml'):
            self.assertIn(route, (self.output / relative).read_text(), relative)
        self.assertTrue((self.output / '.nojekyll').is_file())
        self.assertIn('page-home--plain', (self.output / 'index.html').read_text())
        self.assertFalse(list(self.output.rglob('*.py')))
        self.assertFalse(list(self.output.rglob('*.md')))
        self.assertFalse((self.output / '.venv').exists())
        (self.root / 'content/notes').rename(self.root / 'content/travel')
        self.run_build()
        self.assertTrue((self.output / 'travel/my-first-post/index.html').is_file())
        self.assertFalse((self.output / 'notes').exists())
        self.assertIn('/travel/index.html', self.resolved_references('index.html'))

    def test_folder_discovery_rename_and_generated_files(self):
        self.post()
        (self.root / 'content/cards/_topic.yml').write_text('label: Trading cards\norder: 2\ncolor: "#ffee00"\n')
        result = self.run_build()
        self.assertEqual((result['posts'], result['topics']), (1, 1))
        self.assertIn('Trading cards', (self.output / 'index.html').read_text())
        self.assertTrue((self.output / 'cards/first/index.html').exists())
        self.assertTrue((self.output / 'feed.xml').exists())
        self.assertTrue((self.output / 'sitemap.xml').exists())
        self.assertTrue((self.output / '.nojekyll').exists())
        self.assertFalse((self.output / 'content').exists())
        (self.root / 'content/cards').rename(self.root / 'content/collection')
        self.run_build()
        self.assertFalse((self.output / 'cards').exists())
        self.assertTrue((self.output / 'collection/first/index.html').exists())
        self.assertIn('/collection/index.html', self.resolved_references('index.html'))

    def test_drafts_hidden_folders_and_empty_topics(self):
        self.post(front='draft: true')
        self.post('_private/hidden/index.md')
        self.post('notes/_draft.md')
        self.run_build()
        self.assertEqual(json.loads((self.output / 'search-index.json').read_text()), [])
        self.assertTrue((self.output / 'cards/index.html').exists())
        self.assertFalse((self.output / '_private').exists())

    def test_unlisted_posts_keep_direct_route_but_leave_all_discovery_surfaces(self):
        self.post()
        source = self.post('cards/resume/index.md', front='unlisted: true\nfeatured: true\npermalink: /resume/2025/resume.html', body='Complete historical resume content.')
        templates = self.root / 'templates'
        with (templates / 'home.html').open('a') as file:
            file.write('{% for post in featured_posts %}<a href="{{ post.url }}">Featured</a>{% endfor %}{% for topic in topics %}<b>{{ topic.count }}</b>{% endfor %}')
        result = self.run_build()
        self.assertEqual((result['posts'], result['listed_posts'], result['unlisted_posts']), (2, 1, 1))
        route = '/resume/2025/resume.html'
        self.assertIn('Complete historical resume content.', (self.output / route.lstrip('/')).read_text())
        for relative in ('index.html', 'posts/index.html', 'cards/index.html'):
            with self.subTest(relative=relative):
                self.assertNotIn(route, self.resolved_references(relative))
        for relative in ('search-index.json', 'feed.xml', 'sitemap.xml'):
            with self.subTest(relative=relative):
                self.assertNotIn(route, (self.output / relative).read_text())
        self.assertIn('<b>1</b>', (self.output / 'index.html').read_text())
        source.write_text(source.read_text().replace('unlisted: true', 'unlisted: false'))
        result = self.run_build()
        self.assertEqual((result['listed_posts'], result['unlisted_posts']), (2, 0))
        for relative in ('index.html', 'posts/index.html', 'cards/index.html'):
            self.assertIn(route, self.resolved_references(relative))
        for relative in ('search-index.json', 'feed.xml', 'sitemap.xml'):
            self.assertIn(route, (self.output / relative).read_text())
        self.assertIn('<b>2</b>', (self.output / 'index.html').read_text())

    def test_unlisted_requires_a_boolean(self):
        self.post(front='unlisted: "true"')
        with self.assertRaisesRegex(BuildError, 'unlisted must be true or false'):
            self.run_build()

    def test_news_archive_lists_every_listed_post_and_is_in_sitemap(self):
        for index in range(8):
            self.post(f'cards/story-{index}/index.md')
        self.post('notes/private/index.md', front='unlisted: true')
        self.run_build()
        archive = (self.output / 'posts/index.html').read_text()
        self.assertIn('<title>NEWS</title>', archive)
        for index in range(8):
            self.assertIn(f'/cards/story-{index}/index.html', self.resolved_references('posts/index.html'))
        self.assertNotIn('/notes/private/index.html', self.resolved_references('posts/index.html'))
        self.assertIn('https://type-null.github.io/posts/', (self.output / 'sitemap.xml').read_text())
        # The engine supplies the full collection; the homepage template chooses
        # its six newest entries without constraining the archive context.
        self.assertIn('/cards/story-0/index.html', self.resolved_references('index.html'))

    def test_news_archive_route_is_reserved(self):
        self.post('posts/a-story/index.md')
        with self.assertRaisesRegex(BuildError, 'reserved output URL: /posts/'):
            self.run_build()
        (self.root / 'content/posts/a-story/index.md').unlink()
        (self.root / 'content/posts/a-story').rmdir()
        (self.root / 'content/posts').rmdir()
        self.post(front='permalink: /posts/')
        with self.assertRaisesRegex(BuildError, 'reserved output URL: /posts/'):
            self.run_build()

    def test_source_directory_routes_are_reserved_before_publication(self):
        for directory in ('content', 'templates', 'scripts', 'tests', 'docs', 'legacy', 'archive', 'examples'):
            with self.subTest(directory=directory):
                self.post(front=f'permalink: /{directory}/article/')
                with self.assertRaisesRegex(BuildError, 'reserved output URL'):
                    discover(self.root)

    def test_root_sync_rebuild_removes_renamed_routes_without_reingesting_output(self):
        source = self.post(body='![Photo](photo.png)')
        Image.new('RGB', (8, 8)).save(source.parent / 'photo.png')
        removed = self.post('cards/removed/index.md', front='permalink: /sports/2021/03/210307_so.html', body='![Old photo](old.png)')
        Image.new('RGB', (8, 8)).save(removed.parent / 'old.png')
        archived = self.root / 'archive/legacy-pages/sports/2021/03/210307_so.html'
        archived.parent.mkdir(parents=True)
        archived.write_text('Old article must never return to publication')
        tool = self.root / 'legacy/card/toolkit.html'
        tool.parent.mkdir(parents=True)
        tool.write_text('<p>An author-maintained standalone tool</p>')
        stylesheet = self.root / 'assets/css/base.css'
        stylesheet.parent.mkdir(parents=True)
        stylesheet.write_text('body {background:url("/assets/images/type-null.png")}')
        home = self.root / 'templates/home.html'
        original_home = home.read_text()
        home.write_text(original_home + '<link rel="stylesheet" href="/assets/css/base.css">')
        original_asset = (self.root / 'assets/images/type-null.png').read_bytes()
        original_css = stylesheet.read_bytes()
        self.run_build(sync=True)
        self.assertEqual((self.root / 'index.html').read_bytes(), (self.output / 'index.html').read_bytes())
        generated_css = [path for path in json.loads((self.root / '.site-root.json').read_text())['files'] if path.startswith('assets/generated/css/')]
        self.assertTrue(generated_css)
        self.assertTrue((self.root / 'cards/first/photo.png').is_file())
        self.assertTrue((self.root / 'sports/2021/03/old.png').is_file())
        # A neighboring author file is not owned by the mirror and must survive.
        (self.root / 'cards/keep.txt').write_text('Author-owned neighbor')
        (self.root / 'content/cards').rename(self.root / 'content/collection')
        shutil.rmtree(self.root / 'content/collection/removed')
        home.write_text(original_home)
        self.run_build(sync=True)
        for destination in (self.root, self.output):
            self.assertFalse((destination / 'cards/first').exists())
            self.assertFalse((destination / 'sports/2021/03/210307_so.html').exists())
            self.assertFalse((destination / 'sports/2021/03/old.png').exists())
            self.assertTrue((destination / 'collection/first/index.html').is_file())
            self.assertTrue((destination / 'collection/first/photo.png').is_file())
            self.assertIn('standalone tool', (destination / 'card/toolkit.html').read_text())
            self.assertTrue(all(not (destination / path).exists() for path in generated_css))
        self.assertEqual((self.root / 'cards/keep.txt').read_text(), 'Author-owned neighbor')
        self.assertEqual((self.root / 'index.html').read_bytes(), (self.output / 'index.html').read_bytes())
        self.assertEqual((self.root / 'assets/images/type-null.png').read_bytes(), original_asset)
        self.assertEqual(stylesheet.read_bytes(), original_css)
        self.assertEqual(archived.read_text(), 'Old article must never return to publication')
        self.assertTrue((self.output / 'search-index.js').read_text().startswith('window.TYPE_NULL_SEARCH_INDEX = '))

    def test_rich_metadata_and_toc_share_markdown_heading_ids(self):
        self.post(front='''template: review
subtitle: A closer look
eyebrow: Field test
author: A guest author
updated: 2025-04-08
lang: zh-Hans
cover_alt: Two card packs
cover_caption: From the archive
toc: true
seo:
  title: A search title
  description: A search description
  image: social.png
links:
  - label: Read details
    url: details.pdf
    style: secondary
facts:
  - label: Number of cards
    value: 60
''', body='## Setup\n\nSome notes.\n\n## Setup\n\nMore notes.')
        _, posts = discover(self.root)
        post = posts[0]
        self.assertEqual(post['updated'], '2025-04-08')
        self.assertEqual(post['author'], 'A guest author')
        self.assertEqual(post['lang'], 'zh-Hans')
        self.assertEqual(post['facts'], [{'label': 'Number of cards', 'value': '60'}])
        self.assertEqual(post['links'][0]['url'], '/cards/first/details.pdf')
        self.assertEqual(post['seo']['image'], '/cards/first/social.png')
        for anchor in ('setup', 'setup_1'):
            self.assertIn(f'id="{anchor}"', post['html'])
            self.assertIn(f'href="#{anchor}"', post['toc_html'])

    def test_invalid_rich_metadata_reports_source(self):
        for front in ('updated: 2020-01-01', 'lang: "not a language"', 'toc: "true"', 'author: 42', 'seo: []', 'seo:\n  image: javascript:bad', 'seo:\n  title: []', 'facts:\n  - label: Empty', 'links:\n  - label: Invalid\n    url: /\n    style: flashy', 'links:\n  - label: Bad\n    url: data:bad', 'related: not-a-list'):
            with self.subTest(front=front):
                source = self.post(front=front)
                with self.assertRaises(BuildError) as raised:
                    discover(self.root)
                self.assertIn(str(source), str(raised.exception))

    def test_cover_montage_and_campaign_images_normalize_and_validate_files(self):
        source = self.post(front='cover_images: [pack-one.png, /assets/images/type-null.png]\nhero_image: desktop.png\nhero_mobile_image: mobile.png')
        for filename in ('pack-one.png', 'desktop.png', 'mobile.png'):
            Image.new('RGB', (16, 16)).save(source.parent / filename)
        _, posts = discover(self.root)
        post = posts[0]
        self.assertEqual(post['cover_images'], ['/cards/first/pack-one.png', '/assets/images/type-null.png'])
        self.assertEqual(post['hero_image'], '/cards/first/desktop.png')
        self.assertEqual(post['hero_mobile_image'], '/cards/first/mobile.png')
        with (self.root / 'templates/article.html').open('a') as file:
            file.write('{% for image in page.cover_images %}<img src="{{ image }}" alt="">{% endfor %}<picture><source media="(max-width: 750px)" srcset="{{ page.hero_mobile_image }}"><img src="{{ page.hero_image }}" alt=""></picture>')
        self.run_build()
        (source.parent / 'mobile.png').unlink()
        with self.assertRaisesRegex(BuildError, r'missing local link (?:/cards/first/)?mobile\.png'):
            self.run_build()

    def test_cover_montage_and_campaign_metadata_rejects_invalid_values(self):
        cases = ('cover_images: photo.png', 'cover_images: [1]', 'cover_images: [""]', 'cover_images: [a,b,c,d,e,f,g]', 'cover_images: [javascript:bad]', 'hero_image: 42', 'hero_image: javascript:bad', 'hero_mobile_image: data:bad')
        for front in cases:
            with self.subTest(front=front):
                self.post(front=front)
                with self.assertRaises(BuildError):
                    discover(self.root)
        self.post()
        _, posts = discover(self.root)
        self.assertEqual(posts[0]['cover_images'], [])
        self.assertEqual(posts[0]['hero_image'], '')
        self.assertEqual(posts[0]['hero_mobile_image'], '')

    def test_offline_mode_validates_optional_campaign_materials(self):
        (self.root / 'site.yml').write_text('offline: true\n')
        for front in ('cover_images: [https://example.com/art.png]', 'hero_image: https://example.com/desktop.png', 'hero_mobile_image: https://example.com/mobile.png'):
            with self.subTest(front=front):
                self.post(front=front)
                with self.assertRaisesRegex(BuildError, 'offline mode: save media locally'):
                    build(self.root, self.output, check=False)

    def test_explicit_related_links_require_listed_published_targets(self):
        self.post(front='related: [/cards/second/]')
        second = self.post('cards/second/index.md')
        _, posts = discover(self.root)
        first = next(post for post in posts if post['url'] == '/cards/first/')
        self.assertEqual([post['url'] for post in first['related_posts']], ['/cards/second/'])
        self.post('cards/second/index.md', front='unlisted: true')
        with self.assertRaisesRegex(BuildError, 'another listed, published post'):
            discover(self.root)
        second.unlink()
        with self.assertRaisesRegex(BuildError, 'another listed, published post'):
            discover(self.root)

    def test_automatic_related_posts_are_relevant_bounded_and_listed(self):
        self.post(front='tags: [collection]')
        for index in range(4):
            self.post(f'cards/note-{index}/index.md')
        self.post('notes/shared/index.md', front='tags: [collection]')
        self.post('cards/private/index.md', front='unlisted: true\ntags: [collection]')
        self.post('notes/unrelated/index.md')
        _, posts = discover(self.root)
        first = next(post for post in posts if post['url'] == '/cards/first/')
        related = first['related_posts']
        self.assertEqual(len(related), 3)
        self.assertEqual(related[0]['url'], '/notes/shared/')
        self.assertTrue(all(not post['unlisted'] and post['url'] != first['url'] for post in related))
        self.assertNotIn('/notes/unrelated/', [post['url'] for post in related])

    def test_dedicated_templates_and_seo_defaults(self):
        self.post(front='template: landing\nseo:\n  title: SEO landing title\n  description: SEO details\n  image: https://images.example.com/cover.png')
        self.post('cards/review/index.md', front='template: review')
        template = '<h1>{{ page.title }}</h1><p>{{ page.template }}|{{ page.seo_title }}|{{ page.seo_description }}|{{ page.seo_image_url }}|{{ page.lang }}</p>'
        (self.root / 'templates/landing.html').write_text(template)
        (self.root / 'templates/review.html').write_text(template)
        self.run_build()
        self.assertIn('landing|SEO landing title|SEO details|https://images.example.com/cover.png|en', (self.output / 'cards/first/index.html').read_text())
        self.assertIn('review|First field note|', (self.output / 'cards/review/index.html').read_text())
        (self.root / 'templates/landing.html').unlink()
        self.run_build()
        self.assertIn('Hello, <strong>world</strong>', (self.output / 'cards/first/index.html').read_text())

    def test_offline_mode_rejects_remote_media_but_allows_outbound_links(self):
        (self.root / 'site.yml').write_text('offline: true\n')
        cases = [('', '![Remote](https://example.com/image.png)'), ('cover: https://example.com/cover.png', 'Hello'), ('embeds:\n  - type: youtube\n    url: https://youtu.be/dQw4w9WgXcQ\n    title: Video', 'Hello'), ('embeds:\n  - type: website\n    url: https://example.com/\n    title: Website', 'Hello')]
        for front, body in cases:
            with self.subTest(front=front, body=body):
                self.post(front=front, body=body)
                with self.assertRaisesRegex(BuildError, 'offline mode: save media locally'):
                    build(self.root, self.output, check=False)
        self.post(body='[An outbound reference](https://example.com/)')
        self.run_build()
        self.assertIn('href="https://example.com/"', (self.output / 'cards/first/index.html').read_text())

    def test_offline_mode_rejects_template_runtime_dependencies(self):
        (self.root / 'site.yml').write_text('offline: true\n')
        self.post()
        with (self.root / 'templates/home.html').open('a') as file:
            file.write('<script src="https://cdn.example.com/runtime.js"></script>')
        with self.assertRaisesRegex(BuildError, 'offline mode: save media locally'):
            build(self.root, self.output, check=False)
        (self.root / 'site.yml').write_text('offline: "true"\n')
        with self.assertRaisesRegex(BuildError, 'site.offline must be true or false'):
            self.run_build()

    def test_offline_mode_follows_only_referenced_stylesheet_imports(self):
        (self.root / 'site.yml').write_text('offline: true\n')
        self.post()
        css = self.root / 'assets/css'
        css.mkdir()
        (css / 'main.css').write_text('@import "nested.css";')
        (css / 'nested.css').write_text('body {background:url(https://example.com/pattern.png)}')
        (css / 'unused.css').write_text('@import "https://unused.example.com/archive.css";')
        with (self.root / 'templates/home.html').open('a') as file:
            file.write('<link rel="stylesheet" href="/assets/css/main.css">')
        with self.assertRaisesRegex(BuildError, 'offline mode: save media locally'):
            build(self.root, self.output, check=False)
        (css / 'nested.css').write_text('body {color:blue}')
        self.run_build()

    def test_relative_images_unicode_filenames_and_single_file_posts(self):
        source = self.post('My Travels/京都/index.md', front='cover: photo—one.png', body='![A place](photo—one.png)')
        Image.new('RGB', (8, 8)).save(source.parent / 'photo—one.png')
        self.post('notes/short.md')
        self.run_build()
        page = self.output / 'my-travels/京都/index.html'
        self.assertTrue(page.exists())
        self.assertTrue((page.parent / 'photo—one.png').exists())
        self.assertIn('loading="lazy"', page.read_text())
        self.assertTrue((self.output / 'notes/short/index.html').exists())

    def test_markdown_links_resolve_published_routes(self):
        self.post(body='[Next](../second/index.md#hello)')
        self.post('cards/second/index.md', front='permalink: /cards/old.html', body='## Hello')
        self.run_build()
        self.assertIn('/cards/old.html#hello', self.resolved_references('cards/first/index.html'))

    def test_legacy_urls_preserved_and_generated_article_replaces_one(self):
        for route in ('card/toolkit.html', 'sports/2025/trading_suits.html', 'sports/2025/betting_game.html', 'resume/2025/resume.html', 'florida/map.html'):
            path = self.root / route
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('<script>window.legacy = true;</script>')
        old_article = self.root / 'sports/2021/03/210307_so.html'
        old_article.parent.mkdir(parents=True)
        old_article.write_text('old broken article')
        self.post(front='permalink: /sports/2021/03/210307_so.html')
        self.run_build()
        self.assertIn('<script>', (self.output / 'card/toolkit.html').read_text())
        self.assertIn('Hello, <strong>world</strong>', (self.output / old_article.relative_to(self.root)).read_text())

    def test_embeds_render_placed_and_append_unplaced_but_leave_code(self):
        self.post(front='embeds:\n  - type: youtube\n    url: https://youtu.be/dQw4w9WgXcQ\n    title: A video\n  - type: website\n    url: https://example.com/\n    title: A website', body='Before\n\n[[embed:1]]\n\nAfter\n\n```text\n[[embed:2]]\n```')
        self.run_build()
        content = (self.output / 'cards/first/index.html').read_text()
        self.assertEqual(content.count('<iframe '), 2)
        self.assertLess(content.index('youtube-nocookie'), content.index('After'))
        self.assertIn('[[embed:2]]', content)
        self.assertIn('sandbox="allow-scripts allow-forms allow-popups"', content)
        self.assertIn('rel="noopener noreferrer"', content)

    def test_video_pdf_gallery_and_title_escaping(self):
        source = self.post(front='cover: picture.png\nembeds:\n  - type: video\n    url: clip.mp4\n    title: Video\n    poster: picture.png\n  - type: pdf\n    url: paper.pdf\n    title: Paper\ngallery:\n  - src: picture.png\n    alt: \'An "image"\'', body='A gallery.')
        Image.new('RGB', (8, 8)).save(source.parent / 'picture.png')
        (source.parent / 'clip.mp4').write_bytes(b'video fixture')
        (source.parent / 'paper.pdf').write_bytes(b'%PDF fixture')
        self.run_build()
        text = (self.output / 'cards/first/index.html').read_text()
        self.assertIn('<video controls preload="metadata"', text)
        self.assertIn('/cards/first/paper.pdf', self.resolved_references('cards/first/index.html'))
        self.assertIn('/cards/first/paper.pdf', self.resolved_references('cards/first/index.html', 'iframe', 'src'))
        self.assertIn('An &#34;image&#34;', text)

    def test_invalid_metadata_fail_with_source(self):
        cases = ['date: impossible', 'template: mystery', 'draft: "false"', 'tags: not-a-list', 'cover: javascript:alert(1)', 'embeds: invalid', 'gallery:\n  - src: photo.png']
        for front in cases:
            with self.subTest(front=front):
                source = self.post(front=front)
                with self.assertRaises(BuildError) as raised:
                    self.run_build()
                self.assertIn(str(source), str(raised.exception))

    def test_duplicate_routes_and_reserved_routes(self):
        self.post()
        self.post('cards/second.md', front='permalink: /cards/first/')
        with self.assertRaisesRegex(BuildError, 'Duplicate'):
            self.run_build()
        for url in ('/', '/404.html', '/assets/hi.html', '/../oops/', '/%2e%2e/oops/'):
            with self.subTest(url=url):
                self.post('cards/second.md', front=f'permalink: {url}')
                with self.assertRaises(BuildError):
                    self.run_build()

    def test_topic_slug_collisions(self):
        self.post('My topic/a.md')
        self.post('my-topic/b.md')
        with self.assertRaisesRegex(BuildError, 'Duplicate'):
            self.run_build()

    def test_missing_images_and_bad_anchors_are_checked(self):
        self.post(body='![missing](absent.png)')
        with self.assertRaisesRegex(BuildError, 'missing local link'):
            self.run_build()
        self.post(body='[missing](#no-such-heading)')
        with self.assertRaisesRegex(BuildError, 'missing anchor'):
            self.run_build()

    def test_unsafe_markup_and_urls_are_rejected(self):
        for body in ('<script>alert(1)</script>', '<img src="x" onerror="alert(1)">', '[bad](javascript:alert%281%29)', '<iframe src="https://example.com"></iframe>'):
            with self.subTest(body=body):
                self.post(body=body)
                with self.assertRaises(BuildError):
                    self.run_build()
        for url in ('data:image/svg+xml,bad', 'javascript:alert(1)', '//evil.com', '../private.png', '/%2e%2e/private', '/image%0A.png', r'foo\bar'):
            with self.subTest(url=url), self.assertRaises(BuildError):
                safe_url(url)

    def test_bad_embed_reference_and_youtube_host_are_rejected(self):
        self.post(body='[[embed:1]]')
        with self.assertRaisesRegex(BuildError, 'Embed reference'):
            self.run_build()
        self.post(front='embeds:\n  - type: youtube\n    url: https://youtube.com.evil.example/watch?v=dQw4w9WgXcQ\n    title: Unsafe')
        with self.assertRaisesRegex(BuildError, 'youtube embed'):
            self.run_build()

    def test_first_party_tools_keep_storage_origin(self):
        self.post(front='embeds:\n  - type: website\n    url: /card/toolkit.html\n    title: Local tool')
        legacy = self.root / 'card/toolkit.html'
        legacy.parent.mkdir()
        legacy.write_text('<p>A trusted local app</p>')
        self.run_build()
        page = (self.output / 'cards/first/index.html').read_text()
        self.assertIn('/card/toolkit.html', self.resolved_references('cards/first/index.html', 'iframe', 'src'))
        self.assertNotIn('sandbox=', page)

    def test_article_tool_frame_and_new_tab_link_share_a_portable_destination(self):
        class EmbedParts(HTMLParser):
            def __init__(self):
                super().__init__()
                self.frames, self.links = [], []

            def handle_starttag(self, tag, attributes):
                attrs = dict(attributes)
                if tag == 'iframe':
                    self.frames.append(attrs)
                if tag == 'a' and 'embed-open' in attrs.get('class', '').split():
                    self.links.append(attrs)

        title = 'Odds "calculator" & <examples>'
        source = self.post(
            front='embeds:\n  - type: website\n    url: "tools/概率 calculator.html?copies=2&deck=60#result"\n'
                  f'    title: {json.dumps(title)}',
            body='Before the calculator.\n\n[[embed:1]]\n\nAfter the calculator.',
        )
        tool = source.parent / 'tools/概率 calculator.html'
        tool.parent.mkdir()
        tool.write_text('<!doctype html><title>Calculator</title><p id="result">Local tool</p>')
        self.run_build()
        content = (self.output / 'cards/first/index.html').read_text()
        parsed = EmbedParts()
        parsed.feed(content)
        self.assertEqual(len(parsed.frames), 1)
        self.assertEqual(len(parsed.links), 1)
        frame, link = parsed.frames[0], parsed.links[0]
        self.assertEqual(frame['src'], link['href'])
        self.assertEqual(link['target'], '_blank')
        self.assertTrue({'noopener', 'noreferrer'} <= set(link['rel'].split()))
        self.assertEqual(frame['title'], title)
        self.assertEqual(link['aria-label'], f'Open {title} in a new tab')
        expected = '/cards/first/tools/概率 calculator.html?copies=2&deck=60#result'
        self.assertIn(expected, self.resolved_references('cards/first/index.html'))
        self.assertTrue((self.output / 'cards/first/tools/概率 calculator.html').is_file())
        self.assertLess(content.index('Before the calculator.'), content.index('<figure'))
        self.assertLess(content.index('</figure>'), content.index('After the calculator.'))
        self.assertIn('Open in new tab', content)
        self.assertNotIn('embed-repository', content)

    def test_local_website_embed_has_accessible_github_source_button_in_offline_build(self):
        class EmbedParts(HTMLParser):
            def __init__(self):
                super().__init__()
                self.links, self.frames, self.icons = [], [], []

            def handle_starttag(self, tag, attributes):
                attrs = dict(attributes)
                if tag == 'a' and attrs.get('class') == 'embed-repository':
                    self.links.append(attrs)
                elif tag == 'iframe':
                    self.frames.append(attrs)
                elif tag == 'svg':
                    self.icons.append(attrs)

        (self.root / 'site.yml').write_text('offline: true\n')
        title = 'Calendar "demo" & <source>'
        repository = 'https://github.com/type-null/PTCG-calendar'
        source = self.post(front='embeds:\n  - type: website\n    url: app/index.html\n'
                           f'    title: {json.dumps(title)}\n    repository: {repository}',
                           body='Use the calendar.\n\n[[embed:1]]')
        (source.parent / 'app').mkdir()
        (source.parent / 'app/index.html').write_text('<!doctype html><title>Local calendar</title>')
        self.run_build()
        page = (self.output / 'cards/first/index.html').read_text()
        parsed = EmbedParts()
        parsed.feed(page)
        self.assertEqual(len(parsed.links), 1)
        link = parsed.links[0]
        self.assertEqual(link['href'], repository)
        self.assertEqual(link['target'], '_blank')
        self.assertEqual(set(link['rel'].split()), {'noopener', 'noreferrer'})
        self.assertEqual(link['aria-label'], f'View {title} source on GitHub (opens in a new tab)')
        self.assertEqual(link['title'], link['aria-label'])
        self.assertEqual(len(parsed.icons), 1)
        self.assertEqual(parsed.icons[0]['aria-hidden'], 'true')
        self.assertEqual(parsed.icons[0]['focusable'], 'false')
        self.assertEqual(len(parsed.frames), 1)
        self.assertEqual(parsed.frames[0]['src'], 'app/index.html')
        self.assertEqual(parsed.frames[0]['title'], title)
        self.assertNotIn('sandbox', parsed.frames[0])
        self.assertIn('<span class="embed-actions">', page)
        self.assertIn('Open in new tab', page)

    def test_embed_repository_accepts_only_explicit_github_repository_urls(self):
        post = {'url': '/cards/demo/'}
        embed = {'type': 'website', 'url': 'app/index.html', 'title': 'Project demo'}
        valid = ('https://github.com/type-null/PTCG-calendar',
                 'https://github.com/type-null/PTCG-database/',
                 'https://github.com/a/.github')
        for repository in valid:
            with self.subTest(repository=repository):
                rendered = render_embed({**embed, 'repository': repository}, post)
                self.assertIn(f'href="{repository}"', rendered)
        invalid = (None, False, 42, '', '   ', 'javascript:alert(1)', '/repo',
                   'http://github.com/type-null/PTCG-calendar',
                   'https://github.com.evil.example/type-null/PTCG-calendar',
                   'https://github.com@evil.example/type-null/PTCG-calendar',
                   'https://user@github.com/type-null/PTCG-calendar',
                   'https://github.com:443/type-null/PTCG-calendar',
                   'https://github.com/type-null', 'https://github.com/type-null/repo/tree/main',
                   'https://github.com/type-null/repo?redirect=other',
                   'https://github.com/type-null/repo#readme',
                   'https://github.com/type-null/..', 'https://github.com/type-null/%2e%2e',
                   'https://github.com/type-null/repo\" onmouseover=\"bad',
                   'https://github.com/type-null/repo\\other', 'https://[')
        for repository in invalid:
            with self.subTest(repository=repository), self.assertRaisesRegex(BuildError, 'embed repository'):
                render_embed({**embed, 'repository': repository}, post)
        with self.assertRaisesRegex(BuildError, 'only for website'):
            render_embed({**embed, 'type': 'pdf', 'repository': valid[0]}, post)

    def test_github_source_link_does_not_allow_remote_frame_in_offline_mode(self):
        (self.root / 'site.yml').write_text('offline: true\n')
        self.post(front='embeds:\n  - type: website\n    url: https://type-null.github.io/PTCG-calendar/\n'
                  '    title: Remote app\n    repository: https://github.com/type-null/PTCG-calendar')
        with self.assertRaisesRegex(BuildError, 'offline mode: save media locally'):
            self.run_build()

    def test_project_card_uses_local_screenshot_and_github_until_site_is_published(self):
        (self.root / 'site.yml').write_text('offline: true\n')
        repository = 'https://github.com/type-null/PTCG-calendar'
        source = self.post(front='embeds:\n  - type: project\n    image: screenshot.png\n'
                           f'    title: Calendar\n    repository: {repository}',
                           body='Introduction.\n\n[[embed:1]]\n\nDetails.')
        Image.new('RGB', (1000, 480), '#d8e9ef').save(source.parent / 'screenshot.png')
        self.run_build()
        content = (self.output / 'cards/first/index.html').read_text()
        self.assertIn('class="project-preview"', content)
        self.assertEqual(content.count(f'href="{repository}"'), 2)
        self.assertIn('Calendar on GitHub in a new tab', content)
        self.assertIn('embed-repository', content)
        self.assertNotIn('embed-open', content)
        self.assertNotIn('<iframe', content)
        self.assertIn('/cards/first/screenshot.png', self.resolved_references('cards/first/index.html', 'img', 'src'))
        self.assertLess(content.index('Introduction.'), content.index('<figure'))
        self.assertLess(content.index('</figure>'), content.index('Details.'))

    def test_project_live_url_and_source_are_distinct_safe_links_in_offline_output(self):
        (self.root / 'site.yml').write_text('offline: true\n')
        title = 'A "research" site & <details>'
        website = 'https://type-null.github.io/research/?view=map&year=2026#results'
        self.post(front='embeds:\n  - type: project\n    image: /assets/images/type-null.png\n'
                  f'    title: {json.dumps(title)}\n    repository: https://github.com/type-null/research\n'
                  f'    url: {website}')
        self.run_build()
        content = (self.output / 'cards/first/index.html').read_text()
        links = References('a', 'href')
        links.feed(content)
        self.assertEqual(links.values.count(website), 2)
        self.assertIn('https://github.com/type-null/research', links.values)
        self.assertEqual(content.count('target="_blank" rel="noopener noreferrer"'), 3)
        self.assertIn('Open website', content)
        self.assertIn('&lt;details&gt;', content)
        self.assertNotIn('<details>', content)
        self.assertNotIn('<iframe', content)

    def test_project_card_rejects_invalid_destinations_and_remote_screenshots(self):
        post = {'url': '/notes/research/'}
        embed = {'type': 'project', 'image': 'cover.png', 'title': 'Research',
                 'repository': 'https://github.com/type-null/research'}
        for url in (None, False, '', 'javascript:alert(1)', 'http://example.com',
                    '//example.com', '/local.html', 'https://user:secret@example.com',
                    'https://[', 'https://example.com:bad', 'https://bad host.example/'):
            with self.subTest(url=url), self.assertRaisesRegex(BuildError, 'project URL'):
                render_embed({**embed, 'url': url}, post)
        for repository in (None, '', 'https://example.com/owner/repo', 'https://github.com.evil.test/a/b'):
            with self.subTest(repository=repository), self.assertRaisesRegex(BuildError, 'embed repository'):
                render_embed({**embed, 'repository': repository}, post)
        for image in (None, '', 'https://example.com/cover.png', '//example.com/cover.png', '../cover.png'):
            with self.subTest(image=image), self.assertRaisesRegex(BuildError, 'project image'):
                render_embed({**embed, 'image': image}, post)

    def test_project_missing_local_screenshot_fails_checked_build(self):
        self.post(front='embeds:\n  - type: project\n    title: Research\n    image: missing.png\n'
                  '    repository: https://github.com/type-null/research')
        with self.assertRaisesRegex(BuildError, 'missing.png'):
            self.run_build()

    def test_interactive_project_keeps_offline_preview_and_defers_remote_frame(self):
        (self.root / 'site.yml').write_text('offline: true\n')
        self.post(front='embeds:\n  - type: project\n    title: Research\n'
                  '    image: /assets/images/type-null.png\n'
                  '    repository: https://github.com/type-null/research\n'
                  '    url: https://type-null.github.io/research/\n    interactive: true')
        self.run_build()
        page = (self.output / 'cards/first/index.html').read_text()
        self.assertIn('data-project-url="https://type-null.github.io/research/"', page)
        self.assertIn('data-project-load hidden', page)
        self.assertIn('data-project-close hidden', page)
        self.assertIn('data-project-status role="status"', page)
        self.assertEqual(page.count('class="project-preview"'), 1)
        self.assertNotIn('<iframe', page)

    def test_interactive_project_requires_boolean_and_destination(self):
        post = {'url': '/notes/research/'}
        embed = {'type': 'project', 'image': 'cover.png', 'title': 'Research',
                 'repository': 'https://github.com/type-null/research'}
        for value in ('true', 1, None):
            with self.subTest(value=value), self.assertRaisesRegex(BuildError, 'interactive: must be'):
                render_embed({**embed, 'interactive': value}, post)
        with self.assertRaisesRegex(BuildError, 'interactive: requires'):
            render_embed({**embed, 'interactive': True}, post)

    def test_homepage_announcement_flag_requires_boolean(self):
        self.post(front='announcement: "false"')
        with self.assertRaisesRegex(BuildError, 'announcement must be true or false'):
            self.run_build()

    def test_code_sample_unsafe_markup_is_preserved(self):
        self.post(body='```html\n<script>alert(1)</script>\n```')
        self.run_build()
        self.assertIn('&lt;script&gt;', (self.output / 'cards/first/index.html').read_text())

    def test_output_safety_and_failed_build_preserves_previous_site(self):
        self.post()
        self.run_build()
        original = (self.output / 'index.html').read_bytes()
        self.post(body='![broken](missing.png)')
        with self.assertRaises(BuildError):
            self.run_build()
        self.assertEqual((self.output / 'index.html').read_bytes(), original)
        for path in (self.root, self.root.parent, self.root / 'content', self.root / 'assets/output'):
            with self.subTest(path=path), self.assertRaisesRegex(BuildError, 'unsafe output'):
                build(self.root, path)
        arbitrary = self.root / 'my-files'
        arbitrary.mkdir()
        (arbitrary / 'keep.txt').write_text('Do not remove')
        with self.assertRaisesRegex(BuildError, 'not empty'):
            build(self.root, arbitrary)
        self.assertTrue((arbitrary / 'keep.txt').exists())

    def test_external_media_symlink_is_rejected(self):
        source = self.post()
        outside = self.root.parent / 'private.txt'
        outside.write_text('private')
        (source.parent / 'leak.txt').symlink_to(outside)
        with self.assertRaisesRegex(BuildError, 'symlink'):
            self.run_build()

    def test_nested_draft_media_is_not_published_by_parent_post(self):
        self.post()
        draft = self.post('cards/first/private/index.md', front='draft: true')
        (draft.parent / 'private.txt').write_text('Do not publish')
        self.run_build()
        self.assertFalse((self.output / 'cards/first/private').exists())

    def test_reserved_file_ancestors_and_media_page_collisions(self):
        source = self.post()
        for url in ('/feed.xml/', '/search-index.json/', '/.site-build.json/'):
            with self.subTest(url=url):
                self.post(front=f'permalink: {url}')
                with self.assertRaises(BuildError):
                    self.run_build()
        self.post(front='permalink: /hello.html')
        self.post('cards/second.md', front='permalink: /hello.html/nested/')
        with self.assertRaisesRegex(BuildError, 'Duplicate'):
            self.run_build()
        (self.root / 'content/cards/second.md').unlink()
        self.post()
        (source.parent / 'index.html').write_text('A colliding asset')
        with self.assertRaisesRegex(BuildError, 'collides'):
            self.run_build()

    def test_symlink_topic_and_legacy_escape_are_rejected(self):
        outside = self.root.parent / 'outside'
        outside.mkdir()
        (outside / 'private.md').write_text('---\ntitle: Private\ndate: 2025-04-05\n---\nSecret')
        (self.root / 'content/leak').symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(BuildError, 'symlink'):
            self.run_build()
        (self.root / 'content/leak').unlink()
        legacy = self.root / 'card'
        legacy.mkdir()
        (legacy / 'private.html').symlink_to(outside / 'private.md')
        with self.assertRaisesRegex(BuildError, 'symlink'):
            self.run_build()

    def test_encoded_reserved_characters_in_filenames_survive(self):
        source = self.post(body='![Art](art%23one.png)\n\n[Read](report%3Ffinal.pdf)')
        Image.new('RGB', (8, 8)).save(source.parent / 'art#one.png')
        (source.parent / 'report?final.pdf').write_text('PDF fixture')
        self.run_build()
        text = (self.output / 'cards/first/index.html').read_text()
        self.assertIn('art%23one.png', text)
        self.assertIn('report%3Ffinal.pdf', text)

    def test_svg_and_form_script_links_are_rejected(self):
        for body in ('<svg><a xlink:href="javascript:alert(1)">Click</a></svg>', '<form action="javascript:alert(1)"><button>Click</button></form>'):
            with self.subTest(body=body):
                self.post(body=body)
                with self.assertRaisesRegex(BuildError, 'Unsupported raw'):
                    self.run_build()

    def test_timeline_thumbnails_are_small_and_data_keeps_original_images(self):
        self.post(front='template: timeline')
        image = self.root / 'assets/images/package.png'
        Image.new('RGBA', (800, 1200), '#efefef').save(image)
        data = self.root / 'content/_data'
        data.mkdir()
        (data / 'card-sets.json').write_text(json.dumps({'sets': [{'id': 'base-1', 'name': 'Base', 'year': 1996, 'month': 10, 'image': '/assets/images/package.png'}]}))
        self.run_build()
        item = json.loads((self.output / 'assets/data/card-sets.json').read_text())['sets'][0]
        self.assertEqual(item['image'], '/assets/images/package.png')
        self.assertLessEqual(item['thumbnailWidth'], 160)
        self.assertLessEqual(item['thumbnailHeight'], 200)
        with Image.open(self.output / item['thumbnail'].lstrip('/')) as thumbnail:
            self.assertEqual(thumbnail.format, 'WEBP')
        self.assertNotIn('thumbnail', json.loads((data / 'card-sets.json').read_text())['sets'][0])

    def test_gallery_previews_are_bounded_deterministic_and_keep_originals(self):
        from build import prepare_galleries
        self.post(front='gallery:\n  - src: /assets/images/large.png\n    alt: Pack artwork\n  - src: https://example.com/remote.png\n    alt: Remote artwork')
        original = self.root / 'assets/images/large.png'
        Image.new('RGB', (1600, 2200), '#cc5577').save(original)
        topics, posts = discover(self.root)
        prepare_galleries(posts, self.root)
        item = posts[0]['gallery'][0]
        first_path = item['thumbnail']
        self.assertEqual(item['src'], '/assets/images/large.png')
        self.assertLessEqual(item['thumbnailWidth'], 600)
        self.assertLessEqual(item['thumbnailHeight'], 700)
        with Image.open(original) as image:
            self.assertEqual(image.size, (1600, 2200))
        with Image.open(self.root / first_path.lstrip('/')) as preview:
            self.assertEqual(preview.format, 'WEBP')
        self.assertNotIn('thumbnail', posts[0]['gallery'][1])
        prepare_galleries(posts, self.root)
        self.assertEqual(item['thumbnail'], first_path)
        self.run_build()
        self.assertTrue((self.output / first_path.lstrip('/')).is_file())

    def test_missing_gallery_image_fails_without_link_check(self):
        self.post(front='gallery:\n  - src: absent.png\n    alt: Missing')
        with self.assertRaisesRegex(BuildError, 'missing or unsafe gallery image'):
            build(self.root, self.output, check=False)

    def test_build_is_deterministic(self):
        self.post()
        self.run_build()
        first = {str(path.relative_to(self.output)): path.read_bytes() for path in self.output.rglob('*') if path.is_file()}
        self.run_build()
        second = {str(path.relative_to(self.output)): path.read_bytes() for path in self.output.rglob('*') if path.is_file()}
        self.assertEqual(first, second)


if __name__ == '__main__':
    unittest.main()

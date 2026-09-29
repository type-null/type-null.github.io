"""Homepage topic selection uses real published posts and portable links."""
import contextlib
from html.parser import HTMLParser
import io
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from urllib.parse import urljoin

from PIL import Image
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build import BuildError, build, discover


class Sections(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.sections = {}
        self.current = None
        self.feed(html)

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        classes = attrs.get('class', '').split()
        if tag == 'section' and 'home-topic' in classes:
            self.current = {'layout': attrs['data-layout'], 'links': [], 'variants': [], 'buttons': []}
            self.sections[attrs['data-topic']] = self.current
        elif self.current is not None:
            if tag == 'article':
                self.current['variants'].extend(value.removeprefix('topic-preview--') for value in classes if value.startswith('topic-preview--'))
            elif tag == 'a':
                key = 'links' if 'topic-showcase-link' in classes else 'buttons' if 'button' in classes else None
                if key:
                    self.current[key].append(urljoin('/', attrs['href']))

    def handle_endtag(self, tag):
        if tag == 'section':
            self.current = None


class HomeTopicTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / 'repo'
        (self.root / 'content').mkdir(parents=True)
        (self.root / 'templates').mkdir()
        (self.root / 'assets/images').mkdir(parents=True)
        Image.new('RGB', (16, 16), '#eeeeff').save(self.root / 'assets/images/type-null.png')
        for name in ('home-topics.html', 'macros.html'):
            shutil.copy2(ROOT / 'templates' / name, self.root / 'templates' / name)
        (self.root / 'templates/home.html').write_text('<!doctype html><main>{% include "home-topics.html" %}</main>')
        for name in ('article', 'archive', 'topic', '404'):
            (self.root / 'templates' / f'{name}.html').write_text('<!doctype html><h1>{{ page.title }}</h1>')

    def tearDown(self):
        self.temporary.cleanup()

    def topic(self, name, **metadata):
        directory = self.root / 'content' / name
        directory.mkdir(exist_ok=True)
        (directory / '_topic.yml').write_text(yaml.safe_dump(metadata))

    def post(self, topic, slug, **metadata):
        source = self.root / 'content' / topic / slug / 'index.md'
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text('---\n' + yaml.safe_dump({'title': slug, 'date': '2026-09-01', 'description': 'An actual post.', **metadata}) + '---\nReal article body.')

    def homepage(self):
        with contextlib.redirect_stdout(io.StringIO()):
            build(self.root, check=True)
        html = (self.root / '_site/index.html').read_text()
        return html, Sections(html).sections

    def test_formats_select_topic_posts_and_keep_unlisted_and_drafts_private(self):
        self.topic('cards', home_layout='gallery')
        self.topic('sports', home_layout='feature')
        self.topic('notes', home_layout='journal')
        for number in range(8):
            self.post('cards', f'art-{number}', date=f'2026-09-{number + 1:02}')
        for number in range(6):
            self.post('notes', f'note-{number}', date=f'2026-09-{number + 1:02}')
        self.post('sports', 'article', date='2026-09-20')
        self.post('sports', 'new-tool', date='2026-09-18', template='tool')
        self.post('sports', 'old-tool', date='2026-09-17', template='landing')
        self.post('notes', 'unlisted-resume', unlisted=True, date='2026-09-30')
        self.post('cards', 'private-draft', draft=True, date='2026-09-30')
        html, sections = self.homepage()
        self.assertEqual(sections['cards']['links'], [f'/cards/art-{number}/index.html' for number in range(7, 1, -1)])
        self.assertEqual(sections['notes']['links'], [f'/notes/note-{number}/index.html' for number in range(5, 1, -1)])
        self.assertEqual(sections['sports']['links'], ['/sports/new-tool/index.html', '/sports/article/index.html', '/sports/old-tool/index.html'])
        self.assertEqual(sections['sports']['variants'], ['lead', 'small', 'small'])
        self.assertEqual([sections[topic]['layout'] for topic in ('cards', 'sports', 'notes')], ['gallery', 'feature', 'journal'])
        self.assertNotIn('unlisted-resume', html)
        self.assertNotIn('private-draft', html)
        self.assertNotIn('class="post-card', html)
        self.assertEqual(html.count('data-color-reveal='), 3)

    def test_feature_falls_back_to_latest_article_without_duplicate_links(self):
        self.topic('fieldwork', home_layout='feature')
        self.post('fieldwork', 'older', date='2026-08-01')
        self.post('fieldwork', 'newer', date='2026-09-01')
        _, sections = self.homepage()
        self.assertEqual(sections['fieldwork']['links'], ['/fieldwork/newer/index.html', '/fieldwork/older/index.html'])
        self.assertEqual(sections['fieldwork']['variants'], ['lead', 'small'])

    def test_one_feature_needs_no_empty_preview_strip(self):
        self.topic('tools', home_layout='feature')
        self.post('tools', 'only-tool', template='tool')
        html, sections = self.homepage()
        self.assertEqual(sections['tools']['links'], ['/tools/only-tool/index.html'])
        self.assertNotIn('topic-feature__previews', html)

    def test_empty_topic_gets_default_layout_and_working_topic_link(self):
        self.topic('new-topic')
        html, sections = self.homepage()
        self.assertEqual(sections['new-topic'], {'layout': 'gallery', 'links': [], 'variants': [], 'buttons': ['/new-topic/index.html']})
        self.assertIn('New posts will appear here.', html)

    def test_layout_survives_folder_rename_and_label_change(self):
        self.topic('notes', home_layout='journal', label='Reading & writing')
        self.post('notes', 'hello')
        (self.root / 'content/notes').rename(self.root / 'content/stories')
        html, sections = self.homepage()
        self.assertEqual(sections['stories']['layout'], 'journal')
        self.assertEqual(sections['stories']['links'], ['/stories/hello/index.html'])
        self.assertIn('READING &amp; WRITING', html)

    def test_invalid_layout_is_a_clear_authoring_error(self):
        for value in ('carousel', '', None, False, ['gallery'], {'layout': 'gallery'}):
            with self.subTest(value=value):
                self.topic('notes', home_layout=value)
                with self.assertRaisesRegex(BuildError, 'home_layout must be gallery, feature, or journal'):
                    discover(self.root)


if __name__ == '__main__':
    unittest.main()

"""Dates survive real template rendering and rebuilds without Git or file times."""
import contextlib
import datetime as dt
from html.parser import HTMLParser
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build import BuildError, TEMPLATES, build, discover
from post_dates import metadata_dates, parse_post_time, publication_date


class DateElements(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.times, self.meta = [], {}
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'time':
            self.times.append(attrs.get('datetime'))
        if tag == 'meta':
            self.meta[attrs.get('name') or attrs.get('property')] = attrs.get('content')


class PostDateParsingTests(unittest.TestCase):
    def test_calendar_and_timestamp_inputs_keep_declared_precision_and_offset(self):
        for raw, expected in (
            ('2024-02-29', '2024-02-29'),
            ('2026-09-29T14:00:00-04:00', '2026-09-29T14:00:00-04:00'),
            ('2026-09-29T14:00Z', '2026-09-29T14:00:00+00:00'),
            ('2026-09-29T14:00:03.125+05:30', '2026-09-29T14:00:03.125000+05:30'),
        ):
            for value in (raw, yaml.safe_load(raw)):
                with self.subTest(raw=raw, kind=type(value).__name__):
                    self.assertEqual(parse_post_time(value, 'updated').isoformat(), expected)

    def test_rejects_ambiguous_invalid_and_nonscalar_values(self):
        values = [None, True, False, 20260929, 1.5, [], {}, '', 'today', '2026-9-29',
                  '2026-02-29', '2026-09-29T14:00:00', '2026-09-29 14:00:00',
                  '2026-09-29T14:00:00-0400', '2026-09-29T14:00:00+00:60',
                  '2026-09-29T14:00:00+24:00', '2026-09-29T25:00:00Z',
                  '2026-09-29T14:00:00.1234567Z', dt.datetime(2026, 9, 29, 14)]
        for value in values:
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'updated: use YYYY-MM-DD'):
                parse_post_time(value, 'updated')

    def test_publication_is_a_calendar_date_only(self):
        for value in ('2026-09-29', dt.date(2026, 9, 29)):
            self.assertEqual(publication_date(value), dt.date(2026, 9, 29))
        for value in (None, 20260929, '2026-09-29T00:00:00Z', dt.datetime(2026, 9, 29), '2026-02-30'):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'date: use'):
                publication_date(value)

    def test_missing_dates_use_initial_edition_and_never_today(self):
        dates = metadata_dates({}, dt.date(2001, 2, 3))
        self.assertEqual((dates['created'], dates['updated']), ('2001-02-03', '2001-02-03'))
        self.assertEqual((dates['created_inferred'], dates['updated_explicit']), (True, False))
        self.assertEqual(dates['created_display'], 'Feb 3, 2001')
        self.assertFalse(dates['show_publication_date'])

    def test_day_precision_allows_same_day_first_writing_and_revision_times(self):
        published = dt.date(2026, 9, 29)
        for meta in ({'created': '2026-09-29T23:59:59-04:00'},
                     {'updated': '2026-09-29T00:00:00+05:30'},
                     {'created': '2026-09-29', 'updated': '2026-09-29T00:00:00Z'}):
            with self.subTest(meta=meta):
                metadata_dates(meta, published)
        dates = metadata_dates({'created': '2026-09-28', 'updated': '2026-09-29T14:05:00-04:00'}, published)
        self.assertTrue(dates['show_publication_date'])
        self.assertEqual(dates['updated_display'], 'Sep 29, 2026, 14:05 UTC-04:00')

    def test_ordering_rejects_revisions_before_publication_or_first_writing(self):
        published = dt.date(2026, 9, 29)
        for meta, field in (({'created': '2026-09-30'}, 'created'),
                            ({'updated': '2026-09-28'}, 'updated'),
                            ({'created': '2026-09-29T12:00:00Z', 'updated': '2026-09-29T11:59:59Z'}, 'updated')):
            with self.subTest(meta=meta), self.assertRaisesRegex(ValueError, field + ' must be'):
                metadata_dates(meta, published)

    def test_exact_timestamps_compare_instants_across_offsets(self):
        published = dt.date(2026, 9, 29)
        # This revision has a later local calendar day but actually predates writing.
        with self.assertRaisesRegex(ValueError, 'updated must be on or after created'):
            metadata_dates({'created': '2026-09-28T23:30:00-12:00', 'updated': '2026-09-29T00:30:00+14:00'}, published)
        # Different clock readings for the same instant are valid.
        metadata_dates({'created': '2026-09-29T08:00:00-04:00', 'updated': '2026-09-29T14:00:00+02:00'}, published)


class PostDateRenderingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.output = self.root / '_site'
        shutil.copytree(ROOT / 'templates', self.root / 'templates')
        data = self.root / 'content/_data/card-sets.json'
        data.parent.mkdir(parents=True)
        data.write_text(json.dumps({'sets': [], 'years': [2024, 2025], 'eras': []}))

    def tearDown(self):
        self.temporary.cleanup()

    def post(self, name='first', *, template='article', date='2026-09-29', dates=''):
        source = self.root / f'content/notes/{name}/index.md'
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(f'---\ntitle: {name}\ndate: {date}\ntemplate: {template}\n{dates}\n---\nA body for the test.\n')
        return source

    def run_build(self):
        with contextlib.redirect_stdout(io.StringIO()):
            build(self.root, self.output)

    def test_all_templates_display_both_dates_with_exact_machine_readable_metadata(self):
        for template in TEMPLATES:
            self.post(template, template=template, dates='created: 2026-09-28T20:30:00-04:00\nupdated: 2026-09-29T14:00:00-04:00')
        self.run_build()
        for template in TEMPLATES:
            with self.subTest(template=template):
                text = (self.output / f'notes/{template}/index.html').read_text()
                document = DateElements(text)
                self.assertIn('First written <time', text)
                self.assertIn('Last revised <time', text)
                self.assertIn('Published <time', text)
                self.assertIn('2026-09-28T20:30:00-04:00', document.times)
                self.assertIn('2026-09-29T14:00:00-04:00', document.times)
                self.assertEqual(document.meta['article:published_time'], '2026-09-29')
                self.assertEqual(document.meta['dcterms.created'], '2026-09-28T20:30:00-04:00')
                self.assertEqual(document.meta['article:modified_time'], '2026-09-29T14:00:00-04:00')

    def test_explicit_dates_are_in_search_and_sitemap_without_changing_publication_order(self):
        self.post('older', date='2025-01-01', dates='created: 2024-12-31\nupdated: 2026-09-29T14:00:00Z')
        self.post('newer', date='2026-01-01')
        self.run_build()
        index = json.loads((self.output / 'search-index.json').read_text())
        self.assertEqual([post['title'] for post in index], ['newer', 'older'])
        self.assertEqual(index[1]['created'], '2024-12-31')
        self.assertEqual(index[1]['updated'], '2026-09-29T14:00:00+00:00')
        self.assertIn('"updated": "2026-09-29T14:00:00+00:00"', (self.output / 'search-index.js').read_text())
        namespace = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        entries = ET.parse(self.output / 'sitemap.xml').findall('s:url', namespace)
        revisions = {entry.findtext('s:loc', namespaces=namespace): entry.findtext('s:lastmod', namespaces=namespace) for entry in entries}
        self.assertEqual(revisions['https://type-null.github.io/notes/older/'], '2026-09-29T14:00:00+00:00')
        self.assertEqual(revisions['https://type-null.github.io/notes/newer/'], '2026-01-01')
        self.assertIsNone(revisions['https://type-null.github.io/'])
        items = ET.parse(self.output / 'feed.xml').findall('channel/item')
        self.assertEqual([item.findtext('title') for item in items], ['newer', 'older'])
        self.assertEqual(items[1].findtext('pubDate'), 'Wed, 01 Jan 2025 00:00:00 GMT')

    def test_touching_source_and_rebuilding_preserves_dates_and_source_bytes(self):
        source = self.post(date='2001-02-03')
        before = source.read_bytes()
        self.run_build()
        html = (self.output / 'notes/first/index.html').read_bytes()
        os.utime(source, (1_800_000_000, 1_800_000_000))
        self.run_build()
        self.assertEqual(source.read_bytes(), before)
        self.assertEqual((self.output / 'notes/first/index.html').read_bytes(), html)
        self.assertIn(b'Initial published edition; no later revision was recorded.', html)
        self.assertIn(b'Uses the publication date because no separate writing date was recorded.', html)
        self.assertNotIn(b'Published <time', html)
        dates = DateElements(html.decode())
        self.assertEqual(dates.meta['article:modified_time'], '2001-02-03')

    def test_discovery_errors_name_the_source_and_field(self):
        for dates, field in (('created: null', 'created'), ('updated: null', 'updated'),
                             ('created: true', 'created'), ('updated: 2026-09-29T14:00:00', 'updated'),
                             ('created: 2026-09-30', 'created')):
            source = self.post(dates=dates)
            with self.subTest(dates=dates), self.assertRaisesRegex(BuildError, f'{source}: {field}'):
                discover(self.root)

    def test_front_matter_validation_precedes_yaml_timestamp_normalization(self):
        for timestamp in ('2026-09-29T14:00:00+01:99', '2026-09-29T14:00:00.1234567Z'):
            for value in (timestamp, f'"{timestamp}"'):
                self.post(dates='updated: ' + value)
                with self.subTest(value=value), self.assertRaisesRegex(BuildError, 'updated: use YYYY-MM-DD'):
                    discover(self.root)
        # The custom loader must not change YAML parsing elsewhere in the process.
        self.assertIsInstance(yaml.safe_load('2026-09-29'), dt.date)


if __name__ == '__main__':
    unittest.main()

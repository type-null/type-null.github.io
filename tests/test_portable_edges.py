"""Counterexamples found while reviewing file:// publishing and CSS closure."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from portable import make_portable


class PortableEdgeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='portable café 雪 ')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def write(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
        return path

    def test_stylesheet_rel_tokens_are_case_insensitive(self):
        page = self.write('notes/index.html', '<LINK REL="StyleSheet" HREF="/assets/css/main.css?version=2#theme">')
        original = self.write('assets/css/main.css', 'p{background:url(/assets/art.png)}')
        make_portable(self.root)
        self.assertIn('HREF="../assets/generated/css/assets/css/main.css?version=2#theme"', page.read_text())
        compiled = self.root / 'assets/generated/css/assets/css/main.css'
        self.assertIn('url("../../../../art.png")', compiled.read_text())
        self.assertEqual(original.read_text(), 'p{background:url(/assets/art.png)}')

    def test_import_url_compiles_extensionless_stylesheets_with_query_and_fragment(self):
        self.write('index.html', '<link rel="stylesheet" href="/assets/css/main.css">')
        self.write('assets/css/main.css', '@import url("theme?edition=2#local") screen;')
        original = self.write('assets/css/theme', '@import "main.css"; p{background:url(/assets/images/art.svg#paint);filter:url(#shadow)}')
        make_portable(self.root)
        compiled = self.root / 'assets/generated/css/assets/css/theme'
        self.assertTrue(compiled.is_file(), 'Every @import must compile its own resource references, regardless of extension')
        self.assertIn('url("../../../../images/art.svg#paint")', compiled.read_text())
        self.assertIn('filter:url(#shadow)', compiled.read_text())
        self.assertIn('@import "main.css"', compiled.read_text())
        self.assertEqual(original.read_text(), '@import "main.css"; p{background:url(/assets/images/art.svg#paint);filter:url(#shadow)}')
        self.assertIn('?edition=2#local', (self.root / 'assets/generated/css/assets/css/main.css').read_text())

    def test_data_and_local_srcset_candidates_are_both_preserved(self):
        data = 'data:image/gif;base64,R0lGODlhAQABAAAAACw='
        page = self.write('notes/index.html', f'<img srcset="{data} 1x, /assets/high.png 2x">')
        make_portable(self.root)
        self.assertIn(f'srcset="{data} 1x, ../assets/high.png 2x"', page.read_text())

    def test_encoded_reserved_characters_and_unicode_survive_relocation(self):
        self.write('assets/雪 #? &.png', 'image fixture')
        page = self.write('notes/旅 の記録/index.html', '<img src="/assets/%E9%9B%AA%20%23%3F%20%26.png"><a href="/notes/旅%20の記録/?a=1&amp;b=2#写真">Story</a>')
        make_portable(self.root)
        rendered = page.read_text()
        self.assertIn('src="../../assets/%E9%9B%AA%20%23%3F%20&amp;.png"', rendered)
        self.assertIn('href="index.html?a=1&amp;b=2#写真"', rendered)

    def test_scripts_comments_entities_and_svg_case_are_untouched(self):
        preserved = '''<!-- /assets/keep-comment.png -->
<svg viewBox="0 0 16 16"><linearGradient id="paint"><stop offset="0"/></linearGradient><use xlink:href="#paint"/></svg>
<script>const literal = '<a href="/keep-script">A & B</a>'; const data = {url:"/assets/keep.png"};</script>
<p>Quotes &quot;x&quot;, numeric &#x96ea;, and Unicode 雪.</p>'''
        page = self.write('notes/index.html', preserved + '<img src="/assets/actual.png">')
        make_portable(self.root)
        self.assertTrue(page.read_text().startswith(preserved))
        self.assertIn('src="../assets/actual.png"', page.read_text())


if __name__ == '__main__':
    unittest.main()

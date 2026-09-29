"""Regression coverage for emitted paths that must work without an HTTP origin."""
import sys
from pathlib import Path
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from portable import make_portable


class PortableTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def write(self, path, text):
        file = self.root / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(text)
        return file

    def test_navigation_at_both_depths_and_canonical_metadata(self):
        home = self.write('index.html', '<a href="/notes/">Notes</a><a href="/">Home</a>')
        post = self.write('notes/story/index.html', '<link rel="canonical" href="https://type-null.github.io/notes/story/"><a href="/notes/?q=a&amp;b=c#title">Notes</a><a href="/">Home</a><a href="#title">Jump</a><a href="?q=reset">Query</a>')
        make_portable(self.root)
        self.assertEqual(home.read_text(), '<a href="notes/index.html">Notes</a><a href="index.html">Home</a>')
        self.assertIn('href="../index.html?q=a&amp;b=c#title"', post.read_text())
        self.assertIn('href="../../index.html"', post.read_text())
        self.assertIn('href="#title"', post.read_text())
        self.assertIn('href="?q=reset"', post.read_text())
        self.assertIn('href="https://type-null.github.io/notes/story/"', post.read_text())

    def test_images_video_iframe_pdf_and_encoded_filenames(self):
        post = self.write('notes/story/index.html', '''<img src='/assets/雪%20pack.png' srcset="/assets/small.webp 1x, /assets/large.webp 2x"><video src="clip.webm" poster="/assets/poster.png"></video><iframe src="/card/toolkit.html"></iframe><object data="notes.pdf"></object><a href="https://example.org/source">Source</a>''')
        make_portable(self.root)
        text = post.read_text()
        self.assertIn('src="../../assets/%E9%9B%AA%20pack.png"', text)
        self.assertIn('srcset="../../assets/small.webp 1x, ../../assets/large.webp 2x"', text)
        self.assertIn('src="clip.webm" poster="../../assets/poster.png"', text)
        self.assertIn('src="../../card/toolkit.html"', text)
        self.assertIn('data="notes.pdf"', text)
        self.assertIn('href="https://example.org/source"', text)

    def test_css_sources_untouched_and_imports_rebased_including_cycles(self):
        page = self.write('notes/index.html', '<link rel="stylesheet" href="/assets/css/main.css">')
        css = self.write('assets/css/main.css', '''@import 'other.css'; /* url(/keep-comment) */
@font-face{src:url('../fonts/local.woff2')}p{background:url("/assets/images/space%20image.png")}''')
        self.write('assets/css/other.css', '@import url("main.css"); a{background:url(data:image/png;base64,AAA)}')
        original = css.read_text()
        make_portable(self.root)
        self.assertEqual(css.read_text(), original)
        self.assertIn('href="../assets/generated/css/assets/css/main.css"', page.read_text())
        compiled = (self.root / 'assets/generated/css/assets/css/main.css').read_text()
        self.assertIn("@import 'other.css'", compiled)
        self.assertIn('url("../../../../fonts/local.woff2")', compiled)
        self.assertIn('url("../../../../images/space%20image.png")', compiled)
        self.assertIn('/* url(/keep-comment) */', compiled)
        self.assertIn('data:image/png;base64,AAA', (self.root / 'assets/generated/css/assets/css/other.css').read_text())

    def test_inline_styles_svg_and_script_payloads_keep_their_meaning(self):
        script = '<script type="application/json">{"image":"/assets/art.png","text":"<tag> & café"}</script>'
        svg = '<svg viewBox="0 0 12 12"><linearGradient id="g"><stop offset="0"/></linearGradient><use xlink:href="#g" /></svg>'
        page = self.write('notes/index.html', '<!DOCTYPE html>\n<!--keep-->\n<style>a{background:url(/assets/a.png)}</style><p style="background:url(&quot;/assets/b.png&quot;)">A &amp; B</p>' + svg + script)
        make_portable(self.root)
        text = page.read_text()
        self.assertIn('<style>a{background:url("../assets/a.png")}</style>', text)
        self.assertIn('style="background:url(&quot;../assets/b.png&quot;)"', text)
        self.assertIn(svg, text)
        self.assertIn(script, text)
        self.assertIn('A &amp; B', text)
        self.assertIn('<!--keep-->', text)


if __name__ == '__main__':
    unittest.main()

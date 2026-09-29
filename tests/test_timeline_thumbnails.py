"""Pack previews normalize transparent padding without changing source artwork."""

import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build import BuildError, prepare_timeline


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TimelineThumbnailTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / 'repo'
        self.output = self.root / '_site'
        self.assets = self.root / 'assets/images'
        self.assets.mkdir(parents=True)
        self.source = self.root / 'content/_data/card-sets.json'
        self.source.parent.mkdir(parents=True)

    def prepare(self, items):
        self.source.write_text(json.dumps({'sets': items}), encoding='utf-8')
        before = digest(self.source)
        result = prepare_timeline(self.root, self.output)
        self.assertEqual(digest(self.source), before, 'Preview generation changed the source dataset')
        self.assertEqual(
            json.loads((self.output / 'assets/data/card-sets.json').read_text()), result,
            'The rendered dataset must contain the actual preview dimensions',
        )
        return result['sets']

    def preview(self, image, **save_options):
        source = self.assets / 'pack.png'
        image.save(source, **save_options)
        before = digest(source)
        item, = self.prepare([{'id': 'test-pack', 'image': '/assets/images/pack.png'}])
        self.assertEqual(digest(source), before, 'Preview generation changed the original image')
        with Image.open(self.output / item['thumbnail'].lstrip('/')) as thumbnail:
            result = thumbnail.copy()
        self.assertEqual(result.size, (item['thumbnailWidth'], item['thumbnailHeight']))
        return result

    def test_real_august_and_september_packs_match_june_scale(self):
        expected = {
            '2025-08-m-m1l': (100, 200),
            '2025-08-m-m1s': (99, 200),
            '2025-09-m-m2': (99, 200),
            '2025-06-sv-sv11b': (103, 200),
            '2025-06-sv-sv11w': (103, 200),
        }
        production_source = ROOT / 'content/_data/card-sets.json'
        production_before = digest(production_source)
        items = [item for item in json.loads(production_source.read_text())['sets']
                 if item['id'] in expected]
        self.assertEqual(len(items), len(expected))
        originals = {}
        for item in items:
            original = ROOT / item['image'].lstrip('/')
            copy = self.root / item['image'].lstrip('/')
            copy.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(original, copy)
            originals[original] = originals[copy] = digest(original)

        for item in self.prepare(items):
            with self.subTest(release=item['id']):
                with Image.open(self.output / item['thumbnail'].lstrip('/')) as image:
                    self.assertEqual(image.size, expected[item['id']])
                    self.assertEqual(image.size, (item['thumbnailWidth'], item['thumbnailHeight']))
                    # The visible pack reaches both canvas edges, instead of
                    # occupying roughly half of the original square preview.
                    left, top, right, bottom = image.getchannel('A').getbbox()
                    self.assertLessEqual(left, 1)
                    self.assertGreaterEqual(right, image.width - 1)
                    self.assertLessEqual(top, 1)
                    self.assertGreaterEqual(bottom, image.height - 1)
        self.assertEqual(digest(production_source), production_before)
        for original, before in originals.items():
            self.assertEqual(digest(original), before, str(original))

    def test_opaque_white_padding_and_black_artwork_are_preserved(self):
        for color in ('white', 'black'):
            with self.subTest(color=color):
                image = Image.new('RGB', (80, 60), color)
                image.paste('red', (30, 10, 50, 50))
                preview = self.preview(image)
                self.assertEqual(preview.size, (80, 60))
                # Alpha cropping must not be replaced with a background-color
                # heuristic that could remove pale or dark artwork.
                self.assertEqual(preview.convert('RGBA').getchannel('A').getextrema(), (255, 255))

    def test_palette_transparency_is_cropped(self):
        image = Image.new('P', (24, 30), 0)
        image.putpalette([255, 255, 255, 200, 30, 60] + [0] * 762)
        image.paste(1, (5, 6, 15, 26))
        self.assertEqual(self.preview(image, transparency=0).size, (10, 20))

    def test_grayscale_alpha_is_cropped_without_losing_transparency(self):
        image = Image.new('LA', (24, 30), (200, 0))
        image.paste((200, 255), (5, 6, 15, 26))
        image.putpixel((5, 6), (200, 64))
        preview = self.preview(image)
        self.assertEqual(preview.size, (10, 20))
        self.assertEqual(preview.convert('RGBA').getpixel((0, 0))[3], 64)

    def test_even_faint_edge_pixels_are_kept(self):
        image = Image.new('RGBA', (20, 20), (255, 0, 0, 0))
        image.paste((200, 40, 80, 255), (6, 4, 14, 16))
        image.putpixel((1, 5), (200, 40, 80, 1))
        preview = self.preview(image)
        self.assertEqual(preview.size, (13, 12))
        self.assertEqual(preview.convert('RGBA').getpixel((0, 1))[3], 1)

    def test_exif_orientation_is_applied_before_measuring_the_pack(self):
        image = Image.new('RGBA', (18, 26), (0, 0, 0, 0))
        image.paste((200, 40, 80, 255), (3, 4, 11, 22))
        exif = Image.Exif()
        exif[274] = 6  # Display rotated clockwise.
        self.assertEqual(self.preview(image, exif=exif).size, (18, 8))

    def test_fully_transparent_artwork_has_an_actionable_error(self):
        image = Image.new('RGBA', (30, 30), (200, 100, 50, 0))
        with self.assertRaisesRegex(BuildError, r'pack\.png: image contains no visible pixels'):
            self.preview(image)


if __name__ == '__main__':
    unittest.main()

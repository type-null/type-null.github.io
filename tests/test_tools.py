"""Retained tools: offline asset integrity and executable probability regressions."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parents[1]


class AssetParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.assets = []

    def handle_starttag(self, tag, attributes):
        attributes = dict(attributes)
        if tag == 'script' and attributes.get('src'):
            self.assets.append(attributes['src'])
        if tag == 'link' and attributes.get('rel') == 'stylesheet':
            self.assets.append(attributes['href'])


class ToolTests(unittest.TestCase):
    def test_probability_models_against_independent_oracle(self):
        node = shutil.which('node')
        if node:
            command = [node, str(ROOT / 'tests/tool_probability.test.js')]
            source = None
        elif sys.platform == 'darwin' and shutil.which('osascript'):
            command = ['osascript', '-l', 'JavaScript', '-']
            source = (ROOT / 'assets/js/tools/probability.js').read_text() + '\n'
            source += (ROOT / 'tests/tool_probability.test.js').read_text()
            source += '\nJSON.stringify(runProbabilityTests(ToolProbability));\n'
        else:
            self.skipTest('A JavaScript runtime is required; run node tests/tool_probability.test.js.')
        result = subprocess.run(command, input=source, text=True, capture_output=True, timeout=90, cwd=ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout.strip())
        self.assertEqual(report['hands'], 286)
        self.assertEqual(report['prizeCases'], 6200)
        self.assertGreaterEqual(report['checks'], 37000)

    def test_tools_have_only_resolvable_local_runtime_assets(self):
        for relative in ['card/toolkit.html', 'sports/2025/trading_suits.html', 'sports/2025/betting_game.html']:
            page = ROOT / relative
            parser = AssetParser()
            parser.feed(page.read_text())
            for asset in parser.assets:
                with self.subTest(page=relative, asset=asset):
                    self.assertNotIn('://', asset)
                    self.assertFalse(asset.startswith('//'))
                    resolved = ROOT / asset.lstrip('/') if asset.startswith('/') else page.parent / asset
                    self.assertTrue(resolved.is_file(), str(resolved))


if __name__ == '__main__':
    unittest.main()

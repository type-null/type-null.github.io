"""Preservation checks for the reversible local-material archive."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('archive_check', Path(__file__).resolve().parents[1] / 'scripts/check-archive.py')
CHECKER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKER)


class ArchiveChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.file = self.root / 'archive/original-assets/assets/old.png'
        self.file.parent.mkdir(parents=True)
        self.file.write_bytes(b'original image')
        self.manifest = {'files': [{'original': 'assets/old.png', 'archived': str(self.file.relative_to(self.root)),
            'bytes': 14, 'sha256': hashlib.sha256(b'original image').hexdigest()}], 'total_files': 1, 'total_bytes': 14}
        self.write_manifest()
        self.image = self.root / 'assets/current.png'
        self.image.parent.mkdir()
        self.image.write_bytes(b'timeline original')
        data = self.root / 'content/_data/card-sets.json'
        data.parent.mkdir(parents=True)
        data.write_text(json.dumps({'sets': [{'image': '/assets/current.png'}]}))

    def write_manifest(self):
        (self.root / 'archive/original-assets/manifest.json').write_text(json.dumps(self.manifest))

    def test_complete_archive_and_active_timeline(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(CHECKER.verify(self.root), (1, 14))

    def test_same_size_corruption_fails_hash_check(self):
        self.file.write_bytes(b'changed! image')
        with self.assertRaisesRegex(ValueError, 'Archive content changed'):
            CHECKER.verify(self.root)

    def test_missing_archived_material_fails(self):
        self.file.unlink()
        with self.assertRaises(FileNotFoundError):
            CHECKER.verify(self.root)

    def test_path_cannot_escape_archive(self):
        self.manifest['files'][0]['archived'] = 'archive/original-assets/../../assets/current.png'
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, 'Unsafe archive path'):
            CHECKER.verify(self.root)

    def test_active_timeline_original_cannot_be_archived_away(self):
        self.image.unlink()
        with self.assertRaisesRegex(ValueError, 'Timeline original is missing'):
            CHECKER.verify(self.root)

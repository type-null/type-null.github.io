"""The generated root mirror must never take ownership of author source files."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from publish_root import PublishError, plan_sync, read_manifest, sync_root


class PublishRootTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / 'repo'
        self.root.mkdir()
        self.site = self.root / '_site'
        self.site.mkdir()
        self.generated('.site-build.json', '{"generator":"type-null"}')

    def tearDown(self):
        self.temporary.cleanup()

    @staticmethod
    def put(base, relative, content):
        target = base / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content.encode('utf-8') if isinstance(content, str) else content)
        return target

    def generated(self, relative, content):
        return self.put(self.site, relative, content)

    @staticmethod
    def digest(content):
        data = content.encode('utf-8') if isinstance(content, str) else content
        return hashlib.sha256(data).hexdigest()

    def manifest(self, files):
        self.put(self.root, '.site-root.json', json.dumps({'version': 1, 'files': files}))

    def snapshot(self):
        state = {}
        for path in self.root.rglob('*'):
            relative = path.relative_to(self.root).as_posix()
            if path.is_symlink():
                state[relative] = ('symlink', str(path.readlink()))
            elif path.is_file():
                state[relative] = ('file', path.read_bytes())
            elif path.is_dir():
                state[relative] = ('directory',)
        return state

    def assert_rejected_without_mutation(self):
        before = self.snapshot()
        with self.assertRaises(PublishError):
            plan_sync(self.root, self.site)
        self.assertEqual(self.snapshot(), before, 'Planning changed the repository')
        with self.assertRaises(PublishError):
            sync_root(self.root, self.site)
        self.assertEqual(self.snapshot(), before, 'Rejected synchronization changed the repository')

    def test_empty_manifest_and_planning_are_read_only(self):
        self.generated('index.html', '<h1>New homepage</h1>')
        before = self.snapshot()
        self.assertEqual(read_manifest(self.root), {'version': 1, 'files': {}})
        self.assertIsInstance(plan_sync(self.root, self.site), dict)
        self.assertEqual(self.snapshot(), before)

    def test_new_generated_files_are_copied_and_tracked_with_hashes(self):
        outputs = {
            'index.html': '<h1>Home</h1>',
            'notes/旅の記録/index.html': '<h1>A Unicode route</h1>',
            'assets/images/timeline/new.webp': b'generated image bytes',
            '.nojekyll': b'',
        }
        for relative, content in outputs.items():
            self.generated(relative, content)
        self.assertIsInstance(sync_root(self.root, self.site), dict)
        self.assertEqual(read_manifest(self.root), {
            'version': 1,
            'files': {relative: self.digest(content) for relative, content in outputs.items()},
        })
        for relative, content in outputs.items():
            expected = content.encode('utf-8') if isinstance(content, str) else content
            self.assertEqual((self.root / relative).read_bytes(), expected)
        self.assertFalse((self.root / '.site-build.json').exists())
        self.assertNotIn('.site-root.json', read_manifest(self.root)['files'])
        before = self.snapshot()
        sync_root(self.root, self.site)
        self.assertEqual(self.snapshot(), before, 'An identical second sync must be idempotent')

    def test_identical_author_assets_remain_unmanaged_and_survive_omission(self):
        asset = 'assets/images/original.png'
        self.put(self.root, asset, b'original source image')
        self.generated(asset, b'original source image')
        self.put(self.root, 'assets/author-notes.txt', 'Keep this author file')
        self.generated('index.html', 'Generated home')
        sync_root(self.root, self.site)
        self.assertNotIn(asset, read_manifest(self.root)['files'])
        (self.site / asset).unlink()
        sync_root(self.root, self.site)
        self.assertEqual((self.root / asset).read_bytes(), b'original source image')
        self.assertEqual((self.root / 'assets/author-notes.txt').read_text(), 'Keep this author file')

    def test_legacy_asset_backup_does_not_transfer_author_asset_ownership(self):
        asset = 'assets/images/original.png'
        self.put(self.root, asset, b'original source image')
        self.put(self.root, 'legacy/' + asset, b'original source image')
        self.generated(asset, b'original source image')
        sync_root(self.root, self.site)
        self.assertNotIn(asset, read_manifest(self.root)['files'])
        (self.site / asset).unlink()
        sync_root(self.root, self.site)
        self.assertEqual((self.root / asset).read_bytes(), b'original source image')

    def test_managed_updates_and_stale_route_cleanup_preserve_author_siblings(self):
        self.generated('index.html', 'Version one')
        self.generated('notes/old/index.html', 'Retired generated post')
        self.generated('obsolete/deep/index.html', 'Retired empty branch')
        sync_root(self.root, self.site)
        self.put(self.root, 'notes/old/photo.jpg', b'author photograph')
        self.generated('index.html', 'Version two')
        (self.site / 'notes/old/index.html').unlink()
        (self.site / 'obsolete/deep/index.html').unlink()
        self.generated('notes/new/index.html', 'Renamed generated post')
        sync_root(self.root, self.site)
        self.assertEqual((self.root / 'index.html').read_text(), 'Version two')
        self.assertEqual((self.root / 'notes/new/index.html').read_text(), 'Renamed generated post')
        self.assertFalse((self.root / 'notes/old/index.html').exists())
        self.assertFalse((self.root / 'obsolete').exists())
        self.assertEqual((self.root / 'notes/old/photo.jpg').read_bytes(), b'author photograph')
        self.assertEqual(set(read_manifest(self.root)['files']), {'index.html', 'notes/new/index.html'})

    def test_edited_managed_file_blocks_update_before_any_mutation(self):
        self.generated('index.html', 'Published home')
        self.generated('notes/post/index.html', 'Published post')
        sync_root(self.root, self.site)
        self.put(self.root, 'notes/post/index.html', 'A manual edit that must survive')
        self.generated('index.html', 'Would otherwise be updated first')
        self.generated('brand-new/index.html', 'Would otherwise be created')
        self.generated('notes/post/index.html', 'Generated replacement')
        self.assert_rejected_without_mutation()

    def test_edited_managed_file_blocks_stale_deletion_before_any_mutation(self):
        self.generated('notes/post/index.html', 'Published post')
        sync_root(self.root, self.site)
        self.put(self.root, 'notes/post/index.html', 'Preserve this edit')
        (self.site / 'notes/post/index.html').unlink()
        self.generated('index.html', 'Would otherwise be created')
        self.assert_rejected_without_mutation()

    def test_unowned_different_file_cannot_be_overwritten(self):
        self.put(self.root, 'index.html', 'Existing hand-authored homepage')
        self.generated('index.html', 'Generated homepage')
        self.generated('brand-new/index.html', 'Must not be partially copied')
        self.assert_rejected_without_mutation()

    def test_author_file_as_destination_parent_is_rejected_before_partial_copy(self):
        self.put(self.root, 'z-parent', 'An author file, not a generated directory')
        self.generated('a-new/index.html', 'Must not be copied before discovering the conflict')
        self.generated('z-parent/index.html', 'Cannot be written through a regular file')
        self.assert_rejected_without_mutation()

    def test_bootstrap_replacement_requires_matching_preserved_legacy_copy(self):
        original = 'Hand-authored timeline'
        self.put(self.root, 'card/timeline.html', original)
        self.put(self.root, 'legacy/card/timeline.html', original)
        self.generated('card/timeline.html', 'New generated timeline')
        sync_root(self.root, self.site)
        self.assertEqual((self.root / 'card/timeline.html').read_text(), 'New generated timeline')
        self.assertEqual((self.root / 'legacy/card/timeline.html').read_text(), original)
        self.assertEqual(read_manifest(self.root)['files'], {
            'card/timeline.html': self.digest('New generated timeline'),
        })

    def test_mismatching_legacy_backup_does_not_authorize_bootstrap(self):
        self.put(self.root, 'index.html', 'New author edits after backup')
        self.put(self.root, 'legacy/index.html', 'Old backup')
        self.generated('index.html', 'Generated replacement')
        self.assert_rejected_without_mutation()

    def test_forbidden_source_directories_are_never_publish_destinations(self):
        for directory in ('content', 'templates', 'scripts', 'tests', 'docs',
                          'legacy', 'archive', '.git', '.venv', 'examples', '_site'):
            with self.subTest(directory=directory):
                incoming = self.generated(f'{directory}/source.txt', 'Must not publish')
                self.assert_rejected_without_mutation()
                incoming.unlink()
                incoming.parent.rmdir()

    def test_manifest_cannot_claim_source_files_or_traversal_paths(self):
        protected = ('content/post.md', 'templates/base.html', 'scripts/build.py',
                     'tests/test.py', 'docs/guide.md', 'legacy/index.html',
                     'archive/index.html',
                     '.git/config', '.venv/config', 'examples/post.md',
                     '_site/index.html', '../outside.txt', '/absolute.txt',
                     'notes/../outside.txt', 'notes\\outside.txt', '.',
                     'notes/\x00invalid.html')
        for relative in protected:
            with self.subTest(relative=relative):
                self.manifest({relative: self.digest('old')})
                self.assert_rejected_without_mutation()
        (self.root / '.site-root.json').unlink()

    def test_malformed_manifest_fails_without_changes(self):
        malformed = ('not JSON', '[]', '{"version":2,"files":{}}',
                     '{"version":1,"files":[]}',
                     '{"version":1,"files":{"index.html":"not-a-sha256"}}')
        for content in malformed:
            with self.subTest(content=content):
                self.put(self.root, '.site-root.json', content)
                self.assert_rejected_without_mutation()

    def test_source_file_and_directory_symlinks_cannot_publish_external_data(self):
        outside = Path(self.temporary.name) / 'private'
        outside.mkdir()
        secret = self.put(outside, 'secret.html', 'Private external bytes')
        for directory in (False, True):
            with self.subTest(directory=directory):
                link = self.site / ('linked-directory' if directory else 'secret.html')
                link.symlink_to(outside if directory else secret, target_is_directory=directory)
                self.assert_rejected_without_mutation()
                self.assertEqual(secret.read_text(), 'Private external bytes')
                link.unlink()

    def test_destination_symlink_cannot_redirect_writes_outside_root(self):
        outside = Path(self.temporary.name) / 'private'
        outside.mkdir()
        self.put(outside, 'index.html', 'Private external bytes')
        (self.root / 'notes').symlink_to(outside, target_is_directory=True)
        self.generated('notes/index.html', 'Generated bytes')
        self.assert_rejected_without_mutation()
        self.assertEqual((outside / 'index.html').read_text(), 'Private external bytes')

    def test_symlinked_legacy_backup_cannot_authorize_replacement(self):
        outside = self.put(Path(self.temporary.name), 'backup.html', 'Original page')
        self.put(self.root, 'index.html', 'Original page')
        (self.root / 'legacy').mkdir()
        (self.root / 'legacy/index.html').symlink_to(outside)
        self.generated('index.html', 'Replacement page')
        self.assert_rejected_without_mutation()

    def test_symlinked_legacy_parent_cannot_authorize_replacement(self):
        self.put(self.root, 'card/timeline.html', 'Original timeline')
        backup = self.put(self.root, 'legacy/other-card/timeline.html', 'Original timeline')
        (self.root / 'legacy/card').symlink_to(backup.parent, target_is_directory=True)
        self.generated('card/timeline.html', 'Replacement timeline')
        self.assert_rejected_without_mutation()

    def test_symlinked_manifest_cannot_claim_ownership(self):
        outside = self.put(Path(self.temporary.name), 'manifest.json',
                           json.dumps({'version': 1, 'files': {}}))
        (self.root / '.site-root.json').symlink_to(outside)
        self.generated('index.html', 'New homepage')
        self.assert_rejected_without_mutation()

    def test_dangling_manifest_symlink_is_rejected_before_changes(self):
        missing = Path(self.temporary.name) / 'missing-manifest.json'
        (self.root / '.site-root.json').symlink_to(missing)
        self.generated('index.html', 'New homepage')
        self.assert_rejected_without_mutation()
        self.assertFalse(missing.exists())


if __name__ == '__main__':
    unittest.main()

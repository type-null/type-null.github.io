"""Regression tests for the historical timeline import (Python stdlib only)."""

from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("timeline_import", ROOT / "scripts/import-timeline.py")
IMPORTER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(IMPORTER)


def package(code="SV1S", href="#", name="スカーレットex", era="SV"):
    return f'<a href="{href}"><img src="/assets/images/card/set-package-jp/{era}/{code}.png" alt="{name}"></a>'


def table(first_month="", year=2023, month_count=12):
    cells = "<td>" + first_month + "</td>" + "<td></td>" * (month_count - 1)
    return f'<table class="m-tbl-nml"><tbody><tr><th>{year}</th>{cells}</tr></tbody></table>'


class OriginalArchiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data, cls.parser = IMPORTER.parse_timeline(IMPORTER.SOURCE.read_text(encoding="utf-8"))

    def test_every_historical_record_is_preserved(self):
        # Snapshot includes every original year/month, Japanese name, image and URL,
        # so shifting even one date/cell or losing a paired release fails the test.
        fields = ["year", "month", "name", "image", "url"]
        records = [{key: item[key] for key in fields} for item in self.data["sets"]]
        digest = hashlib.sha256(json.dumps(records, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        self.assertEqual(digest, "bb081b266c6a04f6dbf34d8d30a033e3b77166e76d4a1cca2fe6a0997f38d2c1")
        self.assertEqual(len(records), 186)
        self.assertEqual(self.data["years"], list(range(1996, 2027)))
        self.assertEqual(self.data["metadata"]["coverageStart"], "1996-10")
        self.assertEqual(self.data["metadata"]["coverageEnd"], "2026-09")

    def test_import_command_is_reproducible(self):
        # The editable production dataset may grow. Pin the archive import,
        # not the current editorial record count.
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "card-sets.json"
            subprocess.run([sys.executable, str(ROOT / "scripts/import-timeline.py"), "--output", str(output)], check=True, capture_output=True)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), self.data)

    def test_ids_assets_and_links(self):
        sets = self.data["sets"]
        self.assertEqual(len({item["id"] for item in sets}), 186)
        self.assertEqual(sum(item["url"] is not None for item in sets), 39)
        for item in sets:
            self.assertTrue((ROOT / item["image"].lstrip("/")).is_file(), item["image"])
            self.assertTrue(item["url"] is None or item["url"].startswith("https://"))
        occupancy = Counter(Counter((item["year"], item["month"]) for item in sets).values())
        self.assertEqual(occupancy, {1: 121, 2: 31, 3: 1})

    def test_baseline_is_measured_from_archive(self):
        measured = IMPORTER.audit(IMPORTER.SOURCE, self.parser, self.data)
        self.assertEqual(measured["htmlBytes"], 93391)
        self.assertEqual(measured["imageTags"], 191)
        self.assertEqual(measured["referencedImageBytes"], 192957452)
        self.assertEqual(measured["missingImages"], [])


class ImportEdgeCaseTests(unittest.TestCase):
    def test_comments_and_unrelated_images_are_ignored(self):
        html = '<img src="/unrelated.png" alt="Decoration">' + table(package())
        html += "<!--" + table(package("SV2"), year=2027) + "-->"
        data, _ = IMPORTER.parse_timeline(html)
        self.assertEqual(len(data["sets"]), 1)
        self.assertEqual(data["years"], [2023])

    def test_pairs_entities_and_empty_links(self):
        data, _ = IMPORTER.parse_timeline(table(package(name="A &amp; B") + package("SV1V", href="")))
        self.assertEqual([item["name"] for item in data["sets"]], ["A & B", "スカーレットex"])
        self.assertEqual([item["month"] for item in data["sets"]], [1, 1])
        self.assertEqual([item["url"] for item in data["sets"]], [None, None])

    def test_code_retains_source_case(self):
        data, _ = IMPORTER.parse_timeline(table(package("sv7a-key")))
        self.assertEqual(data["sets"][0]["code"], "sv7a")

    def test_bad_month_count_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "expected 12 months"):
            IMPORTER.parse_timeline(table(package(), month_count=11))

    def test_duplicate_release_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Duplicate release identity"):
            IMPORTER.parse_timeline(table(package() + package()))

    def test_unsafe_link_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unsafe"):
            IMPORTER.parse_timeline(table(package(href="javascript:alert(1)")))

    def test_unknown_era_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unknown era"):
            IMPORTER.parse_timeline(table(package(era="UNKNOWN")))

    def test_missing_name_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Missing release name"):
            IMPORTER.parse_timeline(table(package(name="")))

    def test_merged_cells_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "Merged timeline cells"):
            IMPORTER.parse_timeline(table(package()).replace("<td>", '<td colspan="2">', 1))

    def test_unclosed_table_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "complete timeline table"):
            IMPORTER.parse_timeline(table(package()).replace("</table>", ""))

    def test_no_timeline_table_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "complete timeline table"):
            IMPORTER.parse_timeline("<p>No timeline</p>")


if __name__ == "__main__":
    unittest.main()

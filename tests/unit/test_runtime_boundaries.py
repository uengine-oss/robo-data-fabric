from __future__ import annotations

import csv
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
SPEC = REPO / "specs" / "005-runtime-boundaries"


class RuntimeBoundaryTest(unittest.TestCase):
    def test_every_audited_runtime_folder_exists(self) -> None:
        with (SPEC / "folder-audit.tsv").open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream, delimiter="\t"))
        self.assertTrue(rows)
        self.assertEqual(len(rows), len({row["path"] for row in rows}))
        for row in rows:
            self.assertTrue((REPO / row["path"]).is_dir(), row["path"])


if __name__ == "__main__":
    unittest.main()

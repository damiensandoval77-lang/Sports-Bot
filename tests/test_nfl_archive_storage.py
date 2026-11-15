"""Lossless NFL history migration, append and repeated-run safeguards."""
import csv
import gzip
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import reconcile_nfl_picks as r

class StorageTests(unittest.TestCase):
    def test_migration_append_and_idempotence(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/r.ARCHIVE.name
            rows=[{"player":"José", "line":"12.5"}]
            fields=["player","line"]
            r.write_csv_if_changed(path,rows,fields)
            original=path.read_bytes()
            with patch.object(r,"ARCHIVE_COMPRESS_BYTES",1):
                self.assertTrue(r.write_csv_if_changed(path,rows,fields))
            gz=path.with_suffix(".csv.gz")
            self.assertFalse(path.exists())
            self.assertEqual(gzip.decompress(gz.read_bytes()),original)
            self.assertEqual(r.read_csv(path),rows)
            rows.append({"player":"Another", "line":"11.5"})
            self.assertTrue(r.write_csv_if_changed(path,rows,fields))
            self.assertEqual(r.read_csv(path),rows)
            before=gz.read_bytes()
            self.assertFalse(r.write_csv_if_changed(path,rows,fields))
            self.assertEqual(before,gz.read_bytes())
    def test_ambiguous_and_corrupt_archives_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/r.ARCHIVE.name
            gz=path.with_suffix(".csv.gz")
            gz.write_bytes(b"bad gzip")
            with self.assertRaises(OSError):r.read_csv(path)
            path.write_text("player\nold\n")
            with self.assertRaises(ValueError):r.read_csv(path)
if __name__=="__main__":unittest.main()

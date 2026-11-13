"""No-token/network tests for secure private-to-public NFL snapshot transfer."""
import csv
import io
import json
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from sync_private_nfl_snapshot import sync,validate_payload
CAPTURE="2026-11-09T17:00:00+00:00"
NAME="latest_2026_00.csv"
def payload(rows=8,capture=CAPTURE):
    data=[]
    for i in range(rows):
        data.append(dict(captured_at=capture,game_id=f"g{i%2}",player_id=f"p{i}",
            target="REC_YDS",line="60.5",projection_id=f"quote{i}",
            pick="More",model_pct="58"))
    out=io.StringIO()
    writer=csv.DictWriter(out,fieldnames=list(data[0]))
    writer.writeheader();writer.writerows(data)
    manifest={"season":2026,"captured_at":capture,"rows":rows,"files":[NAME]}
    return {NAME:out.getvalue().encode(),
            "latest_2026.json":json.dumps(manifest).encode()}
class TestNFLSync(unittest.TestCase):
    def test_atomic_verified_copy_and_idempotence(self):
        with tempfile.TemporaryDirectory() as folder:
            data=payload()
            out=Path(folder)
            self.assertTrue(sync(lambda n:data[n],out)["changed"])
            self.assertEqual(json.loads((out/"latest_2026.json").read_text())["rows"],8)
            original=(out/NAME).read_bytes()
            self.assertFalse(sync(lambda n:data[n],out)["changed"])
            self.assertEqual(original,(out/NAME).read_bytes())
    def test_archives_old_snapshot_before_rotation_and_failure_blocks_copy(self):
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder);old=payload();sync(lambda n:old[n],out)
            (out/"schedule_2026.json").write_text("{}")
            newer=payload(capture="2026-11-10T17:00:00+00:00")
            seen=[]
            def archive(root):
                seen.append(json.loads((root/"latest_2026.json").read_text())["captured_at"])
            with patch("reconcile_nfl_picks.run",side_effect=archive):
                sync(lambda n:newer[n],out)
            self.assertEqual(seen,[CAPTURE])
            newer2=payload(capture="2026-11-11T17:00:00+00:00")
            before=(out/NAME).read_bytes()
            with patch("reconcile_nfl_picks.run",side_effect=ValueError("archive failed")):
                with self.assertRaisesRegex(ValueError,"archive failed"):
                    sync(lambda n:newer2[n],out)
            self.assertEqual((out/NAME).read_bytes(),before)

    def test_bad_new_chunk_preserves_last_good(self):
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder)
            data=payload()
            sync(lambda n:data[n],out)
            previous=(out/"latest_2026.json").read_bytes()
            newer=payload(capture="2026-11-10T17:00:00+00:00")
            newer[NAME]=newer[NAME].replace(b"60.5",b"INVALID")
            with self.assertRaisesRegex(ValueError,"Invalid frozen line"):
                sync(lambda n:newer[n],out)
            self.assertEqual(previous,(out/"latest_2026.json").read_bytes())
    def test_partial_chunk_blocks_publication(self):
        data=payload()
        data["latest_2026.json"]=json.dumps({"season":2026,
            "captured_at":CAPTURE,"rows":9,"files":[NAME]}).encode()
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError,"Incomplete private NFL capture"):
                sync(lambda n:data[n],Path(folder))
            self.assertFalse((Path(folder)/"latest_2026.json").exists())
    def test_file_traversal_rejected_before_download(self):
        with tempfile.TemporaryDirectory() as folder:
            data={"latest_2026.json":json.dumps({"season":2026,
                "captured_at":CAPTURE,"rows":8,
                "files":["../../secrets.csv"]}).encode()}
            with self.assertRaisesRegex(ValueError,"Unsafe chunk names"):
                sync(lambda n:data[n],Path(folder))
    def test_invalid_identity_rejected(self):
        data=payload()
        data[NAME]=data[NAME].replace(b"quote0",b"")
        manifest=json.loads(data["latest_2026.json"].decode())
        with self.assertRaisesRegex(ValueError,"Blank NFL frozen prediction identity"):
            validate_payload(manifest,{NAME:data[NAME]})
if __name__=="__main__":
    unittest.main()

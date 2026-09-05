#!/usr/bin/env python3
"""Round-trip verification of bundle v3 fetched from the live GitHub raw URLs.

Fetches bundle/INDEX.json + all 59 shards from raw.githubusercontent.com,
re-assembles every tracked file per the parts-v3 protocol (parts grouped by
path, ordered by seq, text concatenated), and compares byte-for-byte against
the local git working tree. Prints per-file PASS/FAIL and a final verdict.
"""
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

REPO = Path("/home/z/my-project/peach-goma-project")
RAW_BASE = ("https://raw.githubusercontent.com/"
            "SonaMother/peach-goma-skyhop-3d-cat-platformer/main")

def fetch(rel: str) -> bytes:
    with urllib.request.urlopen(f"{RAW_BASE}/{rel}", timeout=30) as r:
        return r.read()

def main() -> int:
    index = json.loads(fetch("bundle/INDEX.json").decode("utf-8"))
    files_meta = {f["path"]: f for f in index["files"]}
    print(f"layout={index['layout']}  shards={len(index['shards'])}  files={len(files_meta)}")

    # fetch every shard (JSON decodes the \u003c-style escapes automatically)
    parts_by_file: dict[str, list] = {}
    worst = 0
    for entry in index["shards"]:
        fname = entry["file"]
        raw = fetch(f"bundle/{fname}")
        worst = max(worst, len(raw))
        shard = json.loads(raw.decode("utf-8"))
        for p in shard["parts"]:
            parts_by_file.setdefault(p["path"], []).append(p)
    print(f"all {len(index['shards'])} shards fetched; largest on wire = {worst} B (cap 8192)")

    fails = 0
    for path, fmeta in files_meta.items():
        plist = sorted(parts_by_file[path], key=lambda p: p["seq"])
        got = "".join(p["text"] for p in plist).encode("utf-8")
        local = (REPO / path).read_bytes()

        part_sha_ok = all(
            hashlib.sha256(p["text"].encode("utf-8")).hexdigest() == p["sha256"]
            for p in plist)
        ok = (len(plist) == fmeta["parts"]
              and len(got) == fmeta["bytes"]
              and hashlib.sha256(got).hexdigest() == fmeta["sha256"]
              and got == local
              and part_sha_ok)
        if not ok:
            fails += 1
            print(f"  FAIL  {path}: parts {len(plist)}/{fmeta['parts']}, "
                  f"bytes {len(got)}/{fmeta['bytes']}/{len(local)}, "
                  f"sha_ok={part_sha_ok}, "
                  f"match_local={got == local}")
        else:
            print(f"  PASS  {path}  ({fmeta['bytes']} B, {fmeta['parts']} part(s))")

    print(f"\nVERDICT: {len(files_meta) - fails}/{len(files_meta)} files byte-identical "
          f"to local working tree")
    return 1 if fails else 0

if __name__ == "__main__":
    sys.exit(main())

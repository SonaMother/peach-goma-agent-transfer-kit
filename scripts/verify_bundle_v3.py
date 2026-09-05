#!/usr/bin/env python3
"""Round-trip verification of bundle v3 (parts-v3 JSON shards).

local:  reassembles every file from bundle/ on disk and byte-compares
        against the local git working tree (run BEFORE pushing).
remote: fetches bundle/INDEX.json + all shards from raw.githubusercontent.com
        first, then reassembles and byte-compares (run AFTER pushing).

Usage:
  python3 verify_bundle_v3.py local  --repo-dir /path/to/project
  python3 verify_bundle_v3.py remote --repo-dir /path/to/project \
      --gh-repo Owner/name [--branch main]
"""
import argparse
import hashlib
import json
import urllib.request
from pathlib import Path


def parse_args():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("mode", choices=["local", "remote"])
    p.add_argument("--repo-dir", required=True, type=Path)
    p.add_argument("--gh-repo", default=None, metavar="OWNER/NAME",
                   help="required for remote mode")
    p.add_argument("--branch", default="main")
    return p.parse_args()


args = parse_args()
REPO: Path = args.repo_dir
BUNDLE = REPO / "bundle"


def fetch(rel: str) -> bytes:
    base = (f"https://raw.githubusercontent.com/{args.gh_repo}/{args.branch}")
    with urllib.request.urlopen(f"{base}/{rel}", timeout=30) as r:
        return r.read()


def read(rel: str) -> bytes:
    if args.mode == "remote":
        return fetch(rel)
    return (BUNDLE / rel.split("/", 1)[1]).read_bytes()


def main() -> int:
    if args.mode == "remote" and not args.gh_repo:
        raise SystemExit("remote mode requires --gh-repo OWNER/NAME")
    index = json.loads(read("bundle/INDEX.json").decode("utf-8"))
    files_meta = {f["path"]: f for f in index["files"]}
    print(f"mode={args.mode}  layout={index['layout']}  "
          f"shards={len(index['shards'])}  files={len(files_meta)}")

    # load every shard (JSON decoding handles \u003c-style escapes)
    parts_by_file: dict[str, list] = {}
    worst = 0
    for entry in index["shards"]:
        fname = entry["file"]
        raw = read(f"bundle/{fname}")
        worst = max(worst, len(raw))
        shard = json.loads(raw.decode("utf-8"))
        for p in shard["parts"]:
            parts_by_file.setdefault(p["path"], []).append(p)
    print(f"all {len(index['shards'])} shards loaded; largest on wire = {worst} B (cap 8192)")

    fails = 0
    for path, fmeta in sorted(files_meta.items()):
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
    raise SystemExit(main())

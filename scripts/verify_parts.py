#!/usr/bin/env python3
"""verify_parts.py - round-trip verification for the "simple parts" channel.

Reassembles every file from parts/ (raw) and parts-esc/ (escaped) and
compares byte-for-byte against the local git working tree.

Usage:
  python3 verify_parts.py local --repo-dir /path/to/project \
      --gh-repo Owner/name [--branch main]
  python3 verify_parts.py remote --repo-dir /path/to/project \
      --gh-repo Owner/name [--branch main]   # fetch parts from GitHub raw
"""
import argparse
import hashlib
import urllib.request
from pathlib import Path

ESC_MAP = {r"\u003c": "<", r"\u003e": ">", r"\u0026": "&"}
HDR_MARK = "[PART "


def parse_args():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("mode", choices=["local", "remote"])
    p.add_argument("--repo-dir", required=True, type=Path)
    p.add_argument("--gh-repo", required=True, metavar="OWNER/NAME")
    p.add_argument("--branch", default="main")
    return p.parse_args()


ARGS = parse_args()
REPO: Path = ARGS.repo_dir
RAW_BASE = (f"https://raw.githubusercontent.com/"
            f"{ARGS.gh_repo}/{ARGS.branch}")


def fetch(rel: str) -> bytes:
    with urllib.request.urlopen(f"{RAW_BASE}/{rel}", timeout=30) as r:
        return r.read()


def unesc(s: str) -> str:
    for k, v in ESC_MAP.items():
        s = s.replace(k, v)
    return s


def read_parts(d: Path) -> dict[str, list[tuple[int, int, str]]]:
    """returns {target_path: [(k, n, content)]} parsed from part files."""
    out = {}
    for f in sorted(d.glob("*.txt")):
        text = f.read_bytes().decode("utf-8")
        first_nl = text.index("\n")
        header, body = text[:first_nl], text[first_nl + 1:]
        assert header.startswith(HDR_MARK), f"{f.name}: bad header"
        inner = header[len(HDR_MARK):-1]
        kn, path_part = inner.rsplit(" | ", 1)
        k_of = kn.split(" of ")
        k, n = int(k_of[0]), int(k_of[1])
        out.setdefault(path_part, []).append((k, n, body))
    return out


def verify(d: Path, escape: bool, src_mode: str) -> int:
    parts = read_parts(d)
    if src_mode == "remote":
        # re-fetch from remote into memory instead of using disk copies
        names = [p.name for p in sorted(d.glob("*.txt"))]
        parts = {}
        for name in names:
            text = fetch(f"{d.name}/{name}").decode("utf-8")
            first_nl = text.index("\n")
            header, body = text[:first_nl], text[first_nl + 1:]
            inner = header[len(HDR_MARK):-1]
            kn, path_part = inner.rsplit(" | ", 1)
            k, n = (int(x) for x in kn.split(" of ")[0:2])
            parts.setdefault(path_part, []).append((k, n, body))

    fails = 0
    for path, plist in sorted(parts.items()):
        plist.sort(key=lambda t: t[0])
        n = plist[0][1]
        assert all(p[1] == n for p in plist), f"{path}: inconsistent n"
        assert [p[0] for p in plist] == list(range(1, n + 1)), f"{path}: seq gap"
        text = "".join(p[2] for p in plist)
        if escape:
            text = unesc(text)
        got = text.encode("utf-8")
        local = (REPO / path).read_bytes()
        ok = got == local
        if not ok:
            fails += 1
            print(f"  FAIL  {path}: got {len(got)} B vs local {len(local)} B, "
                  f"sha_got={hashlib.sha256(got).hexdigest()[:12]}, "
                  f"sha_loc={hashlib.sha256(local).hexdigest()[:12]}")
        else:
            print(f"  PASS  {path}  ({len(local):,} B, {n} part(s))")
    missing = 0
    print(f"  => {'esc' if escape else 'raw'} set: "
          f"{len(parts) - fails}/{len(parts)} files byte-identical")
    return fails


def main() -> int:
    mode = ARGS.mode
    print(f"mode={mode}  repo={ARGS.gh_repo}@{ARGS.branch}")
    f1 = verify(REPO / "parts", escape=False, src_mode=mode)
    f2 = verify(REPO / "parts-esc", escape=True, src_mode=mode)
    total = f1 + f2
    print(f"\nVERDICT: {'ALL PASS' if total == 0 else f'{total} FAILURES'} "
          f"(both sets, {mode})")
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main())

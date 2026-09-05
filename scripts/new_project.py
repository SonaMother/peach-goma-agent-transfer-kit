#!/usr/bin/env python3
"""new_project.py - one command to prepare ANY git repo for AI-agent transfer.

Runs, in order:
  1. make_simple_parts.py     -> parts/ + parts-esc/ + PARTS_INDEX.md
  2. make_recreate_bundle.py  -> RECREATE_PROJECT.md (single-file bundle)
  3. make_json_shards_v2.py   -> bundle/INDEX.json + shard-*.json (<=8KB each)
  4. make_agent_prompt.py     -> AGENT_PROMPT.txt (the hand-off file agents read)
  5. verify_parts.py local    -> byte-compare both part sets against sources
  6. verify_bundle_v3.py local-> byte-compare JSON bundle against sources

Then prints the publish checklist (commit, push, verify remote, hand-off URL).

Usage:
  python3 new_project.py --repo-dir /path/to/project --gh-repo Owner/name \
      [--branch main] [--project-name "My Project"] \
      [--install-cmd "npm install"] [--run-cmd "npm run dev"] \
      [--fabrication-tell "..."] [--exclude extra.bin] ...
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def parse_args():
    import argparse
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--repo-dir", required=True, type=Path)
    p.add_argument("--gh-repo", required=True, metavar="OWNER/NAME")
    p.add_argument("--branch", default="main")
    p.add_argument("--project-name", default=None)
    p.add_argument("--install-cmd", default="npm install")
    p.add_argument("--run-cmd", default="npm run dev")
    p.add_argument("--fabrication-tell", default="")
    p.add_argument("--exclude", action="append", default=[])
    return p.parse_args()


def run(script: str, *argv: str) -> None:
    print(f"\n=== {script} {' '.join(argv)}")
    subprocess.run([sys.executable, str(HERE / script), *argv], check=True)


def main() -> int:
    a = parse_args()
    repo: Path = a.repo_dir.resolve()
    if not (repo / ".git").exists():
        raise SystemExit(f"ERROR: {repo} is not a git working tree")
    if a.gh_repo.count("/") != 1:
        raise SystemExit("ERROR: --gh-repo must be OWNER/NAME")

    base = ["--repo-dir", str(repo), "--gh-repo", a.gh_repo,
            "--branch", a.branch]
    named = base + (["--project-name", a.project_name]
                    if a.project_name else [])
    if a.fabrication_tell:
        named += ["--fabrication-tell", a.fabrication_tell]
    iorun = ["--install-cmd", a.install_cmd, "--run-cmd", a.run_cmd]
    excl = []
    for x in a.exclude:
        excl += ["--exclude", x]

    run("make_simple_parts.py", *base, *iorun, *excl)
    run("make_recreate_bundle.py", *named)
    run("make_json_shards_v2.py", *named)
    run("make_agent_prompt.py", *named, *iorun)

    print("\n" + "=" * 70)
    print("LOCAL VERIFICATION")
    print("=" * 70)
    run("verify_parts.py", "local", *base)
    run("verify_bundle_v3.py", "local", "--repo-dir", str(repo))

    print("\n" + "=" * 70)
    print("PUBLISH CHECKLIST")
    print("=" * 70)
    print(f"""1. Review the generated files in {repo}:
       parts/  parts-esc/  bundle/  PARTS_INDEX.md  AGENT_PROMPT.txt
       RECREATE_PROJECT.md
2. Commit and push (from {repo}):
       git add -A
       git commit -m "AI-agent transfer files: parts, bundle, guides"
       git push origin {a.branch}
3. Verify the live remote (after push):
       python3 {HERE / 'verify_parts.py'} remote --repo-dir {repo} --gh-repo {a.gh_repo} --branch {a.branch}
       python3 {HERE / 'verify_bundle_v3.py'} remote --repo-dir {repo} --gh-repo {a.gh_repo} --branch {a.branch}
4. Give every agent EXACTLY ONE URL (nothing else):
       https://raw.githubusercontent.com/{a.gh_repo}/{a.branch}/AGENT_PROMPT.txt
5. Re-run this generator whenever a source file changes - the parts must
   never go stale (a stale part table silently corrupts reconstructions).""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

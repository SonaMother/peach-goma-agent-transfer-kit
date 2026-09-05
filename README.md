# AI-Agent Repo Transfer Kit

The scripts, rules, and guides that ship a code repository through **fragile
AI-agent web fetchers** - agents that cannot `git clone`, cannot unzip, cannot
run code, and whose only capability is: *fetch a URL, read the text, hand-write
files*.

Proven in production: after 3 failed transfer attempts (mangled JSX, collapsed
newlines, silent truncation, and fabricated success reports), a 4th agent
rebuilt the target repo **byte-exact, 34/34 files**, using the channel and
rules in this kit.

- Target repo: https://github.com/SonaMother/peach-goma-skyhop-3d-cat-platformer
- Handoff URL given to agents:
  `https://raw.githubusercontent.com/SonaMother/peach-goma-skyhop-3d-cat-platformer/main/AGENT_PROMPT.txt`

## The problem, in one paragraph

Web-only AI agents fetch URLs through a lossy pipeline. Observed damage across
agents: (a) HTML-like tag stripping - every `<div>`, `<Canvas>`, even `&&`
disappears, also inside JSON bodies; (b) newline collapsing - lines merge, so
indentation and line structure are destroyed; (c) size truncation - responses
cut off around 4-8 KB; (d) no HTTP headers - custom `Accept:` headers cannot be
sent; (e) no base64 decoder. None of this is visible to the agent, which is
why the worst failure mode is not breakage but **confident fabrication**
(invented hashes, invented files, claimed success).

## Repo map

| Path | What it is |
|---|---|
| `guides/AGENT_PROMPT.txt` | The instruction sheet handed to agents first: calibrate, pick channel, anti-hallucination rules, mandatory honest final report |
| `guides/PARTS_INDEX.md` | Self-calibrating walk instructions for the fetch-only "simple parts" channel (probes + THE LOOP + part table + anchors) |
| `scripts/make_simple_parts.py` | Generator: splits every tracked source file into `parts/` (raw) + `parts-esc/` (escaped) + builds `PARTS_INDEX.md` |
| `scripts/verify_parts.py` | Verifier: reassembles both part sets and byte-compares to source, locally or fetched from the live remote |
| `scripts/make_json_shards_v2.py` | Generator: bundle v3 - single-line, tag-proof JSON shards (<= 8 KB wire) for newline-collapsing fetchers (channel F) |
| `scripts/verify_bundle_v3.py` | Verifier: fetches the live JSON bundle from GitHub raw, reassembles, byte-compares |
| `scripts/make_recreate_bundle.py` | Generator: single-file markdown bundle (only for fetchers that do NOT strip tags) |

The channels, in the order agents are told to try:

| Channel | Requires | Exact? |
|---|---|---|
| A. `npm pack github:user/repo` | npm/shell | byte-exact, one command |
| B. `git clone` | git | byte-exact |
| C. Contents API + base64 decode | code execution | byte-exact (fetch-only agents: unusable - needs header or decoder) |
| D. `parts/` walk | fetcher keeps `< > &` and newlines | byte-exact |
| E. `parts-esc/` walk | fetcher strips tags but keeps newlines | byte-exact after 3 replace-alls |
| F. `bundle/INDEX.json` shards | fetcher collapses newlines too | byte-exact after JSON parse |

## Design rules (the part that actually matters)

1. **Calibrate before trusting.** `PARTS_INDEX.md` STEP 0 embeds a tag probe
   and a newline probe. The agent measures its own fetcher and routes itself
   to the right channel - we never assume which lane works.
2. **Escape, don't avoid.** `parts-esc/` stores `< > &` as `\u003c \u003e
   \u0026`, so tag-strippers find nothing to strip. The generator asserts no
   source file already contains those literal sequences (ambiguity guard).
3. **Cap in bytes AND lines.** Every part is <= 100 lines and <= 4,000 bytes
   *on the wire* (UTF-8). Byte caps dominate character caps (bytes >= chars
   for UTF-8), so the limit holds whether a fetcher counts bytes or
   characters; the line cap exists because some pipelines are line-oriented.
4. **Write as you read.** One fetch = one part = create-or-append. The agent
   never holds whole files in memory, never rewrites from memory.
5. **Verification is separate code.** Verifiers re-parse part headers,
   re-assemble, and byte-compare against the working tree - locally and again
   from the live remote. Builders are never trusted.
6. **Anchors instead of trust.** Known byte sizes and first-line contents
   (e.g. `index.html` is 783 bytes and Vite-style; a CRA-style `%PUBLIC_URL%`
   means the agent fabricated it).
7. **Honest failure beats fake success.** The rules forbid claiming success
   without printing a verification value, and the final report template forces
   explicit OK/FAIL per gate.

## Adapting to another repository

1. In each script, edit the constants at the top: `REPO` (path to your local
   working clone) and, in the verifiers, `RAW_BASE` (your repo's raw URL).
2. Review the exclusion sets (`EXCLUDE_FILES` / `EXCLUDE`) - lockfiles and
   agent-meta files should not be shopped as parts.
3. `python3 scripts/make_simple_parts.py` then
   `python3 scripts/verify_parts.py local`.
4. Commit and push everything the generators wrote, then
   `python3 scripts/verify_parts.py remote` against the live site.
5. Give agents `AGENT_PROMPT.txt` (raw URL), nothing else.

Note: `package-lock.json` is intentionally excluded everywhere - `npm install`
regenerates it, and it alone would roughly double the transfer.

## Historical note

`make_json_shards.py` (v1, plain-JSON shards up to 123 KB) is intentionally
not included: agent #2 proved single responses get truncated far below that
size, and v3 (shards <= 8 KB, zero raw `< > &`, single-line) superseded it.
Keep only what survived contact with real fetchers.

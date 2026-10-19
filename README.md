# hustle-name-shortlist

Domain / brand-name shortlists for founders — Tier 0 hustle MVP.

Generate ~50 name candidates from niche + vibe keywords, apply light trademark-ish heuristics (**not legal advice**), check free DNS/A-record hints (no paid WHOIS), and write a Markdown one-pager to `out/shortlist.md`.

## Requirements

- Python 3.11+
- Optional: `OPENAI_API_KEY` for LLM name generation (falls back to a combinatorial/template generator)

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp config.example.yaml config.yaml
```

## Run

CLI args:

```bash
python -m src --niche "developer tools" --vibe "calm,premium,playful"
```

Or via config:

```bash
cp config.example.yaml config.yaml
# edit niche / vibe
python -m src
```

Useful flags:

| Flag | Meaning |
|------|---------|
| `--count 50` | Number of candidates |
| `--tlds com,io,ai` | TLDs for DNS A-record hints |
| `--out out/shortlist.md` | Output path |
| `--skip-dns` | Skip DNS (fast offline demo) |
| `--no-config` | Ignore `config.yaml` |

## Output

- **`out/shortlist.md`** — ranked table with heuristic TM risk, flags, and DNS hints

## Environment

| Variable | Required | Purpose |
|----------|----------|---------|
| `OPENAI_API_KEY` | No | If set, names are generated via OpenAI; otherwise combinatorial templates |
| `OPENAI_MODEL` | No | Defaults to `gpt-4o-mini` |

## Compliance notes

- DNS lookups use public resolvers via `dnspython` (A records only).
- No paid WHOIS/availability API in v1.
- Heuristics are **not** trademark clearance. Do not treat this as legal advice.
- Human curation is expected — naming is taste-driven.

## Project layout

```
config.example.yaml
requirements.txt
src/
  __main__.py
  cli.py
  generate.py
  heuristics.py
  dns_check.py
  render.py
out/
  .gitkeep
```

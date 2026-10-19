# hustle-name-shortlist

Domain / brand-name shortlists for founders — Tier 0 hustle MVP.

Generate ~50 name candidates from niche + vibe keywords, apply light trademark-ish heuristics (**not legal advice**), check free DNS/A-record hints (no paid WHOIS), write `out/shortlist.md`, then **human-approve** and **export** a client-ready Markdown/HTML pack + mailto draft under `out/export/`.

**No auto-email.** Export only writes files and a `mailto:` URI for you to open manually.

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

## Workflow

```text
generate → out/shortlist.md → human approve → out/export/ (md + html + mailto)
```

### 1. Generate

```bash
python -m src --niche "developer tools" --vibe "calm,premium,playful" --skip-dns
# or: python -m src generate --niche "developer tools" --vibe "calm,premium,playful"
```

### 2. Human approve

Review `out/shortlist.md`, then stamp approval (content hash locked):

```bash
python -m src approve
# optional: python -m src approve --note "trimmed to playful stems" --force
python -m src approve --check
```

Writes `out/shortlist.approved.json`. Editing the shortlist after approve invalidates the stamp.

### 3. Export client delivery (no send)

```bash
python -m src export --to client@example.com --client-name "Alex"
```

Writes under `out/export/`:

| File | Purpose |
|------|---------|
| `delivery.md` | Client-ready Markdown one-pager |
| `delivery.html` | HTML for paste / static preview |
| `mailto.txt` | `mailto:` URI draft — **does not send** |
| `README.txt` | What each file is |

Export refuses unapproved shortlists unless `--allow-unapproved` (demo only).

## Useful generate flags

| Flag | Meaning |
|------|---------|
| `--count 50` | Number of candidates |
| `--tlds com,io,ai` | TLDs for DNS A-record hints |
| `--out out/shortlist.md` | Output path |
| `--skip-dns` | Skip DNS (fast offline demo) |
| `--no-config` | Ignore `config.yaml` |

## Environment

| Variable | Required | Purpose |
|----------|----------|---------|
| `OPENAI_API_KEY` | No | If set, names are generated via OpenAI; otherwise combinatorial templates |
| `OPENAI_MODEL` | No | Defaults to `gpt-4o-mini` |

## Compliance notes

- DNS lookups use public resolvers via `dnspython` (A records only).
- No paid WHOIS/availability API in v1.
- Heuristics are **not** trademark clearance. **This is not legal advice.**
- Human curation + approval is required before client delivery.
- Mailto export never auto-sends mail.

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
  approve.py
  export_delivery.py
out/
  .gitkeep
  shortlist.md              # after generate
  shortlist.approved.json   # after approve
  export/                   # after export
    delivery.md
    delivery.html
    mailto.txt
```

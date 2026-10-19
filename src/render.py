"""Render Markdown shortlist artifact."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


DISCLAIMER = (
    "**Disclaimer:** This shortlist uses light trademark-ish heuristics and free "
    "DNS/A-record hints only. It is **not legal advice**, not a USPTO/EUIPO search, "
    "and not a guarantee of domain availability or trademark clearance. Always "
    "verify with a registrar and a qualified trademark attorney before use."
)


def render_shortlist(
    *,
    niche: str,
    vibe: list[str],
    mode: str,
    ranked: list[dict],
    dns_by_name: dict[str, list[dict]],
    tlds: list[str],
) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    vibe_str = ", ".join(vibe) if vibe else "(none)"
    lines = [
        "# Domain / brand-name shortlist",
        "",
        DISCLAIMER,
        "",
        f"- **Niche:** {niche}",
        f"- **Vibe:** {vibe_str}",
        f"- **Generator:** {mode}",
        f"- **TLDs checked (A records):** {', '.join('.' + t for t in tlds)}",
        f"- **Generated:** {now}",
        f"- **Candidates:** {len(ranked)}",
        "",
        "## Ranked candidates",
        "",
        "| # | Name | Score | TM risk (heuristic) | DNS hints | Flags |",
        "|---|------|------:|---------------------|-----------|-------|",
    ]

    for i, row in enumerate(ranked, start=1):
        name = row["name"]
        dns_rows = dns_by_name.get(name, [])
        dns_bits = []
        for d in dns_rows:
            label = {"has_a": "taken?", "no_a": "no A", "error": "err"}.get(
                d["status"], d["status"]
            )
            dns_bits.append(f"{d['domain']} ({label})")
        dns_cell = "; ".join(dns_bits) if dns_bits else "—"
        flags = ", ".join(row["flags"]) if row["flags"] else "—"
        lines.append(
            f"| {i} | `{name}` | {row['score']} | {row['tm_risk_heuristic']} "
            f"| {dns_cell} | {flags} |"
        )

    lines.extend(
        [
            "",
            "## How to use",
            "",
            "1. Skim **low** TM-risk rows with **no A** DNS hints.",
            "2. Confirm registration at a registrar (Namecheap, Cloudflare, Google Domains successors, etc.).",
            "3. Run a real trademark search before shipping under the brand.",
            "4. Curate to 3–5 favorites — naming is taste-driven.",
            "",
            "## Notes",
            "",
            "- `no A` only means no IPv4 address in public DNS; the domain may still be registered.",
            "- Blocklist and scoring are deliberately shallow for a free MVP loop.",
            "",
        ]
    )
    return "\n".join(lines)


def write_shortlist(path: str | Path, content: str) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, encoding="utf-8")
    return out

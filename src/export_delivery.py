"""Client-ready Markdown/HTML + mailto export. Never sends email."""

from __future__ import annotations

import argparse
import html
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from .approve import is_approved

CLIENT_DISCLAIMER = (
    "**Disclaimer (not legal advice):** This shortlist uses light trademark-ish "
    "heuristics and free DNS/A-record hints only. It is **not legal advice**, "
    "not a USPTO/EUIPO search, and not a guarantee of domain availability or "
    "trademark clearance. Always verify with a registrar and a qualified "
    "trademark attorney before use."
)

HTML_DISCLAIMER = (
    "<strong>Disclaimer (not legal advice):</strong> This shortlist uses light "
    "trademark-ish heuristics and free DNS/A-record hints only. It is "
    "<strong>not legal advice</strong>, not a USPTO/EUIPO search, and not a "
    "guarantee of domain availability or trademark clearance. Always verify "
    "with a registrar and a qualified trademark attorney before use."
)


def _extract_meta(md: str) -> dict[str, str]:
    meta: dict[str, str] = {}
    for key in ("Niche", "Vibe", "Generator", "Generated", "Candidates"):
        m = re.search(rf"-\s+\*\*{key}:\*\*\s+(.+)$", md, re.MULTILINE)
        if m:
            meta[key.lower()] = m.group(1).strip()
    return meta


def build_client_markdown(source_md: str, *, client_name: str = "") -> str:
    """Wrap approved shortlist as a client-facing delivery one-pager."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    meta = _extract_meta(source_md)
    greeting = f"Hi {client_name}," if client_name else "Hi,"
    # Strip the internal disclaimer block if present; we restate client-facing.
    body = source_md.strip()
    body = re.sub(
        r"\*\*Disclaimer:\*\*.*?(?=\n- \*\*Niche:|\n## )",
        "",
        body,
        count=1,
        flags=re.DOTALL,
    ).strip()

    lines = [
        "# Brand / domain name shortlist — delivery",
        "",
        greeting,
        "",
        "Here is your curated name shortlist pack. Please review the ranked "
        "table, pick 3–5 favorites, then confirm domains at a registrar and "
        "run a real trademark search before shipping under any brand.",
        "",
        CLIENT_DISCLAIMER,
        "",
        f"- **Niche:** {meta.get('niche', '(see shortlist)')}",
        f"- **Vibe:** {meta.get('vibe', '(see shortlist)')}",
        f"- **Exported:** {now}",
        f"- **Source candidates:** {meta.get('candidates', '—')}",
        "",
        "---",
        "",
        body,
        "",
        "---",
        "",
        "## Delivery notes",
        "",
        "- This file was exported after **human approval** of the draft shortlist.",
        "- No email was sent automatically — open the companion `mailto.txt` "
        "link if you want to paste into your mail client.",
        "- Naming is taste-driven; final curation stays with you.",
        "",
    ]
    return "\n".join(lines)


def markdown_to_simple_html(md: str, *, title: str = "Name shortlist") -> str:
    """Minimal Markdown→HTML for paste into email clients (no external deps)."""
    lines = md.splitlines()
    out: list[str] = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        f"<title>{html.escape(title)}</title>",
        "<style>",
        "body{font-family:Georgia,serif;line-height:1.5;max-width:52rem;",
        "margin:2rem auto;padding:0 1rem;color:#1a1a1a;}",
        "table{border-collapse:collapse;width:100%;font-size:0.95rem;}",
        "th,td{border:1px solid #ccc;padding:0.4rem 0.55rem;text-align:left;}",
        "th{background:#f4f4f4;}",
        "code{font-family:ui-monospace,Menlo,monospace;}",
        ".disclaimer{background:#fff8e6;border-left:4px solid #c90;padding:0.75rem 1rem;}",
        "hr{border:none;border-top:1px solid #ddd;margin:1.5rem 0;}",
        "</style>",
        "</head>",
        "<body>",
    ]

    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("# "):
            out.append(f"<h1>{html.escape(line[2:].strip())}</h1>")
        elif line.startswith("## "):
            out.append(f"<h2>{html.escape(line[3:].strip())}</h2>")
        elif line.startswith("---"):
            out.append("<hr>")
        elif line.startswith("|") and i + 1 < len(lines) and re.match(
            r"^\|[\s\-:|]+\|$", lines[i + 1]
        ):
            # table header + separator
            headers = [c.strip() for c in line.strip("|").split("|")]
            out.append("<table><thead><tr>")
            for h in headers:
                out.append(f"<th>{_inline_md(h)}</th>")
            out.append("</tr></thead><tbody>")
            i += 2  # skip separator
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip("|").split("|")]
                out.append("<tr>")
                for c in cells:
                    out.append(f"<td>{_inline_md(c)}</td>")
                out.append("</tr>")
                i += 1
            out.append("</tbody></table>")
            continue
        elif line.startswith("- "):
            out.append("<ul>")
            while i < len(lines) and lines[i].startswith("- "):
                out.append(f"<li>{_inline_md(lines[i][2:].strip())}</li>")
                i += 1
            out.append("</ul>")
            continue
        elif line.strip() == "":
            pass
        elif "not legal advice" in line.lower() or line.startswith("**Disclaimer"):
            out.append(f'<p class="disclaimer">{_inline_md(line)}</p>')
        else:
            out.append(f"<p>{_inline_md(line)}</p>")
        i += 1

    # Prefer the stronger HTML disclaimer block near the top if we already
    # rendered the MD disclaimer; also inject a canonical HTML version once.
    body = "\n".join(out)
    if 'class="disclaimer"' not in body:
        # Insert after first h1
        body = body.replace(
            "</h1>",
            f'</h1>\n<p class="disclaimer">{HTML_DISCLAIMER}</p>',
            1,
        )
    body += "\n</body>\n</html>\n"
    return body


def _inline_md(text: str) -> str:
    """Escape then apply a few inline Markdown patterns."""
    # Protect code spans first
    parts: list[str] = []
    last = 0
    for m in re.finditer(r"`([^`]+)`", text):
        parts.append(html.escape(text[last : m.start()]))
        parts.append(f"<code>{html.escape(m.group(1))}</code>")
        last = m.end()
    parts.append(html.escape(text[last:]))
    s = "".join(parts)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", s)
    return s


def build_mailto(
    *,
    to: str,
    subject: str,
    body: str,
) -> str:
    """Return a mailto: URI. Does not send mail."""
    # Keep body modest for client URI length limits
    max_body = 1800
    if len(body) > max_body:
        body = (
            body[:max_body]
            + "\n\n[…truncated — attach out/export/delivery.md or delivery.html…]"
        )
    return (
        f"mailto:{quote(to, safe='@.+_-')}?"
        f"subject={quote(subject)}&body={quote(body)}"
    )


def export_delivery(
    *,
    shortlist: Path,
    out_dir: Path,
    to: str = "",
    client_name: str = "",
    subject: str | None = None,
    require_approved: bool = True,
) -> dict[str, Path]:
    if require_approved:
        ok, reason = is_approved(shortlist)
        if not ok:
            raise RuntimeError(
                f"Export blocked: {reason}. "
                f"Run: python -m src approve --path {shortlist}"
            )

    source = shortlist.read_text(encoding="utf-8")
    client_md = build_client_markdown(source, client_name=client_name)
    client_html = markdown_to_simple_html(
        client_md, title="Brand / domain name shortlist"
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / "delivery.md"
    html_path = out_dir / "delivery.html"
    mailto_path = out_dir / "mailto.txt"
    readme_path = out_dir / "README.txt"

    md_path.write_text(client_md, encoding="utf-8")
    html_path.write_text(client_html, encoding="utf-8")

    meta = _extract_meta(source)
    niche = meta.get("niche", "your niche")
    subj = subject or f"Name shortlist pack — {niche}"
    mailto_body = (
        f"{'Hi ' + client_name + ',' if client_name else 'Hi,'}\n\n"
        f"Attached conceptually: your brand/domain name shortlist for {niche}.\n\n"
        "Open delivery.md or delivery.html from the export folder and paste "
        "into your message. This mailto link does not send automatically.\n\n"
        "Disclaimer: not legal advice — heuristics only; verify domains and "
        "trademarks before use.\n"
    )
    recipient = to.strip() or "client@example.com"
    mailto_uri = build_mailto(to=recipient, subject=subj, body=mailto_body)
    mailto_path.write_text(
        "\n".join(
            [
                "# Mailto draft (does NOT send email)",
                f"# To: {recipient}",
                f"# Subject: {subj}",
                "# Open this URI in a browser or mail client after human review.",
                "",
                mailto_uri,
                "",
            ]
        ),
        encoding="utf-8",
    )
    readme_path.write_text(
        "\n".join(
            [
                "Client delivery export",
                "======================",
                "",
                "Files:",
                "  delivery.md   — client-ready Markdown one-pager",
                "  delivery.html — HTML for paste into email / static host",
                "  mailto.txt    — mailto: URI draft (NO auto-send)",
                "",
                "This pack is not legal advice. Human-approved before export.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return {
        "md": md_path,
        "html": html_path,
        "mailto": mailto_path,
        "readme": readme_path,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="hustle-name-shortlist export",
        description=(
            "Export human-approved shortlist to out/export/ as Markdown, HTML, "
            "and a mailto: draft. Never sends email."
        ),
    )
    p.add_argument(
        "--path",
        type=Path,
        default=Path("out/shortlist.md"),
        help="Approved shortlist path (default: out/shortlist.md)",
    )
    p.add_argument(
        "--out-dir",
        type=Path,
        default=Path("out/export"),
        help="Export directory (default: out/export)",
    )
    p.add_argument(
        "--to",
        type=str,
        default="",
        help="Recipient for mailto: draft only (default: client@example.com)",
    )
    p.add_argument(
        "--client-name",
        type=str,
        default="",
        help="Optional client name for greeting",
    )
    p.add_argument(
        "--subject",
        type=str,
        default=None,
        help="Mailto subject override",
    )
    p.add_argument(
        "--allow-unapproved",
        action="store_true",
        help="Skip approval gate (demo only — not for real delivery)",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.path.exists():
        print(f"Missing {args.path}. Generate + approve first.", file=sys.stderr)
        return 2
    try:
        written = export_delivery(
            shortlist=args.path,
            out_dir=args.out_dir,
            to=args.to,
            client_name=args.client_name,
            subject=args.subject,
            require_approved=not args.allow_unapproved,
        )
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print("Exported client delivery (no email sent):")
    for key, path in written.items():
        print(f"  [{key}] {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

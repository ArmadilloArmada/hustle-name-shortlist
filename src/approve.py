"""Human approval gate for out/shortlist.md before client delivery."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

APPROVAL_FILENAME = "shortlist.approved.json"


def content_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def approval_path_for(shortlist: Path) -> Path:
    """Sidecar stamp next to the shortlist (out/shortlist.approved.json)."""
    return shortlist.parent / APPROVAL_FILENAME


def load_approval(stamp: Path) -> dict | None:
    if not stamp.exists():
        return None
    try:
        data = json.loads(stamp.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def is_approved(shortlist: Path, stamp: Path | None = None) -> tuple[bool, str]:
    """Return (ok, reason). Content hash must match the approval stamp."""
    stamp = stamp or approval_path_for(shortlist)
    if not shortlist.exists():
        return False, f"shortlist missing: {shortlist}"
    data = load_approval(stamp)
    if data is None:
        return False, f"no approval stamp at {stamp}"
    expected = data.get("sha256")
    actual = content_sha256(shortlist)
    if expected != actual:
        return False, (
            "shortlist changed since approval — re-run approve "
            f"(stamp={expected}, now={actual})"
        )
    recorded = data.get("path")
    if recorded and Path(recorded).resolve() != shortlist.resolve():
        # Allow relative path string mismatch if same resolved file
        if Path(str(recorded)).name != shortlist.name:
            return False, f"approval path mismatch: {recorded} vs {shortlist}"
    return True, f"approved at {data.get('approved_at', '?')}"


def write_approval(
    shortlist: Path,
    *,
    note: str = "",
    force: bool = False,
) -> Path:
    if not shortlist.exists():
        raise FileNotFoundError(f"Cannot approve missing file: {shortlist}")
    stamp = approval_path_for(shortlist)
    if stamp.exists() and not force:
        ok, reason = is_approved(shortlist, stamp)
        if ok:
            return stamp
    payload = {
        "path": str(shortlist.as_posix()),
        "sha256": content_sha256(shortlist),
        "approved_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "approver": "human",
        "note": note.strip(),
        "disclaimer": (
            "Human curation only. Heuristics are not legal advice, not trademark "
            "clearance, and not a guarantee of domain availability."
        ),
    }
    stamp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return stamp


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="hustle-name-shortlist approve",
        description=(
            "Record human approval of out/shortlist.md before export. "
            "Does not send email or publish anywhere."
        ),
    )
    p.add_argument(
        "--path",
        type=Path,
        default=Path("out/shortlist.md"),
        help="Shortlist Markdown to approve (default: out/shortlist.md)",
    )
    p.add_argument(
        "--note",
        type=str,
        default="",
        help="Optional curation note stored in the approval stamp",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing approval stamp",
    )
    p.add_argument(
        "--check",
        action="store_true",
        help="Only verify approval status (exit 0 if approved)",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    shortlist = args.path

    if args.check:
        ok, reason = is_approved(shortlist)
        print(reason)
        return 0 if ok else 1

    if not shortlist.exists():
        print(
            f"Missing {shortlist}. Generate first:\n"
            '  python -m src --niche "developer tools" --vibe "calm,premium"',
            file=sys.stderr,
        )
        return 2

    stamp = write_approval(shortlist, note=args.note, force=args.force)
    ok, reason = is_approved(shortlist, stamp)
    print(f"Approved {shortlist} → {stamp}")
    print(reason)
    print(
        "Next: python -m src export --to client@example.com "
        "(writes out/export/; does not send mail)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

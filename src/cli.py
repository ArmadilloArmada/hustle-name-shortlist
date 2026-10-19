"""CLI entry: niche + vibe → shortlist.md."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from .dns_check import check_domains
from .generate import generate_names
from .heuristics import filter_and_rank
from .render import render_shortlist, write_shortlist


def load_config(path: Path | None) -> dict:
    if path is None:
        return {}
    if not path.exists():
        print(f"Config not found: {path}", file=sys.stderr)
        sys.exit(2)
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        print("Config must be a YAML mapping", file=sys.stderr)
        sys.exit(2)
    return data


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="hustle-name-shortlist",
        description=(
            "Generate ~50 brand/domain name candidates with light trademark-ish "
            "heuristics and free DNS/A-record availability hints."
        ),
    )
    p.add_argument(
        "--config",
        type=Path,
        default=Path("config.yaml"),
        help="YAML config path (default: config.yaml)",
    )
    p.add_argument("--niche", type=str, help="Business niche (overrides config)")
    p.add_argument(
        "--vibe",
        type=str,
        help="Comma-separated vibe keywords (overrides config)",
    )
    p.add_argument(
        "--count",
        type=int,
        default=None,
        help="Number of candidates (default: 50)",
    )
    p.add_argument(
        "--tlds",
        type=str,
        default=None,
        help="Comma-separated TLDs for DNS checks (default: com,io,ai,co)",
    )
    p.add_argument(
        "--out",
        type=str,
        default=None,
        help="Output Markdown path (default: out/shortlist.md)",
    )
    p.add_argument(
        "--skip-dns",
        action="store_true",
        help="Skip DNS lookups (faster offline demo)",
    )
    p.add_argument(
        "--no-config",
        action="store_true",
        help="Ignore config.yaml even if present",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    cfg = {} if args.no_config else load_config(args.config if args.config.exists() else None)

    niche = args.niche or cfg.get("niche")
    if not niche:
        print("Provide --niche or set niche in config.yaml", file=sys.stderr)
        return 2

    if args.vibe:
        vibe = [v.strip() for v in args.vibe.split(",") if v.strip()]
    else:
        raw = cfg.get("vibe", [])
        if isinstance(raw, str):
            vibe = [v.strip() for v in raw.split(",") if v.strip()]
        else:
            vibe = [str(v).strip() for v in (raw or []) if str(v).strip()]

    count = args.count if args.count is not None else int(cfg.get("count", 50))
    if args.tlds:
        tlds = [t.strip().lstrip(".") for t in args.tlds.split(",") if t.strip()]
    else:
        tlds = [str(t).lstrip(".") for t in cfg.get("tlds", ["com", "io", "ai", "co"])]
    out_path = args.out or cfg.get("out", "out/shortlist.md")

    names, mode = generate_names(str(niche), vibe, count=count)
    ranked = filter_and_rank(names)

    if args.skip_dns:
        dns_by_name = {r["name"]: [] for r in ranked}
    else:
        # Check top candidates to keep dry-runs snappy; still include all names
        # but DNS only for those that pass a soft score floor
        check_names = [r["name"] for r in ranked if r["score"] >= 40] or [
            r["name"] for r in ranked
        ]
        dns_by_name = check_domains(check_names, tlds)
        for r in ranked:
            dns_by_name.setdefault(r["name"], [])

    md = render_shortlist(
        niche=str(niche),
        vibe=vibe,
        mode=mode,
        ranked=ranked,
        dns_by_name=dns_by_name,
        tlds=tlds,
    )
    written = write_shortlist(out_path, md)
    print(f"Wrote {written} ({len(ranked)} names, generator={mode})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

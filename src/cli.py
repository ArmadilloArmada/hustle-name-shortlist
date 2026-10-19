"""CLI entry: generate → human approve → export (no auto-email)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from . import approve as approve_mod
from . import export_delivery as export_mod
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


def add_generate_args(p: argparse.ArgumentParser) -> None:
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


def cmd_generate(args: argparse.Namespace) -> int:
    cfg = {} if args.no_config else load_config(
        args.config if args.config.exists() else None
    )

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
    print("Human review next: python -m src approve")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="hustle-name-shortlist",
        description=(
            "Generate brand/domain shortlists, human-approve, then export "
            "client-ready Markdown/HTML + mailto (never auto-sends)."
        ),
    )
    sub = p.add_subparsers(dest="command")

    gen = sub.add_parser(
        "generate",
        help="Generate out/shortlist.md from niche + vibe",
    )
    add_generate_args(gen)
    gen.set_defaults(_handler=cmd_generate)

    ap = sub.add_parser(
        "approve",
        help="Record human approval of out/shortlist.md",
    )
    ap.add_argument(
        "--path",
        type=Path,
        default=Path("out/shortlist.md"),
        help="Shortlist Markdown to approve",
    )
    ap.add_argument("--note", type=str, default="", help="Optional curation note")
    ap.add_argument("--force", action="store_true", help="Overwrite stamp")
    ap.add_argument(
        "--check",
        action="store_true",
        help="Only verify approval status",
    )
    ap.set_defaults(_handler=lambda a: approve_mod.main(_approve_argv(a)))

    ex = sub.add_parser(
        "export",
        help="Export approved shortlist to out/export/ (no email send)",
    )
    ex.add_argument(
        "--path",
        type=Path,
        default=Path("out/shortlist.md"),
        help="Approved shortlist path",
    )
    ex.add_argument(
        "--out-dir",
        type=Path,
        default=Path("out/export"),
        help="Export directory",
    )
    ex.add_argument(
        "--to",
        type=str,
        default="",
        help="Mailto recipient (draft only)",
    )
    ex.add_argument("--client-name", type=str, default="", help="Greeting name")
    ex.add_argument("--subject", type=str, default=None, help="Mailto subject")
    ex.add_argument(
        "--allow-unapproved",
        action="store_true",
        help="Skip approval gate (demo only)",
    )
    ex.set_defaults(_handler=lambda a: export_mod.main(_export_argv(a)))

    return p


def _approve_argv(args: argparse.Namespace) -> list[str]:
    argv = ["--path", str(args.path)]
    if args.note:
        argv.extend(["--note", args.note])
    if args.force:
        argv.append("--force")
    if args.check:
        argv.append("--check")
    return argv


def _export_argv(args: argparse.Namespace) -> list[str]:
    argv = ["--path", str(args.path), "--out-dir", str(args.out_dir)]
    if args.to:
        argv.extend(["--to", args.to])
    if args.client_name:
        argv.extend(["--client-name", args.client_name])
    if args.subject:
        argv.extend(["--subject", args.subject])
    if args.allow_unapproved:
        argv.append("--allow-unapproved")
    return argv


def main(argv: list[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)

    if not raw or raw[0] in {"-h", "--help"}:
        build_parser().print_help()
        return 0

    # Subcommands: generate | approve | export
    if raw[0] in {"generate", "approve", "export"}:
        parser = build_parser()
        args = parser.parse_args(raw)
        handler = getattr(args, "_handler", None)
        if handler is None:
            parser.print_help()
            return 2
        return int(handler(args))

    # Backward compatible: `python -m src --niche …` still generates.
    parser = argparse.ArgumentParser(
        prog="hustle-name-shortlist",
        description="Generate ~50 brand/domain name candidates (legacy flags).",
    )
    add_generate_args(parser)
    args = parser.parse_args(raw)
    return cmd_generate(args)


if __name__ == "__main__":
    raise SystemExit(main())

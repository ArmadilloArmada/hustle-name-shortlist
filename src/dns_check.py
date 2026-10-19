"""Free DNS / A-record availability hints (no paid WHOIS API)."""

from __future__ import annotations

import concurrent.futures
from typing import Iterable

try:
    import dns.resolver
    import dns.exception
except ImportError:  # pragma: no cover
    dns = None  # type: ignore


def check_a_record(domain: str, timeout: float = 2.0) -> dict:
    """
    Query public DNS for A records.

    Returns:
      status: 'has_a' | 'no_a' | 'error'
      hint: short human label for shortlists

    no_a means no A record was found — the name may still be registered
    (parked NS-only, other RR types, or registry reserved). This is a free
    hint, not a registration guarantee.
    """
    if dns is None:
        return {"domain": domain, "status": "error", "hint": "dnspython missing"}

    resolver = dns.resolver.Resolver(configure=True)
    resolver.lifetime = timeout
    resolver.timeout = timeout
    try:
        answers = resolver.resolve(domain, "A")
        ips = [rdata.address for rdata in answers]
        return {
            "domain": domain,
            "status": "has_a",
            "hint": "A record present (likely taken / in use)",
            "ips": ips[:3],
        }
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers):
        return {
            "domain": domain,
            "status": "no_a",
            "hint": "No A record (may be available — verify at a registrar)",
            "ips": [],
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "domain": domain,
            "status": "error",
            "hint": f"DNS lookup failed: {type(exc).__name__}",
            "ips": [],
        }


def check_domains(
    names: Iterable[str],
    tlds: list[str],
    max_workers: int = 16,
) -> dict[str, list[dict]]:
    """Map each name → list of per-TLD DNS hints."""
    domains: list[tuple[str, str]] = []
    for name in names:
        for tld in tlds:
            domains.append((name, f"{name}.{tld.lstrip('.')}"))

    results: dict[str, list[dict]] = {}
    for name, _ in domains:
        results.setdefault(name, [])

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_map = {
            pool.submit(check_a_record, domain): (name, domain)
            for name, domain in domains
        }
        for future in concurrent.futures.as_completed(future_map):
            name, _domain = future_map[future]
            results[name].append(future.result())

    for name in results:
        results[name].sort(key=lambda d: d["domain"])
    return results

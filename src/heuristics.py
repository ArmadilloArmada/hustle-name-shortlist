"""Lightweight trademark-ish heuristics. NOT legal advice."""

from __future__ import annotations

import re

# Common megabrands / reserved stems — heuristic only, not exhaustive.
BLOCKLIST = {
    "google",
    "apple",
    "amazon",
    "microsoft",
    "meta",
    "facebook",
    "instagram",
    "twitter",
    "xcorp",
    "openai",
    "chatgpt",
    "nvidia",
    "tesla",
    "netflix",
    "spotify",
    "uber",
    "airbnb",
    "stripe",
    "paypal",
    "oracle",
    "samsung",
    "adobe",
    "salesforce",
    "linkedin",
    "tiktok",
    "bytedance",
    "alibaba",
    "tencent",
    "ibm",
    "intel",
    "cisco",
    "slack",
    "zoom",
    "shopify",
    "github",
    "gitlab",
    "cloudflare",
    "vercel",
    "notion",
    "figma",
    "canva",
}

GENERIC_SUFFIXES = ("ly", "ify", "io", "ai", "hq", "app", "lab", "labs", "hub")


def score_name(name: str) -> dict:
    """
    Return heuristic flags and a 0–100 brandability score.

    Disclaimer: These are rough filters for shortlisting. They are not
    trademark clearance, USPTO search, or legal advice.
    """
    name = name.lower().strip()
    flags: list[str] = []
    score = 70

    if name in BLOCKLIST:
        flags.append("blocklist_exact")
        score -= 50

    for brand in BLOCKLIST:
        if brand in name and name != brand:
            flags.append(f"contains_blocklist:{brand}")
            score -= 25
            break

    if re.search(r"(inc|llc|corp|ltd|gmbh)$", name):
        flags.append("legal_entity_suffix")
        score -= 15

    if len(name) < 5:
        flags.append("very_short")
        score -= 5
    elif len(name) > 14:
        flags.append("long")
        score -= 10
    else:
        score += 5

    vowels = sum(1 for c in name if c in "aeiou")
    if vowels == 0:
        flags.append("no_vowels")
        score -= 15
    elif vowels / len(name) >= 0.35:
        score += 5
        flags.append("pronounceable_bias")

    if re.search(r"(.)\1\1", name):
        flags.append("triple_repeat")
        score -= 10

    if any(name.endswith(suf) for suf in GENERIC_SUFFIXES):
        flags.append("common_startup_suffix")
        # Slight nudge only — not a hard fail
        score -= 2

    if re.fullmatch(r"[a-z]+", name):
        score += 3
    else:
        flags.append("non_alpha")
        score -= 8

    score = max(0, min(100, score))
    risk = "high" if score < 40 else "medium" if score < 65 else "low"

    return {
        "name": name,
        "score": score,
        "tm_risk_heuristic": risk,
        "flags": flags,
    }


def filter_and_rank(names: list[str]) -> list[dict]:
    ranked = [score_name(n) for n in names]
    ranked.sort(key=lambda r: (-r["score"], r["name"]))
    return ranked

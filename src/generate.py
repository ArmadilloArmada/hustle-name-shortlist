"""Name candidate generation: OpenAI when keyed, else combinatorial templates."""

from __future__ import annotations

import itertools
import os
import re
from typing import Iterable


PREFIXES = [
    "neo",
    "luma",
    "vera",
    "nova",
    "bolt",
    "soft",
    "clear",
    "bright",
    "quiet",
    "swift",
    "open",
    "true",
    "plain",
    "north",
    "harbor",
]

SUFFIXES = [
    "ly",
    "io",
    "hq",
    "lab",
    "labs",
    "kit",
    "base",
    "stack",
    "craft",
    "forge",
    "works",
    "hub",
    "desk",
    "mint",
    "lane",
]

BLENDS = [
    "{a}{b}",
    "{a}{b}ly",
    "{a}{b}hq",
    "get{a}",
    "try{a}",
    "use{a}",
    "{a}app",
    "{a}kit",
]


def _slug_token(text: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "", text.lower())
    return cleaned[:16] if cleaned else "brand"


def _tokens(niche: str, vibe: Iterable[str]) -> list[str]:
    words: list[str] = []
    for chunk in [niche, *vibe]:
        for part in re.split(r"[\s,/|;]+", chunk.strip().lower()):
            token = _slug_token(part)
            if token and token not in words:
                words.append(token)
    return words or ["brand"]


def generate_combinatorial(niche: str, vibe: list[str], count: int = 50) -> list[str]:
    """Deterministic template generator — works offline with no API key."""
    seeds = _tokens(niche, vibe)
    stems = list(dict.fromkeys(seeds + PREFIXES[:8] + SUFFIXES[:8]))

    candidates: list[str] = []
    seen: set[str] = set()

    def add(name: str) -> None:
        name = re.sub(r"[^a-z0-9]", "", name.lower())
        if 4 <= len(name) <= 18 and name not in seen:
            seen.add(name)
            candidates.append(name)

    for a, b in itertools.product(seeds, PREFIXES + SUFFIXES):
        for pattern in BLENDS:
            add(pattern.format(a=a, b=_slug_token(b)))
            if len(candidates) >= count:
                return candidates[:count]

    for a, b in itertools.product(stems, stems):
        if a == b:
            continue
        add(f"{a}{b}")
        add(f"{a}{_slug_token(b)[:4]}")
        if len(candidates) >= count:
            return candidates[:count]

    # Pad with numbered variants if still short
    i = 1
    while len(candidates) < count and seeds:
        add(f"{seeds[0]}{PREFIXES[i % len(PREFIXES)]}{i}")
        i += 1

    return candidates[:count]


def generate_with_openai(niche: str, vibe: list[str], count: int = 50) -> list[str] | None:
    """Return LLM names when OPENAI_API_KEY is set; else None."""
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None

    try:
        from openai import OpenAI
    except ImportError:
        return None

    client = OpenAI(api_key=api_key)
    vibe_str = ", ".join(vibe) if vibe else "modern"
    prompt = (
        f"Generate exactly {count} brandable product/domain name candidates "
        f"for a founder in the niche '{niche}' with vibe keywords: {vibe_str}. "
        "Rules: lowercase, alphanumeric only, 4-16 chars, no spaces or hyphens, "
        "no trademarked megabrands, inventive but pronounceable. "
        "Return one name per line, no numbering or commentary."
    )
    response = client.chat.completions.create(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9,
    )
    text = (response.choices[0].message.content or "").strip()
    names: list[str] = []
    seen: set[str] = set()
    for line in text.splitlines():
        name = re.sub(r"[^a-z0-9]", "", line.strip().lower())
        if 4 <= len(name) <= 18 and name not in seen:
            seen.add(name)
            names.append(name)
    if len(names) < count // 2:
        # Fall back / top up with combinatorial
        for extra in generate_combinatorial(niche, vibe, count):
            if extra not in seen:
                seen.add(extra)
                names.append(extra)
            if len(names) >= count:
                break
    return names[:count]


def generate_names(niche: str, vibe: list[str], count: int = 50) -> tuple[list[str], str]:
    """Return (names, mode) where mode is 'openai' or 'combinatorial'."""
    llm = generate_with_openai(niche, vibe, count)
    if llm:
        return llm, "openai"
    return generate_combinatorial(niche, vibe, count), "combinatorial"

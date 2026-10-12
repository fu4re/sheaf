"""Module [6] — Ground-Truth Comparator. OUTSIDE the loop (measurement only).

Compares the agent-proposed economic invariant against a hand-fixed canonical
one (for Tier-2 this becomes the Aave CVL ground truth). Produces the research
"ground-truth delta": how close the agent is to the expert. Does NOT participate
in the proof.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

CANON = Path(__file__).parent / "ground_truth" / "canonical.json"


def _normalize(expr: str) -> str:
    """Whitespace-insensitive; canonicalize a commutative `a == b`."""
    e = re.sub(r"\s+", "", expr)
    # canonicalize `a >= b` to `b <= a` so the two spellings compare equal
    m = re.match(r"^(.+?)>=(.+)$", e)
    if m:
        return f"{m.group(2)}<={m.group(1)}"
    m = re.match(r"^(.+?)==(.+)$", e)
    if m:
        a, b = sorted([m.group(1), m.group(2)])
        return f"{a}=={b}"
    return e


def compare(spec: dict, contract_name: str) -> dict:
    proposed = spec.get("invariant", {}).get("solidity_expr", "")
    canon_all = json.loads(CANON.read_text())
    canon = canon_all.get(contract_name)
    if not canon:
        return {"match": "no_ground_truth", "proposed_expr": proposed}
    canonical = canon["canonical_invariant"]["solidity_expr"]
    match = "exact" if _normalize(proposed) == _normalize(canonical) else "divergent"
    return {
        "match": match,
        "proposed_expr": proposed,
        "canonical_expr": canonical,
        "proposed_normalized": _normalize(proposed),
        "canonical_normalized": _normalize(canonical),
    }

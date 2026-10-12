"""Tier-2 spec-generation realism measurement (T-05/T-15, module [6]).

1. module [1] (agent) enumerates the economic-invariant SET for ATokenVault.deposit
   from the REAL Aave source.
2. module [6] (LLM judge) scores that set against the proven Certora ground truth
   (coverage: recovered / partial / missed), PropertyGPT-style.

Both steps go through `claude -p` and are cached as artifacts for replay.

Usage:
  python3 measurement/aave_spec_gen.py            # live (agent + judge)
  python3 measurement/aave_spec_gen.py --replay   # use cached artifacts only
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from untrusted.economic_spec_generator.spec_runner import claude_json, generate_spec_set  # noqa: E402

SUT = ROOT / "ground_truth" / "aave_vault" / "src" / "ATokenVault.sol"
GROUND_TRUTH = ROOT / "measurement" / "ground_truth" / "aave_economic_invariants.json"
ART = ROOT / "measurement" / "artifacts"
SPEC_SET = ART / "ATokenVault__spec_set.json"
COVERAGE = ART / "ATokenVault__coverage.json"


def judge_prompt(agent_set: dict, gt: dict) -> str:
    return f"""You are module [6], the Ground-Truth Comparator (a measurement judge).

Below are (A) economic invariants an AI agent generated for ATokenVault.deposit,
and (B) the EXPERT Certora invariants (all formally proven). For EACH expert
invariant, decide whether the agent recovered the same economic law.

Match by economic MEANING, not by string. Be conservative:
- "recovered": an agent invariant expresses the same law (even if phrased differently).
- "partial": an agent invariant is related but weaker, narrower, or only implied.
- "missed": no agent invariant covers it.

Also list agent invariants that go BEYOND the expert set (extras).

(A) AGENT invariants:
{json.dumps(agent_set.get("invariants", []), ensure_ascii=False, indent=2)}

(B) EXPERT (Certora, proven) invariants:
{json.dumps(gt.get("economic_invariants", []), ensure_ascii=False, indent=2)}

Output STRICT JSON only:
{{
  "coverage": [
    {{"ground_truth_id": "<id>", "status": "recovered|partial|missed",
      "matched_agent_name": "<agent invariant name or null>", "note": "<short>"}}
  ],
  "extra_agent_invariants": ["<agent name>", "..."],
  "summary": {{"recovered": 0, "partial": 0, "missed": 0, "coverage_pct": 0}}
}}"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--replay", action="store_true", help="use cached artifacts, no model calls")
    ap.add_argument("--model", default="sonnet")
    args = ap.parse_args()
    ART.mkdir(parents=True, exist_ok=True)
    gt = json.loads(GROUND_TRUTH.read_text())

    # [1] agent enumerates the economic-invariant set
    if args.replay and SPEC_SET.exists():
        agent_set = json.loads(SPEC_SET.read_text())
        print(f"[1] replay: {len(agent_set.get('invariants', []))} agent invariants", file=sys.stderr)
    else:
        print(f"[1] economic_spec_generator (SET) on real ATokenVault -> {args.model} ...", file=sys.stderr)
        agent_set = generate_spec_set(SUT, "ATokenVault", "deposit", model=args.model)
        SPEC_SET.write_text(json.dumps(agent_set, ensure_ascii=False, indent=2))
    for inv in agent_set.get("invariants", []):
        print(f"    [{inv.get('dimension','?'):12}] {inv.get('solidity_expr')}", file=sys.stderr)

    # [6] judge scores coverage vs the Certora ground truth
    if args.replay and COVERAGE.exists():
        cov = json.loads(COVERAGE.read_text())
    else:
        print("[6] judge: scoring coverage vs Certora ground truth ...", file=sys.stderr)
        cov, prov = claude_json(judge_prompt(agent_set, gt), model=args.model)
        cov["_provenance"] = prov
        COVERAGE.write_text(json.dumps(cov, ensure_ascii=False, indent=2))

    s = cov.get("summary", {})
    print("\n=== COVERAGE vs Certora (7 expert economic invariants) ===")
    for c in cov.get("coverage", []):
        mark = {"recovered": "✅", "partial": "🟡", "missed": "❌"}.get(c["status"], "?")
        print(f"  {mark} {c['ground_truth_id']:32} <- {c.get('matched_agent_name') or '—'}")
    print(f"\n  recovered={s.get('recovered')} partial={s.get('partial')} missed={s.get('missed')} "
          f"| coverage≈{s.get('coverage_pct')}%")
    print(f"  agent extras (beyond expert set): {cov.get('extra_agent_invariants')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

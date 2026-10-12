"""Naive-loop aggregator (Task 0004) — turns N per-run artifacts into the two
pre-registered decision metrics, per level and per expressiveness class.

  mean ± spread   — reliability of ONE cheap run (proved_clean_rate averaged over N)
  union / best-of-N — did the loop prove the invariant in ANY run / n_canonical.
                      This is the HONEST ceiling of the cheap path: at $-cents/run,
                      N runs are still cheap, and the cheap path's power is repetition.
                      The pivot decision reads UNION (revision of 0004).

All rates are computed on proved_CLEAN (proved AND survived Probe R) — a vacuous proof
is not a win. false_proven incidence is reported separately (a high rate is the strongest
argument FOR curation: "the loop converges but lies").

Usage:
  python3 aggregate.py                 # all levels found under runs/
  python3 aggregate.py --level L1 L2   # subset
"""
from __future__ import annotations

import argparse
import json
import statistics as stats
import sys
from collections import defaultdict
from pathlib import Path

NAIVE = Path(__file__).resolve().parent
RUNS = NAIVE / "runs"
sys.path.insert(0, str(NAIVE))
from judge import judge_run  # noqa: E402

LEVELS = json.loads((NAIVE / "levels.json").read_text())


def _artifacts(level: str) -> list[tuple[Path, dict]]:
    """Return (sandbox_dir, artifact) pairs for each completed run of `level`."""
    out = []
    for d in sorted(RUNS.glob(f"{level}__*")):
        af = d / "artifact.json"
        if af.exists():
            try:
                out.append((d, json.loads(af.read_text())))
            except json.JSONDecodeError:
                continue
    return out


def aggregate_level(level: str) -> dict:
    arts = _artifacts(level)
    canon = LEVELS[level]["canonical"]
    n = len(canon)
    names = [c["name"] for c in canon]
    cls_of = {c["name"]: c["class"] for c in canon}

    # Re-judge fresh from each sandbox so scoring reflects the CURRENT judge (incl. any
    # hardening added after the run) rather than the verdict stored at run time.
    runs = [judge_run(d, level) for d, _ in arts]
    n_runs = len(runs)
    if not n_runs:
        return {"level": level, "n_runs": 0, "note": "no runs yet"}

    clean_rates = [r["proved_clean_rate"] for r in runs]
    # union: an invariant counts if it was proved-clean in ANY run
    proved_clean_any = set()
    false_proven_any = defaultdict(int)
    for r in runs:
        run_false = set(r.get("false_proven_names", []))
        for res in r["results"]:
            if res.get("clean"):
                proved_clean_any.add(res["name"])
        for nm in run_false:
            false_proven_any[nm] += 1

    union_by_class = defaultdict(lambda: {"total": 0, "union_proved": 0})
    for nm in names:
        c = cls_of[nm]
        union_by_class[c]["total"] += 1
        if nm in proved_clean_any:
            union_by_class[c]["union_proved"] += 1

    # cost / iteration telemetry across runs
    costs = [a["telemetry"].get("cost_usd") or 0 for _, a in arts]
    iters = [a["telemetry"].get("solc_invocations") or 0 for _, a in arts]

    return {
        "level": level,
        "title": LEVELS[level]["title"],
        "n_runs": n_runs,
        "n_canonical": n,
        "mean_clean_rate": round(stats.mean(clean_rates), 3),
        "stdev_clean_rate": round(stats.pstdev(clean_rates), 3) if n_runs > 1 else 0.0,
        "min_clean_rate": round(min(clean_rates), 3),
        "max_clean_rate": round(max(clean_rates), 3),
        "union_clean_count": len(proved_clean_any),
        "union_clean_rate": round(len(proved_clean_any) / n, 3) if n else 0.0,
        "union_proved_names": sorted(proved_clean_any),
        "never_proved": sorted(set(names) - proved_clean_any),
        "union_by_class": {k: v for k, v in union_by_class.items()},
        "false_proven_incidence": dict(false_proven_any),
        "cost_usd_total": round(sum(costs), 4),
        "solc_iters_mean": round(stats.mean(iters), 1) if iters else 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", nargs="*", default=[k for k in LEVELS if not k.startswith("_")])
    args = ap.parse_args()

    report = {lvl: aggregate_level(lvl) for lvl in args.level}
    print(json.dumps(report, indent=2, ensure_ascii=False))

    # human-readable decision table
    print("\n level | runs | mean(clean) ±sd | union/best-of-N | never proved | false-proven", flush=True)
    print(" " + "-" * 88)
    for lvl, r in report.items():
        if r.get("n_runs", 0) == 0:
            print(f" {lvl:>4}  |  0   | (no runs)")
            continue
        fp = sum(r["false_proven_incidence"].values())
        print(f" {lvl:>4}  | {r['n_runs']:>3}  | {r['mean_clean_rate']:.2f} ±{r['stdev_clean_rate']:.2f}      "
              f"| {r['union_clean_rate']:.2f} ({r['union_clean_count']}/{r['n_canonical']})       "
              f"| {len(r['never_proved']):>2}           | {fp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

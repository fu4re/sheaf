"""Naive-loop driver (Task 0004) — the autonomous `vibecoding + vibesolving` loop.

This is the executable form of H0's "easy path": a single headless Claude Code agent
(latest Opus) is dropped into an ISOLATED sandbox with solc/halmos/forge as tools and
the canonical economic law as its spec. It writes the contract + invariant harnesses and
drives the solver itself, iterating to convergence. Claude Code IS the loop (it iterates
internally); we measure from the outside.

Fair-fight rules (revision of 0004):
  * model = latest Opus, generous turn budget  -> we test the CEILING, not a weak model
  * the agent gets all PUBLIC technique (ghost vars, tracked-sum, assume-abstraction,
    snapshots, vacuity self-check) via the prompt; it is denied only our CURATED artifacts
    -> the sandbox is a clean room with none of cycle/trusted/harness present
  * judge = solver, run by judge.py AFTER the agent finishes -> never the agent's self-report

Usage:
  python3 loop.py --level L1                      # one live Opus run on L1
  python3 loop.py --level L1 --dry-run            # render prompt only (no model call)
  python3 loop.py --level L4                      # given-code run on the real Vat port
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

NAIVE = Path(__file__).resolve().parent
CYCLE = NAIVE.parent
sys.path.insert(0, str(NAIVE))

from judge import judge_run  # noqa: E402

LEVELS = json.loads((NAIVE / "levels.json").read_text())
PROMPT_TEMPLATE = NAIVE / "prompts" / "agent_synthesis.md"
RUNS = NAIVE / "runs"

ALLOWED_TOOLS = ",".join([
    "Write", "Edit", "Read", "Glob", "Grep",
    "Bash(solc:*)", "Bash(forge:*)", "Bash(halmos:*)",
    "Bash(cat:*)", "Bash(ls:*)", "Bash(grep:*)", "Bash(echo:*)",
    "Bash(mkdir:*)", "Bash(pwd:*)", "Bash(head:*)", "Bash(tail:*)",
])


def _model_facing(template: Path) -> str:
    parts = template.read_text().split("\n---\n", 1)
    return (parts[1] if len(parts) == 2 else template.read_text()).strip()


def _canonical_list(canon: list[dict]) -> str:
    lines = []
    for i, inv in enumerate(canon, 1):
        lines.append(f"{i}. `{inv['name']}` — {inv['informal']}  _(class: {inv['class']})_")
    return "\n".join(lines)


def _task_body(level: str, spec: dict, sandbox: Path) -> str:
    if spec["mode"] == "synthesis":
        return (
            f"Write a **new** {spec['title']} in Solidity `^0.8.0` **from scratch** in this "
            f"directory. You control the implementation — you may choose any representation that "
            f"makes the proof tractable (this is correct-by-construction synthesis)."
        )
    # invariant_on_given_code (L4): copy the SUT in, forbid modifying it.
    src = CYCLE / spec["given_code"]
    dst = sandbox / Path(spec["given_code"]).name
    shutil.copyfile(src, dst)
    return (
        f"The real contract **`{dst.name}`** is in this directory (a verified-equivalent port of "
        f"MakerDAO's Vat). Do **NOT** modify it. Write harnesses that prove the following "
        f"invariants about it — you may write a focused harness (subclass / inlined slice / ghost "
        f"abstraction) as long as it is a sound model of `{dst.name}`'s relevant logic."
    )


def render_prompt(level: str, sandbox: Path) -> str:
    spec = LEVELS[level]
    body = _task_body(level, spec, sandbox)
    return (
        _model_facing(PROMPT_TEMPLATE)
        .replace("{{MODE}}", spec["mode"])
        .replace("{{LEVEL_TITLE}}", spec["title"])
        .replace("{{TASK_BODY}}", body)
        .replace("{{CANONICAL_LIST}}", _canonical_list(spec["canonical"]))
    )


def _parse_stream(transcript: list[dict]) -> dict:
    """Extract loop telemetry from the stream-json transcript."""
    result_event = next((e for e in reversed(transcript) if e.get("type") == "result"), None)
    solc_calls = halmos_calls = forge_calls = 0
    for e in transcript:
        if e.get("type") != "assistant":
            continue
        for block in e.get("message", {}).get("content", []):
            if block.get("type") == "tool_use" and block.get("name") == "Bash":
                cmd = block.get("input", {}).get("command", "")
                solc_calls += cmd.count("solc ")
                halmos_calls += cmd.count("halmos ")
                forge_calls += cmd.count("forge ")
    return {
        "solc_invocations": solc_calls,       # proxy for solver iterations (plateau curve)
        "halmos_invocations": halmos_calls,
        "forge_invocations": forge_calls,
        "num_turns": (result_event or {}).get("num_turns"),
        "cost_usd": (result_event or {}).get("total_cost_usd"),
        "duration_ms": (result_event or {}).get("duration_ms"),
        "result_text": (result_event or {}).get("result"),
        "is_error": (result_event or {}).get("is_error"),
        "session_id": (result_event or {}).get("session_id"),
    }


def run_once(level: str, model: str = "opus", max_turns: int = 60,
             proc_timeout_s: int = 1800, run_id: str | None = None) -> dict:
    if level not in LEVELS:
        raise SystemExit(f"unknown level {level!r}; have {list(LEVELS)[:-0] or ''}")
    run_id = run_id or time.strftime("%Y%m%d-%H%M%S")
    sandbox = RUNS / f"{level}__{run_id}"
    sandbox.mkdir(parents=True, exist_ok=True)

    prompt = render_prompt(level, sandbox)
    (sandbox / "_prompt.md").write_text(prompt)

    cmd = [
        "claude", "-p", prompt,
        "--output-format", "stream-json", "--verbose",
        "--model", model,
        "--max-turns", str(max_turns),
        "--permission-mode", "acceptEdits",
        "--allowedTools", ALLOWED_TOOLS,
    ]
    t0 = time.time()
    proc = subprocess.run(cmd, cwd=sandbox, capture_output=True, text=True, timeout=proc_timeout_s)
    wall = round(time.time() - t0, 1)

    transcript = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            transcript.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    (sandbox / "transcript.jsonl").write_text(proc.stdout)
    if proc.returncode != 0 and not transcript:
        (sandbox / "_stderr.txt").write_text(proc.stderr)

    telemetry = _parse_stream(transcript)
    telemetry["agent_returncode"] = proc.returncode
    telemetry["wall_s"] = wall

    verdict = judge_run(sandbox, level)

    artifact = {
        "level": level,
        "run_id": run_id,
        "model": model,
        "max_turns": max_turns,
        "telemetry": telemetry,
        "judge": verdict,
    }
    (sandbox / "artifact.json").write_text(json.dumps(artifact, indent=2, ensure_ascii=False))
    return artifact


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", required=True, choices=[k for k in LEVELS if not k.startswith("_")])
    ap.add_argument("--model", default="opus")
    ap.add_argument("--max-turns", type=int, default=60)
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--dry-run", action="store_true", help="render prompt only, no model call")
    args = ap.parse_args()

    if args.dry_run:
        sb = RUNS / f"{args.level}__dryrun"
        sb.mkdir(parents=True, exist_ok=True)
        print(render_prompt(args.level, sb))
        return 0

    art = run_once(args.level, model=args.model, max_turns=args.max_turns, proc_timeout_s=args.timeout)
    j = art["judge"]
    t = art["telemetry"]
    print(json.dumps(art, indent=2, ensure_ascii=False))
    print(
        f"\n[{art['level']}] proved {j['proved_count']}/{j['n_canonical']} "
        f"(rate={j['proved_rate']}) | solc_iters={t['solc_invocations']} "
        f"| cost=${t['cost_usd']} | {t['wall_s']}s",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Module [1] — Economic Spec Generator (UNTRUSTED). Backend: `claude -p`.

Sends the pinned prompt + the SUT source to a Claude model and parses the
returned economic invariant JSON. The model/version is recorded for provenance
(partial mitigation of risk #4). Nothing here is trusted — the gateway re-checks.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).parent
PROMPT_TEMPLATE = HERE / "prompt.md"
PROMPT_SET_TEMPLATE = HERE / "prompt_set.md"


def _model_facing_prompt(template: Path) -> str:
    """Everything after the first horizontal rule is the model-facing template."""
    txt = template.read_text()
    parts = txt.split("\n---\n", 1)
    return (parts[1] if len(parts) == 2 else txt).strip()


def build_prompt(contract_name: str, method: str, contract_source: str, template: Path = PROMPT_TEMPLATE) -> str:
    return (
        _model_facing_prompt(template)
        .replace("{{CONTRACT_NAME}}", contract_name)
        .replace("{{METHOD}}", method)
        .replace("{{CONTRACT_SOURCE}}", contract_source)
    )


def _extract_json(text: str) -> dict:
    text = re.sub(r"```(?:json)?", "", text).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"no JSON object in model output: {text[:200]!r}")
    return json.loads(text[start : end + 1])


def claude_json(prompt: str, model: str = "sonnet", proc_timeout_s: int = 300) -> tuple[dict, dict]:
    """Headless `claude -p` call returning (parsed_json, provenance)."""
    cmd = ["claude", "-p", prompt, "--output-format", "json", "--model", model]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=proc_timeout_s)
    if proc.returncode != 0:
        raise RuntimeError(f"claude -p failed ({proc.returncode}): {proc.stderr[:300]}")
    envelope = json.loads(proc.stdout)
    parsed = _extract_json(envelope.get("result", proc.stdout))
    prov = {
        "backend": "claude -p",
        "model_requested": model,
        "session_id": envelope.get("session_id"),
        "usage": envelope.get("usage"),
        "cost_usd": envelope.get("total_cost_usd"),
    }
    return parsed, prov


def generate_spec(
    sut_path, contract_name: str, method: str, model: str = "sonnet", proc_timeout_s: int = 240
) -> dict:
    prompt = build_prompt(contract_name, method, Path(sut_path).read_text())
    spec, prov = claude_json(prompt, model, proc_timeout_s)
    spec["_provenance"] = prov
    return spec


def generate_spec_set(
    sut_path, contract_name: str, method: str, model: str = "sonnet", proc_timeout_s: int = 300
) -> dict:
    """SET mode: enumerate the full set of economic invariants (Tier-2 realism)."""
    prompt = build_prompt(contract_name, method, Path(sut_path).read_text(), template=PROMPT_SET_TEMPLATE)
    spec, prov = claude_json(prompt, model, proc_timeout_s)
    spec["_provenance"] = prov
    return spec

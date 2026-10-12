"""Module [4] — Translator / Validator. The deterministic GATEWAY.

Takes the untrusted agent's economic invariant (a Solidity boolean expression)
and assembles a self-contained harness .sol around the SUT, then deterministically
checks that it compiles. This is the trust boundary: nothing reaches the solver
unless it compiles, and past here the spec is treated "as written" — no faith in
the LLM. Ghost/overflow scaffolding is supplied by the trusted side, not the agent.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

SOLC = shutil.which("solc") or "/opt/homebrew/bin/solc"

_SPDX = re.compile(r"^\s*//\s*SPDX-License-Identifier:.*$", re.M)
_PRAGMA = re.compile(r"^\s*pragma\s+solidity[^;]*;\s*$", re.M)
# NatSpec doc comments (`///` lines, `/** */` blocks) would re-attach to the inlined
# contract and break on `@`-tags (e.g. emails / provenance) — strip them.
_NATSPEC_LINE = re.compile(r"^[ \t]*///.*$", re.M)
_NATSPEC_BLOCK = re.compile(r"/\*\*.*?\*/", re.S)


class GatewayError(Exception):
    pass


def _strip_header(src: str) -> str:
    src = _NATSPEC_BLOCK.sub("", src)
    src = _NATSPEC_LINE.sub("", src)
    return _PRAGMA.sub("", _SPDX.sub("", src)).strip()


def _safe(tag: str) -> str:
    """Filename-safe slug (candidate names may contain ==, >, (), spaces, …)."""
    return re.sub(r"[^A-Za-z0-9_]+", "_", tag).strip("_")


def build_harness(sut_path, contract_name: str, invariant_expr: str, out_dir, tag: str = "") -> Path:
    """Inline the SUT verbatim and append a harness that asserts the agent's
    invariant in a view function. The solver then proves/refutes it over ALL
    reachable states (constructor + any sequence of the inherited public funcs).

    `tag` disambiguates the output filename when triaging many candidates."""
    body = _strip_header(Path(sut_path).read_text())
    harness = f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

// ===== SUT (inlined verbatim from {Path(sut_path).name}) =====
{body}

// ===== Generated harness (gateway [4]) =====
// Economic invariant proposed by module [1] (UNTRUSTED), discharged over all
// reachable states by the solver core [5]. Scaffolding is trusted & pre-fixed.
contract __Harness is {contract_name} {{
    function __check_invariant() public view {{
        assert({invariant_expr});
    }}
}}
"""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    suffix = f"__{_safe(tag)}" if tag else ""
    hp = out / f"{contract_name}{suffix}__harness.sol"
    hp.write_text(harness)
    return hp


_INVARIANT_LINE = re.compile(
    r"^[ \t]*assert\(.*?\);[ \t]*//[ \t]*__INVARIANT__.*$", re.M
)


def build_from_harness(template_path, contract_name: str, invariant_expr: str, out_dir, tag: str = "") -> Path:
    """Harness mode (Slice 2): inject the agent's invariant into a PRE-FIXED,
    trusted proof harness (e.g. one that abstracts nonlinear arithmetic via a
    ghost). The agent still only supplies the 1-line economic invariant; all the
    ghost scaffolding stays trusted. Replaces the single `__INVARIANT__`-tagged
    assert with the agent's expression."""
    src = Path(template_path).read_text()
    new, n = _INVARIANT_LINE.subn(
        f"        assert({invariant_expr}); // __INVARIANT__ (gateway-injected)", src
    )
    if n != 1:
        raise GatewayError(f"expected exactly one __INVARIANT__ assert in template, found {n}")
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    suffix = f"__{_safe(tag)}" if tag else ""
    hp = out / f"{contract_name}{suffix}__harness.sol"
    hp.write_text(new)
    return hp


# Cross-contract A/G mode (Task 0003): an external CALL is abstracted the same way
# Slice 2 abstracts a nonlinear op — havoc the callee's effect, then `require(...)`
# acting as `assume` pins it to the callee's GUARANTEE G_B. The trusted harness has
# two kinds of injectable hole: the `__INVARIANT__` assert(s) (the caller law I_A) and
# one-or-more `__SUMMARY__` require(s) (the assumed guarantee at each call site). Both
# pass through the SAME deterministic compile gate; only the booleans are agent-supplied.
_SUMMARY_LINE = re.compile(
    r"^[ \t]*require\(.*?\);[ \t]*//[ \t]*__SUMMARY__.*$", re.M
)


def build_cross_harness(template_path, contract_name: str, invariant_expr: str,
                        summary_exprs, out_dir, tag: str = "") -> Path:
    """Inject the caller invariant into EVERY `__INVARIANT__` assert (a multi-leg
    harness — deposit + withdraw — has more than one, all the same law) and the
    candidate guarantee clauses into the `__SUMMARY__` require(s), in source order.
    The havoc scaffolding (fresh `*_post` inputs, the `vaultBal = vaultBal_post`
    commit) stays trusted & pre-fixed. To ABLATE a clause (necessity test), pass
    `"true"` for it — that drops the constraint without touching the template."""
    src = Path(template_path).read_text()

    new_src, n_inv = _INVARIANT_LINE.subn(
        f"        assert({invariant_expr}); // __INVARIANT__ (gateway-injected)", src
    )
    if n_inv < 1:
        raise GatewayError(f"expected >=1 __INVARIANT__ assert in template, found {n_inv}")

    summary_exprs = list(summary_exprs)
    tags = _SUMMARY_LINE.findall(new_src)
    if len(tags) != len(summary_exprs):
        raise GatewayError(
            f"expected {len(summary_exprs)} __SUMMARY__ require(s) in template, found {len(tags)}"
        )
    it = iter(summary_exprs)
    new_src = _SUMMARY_LINE.sub(
        lambda _m: f"        require({next(it)}); // __SUMMARY__ (gateway-injected)", new_src
    )

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    suffix = f"__{_safe(tag)}" if tag else ""
    hp = out / f"{contract_name}{suffix}__cross.sol"
    hp.write_text(new_src)
    return hp


def validate_compiles(harness_path) -> tuple[bool, list[str], str]:
    """Pure type/compile check of the injected expression (SMTChecker off).
    `--optimize` avoids spurious 'stack too deep' codegen errors on large real
    contracts (e.g. Vat.frob); it does not affect type-checking of the invariant."""
    proc = subprocess.run([SOLC, "--optimize", "--bin", str(harness_path)], capture_output=True, text=True)
    raw = (proc.stderr or "").strip()
    errors = [l for l in raw.splitlines() if l.strip().startswith("Error:")]
    return (len(errors) == 0, errors, raw)

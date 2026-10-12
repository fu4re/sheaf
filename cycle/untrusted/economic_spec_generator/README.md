# Module [1] — Economic Spec Generator (interface contract)

**Trust line:** UNTRUSTED ("agent proposes"). Output may be wrong/hallucinated;
nothing downstream trusts it until the solver [5] discharges it.

**Backend:** `claude -p` (Claude Agent SDK headless path). Model id is pinned per
run and recorded in the artifact (partial mitigation of risk #4 — reproducibility).

## I/O contract

**Input:** `{contract_name, method, contract_source}` (+ the pinned [prompt.md](prompt.md)).

**Output (JSON):**
```json
{
  "module": "economic_spec_generator",
  "contract": "MiniVault",
  "method": "deposit",
  "invariant": {
    "name": "shares_backed_by_assets",
    "solidity_expr": "totalShares == totalAssets",
    "kind": "contract_invariant",
    "informal": "every share is backed by an asset unit; no value from air"
  },
  "state_vars_referenced": ["totalShares", "totalAssets"],
  "rationale": "..."
}
```

The single field the gateway [4] consumes is `invariant.solidity_expr`; the rest
is provenance for the measurement layer [6].

## Replay

The orchestrator caches each generated spec under
`measurement/artifacts/<contract>__spec.json`. Re-running with `--spec-file <path>`
skips the model call and replays deterministically (CI / ablation).

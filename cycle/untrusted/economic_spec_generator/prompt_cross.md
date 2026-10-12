# Module [1] — Cross-Contract Spec Generator (UNTRUSTED / "agent proposes")

This prompt is the committed, version-pinned artifact behind module [1] in CROSS-CONTRACT
mode (Task 0003). The runner substitutes `{{CALLER_NAME}}`, `{{CALLEE_NAME}}`, `{{METHOD}}`,
`{{CALLER_SOURCE}}`, `{{CALLEE_SOURCE}}` and sends it to a Claude model via `claude -p`.
Output is consumed verbatim by the deterministic gateway [4] — so the contract is: **emit
only JSON**.

---

You are the **Cross-Contract Spec Generator** in a neurosymbolic assume-guarantee cycle.
You operate on the UNTRUSTED side: you *propose*, a symbolic solver *verifies and discards
what is unnecessary*. You may be wrong — that is fine; the solver catches it.

A caller contract **A** calls an external callee **B**. The solver cannot reason through the
external call — by default it havocs it (assumes arbitrary reentrancy) and the cross-contract
invariant is unprovable. Your job is to produce the **assume-guarantee decomposition** so the
solver can prove A relative to an explicit, separately-discharged guarantee about B:

1. **The CALLER INVARIANT `I_A`** — the one economic law of A that couples A's internal
   accounting to B's storage (e.g. the vault is *solvent*: it holds at least what it accounts
   for). ONE Solidity boolean over the harness state variables (`totalAssets`, and `vaultBal`
   — the trusted mirror of `B.balanceOf(address(A))`).

2. **The ASSUMED GUARANTEE `G_B`** — a SET of candidate clauses describing what the external
   call does, expressed over the harness call variables (`vaultBal`, `vaultBal_post`,
   `assets`), where `vaultBal_post` is the vault's balance *after* the call. **OVER-GENERATE**:
   propose many candidates of varying logical strength (exact equality, lower bound, upper
   bound, monotone, …). The solver will (a) discharge each against B's real code, (b) keep only
   the clauses needed to prove `I_A`, and (c) report the WEAKEST sufficient one (the tightest,
   most reusable demand on B). Do NOT self-censor — redundant, too-weak, or unsound clauses are
   filtered by the solver, not by you. Recall is your job; precision is the solver's.

Hard rules:
- `I_A`: ONE boolean over harness state. The ECONOMIC law (solvency / conservation), not an
  overflow or functional detail.
- `summary_clauses`: a JSON array of boolean expressions over `(vaultBal, vaultBal_post,
  assets)` — the relation between the vault's balance before and after the external call.
- Do NOT write havoc scaffolding, ghost variables, `require` guards, or loops — that is the
  trusted, pre-fixed harness and is not your responsibility.
- Reference only the harness variables named above. Output STRICT JSON, no prose, no fences.

Caller A — `{{CALLER_NAME}}`, method `{{METHOD}}`:

```solidity
{{CALLER_SOURCE}}
```

Callee B — `{{CALLEE_NAME}}`:

```solidity
{{CALLEE_SOURCE}}
```

Respond with exactly this JSON shape:

{
  "module": "cross_contract_spec_generator",
  "caller": "{{CALLER_NAME}}",
  "callee": "{{CALLEE_NAME}}",
  "method": "{{METHOD}}",
  "invariant": {
    "name": "<short_snake_case>",
    "solidity_expr": "<boolean over harness state, e.g. vaultBal >= totalAssets>",
    "kind": "cross_contract_invariant",
    "informal": "<one sentence: the economic law coupling A's accounting to B's storage>"
  },
  "summary_clauses": [
    "<boolean over vaultBal / vaultBal_post / assets>",
    "<another candidate of different strength>",
    "..."
  ],
  "assumed_guarantee_informal": "<one sentence: what B must guarantee at the call site for I_A to hold>",
  "rationale": "<one or two sentences on why this is the conservation law and what B must promise>"
}

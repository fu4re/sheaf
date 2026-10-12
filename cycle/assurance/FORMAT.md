# Assurance Package — normative format (Task 0003 / gate T2)

A verification session emits **one self-contained directory** that a third party
re-checks *backwards*, without access to the session. This file is the normative
spec; [`schema.py`](schema.py) is its executable structural form;
[`verify_package.py`](verify_package.py) enforces the cross-file invariants.

> The product is an **epistemic claim** ("proved"). If the artifact does not carry
> the exact claim formula **plus a bounded, human-readable list of assumptions**,
> independently re-checkable, there is nothing to sell. This package *is* that
> artifact.

## Layout

```
<package>/
  assurance_graph.yaml          CORE  — claims and their edges to leaves
  trusted/ledger.yaml           CORE  — registry of ALL leaves (proven | assumed)
  evidence/
    smt/**                      what the graph cites; re-checkable (harness + verdict)
    lean/**                     Lean proof refs + `lake build` log
  view/AUDIT.md                 PROJECTION — auto-generated from the core, never hand-kept
  provenance.intoto.json        WRAPPER — provenance of the supply, NOT of the claim
```

Hierarchy by the principle *"without it the epistemics collapse → core; without it
we only lose convenience → wrapper"*: `assurance_graph` + `ledger` + `evidence` are
the **core** (in the trusted base of the *claim*); the linter is **meta**; provenance
is in the trusted base of the *supply chain*, not the claim; the view is a projection.

## Package invariant (machine-checked by the linter)

1. **Closure** — no claim references a leaf absent from `ledger.yaml`.
2. **Acyclicity** — the claim graph (edges of `kind: claim`) is a DAG.
3. **Evidence** — every `proven` claim carries re-checkable evidence; every
   `refuted` claim carries a `witness`.
4. **No hidden assumption** — the linter MUST fail (exit 1) if a leaf an edge
   depends on is missing from the ledger. *Demonstrating that failure is part of
   acceptance.*
5. **Edge honesty** — an edge labelled `proven` may not resolve to an `assumed`
   leaf. You cannot relabel a thing you took on faith as a thing you proved.

## Claim record (in `assurance_graph.yaml`, under `claims:`)

| field | meaning |
|---|---|
| `id` | stable identifier, for linking |
| `human` | one natural-language line |
| `formal` | machine-readable formula (SMT-LIB expression) — **not** prose |
| `shape` | `stateless` \| `quantified-over-mapping` \| `temporal-2state` (F0001 taxonomy) |
| `verdict` | `proven` \| `refuted` \| `inconclusive` — the latter two are **not** hidden |
| `engine` | solver + version + mode (+ `lean-smt reconstruction` if present) |
| `evidence` | `{smt_query, lean_proof, reproduce}` for a verdict that holds; `{witness}` for refuted |
| `depends_on[]` | edges out of the claim (see below) |

Each edge in `depends_on[]` is `{kind, ref, status, human}`:

- `kind` — what `ref` points at: `claim` (another claim, recurse) · `lean_theorem`
  · `assumption` · `harness_faithfulness` (the last three resolve into the ledger).
- `ref` — the target id.
- `status` — the **epistemic verb of the edge**:
  - `proven` — *traverse further*: the ref is itself discharged (a claim that
    holds, or a Lean theorem that builds). The proof continues down the edge.
  - `assumed` — *stop*: the ref is a leaf of the trusted base, taken on faith and
    named in the ledger.
- `human` — one line on what the edge means.

## Trusted-base ledger (`trusted/ledger.yaml`)

The registry of **every leaf** the graph closes onto.

- `lean_theorems[]` — `{id, statement_human, statement_formal, file, theorem_name,
  build_status, status}`. `build_status ∈ {ok, failed, not_built}` — and it must
  not lie: a leaf is only `proven` if its theorem actually builds.
- `assumptions[]` — `{id, statement_human, statement_formal, why_assumed,
  risk_if_false, status}`. The bounded, visible list of what is taken on faith.
- `harness_faithfulness[]` — `{id?, target, claim, evidence, evidence_ref, status}`
  with `status ∈ {lean_proven, diff_fuzz, unverified}`. **The weakest link**
  (model ↔ bytecode). Visible, not hidden — never silently dropped.

## Trust ladder (which leaf carries which trust)

- `proven` via `lean_theorem` (`build_status: ok`) → discharged by the Lean kernel.
- `proven` via `claim` → discharged by the solver, recursing into that claim.
- `assumed` via `assumption` → on faith; the bound on the proof's reach.
- `harness_faithfulness` → the model↔bytecode seam; `unverified` is an honest leaf,
  `diff_fuzz` is evidence-not-proof, `lean_proven` is discharged.

A reader who walks the graph top-down hits, at every frontier, either a `proven`
edge they can re-check or an `assumed` leaf they can read and judge. Nothing in
between, nothing hidden.

## Decoupling contract

The format and the linter know **only** these files. Everything that knows about a
specific orchestrator / solver / LLM is confined to [`adapters/`](adapters/).
Swapping the backend means rewriting one adapter; the format and linter do not move.

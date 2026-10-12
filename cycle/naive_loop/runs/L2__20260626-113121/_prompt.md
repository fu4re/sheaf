You are an autonomous smart-contract verification engineer. You work **correct-by-construction**:
the economic specification is given to you, and you must produce Solidity code together with a
**machine-checked proof** that the code satisfies it.

## Your task (synthesis)

Level: **vault + fee + nonzero exchange rate (mulDiv rounding)**

Write a **new** vault + fee + nonzero exchange rate (mulDiv rounding) in Solidity `^0.8.0` **from scratch** in this directory. You control the implementation — you may choose any representation that makes the proof tractable (this is correct-by-construction synthesis).

For **each** canonical economic invariant below, produce a self-contained SMTChecker harness file
and drive `solc`'s SMTChecker until the invariant is **proved safe**:

1. `solvency_price_geq_1` — totalAssets >= totalShares under fee + rounding  _(class: stateless)_
2. `fee_backing` — accruedFees <= totalAssets — cannot owe more fees than assets held  _(class: stateless)_
3. `share_price_monotone` — shares minted per deposit never exceed proportional share (no dilution via rounding)  _(class: stateless)_

## Tools you have (use them freely, iterate as many times as needed)

- `solc` 0.8.x with SMTChecker (z3) — your **proof engine**. Canonical invocation per file:
  ```
  solc --model-checker-engine chc --model-checker-targets assert --model-checker-solvers z3 --model-checker-timeout 20000 <file>.sol
  ```
  `proved safe` = success. `Assertion violation happens here` + `Counterexample:` = your code or
  invariant is wrong — read the counterexample, fix, retry. `could not be proved` /
  `might happen here` = the solver could not discharge it (nonlinear / over-approximation) —
  reformulate so it can.
- `halmos` — symbolic EVM prover; an alternative engine when SMTChecker stalls (good at
  mapping-sum reasoning). You may use it as a second opinion.
- `forge test` — fuzz your own invariants to find counterexamples cheaply *before* the solver.

## Allowed (public technique — use whatever you need)

Ghost variables; a tracked-sum accumulator updated in the contract to express a sum over a
mapping; `require(...)` as a sound *assume* to abstract nonlinear arithmetic; a pre-state
snapshot to express a 2-state (`old()`-style) property; mutate-an-invariant-and-re-verify to
self-check that your `proved` is not vacuous. These are standard solc / Certora / Kupferman
techniques — they are yours to invent and write yourself.

## Forbidden

Do **not** search for, import, or copy any pre-written curated proof-harness library, ghost-axiom
registry, or canonical-invariant catalogue. Build every harness yourself, from scratch, in this
directory. (There is none in this sandbox — keep it that way.)

## Output contract (the harness scores you on these — be exact)

In the current directory produce:

1. One file per invariant: **`inv_<name>.sol`** where `<name>` is the canonical `name` below.
   Each is a **single self-contained** Solidity file (pragma `^0.8.0`), containing the vault
   logic (or, for given-code levels, the relevant slice) and exactly the invariant under test as
   `assert(<expr>)` on a reachable path. It must be checkable by the canonical `solc` invocation
   above with no extra flags.
2. **`manifest.json`**: a JSON array, one object per file you produced:
   ```json
   [{"file": "inv_conservation_1to1.sol", "name": "conservation_1to1",
     "informal": "...", "class": "stateless",
     "used_ghost": false, "used_snapshot": false, "used_assume_abstraction": false,
     "self_vacuity_checked": true, "engine": "smtchecker",
     "agent_verdict": "proved", "notes": "..."}]
   ```
   `agent_verdict` is YOUR claim; the harness re-runs the solver itself and trusts only that.
   The `used_*` flags feed the self-harness-rate metric — report them honestly.

Stop when every invariant you can prove is proved, or you have genuinely converged (no new
`proved` after repeated attempts). Then write a final one-paragraph summary to stdout describing
which invariants you proved, which you could not, and why.
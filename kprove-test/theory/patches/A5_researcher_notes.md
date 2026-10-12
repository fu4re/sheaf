# A5 researcher handoff

## Artifacts

- `ghost.diff` — full patch from stock KEVM 1.0.678 `evm.md` to the T3 fork in `repro/t3-q0/evm.md`.
- `ghost-t1-callcounter.diff` — T1-only `<callCounter>` patch.
- `ghost-t3-delta.diff` — delta from the T1 fork to the T3 `<inFunc>` fork.

The full patch was generated from:

```sh
diff -u --label a/evm.md --label b/evm.md \
  /nix/store/53c9hz1bs88a067spgbrbbs1j3nkjlvx-source/src/kevm_pyk/kproj/evm-semantics/evm.md \
  repro/t3-q0/evm.md
```

## Facts visible in `ghost.diff`

1. Ghost cells are `<callCounter>`, `<inFunc>`, and `<monitoredAddr>`.
2. `#selKey`, `#ifGet`, and `#bump` are total functions, not `<k>` ghost steps.
3. The patch has no new ghost constructors inserted into `<k>`.
4. `<callCounter>` is updated inline at `#mkCall` and `#mkCreate`.
5. `<inFunc>` is updated inline at `#mkCall` and the three return joints.
6. The return-joint updates read existing non-ghost cells `<id>` and `<callData>` to compute the selector before `#popCallStack`.
7. The patch does not add `requires` clauses to stock transition rules.
8. The patch does not write non-ghost cells. It only reads non-ghost data and writes ghost cells.

## Consequence for the A5 proof

The proof should use a strong projection argument for this concrete patch: the D3/tau class is empty for the current implementation. The existing weak-bisimulation skeleton can be kept as a generalization, but the accepted A5 for `ghost.diff` should classify all semantic transition-rule changes as D2-style inline ghost effects plus total ghost functions.

Required proof edits:

- Extend the erasure projection `pi` to remove `<monitoredAddr>`.
- Replace "ghost elements in `<k>` / `#bump` as D3" by "total ghost helper functions used in RHS ghost-cell updates".
- Weaken the L3 condition from "LHS literally unchanged" to "no new non-ghost guard and no non-ghost write; added cells are read-only and already present in every configuration".
- Weaken L4 from "no non-ghost reads" to "no non-ghost writes and no applicability restriction on non-ghost rules".
- State that for `ghost.diff` the bisimulation is strong after erasure; the weak/stuttering form is only needed for a future patch that really inserts ghost `<k>` items.

## Open proof obligations

- Check helper totality and guard completeness for `#ifGet` and `#bump`.
- Check that all stock-rule `requires` clauses are unchanged.
- Check that added cells in return rules are read-only and do not make matching stricter beyond ordinary total KEVM configuration shape.
- Check that no RHS writes to `<gas>` or any other non-ghost cell were introduced by the patch.

# A5 VO audit for `ghost.diff`

Status: manual audit of `theory/patches/ghost.diff`, generated from the T3 fork. This closes the paper-level classification of hunks, but it is not a parser-backed machine proof.

## Classification

| # | Hunk | Class | Notes |
|---|---|---|---|
| 1 | Add `<callCounter>`, `<inFunc>`, `<monitoredAddr>` to `<kevm>` | D0 | Static ghost cells. Projection must erase all three cells. |
| 2 | Add `#selKey(Bytes)` total function | GF | Ghost helper equation, no transition step, no `<k>` item. |
| 3 | Add `#ifGet(Map, Int)` total function | GF | Branches `K in_keys(M)` / `notBool K in_keys(M)` are intended complete and disjoint. |
| 4 | Add `#bump(Map, Int, Int, Int, Int)` total function | GF | Branches `A ==Int MON` / `A =/=Int MON` are intended complete and disjoint. |
| 5 | Extend `#mkCall` with `<callCounter>` increment | D2 | Inline ghost write; stock non-ghost RHS remains. |
| 6 | Extend `#mkCall` with `<inFunc>` update via `#bump` and read `<monitoredAddr>` | D2 | Inline ghost write, no new `requires`; reads stock rule arguments and ghost monitor address. |
| 7 | Extend `return.exception` with read `<id>`, read `<callData>`, read `<monitoredAddr>`, write `<inFunc>` | D2-read | Added non-ghost cells are read-only; no new `requires`; no non-ghost write. |
| 8 | Extend `return.revert` similarly | D2-read | Same as #7. |
| 9 | Extend `return.success` similarly | D2-read | Same as #7. |
| 10 | Extend `#mkCreate` with `<callCounter>` increment | D2 | Inline ghost write; stock non-ghost RHS remains. |

No D3/tau transition rules are present in this concrete patch. `#bump` is a total function, not a ghost element in `<k>`.

## VO status

| VO | Status | Evidence |
|---|---|---|
| VO-1 classification | Closed manually | All hunks are D0, GF, D2, or D2-read. No D3 hunks. |
| VO-2 no ghost in stock LHS | Needs parser-backed check for final acceptance | Manual diff shows ghost cells only in added fragments. |
| VO-3 D3 totality | Vacuous for `ghost.diff` | No D3 transition rules. Helper totality is covered by GF obligations. |
| VO-4 D3 no self-generation | Vacuous for `ghost.diff` | No ghost `<k>` constructors. |
| VO-5 D3 determinism | Vacuous for `ghost.diff` | No D3 transition rules. |
| VO-6 D2 applicability preservation | Partially closed | No new `requires`; D2-read hunks add reads of cells that exist in every well-formed KEVM configuration. Parser-backed confirmation recommended. |
| VO-7 no non-ghost writes | Closed manually from diff | Added writes target `<callCounter>` or `<inFunc>` only. Added `<id>`, `<callData>`, `<monitoredAddr>` occurrences are reads. |
| VO-8 deterministic ghost init | Closed manually | Added ghost initial values: `0`, `.Map`, `0`. |

## Proof shape recommended

For this concrete `ghost.diff`, prove strong bisimulation under erasure:

- erase `<callCounter>`, `<inFunc>`, `<monitoredAddr>`;
- erase no `<k>` items, because none are introduced;
- ignore total ghost helper equations except as pure computations inside erased ghost RHS;
- for each D2/D2-read step, project the RHS and obtain exactly the stock RHS;
- for each stock step, lift it by applying the corresponding fork rule with arbitrary ghost state, using totality of helper functions.

The weak/stuttering version remains useful only as a future-proof generalization.

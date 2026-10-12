# SPIKE-T1 Tracker

Source: [tast_t1.md](tast_t1.md) · Report: [t1_report.md](t1_report.md) · Env:
`source scripts/env.sh`. Fork built on C9-Q4 `<callCounter>`.

Legend: `[ ]` todo · `[~]` in progress · `[x]` done · `[!]` blocked/stop-rule.

## Stop rule
- `[x]` **Q1 requires whole-CALL-family edit AND breaks a stock test → NOT hit.**
  N=2 shared junctions (not 6 opcodes); regression ADD proves on the fork.
  A5 stays in the cheap form (3 additive lines).

## Q1 — increment on CALL `[x]` → only edit, N=2, regression clean
- `[x]` Recon: 4 message-calls funnel to `#mkCall` (evm.md:1677); CREATE/CREATE2
  to `#mkCreate` (1948); dispatcher `#exec[CO:CallOp]`/`#exec[CSO:CallSixOp]`.
- `[x]` (i) priority hook → self-loops (counter=8 for 1 call, CALL never consumed).
- `[x]` (ii) `#mkCall`+`#mkCreate` edit: 3 additive lines; builds; increment PROVED
  (`q1b-mkcall-spec.k` `#Top`, depth 1).
- `[x]` (iii) no non-competing K hook; collapses to (i)/(ii).
- `[x]` Regression: stock `add-spec.k` on fork → PROVED (`#Top`).
- `[x]` Negative control: ADD leaves `<callCounter>` unchanged → PROVED.

## Q2 — toy A→B + REVERT `[x]`
- `[x]` REVERT persistence PROVED: full `#pushCallStack~>#pushWorldState~>
  #popCallStack~>#popWorldState` is transparent to `<callCounter>` (=7 throughout).
  The 4 revert ops save/restore only `<callState>`/`<accounts>`/`<substate>`
  (evm.md:246/252/276/283). → ghost survives revert → T2 interface unchanged.
- `[x]` A→B count: real STATICCALL A(1)→B(100) executes end-to-end, `<callCounter>`=1
  observed on the return path. Additive by construction (1 opcode → 1 #mkCall → +1).
- `[!]` Foundry/Kontrol-on-fork clean `#Top`: needs forked kdist (integration note,
  same boundary as TCG-003 vendored-fork). Substituted by KEVM-level run.

## Q3 — goal-as-own-circularity `[x]` → goal ∈ C
Countdown loop: pos PROVED (`#Top`, symbolic N ⇒ goal used as its own circularity);
neg control FAILED (self-application unreachable: step → `gone`, stuck, implication
fails). Contrast isolates the mechanism. Base of induction A3a holds. `repro/t1-q3`.

## Q4 — consequence junction `[x]` → mechanics demonstrated
q4c: junction closes by subsumption (reached ⊑ weaker target; no rule from `post`) →
PROVED. q4t: trusted rule rewrites `post=>done` → PROVED. Discriminator: q4t-no-trusted
FAILED (`post` doesn't unify with `done`, cannot rewrite). Log: consequence = "unifies
with destination + implication check"; trusted = rewrite edge. `repro/t1-q4`.

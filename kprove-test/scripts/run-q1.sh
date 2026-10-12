#!/usr/bin/env bash
# Q1: is a `trusted` claim an axiom usable from step 0, or a step-guarded
# circularity (usable only after >=1 execution step)?
#
# Two designs on a toy semantics where q1Start has NO real rewrite rule:
#   D1: goal head = q1Start (no real step available before the lemma)
#   D2: goal head = q1Boot, with a real rule q1Boot=>q1Start (one real step,
#       THEN the lemma could apply)
# Reading:
#   D1 PROVED               -> axiom-from-step-0
#   D1 FAILED & D2 PROVED   -> circularity-guarded (lemma needs the >=1 step)
#   D1 FAILED & D2 FAILED   -> trusted sibling claim not applied at all
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/scripts/env.sh"
cd "$ROOT"
mkdir -p logs
run() { # name file module def [extra...]
  local name="$1" file="$2" mod="$3" def="$4"; shift 4
  kprove "$file" --definition "$def" --spec-module "$mod" "$@" > "logs/$name.log" 2>&1
  local ec=$?
  printf '%-26s exit=%s  %s\n' "$name" "$ec" "$([ $ec -eq 0 ] && echo PROVED || echo FAILED)"
}
# D1 (clean, no competing real rule)
D1=repro/q1; DEF1="$D1/q1c-kompiled"
kompile "$D1/q1c-semantics.k" --backend haskell --main-module Q1C --syntax-module Q1C --output-definition "$DEF1" >logs/q1c-kompile.log 2>&1
run q1c-a-true-trusted  "$D1/q1c-a-true-trusted.k"  Q1C-A-TRUE-TRUSTED  "$DEF1"
run q1c-b-untrusted     "$D1/q1c-b-untrusted.k"     Q1C-B-UNTRUSTED     "$DEF1"
run q1c-c-false-trusted "$D1/q1c-c-false-trusted.k" Q1C-C-FALSE-TRUSTED "$DEF1"
# D2 (discriminator: one leading real step)
D2=repro/q1d; DEF2="$D2/q1d-kompiled"
kompile "$D2/q1d-semantics.k" --backend haskell --main-module Q1D --syntax-module Q1D --output-definition "$DEF2" >logs/q1d-kompile.log 2>&1
run q1d-a-true-trusted  "$D2/q1d-a-true-trusted.k"  Q1D-A-TRUE-TRUSTED  "$DEF2"
run q1d-c-false-trusted "$D2/q1d-c-false-trusted.k" Q1D-C-FALSE-TRUSTED "$DEF2"
run q1d-nolemma         "$D2/q1d-nolemma.k"         Q1D-NOLEMMA         "$DEF2"
run q1d-b-untrusted     "$D2/q1d-b-untrusted.k"     Q1D-B-UNTRUSTED     "$DEF2"

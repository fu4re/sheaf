#!/usr/bin/env bash
# T3 Q1 — per-claim verdicts for the full obligations matrix (one --claims run each, module-qualified label).
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/scripts/env.sh"
cd "$ROOT"
mkdir -p logs
DEF="$ROOT/repro/t3-q1/withdraw-kompiled"

row() { # file module label expect
  local file="$ROOT/repro/t3-q1/$1" mod="$2" label="$3" expect="$4"
  kprove "$file" --definition "$DEF" --spec-module "$mod" --claims "$mod.$label" \
    > "logs/t3-q1-m-$label.log" 2>&1
  local ec=$?; local got=$([ $ec -eq 0 ] && echo '#Top' || echo 'FAILED')
  printf '%-28s %-7s expect %-7s  %s\n' "$label" "$got" "$expect" \
    "$([ "$got" = "$expect" ] && echo OK || echo '!!!MISMATCH')"
}

echo "## frame (#1,#2)"
row q1-frame-spec.k        Q1-FRAME-SPEC      frame-deposit             '#Top'
row q1-frame-spec.k        Q1-FRAME-SPEC      frame-withdraw-V          '#Top'
row q1-frame-spec.k        Q1-FRAME-SPEC      frame-withdraw-F          '#Top'
echo "## compat dep->with #3 (K1: both Rely editions)"
row q1-c3-spec.k           Q1-C3-SPEC         c3-V-strict               'FAILED'
row q1-c3-spec.k           Q1-C3-SPEC         c3-V-weak                 '#Top'
row q1-c3-spec.k           Q1-C3-SPEC         c3-F                      '#Top'
echo "## compat #4,#5,#7 + junction #9,#10"
row q1-junc-compat-spec.k  Q1-JUNC-COMPAT-SPEC c4-compat-with-dep       '#Top'
row q1-junc-compat-spec.k  Q1-JUNC-COMPAT-SPEC c5-self-compat-deposit   '#Top'
row q1-junc-compat-spec.k  Q1-JUNC-COMPAT-SPEC c7-env-compat-deposit    '#Top'
row q1-junc-compat-spec.k  Q1-JUNC-COMPAT-SPEC c9-postd-inv             '#Top'
row q1-junc-compat-spec.k  Q1-JUNC-COMPAT-SPEC c10-postw-inv-local      '#Top'
echo "## robust discriminators #6,#8 (V must FAIL, F must PASS)"
row q1-disc-V-spec.k       Q1-DISC-V-SPEC     c6-self-compat-withdraw-V 'FAILED'
row q1-disc-V-spec.k       Q1-DISC-V-SPEC     c8-env-compat-withdraw-V  'FAILED'
row q1-disc-F-spec.k       Q1-DISC-F-SPEC     c6-self-compat-withdraw-F '#Top'
row q1-disc-F-spec.k       Q1-DISC-F-SPEC     c8-env-compat-withdraw-F  '#Top'
echo "## operation-order grounding"
row q1-ground-spec.k       Q1-GROUND-SPEC     ground-V-pending-debit    '#Top'
row q1-ground-spec.k       Q1-GROUND-SPEC     ground-F-no-pending       '#Top'

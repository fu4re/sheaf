# ARL deep read — exact mechanics of axioms in the proof system

**Source:** Ștefănescu, Ciobâcă, Mereuță, Moore, Șerbănuță, Roșu — *All-Path Reachability Logic*,
**LMCS 15(2:5), 2019** (priority version). Page citations use the journal's internal numbering (5:N)
with the PDF page in brackets. Verbatim transcriptions are marked `[текст]`; inferences are marked
`[интерпретация]`.

---

## Headline / stop-rule outcome

- The object literally **named "Theorem 7.1 (Soundness)" is stated only for empty A** (and empty C):
  `If S ⊢ φ ⇒∀ φ′ then S ⊨ φ ⇒∀ φ′`, where `S ⊢ … ≡ S, ∅ ⊢∅ …`.
- **BUT** the general, A-quantified soundness statement exists as **Lemma 7.2**, the engine from which 7.1
  is derived ("the hypotheses about A and C are vacuously true when those sets are empty").
- **Verdict:** cite **Lemma 7.2, not Theorem 7.1**, for the A3a induction step. Lemma 7.2's hypothesis on A
  is the progress-flagged `⊨⁺` relation — **stronger than plain ⇒∀-validity** — and that strengthening is the
  side-condition A3a must carry (Q3). Do NOT invent an axiom-soundness lemma from scratch: the paper provides it.

---

## Q1 — Sequent form and role of A

Sequent (Fig. 1, §4, p. 5:6 [PDF 6]):  **S, A ⊢_C φ ⇒∀ φ′**
Read: `["S with axioms A and circularities C proves φ ⇒∀ φ′"]`.
`[The rules in A are called axioms and rules in C are called circularities.]`  `[Initially, both A and C are empty.]`
Shorthands: `S ⊢C … ≡ S,∅ ⊢C …`; `S,A ⊢ … ≡ S,A ⊢∅ …`; `S ⊢ … ≡ S,∅ ⊢∅ …`.

| Set | Definition | Used by | Modified by |
|---|---|---|---|
| **S** | Operational semantics: *weakly well-defined* reachability system, finite set of unconditional `l∧b ⇒∃ r`. Induces `(T,⇒ᵀ_S)`. | **Step** | **Never** (fixed). |
| **A** (axioms) | Set of **all-path** rules `φ⇒∀φ′` assumed valid. `[the reachability rules in A can be assumed valid]`. | **Axiom** | **Transitivity** (2nd premise `S, A∪C ⊢ …`). |
| **C** (circularities) | All-path rules `[postulated but not yet justified]`; usable only after progress. | **Axiom** (only after moved into A). | **Circularity** (adds goal to C); **Transitivity** (C→A); **Reflexivity** requires C=∅. |

Sequent semantics, verbatim: `[φ ⇒∀ φ′ holds if the rules in A hold and those in C hold after taking at least
one step from φ … and if C ≠ ∅ then φ reaches φ′ after at least one step on all complete paths.]`

Fig. 1 image: fig1_proof_system.png (artifact).

---

## Q2 — Soundness theorem: exact statement & premises

**Theorem 7.1 (Soundness), verbatim (p. 5:12):** `[If S ⊢ φ ⇒∀ φ′ then S ⊨ φ ⇒∀ φ′.]`
Generalization note: `[Due to Circularity and Transitivity the sets A and C may not remain empty, so we need
to prove a more general statement (Lemma 7.2 below) …]`

`⊨δₙ` definition, verbatim (p. 5:12): `[We define S ⊨δₙ φ ⇒∀ φ′ to hold iff for any complete path τ = γ₁…γₖ
of length k ≤ n and for any ρ such that (γ₁,ρ) ⊨ φ, there exists i ∈ {1,…,k} such that (γᵢ,ρ) ⊨ φ′ and also
that this i is not 1 (i.e. γ₁ makes progress) if δ = +.]`  Bridge: `[S ⊨ φ⇒∀φ′ iff S ⊨*ₙ φ⇒∀φ′ for all n∈N.]`

**Lemma 7.2, verbatim (p. 5:12):** `[If S, A ⊢C φ ⇒∀ φ′ then for any n, S ⊨⁺ₙ A and S ⊨⁺ₙ₋₁ C imply that
S ⊨*ₙ φ ⇒∀ φ′, and also that S ⊨⁺ₙ φ ⇒∀ φ′ if C is not empty.]`

**Verdicts:**
- **(a) Quantified over A?** Named theorem NO; **Lemma 7.2 YES**. A-hypothesis is `S ⊨⁺ₙ A` (step-bounded,
  progress-flagged), not plain validity. [явно, p.5:12]
- **(b) Meaning of "A valid" as premise?** Stronger relation `⊨⁺`: all-path-valid AND makes progress (i≠1,
  ≥1 step). Confirmed in Axiom case: `[By the assumption on A, S ⊨⁺ₙ φ⇒∀φ′. Applying this to τ and ρ gives
  an i > 1 with (γᵢ,ρ) ⊨ φ′]` (p.5:13). [явно + интерпретация]
- **(c) Restrictions on A?** A holds **only all-path (`⇒∀`) rules**. One-path `⇒∃` rules live only in S; never
  admitted as axioms. [явно]
- **(d) Coq covers non-empty A?** Text: `[the soundness result has also been mechanized in Coq]`; Thm 7.1's
  only proof runs through Lemma 7.2 with general A/C, so mechanization necessarily includes non-empty A —
  **интерпретация**; verify against Coq dev at fsl.cs.illinois.edu/rl if A3a leans on mechanized status of the
  A-quantified statement specifically.

---

## Q3 — Sufficiency for the A3a induction step (главный выход)

**Verdict: применима — через Lemma 7.2 (не Theorem 7.1), с одной обязательной side-condition (прогресс / ⊨⁺).**

Apply Lemma 7.2 to `S, A(h) ⊢_{C(h)} φₕ⇒∀φₕ′`. With `C(h)=∅` (children pre-proven, no circularity at stitch):
for all n, `S ⊨⁺ₙ A(h) ⟹ S ⊨*ₙ φₕ⇒∀φₕ′`, hence `S ⊨ φₕ⇒∀φₕ′`.

- **(a) Transitive closure of axioms — НЕ протекает.** Lemma 7.2 wants `S ⊨⁺ₙ A(h)` — validity against fixed S,
  not `S∪A(children)`. IH gives S-validity of children directly. **Caveat:** phrase IH as *S-validity of child claim*
  (semantic), not *derivability of child*. [интерпретация from statement]
- **(b) A fixed vs augmented — fixed OK.** A augmented only by Transitivity (C→A). Stitch step with fixed A(h),
  C(h)=∅ needs no augmentation. Augmentation matters only for reading kprove logs. [явно, Fig.1]
- **(c) Side-conditions for A3a premises:**
  1. **Progress / `⊨⁺` on every trusted claim.** IH must be "child is `⊨⁺`-valid = valid AND reaches postcond after
     ≥1 step on all complete paths", not merely `⇒∀`-valid. Discharge by (i) strengthening IH to `⊨⁺`, or
     (ii) proving each child with non-empty C (Circularity yields `⊨⁺ₙ` automatically:
     `[any rule … derived by Circularity has the property that φ reaches φ′ after at least one step]`).
     ⚠️ **Hazard:** subsumption/consequence stitch claims (`φ⇒∀φ′` with `φ→φ′`, zero steps) are NOT `⊨⁺`-valid —
     must go through **Consequence**, not **Axiom**. Encode as a typing rule on DAG edges.
  2. **S weakly well-defined** (Def 3.1, p.5:5) — required by Step. Premise it for KEVM S.
  3. **No extra well-definedness on A beyond validity+progress** — `⊨⁺`-validity is all A owes; do not over-constrain.
     [интерпретация: absence of such clause]

---

## Q4 — Circularity step-guard (эталон для kprove logs)

Mechanism (set manipulation + progress flag, not a separate guard):
- **Circularity** adds goal to **C**: `S,A ⊢_{C∪{φ⇒∀φ′}} φ⇒∀φ′`. Axiom reads A not C → not usable immediately.
- **Transitivity** transfers C→A (2nd premise `S,A∪C ⊢ …`): `[Transitivity enables the circularities as axioms
  for the second premise, since if C is not empty, the first premise is guaranteed to take at least one step.]`
- **Reflexivity** requires C=∅: `[Reflexivity requires C to be empty to ensure that all-path rules derived with
  non-empty C take at least one step]`.
- **Theoretical encoding:** in Lemma 7.2 circularities assumed only at `S ⊨⁺ₙ₋₁ C` (index n−1, one lower than
  axioms at n) — the `n−1` IS the "only after a step" discipline formalized.

Citable unsoundness note (≤25 words), verbatim (§4, p.5:7):
`[This would obviously be unsound if the new assumption was available immediately]`
(context: requiring progress before circularities can be used ⟹ only diverging executions correspond to endless
invocation of a circularity.)

kprove эталон: a rule is a **circularity (C)** until a Step/Transitivity flushes it into **A**; a trusted claim
supplied up front is in **A**, applicable immediately *iff `⊨⁺`-valid*. Applying a trusted claim as circularity, or a
not-yet-progressed circularity as axiom, is exactly what the `n−1` index forbids.

---

## Q5 — Partial correctness / complete paths (для замечания «газ ⟹ полнота»)

**Def 3.1 (p.5:5), verbatim:** `[A ⇒ᵀ_S-path is a finite sequence γ₀⇒ᵀ_S γ₁ … ⇒ᵀ_S γₙ … A ⇒ᵀ_S-path is
complete iff it is not a strict prefix of any other ⇒ᵀ_S-path.]` → complete path = maximal finite path.

**Def 3.2 (p.5:5), verbatim:** `[S ⊨ φ⇒∀φ′ iff for all complete ⇒ᵀ_S-paths τ starting with γ … there exists
some γ′ ∈ τ such that (γ′,ρ) ⊨ φ′.]`

**On infinite paths (one sentence):** infinite/diverging executions are excluded from the quantification — they are
not finite `⇒ᵀ_S`-paths and hence not *complete* paths, so `⇒∀` neither is witnessed nor violated by them
(partial correctness). Verbatim (end of §3, p.5:6): `[reachability rules can only specify properties of complete paths
(that is, terminating execution paths).]`

**EVM/gas remark:** appeals to **Def 3.1 + Def 3.2**. Gas ⟹ every EVM execution finite ⟹ every maximal execution
is a complete path, none excluded ⟹ `⇒∀` over complete paths = over all executions; partial/total gap closes.
The definitions are verbatim; the EVM collapse is **ваша лемма / интерпретация** resting on them.

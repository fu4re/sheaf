# Task 0008 — tcg: K-гейт (check) + verdict→outcome + two-tier acceptance

- **Дата:** 2026-06-28 · **Тип:** инженерная задача (ядро гейта)
- **Опирается на:** [план tcg CLI](../plans/adr-federated-parrot.md) (§ Task 3, § Verdict→outcome, § Soundness-фикс round-2) · ADR-0003 §2.3-2.4 (acceptance≠truth, структурный результат), Инв.1-9 · Finding 0007:55 (false-green class)
- **Зависит от:** 0006, 0007 (frozen φ) · **Разблокирует:** 0009, 0010, 0011
- **TL;DR:** перевести вердикт солвера в структурный `Accept|Refute|Unknown` и реализовать **строгий two-tier acceptance**: green `Verified(b,φ)` ТОЛЬКО при полной ADR-конформности; иначе честный `⊥_assumptions_open`. Запись допущения в ledger ≠ право звать verified.

## Зачем (одно предложение)

Это единственное место, решающее «green», и точка, где [Finding 0007:55](../findings/0007_assurance_package_format.md) поймал бы false-green — поэтому acceptance-предикат и раздел IRREDUCIBLE/DISCHARGEABLE должны быть структурными, а не «честно записать и пропустить».

## Что строим

- `tcg/outcome.py`:
  - `classify(Verdict)→KResult`: `proved→Accept`, `counterexample→Refute(witness)`, `inconclusive→Unknown`, `compile_error→gateway-reject`. **Unknown≠Refute by construction** (разные ветки, witness только у Refute, exit 3 vs 2).
  - Раздел assumed-листов: **IRREDUCIBLE** (ADR Assumptions 1/3/7) vs **DISCHARGEABLE** (Инв.7 bytecode-identity, покрытие Trace/Exit, annotation-discharge).
  - Two-tier предикат: `Verified[green] ⟺ Accept ∧ PASS ∧ frozen ∧ hash ∧ params ∧ φ_context=∅ ∧ bytecode-identity discharged ∧ assumed⊆IRREDUCIBLE ∧ WELL-FORMED`; иначе `⊥_assumptions_open`. **Accept ≠ green.**
- `tcg/commands/check.py`: хеш-recheck frozen φ (отказ при расхождении/незаморозке); inject `pre→require`, `post→assert`, `exit→--model-checker-targets`, `trace→--model-checker-ext-calls`; зов `gateway.build_*`/`validate_compiles`/`run_solver`.

Переиспользует: `cycle/gateway/translator.py`, `cycle/trusted/solver.py` (`Verdict`).

## Definition of Done

1. **Verdict-маппинг точен:** на P-фикстурах `check.json` несёт корректный `Accept|Refute|Unknown|reject`.
2. **Unknown≠Refute:** `inconclusive` → exit 2 (без witness); `counterexample` → exit 3 (+witness). Разные коды.
3. **Хеш-recheck:** на tampered/незамороженной φ — `check` отказывает (exit 1), не запускает солвер.
4. **Two-tier строг:** source-level `MiniVault` Accept+PASS, но `H_bytecode=unverified` ⇒ `outcome.json = ⊥_assumptions_open` (НЕ green, exit 6). Зелёного на source-level **не возникает**.
5. **Refute-путь:** `MiniVaultBuggy` → Refute+witness → `⊥_gen` (exit 5); никакого «verified».
6. **φ_context-гейт:** при непустом `φ_context` исход ≤ `⊥_assumptions_open`, claim только про `φ_checked`.

## Артефакт (проверяемый отдельно)

`runs/<contract>-<stamp>/check.json` + `outcome.json` на паре MiniVault/MiniVaultBuggy. Проверяется независимо: сверить вердикт/witness; убедиться, что green НЕ выдан при `H_bytecode=unverified`; exit-коды соответствуют таблице. **Это артефакт, фиксирующий, что false-green закрыт.**

## Риски / открытые

- `bytecode_identity == discharged` в MVP всегда false (source-level) → штатно `⊥_assumptions_open`; реальная разрядка — backlog (0006-серия / Sourcify-style).
- Маппинг `exit→targets` и `trace→ext-calls` зависит от того, что показал P8 (0006): если havoc-wall блокирует целевой Trace — он остаётся `deferred` в φ_context, не молча.

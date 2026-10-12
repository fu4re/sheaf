# Task 0014 Фаза 1 — census note (honest instrument caveat + the real signal)

**Дата:** 2026-07-03 · judge = `cycle.trusted.solver.run_solver` · corpus = `corpus.txt` (35 фикстур, 25 base)

## Что прогнали и что вышло (`census.json`)

Прогнали `run_solver` по 25 base-фикстурам. Сырой результат: **0 фикстур показали `nl=True`** — но это **артефакт инструмента, НЕ отсутствие стены**:

- **Голые контракты** (`MiniVault`, `ProportionalVault`, `VaultAsset`, `Vat`) → `inconclusive` **без ассерта**: в самом контракте нет `assert` экономического инварианта, значит SMTChecker'у нечего доказывать. Стена нелинейки проявляется, только когда инвариант **заассерчен на raw-контракте** (что делает `tcg check`, инжектя φ.post) — не при прогоне голого файла.
- **Ghost-харнессы** (`ProportionalVaultGhost`, `VatSolvency`, `VatDaiConservation`, `MiniERC20Conservation`, …) → `proved` — но **потому что лемма уже инжектнута** как Solidity-ghost. Это ровно «после» из before/after моста, не «до».

**Вывод по инструменту:** bare-solver census — **неверный измеритель** M/C. Правильный — before/after через tcg-гейт: заассертить инвариант на raw-контракте (→ ⊥_gen), затем инжектнуть лемму (→ Accept). Это **связано с Фазой 4** (bridge), не отдельно измеримо.

## Реальный сигнал, который corpus УЖЕ несёт

Структура ghost-харнессов **прямо показывает переиспользование лемм** — каждый `proved` ghost-харнесс соответствует Lean-разряженной лемме (соответствие задокументировано в `axiom_registry.json`):

| Лемма (Lean, разряжена) | Ghost-харнессы, которые она держит (census `proved`) | M (различных base-фикстур) |
|---|---|---|
| `Erc20.transfer_sum_preserved` / `transfer_pair_sum_preserved` | `MiniERC20Conservation`, `MiniERC20NoMintConservation`, `VaultAssetAG` (cross A/G), `BurnFeeERC20Conservation` | **≈4** |
| `AaveArith.ar_delta` (product distributivity) | `VatSolvency`, `VatDaiConservation` | **≈2** |
| `AaveArith.mulDiv_le_left` | `ProportionalVaultGhost`, `VaultAsset` | **≈2** |

- **Подтверждённый before/after (N=1, строгий):** `ProportionalVault` raw → **⊥_gen** ([ProportionalVault-T0008](../../../cycle/measurement/artifacts/tcg_runs/ProportionalVault-T0008/), `reason: nonlinear`); `ProportionalVaultGhost` (лемма инжектнута) → **proved** (census). Одна лемма (`mulDiv_le_left`) закрывает стену.
- **Refuted-контроль работает:** `FeeERC20Conservation`, `BurnFeeERC20Delta` → `counterexample` (fee ломает консервацию — лемма НЕ должна их «доказывать», и не доказывает).

## Предварительный вердикт масштаба (честно)

- **M ≥ 3** для conservation-семьи (`transfer_sum_preserved` держит ≈4 фикстуры) — **предварительно подтверждает рычаг H1** по reuse-оси, но через *ghost-инжекцию*, не через *автоматический bridge*.
- **C** (покрытие) не измеримо этим инструментом — требует before/after на raw-контрактах через bridge.
- **Строгий M/C против порога (M≥3 ∧ C≥60 %) — ОТКРЫТ**, гейтится Фазой 4: bridge делает инжекцию автоматической, тогда M/C меряется как «сколько raw-⊥_gen флипнулось в Accept одной леммой».

**Итог:** corpus уже структурно демонстрирует переиспользование (M≥3 на conservation), но это надо перемерить строго через автоматический bridge — не через рукописные ghost'ы. Инструментальный census заменяется before/after-замером в Фазе 4.

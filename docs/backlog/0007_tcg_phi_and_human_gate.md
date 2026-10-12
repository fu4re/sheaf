# Task 0007 — tcg: φ-артефакт + Formalizer (F) + Human-gate freeze (H)

- **Дата:** 2026-06-28 · **Тип:** инженерная задача (net-new, load-bearing)
- **Опирается на:** [план tcg CLI](../plans/adr-federated-parrot.md) (§ Task 2, § φ-артефакт) · ADR-0003 §2.2 (φ-кортеж), Инв.6 (заморозка), Инв.9 (pinned-параметры) · Finding 0001 (taxonomy shape)
- **Зависит от:** 0006 (скелет) · **Разблокирует:** 0008
- **TL;DR:** ввести φ как **полный кортеж (Pre,Trace,Post,Exit)** на диске и шаг **H** (человек валидирует и **замораживает** φ хешем). Сейчас F даёт один `solidity_expr`, а H-шага нет нигде. Заморозка механически запрещает downstream'у ослабить спеку (Инв.6).

## Зачем (одно предложение)

Без явного кортежа φ молчаливая деградация до terminal-only — дефект (ADR §2.2); без заморозки H генератор мог бы переписать спеку, против которой его проверяют (Инв.6) — оба ломают эпистемику гейта.

## Что строим

- `tcg/phi.py` — `Spec{pre,trace,post,exit}` + `coverage{checked_dimensions, deferred_dimensions}`; YAML load/dump; канонизация `spec:` + `sha256` content-hash. Деривация `φ_checked` (=checked_dimensions) vs `φ_context` (=deferred).
- `tcg/commands/formalize.py` (F) — обёртка `spec_runner.generate_spec`; **лифт** единственного инварианта в `spec.post[0]`; `pre` из pre-fixed overflow-guards SUT (детектит gateway, не модель); `trace`/`exit` — явные дефолты со `status: declared/deferred`. Replay через `--spec-file`. F абстейнит → `⊥_spec`.
- `tcg/commands/validate.py` (H) — `--approve` пишет `freeze:{content_hash, approved_by, approved_at, intent_attestation, checker_params:{solc_version, evm_version, ext_calls, targets}}`; `--reject` → `⊥_spec`; без флага рендерит φ и выходит 2.

Переиспользует: `cycle/untrusted/economic_spec_generator/spec_runner.py`, idiom replay из `orchestrator.py:81-90`.

## Definition of Done

1. **`tcg formalize`** на `MiniVault.sol` (replay seed-φ) → `phi.draft.yaml` с **всеми четырьмя измерениями** явно; `coverage.deferred_dimensions` непуст и честен.
2. **Анти-деградация:** Trace/Exit присутствуют материально (не выкинуты), помечены `declared/deferred` — не молча.
3. **`tcg validate --approve`** → `phi.frozen.yaml` с freeze-блоком (хеш над `spec:` + `checker_params`).
4. **Tamper-guard (демо):** изменить `spec:` в `phi.frozen.yaml` → последующий хеш-recheck (заглушка из 0008 или unit-тест в phi.py) **отказывает** при расхождении.
5. **`--reject`** → `⊥_spec` (exit 4); без флага → exit 2 (ничего не заморожено).
6. **F-abstain:** при отсутствии парсимого инварианта → `⊥_spec`, без падения.

## Артефакт (проверяемый отдельно)

`runs/MiniVault-<stamp>/phi.frozen.yaml` — замороженный полный кортеж φ с хешем и pinned-параметрами. Проверяется независимо: пересчитать `sha256` над `spec:` и сверить с `freeze.content_hash`; убедиться, что `φ_checked`/`φ_context` выводятся; tamper → mismatch.

## Риски / открытые

- F сейчас одно-инвариантен → полнокортежный промпт = **liveness-фоллоуап** (0006-серия backlog), **никогда не гейтит soundness**: лифт с дефолтами достаточен для MVP.
- Детекция pre-fixed guards в SUT — простая (парс require в конструкторе/модификаторах); если не находит — `pre: []` честно.

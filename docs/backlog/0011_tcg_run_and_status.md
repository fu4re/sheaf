# Task 0011 — tcg: e2e-секвенсор (run) + status

- **Дата:** 2026-06-28 · **Тип:** инженерная задача (склейка, без новой гейт-логики)
- **Опирается на:** [план tcg CLI](../plans/adr-federated-parrot.md) (§ Task 6, § Command surface) · ADR-0003 §2.5 (контур loop, минус G/I)
- **Зависит от:** 0006–0010 · **Разблокирует:** — (завершает MVP-поверхность)
- **TL;DR:** одна команда `tcg run` прогоняет `formalize→validate→check→vacuity→package`, **стоп на первом не-зелёном** с корректным терминальным исходом; `tcg status` рендерит текущее состояние гейтов по слабейшему листу. Чистая секвенция — вся acceptance-логика уже в 0008.

## Зачем (одно предложение)

Пользователю нужен один e2e-вход и читаемый статус; но `run` не должен вводить НИ грамма новой гейт-логики — иначе появляется второй путь к «accepted» мимо 0008 (нарушение Инв.1).

## Что строим

- `tcg/commands/run.py` — секвенсор; стоп на первом не-зелёном; терминал = `Verified(b,φ)` ТОЛЬКО при полной конформности, иначе `⊥_spec` / `⊥_gen` / `⊥_assumptions_open`. Refute выносит witness человеку (G внешний — человек идёт перевайбкодить). Никакого `--k-max`/авто-feedback (это будущий seam).
- `tcg/commands/status.py` — read-only; печатает, какие гейты green/blocked + терминальный исход; верх по **render-правилу** (слабейший лист).

Переиспользует: всё из 0007–0010; `naive_loop/runs/` как образец run-директории.

## Definition of Done

1. **Happy source-level path:** `tcg run` на `MiniVault` → проходит до `package` → `outcome.json = ⊥_assumptions_open` (честный non-green; bytecode-identity открыт), exit 6. **Не green.**
2. **Refute path:** на `MiniVaultBuggy` → стоп на `check` с witness → `⊥_gen` (exit 5).
3. **Vacuity path:** на dead-фикстуре → стоп на `vacuity` FLAG (exit 3), acceptance заблокирован.
4. **Spec/Human path:** F-abstain или `validate --reject` → `⊥_spec` (exit 4).
5. **`tcg status`** на любом run → корректно показывает green/blocked гейты и терминал; верх не зелёный над dischargeable-листом.
6. **Нет нового гейта:** `run` только секвенция; единственный решающий «green» — `outcome.py` из 0008 (grep-проверка: `run.py` не вызывает acceptance-решение сам).

## Артефакт (проверяемый отдельно)

`runs/<contract>-<stamp>/outcome.json` по четырём путям (happy/refute/vacuity/spec) + вывод `tcg status`. Проверяется независимо: сверить терминал и exit-код каждого пути с таблицей; убедиться, что happy-path НЕ зелёный на source-level.

## Риски / открытые

- Автономный `tcg run --intent` (G/I-loop с ce-feedback) — **будущий seam**, явно вне MVP (зона негатива Finding 0006).
- Резюмируемость run-директории: каждая под-команда читает выход предыдущей; держать формат файлов стабильным.

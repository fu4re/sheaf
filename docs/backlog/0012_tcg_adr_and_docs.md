# Task 0012 — tcg: ADR-0004 (привязка инструментов к ролям) + доки

- **Дата:** 2026-06-28 · **Тип:** документная задача (решение, не код)
- **Опирается на:** [план tcg CLI](../plans/adr-federated-parrot.md) (§ Task 7) · ADR-0003 §4.3 («separate ADRs» для конкретных инструментов) · ADR-0002 (перепроверяемость)
- **Зависит от:** acceptance-семантика стабильна (после 0008) · **Разблокирует:** — (фиксирует решения для аудита)
- **TL;DR:** ADR-0003 намеренно tool-agnostic и явно отложил привязку инструментов к ролям. Этот ADR-0004 фиксирует **конкретные решения** реализации: gate-скоуп, two-tier acceptance, раздел IRREDUCIBLE/DISCHARGEABLE, φ split, command surface — чтобы решение было аудируемым, а не разбросанным по плану.

## Зачем (одно предложение)

Репозиторий ADR-first; ключевые продуктовые решения (что значит green, где граница доверия, какой инструмент в какой роли) должны жить в нумерованном ADR, а не только в плане — иначе их нельзя предъявить и оспорить отдельно.

## Что строим

- `docs/adr/0004_tcg_cli_gate.md` в house-style ADR (Status/Context/Decision/Invariants/Consequences/Acceptance-checklist), фиксирующий:
  1. **Скоуп:** MVP = trusted **gate** вокруг внешнего вайб-кодинга; G external/untrusted; автономный loop — будущий seam.
  2. **Привязка ролей:** F=`spec_runner`(claude -p), K=SMTChecker(CHC/BMC)+Lean-kernel, gateway=`translator`, H=человек+freeze.
  3. **Two-tier acceptance:** green `Verified(b,φ)` только при полной конформности; иначе `⊥_assumptions_open`. + round-2 обоснование (два пойманных false-green).
  4. **Раздел assumed-листов:** IRREDUCIBLE (ADR Assumptions 1/3/7) vs DISCHARGEABLE (Инв.7 bytecode-identity, покрытие Trace/Exit, annotation-discharge).
  5. **φ split** `φ_checked` vs `φ_context`.
  6. **Command surface** formalize→validate→check→vacuity→package; exit-таблица.
  7. **Маппинг на roadmap-гейты:** check/vacuity→T1, package→T2, e2e-гейт→шаг к T3.

## Definition of Done

1. **ADR-0004 существует**, статус Accepted, следует структуре ADR-0003.
2. **Цитирует** конкретные инвариганты ADR-0003 (1-9) и показывает, где каждый enforce'ится в CLI.
3. **Round-2 решение записано:** почему «запись в ledger ≠ green», IRREDUCIBLE/DISCHARGEABLE, ссылка на Finding 0007:55.
4. **Acceptance-checklist** ADR-0004 — конкретный, проверяемый против реализации (0008/0010).
5. **Согласован с планом:** ни одного расхождения с `docs/plans/adr-federated-parrot.md` (разойдутся — план или ADR правится, не оба молча).

## Артефакт (проверяемый отдельно)

`docs/adr/0004_tcg_cli_gate.md`. Проверяется независимо: ревью на соответствие ADR-0003 инвариантам + acceptance-checklist сверяется с кодом 0008/0010 (каждый чек-бокс ↔ строка enforcement).

## Риски / открытые

- ADR должен **следовать** за стабилизацией acceptance (0008), иначе зафиксирует устаревшую семантику — писать после/параллельно 0008, финализировать после.
- Не дублировать план целиком: ADR несёт **решения и их обоснование**, план — исполнительную детализацию.

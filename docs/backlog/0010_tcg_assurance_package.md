# Task 0010 — tcg: assurance-package (emit → spine → assemble → lint) + render-правило

- **Дата:** 2026-06-28 · **Тип:** инженерная задача (T2-артефакт)
- **Опирается на:** [план tcg CLI](../plans/adr-federated-parrot.md) (§ Task 5, § Assurance/ledger) · Task 0005 (формат пакета) · Finding 0007 (формат + render-gap) · ADR-0003 Инв.7/8, ADR-0002 (перепроверяемость)
- **Зависит от:** 0008 (+0009) · **Разблокирует:** 0011
- **TL;DR:** превратить зелёный/честно-неполный run в **самодостаточный assurance-package**, переиспользуя `emit_*`/`assemble`/`lint`. Ключевое новое: листы разделены на **IRREDUCIBLE vs DISCHARGEABLE**, и **render-правило** (Finding 0007) не даёт рисовать «✅» над открытым dischargeable-листом.

## Зачем (одно предложение)

Продукт = эпистемическое утверждение; артефакт обязан нести точную формулу claim'а + перепроверяемый ledger допущений (T2) и **визуально различать** полный proof от «source-checked при открытых dischargeable-пунктах» — иначе повторяем ровно [Finding 0007:55](../findings/0007_assurance_package_format.md).

## Что строим

- `tcg/templates/` — синтезатор `spine.yaml` из run'а: топ-claim = Post-инвариант (`shape` из φ.post); edges = ghost-аксиомы (`lean_theorem`) + **4 именованных листа**: `A_solver`/`A_machine_semantics`/`A_human_intent` (IRREDUCIBLE) и `H_bytecode=unverified`/`φ_context` (DISCHARGEABLE).
- `tcg/commands/package.py` — `emit_smt`(Post-solve, `engine`-строка с pinned-версиями) + `emit_lean`(аксиомы из `axiom_registry.json`) → spine → `assemble()` → `lint()`.
- **Render-правило:** расширить `cycle/assurance/verify_package.py` — верхний статус claim'а = слабейший лист по пути; помечать top-claim, отрисованный зелёным над DISCHARGEABLE-листом.

Переиспользует: `cycle/assurance/{emit,assemble,verify_package,schema}.py`; шаблон-пилот под `cycle/artifact_format/`.

## Definition of Done

1. **Пакет WELL-FORMED:** run → `package/` (`assurance_graph.yaml` + `trusted/ledger.yaml` + `evidence/`), `lint` → WELL-FORMED (exit 0).
2. **Independent re-check:** `python -m cycle.assurance.verify_package package/ --replay` воспроизводит каждый `proven`/`refuted`.
3. **Раздел листов виден:** каждый assumed-лист помечен IRREDUCIBLE/DISCHARGEABLE; `H_bytecode=unverified` присутствует.
4. **Render-правило работает (демо):** top-claim над `H_bytecode=unverified` рендерится НЕ зелёным (capped); голого «✅ proved» над dischargeable-листом нет.
5. **Линтер ловит спрятанное:** удалить лист из ledger → INVALID (exit 1).
6. **Честный refuted:** ≥1 над-claim опровергнут с witness (как C3 в пилоте).
7. **Lean честен:** `emit_lean` ставит `build_status` из реального `lake build`; линтер FLAGает рассинхрон.

## Артефакт (проверяемый отдельно)

`runs/<contract>-<stamp>/package/` — самодостаточный пакет. Проверяется независимо третьей стороной: `verify_package --replay` сверху вниз без доступа к сессии; каждый лист либо `proven`(re-checkable) либо `assumed`(named + класс + `risk_if_false`); верх не зелёный над DISCHARGEABLE. **Это и есть артефакт, который мы проверяем отдельно** (слепая обратная проверка как в Task 0005 DoD#7).

## Риски / открытые

- Render-правило — расширение линтера/проекции; держать его как **отдельный machine-checked инвариант**, не косметику.
- lean-smt снятие `A_solver` — НЕ в этой задаче (структурный негатив CHC, Finding 0007 DoD#3); `A_solver` остаётся IRREDUCIBLE-листом с `risk_if_false`.

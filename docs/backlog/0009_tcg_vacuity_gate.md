# Task 0009 — tcg: vacuity-гейт (Probe R безусловно, Probe M opt-in)

- **Дата:** 2026-06-28 · **Тип:** инженерная задача (обёртка над T1-ядром)
- **Опирается на:** [план tcg CLI](../plans/adr-federated-parrot.md) (§ Task 4) · Finding 0005 (vacuity gate) · ADR-0003 (acceptance) · mvp_roadmap T1
- **Зависит от:** 0006, 0008 (check.json) · **Разблокирует:** 0010, 0011
- **TL;DR:** обернуть существующий `vacuity_gate`/`reachability_probe` в CLI-команду так, что **Probe R (reachability) работает на любом контракте сразу**, а **Probe M (mutation) требует `--family`**; без семьи возвращает **BLOCKED, не PASS** — отсутствие семьи не может дать false green.

## Зачем (одно предложение)

«proved» бывает пустым (недостижимый код, conservation≠delta); гейт T1 уже это ловит ([Finding 0005](../findings/0005_vacuity_gate_mutation.md)), но для произвольного пользовательского контракта **нет автоматической adversarial-семьи** — задача честно разграничивает, что оценено, а что BLOCKED.

## Что строим

- `tcg/commands/vacuity.py`:
  - **Probe R всегда:** `reachability_probe(...)` на harness'е из `check.json` (CHC, `assert(false)`-proves ⇒ unreachable ⇒ FLAG).
  - **Probe M opt-in:** при `--family <manifest>` зовёт `vacuity_gate(...)` (мутация + дискриминация семьи); без `--family` — **BLOCKED** на load-bearing-измерении (честно: «не оценено»), НЕ PASS.
  - FLAG/BLOCKED **блокируют acceptance** (вход в two-tier предикат 0008).

Переиспользует: `cycle/measurement/vacuity.py` целиком.

## Definition of Done

1. **Probe R на dead-фикстуре** (`VaultAssetAGDead.sol` / `MiniERC20NoMintConservation.sol`) → **FLAG** (exit 3).
2. **Probe R на честном** `MiniVault` → **PASS** (exit 0) по reachability.
3. **Без `--family`** → load-bearing-измерение **BLOCKED** (exit 2), не PASS — демонстрация, что пропуск семьи не зеленит.
4. **С `--family`** (демо-семья honest+adversary) → `vacuity_gate` отрабатывает PASS/FLAG корректно (переоткрытие conservation≠delta как в F0005).
5. **Гейтит acceptance:** FLAG/BLOCKED из `vacuity.json` → исход 0008 не green.

## Артефакт (проверяемый отдельно)

`runs/<contract>-<stamp>/vacuity.json` на dead + honest фикстурах (и опц. с `--family`). Проверяется независимо: dead→FLAG, honest→PASS(R), no-family→BLOCKED; сверить, что вердикт корректно блокирует green в 0008.

## Риски / открытые

- **Авто-построение семьи** для Probe M на произвольном контракте — НЕ в этой задаче (открытая T1-подзадача в roadmap); MVP честно BLOCKED'ит вместо угадывания.
- Probe R на reachable-state инвариантах: держать CHC-only (BMC даёт spurious CE) — политика engine⟂квантор из F0005.

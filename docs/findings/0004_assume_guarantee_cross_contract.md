# Finding 0004 — Кросс-контрактная верификация через assume-guarantee: солвер как судья на границе контракта

- **Дата:** 2026-06-25 · **Тип:** эмпирический замер (e2e цикл) · **Опирается на:** Finding 0002 (solver-as-judge на self-contained Vat), Task 0003, ADR-0001/0002
- **TL;DR:** взяли **первую кросс-контрактную пару** (`VaultAsset`, держащий реальный внешний `IERC20`, + `MiniERC20`) и провели e2e цикл с **assume-guarantee**-декомпозицией. Главная находка о самом инструменте: **два встроенных режима SMTChecker оба неадекватны** для композиции — `untrusted` (дефолт) havoc'ит вызов и **refute'ит истинный инвариант** (стена), а `trusted`+интерфейс **ВАКУУМЕН** (доказывает даже `assert(false)`). **A/G-суммари — третий путь:** доказывает caller'а относительно **явной** гарантии `G_B`, которую солвер **отдельно разряжает** на callee. **Важная оговорка (по итогам ревью):** разряжать надо **сам добытый дельта-клоз** (`vaultBal_post >= vaultBal + assets`), а не прокси-консервацию — burning-fee токен сохраняет консервацию, но недо-кредитует vault; дельта-discharge (chc+bmc) его ловит (honest→proven, burning-fee→refuted). Слабейшую достаточную `G_B` солвер **добывает ablation'ом**. Faithfulness-рамка (no-reentrancy) честно остаётся доверенным базисом; живая агент-генерация — seed-replay, не измеренная способность. Механизм суммари — **категориально тот же** `havoc + require`, что ghost-абстракция арифметики из Slice 2.

---

## Сетап (воспроизводимый)

| | |
|---|---|
| Цель | **первый external-call SUT** проекта: vault A держит РЕАЛЬНЫЙ внешний ERC20 B. Все прежние SUT self-contained (Vat — «ноль внешних вызовов»). |
| Caller A | `cycle/contracts/cross/VaultAsset.sol` — `deposit`→`transferFrom`, `withdraw`→`transfer`, поле `IERC20 asset`. Арифметика 1:1 (одна стена на экспонат — вызов, не `mulDiv`). |
| Callee B | `cycle/contracts/cross/MiniERC20.sol` (honest) + adversarial `HostileERC20.sol` (реентрантный hook), `FeeERC20.sol` (fee-on-transfer). |
| Инвариант I_A | солвентность `vaultBal >= totalAssets` (`vaultBal` — зеркало `asset.balanceOf(vault)`; донат усиливает ⇒ `>=`, не `==`). |
| Гарантия G_B | per-transfer дельта + консервация `Σ balanceOf == totalSupply`. |
| Генератор | агент over-генерит I_A + набор клозов G_B (`prompt_cross.md`); здесь — seed-replay для детерминизма. |
| **Судья** | **SMTChecker/Z3** (CHC) — 3 A/G-обязательства + ablation, корзины proven/refuted/unknown. **LLM-судья исключён.** |
| Trusted base | консервация B разряжена в **Lean 4** (`Erc20.transfer_sum_preserved`, `#print axioms` чист) + реестр. |
| Тулчейн | solc 0.8.35, z3 4.16.0, Lean 4.31.0 + Mathlib. |

---

## Стена: оба встроенных режима SMTChecker неадекватны (Step 0)

Истинный инвариант I_A на whole-program `{VaultAsset+MiniERC20}` (полная матрица — `cycle/measurement/wall_map_cross.md`):

| Конфигурация | вызов | вердикт |
|---|---|---|
| `untrusted` (дефолт), `IERC20` | havoc + synthesized reentrancy | **violation** — истинный инвариант недоказуем |
| `untrusted`, КОНКРЕТНЫЙ тип | havoc (всё равно) | **violation** — стена держится и для конкретного типа |
| `trusted`, КОНКРЕТНЫЙ тип | реальный inlining | sound (refute'ит `assert(false)`) |
| **`trusted`, `IERC20`** | код callee неизвестен → путь после вызова отброшен | **ВАКУУМНО proved** — доказывает даже `assert(false)` |

- Ядро **само** синтезирует внешний вызов как реентрантный callback (дословный трейс: `asset.transferFrom(...) -- untrusted external call, synthesized as: VaultAsset.setX(1) -- reentrant call`). Звуковая, но столь грубая над-аппроксимация, что истинный инвариант refute'ится.
- **`trusted`+интерфейс — живая vacuous-proof ловушка** в продакшн-инструменте EF: самый частый реальный случай (интегрируешься против `IERC20`, исходник токена неизвестен) даёт молчаливый зелёный `proved` на чём угодно. Контроль: `untrusted` тот же `assert(false)` корректно refute'ит; `trusted`+конкретный тип — тоже.

**Вывод:** из коробки выбор только между «звуковой-но-бесполезный» и «точный-но-вакуумный». A/G — третий путь.

## Генерация: агент даёт декомпозицию, не один инвариант

Новая роль агента (`prompt_cross.md`): прочитать A и B и выдать **(a)** I_A и **(b)** НАБОР клозов-кандидатов G_B (over-generation), а не один инвариант. «Интерпретировать внешний вызов» = предложить, что вызов гарантирует; отбор — на солвере.

## Судья = солвер: три обязательства assume-guarantee

| Обяз. | Что доказывается | Артефакт | Вердикт |
|---|---|---|---|
| **1** (caller) | A ⊨ I_A, вызов заменён `havoc + require(G_B)` | `trusted/harness/cross/VaultAssetAG.sol` | **proven** (2 VC) |
| 1 (не-вакуумность) | слишком слабое суммари (`vaultBal_post >= vaultBal`) | `VaultAssetAGBuggy.sol` | **refuted** |
| **2A** консервация (honest) | B ⊨ `Σ balanceOf == totalSupply` | `MiniERC20Conservation.sol` | **proven** |
| 2A (adversarial) | supply-inflation токен | `MiniERC20ConservationBuggy.sol` | **refuted** |
| 2A (adversarial) | losing-fee токен | `FeeERC20Conservation.sol` | **refuted** |
| 2A (ЗАЗОР) | **burning-fee** токен | `BurnFeeERC20Conservation.sol` | **proven ← консервация держится, но vault недо-кредитован** |
| **2B** дельта (honest) | B ⊨ «transfer кредитует получателя на ≥ amount» | `MiniERC20Delta.sol` | **proven** (chc+bmc) |
| 2B (закрывает зазор) | **burning-fee** токен | `BurnFeeERC20Delta.sol` | **refuted** (bmc; chc → unknown) |

### Зазор conservation ≠ delta (само-найденный, закрыт)

**Честная находка по итогам ревью:** обяз. 2 изначально разряжало **только консервацию** (`Σ balanceOf == totalSupply`), а майнинг добывал **дельта-клоз** (`vaultBal_post >= vaultBal + assets`). Это **не одно и то же**: **burning-fee** токен (комиссия сжигается, `totalSupply -= 1`) **сохраняет консервацию** (Σ и totalSupply падают синхронно) — `proven` — но кредитует получателя на `amount-1`, ломая ровно тот дельта-клоз, на который опирается caller. Прежний `FeeERC20` ловился лишь потому, что **терял** комиссию (Σ < totalSupply); burning-fee прошёл бы. ⇒ консервация — **необходима, но недостаточна**.

**Фикс:** разряжать **сам добытый дельта-клоз** в его callee-side форме (2B, 2-state harness, **chc+bmc** — BMC ловит 2-шаговый контрпример `mint();transfer()`, который CHC отдаёт как `unknown`, комплементарность движков из Finding 0002). Теперь **разряжаемое свойство = свойство, на которое опирается caller**; burning-fee `refuted` в 2B, хотя прошёл 2A. Зазор закрыт; артефакт `cross_ag__triage.json` (obligation_2A/2B).

Обяз. 2 ловит «плохой callee» **до** того, как суммари примет его гарантии — «moat = proof harness» на границе контракта. (Само-найденный зазор — иллюстрация «провал тоже результат»: майнинг и discharge должны разряжать ОДИН клоз, не прокси.)

## Добыча слабейшего интерфейса (ablation = «солвер отбрасывает ненужное»)

Агент over-генерит 5 клозов deposit-гарантии; солвер решает достаточность и логическую силу (`cross_ag__triage.json`):

| клоз | вердикт | роль |
|---|---|---|
| `vaultBal_post == vaultBal + assets` | proven | sufficient (сильнее, чем нужно) |
| `vaultBal_post >= vaultBal + assets` | proven | **sufficient + ВЕСЕЙШИЙ ← добытый интерфейс** |
| `vaultBal_post >= vaultBal` | refuted | insufficient → отброшен |
| `vaultBal_post <= vaultBal + assets` | refuted | insufficient → отброшен |
| `assets <= type(uint128).max` | refuted | insufficient → отброшен |

**Слабейшая достаточная гарантия = `vaultBal_post >= vaultBal + assets`** («B кредитует vault не меньше чем на `assets`») — тугейший спрос на B, самая переиспользуемая суммари. Assumption-синтез **символьно**, не мнением LLM. Это «отбросить ненужное» из постановки, реализованное солвером.

## Рамка (Обяз. 4): честно локализованный остаточный trusted base

`HostileERC20` (ERC777-style hook реентрит `deposit`) нарушает не state-property B, а **рамку** (B зовёт обратно в A). Поэтому:
- Обяз. 2 (консервация B) её **не видит** — консервация B может держаться, пока B реентрит;
- whole-program её **не выделяет** (`untrusted` refute'ит ВСЁ; `trusted`+iface вакуумен).

⇒ no-reentrancy остаётся **доверенным допущением суммари** — но теперь это **явно названный** клоз рамки, а не молчаливая модельная условность (как в `trusted`-режиме). Это та самая «слишком сильная аксиома ложно доказывает» (`ghost.md:47`), поднятая на кросс-контрактный уровень: `proved` означает «солвентно ПРИ no-reentrancy». Разрядка реентрантности на байткоде (evm-smith Frame library, `Register/BalanceMono`) — следующий экспонат.

## Lean замыкает trusted base гарантии callee (второй случай после `ar_delta`)

Faithfulness tracked-sum шадоу (`ghostSum` не трогается на transfer) опирается на: transfer сохраняет `Σ balanceOf`. Машинно доказано в Lean (`cycle/trusted/proofs/aave_arith/AaveArith/Basic.lean`):
- `Erc20.transfer_pair_sum_preserved : (a-amt)+(b+amt) = a+b` (ℕ, `omega`) — аналог `ar_delta`;
- `Erc20.transfer_sum_preserved` — Σ по `Finset` инвариантна под transfer.
- `#print axioms` → только `[propext, Classical.choice, Quot.sound]`, **ноль sorry, ноль контракт-аксиом**. Реестр: `axiom_registry.json::erc20_transfer_sum_preserved` (мост L1). Первый раз, когда Lean-теорема замыкает trusted base **гарантии callee** в A/G-декомпозиции, а не self-contained ghost.

## Комплементарность (главный вывод)

Цикл работает **связкой**: агент даёт A/G-декомпозицию (over-generation), солвер — (1) доказывает caller'а под суммари, (2) разряжает/опровергает гарантию на callee, (3) добывает слабейший достаточный интерфейс ablation'ом, Lean замыкает арифметику. Ни одна точка доверия не на LLM-судье. **Ценность — там, где оба встроенных режима SMTChecker (havoc-стена / vacuous-proof) проваливаются:** A/G делает гарантию явной и refutable.

## Сдвиг относительно Finding 0002

| | 0002 (Vat) | 0004 (cross-contract) |
|---|---|---|
| Контракт | self-contained (ноль внешних вызовов) | **первый external-call SUT** |
| Стена | сложность/нелинейность одного контракта | **внешний вызов** (havoc / vacuous) |
| Судья | солвер (proven/refuted/inconclusive) | солвер × **3 A/G-обязательства** + ablation |
| Новое | солвер опроверг агентский over-claim | **слабейший интерфейс добыт солвером; vacuous-proof в `trusted`-режиме вскрыт** |
| Lean | `ar_delta` замкнул solvency-шадоу Vat | `transfer_sum_preserved` замкнул **гарантию callee** |

## Артефакты и воспроизводимость

| Что | Где |
|---|---|
| SUT-пара + adversarial | `cycle/contracts/cross/{VaultAsset,MiniERC20,HostileERC20,FeeERC20}.sol` |
| A/G caller harness (+ non-vacuity) | `cycle/trusted/harness/cross/VaultAssetAG.sol`, `…Buggy.sol` |
| Obl.2A консервация (honest/buggy/lose-fee/burn-fee) | `cycle/trusted/harness/cross/{MiniERC20Conservation,…Buggy,FeeERC20Conservation,BurnFeeERC20Conservation}.sol` |
| Obl.2B дельта-discharge (добытый клоз, chc+bmc) | `cycle/trusted/harness/cross/{MiniERC20Delta,BurnFeeERC20Delta}.sol` |
| Gateway (cross-инъекция) | `cycle/gateway/translator.py::build_cross_harness` |
| Triage + ablation + discharge | `cycle/measurement/triage.py::{mine_interface,triage_callees,discharge}` |
| e2e runner + артефакт | `cycle/measurement/cross_triage_demo.py` → `cycle/measurement/artifacts/cross_ag__triage.json` |
| Один command e2e | `cycle/orchestrator.py --cross-template …` (+ `VaultAsset__cross_spec.seed.json`) |
| Карта стен (Step 0 + обязательства) | `cycle/measurement/wall_map_cross.md` |
| Lean + реестр | `…/AaveArith/Basic.lean::Erc20.*`, `cycle/trusted/proofs/axiom_registry.json` |
| Агент (новая роль) | `cycle/untrusted/economic_spec_generator/prompt_cross.md` |

## Честные оговорки

- **Faithfulness суммари — moat и трудная часть.** Слишком сильное суммари ложно доказывает; ловим Обяз. 2 + Lean, но **рамка (no-reentrancy) остаётся доверенной** (не разряжается солвером на конкретном токене — её природа межтранзакционная).
- **Mined-клоз ↔ discharge: теперь ОДИН клоз (2B), не прокси.** Остаточный L1-мост — только **идентификация переменных** `vaultBal := balanceOf(vault)` (caller-side зеркало ↔ callee-side balance): человеческая сверка, как мост L1 реестра. Уровень L2 — вне scope.
- **Per-clause discharge пока на РУЧНЫХ harness'ах.** 2B-дельта-harness'ы (`MiniERC20Delta`, `BurnFeeERC20Delta`) написаны вручную; **авто-генерация callee-harness из добытого клоза** (чтобы майнинг и discharge были одной кнопкой для любого клоза) — следующий шаг. Methodology обещает sound/needed-триаж 100% клозов; реализовано: sufficiency/weakness (caller) + ручной delta-discharge (callee) для добытого клоза.
- **`HostileERC20` — концептуальный экспонат, не runnable-атака.** VaultAsset не имеет hook'а, в triage не участвует. Runnable-свидетельство реентрантности = проба Step-0 B3 (солвер сам синтезировал реентрантный `setX` и refute'ил). Полный runnable reentrancy-attack harness (vault hook + refuted solvency) — именованный следующий шаг.
- **Живая агент-генерация — seed-replay, не измеренная способность.** `prompt_cross.md` готов, но `orchestrator.py` в cross-режиме теперь **требует `--spec-file`** (отказывается молча звать обычный prompt). Claim «агент over-генерит I_A + G_B» корректен как design/replay; N прогонов живого агента — следующий шаг.
- **Greedy ablation** даёт *а* минимальный набор, не глобально-минимальный при коррелированных клозах.
- **k-bound CHC** на глубоких реентрантных интерливингах (та же оговорка §7 ADR).
- **Найденная vacuous-proof в `trusted`-режиме** — это поведение версии solc 0.8.35; стоит сообщить upstream (issue), а не только зафиксировать.

## Долгосрок (объявлено)

1. **A/G как мост L2 между движками:** SMTChecker доказывает caller'а под суммари (дёшево), Lean/evm-smith разряжает гарантию callee на байткоде (доверенно), спека границы = общий объект. Ровно cross-contract цель `task.md` Трек 3.
2. **Само-наполняющаяся библиотека суммари:** каждый разряженный callee (ERC20, ERC4626, oracle) кладёт переиспользуемую *слабейшую* гарантию. Moat = курируемая библиотека суммари.
3. **Реентрантность как first-class разряжаемое допущение** (evm-smith Frame library) — закрыть рамку честно.
4. **CEGAR над суммари:** контрпример I_A называет слабый клоз → агенту → уточнить → петля (0002/D2 на интерфейсе).
5. **Слабейший интерфейс как продукт:** ablation-минимизированный контракт = точное свойство, которое обязана давать зависимость; аудируемо и переиспользуемо.

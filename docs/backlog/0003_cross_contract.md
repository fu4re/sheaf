# Task 0003 — Кросс-контрактная верификация через assume-guarantee: солвер на границе контракта

- **Дата:** 2026-06-25 · **Тип:** методология + e2e-валидация (итерация цикла)
- **Опирается на:** Finding 0002 (solver-as-judge на self-contained Vat) · `task.md` Трек 3 · A/G-контракты (Sharf–Besselink–Johansson, arXiv 2103.13743)
- **Домен:** vault (caller) + ERC20 (callee) — `cycle/contracts/cross/`
- **Статус:** **валидировано** (см. Finding 0004); этот документ фиксирует методологию для переиспользования.

---

## TL;DR постановки

Поднять цикл с self-contained контрактов (Vat) на **межконтрактное взаимодействие** (composition: из A⊨spec_A и B⊨spec_B получить гарантию на A∘B), где:
1. внешний вызов абстрагируется **assume-guarantee-суммари** = `havoc + require(G_B)` — **тот же механизм**, что ghost-абстракция нелинейной арифметики (Slice 2), поднятый с арифметической операции на вызов;
2. **судьёй остаётся солвер**: три A/G-обязательства + добыча слабейшей гарантии ablation'ом, ноль LLM-судьи;
3. **trusted base гарантии callee разряжается машинно** (Lean), а рамка (no-reentrancy) — честно локализуется как остаточное доверенное допущение;
4. AI-агент получает новую роль: **интерпретировать внешний вызов** = предложить декомпозицию (I_A + over-generated G_B), фильтрацию берёт солвер.

**Главная метрика:** для 100% клозов G_B — вердикт солвера (sound/unsound × needed/unneeded); I_A доказан под слабейшим достаточным суммари; ни одна точка доверия не на LLM.

---

## Мотивация

- **Vat был выбран self-contained** именно потому, что Aave оказался cross-contract — отложили (`PROVENANCE.md:5`). Cross-contract = заявленная **территория роста** проекта («самое ценное и самое трудное совпадают»; «cross-contract уязвимости не ловит почти никто», `insights/fv_and_agentic_development.md`).
- **Цитируемая работа** — абстрактная алгебра A/G-**контрактов** (assumption/guarantee, refinement, условия композиции), в её домене разряжаемая через LP. **Наш вклад = инстанцировать её на EVM, разряжая условия композиции солвером (SMTChecker) вместо LP.**
- **Реврейм, на котором всё держится:** `require`, пинавший havoc'нутый `mintedShares` в `ProportionalVaultGhost.sol`, **категориально тождественен** assumed guarantee внешнего вызова. Кросс-контракт — **лифт** существующей машинерии, не новая инфраструктура.

---

## Методология (что стало True)

A/G-контракт компонента = (Assumption, Guarantee). Три обязательства солвера + рамка:

### Обяз. 1 — CALLER proof
`A ⊨ I_A`, где каждый внешний вызов B заменён суммари = `havoc(проекция storage B) + require(G_B)`. Зеркалим **только** ту ячейку B, что читает I_A (`vaultBal`). havoc = свежий вход `vaultBal_post`; пин = инъектируемый `require(G_B)`. **DoD:** I_A `proven` относительно G_B; слишком слабое суммари `refuted` (не-вакуумность).

### Обяз. 2 — CALLEE discharge (главная, judge=solver)
`B ⊨ G_B`, корзины proven/refuted/unknown + Lean. **ВАЖНО — разряжать ИМЕННО добытый клоз, а не прокси.** Консервация `Σ balanceOf == totalSupply` **необходима, но недостаточна**: burning-fee токен её сохраняет (Σ и totalSupply падают синхронно), но недо-кредитует получателя — ломая дельта-клоз caller'а. Поэтому:
- **2A (консервация)** — ловит supply-inflation и losing-fee; **пропускает burning-fee** (зазор).
- **2B (дельта)** — разряжает сам добытый клоз `vaultBal_post >= vaultBal + assets` в callee-side форме («transfer кредитует ≥ amount»), **chc+bmc** (BMC ловит 2-шаговый CE). Burning-fee `refuted` здесь, хотя прошёл 2A.
**DoD:** honest `proven`; все adversarial (включая burning-fee) `refuted` на 2B; разряжаемое свойство = свойство, на которое опирается caller. **Текущий статус:** 2B-harness'ы ручные; авто-генерация callee-harness из добытого клоза — следующий шаг.

### Добыча слабейшего интерфейса (ablation — «отбросить ненужное»)
Агент over-генерит конъюнкцию клозов; солвер, без LLM-судьи: (a) **sufficiency/weakness на caller-side** (дроп клоза = инъект `"true"`; если I_A всё ещё proven → unneeded → drop; логически слабейший = добытый интерфейс); (b) **sound-фильтр на callee-side** = Обяз. 2B discharge добытого клоза. **DoD:** weakest sufficient G_B вычислен солвером И разряжен на callee одним и тем же клозом. **Честно:** реализованы caller-side mining + ручной 2B-discharge добытого клоза; полный per-clause авто-discharge всей конъюнкции — следующий шаг.

### Обяз. 4 — РАМКА (честная оговорка, не разряжается этим циклом)
Суммари трогает только то, что трогает B, **без реентрантности в A**. Реентрантность — не state-property B, а callback в A; Обяз. 2 её не видит, whole-program не выделяет (`untrusted` refute'ит всё, `trusted`+iface вакуумен). ⇒ no-reentrancy — **явно названный доверенный клоз**, разрядка на байткоде (evm-smith) = следующий экспонат.

---

## Открытые развилки

- **D1 — caller↔callee мост.** Клозы caller'а над `vaultBal_post`; гарантия callee над `balanceOf`. Связь `vaultBal := balanceOf(vault)` — модельный шаг L1 (человеческая сверка), как реестр L1. L2 (единый формализм) — вне scope.
- **D2 — CEGAR над суммари (scope-флаг).** Контрпример I_A → слабый клоз → агенту → уточнить → петля. По умолчанию: артефакт сохраняем, петлю опционально.
- **D3 — разрядка рамки no-reentrancy** через evm-smith Frame library / статпроверку — следующая итерация, не эта.

---

## Метрики

| Ось | Метрика | Приоритет |
|---|---|---|
| **Обяз. 2 (главная)** | доля клозов с вердиктом солвера; sound/unsound | главная |
| Обяз. 1 | I_A proven под суммари; whole-program (стена) для контраста | вторичная |
| Mining | размер mined_interface; # отброшенных unneeded; # пойманных unsound | вторичная |
| Рамка | разряжено vs остаётся в trusted base (no-reentrancy) | контроль |
| — | стоимость `claude -p`; стохастика по N прогонам | контроль |

---

## Сетап (воспроизводимый, расширение пилота)

- **SUT:** `VaultAsset` (A, `IERC20`) + `MiniERC20`/`HostileERC20`/`FeeERC20` (B). I_A = `vaultBal >= totalAssets`.
- **Гейтвей:** `build_cross_harness` (теги `__INVARIANT__` + `__SUMMARY__`), детерминированный compile-check.
- **Судья:** SMTChecker CHC/z3 × 3 обязательства + ablation (`triage.py::{mine_interface,triage_callees}`).
- **Разрядка:** Lean `Erc20.transfer_sum_preserved` + реестр L1.
- **e2e:** `orchestrator.py --cross-template …` (один command) / `cross_triage_demo.py` (полный триаж).
- **Артефакты:** `measurement/artifacts/cross_ag__triage.json`, `measurement/wall_map_cross.md`.

---

## Риски и честные оговорки (заранее, подтвердились)

- **`trusted`-режим SMTChecker неадекватен:** на интерфейсе вакуумен (доказывает `assert(false)`), на конкретном типе требует исходник + не композиционен. A/G — единственный режим с явной refutable гарантией. (Сообщить upstream.)
- **Faithfulness суммари = moat** (как ghost-аксиома). Слишком сильное → ложный proved; ловим Обяз. 2 + Lean; рамка остаётся доверенной.
- **Greedy ablation** — *а* минимальный набор; **k-bound CHC** на глубоких интерливингах.

---

## Порядок действий (по отдаче/риску) — выполнено

1. **Step 0 (блокирующий):** пробы модели внешнего вызова → матрица стены + фрейминг. ✓
2. **Обяз. 1:** caller-под-суммари proven / buggy refuted. ✓
3. **Обяз. 2:** discharge honest proven / adversarial refuted. ✓
4. **Mining:** weakest sufficient interface. ✓
5. **Lean:** разрядка консервации + реестр. ✓
6. **Доставка:** Finding 0004 + wall_map_cross + артефакты. ✓
7. **Следующее:** N прогонов агента (стохастика); разрядка рамки (D3); ERC4626/oracle в библиотеку суммари.

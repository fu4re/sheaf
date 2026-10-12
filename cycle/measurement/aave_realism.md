# Реализм агентской spec-генерации на реальном Aave (T-05 / T-15 / §5.4)

**Вопрос:** насколько близко агент подходит к эксперту Certora по части генерации
экономических спек — на настоящем `ATokenVault.deposit` (fees, yield-accrual,
aToken-rebase, округление)?

**Сетап:** модуль [1] (claude -p, sonnet) читает реальный `ATokenVault.sol` и
перечисляет набор экономических инвариантов; модуль [6] (LLM-судья) считает
покрытие против 7 **доказанных** Certora-инвариантов. Один прогон.
Артефакты: `artifacts/ATokenVault__spec_set.json`, `artifacts/ATokenVault__coverage.json`.

---

## Результат: 64% покрытия + 4 «лишних» инварианта

| Certora-инвариант | Статус | Чем покрыт |
|---|---|---|
| `solvency` (`totalSupply!=0 ⇒ totalAssets!=0`) | ✅ recovered | `solvency_nonzero_supply` |
| `fees_backed` (`claimableFees ≤ aTokenBal`) | ✅ recovered | `fee_bounded_by_atoken_holdings` |
| `accounting_leq_real_balance` | ✅ recovered | `last_vault_balance_le_actual` |
| `balance_leq_supply` | ✅ recovered | `per_account_share_conservation` |
| `conservation_shares` (`sumAllBalance == totalSupply`) | 🟡 partial | дал корролярий `balanceOf ≤ totalSupply`, не сумму |
| `fees_monotonic` | ❌ missed | — |
| `balance_change_causes_accrual` | ❌ missed | — |

**recovered 4 · partial 1 · missed 2 ≈ 64%** — в баллпарке PropertyGPT (80% при
многих прогонах; здесь один shot и более жёсткая цель).

---

## Главная находка: промахи СТРУКТУРНЫЕ, не случайные

Агент промахнулся ровно по тем инвариантам, которые **не выразимы в его выходном
языке** (одна Solidity-строка над текущим состоянием) — это не пробел знаний, а
**пробел выразительности**:

1. **`sumAllBalance() == totalSupply()`** требует **ghost-суммы по mapping** (Certora
   ведёт её ghost-переменной с hook'ами на изменение баланса). В plain-Solidity это
   невыразимо — **та же стена квантора/ghost, что и в T-04**. Агент дал максимум
   выразимого: `balanceOf(receiver) <= totalSupply()`.
2. **`fees_monotonic`** и **`balance_change_causes_accrual`** — **темпоральные / 2-state**
   свойства (`old() vs new`). Шейп «инвариант одного состояния» их не выражает.

→ Чтобы закрыть разрыв, нужен не «более умный агент», а **расширение DSL инварианта**:
(а) ghost-сумма по mapping, (б) форма pre/post (`old()`). Это конкретный, действенный вывод.

## Над-генерация (precision < coverage)

Агент предложил 8, экспертных покрыл 5, плюс **4 сверх набора**:
- `accounting_identity`: `ATOKEN.balanceOf(this) == totalAssets() + getClaimableFees()`
  — **точная и более сильная**, чем у Certora: агент вытащил из кода само определение
  `totalAssets()` (стр. 462) и поднял его в инвариант. Сильный сигнал.
- `fee_rate_bounded_by_scale` (`getFee() <= 1e18`) — верно (код требует `fee <= SCALE`).
- `total_assets_net_of_fees_non_negative` — корректно (защита от underflow в `totalAssets`).
- `shares_backed_proportionally` — агент сам потянулся к **нелинейному `mulDiv`** — это
  **ровно стена Slice 2**. Без ghost-аксиомы она не докажется; солвер её отфильтрует.

Это и есть профиль PropertyGPT (coverage > precision): агент находит много, часть
избыточна/недоказуема → нужен **символьный фильтр** (ядро доказывает настоящие,
отсекает фантомы). Johansson №2 вживую.

---

## Вердикт по реализму

- **Stateless экономический слой — реалистичен уже сейчас.** 1-строчные законы
  (солвентность, fee-backing, accounting-bounds) агент генерит ~на уровне эксперта,
  иногда дословно. Гипотеза ADR §5.2 «экономику генерить (относительно) легко»
  на Tier-2 **подтверждается**.
- **Quantified (ghost-сумма) и temporal (2-state) — пока НЕ реалистичны** как свободная
  генерация, и по выразительной, а не интеллектуальной причине → чинится DSL'ом.
- **Proof harness остаётся moat'ом** (insights №1–2): мерили только ГЕНЕРАЦИЮ;
  доказуемость этих инвариантов на Aave упирается в `rayMul`-стену (T-14, отдельно).
- Связность арки: промах `sumAllBalance` = стена ghost/квантора (T-04); «лишний»
  `shares_backed_proportionally` = нелинейная стена (Slice 2). Стены одни и те же по циклу.

## Честные оговорки

- **Один прогон.** Стохастику не мерили (отложено) — N прогонов сдвинут числа;
  ⇒ 64% это точечная оценка, не распределение (риск №7).
- **Судья — сам LLM** (субъективность recovered/partial/missed). Усиление: проверять
  «recovered» **солвером** на логическую эквивалентность (см. обсуждение детерминизма).
- Покрытие против дистиллированных 7 свойств; функциональные `erc4626.spec` (округление)
  исключены как не-экономические.

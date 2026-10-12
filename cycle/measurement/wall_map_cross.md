# Карта стен SMTChecker — экспонат #2 (Task 0003: кросс-контрактный вызов через assume-guarantee)

**Вопрос:** кросс-контрактный инвариант (солвентность vault'а, держащего РЕАЛЬНЫЙ внешний
ERC20) доказуем в SMTChecker? Внешний вызов — это новая стена (по аналогии с нелинейной
стеной экспоната #1). Снимает ли её assume-guarantee-суммари?

**Дата:** 2026-06-25 · solc 0.8.35 · z3 4.16.0 · движок CHC · targets=assert

SUT: `contracts/cross/VaultAsset.sol` (A, держит `IERC20`) + `contracts/cross/MiniERC20.sol` (B).
Инвариант I_A (солвентность): **`vaultBal >= totalAssets`** (vault держит ≥ того, что учёл;
донат только усиливает ⇒ `>=`, не `==`). `vaultBal` — зеркало `asset.balanceOf(address(this))`.

---

## Матрица: два встроенных режима SMTChecker оба неадекватны, A/G — третий путь

| # | Конфигурация | модель внешнего вызова | вердикт ядра |
|---|---|---|---|
| **A** | whole-program `{VaultAsset+MiniERC20}`, `IERC20`, `untrusted` (дефолт) | havoc + synthesized reentrancy | **violation** (стена: истинный инвариант недоказуем) |
| **A′** | то же, поле типизировано КОНКРЕТНЫМ `MiniERC20` | havoc (всё равно) | **violation** (стена держится и для конкретного типа) |
| **B** | A/G-суммари `trusted/harness/cross/VaultAssetAG.sol` | вызов заменён `havoc + require(G_B)` | **proved** (2 VC) |
| **B-buggy** | `VaultAssetAGBuggy.sol` — слишком слабое суммари (`vaultBal_post >= vaultBal`) | havoc недо-ограничен | **violation** (refuted — не-вакуумность) |
| **T-iface** | whole-program, `IERC20`, `--model-checker-ext-calls trusted` | callee-код неизвестен → путь после вызова отброшен | **ВАКУУМНО proved** (доказывает даже `assert(false)`) |
| **T-concrete** | whole-program, конкретный тип, `trusted` | реальный inlining известного кода | **sound** (корректно refute'ит `assert(false)`) |

**Главный вывод:** из коробки SMTChecker даёт ровно два неадекватных варианта —
- `untrusted` (дефолт, **звуковой**): каждый внешний вызов = worst-case реентрантный havoc
  → **refute'ит истинный кросс-контрактный инвариант** (строки A/A′). Бесполезно для
  композиции.
- `trusted` + **интерфейс** (типичный реальный случай — интегрируешься против `IERC20`, а не
  против исходника конкретного токена): **ВАКУУМНО** — молча «доказывает» что угодно (T-iface).
  Это живая ловушка vacuous-proof в продакшн-инструменте EF.

A/G-суммари (строка B) — третий путь: доказывает I_A относительно **явной, отдельно
разряжаемой** гарантии G_B. Точность как у `trusted`, но рамка сделана явной и refutable,
а не молчаливой.

---

## Подтверждение havoc+реентрантности (проба B3, дословный трейс ядра)

`assert(x == xBefore)` через внешний вызов `asset.transferFrom(...)`:
```
asset.transferFrom(msg.sender, address(this), assets) -- untrusted external call, synthesized as:
    VaultAsset.setX(1) -- reentrant call
```
Ядро **само синтезирует внешний вызов как реентрантный callback** в публичную функцию A и
havoc'ит состояние A. Это (а) обосновывает, почему harness *заменяет* вызов, а не
вызывает-и-ограничивает (через реальный вызов доказать нельзя — havoc'ится всё), и (б) есть
конкретное лицо A/G-рамки (Обяз. 4): суммари ASSUME'ит отсутствие реентрантности в A.

---

## Три обязательства assume-guarantee (всё вердиктом солвера, 0 LLM-судьи)

| Обяз. | Что | Артефакт | вердикт |
|---|---|---|---|
| **1** (caller) | A ⊨ I_A под суммари G_B | `VaultAssetAG.sol` | **proven** |
| **2A** консервация (honest) | B ⊨ `ghostSum == totalSupply` | `MiniERC20Conservation.sol` | **proven** |
| 2A (adversarial) | супли-инфляция | `MiniERC20ConservationBuggy.sol` | **refuted** |
| 2A (adversarial) | losing-fee | `FeeERC20Conservation.sol` | **refuted** |
| 2A (**ЗАЗОР**) | **burning-fee** | `BurnFeeERC20Conservation.sol` | **proven** ← держит консервацию, но недо-кредитует |
| **2B** дельта (honest) | «transfer кредитует ≥ amount» (= добытый клоз) | `MiniERC20Delta.sol` | **proven** (chc+bmc) |
| 2B (закрывает зазор) | **burning-fee** | `BurnFeeERC20Delta.sol` | **refuted** (bmc) |

**Зазор conservation ≠ delta (само-найденный, закрыт):** разряжать надо **сам добытый дельта-клоз**
(`vaultBal_post >= vaultBal + assets`), а не прокси-консервацию — burning-fee её сохраняет, но
ломает дельту. 2B (chc+bmc, BMC ловит 2-шаговый CE) разряжает именно тот клоз, на который опирается
caller. Обяз. 2 ловит «плохой callee» *до* доверия суммари — как `debt<=Line` в Finding 0002, но на границе.

---

## Добыча слабейшего интерфейса (ablation — «солвер отбрасывает ненужное»)

Агент over-генерит клозы-кандидаты G_B для deposit-вызова; солвер решает достаточность и
логическую силу (`measurement/cross_triage_demo.py`, артефакт `cross_ag__triage.json`):

| клоз | вердикт | роль |
|---|---|---|
| `vaultBal_post == vaultBal + assets` (exact) | proven | sufficient (сильнее, чем нужно) |
| `vaultBal_post >= vaultBal + assets` (at_least) | proven | **sufficient + ВЕСЕЙШИЙ** ← добытый интерфейс |
| `vaultBal_post >= vaultBal` (monotone) | refuted | insufficient → отброшен |
| `vaultBal_post <= vaultBal + assets` (upper) | refuted | insufficient → отброшен |
| `assets <= type(uint128).max` (irrelevant) | refuted | insufficient → отброшен |

**Слабейшая достаточная гарантия = `vaultBal_post >= vaultBal + assets`** («токен кредитует
vault НЕ МЕНЬШЕ чем на `assets`») — тугейший спрос на B, самая переиспользуемая суммари.
Это assumption-синтез символьно, не мнением LLM.

---

## Находки

1. **Внешний вызов — реальная стена, и она НЕ снимается выбором конкретного типа** (A′).
   `untrusted` havoc'ит независимо от статического типа; истинный кросс-контрактный инвариант
   недоказуем «в лоб».
2. **`trusted`+интерфейс ВАКУУМЕН** — доказывает `assert(false)` (T-iface vs T-concrete vs
   untrusted-control). Прямая vacuous-proof ловушка в SMTChecker для самого частого случая
   (вызов через `IERC20`).
3. **A/G-суммари = havoc + require(G_B)** переводит стену `violation` → `proved` (B), и это
   **категориально тот же механизм**, что ghost-абстракция нелинейной арифметики (экспонат #1):
   `require`, пинавший `mintedShares`, теперь пинает эффект внешнего вызова.
4. **Абстракция не вакуумна** (B-buggy refuted) и **плохой callee ловится** Обяз. 2
   (buggy/fee refuted).
5. **Солвер добывает слабейшую достаточную гарантию** ablation'ом — `>= vaultBal + assets`.

---

## Границы находки (честные оговорки)

- **Faithfulness суммари** (звуковая над-аппроксимация B) — это moat/трудная часть, ровно как
  faithfulness ghost-аксиомы (экспонат #1, `ghost.md:47`). Слишком СИЛЬНОЕ суммари дало бы
  ложный `proved`; ловим Обяз. 2 + Lean. Остаточный trusted base = **рамка no-reentrancy**.
- **Рамка (Обяз. 4) НЕ разряжается солвером на конкретном токене.** Реентрантность `HostileERC20`
  — это свойство «B зовёт обратно в A», не state-property B; Обяз. 2 (консервация B) её не видит.
  whole-program её тоже не выделяет (`untrusted` refute'ит ВСЁ; `trusted`+iface вакуумен). Значит
  no-reentrancy остаётся **доверенным допущением суммари** — честно локализованный trusted base.
  Разрядка реентрантности на байткоде (evm-smith Frame library) — следующий экспонат.
- **Greedy ablation** даёт *а* минимальный набор, не глобально-минимальный при коррелированных
  клозах. Зафиксировано честно.
- **k-bound CHC** на глубоких интерливингах — та же оговорка §7 ADR.

---

**Артефакты:** `contracts/cross/{VaultAsset,MiniERC20,HostileERC20,FeeERC20}.sol`;
`trusted/harness/cross/{VaultAssetAG(+Buggy),MiniERC20Conservation(+Buggy),FeeERC20Conservation}.sol`;
`gateway/translator.py::build_cross_harness`; `measurement/triage.py::{mine_interface,triage_callees}`;
`measurement/cross_triage_demo.py` → `measurement/artifacts/cross_ag__triage.json`;
Lean `AaveArith/Basic.lean::Erc20.transfer_*` + `axiom_registry.json`.

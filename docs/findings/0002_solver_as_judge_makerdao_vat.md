# Finding 0002 — Solver-as-judge on a self-contained real contract (MakerDAO Vat)

- **Дата:** 2026-06-22 · **Тип:** эмпирический замер (один прогон, pilot) · **Опирается на:** Finding 0001, Task 0002
- **TL;DR:** на реальном self-contained `Vat` (DSS CDP-ядро) **судьёй был солвер, не LLM**.
  Агент **поднял локальные `require`-guards `frob` в инварианты, но промахнулся по всем
  глобальным законам сохранения**. Солвер это вскрыл сам: **опроверг** ложный агентский
  инвариант контрпримером и **доказал** закон сохранения, который агент даже не выразил.
  Агент и символьное ядро оказались **комплементарны**.

## Сетап (воспроизводимый)

| | |
|---|---|
| Цель | MakerDAO `dss` @ `fa4f663`, `src/vat.sol` — **self-contained** (ноль внешних вызовов), rad/ray/wad CDP-учёт |
| SUT | порт 0.6.12→0.8, **эквивалентность доказана**: хирургический diff + дифференциальный фаззинг 300×16 = **4800 операций, ноль расхождений** (`cycle/ground_truth/dss_vat/port_notes.md`) |
| Метод | `frob` (lock collateral / draw debt) |
| Ground truth | каноничные инварианты Maker (K-framework/Certora): `Σdai==debt`, `Σsin==vice`, `Art==Σart`, `debt==vice+Σ(Art·rate)`, fold-монотонность |
| Генератор | агент (`claude -p`, sonnet), набор инвариантов; $0.20 |
| **Судья** | **SMTChecker/Z3** (CHC + BMC) — корзины proven/refuted/inconclusive + артефакты. **LLM-судья исключён из контура доверия.** |

## Генерация: агент поднимает guards, не видит сохранение

8 инвариантов. **Пять** — дословно `require`-проверки `frob` (синтаксически видны в коде):
collateralization `art·rate <= ink·spot`, dust, debt-ceiling `Art·rate<=line`, global
ceiling `debt<=Line`, ilk-init `rate!=0`. **Три** — слабые королларии законов Maker
(`debt>=vice`, `art<=Art`, `debt>=Art·rate`).

**Промахнулся по ВСЕМ глобальным законам сохранения** (`Σdai==debt`, `Σsin==vice`,
`Art==Σart`) — они эмерджентны (сумма по mapping, рассуждение через все функции), не
видны в `frob`. Тот же структурный промах, что в Finding 0001, **+ новый паттерн:
агент лифтит локальные guards, а не выводит глобальную консервацию.**

## Судья = солвер (а не LLM): три исхода на реальном Vat

| Кандидат | Движок | Вердикт | Артефакт |
|---|---|---|---|
| `debt <= Line` (агентский) | **BMC** | **refuted** | witness `Line=0, debt=1` |
| `Σ dai == debt` (Maker, агент НЕ предложил) | CHC | **proven** | tracked-sum ghost harness |
| `debt == vice + Σ(Art·rate)` (Maker solvency) | CHC | **proven** | ray-mul абстрагирован product-ghost; faithfulness ← Lean `ar_delta` |
| `debt<=Line`, `debt>=vice` на сыром полном Vat | CHC | **inconclusive** | complexity wall |

Доказаны **два** реальных закона сохранения Maker (`Σdai==debt`, solvency), один агентский
over-claim **опровергнут** — всё вердиктом солвера, ноль LLM-судьи.

- **Опроверг агентский over-claim:** `debt<=Line` — это локальный `require` `frob`, но как
  **глобальный инвариант ложен** (`suck`/`fold` поднимают debt мимо проверки). Солвер нашёл
  контрпример **сам, без мнения модели** — операционализация «агент находит что хочет,
  символьное — что истинно» (Johansson №2) **символьным ядром**, не второй нейросетью.
- **Доказал закон, который агент пропустил:** `Σdai==debt` на фокусном harness — `proven`.

## Комплементарность (главный вывод)

Агент и ядро **дополняют друг друга**: агент видит **локальные guards** (которые ядро не
верифицирует на сыром Vat из-за сложности), ядро доказывает **глобальную консервацию**
(которую агент даже не выражает). Ценность цикла — в их **связке** + фокусном proof-harness
(доверенные леса). Это прямо тезис «moat = proof harness, не генерация инвариантов».

## Карта стен реального Vat (новые экспонаты)

1. **Complexity wall:** сырой полный Vat → CHC `inconclusive` даже для `live<=1` (тонет в `frob`/`fold`).
2. **Знаковая арифметика `_add(uint,int)`** (two's-complement reinterpret + wrap-check) **ломает CHC**
   даже на тривиально-индуктивном инварианте → лечится **звуковой CHC-дружественной переформулировкой**.
3. **Сумма по mapping** (`Σdai`) невыразима → tracked-sum ghost (как Finding 0001).
4. **BMC находит мелкие контрпримеры, которых CHC не берёт** (`debt<=Line`) — движки комплементарны.
5. **Нелинейный `Art·rate`** (solvency) → абстрагирован product-ghost `ghostAR`; инвариант
   `debt==vice+ghostAR` **proven**. Faithfulness шадоу (`ghostAR == Σ Art·rate`) опирается на
   **Lean-доказанную дистрибутивность** `ar_delta` ((Art+dart)·rate = Art·rate + dart·rate).
   Это **первый случай, когда Lean-теорема замыкает trusted base реального инварианта** —
   шадоу не на веру, а на машинно-проверенной теореме (мост L1: prose-референс в
   `cycle/trusted/proofs/axiom_registry.json`, не вшито в код по решению о decoupled-link).

## Сдвиг относительно Finding 0001
Там: judge=LLM, один прогон, recall — единственная метрика, mock-уровень. Здесь: **judge=солвер**
(proven/refuted/inconclusive + артефакты прувера), **реальный self-contained контракт**,
**SUT доказанно эквивалентен оригиналу**, ядро **само опровергает и доказывает**.

## Артефакты и воспроизводимость

| Что | Где |
|---|---|
| Оригинал Vat (байт-в-байт) + порт (SUT) | `cycle/ground_truth/dss_vat/{legacy/Vat_0_6.sol, src/Vat.sol}` |
| Доказательство эквивалентности порта | `cycle/ground_truth/dss_vat/{port_notes.md, test/VatDiff.t.sol}` → `forge test` (300 runs) |
| Фокусные harness'ы (proven) | `cycle/trusted/harness/{VatDaiConservation,VatSolvency}.sol` (+ Buggy) |
| Солвер-судья (триаж) | `cycle/measurement/triage.py` (proven/refuted/inconclusive; равенство ← солвер) |
| Агентский набор инвариантов | `cycle/measurement/artifacts/Vat__spec_set.json` ($0.20, sonnet) |
| Ground-truth Maker | `cycle/measurement/ground_truth/vat_invariants.json` |
| Lean-теоремы + реестр (trusted base) | `cycle/trusted/proofs/{aave_arith/AaveArith/Basic.lean, axiom_registry.json}` |

## Честные оговорки
- **Фокусные harness'ы — звуковые над-аппроксимации** (havoc нерелевантного + точные дельты);
  это доверенные леса (proof harness), их фиделити — отдельный трудный вопрос (тот самый moat).
- **Один прогон** агента; стохастику не мерили.
- **На сыром полном Vat судья даёт inconclusive** для большинства — честное отражение
  complexity-стены реального контракта; осмысленные proven/refuted требуют фокусных harness'ов.
- Recall по 5 эталонам мал (0 полных, корролярии частично) — но агент нашёл 5 реальных
  safety-инвариантов сверх набора (Maker их тоже верифицирует).

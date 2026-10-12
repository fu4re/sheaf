# Карта вакуумности — экспонат #3 (Task T1: авто-гейт на пустые proof через мутацию инварианта)

**Вопрос:** «proved» может быть **пустым**. Можно ли БЕЗ ЧЕЛОВЕКА, одним солвером, ловить
вакуумные доказательства — недостижимый код (antecedent failure) и инварианты-прокси, не
несущие нагрузки? И в какой слой ложится такая проверка?

**Дата:** 2026-06-25 · solc 0.8.35 · z3 4.16.0 · targets=assert · judge = солвер, 0 LLM

**Канон:** Beer/Ben-David/Eisner (IBM Haifa 2001) — vacuity + antecedent-failure; Kupferman
(CONCUR 2006) — **vacuity = coverage = переверификация на мутированном входе**. Алгоритм гейта:
мутируй компонент инварианта → если вердикт не изменился → компонент инертен → (частично) вакуумно.

**Слой (ответ):** **доверенный слой рядом с солвером, НЕ агент.** Вакуумность — суждение о
качестве proof; отдать его LLM = модель оценивает собственное доказательство (запрещённый
анти-паттерн). Мутация — детерминированный синтаксический трансформ; вердикт — солвера;
PASS/FLAG — сравнение солверных вердиктов. Модуль `measurement/vacuity.py`, сосед `triage.py`.

---

## Два пробника (оба = мутируй-и-переверифицируй, 0 LLM-судьи)

| Пробник | Мутация | Движок | PASS / FLAG |
|---|---|---|---|
| **R** достижимость / antecedent-failure | инвариант → `false` | **CHC only** | `assert(false)` **proved** ⇒ точка недостижима ⇒ ВАКУУМНО → **FLAG**; **counterexample** ⇒ достижимо → **PASS**; inconclusive → **UNKNOWN** |
| **M** нагруженность («насколько бесполезна спека») | компонент → строго слабее | **per-family** | инвариант **proves** на плохом callee (blind spot) → **FLAG**; refute'ит всех адверсариев → **PASS** |

---

## Probe R — карта достижимости (CHC)

| harness | вид | `assert(false)` CHC | итог |
|---|---|---|---|
| **VaultAssetAGDead** (фикстура) | `require(false)` гард | **proved** | **FLAG** (antecedent failure) |
| **MiniERC20NoMintConservation** (фикстура) | underflow `totalSupply-=1` без mint | **proved** | **FLAG** (мёртвый путь) |
| MiniERC20Conservation | живой honest | counterexample | PASS |
| MiniERC20ConservationBuggy / FeeERC20 / BurnFee*Conservation | живые callee | counterexample | PASS |
| MiniERC20Delta | живой honest | counterexample | PASS |
| BurnFeeERC20Delta | адверсарий (2-state) | inconclusive | UNKNOWN¹ |

¹ UNKNOWN на BurnFeeERC20Delta несущественно: это **адверсарий**, его достижимость
само-сертифицируется его же refutation в Probe M (refute'ящий трейс достигает assert).
Probe R важен для harness'ов, которые мы ждём **proved** (там прячется вакуумность).

**Главное по R:** оба намеренно-вакуумных фикстура → **FLAG**; все honest-harness'ы достижимы.
`assert(false)`-proves — **сертификат недостижимости** (то же ядро, что вакуумный `trusted`-режим
из экспоната #2, `wall_map_cross.md:23`).

### CHC-only — не вкусовщина, а измерение
`assert(false)` на мёртвом underflow-пути: **CHC=proved (верно, недостижимо), BMC=counterexample
(ЛОЖНО)**. BMC не ограничивает входное состояние конструктор-достижимым → синтезирует
недостижимый трейс. Правило «refuted if ANY engine» здесь **обнулило бы вакуумный proof в PASS**
(false-negative). Поэтому Probe R — **только CHC**. Это противоположная движковая политика, чем у
Probe M (ниже) — путать нельзя.

---

## Probe M — гейт нагруженности (движок ⟂ виду инварианта)

| семья | инвариант | вид | движок | refuted | blind(proved) | **итог** |
|---|---|---|---|---|---|---|
| **conservation** | `ghostSum == totalSupply` | reachable-state (view) | **CHC** | SupplyInflation, LosingFee | **BurnFee** | **FLAG** (слепа к burning-fee) |
| **delta** | `balanceOf[to] >= beforeTo + amount` | 2-state Hoare (inline) | **CHC+BMC** | BurnFee | — | **PASS** |

**АВТО-ПЕРЕОТКРЫТИЕ ЗАЗОРА:** консервация **PROVES** на burning-fee callee (blind spot) — гейт
печатает «вакуумный прокси, используй дельту»; дельта **REFUTES** того же burning-fee (BMC) — чисто.
Это ровно зазор conservation≠delta, который в прошлой сессии нашли **руками под ревью** — теперь
пойман **автоматически**, без человека.

### Движок ⟂ кванторной форме инварианта (вторичная находка, измерено)
| вид инварианта | пример | сonsound движок | почему |
|---|---|---|---|
| reachable-state (над достижимыми состояниями) | консервация в `view` | **CHC** | BMC проверяет из СВОБОДНОГО входного состояния → spurious refutation из конструктор-недостижимого `ghostSum=1,totalSupply=0` (пустой трейс) — **двойник вакуумного proof: spurious counterexample** |
| 2-state / per-transition Hoare | дельта inline в `transfer` | **CHC+BMC** | свойство держится из ЛЮБОГО входа под precondition; CHC отдаёт under-credit как inconclusive, BMC ловит |

Использование BMC на reachable-state инварианте даёт **ложные опровержения** (измерено: honest-консервация
«refuted» под BMC). Движок **обязан** соответствовать кванторной форме — это объявляется per-family
(как в коде уже: `triage_one`/CHC для консервации vs `discharge`/CHC+BMC для дельты).

---

## Probe M2 — профиль полезности по компонентам (буквально «мутируй компоненты»)

**conservation** `ghostSum == totalSupply` (CHC) — `==` распадается на две нагруженные половины,
КАЖДАЯ защищает своего адверсария; **ни одно ослабление не ловит BurnFee** (зазор структурен свойству):

| мутация | класс | refutes | потеряно |
|---|---|---|---|
| `drop_to_true` (⊤) | load_bearing | — | →blind: SupplyInflation, LosingFee |
| `eq_to_ge` (== → >=) | load_bearing | — | →blind: SupplyInflation · →undecided: LosingFee² |
| `eq_to_le` (== → <=) | load_bearing | SupplyInflation | →blind: LosingFee |

**delta** `balanceOf[to] >= beforeTo + amount` (CHC+BMC) — нагружено всё, КРОМЕ `beforeTo`;
у инварианта **нулевой допуск** (1 единица слака ослепляет):

| мутация | класс | refutes | потеряно |
|---|---|---|---|
| `drop_to_true` (⊤) | load_bearing | — | →blind: BurnFee |
| `zero_rhs` (RHS→0, тавтология) | load_bearing | — | →blind: BurnFee |
| `relax_plus1` (+1 слак) | load_bearing | — | →blind: BurnFee ← 1 единица слака = ровно сожжённая комиссия |
| `keep_only_beforeTo` (бросить `amount`) | load_bearing | — | →blind: BurnFee |
| `keep_only_amount` (бросить `beforeTo`) | **inert** | BurnFee | — ← `beforeTo` не ловит комиссию; нагрузку несёт `amount` |

² **Честно:** «потеряно→undecided» = ослабление сделало клоз НЕразрешимым в бюджете (CHC inconclusive),
а не доказуемо-инертным. Разделяем `proved`-blind (настоящая вакуумность) и `unknown` (бюджет солвера) —
иначе неполнота солвера маскируется под вакуумность.

---

## Находки

1. **`assert(false)`-proves = машинный сертификат недостижимости.** Оба намеренно-вакуумных
   фикстура (antecedent-failure `require(false)` и мёртвый underflow) пойманы **без человека**;
   все honest-harness'ы достижимы. Probe R — CHC-only (BMC даёт spurious-достижимость, измерено).
2. **Гейт САМ переоткрыл зазор conservation≠delta.** Консервация — blind к burning-fee (PROVES),
   дельта — refute'ит. Без LLM, тем же солвером. То, что ловил человек под ревью — теперь авто.
3. **Probe M2 даёт профиль полезности по компонентам.** `==` = две нагруженные половины (каждая —
   свой адверсарий); у дельты `amount` несёт нагрузку, `beforeTo` инертен, допуск нулевой
   (любой +1-слак ослепляет). Это прямой замер «насколько бесполезна спека».
4. **Движок обязан соответствовать кванторной форме инварианта** (reachable-state ⇒ CHC;
   per-transition Hoare ⇒ CHC+BMC). Нарушение → **spurious counterexample** — двойник вакуумного
   proof. Гейт раскрыл этот класс несоундности в собственном пайплайне.
5. **Слой определён:** вакуум-гейт — доверенный (солвер-судимый), не агентский. Единственная
   роль агента — downstream и опциональна: предложить усиление инертного компонента → пере-судит солвер.
6. **Гейт ужесточён до standing-grade (по ревью кода):** три статуса `PASS`/`FLAG`/**`BLOCKED`**
   («не смог проверить невакуумность» ≠ зелёное); precondition «base доказан на honest» (ложный
   инвариант → `FLAG`-invalid, не PASS); `vacuity_demo.py` — acceptance-check с **non-zero exit**
   (регрессия фикстуры валит прогон, не переписывает артефакт молча); witness/raw сохранены в
   артефакте (`discharge_ev`) — BMC-spurious улика `ghostSum=1,totalSupply=0` как доказательство.

---

## Границы находки (честные оговорки)

- **Каталог мутаций — конечный, синтаксический, для АТОМАРНЫХ реляционных инвариантов** (`a OP b`,
  `a OP b+c`). Конъюнкции реальных протоколов требуют богаче каталог — следующая итерация.
- **`undecided` ≠ `inert`.** Ослабление, делающее клоз неразрешимым в бюджете (CHC inconclusive),
  помечено `load_bearing?`/`lost→undecided`, не путается с доказуемой инертностью (honest split).
- **Семья = ручной маппинг harness'ов** (как весь курируемый harness-слой, T3). Авто-построение
  семьи из callee-side формы — вне scope.
- **Probe R сертифицирует достижимость в `untrusted`-модели `run_solver`.** `trusted`-режимная
  path-deletion-вакуумность (экспонат #2) ловится косвенно — через blind-spots Probe M, не через R.
- **Greedy по компонентам** — локальная классификация, не глобально-минимальный нагруженный набор
  при коррелированных компонентах (как greedy-ablation в mining).

---

**Артефакты:** `trusted/harness/cross/{VaultAssetAGDead,MiniERC20NoMintConservation}.sol` (фикстуры);
`measurement/vacuity.py` (`reachability_probe`/`mutate_invariant`/`family_discrimination`/
`load_bearing_profile`/`vacuity_gate`); `measurement/vacuity_demo.py` →
`measurement/artifacts/vacuity_report.json`. Реюз: `gateway/translator.py::build_from_harness`,
`measurement/triage.py::{discharge,_BUCKET,_safe_tag}`, `trusted/solver.py::run_solver`.

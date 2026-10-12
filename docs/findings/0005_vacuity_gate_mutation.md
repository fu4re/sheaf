# Finding 0005 — Авто-гейт на вакуумность через мутацию инварианта: солвер ловит пустые proof без человека

- **Дата:** 2026-06-25 · **Тип:** эмпирический замер (capability build, e2e) · **Опирается на:** Finding 0002 (solver-as-judge), Finding 0004 (cross-contract A/G, зазор conservation≠delta), `mvp_roadmap.md` T1, ADR-0002
- **TL;DR:** «proved» может быть **пустым**. Собрали **автоматический, без человека, гейт на вакуумность** (T1) — два солвер-судимых пробника, оба = *мутируй-и-переверифицируй* (Kupferman: vacuity = coverage = переверификация на мутированном входе). **Probe R** (инвариант → `false`; `assert(false)` **proved** ⇒ точка недостижима ⇒ FLAG) ловит **оба** намеренно-вакуумных фикстура (antecedent-failure `require(false)` и мёртвый underflow-путь); все honest-harness'ы достижимы. **Probe M** (мутируй компонент → дискриминация против семьи адверсариев) **САМ переоткрыл зазор conservation≠delta** — тот, что в Finding 0004 нашли **руками под ревью**: консервация PROVES на burning-fee callee (слепое пятно → FLAG), дельта его REFUTES (→ PASS). **Ответ на «в какой слой»: доверенный слой рядом с солвером, НЕ агент** — вакуумность это суждение о качестве proof, отдать его LLM = модель оценивает собственное доказательство. **Побочная находка:** движок ОБЯЗАН соответствовать кванторной форме инварианта (reachable-state ⇒ CHC; 2-state Hoare ⇒ CHC+BMC); BMC на state-инварианте даёт **spurious counterexample из недостижимого состояния — двойник вакуумного proof**. Честные границы: каталог мутаций пока атомарный, семьи — ручной маппинг.

---

## Сетап (воспроизводимый)

| | |
|---|---|
| Цель | **авто-гейт T1**: ловить пустые `proved` (недостижимый код + инварианты-прокси) одним солвером, 0 LLM-судьи |
| Probe R | инвариант → `false`; `run_solver(engine=chc)`. `proved` ⇒ недостижимо ⇒ ВАКУУМНО (FLAG); `counterexample` ⇒ достижимо (PASS); `inconclusive` ⇒ UNKNOWN |
| Probe M | мутируй компонент → строго слабее; `discharge` против СЕМЬИ (honest + adversarial siblings одной callee-side формы); blind spot = инвариант **proves** на плохом callee |
| Фикстуры (намеренно вакуумные) | `VaultAssetAGDead.sol` (`require(false)` гард) · `MiniERC20NoMintConservation.sol` (`totalSupply-=1` без mint → underflow-revert → мёртвый путь) |
| Семья conservation | honest `MiniERC20Conservation` + adv {supply-inflation, losing-fee, **burning-fee**} |
| Семья delta | honest `MiniERC20Delta` + adv {**burning-fee**} |
| **Судья** | **SMTChecker/Z3** — CHC для Probe R; per-family движок для Probe M. **LLM-судья исключён.** |
| Тулчейн | solc 0.8.35, z3 4.16.0 |
| Канон | Beer/Ben-David/Eisner (IBM Haifa 2001, antecedent-failure); Kupferman (CONCUR 2006, vacuity≡coverage≡переверификация на мутированном входе) |

Полная матрица — `cycle/measurement/vacuity_map.md`; артефакт — `cycle/measurement/artifacts/vacuity_report.json`.

---

## В какой слой ложится проверка (прямой ответ на постановку)

**Доверенный слой рядом с солвером, НЕ агент.** Три причины, все из хребта проекта:
1. **judge = solver, никогда LLM.** Вакуумность — суждение о **качестве** доказательства; LLM-судья = модель оценивает собственный proof (запрещённый анти-паттерн).
2. **Kupferman делает проверку механической.** Мутация — детерминированный синтаксический трансформ (0 семантики, 0 суждения); вердикт — солвера; PASS/FLAG — сравнение солверных вердиктов.
3. **Размещение в коде:** `cycle/measurement/vacuity.py`, сосед `triage.py`, реюз `build_from_harness`/`discharge`/`run_solver`. Не в `untrusted/`-мире агента.

Единственная роль агента — **downstream и опциональна:** пометил гейт компонент инертным → агент МОЖЕТ предложить усиление → **пере-судит солвер**. Агент предлагает, доверенный слой располагает.

---

## Probe R — достижимость / antecedent failure (только CHC)

`assert(false)`-proves = **машинный сертификат недостижимости** (то же ядро, что вакуумный `trusted`-режим из Finding 0004, `wall_map_cross.md:23`).

| harness | вид | `assert(false)` CHC | итог |
|---|---|---|---|
| **VaultAssetAGDead** (фикстура) | `require(false)` гард | **proved** | **FLAG** (antecedent failure) |
| **MiniERC20NoMintConservation** (фикстура) | underflow `totalSupply-=1` без mint | **proved** | **FLAG** (мёртвый путь) |
| MiniERC20Conservation + 3 adv-консервации | живые callee (view-инвариант) | counterexample | PASS |
| MiniERC20Delta | живой honest (inline) | counterexample | PASS |
| BurnFeeERC20Delta | adv (2-state) | inconclusive | UNKNOWN¹ |

¹ UNKNOWN на адверсарии несущественно: его достижимость **само-сертифицируется** его же refutation в Probe M (refute'ящий трейс достигает assert). Probe R важен для harness'ов, которые мы ждём `proved`.

**CHC-only — измерено, не постулировано.** `assert(false)` на мёртвом underflow-пути: **CHC=proved (верно), BMC=counterexample (ЛОЖНО)** — BMC не ограничивает входное состояние конструктор-достижимым. Правило «refuted if ANY engine» обнулило бы вакуумный proof в PASS (false-negative). Поэтому Probe R = **только CHC** (противоположная политика, чем у Probe M ниже).

---

## Probe M — нагруженность + авто-переоткрытие зазора (движок ⟂ виду инварианта)

| семья | инвариант | вид | движок | refuted | blind (proved) | **итог** |
|---|---|---|---|---|---|---|
| **conservation** | `ghostSum == totalSupply` | reachable-state (view) | **CHC** | supply-inflation, losing-fee | **burning-fee** | **FLAG** (слепа к burn) |
| **delta** | `balanceOf[to] >= beforeTo + amount` | 2-state Hoare (inline) | **CHC+BMC** | burning-fee | — | **PASS** |

**Зазор conservation≠delta переоткрыт АВТОМАТИЧЕСКИ.** Консервация **proves** на burning-fee callee (slepое пятно) — гейт печатает «вакуумный прокси»; дельта **refute'ит** того же burning-fee (под BMC) — чисто. Это ровно зазор из Finding 0004, найденный там **руками под ревью** — теперь пойман без человека, тем же солвером. (Иллюстрация «гейт ловит то, что ловил эксперт».)

### Probe M2 — профиль полезности по компонентам («мутируй компоненты, измерь бесполезность»)

`==` распадается на **две нагруженные половины**, каждая защищает своего адверсария; **ни одно ослабление консервации не ловит burning-fee** (зазор структурен свойству, а не настройке):

| мутация конс. | класс | refutes | потеряно |
|---|---|---|---|
| `drop_to_true` | load_bearing | — | →blind: supply-inflation, losing-fee |
| `== → >=` | load_bearing | — | →blind: supply-inflation · →undecided: losing-fee² |
| `== → <=` | load_bearing | supply-inflation | →blind: losing-fee |

У дельты нагружено всё, КРОМЕ `beforeTo`; **нулевой допуск** (1 единица слака ослепляет):

| мутация дельты | класс | refutes |
|---|---|---|
| `drop_to_true` / `RHS→0` / `+1 слак` / `бросить amount` | load_bearing | — (→blind: burn) |
| **`бросить beforeTo`** (`balanceOf[to] >= amount`) | **inert** | burning-fee ← нагрузку несёт `amount`, не `beforeTo` |

² **Честно:** «потеряно→undecided» = ослабление сделало клоз НЕразрешимым в бюджете (CHC inconclusive), а не доказуемо-инертным. Гейт **разделяет** `proved`-blind (настоящая вакуумность) и `unknown` (бюджет солвера) — иначе неполнота маскируется под вакуумность. Слепое пятно FLAG'ается **только** на `proved`.

---

## Побочная находка: движок ОБЯЗАН соответствовать кванторной форме инварианта

| вид инварианта | пример | соундный движок | почему (измерено) |
|---|---|---|---|
| reachable-state (над достижимыми) | консервация в `view` | **CHC** | BMC проверяет из СВОБОДНОГО входа → spurious refutation из конструктор-недостижимого `ghostSum=1,totalSupply=0` (пустой трейс) — **двойник вакуумного proof** |
| 2-state / per-transition Hoare | дельта inline в `transfer` | **CHC+BMC** | держится из ЛЮБОГО входа под precondition; CHC отдаёт under-credit как inconclusive, BMC ловит (комплементарность 0002) |

Использование BMC на reachable-state инварианте **«опровергает» даже honest-консервацию**. Это уже закодировано в пайплайне (CHC `triage_one` vs CHC+BMC `discharge`); гейт сделал правило **явным и измеренным**. `vacuity.py` объявляет движок per-family.

---

## Сдвиг относительно Finding 0004

| | 0004 (cross-contract A/G) | 0005 (vacuity gate) |
|---|---|---|
| Что доказываем | I_A под суммари + discharge G_B | **что сам proof не пуст** |
| Зазор conservation≠delta | найден **вручную под ревью** | **переоткрыт АВТОМАТИЧЕСКИ** гейтом |
| Несоундность инструмента | `trusted`+iface вакуумен (vacuous proof) | BMC на state-инварианте даёт **spurious counterexample** (дуальная несоундность) |
| Новое | слабейший интерфейс ablation'ом | **гейт на вакуумность**; движок ⟂ кванторной форме |

---

## Артефакты и воспроизводимость

| Что | Где |
|---|---|
| Гейт (R + M + mutate + family) | `cycle/measurement/vacuity.py` |
| e2e runner + артефакт | `cycle/measurement/vacuity_demo.py` → `cycle/measurement/artifacts/vacuity_report.json` |
| Намеренно-вакуумные фикстуры | `cycle/trusted/harness/cross/{VaultAssetAGDead,MiniERC20NoMintConservation}.sol` |
| Карта вакуумности | `cycle/measurement/vacuity_map.md` |
| Реюз (без правок) | `gateway/translator.py::build_from_harness`, `triage.py::{discharge,_BUCKET,_safe_tag}`, `trusted/solver.py::run_solver` |
| Один command e2e | `python3 -m cycle.measurement.vacuity_demo` |

---

## Интегритет гейта (ужесточение по ревью кода)

Гейт сам не должен давать ложно-зелёное — иначе подрывает собственную цель. Четыре правки (все проверены):
1. **Три статуса `PASS` / `FLAG` / `BLOCKED`.** «Не смогли проверить невакуумность» (Probe R `UNKNOWN`; недоказанный honest; undecided-адверсарий, где blind spot не исключить; семья без адверсариев) → **BLOCKED**, не PASS. `FLAG` = уверенная проблема (недостижимо / blind spot / инвариант ЛОЖЕН на honest). Раньше всё это уходило в `notes` и рендерилось зелёным — для standing-гейта недопустимо.
2. **Precondition «base доказан на honest».** M-проба теперь требует, чтобы инвариант держался на честном callee; иначе «невакуумный» инвариант может быть просто **неверным** (`FLAG`: invalid, не vacuous — мутировать ложный инвариант бессмысленно).
3. **Acceptance-check с non-zero exit.** `vacuity_demo.py` делает 8 проверок и возвращает `1` при регрессии — фикстура, переставшая FLAG'аться, **валит прогон**, а не молча переписывает артефакт.
4. **Свидетельства в отчёте.** `discharge_ev` хранит witness/reason per-engine; артефакт несёт BMC-spurious улику (`ghostSum=1,totalSupply=0`, пустой трейс) как машинное доказательство per-family-движка, не прозу.

## Честные оговорки

- **Каталог мутаций — конечный, синтаксический, для АТОМАРНЫХ реляционных инвариантов** (`a OP b`, `a OP b+c`). Конъюнкции реальных протоколов требуют богаче каталог — следующая итерация (связано с T4).
- **Семья = ручной маппинг harness'ов** (как весь курируемый harness-слой, T3). Авто-построение семьи из callee-side формы — вне scope.
- **`trusted`-режимная path-deletion вакуумность** (Finding 0004) ловится **косвенно** — через blind-spots Probe M, не через Probe R: `run_solver` гоняет в `untrusted`-модели (`--model-checker-ext-calls` не передаётся). Прямой probe на `trusted`-режим — именованный следующий шаг.
- **`undecided` ≠ `inert`.** Ослабление, делающее клоз неразрешимым в бюджете, помечено `load_bearing?`/`lost→undecided`, не путается с доказуемой инертностью.
- **Greedy по компонентам** — локальная классификация, не глобально-минимальный нагруженный набор при коррелированных компонентах (как greedy-ablation в mining).
- **Найденная BMC-spuriousness на state-инварианте** — поведение solc 0.8.35; стоит сообщить upstream вместе с `trusted`-vacuous-proof из 0004.

## Долгосрок (объявлено)

1. **Каталог мутаций на конъюнкции** (per-conjunct drop + per-atom ослабление) — гейт на реальных протокольных инвариантах (T4).
2. **Авто-построение семьи** из добытого weakest-интерфейса (Finding 0004) — honest/adversarial callee-варианты генерируются, не маппятся вручную (T3).
3. **Probe R в `trusted`-модели** — прямой захват path-deletion вакуумности (а не только косвенно через blind-spots).
4. **Вакуум-гейт как standing-гейт в orchestrator** — ни один `proved` не репортится без прохождения R + M (на этой итерации намеренно standalone-модуль).
5. **Spurious-counterexample как first-class бакет** — наряду с вакуумным proof, дуальная несоундность «опровержение из недостижимого состояния» детектируется системно (движок ⟂ кванторной форме автоматически).

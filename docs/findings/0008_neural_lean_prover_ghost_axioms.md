# Finding 0008 — Нейро-провер как untrusted-генератор за ядром Lean: ноль добавленного доверия, и пять НОВЫХ разрядок на нашем домене

- **Дата:** 2026-06-29 · **Тип:** эмпирический замер (capability build, e2e, kernel-judged) · **Опирается на:** Finding 0002 (solver-as-judge), ADR-0003 (untrusted-генератор + trusted-чекер), план tcg CLI §Q3, Task 0006 (neural_lean_seam), Task 0013
- **TL;DR:** Гипотеза §Q3: нейро-провер = **untrusted-генератор**, а ядро Lean (уже в нашей trusted base) = судья ⇒ использование любого провер'а добавляет **НОЛЬ доверия** (кривой терм отвергается ядром). Проверили **end-to-end на НАШЕМ домене** (definition-heavy DeFi fixed-point, не олимпиадная математика), судья — `lake build` против пиннутого тулчейна. **Результат: 8/8 теорем приняты ядром, все sorry-free** (`#print axioms` = только `propext/Classical.choice/Quot.sound`). Из них **5 — ГЕНУИННО НОВЫЕ разрядки** из `not_yet_discharged` (mulDiv tightness, rayMul/rayDiv границы) — теоремы, у которых **не было** готового доказательства для копирования; они **сужают trusted base**. Trust-модель подтверждена конкретно: ложную теорему (rayMul-граница без гипотезы) ядро **отвергло** (`unsolved goals`, build fail); подсаженный `sorry` audit **поймал** (`sorryAx`). **Честная граница:** провер здесь — **Claude** (доступный сильный LM), НЕ специализированные Pythagoras-32B/Goedel-V2/DeepSeek-V2 — их веса (8–32B) в этой среде **не запускаются** (нет GPU/ollama/torch, 17 ГБ RAM). Значит это **нижняя граница способности** («наш домен нейро-разрешим, ядро-судимо») + валидация trust-модели, **НЕ** бенчмарк pass@k специализированных провер'ов (это отложенный замер с инфрой).

---

## Сетап (воспроизводимый)

| | |
|---|---|
| Гипотеза | нейро-провер = untrusted-генератор (роль I/G в TCG); ядро Lean = судья ⇒ **ноль добавленного доверия** |
| Вопрос | способность **на НАШЕМ домене** (mulDiv/rayMul/rayDiv + Σ-over-Finset), не miniF2F |
| **Судья** | **ядро Lean 4.31.0 + Mathlib v4.31.0** через `lake build`; теорема засчитана ⟺ ядро приняло. **LLM-судья исключён.** |
| Провер (генератор) | **Claude (Opus 4.x)** — доступный сильный LM. Специализированные провер'ы **не запускаемы** в среде (см. § Честная граница) |
| Аудит вакуумности | `#print axioms` на каждой теореме — обязан быть `⊆ {propext, Classical.choice, Quot.sound}`, **без `sorryAx`** (build-pass ≠ доказательство) |
| Trust-демо | (a) ложная теорема с реальным (не-sorry) доказательством → ядро **отвергает** (build fail); (b) `sorry`-терм → build проходит, но audit ловит `sorryAx` |
| Анкеры (Tier B, уже разряжены в `Basic.lean`) | L1 `mulDiv_le_left` (easy) · L2 `ar_delta` (trivial) · L3 `transfer_sum_preserved` (hard, Σ-over-Finset, двойной `Function.update`) |
| Открытый фронтир (Tier C, `axiom_registry.json::not_yet_discharged`) | mulDiv tightness · rayMul границы · rayDiv границы |
| Тулчейн | Lean 4.31.0 + Mathlib v4.31.0 (пины проекта), solc/z3 не задействованы |

Артефакты: `cycle/trusted/proofs/aave_arith/AaveArith/NeuralProbe.lean` (8 теорем) + `NeuralProbeCheck.lean` (axiom-аудит). Воспроизведение: `lake build AaveArith.NeuralProbe && lake build AaveArith.NeuralProbeCheck`.

---

## Trust-модель — подтверждена конкретно (DoD#1)

| Демонстрация | Что подано ядру | Вердикт ядра/аудита |
|---|---|---|
| **Кривой терм отвергается** | `rayMul_lower` **без** гипотезы `RAY ≤ index` (ложно: index=0 ⇒ rayMul=0 ⇏ x≤0), тот же skeleton | `lake build` → **error: unsolved goals**, rc≠0 — **REJECTED** |
| **`sorry` ловится аудитом** | `sorry_demo : x ≤ mulDiv x y d := by sorry` | build проходит (warning), но `#print axioms` → **`[sorryAx]`** — поймано |
| **Честный терм принимается** | 8 теорем ниже | build rc=0, `#print axioms` ⊆ `{propext, Classical.choice, Quot.sound}` |

**Вывод:** модель **не может** протащить ложную теорему мимо ядра. Это и есть «ноль добавленного доверия»: ценность генератора (любого — Claude, Goedel, Pythagoras) ограничена тем, что **примет ядро**. Паттерн TCG, применённый рекурсивно к разрядке ghost-аксиом.

---

## Замер: 8/8 приняты ядром, все sorry-free

### Tier B — воспроизведение анкеров (по тирам сложности)

| Лемма | Тир | Вердикт ядра | `#print axioms` |
|---|---|---|---|
| `mulDiv_le_left'` (`y≤d → mulDiv x y d ≤ x`) | L1 easy | ✅ proven | `propext, Quot.sound` |
| `ar_delta'` (`(A+d)·r = A·r + d·r`, ℤ) | L2 trivial | ✅ proven (`by ring`) | `propext` |
| `transfer_sum_preserved'` (Σ-over-Finset, двойной `update`) | **L3 hard** | ✅ proven | `propext, Classical.choice, Quot.sound` |

### Tier C — НОВЫЕ разрядки открытого фронтира (`not_yet_discharged`)

| Лемма (новая) | Утверждение | Вердикт |
|---|---|---|
| `mulDiv_tightness` | `0<d → x·y < (mulDiv x y d + 1)·d` | ✅ **NEW** |
| `rayMul_lower` | `RAY≤index → x ≤ rayMul x index` | ✅ **NEW** |
| `rayMul_upper` | `index≤2·RAY → rayMul x index ≤ 2·x` | ✅ **NEW** |
| `rayDiv_upper` | `RAY≤index → rayDiv x index ≤ x` | ✅ **NEW** |
| `rayDiv_lower` | `0<index → index≤2·RAY → x/2 ≤ rayDiv x index` | ✅ **NEW** |

Все пять — над определениями `rayMul x i := x·i/RAY`, `rayDiv x i := x·RAY/i`, `RAY := 10^27` (нужно лишь `RAY>0`). `mulDiv_tightness` + уже-разряженная `mulDiv_mul_le` дают **точный** двусторонний bracket: `mulDiv·d ≤ x·y < (mulDiv+1)·d`. Это ровно те AAVE-границы, что Certora-спеки **постулируют** — теперь они теоремы.

---

## Что это значит для функционала (усиление ADR)

- **Паттерн GO.** Нейро-Lean-провер как untrusted-синтезатор за ядром Lean — soundness-безопасен **по построению**. Каждый успех переводит лист `assumed → lean_theorem(proven)` — **сужает** trusted base, не расширяет. Прямо служит мандату «максимальная точность без неявных допущений».
- **Наш домен — нейро-разрешим (нижняя граница).** Сильный LM + kernel-checking разряжает definition-heavy DeFi-арифметику, включая Σ-over-Finset, на нашем lake-проекте с пиннутым Mathlib — **с первой попытки**, без self-correction-петли.
- **5 новых машинно-проверенных лемм** готовы к промоушену из `NeuralProbe.lean` в `Basic.lean` + апдейту `axiom_registry.json` (переезд из `not_yet_discharged` в `discharged`). Это отдельный, осознанный trusted-base-коммит (не делаю молча из experiment-файла).

---

## Честные границы (negative/unmeasured — first-class)

1. **Провер = Claude, НЕ специализированные.** Pythagoras-32B / Goedel-V2-8B/32B / DeepSeek-Prover-V2-7B / Kimina **не запущены**: среда без GPU/ollama/llama.cpp/torch, 17 ГБ RAM. Их **pass@k на наших леммах не измерен** — это и есть исходный вопрос Task 0013, и он остаётся открытым до инфры (хостинг/GPU). Здесь — валидация **trust-модели** + **нижняя граница** «домен разрешим», не бенчмарк провер'ов.
2. **Tier B — не слепой.** Доказательства L1/L2/L3 были **видимы** генератору (`Basic.lean` прочитан); воспроизведение — слабое свидетельство. **Load-bearing — Tier C** (5 лемм, у которых готового доказательства НЕ было) + trust-демо.
3. **Глубина домена.** Разряженные леммы — арифметика/алгебра floor-деления и Σ-конс; «forall arithmetic lemmas» (`(s_bal - ass/index)·index == s_bal·index - ass`) из `not_yet_discharged` **не атакованы**. Не утверждаем покрытие всего фронтира.
4. **ℕ-модель.** Как и `Basic.lean`, теоремы над ℕ (floor-деление), не над 256-битным словом; non-overflow side-condition (`x·y < 2^256`) перенос — отдельный шаг (тот же caveat, что в `axiom_registry.json::trusted_base_caveat`).
5. **Версионная совместимость — OK.** Вывод собрался против именно наших пинов (Lean 4.31.0 / Mathlib v4.31.0); рассинхрона тактик не было.

---

## Воспроизведение

```
cd cycle/trusted/proofs/aave_arith
lake build AaveArith.NeuralProbe        # 8 теорем — rc 0 ⟺ ядро приняло
lake build AaveArith.NeuralProbeCheck   # #print axioms: ⊆ {propext,Classical.choice,Quot.sound}; sorry_demo → sorryAx
```

Любая аксиома помечена `proven` **только** если ядро принимает её терм; `#print axioms` без `sorryAx` отделяет доказательство от заглушки.

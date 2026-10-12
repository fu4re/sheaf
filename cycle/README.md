# `cycle/` — нейросимволический цикл формальной верификации (ADR-0001)

Реализация исследовательского цикла «агент генерирует — символьное ядро доказывает»
на одном методе `deposit` (ERC-4626). См. [ADR-0001](../docs/adr/0001_neurosymbolic_erc4626_deposit.md)
и [бэклог 0001](../docs/backlog/0001_e2e_cycle.md).

**Статус:** ✅ T-01 (SMT-бэкенд) · ✅ T-02 (пин solc) ·
✅ Slice 1 (разделение ответственности на живом агенте) ·
✅ Slice 2 / T-04 (ghost-абстракция нелинейного `mulDiv` — стена снята,
[`wall_map.md`](measurement/wall_map.md)) ·
✅ T-05 + Tier-2 spec-gen realism (агент vs Certora на реальном Aave: **64% покрытия**,
[`aave_realism.md`](measurement/aave_realism.md)).
Далее: расширение DSL инварианта (ghost-сумма + 2-state) / тугие нелинейные аксиомы (T-14).

---

## Окружение (зафиксировано для воспроизводимости research-замера)

| Компонент | Версия | Источник |
|---|---|---|
| macOS | 14.6 (23G80), **arm64** | — |
| `solc` | **0.8.35**+commit.47b9dedd.Darwin.appleclang, нативный arm64 | `brew install solidity` |
| SMT-солвер | **z3 4.16.0** | `brew install z3` (runtime-dep `solidity`) |
| `forge` | 1.2.3-stable | foundry |
| `python3` | 3.12.2 | pyenv |

Канонический бинарь ядра: `/opt/homebrew/bin/solc` (на него же указывает `foundry.toml`).

---

## T-01 — SMT-бэкенд реально работает на этой машине ✅

**Снятая неизвестность (риск №1):** «бандлится ли z3 в solc-сборке под macOS?»

**Ответ — эмпирический:**
- Официальные статические сборки `solc-bin` для macOS — **только x86_64** (`macosx-amd64`).
  На arm64 они шли бы через Rosetta, и их SMTChecker не подгрузил бы нативный arm64-`libz3`
  (архитектурный конфликт). Этот путь отвергнут.
- Формула brew `solidity` объявляет `z3` **runtime-зависимостью** и ставит **нативный arm64**
  `solc`, динамически слинкованный с brew-`z3`. SMTChecker работает из коробки.

**Проверены оба движка** (солвер z3):

| Движок | Назначение | Smoke-результат |
|---|---|---|
| **CHC** | неограниченное доказательство (Constrained Horn Clauses) | ✅ |
| **BMC** | bounded model checking (k-bound) | ✅ |

### Два эталонных примера

Тема намеренно созвучна `deposit` — округление целочисленного деления (assets→shares).

**1. `proved`** — [trusted/smt_smoke/ProvablePass.sol](trusted/smt_smoke/ProvablePass.sol):
```bash
solc --model-checker-engine chc --model-checker-targets assert \
     --model-checker-solvers z3 cycle/trusted/smt_smoke/ProvablePass.sol
# => Info: CHC: 1 verification condition(s) proved safe!
```

**2. `counterexample + witness`** — [trusted/smt_smoke/ProvableFail.sol](trusted/smt_smoke/ProvableFail.sol):
```bash
solc --model-checker-engine chc --model-checker-targets assert \
     --model-checker-solvers z3 cycle/trusted/smt_smoke/ProvableFail.sol
# => Warning: CHC: Assertion violation happens here.
#    Counterexample:  a = 1
#    Transaction trace: ProvableFail.roundTripDivByTwo(1)
```

Оба вердикта получены ⇒ труба ядра [5] и доказывает истинное, и опровергает ложное
конкретным контрпримером. **Риск №1 снят.**

---

## T-02 — пин версии solc ✅

**Решение: `solc 0.8.35`** (нативная arm64), одна версия для Tier-1 и Tier-2.

**Обоснование (почему не 0.8.10, «как у Aave»):** мы завязаны на Aave только как на
**источник ground-truth и эталонную стену** (доказанные CVL-спеки + арифметика `rayMul`/`rayDiv`),
а НЕ как на тулчейн. Сравнение идёт на уровне **спека ↔ CVL** (T-15), не solc↔solc, поэтому
bytecode-точность к Aave не нужна. `ATokenVault` (pragma `^0.8.10`) компилируется под 0.8.35
*(подтвердить в T-05)*. При этом 0.8.35 — сильнейшая версия SMTChecker и единственная нативная
на этой arm64-машине; 0.8.10 потребовал бы хрупкой связки x86_64-solc/Rosetta + x86_64-z3 и дал бы
заведомо более слабое ядро. Если даже сильнейшая версия упрётся в стену ghost-арифметики — это
*robust* научный результат, а не артефакт устаревшего тулчейна.

---

## Пайплайн — Slice 1 (разделение ответственности замкнуто) ✅

Исполняемая форма гипотезы **«агент предполагает — солвер доказывает»**, разрез по
линии доверия (ADR §2.4). Каждый модуль изолирован и отключаем.

```
[1] UNTRUSTED        →  [4] GATEWAY         →  [5] TRUSTED        →  [6] MEASUREMENT
economic_spec_gen       translator             solver (SMTChecker)   comparator
(claude -p: 1-стр.      инвариант → harness    proved /              ground-truth
 эконом-инвариант)      + compile-check        counterexample(+wit)  дельта
                              ↑
                   trusted/harness (PRE-FIXED: overflow-обвязка;
                   ghost-арифметика mulDiv — Slice 2 / T-04)
```

**Эмпирический результат (живой агент, model=sonnet):**

| Контракт | Агент предложил | Вердикт ядра | Witness | GT-дельта |
|---|---|---|---|---|
| `MiniVault` (good) | `totalShares == totalAssets` | **`proved`** | — | `exact` |
| `MiniVaultBuggy` (bad) | `totalShares == totalAssets` | **`counterexample`** | `deposit(0) → shares=1, assets=0` | `exact` |

Ключевое: на сломанном контракте агент предложил *правильный* (намеренный) инвариант,
а солвер опроверг его контрпримером — операционализация «намерение vs реализация =
детектор бага» (Johansson №2). Разделение ответственности подтверждено: недоверенный
выход проходит через детерминированный шлюз, истину выдаёт только ядро.

> Линейная арифметика (1:1) выбрана намеренно, чтобы изолировать механику разделения
> от стены нелинейного `mulDiv`. Эту стену вводит Slice 2 (см. `trusted/harness/ghost.md`).

## Пайплайн — Slice 2 (ghost-абстракция нелинейного `mulDiv`, T-04) ✅

`ProportionalVault.deposit` считает `shares = floor(assets * totalShares / totalAssets)` —
произведение двух storage-переменных, **нелинейная стена**. Инвариант агента один и тот
же (`totalShares <= totalAssets`, солвентность), меняется только harness:

| Режим harness | Обработка `mulDiv` | Вердикт ядра |
|---|---|---|
| `subclass` (concrete) | реальная нелинейная арифметика | **`inconclusive`** — стена |
| `ghost` (frozen axiom) | havoc'нутая доля + `require(mintedShares <= assets)` | **`proved`** |

**T-04 снят:** ghost-абстракция выразима в SMTChecker **без CVL-hooks** — havoc =
недетерминированный вход функции, аксиома = `require` (assume). Один инвариант, два
вердикта ⇒ стена в **proof harness (арифметике), не в инварианте** (гипотеза ADR §5.2).
Полный экспонат + честные оговорки (линейная над-аппроксимация; соундность аксиомы —
оффлайн; риск курирования) — в [`measurement/wall_map.md`](measurement/wall_map.md).

```bash
# тот же инвариант, две стены:
python3 orchestrator.py --contract contracts/ProportionalVault.sol --name ProportionalVault \
        --spec-file measurement/artifacts/ProportionalVault__spec.seed.json            # inconclusive
python3 orchestrator.py --contract contracts/ProportionalVault.sol --name ProportionalVault \
        --harness trusted/harness/ProportionalVaultGhost.sol \
        --spec-file measurement/artifacts/ProportionalVault__spec.seed.json            # proved
```

## Tier-2 — реализм spec-генерации (агент vs Certora на реальном Aave) ✅

Модуль [1] читает настоящий `ATokenVault.sol` и перечисляет набор экономических
инвариантов; модуль [6] (LLM-судья) считает покрытие против 7 **доказанных**
Certora-свойств. Результат: **recovered 4 · partial 1 · missed 2 ≈ 64%** + 4 «лишних».

Главное (полный разбор — [`measurement/aave_realism.md`](measurement/aave_realism.md)):
- **Stateless экономика** (солвентность, fee-backing, accounting-bounds) генерится ~на
  уровне эксперта — иногда дословно; один extra (`accounting_identity`) **сильнее** Certora.
- **Промахи структурные, не случайные:** `sumAllBalance==totalSupply` (нужна ghost-сумма
  по mapping — стена T-04) и `fees_monotonic`/`accrual` (2-state, нужен `old()`). Это пробел
  **выразительности DSL**, не интеллекта.
- Агент сам потянулся к нелинейному `shares_backed_proportionally` — стена Slice 2. Стены
  по циклу одни и те же.

```bash
python3 measurement/aave_spec_gen.py            # live: агент + судья
python3 measurement/aave_spec_gen.py --replay   # из кэша
```

## Структура каталога

```
cycle/
├── README.md                 # живой журнал окружения и решений
├── foundry.toml              # пин solc + дефолты SMTChecker
├── orchestrator.py           # вайринг [1]→[4]→[5]→[6], эмиссия артефакта
├── contracts/                # SUT (mocked, known-answer)
│   ├── MiniVault.sol         #   Slice 1 known-GOOD: конверсия 1:1 доказуема
│   ├── MiniVaultBuggy.sol    #   Slice 1 known-BAD: печатает долю из воздуха
│   └── ProportionalVault.sol #   Slice 2: реальный нелинейный mulDiv (стена)
├── untrusted/                # МИР «ПРЕДПОЛАГАЕТ» (LLM)
│   └── economic_spec_generator/  # модуль [1]: spec_runner.py (claude -p)
│       ├── prompt.md         #     single-invariant mode (Slice 1/2)
│       └── prompt_set.md     #     SET mode (Tier-2 realism)
├── gateway/                  # ШЛЮЗ (детерминированный)
│   └── translator.py         #   модуль [4]: subclass-mode + ghost harness-mode + compile-check
├── trusted/                  # МИР «ДОКАЗЫВАЕТ»
│   ├── solver.py             #   модуль [5]: SMTChecker-раннер + парсер вердиктов (T-06)
│   ├── harness/              #   frozen ghost-библиотека (TRUSTED)
│   │   ├── ghost.md          #     механизм + аксиомы (T-04 снят)
│   │   ├── ProportionalVaultGhost.sol       # havoc + frozen axiom → proved
│   │   └── ProportionalVaultGhostBuggy.sol  # слабая аксиома → counterexample
│   └── smt_smoke/            #   T-01: канонические proved / counterexample примеры
├── ground_truth/             # ВЕНДОРЕННЫЙ эталон (T-05)
│   └── aave_vault/           #   ATokenVault.sol + certora_specs/*.spec + PROVENANCE.md
└── measurement/              # ВНЕ ПЕТЛИ
    ├── comparator.py         #   модуль [6]: дельта инвариант ↔ ground-truth (Slice 1/2)
    ├── aave_spec_gen.py      #   Tier-2: генерация набора + LLM-судья покрытия
    ├── wall_map.md           #   карта стен SMTChecker — экспонат #1 (T-04)
    ├── aave_realism.md       #   реализм spec-генерации vs Certora (64%)
    ├── ground_truth/         #   дистиллированные эталонные инварианты (canonical + aave)
    └── artifacts/            #   spec/verdict/coverage JSON + harness'ы
```

### Как запустить пайплайн

```bash
cd cycle
# живой агент предлагает инвариант:
python3 orchestrator.py --contract contracts/MiniVault.sol      --name MiniVault
python3 orchestrator.py --contract contracts/MiniVaultBuggy.sol --name MiniVaultBuggy
# детерминированный реплей (без вызова модели):
python3 orchestrator.py --contract contracts/MiniVault.sol --name MiniVault \
        --spec-file measurement/artifacts/MiniVault__spec.seed.json
```

---

## Как воспроизвести с нуля

```bash
brew install solidity z3        # нативный arm64 solc 0.8.35 + z3 4.16.0
solc --version                  # ожидаем 0.8.35+...Darwin.appleclang
# smoke-тесты T-01:
solc --model-checker-engine chc --model-checker-targets assert \
     --model-checker-solvers z3 cycle/trusted/smt_smoke/ProvablePass.sol  # proved
solc --model-checker-engine chc --model-checker-targets assert \
     --model-checker-solvers z3 cycle/trusted/smt_smoke/ProvableFail.sol  # counterexample a=1
```

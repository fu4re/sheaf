# План: `tcg` CLI — trusted gate вокруг вайб-кодинга (продуктизация ADR-0003)

## Context — зачем

ADR-0003 ([docs/adr/0003_tcg.md](docs/adr/0003_tcg.md)) + whitepaper зафиксировали **Trusted Code Generation**: e2e-процесс, где LLM свободно «вайб-кодит», но наружу выходит только то, что прошло формальную проверку. ADR намеренно tool-agnostic (роли F/G/I/K/H + границы доверия), а §4.3 явно откладывает привязку конкретных инструментов в «separate ADRs». Задача — спроектировать **реализацию этого процесса как CLI-тулы** поверх уже валидированного `cycle/`.

Текущее состояние: `cycle/` реализует F→gateway→K→measurement на **данном** контракте ([cycle/orchestrator.py](cycle/orchestrator.py)), плюс T1 vacuity-gate ([cycle/measurement/vacuity.py](cycle/measurement/vacuity.py)) и T2 assurance-package ([cycle/assurance/](cycle/assurance/)). Чего нет: явного шага **H** (человек-оракул + заморозка φ), полного кортежа **φ=(Pre,Trace,Post,Exit)** (сейчас один `solidity_expr`), и продуктовой acceptance-семантики (orchestrator заканчивается `compare()` против ground-truth — это измерение, а не гейт).

Желаемый исход: тула `tcg`, которая на контракт, вайб-коженный снаружи, выдаёт безопасный исход с предъявляемым assurance-package — и **никогда** не печатает green `Verified(b,φ)` вне ПОЛНОЙ конформности (`K=Accept ∧ vacuity=PASS ∧ φ_context=∅ ∧ bytecode-identity discharged ∧ assumed⊆IRREDUCIBLE`); иначе честный `⊥_spec` / `⊥_gen` / `⊥_assumptions_open` (см. round-2 ниже).

## Решённый скоуп (ответы пользователя)

1. **Trusted gate, G снаружи.** MVP = `F→H→K→vacuity→package` вокруг контракта, который вайб-кодится в редакторе/Claude Code. G — задокументированный untrusted-seam (человек или агент); автономного `tcg run`-лупа в MVP нет (будущий seam). Совпадает с валидированным субстратом и с moat'ом ([Finding 0006](docs/findings/0006_naive_loop_ceiling.md): ценность в чекере/harness, не в генераторе).
2. **ADR-0004 + CLI + backlog-0006.** Новый ADR привязывает инструменты к ролям; CLI оборачивает `cycle/`; backlog рамкует следующие инкременты.
3. **Verify-level — НЕ умозрительно.** Первая задача пайплайна = эмпирическая проверка сетапа (Task 1 spike); решение «source-level vs глубже» принимается на доказательствах. Нейро-провер'ы изучены ниже (§ Q3) — для разрядки ghost-аксиом в Lean *без добавления доверия*.

### Soundness-фикс (round 2) — два пойманных false-green

Ревью поймало два дефекта класса «запись допущения ≠ его разрядка» (ровно [Finding 0007:55](docs/findings/0007_assurance_package_format.md)):
- **Obj 1:** `Verified(b,φ)` допускался при `H_bytecode=unverified` — нарушение Инв.7 (ADR:158,197).
- **Obj 2:** φ объявлена full-tuple, но acceptance проверял подмножество (Trace/Exit `deferred`) — молчаливая terminal-only деградация (ADR §2.2 называет это дефектом).

**Принятое решение (Strict):** assumed-листы разделены на **IRREDUCIBLE** (ADR Assumptions 1/3/7 — семантика, soundness чекера, human-intent; легитимно под green) и **DISCHARGEABLE** (Инв.7 bytecode-identity, покрытие Trace/Exit, annotation-discharge — обязаны быть закрыты). green `Verified(b,φ)` ⟺ полная конформность (`φ_context=∅ ∧ bytecode-identity discharged ∧ assumed⊆IRREDUCIBLE`); иначе honest **`⊥_assumptions_open`** (не green, evidence-package эмитится, claim только про `φ_checked`). φ разделена `φ_checked` vs `φ_context`. Детали — §§ Acceptance, ledger, verify-level ниже.

---

## Архитектура

### Module layout — новый пакет `tcg/`, argparse, без новых рантайм-зависимостей

Весь репозиторий — argparse + py3.12, единственная сторонняя зависимость PyYAML; `orchestrator.py`/`assemble.py`/`verify_package.py` уже задают конвенцию «три статуса + ненулевой exit». Click/typer добавили бы зависимость против духа ADR-0002 («перепроверяемо третьей стороной минимальным тулингом»). **argparse с субпарсерами.** `tcg/` импортирует `cycle/` как библиотеку (как это делает `vacuity.py`); `cycle/` остаётся субстратом, `tcg/` — продуктовая поверхность.

```
tcg/
  __main__.py            # python -m tcg ...
  cli.py                 # argparse root + dispatch
  outcome.py             # исходы как закрытый тип: Verified(b,φ) [full green] | BotSpec | BotGen | BotAssumptionsOpen;
                         #   + classify(verdict)→KResult + two-tier acceptance. Единственное место, решающее «green».
                         #   Accept ≠ green: green требует ПОЛНОЙ ADR-конформности (§ Acceptance ниже).
  phi.py                 # φ-артефакт: Spec{pre,trace,post,exit}, YAML load/dump, content-hash, freeze-блок
  commands/
    formalize.py         # F  → spec_runner.generate_spec → лифт в кортеж φ
    validate.py          # H  → review + FREEZE (хеш + approval). Инв.6 и Инв.9 здесь.
    check.py             # K  → gateway.validate_compiles → solver.run_solver на ДАННОМ контракте
    vacuity.py           # gate-обёртка (Probe R всегда; Probe M при --family)
    package.py           # assurance: emit → spine → assemble → lint. T2-артефакт.
    setup_check.py       # TASK 1 spike: эмпирически гоняет solc/z3/SMTChecker/lake; печатает walls
    run.py, status.py    # секвенсор e2e-гейта + read-only статус
```

**Workspace:** каждый запуск — run-директория `runs/<contract>-<UTCstamp>/` (под `cycle/measurement/artifacts/tcg_runs/`, зеркалит `naive_loop/runs/`): `intent.txt`, `contract.sol`, `phi.draft.yaml`, `phi.frozen.yaml`, `check.json`, `vacuity.json`, `records/*.record.yaml`, `spine.yaml`, `package/`, `outcome.json`. Резюмируемо и аудируемо.

### Command surface

Конвенция: каждый гейт печатает трёхстатусный вердикт и **выходит ненулевым, если не зелёный**. Единая таблица exit-кодов в `outcome.py` — **код 2 (Unknown/BLOCKED/abstain) и код 3 (Refute/FLAG/INVALID) разделены**, чтобы «не смог проверить» и «нашёл дефект» никогда не делили код (Инв. 4 и 5):

```
0 green = Verified(b,φ) (ПОЛНАЯ конформность) · 2 Unknown/BLOCKED/abstain
3 Refute/FLAG/INVALID (реальный дефект) · 4 ⊥_spec · 5 ⊥_gen
6 ⊥_assumptions_open (Accept+PASS, но dischargeable-конформность открыта — НЕ green) · 1 usage/internal
```

| Субкоманда | Зовёт (существующее) | In→Out |
|---|---|---|
| `tcg formalize --contract --name --method [--model] [--spec-file]` | `spec_runner.generate_spec` (replay через `--spec-file`, идиома orchestrator:81-90) | intent+contract → `phi.draft.yaml`; F абстейнит → `⊥_spec` |
| `tcg validate [--approve\|--reject] [--reviewer]` | net-new (H-шага нет нигде) | `phi.draft` → `phi.frozen` с freeze-блоком; без флага рендерит φ и выходит 2 (ничего не заморожено) |
| `tcg check [--engine] [--harness] [--targets] [--timeout-ms]` | `gateway.build_*`, `validate_compiles`, `solver.run_solver` | frozen-φ+contract → `check.json` (Accept\|Refute\|Unknown); отказ если φ не заморожена/хеш не сходится |
| `tcg vacuity [--family] [--engines]` | `vacuity.reachability_probe` (всегда), `vacuity_gate` (при `--family`) | `check.json` → `vacuity.json` (PASS/FLAG/BLOCKED) |
| `tcg package --src-root [--lean-axioms] [--faithfulness-evidence]` | `assurance.emit_*`, `assemble`, `verify_package.lint` | зелёный run → `records/*`→`spine.yaml`→`package/`→lint |
| `tcg run` / `tcg status` | секвенсор / read-only | e2e-гейт, стоп на первом не-зелёном с нужным `⊥`; статус гейтов |
| `tcg setup-check [--json] [--probe-neural-lean]` | Task 1 spike (§ниже) | матрица P0–P8, выход ненулевым если verdict WRONG |

### φ-артефакт — `phi.py`, YAML (консистентно с assurance-слоем)

ADR §2.2: `φ=(Pre,Trace,Post,Exit)`, и «молчаливая деградация до terminal-only — дефект». Сейчас F даёт только `invariant.solidity_expr` (Post-like). **Все четыре измерения представляются явно**, даже где MVP механически проверяет подмножество; что проверено vs отложено — записывается, не выкидывается молча:

```yaml
schema: tcg/phi/v1
contract: MiniVault   method: deposit   intent_ref: intent.txt
spec:
  pre:   [{id: pre_caps, solidity_expr: "...", checked_as: assume}]      # → require() (precondition)
  trace: [{id: trace_nonreentrant, kind: reentrancy_frame,
           checked_as: ext_calls_untrusted, status: declared}]          # MVP: --model-checker-ext-calls untrusted (havoc-wall)
  post:  [{id: post_conservation, solidity_expr: "totalShares==totalAssets",
           shape: stateless, checked_as: assert}]                       # → --model-checker-targets assert (эконом. инвариант)
  exit:  {admissible: [halt, revert],
          forbidden_conditions: [{condition: overflow, target: overflow}, ...]}  # → SMTChecker safety targets
coverage: {checked_dimensions: [pre, post, exit-safety-subset],
           deferred_dimensions: [trace-deep, exit-outofgas],            # ЧЕСТНЫЙ self-report (ADR §4.2 «молчание = слепое пятно»)
           note: "Trace представлен, но механически проверяется только non-reentrant подмножество"}
```

**φ_checked vs φ_context (round-2):** `φ_checked` = `checked_dimensions` (K разрядил механически); `φ_context` = `deferred_dimensions` (declared, НЕ проверены). Любое verified-утверждение — **только про `φ_checked`**; непустой `φ_context` ⇒ `⊥_assumptions_open` (не green): нельзя говорить «artifact satisfies φ», когда Trace/Exit лишь записаны в ledger.

- **F (`formalize.py`)**: `generate_spec` → лифт единственного инварианта в `spec.post[0]`; `pre` из pre-fixed overflow-guards SUT (детектит gateway, не модель); `trace`/`exit` — явные дефолты со `status: declared/deferred`. Полнокортежный промпт — liveness-фоллоуап (backlog-0006), **никогда не гейтит soundness**.
- **H-заморозка (`validate.py`, Инв.6+9)**: канонизировать `spec:`, `sha256`→`content_hash`; `--approve` пишет `freeze:{content_hash, approved_by, approved_at, intent_attestation, checker_params:{solc_version, evm_version, ext_calls, targets}}`. `check`/`package` пересчитывают хеш над `spec:` и **отказывают при расхождении** — механически запрещает любому downstream (или будущему G-лупу) ослабить спеку, против которой проверяют.

### Verdict→outcome и acceptance-предикат (`outcome.py`)

| `Verdict.verdict` (solver.py) | ADR §2.4 | Обработка |
|---|---|---|
| `proved` | **Accept(cert)** | кандидат на accept; cert = harness+команда+`raw` |
| `counterexample` | **Refute(ce)** | несёт `witness`; единственный, кто кормил бы луп → MVP завершает `⊥_gen`, выносит witness человеку |
| `inconclusive` | **Unknown(reason)** | не-acceptance, **без** ce; НЕ реплеить как refutation (Инв.5) |
| `compile_error` | **gateway reject** | граница отказала; non-acceptance с отдельным reason |

**Acceptance — строгий two-tier (round-2 фикс, выбор Strict).** Запись допущения в ledger ≠ право звать `Verified`. assumed-листы разделены: **IRREDUCIBLE** = ADR Assumptions 1/3/7 (машинная семантика, soundness чекера, human-intent) — легитимно остаются под green; **DISCHARGEABLE** = Инв.7 bytecode-identity, покрытие Trace/Exit, annotation-discharge — **обязаны** быть закрыты для green.

```
Verified(b, φ) [green] ⟺ k_result==Accept ∧ vacuity==PASS            # Инв.1; FLAG/BLOCKED блокируют
                 ∧ φ.is_frozen ∧ φ.hash_matches ∧ φ.checker_params==run.params   # Инв.6, 9
                 ∧ φ_context == ∅                  # §2.2/Obj 2: КАЖДОЕ замороженное измерение φ разряжено механически
                 ∧ bytecode_identity == discharged  # Инв.7/Obj 1: runtime bytecode bit-identical — НЕ `unverified`
                 ∧ ledger.assumed ⊆ IRREDUCIBLE     # ни одного DISCHARGEABLE-пункта под green
                 ∧ lint == WELL-FORMED
Accept ∧ PASS, но НЕ всё выше ⟹ ⊥_assumptions_open  # source-level accept при открытых dischargeable-пунктах:
                 #   НЕ green. Evidence-package ВСЁ РАВНО эмитится (claim только про φ_checked; открытые
                 #   допущения названы в заголовке). НЕ «четвёртый shipped-but-unverified путь» (checklist:200) —
                 #   это reason-код внутри not-verified (⊥), ничего не отгружается как verified.
F абстейнил / H отверг ⟹ ⊥_spec    ·    Refute / Unknown / budget ⟹ ⊥_gen
```

Verified-утверждение — **всегда только про `φ_checked`** (что K разрядил), никогда про `φ_context`. `classify(verdict)→KResult` — единственный перевод; **Accept ≠ green** (Accept лишь необходимое условие). Unknown≠Refute by construction (разные ветки, witness только у Refute, exit 3 vs 2). `lint=="WELL-FORMED"` (его `check_closure` FLAGает лист-сироту) — *необходимое, но не достаточное*: WELL-FORMED пропускает honestly-recorded `unverified`-faithfulness-лист, поэтому green гейтит **two-tier предикат**, а не линтер.

### Где enforce'ятся 9 инвариантов

| # | Инвариант | Где | Механизм |
|---|---|---|---|
| 1 | K — единственный гейт | `outcome.emit_verified` | Accept — единственная truthy-ветка; `compare()` намеренно ВНЕ пути |
| 2 | Модель не доверяется | `check.py` | F-выход всегда subject у `validate_compiles`→`run_solver`, никогда не axiom |
| 3 | Acceptance≠truth | `outcome.py`+`package.py` | `Accept`≠`Verified` как типы; soundness-мост = именованный лист `A_solver` |
| 4 | Unknown=rejection | `classify` | `inconclusive→Unknown→⊥`, exit 2; нет accept-on-doubt |
| 5 | Refute≠Unknown | `classify` + exit 3 vs 2 | только Refute несёт witness и loop-eligible |
| 6 | φ заморожена после H | `validate.py` + хеш-recheck | хеш над `spec:`; downstream отказывает при расхождении |
| 7 | verified==deployed | `outcome.py` two-tier + `package.py` лист | source-identity сам по себе **НЕ даёт green** → `⊥_assumptions_open`; full `Verified` требует discharge bytecode-identity (DISCHARGEABLE). `harness_faithfulness: unverified` виден, но капает верхний статус ниже green |
| 8 | Аннотации checked\|declared | `package.py` + `checked_as` | `assert`(checked) vs `assume`(declared require); ghost-аксиомы → `lean_theorem`/`assumption` листы |
| 9 | Параметры pinned | `validate.freeze.checker_params` + recheck | solc/evm/ext-calls/targets с φ, переподтверждаются на check |

### Assurance/ledger (`package.py`) — переиспользует слой целиком

Шаблон — пилот [cycle/artifact_format/pilot-vaultasset-2026-06-26.src/spine.yaml](cycle/artifact_format/). Поток: `emit_smt`(Post-solve, `engine`-строка несёт pinned-версии = Инв.9) + `emit_lean`(ghost-аксиомы из `axiom_registry.json`) → синтез `spine.yaml` (топ-claim = Post-инвариант, edges = аксиомы + именованные допущения) → `assemble()` → `lint()`. Exit = вердикт линтера (WELL-FORMED→0, INVALID→3, BLOCKED→2).

**Именованные листы — разделены на IRREDUCIBLE (могут остаться под green) и DISCHARGEABLE (открытый ⇒ НЕ green):**

| Лист | kind / status | Класс | Запись |
|---|---|---|---|
| `L_<axiom>` (mulDiv_le_left, transfer_pair_sum_preserved, …) | `lean_theorem` / proven | — (разряжен) | ghost-аксиома **разряжена ядром**, не assumed (Инв.8) |
| `A_solver` | `assumption` / assumed | **irreducible** (Assumption 3) | soundness-мост ADR §2.3; lean-smt заменил бы это |
| `A_machine_semantics` | `assumption` / assumed | **irreducible** (Assumption 1) | «SMTChecker-модель EVM верна реальному EVM/KEVM»; `risk_if_false: семантический зазор» |
| `A_human_intent` (φ≈n) | `assumption` / assumed | **irreducible** (Assumption 7) | заморожено H; единственный неформальный зазор |
| `H_bytecode` (Инв.7) | `harness_faithfulness` / **unverified** | **DISCHARGEABLE** | open ⇒ `⊥_assumptions_open`; green требует `identity_matched`/`diff_fuzz` |
| `φ_context` (deferred trace/exit) | `assumption` / assumed | **DISCHARGEABLE** | open ⇒ `⊥_assumptions_open`; green требует механической разрядки измерения |

**Render-правило (Finding 0007):** верхний статус claim'а = слабейший лист по его пути. Любой `unverified`-faithfulness или открытый DISCHARGEABLE-лист **капает** верх ниже green — никакого голого «✅ proved» над открытым dischargeable-пунктом. Расширить `verify_package` (рендер/линт): помечать top-claim, отрисованный зелёным над DISCHARGEABLE-листом.

Свойство (ADR-0002): package **независимо перепроверяем** — `python -m cycle.assurance.verify_package package/ --replay` воспроизводит каждый `proven`/`refuted`, а каждый `assumed`-лист назван с `risk_if_false`.

---

## Q3 — verify-level + нейро-провер для Lean-разрядки ghost-аксиом (изучено, аргументированный выбор)

### Ключевой инсайт доверия (уверенный вывод)

Все четыре провер'а **эмитят настоящие Lean-4 термы/тактики, которые проверяет ядро Lean** (иначе бенчмарк не засчитывается). Значит провер — **untrusted-генератор** ровно как G/I в TCG; ядро Lean (уже в нашей trusted base) — судья. **Использование любого из них добавляет НОЛЬ доверия.** Это идеальный фит под «максимальную точность без неявных допущений»: кривой proof отвергается ядром. Тот же паттерн TCG, применённый рекурсивно к разрядке ghost-аксиом. Каждый успешный proof переводит лист `assumed → lean_theorem(proven)` — **сужает** trusted base, а не расширяет.

### Кандидаты (open weights, Lean 4, kernel-checkable)

| Провер | Параметры | Релиз | miniF2F-test | Заметки |
|---|---|---|---|---|
| **Pythagoras-Prover** ([arXiv 2606.12594](https://arxiv.org/abs/2606.12594)) | 4B / 32B / Diffusion | июнь 2026 | **89.8% pass@32, 92.6% pass@2024** (лучший на сегодня, БЕЗ self-correction) | новейший; ALF-аугментация; `Pythagoras-LM/*` на HF |
| **Goedel-Prover-V2** ([arXiv 2508.03613](https://arxiv.org/abs/2508.03613)) | 8B / 32B | авг 2025 | 88.1% (90.4% +self-corr); PutnamBench #1 | **self-correct через Lean-компилятор-фидбек** (как наш refute-loop); 8B локально |
| **DeepSeek-Prover-V2** ([arXiv 2504.21801](https://arxiv.org/abs/2504.21801)) | 7B / 671B | апр 2025 | 88.9% | recursive subgoal decomposition; 7B запускаем как baseline |
| **Kimina-Prover** ([arXiv 2504.11354](https://arxiv.org/abs/2504.11354)) | 72B / distill 1.7B,7B | июль 2025 | 84.0% (distill-1.7B: 72.95%) | минимальный footprint; + Kimina-Autoformalizer-7B |

### Аргументированный вывод (честно)

- **Паттерн: GO.** Нейро-Lean-провер = untrusted proof-синтезатор (роль `I` для trusted-base-слоя), ядро Lean = чекер. Ноль доверия. Прямо служит мандату «без неявных допущений».
- **Способность на НАШИХ леммах: ТЕСТ, не предполагать.** Бенчмарки — олимпиадная математика (miniF2F=AIME/AMC/IMO, Putnam); наш домен другой. Наши аксиомы делятся:
  - *Mathlib-shaped easy* (`mulDiv` границы = `Nat.div_mul_le_self`; `ar_delta` = `add_mul`): почти наверняка one-shot — это «найди нужную Mathlib-лемму + пара тактик».
  - *Definition-heavy hard* (`transfer_sum_preserved` над `Finset` с двойным `Function.update`, через `Finset.sum_update_of_mem`+`omega`): ссылается на **наши** defs, не self-contained miniF2F-строку. Прямого бенчмарк-доказательства, что провер'ы это умеют, поиск **не нашёл** → реальная неизвестность.
- **В нашу пользу:** мы **сами пишем** Lean-утверждение аксиомы (оно обязано точно совпадать с SMT-абстракцией), т.е. нам нужна только стадия *доказательства*, не autoformalization. Слабый e2e-autoformalization-пайплайн (~36% в литературе) к нам не применим — мы в более сильном режиме «докажи это конкретное утверждение».
- **Риск интеграции (флажок):** наш проект пиннится Lean 4.31.0 + Mathlib v4.31.0; тактики ломаются между версиями Mathlib. Spike обязан проверить, что вывод провер'а **билдится против НАШЕГО пиннутого тулчейна**, не «какого-то Lean».
- **MVP не блокируется этим.** Ручные Lean-аксиомы уже работают ([Finding 0002](docs/findings/0002_solver_as_judge_makerdao_vat.md)/0007). Нейро-провер — *liveness/cost*-ускорение (автоматизация ручного Lean-труда), **не** soundness-блокер.

**Резолюция verify-level:** K контракта остаётся **source-level SMTChecker** (Post + safety-subset). На source-level **bytecode-identity — DISCHARGEABLE и НЕ разряжен**, поэтому такой run даёт `⊥_assumptions_open`, **не** green `Verified`. Путь к green: discharge bytecode-identity (runtime hash + compiler settings + immutables/constructor/metadata, backlog) — после чего остаются только IRREDUCIBLE-листы `A_solver`/`A_machine_semantics` (полный bytecode-level discharge семантики = KEVM/Halmos, отдельный verify-level). Нейро-провер слоится в **Lean-слой ghost-аксиом**, переводя DISCHARGEABLE ghost-аксиомы `assumed→lean_theorem(proven)` — *сужает* trusted base без добавления доверия. **Финальный коммит — гейтится Task-1 spike'ом** (P1–P8 меряют, что source-level реально даёт; P8 — потолок Trace; neural-Lean-seam — провер на наших аксиомах). Не предполагаем — меряем.

---

## Задачи (фазированно; ✅ reuse · 🟡 wrapper · 🔴 new)

**Task 1 — setup-verification spike (ПЕРВАЯ, блокирующая).** 🔴 `setup_check.py`, `cli.py`-скелет, `outcome.py` exit-таблица. ✅ reuse `run_solver`/`reachability_probe`/фикстуры. Гоняет матрицу и **печатает работает-vs-стена**:

| Probe | Фикстура (существует) | Ожидание | Дерискает |
|---|---|---|---|
| P0 версии | — | совпадение с пинами AGENTS.md | **вскрывает z3 4.12.6(standalone) vs 4.16.0(pin)** — SMTChecker судит *bundled* z3; записать какой реально |
| P1 prove | `trusted/smt_smoke/ProvablePass.sol` | `proved` | CHC доказывает истинное |
| P2 refute+witness | `ProvableFail.sol` | `counterexample`, witness `a=1` | Refute реален, не «не доказано» |
| P3/P4 e2e good/bad | `contracts/MiniVault.sol` / `MiniVaultBuggy.sol` + seed-φ | Accept / **Refute+witness** | гейт принимает корректный, **отвергает багнутый с witness** |
| P5 vacuity FLAG | `VaultAssetAGDead.sol` (`require(false)`), `MiniERC20NoMintConservation.sol` | **FLAG** (assert(false) proved ⇒ unreachable) | **намеренно-вакуумный FLAGается** |
| P6 BMC | `MiniERC20Delta`-семья | CHC inconclusive, BMC refutes | CHC+BMC работают, engine⟂квантор-политика держится |
| P7 Lean build | `cycle/trusted/proofs/aave_arith/` | `lake build` rc=0 | trusted-base реально билдится; `build_status:ok` не ложь |
| P8 ext-calls | one-call cross harness | untrusted=havoc-wall, trusted=может вакуум | **эмпирический потолок source-level Trace** → решение о глубине |

Печатает «verify-level verdict» (если P1–P6 OK → source-level достаточен для MVP-гейта; если P8 показывает havoc-wall на целевых Trace-свойствах → «Trace требует KEVM/Halmos — DEFERRED»). **Exit ненулевой если любой probe WRONG** (сетап молча врёт — худший случай). `--probe-neural-lean` пишет в `setup_report.json::neural_lean_seam` одну не-разряженную аксиому из `axiom_registry.json` (Lean-утверждение + путь проекта) — чистый handoff для отдельного теста провер'а, **данными, не исполнением**.

**Task 2 — φ-артефакт + F + H-заморозка.** 🔴 `phi.py` (кортеж, YAML, хеш). 🟡 `formalize.py` (лифт инварианта в кортеж с явными Trace/Exit-дефолтами). 🔴 `validate.py` (H-шаг + freeze + `checker_params` — Инв.6+9). Net-new и load-bearing.

**Task 3 — K-гейт (`check`) + verdict→outcome.** ✅ reuse gateway/solver. 🔴 `outcome.classify` + **two-tier acceptance** (`Verified` vs `⊥_assumptions_open`) + раздел IRREDUCIBLE/DISCHARGEABLE + φ_checked/φ_context. 🟡 `check.py` (хеш-recheck, inject Pre→require, Post→assert, Exit→targets, Trace→ext-calls). Обобщает orchestrator-спину в гейт с acceptance-семантикой.

**Task 4 — vacuity (`vacuity`).** ✅ reuse `vacuity_gate`. 🟡 `vacuity.py`: **Probe R на любой контракт сразу; Probe M opt-in через `--family`** — без семьи возвращает BLOCKED (не PASS) на load-bearing-измерении (честно: «не оценено»). Отсутствие семьи **не может** дать false green. Авто-построение семьи — backlog (T1-подзадача уже в roadmap).

**Task 5 — assurance (`package`).** ✅ reuse `emit_*`/`assemble`/`lint`. 🔴 spine-синтезатор (топ Post-claim + lean-листы аксиом + 4 именованных допущения: `A_solver`, `A_machine_semantics`, `H_bytecode=unverified`, deferred-измерения). 🟡 `package.py`. Зелёный run → WELL-FORMED, `--replay`-able package.

**Task 6 — `run` + `status`.** 🟡 секвенсор, стоп на первом не-зелёном; терминал = `Verified(b,φ)` только при полной конформности, иначе `⊥_spec`/`⊥_gen`/`⊥_assumptions_open`. `status` рендерит верх по слабейшему листу (render-правило). Без новой гейт-логики.

**Task 7 — доки.** 🔴 `docs/adr/0004_tcg_cli_gate.md` (решения: MVP = trusted gate вокруг внешнего вайб-кодинга; G external/untrusted; поверхность formalize→validate→check→vacuity→package; **two-tier acceptance — green `Verified(b,φ)` только при полной конформности, иначе `⊥_assumptions_open`; раздел IRREDUCIBLE vs DISCHARGEABLE assumed-листов; φ_checked vs φ_context**; автономный `tcg run`-loop — будущий seam; маппинг команд на roadmap-гейты: check/vacuity→T1, package→T2, e2e-гейт→шаг к T3). 🔴 `docs/backlog/0006_*.md` (инкременты, путь `⊥_assumptions_open → green Verified`: авто-семья, полнокортежный F-промпт + покрытие Trace/Exit, bytecode-identity discharge, нейро-Lean-разрядка как валидированное расширение, автономный G/I-loop).

---

## Verification — как тестировать e2e

1. **Task 1 первым:** `python -m tcg setup-check` → матрица P0–P8 зелёная (или честные WALL/DEFERRED); exit 0; ни одного WRONG. Это и есть эмпирическое разрешение verify-level.
2. **Source-level run (честный non-green):** `tcg run --contract contracts/MiniVault.sol --name MiniVault` (replay seed-φ) → `formalize`(φ-кортеж) → `validate --approve`(заморозка) → `check`(Accept) → `vacuity`(PASS, Probe R) → `package`(WELL-FORMED, но `H_bytecode=unverified`). `outcome.json` = **`⊥_assumptions_open`** (НЕ green): открыт dischargeable-лист bytecode-identity. Это корректный MVP-исход — честный evidence-package без false-green; `package` рендерит верх ниже green. green `Verified(b,φ)` достижим только после discharge bytecode-identity (backlog).
3. **Refute-путь:** тот же на `MiniVaultBuggy.sol` → `check` exit 3 + witness; `run` завершается `⊥_gen`; **никакого** «verified».
4. **Vacuity-путь:** dead-фикстура → `vacuity` FLAG, acceptance заблокирован.
5. **Honesty-путь:** удалить ledger-лист → `package` lint INVALID (closure-FLAG), exit 3 — скрытое допущение поймано.
6. **Independent re-check:** `python -m cycle.assurance.verify_package <pkg>/ --replay` воспроизводит вердикты.
7. **(После Task 1 neural-seam, отдельно):** взять `neural_lean_seam`-аксиому, прогнать Pythagoras-32B/Goedel-V2 → дропнуть вывод в `aave_arith` lake-проект → `lake build` (ядро). Начать с лёгкой (`mulDiv_le_left`), затем стресс-тест `transfer_sum_preserved`. Замер → следующий numbered Finding.

## Critical files

- [cycle/orchestrator.py](cycle/orchestrator.py) — F→gateway→K-спина, которую CLI обобщает; argparse/replay-идиома.
- [cycle/trusted/solver.py](cycle/trusted/solver.py) — `run_solver`/`Verdict`; источник `proved|counterexample|inconclusive|compile_error`.
- [cycle/measurement/vacuity.py](cycle/measurement/vacuity.py) — `vacuity_gate`/`reachability_probe`; PASS/FLAG/BLOCKED + family-gap.
- [cycle/assurance/](cycle/assurance/) — `emit.py`/`assemble.py`/`verify_package.py`/`schema.py`; emit/assemble/lint, контракт ledger'а.
- [cycle/trusted/proofs/aave_arith/AaveArith/Basic.lean](cycle/trusted/proofs/aave_arith/AaveArith/Basic.lean) + `axiom_registry.json` — ghost-аксиомы (mulDiv-границы, ar_delta, transfer_sum_preserved); neural-seam цель.
- pilot `spine.yaml` под `cycle/artifact_format/` — шаблон для spine-синтезатора.

## Честные gaps (что НЕ закрываем в MVP — записать, не замолчать)

1. **F одно-инвариантен**, не кортеж → лифт с явными `declared/deferred`-дефолтами; полнокортежный промпт = liveness-фоллоуап, не soundness-гейт.
2. **H/freeze не существует** нигде → net-new (Task 2).
3. **Vacuity Probe M требует ручную семью** → Probe R безусловно; Probe M opt-in; без семьи BLOCKED, не PASS.
4. **Live cross-agent не подключён** (orchestrator:76-80 отказывается) → MVP single-contract; cross-A/G — будущий seam с тем же честным отказом.
5. **Инв.7 (bytecode-identity) не разряжаем на source-level** → DISCHARGEABLE-лист `harness_faithfulness: unverified`, который **капает исход до `⊥_assumptions_open` (не green)**. Путь к green (backlog): runtime bytecode hash + pinned compiler settings + immutables/constructor/metadata accounting (Sourcify-style). НЕ оставляем dischargeable-пункт под зелёным.
6. **z3 version skew** (4.12.6 vs 4.16.0 pin) → Task 1 P0 записывает реально судящий z3 в каждый record (Инв.9).
7. **Нейро-провер на наших леммах — неизмерено** → seam-данные в Task 1; коммит после замера, не предположения.

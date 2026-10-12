# `cycle/naive_loop/` — голый луп «вайбкодинг + вайбсолвер» (Task 0004 → Finding 0006)

Исполняемая форма провокации **«никакой ресерч не нужен — хватит бесконечного лупа»**:
один автономный агент (latest Opus) пишет код+инварианты+harness и сам гоняет солвер до
сходимости. Если голый луп закрывает нашу заявленную позицию (`спека → код + доказательство`)
сам — наш ресерч (DSL, proof harness, библиотека) overkill, и корректный вывод = **пивот**.

**Результат (Finding 0006): луп рапортует `proved` 100% на всех уровнях; честно — обваливается
по мере роста реалистичности.** L1 3/3 настоящих → L4 **0/4** на реальном Vat (все `proved` —
о реимплементации, faithfulness не установлена). Разрыв «рапорт↔честно» = false-proven,
порождаемый ровно обязательствами курируемого harness-слоя. **Не пивот; H1 подтверждён.**

## Честный бой (правила ревизии 0004)

- **Модель:** latest Opus, агентный (сам зовёт solc/halmos/forge), max budget — тест **потолка**.
- **Разрешено всё публичное:** ghost-vars, tracked-sum, `require`-assume, snapshot 2-state,
  Kupferman-самопроверка, меню движков (SMTChecker + halmos).
- **Запрещены только наши артефакты:** `trusted/harness/*Ghost.sol`, `Vat*.sol`, `axiom_registry.json`,
  дистиллированные наборы. Sandbox — чистая комната.
- **Судья = солвер, никогда LLM.** `judge.py` не доверяет self-report агента.

## Файлы

| Файл | Роль |
|---|---|
| `levels.json` | pre-registered лестница L1–L4 + канон-наборы (класс stateless/quantified/temporal + флаги `requires_mapping_sum`/`requires_product`) |
| `prompts/agent_synthesis.md` | задача агенту (кодирует честный бой + output-контракт `inv_<name>.sol`+`manifest.json`) |
| `loop.py` | драйвер: Opus headless в sandbox, captures транскрипт/стоимость/итерации, потом судит |
| `judge.py` | judge=солвер: бакеты proved/refuted/inconclusive/missing + **Probe R** (достижимость) + **faithfulness-гейт** (PASS/FLAG/BLOCKED) |
| `aggregate.py` | две метрики ревизии: mean±spread и **union/best-of-N** (на `clean`), per-class, false-proven |
| `runs/` | per-run sandboxes (gitignored): harness'ы агента + `transcript.jsonl` + `artifact.json` |

## Запуск

```bash
cd cycle/naive_loop
python3 loop.py --level L1 --model opus          # один автономный прогон
python3 loop.py --level L1 --dry-run             # только промпт, без модели
python3 judge.py runs/L1__<id> --level L1        # пересудить sandbox
python3 aggregate.py                             # сводка по всем уровням (пересуживает свежим судьёй)
```

Честные границы — см. Finding 0006 §«Честные оговорки» (N=1 пилот; авто-гейт ловит faithfulness
L4, но не нагруженность L3 — её ловит ручной Probe-M; планка refinement — эвристика).

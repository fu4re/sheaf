# Task 0006 — tcg: setup-verification spike (P0–P8)

- **Дата:** 2026-06-28 · **Тип:** инженерная задача (foundation, блокирующая)
- **Опирается на:** [план tcg CLI](../plans/adr-federated-parrot.md) (§ Task 1) · ADR-0003 (роли/инварианты) · Finding 0005 (vacuity) · Finding 0002 (solver-as-judge)
- **Зависит от:** — · **Разблокирует:** 0007, 0008, 0009, 0010, 0011
- **TL;DR:** прежде чем строить гейт — **эмпирически проверить тулчейн**, а не предположить. Один прогон гоняет solc/SMTChecker(CHC+BMC)/bundled-z3/lake на known-good и known-bad фикстурах, печатает работает-vs-стена и **падает, если сетап молча врёт**. На этом решается verify-level (source-level достаточен или нет).

## Зачем (одно предложение)

Для верификационного продукта **ложный зелёный хуже отсутствия инструмента**; verify-level (source vs глубже) нельзя выбирать умозрительно — эта задача даёт доказательную базу для выбора и фундамент CLI (`cli.py` + `outcome.py` exit-таблица).

## Что строим

- `tcg/__main__.py`, `tcg/cli.py` — argparse-скелет с субпарсерами (без новых рантайм-зависимостей; py3.12 + PyYAML).
- `tcg/outcome.py` — единая exit-таблица (`0 green · 2 Unknown/BLOCKED · 3 Refute/FLAG/INVALID · 4 ⊥_spec · 5 ⊥_gen · 6 ⊥_assumptions_open · 1 usage`).
- `tcg/commands/setup_check.py` — матрица probe'ов, каждый печатает `OK / WALL(reason) / WRONG(expected vs got)`.

Переиспользует: `cycle/trusted/solver.py::run_solver`, `cycle/measurement/vacuity.py::reachability_probe`, существующие фикстуры. **Read-only по исходникам** (пишет только JSON-отчёт + во временный BUILD-каталог).

| Probe | Фикстура | Ожидание | Дерискает |
|---|---|---|---|
| P0 версии | — | пины AGENTS.md | z3 standalone(4.12.6) vs pin(4.16.0); записать реально судящий bundled-z3 |
| P1 prove | `trusted/smt_smoke/ProvablePass.sol` | `proved` | CHC доказывает истинное |
| P2 refute+witness | `ProvableFail.sol` | `counterexample`, witness `a=1` | Refute реален |
| P3/P4 e2e good/bad | `MiniVault.sol` / `MiniVaultBuggy.sol` + seed-φ | Accept / Refute+witness | гейт принимает корректный, отвергает багнутый с witness |
| P5 vacuity FLAG | `VaultAssetAGDead.sol`, `MiniERC20NoMintConservation.sol` | FLAG | намеренно-вакуумный FLAGается |
| P6 BMC | `MiniERC20Delta`-семья | CHC inconclusive, BMC refutes | CHC+BMC + engine⟂квантор |
| P7 Lean build | `cycle/trusted/proofs/aave_arith/` | `lake build` rc=0 | trusted-base реально билдится |
| P8 ext-calls | one-call cross harness | untrusted=havoc-wall, trusted=может вакуум | потолок source-level Trace |

## Definition of Done

1. **`python -m tcg setup-check` запускается** и печатает матрицу P0–P8 (OK/WALL/WRONG по каждому).
2. **Падает на WRONG:** если любой probe дал НЕ ожидаемый вердикт (сетап врёт) → exit ненулевой; WALL (инструмент отсутствует) → exit 2, но не маскируется под OK.
3. **P1–P6 проходят** на этой машине ИЛИ честно помечены WALL с причиной.
4. **z3-skew зафиксирован:** P0 записывает версию реально судящего (bundled) z3, не standalone.
5. **Verify-level verdict напечатан:** «source-level достаточен для MVP-гейта» либо «Trace требует KEVM/Halmos — DEFERRED» — на основе P1–P6/P8, не предположения.
6. **`--probe-neural-lean`** пишет в отчёт одну не-разряженную ghost-аксиому (Lean-утверждение + путь lake-проекта) как seam для 0013 — данными, не исполнением.

## Артефакт (проверяемый отдельно)

`cycle/measurement/artifacts/tcg_runs/setup_report.json` — матрица probe'ов + verify-level verdict + neural_lean_seam. Проверяется независимо: перезапуск `tcg setup-check` воспроизводит вердикты; CI-ассерт exit-кода. **Это первый артефакт, который верифицируется отдельно** (фундамент доверия ко всему остальному).

## Риски / открытые

- Пути фикстур и точные вердикты — **со слов под-агента**; первый шаг реализации = подтвердить, что фикстуры существуют (если нет — добавить минимальные в `cycle/trusted/smt_smoke/`).
- bundled-z3 версия неизвестна до P0 — это и есть смысл probe'а.

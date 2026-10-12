# SPIKE-T1 Report — Ghost-механика на CALL + аппендиксы TCG-005

Источник задачи: [tast_t1.md](tast_t1.md) · Стенд: C9 (native arm64) · Форк из
C9-Q4. Judge = solver (kprove/kore-exec); вердикты — только из наблюдённого
поведения. Приоритет Q1→Q2→Q3→Q4.

## Стенд (pinned)

| Компонент | Версия / hash |
|---|---|
| Kontrol | 1.0.255 |
| K (`kprove`/`kompile`) | v7.1.337 |
| `kore-exec` (haskell backend) | 0.1.155 |
| KEVM semantics | 1.0.678 · nix `l131dddk…-kevm-source` |
| blockchain-k-plugin | `207ae5121e5178a09742ed746f2d15e34b1750cc` |
| Хост | macOS 14.6, Darwin 23.6.0, arm64 |

Сборка форка: `kompile <top>.k --backend haskell -I . -I <kproj>/evm-semantics -I
<kproj>/plugin` (порядок `-I .` первым обязателен — иначе `requires "evm.md"`
резолвится на стоковый `evm.md` из `-I`, и правки теряются).

## Вердикты (сводка)

| Q | Вердикт | Стоп-правило |
|---|---|---|
| **Q1** инкремент на CALL | **только правка, N=2 правила (`#mkCall`+`#mkCreate`), diff = 3 аддитивные строки; штатное не сломано** | **НЕ сработало** (не «всё семейство» + регрессия зелёная) |
| **Q2** toy + REVERT | **ghost переживает REVERT (PROVED); 1 CALL → счётчик=1 (наблюдено)** | — |
| **Q3** goal-as-circularity | **цель ∈ C (самоприменима после шага): pos PROVED / neg FAILED** | — |
| **Q4** consequence-стык | **механика продемонстрирована: стык subsumption'ом без trusted-правила; различитель в логах зафиксирован** | — |

---

## Q1 — Инкремент на CALL: механика

**Вердикт:** `без правки штатных правил: НЕВОЗМОЖНО чисто | только правка: N=2
правила (общие стыки #mkCall и #mkCreate), diff = 3 аддитивные строки, покрывает
все 6 опкодов CALL-семейства`.

**Стоп-правило НЕ сработало:** правится не «всё CALL-семейство» (6 опкодов), а 2
общих внутренних стыка; штатный KEVM-тест на форке проходит (регрессия зелёная).
Это оставляет A5 в дешёвой форме: инструментация — 3 аддитивные строки на общих
junction'ах, структурно идентичные уже существующему `<callDepth> +Int 1`.

### Разведка: куда сходится CALL-семейство (evm.md)

Все 4 message-call опкода → общий `#call` → `#callWithCode` → **`#mkCall`**
(evm.md:1677). CREATE/CREATE2 → `#create` → **`#mkCreate`** (evm.md:1948).
Диспетчер `#exec [ CO:CallOp ]` (evm.md:509) + `#exec [ CSO:CallSixOp ]` (508)
покрывают всю четвёрку двумя sort-специализированными правилами. `#mkSystemCall`
(EIP-4788 beacon-roots) — протокольный фрейм, НЕ пользовательский опкод (инстру-
ментируется отдельно, если считать протокольные вызовы).

⇒ Наивная оценка «правка каждого опкода» = 6. Реальная = **2 стыка** (`#mkCall`
для 4 message-call'ов, `#mkCreate` для 2 create'ов).

### (i) Неинвазивный хук с приоритетом — самоприменение (провал зафиксирован)

Внешний модуль, правило приоритета 40 (< штатных 50) на CALL-опкоде,
инкрементит `<callCounter>` и «возвращает» CALL штатному правилу:
`repro/t1-q1/i-priority/main.k`.

```
kprove q1i-selfloop-spec.k --definition i-priority-kompiled --depth 8
```
Фронтир после 8 шагов (`logs/t1-q1-i-selfloop.log`):
```
  <k>
    CALL 0 43 0 0 0 0 0 ~> _DotVar2 ~> .K     // CALL ВСЁ ЕЩЁ в голове — не съеден
  </k>
  <callCounter>
    8                                          // 1 вызов -> счётчик 8: переусчёт
  </callCounter>
... backend terminated because the configuration cannot be rewritten further
```
Приоритет 40 всегда выигрывает ⇒ штатное `[call]` НИКОГДА не срабатывает ⇒ CALL
не исполняется (не завершается) и счётчик растёт на каждый шаг. Гашение
самоприменения требует guard-флага (доп. ячейка) + хука пере-взвода после
возврата вызова — т.е. снова правок семантики. **(i) чисто-неинвазивно
невозможно.**

### (ii) Правка на стыках #mkCall / #mkCreate — работает

Форк: `repro/t1-q1/ii-mkcall/evm.md`. Полный diff к стоковому `evm.md` (3
аддитивные строки, N=2 правила тронуто):
```diff
40a41,42
>         <callCounter> 0 </callCounter>   // GHOST: user-call frame counter (outside <ethereum>, survives revert)
1681a1684                                  // rule #mkCall
>          <callCounter> CC => CC +Int 1 </callCounter>   // +1 per message-call frame (CALL/CALLCODE/DELEGATECALL/STATICCALL)
1958a1962                                  // rule #mkCreate
>          <callCounter> CC => CC +Int 1 </callCounter>   // +1 per create frame (CREATE/CREATE2)
```
Сборка: `callCounter` присутствует (22 вхождения в `compiled.txt`).

**Инкремент реально срабатывает** (Tier B, `repro/t1-q1/ii-mkcall/q1b-mkcall-spec.k`):
```
kprove q1b-mkcall-spec.k --definition ii-mkcall-kompiled --spec-module Q1B-MKCALL-SPEC --depth 1
=> #Top   (PROVED)
```
Один шаг `#mkCall` переводит `<callCounter> CC => CC +Int 1` (все прочие ячейки
правила заданы явно, цель `<k>` = точный однашаговый остаток). ⇒ вход в
message-call фрейм инкрементит ghost-ячейку.

### (iii) Иной механизм K — сводится к (i)/(ii)

Опкоды KEVM — данные, диспетчеризуемые через `#exec [ OP ]`, а не `strict`-
конструкторы; хуков «после применения правила» в K нет. Любая точка наблюдения
«был CALL» — это либо правило, срабатывающее на CALL (⇒ (ii)), либо конкурирующее
правило (⇒ (i), самоприменение). Единственная точка `#exec`-инструментации —
`#exec [ CO:CallOp ]` (2 правила), правка которых — та же (ii). Отдельного
неконкурирующего хука нет.

### Обязательная проверка: штатное поведение не сломано (регрессия)

Стоковая KEVM-спека `media/201908-trufflecon/add-spec.k` (правило `#next [ ADD ]`,
арифметика + диспетчер опкодов), адаптирована под форк
(`repro/t1-q1/ii-mkcall/regression-add-spec.k`):
```
kprove regression-add-spec.k --definition ii-mkcall-kompiled --spec-module REGRESSION-ADD-SPEC
=> #Top   (PROVED)
```
Негативный контроль (`q1-negctl-spec.k`): ADD оставляет `<callCounter>` неизменным
— PROVED (см. ниже). ⇒ инкремент строго на call-фреймах, штатная семантика цела.
Обоснование по конструкции: ячейка `<callCounter>` не входит в LHS ни одного
штатного правила; инкременты пишут только её ⇒ применимость штатных правил не
меняется.

### Репродьюсер
- `repro/t1-q1/ii-mkcall/` — форк (ii): `evm.md`, `kevm-fork.k`, `q1b-mkcall-spec.k`,
  `regression-add-spec.k`, `q1-negctl-spec.k`.
- `repro/t1-q1/i-priority/` — форк (i): `evm.md` (только ячейка), `main.k`
  (правило-перехватчик), `q1i-selfloop-spec.k`.
- Логи: `logs/t1-q1-*.log`.

---

## Q2 — Сквозной toy + поведение при REVERT

**Вердикт:** `A→B: один внешний вызов → <callCounter> += 1 (наблюдено на реальном
STATICCALL) | REVERT: ghost-ячейка ПЕРЕЖИВАЕТ откат (PROVED)`.

### Q2a — счёт вызовов (реальный опкод)

Реальный STATICCALL A(1)→B(100) на форке
(`repro/t1-q1/ii-mkcall/q2a-call-count-spec.k`):
```
kprove q2a-call-count-spec.k --definition ii-mkcall-kompiled --spec-module Q2A-CALL-COUNT-SPEC --depth 30
```
Опкод исполнился до конца (вызов вернулся), на достигнутом узле
(`logs/t1-q2a-call-count.log`):
```
  <k>  #dropWorldState ~> 1 ~> #push ~> #refund 1000000 ~> #setLocalMem 0 0 b"" ~> #halt ~> _DotVar2  </k>
  <callCounter>  1  </callCounter>      // ровно один инкремент на один внешний вызов
```
Trace-факт «был вызов» выражен в Post через ghost (`callCounter = 1`). Аддитивность
(N вызовов → +N) — по конструкции: каждый из 4 message-call опкодов даёт ровно один
`~> #call` → один `#mkCall` → +1 (см. Q1). Полное закрытие claim'а в зелёный `#Top`
для сквозного вызова требует авто-конфига Kontrol (десятки мутируемых ячеек) —
это интеграционная граница (форк-kdist), а не свойство инкремента.

### Q2b — персистентность через REVERT (критично для T2)

KEVM откатывает фрейм так: `#popCallStack ~> #popWorldState`
(правило `EVM.return.revert`, evm.md:1835). Механизм сохранения/восстановления:
- `#pushCallStack`/`#popCallStack` (evm.md:246/252) — **только `<callState>`**;
- `#pushWorldState`/`#popWorldState` (evm.md:276/283) — **только `<accounts>`+`<substate>`**.

`<callCounter>` — прямой ребёнок `<kevm>`, вне `<ethereum>`, вне `<callState>` →
ни одно из 4 правил отката его не упоминает. Доказано
(`repro/t1-q1/ii-mkcall/q2-revert-spec.k`):
```
kprove q2-revert-spec.k --definition ii-mkcall-kompiled --spec-module Q2-REVERT-SPEC
=> #Top   (PROVED)
claim: <k> #pushCallStack ~> #pushWorldState ~> #popCallStack ~> #popWorldState => .K ... </k>
       <callCounter> 7 => 7 </callCounter>     // прозрачно для всей последовательности фрейм-вход→revert
```
⇒ **ghost-ячейка переживает REVERT**. Монитор видит сквозь try/catch → интерфейс
монитора для T2/T3 менять НЕ нужно (ожидаемое = факт). Это следствие размещения
ячейки вне account-substate (C9-Q4 + placement в форке).

### Репродьюсер
- `repro/t1-q1/ii-mkcall/q2a-call-count-spec.k`, `q2-revert-spec.k`.
- Логи: `logs/t1-q2a-call-count.log`, `logs/t1-q2-revert.log`.

---

## Q3 — Аппендикс TCG-005 §6.1: goal-as-own-circularity

**Вердикт:** `цель ∈ C (самоприменима после ≥1 шага)`.

Countdown-loop (`repro/t1-q3/`): `loop`/`count(N) => count(0)`. Замыкание для
СИМВОЛЬНОГО N требует индукции — после первого шага (`loop=>loop`, `N=>N-1`)
остаток `(loop, count(N-1))` разряжается самой целью, применённой как circularity
(K регистрирует её как circularity только после ≥1 шага).

**Положительный:**
```
kprove q3-loop-spec.k --definition q3-kompiled --spec-module Q3-LOOP-SPEC
=> #Top   (PROVED)
```
Для символьного N доказуемо только через goal-circularity ⇒ **цель была применима
как собственная circularity**.

**Отрицательный контроль** (самоприменение недостижимо: шаг ведёт в `gone`, не
`loop`):
```
kprove q3-neg-spec.k --definition q3-neg-kompiled --spec-module Q3-NEG-SPEC
=> FAILED
  <k> gone ~> _DotVar1 </k> <count> ... </count>
  The configuration's term doesn't unify with the destination's term ... cannot be
  rewritten further ... (InfoReachability) while checking the implication
```
Единственное отличие от положительного — достижимость самоприменения ⇒ контраст
изолирует механизм. **C≠∅ у листьев ⟹ ⊨⁺ бесплатно** — база индукции A3a держится.

### Репродьюсер
- `repro/t1-q3/q3-semantics.k` + `q3-loop-spec.k` (pos); `q3-neg-semantics.k` +
  `q3-neg-spec.k` (neg). Логи: `logs/t1-q3-*.log`.

---

## Q4 — Аппендикс TCG-005 §6.2: consequence-механика стыка

**Вердикт:** `механика продемонстрирована (стык через subsumption БЕЗ trusted-леммы);
различитель consequence vs trusted-правило зафиксирован в логах`.

Семантика (`repro/t1-q4/q4-semantics.k`): один шаг `seg1 => post` (`n:=n+1`),
правила ИЗ `post` НЕТ. Родительская цель — `seg1 => (Post_i)` с ослабленным Pre_j
(`ensures ?Y >=Int X`).

**Consequence-стык (без trusted)** `q4c-consequence-spec.k` → **PROVED**: достигнутое
`(post, n=X+1)` **унифицируется** с destination `post` И импликация `X+1 >=Int X`
держится → стык закрывается **subsumption'ом**; правило из `post` не применяется
(его нет).

**Trusted-стык** `q4t-trusted-spec.k` → **PROVED**: trusted-правило
`post => done [trusted]` **переписывает** промежуточную конфигурацию.

**Различитель (для шага 4 протокола)** — контраст `q4t-no-trusted-spec.k` (та же
родительская цель `seg1 => done`, но без trusted-правила) → **FAILED**:
```
  <k> post ~> _DotVar1 </k>
  The configuration's term DOESN'T unify with the destination's term and the
  configuration cannot be rewritten further ... (InfoReachability) while checking the implication
```
| | consequence (subsumption) | trusted-правило |
|---|---|---|
| в логе | «term **unifies** with destination» + impl. check (InfoReachability); шага-rewrite'а из junction-состояния НЕТ | junction-состояние **переписывается** (rewrite-ребро на RHS правила) |
| при удалении правил из junction-состояния | пруф держится (это чистая импликация) | пруф **ломается** (`done` не унифицируется и не переписывается → FAILED) |

⇒ consequence-переход = импликация (Post_i ⟹ Pre_j), НЕ применение правила;
различим в логах по «unifies with destination + implication check» vs rewrite-ребро.

### Репродьюсер
- `repro/t1-q4/q4-semantics.k`; `q4c-consequence-spec.k`, `q4t-trusted-spec.k`,
  `q4t-no-trusted-spec.k`. Логи: `logs/t1-q4*.log`.

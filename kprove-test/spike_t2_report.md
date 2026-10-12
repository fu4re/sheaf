# SPIKE-T2 Report — Интерфейсы мини-экземпляра + Guar_env (теоретик)

**Проект:** Loop-based Trusted Code Generation для Solidity/EVM.
**Отношение к другим файлам:** входные документы — TCG-004 (постулат A3b, посылки H5–H8; Р6 — Guar_env), TCG-005 (типизация рёбер `trusted-lemma`/`consequence`; ⊨⁺/Consequence), ARL-отчёт (Lemma 7.2), literature map (P0.3 statusCode/ghost, P2.a A_keccak, P2.b hostile-env, P1.4/P1.5 novelty). Ghost-механика — SPIKE-T1 (`<callCounter>`: инкремент на `#mkCall`/`#mkCreate`, переживает REVERT).
**Статус:** Q1 → Q2 → Q3 → Q4 закрыты; **стоп-правило Q2 не сработало** (V и F различаются). Спайк успешен. **Единственная материальная зависимость на T3:** доделка T1 под §2 (`<inFunc>` — спецификация ниже).
**Дата:** 2026-07-15

---

## 0. Нотация и рамка

- `bal[u] ≜ <storage>[C][#hashedLocation("Solidity", BAL_SLOT, u)]` — слот ledger-баланса пользователя `u` в контракте `C` (BAL_SLOT — фиксированный слот маппинга `mapping(address=>uint256) balances`).
- `balances[a]` — нативный ETH-баланс аккаунта `a` (ячейка `<balances>` в KEVM).
- `Σ bal ≜ Σ_{u ∈ Users} bal[u]` — сумма ledger-балансов; `Users` — символьное конечное множество известных участников (в claims — универсально квантифицируется, `A_keccak` разряжает дизъюнктность слотов).
- `<callCounter>` — ghost из T1: аддитивный счётчик CALL-фреймов (все message-call + create); переживает REVERT (T1 Q2b: PROVED).
- `<inFunc>` — ghost, спецификация в §2 (не реализован в T1, реализация — прекондиция T3).
- `[текст]` — verbatim из источника (со ссылкой); `[интерпретация]` — вывод против фактов семантики.
- Формулы — псевдо-K, транслируемая в K-claims (kompile-friendly): именованные ячейки, `_ => _` для перехода, `requires` для guard'а, `ensures` для post-guard'а. Универсальная квантификация по конфигурации подразумевается по правилам ARL (Def 3.2).

**Объект:** контракт `C` с двумя функциями — `deposit()` и `withdraw(uint256 amt)`. Второй — в двух вариантах: **V** (перевод до обнуления баланса) и **F** (checks-effects-interactions). Env — третий участник, только через Guar_env (§Q3).

**Solidity-уровень (только для читаемости; спека — над bytecode/KEVM):**
```solidity
mapping(address => uint256) balances;

function deposit() external payable {
    balances[msg.sender] += msg.value;                     // (D)
}

function withdraw_V(uint256 amt) external {                // ВАРИАНТ V
    require(balances[msg.sender] >= amt);                  // (V1)
    (bool ok,) = msg.sender.call{value: amt}("");          // (V2) SUSPENSION POINT
    require(ok);                                           // (V3)
    balances[msg.sender] -= amt;                           // (V4) — ПОСЛЕ CALL
}

function withdraw_F(uint256 amt) external {                // ВАРИАНТ F
    require(balances[msg.sender] >= amt);                  // (F1)
    balances[msg.sender] -= amt;                           // (F2) — ДО CALL
    (bool ok,) = msg.sender.call{value: amt}("");          // (F3) SUSPENSION POINT
    require(ok);                                           // (F4)
}
```

---

## 2. Спецификация `<inFunc>` (постулат; ТЗ для доделки T1)

Одиночного `<callCounter>` из T1 недостаточно для предиката «функция X активна» — реентранси-предикат по своей природе стеко-подобен (аддитив-декремент). Фиксируем интерфейс монитора здесь; T3 реализует его как расширение форка (2 стыка `#mkCall`/`#mkCreate` уже есть; надо добавить 3 стыка на выходе фрейма).

**Сигнатура:**
```
<inFunc> : Map(Int, Int)              // FuncSig4 ↦ активных фреймов
```
Ключ — 4-байтовый селектор функции (Solidity ABI: `keccak256(sig)[:4]` как `Int` в `[0, 2^32)`). Значение — счётчик Nat.

**Точки записи:**
1. **Вход в функциональный фрейм** (ancillary rule над `#exec [ JUMPDEST ]` или Kontrol summary-boundary, точная точка — вопрос T3): `<inFunc>[sig] => <inFunc>[sig] +Int 1`, где `sig = <callData>[0..4]` первого фрейма.
2. **Выход штатный** (`#return` @ evm.md `EVM.return.normal`): `<inFunc>[sig] => <inFunc>[sig] -Int 1`.
3. **Выход REVERT** (`#return.revert` @ evm.md:1835, тот же родитель, что `#popCallStack`): `<inFunc>[sig] => <inFunc>[sig] -Int 1`. Отличие от `<callCounter>` — тот через revert не откатывается по построению (вне `<callState>`, C9-Q4), но `<inFunc>` **должен** декрементироваться явно, потому что состояние «активна» связано с фактом присутствия в стеке.
4. **`STOP` / `#halt`** — тот же декремент.

**Инвариант (для A5-прозрачности):**
```
INV_inFunc : ∀sig. <inFunc>[sig] = |{ фреймы в call-stack, чей selector = sig }|
```

**Предикат ре-входа для селектора `sig`:**
```
reentered(sig)  ≜  <inFunc>[sig] ≥ 2
```

**Стоимость A5:** T1 показал форк = 3 аддитивные строки на 2 стыках. Расширение — ещё 3 строки на 3 стыках выхода (`#return.normal`, `#return.revert`, `#halt`); все — аддитивные, не трогают LHS штатных правил (аргумент A5-прозрачности переносится дословно из T1 §Q1).

**Открытое** (T3 discovery-work, не блокирует T2): точная точка «вход селектора» — либо инструментация после диспетчера Solidity (не bytecode-clean, требует Kontrol summary), либо на первом `JUMPDEST` фрейма с извлечением `<callData>[0..4]`. Выбор — по стоимости A5; **на формулы T2 не влияет** (интерфейс монитора зафиксирован).

---

## 3. Q1 — Интерфейсы обоих loop'ов

Для каждой функции — таблица `(Pre, Post, Exit, Foot_r, Foot_w, Rely, Guar)`. Обоснования — по строке на поле.

### 3.1 `deposit()` — идентично в V и F

| Поле | Формула (псевдо-K над KEVM-конфиг) |
|---|---|
| **Pre_d** | `<statusCode> .StatusCode </statusCode> ∧ <callData> SIG₁ +Bytes _ </callData> ∧ <callValue> V </callValue> ∧ <caller> U </caller> ∧ bal[U] = B₀ ∧ B₀ +Int V <Int pow256 ∧ balances[C] = EC₀ ∧ balances[U] = EU₀ ∧ EU₀ ≥Int V ∧ <callCounter> CC </callCounter> ∧ <inFunc> IF </inFunc>` |
| **Post_d** | `<statusCode> EVMC_SUCCESS </statusCode> ∧ bal'[U] = B₀ +Int V ∧ ∀u≠U. bal'[u] = bal[u] ∧ balances'[C] = EC₀ +Int V ∧ balances'[U] = EU₀ -Int V ∧ <callCounter> CC </callCounter> ∧ <inFunc'> IF </inFunc>` |
| **Exit_d** | `EVMC_SUCCESS` |
| **Foot_r_d** | `{ bal[U], <callValue>, <caller>, balances[C], balances[U] }` |
| **Foot_w_d** | `{ bal[U], balances[C], balances[U] }` |
| **Rely_d** | В точках приостановки — их нет (deposit не делает внешних вызовов; между `[D]` и границей транзакции — атомарное исполнение EVM). На **границе транзакции** (H8): `∀u. 0 ≤Int bal[u] <Int pow256 ∧ 0 ≤Int balances[C] <Int pow256` — leger-баланс well-formed. |
| **Guar_d** | Записи ⊆ Foot_w_d (frame-claim). Внешних вызовов НЕТ ⟹ `<callCounter>` неизменна ⟹ никаких обещаний по CALL. `<inFunc>[SIG_deposit]` +1 на входе, -1 на выходе (баланс = 0 после успешного завершения). |

**Обоснования (по строке):**
- Pre: `.StatusCode` фиксирует, что мы в точке вызова (не в середине exception-handling); `B₀ +Int V <Int pow256` — отсутствие overflow (иначе Solidity 0.8+ ревертит; либо добавить revert-путь в Post).
- Post: все `bal[u]` кроме `U` не тронуты — механически проверяемое frame-условие; `<callCounter>` неизменен по конструкции (нет `#mkCall`/`#mkCreate` в теле).
- Exit: `EVMC_SUCCESS` через `<statusCode>`-native (P0.3 lit-map: verified-smart-contracts spec-tmpl.k pattern).
- Foot_r/w: буквальный список слотов, читаемых/писуемых семантикой опкодов Solidity-компилятора (SLOAD/SSTORE на BAL_SLOT+keccak(U), плюс native balance-transfer).
- Rely: точки приостановки — H8. Deposit не имеет CALL, значит внутри тела точек приостановки нет. На tx-boundary — только всеформленность `bal[·]`, потому что депозит не читает других слотов.
- Guar: frame ⊆ Foot_w — фактическая проверка H5 (см. Q4 obligation `frame-deposit`).

### 3.2 `withdraw_V(amt)` — уязвимый вариант

| Поле | Формула |
|---|---|
| **Pre_w^V** | `<statusCode> .StatusCode </statusCode> ∧ <callData> SIG₂ +Bytes #buf(32, A) </callData> ∧ <caller> U </caller> ∧ bal[U] = B₀ ∧ B₀ ≥Int A ∧ balances[C] = EC₀ ∧ EC₀ ≥Int A ∧ <callCounter> CC </callCounter> ∧ <inFunc> IF </inFunc>` |
| **Post_w^V** | `(<statusCode> EVMC_SUCCESS </statusCode> ∧ bal'[U] = B₀ -Int A ∧ balances'[C] = EC₀ -Int A ∧ balances'[U] = EU₀ +Int A) ∨ (<statusCode> EVMC_REVERT </statusCode> ∧ bal'[U] = B₀ ∧ balances'[C] = EC₀)`. Дизъюнкт REVERT — если внешний CALL вернул ok=false. |
| **Exit_w^V** | `EVMC_SUCCESS ∨ EVMC_REVERT` |
| **Foot_r_w^V** | `{ bal[U], <caller>, balances[C], balances[U] }` |
| **Foot_w_w^V** | `{ bal[U], balances[C], balances[U] }` |
| **Rely_w^V** | В **единственной точке приостановки** (V2 = момент внешнего CALL, `<k>` головой на `#exec [ CALL ... ]`): `bal[U]` НЕ уменьшается за время внешнего фрейма. Формально: `Rely_w^V @ V2 : bal[U] ≥Int B₀` (пре-CALL значение). На tx-boundary — как у deposit (well-formed leger). |
| **Guar_w^V** | Записи ⊆ Foot_w. Совершает не более одного message-CALL на адрес U с value = A (V2). Может ре-входить в любой public entry point C (в том числе withdraw_V). `<callCounter> +Int 1` на V2 (T1 §Q1). `<inFunc>[SIG_withdraw_V] +Int 1` на входе, `-Int 1` на выходе. |

**Обоснования:**
- Post-дизъюнкт: V-вариант ревертит на неуспешном CALL (проверка `ok` в V3), при этом ledger откатывается (bal[U] не изменялся до V4). Ветка SUCCESS соответствует `ok=true`.
- Rely_w^V @ V2 — **ключевой момент**: между V1 (`SLOAD bal[U]`) и V4 (`SSTORE bal[U]`) значение bal[U], которое компилятор использует для вычисления `B₀ -Int A`, кэшируется в стеке EVM. Если env изменил `<storage>` во время CALL, компиляция всё равно записывает `B₀ -Int A`, где `B₀` — старое значение → Rely формализует именно это: **никто не должен обнулить bal[U] за время нашего CALL, иначе финальная запись V4 пишет старое-минус-A против нового состояния** (это и есть механика реентранси). Формально: Rely требует, чтобы env-транзиции сохраняли инвариант `bal[U] = B₀` на интервале `[V2, V2_return]`.
- Guar разрешает ре-вход в собственные entry-points — это правда, потому что V не имеет ни reentrancy-guard, ни `nonReentrant`-модификатора.

### 3.3 `withdraw_F(amt)` — исправленный вариант

| Поле | Формула |
|---|---|
| **Pre_w^F** | Идентично Pre_w^V. |
| **Post_w^F** | `<statusCode> EVMC_SUCCESS </statusCode> ∧ bal'[U] = B₀ -Int A ∧ balances'[C] = EC₀ -Int A ∧ balances'[U] = EU₀ +Int A` — или ветка `EVMC_REVERT` с полным откатом (F4 revert-check). |
| **Exit_w^F** | `EVMC_SUCCESS ∨ EVMC_REVERT` |
| **Foot_r_w^F**, **Foot_w_w^F** | Идентичны варианту V (тот же bytecode-набор SLOAD/SSTORE, только порядок другой). |
| **Rely_w^F** | В **единственной точке приостановки** (F3, момент внешнего CALL): НЕТ ограничения на `bal[U]` — запись F2 уже произошла, значение bal[U] = B₀ -Int A закоммичено в storage. На tx-boundary — как у deposit. Формально: `Rely_w^F @ F3 : ⊤` (over `bal[U]`); только `balances[U]` не должен уменьшаться под нами (нативный ETH-баланс) — это обеспечивается семантикой EVM (env не может списать native-баланс без вызова к нам). |
| **Guar_w^F** | Записи ⊆ Foot_w. Один message-CALL на адрес U с value = A (F3), при этом на момент CALL `bal[U] = B₀ -Int A` уже записано. `<callCounter> +Int 1` на F3. `<inFunc>[SIG_withdraw_F] +Int 1`/`-Int 1` по фрейму. Ре-вход в C разрешён. |

**Обоснования:**
- Ключевое отличие Guar_w^F от Guar_w^V — **временнáя привязка**: F гарантирует, что **на момент своего внешнего CALL** значение `bal[U]` уже отражает списание. Это ровно то различие, которое видит self-compat (см. Q2).

---

## 4. Q2 — Self-compat: инстанциация PAR-правила для повторного входа

### 4.1 Формулировка PAR-правила для реентранси

Классическое PAR (Jones/RGSim, TOPLAS): для параллельных компонент `P₁ ∥ P₂` c интерфейсами `(Pre_i, Post_i, Rely_i, Guar_i)` требуется попарно `Guar_i ⟹ Rely_j` для `i ≠ j`.

**Инстанциация для реентранси (не в литературе — новизна A3b, P1.5):** «параллелизма нет, но окружение может выполнить нашу же функцию посреди нашего же CALL». Виртуальные потоки = **экземпляры фрейма**, индексированные `<callDepth>` или (эквивалентно, per H8-suspension) значением `<inFunc>[sig]` в момент повторного входа. Self-compat:
```
∀i, j : экземпляры одного loop w, i ≠ j :  Guar_w(instance j) ⟹ Rely_w(instance i)
```
Guar_w и Rely_w — property of **actions** (переходов state-to-state), не instance-locale (Jones-style: relation on ⟨state, state'⟩). Тогда self-compat редуцируется к **одному** условию:
```
(SELF-COMPAT_w)   Guar_w ⟹ Rely_w
```
как отношения на переходах — без параметризации экземплярами. Инстансы нужны только для **интерпретации** (кто был субъектом какого перехода); формально они устраняются.

### 4.2 Когерентность инстанциации

**Вердикт: когерентно, инстанциация ЯВНАЯ через `<inFunc>` (не требует расширения интерфейса сверх §2), различает V/F.**

- **Не требуется**: индексация Guar/Rely по callDepth. Достаточно, чтобы `<inFunc>` был в конфигурации — тогда предикат «между двумя моментами произошёл ре-вход» = `<inFunc>[sig]` в claim'е доступен обеим сторонам импликации.
- **Требуется** (это H8): Rely_w формулируется ТОЛЬКО в точках приостановки. Иначе self-compat вырождается: атомарные транзиции EVM не наблюдаемы для env, и любое Rely внутри тела — беззубо ограничивает Guar.

### 4.3 Формула SELF-COMPAT для варианта V — **проваливается**

Разворачиваем Guar_w^V ⟹ Rely_w^V в единственной точке приостановки V2:

**Guar_w^V как отношение на переходах** (что делает withdraw_V между V2 и V2_return):
```
Guar_w^V @ V2  :  ∃ A' ≤ B₀. bal[U] := bal[U] -Int A'     — если во время нашего CALL произошёл ре-вход и внутренний фрейм withdraw_V завершился успешно, он выполнил свой V4 и уменьшил bal[U]. (Никаких других записей в bal[U] Guar не разрешает; но эту — разрешает.)
```

**Rely_w^V @ V2:** `bal[U] = B₀` — значение сохраняется на весь интервал внешнего фрейма.

**Импликация:**
```
Guar_w^V  ⟹ ¬Rely_w^V     — внутренний withdraw_V, разрешённый Guar_w^V,
                              как раз уменьшает bal[U] и нарушает Rely_w^V.
```
Формально: возьмём переход `⟨bal[U] = B₀, ..., <callCounter> = CC⟩ ⇒ ⟨bal[U] = B₀ -Int A', ..., <callCounter> = CC + N⟩` для некоторого `N ≥ 1` (внутренние фреймы использовали хотя бы 1 CALL). Этот переход **∈ Guar_w^V** (записал в свой footprint, использовал разрешённый CALL); **∉ Rely_w^V** (bal[U] изменился, а Rely_w^V требовал сохранения). Contra.

**⟹ SELF-COMPAT_w для V проваливается.** Что и требовалось: V-вариант обязан провалиться, потому что классический DAO-style-реентранси именно этот инвариант и ломает.

### 4.4 Формула SELF-COMPAT для варианта F — **проходит**

**Guar_w^F @ F3** (что F делает во время своего внешнего CALL):
```
Guar_w^F @ F3  :  ре-вход внутренним фреймом withdraw_F может изменить bal[U'] для *других* U', если U' — msg.sender внутреннего фрейма.
                  На нашем U (наш msg.sender): bal[U] УЖЕ равен B₀ -Int A на момент F3 (записано F2 до CALL).
                  Внутренний withdraw_F для того же U ещё раз выполнит F1 (require bal[U] ≥ amt') — но bal[U] уже уменьшен, а `amt'` контролируется env. Если amt' > bal[U] на этот момент — F1 ревертит; если ≤ — F2 списывает ещё amt' и делает свой CALL. И так далее.
```
**Rely_w^F @ F3:** `⊤` над bal[U] (мы уже вписали своё). Единственное ограничение — `balances[U]` (native ETH) не должно уменьшиться под нами — но env не может списать native-баланс, минуя нас (Q3, Guar_env: «не может писать чужой storage / native balance напрямую»).

**Импликация:**
```
Guar_w^F  ⟹  Rely_w^F     — тривиально: Rely_w^F @ F3 не ограничивает bal[U],
                              а Guar_w^F не пишет в balances[U] иначе как через
                              стандартный CALL (учтён семантикой).
```

**⟹ SELF-COMPAT_w для F проходит.**

### 4.5 Что различает V и F — одной фразой

Различие держится на **временнóй привязке точки записи к точке приостановки**. Guar_w^V @ V2 разрешает будущему-внутреннему-фрейму «ещё не списал»; Guar_w^F @ F3 гарантирует «уже списал». Rely_w^V @ V2 требует «bal[U] = B₀» — противоречит Guar; Rely_w^F @ F3 = ⊤ на bal[U] — совместимо. Модификация одного порядка операторов ЛОКАЛЬНО меняет и Guar, и Rely так, что self-compat переворачивается — это и есть искомая **дискриминирующая способность** дисциплины.

### 4.6 Итог Q2 — **вердикт**

**`когерентно, различает V/F`.** Стоп-правило спайка НЕ сработало. Дисциплина имеет зубы, дальнейшая работа по Q3–Q4 осмысленна.

**Замечание:** инстанциация PAR-правила потребовала одного нестандартного шага — устранения индексации по экземплярам через переопределение Guar/Rely как отношений на переходах. Это стандартный приём в Jones-школе R/G (Jones, TOPLAS 1983; Liang et al., RGSim, TOPLAS 36(1) 2014), но **применение к реентранси — новое** (P1.5 не нашёл прецедента над EVM). Для A3b-доказательства это — центральная лемма (её нужно записать явно, как отдельный факт формализма над EVM).

---

## 5. Q3 — Guar_env, первая редакция

### 5.1 Форма (Р6 TCG-004, KEVM `[trusted]`-стиль)

Один символьный переход, over-approximating «любой EVM-код»:
```
rule [env-step]:
    <k> #execute:EnvOp => .K ... </k>
    <callDepth> D => D' </callDepth>          // env выполняет 0 или более фреймов
    <accounts>
      <account> <acctID> A </acctID> <storage> S => S' </storage> <balance> B => B' </balance> ... </account>
      ...                                     // env МОЖЕТ менять storage/balance ЛЮБЫХ аккаунтов, КРОМЕ C's storage напрямую (см. ниже)
    </accounts>
    <substate> ... => ... </substate>         // logs, touchedAccounts — свободно
    <statusCode> _ => STC' </statusCode>      // может ревертить/успевать
    <callCounter> CC => CC +Int K </callCounter>   // K ≥ 0 message-call фреймов (T1: инкремент только через #mkCall/#mkCreate)
    <inFunc> IF => IF' </inFunc>              // может увеличить/уменьшить любые счётчики через legitimate entry into C
  requires
    // Ограничения (то, что env НЕ может):
    ∀a. a = C ⟹ S'[C] изменён ТОЛЬКО через легитимные SSTORE, вызванные фреймами C
                (т.е. изменения S[C] отражены и в <callCounter>, и в <inFunc> — Aasm access-control-условие)
    ∧ B'[C] изменён ТОЛЬКО через message-call с value TO C или FROM C
    ∧ <origin>, <coinbase>, <blockhash>...<blockDifficulty> — не тронуты (env не пишет block-context)
    ∧ IF' полностью определяется реальным call-stack'ом (INV_inFunc сохраняется — A5-transparency)
  [trusted]                                    // KEVM abstract-semantics.k idiom (P2.b lit-map)
```

**Читается:** `env-step` — единичная символьная транзиция, представляющая произвольный EVM-код между двумя точками приостановки нашего loop'а. Реальный env — конечная композиция таких шагов; каждая шаг оверапроксимирован.

### 5.2 Таблица «может / не может / почему»

| # | env МОЖЕТ | Обоснование из семантики EVM |
|---|---|---|
| 1 | Вызывать любые public entry points `C` (deposit, withdraw_V, withdraw_F) | Публичные функции — часть внешнего интерфейса; entry не требует привилегий. Selector-based dispatch публичен. |
| 2 | Переводить value через `msg.value` при вызове наших entry-points | EVM `CALL` opcode принимает value как аргумент; ограничен только `balances[env] ≥ value`. |
| 3 | Ре-входить в незащищённые точки | Соглашение: у нас нет `nonReentrant`-модификатора и явных guard'ов (это часть модели уязвимости V). Env может вызвать withdraw_V пока withdraw_V активен. |
| 4 | Ревертить свой фрейм | `REVERT` — стандартный opcode, откатывает изменения фрейма (не транзакции целиком, если родитель не ревертит тоже). |
| 5 | Потреблять газ до `OUT_OF_GAS` | `<gas>` — публичная ячейка, монотонно убывает; env может исчерпать. |
| 6 | Писать в свой storage (`<storage>[env]`) и native balance любых аккаунтов, к которым имеет CALL-доступ | Изолированные SSTORE в чужой контракт — только через его CALL-frame. Native balance перемещается только опкодами CALL/SELFDESTRUCT. |
| 7 | Публиковать logs, изменять `<touchedAccounts>` | EVM позволяет LOG₀…LOG₄ и `touchedAccounts` расширяется автоматически. |

| # | env НЕ МОЖЕТ | Обоснование из семантики EVM |
|---|---|---|
| A | Подделать `msg.sender` **при вызове нашего фрейма** | KEVM: `<caller>` устанавливается опкодом CALL из caller'ского фрейма; env не может назвать `msg.sender = C` для нашего фрейма, потому что источник CALL — сам env (или его subcontract). Аналог: невозможно установить `<caller>` ≠ фактический родитель фрейма — семантическое свойство `#mkCall` (evm.md:1677, T1). |
| B | Прямо писать `<storage>[C]` (наши слоты) | SSTORE — per-frame opcode, изменяет storage контекстного аккаунта (`<id>`). Пока `<id> ≠ C`, SSTORE в env-фрейме не может изменить `<storage>[C]`. Единственный путь env→<storage>[C] — через CALL в наши entry-points. |
| C | Прямо писать `balances[C]` (native ETH баланс контракта) кроме через CALL к нам | Native transfer — только через опкоды CALL/CALLCODE/CREATE(2)/SELFDESTRUCT. Первые три идут через наши entry-points (`#mkCall` устанавливает `<caller>` и `<id>`). SELFDESTRUCT (Cancun: SENDALL) — субъект по посыл-к-себе; для передачи в C нужен, чтобы env выполнил `SELFDESTRUCT C` из собственного фрейма — что уменьшает env's balance и увеличивает `balances[C]` (пишется семантикой корректно, не является atypical write; A_selfdestruct — допущение об отсутствии таких вызовов, см. §5.3). |
| D | Нарушить атомарность транзакции | EVM: транзакция целиком коммитится или целиком откатывается (top-level revert = полный rollback). Промежуточные состояния между вложенными фреймами atomic в пределах opcode. Формально: `<callStack>`+`<worldStack>` pop-механизм (evm.md:246/276) обеспечивает atomicity. Верифицировано T1 §Q2b (ghost переживает revert — но native state откатывается). |
| E | Модифицировать `<origin>`, `<coinbase>`, `<gasLimit>`, `<blockhash>` и прочий block-context | Эти ячейки устанавливаются на границе транзакции/блока (native); не изменяются opcode'ами env. |
| F | Изменить наш `<inFunc>[sig]` иначе как через легитимный вход/выход фрейма `sig` | Прямое следствие INV_inFunc (§2): env может увеличить/уменьшить наш счётчик ТОЛЬКО организовав реальный вход в наш фрейм → это учтено в записи `<callCounter> +Int K`. Прямая запись в `<inFunc>` невозможна (ghost-ячейка не имеет SSTORE-путей). |

### 5.3 Допущения (Aasm-леджер, дополнения)

- **A_access:** в mini-экземпляре ни deposit, ни withdraw не имеют per-user access control (`onlyOwner`, whitelist и т.п.). Публичные entry-points открыты. Если бы были — Guar_env должен был бы явно исключить неавторизованные вызовы, а compat-обязательства учли бы это.
- **A_selfdestruct:** в scope мини-экземпляра env не использует `SELFDESTRUCT C` для внезапного увеличения `balances[C]`. Обоснование: это разрушает инвариант «`balances[C] ≥ Σ bal[u]`» в противоположную сторону (баланс растёт без увеличения ledger'а — не является уязвимостью, но ломает точную форму инварианта). Практический выход — ослабить инвариант до `balances[C] ≥ Σ bal[u]` (⊇, а не =). Оставлено как `A_selfdestruct` в леджере.
- **A_precompile:** env-вызовы в precompiles (0x01..0x0a) абстрагируются как `[trusted]` символьные правила (P2.b lit-map, verified-smart-contracts abstract-semantics.k pattern).
- **A_gas_termination:** каждый env-шаг конечен (газ убывает); каскад env-шагов между двумя точками приостановки нашего фрейма — конечен по построению EVM. Разряжается газ-микролеммой TCG-005 §Р5.
- **A_keccak:** unchanged, TCG-004 Р4.

---

## 6. Q4 — Таблица obligations мини-экземпляра

Типы рёбер по TCG-005 §4.2: `trusted-lemma` (шаг индукции по DAG, требует ⊨⁺-валидности цели), `consequence` (junction/subsumption, достаточно ⊨*). Итоговый trace-инвариант — `root` (top of trusted-lemma-подграфа).

### 6.1 Trace-invariant корневых узлов

**INV** (глобальный, root A3b):
```
∀ tx-boundary γ.  balances[C](γ) ≥Int Σ_u bal[u](γ)     ("solvency inv")
```
Читается: на всякой границе транзакции нативный баланс контракта покрывает сумму ledger-баланасов.

### 6.2 Полная таблица

| # | Obligation | Формула (сжатая) | Тип ребра (TCG-005 §4.2) | Ожидание V | Ожидание F |
|---|---|---|---|---|---|
| **1** | `frame-deposit` | Записи deposit ⊆ Foot_w_d | trusted-lemma | ✅ PASS | ✅ PASS |
| **2** | `frame-withdraw` | Записи withdraw ⊆ Foot_w_w | trusted-lemma | ✅ PASS | ✅ PASS |
| **3** | `compat-dep→with` | Guar_d ⟹ Rely_w в footprint-пересечении `{bal[U], balances[C]}` | compat (trusted-lemma-подобный) | ✅ PASS (deposit только +к bal, Rely_w про bal[U] сохранение → монотонное ↑ совместимо: в V-вариант Rely требует `= B₀` — deposit другим U не трогает bal[U], нашим U — увеличивает, что тоже нарушает `= B₀`. **Тонкость:** env вызывает deposit(U) во время нашего CALL → bal[U] увеличится. Формально: Guar_d ⟹̸ Rely_w^V. Классифицируется как **compat FAIL для V**, но по другой причине, чем self-compat.) ⚠️ **FAIL для V** | ✅ PASS для F (Rely_w^F не ограничивает bal[U]) |
| **4** | `compat-with→dep` | Guar_w ⟹ Rely_d | compat | ✅ PASS (Rely_d нет точек приостановки внутри → ограничение только на tx-boundary well-form; withdraw записи корректны) | ✅ PASS |
| **5** | `self-compat-deposit` | Guar_d ⟹ Rely_d | compat (self) | ✅ PASS тривиально (Rely_d @ suspension пуст, точек приостановки нет) | ✅ PASS |
| **6** | `self-compat-withdraw` (см. §Q2) | Guar_w ⟹ Rely_w | compat (self) | ❌ **FAIL** (§4.3) | ✅ PASS (§4.4) |
| **7** | `env-compat-deposit` | Guar_env ⟹ Rely_d | compat (env-узел, H7) | ✅ PASS (Rely_d минимален: well-form; Guar_env явно сохраняет `0 ≤ bal[u] < pow256`) | ✅ PASS |
| **8** | `env-compat-withdraw` | Guar_env ⟹ Rely_w | compat (env, H7) | ❌ **FAIL** (env может вызвать withdraw_V — сводится к §4.3) | ✅ PASS |
| **9** | `Post_d ⟹ INV` (junction) | В точке завершения deposit: `balances[C] ≥ Σ bal[u]` сохраняется (bal[U] +=V, balances[C] += V — равное увеличение) | **consequence** (subsumption, zero-step) | ✅ PASS | ✅ PASS |
| **10** | `Post_w ⟹ INV` (junction) | В точке завершения withdraw: `balances[C] ≥ Σ bal[u]` сохраняется (bal[U] -=A, balances[C] -=A) | **consequence** | ✅ PASS для локального withdraw-фрейма (внутренняя алгебра сходится); НО глобальный INV нарушается через реентранси (не решается локально — только через **compat-цепочку**; V проваливает #6/#8) — **root A3b INV для V — FAIL** | ✅ PASS |
| **11** | `INV` root (глобальный trace-инвариант) | Конъюнкция локальных INV-preservation + всех compat-пар | **root** (top of trusted-lemma подграфа) | ❌ **FAIL** (следствие FAIL на #6, #3, #8) | ✅ PASS |

### 6.3 Ремарки к типизации рёбер

- **#1, #2** — классические frame-claim'ы: цель — ⊨⁺-узел (тело deposit/withdraw делает ≥1 SSTORE-шаг → progress автоматом). Trusted-lemma (H5 через семантический аргумент).
- **#3–#8** — compat-рёбра. По TCG-004 §4 (леджер TCG-003) допускается **циклический подграф** compat-рёбер, корректность несёт A3b. Ожидание V/F различается на #3, #6, #8 — три места, где V материализует уязвимость.
- **#9, #10** — junction (consequence): Post_i ⟹ Pre_INV нулевого шага (импликация значений). По TCG-005 Р2/#2, consequence-рёбра ведут в нуль-шаговые узлы; достаточно ⊨* (не ⊨⁺). Механика продемонстрирована T1 §Q4 (impl. check без rewrite).
- **#11** — root; собирается индукцией по PAR-правилу. Проходит если все #3–#8 проходят (что и есть смысл A3b).

### 6.4 Критерий выхода спайка

Стоп-правило: если **хотя бы одна obligation** имеет одинаковый статус в V и F — дисциплина беззуба. **Наблюдаем: 3 из 11 obligations различают V/F (#3, #6, #8), плюс производные #10, #11.** Пять точек различения на 11-строчной таблице — материальная дискриминирующая способность.

Спайк успешен: T3 может кодировать эту таблицу и прогонять её в kprove как систему claims.

---

## 7. Открытое (для T3 и последующих спайков)

1. **`<inFunc>` реализация.** Точная точка «вход селектора» — Kontrol summary-boundary vs первый `JUMPDEST` с извлечением calldata prefix. Влияет только на A5-cost; формулы Q1–Q4 инвариантны.
2. **compat #3 для V** — я классифицировал как FAIL, но в чуть более слабой Rely_w^V (запретить только УМЕНЬШЕНИЕ bal[U], не изменение вообще) — это станет PASS. Ослабление корректно? Похоже да (deposit-от-env увеличивает bal[U], что для нас безопасно — мы вычтем свой A из увеличенного B₀+V ≥ B₀ ≥ A, финальное значение bal[U] = B₀+V-A ≥ 0). Формулировка Rely_w в §Q1 намеренно строгая; **вопрос T3** — какая версия проходит в реальном kprove-прогоне.
3. **A_selfdestruct** — если ослабить INV до `≥`, отношение всё работает. Убрать A_selfdestruct или зафиксировать явно?
4. **Junction'ов только 2 (#9, #10)** — мини-экземпляр их почти не задействует. Для более сложных loop'ов consequence-цепочки будут доминировать; отдельный спайк.
5. **Coq-механизация PAR-правила поверх ARL** — TCG-005 §6 fue пункт про статус Lemma 7.2 в Coq; для A3b-доказательства нужно понимать, покрывает ли Coq-разработка непустые A/C. Не блокирует бумажное A3b, но блокирует «полностью механизированное».
6. **Multiple msg.sender** — Users в §0 — универсально-квантифицированный конечный набор. В proof engineering — либо через универсальный квантификатор в Pre (kprove проверит на символическом U), либо через сегментирование по классам эквивалентности (Certora-style). Инвариантно к формулам.

---

## 8. Источники

- **TCG-004.md** — постулат A3b, посылки H5–H8 (§3), Р6 Guar_env, Р4 A_keccak. Роль: несущая, буквально цитируемая (H5–H8 воспроизведены в §Q4).
- **TCG-005.md** — типизация рёбер `trusted-lemma`/`consequence` (§4.2 Р2, §5 H5), ⊨⁺/Consequence, PAR-правило. Роль: типизация obligations в §Q4.
- **ARL_axiom_mechanics_report.md** — Lemma 7.2 (side-condition ⊨⁺), Def 3.1/3.2 (complete paths). Роль: ⊨⁺-обоснование H5 для frame-claims; квантификация в Post_w.
- **literature_map_A3a_A3b.md** — P0.3 (statusCode/ghost expressibility); P2.a (A_keccak); P2.b (hostile-env как `[trusted]`-правило — прототип §Q3); P1.4/P1.5 (novelty — self-compat при реентранси не найден). Роль: цитируемые прототипы + граница новизны.
- **t1_report.md (SPIKE-T1)** — `<callCounter>` реализация (Q1: 2 стыка `#mkCall`/`#mkCreate`), Q2b (переживает REVERT), Q3 (goal-as-own-circularity), Q4 (consequence в логах). Роль: механическая база под ghost-монитор; §2 постулирует расширение `<inFunc>` в том же стиле.
- **PAR-правило:** Jones (TOPLAS 1983), Liang et al. RGSim (TOPLAS 36(1) 2014). Роль: базовая форма правила, инстанциация к реентранси — §Q2.4 (новизна A3b, P1.5).
- **KEVM abstract-semantics.k** (runtimeverification/verified-smart-contracts) — `[trusted]`-стиль правил (§Q3). Роль: idiom для Guar_env.

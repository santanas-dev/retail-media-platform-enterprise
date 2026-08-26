# RM-GOV-001 — Mini-design: `roadmap.yaml` sequencing SSOT

> **Дата:** 2026-08-26
> **Задача:** `RM-GOV-001` (`kind: design`, этап G, зависимостей нет)
> **База:** `develop @ 2b935bb` = `origin/develop @ 2b935bb`
> **Статус:** **ожидает утверждения владельцем** — это условие приёмки задачи
> **Изменения канона/roadmap/registry/PROJECT_STATE/стенда:** нет

## 1. Задача и граница

`roadmap.yaml` становится единственным источником **последовательности работ**. Он не
дублирует и не переопределяет:

| Что | Владелец | Почему не здесь |
|---|---|---|
| статус функции (`reachable`/`blocked`) | `feature-registry.yaml` | registry — авторитет по статусу |
| спецификация journey | `user-journeys.md` | Tier 2 спецификация |
| текущий workstream / Next | `PROJECT_STATE.md` | канонический статус workstream'ов |
| архитектурные решения | ADR | ADR-процесс |
| фактическое поведение | код, тесты, CI | Tier 1 |

Схема удерживает эту границу **механически**: `additionalProperties: false` на всех объектах,
поэтому «протащить» в SSOT статус функции, шаг journey или процент готовности нельзя — документ
перестанет валидироваться. Проценты в схеме отсутствуют как класс: метрики генерируются
(`RM-GOV-003`), а не хранятся.

## 2. Артефакты задачи

| Файл | Назначение |
|---|---|
| `docs/product/roadmap.schema.json` | JSON Schema (draft 2020-12) |
| `scripts/ci/check-roadmap-schema.py` | валидатор: схема + семантические правила; импортируемый модуль |
| `scripts/ci/fixtures/roadmap.schema.example.yaml` | фикстура самопроверки; **не** roadmap |

Размещение схемы рядом с данными (`docs/product/`), а не в `packages/contracts/`, — сознательно:
`packages/contracts/*.schema.json` описывают продуктовые контракты (манифест, PoP-событие) и
проверяются job'ом `json-schema`. Roadmap — governance-артефакт; смешивать пространства имён
не следует. Валидатор лежит в `scripts/ci/` рядом с `check-import-boundaries.py` и повторяет его
идиому (`[label] PASS/FAIL`, exit 0/1).

Согласно правилу B-3 редакции v2 этот файл — **модуль schema-validation**, а не отдельный CI
gate: единственную orchestration entrypoint владеет `RM-GOV-004` и вызывает отсюда `validate()`.

## 3. Модель данных

Корень: `schema_version`, `base`, `stages`, `gates`, `tasks`, опционально `owner_decisions` и
`maturity`.

**Задача (`tasks[]`)** — обязательны `id`, `kind`, `stage`, `title`, `dependencies`,
`acceptance`, `decision_status`, `delivery_status`. Опционально: `alias`, `business_outcome`,
`priority`, `wave`, `owner_gate`, `feature_ids`, `evidence_refs`, `notes`.

- `acceptance[]` — не строки, а объекты `{check, verified_by, ref}`, где
  `verified_by ∈ {command, ci_job, behavioral, ui_smoke, artifact, owner, human}`. Это делает
  требование «каждая приёмка называет команду, CI job, proof или artifact» **проверяемым**, а не
  декларативным.
- **Обязательный конкретный `ref` для machine-verifiable приёмок.** Если
  `verified_by ∈ {command, ci_job, behavioral, ui_smoke, artifact}` — то есть приёмку может
  выполнить или открыть третья сторона, — поле `ref` **обязательно** (JSON Schema `if/then`,
  `minLength: 3`) и не должно быть заглушкой (`TBD`, `TODO`, `n/a`, `—`, «позже», «уточнить»
  и т.п. — семантическое правило `VAGUE-REF`). Для `owner` и `human` `ref` не требуется: это
  суждение, а не исполняемая проверка. Без этого правила «`verified_by: command`» без команды
  выглядел бы доказательством, ничего не доказывая.
- `owner_gate` — `{required: true, reason}`, где `reason` из закрытого списка:
  `canon_change`, `migration_application`, `device_contract`, `protected_boundary`,
  `deployment`, `merge`, `release`, `scope_decision`.
- `evidence_refs[]` — `{kind, ref, status, observed_at, environment}`; `status ∈
  {verified, disputed, superseded}`. Типы доказательств различены по требованию RG-3:
  `identity`, `readiness`, `stand_safe_smoke`, `browser_targeted`, `full_journey`,
  `operator_walkthrough` и др. — один тип не подменяет другой. `environment` несёт identity
  окружения (имя, SHA, bundle, `schema_head`).

**Зрелость (`maturity[]`)** — восьмиступенчатая лестница по `feature_id`, отдельно от registry:
`implemented → automated_verified → ci_enforced → stand_deployed → stand_verified →
walkthrough_ok → pilot_ready → production_ready`. Поле `proof_granularity`
(`dedicated | shared:<smoke-id>`) обязательно с уровня `ci_enforced` — это закрывает
наблюдение N3 (43 reachable UI доказываются 38 смоуками; пять commerce-функций делят один).

## 4. Три расхождения с ранним предложением — решены в пользу утверждённой очереди

Схема обязана выражать **фактические 42 задачи**, а не абстракцию из §4.2 governance-аудита.

| # | Раннее предложение (§4.2/§4.3) | Утверждённая очередь | Решение в схеме |
|---|---|---|---|
| 1 | префиксы `RM-BIZ/RM-TECH/RM-GOV` (3) | фактически **8**: GOV, ENV, STAB, UX, BIZ, TECH, PILOT, OPS | шаблон `RM-(GOV\|ENV\|STAB\|UX\|BIZ\|TECH\|PILOT\|OPS)-\d{3}[AB]?`; суффикс `[AB]` нужен для `RM-TECH-207A/207B` |
| 2 | `wave: W0…W5` | этапы `G, E0, S, U, BT, POPS` + `Gate G/S/U` | `stage` — авторитет последовательности; `wave` оставлен **опциональной** ссылкой на продуктовые волны `roadmap.md`, чтобы не потерять связь и не дублировать |
| 3 | — | у `RM-UX-*` есть legacy-метки `A3, A2, A4, A6, A1b, A5, A7` | опциональное поле `alias` |

## 5. Находка, вскрытая при проектировании 🟡

**Таксономия `kind` в утверждённом кандидате неполна на одно значение.**

- §2 (строка 41) объявляет: `kind: governance|design|implementation|human|external` — **пять**.
- §8 (строка 129) присваивает `RM-PILOT-002` вид **`external-plan`** — шестой.

Проверено подсчётом по документу: `design 5 · governance 10 · implementation 23 · human 1 ·
external-plan 1 · external 2` = 42.

Схема принимает **все шесть** фактически использованных значений — иначе `RM-GOV-002` не сможет
создать валидный initial YAML, содержащий утверждённые 42 задачи. Это выбор в пользу
исполнимости; **владельцу и Codex предлагается либо подтвердить `external-plan` как штатный вид,
либо переназначить `RM-PILOT-002`**. Молча расширять таксономию я не считаю правильным, поэтому
фиксирую расхождение здесь.

## 6. Семантические правила валидатора

JSON Schema их выразить не может; они реализованы в `check-roadmap-schema.py`:

| Правило | Находка |
|---|---|
| уникальность `id` | `DUPLICATE-ID` |
| все зависимости существуют (задача или gate) | `DANGLING-DEP` |
| граф зависимостей ацикличен | `CYCLE` |
| задача не зависит от задачи более позднего этапа | `STAGE-ORDER` |
| `delivery_status: done` требует ≥1 `evidence_ref` со `status: verified` | `OVERCLAIM` |
| приёмка с `verified_by: owner` требует объявленного `owner_gate` | `MISSING-OWNER-GATE` |
| уровень ≥ `ci_enforced` требует `proof_granularity` | `PROOF-GRANULARITY` |
| `feature_id` существует в `feature-registry.yaml` | `UNKNOWN-FEATURE` |
| machine-verifiable приёмка имеет непустой `ref` | `MISSING-REF` (+ `SCHEMA` от `if/then`) |
| `ref` не является заглушкой и не короче 3 символов | `VAGUE-REF` |

`OVERCLAIM` — механическая реализация анти-overclaim условия из B-1: без неё требование
«`delivery_status=done` запрещён без достаточных `evidence_refs`» осталось бы словами.
`STAGE-ORDER` механически защищает утверждённый порядок `G → E0 → S → U → branches`.
`MISSING-REF`/`VAGUE-REF` закрывают тот же класс на уровне приёмок: правило проверяется дважды —
структурно (`if/then` в схеме) и семантически (заглушки), поэтому «команда без команды» не
пройдёт ни одним путём.

**Правило сразу поймало два пробела в моей собственной фикстуре** — `RM-STAB-001`
(`verified_by: command`) и `RM-STAB-002` (`verified_by: behavioral`) были записаны без `ref`.
Оба заменены на существующие артефакты (`tests/behavioral/test_commerce_rls.py`,
`tests/behavioral/test_adr018_multitenancy_rls.py` — наличие проверено). Правило, которое не
находит ничего в день внедрения, обычно ничего и не проверяет.

## 7. Доказательство (выполнено, не заявлено)

```
$ python3 scripts/ci/check-roadmap-schema.py --self-test
[roadmap-schema self-test] fixture clean: scripts/ci/fixtures/roadmap.schema.example.yaml
    tamper: dangling dependency                          -> CAUGHT (DANGLING-DEP)
    tamper: dependency cycle                             -> CAUGHT (CYCLE)
    tamper: done without verified evidence               -> CAUGHT (OVERCLAIM)
    tamper: id outside approved prefixes                 -> CAUGHT (SCHEMA)
    tamper: kind outside taxonomy                        -> CAUGHT (SCHEMA)
    tamper: ci_enforced without proof_granularity        -> CAUGHT (PROOF-GRANULARITY)
    tamper: owner acceptance without owner_gate          -> CAUGHT (MISSING-OWNER-GATE)
    tamper: stage depends on later stage                 -> CAUGHT (STAGE-ORDER)
    tamper: percentage field smuggled in                 -> CAUGHT (SCHEMA)
    tamper: machine-verifiable acceptance without ref    -> CAUGHT (SCHEMA)
    tamper: machine-verifiable acceptance with placeholder ref -> CAUGHT (VAGUE-REF)

[roadmap-schema] self-test PASS
```

Фикстура чистая, **все одиннадцать tamper пойманы**. Зелёный без красного ничего не доказывает,
поэтому tamper-матрица — часть приёмки, а не приложение к ней.

До `RM-GOV-002` вызов без аргументов честно падает: `MISSING-FILE`, exit 1 — файла
`docs/product/roadmap.yaml` ещё нет. Это ожидаемо; в CI модуль включает `RM-GOV-004`, который
идёт после `RM-GOV-002`.

## 8. Что остаётся следующим задачам

- `RM-GOV-002` — создаёт initial `docs/product/roadmap.yaml` по этой схеме и раскладывает
  93 technical items / 13 SECTION / 57 business rows.
- `RM-GOV-003` — генератор `YAML + registry + evidence → roadmap.md + XLSX + метрики`.
- `RM-GOV-004` — единственная CI orchestration entrypoint; подключает `validate()` отсюда.
- `RM-GOV-006` — правило факта и требования; `RM-GOV-005` — canonical cutover.

## 9. Запрошенное решение владельца

1. **Утвердить модель** — условие приёмки `RM-GOV-001`.
2. **Решить по `external-plan`** (§5): подтвердить как штатный вид либо переназначить
   `RM-PILOT-002`.
3. Подтвердить размещение схемы в `docs/product/` (§2), если есть иное предпочтение.

Ни один файл канона, roadmap, registry, `PROJECT_STATE.md` и стенд не изменялись; коммит и push
не выполнялись.

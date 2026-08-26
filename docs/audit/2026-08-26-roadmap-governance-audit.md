# Аудит технической и бизнес-дорожной карты и предложение единого формата

> ## ⚠️ НЕ КАНОН — аудит и рекомендация владельцу
>
> | | |
> |---|---|
> | **Тип** | Независимый roadmap/governance audit |
> | **Снято на** | `develop @ 2b935bb`; live stand `stand-27dc397` |
> | **Дата** | 2026-08-26 |
> | **Автор** | Codex, архитектор/ревьюер |
> | **Предмет** | Техническая roadmap, бизнес-roadmap, maturity, стенд, формат и ответственность |
> | **Статус** | Ожидает независимой сверки Claude Code и решения владельца |
> | **Изменения продукта/канона** | Нет |
> | **Открытых находок** | 8: 3 🔴 · 4 🟡 · 1 🟢 |
> | **Открытых решений** | 5 |
> | **Отменён** | — |

## 1. Owner instruction и граница работы

Новая инструкция владельца: до выравнивания проекта сначала провести совместный аудит
технической и бизнес-дорожной карты, утвердить единый формат и ответственность за результат,
затем разложить утверждённую карту на задачи и согласовать их между Codex и Claude. Реализация
и продолжение `PORTAL-UX-POLISH-001A3` до этого не начинаются.

Этот документ не меняет `PROJECT_STATE.md`, roadmap, registry, код или стенд. Он фиксирует
проверяемые расхождения и предлагает модель для решения владельца.

## 2. Что проверено

- Git: local `develop` и `origin/develop` совпадают — `2b935bb980028a3e67db51718377836bb6242da9`.
- `PROJECT_STATE.md`: только текущий checkpoint, Next и записи о live stand/A1a.
- `roadmap.md`: определения зрелости, technical/business views, UX slicing, волны, решения
  владельца и метрики; файл целиком не перечитывался линейно.
- `pre-pilot-journey-plan.md` и `roadmap-maintenance-rules.md`: актуальные декларации и правила.
- XLSX: программно просмотрены все ячейки обоих листов — 107×5 и 59×11, формулы, статусы,
  narrative-поля и ссылки на окружение.
- `feature-registry.yaml`: 58 features, 53 reachable, 5 blocked; 39 admin, 5 advertiser,
  1 public, 13 service.
- Guard: `python3 scripts/roadmap-consistency-check.py --strict` → 0 findings.
- Live stand: admin `:3000` и advertiser `:3001` → HTTP 200; `/version` →
  `stand-27dc397`, SHA `27dc39707c5c56cdfdcc4250d5aa875d3789c8dc`, schema `036`, staging;
  `/health/live` → OK; `/health/ready` → database OK, DB role non-superuser/NOBYPASSRLS;
  оба `build-info.json` совпадают с API identity.

## 3. Находки

### R1 · Нет единственного источника roadmap и однозначного приоритета 🔴

Одновременно действуют несовместимые декларации:

- `AGENTS.md` индексирует `pre-pilot-journey-plan.md` как порядок волн, а XLSX — как
  производную бизнес-карту;
- `pre-pilot-journey-plan.md` объявляет себя историческим и делегирует актуальный порядок
  `roadmap.md`;
- `roadmap.md` объявляет себя каноническим, но отсутствует в Sources of Truth;
- `roadmap-maintenance-rules.md` требует «один файл: XLSX» и запрещает альтернативные форматы.

Следствие: агент может формально обосновать три разных источника порядка. До решения владельца
никакой из них нельзя безопасно использовать для task decomposition.

### R2 · Бизнес-XLSX проходит guard при фактически устаревшем содержимом 🔴

Guard возвращает 0, однако в бизнес-листе одновременно записано:

- `self.campaign_view` «без UI-smoke», хотя registry считает его reachable;
- UI `user.create_advertiser` и `user.reset_password` «нет/отсутствует», хотя их smoke зелёные;
- self-service создание/редактирование кампаний названо доступным, но
  `self.campaign_create` blocked/deferred;
- inventory rules UI назван неготовым, хотя `inventory.rule_create` reachable;
- в строке device health указано «нет операционного интерфейса», а в соседних колонках тот же
  UI и journey отмечены зелёными;
- указан старый preview URL `192.168.110.77`, тогда как текущий live stand — `192.168.110.81`.

В книге **нет ни одной формулы**. Колонка «Итог», объявленная производной, фактически заполнена
вручную. Значит green guard доказывает только узкую согласованность journey-token'ов, но не
правду бизнес-описания или результата.

### R3 · Технический лист смешивает roadmap, инвентарь и исторический журнал 🔴

Из 93 технических строк 21 нарушает собственный словарь статусов: в поле статуса записаны
S-номера и длинные результаты. Домены продублированы между историческими секциями:
observability, backup/DR, reporting/export, inventory, LDAPS и ClickHouse встречаются повторно.

Примеры логических конфликтов:

- ADR-018 всё ещё «в работе», хотя ADR принят и реализован;
- Production Observability и DR/Backups помечены «готово», но production остаётся NO-GO;
- готовые строки содержат незакрытые «следующие шаги», иногда буквально будущую реализацию;
- Device fleet health в ТЗ-покрытии «не начато», хотя `device.health_view` reachable;
- Channel Orchestrator «требует решения», хотя ADR-019 уже фиксирует deferred;
- строки S-086/S-087/S-088 используют поле статуса как отчёт о выполнении.

Лист непригоден как исполняемый backlog: у большинства строк нет стабильного roadmap ID,
структурных dependencies, acceptance gate и ответственного за решение.

### R4 · Уровни зрелости полезны, но доказательства смешаны 🟡

Различение `reachable → CI-enforced → stand-verified → walkthrough → pilot → production`
архитектурно правильное. Текущая реализация смешивает разные факты:

- «развёрнут» часто означает лишь наличие кода в общем bundle, а не прохождение journey;
- stand-verified хранится вручную в Markdown без timestamp и ссылки на proof artifact;
- 43 UI-journey объявлены CI-enforced, хотя аудит C1 выявил smoke, нарушающие Done Gate;
- stand-safe smoke, визуальная проверка и полный бизнес-journey не разделены типами proof.

Для каждой maturity-ступени нужны отдельные структурные evidence-поля; повышение следующего
уровня не должно следовать автоматически из предыдущего.

### R5 · Публичные проценты частично невоспроизводимы и один подписан неверно 🟡

- `53/58` — reachable всех features, включая 10 service, а не «доля функций, достижимых в UI»;
- business journey completeness `~60%` и pilot readiness `~25%` не имеют вычислимой формулы;
- browser-verified `4/43` не отражает новые виды stand-proof и не содержит даты/stand SHA;
- единицы измерения смешивают feature, role journey, инфраструктуру и субъективную зрелость.

До появления формул допустимы только точные counts по определённому denominator или
качественный статус без процента.

### R6 · Правила описывают действия, но не назначают ответственность за результат 🟡

Не определено, кто:

- формулирует бизнес-результат и приоритет;
- обновляет implementation evidence после задачи;
- принимает архитектурный результат;
- подтверждает stand verification;
- имеет право повысить pilot/production readiness.

В историческом плане осталась фраза «одна задача Hermes за раз», хотя Hermes retired.
Без RACI автор реализации может одновременно записать и принять собственный результат.

### R7 · Roadmap guard проверяет слишком узкую проекцию 🟡

Скрипт читает business sheet, registry, имена smoke-функций и CI subset. Он не проверяет:

- technical sheet и словарь его статусов;
- `roadmap.md`, `PROJECT_STATE.md`, maintenance rules и единственность канона;
- нормативность `user-journeys.md` и семантику UI-smoke;
- narrative-поля XLSX, формулы/derived result и актуальный stand identity;
- dependencies, owner decisions и maturity transitions.

Нулевой exit code поэтому не означает согласованную дорожную карту.

### R8 · Live stand существует и исправен, но roadmap адресует его непоследовательно 🟢

Стенд подтверждён live на `192.168.110.81` и совпадает с checkpoint: `stand-27dc397`, schema
`036`. Это обязательный слой доказательств, а не забытая инфраструктура. Проблема не в стенде,
а в модели roadmap: старый preview `.77`, текущий stand `.81`, bundle deployment, safe smoke,
browser proof и human walkthrough представлены несогласованными текстовыми пометками.

## 4. Предлагаемый единый формат

### 4.1 Canon и проекции

После одобрения владельца ввести **один машинно-читаемый sequencing SSOT**:
`docs/product/roadmap.yaml`.

Он хранит только приоритет, волны, зависимости, решения и work items. Он **не дублирует**:

- feature status — остаётся в `feature-registry.yaml`;
- journey specification — остаётся в `user-journeys.md`;
- текущий workstream/checkpoint — остаётся в `PROJECT_STATE.md`;
- архитектуру — ADR;
- фактическое поведение — код, тесты и CI.

`roadmap.md` и XLSX становятся **генерируемыми read-only проекциями** одного YAML + registry +
evidence. Ручное редактирование generated-файлов запрещается. Старые maintenance rules после
миграции помечаются superseded.

### 4.2 Единица планирования

Каждый элемент имеет стабильный ID:

- `RM-BIZ-###` — бизнес-результат;
- `RM-TECH-###` — технический enabler/risk reduction;
- `RM-GOV-###` — governance/truth work.

Обязательные поля:

```yaml
id: RM-BIZ-001
kind: business | technical | governance
title: ...
business_outcome: ...
feature_ids: []
workstream_ids: []
wave: W0 | W1 | W2 | W3 | W4 | W5
priority: P0 | P1 | P2 | P3
decision_status: proposed | approved | rejected
delivery_status: planned | ready | in_progress | verification | blocked | deferred | done
dependencies: []
acceptance: []
owner_decisions: []
evidence_refs: []
```

`delivery_status=done` не вводится вручную по ощущению: generator допускает его только при
закрытых acceptance gates и валидных evidence refs.

### 4.3 Отдельная maturity-модель

Для feature/business outcome хранятся независимые ступени:

1. `implemented` — код существует;
2. `automated_verified` — целевые unit/behavioral/UI tests зелёные;
3. `ci_enforced` — proof входит в обязательный gate;
4. `stand_deployed` — exact bundle SHA развёрнут;
5. `stand_verified` — указаны proof type, timestamp, environment identity и результат;
6. `walkthrough_ok` — подтверждает только человек;
7. `pilot_ready` — отдельное решение владельца по pilot gate;
8. `production_ready` — отдельное решение владельца по production gate.

Proof types на стенде различаются: `identity`, `readiness`, `stand-safe-smoke`, `browser-targeted`,
`full-journey`, `operator-walkthrough`. Один тип не подменяет другой.

## 5. Кто заполняет результат

| Данные | Кто формулирует/заполняет | Кто принимает |
|---|---|---|
| Business outcome, priority, wave, scope | владелец | владелец |
| Architecture/acceptance mini-design | Codex предлагает | владелец утверждает |
| Implementation, tests, SHA, CI, stand evidence | Claude Code после фактического прогона | Codex независимо проверяет |
| Canonical status/result в репозитории | Claude Code после ACCEPT ревью | владелец для business/pilot/prod gates |
| Roadmap derived fields и counts | generator/guard | CI |
| Operator walkthrough | человек-владелец/аудитор | владелец |
| Release/deploy/merge | только по явному разрешению владельца | владелец |

Codex не реализует и не повышает canonical status. Claude не принимает собственную работу:
он записывает candidate result с доказательствами, Codex выдаёт `ACCEPT`/`REJECT`, после чего
Claude синхронизирует канон. Generated Markdown/XLSX не заполняет вручную ни один агент.

## 6. Решения владельца до task breakdown

1. **RG-1:** утвердить `roadmap.yaml` sequencing SSOT и generated Markdown/XLSX.
2. **RG-2:** утвердить RACI из §5.
3. **RG-3:** утвердить maturity-модель и запрет процентов без формулы.
4. **RG-4:** подтвердить паузу A3 до roadmap reconcile и согласованного task breakdown.
5. **RG-5:** решить, является ли `stand-27dc397` текущим baseline для планирования; pilot и
   production при этом остаются отдельными и неготовыми.

## 7. Что намеренно не сделано

- roadmap, registry, PROJECT_STATE и код не изменялись;
- task breakdown ещё не создан: он должен следовать только из утверждённого формата;
- stand не мутировался — выполнены только публичные read-only проверки;
- Claude ещё не подтвердил этот аудит независимо.

Следующий шаг: Claude воспроизводит счётчики и возражает/соглашается по R1–R8. После единой
редакции владелец утверждает RG-1…RG-5. Только затем Codex проектирует task breakdown, Claude
проверяет исполнимость, владелец утверждает порядок, и начинается выравнивание проекта.

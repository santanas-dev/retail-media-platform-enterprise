# Roadmap — сгенерированная проекция

> **СГЕНЕРИРОВАНО. НЕ РЕДАКТИРОВАТЬ РУКАМИ.**
> Правки вносятся в SSOT-входы, затем проекция перегенерируется.
>
> | | |
> |---|---|
> | Генератор | `scripts/ci/roadmap-generate.py` (RM-GOV-003) |
> | Входы | `docs/product/roadmap.yaml`, `docs/product/feature-registry.yaml`, `tests/ui-smoke/ci-subset.txt` |
> | Base SHA | `2b935bb980028a3e67db51718377836bb6242da9` |
> | Перегенерация | `python3 scripts/ci/roadmap-generate.py` |
> | Проверка дрейфа | `python3 scripts/ci/roadmap-generate.py --check-clean-diff` |
> | Статус | действующее представление roadmap (cutover `RM-GOV-005` выполнен) |

Эти файлы — единственное действующее представление roadmap. Вытесненные `roadmap.md` и `roadmap-s020-2026-07-10.xlsx` архивированы в `docs/product/history/` (canonical cutover RM-GOV-005).

## Метрики (посчитаны генератором)

### Очередь

| Метрика | Значение |
|---|---|
| Всего задач | 107 |
| По этапам | A=14, C=11, CH=9, CORE=22, E0=3, G=11, POPS=8, S=18, U=11 |
| По типу | design=12, external=2, external-plan=2, governance=20, human=1, implementation=70 |
| По статусу поставки | blocked=16, done=9, planned=79, verification=3 |
| Требуют owner gate | 30 |
| С verified evidence | 12 |
| Максимальная глубина зависимостей | 9 |
| Гейты | Gate-G, Gate-S, Gate-U, Gate-C |
| Решения владельца | 38 |

### Функции (из registry — функциональный SSOT)

| Метрика | Значение |
|---|---|
| Всего функций | 73 |
| reachable · blocked | 52 · 21 |
| По фронтенду | admin-web=49, advertiser-web=5, public=1, service=18 |
| UI-функций (не service) | 55 |
| Закреплено в CI-subset | 43 |
| blocked с пустым `gap` | 0 |

### Зрелость

Уровни зрелости **не заявлено** ни для одной функции.

Причина: roadmap.yaml не содержит блока `maturity`; уровни выше registry не выводимы из входов и не домысливаются генератором.

Генератор не выводит `stand_verified`, `walkthrough_ok`, `pilot_ready` и `production_ready` из registry: registry доказывает достижимость, а не зрелость. Пока владелец не заполнит блок `maturity` в `roadmap.yaml`, проекция говорит «не заявлено», а не «0» — это разные утверждения.

### Сверки между входами

| Сверка | Результат |
|---|---|
| blocked в roadmap.yaml, но не в registry | — |
| blocked в registry, но без `unblocked_by` | — |
| reachable без найденного smoke | — |

## Решения владельца

| ID | Статус | Дата | DEC alias | Формулировка | Источники |
|---|---|---|---|---|---|
| `OD-001` | approved | 2026-08-26 | — | Код/тесты описывают фактическое поведение; ТЗ/ADR — требуемое. Расхождение является дефектом до явного ADR. | — |
| `OD-002` | approved | 2026-08-26 | DEC-003 | Ed25519 обязателен для device pilot/production. HMAC допустим только для dev и control-plane stand. | tz-v2.6 §29 DEC-003; RM-STAB-010 (implementation evidence) |
| `OD-003` | approved | 2026-08-26 | — | Retailer scope — первоклассная граница; bypass только system_admin и security_admin. | — |
| `OD-004` | approved | 2026-08-26 | — | UI-smoke отделён от ordinary pytest и является blocking gate для develop, release и повышения journey до reachable. | — |
| `OD-005` | approved | 2026-08-26 | DEC-011 | self.campaign_create исключён из ближайшего control-plane pilot; первый pilot managed-first. | tz-v2.6 §29 DEC-011; OD-013 (post-pilot self-service - открыто) |
| `OD-006` | approved | 2026-08-26 | — | При renewal занятые seats старого grant атомарно закрываются и продолжаются под новым grant. | — |
| `OD-007` | approved | 2026-08-26 | — | Активный baseline — .81 / stand-27dc397; .77 называется только unreachable at check time. | — |
| `OD-008` | open | — | DEC-004 | MFA обязателен до production; согласование NATS с ИТ/ops — до pilot deployment. | ADR-002 (NATS JetStream baseline); tz-v2.6 §29 DEC-004 |
| `OD-009` | open | — | DEC-006, DEC-007 | Объём безопасности и соответствия до production — SIEM/Wazuh-экспорт, минимизация PII, доступ администратора только через VPN, retention и партиционирование данных. Вопрос - расширяется ли scope RM-OPS-001 этими четырьмя пунктами или каждый становится отдельной задачей. Ни один сейчас не назван ни одной из 42 задач. | user-journeys.md §5.1 2026-07-18 (SLA/retention defaults приняты); tz-v2.6 §29 DEC-006/DEC-007 |
| `OD-010` | open | — | DEC-008 | Безопасная выкатка — staged rollout с rollback и feature flags. Вопрос - это предусловие пилота или production. От ответа зависит, входят ли они в RM-PILOT-002 preflight или только в RM-OPS-001. | tz-v2.6 §29 DEC-008, §22.7/22.9 |
| `OD-011` | open | — | DEC-009 | Нагрузочные профили и критерии производительности на 40K устройств. Вопрос - измеряется ли это до пилота как вход в SLO (RM-TECH-205) и в триггер ClickHouse (RM-TECH-209), или откладывается до production. | tz-v2.6 §29 DEC-009, §22.15; RM-TECH-205 |
| `OD-012` | open | — | — | Часовые пояса, календарь и праздничное расписание показов. Это корректность доставки, а не операционный вопрос - вопрос владельцу - входит ли в scope пилота. | — |
| `OD-013` | open | — | — | Self-service онбординг рекламодателя - сброс пароля самим пользователем и приглашения. Админский сброс и приглашение уже reachable с зелёными смоуками; self-service отсутствует. Вопрос согласуется с OD-005 (managed-first) - нужен ли self-service в первом пилоте. | — |
| `OD-014` | open | — | DEC-027 | A/B lift и attribution - материал ветки v2.6, зависит от модели арендатора (ADR-018). Вопрос - фиксируется ли как отложенное решением, по образцу ADR-019 для Channel Orchestrator, или остаётся неопределённым. | ADR-018; tz-v2.6 §29 DEC-027, REQ-V26-002/010 |
| `OD-015` | open | — | — | Операционный центр здоровья устройств. Функция device.health_view reachable и закреплена в CI; вопрос - достаточно ли этого представления для пилота или требуется отдельный операционный центр как самостоятельный объём работ. | — |
| `OD-016` | approved | 2026-08-26 | — | 192.168.110.77 выводится из эксплуатации решением владельца 2026-08-26. Уточняет OD-007 в части .77 - формулировка «unreachable at check time» была наблюдением до решения; теперь диспозиция decommissioned. Часть OD-007 про активный baseline .81/stand-27dc397 остаётся в силе без изменений. | — |
| `OD-017` | approved | 2026-08-28 | — | Содержание ТЗ v2.6 r421 принято владельцем 2026-08-28 — REVIEW → ACCEPTED. SHA-256 принятой редакции r421 = 59478746c1368e3db556ec805b5345e829b00113cf94b4b556294bbce0fa58e6. Не равно APPROVED - статус документа остаётся DRAFT до артефактов Дополнения AG (traceability, role/scope, routes/journeys, OpenAPI/events, ERD/data, channel matrix, NFR/load, retention/legal, DEV manifest, roadmap views) и закрытия применимых gates. Cutover пути по AQ.1 №3 выполняет Claude - живой драфт docs/product/requirements/tz-v2.6-draft.md (r422 = r421 + пути/sidecar, нормативные разделы без изменений); старый путь docs/audit/2026-08-26-tz-v2.6-design-draft.md остаётся immutable redirect. | — |
| `OD-018` | approved | 2026-08-28 | DEC-022 | DEC-022 - исключения из принципа аддитивности v2.6 - только §3.1 delivery/priority engine (competitive separation). Любое другое изменение существующих Campaign/Delivery/PoP контрактов в рамках v2.6 запрещено без нового решения владельца. | tz-v2.6 §29 DEC-022; v2.6 addendum §0.3/§8.3 |
| `OD-019` | approved | 2026-08-28 | DEC-024 | DEC-024 - дубликат PoP внутри batch - валидный batch отвечает HTTP 200; дублирующее событие помечается per-event `duplicate` с machine error code 409 в теле и не учитывается повторно. ADR-017 получает amendment, behavioral-тест закрепляет семантику; реализация - отдельной задачей task breakdown. | ADR-017 (amendment требуется); tz-v2.6 §29 DEC-024 |
| `OD-020` | approved | 2026-08-28 | DEC-026 | DEC-026 - отмена коммерческого заказа - переход draft → cancelled разрешён; confirmed закрывается только reversal/compensation workflow, прямая отмена confirmed запрещена. _ORDER_TRANSITIONS и тесты приводятся отдельной задачей task breakdown. | tz-v2.6 §29 DEC-026; packages/domain _ORDER_TRANSITIONS (факт) |
| `OD-021` | open | — | DEC-001 | Каналы первой production-очереди и владелец каждого не выбраны. Вопрос владельцу - перечень каналов, владелец, SLA и бюджет каждого. До решения единственный реальный канал - KSO (ADR-019), хуки под несуществующие каналы запрещены. | ADR-019; tz-v2.6 §23/§25, §29 DEC-001 |
| `OD-022` | approved | 2026-07-20 | DEC-002 | Channel Orchestrator и Adapter Layer вводятся только после появления второго реального канала; mock-first до этого триггера запрещён. Ратифицировано ADR-019. | ADR-019; user-journeys.md §5.1 (§24 - ПРАГМАТИКА, 2026-07-18) |
| `OD-023` | open | — | DEC-005 | Master-система цен/SKU и владелец reconciliation не зафиксированы. Вопрос владельцу - имя/роль владельца master-данных цен/SKU. До решения ESL/price-checker, attribution/audience и dynamic creative остаются blocked. | tz-v2.6 §16.2, §23.7, §29 DEC-005; AQ.1 №5 (master-data adapter - отсутствующий prerequisite) |
| `OD-024` | open | — | DEC-010 | Пилотная шкала КСО → 10 → 100 → 500 → сеть принята 2026-07-18. Открыты измеримые exit criteria каждого перехода - вопрос владельцу, какие метрики и пороги закрывают ступень. | user-journeys.md §5.1 2026-07-18 (шкала КСО → 10 → 100 → 500 → сеть принята); tz-v2.6 §29 DEC-010 |
| `OD-025` | open | — | DEC-012 | RTO/RPO, HA target и владелец DR не определены. Вопрос владельцу - целевые RTO/RPO для production, кто владеет DR и что является go/no-go критерием. | tz-v2.6 §5/§17, §29 DEC-012 |
| `OD-026` | open | — | DEC-013 | Advertiser/BI API access не решён. Вопрос владельцу - scoped API keys с rotation/revoke/audit в первой очереди либо явное исключение из неё. | tz-v2.6 §12/§16, REQ-INT-003, §29 DEC-013 |
| `OD-027` | open | — | DEC-014 | Внешний monitoring-dashboard - read-only наблюдатель без права менять файлы, статусы, задачи и owner decisions. Требуется решение владельца с датой - scope, freshness/correlation contract, оформление расхождений (MON-DIVERGENCE) и запрет записи статусов. | tz-v2.6 Дополнение R, REQ-ARCH-002, §29 DEC-014 |
| `OD-028` | open | — | DEC-015 | Production deployment topology не выбрана - Docker Swarm или approved equivalent. Вопрос владельцу - топология, владелец, критерии HA/rollback, стоимость эксплуатации и migration evidence. | tz-v2.6 REQ-ARCH-004, §29 DEC-015 |
| `OD-029` | open | — | DEC-016 | Device PKI/mTLS activation и срок отказа от token-only flow не решены. Вопрос владельцу/ИБ - PKI/CRL/OCSP, proxy enforcement, migration и rollback. | tz-v2.6 REQ-SEC-003, §29 DEC-016; OD-002 (Ed25519 - принято) |
| `OD-030` | open | — | DEC-017 | Полный ЭДО/биллинг по умолчанию вне первой очереди. Требуется owner/legal решение - границы сущностей и trigger возврата в scope. | tz-v2.6 §2.2, §22.12, §29 DEC-017 |
| `OD-031` | open | — | DEC-018 | DSP/SSP-закупка по умолчанию вне первой очереди. Требуется product/legal решение, ручное согласование и review date. | tz-v2.6 §2.2, §29 DEC-018 |
| `OD-032` | open | — | DEC-019 | Персонализация покупателя по умолчанию вне первой очереди. Требуется privacy/legal решение - lawful purpose и review trigger. | tz-v2.6 §2.2, §14, §29 DEC-019 |
| `OD-033` | open | — | DEC-020 | Звук в торговом зале по умолчанию вне первой очереди. Требуется business/operations safety решение и review date. | tz-v2.6 §2.2, §9, §29 DEC-020 |
| `OD-034` | approved | 2026-07-18 | DEC-021 | Произвольный HTML/JS-контент запрещён в первой очереди - только изображения/видео. Активация не ранее отдельного решения и только через sandbox/CSP с согласованием ИБ (security gate). | user-journeys.md §5.1 2026-07-18 (HTML5 запрещён на старте); tz-v2.6 §2.2, §7, §29 DEC-021 |
| `OD-035` | approved | — | DEC-023 | Продуктовая модель ролей принята решением Q2 (user-journeys.md §3). Отсутствующие bundles campaign_manager/moderator/approver/ops_operator создаются аддитивно, alias operator сохраняется на период миграции - это implementation, не новое решение. | user-journeys.md §3 (продуктовое решение Q2 - матрица ролей); tz-v2.6 REQ-UX-001, §29 DEC-023; RM-STAB-003/004/007 (seed 5 из 7 ролей - implementation debt) |
| `OD-036` | approved | 2026-07-05 | DEC-025 | Жизненный цикл кампании - полный accepted lifecycle ADR-015, включая scheduled, resume, revise и archive. Текущий код не соответствует и требует implementation task; иной вариант - только amendment ADR-015. | ADR-015 (Accepted 2026-07-05); tz-v2.6 §29 DEC-025 |
| `OD-037` | approved | 2026-08-28 | — | Порядок стадий roadmap утверждён владельцем 2026-08-28 - G → E0 → S → C → CORE → U → CH → A → POPS (Governance → Environment → Stabilization → Contracts → Core → Portal → Channels → Analytics/Scale → Production). Стадия BT расформирована - её 14 задач переезжают по фазам с сохранением ID и истории; введён Gate-C; у шести задач Core/Contracts зависимость Gate-U заменена на Gate-S, потому что Portal идёт после Core. Кандидат - docs/audit/2026-08-28-claude-a3-task-breakdown-candidate.md. | docs/audit/2026-08-28-claude-a3-task-breakdown-candidate.md §1/§3; docs/audit/2026-08-28-codex-review-claude-a3.md |
| `OD-038` | approved | 2026-08-28 | — | Конфликт канона разрешён владельцем 2026-08-28 - feature-registry device.onboard переводится reachable → blocked с unblocked_by RM-TECH-210, потому что в production-path устройство получает 403 INVALID_CODE (RLS-CONTEXT-DEVICE-001, доказано прямым запросом к БД); ранее reachable держался под административной маской behavioral-набора. Smoke сохраняется; статус возвращается к reachable только по behavioral evidence под runtime-ролью на PostgreSQL. | tz-v2.6-draft §11; PROJECT_STATE RLS-CONTEXT-DEVICE-001; RM-TECH-210 |

## Гейты

| Гейт | Закрывает этап | Утверждает | Условия |
|---|---|---|---|
| `Gate-C` | C | owner | OpenAPI + event/manifest JSON Schema и ERD/data dictionary приняты владельцем как артефакты Дополнения AG; contract tests зелёные в CI |
| `Gate-G` | G | owner | Codex проверяет generator и tamper matrix; владелец утверждает canonical cutover |
| `Gate-S` | S | codex | новые counts и evidence воспроизводимы |
| `Gate-U` | U | human | человек проходит walkthrough на exact stand bundle |

## Очередь по этапам

### G — Единая система roadmap (11) · закрывается `Gate-G`

| ID | Kind | Задача | Зависит от | Глубина | Поставка | Owner gate | Приёмка | Evidence |
|---|---|---|---|---|---|---|---|---|
| `RM-GOV-001` | design | Schema/mini-design `roadmap.yaml` | — | 0 | done | scope_decision | schema validator [command: `python3 scripts/ci/check-roadmap-schema.py --self-test`] | verified · command · `python3 scripts/ci/check-roadmap-schema.py --self-test`; verified · artifact · `docs/architecture/rm-gov-001-roadmap-yaml-design-gate.md` |
| `RM-GOV-002` | governance | Reconciliation/migration manifest | `RM-GOV-001` | 1 | done | — | disposition для 93 technical items, 13 SECTION и 57 business rows [command: `python3 scripts/ci/check-roadmap-schema.py --file docs/product/roadmap.yaml`] | verified · command · `python3 scripts/ci/roadmap-migration-counts.py`; verified · artifact · `docs/product/roadmap-migration-manifest.yaml`; verified · command · `python3 scripts/ci/check-roadmap-schema.py --file docs/product/roadmap.yaml` |
| `RM-GOV-003` | implementation | Односторонний generator YAML + registry + evidence → Markdown/XLSX/metrics | `RM-GOV-001`, `RM-GOV-002` | 2 | done | — | deterministic generation [command: `python3 scripts/ci/roadmap-generate.py --check-clean-diff`] | verified · command · `python3 scripts/ci/roadmap-generate.py --check-clean-diff`; verified · command · `python3 scripts/ci/roadmap-generate.py --self-test`; verified · artifact · `docs/architecture/rm-gov-003-roadmap-generator-design-gate.md` |
| `RM-GOV-004` | implementation | Структурный roadmap guard | `RM-GOV-003` | 3 | done | — | tamper matrix красная для drift/schema/dependencies/metrics/SSOT и зелёная на baseline [ci_job: `roadmap-governance-guard`] | verified · command · `python3 scripts/ci/roadmap-governance-guard.py`; verified · command · `python3 scripts/ci/roadmap-governance-guard.py --self-test`; verified · ci_run · `gh run 33000750265 — roadmap-governance-guard success на 47be5dd`; verified · artifact · `docs/architecture/rm-gov-004-roadmap-governance-guard-design-gate.md` |
| `RM-GOV-005` | governance | Canonical cutover | `RM-GOV-003`, `RM-GOV-004`, `RM-GOV-006` | 4 | done | canon_change | один sequencing SSOT в `AGENTS.md` [owner] | verified · command · `python3 scripts/ci/roadmap-governance-guard.py`; verified · command · `python3 scripts/ci/roadmap-governance-guard.py --self-test`; verified · ci_run · `gh run 33000750265 — release-gate success на 47be5dd`; verified · artifact · `docs/architecture/rm-gov-005-canonical-cutover-design-gate.md` |
| `RM-GOV-006` | governance | Единое правило факта и требования | `RM-GOV-001` | 1 | done | — | approved правило §1.1 записано без конфликта в индекс/ADR-процесс [artifact: `docs/architecture/adr/ADR-020-fact-vs-requirement.md`] | verified · adr · `docs/architecture/adr/ADR-020-fact-vs-requirement.md`; verified · command · `python3 scripts/ci/roadmap-governance-guard.py --module doc`; verified · command · `python3 scripts/ci/roadmap-governance-guard.py --self-test` |
| `RM-GOV-007` | governance | Единый реестр решений (A2): DEC как alias owner_decisions, модуль guard decisions | `RM-GOV-005` | 5 | verification | — | 27/27 DEC §29 представлены alias ровно одного OD; guard decisions зелёный [ci_job: `roadmap-governance-guard`] | verified · ci_run · `https://github.com/santanas-dev/retail-media-platform-enterprise/actions/runs/33164564954` |
| `RM-GOV-008` | governance | Трассировка требований (A1): requirements-traceability.yaml + модуль guard req | `RM-GOV-007` | 6 | verification | — | 101 REQ, 69 SC, 58/58 registry ID трассированы; guard req зелёный [ci_job: `roadmap-governance-guard`] | verified · ci_run · `https://github.com/santanas-dev/retail-media-platform-enterprise/actions/runs/33166246511` |
| `RM-GOV-009` | governance | Task breakdown A3 → roadmap.yaml: новые стадии C/CORE/CH/A, перестановка BT, schema stage enum | `RM-GOV-008` | 7 | verification | canon_change | все 101 REQ имеют roadmap_ids или approved deferred; traceability без task_required [command: `python3 scripts/ci/roadmap-governance-guard.py`]; владелец принял очередь (ACCEPT с SHA) [owner: `docs/product/roadmap.yaml:owner_decisions (ACCEPT владельца с датой)`] | verified · ci_run · `https://github.com/santanas-dev/retail-media-platform-enterprise/actions/runs/33169752021` |
| `RM-GOV-010` | governance | Owner/RACI для REQ и SC (170 TBD) и mapping 23 PENDING-ID journeys | `RM-GOV-008` | 7 | planned | scope_decision | 0 полей TBD в traceability; pending_journey_map без awaiting_owner [command: `python3 scripts/ci/roadmap-governance-guard.py`]; назначения подтверждены владельцем [owner: `docs/product/roadmap.yaml:owner_decisions (ACCEPT владельца с датой)`] | — |
| `RM-GOV-011` | governance | Правила агентов и приёмки: ADR-020 в индекс, Done Gate ↔ §27 DoD требования | `RM-GOV-006` | 2 | planned | canon_change | индекс Sources of Truth содержит ADR-020; §27 DoD REQ отражён в Done Gate AGENTS.md [artifact: `diff AGENTS.md`] | — |

### E0 — Окружения (3)

| ID | Kind | Задача | Зависит от | Глубина | Поставка | Owner gate | Приёмка | Evidence |
|---|---|---|---|---|---|---|---|---|
| `RM-ENV-001` | governance | Инвентарь `.77/.81/DEV/PROD` и очистка активных ссылок | `Gate-G` | 0 | done | scope_decision | versioned environment inventory [artifact: `docs/product/environment-inventory.yaml`] | verified · ci_run · `gh run 33003166965 — roadmap-governance-guard success на 9b88ae8`; verified · artifact · `docs/product/environment-inventory.yaml`; verified · command · `curl -s -o /dev/null -w '%{http_code}' --max-time 4 http://192.168.110.77:3000/`; verified · command · `curl -s http://192.168.110.81:8000/version`; verified · command · `python3 scripts/ci/roadmap-governance-guard.py --module env`; verified · artifact · `docs/architecture/rm-env-001-environment-inventory-design-gate.md` |
| `RM-ENV-002` | implementation | Стенд: seed/reset в утверждённое время и точный демо-состав | `RM-ENV-001` | 1 | planned | — | seed/reset воспроизводим, время до smoke-набора измерено и ≤ owner target [command: `tests/test_local_stand.py`]; подсчёт по БД совпадает с §25 REQ-STAND-002 (10/50/500; 2000 KSO …) [behavioral: `tests/test_local_stand.py`]; в seed нет реальных PII/tokens/договоров [command: `tests/test_local_stand.py`] | — |
| `RM-ENV-003` | governance | DEV environment manifest (AG): endpoint/версии/SHA/schema/доступность + seed/reset | `RM-ENV-001`, `RM-ENV-002` | 2 | planned | — | environment-inventory.yaml содержит поля AG для DEV/.81; guard env зелёный [command: `python3 scripts/ci/roadmap-governance-guard.py`] | — |

### S — Стабилизация доказательств и границ (18) · закрывается `Gate-S`

| ID | Kind | Задача | Зависит от | Глубина | Поставка | Owner gate | Приёмка | Evidence |
|---|---|---|---|---|---|---|---|---|
| `RM-STAB-001` | implementation | Единый контракт `BEHAVIORAL_APP_DB_URL` | `RM-ENV-001` | 1 | done | — | обе DSN-формы проходят один targeted behavioral command через один helper [command: `RUN_BEHAVIORAL_TESTS=1 python3 -m pytest tests/behavioral/test_commerce_rls.py -q`] | verified · command · `RUN_BEHAVIORAL_TESTS=1 python3 -m pytest tests/behavioral/test_commerce_rls.py -q`; verified · behavioral · `RUN_BEHAVIORAL_TESTS=1 BEHAVIORAL_APP_DB_URL=postgresql://... python3 -m pytest tests/behavioral/test_commerce_rls.py tests/behavioral/test_campaign_permission_split_001.py -q`; verified · behavioral · `RUN_BEHAVIORAL_TESTS=1 BEHAVIORAL_APP_DB_URL=postgresql+asyncpg://... python3 -m pytest tests/behavioral/test_commerce_rls.py tests/behavioral/test_campaign_permission_split_001.py -q`; verified · behavioral · `tamper — helper перестаёт нормализовать в каждую сторону`; verified · ci_run · `gh run 33006795900 — Behavioral PostgreSQL Tests success на 00d75a6`; verified · artifact · `tests/behavioral/dsn.py` |
| `RM-STAB-002` | implementation | Strict RLS context по умолчанию | `RM-STAB-001` | 2 | done | — | admin elevation только setup [behavioral: `tests/behavioral/conftest.py::strict get_db default`] | verified · behavioral · `tests/behavioral/test_rls_context_strictness.py`; verified · behavioral · `RUN_BEHAVIORAL_TESTS=1 python3 -m pytest tests/behavioral -q`; verified · behavioral · `tamper — маска возвращена, хук фазы убран, запись allowlist без дефекта`; verified · ci_run · `gh run 33015298420 — Behavioral PostgreSQL Tests success на 1e7a2bf`; verified · artifact · `docs/architecture/rm-stab-002-strict-rls-context-design-gate.md` |
| `RM-STAB-003` | design | Зафиксировать approved personas/retailer-scope | `RM-STAB-002` | 3 | planned | scope_decision | mini-design/ADR: persona→permissions→scope [owner] | — |
| `RM-STAB-004` | implementation | Реализовать approved RBAC/RLS scope | `RM-STAB-003`, `RM-STAB-006` | 5 | planned | migration_application | API/portal/migration согласованы [behavioral: `tests/behavioral/test_retailer_scope_rbac.py`] | — |
| `RM-STAB-005` | implementation | Исправить C1 UI-smoke и расширить общий guard | `RM-ENV-001` | 1 | planned | — | нет API/deep goto/sleep/broad retry [command: `UI_SMOKE_RUN=1 python3 -m pytest tests/ui-contract -q`] | — |
| `RM-STAB-006` | governance | Нормативный формат всех UI journeys registry | `RM-STAB-003` | 4 | planned | — | validator: actor, permission, entry, `Happy-path: N`, selectors, negative expectation [command: `python3 scripts/ci/check-journey-spec.py --strict`]; число journeys вычисляется из feature-registry, не фиксируется в задаче (RM-GOV-009 - «45/45» не подтверждено r421) [command: `python3 scripts/roadmap-consistency-check.py`] | — |
| `RM-STAB-007` | implementation | UI proof под intended roles | `RM-STAB-004`, `RM-STAB-006` | 6 | planned | — | critical journeys имеют positive intended-role и negative missing-permission proof [ui_smoke: `tests/ui-smoke/ci-subset.txt (intended-role variants)`] | — |
| `RM-STAB-008` | implementation | Единая blocking-политика UI-smoke | `RM-STAB-005`, `RM-STAB-007` | 7 | planned | canon_change | ordinary pytest отделён [ci_job: `release-gate`] | — |
| `RM-STAB-009` | implementation | Воспроизводимые CI dependencies | `RM-ENV-001` | 1 | planned | — | CI ставит project lock/requirements [ci_job: `python-tests (installs from requirements.txt)`] | — |
| `RM-STAB-010` | governance | Зафиксировать signing gate | `RM-ENV-001` | 1 | planned | — | ADR/roadmap отражают §1.2 [artifact: `docs/architecture/adr/ADR-021-manifest-signing-gate.md`] | — |
| `RM-STAB-011` | governance | W0 rebaseline | `RM-STAB-001`, `RM-STAB-002`, `RM-STAB-003`, `RM-STAB-004`, `RM-STAB-005`, `RM-STAB-006`, `RM-STAB-007`, `RM-STAB-008`, `RM-STAB-009`, `RM-STAB-010` | 8 | planned | — | named targeted → behavioral → UI subset → guards [command: `python3 scripts/ci/check-roadmap-schema.py --file docs/product/roadmap.yaml`] | — |
| `RM-STAB-012` | implementation | Async I/O boundary: детектор blocking I/O в async handlers (ADR-012) | `RM-STAB-009` | 2 | planned | — | статический/рантайм-детектор красный на blocking I/O без threadpool; текущий код чист [command: `tests/test_api_tx_boundary.py`] | — |
| `RM-STAB-013` | implementation | API attack protection: runtime negative suite (schema/size, IDOR, CSRF/XSS, SSRF, rate limit, headers, no secrets in logs) | `RM-STAB-002` | 3 | planned | — | каждый control имеет negative-тест: красный при отключении, зелёный при включении [behavioral: `tests/test_s065_rate_limit.py`]; 429 + Retry-After по endpoint и principal; audit rate-limit [behavioral: `tests/test_s065_rate_limit.py`] | — |
| `RM-STAB-014` | implementation | Полнота аудита критичных действий и реальный actor (user/service/device) | `RM-STAB-002` | 3 | planned | — | реестр критичных действий ↔ audit events 100%; anonymous/подставной actor отклонён [behavioral: `tests/behavioral/test_rm_stab_014.py`] | — |
| `RM-STAB-015` | implementation | Control plane системного администратора: отдельные permission-коды и scope | `RM-STAB-004` | 6 | planned | — | users/roles/devices/settings/monitoring/audit — отдельные коды; approved campaign без отдельного права не меняется [behavioral: `tests/test_phase3_user_management.py`] | — |
| `RM-STAB-016` | implementation | Object storage boundary: приватные buckets, presigned TTL, ограниченные service accounts | `RM-ENV-001` | 1 | planned | — | анонимный доступ запрещён; просроченный presigned URL отклонён [behavioral: `tests/test_storage_service.py`] | — |
| `RM-STAB-017` | implementation | Независимость production от внешнего runtime: production smoke при выключенных dashboard/LLM-агентах | `RM-STAB-009` | 2 | planned | — | полный production smoke проходит без внешних наблюдателей; ни один сервис не вызывает внешний runtime (egress allow-list) [command: `tests/test_production_config_gate.py`] | — |
| `RM-TECH-210` | implementation | RLS-контекст на device-маршрутах онбординга | `RM-STAB-002` | 3 | planned | device_contract | POST /device/onboard и POST /identity/device-codes работают под ролью приложения БЕЗ элевации до admin; обе записи снимаются из ENDPOINT_ELEVATION_ALLOWLIST, и behavioral-набор остаётся зелёным без них [behavioral: `tests/behavioral/test_edge001_device_onboarding.py`]; прямой запрос к БД под ролью приложения без контекста находит активный код онбординга [behavioral: `tests/behavioral/test_rls_context_strictness.py`] | — |

### C — Контракты: API, события, manifest, ERD (11) · закрывается `Gate-C`

| ID | Kind | Задача | Зависит от | Глубина | Поставка | Owner gate | Приёмка | Evidence |
|---|---|---|---|---|---|---|---|---|
| `RM-TECH-220` | implementation | OpenAPI + event/manifest JSON Schema (AG): as-built генерация + target из §26/AB, contract tests | `Gate-S` | 0 | planned | — | OpenAPI/event schemas версионированы, examples и deprecation policy; contract tests зелёные [command: `python3 scripts/ci/roadmap-governance-guard.py`]; одна canonical opaque идентификация на версию API; alias {id} с deprecation date [behavioral: `tests/behavioral/test_rm_tech_220.py`] | — |
| `RM-TECH-221` | implementation | Разделение User/Device/analytics/emergency API; device client не достигает admin | `RM-TECH-220` | 1 | planned | — | device JWT → admin endpoint = 403 на всех admin-роутах [behavioral: `tests/test_phase3_protected_identity.py`] | — |
| `RM-TECH-222` | implementation | Канонический POST /api/v1/pop/batch, legacy /device/pop/batch как alias с deprecation | `RM-TECH-220` | 1 | planned | — | ответы канонического и legacy идентичны; deprecation header; batch>500 → 422; чужой device_id отклонён [behavioral: `tests/test_contract_pop.py`] | — |
| `RM-TECH-223` | implementation | Manifest field contract и ACK-состояния runtime (opaque media_ref, no MinIO keys) | `RM-TECH-220` | 1 | planned | device_contract | все обязательные поля §25 REQ-MAN-004 в schema; внутренний object key не раскрыт; 6 ACK states принимаются [behavioral: `tests/test_contract_manifest.py`] | — |
| `RM-TECH-224` | implementation | Heartbeat contract POST /api/v1/device/heartbeat: дедуп, scope, clock drift, freshness thresholds | `RM-TECH-220` | 1 | planned | device_contract | валидный/повтор/чужой scope/просроченный heartbeat дают ожидаемые результаты; legacy alias с той же семантикой [behavioral: `tests/behavioral/test_edge004_heartbeat.py`] | — |
| `RM-TECH-225` | implementation | PoP duplicate semantics по OD-019: 200 + per-event duplicate/409, amendment ADR-017 | `RM-TECH-222` | 2 | planned | — | ADR-017 amendment принят; behavioral: повтор batch → per-event duplicate, summary не удвоен, порядок хронологический [behavioral: `tests/behavioral/test_edge003_pop_ingestion.py`] | — |
| `RM-TECH-226` | implementation | Proof model: pop_mode error/not_applied — schema/runtime migration из compatibility projection | `RM-TECH-225` | 3 | planned | migration_application | ProofMode содержит 9 значений; отчёт не смешивает playback/apply/delivery/error [behavioral: `tests/behavioral/test_pop_schema.py`] | — |
| `RM-TECH-227` | implementation | Валидация proof_event_v1: playback_result/failure_reason, clock-drift quarantine, no internal IDs/PII | `RM-TECH-225` | 3 | planned | — | недопустимый playback_result/внутренний ID/сдвиг часов → 422 или quarantine; SHA/signature проверены [behavioral: `tests/test_contract_pop.py`] | — |
| `RM-TECH-228` | implementation | Окно совместимости device/API/manifest: heartbeat объявляет версии, сервер выбирает представление | `RM-TECH-224` | 2 | planned | — | совместимая версия выбрана по объявленным capabilities; breaking change без staged rollout отклонён contract-тестом [behavioral: `tests/test_version_identity.py`] | — |
| `RM-TECH-229` | design | ERD + data dictionary + migration plan (AG): инвентарь сущностей §15, retailer_id NOT NULL + двухуровневый RLS | `RM-TECH-220` | 1 | planned | — | as-built ERD из моделей; каждая группа §15 присутствует или имеет migration task; tenant-таблицы с retailer_id+FK+RLS [artifact: `tests/behavioral/test_adr018_multitenancy_rls.py`]; behavioral RLS proof под ролью приложения NOBYPASSRLS [behavioral: `tests/behavioral/test_adr018_multitenancy_rls.py`] | — |
| `RM-TECH-230` | design | Channel Adapter contract (design-only до второго канала): versioned task, receipt, proof/ack, error, health, mock mode | `RM-TECH-220` | 1 | planned | — | contract spec + JSON Schema без реализации adapter/mock (ADR-019) [artifact: `docs/architecture contract`] | — |

### CORE — Ядро: иерархия, outbox, lifecycle, безопасность (22)

| ID | Kind | Задача | Зависит от | Глубина | Поставка | Owner gate | Приёмка | Evidence |
|---|---|---|---|---|---|---|---|---|
| `RM-BIZ-001` | governance | Записать managed-first scope | `Gate-S` | 0 | planned | — | roadmap явно исключает `self.campaign_create` из ближайшего control-plane pilot [artifact: `docs/product/roadmap.yaml (pilot scope)`] | — |
| `RM-TECH-201` | design | Таксономия причин недопоказа | `Gate-S` | 0 | planned | — | 8 категорий ТЗ, source/report/history contract и owner-approved artifact [artifact: `docs/product/underdelivery-reason-taxonomy.yaml`] | — |
| `RM-TECH-202` | implementation | Вытеснение и объяснимые приоритеты | `RM-TECH-201` | 1 | planned | — | versioned rules [behavioral: `tests/behavioral/test_campaign_preemption.py`] | — |
| `RM-TECH-203` | implementation | Overbooking policy | `RM-TECH-202` | 2 | planned | — | default deny [behavioral: `tests/behavioral/test_inventory_overbooking_policy.py`] | — |
| `RM-TECH-204` | implementation | Creative QA без неутверждённого HTML5 | `Gate-S` | 0 | planned | — | metadata/antivirus/executable deny и immutable QA result [behavioral: `tests/behavioral/test_creative_qa.py`] | — |
| `RM-TECH-206` | implementation | License renewal/grant boundary | `Gate-S` | 0 | planned | — | атомарная семантика §1.6 [behavioral: `tests/behavioral/test_license_renewal_boundary.py`] | — |
| `RM-TECH-240` | implementation | Универсальная иерархия носителей: migration + seed network/branch/cluster/store/store_group/channel/device/surface | `RM-TECH-229` | 2 | planned | migration_application | все уровни существуют с FK и RLS; seed заполняет иерархию; чужой scope не видит [behavioral: `tests/behavioral/test_scope_rls.py`] | — |
| `RM-TECH-241` | implementation | Target resolution boundary: broad target → display_surface_id, запрет physical_device_id как target | `RM-TECH-240` | 3 | planned | — | планирование разрешает target до surface; physical_device_id в target отклоняется [behavioral: `tests/test_s089_inventory_simulation.py`] | — |
| `RM-TECH-242` | implementation | Outbox для любой OLTP-записи с domain event; revocation/refresh manifest при pause/archive/expiry | `RM-TECH-240` | 3 | planned | — | каждая доменная мутация создаёт outbox event в той же транзакции; pause/archive порождают revocation [behavioral: `tests/behavioral/test_outbox.py`] | — |
| `RM-TECH-243` | implementation | Outbox relay: lease/publishing, Nats-Msg-Id, 7 попыток → dead_letter, partition order, DLQ policy, no PII | `RM-TECH-242` | 4 | planned | — | 7 отказов брокера → dead_letter с operator action; ack → published; replay идемпотентен [behavioral: `tests/behavioral/test_outbox_relay.py`]; NATS recovery integration зелёный [command: `tests/behavioral/test_outbox_relay.py`] | — |
| `RM-TECH-244` | implementation | Adapter task lifecycle через persisted queue (event-driven массовая публикация) | `RM-TECH-243` | 5 | planned | — | активация на 1000 устройств не ждёт устройств; задачи агрегируют статусы [behavioral: `tests/behavioral/test_delivery_foundation.py`] | — |
| `RM-TECH-245` | implementation | Campaign lifecycle по ADR-015/OD-036: scheduled, resume, revise, archive; единый guard и audit | `RM-STAB-004` | 6 | planned | migration_application | _CAMPAIGN_TRANSITIONS = ADR-015; каждый переход через guard с audit; возврат в draft создаёт revision [behavioral: `tests/behavioral/test_campaign_domain.py`]; campaign.* smokes зелёные после изменения [ui_smoke: `tests/ui-smoke/test_rm_tech_245.py`] | — |
| `RM-TECH-246` | implementation | Commerce order: отмена по OD-020 (draft→cancelled, confirmed — reversal), payment projection отдельно | `RM-STAB-004` | 6 | planned | — | _ORDER_TRANSITIONS: draft→cancelled разрешён, confirmed→cancelled запрещён, reversal с audit [behavioral: `tests/test_commerce_a2.py`] | — |
| `RM-TECH-247` | implementation | Approval policy: required roles/scope/порядок/timeout per campaign/placement/creative | `RM-TECH-245` | 7 | planned | — | политика версионирована; submit/approve соблюдают порядок и timeout; negative для чужого scope [behavioral: `tests/behavioral/test_campaign_approval.py`] | — |
| `RM-TECH-248` | implementation | Flight/placement windows: versioned start_at/end_at UTC, проверка при simulation/manifest/runtime | `RM-TECH-245` | 7 | planned | — | показ вне окна запрещён на трёх уровнях; DST/праздники/closed stores — версионированные правила [behavioral: `tests/test_s063_pop_timezone.py`] | — |
| `RM-TECH-249` | implementation | Manifest eligibility: approved status + валидный flight/contract + resolved target + readiness | `RM-TECH-248` | 8 | planned | — | неэлигибельная кампания не попадает в manifest; причина объяснима [behavioral: `tests/behavioral/test_delivery_generation.py`] | — |
| `RM-TECH-250` | implementation | Creative/rendition state machine и immutable media history (uploaded→scanning→qa_failed/approved→superseded→retained) | `RM-TECH-204` | 1 | planned | migration_application | каждая версия хранит uploader/SHA-256/QA-решение/связь; закрытый отчёт воспроизводим после logical delete [behavioral: `tests/behavioral/test_creative_assets.py`] | — |
| `RM-TECH-251` | implementation | Data ownership/lineage: immutable versioning и diff campaign/placement/playlist, словарь владельцев | `RM-TECH-229` | 2 | planned | — | сохранение создаёт версию с diff и actor; предыдущая неизменяема [behavioral: `tests/behavioral/test_rm_tech_251.py`] | — |
| `RM-TECH-252` | implementation | Identity: AD/LDAP или SSO для internal staff, MFA до production (OD-008) | `RM-STAB-004` | 6 | planned | protected_boundary | логин через IdP; production-профиль без MFA отклоняет; TLS-профиль зафиксирован [behavioral: `tests/test_phase3_auth_api.py`] | — |
| `RM-TECH-253` | design | Data protection: data classes, lawful purpose, минимизация PII, residency; retention по OD-009 | `RM-TECH-229` | 2 | planned | — | реестр data classes для всех сущностей; новая PII-сущность без класса — красный design-gate [artifact: `docs/architecture data classes`] | — |
| `RM-TECH-254` | implementation | Emergency state machine: requested→authorized→dispatching→applied→resuming→closed, MFA+reason, приоритетный канал | `RM-TECH-245` | 7 | planned | — | emergency с причиной; per-target result; audit actor/reason/affected; resume возвращает штатный manifest [behavioral: `tests/test_phase3_emergency_api.py`]; emergency.* smokes зелёные [ui_smoke: `tests/ui-smoke/test_uismoke__emergency__activate.py`] | — |
| `RM-TECH-255` | implementation | Device health/commands: пороги статусов по профилю, per-device view, команды с подтверждением | `RM-TECH-224` | 2 | planned | — | online→degraded→offline по порогам; команда доставлена и подтверждена [behavioral: `tests/behavioral/test_rm_tech_255.py`]; device.health_view smoke зелёный [ui_smoke: `tests/ui-smoke/test_uismoke__device__health_view.py`] | — |

### U — Portal: утверждённый UX-порядок (11) · закрывается `Gate-U`

| ID | Kind | Задача | Зависит от | Глубина | Поставка | Owner gate | Приёмка | Evidence |
|---|---|---|---|---|---|---|---|---|
| `RM-BIZ-002` | implementation | `self.campaign_create` в будущей ветке | `RM-BIZ-001` | 1 | blocked | scope_decision | mini-design, journey, backend/UI/RLS, intended-role smoke, walkthrough [ui_smoke: `tests/ui-smoke/test_uismoke__self__campaign_create.py`] | — |
| `RM-UX-001` (A3) | implementation | Accessibility оставшихся форм + route matrix | `Gate-S` | 0 | planned | — | labels/ARIA/axe/targeted vitest [artifact: `docs/product/ux-route-matrix.yaml`] | — |
| `RM-UX-002` (A2) | implementation | Поиск/сортировка/усечение таблиц | `RM-UX-001` | 1 | planned | — | server semantics для pagination [ui_smoke: `tests/ui-smoke/test_uismoke__campaign__create.py`] | — |
| `RM-UX-003` (A4) | implementation | Responsive-проверка | `RM-UX-002` | 2 | planned | — | все routes из `ux-route-matrix.yaml` проверены на 390px без overflow/crop [artifact: `docs/product/ux-responsive-report.yaml`] | — |
| `RM-UX-004` (A6) | implementation | Согласованность состояний и терминов | `RM-UX-003` | 3 | planned | — | route matrix покрывает empty/loading/error/403/success и locale-key check [artifact: `docs/product/ux-route-matrix.yaml (states coverage)`] | — |
| `RM-UX-005` (A1b) | implementation | Adoption доказанных primitives малыми slices | `RM-UX-004` | 4 | planned | — | каждый slice имеет отдельный diff/test/review [ci_job: `frontend`] | — |
| `RM-UX-006` (A5) | implementation | Advertiser-web UX audit/fixes | `RM-UX-005` | 5 | planned | — | versioned `docs/product/advertiser-route-matrix.yaml` с точным списком 15 routes [artifact: `docs/product/advertiser-route-matrix.yaml`] | — |
| `RM-UX-007` (A7) | human | Human operator walkthrough | `RM-UX-001`, `RM-UX-002`, `RM-UX-003`, `RM-UX-004`, `RM-UX-005`, `RM-UX-006` | 6 | planned | — | человек проходит exact stand bundle [human] | — |
| `RM-UX-008` | implementation | Campaign readiness matrix по каналам (rendition/inventory/conflicts/forecast/PoP mode/SLA) с действием на blocked | `RM-TECH-249`, `RM-UX-004` | 9 | planned | — | экран согласования показывает матрицу; каждый blocked/warning ведёт к действию [ui_smoke: `tests/ui-smoke/test_rm_ux_008.py`] | — |
| `RM-UX-009` | implementation | Договор рекламодателя: immutable file versions, server-side SHA-256, legal status (юр. решение) | `RM-TECH-250` | 2 | planned | — | повторная загрузка создаёт новую версию, SHA проверен сервером; старая версия неизменяема [behavioral: `tests/test_advertiser_contracts.py`]; advertiser.contract_crud smoke зелёный [ui_smoke: `tests/ui-smoke/test_uismoke__advertiser__contract_pdf_upload.py`] | — |
| `RM-UX-011` | governance | role-scope-matrix.yaml + portal-route-matrix.yaml + journeys/ (AG) из seed/pg_policies/registry | `RM-STAB-004`, `RM-STAB-006` | 6 | planned | — | матрицы генерируются и сверяются guard; deny-cases покрыты behavioral [command: `python3 scripts/ci/roadmap-governance-guard.py`] | — |

### CH — Каналы: KSO-first, второй канал по ADR-019 (9)

| ID | Kind | Задача | Зависит от | Глубина | Поставка | Owner gate | Приёмка | Evidence |
|---|---|---|---|---|---|---|---|---|
| `RM-TECH-207A` | design | KSO environment + player/playlist design | `Gate-S` | 0 | planned | scope_decision | versioned environment audit, import/contract mini-design и test plan [artifact: `docs/architecture/kso-environment-audit.md`] | — |
| `RM-TECH-207B` | implementation | KSO player/playlist/PoP chain | `RM-TECH-207A` | 1 | planned | device_contract | contract tests и playback→manifest→PoP behavioral proof [behavioral: `tests/behavioral/test_kso_playback_chain.py`]; Playlist entity и state machine §6 ТЗ (draft → validating → valid/invalid → approved → published → superseded/rolled_back); published immutable [behavioral: `tests/behavioral/test_kso_playback_chain.py`]; manifest target lifecycle (generated → signed → queued → delivered → applied/failed/expired) и canonical POST /api/v1/pop/batch [behavioral: `tests/behavioral/test_kso_playback_chain.py`] | — |
| `RM-TECH-208` | implementation | Signed licensing Layer 2 | `RM-TECH-206`, `RM-TECH-207B`, `RM-STAB-010` | 2 | planned | protected_boundary | Ed25519 offline verify, kid/rotation/revocation, UI, tamper/rollback [behavioral: `tests/behavioral/test_signed_license_layer2.py`] | — |
| `RM-TECH-260` | implementation | Runtime cache lifecycle: лимит по профилю, детерминированная очистка, last-known-good | `RM-TECH-207B` | 2 | planned | device_contract | кэш на лимите: очистка по правилу; last-known-good сохранён; просроченная реклама не показывается [behavioral: `tests/behavioral/test_rm_tech_260.py`] | — |
| `RM-TECH-261` | design | Второй канал: решение OD-021 + channel-capability-matrix.yaml (AG); extraction design по ADR-019 | `RM-TECH-207B`, `RM-TECH-230` | 2 | blocked | scope_decision | владелец назвал канал и владельца (OD-021); матрица возможностей утверждена [owner: `docs/product/roadmap.yaml:owner_decisions (ACCEPT владельца с датой)`]; extraction design: KSO-вертикаль как первый adapter без поломки контрактов [artifact: `docs/audit/RM-TECH-261-artifact.md (создаётся задачей)`] | — |
| `RM-TECH-262` | implementation | Dynamic creative binding/rendition safety (V26-008) на одном канале | `RM-TECH-280`, `RM-TECH-261` | 3 | blocked | — | master-confirmed price/promo подставляется при manifest generation; SLA-тест dynamic manifest [behavioral: `tests/behavioral/test_rm_tech_262.py`] | — |
| `RM-TECH-263` | implementation | Field mobile operations: scoped mobile web для сотрудника магазина (устройства, фото, инциденты) | `RM-TECH-210`, `RM-TECH-255` | 4 | blocked | — | journey field_ops.device_confirm под ролью магазина с RLS; negative чужой магазин [ui_smoke: `tests/ui-smoke/test_rm_tech_263.py`] | — |
| `RM-TECH-264` | implementation | ESL/price-checker: интеграция только через approved price/SKU master (INT-002) | `RM-TECH-280` | 3 | blocked | — | price-related данные приходят из master или проходят reconciliation; расхождение блокирует показ [behavioral: `tests/behavioral/test_rm_tech_264.py`] | — |
| `RM-TECH-280` | design | Prerequisite: master-data adapter цен/SKU (контракт, owner OD-023, reconciliation) | `RM-TECH-229` | 2 | blocked | scope_decision | владелец master-данных назначен (OD-023 approved); contract + reconciliation design утверждены [owner: `docs/product/roadmap.yaml:owner_decisions (ACCEPT владельца с датой)`]; adapter в mock/test mode проходит contract tests [behavioral: `tests/behavioral/test_rm_tech_280.py`] | — |

### A — Аналитика и масштаб: attribution, NFR, интеграции (14)

| ID | Kind | Задача | Зависит от | Глубина | Поставка | Owner gate | Приёмка | Evidence |
|---|---|---|---|---|---|---|---|---|
| `RM-BIZ-003` | implementation | `self.report_view` plan/fact | `RM-TECH-201`, `RM-TECH-207B` | 2 | planned | — | реальные PoP/причины/RLS, journey/smoke/walkthrough [ui_smoke: `tests/ui-smoke/test_uismoke__self__report_view.py`] | — |
| `RM-TECH-205` | governance | SLO objectives и измерение | `Gate-S` | 0 | planned | — | каждое число ТЗ имеет formula/window/owner/metric либо `not measurable` [artifact: `docs/product/slo-objectives.yaml`] | — |
| `RM-TECH-209` | governance | ClickHouse capacity trigger | `RM-TECH-207B` | 2 | planned | — | измеряемый PoP rate/retention threshold и owner migration gate [artifact: `docs/product/clickhouse-capacity-trigger.yaml`] | — |
| `RM-TECH-256` | governance | Business outcome KPI: baseline/target/metric definition для целей §1.2 (OD-024 exit criteria) | `RM-TECH-205` | 1 | planned | scope_decision | каждая бизнес-цель имеет baseline/target/формулу/владельца, утверждено владельцем [owner: `docs/product/roadmap.yaml:owner_decisions (ACCEPT владельца с датой)`] | — |
| `RM-TECH-281` | implementation | Prerequisite: sales-reference ingestion (агрегаты store/SKU/day) + методология baseline/test-control | `RM-TECH-280` | 3 | blocked | — | пакетная загрузка агрегатов без PII; versioned baseline; методика утверждена владельцем [behavioral: `tests/behavioral/test_rm_tech_281.py`] | — |
| `RM-TECH-282` | implementation | Attribution & sales lift: test/control, versioned baseline, pilot lift report | `RM-TECH-281`, `RM-TECH-229` | 4 | blocked | — | pilot lift report по test/control с explainable методикой; RLS scope [behavioral: `tests/behavioral/test_rm_tech_282.py`] | — |
| `RM-TECH-283` | design | Prerequisite: audience source/privacy contract (анонимные store-атрибуты, 152-ФЗ, OD-032) | `RM-TECH-280`, `RM-TECH-253` | 3 | blocked | scope_decision | privacy/legal решение (OD-032) и контракт источника утверждены [owner: `docs/product/roadmap.yaml:owner_decisions (ACCEPT владельца с датой)`] | — |
| `RM-TECH-284` | implementation | A/B attribution и winner metric (minimum sample, owner approval результата) | `RM-TECH-282` | 5 | blocked | — | A/B фиксирует группы/период/метрику; winner только при minimum sample и ручном утверждении [behavioral: `tests/behavioral/test_rm_tech_284.py`] | — |
| `RM-TECH-285` | implementation | Competitive separation: competitive_category, интервал/исключение в playlist/manifest (исключение §3.1 по OD-018) | `RM-TECH-202`, `RM-TECH-280` | 3 | blocked | — | separation block/override test; изменение priority engine ограничено §3.1 [behavioral: `tests/behavioral/test_rm_tech_285.py`] | — |
| `RM-TECH-286` | implementation | Financial-system exchange: versioned/idempotent export + payment-status contract (после DEC-017) | `RM-TECH-246` | 7 | blocked | — | idempotent export round-trip; повтор не создаёт дубликатов; scope финансового контура зафиксирован [behavioral: `tests/behavioral/test_rm_tech_286.py`] | — |
| `RM-TECH-287` | implementation | BI/export/SIEM/vendor API: scoped keys, rate-limit, immutable audit, circuit breaker (после DEC-013) | `RM-STAB-013` | 4 | blocked | — | 401/403/429 negative; vendor connector с отдельными credentials и failure mode [behavioral: `tests/test_s065_rate_limit.py`] | — |
| `RM-TECH-288` | governance | nfr-slo.yaml + load-profiles.yaml (AG): method, percentile, error budget, generator, CI evidence | `RM-TECH-205` | 1 | planned | — | каждый SLO имеет window/denominator/exclusions; load generator и прогон в CI/стенде [artifact: `nfr-slo.yaml`] | — |
| `RM-TECH-289` | design | Extension points designed-not-implemented: ADR для programmatic (V26-007) и external measurement (V26-011) | `RM-TECH-220` | 1 | planned | — | ADR принят с пометкой designed-not-implemented; код не пишется до OD-021/OD-031 [artifact: `docs/audit/RM-TECH-289-artifact.md (создаётся задачей)`] | — |
| `RM-UX-010` | implementation | Service-quality reporting: доля active devices/logical carriers, plan/fact по каналу (analytics.compare) | `RM-BIZ-003` | 3 | planned | — | отчёт по каналу с долями и причинами; RLS scope advertiser [ui_smoke: `tests/ui-smoke/test_rm_ux_010.py`] | — |

### POPS — Внешние действия: pilot и production (8)

| ID | Kind | Задача | Зависит от | Глубина | Поставка | Owner gate | Приёмка | Evidence |
|---|---|---|---|---|---|---|---|---|
| `RM-OPS-001` | external | Production readiness | `RM-PILOT-003` | 4 | planned | deployment | не запускается автоматически после pilot [owner] | — |
| `RM-OPS-002` | implementation | Network segmentation: firewall rules по environment + negative reachability tests из device-сегмента | `RM-PILOT-002` | 3 | planned | — | Admin API/PostgreSQL/MinIO/Redis недостижимы из device-сегмента; Gateway только HTTPS/mTLS [command: `python3 scripts/ci/roadmap-governance-guard.py`] | — |
| `RM-OPS-003` | external-plan | Production HA baseline: ≥2 backend, масштабируемый Gateway, standby PostgreSQL, MinIO replication, quarterly restore drill | `RM-OPS-001` | 5 | blocked | deployment | production config gate зелёный; restore drill выполнен и записан [command: `tests/test_production_config_gate.py`]; топология утверждена (OD-028), RTO/RPO (OD-025) [owner: `docs/product/roadmap.yaml:owner_decisions (ACCEPT владельца с датой)`] | — |
| `RM-OPS-004` | implementation | Rollout entity/state machine и feature flags: planned→lab→canary→staged→paused→completed/rolled_back | `RM-PILOT-002` | 3 | blocked | — | rollback возвращает предыдущую версию; flag отключает функцию; ответственность по OD-010 [behavioral: `tests/integration/test_stand_rollback_drill.py`] | — |
| `RM-OPS-005` | governance | retention-policy.yaml + legal decision register (AG): сроки, 152-ФЗ, deletion/archive, review date | `RM-TECH-253` | 3 | blocked | scope_decision | юридическое утверждение retention/152-ФЗ (OD-009) [owner: `docs/product/roadmap.yaml:owner_decisions (ACCEPT владельца с датой)`] | — |
| `RM-PILOT-001` | design | Managed control-plane pilot scope | `Gate-S`, `Gate-U`, `RM-ENV-001` | 1 | planned | — | exact bundle/host/rollback/TLS [artifact: `docs/runbook/pilot-scope.md`] | — |
| `RM-PILOT-002` | external-plan | Deployment plan/preflight | `RM-PILOT-001` | 2 | planned | — | immutable lock, backup/restore, migration rehearsal, secrets/TLS/monitoring [artifact: `infra/deploy/images.lock.json + dry-run evidence`] | — |
| `RM-PILOT-003` | external | Controlled pilot deploy | `RM-PILOT-002` | 3 | planned | deployment | SHA/lock/schema/health, stand-safe journeys, rollback readiness [owner] | — |

## Заблокированные функции и условия разблокировки

| Feature | Registry gap | Разблокирует | Условия | Решение |
|---|---|---|---|---|
| `analytics.compare` | Запланировано задачей RM-UX-010 (ТЗ v2.6 r421); реализации и smoke нет. | `RM-UX-010` | функция реализована задачей RM-UX-010 и имеет зелёный smoke/behavioral proof | — |
| `attribution.lift_report` | Запланировано задачей RM-TECH-282 (ТЗ v2.6 r421); реализации и smoke нет. | `RM-TECH-282` | функция реализована задачей RM-TECH-282 и имеет зелёный smoke/behavioral proof | — |
| `campaign.competitive_separation` | Запланировано задачей RM-TECH-285 (ТЗ v2.6 r421); реализации и smoke нет. | `RM-TECH-285` | функция реализована задачей RM-TECH-285 и имеет зелёный smoke/behavioral proof | — |
| `campaign.readiness` | Запланировано задачей RM-TECH-249 (ТЗ v2.6 r421); реализации и smoke нет. | `RM-TECH-249` | функция реализована задачей RM-TECH-249 и имеет зелёный smoke/behavioral proof | — |
| `campaign.schedule` | Запланировано задачей RM-TECH-248 (ТЗ v2.6 r421); реализации и smoke нет. | `RM-TECH-248` | функция реализована задачей RM-TECH-248 и имеет зелёный smoke/behavioral proof | — |
| `content.dynamic_binding` | Запланировано задачей RM-TECH-262 (ТЗ v2.6 r421); реализации и smoke нет. | `RM-TECH-262` | функция реализована задачей RM-TECH-262 и имеет зелёный smoke/behavioral proof | — |
| `device.onboard` | OD-038 / RLS-CONTEXT-DEVICE-001: в production-path устройство получает 403 INVALID_CODE — маршрут без RLS-контекста; reachable держался под admin-маской тестов. Unblock: RM-TECH-210 (behavioral под runtime-ролью на PostgreSQL). | `RM-TECH-210` | POST /device/onboard и POST /identity/device-codes работают под runtime-ролью на PostgreSQL без элевации (behavioral evidence) | OD-038 |
| `experiment.evaluate` | Запланировано задачей RM-TECH-284 (ТЗ v2.6 r421); реализации и smoke нет. | `RM-TECH-284` | функция реализована задачей RM-TECH-284 и имеет зелёный smoke/behavioral proof | — |
| `field_ops.device_confirm` | Запланировано задачей RM-TECH-263 (ТЗ v2.6 r421); реализации и smoke нет. | `RM-TECH-263` | функция реализована задачей RM-TECH-263 и имеет зелёный smoke/behavioral proof | — |
| `finance.exchange` | Запланировано задачей RM-TECH-286 (ТЗ v2.6 r421); реализации и smoke нет. | `RM-TECH-286` | функция реализована задачей RM-TECH-286 и имеет зелёный smoke/behavioral proof | — |
| `finance.reconcile` | Запланировано задачей RM-TECH-286 (ТЗ v2.6 r421); реализации и smoke нет. | `RM-TECH-286` | функция реализована задачей RM-TECH-286 и имеет зелёный smoke/behavioral proof | — |
| `integration.reconcile` | Запланировано задачей RM-TECH-281 (ТЗ v2.6 r421); реализации и smoke нет. | `RM-TECH-281` | функция реализована задачей RM-TECH-281 и имеет зелёный smoke/behavioral proof | — |
| `kpi.review` | Запланировано задачей RM-TECH-256 (ТЗ v2.6 r421); реализации и smoke нет. | `RM-TECH-256` | функция реализована задачей RM-TECH-256 и имеет зелёный smoke/behavioral proof | — |
| `license.upload` | Layer 2 (signed-license/JWS/CRL + UI upload) — не реализован. | `RM-TECH-208` | signed-license Layer 2: upload .lic + проверка подписи | — |
| `license.view` | Layer 2 (signed-license/UI) — не реализован. | `RM-TECH-208` | signed-license Layer 2: offline Ed25519 verify + kid/CRL | — |
| `placement.audience_targeting` | Запланировано задачей RM-TECH-283 (ТЗ v2.6 r421); реализации и smoke нет. | `RM-TECH-283` | функция реализована задачей RM-TECH-283 и имеет зелёный smoke/behavioral proof | — |
| `playlist.build` | Плеер не перенесён в enterprise. Код есть в старом репо (PLAYER-AUD-001), адаптация — после manifest/onboard/ingest. | `RM-TECH-207B` | плеер перенесён в enterprise-репозиторий и есть реальный КСО | — |
| `release.rollback` | Запланировано задачей RM-OPS-004 (ТЗ v2.6 r421); реализации и smoke нет. | `RM-OPS-004` | функция реализована задачей RM-OPS-004 и имеет зелёный smoke/behavioral proof | — |
| `rollout.rollback` | Запланировано задачей RM-OPS-004 (ТЗ v2.6 r421); реализации и smoke нет. | `RM-OPS-004` | функция реализована задачей RM-OPS-004 и имеет зелёный smoke/behavioral proof | — |
| `self.campaign_create` | UI-smoke отсутствует. P2 — self-service фаза, не пилот. | `RM-BIZ-002` | владелец включает self-service в scope пилота | OD-005 |
| `self.report_view` | UI-smoke отсутствует. Фронтенд advertiser-web не проходил аудит. | `RM-BIZ-003` | реальные PoP-события от плеера, а не симулятора | — |

## Матрица функций (registry + evidence)

Столбец «Зрелость» берётся только из блока `maturity` в `roadmap.yaml`. Генератор его не вычисляет.

### admin-web — 49

| Feature ID | Название | Приоритет | Статус | Smoke | В CI-subset | Зрелость |
|---|---|---|---|---|---|---|
| `adsettings.configure` | Сохранить настройки AD | P1 | reachable | `test_uismoke__adsettings__configure` | ✅ | не заявлено |
| `adsettings.test` | Проверить подключение AD | P1 | reachable | `test_uismoke__adsettings__test` | ✅ | не заявлено |
| `advertiser.application_review` | Рассмотреть заявку рекламодателя | P0 | reachable | `test_uismoke__advertiser__application_review` | ✅ | не заявлено |
| `advertiser.brand_crud` | Управление брендами рекламодателя (создание, редактирование) | P1 | reachable | `test_uismoke__advertiser__brand_crud` | ✅ | не заявлено |
| `advertiser.contact_crud` | Управление контактами рекламодателя (создание, редактирование, привязка к учётной записи) | P1 | reachable | `test_uismoke__advertiser__contact_crud` | ✅ | не заявлено |
| `advertiser.contract_crud` | Договоры рекламодателя — создание, редактирование, PDF upload | P1 | reachable | `test_uismoke__advertiser__contract_pdf_upload` | ✅ | не заявлено |
| `advertiser.create_org` | Создать организацию рекламодателя (managed) | P0 | reachable | `test_uismoke__advertiser__create_org` | ✅ | не заявлено |
| `advertiser.invite` | Пригласить рекламодателя | P1 | reachable | `test_uismoke__advertiser__invite` | ✅ | не заявлено |
| `advertiser.legal_requisites` | Юридические реквизиты рекламодателя (заполнение, редактирование) | P1 | reachable | `test_uismoke__advertiser__legal_requisites` | ✅ | не заявлено |
| `advertiser.view` | Смотреть карточку рекламодателя | P1 | reachable | `test_uismoke__advertiser__view` | ✅ | не заявлено |
| `analytics.compare` | Отчёт качества услуги по каналам (plan/fact, доля active devices) | P1 | blocked | `test_uismoke__analytics__compare` | — | не заявлено |
| `attribution.lift_report` | Отчёт sales lift test/control (attribution) | P2 | blocked | `test_uismoke__attribution__lift_report` | — | не заявлено |
| `audit.view` | Смотреть журнал аудита | P1 | reachable | `test_uismoke__audit__view` | ✅ | не заявлено |
| `campaign.activate` | Запустить одобренную кампанию | P1 | reachable | `test_uismoke__campaign__activate` | ✅ | не заявлено |
| `campaign.approve` | Одобрить кампанию | P0 | reachable | `test_uismoke__campaign__approve` | ✅ | не заявлено |
| `campaign.create` | Создание кампании | P0 | reachable | `test_uismoke__campaign__create` | ✅ | не заявлено |
| `campaign.edit` | Редактирование кампании (рейсы/размещения) | P0 | reachable | `test_uismoke__campaign__edit` | ✅ | не заявлено |
| `campaign.pause` | Приостановить активную кампанию | P1 | reachable | `test_uismoke__campaign__pause` | ✅ | не заявлено |
| `campaign.readiness` | Матрица готовности кампании по каналам | P1 | blocked | `test_uismoke__campaign__readiness` | — | не заявлено |
| `campaign.reject` | Отклонить кампанию с причиной | P0 | reachable | `test_uismoke__campaign__reject` | ✅ | не заявлено |
| `campaign.schedule` | Flight/placement windows кампании (versioned, UTC + local TZ) | P1 | blocked | `test_uismoke__campaign__schedule` | — | не заявлено |
| `campaign.submit` | Отправить кампанию на согласование | P0 | reachable | `test_uismoke__campaign__submit` | ✅ | не заявлено |
| `commerce.booking` | Бронирование (offered→booked) | P1 | reachable | `test_uismoke__commerce__order_create` | ✅ | не заявлено |
| `commerce.offer_generate` | Генерация коммерческого предложения (draft→offered) | P1 | reachable | `test_uismoke__commerce__order_create` | ✅ | не заявлено |
| `commerce.order_close` | Закрытие заказа (terminal) | P1 | reachable | `test_uismoke__commerce__order_create` | ✅ | не заявлено |
| `commerce.order_create` | Создание коммерческого заказа | P1 | reachable | `test_uismoke__commerce__order_create` | ✅ | не заявлено |
| `commerce.payment_status` | Статус оплаты заказа | P1 | reachable | `test_uismoke__commerce__order_create` | ✅ | не заявлено |
| `commerce.price_list_manage` | Управление версиями прайс-листов | P1 | reachable | `test_uismoke__commerce__tariff_manage` | ✅ | не заявлено |
| `commerce.tariff_manage` | Управление тарифами и прайс-листами | P1 | reachable | `test_uismoke__commerce__tariff_manage` | ✅ | не заявлено |
| `creative.moderate_approve` | Одобрить креатив (модерация) | P0 | reachable | `test_uismoke__creative__moderate_approve` | ✅ | не заявлено |
| `creative.moderate_reject` | Отклонить креатив с причиной (модерация) | P0 | reachable | `test_uismoke__creative__moderate_reject` | ✅ | не заявлено |
| `creative.upload` | Загрузка креатива | P0 | reachable | `test_uismoke__creative__upload` | ✅ | не заявлено |
| `device.health_view` | Видеть состояние парка устройств | P1 | reachable | `test_uismoke__device__health_view` | ✅ | не заявлено |
| `emergency.activate` | Экстренно остановить показ | P0 | reachable | `test_uismoke__emergency__activate` | ✅ | не заявлено |
| `emergency.deactivate` | Снять аварийный режим | P0 | reachable | `test_uismoke__emergency__deactivate` | ✅ | не заявлено |
| `experiment.evaluate` | A/B: группы, период, winner metric, ручное утверждение результата | P2 | blocked | `test_uismoke__experiment__evaluate` | — | не заявлено |
| `field_ops.device_confirm` | Полевые операции: устройства магазина, фото, инциденты (mobile web) | P2 | blocked | `test_uismoke__field_ops__device_confirm` | — | не заявлено |
| `finance.reconcile` | Финансовая сверка: заказ/договор/тариф/price list | P2 | blocked | `test_uismoke__finance__reconcile` | — | не заявлено |
| `inventory.rule_create` | Создать правило инвентаря | P1 | reachable | `test_uismoke__inventory__rule_create` | ✅ | не заявлено |
| `inventory.simulate` | Прогноз показов (симуляция инвентаря) | P1 | reachable | `test_uismoke__inventory__simulate` | ✅ | не заявлено |
| `kpi.review` | Бизнес-KPI: baseline/target/metric по целям §1.2 | P2 | blocked | `test_uismoke__kpi__review` | — | не заявлено |
| `placement.audience_targeting` | Store-audience targeting по анонимным атрибутам магазина | P2 | blocked | `test_uismoke__placement__audience_targeting` | — | не заявлено |
| `rollout.rollback` | Staged rollout и rollback с feature flags | P1 | blocked | `test_uismoke__rollout__rollback` | — | не заявлено |
| `system.theme_switch` | Переключение темы (light/dark) | P2 | reachable | `test_uismoke__system__theme_switch` | ✅ | не заявлено |
| `user.assign_roles` | Назначить роли/права пользователю | P0 | reachable | `test_uismoke__user__assign_roles` | ✅ | не заявлено |
| `user.create_advertiser` | Завести локального рекламодателя | P0 | reachable | `test_uismoke__user__create_advertiser` | ✅ | не заявлено |
| `user.deactivate` | Заблокировать пользователя | P1 | reachable | `test_uismoke__user__deactivate` | ✅ | не заявлено |
| `user.reset_password` | Сбросить пароль пользователю | P1 | reachable | `test_uismoke__user__reset_password` | ✅ | не заявлено |
| `user.split_internal_advertiser` | Разделить пользователей на внутренних и рекламодателей | P1 | reachable | `test_uismoke__user__split_internal_advertiser` | ✅ | не заявлено |

### advertiser-web — 5

| Feature ID | Название | Приоритет | Статус | Smoke | В CI-subset | Зрелость |
|---|---|---|---|---|---|---|
| `self.apply_or_brief` | Подать заявку/бриф (кабинет рекламодателя) | P1 | reachable | `test_uismoke__self__apply_or_brief` | ✅ | не заявлено |
| `self.campaign_create` | Самому завести кампанию (self-service, P2) | P2 | blocked | `test_uismoke__self__campaign_create` | — | не заявлено |
| `self.campaign_view` | Смотреть свои кампании (кабинет рекламодателя) | P0 | reachable | `test_uismoke__self__campaign_view` | ✅ | не заявлено |
| `self.login` | Войти в кабинет рекламодателя | P0 | reachable | `test_uismoke__self__login` | ✅ | не заявлено |
| `self.report_view` | Смотреть отчёт план/факт (PoP) — кабинет рекламодателя | P1 | blocked | `test_uismoke__self__report_view` | — | не заявлено |

### public — 1

| Feature ID | Название | Приоритет | Статус | Smoke | В CI-subset | Зрелость |
|---|---|---|---|---|---|---|
| `advertiser.apply` | Подать заявку на подключение (публичная форма) | P1 | reachable | `test_uismoke__advertiser__apply` | ✅ | не заявлено |

### service — 18

| Feature ID | Название | Приоритет | Статус | Smoke | В CI-subset | Зрелость |
|---|---|---|---|---|---|---|
| `backup.restore` | Резервное копирование и восстановление | P1 | reachable | `001C-FU: test_restore_drill_verify.py (16 behavioral) + test_backup_restore_drill.py (27 negative matrix) — real PG+MinIO drill` | — | не заявлено |
| `campaign.competitive_separation` | Competitive separation при построении playlist/manifest | P2 | blocked | `behavioral: tests/behavioral/test_rm_tech_285.py` | — | не заявлено |
| `campaign.complete` | Автоматическое завершение кампании по концу рейса | P1 | reachable | `n/a (service feature, no UI journey)` | — | не заявлено |
| `content.dynamic_binding` | Dynamic creative: подстановка master-confirmed price/promo | P2 | blocked | `behavioral: tests/behavioral/test_rm_tech_262.py` | — | не заявлено |
| `device.heartbeat` | Heartbeat устройств (health/статус) | P0 | reachable | `EDGE-004 behavioral (12 тестов): test_edge004_*.py` | — | не заявлено |
| `device.onboard` | Онбординг устройства (device-code → JWT) | P0 | blocked | `EDGE-001 behavioral (13 тестов): test_edge001_*.py` | — | не заявлено |
| `finance.exchange` | Обмен с финансовой системой: idempotent export + payment-status | P2 | blocked | `behavioral: tests/behavioral/test_rm_tech_286.py` | — | не заявлено |
| `integration.reconcile` | Ingestion агрегатов чековых данных и сверка с master-данными | P2 | blocked | `behavioral: tests/behavioral/test_rm_tech_281.py` | — | не заявлено |
| `license.enforce` | Enforcement лицензии при device enrollment | P1 | reachable | `test_license_enrollment.py (13 behavioral tests)` | — | не заявлено |
| `license.report` | Отчёт по лицензии (занятые/свободные seats + пик) | P1 | reachable | `test_license_report.py (16 behavioral tests)` | — | не заявлено |
| `license.seat_release` | Освобождение лицензионного seat при decommission | P1 | reachable | `test_license_decommission.py (13 behavioral tests)` | — | не заявлено |
| `license.upload` | Загрузка/установка лицензионного файла | P1 | blocked | `n/a` | — | не заявлено |
| `license.view` | Просмотр активных лицензий (UI) | P1 | blocked | `n/a` | — | не заявлено |
| `manifest.deliver` | Доставка манифеста на устройство | P0 | reachable | `EDGE-002 behavioral (13 тестов): test_edge002_*.py` | — | не заявлено |
| `observability` | Мониторинг и метрики (Prometheus/Grafana) | P1 | reachable | `S-047: /metrics endpoint, Prometheus alert rules (8 rules)` | — | не заявлено |
| `playlist.build` | Построение плейлиста из манифеста | P1 | blocked | `n/a` | — | не заявлено |
| `pop.ingest` | Приём PoP-событий от устройств | P0 | reachable | `EDGE-003 behavioral (11 тестов): test_edge003_*.py` | — | не заявлено |
| `release.rollback` | Rollback релиза по плану развёртывания | P1 | blocked | `behavioral: tests/behavioral/test_rm_ops_004.py` | — | не заявлено |

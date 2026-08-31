# Единый план реализации v2.6 — кандидат RM-GOV-012

> **Статус: КАНДИДАТ — не канон.** Последовательность работ остаётся в `docs/product/roadmap.yaml` (SSOT); этот документ —
> согласованная проекция ТЗ v2.6, технической и бизнесовой roadmap, хронологии этапов, зависимостей и acceptance gates,
> подготовленная **без изменения кода** по указанию владельца 2026-08-31 (`OD-041`). Становится входом для разработки только
> после независимой проверки Codex и утверждения владельцем (ACCEPT RM-GOV-012). До этого RM-UX-007 и operator walkthrough
> приостановлены, новые продуктовые функции не реализуются (Дополнение AG, шаг 7).

| Источник | Ревизия / идентичность |
|---|---|
| ТЗ v2.6 | `draft-2026-08-31-r428`, sha256 `ffb8cf7d192e…` (нормативные §6/§25/§26/AP = r419; содержание ACCEPTED OD-017) |
| `docs/product/roadmap.yaml` | sha256 `f9c23debb80e…` — 109 задач (109 approved / 0 proposed; delivery 9 done / 3 verification / 2 in_progress / 85 planned / 10 blocked), 42 OD (23 approved / 19 open), 9 этапов, 9 gates |
| `docs/product/feature-registry.yaml` | 79 функций: 52 reachable / 27 blocked |
| `docs/product/requirements-traceability.yaml` | 101 REQ / 69 SC, TBD 0, awaiting_owner 0 |
| DEV-стенд | `stand-81` (192.168.110.81), `stand-27dc397`, schema 036 — `environment-inventory.yaml` |

## 1. Порядок до старта разработки (OD-041 ↔ Дополнение AG)

| Шаг AG | Содержание | Где в roadmap | Состояние |
|---|---|---|---|
| (1) owner decisions и RACI | 27 DEC → OD; роли OD-039; OD-023 approved | стадия G (RM-GOV-007/010) | roles ✔, имена — amendment; 19 OD open |
| (2) трассировка и схемы | traceability; OpenAPI/event/manifest; ERD/data dictionary | G (RM-GOV-008), C (RM-TECH-220/229) | traceability ✔ (verification); схемы planned |
| (3) portal journeys/smoke | route/role-scope matrix, journeys registry, UI-smoke policy | S (RM-STAB-006/007/008), C (RM-UX-011) | planned |
| (4) миграция и compatibility | migration plan additive-first, compatibility window | C (RM-TECH-229/228) | planned |
| (5) NFR/security/DR evidence | nfr-slo/load-profiles, retention/legal, data protection | C (RM-TECH-205/288/253, RM-OPS-005 — предложение переноса) | planned / blocked OD-009 |
| (6) независимая сверка Claude/Codex | этот план + roadmap | RM-GOV-012 | ожидает Codex |
| (7) owner approval → разработка | ТЗ → APPROVED, Gate-C | Gate-C | ожидает владельца |

**Точка старта разработки = решение `Gate-C`** (входные условия гейта — проверяемые факты; решение — акт владельца, см. §3.3).
Стадии G/E0/S — governance, окружения и стабилизация существующего (не новые функции); стадия C — контракты и все
артефакты AG; CORE и далее — реализация.

## 2. Хронология: логические этапы ТЗ (Дополнение K, §18) ↔ этапы roadmap (OD-037)

> **Projection.** Таблица — соответствие (mapping) логических этапов ТЗ K стадиям `roadmap.yaml`, а не второй порядок работ:
> порядок и принадлежность задач задаёт только `roadmap.yaml:stages/tasks`; K-этап — ссылка на источник требования (замечание Codex №3).

| Этап K | Этап(ы) roadmap | Задачи |
|---|---|---|
| 0 feasibility/stand | E0 + S | RM-ENV-001/002/003, RM-STAB-001/002/009/011 |
| 1 core/security | S + CORE | RM-STAB-004/013/014/015/016/017, RM-TECH-210, RM-TECH-252 |
| 2 hierarchy/channels/devices | C + CORE | RM-TECH-223/224/228 (контракты), RM-TECH-240/241/255 |
| 3 content/QA | CORE + CH | RM-TECH-204/250, RM-TECH-262 |
| 4 inventory | CORE | RM-TECH-201/202/203 |
| 5 campaigns/placements | CORE + U | RM-TECH-245…249, RM-UX-008/009, RM-BIZ-001 |
| 6 playlists/manifest | C + CH | RM-TECH-223, RM-TECH-207A/207B/260 |
| 7 players/adapters | CH | RM-TECH-207B, RM-TECH-230/231/261/264 |
| 8 PoP ingestion (PostgreSQL Phase 1) | C + CH | RM-TECH-222/225/226/227, RM-TECH-207B |
| 9 analytics/reports | A | RM-BIZ-003, RM-UX-010, RM-TECH-256/281…285 |
| 10 emergency/audit | S + CORE | RM-STAB-014, RM-TECH-254 |
| 11 HA/DR/load/pilot | C (NFR-артефакты) + A + POPS | RM-TECH-205/288/209, RM-PILOT-*, RM-OPS-* |

Порядок roadmap `G → E0 → S → C → CORE → U → CH → A → POPS` сохраняет логические зависимости K: core/security раньше
иерархии/каналов, контракты раньше реализации, playlist/manifest/PoP-контракты (C) раньше плеера (CH), аналитика после PoP,
HA/DR/pilot последними. Расхождений порядка не найдено (гейт `STAGE-ORDER`: зависимостей на более поздний этап — 0).

### Гейты: условия и решения

| Гейт | Этап | Approver | Статус | Решение при утверждении |
|---|---|---|---|---|
| `Gate-G` | G | owner | approved 2026-08-26 | — |
| `Gate-E0` | E0 | owner | не утверждён | окружения инвентаризованы и доказательны - наблюдения на stand-81 принимаются как evidence для стадий S и далее; этап E0 закрыт |
| `Gate-S` | S | codex | не утверждён | — |
| `Gate-U` | U | human | не утверждён | портал признан юзабельным человеком-оператором (AGENTS.md правило 8) - этап U закрыт |
| `Gate-C` | C | owner | не утверждён | ТЗ v2.6 переводится владельцем в APPROVED; разрешён старт разработки новых продуктовых функций (OD-041, Дополнение AG шаг 7) |
| `Gate-CORE` | CORE | codex | не утверждён | ядро доказано behavioral evidence и migration rehearsal - этап CORE закрыт, портал (U) и каналы (CH) строятся на нём |
| `Gate-CH` | CH | owner | не утверждён | цепочка KSO доказана на стенде под device_contract - этап CH закрыт; второй канал остаётся за OD-021 |
| `Gate-A` | A | codex | не утверждён | NFR/SLO evidence воспроизводимы, аналитика без утверждённой методики остаётся blocked - этап A закрыт |
| `Gate-POPS` | POPS | owner | не утверждён | pilot развёрнут и production readiness принята владельцем - внешние действия завершены |

## 2b. Режимы реализации по REQ (OD-042: baseline develop @ 4ac3ddb, контракт r428)

| Режим | REQ | Смысл |
|---|---|---|
| `preserve` | 9 | существующая реализация удовлетворяет REQ; только evidence/документы |
| `adapt` | 54 | существующее сохраняется, дополняется аддитивно под r428 |
| `replace` | 2 | поведение противоречит r428 — заменяется только при доказанном конфликте (conflict_ref) |
| `new` | 36 | реализации/артефакта нет — создаётся |

`replace` только по `conflict_ref`: REQ-MAN-002 (OD-002; docs/audit/2026-08-27-claude-review-r417-stability.m…); REQ-SEC-003 (OD-002; docs/audit/2026-08-27-claude-review-r417-stability.m…).
Полная таблица REQ → режим → baseline → задачи → evidence — `docs/audit/2026-08-31-claude-rm-gov-012-coverage-report.md`.

## 3. Этапы, задачи, зависимости и acceptance gates

### 0. Этап `G` — Единая система roadmap

**Выходной gate `Gate-G`** (approver: owner; approved 2026-08-26).

- Входные условия: Codex проверяет generator и tamper matrix; владелец утверждает canonical cutover
- Approval note: принят владельцем после собственной проверки; два замечания по гейту и триаж 19 открытых пунктов закрыты до принятия

| Задача | kind | Название | Зависимости | owner_role | owner_gate | приёмка | статус |
|---|---|---|---|---|---|---|---|
| `RM-GOV-001` | design | Schema/mini-design `roadmap.yaml` | — | — | scope_decision | command | done |
| `RM-GOV-002` | governance | Reconciliation/migration manifest | RM-GOV-001 | — | — | command | done |
| `RM-GOV-003` | implementation | Односторонний generator YAML + registry + evidence → Markdown/XLSX/metrics | RM-GOV-001, RM-GOV-002 | — | — | command | done |
| `RM-GOV-004` | implementation | Структурный roadmap guard | RM-GOV-003 | — | — | ci_job | done |
| `RM-GOV-006` | governance | Единое правило факта и требования | RM-GOV-001 | — | — | artifact | done |
| `RM-GOV-005` | governance | Canonical cutover | RM-GOV-003, RM-GOV-004, RM-GOV-006 | — | canon_change | owner | done |
| `RM-GOV-007` | governance | Единый реестр решений (A2): DEC как alias owner_decisions, модуль guard decisions | RM-GOV-005 | PMO/Claude Code | — | ci_job | verification |
| `RM-GOV-008` | governance | Трассировка требований (A1): requirements-traceability.yaml + модуль guard req | RM-GOV-007 | Product+Technical owner/Claude Code | — | ci_job | verification |
| `RM-GOV-009` | governance | Task breakdown A3 → roadmap.yaml: новые стадии C/CORE/CH/A, перестановка BT, schema stage enum | RM-GOV-008 | Product/PMO owner | canon_change | command/owner | verification |
| `RM-GOV-010` | governance | Owner/RACI для REQ и SC (170 TBD) и mapping 23 PENDING-ID journeys | RM-GOV-008 | Product owner | scope_decision | command/owner | in_progress |
| `RM-GOV-011` | governance | Правила агентов и приёмки: ADR-020 в индекс, Done Gate ↔ §27 DoD требования | RM-GOV-006 | Owner/Claude Code | canon_change | artifact | planned |
| `RM-GOV-012` | governance | Выравнивание ТЗ v2.6 ↔ roadmap ↔ хронология ↔ зависимости ↔ acceptance gates; единый план реали | RM-GOV-010 | PMO/Claude Code | canon_change | artifact/command/owner | in_progress |

### 1. Этап `E0` — Окружения

**Выходной gate `Gate-E0`** (approver: owner; не утверждён).

- Входные условия: RM-ENV-003 - DEV environment manifest (environment-inventory.yaml, стенд stand-81) принят владельцем как артефакт Дополнения AG (owner_gate scope_decision); guard env зелёный - стенд совпадает с base.stand_baseline; evidence только у окружений с наблюдаемой identity
- Решение при утверждении: окружения инвентаризованы и доказательны - наблюдения на stand-81 принимаются как evidence для стадий S и далее; этап E0 закрыт
- Пометка: историческая пометка (RM-GOV-012, 2026-08-31) - гейт введён после того, как RM-ENV-001 была закрыта done 2026-08-26 (owner gate scope_decision, .77 decommissioned по OD-016); гейт не переоценивает RM-ENV-001 задним числом и закрывается приёмкой RM-ENV-003

| Задача | kind | Название | Зависимости | owner_role | owner_gate | приёмка | статус |
|---|---|---|---|---|---|---|---|
| `RM-ENV-001` | governance | Инвентарь `.77/.81/DEV/PROD` и очистка активных ссылок | Gate-G | — | scope_decision | artifact | done |
| `RM-ENV-002` | implementation | Стенд: seed/reset в утверждённое время и точный демо-состав | RM-ENV-001 | Operations owner | — | behavioral/command | planned |
| `RM-ENV-003` | governance | DEV environment manifest (AG): endpoint/версии/SHA/schema/доступность + seed/reset | RM-ENV-001, RM-ENV-002 | Operations owner | scope_decision | command/owner | planned |

### 2. Этап `S` — Стабилизация доказательств и границ

**Выходной gate `Gate-S`** (approver: codex; не утверждён).

- Входные условия: новые counts и evidence воспроизводимы

| Задача | kind | Название | Зависимости | owner_role | owner_gate | приёмка | статус |
|---|---|---|---|---|---|---|---|
| `RM-STAB-001` | implementation | Единый контракт `BEHAVIORAL_APP_DB_URL` | RM-ENV-001 | — | — | command | done |
| `RM-STAB-002` | implementation | Strict RLS context по умолчанию | RM-STAB-001 | — | — | behavioral | done |
| `RM-STAB-003` | design | Зафиксировать approved personas/retailer-scope | RM-STAB-002 | — | scope_decision | owner | planned |
| `RM-STAB-006` | governance | Нормативный формат всех UI journeys registry | RM-STAB-003 | — | — | command | planned |
| `RM-STAB-004` | implementation | Реализовать approved RBAC/RLS scope | RM-STAB-003, RM-STAB-006 | — | migration_application | behavioral | planned |
| `RM-STAB-007` | implementation | UI proof под intended roles | RM-STAB-004, RM-STAB-006 | — | — | ui_smoke | planned |
| `RM-STAB-005` | implementation | Исправить C1 UI-smoke и расширить общий guard | RM-ENV-001 | — | — | command | planned |
| `RM-STAB-009` | implementation | Воспроизводимые CI dependencies | RM-ENV-001 | — | — | ci_job | planned |
| `RM-STAB-010` | governance | Зафиксировать signing gate | RM-ENV-001 | — | — | artifact | planned |
| `RM-STAB-008` | implementation | Единая blocking-политика UI-smoke | RM-STAB-005, RM-STAB-007 | — | canon_change | ci_job | planned |
| `RM-STAB-011` | governance | W0 rebaseline | RM-STAB-001, RM-STAB-002, RM-STAB-003, RM-STAB-004, RM-STAB-005, RM-STAB-006, RM-STAB-007, RM-STAB-008, RM-STAB-009, RM-STAB-010 | — | — | command | planned |
| `RM-TECH-210` | implementation | RLS-контекст на device-маршрутах онбординга | RM-STAB-002 | — | device_contract | behavioral | planned |
| `RM-STAB-012` | implementation | Async I/O boundary: детектор blocking I/O в async handlers (ADR-012) | RM-STAB-009 | Technical owner | — | command | planned |
| `RM-STAB-013` | implementation | API attack protection: runtime negative suite (schema/size, IDOR, CSRF/XSS, SSRF, rate limit, h | RM-STAB-002 | Security owner | — | behavioral | planned |
| `RM-STAB-014` | implementation | Полнота аудита критичных действий и реальный actor (user/service/device) | RM-STAB-002 | Security owner | — | behavioral | planned |
| `RM-STAB-015` | implementation | Control plane системного администратора: отдельные permission-коды и scope | RM-STAB-004 | Security owner | — | behavioral | planned |
| `RM-STAB-016` | implementation | Object storage boundary: приватные buckets, presigned TTL, ограниченные service accounts | RM-ENV-001 | Security owner | — | behavioral | planned |
| `RM-STAB-017` | implementation | Независимость production от внешнего runtime: production smoke при выключенных dashboard/LLM-аг | RM-STAB-009 | Technical owner | — | command | planned |

### 3. Этап `C` — Контракты: API, события, manifest, ERD

**Выходной gate `Gate-C`** (approver: owner; не утверждён).

- Входные условия: каждый артефакт handoff-пакета Дополнения AG принят владельцем отдельно - traceability (RM-GOV-008), DEV manifest (RM-ENV-003), role-scope/route/journeys (RM-UX-011), OpenAPI + event/manifest JSON Schema (RM-TECH-220), ERD/data dictionary/migration plan (RM-TECH-229), channel-capability-matrix KSO (RM-TECH-231), nfr-slo + load-profiles (RM-TECH-288), retention-policy + legal register (RM-OPS-005), roadmap views (RM-GOV-003/009); contract tests стадии C зелёные в CI; независимая сверка Claude/Codex единого плана реализации (RM-GOV-012) выполнена, замечания закрыты
- Решение при утверждении: ТЗ v2.6 переводится владельцем в APPROVED; разрешён старт разработки новых продуктовых функций (OD-041, Дополнение AG шаг 7)
- Пометка: условия расширены предложением RM-GOV-012 (2026-08-31) до ACCEPT владельца; до этого действовали два условия - схемы/ERD приняты и contract tests зелёные

| Задача | kind | Название | Зависимости | owner_role | owner_gate | приёмка | статус |
|---|---|---|---|---|---|---|---|
| `RM-TECH-205` | governance | SLO objectives и измерение | Gate-S | — | — | artifact | planned |
| `RM-TECH-220` | implementation | OpenAPI + event/manifest JSON Schema (AG): as-built генерация + target из §26/AB, contract test | Gate-S | Technical owner | — | behavioral/command | planned |
| `RM-TECH-221` | implementation | Разделение User/Device/analytics/emergency API; device client не достигает admin | RM-TECH-220 | Security owner | — | behavioral | planned |
| `RM-TECH-222` | implementation | Канонический POST /api/v1/pop/batch, legacy /device/pop/batch как alias с deprecation | RM-TECH-220 | Technical owner | — | behavioral | planned |
| `RM-TECH-223` | implementation | Manifest field contract и ACK-состояния runtime (opaque media_ref, no MinIO keys) | RM-TECH-220 | Technical owner | device_contract | behavioral | planned |
| `RM-TECH-224` | implementation | Heartbeat contract POST /api/v1/device/heartbeat: дедуп, scope, clock drift, freshness threshol | RM-TECH-220 | Technical owner | device_contract | behavioral | planned |
| `RM-TECH-225` | implementation | PoP duplicate semantics по OD-019: 200 + per-event duplicate/409, amendment ADR-017 | RM-TECH-222 | Technical owner | — | behavioral | planned |
| `RM-TECH-226` | implementation | Proof model: pop_mode error/not_applied — schema/runtime migration из compatibility projection | RM-TECH-225 | Technical owner | migration_application | behavioral | planned |
| `RM-TECH-227` | implementation | Валидация proof_event_v1: playback_result/failure_reason, clock-drift quarantine, no internal I | RM-TECH-225 | Security owner | — | behavioral | planned |
| `RM-TECH-228` | implementation | Окно совместимости device/API/manifest: heartbeat объявляет версии, сервер выбирает представлен | RM-TECH-224 | Technical owner | — | behavioral | planned |
| `RM-TECH-229` | design | ERD + data dictionary + migration plan (AG): инвентарь сущностей §15, retailer_id NOT NULL + дв | RM-TECH-220 | Product Data Owner/Technical owner | — | artifact/behavioral | planned |
| `RM-TECH-230` | design | Channel Adapter contract (design-only до второго канала): versioned task, receipt, proof/ack, e | RM-TECH-220 | Architecture owner | — | artifact | planned |
| `RM-TECH-231` | design | channel-capability-matrix.yaml (AG) для первого канала KSO: channel/surface/rendition/proof/SLA | RM-TECH-230 | Channel/Content owner | scope_decision | artifact/owner | planned |
| `RM-TECH-253` | design | Data protection: data classes, lawful purpose, минимизация PII, residency; retention по OD-009 | RM-TECH-229 | Security/Legal owner | — | artifact | planned |
| `RM-UX-011` | governance | role-scope-matrix.yaml + portal-route-matrix.yaml + journeys/ (AG) из seed/pg_policies/registry | RM-STAB-004, RM-STAB-006 | Security + Product/UX owner | — | command | planned |
| `RM-TECH-288` | governance | nfr-slo.yaml + load-profiles.yaml (AG): method, percentile, error budget, generator, CI evidenc | RM-TECH-205 | SRE/Operations owner | — | artifact | planned |
| `RM-OPS-005` | governance | retention-policy.yaml + legal decision register (AG): сроки, 152-ФЗ, deletion/archive, review d | RM-TECH-253 | Security/Legal owner | scope_decision | owner | blocked |

### 4. Этап `CORE` — Ядро: иерархия, outbox, lifecycle, безопасность

**Выходной gate `Gate-CORE`** (approver: codex; не утверждён).

- Входные условия: behavioral evidence под runtime-ролью приложения на PostgreSQL для иерархии носителей, target resolution, outbox/relay, campaign/commerce lifecycle, emergency state machine; migration rehearsal up/down на стенде для каждой migration_application-задачи; contract tests стадии C не сломаны
- Решение при утверждении: ядро доказано behavioral evidence и migration rehearsal - этап CORE закрыт, портал (U) и каналы (CH) строятся на нём
- Пометка: предложение RM-GOV-012 (2026-08-31) - гейт введён выравниванием и действует после ACCEPT владельца

| Задача | kind | Название | Зависимости | owner_role | owner_gate | приёмка | статус |
|---|---|---|---|---|---|---|---|
| `RM-BIZ-001` | governance | Записать managed-first scope | Gate-S | — | — | artifact | planned |
| `RM-TECH-201` | design | Таксономия причин недопоказа | Gate-S | — | — | artifact | planned |
| `RM-TECH-202` | implementation | Вытеснение и объяснимые приоритеты | RM-TECH-201 | — | — | behavioral | planned |
| `RM-TECH-203` | implementation | Overbooking policy | RM-TECH-202 | — | — | behavioral | planned |
| `RM-TECH-204` | implementation | Creative QA без неутверждённого HTML5 | Gate-S | — | — | behavioral | planned |
| `RM-TECH-206` | implementation | License renewal/grant boundary | Gate-S | — | — | behavioral | planned |
| `RM-TECH-240` | implementation | Универсальная иерархия носителей: migration + seed network/branch/cluster/store/store_group/cha | RM-TECH-229 | Product Data Owner | migration_application | behavioral | planned |
| `RM-TECH-241` | implementation | Target resolution boundary: broad target → display_surface_id, запрет physical_device_id как ta | RM-TECH-240 | Technical owner | — | behavioral | planned |
| `RM-TECH-242` | implementation | Outbox для любой OLTP-записи с domain event; revocation/refresh manifest при pause/archive/expi | RM-TECH-240 | Technical owner | — | behavioral | planned |
| `RM-TECH-243` | implementation | Outbox relay: lease/publishing, Nats-Msg-Id, 7 попыток → dead_letter, partition order, DLQ poli | RM-TECH-242 | Technical owner | — | behavioral/command | planned |
| `RM-TECH-244` | implementation | Adapter task lifecycle через persisted queue (event-driven массовая публикация) | RM-TECH-243 | Technical owner | — | behavioral | planned |
| `RM-TECH-245` | implementation | Campaign lifecycle по ADR-015/OD-036: scheduled, resume, revise, archive; единый guard и audit | RM-STAB-004 | Product/Technical owner | migration_application | behavioral/ui_smoke | planned |
| `RM-TECH-246` | implementation | Commerce order: отмена по OD-020 (draft→cancelled, confirmed — reversal), payment projection от | RM-STAB-004 | Product owner | — | behavioral | planned |
| `RM-TECH-247` | implementation | Approval policy: required roles/scope/порядок/timeout per campaign/placement/creative | RM-TECH-245 | Product owner | — | behavioral | planned |
| `RM-TECH-248` | implementation | Flight/placement windows: versioned start_at/end_at UTC, проверка при simulation/manifest/runti | RM-TECH-245 | Product owner | — | behavioral | planned |
| `RM-TECH-249` | implementation | Manifest eligibility: approved status + валидный flight/contract + resolved target + readiness | RM-TECH-248 | Technical owner | — | behavioral | planned |
| `RM-TECH-250` | implementation | Creative/rendition state machine и immutable media history (uploaded→scanning→qa_failed/approve | RM-TECH-204 | Content owner | migration_application | behavioral | planned |
| `RM-TECH-251` | implementation | Data ownership/lineage: immutable versioning и diff campaign/placement/playlist, словарь владел | RM-TECH-229 | Product Data Owner | — | behavioral | planned |
| `RM-TECH-252` | implementation | Identity: AD/LDAP или SSO для internal staff, MFA до production (OD-008) | RM-STAB-004 | Security owner | protected_boundary | behavioral | planned |
| `RM-TECH-254` | implementation | Emergency state machine: requested→authorized→dispatching→applied→resuming→closed, MFA+reason,  | RM-TECH-245 | Operations owner | — | behavioral/ui_smoke | planned |
| `RM-TECH-255` | implementation | Device health/commands: пороги статусов по профилю, per-device view, команды с подтверждением | RM-TECH-224 | Operations owner | — | behavioral/ui_smoke | planned |

### 5. Этап `U` — Portal: утверждённый UX-порядок

**Выходной gate `Gate-U`** (approver: human; не утверждён).

- Входные условия: человек проходит walkthrough на exact stand bundle
- Решение при утверждении: портал признан юзабельным человеком-оператором (AGENTS.md правило 8) - этап U закрыт
- Пометка: приостановлен владельцем 2026-08-31 (OD-041) до утверждения единого плана реализации; walkthrough - на DEV-стенде stand-81 по docs/product/operator-walkthrough-dev.md

| Задача | kind | Название | Зависимости | owner_role | owner_gate | приёмка | статус |
|---|---|---|---|---|---|---|---|
| `RM-UX-001` | implementation | Accessibility оставшихся форм + route matrix | Gate-S | — | — | artifact | planned |
| `RM-UX-002` | implementation | Поиск/сортировка/усечение таблиц | RM-UX-001 | — | — | ui_smoke | planned |
| `RM-UX-003` | implementation | Responsive-проверка | RM-UX-002 | — | — | artifact | planned |
| `RM-UX-004` | implementation | Согласованность состояний и терминов | RM-UX-003 | — | — | artifact | planned |
| `RM-UX-005` | implementation | Adoption доказанных primitives малыми slices | RM-UX-004 | — | — | ci_job | planned |
| `RM-UX-006` | implementation | Advertiser-web UX audit/fixes | RM-UX-005 | — | — | artifact | planned |
| `RM-UX-007` | human | Human operator walkthrough | RM-UX-001, RM-UX-002, RM-UX-003, RM-UX-004, RM-UX-005, RM-UX-006 | — | — | human | planned |
| `RM-BIZ-002` | implementation | `self.campaign_create` в будущей ветке | RM-BIZ-001 | — | scope_decision | ui_smoke | blocked |
| `RM-UX-008` | implementation | Campaign readiness matrix по каналам (rendition/inventory/conflicts/forecast/PoP mode/SLA) с де | RM-TECH-249, RM-UX-004 | Product/UX owner | — | ui_smoke | planned |
| `RM-UX-009` | implementation | Договор рекламодателя: immutable file versions, server-side SHA-256, legal status (юр. решение) | RM-TECH-250 | Product owner | — | behavioral/ui_smoke | planned |

### 6. Этап `CH` — Каналы: KSO-first, второй канал по ADR-019

**Выходной gate `Gate-CH`** (approver: owner; не утверждён).

- Входные условия: цепочка KSO manifest → playlist → PoP доказана на стенде под device_contract (RM-TECH-207B, RM-TECH-260); registry playlist.build/device.onboard reachable по smoke/behavioral; второй канал только по OD-021 (RM-TECH-261); ESL/dynamic creative только после master-data adapter (RM-TECH-280)
- Решение при утверждении: цепочка KSO доказана на стенде под device_contract - этап CH закрыт; второй канал остаётся за OD-021
- Пометка: предложение RM-GOV-012 (2026-08-31) - гейт введён выравниванием и действует после ACCEPT владельца

| Задача | kind | Название | Зависимости | owner_role | owner_gate | приёмка | статус |
|---|---|---|---|---|---|---|---|
| `RM-TECH-207A` | design | KSO environment + player/playlist design | Gate-S | — | scope_decision | artifact | planned |
| `RM-TECH-207B` | implementation | KSO player/playlist/PoP chain | RM-TECH-207A | — | device_contract | behavioral | planned |
| `RM-TECH-208` | implementation | Signed licensing Layer 2 | RM-TECH-206, RM-TECH-207B, RM-STAB-010 | — | protected_boundary | behavioral | planned |
| `RM-TECH-260` | implementation | Runtime cache lifecycle: лимит по профилю, детерминированная очистка, last-known-good | RM-TECH-207B | Channel owner | device_contract | behavioral | planned |
| `RM-TECH-261` | design | Второй канал: решение OD-021 + channel-capability-matrix.yaml (AG); extraction design по ADR-01 | RM-TECH-207B, RM-TECH-230 | Channel owner | scope_decision | artifact/owner | blocked |
| `RM-TECH-262` | implementation | Dynamic creative binding/rendition safety (V26-008) на одном канале | RM-TECH-280, RM-TECH-261 | Content/Channel owner | — | behavioral | planned |
| `RM-TECH-263` | implementation | Field mobile operations: scoped mobile web для сотрудника магазина (устройства, фото, инциденты | RM-TECH-210, RM-TECH-255 | Operations/UX owner | — | ui_smoke | planned |
| `RM-TECH-264` | implementation | ESL/price-checker: интеграция только через approved price/SKU master (INT-002) | RM-TECH-280 | Channel/Product Data Owner | — | behavioral | planned |
| `RM-TECH-280` | design | Prerequisite: master-data adapter цен/SKU (контракт, owner OD-023, reconciliation) | RM-TECH-229 | Product Data Owner (OD-023) | scope_decision | behavioral/owner | planned |

### 7. Этап `A` — Аналитика и масштаб: attribution, NFR, интеграции

**Выходной gate `Gate-A`** (approver: codex; не утверждён).

- Входные условия: SLO/NFR evidence по nfr-slo.yaml и load-profiles.yaml воспроизводимы в CI/на стенде (RM-TECH-205/288); ClickHouse trigger оценён (RM-TECH-209); attribution/A-B только при approved методике владельца (OD-014); задачи без решения остаются blocked, а не done
- Решение при утверждении: NFR/SLO evidence воспроизводимы, аналитика без утверждённой методики остаётся blocked - этап A закрыт
- Пометка: предложение RM-GOV-012 (2026-08-31) - гейт введён выравниванием и действует после ACCEPT владельца

| Задача | kind | Название | Зависимости | owner_role | owner_gate | приёмка | статус |
|---|---|---|---|---|---|---|---|
| `RM-BIZ-003` | implementation | `self.report_view` plan/fact | RM-TECH-201, RM-TECH-207B | — | — | ui_smoke | planned |
| `RM-TECH-209` | governance | ClickHouse capacity trigger | RM-TECH-207B | — | — | artifact | planned |
| `RM-TECH-256` | governance | Business outcome KPI: baseline/target/metric definition для целей §1.2 (OD-024 exit criteria) | RM-TECH-205 | Product owner | scope_decision | owner | planned |
| `RM-UX-010` | implementation | Service-quality reporting: доля active devices/logical carriers, plan/fact по каналу (analytics | RM-BIZ-003 | Product owner | — | ui_smoke | planned |
| `RM-TECH-281` | implementation | Prerequisite: sales-reference ingestion (агрегаты store/SKU/day) + методология baseline/test-co | RM-TECH-280 | Analytics owner | — | behavioral | planned |
| `RM-TECH-282` | implementation | Attribution & sales lift: test/control, versioned baseline, pilot lift report | RM-TECH-281, RM-TECH-229 | Analytics/Product owner | — | behavioral | blocked |
| `RM-TECH-283` | design | Prerequisite: audience source/privacy contract (анонимные store-атрибуты, 152-ФЗ, OD-032) | RM-TECH-280, RM-TECH-253 | Product Data Owner/Legal owner | scope_decision | owner | blocked |
| `RM-TECH-284` | implementation | A/B attribution и winner metric (minimum sample, owner approval результата) | RM-TECH-282 | Analytics/Product owner | — | behavioral | blocked |
| `RM-TECH-285` | implementation | Competitive separation: competitive_category, интервал/исключение в playlist/manifest (исключен | RM-TECH-202, RM-TECH-280 | Campaign/Inventory owner | — | behavioral | planned |
| `RM-TECH-286` | implementation | Financial-system exchange: versioned/idempotent export + payment-status contract (после DEC-017 | RM-TECH-246 | Finance/Integration owner | — | behavioral | blocked |
| `RM-TECH-287` | implementation | BI/export/SIEM/vendor API: scoped keys, rate-limit, immutable audit, circuit breaker (после DEC | RM-STAB-013 | Security owner | — | behavioral | blocked |
| `RM-TECH-289` | design | Extension points designed-not-implemented: ADR для programmatic (V26-007) и external measuremen | RM-TECH-220 | Architecture owner | — | artifact | planned |

### 8. Этап `POPS` — Внешние действия: pilot и production

**Выходной gate `Gate-POPS`** (approver: owner; не утверждён).

- Входные условия: pilot развёрнут по RM-PILOT-003 (deployment gate) на exact bundle; production readiness RM-OPS-001 - RTO/RPO (OD-025), топология/HA (OD-028), rollback/DR evidence; staged rollout и feature flags по OD-010; ничего не запускается автоматически после pilot
- Решение при утверждении: pilot развёрнут и production readiness принята владельцем - внешние действия завершены
- Пометка: предложение RM-GOV-012 (2026-08-31) - гейт введён выравниванием и действует после ACCEPT владельца

| Задача | kind | Название | Зависимости | owner_role | owner_gate | приёмка | статус |
|---|---|---|---|---|---|---|---|
| `RM-PILOT-001` | design | Managed control-plane pilot scope | Gate-S, Gate-U, RM-ENV-001 | — | — | artifact | planned |
| `RM-PILOT-002` | external-plan | Deployment plan/preflight | RM-PILOT-001 | — | — | artifact | planned |
| `RM-PILOT-003` | external | Controlled pilot deploy | RM-PILOT-002 | — | deployment | owner | planned |
| `RM-OPS-001` | external | Production readiness | RM-PILOT-003 | — | deployment | owner | planned |
| `RM-OPS-002` | implementation | Network segmentation: firewall rules по environment + negative reachability tests из device-сег | RM-PILOT-002 | Security/Operations owner | — | command | planned |
| `RM-OPS-003` | external-plan | Production HA baseline: ≥2 backend, масштабируемый Gateway, standby PostgreSQL, MinIO replicati | RM-OPS-001 | SRE/Operations owner | deployment | command/owner | blocked |
| `RM-OPS-004` | implementation | Rollout entity/state machine и feature flags: planned→lab→canary→staged→paused→completed/rolled | RM-PILOT-002 | Operations owner | — | behavioral | blocked |

## 4. Артефакты handoff-пакета (Дополнение AG) → задачи

| Артефакт AG | Ответственный (OD-039) | Задача | Состояние | Стадия |
|---|---|---|---|---|
| requirements-traceability.yaml | Product + Technical owner | RM-GOV-008 | verification (CI 33166246511) | G |
| role-scope-matrix.yaml | Security owner | RM-UX-011 (+RM-STAB-003/004/006) | planned | C ← U (предложение) |
| portal-route-matrix.yaml + journeys/ | Product/UX owner | RM-UX-011, RM-STAB-006 | planned | C ← U (предложение) |
| OpenAPI + event/manifest JSON Schema | Technical owner | RM-TECH-220 | planned | C |
| ERD + data dictionary + migration plan | Product Data Owner/Technical owner | RM-TECH-229 | planned | C |
| channel-capability-matrix.yaml | Channel/Content owner | RM-TECH-231 (KSO; второй канал — RM-TECH-261/OD-021) | planned (proposed) | C (новая) |
| nfr-slo.yaml + load-profiles.yaml | Operations owner | RM-TECH-288 (+RM-TECH-205) | planned | C ← A (предложение) |
| retention-policy.yaml + legal decision register | Security/Legal owner | RM-OPS-005 (+RM-TECH-253) | blocked OD-009 | C ← POPS/CORE (предложение) |
| DEV environment manifest | Operations owner | RM-ENV-003 (environment-inventory.yaml, stand-81) — закрывает Gate-E0 | planned | E0 |
| roadmap + generated views | PMO | RM-GOV-003 (done), RM-GOV-009 (verification) | done/verification | G |

Все артефакты принимаются владельцем **до решения `Gate-C`**. Два артефакта упираются в open-решения: retention/legal — `OD-009`,
channel-capability-matrix для второго канала — `OD-021` (KSO-версия делается без него, RM-TECH-231).

## 5. Условия §22 ТЗ для `APPROVED`

| Условие §22 | Чем закрывается | Состояние |
|---|---|---|
| 1 scope и RACI подписаны владельцем | OD-039 (роли), имена исполнителей — amendment; scope OD-005/030…033 | частично |
| 2 конфликты разрешены, owner decisions заполнены | 42 OD: 23 approved / 19 open (см. §6) | открыто — 19 OD |
| 3 полный каталог REQ без orphan/duplicate | 101 REQ, guard req чист | выполнено |
| 4 domain/ERD/API/event/manifest schemas согласованы | RM-TECH-220/229 (стадия C) | planned |
| 5 user stories, journeys, role/scope matrix | AP 41 story; RM-STAB-006, RM-UX-011 | planned |
| 6 проверяемые NFR, load profiles, acceptance evidence | RM-TECH-205/288 → C (предложение) | planned |
| 7 миграционный план additive-first | RM-TECH-229 (migration plan), OD-018 (§3.1 исключение) | planned |
| 8 roadmap: каждая строка — задача или approved deferred | 101/101 REQ с roadmap_ids; registry 79 — 27 blocked с unblocked_by | выполнено |
| 9 независимая сверка Claude/Codex; monitoring как сигнал | Codex review плана (RM-GOV-012); .78:3200 read-only (OD-027 open) | в процессе |

## 6. Открытые решения владельца и что они держат

| OD | DEC | Суть | Заблокировано |
|---|---|---|---|
| `OD-008` | DEC-004 | MFA обязателен до production; согласование NATS с ИТ/ops — до pilot deployment.… | — |
| `OD-009` | DEC-006/DEC-007 | Объём безопасности и соответствия до production — SIEM/Wazuh-экспорт, минимизация PII, доступ администратора т… | RM-OPS-001, RM-OPS-005 |
| `OD-010` | DEC-008 | Безопасная выкатка — staged rollout с rollback и feature flags. Вопрос - это предусловие пилота или production… | RM-OPS-001, RM-OPS-004, RM-PILOT-002 |
| `OD-011` | DEC-009 | Нагрузочные профили и критерии производительности на 40K устройств. Вопрос - измеряется ли это до пилота как в… | RM-TECH-205, RM-TECH-209 |
| `OD-012` | — | Часовые пояса, календарь и праздничное расписание показов. Это корректность доставки, а не операционный вопрос… | — |
| `OD-013` | — | Self-service онбординг рекламодателя - сброс пароля самим пользователем и приглашения. Админский сброс и пригл… | RM-BIZ-002 |
| `OD-014` | DEC-027 | A/B lift и attribution - материал ветки v2.6, зависит от модели арендатора (ADR-018). Вопрос - фиксируется ли … | RM-TECH-282, RM-TECH-284 |
| `OD-015` | — | Операционный центр здоровья устройств. Функция device.health_view reachable и закреплена в CI; вопрос - достат… | — |
| `OD-021` | DEC-001 | Каналы первой production-очереди и владелец каждого не выбраны. Вопрос владельцу - перечень каналов, владелец,… | RM-TECH-261 |
| `OD-024` | DEC-010 | Пилотная шкала КСО → 10 → 100 → 500 → сеть принята 2026-07-18. Открыты измеримые exit criteria каждого переход… | RM-PILOT-001 |
| `OD-025` | DEC-012 | RTO/RPO, HA target и владелец DR не определены. Вопрос владельцу - целевые RTO/RPO для production, кто владеет… | RM-OPS-001, RM-OPS-003 |
| `OD-026` | DEC-013 | Advertiser/BI API access не решён. Вопрос владельцу - scoped API keys с rotation/revoke/audit в первой очереди… | RM-TECH-287 |
| `OD-027` | DEC-014 | Внешний monitoring-dashboard - read-only наблюдатель без права менять файлы, статусы, задачи и owner decisions… | — |
| `OD-028` | DEC-015 | Production deployment topology не выбрана - Docker Swarm или approved equivalent. Вопрос владельцу - топология… | RM-OPS-001, RM-OPS-003 |
| `OD-029` | DEC-016 | Device PKI/mTLS activation и срок отказа от token-only flow не решены. Вопрос владельцу/ИБ - PKI/CRL/OCSP, pro… | — |
| `OD-030` | DEC-017 | Полный ЭДО/биллинг по умолчанию вне первой очереди. Требуется owner/legal решение - границы сущностей и trigge… | RM-TECH-286 |
| `OD-031` | DEC-018 | DSP/SSP-закупка по умолчанию вне первой очереди. Требуется product/legal решение, ручное согласование и review… | — |
| `OD-032` | DEC-019 | Персонализация покупателя по умолчанию вне первой очереди. Требуется privacy/legal решение - lawful purpose и … | RM-TECH-283 |
| `OD-033` | DEC-020 | Звук в торговом зале по умолчанию вне первой очереди. Требуется business/operations safety решение и review da… | — |

## 7. Бизнес-roadmap: когда функции становятся reachable

Сейчас reachable 52 (43 UI со smoke + 9 service). Blocked-функции (27) разблокируются задачами по этапам
(гейт `MISSING-UNBLOCK` гарантирует путь у каждой):

| Этап | Функций | Функция ← задача (решение) |
|---|---|---|
| `S` | 1 | `device.onboard` ← RM-TECH-210 (OD-038) |
| `CORE` | 5 | `campaign.readiness` ← RM-TECH-249; `campaign.schedule` ← RM-TECH-248; `campaign.underdelivery` ← RM-TECH-201 (OD-040); `data.catalog` ← RM-TECH-251 (OD-040); `inventory.priority` ← RM-TECH-202 (OD-040) |
| `U` | 1 | `self.campaign_create` ← RM-BIZ-002 (OD-005) |
| `CH` | 8 | `playlist.build` ← RM-TECH-207B; `license.view` ← RM-TECH-208; `license.upload` ← RM-TECH-208; `content.dynamic_binding` ← RM-TECH-262; `field_ops.device_confirm` ← RM-TECH-263; `carrier.manage` ← RM-TECH-255/RM-TECH-207A (OD-040); `channel.register` ← RM-TECH-207A/RM-TECH-244 (OD-040); `channel.rendition_validate` ← RM-TECH-204/RM-TECH-207A (OD-040) |
| `A` | 10 | `self.report_view` ← RM-BIZ-003; `analytics.compare` ← RM-UX-010; `attribution.lift_report` ← RM-TECH-282; `campaign.competitive_separation` ← RM-TECH-285; `experiment.evaluate` ← RM-TECH-284; `finance.exchange` ← RM-TECH-286; `finance.reconcile` ← RM-TECH-286; `integration.reconcile` ← RM-TECH-281; `kpi.review` ← RM-TECH-256; `placement.audience_targeting` ← RM-TECH-283 |
| `POPS` | 2 | `release.rollback` ← RM-OPS-004; `rollout.rollback` ← RM-OPS-004 |

Статус `reachable` присваивается только по зелёному UI-smoke/behavioral (правило 7), `done` задачи — только по
verified evidence и после гейта этапа; walkthrough (правило 8) закрывает Gate-U, а не отдельные функции.

## 8. Критические цепочки (глубина зависимостей от Gate-S)

- Pilot/production: `Gate-U → RM-PILOT-001 → RM-PILOT-002 → RM-PILOT-003 → RM-OPS-001 (→ RM-OPS-003)` — глубина 28–29; держат Gate-U (walkthrough, OD-041) и OD-025/OD-028.
- Attribution: `RM-TECH-220 → 229 → 280 → 281 → 282 → 284` — глубина 23; держит OD-014.
- KSO chain: `RM-TECH-207A → 207B` (глубина 19) → `260`, `208`, `262/264` (после RM-TECH-280), `playlist.build`/`device.onboard` reachable.
- Portal: `RM-UX-001 → … → RM-UX-007` — глубина 24; приостановлено OD-041.
- Master-data: `RM-TECH-229 → 280 → 262/264/281/285` — разблокировано OD-023.

## 9. Выравнивание: найдено и сделано (2026-08-31)

| # | Разрыв | Действие | Требует ACCEPT |
|---|---|---|---|
| 1 | Этапы E0/CORE/CH/A/POPS без acceptance gate (ТЗ K: каждый этап имеет вход/выход/acceptance) | добавлены Gate-E0 (owner, приёмка RM-ENV-003; историческая пометка о RM-ENV-001 done 2026-08-26 — по заключению Codex), Gate-CORE (codex), Gate-CH (owner), Gate-A (codex), Gate-POPS (owner) | да |
| 2 | AG требует все артефакты до разработки, roadmap держал NFR (A), retention (POPS), role-scope/journeys (U), data classes (CORE) после старта | перенос RM-TECH-205/288/253, RM-OPS-005, RM-UX-011 в C; Gate-C: входные условия (10 артефактов AG приняты, contract tests, сверка Codex) отделены от решения (ТЗ APPROVED, старт разработки) — поля `decision`/`note` в схеме гейта | да |
| 3 | channel-capability-matrix (AG) держится за OD-021 (второй канал) — блокирует APPROVED | новая RM-TECH-231: матрица для KSO без OD-021; RM-TECH-261 расширяет | да (proposed) |
| 4 | 6 blocked-функций без `feature_ids` у разблокирующих задач (бизнес ↔ техническая roadmap) | feature_ids у RM-BIZ-002/003, RM-TECH-207B/208/210 | нет |
| 5 | RM-TECH-263 `blocked` по зависимости, а не решению; RM-TECH-284 без названного OD | 263 → planned; 284 → «blocked OD-014» | нет |
| 6 | REQ-BIZ-009/V26-006/INT-003 `planned` при единственной blocked-задаче | → blocked (OD-030/OD-026); правило «REQ blocked ⇔ все задачи blocked по open OD» в карте | нет |
| 7 | owner/human-приёмки без ref (RM-STAB-003, RM-OPS-001, RM-PILOT-003, RM-UX-007) | refs добавлены; RM-GOV-005 (done) не трогается | нет |
| 8 | Дополнение AN — снимок 2026-08-27 с `UNMAPPED`, противоречил roadmap | r428: пометка «снимок» + актуальные задачи; AG — соответствие артефакт→задача | нет (ненормативные разделы) |
| 9 | RM-UX-007/walkthrough | приостановлены OD-041, не закрыты | — |

Не тронуто: нормативные §6/§25/§26/AP ТЗ; done-задачи; registry-статусы; код продукта.

## 10. Что дальше

1. Codex — независимая проверка этого плана и diff SSOT (roadmap/registry/traceability/ТЗ r428).
2. Владелец — ACCEPT RM-GOV-012 (гейты, переносы в C, RM-TECH-231), решения по OD-009/OD-021/OD-014 либо явное «остаётся blocked».
3. Commit/push по разрешению владельца; CI-evidence.
4. Стадия C → решение Gate-C (ТЗ APPROVED) → разработка CORE; RM-UX-007/walkthrough возобновляются по решению владельца.

# A3 — кандидатный task breakdown ТЗ v2.6 (r421) на основе A1

> ⚠️ **НЕ КАНОН, НЕ ROADMAP** · тип: кандидат очереди для owner ACCEPT · SHA: `develop @ d8b6872` + рабочее дерево
> · дата: 2026-08-28 · автор: Claude Code · основание: указание владельца 2026-08-28 (7 пунктов)
> · машинный источник: `2026-08-28-a3-task-breakdown.candidate.yaml` (счётчики ниже вычислены из него)
> · открытых решений владельца: 4 (§6) · Отменён: —
>
> `roadmap.yaml` не изменён, ничего не закоммичено. Применение — задача `RM-GOV-009` (owner gate `canon_change`).

## 0. Счётчики покрытия

| Показатель | Значение |
|---|---|
| REQ без roadmap-задачи до A3 | **51** |
| REQ без задачи после A3 | **0** (51/51 покрыты) |
| Новых задач | **64** — по фазам: Governance 5, Environment 2, Stabilization 6, Contracts 11, Core 16, Analytics/Scale 11, Portal 3, Channels 6, Production 4 |
| Статусы новых задач | verification 2, planned 47, blocked 15 (`done` — нигде) |
| Owner gates | canon_change 2, scope_decision 6, device_contract 3, migration_application 4, protected_boundary 1, deployment 1 |
| Существующих задач проверено на r421 | 43; с замечанием 19: конфликт-канон 1, редакция 3, согласовано 5, уточнение 10 |
| Перестановка стадий (BT → C/CORE/U/CH/A/S) | 14 задач; переназначение зависимости Gate-U → Gate-S: 6 |
| Новые registry ID (создаются при ACCEPT, статус blocked/planned) | 15: `analytics.compare`, `attribution.lift_report`, `campaign.competitive_separation`, `campaign.readiness`, `campaign.schedule`, `content.dynamic_binding`, `experiment.evaluate`, `field_ops.device_confirm`, `finance.exchange`, `finance.reconcile`, `integration.reconcile`, `kpi.review`, `placement.audience_targeting`, `release.rollback`, `rollout.rollback` |
| Задач с blocked-статусом (ждут OD) | 15 |

## 1. Порядок фаз (указание владельца) и стадии roadmap

| # | Фаза | stage ID | Существующий? | Гейт |
|---|---|---|---|---|
| 0 | Governance | `G` | да | Gate-G (approved 2026-08-26) |
| 1 | Environment | `E0` | да | — |
| 2 | Stabilization | `S` | да | Gate-S |
| 3 | Contracts | `C` | **новый** | Gate-C (новый: contracts/OpenAPI/ERD) |
| 4 | Core | `CORE` | **новый** | — |
| 5 | Portal | `U` | да | Gate-U |
| 6 | Channels | `CH` | **новый** | — |
| 7 | Analytics/Scale | `A` | **новый** | — |
| 8 | Production | `POPS` | да | owner gate deployment |

Стадия `BT` («Бизнесовые и технические разрывы») расформировывается: её 14 задач переезжают по фазам (§3), ID и история сохраняются (уточнение при применении: RM-BIZ-003 → A и RM-TECH-208 → CH, т.к. зависят от RM-TECH-207B в CH; STAGE-ORDER schema-check). Схема: `stage` enum += `C, CORE, CH, A`; `STAGE_ORDER` в schema-check; опциональное поле `owner_role` у задачи. Стадия `U` (Portal) по порядку владельца идёт **после** Core, поэтому у шести задач Core/Contracts зависимость `Gate-U` переназначается на `Gate-S` (§3) — иначе Core ждёт Portal.

## 2. Проверка существующих 43 задач на противоречия с r421

Done-задачи (`RM-GOV-001…006`, `RM-ENV-001`, `RM-STAB-001/002`) не редактируются — задним числом ничего не меняется. Остальные 34 сверены с §6/§9/§11/§12/§23/§25 и OD-001…036. Без замечаний: 15. С замечаниями:

| Задача | Вердикт | Предложение (ID сохраняется) |
|---|---|---|
| `RM-STAB-003` | **уточнение** | добавить ссылки OD-035/DEC-023 (Q2: 7 ролей) и REQ-UX-001; acceptance без изменений |
| `RM-STAB-006` | **редакция** | число «45/45» не подтверждено текстом r421 (AP: 41 story, registry 58 ID, journeys.md без числа 45) → acceptance: «все UI-journeys registry имеют нормативный формат; N вычисляется из registry»; ID и история сохраняются |
| `RM-STAB-010` | **уточнение** | добавить alias DEC-003/OD-002, REQ-MAN-002/SEC-003 |
| `RM-STAB-011` | **уточнение** | STAND-001/002 перепривязать на RM-ENV-002 после ACCEPT |
| `RM-BIZ-001` | **уточнение** | ссылки OD-005/DEC-011, REQ-SCOPE-001 |
| `RM-BIZ-002` | **редакция** | REQ-V26-003 и OD-013: полный self-service вне pilot scope → delivery_status planned→blocked (OD-013), deps += OD-013; ID сохранён |
| `RM-TECH-201` | **согласовано** | 8 категорий = REQ-BIZ-008 (technical/operational/business/emergency/content/planning/device/store) |
| `RM-TECH-202` | **уточнение** | REQ-BIZ-007 и порядок приоритета §12; исключение §3.1 (OD-018) — единственная точка изменения engine → RM-TECH-285 зависит от неё |
| `RM-TECH-203` | **согласовано** | default deny = §12/§5.1 «overbooking запрещён, только после owner-approved policy»; REQ-BIZ-001/016 |
| `RM-TECH-204` | **согласовано** | OD-034/DEC-021; REQ-CONT-001 |
| `RM-TECH-205` | **уточнение** | REQ-NFR-001/006/007; пороги ждут OD-011/OD-009 — добавить в notes; артефакты AG выносятся в RM-TECH-288 |
| `RM-TECH-207A` | **уточнение** | REQ-STAND-003 feasibility gate явно в acceptance; ADR-019/OD-022 |
| `RM-TECH-207B` | **редакция** | acceptance дополнить: Playlist entity/state machine §6 (сейчас нет), manifest target lifecycle, canonical /api/v1/pop/batch; REQ-MAN-001/003/005, REQ-POP-*; device_contract gate уже есть |
| `RM-TECH-209` | **согласовано** | ADR-007/REQ-NFR-004: PostgreSQL до owner gate |
| `RM-TECH-210` | **конфликт-канон** | r421 §11: device.onboard/field ops/device pilot = blocked до PostgreSQL runtime-role evidence; feature-registry держит device.onboard reachable. Предложение: registry device.onboard → blocked + blocked_features(unblocked_by RM-TECH-210) — решение владельца, не агента (CLAUDE.md: contradiction → STOP) |
| `RM-BIZ-003` | **уточнение** | REQ-BIZ-011; зависит от RM-TECH-207B (реальные PoP) — без изменений |
| `RM-PILOT-001` | **уточнение** | deps += OD-024 (exit criteria ступеней), REQ-ARCH-004 |
| `RM-OPS-001` | **уточнение** | зависит от OD-025 (RTO/RPO) и OD-028 (топология); REQ-OPS-005/006; HA baseline выделен в RM-OPS-003 |
| `RM-UX-007` | **согласовано** | REQ-UX-002 human walkthrough |

**Единственный конфликт канона** — `RM-TECH-210`: registry `device.onboard: reachable` против r421 §11 «blocked до runtime-role evidence». По CLAUDE.md это STOP: решение владельца, предложение записано в таблице.

## 3. Перестановка стадий существующих задач

| Задача | Было | Станет | Зависимость |
|---|---|---|---|
| `RM-TECH-201` | `BT` | `CORE` (Core) | Gate-U → Gate-S (Core/Contracts идут до Portal по порядку владельца) |
| `RM-TECH-202` | `BT` | `CORE` (Core) | без изменений |
| `RM-TECH-203` | `BT` | `CORE` (Core) | без изменений |
| `RM-TECH-204` | `BT` | `CORE` (Core) | Gate-U → Gate-S (Core/Contracts идут до Portal по порядку владельца) |
| `RM-TECH-206` | `BT` | `CORE` (Core) | Gate-U → Gate-S (Core/Contracts идут до Portal по порядку владельца) |
| `RM-TECH-208` | `BT` | `CH` (Channels) | без изменений |
| `RM-TECH-205` | `BT` | `A` (Analytics/Scale) | Gate-U → Gate-S (Core/Contracts идут до Portal по порядку владельца) |
| `RM-TECH-209` | `BT` | `A` (Analytics/Scale) | без изменений |
| `RM-TECH-207A` | `BT` | `CH` (Channels) | Gate-U → Gate-S (Core/Contracts идут до Portal по порядку владельца) |
| `RM-TECH-207B` | `BT` | `CH` (Channels) | без изменений |
| `RM-TECH-210` | `BT` | `S` (Stabilization) | без изменений |
| `RM-BIZ-001` | `BT` | `CORE` (Core) | Gate-U → Gate-S (Core/Contracts идут до Portal по порядку владельца) |
| `RM-BIZ-002` | `BT` | `U` (Portal) | без изменений |
| `RM-BIZ-003` | `BT` | `A` (Analytics/Scale) | без изменений |

## 4. Новые задачи по фазам

Поля: REQ/SC/DEC — из A1 (SC и DEC подтягиваются по REQ автоматически); owner — роль (имя назначает владелец, RM-GOV-010); статус — `planned`, `blocked` (ждёт OD) или `verification` (факт выполнен, ждёт ACCEPT); evidence — что будет приложено; риск — регрессии.

### 0. Governance (`G`) — 5 задач

**`RM-GOV-007`** — Единый реестр решений (A2): DEC как alias owner_decisions, модуль guard decisions  
- kind `governance` · статус `verification` · owner: PMO/Claude Code
- REQ: `REQ-GOV-003` · SC: `SC-GOV-004` · DEC: —
- зависимости: `RM-GOV-005`
- acceptance (`ci_job`): 27/27 DEC §29 представлены alias ровно одного OD; guard decisions зелёный
- evidence: ci_run 33164564954 (b0f9cdb); docs/audit/2026-08-28-claude-a2-decision-registry.md
- риск регрессии: низкий: только docs/scripts
- примечание: факт выполнен 2026-08-28 по указанию владельца; done — после owner ACCEPT (EVIDENCE-KIND ci_run есть)

**`RM-GOV-008`** — Трассировка требований (A1): requirements-traceability.yaml + модуль guard req  
- kind `governance` · статус `verification` · owner: Product+Technical owner/Claude Code
- REQ: `REQ-GOV-002`, `REQ-GOV-003` · SC: `SC-GOV-003`, `SC-GOV-004` · DEC: —
- зависимости: `RM-GOV-007`
- acceptance (`ci_job`): 101 REQ, 69 SC, 58/58 registry ID трассированы; guard req зелёный
- evidence: ci_run 33166246511 (d8b6872); docs/audit/2026-08-28-claude-a1-requirements-traceability.md
- риск регрессии: низкий
- примечание: факт выполнен 2026-08-28; done — после owner ACCEPT

**`RM-GOV-009`** — Task breakdown A3 → roadmap.yaml: новые стадии C/CORE/CH/A, перестановка BT, schema stage enum  
- kind `governance` · статус `planned` · owner: Product/PMO owner · owner gate `canon_change`
- REQ: `REQ-GOV-003` · SC: `SC-GOV-004` · DEC: —
- зависимости: `RM-GOV-008`
- acceptance (`command`): все 101 REQ имеют roadmap_ids или approved deferred; traceability без task_required
- acceptance (`owner`): владелец принял очередь (ACCEPT с SHA)
- evidence: check-roadmap-schema PASS; guard req/decisions PASS; ci_run
- риск регрессии: средний: STAGE_ORDER/schema enum и генерируемые проекции

**`RM-GOV-010`** — Owner/RACI для REQ и SC (170 TBD) и mapping 23 PENDING-ID journeys  
- kind `governance` · статус `planned` · owner: Product owner · owner gate `scope_decision`
- REQ: `REQ-GOV-002` · SC: `SC-GOV-003` · DEC: —
- зависимости: `RM-GOV-008`
- acceptance (`command`): 0 полей TBD в traceability; pending_journey_map без awaiting_owner
- acceptance (`owner`): назначения подтверждены владельцем
- evidence: traceability diff; guard req
- риск регрессии: низкий

**`RM-GOV-011`** — Правила агентов и приёмки: ADR-020 в индекс, Done Gate ↔ §27 DoD требования  
- kind `governance` · статус `planned` · owner: Owner/Claude Code · owner gate `canon_change`
- REQ: `REQ-GOV-001` · SC: `SC-GOV-005` · DEC: —
- зависимости: `RM-GOV-006`
- acceptance (`artifact`): индекс Sources of Truth содержит ADR-020; §27 DoD REQ отражён в Done Gate AGENTS.md
- evidence: guard doc PASS; diff AGENTS.md
- риск регрессии: низкий

### 1. Environment (`E0`) — 2 задач

**`RM-ENV-002`** — Стенд: seed/reset в утверждённое время и точный демо-состав  
- kind `implementation` · статус `planned` · owner: Operations owner
- REQ: `REQ-STAND-001`, `REQ-STAND-002` · SC: `SC-STAND-001`, `SC-STAND-002` · DEC: —
- зависимости: `RM-ENV-001`
- acceptance (`command`): seed/reset воспроизводим, время до smoke-набора измерено и ≤ owner target
- acceptance (`behavioral`): подсчёт по БД совпадает с §25 REQ-STAND-002 (10/50/500; 2000 KSO …)
- acceptance (`command`): в seed нет реальных PII/tokens/договоров
- evidence: tests/test_local_stand.py; scripts/dev seed report
- риск регрессии: средний: массовый seed может ломать существующие smoke-фикстуры
- примечание: в A1 STAND-001/002 временно привязаны к RM-STAB-011 — после ACCEPT перепривязать сюда

**`RM-ENV-003`** — DEV environment manifest (AG): endpoint/версии/SHA/schema/доступность + seed/reset  
- kind `governance` · статус `planned` · owner: Operations owner
- REQ: `REQ-ARCH-004` · SC: `SC-OPS-001` · DEC: `DEC-015`
- зависимости: `RM-ENV-001`, `RM-ENV-002`
- acceptance (`command`): environment-inventory.yaml содержит поля AG для DEV/.81; guard env зелёный
- evidence: guard env; inventory diff
- риск регрессии: низкий

### 2. Stabilization (`S`) — 6 задач

**`RM-STAB-012`** — Async I/O boundary: детектор blocking I/O в async handlers (ADR-012)  
- kind `implementation` · статус `planned` · owner: Technical owner
- REQ: `REQ-ARCH-003` · SC: `SC-ARCH-005` · DEC: —
- зависимости: `RM-STAB-009`
- acceptance (`command`): статический/рантайм-детектор красный на blocking I/O без threadpool; текущий код чист
- evidence: tests/test_api_tx_boundary.py; новый lint/pytest
- риск регрессии: средний: может вскрыть существующие blocking-вызовы

**`RM-STAB-013`** — API attack protection: runtime negative suite (schema/size, IDOR, CSRF/XSS, SSRF, rate limit, headers, no secrets in logs)  
- kind `implementation` · статус `planned` · owner: Security owner
- REQ: `REQ-SEC-006` · SC: `SC-SEC-004` · DEC: —
- зависимости: `RM-STAB-002`
- acceptance (`behavioral`): каждый control имеет negative-тест: красный при отключении, зелёный при включении
- acceptance (`behavioral`): 429 + Retry-After по endpoint и principal; audit rate-limit
- evidence: tests/test_s065_rate_limit.py; tests/test_phase3_security.py; новый negative suite
- риск регрессии: средний: ужесточение headers/CORS может сломать admin-web/advertiser-web

**`RM-STAB-014`** — Полнота аудита критичных действий и реальный actor (user/service/device)  
- kind `implementation` · статус `planned` · owner: Security owner
- REQ: `REQ-SEC-005` · SC: `SC-SEC-003` · DEC: —
- зависимости: `RM-STAB-002`
- acceptance (`behavioral`): реестр критичных действий ↔ audit events 100%; anonymous/подставной actor отклонён
- evidence: tests/ui-smoke/test_uismoke__audit__view.py; новый behavioral
- риск регрессии: низкий

**`RM-STAB-015`** — Control plane системного администратора: отдельные permission-коды и scope  
- kind `implementation` · статус `planned` · owner: Security owner
- REQ: `REQ-SEC-009` · SC: `SC-SEC-007` · DEC: —
- зависимости: `RM-STAB-004`
- acceptance (`behavioral`): users/roles/devices/settings/monitoring/audit — отдельные коды; approved campaign без отдельного права не меняется
- evidence: tests/test_phase3_user_management.py; tests/test_s019_role_safety.py
- риск регрессии: средний: миграция permission-кодов затрагивает seed ролей (RM-STAB-004)

**`RM-STAB-016`** — Object storage boundary: приватные buckets, presigned TTL, ограниченные service accounts  
- kind `implementation` · статус `planned` · owner: Security owner
- REQ: `REQ-SEC-007` · SC: `SC-SEC-005` · DEC: —
- зависимости: `RM-ENV-001`
- acceptance (`behavioral`): анонимный доступ запрещён; просроченный presigned URL отклонён
- evidence: tests/test_storage_service.py; tests/integration/test_minio_upload.py
- риск регрессии: низкий

**`RM-STAB-017`** — Независимость production от внешнего runtime: production smoke при выключенных dashboard/LLM-агентах  
- kind `implementation` · статус `planned` · owner: Technical owner
- REQ: `REQ-ARCH-002` · SC: `SC-ARCH-004` · DEC: `DEC-014`
- зависимости: `RM-STAB-009`
- acceptance (`command`): полный production smoke проходит без внешних наблюдателей; ни один сервис не вызывает внешний runtime (egress allow-list)
- evidence: tests/test_production_config_gate.py; egress check
- риск регрессии: низкий
- примечание: monitoring-dashboard — read-only наблюдатель (OD-027), не зависимость

### 3. Contracts (`C`) — 11 задач

**`RM-TECH-220`** — OpenAPI + event/manifest JSON Schema (AG): as-built генерация + target из §26/AB, contract tests  
- kind `implementation` · статус `planned` · owner: Technical owner
- REQ: `REQ-ARCH-001`, `REQ-API-001` · SC: `SC-API-001`, `SC-ARCH-003` · DEC: —
- зависимости: `Gate-S`
- acceptance (`command`): OpenAPI/event schemas версионированы, examples и deprecation policy; contract tests зелёные
- acceptance (`behavioral`): одна canonical opaque идентификация на версию API; alias {id} с deprecation date
- evidence: generated openapi.json diff; contract tests
- риск регрессии: средний: выявит смешение {id}/{code}

**`RM-TECH-221`** — Разделение User/Device/analytics/emergency API; device client не достигает admin  
- kind `implementation` · статус `planned` · owner: Security owner
- REQ: `REQ-API-002` · SC: `SC-API-002` · DEC: —
- зависимости: `RM-TECH-220`
- acceptance (`behavioral`): device JWT → admin endpoint = 403 на всех admin-роутах
- evidence: tests/test_phase3_protected_identity.py; новый negative
- риск регрессии: низкий

**`RM-TECH-222`** — Канонический POST /api/v1/pop/batch, legacy /device/pop/batch как alias с deprecation  
- kind `implementation` · статус `planned` · owner: Technical owner
- REQ: `REQ-API-003`, `REQ-POP-003` · SC: `SC-API-003`, `SC-POP-003` · DEC: —
- зависимости: `RM-TECH-220`
- acceptance (`behavioral`): ответы канонического и legacy идентичны; deprecation header; batch>500 → 422; чужой device_id отклонён
- evidence: tests/test_contract_pop.py; tests/behavioral/test_edge002fu_real_endpoint.py
- риск регрессии: средний: runtime/плеер использует legacy path

**`RM-TECH-223`** — Manifest field contract и ACK-состояния runtime (opaque media_ref, no MinIO keys)  
- kind `implementation` · статус `planned` · owner: Technical owner · owner gate `device_contract`
- REQ: `REQ-MAN-004` · SC: `SC-MAN-001` · DEC: —
- зависимости: `RM-TECH-220`
- acceptance (`behavioral`): все обязательные поля §25 REQ-MAN-004 в schema; внутренний object key не раскрыт; 6 ACK states принимаются
- evidence: tests/test_contract_manifest.py; tests/behavioral/test_edge002_manifest_delivery.py
- риск регрессии: высокий: меняет device-facing контракт — owner gate device_contract

**`RM-TECH-224`** — Heartbeat contract POST /api/v1/device/heartbeat: дедуп, scope, clock drift, freshness thresholds  
- kind `implementation` · статус `planned` · owner: Technical owner · owner gate `device_contract`
- REQ: `REQ-OPS-009` · SC: `SC-OPS-002` · DEC: —
- зависимости: `RM-TECH-220`
- acceptance (`behavioral`): валидный/повтор/чужой scope/просроченный heartbeat дают ожидаемые результаты; legacy alias с той же семантикой
- evidence: tests/behavioral/test_edge004_heartbeat.py
- риск регрессии: высокий: device-facing

**`RM-TECH-225`** — PoP duplicate semantics по OD-019: 200 + per-event duplicate/409, amendment ADR-017  
- kind `implementation` · статус `planned` · owner: Technical owner
- REQ: `REQ-POP-002` · SC: `SC-POP-002` · DEC: `DEC-024`
- зависимости: `RM-TECH-222`
- acceptance (`behavioral`): ADR-017 amendment принят; behavioral: повтор batch → per-event duplicate, summary не удвоен, порядок хронологический
- evidence: tests/behavioral/test_edge003_pop_ingestion.py; ADR-017 amendment
- риск регрессии: низкий: закрепляет текущее поведение

**`RM-TECH-226`** — Proof model: pop_mode error/not_applied — schema/runtime migration из compatibility projection  
- kind `implementation` · статус `planned` · owner: Technical owner · owner gate `migration_application`
- REQ: `REQ-POP-001` · SC: `SC-POP-001` · DEC: —
- зависимости: `RM-TECH-225`
- acceptance (`behavioral`): ProofMode содержит 9 значений; отчёт не смешивает playback/apply/delivery/error
- evidence: tests/behavioral/test_pop_schema.py; migration
- риск регрессии: средний: enum migration + отчёты

**`RM-TECH-227`** — Валидация proof_event_v1: playback_result/failure_reason, clock-drift quarantine, no internal IDs/PII  
- kind `implementation` · статус `planned` · owner: Security owner
- REQ: `REQ-POP-004` · SC: `SC-POP-004` · DEC: —
- зависимости: `RM-TECH-225`
- acceptance (`behavioral`): недопустимый playback_result/внутренний ID/сдвиг часов → 422 или quarantine; SHA/signature проверены
- evidence: tests/test_contract_pop.py; tests/behavioral/test_pop_schema.py
- риск регрессии: средний

**`RM-TECH-228`** — Окно совместимости device/API/manifest: heartbeat объявляет версии, сервер выбирает представление  
- kind `implementation` · статус `planned` · owner: Technical owner
- REQ: `REQ-NFR-003` · SC: `SC-NFR-003` · DEC: —
- зависимости: `RM-TECH-224`
- acceptance (`behavioral`): совместимая версия выбрана по объявленным capabilities; breaking change без staged rollout отклонён contract-тестом
- evidence: tests/test_version_identity.py
- риск регрессии: средний

**`RM-TECH-229`** — ERD + data dictionary + migration plan (AG): инвентарь сущностей §15, retailer_id NOT NULL + двухуровневый RLS  
- kind `design` · статус `planned` · owner: Data/Technical owner
- REQ: `REQ-DATA-002`, `REQ-V26-001` · SC: `SC-DATA-003` · DEC: —
- зависимости: `RM-TECH-220`
- acceptance (`artifact`): as-built ERD из моделей; каждая группа §15 присутствует или имеет migration task; tenant-таблицы с retailer_id+FK+RLS
- acceptance (`behavioral`): behavioral RLS proof под ролью приложения NOBYPASSRLS
- evidence: tests/behavioral/test_adr018_multitenancy_rls.py; generated ERD
- риск регрессии: средний: backfill retailer_id

**`RM-TECH-230`** — Channel Adapter contract (design-only до второго канала): versioned task, receipt, proof/ack, error, health, mock mode  
- kind `design` · статус `planned` · owner: Architecture owner
- REQ: `REQ-ORCH-006` · SC: `SC-ORCH-005` · DEC: —
- зависимости: `RM-TECH-220`
- acceptance (`artifact`): contract spec + JSON Schema без реализации adapter/mock (ADR-019)
- evidence: docs/architecture contract; schema
- риск регрессии: низкий: только документ

### 4. Core (`CORE`) — 16 задач

**`RM-TECH-240`** — Универсальная иерархия носителей: migration + seed network/branch/cluster/store/store_group/channel/device/surface  
- kind `implementation` · статус `planned` · owner: Data owner · owner gate `migration_application`
- REQ: `REQ-CORE-001` · SC: `SC-DATA-001` · DEC: —
- зависимости: `RM-TECH-229`
- acceptance (`behavioral`): все уровни существуют с FK и RLS; seed заполняет иерархию; чужой scope не видит
- evidence: migration; tests/behavioral/test_scope_rls.py
- риск регрессии: высокий: схема ядра

**`RM-TECH-241`** — Target resolution boundary: broad target → display_surface_id, запрет physical_device_id как target  
- kind `implementation` · статус `planned` · owner: Technical owner
- REQ: `REQ-CORE-003` · SC: `SC-ARCH-002` · DEC: —
- зависимости: `RM-TECH-240`
- acceptance (`behavioral`): планирование разрешает target до surface; physical_device_id в target отклоняется
- evidence: tests/test_s089_inventory_simulation.py
- риск регрессии: средний

**`RM-TECH-242`** — Outbox для любой OLTP-записи с domain event; revocation/refresh manifest при pause/archive/expiry  
- kind `implementation` · статус `planned` · owner: Technical owner
- REQ: `REQ-ORCH-003` · SC: `SC-ORCH-002` · DEC: —
- зависимости: `RM-TECH-240`
- acceptance (`behavioral`): каждая доменная мутация создаёт outbox event в той же транзакции; pause/archive порождают revocation
- evidence: tests/behavioral/test_outbox.py
- риск регрессии: средний: транзакционные границы всех сервисов

**`RM-TECH-243`** — Outbox relay: lease/publishing, Nats-Msg-Id, 7 попыток → dead_letter, partition order, DLQ policy, no PII  
- kind `implementation` · статус `planned` · owner: Technical owner
- REQ: `REQ-ORCH-004` · SC: `SC-ORCH-003` · DEC: `DEC-004`
- зависимости: `RM-TECH-242`
- acceptance (`behavioral`): 7 отказов брокера → dead_letter с operator action; ack → published; replay идемпотентен
- acceptance (`command`): NATS recovery integration зелёный
- evidence: tests/behavioral/test_outbox_relay.py; tests/integration/test_nats_recovery.py
- риск регрессии: средний

**`RM-TECH-244`** — Adapter task lifecycle через persisted queue (event-driven массовая публикация)  
- kind `implementation` · статус `planned` · owner: Technical owner
- REQ: `REQ-ORCH-002` · SC: `SC-ORCH-006` · DEC: `DEC-004`
- зависимости: `RM-TECH-243`
- acceptance (`behavioral`): активация на 1000 устройств не ждёт устройств; задачи агрегируют статусы
- evidence: tests/behavioral/test_delivery_foundation.py
- риск регрессии: средний

**`RM-TECH-245`** — Campaign lifecycle по ADR-015/OD-036: scheduled, resume, revise, archive; единый guard и audit  
- kind `implementation` · статус `planned` · owner: Product/Technical owner · owner gate `migration_application`
- REQ: `REQ-BIZ-010` · SC: — · DEC: `DEC-025`
- зависимости: `RM-STAB-004`
- acceptance (`behavioral`): _CAMPAIGN_TRANSITIONS = ADR-015; каждый переход через guard с audit; возврат в draft создаёт revision
- acceptance (`ui_smoke`): campaign.* smokes зелёные после изменения
- evidence: tests/behavioral/test_campaign_domain.py; tests/ui-smoke/test_uismoke__campaign__*.py
- риск регрессии: высокий: меняет runtime enum кампании и UI

**`RM-TECH-246`** — Commerce order: отмена по OD-020 (draft→cancelled, confirmed — reversal), payment projection отдельно  
- kind `implementation` · статус `planned` · owner: Product owner
- REQ: `REQ-BIZ-014` · SC: — · DEC: `DEC-017`, `DEC-026`
- зависимости: `RM-STAB-004`
- acceptance (`behavioral`): _ORDER_TRANSITIONS: draft→cancelled разрешён, confirmed→cancelled запрещён, reversal с audit
- evidence: tests/test_commerce_a2.py; tests/behavioral/test_commerce_rls.py
- риск регрессии: средний

**`RM-TECH-247`** — Approval policy: required roles/scope/порядок/timeout per campaign/placement/creative  
- kind `implementation` · статус `planned` · owner: Product owner
- REQ: `REQ-BIZ-003` · SC: — · DEC: —
- зависимости: `RM-TECH-245`
- acceptance (`behavioral`): политика версионирована; submit/approve соблюдают порядок и timeout; negative для чужого scope
- evidence: tests/behavioral/test_campaign_approval.py
- риск регрессии: средний

**`RM-TECH-248`** — Flight/placement windows: versioned start_at/end_at UTC, проверка при simulation/manifest/runtime  
- kind `implementation` · статус `planned` · owner: Product owner
- REQ: `REQ-BIZ-005`, `REQ-NFR-002` · SC: `SC-NFR-002` · DEC: —
- зависимости: `RM-TECH-245`
- acceptance (`behavioral`): показ вне окна запрещён на трёх уровнях; DST/праздники/closed stores — версионированные правила
- evidence: tests/test_s063_pop_timezone.py; новый behavioral
- риск регрессии: высокий: расписание доставки
- новые registry ID: `campaign.schedule`

**`RM-TECH-249`** — Manifest eligibility: approved status + валидный flight/contract + resolved target + readiness  
- kind `implementation` · статус `planned` · owner: Technical owner
- REQ: `REQ-BIZ-006` · SC: — · DEC: —
- зависимости: `RM-TECH-248`
- acceptance (`behavioral`): неэлигибельная кампания не попадает в manifest; причина объяснима
- evidence: tests/behavioral/test_delivery_generation.py
- риск регрессии: средний
- новые registry ID: `campaign.readiness`

**`RM-TECH-250`** — Creative/rendition state machine и immutable media history (uploaded→scanning→qa_failed/approved→superseded→retained)  
- kind `implementation` · статус `planned` · owner: Content owner · owner gate `migration_application`
- REQ: `REQ-CONT-002` · SC: `SC-DATA-002` · DEC: —
- зависимости: `RM-TECH-204`
- acceptance (`behavioral`): каждая версия хранит uploader/SHA-256/QA-решение/связь; закрытый отчёт воспроизводим после logical delete
- evidence: tests/behavioral/test_creative_assets.py
- риск регрессии: средний

**`RM-TECH-251`** — Data ownership/lineage: immutable versioning и diff campaign/placement/playlist, словарь владельцев  
- kind `implementation` · статус `planned` · owner: Data owner
- REQ: `REQ-DATA-001` · SC: `SC-DATA-004` · DEC: `DEC-007`
- зависимости: `RM-TECH-229`
- acceptance (`behavioral`): сохранение создаёт версию с diff и actor; предыдущая неизменяема
- evidence: новый behavioral
- риск регрессии: средний

**`RM-TECH-252`** — Identity: AD/LDAP или SSO для internal staff, MFA до production (OD-008)  
- kind `implementation` · статус `planned` · owner: Security owner · owner gate `protected_boundary`
- REQ: `REQ-SEC-001` · SC: `SC-SEC-008` · DEC: —
- зависимости: `RM-STAB-004`
- acceptance (`behavioral`): логин через IdP; production-профиль без MFA отклоняет; TLS-профиль зафиксирован
- evidence: tests/test_phase3_auth_api.py; tests/behavioral/test_auth_dual_e2e.py
- риск регрессии: высокий: вход всех пользователей

**`RM-TECH-253`** — Data protection: data classes, lawful purpose, минимизация PII, residency; retention по OD-009  
- kind `design` · статус `planned` · owner: Security/Legal owner
- REQ: `REQ-SEC-004` · SC: `SC-SEC-011` · DEC: `DEC-007`
- зависимости: `RM-TECH-229`
- acceptance (`artifact`): реестр data classes для всех сущностей; новая PII-сущность без класса — красный design-gate
- evidence: docs/architecture data classes
- риск регрессии: низкий

**`RM-TECH-254`** — Emergency state machine: requested→authorized→dispatching→applied→resuming→closed, MFA+reason, приоритетный канал  
- kind `implementation` · статус `planned` · owner: Operations owner
- REQ: `REQ-OPS-007` · SC: `SC-OPS-003` · DEC: —
- зависимости: `RM-TECH-245`
- acceptance (`behavioral`): emergency с причиной; per-target result; audit actor/reason/affected; resume возвращает штатный manifest
- acceptance (`ui_smoke`): emergency.* smokes зелёные
- evidence: tests/test_phase3_emergency_api.py; tests/ui-smoke/test_uismoke__emergency__activate.py
- риск регрессии: высокий: аварийный контур

**`RM-TECH-255`** — Device health/commands: пороги статусов по профилю, per-device view, команды с подтверждением  
- kind `implementation` · статус `planned` · owner: Operations owner
- REQ: `REQ-OPS-001` · SC: `SC-OPS-006` · DEC: —
- зависимости: `RM-TECH-224`
- acceptance (`behavioral`): online→degraded→offline по порогам; команда доставлена и подтверждена
- acceptance (`ui_smoke`): device.health_view smoke зелёный
- evidence: tests/ui-smoke/test_uismoke__device__health_view.py
- риск регрессии: средний

### 5. Portal (`U`) — 3 задач

**`RM-UX-008`** — Campaign readiness matrix по каналам (rendition/inventory/conflicts/forecast/PoP mode/SLA) с действием на blocked  
- kind `implementation` · статус `planned` · owner: Product/UX owner
- REQ: `REQ-UX-004` · SC: `SC-UX-002` · DEC: —
- зависимости: `RM-TECH-249`, `RM-UX-004`
- acceptance (`ui_smoke`): экран согласования показывает матрицу; каждый blocked/warning ведёт к действию
- evidence: новый ui-smoke; vitest
- риск регрессии: средний

**`RM-UX-009`** — Договор рекламодателя: immutable file versions, server-side SHA-256, legal status (юр. решение)  
- kind `implementation` · статус `planned` · owner: Product owner
- REQ: `REQ-BIZ-017` · SC: — · DEC: —
- зависимости: `RM-TECH-250`
- acceptance (`behavioral`): повторная загрузка создаёт новую версию, SHA проверен сервером; старая версия неизменяема
- acceptance (`ui_smoke`): advertiser.contract_crud smoke зелёный
- evidence: tests/test_advertiser_contracts.py; tests/ui-smoke/test_uismoke__advertiser__contract_pdf_upload.py
- риск регрессии: низкий

**`RM-UX-011`** — role-scope-matrix.yaml + portal-route-matrix.yaml + journeys/ (AG) из seed/pg_policies/registry  
- kind `governance` · статус `planned` · owner: Security + Product/UX owner
- REQ: `REQ-UX-001`, `REQ-SEC-002` · SC: `SC-SEC-009` · DEC: `DEC-023`
- зависимости: `RM-STAB-004`, `RM-STAB-006`
- acceptance (`command`): матрицы генерируются и сверяются guard; deny-cases покрыты behavioral
- evidence: generated matrices; guard registry
- риск регрессии: низкий

### 6. Channels (`CH`) — 6 задач

**`RM-TECH-260`** — Runtime cache lifecycle: лимит по профилю, детерминированная очистка, last-known-good  
- kind `implementation` · статус `planned` · owner: Channel owner · owner gate `device_contract`
- REQ: `REQ-OPS-008` · SC: `SC-EDGE-002` · DEC: —
- зависимости: `RM-TECH-207B`
- acceptance (`behavioral`): кэш на лимите: очистка по правилу; last-known-good сохранён; просроченная реклама не показывается
- evidence: runtime simulator tests
- риск регрессии: средний: плеер

**`RM-TECH-261`** — Второй канал: решение OD-021 + channel-capability-matrix.yaml (AG); extraction design по ADR-019  
- kind `design` · статус `blocked` · owner: Channel owner · owner gate `scope_decision`
- REQ: `REQ-CHAN-001`, `REQ-ORCH-005` · SC: `SC-CHAN-002`, `SC-ORCH-004` · DEC: `DEC-001`, `DEC-002`
- зависимости: `RM-TECH-207B`, `RM-TECH-230`
- acceptance (`owner`): владелец назвал канал и владельца (OD-021); матрица возможностей утверждена
- acceptance (`artifact`): extraction design: KSO-вертикаль как первый adapter без поломки контрактов
- evidence: OD-021; design doc
- риск регрессии: высокий: рефакторинг KSO-вертикали
- примечание: blocked до OD-021; Orchestrator/Adapter Layer/mock не создаются раньше (ADR-019/OD-022)

**`RM-TECH-262`** — Dynamic creative binding/rendition safety (V26-008) на одном канале  
- kind `implementation` · статус `blocked` · owner: Content/Channel owner
- REQ: `REQ-V26-008` · SC: — · DEC: `DEC-005`
- зависимости: `RM-TECH-280`, `RM-TECH-261`
- acceptance (`behavioral`): master-confirmed price/promo подставляется при manifest generation; SLA-тест dynamic manifest
- evidence: new behavioral
- риск регрессии: высокий
- новые registry ID: `content.dynamic_binding`
- примечание: blocked: ложная ESL-посылка, master adapter (OD-023)

**`RM-TECH-263`** — Field mobile operations: scoped mobile web для сотрудника магазина (устройства, фото, инциденты)  
- kind `implementation` · статус `blocked` · owner: Operations/UX owner
- REQ: `REQ-V26-009` · SC: — · DEC: —
- зависимости: `RM-TECH-210`, `RM-TECH-255`
- acceptance (`ui_smoke`): journey field_ops.device_confirm под ролью магазина с RLS; negative чужой магазин
- evidence: new ui-smoke
- риск регрессии: средний
- новые registry ID: `field_ops.device_confirm`
- примечание: blocked RM-TECH-210

**`RM-TECH-264`** — ESL/price-checker: интеграция только через approved price/SKU master (INT-002)  
- kind `implementation` · статус `blocked` · owner: Channel/Data owner
- REQ: `REQ-INT-002` · SC: — · DEC: `DEC-005`
- зависимости: `RM-TECH-280`
- acceptance (`behavioral`): price-related данные приходят из master или проходят reconciliation; расхождение блокирует показ
- evidence: new behavioral
- риск регрессии: высокий
- примечание: blocked OD-023

**`RM-TECH-280`** — Prerequisite: master-data adapter цен/SKU (контракт, owner OD-023, reconciliation)  
- kind `design` · статус `blocked` · owner: Data owner (OD-023) · owner gate `scope_decision`
- REQ: `REQ-INT-002` · SC: — · DEC: `DEC-005`
- зависимости: `RM-TECH-229`
- acceptance (`owner`): владелец master-данных назначен (OD-023 approved); contract + reconciliation design утверждены
- acceptance (`behavioral`): adapter в mock/test mode проходит contract tests
- evidence: OD-023; contract tests
- риск регрессии: средний
- примечание: отсутствующий prerequisite по AQ.1 №5; blocked до имени владельца

### 7. Analytics/Scale (`A`) — 11 задач

**`RM-TECH-256`** — Business outcome KPI: baseline/target/metric definition для целей §1.2 (OD-024 exit criteria)  
- kind `governance` · статус `planned` · owner: Product owner · owner gate `scope_decision`
- REQ: `REQ-BIZ-013` · SC: — · DEC: `DEC-010`
- зависимости: `RM-TECH-205`
- acceptance (`owner`): каждая бизнес-цель имеет baseline/target/формулу/владельца, утверждено владельцем
- evidence: artifact kpi register
- риск регрессии: низкий
- новые registry ID: `kpi.review`

**`RM-UX-010`** — Service-quality reporting: доля active devices/logical carriers, plan/fact по каналу (analytics.compare)  
- kind `implementation` · статус `planned` · owner: Product owner
- REQ: `REQ-BIZ-004` · SC: — · DEC: —
- зависимости: `RM-BIZ-003`
- acceptance (`ui_smoke`): отчёт по каналу с долями и причинами; RLS scope advertiser
- evidence: новый ui-smoke; tests/behavioral/test_pop_reporting_scope.py
- риск регрессии: средний
- новые registry ID: `analytics.compare`

**`RM-TECH-281`** — Prerequisite: sales-reference ingestion (агрегаты store/SKU/day) + методология baseline/test-control  
- kind `implementation` · статус `blocked` · owner: Analytics owner
- REQ: `REQ-INT-001` · SC: — · DEC: —
- зависимости: `RM-TECH-280`
- acceptance (`behavioral`): пакетная загрузка агрегатов без PII; versioned baseline; методика утверждена владельцем
- evidence: new behavioral; methodology doc
- риск регрессии: средний
- новые registry ID: `integration.reconcile`
- примечание: blocked RM-TECH-280

**`RM-TECH-282`** — Attribution & sales lift: test/control, versioned baseline, pilot lift report  
- kind `implementation` · статус `blocked` · owner: Analytics/Product owner
- REQ: `REQ-V26-002` · SC: — · DEC: `DEC-005`, `DEC-027`
- зависимости: `RM-TECH-281`, `RM-TECH-229`
- acceptance (`behavioral`): pilot lift report по test/control с explainable методикой; RLS scope
- evidence: new behavioral; report
- риск регрессии: средний
- новые registry ID: `attribution.lift_report`

**`RM-TECH-283`** — Prerequisite: audience source/privacy contract (анонимные store-атрибуты, 152-ФЗ, OD-032)  
- kind `design` · статус `blocked` · owner: Data/Legal owner · owner gate `scope_decision`
- REQ: `REQ-V26-005` · SC: — · DEC: `DEC-005`, `DEC-019`
- зависимости: `RM-TECH-280`, `RM-TECH-253`
- acceptance (`owner`): privacy/legal решение (OD-032) и контракт источника утверждены
- evidence: OD-032; contract
- риск регрессии: низкий
- новые registry ID: `placement.audience_targeting`

**`RM-TECH-284`** — A/B attribution и winner metric (minimum sample, owner approval результата)  
- kind `implementation` · статус `blocked` · owner: Analytics/Product owner
- REQ: `REQ-BIZ-012`, `REQ-V26-010` · SC: — · DEC: `DEC-027`
- зависимости: `RM-TECH-282`
- acceptance (`behavioral`): A/B фиксирует группы/период/метрику; winner только при minimum sample и ручном утверждении
- evidence: new behavioral
- риск регрессии: средний
- новые registry ID: `experiment.evaluate`

**`RM-TECH-285`** — Competitive separation: competitive_category, интервал/исключение в playlist/manifest (исключение §3.1 по OD-018)  
- kind `implementation` · статус `blocked` · owner: Campaign/Inventory owner
- REQ: `REQ-V26-004` · SC: — · DEC: `DEC-005`, `DEC-022`
- зависимости: `RM-TECH-202`, `RM-TECH-280`
- acceptance (`behavioral`): separation block/override test; изменение priority engine ограничено §3.1
- evidence: new behavioral
- риск регрессии: высокий: priority engine
- новые registry ID: `campaign.competitive_separation`

**`RM-TECH-286`** — Financial-system exchange: versioned/idempotent export + payment-status contract (после DEC-017)  
- kind `implementation` · статус `blocked` · owner: Finance/Integration owner
- REQ: `REQ-V26-006`, `REQ-BIZ-009` · SC: — · DEC: `DEC-017`
- зависимости: `RM-TECH-246`
- acceptance (`behavioral`): idempotent export round-trip; повтор не создаёт дубликатов; scope финансового контура зафиксирован
- evidence: new behavioral
- риск регрессии: средний
- новые registry ID: `finance.exchange`, `finance.reconcile`
- примечание: blocked OD-030

**`RM-TECH-287`** — BI/export/SIEM/vendor API: scoped keys, rate-limit, immutable audit, circuit breaker (после DEC-013)  
- kind `implementation` · статус `blocked` · owner: Security owner
- REQ: `REQ-INT-003` · SC: `SC-SEC-002` · DEC: `DEC-013`
- зависимости: `RM-STAB-013`
- acceptance (`behavioral`): 401/403/429 negative; vendor connector с отдельными credentials и failure mode
- evidence: tests/test_s065_rate_limit.py; new behavioral
- риск регрессии: средний
- примечание: blocked OD-026

**`RM-TECH-288`** — nfr-slo.yaml + load-profiles.yaml (AG): method, percentile, error budget, generator, CI evidence  
- kind `governance` · статус `planned` · owner: SRE/Operations owner
- REQ: `REQ-NFR-001`, `REQ-NFR-006`, `REQ-NFR-007`, `REQ-NFR-005` · SC: `SC-NFR-001`, `SC-NFR-005`, `SC-NFR-006`, `SC-NFR-007` · DEC: `DEC-006`, `DEC-009`
- зависимости: `RM-TECH-205`
- acceptance (`artifact`): каждый SLO имеет window/denominator/exclusions; load generator и прогон в CI/стенде
- evidence: load run report; nfr-slo.yaml
- риск регрессии: низкий

**`RM-TECH-289`** — Extension points designed-not-implemented: ADR для programmatic (V26-007) и external measurement (V26-011)  
- kind `design` · статус `planned` · owner: Architecture owner
- REQ: `REQ-V26-007`, `REQ-V26-011` · SC: `SC-ARCH-006` · DEC: `DEC-001`, `DEC-018`
- зависимости: `RM-TECH-220`
- acceptance (`artifact`): ADR принят с пометкой designed-not-implemented; код не пишется до OD-021/OD-031
- evidence: ADR
- риск регрессии: низкий

### 8. Production (`POPS`) — 4 задач

**`RM-OPS-002`** — Network segmentation: firewall rules по environment + negative reachability tests из device-сегмента  
- kind `implementation` · статус `planned` · owner: Security/Operations owner
- REQ: `REQ-SEC-008` · SC: `SC-SEC-006` · DEC: —
- зависимости: `RM-PILOT-002`
- acceptance (`command`): Admin API/PostgreSQL/MinIO/Redis недостижимы из device-сегмента; Gateway только HTTPS/mTLS
- evidence: reachability test log
- риск регрессии: средний: сеть пилота

**`RM-OPS-003`** — Production HA baseline: ≥2 backend, масштабируемый Gateway, standby PostgreSQL, MinIO replication, quarterly restore drill  
- kind `external-plan` · статус `blocked` · owner: SRE/Operations owner · owner gate `deployment`
- REQ: `REQ-OPS-006`, `REQ-ARCH-004` · SC: `SC-OPS-001`, `SC-OPS-005` · DEC: `DEC-012`, `DEC-015`
- зависимости: `RM-OPS-001`
- acceptance (`command`): production config gate зелёный; restore drill выполнен и записан
- acceptance (`owner`): топология утверждена (OD-028), RTO/RPO (OD-025)
- evidence: tests/test_production_config_gate.py; drill record
- риск регрессии: высокий
- примечание: blocked OD-025/OD-028

**`RM-OPS-004`** — Rollout entity/state machine и feature flags: planned→lab→canary→staged→paused→completed/rolled_back  
- kind `implementation` · статус `blocked` · owner: Operations owner
- REQ: `REQ-OPS-002` · SC: `SC-OPS-007` · DEC: `DEC-008`
- зависимости: `RM-PILOT-002`
- acceptance (`behavioral`): rollback возвращает предыдущую версию; flag отключает функцию; ответственность по OD-010
- evidence: tests/integration/test_stand_rollback_drill.py
- риск регрессии: средний
- новые registry ID: `rollout.rollback`, `release.rollback`
- примечание: blocked OD-010

**`RM-OPS-005`** — retention-policy.yaml + legal decision register (AG): сроки, 152-ФЗ, deletion/archive, review date  
- kind `governance` · статус `blocked` · owner: Security/Legal owner · owner gate `scope_decision`
- REQ: `REQ-SEC-004` · SC: `SC-SEC-011` · DEC: `DEC-007`
- зависимости: `RM-TECH-253`
- acceptance (`owner`): юридическое утверждение retention/152-ФЗ (OD-009)
- evidence: OD-009; retention-policy.yaml
- риск регрессии: низкий
- примечание: blocked OD-009

## 5. Покрытие 51 REQ → задачи

| REQ | Задачи |
|---|---|
| `REQ-CORE-001` | `RM-TECH-240` |
| `REQ-CORE-003` | `RM-TECH-241` |
| `REQ-ARCH-001` | `RM-TECH-220` |
| `REQ-ARCH-002` | `RM-STAB-017` |
| `REQ-ARCH-003` | `RM-STAB-012` |
| `REQ-ORCH-002` | `RM-TECH-244` |
| `REQ-ORCH-003` | `RM-TECH-242` |
| `REQ-ORCH-004` | `RM-TECH-243` |
| `REQ-CONT-002` | `RM-TECH-250` |
| `REQ-BIZ-003` | `RM-TECH-247` |
| `REQ-BIZ-004` | `RM-UX-010` |
| `REQ-BIZ-005` | `RM-TECH-248` |
| `REQ-BIZ-006` | `RM-TECH-249` |
| `REQ-BIZ-009` | `RM-TECH-286` |
| `REQ-BIZ-010` | `RM-TECH-245` |
| `REQ-BIZ-012` | `RM-TECH-284` |
| `REQ-BIZ-013` | `RM-TECH-256` |
| `REQ-BIZ-014` | `RM-TECH-246` |
| `REQ-BIZ-017` | `RM-UX-009` |
| `REQ-V26-001` | `RM-TECH-229` |
| `REQ-V26-002` | `RM-TECH-282` |
| `REQ-V26-004` | `RM-TECH-285` |
| `REQ-V26-005` | `RM-TECH-283` |
| `REQ-V26-006` | `RM-TECH-286` |
| `REQ-V26-007` | `RM-TECH-289` |
| `REQ-V26-008` | `RM-TECH-262` |
| `REQ-V26-009` | `RM-TECH-263` |
| `REQ-V26-010` | `RM-TECH-284` |
| `REQ-V26-011` | `RM-TECH-289` |
| `REQ-SEC-001` | `RM-TECH-252` |
| `REQ-SEC-004` | `RM-TECH-253`, `RM-OPS-005` |
| `REQ-OPS-001` | `RM-TECH-255` |
| `REQ-OPS-009` | `RM-TECH-224` |
| `REQ-OPS-007` | `RM-TECH-254` |
| `REQ-OPS-008` | `RM-TECH-260` |
| `REQ-UX-004` | `RM-UX-008` |
| `REQ-INT-001` | `RM-TECH-281` |
| `REQ-INT-002` | `RM-TECH-264`, `RM-TECH-280` |
| `REQ-INT-003` | `RM-TECH-287` |
| `REQ-API-001` | `RM-TECH-220` |
| `REQ-API-002` | `RM-TECH-221` |
| `REQ-API-003` | `RM-TECH-222` |
| `REQ-DATA-001` | `RM-TECH-251` |
| `REQ-DATA-002` | `RM-TECH-229` |
| `REQ-NFR-002` | `RM-TECH-248` |
| `REQ-NFR-003` | `RM-TECH-228` |
| `REQ-SEC-005` | `RM-STAB-014` |
| `REQ-SEC-006` | `RM-STAB-013` |
| `REQ-SEC-007` | `RM-STAB-016` |
| `REQ-SEC-008` | `RM-OPS-002` |
| `REQ-SEC-009` | `RM-STAB-015` |

## 6. Решения владельца, нужные до ACCEPT очереди

1. **Порядок стадий**: подтвердить расформирование `BT`, новые стадии `C/CORE/CH/A`, `Gate-C`, и переназначение `Gate-U → Gate-S` у шести задач (§3).
2. **`RM-TECH-210` / registry**: `device.onboard` → `blocked` до PostgreSQL runtime-role evidence (r421 §11) или оставить `reachable` с записью расхождения.
3. **`RM-STAB-006`**: снять число «45/45» в пользу вычисляемого из registry.
4. **`RM-BIZ-002`**: `planned → blocked` до OD-013.

Открытые OD, от которых зависят blocked-задачи: OD-009/010/013/021/023/025/026/028/030/032. Имя владельца master-данных (OD-023) разблокирует RM-TECH-280 и цепочку Analytics.

## 7. Что произойдёт при ACCEPT (RM-GOV-009)

Claude вносит в `roadmap.yaml`: стадии/гейт, 64 задач, перестановку 14 задач, правки acceptance по §2; в `feature-registry.yaml` — 15 новых ID (blocked/planned); в `requirements-traceability.yaml` — `roadmap_ids` для 51 REQ (disposition task_required → task/blocked). `done` не присваивается ни одной задаче; `RM-GOV-007/008` остаются `verification` до ACCEPT владельца. Проверки: schema-check, guard (11 измерений), generate, consistency, CI.

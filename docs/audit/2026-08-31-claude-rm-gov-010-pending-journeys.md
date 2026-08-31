# Claude — RM-GOV-010 (часть 2): 8 awaiting_owner PENDING-ID journeys — варианты mapping и walkthrough-сценарии

Статус: **ждёт решений владельца; не закоммичено.** База: `develop @ 4ac3ddb` + рабочее дерево (RM-GOV-010-A).

## 1. Точный список awaiting_owner (traceability `pending_journey_map`)

| # | PENDING-ID | Story (AP) | REQ, задачи | Варианты | Рекомендация |
|---|---|---|---|---|---|
| 1 | `audit.compare` | US-REG-001 — аудитор сопоставляет ТЗ/roadmap/Git/CI/стенд/monitoring | REQ-GOV-001 → RM-GOV-006 (done) | **A** `rejected` как product-journey: это governance-процедура, доказательство — `roadmap-governance-guard` в CI; **B** новый service-ID `audit.compare` reachable со smoke = guard | **A** |
| 2 | `campaign.underdelivery` | US-UDR-001 — недопоказ и make-good | REQ-BIZ-008 → RM-TECH-201 | **A** новый registry-ID `blocked`, unblocked_by RM-TECH-201; **B** alias `kpi.review`/`analytics.compare` (оба blocked, иная функция) | **A** |
| 3 | `carrier.manage` | US-CHAN-003 — единый Operations-контур для device/carrier/surface | REQ-CHAN-003, OPS-001, SEC-002, UX-001 → RM-TECH-207A, RM-TECH-255 | **A** новый ID `blocked`, unblocked_by RM-TECH-255 + RM-TECH-207A; **B** alias `device.health_view` (только чтение — занижает story) | **A** |
| 4 | `channel.register` | US-CHAN-001 — регистрация channel/device/surface/profile + adapter contract | REQ-CHAN-001, ORCH-002 → RM-TECH-207A, RM-TECH-244 | **A** новый ID `blocked`, unblocked_by RM-TECH-207A + RM-TECH-244; **B** `rejected` до второго канала (OD-022: orchestrator только после него) | **A** |
| 5 | `channel.rendition_validate` | US-CHAN-002 — renditions и channel-ограничения | REQ-MAN-001, CONT-001 → RM-TECH-204, 207A, 207B | **A** новый ID `blocked`, unblocked_by RM-TECH-204 + RM-TECH-207A; **B** sub-function `creative.upload` (alias, без новой функции) | **A** |
| 6 | `data.catalog` | US-DATA-001 — owner/PII-класс/retention/lineage сущности | REQ-DATA-001, SEC-004 → RM-TECH-251 | **A** новый ID `blocked`, unblocked_by RM-TECH-251; **B** `rejected` (артефакт, не UI) | **A** |
| 7 | `inventory.priority` | US-PRI-001 — тип кампании и объяснимое вытеснение | REQ-BIZ-007 → RM-TECH-202 | **A** новый ID `blocked`, unblocked_by RM-TECH-202; **B** sub-function `inventory.rule_create` (priority = атрибут правила) | **A** |
| 8 | `security.review` | US-SEC-001 — критичные события, смена прав, SIEM-экспорт | REQ-SEC-001/003/004 → RM-TECH-252/253, RM-STAB-010, RM-OPS-005 | **A** mapped → canonical `audit.view` (AP: «`audit.view` plus PENDING-ID security.review»; расширение — acceptance REQ-SEC-001); **B** новый ID `blocked`, unblocked_by RM-TECH-252 + RM-TECH-253 (задачи identity/data protection, не SIEM) | **A** |

Правила применения: новый registry-ID = `status: blocked`, `blocked_features.unblocked_by` = задачи выше
(гейт `MISSING-UNBLOCK`/`UNBLOCK-DANGLING`); REQ переносит ID из `pending_journey_ids` в `journey_ids`;
`rejected` → `pending_journey_map.status: rejected`, REQ остаётся покрытым SC; решение — OD с датой.

## 2. Walkthrough

Сценарии для владельца: `docs/product/operator-walkthrough-dev.md` (17 сценариев, 43 UI-journey, статус
PENDING) — на DEV-стенде `192.168.110.81` (`stand-27dc397`, schema 036; curl 2026-08-31: :3000/:3001/`/version`/MinIO :9000 → 200,
device-gateway 127.0.0.1:8001 — loopback хоста, с santa2 не наблюдался). santa2 `:3100` — локальный preview, не стенд.

## 3. Решения владельца (2026-08-31) и применение

Владелец принял рекомендации по всем 8 пунктам → `OD-040` (approved 2026-08-31):

- registry: +6 features `blocked` (admin-web, P1, smoke-имена зарезервированы) → **79 / 52 reachable / 27 blocked**;
  `roadmap.yaml:blocked_features` +6 с `unblocked_by`/`owner_decision: OD-040`; `feature_ids` у RM-TECH-201/202/204/244/251/255.
- traceability: `pending_journey_map` — mapped 22 / rejected 1 / awaiting_owner **0**; journey_ids обновлены у 15 REQ
  (REQ-CHAN-001, REQ-CHAN-003, REQ-ORCH-002, REQ-MAN-001, REQ-CONT-001, REQ-BIZ-007, REQ-BIZ-008, REQ-SEC-001, REQ-SEC-002, REQ-SEC-003, REQ-SEC-004, REQ-OPS-001, REQ-UX-001, REQ-DATA-001, REQ-GOV-001); перепривязка на r427 (`6ae7110783a5…`).
- драфт r427: changelog OD-040; Дополнение AP не переписывается (нормативно, SHA r419).
- RM-GOV-010: обе приёмки выполнены локально (guard: TBD 0, awaiting_owner 0; OD-039/040/023 approved) — статус `in_progress`
  до CI-прогона, затем `verification`; `done` — только ACCEPT владельца.
- santa2 preview-контур обновлён до `4ac3ddb` (refresh-dev.sh, разрешение владельца) — это не DEV-стенд; DEV-стенд `.81` =
  `stand-27dc397`, перепроверен curl 2026-08-31 и переучтён в `environment-inventory.yaml` (+MinIO, device-gateway loopback,
  запись `santa2-roadmap-board` для `.78:3200` как внешнего read-only мониторинга).

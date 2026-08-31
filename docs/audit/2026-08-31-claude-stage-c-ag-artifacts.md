# Claude — стадия C: подготовка 10 артефактов handoff-пакета AG (kickoff, 2026-08-31)

Статус: **рабочее дерево, не закоммичено; все файлы — candidate/prepared (OD-043): без delivery in_progress и без acceptance.**
База: `develop @ 06ae22e` (код = 4ac3ddb; продуктовый код не менялся). Решения: OD-041 (порядок), OD-042 (r428 — контракт, RM-GOV-012 — процесс).
Семантика зависимостей (OD-043): C-задачи остаются `planned` до закрытия `Gate-S`; подготовка кандидатов допустима (Дополнение AG:
mini-design до шага 7), реализация и приёмка — только после старта задачи. Гейт `DEP-NOT-CLOSED` в check-roadmap-schema.

| # | Артефакт AG | Задача | Файл(ы) | Как получен | Состояние |
|---|---|---|---|---|---|
| 1 | requirements-traceability.yaml | RM-GOV-008 | `docs/product/requirements-traceability.yaml` | A1 + OD-039/040/042 | verification (CI) |
| 2 | role-scope-matrix.yaml | RM-UX-011 | `docs/product/role-scope-matrix.yaml` | as-built: seeded БД (5 ролей × 30 permissions), Q2 (7 ролей, OD-035), scopes.py, 38 RLS-таблиц, deny-cases → тесты | candidate/prepared |
| 3 | portal-route-matrix.yaml + journeys/ | RM-UX-011, RM-STAB-006 | `docs/product/portal-route-matrix.yaml`, `docs/product/journeys/journeys.yaml` | as-built: main.tsx обоих порталов (16+9 маршрутов), registry 79 journeys, AP actor/permission/happy/negative, user-journeys пути | candidate/prepared |
| 4 | OpenAPI + event/manifest JSON Schema | RM-TECH-220 | `docs/architecture/api/openapi-as-built-v1.json`, `openapi-target-v2.6.md`, `docs/architecture/events/event-envelope-v1.schema.json` (+ существующие `packages/contracts/*.schema.json`) | `app.openapi()` (113 paths/128 ops/149 схем), outbox_relay envelope, §13/§26 дельты | candidate/prepared |
| 5 | ERD + data dictionary + migration plan | RM-TECH-229 | `docs/architecture/erd/data-dictionary-as-built.md`, `migration-plan-v2.6.md` | SQLAlchemy metadata (62 таблицы, 622 колонки, 97 FK), pg_tables.rowsecurity (38), §13 target inventory → present/missing → задачи | candidate/prepared |
| 6 | channel-capability-matrix.yaml | RM-TECH-231 | `docs/product/channel-capability-matrix.yaml` | §7/§8/Доп. L, contracts, player client; KSO + declared каналы | candidate/prepared |
| 7 | nfr-slo.yaml + load-profiles.yaml | RM-TECH-288 (+205 `slo-objectives.yaml`) | `docs/product/slo-objectives.yaml`, `nfr-slo.yaml`, `load-profiles.yaml` | §8/REQ-NFR: 11 SLO с window/denominator/owner/status, 7 load-профилей | candidate/prepared |
| 8 | retention-policy.yaml + legal register | RM-OPS-005 (blocked OD-009) | `docs/product/retention-policy.yaml` | working defaults REQ-DATA-001, legal register DEC→OD | candidate/prepared — не действует до OD-009 |
| 9 | DEV environment manifest | RM-ENV-003 | `docs/product/environment-inventory.yaml` | curl 2026-08-31 stand-81 (:3000/3001/8000 version+health live/ready, MinIO :9000) | candidate/prepared |
| 10 | roadmap + generated views | RM-GOV-003/009 | `roadmap.yaml`, `docs/product/generated/*` | генератор | done/verification |

Следующие шаги: (1) Codex — сверка кандидатов с кодом (не приёмка); (2) закрытие стадии S → `Gate-S` (codex); (3) старт C-задач
(planned → in_progress только при закрытых зависимостях), приёмка кандидатов внутри задач (owner_gate); (4) решения OD-009/OD-011/OD-021/OD-025;
(5) Gate-C → ТЗ APPROVED (не раньше).

## Правки по указанию владельца (семантика зависимостей, 2026-08-31)

- `OD-043`: статус выше `planned` только при закрытых зависимостях (задачи done/verification, гейты approved_on); C-задачи `planned` до Gate-S; кандидаты допустимы без приёмки; гейт `DEP-NOT-CLOSED` в `check-roadmap-schema.py` (+2 tamper-кейса).
- 8 задач возвращены в `planned` (RM-TECH-220/229/231/205/288, RM-UX-011, RM-STAB-006, RM-ENV-003); notes — «кандидат подготовлен, без приёмки».
- 13 файлов помечены candidate/prepared (OD-043).
- Попутно: фикстура `scripts/ci/fixtures/roadmap.schema.example.yaml` отстала от registry после OD-040 (6 blocked-ID без `blocked_features`) — дополнена; schema self-test снова чист.

# A1 — `requirements-traceability.yaml`: REQ → story → journey → registry → roadmap → evidence

> ⚠️ **НЕ КАНОН** · тип: запись о выполнении артефакта A1 (AQ ledger «REQ→roadmap/evidence не замыкается», «53 REQ без story/scenario»)
> · SHA: `develop @ b0f9cdb` + рабочее дерево · дата: 2026-08-28 · автор: Claude Code
> · основание: OD-017, указание владельца «после успешного CI переходи к A1» (CI A2: run 33164564954 success)
> · открытых находок: 3 (§4) · Отменён: —

## 1. Что сделано

| Слой | Изменение |
|---|---|
| `docs/product/requirements-traceability.yaml` | **101 REQ** §25 драфта r422 по формату §37 (все обязательные поля), **69 `SC-*`**, `pending_journey_map` (23 PENDING-ID из AP), `registry_exclusions` (пусто — все 58 registry ID трассированы) |
| `docs/product/requirements-traceability.schema.json` | JSON Schema 2020-12: enum статусов §37, форматы ID, acceptance given/when/then, evidence kinds/status |
| `scripts/ci/roadmap-governance-guard.py` | модуль **`req`**: SCHEMA, DRAFT-REVISION-DRIFT, UNMAPPED/UNKNOWN-REQ, STORY/JOURNEY/PENDING/SC/TASK/DECISION-UNKNOWN, COVERAGE (§37), STATUS/OVERCLAIM/STATUS-SOURCE, BLOCKED-NO-REASON, DISPOSITION, EVIDENCE-PATH, SC-ORPHAN/ASYMMETRIC, REGISTRY-UNTRACED (REQ-GOV-002), TBD-AT-APPROVED; 9 tamper-кейсов (в т.ч. STATUS-SOURCE); sandbox расширен на `tests/` — self-test **48/48, 11 измерений** |

Покрытие: {'governance': 5, 'technical': 47, 'business': 30, 'security': 10, 'operational': 9}. Story есть у 47 REQ;
**SC — 69** (§37 требует SC для technical/security/operational/governance даже при наличии story — поэтому 69, а не 53;
два SC покрывают по два REQ, так что `scenario_ids` заполнены у 71 REQ — это число REQ, не сценариев).
Delivery: planned 87 / blocked 10 / in_progress 4 (SC: planned 65 / in_progress 4).
**Правило (замечание Codex, принято):** `feature-registry: reachable` и candidate-тест сами по себе
не дают `in_progress`; статус берётся из roadmap/traceability — `in_progress` только при roadmap task
в статусе in_progress/verification/done либо verified evidence, иначе `planned` + `candidate`.
`done` — нигде (нет verified evidence по правилу OD-001). Правило записано в `rules` yaml и
проверяется guard (`req/STATUS-SOURCE`, tamper-кейс).

## 2. Решения при сборке (для сверки Codex)

1. `REQ-V26-001` (tenant conformance), `REQ-V26-007/011` (design-only extension points), `REQ-UX-003/004`,
   `REQ-INT-003`, `REQ-SCOPE-001`, `REQ-UX-002` — coverage_type не business (technical/security/governance): у них нет UI-journey по смыслу.
2. AP US-V26-003 называет «two pending IDs» без имён → placeholder `campaign.competitive_separation`,
   `placement.audience_targeting` в `pending_journey_map` (awaiting_owner).
3. Registry reverse-trace: service/UI-функции, не названные ни одной story (manifest.deliver, pop.ingest,
   device.onboard/heartbeat, playlist.build, observability, adsettings.*, user.*, campaign.edit/activate/pause,
   creative.upload, audit.view, emergency.*, backup.restore, self.login, system.theme_switch) привязаны
   к владеющему техническому REQ в `journey_ids`.
4. `roadmap_ids` заполнены только там, где задача очевидна по названию; 51 REQ имеют
   `disposition: task_required` — вход для A3.
5. Evidence — `status: candidate` (путь существует, семантика тестом не доказана для данного REQ);
   `verified` ставится только с CI run и датой. Candidate не влияет на delivery_status.
6. `document.revision` привязан к r422: любая новая редакция драфта делает CI красным до пересверки — намеренно.

## 3. Проверки

guard PASS + self-test 48/48 · schema-check 0 · generate CLEAN · consistency 0. CI — после commit/push.

## 4. Остаток

1. **Owner/implementation owner:** 170 полей `TBD` (product/technical owner каждого REQ и SC) —
   допустимо до `APPROVED`, блокирует его. Нужно назначение владельцем (можно ролями).
2. **23 PENDING-ID journeys** ждут owner mapping в canonical registry ID (AQ «27 design journey IDs»).
3. **51 REQ без roadmap task** → A3 task breakdown (owner-gated).

## 5. Дальше

A3: task breakdown — задачи для 51 REQ `task_required`, §6 «Требуется», OD-019/020/036 code tasks,
RM-TECH-210, prerequisites (master-data adapter, sales-reference, audience/privacy, dynamic binding,
второй канал) → ACCEPT очереди; затем остальные артефакты AG.

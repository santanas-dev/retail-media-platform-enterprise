# Claude — RM-GOV-012 / OD-042: отчёт о покрытии — REQ × режим × задачи × registry × evidence

Статус: **рабочее дерево, не закоммичено.** Контракт: ТЗ `draft-2026-08-31-r428` (`ffb8cf7d192e…`); roadmap sha `f9c23debb80e…`;
baseline кода: `develop @ 4ac3ddb`. Проекции (`docs/product/generated/*`) — только генерацией `roadmap-generate.py`.

## 1. Итог по режимам (OD-042)

| Режим | REQ | Доля |
|---|---|---|
| `preserve` | 9 | 8% |
| `adapt` | 54 | 53% |
| `replace` | 2 | 1% |
| `new` | 36 | 35% |

`replace` (2) — только с доказанным конфликтом: REQ-MAN-002 и REQ-SEC-003 — HMAC-подпись сохраняется для dev/stand, для pilot/prod
вводится Ed25519 (OD-002 approved; `docs/audit/2026-08-27-claude-review-r417-stability.md`). Существующая реализация 63 REQ
(preserve 9 + adapt 54) **сохраняется**; 36 REQ — новые функции/артефакты.

Режим × этап (по самой ранней задаче REQ):

| Этап | preserve | adapt | replace | new |
|---|---|---|---|---|
| `G` | 3 | 0 | 0 | 0 |
| `E0` | 0 | 2 | 0 | 0 |
| `S` | 0 | 10 | 2 | 1 |
| `C` | 2 | 8 | 0 | 3 |
| `CORE` | 1 | 19 | 0 | 3 |
| `U` | 1 | 2 | 0 | 2 |
| `CH` | 2 | 11 | 0 | 7 |
| `A` | 0 | 1 | 0 | 15 |
| `POPS` | 0 | 1 | 0 | 5 |

Режим × тип покрытия:

| coverage_type | preserve | adapt | replace | new |
|---|---|---|---|---|
| business | 0 | 13 | 0 | 17 |
| governance | 5 | 0 | 0 | 0 |
| operational | 0 | 6 | 0 | 3 |
| security | 0 | 7 | 1 | 2 |
| technical | 4 | 28 | 1 | 14 |

## 2. Покрытие

- REQ с задачами roadmap: **101/101**; с baseline кода: 87/101 (пусто у 14 `new`-REQ без смежного кода); regression_criteria: 101/101.
- Evidence: 208 записей, verified 0 (все candidate до CI/стенда); REQ без evidence: 39 — REQ-CORE-001, REQ-CHAN-001, REQ-LIC-001, REQ-ORCH-006, REQ-BIZ-002, REQ-BIZ-004, REQ-BIZ-005, REQ-BIZ-006, REQ-BIZ-007, REQ-BIZ-008, REQ-BIZ-011, REQ-BIZ-012, REQ-BIZ-013, REQ-V26-002, REQ-V26-003, REQ-V26-004, REQ-V26-005, REQ-V26-006, REQ-V26-007, REQ-V26-008, REQ-V26-009, REQ-V26-010, REQ-V26-011, REQ-OPS-008, REQ-UX-002, REQ-UX-003, REQ-UX-004, REQ-INT-001, REQ-INT-002, REQ-API-001, REQ-DATA-001, REQ-NFR-001, REQ-NFR-004, REQ-NFR-005, REQ-NFR-006, REQ-NFR-007, REQ-SEC-008, REQ-STAND-002, REQ-STAND-003.
- Delivery REQ: {'planned': 88, 'blocked': 9, 'in_progress': 4}; blocked держат open OD (см. план §6).
- Registry: reachable 52 (UI 43 / service 9) · blocked 27 → по этапам {'U': 1, 'A': 10, 'CH': 8, 'S': 1, 'CORE': 5, 'POPS': 2} · frontend {'admin-web': 55, 'advertiser-web': 5, 'public': 1, 'service': 18}.

## 3. Техническая карта (roadmap.yaml → `docs/product/generated/roadmap.generated.md` §«Очередь по этапам», xlsx лист «Технический Roadmap»)

| Этап | Задач | Delivery | Зависимостей | С evidence_refs | Gate |
|---|---|---|---|---|---|
| `G` | 12 | {'done': 6, 'verification': 3, 'in_progress': 2, 'planned': 1} | 14 | 9 | Gate-G |
| `E0` | 3 | {'done': 1, 'planned': 2} | 4 | 1 | Gate-E0 |
| `S` | 18 | {'done': 2, 'planned': 16} | 30 | 2 | Gate-S |
| `C` | 17 | {'planned': 16, 'blocked': 1} | 18 | 0 | Gate-C |
| `CORE` | 21 | {'planned': 21} | 21 | 0 | Gate-CORE |
| `U` | 10 | {'planned': 9, 'blocked': 1} | 16 | 0 | Gate-U |
| `CH` | 9 | {'planned': 8, 'blocked': 1} | 14 | 0 | Gate-CH |
| `A` | 12 | {'planned': 7, 'blocked': 5} | 16 | 0 | Gate-A |
| `POPS` | 7 | {'planned': 5, 'blocked': 2} | 9 | 0 | Gate-POPS |

## 4. Бизнесовая карта (feature-registry → `roadmap.generated.md` §«Матрица функций», xlsx лист «Бизнес-функции Roadmap»)

reachable 52 (UI 43 / service 9) · blocked 27 → по этапам {'U': 1, 'A': 10, 'CH': 8, 'S': 1, 'CORE': 5, 'POPS': 2} · frontend {'admin-web': 55, 'advertiser-web': 5, 'public': 1, 'service': 18}. Каждая blocked-функция имеет `unblocked_by` (гейт MISSING-UNBLOCK) и owner_decision где применимо.

## 5. REQ → режим → задачи/этап → journeys → baseline → evidence

| REQ | type | режим | этап: задачи | journeys (✔ reachable / ⛔ blocked) | baseline | evidence (всего/verified) | delivery |
|---|---|---|---|---|---|---|---|
| REQ-SCOPE-001 | governance | `preserve` | CORE: RM-BIZ-001 |  | 4 | 1/0 | planned |
| REQ-CORE-001 | technical | `adapt` | CORE: RM-TECH-240 |  | 5 | 0/0 | planned |
| REQ-CORE-002 | technical | `adapt` | CH: RM-TECH-207A |  | 3 | 1/0 | planned |
| REQ-CORE-003 | technical | `adapt` | CORE: RM-TECH-241 |  | 3 | 1/0 | planned |
| REQ-ARCH-001 | technical | `adapt` | C: RM-TECH-220 |  | 3 | 1/0 | planned |
| REQ-ARCH-002 | technical | `adapt` | S: RM-STAB-017 |  | 2 | 1/0 | planned |
| REQ-ARCH-003 | technical | `adapt` | S: RM-STAB-012 |  | 3 | 1/0 | planned |
| REQ-ARCH-004 | technical | `new` | POPS: RM-PILOT-002, RM-OPS-001 |  | 4 | 3/0 | planned |
| REQ-CHAN-001 | technical | `new` | CH: RM-TECH-207A | channel.register⛔ | 5 | 0/0 | planned |
| REQ-CHAN-002 | technical | `adapt` | CH: RM-TECH-207A |  | 7 | 2/0 | planned |
| REQ-CHAN-003 | technical | `new` | CH: RM-TECH-207A | carrier.manage⛔ | 7 | 1/0 | planned |
| REQ-LIC-001 | business | `adapt` | CORE: RM-TECH-206, RM-TECH-208 | license.enforce✔, license.report✔, license.seat_release✔, license.upload⛔ … | 7 | 0/0 | planned |
| REQ-ORCH-001 | technical | `preserve` | CH: RM-TECH-207A |  | 2 | 2/0 | planned |
| REQ-ORCH-002 | technical | `adapt` | CORE: RM-TECH-244 | channel.register⛔ | 6 | 3/0 | planned |
| REQ-ORCH-003 | technical | `adapt` | CORE: RM-TECH-242 |  | 6 | 2/0 | planned |
| REQ-ORCH-004 | technical | `adapt` | CORE: RM-TECH-243 |  | 6 | 4/0 | planned |
| REQ-ORCH-005 | technical | `preserve` | CH: RM-TECH-207A |  | 3 | 1/0 | planned |
| REQ-ORCH-006 | technical | `new` | CH: RM-TECH-207A |  | 0 | 0/0 | planned |
| REQ-MAN-001 | technical | `adapt` | CH: RM-TECH-207A, RM-TECH-207B | manifest.deliver✔, channel.rendition_validate⛔ | 7 | 2/0 | planned |
| REQ-MAN-004 | technical | `adapt` | CH: RM-TECH-207B |  | 7 | 2/0 | planned |
| REQ-MAN-005 | technical | `adapt` | CH: RM-TECH-207B | playlist.build⛔ | 6 | 1/0 | planned |
| REQ-MAN-002 | technical | `replace` | S: RM-STAB-010 |  | 7 | 2/0 | planned |
| REQ-MAN-003 | technical | `adapt` | CH: RM-TECH-207B |  | 3 | 2/0 | planned |
| REQ-POP-001 | technical | `adapt` | CH: RM-TECH-207B |  | 9 | 2/0 | planned |
| REQ-POP-002 | technical | `adapt` | CH: RM-TECH-207B |  | 9 | 3/0 | planned |
| REQ-POP-003 | technical | `adapt` | CH: RM-TECH-207B | pop.ingest✔ | 9 | 2/0 | planned |
| REQ-POP-004 | technical | `adapt` | CH: RM-TECH-207B |  | 9 | 2/0 | planned |
| REQ-CONT-001 | technical | `adapt` | CORE: RM-TECH-204 | creative.moderate_approve✔, creative.moderate_reject✔, creative.upload✔, channel.rendition_validate⛔ | 6 | 6/0 | planned |
| REQ-CONT-002 | technical | `adapt` | CORE: RM-TECH-250 |  | 6 | 2/0 | planned |
| REQ-BIZ-001 | business | `adapt` | CORE: RM-TECH-203 | campaign.create✔, inventory.rule_create✔, inventory.simulate✔ | 3 | 3/0 | planned |
| REQ-BIZ-002 | business | `new` | S: RM-STAB-003 | finance.reconcile⛔ | 6 | 0/0 | planned |
| REQ-BIZ-003 | business | `adapt` | CORE: RM-TECH-247 | campaign.approve✔, campaign.reject✔, campaign.submit✔, self.campaign_view✔ … | 10 | 4/0 | planned |
| REQ-BIZ-004 | business | `new` | A: RM-UX-010 | analytics.compare⛔ | 3 | 0/0 | planned |
| REQ-BIZ-005 | business | `adapt` | CORE: RM-TECH-248 | campaign.schedule⛔ | 10 | 0/0 | planned |
| REQ-BIZ-006 | business | `adapt` | CORE: RM-TECH-249 | campaign.readiness⛔ | 6 | 0/0 | planned |
| REQ-BIZ-007 | business | `new` | CORE: RM-TECH-202 | inventory.priority⛔ | 3 | 0/0 | planned |
| REQ-BIZ-008 | business | `new` | CORE: RM-TECH-201 | campaign.underdelivery⛔ | 3 | 0/0 | planned |
| REQ-BIZ-009 | business | `adapt` | A: RM-TECH-286 | commerce.booking✔, commerce.offer_generate✔, commerce.order_close✔, commerce.order_create✔ … | 6 | 7/0 | blocked |
| REQ-BIZ-010 | business | `adapt` | CORE: RM-TECH-245 | campaign.activate✔, campaign.complete✔, campaign.edit✔, campaign.pause✔ | 10 | 3/0 | planned |
| REQ-BIZ-011 | business | `new` | A: RM-BIZ-003 | self.report_view⛔ | 3 | 0/0 | planned |
| REQ-BIZ-012 | business | `new` | A: RM-TECH-284 | experiment.evaluate⛔ | 0 | 0/0 | blocked |
| REQ-BIZ-013 | business | `new` | A: RM-TECH-256 | kpi.review⛔ | 0 | 0/0 | planned |
| REQ-BIZ-014 | business | `adapt` | CORE: RM-TECH-246 | commerce.booking✔, commerce.offer_generate✔, commerce.order_close✔, commerce.order_create✔ … | 6 | 7/0 | planned |
| REQ-BIZ-015 | business | `adapt` | S: RM-STAB-003 | advertiser.application_review✔, advertiser.apply✔, advertiser.brand_crud✔, advertiser.contact_crud✔ … | 9 | 9/0 | planned |
| REQ-BIZ-016 | business | `adapt` | CORE: RM-TECH-203 | adsettings.configure✔, adsettings.test✔, inventory.rule_create✔, inventory.simulate✔ | 3 | 4/0 | planned |
| REQ-BIZ-017 | business | `adapt` | U: RM-UX-009 | advertiser.contract_crud✔ | 4 | 1/0 | planned |
| REQ-V26-001 | technical | `preserve` | C: RM-TECH-229 |  | 5 | 2/0 | planned |
| REQ-V26-002 | business | `new` | A: RM-TECH-282 | attribution.lift_report⛔ | 0 | 0/0 | blocked |
| REQ-V26-003 | business | `new` | U: RM-BIZ-002 | self.campaign_create⛔ | 4 | 0/0 | blocked |
| REQ-V26-004 | business | `new` | A: RM-TECH-285 | campaign.competitive_separation⛔, placement.audience_targeting⛔ | 3 | 0/0 | planned |
| REQ-V26-005 | business | `new` | A: RM-TECH-283 | campaign.competitive_separation⛔, placement.audience_targeting⛔ | 0 | 0/0 | blocked |
| REQ-V26-006 | business | `new` | A: RM-TECH-286 | finance.exchange⛔ | 6 | 0/0 | blocked |
| REQ-V26-007 | technical | `new` | A: RM-TECH-289 |  | 0 | 0/0 | planned |
| REQ-V26-008 | business | `new` | CH: RM-TECH-262 | content.dynamic_binding⛔ | 6 | 0/0 | planned |
| REQ-V26-009 | business | `new` | CH: RM-TECH-263 | field_ops.device_confirm⛔ | 7 | 0/0 | blocked |
| REQ-V26-010 | business | `new` | A: RM-TECH-284 | attribution.lift_report⛔ | 0 | 0/0 | blocked |
| REQ-V26-011 | technical | `new` | A: RM-TECH-289 |  | 0 | 0/0 | planned |
| REQ-SEC-001 | security | `adapt` | CORE: RM-TECH-252 | audit.view✔, device.health_view✔, user.assign_roles✔ | 7 | 6/0 | planned |
| REQ-SEC-002 | security | `adapt` | S: RM-STAB-002, RM-STAB-004, RM-TECH-210 | advertiser.application_review✔, advertiser.apply✔, advertiser.brand_crud✔, advertiser.contact_crud✔ … | 6 | 24/0 | in_progress |
| REQ-SEC-003 | security | `replace` | S: RM-STAB-010, RM-TECH-210 | audit.view✔, device.onboard⛔, license.enforce✔, license.report✔ … | 7 | 3/0 | planned |
| REQ-SEC-004 | security | `adapt` | C: RM-OPS-005, RM-TECH-253 | advertiser.contract_crud✔, audit.view✔, emergency.activate✔, emergency.deactivate✔ … | 2 | 4/0 | planned |
| REQ-OPS-001 | operational | `adapt` | CORE: RM-TECH-255 | audit.view✔, device.health_view✔, emergency.activate✔, emergency.deactivate✔ … | 4 | 7/0 | planned |
| REQ-OPS-009 | operational | `adapt` | C: RM-TECH-224 | device.heartbeat✔ | 7 | 1/0 | planned |
| REQ-OPS-007 | operational | `adapt` | CORE: RM-TECH-254 | emergency.activate✔, emergency.deactivate✔ | 3 | 5/0 | planned |
| REQ-OPS-008 | operational | `adapt` | CH: RM-TECH-260 |  | 4 | 0/0 | planned |
| REQ-OPS-002 | operational | `new` | POPS: RM-PILOT-002 | release.rollback⛔, rollout.rollback⛔ | 4 | 1/0 | planned |
| REQ-OPS-003 | operational | `adapt` | POPS: RM-OPS-001 | backup.restore✔, release.rollback⛔ | 4 | 4/0 | planned |
| REQ-OPS-004 | operational | `adapt` | C: RM-TECH-205 | observability✔, rollout.rollback⛔ | 1 | 1/0 | planned |
| REQ-OPS-005 | operational | `new` | POPS: RM-OPS-001 |  | 2 | 1/0 | planned |
| REQ-OPS-006 | operational | `new` | POPS: RM-OPS-001 |  | 2 | 3/0 | planned |
| REQ-UX-001 | business | `adapt` | S: RM-STAB-003, RM-STAB-004, RM-STAB-007, RM-STAB-006 | advertiser.application_review✔, advertiser.apply✔, advertiser.brand_crud✔, advertiser.contact_crud✔ … | 3 | 26/0 | planned |
| REQ-UX-002 | governance | `preserve` | U: RM-UX-007 |  | 3 | 0/0 | planned |
| REQ-UX-003 | technical | `adapt` | U: RM-UX-001, RM-UX-003 |  | 3 | 0/0 | planned |
| REQ-UX-004 | technical | `new` | U: RM-UX-008 |  | 3 | 0/0 | planned |
| REQ-UX-005 | business | `adapt` | S: RM-STAB-004 | user.assign_roles✔ | 3 | 1/0 | planned |
| REQ-INT-001 | business | `new` | A: RM-TECH-281 | integration.reconcile⛔ | 0 | 0/0 | planned |
| REQ-INT-002 | business | `new` | CH: RM-TECH-264, RM-TECH-280 | integration.reconcile⛔ | 0 | 0/0 | planned |
| REQ-INT-003 | security | `new` | A: RM-TECH-287 |  | 3 | 1/0 | blocked |
| REQ-API-001 | technical | `adapt` | C: RM-TECH-220 |  | 5 | 0/0 | planned |
| REQ-API-002 | technical | `adapt` | C: RM-TECH-221 |  | 5 | 2/0 | planned |
| REQ-API-003 | technical | `adapt` | C: RM-TECH-222 |  | 9 | 2/0 | planned |
| REQ-DATA-001 | technical | `new` | CORE: RM-TECH-251 | data.catalog⛔ | 0 | 0/0 | planned |
| REQ-DATA-002 | technical | `preserve` | C: RM-TECH-229 |  | 5 | 2/0 | planned |
| REQ-NFR-001 | technical | `new` | C: RM-TECH-205 |  | 1 | 0/0 | planned |
| REQ-NFR-002 | technical | `adapt` | CORE: RM-TECH-248 |  | 9 | 1/0 | planned |
| REQ-NFR-003 | technical | `adapt` | C: RM-TECH-228 |  | 5 | 1/0 | planned |
| REQ-NFR-004 | technical | `new` | A: RM-TECH-209 |  | 0 | 0/0 | planned |
| REQ-NFR-005 | technical | `new` | A: RM-TECH-209 |  | 0 | 0/0 | planned |
| REQ-NFR-006 | technical | `new` | C: RM-TECH-205 |  | 0 | 0/0 | planned |
| REQ-NFR-007 | technical | `new` | C: RM-TECH-205 |  | 1 | 0/0 | planned |
| REQ-SEC-005 | security | `adapt` | S: RM-STAB-014 | audit.view✔ | 4 | 3/0 | planned |
| REQ-SEC-006 | security | `adapt` | S: RM-STAB-013 |  | 3 | 2/0 | planned |
| REQ-SEC-007 | security | `adapt` | S: RM-STAB-016 |  | 2 | 2/0 | planned |
| REQ-SEC-008 | security | `new` | POPS: RM-OPS-002 |  | 4 | 0/0 | planned |
| REQ-SEC-009 | security | `adapt` | S: RM-STAB-015 | user.create_advertiser✔, user.deactivate✔, user.reset_password✔, user.split_internal_advertiser✔ | 3 | 7/0 | planned |
| REQ-STAND-001 | technical | `adapt` | E0: RM-ENV-002 |  | 4 | 3/0 | planned |
| REQ-STAND-002 | technical | `adapt` | E0: RM-ENV-002 |  | 4 | 0/0 | planned |
| REQ-STAND-003 | technical | `new` | CH: RM-TECH-207A |  | 4 | 0/0 | planned |
| REQ-GOV-001 | governance | `preserve` | G: RM-GOV-006 |  | 4 | 1/0 | in_progress |
| REQ-GOV-002 | governance | `preserve` | G: RM-GOV-005 |  | 4 | 2/0 | in_progress |
| REQ-GOV-003 | governance | `preserve` | G: RM-GOV-004 |  | 4 | 2/0 | in_progress |

## 6. Гейт-правила, введённые OD-042

`req/MODE-REPLACE-NO-CONFLICT` (replace без conflict_ref — красный), `req/BASELINE-PATH` (baseline-путь должен существовать),
schema: `implementation_mode`/`mode_rationale`/`code_baseline`/`regression_criteria` обязательны; self-test +2 tamper-кейса.

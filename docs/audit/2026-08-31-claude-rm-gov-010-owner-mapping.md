# Claude — RM-GOV-010 (часть 1): OD-039 ролевая модель владельцев, OD-023 approved, owner mapping REQ/SC

Статус: **применено в рабочем дереве; не закоммичено** (указание владельца 2026-08-31).
База: `origin/develop @ 4ac3ddb` (r425) + рабочее дерево.

## 1. Решения владельца (ответы 2026-08-31)

| OD | Решение | Статус |
|---|---|---|
| **OD-039** (новый) | Ролевая модель владельцев REQ/SC: owner — роль из нормализованного словаря (Product / Technical / Architecture / Security / Operations / Data / Legal / Finance / Channel-Content / Analytics / PMO); implementation_owner — Claude Code; имена исполнителей ролей — отдельным amendment | approved 2026-08-31 |
| **OD-023** (DEC-005) | Владелец master-данных цен/SKU — роль **Product Data Owner** без имени (имя — amendment); master-система/reconciliation — контракт RM-TECH-280 | open → approved 2026-08-31 |

Правило вывода OD-039: (1) REQ с задачами RM-GOV-009 — из утверждённого `owner_role` задачи (составная роль → первая названная; при разных ролях — роль prerequisite-задачи, иначе первой); (2) REQ старых задач без `owner_role` — по семейству ID (CORE/ORCH/MAN/POP/CONT/CHAN/API/DATA/INT → Technical, BIZ/UX/SCOPE/LIC/V26 → Product, SEC → Security, OPS/NFR/STAND → Operations, ARCH → Architecture, GOV → PMO); (3) SC — роль своих REQ, при разных — по kind, иначе первого REQ.

Уточнение владельца 2026-08-31: единое название роли — **Product Data Owner** (вместо «Data owner»), применено ко всем текущим артефактам, включая составные `owner_role` задач (`Channel/Product Data Owner`, `Product Data Owner/Legal owner`, `Product Data Owner/Technical owner`, `Product Data Owner (OD-023)`); исторические записи 2026-08-28 не переписываются; заголовки «Data ownership…» (REQ-DATA-001, RM-TECH-229) — не роль.

## 2. Применение

- `roadmap.yaml`: OD-039 добавлен; OD-023 approved (statement, decided_on, source «ответ владельца»); разблокированы по роли **RM-TECH-280, 281, 264, 262, 285** (blocked → planned, notes); **RM-TECH-282** (OD-014/DEC-027) и **RM-TECH-283** (OD-032/DEC-019) остаются blocked — причина в notes переписана без OD-023; RM-GOV-010 → `in_progress` (остаток — PENDING-ID journeys).
- `requirements-traceability.yaml`: owner у 101 REQ и 69 SC (TBD **170 → 0**), implementation_owner = Claude Code у 101/101; REQ-INT-001/INT-002/V26-008/V26-004 → planned/task (status_changed_at/actor 2026-08-31, OD-023); REQ-V26-002/V26-005 остаются blocked с причиной OD-014/OD-032; правило OD-039 в `rules`; перепривязка на r426.
- Драфт **r426**: §29 и Дополнение I DEC-005 → approved OD-023; changelog r426; sidecar `43b552747efe…`. Нормативные §6/§25/§26/AP не менялись.
- `requirements/README.md`: DEC-005 закрыт OD-023; OD-039.
- Проекции `docs/product/generated/*` перегенерированы (OD-таблица 39, статусы задач).

## 3. Счётчики

REQ по ролям: {'Technical owner': 29, 'Product owner': 24, 'Operations owner': 16, 'Security owner': 11, 'Product Data Owner': 6, 'Analytics owner': 4, 'Architecture owner': 3, 'Channel/Content owner': 3, 'PMO': 3, 'Finance owner': 2}
SC по ролям: {'Technical owner': 28, 'Operations owner': 15, 'Security owner': 11, 'Product owner': 5, 'Product Data Owner': 3, 'PMO': 3, 'Architecture owner': 2, 'Channel/Content owner': 2}
Источник owner REQ: {'семейство SCOPE': 1, 'owner_role задачи': 53, 'семейство CORE': 1, 'семейство ARCH': 1, 'семейство CHAN': 3, 'семейство LIC': 1, 'семейство ORCH': 3, 'семейство MAN': 5, 'семейство POP': 4, 'семейство CONT': 1, 'семейство BIZ': 7, 'семейство V26': 1, 'семейство SEC': 2, 'семейство OPS': 5, 'семейство UX': 4, 'семейство NFR': 5, 'семейство STAND': 1, 'семейство GOV': 3}
REQ delivery: {'planned': 91, 'blocked': 6, 'in_progress': 4} · OD 39 (approved 20 / open 19) · задачи: {'done': 9, 'planned': 83, 'blocked': 11, 'verification': 3, 'in_progress': 1}

**APPROVED не объявлен** (`document.status: ACCEPTED`): остаются 23 PENDING-ID journeys (8 awaiting_owner), operator walkthrough, имена исполнителей ролей (amendment OD-039/OD-023).

## 4. Mapping REQ → owner (для проверки владельцем)

| REQ | coverage | roadmap | owner | источник |
|---|---|---|---|---|
| REQ-SCOPE-001 | governance | RM-BIZ-001 | Product owner | семейство SCOPE |
| REQ-CORE-001 | technical | RM-TECH-240 | Product Data Owner | owner_role задачи |
| REQ-CORE-002 | technical | RM-TECH-207A | Technical owner | семейство CORE |
| REQ-CORE-003 | technical | RM-TECH-241 | Technical owner | owner_role задачи |
| REQ-ARCH-001 | technical | RM-TECH-220 | Technical owner | owner_role задачи |
| REQ-ARCH-002 | technical | RM-STAB-017 | Technical owner | owner_role задачи |
| REQ-ARCH-003 | technical | RM-STAB-012 | Technical owner | owner_role задачи |
| REQ-ARCH-004 | technical | RM-PILOT-002, RM-OPS-001 | Architecture owner | семейство ARCH |
| REQ-CHAN-001 | technical | RM-TECH-207A | Technical owner | семейство CHAN |
| REQ-CHAN-002 | technical | RM-TECH-207A | Technical owner | семейство CHAN |
| REQ-CHAN-003 | technical | RM-TECH-207A | Technical owner | семейство CHAN |
| REQ-LIC-001 | business | RM-TECH-206, RM-TECH-208 | Product owner | семейство LIC |
| REQ-ORCH-001 | technical | RM-TECH-207A | Technical owner | семейство ORCH |
| REQ-ORCH-002 | technical | RM-TECH-244 | Technical owner | owner_role задачи |
| REQ-ORCH-003 | technical | RM-TECH-242 | Technical owner | owner_role задачи |
| REQ-ORCH-004 | technical | RM-TECH-243 | Technical owner | owner_role задачи |
| REQ-ORCH-005 | technical | RM-TECH-207A | Technical owner | семейство ORCH |
| REQ-ORCH-006 | technical | RM-TECH-207A | Technical owner | семейство ORCH |
| REQ-MAN-001 | technical | RM-TECH-207A, RM-TECH-207B | Technical owner | семейство MAN |
| REQ-MAN-004 | technical | RM-TECH-207B | Technical owner | семейство MAN |
| REQ-MAN-005 | technical | RM-TECH-207B | Technical owner | семейство MAN |
| REQ-MAN-002 | technical | RM-STAB-010 | Technical owner | семейство MAN |
| REQ-MAN-003 | technical | RM-TECH-207B | Technical owner | семейство MAN |
| REQ-POP-001 | technical | RM-TECH-207B | Technical owner | семейство POP |
| REQ-POP-002 | technical | RM-TECH-207B | Technical owner | семейство POP |
| REQ-POP-003 | technical | RM-TECH-207B | Technical owner | семейство POP |
| REQ-POP-004 | technical | RM-TECH-207B | Technical owner | семейство POP |
| REQ-CONT-001 | technical | RM-TECH-204 | Technical owner | семейство CONT |
| REQ-CONT-002 | technical | RM-TECH-250 | Channel/Content owner | owner_role задачи |
| REQ-BIZ-001 | business | RM-TECH-203 | Product owner | семейство BIZ |
| REQ-BIZ-002 | business | RM-STAB-003 | Product owner | семейство BIZ |
| REQ-BIZ-003 | business | RM-TECH-247 | Product owner | owner_role задачи |
| REQ-BIZ-004 | business | RM-UX-010 | Product owner | owner_role задачи |
| REQ-BIZ-005 | business | RM-TECH-248 | Product owner | owner_role задачи |
| REQ-BIZ-006 | business | RM-TECH-249 | Technical owner | owner_role задачи |
| REQ-BIZ-007 | business | RM-TECH-202 | Product owner | семейство BIZ |
| REQ-BIZ-008 | business | RM-TECH-201 | Product owner | семейство BIZ |
| REQ-BIZ-009 | business | RM-TECH-286 | Finance owner | owner_role задачи |
| REQ-BIZ-010 | business | RM-TECH-245 | Product owner | owner_role задачи |
| REQ-BIZ-011 | business | RM-BIZ-003 | Product owner | семейство BIZ |
| REQ-BIZ-012 | business | RM-TECH-284 | Analytics owner | owner_role задачи |
| REQ-BIZ-013 | business | RM-TECH-256 | Product owner | owner_role задачи |
| REQ-BIZ-014 | business | RM-TECH-246 | Product owner | owner_role задачи |
| REQ-BIZ-015 | business | RM-STAB-003 | Product owner | семейство BIZ |
| REQ-BIZ-016 | business | RM-TECH-203 | Product owner | семейство BIZ |
| REQ-BIZ-017 | business | RM-UX-009 | Product owner | owner_role задачи |
| REQ-V26-001 | technical | RM-TECH-229 | Product Data Owner | owner_role задачи |
| REQ-V26-002 | business | RM-TECH-282 | Analytics owner | owner_role задачи |
| REQ-V26-003 | business | RM-BIZ-002 | Product owner | семейство V26 |
| REQ-V26-004 | business | RM-TECH-285 | Product owner | owner_role задачи |
| REQ-V26-005 | business | RM-TECH-283 | Product Data Owner | owner_role задачи |
| REQ-V26-006 | business | RM-TECH-286 | Finance owner | owner_role задачи |
| REQ-V26-007 | technical | RM-TECH-289 | Architecture owner | owner_role задачи |
| REQ-V26-008 | business | RM-TECH-262 | Channel/Content owner | owner_role задачи |
| REQ-V26-009 | business | RM-TECH-263 | Operations owner | owner_role задачи |
| REQ-V26-010 | business | RM-TECH-284 | Analytics owner | owner_role задачи |
| REQ-V26-011 | technical | RM-TECH-289 | Architecture owner | owner_role задачи |
| REQ-SEC-001 | security | RM-TECH-252 | Security owner | owner_role задачи |
| REQ-SEC-002 | security | RM-STAB-002, RM-STAB-004, RM-TECH-210 | Security owner | семейство SEC |
| REQ-SEC-003 | security | RM-STAB-010, RM-TECH-210 | Security owner | семейство SEC |
| REQ-SEC-004 | security | RM-OPS-005, RM-TECH-253 | Security owner | owner_role задачи |
| REQ-OPS-001 | operational | RM-TECH-255 | Operations owner | owner_role задачи |
| REQ-OPS-009 | operational | RM-TECH-224 | Technical owner | owner_role задачи |
| REQ-OPS-007 | operational | RM-TECH-254 | Operations owner | owner_role задачи |
| REQ-OPS-008 | operational | RM-TECH-260 | Channel/Content owner | owner_role задачи |
| REQ-OPS-002 | operational | RM-PILOT-002 | Operations owner | семейство OPS |
| REQ-OPS-003 | operational | RM-OPS-001 | Operations owner | семейство OPS |
| REQ-OPS-004 | operational | RM-TECH-205 | Operations owner | семейство OPS |
| REQ-OPS-005 | operational | RM-OPS-001 | Operations owner | семейство OPS |
| REQ-OPS-006 | operational | RM-OPS-001 | Operations owner | семейство OPS |
| REQ-UX-001 | business | RM-STAB-003, RM-STAB-004, RM-STAB-007, RM-STAB-006 | Product owner | семейство UX |
| REQ-UX-002 | governance | RM-UX-007 | Product owner | семейство UX |
| REQ-UX-003 | technical | RM-UX-001, RM-UX-003 | Product owner | семейство UX |
| REQ-UX-004 | technical | RM-UX-008 | Product owner | owner_role задачи |
| REQ-UX-005 | business | RM-STAB-004 | Product owner | семейство UX |
| REQ-INT-001 | business | RM-TECH-281 | Analytics owner | owner_role задачи |
| REQ-INT-002 | business | RM-TECH-264, RM-TECH-280 | Product Data Owner | owner_role задачи |
| REQ-INT-003 | security | RM-TECH-287 | Security owner | owner_role задачи |
| REQ-API-001 | technical | RM-TECH-220 | Technical owner | owner_role задачи |
| REQ-API-002 | technical | RM-TECH-221 | Security owner | owner_role задачи |
| REQ-API-003 | technical | RM-TECH-222 | Technical owner | owner_role задачи |
| REQ-DATA-001 | technical | RM-TECH-251 | Product Data Owner | owner_role задачи |
| REQ-DATA-002 | technical | RM-TECH-229 | Product Data Owner | owner_role задачи |
| REQ-NFR-001 | technical | RM-TECH-205 | Operations owner | семейство NFR |
| REQ-NFR-002 | technical | RM-TECH-248 | Product owner | owner_role задачи |
| REQ-NFR-003 | technical | RM-TECH-228 | Technical owner | owner_role задачи |
| REQ-NFR-004 | technical | RM-TECH-209 | Operations owner | семейство NFR |
| REQ-NFR-005 | technical | RM-TECH-209 | Operations owner | семейство NFR |
| REQ-NFR-006 | technical | RM-TECH-205 | Operations owner | семейство NFR |
| REQ-NFR-007 | technical | RM-TECH-205 | Operations owner | семейство NFR |
| REQ-SEC-005 | security | RM-STAB-014 | Security owner | owner_role задачи |
| REQ-SEC-006 | security | RM-STAB-013 | Security owner | owner_role задачи |
| REQ-SEC-007 | security | RM-STAB-016 | Security owner | owner_role задачи |
| REQ-SEC-008 | security | RM-OPS-002 | Security owner | owner_role задачи |
| REQ-SEC-009 | security | RM-STAB-015 | Security owner | owner_role задачи |
| REQ-STAND-001 | technical | RM-ENV-002 | Operations owner | owner_role задачи |
| REQ-STAND-002 | technical | RM-ENV-002 | Operations owner | owner_role задачи |
| REQ-STAND-003 | technical | RM-TECH-207A | Operations owner | семейство STAND |
| REQ-GOV-001 | governance | RM-GOV-006 | PMO | семейство GOV |
| REQ-GOV-002 | governance | RM-GOV-005 | PMO | семейство GOV |
| REQ-GOV-003 | governance | RM-GOV-004 | PMO | семейство GOV |

## 5. Mapping SC → owner

| SC | kind | REQ | owner |
|---|---|---|---|
| SC-GOV-001 | governance | REQ-SCOPE-001 | Product owner |
| SC-DATA-001 | data | REQ-CORE-001 | Product Data Owner |
| SC-ARCH-001 | architecture | REQ-CORE-002 | Technical owner |
| SC-ARCH-002 | architecture | REQ-CORE-003 | Technical owner |
| SC-ARCH-003 | architecture | REQ-ARCH-001 | Technical owner |
| SC-ARCH-004 | architecture | REQ-ARCH-002 | Technical owner |
| SC-ARCH-005 | architecture | REQ-ARCH-003 | Technical owner |
| SC-OPS-001 | operational | REQ-ARCH-004 | Architecture owner |
| SC-CHAN-001 | technical | REQ-CHAN-002 | Technical owner |
| SC-ORCH-001 | technical | REQ-ORCH-001 | Technical owner |
| SC-ORCH-002 | technical | REQ-ORCH-003 | Technical owner |
| SC-ORCH-003 | technical | REQ-ORCH-004 | Technical owner |
| SC-ORCH-004 | governance | REQ-ORCH-005 | Technical owner |
| SC-ORCH-005 | contract | REQ-ORCH-006 | Technical owner |
| SC-MAN-001 | contract | REQ-MAN-004 | Technical owner |
| SC-MAN-002 | technical | REQ-MAN-005 | Technical owner |
| SC-SEC-001 | security | REQ-MAN-002 | Technical owner |
| SC-EDGE-001 | technical | REQ-MAN-003 | Technical owner |
| SC-POP-001 | data | REQ-POP-001 | Technical owner |
| SC-POP-002 | technical | REQ-POP-002 | Technical owner |
| SC-POP-003 | contract | REQ-POP-003 | Technical owner |
| SC-POP-004 | contract | REQ-POP-004 | Technical owner |
| SC-DATA-002 | data | REQ-CONT-002 | Channel/Content owner |
| SC-ARCH-006 | architecture | REQ-V26-011, REQ-V26-007 | Architecture owner |
| SC-OPS-002 | operational | REQ-OPS-009 | Technical owner |
| SC-OPS-003 | operational | REQ-OPS-007 | Operations owner |
| SC-EDGE-002 | technical | REQ-OPS-008 | Channel/Content owner |
| SC-OPS-004 | operational | REQ-OPS-005 | Operations owner |
| SC-OPS-005 | operational | REQ-OPS-006 | Operations owner |
| SC-GOV-002 | governance | REQ-UX-002 | Product owner |
| SC-UX-001 | technical | REQ-UX-003 | Product owner |
| SC-UX-002 | technical | REQ-UX-004 | Product owner |
| SC-SEC-002 | security | REQ-INT-003 | Security owner |
| SC-API-001 | contract | REQ-API-001 | Technical owner |
| SC-API-002 | security | REQ-API-002 | Security owner |
| SC-API-003 | contract | REQ-API-003 | Technical owner |
| SC-DATA-003 | data | REQ-DATA-002, REQ-V26-001 | Product Data Owner |
| SC-NFR-001 | performance | REQ-NFR-001 | Operations owner |
| SC-NFR-002 | technical | REQ-NFR-002 | Product owner |
| SC-NFR-003 | contract | REQ-NFR-003 | Technical owner |
| SC-NFR-004 | performance | REQ-NFR-004 | Operations owner |
| SC-NFR-005 | performance | REQ-NFR-005 | Operations owner |
| SC-NFR-006 | performance | REQ-NFR-006 | Operations owner |
| SC-NFR-007 | performance | REQ-NFR-007 | Operations owner |
| SC-SEC-003 | security | REQ-SEC-005 | Security owner |
| SC-SEC-004 | security | REQ-SEC-006 | Security owner |
| SC-SEC-005 | security | REQ-SEC-007 | Security owner |
| SC-SEC-006 | security | REQ-SEC-008 | Security owner |
| SC-SEC-007 | security | REQ-SEC-009 | Security owner |
| SC-STAND-001 | operational | REQ-STAND-001 | Operations owner |
| SC-STAND-002 | operational | REQ-STAND-002 | Operations owner |
| SC-STAND-003 | operational | REQ-STAND-003 | Operations owner |
| SC-GOV-003 | governance | REQ-GOV-002 | PMO |
| SC-GOV-004 | governance | REQ-GOV-003 | PMO |
| SC-CHAN-002 | technical | REQ-CHAN-001 | Technical owner |
| SC-CHAN-003 | technical | REQ-CHAN-003 | Technical owner |
| SC-ORCH-006 | technical | REQ-ORCH-002 | Technical owner |
| SC-MAN-003 | contract | REQ-MAN-001 | Technical owner |
| SC-CONT-001 | technical | REQ-CONT-001 | Technical owner |
| SC-SEC-008 | security | REQ-SEC-001 | Security owner |
| SC-SEC-009 | security | REQ-SEC-002 | Security owner |
| SC-SEC-010 | security | REQ-SEC-003 | Security owner |
| SC-SEC-011 | security | REQ-SEC-004 | Security owner |
| SC-OPS-006 | operational | REQ-OPS-001 | Operations owner |
| SC-OPS-007 | operational | REQ-OPS-002 | Operations owner |
| SC-OPS-008 | operational | REQ-OPS-003 | Operations owner |
| SC-OPS-009 | operational | REQ-OPS-004 | Operations owner |
| SC-DATA-004 | data | REQ-DATA-001 | Product Data Owner |
| SC-GOV-005 | governance | REQ-GOV-001 | PMO |

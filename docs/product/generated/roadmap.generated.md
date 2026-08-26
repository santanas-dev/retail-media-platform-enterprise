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
| Всего задач | 42 |
| По этапам | BT=13, E0=1, G=6, POPS=4, S=11, U=7 |
| По типу | design=5, external=2, external-plan=1, governance=10, human=1, implementation=23 |
| По статусу поставки | done=6, planned=35, verification=1 |
| Требуют owner gate | 12 |
| С verified evidence | 7 |
| Максимальная глубина зависимостей | 8 |
| Гейты | Gate-G, Gate-S, Gate-U |
| Решения владельца | 15 |

### Функции (из registry — функциональный SSOT)

| Метрика | Значение |
|---|---|
| Всего функций | 58 |
| reachable · blocked | 53 · 5 |
| По фронтенду | admin-web=39, advertiser-web=5, public=1, service=13 |
| UI-функций (не service) | 45 |
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

| ID | Статус | Дата | Формулировка |
|---|---|---|---|
| `OD-001` | approved | 2026-08-26 | Код/тесты описывают фактическое поведение; ТЗ/ADR — требуемое. Расхождение является дефектом до явного ADR. |
| `OD-002` | approved | 2026-08-26 | Ed25519 обязателен для device pilot/production. HMAC допустим только для dev и control-plane stand. |
| `OD-003` | approved | 2026-08-26 | Retailer scope — первоклассная граница; bypass только system_admin и security_admin. |
| `OD-004` | approved | 2026-08-26 | UI-smoke отделён от ordinary pytest и является blocking gate для develop, release и повышения journey до reachable. |
| `OD-005` | approved | 2026-08-26 | self.campaign_create исключён из ближайшего control-plane pilot; первый pilot managed-first. |
| `OD-006` | approved | 2026-08-26 | При renewal занятые seats старого grant атомарно закрываются и продолжаются под новым grant. |
| `OD-007` | approved | 2026-08-26 | Активный baseline — .81 / stand-27dc397; .77 называется только unreachable at check time. |
| `OD-008` | open | — | MFA обязателен до production; согласование NATS с ИТ/ops — до pilot deployment. |
| `OD-009` | open | — | Объём безопасности и соответствия до production — SIEM/Wazuh-экспорт, минимизация PII, доступ администратора только через VPN, retention и партиционирование данных. Вопрос - расширяется ли scope RM-OPS-001 этими четырьмя пунктами или каждый становится отдельной задачей. Ни один сейчас не назван ни одной из 42 задач. |
| `OD-010` | open | — | Безопасная выкатка — staged rollout с rollback и feature flags. Вопрос - это предусловие пилота или production. От ответа зависит, входят ли они в RM-PILOT-002 preflight или только в RM-OPS-001. |
| `OD-011` | open | — | Нагрузочные профили и критерии производительности на 40K устройств. Вопрос - измеряется ли это до пилота как вход в SLO (RM-TECH-205) и в триггер ClickHouse (RM-TECH-209), или откладывается до production. |
| `OD-012` | open | — | Часовые пояса, календарь и праздничное расписание показов. Это корректность доставки, а не операционный вопрос - вопрос владельцу - входит ли в scope пилота. |
| `OD-013` | open | — | Self-service онбординг рекламодателя - сброс пароля самим пользователем и приглашения. Админский сброс и приглашение уже reachable с зелёными смоуками; self-service отсутствует. Вопрос согласуется с OD-005 (managed-first) - нужен ли self-service в первом пилоте. |
| `OD-014` | open | — | A/B lift и attribution - материал ветки v2.6, зависит от модели арендатора (ADR-018). Вопрос - фиксируется ли как отложенное решением, по образцу ADR-019 для Channel Orchestrator, или остаётся неопределённым. |
| `OD-015` | open | — | Операционный центр здоровья устройств. Функция device.health_view reachable и закреплена в CI; вопрос - достаточно ли этого представления для пилота или требуется отдельный операционный центр как самостоятельный объём работ. |

## Гейты

| Гейт | Закрывает этап | Утверждает | Условия |
|---|---|---|---|
| `Gate-G` | G | owner | Codex проверяет generator и tamper matrix; владелец утверждает canonical cutover |
| `Gate-S` | S | codex | новые counts и evidence воспроизводимы |
| `Gate-U` | U | human | человек проходит walkthrough на exact stand bundle |

## Очередь по этапам

### G — Единая система roadmap (6) · закрывается `Gate-G`

| ID | Kind | Задача | Зависит от | Глубина | Поставка | Owner gate | Приёмка | Evidence |
|---|---|---|---|---|---|---|---|---|
| `RM-GOV-001` | design | Schema/mini-design `roadmap.yaml` | — | 0 | done | scope_decision | schema validator [command: `python3 scripts/ci/check-roadmap-schema.py --self-test`] | verified · command · `python3 scripts/ci/check-roadmap-schema.py --self-test`; verified · artifact · `docs/architecture/rm-gov-001-roadmap-yaml-design-gate.md` |
| `RM-GOV-002` | governance | Reconciliation/migration manifest | `RM-GOV-001` | 1 | done | — | disposition для 93 technical items, 13 SECTION и 57 business rows [command: `python3 scripts/ci/check-roadmap-schema.py --file docs/product/roadmap.yaml`] | verified · command · `python3 scripts/ci/roadmap-migration-counts.py`; verified · artifact · `docs/product/roadmap-migration-manifest.yaml`; verified · command · `python3 scripts/ci/check-roadmap-schema.py --file docs/product/roadmap.yaml` |
| `RM-GOV-003` | implementation | Односторонний generator YAML + registry + evidence → Markdown/XLSX/metrics | `RM-GOV-001`, `RM-GOV-002` | 2 | done | — | deterministic generation [command: `python3 scripts/ci/roadmap-generate.py --check-clean-diff`] | verified · command · `python3 scripts/ci/roadmap-generate.py --check-clean-diff`; verified · command · `python3 scripts/ci/roadmap-generate.py --self-test`; verified · artifact · `docs/architecture/rm-gov-003-roadmap-generator-design-gate.md` |
| `RM-GOV-004` | implementation | Структурный roadmap guard | `RM-GOV-003` | 3 | done | — | tamper matrix красная для drift/schema/dependencies/metrics/SSOT и зелёная на baseline [ci_job: `roadmap-governance-guard`] | verified · command · `python3 scripts/ci/roadmap-governance-guard.py`; verified · command · `python3 scripts/ci/roadmap-governance-guard.py --self-test`; verified · ci_run · `gh run 33000750265 — roadmap-governance-guard success на 47be5dd`; verified · artifact · `docs/architecture/rm-gov-004-roadmap-governance-guard-design-gate.md` |
| `RM-GOV-005` | governance | Canonical cutover | `RM-GOV-003`, `RM-GOV-004`, `RM-GOV-006` | 4 | done | canon_change | один sequencing SSOT в `AGENTS.md` [owner] | verified · command · `python3 scripts/ci/roadmap-governance-guard.py`; verified · command · `python3 scripts/ci/roadmap-governance-guard.py --self-test`; verified · ci_run · `gh run 33000750265 — release-gate success на 47be5dd`; verified · artifact · `docs/architecture/rm-gov-005-canonical-cutover-design-gate.md` |
| `RM-GOV-006` | governance | Единое правило факта и требования | `RM-GOV-001` | 1 | done | — | approved правило §1.1 записано без конфликта в индекс/ADR-процесс [artifact: `docs/architecture/adr/ADR-020-fact-vs-requirement.md`] | verified · adr · `docs/architecture/adr/ADR-020-fact-vs-requirement.md`; verified · command · `python3 scripts/ci/roadmap-governance-guard.py --module doc`; verified · command · `python3 scripts/ci/roadmap-governance-guard.py --self-test` |

### E0 — Окружения (1)

| ID | Kind | Задача | Зависит от | Глубина | Поставка | Owner gate | Приёмка | Evidence |
|---|---|---|---|---|---|---|---|---|
| `RM-ENV-001` | governance | Инвентарь `.77/.81/DEV/PROD` и очистка активных ссылок | `Gate-G` | 0 | verification | scope_decision | versioned environment inventory [artifact: `docs/product/environment-inventory.yaml`] | verified · artifact · `docs/product/environment-inventory.yaml`; verified · command · `curl -s -o /dev/null -w '%{http_code}' --max-time 4 http://192.168.110.77:3000/`; verified · command · `curl -s http://192.168.110.81:8000/version`; verified · command · `python3 scripts/ci/roadmap-governance-guard.py --module env`; verified · artifact · `docs/architecture/rm-env-001-environment-inventory-design-gate.md` |

### S — Стабилизация доказательств и границ (11) · закрывается `Gate-S`

| ID | Kind | Задача | Зависит от | Глубина | Поставка | Owner gate | Приёмка | Evidence |
|---|---|---|---|---|---|---|---|---|
| `RM-STAB-001` | implementation | Единый контракт `BEHAVIORAL_APP_DB_URL` | `RM-ENV-001` | 1 | planned | — | обе DSN-формы проходят один targeted behavioral command через один helper [command: `RUN_BEHAVIORAL_TESTS=1 python3 -m pytest tests/behavioral/test_commerce_rls.py -q`] | — |
| `RM-STAB-002` | implementation | Strict RLS context по умолчанию | `RM-STAB-001` | 2 | planned | — | admin elevation только setup [behavioral: `tests/behavioral/conftest.py::strict get_db default`] | — |
| `RM-STAB-003` | design | Зафиксировать approved personas/retailer-scope | `RM-STAB-002` | 3 | planned | scope_decision | mini-design/ADR: persona→permissions→scope [owner] | — |
| `RM-STAB-004` | implementation | Реализовать approved RBAC/RLS scope | `RM-STAB-003`, `RM-STAB-006` | 5 | planned | migration_application | API/portal/migration согласованы [behavioral: `tests/behavioral/test_retailer_scope_rbac.py`] | — |
| `RM-STAB-005` | implementation | Исправить C1 UI-smoke и расширить общий guard | `RM-ENV-001` | 1 | planned | — | нет API/deep goto/sleep/broad retry [command: `UI_SMOKE_RUN=1 python3 -m pytest tests/ui-contract -q`] | — |
| `RM-STAB-006` | governance | 45/45 нормативных UI journeys | `RM-STAB-003` | 4 | planned | — | validator: actor, permission, entry, `Happy-path: N`, selectors, negative expectation [command: `python3 scripts/ci/check-journey-spec.py --strict`] | — |
| `RM-STAB-007` | implementation | UI proof под intended roles | `RM-STAB-004`, `RM-STAB-006` | 6 | planned | — | critical journeys имеют positive intended-role и negative missing-permission proof [ui_smoke: `tests/ui-smoke/ci-subset.txt (intended-role variants)`] | — |
| `RM-STAB-008` | implementation | Единая blocking-политика UI-smoke | `RM-STAB-005`, `RM-STAB-007` | 7 | planned | canon_change | ordinary pytest отделён [ci_job: `release-gate`] | — |
| `RM-STAB-009` | implementation | Воспроизводимые CI dependencies | `RM-ENV-001` | 1 | planned | — | CI ставит project lock/requirements [ci_job: `python-tests (installs from requirements.txt)`] | — |
| `RM-STAB-010` | governance | Зафиксировать signing gate | `RM-ENV-001` | 1 | planned | — | ADR/roadmap отражают §1.2 [artifact: `docs/architecture/adr/ADR-021-manifest-signing-gate.md`] | — |
| `RM-STAB-011` | governance | W0 rebaseline | `RM-STAB-001`, `RM-STAB-002`, `RM-STAB-003`, `RM-STAB-004`, `RM-STAB-005`, `RM-STAB-006`, `RM-STAB-007`, `RM-STAB-008`, `RM-STAB-009`, `RM-STAB-010` | 8 | planned | — | named targeted → behavioral → UI subset → guards [command: `python3 scripts/ci/check-roadmap-schema.py --file docs/product/roadmap.yaml`] | — |

### U — Утверждённый UX-порядок (7) · закрывается `Gate-U`

| ID | Kind | Задача | Зависит от | Глубина | Поставка | Owner gate | Приёмка | Evidence |
|---|---|---|---|---|---|---|---|---|
| `RM-UX-001` (A3) | implementation | Accessibility оставшихся форм + route matrix | `Gate-S` | 0 | planned | — | labels/ARIA/axe/targeted vitest [artifact: `docs/product/ux-route-matrix.yaml`] | — |
| `RM-UX-002` (A2) | implementation | Поиск/сортировка/усечение таблиц | `RM-UX-001` | 1 | planned | — | server semantics для pagination [ui_smoke: `tests/ui-smoke/test_uismoke__campaign__create.py`] | — |
| `RM-UX-003` (A4) | implementation | Responsive-проверка | `RM-UX-002` | 2 | planned | — | все routes из `ux-route-matrix.yaml` проверены на 390px без overflow/crop [artifact: `docs/product/ux-responsive-report.yaml`] | — |
| `RM-UX-004` (A6) | implementation | Согласованность состояний и терминов | `RM-UX-003` | 3 | planned | — | route matrix покрывает empty/loading/error/403/success и locale-key check [artifact: `docs/product/ux-route-matrix.yaml (states coverage)`] | — |
| `RM-UX-005` (A1b) | implementation | Adoption доказанных primitives малыми slices | `RM-UX-004` | 4 | planned | — | каждый slice имеет отдельный diff/test/review [ci_job: `frontend`] | — |
| `RM-UX-006` (A5) | implementation | Advertiser-web UX audit/fixes | `RM-UX-005` | 5 | planned | — | versioned `docs/product/advertiser-route-matrix.yaml` с точным списком 15 routes [artifact: `docs/product/advertiser-route-matrix.yaml`] | — |
| `RM-UX-007` (A7) | human | Human operator walkthrough | `RM-UX-001`, `RM-UX-002`, `RM-UX-003`, `RM-UX-004`, `RM-UX-005`, `RM-UX-006` | 6 | planned | — | человек проходит exact stand bundle [human] | — |

### BT — Бизнесовые и технические разрывы (13)

| ID | Kind | Задача | Зависит от | Глубина | Поставка | Owner gate | Приёмка | Evidence |
|---|---|---|---|---|---|---|---|---|
| `RM-BIZ-001` | governance | Записать managed-first scope | `Gate-U` | 0 | planned | — | roadmap явно исключает `self.campaign_create` из ближайшего control-plane pilot [artifact: `docs/product/roadmap.yaml (pilot scope)`] | — |
| `RM-BIZ-002` | implementation | `self.campaign_create` в будущей ветке | `RM-BIZ-001` | 1 | planned | scope_decision | mini-design, journey, backend/UI/RLS, intended-role smoke, walkthrough [ui_smoke: `tests/ui-smoke/test_uismoke__self__campaign_create.py`] | — |
| `RM-BIZ-003` | implementation | `self.report_view` plan/fact | `RM-TECH-201`, `RM-TECH-207B` | 2 | planned | — | реальные PoP/причины/RLS, journey/smoke/walkthrough [ui_smoke: `tests/ui-smoke/test_uismoke__self__report_view.py`] | — |
| `RM-TECH-201` | design | Таксономия причин недопоказа | `Gate-U` | 0 | planned | — | 8 категорий ТЗ, source/report/history contract и owner-approved artifact [artifact: `docs/product/underdelivery-reason-taxonomy.yaml`] | — |
| `RM-TECH-202` | implementation | Вытеснение и объяснимые приоритеты | `RM-TECH-201` | 1 | planned | — | versioned rules [behavioral: `tests/behavioral/test_campaign_preemption.py`] | — |
| `RM-TECH-203` | implementation | Overbooking policy | `RM-TECH-202` | 2 | planned | — | default deny [behavioral: `tests/behavioral/test_inventory_overbooking_policy.py`] | — |
| `RM-TECH-204` | implementation | Creative QA без неутверждённого HTML5 | `Gate-U` | 0 | planned | — | metadata/antivirus/executable deny и immutable QA result [behavioral: `tests/behavioral/test_creative_qa.py`] | — |
| `RM-TECH-205` | governance | SLO objectives и измерение | `Gate-U` | 0 | planned | — | каждое число ТЗ имеет formula/window/owner/metric либо `not measurable` [artifact: `docs/product/slo-objectives.yaml`] | — |
| `RM-TECH-206` | implementation | License renewal/grant boundary | `Gate-U` | 0 | planned | — | атомарная семантика §1.6 [behavioral: `tests/behavioral/test_license_renewal_boundary.py`] | — |
| `RM-TECH-207A` | design | KSO environment + player/playlist design | `Gate-U` | 0 | planned | scope_decision | versioned environment audit, import/contract mini-design и test plan [artifact: `docs/architecture/kso-environment-audit.md`] | — |
| `RM-TECH-207B` | implementation | KSO player/playlist/PoP chain | `RM-TECH-207A` | 1 | planned | device_contract | contract tests и playback→manifest→PoP behavioral proof [behavioral: `tests/behavioral/test_kso_playback_chain.py`] | — |
| `RM-TECH-208` | implementation | Signed licensing Layer 2 | `RM-TECH-206`, `RM-TECH-207B`, `RM-STAB-010` | 2 | planned | protected_boundary | Ed25519 offline verify, kid/rotation/revocation, UI, tamper/rollback [behavioral: `tests/behavioral/test_signed_license_layer2.py`] | — |
| `RM-TECH-209` | governance | ClickHouse capacity trigger | `RM-TECH-207B` | 2 | planned | — | измеряемый PoP rate/retention threshold и owner migration gate [artifact: `docs/product/clickhouse-capacity-trigger.yaml`] | — |

### POPS — Внешние действия: pilot и production (4)

| ID | Kind | Задача | Зависит от | Глубина | Поставка | Owner gate | Приёмка | Evidence |
|---|---|---|---|---|---|---|---|---|
| `RM-OPS-001` | external | Production readiness | `RM-PILOT-003` | 4 | planned | deployment | не запускается автоматически после pilot [owner] | — |
| `RM-PILOT-001` | design | Managed control-plane pilot scope | `Gate-S`, `Gate-U`, `RM-ENV-001` | 1 | planned | — | exact bundle/host/rollback/TLS [artifact: `docs/runbook/pilot-scope.md`] | — |
| `RM-PILOT-002` | external-plan | Deployment plan/preflight | `RM-PILOT-001` | 2 | planned | — | immutable lock, backup/restore, migration rehearsal, secrets/TLS/monitoring [artifact: `infra/deploy/images.lock.json + dry-run evidence`] | — |
| `RM-PILOT-003` | external | Controlled pilot deploy | `RM-PILOT-002` | 3 | planned | deployment | SHA/lock/schema/health, stand-safe journeys, rollback readiness [owner] | — |

## Заблокированные функции и условия разблокировки

| Feature | Registry gap | Разблокирует | Условия | Решение |
|---|---|---|---|---|
| `license.upload` | Layer 2 (signed-license/JWS/CRL + UI upload) — не реализован. | `RM-TECH-208` | signed-license Layer 2: upload .lic + проверка подписи | — |
| `license.view` | Layer 2 (signed-license/UI) — не реализован. | `RM-TECH-208` | signed-license Layer 2: offline Ed25519 verify + kid/CRL | — |
| `playlist.build` | Плеер не перенесён в enterprise. Код есть в старом репо (PLAYER-AUD-001), адаптация — после manifest/onboard/ingest. | `RM-TECH-207B` | плеер перенесён в enterprise-репозиторий и есть реальный КСО | — |
| `self.campaign_create` | UI-smoke отсутствует. P2 — self-service фаза, не пилот. | `RM-BIZ-002` | владелец включает self-service в scope пилота | OD-005 |
| `self.report_view` | UI-smoke отсутствует. Фронтенд advertiser-web не проходил аудит. | `RM-BIZ-003` | реальные PoP-события от плеера, а не симулятора | — |

## Матрица функций (registry + evidence)

Столбец «Зрелость» берётся только из блока `maturity` в `roadmap.yaml`. Генератор его не вычисляет.

### admin-web — 39

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
| `audit.view` | Смотреть журнал аудита | P1 | reachable | `test_uismoke__audit__view` | ✅ | не заявлено |
| `campaign.activate` | Запустить одобренную кампанию | P1 | reachable | `test_uismoke__campaign__activate` | ✅ | не заявлено |
| `campaign.approve` | Одобрить кампанию | P0 | reachable | `test_uismoke__campaign__approve` | ✅ | не заявлено |
| `campaign.create` | Создание кампании | P0 | reachable | `test_uismoke__campaign__create` | ✅ | не заявлено |
| `campaign.edit` | Редактирование кампании (рейсы/размещения) | P0 | reachable | `test_uismoke__campaign__edit` | ✅ | не заявлено |
| `campaign.pause` | Приостановить активную кампанию | P1 | reachable | `test_uismoke__campaign__pause` | ✅ | не заявлено |
| `campaign.reject` | Отклонить кампанию с причиной | P0 | reachable | `test_uismoke__campaign__reject` | ✅ | не заявлено |
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
| `inventory.rule_create` | Создать правило инвентаря | P1 | reachable | `test_uismoke__inventory__rule_create` | ✅ | не заявлено |
| `inventory.simulate` | Прогноз показов (симуляция инвентаря) | P1 | reachable | `test_uismoke__inventory__simulate` | ✅ | не заявлено |
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

### service — 13

| Feature ID | Название | Приоритет | Статус | Smoke | В CI-subset | Зрелость |
|---|---|---|---|---|---|---|
| `backup.restore` | Резервное копирование и восстановление | P1 | reachable | `001C-FU: test_restore_drill_verify.py (16 behavioral) + test_backup_restore_drill.py (27 negative matrix) — real PG+MinIO drill` | — | не заявлено |
| `campaign.complete` | Автоматическое завершение кампании по концу рейса | P1 | reachable | `n/a (service feature, no UI journey)` | — | не заявлено |
| `device.heartbeat` | Heartbeat устройств (health/статус) | P0 | reachable | `EDGE-004 behavioral (12 тестов): test_edge004_*.py` | — | не заявлено |
| `device.onboard` | Онбординг устройства (device-code → JWT) | P0 | reachable | `EDGE-001 behavioral (13 тестов): test_edge001_*.py` | — | не заявлено |
| `license.enforce` | Enforcement лицензии при device enrollment | P1 | reachable | `test_license_enrollment.py (13 behavioral tests)` | — | не заявлено |
| `license.report` | Отчёт по лицензии (занятые/свободные seats + пик) | P1 | reachable | `test_license_report.py (16 behavioral tests)` | — | не заявлено |
| `license.seat_release` | Освобождение лицензионного seat при decommission | P1 | reachable | `test_license_decommission.py (13 behavioral tests)` | — | не заявлено |
| `license.upload` | Загрузка/установка лицензионного файла | P1 | blocked | `n/a` | — | не заявлено |
| `license.view` | Просмотр активных лицензий (UI) | P1 | blocked | `n/a` | — | не заявлено |
| `manifest.deliver` | Доставка манифеста на устройство | P0 | reachable | `EDGE-002 behavioral (13 тестов): test_edge002_*.py` | — | не заявлено |
| `observability` | Мониторинг и метрики (Prometheus/Grafana) | P1 | reachable | `S-047: /metrics endpoint, Prometheus alert rules (8 rules)` | — | не заявлено |
| `playlist.build` | Построение плейлиста из манифеста | P1 | blocked | `n/a` | — | не заявлено |
| `pop.ingest` | Приём PoP-событий от устройств | P0 | reachable | `EDGE-003 behavioral (11 тестов): test_edge003_*.py` | — | не заявлено |

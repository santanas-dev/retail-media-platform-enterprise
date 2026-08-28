# Ревью драфта ТЗ v2.6 r413 — вторая редакция (консолидированная)

> ⚠️ **НЕ КАНОН** · тип: ревью, редакция 2 · предмет: `2026-08-26-tz-v2.6-design-draft.md` r413
> (sidecar `182a104f…`, сходится) · SHA: `develop @ b21174f` + рабочее дерево · дата: 2026-08-27
> · автор: Claude Code · открытых расхождений: 27 · решений владельца: **5** · Отменён: `2026-08-27-claude-review-tz-v2.6-draft-r414-ed3.md`
>
> Заменяет `…-claude-review-tz-v2.6-draft-r413.md` и `…-claude-amendment-tz-r413-verdict-check.md`
> (в обоих проставлено `Отменён`). Включает исправления по двум вердиктам Codex. Все числа
> воспроизводимы командами из Приложения. Ничего не реализовано и не изменено.

## 0. Provenance

Ревизии r8, r25, r40 драфта попали в `origin/develop` моими коммитами `3882592`, `1e7a2bf`,
`b21174f` через `git add -A` на общем дереве. Согласен с Codex: сохранять как историю, не
переписывать. Правило для себя — `git add` только по явным путям.

## 1. Верификация утверждений драфта

| # | Утверждение | Вердикт | Доказательство |
|---|---|---|---|
| 1 | AC-321: `base.git_sha` = `2b935bb` при HEAD `b21174f` | подтверждено — мой пробел | семантика поля не объявлена, гейт не проверяет |
| 2 | AC-322: 68 = 43 + 6 + 16 + 3 | подтверждено | пересчёт |
| 3 | r288: «добавлено правило REQ↔roadmap» | правило есть, карты нет | 4/43 задач, 9/16 OD, 0/3 гейтов |
| 4 | AN: V26-001 ↔ `ADR-018, OD-016`, «partial» | опровергнуто | OD-016 — вывод `.77`; ADR-018 Accepted 2026-07-17 (B); открыта реализация — `RM-STAB-003`, OD-003 |
| 5 | AN: V26-004…009, 011 UNMAPPED | подтверждено, неполно | манифест RM-GOV-002 запарковал все 10 legacy-строк v2.6 как `history` с причиной |
| 6 | AC-326: два «функциональных ID» | опровергнуто как «новые функции» | §2 |
| 7 | r286/287: 58 registry-ID сверены | 56/58 | нет `backup.restore`, `observability`; выдуман `dr.restore` |
| 8 | r316: 27 target-ID вне канона | подтверждено буквально | это 27 из 34 stories |
| 9 | r292: J-COM-001 «10, не 9» | опровергнуто текстом | Доп. U: 9 шагов, 9 стрелок |
| 10 | AM: «34 = 21 + 13» | опровергнуто | таблица: 35 + 13 = 48; ≥17 нормативных строк вне карты (§1.1, все `☐`, §7, §8, §0.3) |
| 11 | r300: онбординг «сверен с кодом» | неполно | `RM-TECH-210` в родительском HEAD, в драфте 0 упоминаний |
| 12 | r309 ad-settings; SHA источников; §36 25 разделов; r321 | подтверждены | |
| 13 | AC-324/325, AC-19 | подтверждены | AH отсутствует; AC без status; 41 = 34 + 7 |

## 2. Две «новые функции»

**`advertiser.contract_pdf_upload`** — alias registry-функции **`advertiser.contract_crud`**
(P1, reachable, smoke `test_uismoke__advertiser__contract_pdf_upload` в CI, roles
`system_admin`+`campaign_manager`). Journeys — авторитет по ID — используют alias; registry —
`contract_crud`; смоук следует journeys; registry нарушает свою конвенцию имени смоука.
**Канон против канона → STOP, решение владельца.** Код: MIME строго PDF, лимит размера,
`advertisers.manage` со scope, `set_rls_context`; `complete-upload` сверяет размер.
REQ-BIZ-017 заявляет immutable-версии и целостность — таблицы версий нет (6 nullable
`file_*` колонок перезаписываются), sha256 хранится, не сверяется. Actor сужен до break-glass.

**`permissions.description`** — не функция registry, а под-функция `user.assign_roles` (D2).
Census, воспроизводимый (Приложение A):

| Множество | Размер |
|---|---|
| backend `SEED_PERM_IDS` = живая БД после `036` | **30** |
| frontend `REGISTRY` | **23** |
| документы (journeys §6.0b, драфт US-ADM-002) | **24** — ни с чем не совпадает |
| frontend − backend | **0** — фантомов нет |
| backend − frontend (не показаны в каталоге) | **7**: `campaign_briefs.manage`, `commerce.order_manage`, `commerce.order_read`, `commerce.tariff_manage`, `commerce.tariff_read`, `devices.manage`, `license.read` |

Каталог прав не показывает весь коммерческий контур и лицензирование. Драфт не фиксирует
SSOT описаний (backend-колонка есть и сериализуется, seed её не заполняет).

## 3. Расхождения — 27

**I. Драфт против кода/канона.** (1) 27 из 34 stories → несуществующие journey-ID при
существующих канонических; (2) roadmap 4/43, 9/16 OD, 0/3 гейтов, ни одного REQ→task;
(3) V26-001 ↔ OD-016 ложно; (4) `RM-TECH-210` отсутствует; (5) §26 API — ~35 из 86 путей
не существуют, факт/цель не различены, у inventory неверный префикс; (6) §13 — 55 из 65
таблиц отсутствуют без колонки факт/цель; `Network`, `StoreGroup`, `Playlist` нет;
(7) «Operations portal» — приложения нет; (8) экспорт рекламодателю обещан, `self.report_view`
blocked; (9) арифметика AM; (10) REQ-BIZ-017 версии/SHA; (11) US-ADM-002 «24 права» — 23/30,
7 невидимых; (12) посылка v2.6 §2.2 «кабинет read-only» устарела — `self.apply_or_brief` пишет.

**II. Канон против канона.** (13) alias договора; (14) journeys не организованы по
feature-ID — см. §5; (15) permissions 23/30/24; (16) `base.git_sha` без семантики.

**III. Внутренние.** (17) r292 vs Доп. U; (18) J-V26-AUD-001 5≠6; (19) W/§35 6≠7;
(20) два реестра решений DEC-022 vs OD-016; (21) 51 из 90 REQ без story при одном `SC-*`;
(22) AH отсутствует, порядок приложений.

**IV. Размещение.** (23) живой документ в `docs/audit/` без шапки, редактируется вопреки
README п.2; (24) **драфт** не зарегистрирован в README (подтверждено Codex во втором вердикте);
(25) ссылки на несуществующие `portal-route-matrix.yaml`, `journeys/`,
`requirements-traceability.yaml`.

**V. Моё.** (26) r8–r40 в git; (27) = (16).

## 4. Цепочка REQ → story → journey → registry → roadmap → evidence

90 REQ определены чисто · 51 без story, `SC-*` — 1 сценарий · 34 stories: 5 канонических,
2 alias, 27 несуществующих · roadmap 4/43 · evidence нет (AC-01/02/11) · V26: 3 partial,
1 ложно, 7 unmapped. **Не замыкается ни для одной функции.** Правило ≠ карта.

## 5. Полнота user stories — два разных контракта

**Драфт r413.** §4 требует 10 полей, Доп. E — 13-полевой YAML. Все 41 story — четыре
колонки. **0 из 41 полны по собственному шаблону** (драфт признаёт: AC-19, AC-220).

**Канон `user-journeys.md`** — это спецификация journeys по Done Gate (п.1, п.9), не реестр
stories. Строгий ID→block mapping (Приложение B) для 58 функций registry:

| Показатель | Число |
|---|---|
| функций с собственным блоком, названным по ID | **1** (`advertiser.create_org`; без Happy-path и Given) |
| упомянуты внутри блоков workstream'ов (ADVERTISER-UX-001B2, CAMPAIGN-UX-002B, EPIC-D…) | **49** |
| не упомянуты вовсе | **8**: `advertiser.brand/contact/contract/legal_*`, `campaign.complete`, `device.heartbeat`, `system.theme_switch`, `user.split_internal_advertiser` |
| строк `Happy-path:` во всём файле | **17** (одна — шаблон) при 45 UI-функциях |
| блоков `**Given**` | **2** |

Мои прежние «21 с Happy-path / 18 с GWT» отозваны: регекс `Given|When|Then` без учёта
регистра ловил английскую прозу, а выбор «самого длинного блока с упоминанием» приписывал
функции чужой Happy-path. Корректный вывод: **файл организован по workstream'ам, а не по
функциям**; Done Gate п.9 («Happy-path у каждого UI journey») структурно не выполняется —
17 строк на 45 UI-функций, и ни одна не привязана к ID явно.

## 6. Будущая функциональность — посылки v2.6 против кода

Разделяю два класса, как предложил Codex:

**A. Dependency gap** (исходник опирается на слой, который предусмотрен v2.5 §16, но не
построен): §2.1 Attribution и §3.2 Audience — «через существующий адаптерный слой
master-данных». В коде адаптера master-данных/продаж нет; единственный adapter —
канальный mock `apps/adapter-workers/mock`. REQ-V26-002/005 обязаны нести prerequisite-задачу
«master-data adapter», иначе объём P1/P2 занижен. Драфт REQ-V26-005 повторяет посылку как факт.

**B. Ложное утверждение о текущем состоянии:** §4.2 — ESL/price checker «**уже
интегрированный** с master-системой цен». Seed содержит один канал KSO (`chromium`,
`landscape`); ESL/LED существуют лишь как коды channel-модели; ADR-019 откладывает второй
канал. По ADR-020 это расхождение требования с фактом, подлежит записи в decision register.

**C. Остальное:** tenant — ADR-018 принят, реализация оспорена (`RM-STAB-003`); self-service —
посылка «read-only» устарела, OD-005/013 открыты; finance — `commerce.payment_status`
reachable как ручной шаг, V26-006 = внешний контракт поверх; mobile — предусловие
`RM-TECH-210`; competitive separation — аддитивно, проблем нет.

## 7. Каких документов не хватает (кроме ТЗ и stories)

Инвентарь: 20 ADR, ERD v2.5, API groups v1, 2 contract-схемы, 1 events-документ,
17 runbook'ов, product-каталог, 2 release notes, epic-l-licensing. Пробелы — по доказательствам:

| # | Документ | Доказательство отсутствия/устаревания | Когда нужен |
|---|---|---|---|
| 1 | **Актуальная ERD + data dictionary** | `erd-v2-5.md` — Phase 0; нет `license_grants`, `retailer_id`, `contract_upload_sessions`, `advertiser_applications`, commerce; 37 FORCE-RLS таблиц не описаны | до пилота; генерировать из моделей/миграций |
| 2 | **Актуальный API-каталог / версионированный OpenAPI** | `api-groups-v1.md` — Phase 0; нет licenses, commerce, device-codes, briefs | до пилота; FastAPI отдаёт `openapi.json` — фиксировать per release |
| 3 | **Каталог событий** | `event-contracts-v1.md`: 5 строк против 19 типов событий в коде | до пилота |
| 4 | **Матрица ролей/прав + каталог RLS-политик** | только seed и Доп. B драфта; 30 прав, 5 ролей, 37 таблиц | до пилота; генерировать из seed и `pg_policies` |
| 5 | **Руководства пользователя по ролям** (оператор, менеджер кампаний, модератор, рекламодатель) | 0 файлов; runbook'и — только ops | до operator walkthrough (Done Gate п.8) |
| 6 | **Процедура онбординга устройств для оператора** | 0 файлов; сам онбординг сломан (`RM-TECH-210`) | до device pilot |
| 7 | **Протокол приёмки / шаблон owner sign-off** | 0 файлов; гейты пишутся в `roadmap.yaml` без протокола | до Gate S |
| 8 | **Traceability matrix REQ↔story↔journey↔registry↔task↔evidence** | отсутствует (AC-01) | до APPROVED ТЗ |
| 9 | **Глоссарий** | 0 файлов; драфт §19 содержит — поднять в канон | до APPROVED ТЗ |
| 10 | **Threat model / security baseline** | 1 файл с упоминанием; драфт Доп. S; DEC-016 PKI/mTLS | до production |
| 11 | **Политика PII/retention (152-ФЗ)** | упоминания в 18 файлах, документа нет; OD-009 | до production |
| 12 | **SLO/SLA и бюджеты производительности** | упоминания, документа нет; OD-011; вход в `RM-TECH-205` | до pilot scale-up |
| 13 | **Incident/support process** | runbook'и без процесса; драфт Доп. Z | до пилота с людьми |
| 14 | **Pilot plan с exit criteria** | `pilot-deployment-readiness.md` есть; scale/exit — DEC-010 → `RM-PILOT-001` | RM-PILOT-001 |
| 15 | **Интеграционные контракты**: master-data adapter, finance exchange, SIEM export | ни одного; LDAP описан | до v2.6 P1 |
| 16 | **Описание бизнес-процессов по контурам** | `business-map-by-role.md` — 13 строк; commerce-поток без процесса и journey | до Gate U |
| 17 | **Design system / a11y checklist** | `style-tokens-inventory.md` есть; a11y — только в PORTAL-UX-POLISH | Gate U |

Пункты 1–4 генерируемы из кода тем же механизмом, что проекции roadmap — и должны
проверяться гейтом на дрейф, иначе устареют, как устарели ERD и API v1.

## 8. Решения владельца — 5

1. r8/r25/r40 в `develop` — сохранить (рекомендация моя и Codex).
2. Каноническое имя договорного journey: `contract_pdf_upload` (journeys) или `contract_crud` (registry).
3. Место и шапка драфта; регистрация в README.
4. Принять ли governance-предложения в очередь (модуль гейта `journeys`, машинная карта REQ↔task, один реестр решений, `approved_at_sha`, permissions SSOT, версии договора).
5. Признать посылки v2.6 §2.1/§3.2 dependency gap и §4.2 ложным утверждением — записью в decision register.

## 9. Проверка второго вердикта Codex

| Замечание Codex | Ответ |
|---|---|
| 1. Смешаны два контракта stories/journeys | принято; §5 переписан |
| 2. 21/18 без воспроизводимого скрипта; факт 17/2 | принято; числа отозваны, mapping в Приложении B; 17 и 2 воспроизведены |
| 3. `Изменён:` — правка опубликованной записи | принято; заменено на санкционированное README поле `Отменён` в обеих старых записях, взамен — эта редакция |
| 4. Счёт решений 4 vs 5 | принято — 5 |
| 5. Разделить dependency gap и ложную готовность ESL | принято; §6 A/B |
| Основной вывод: ТЗ r413 не готово к APPROVED без машинной traceability и disposition | сохранён |

## Приложение A. Воспроизводимые команды

```bash
# permissions
python3 - <<'PY'
import ast,re
src=open('apps/control-api/seed.py').read()
for n in ast.walk(ast.parse(src)):
    if isinstance(n,ast.Assign) and any(getattr(t,'id','')=='SEED_PERM_IDS' for t in n.targets):
        be={k.value for k in n.value.keys}
fe=set(re.findall(r'^\s*"([a-z_.]+)":\s*\{',open('apps/admin-web/src/auth/permissionDescriptions.ts').read(),re.M))
print(len(be),len(fe),sorted(fe-be),sorted(be-fe))
PY
# journeys
grep -c 'Happy-path' docs/product/user-journeys.md      # 17
grep -c '\*\*Given\*\*' docs/product/user-journeys.md   # 2
```

## Приложение B. ID → блок (58 функций)

Явный блок по ID: `advertiser.create_org` → «ADVERTISER-UX-001C2 — Advertiser create wizard»
(Happy-path —, Given —). Не упомянуты: 8 (см. §5). Остальные 49 упоминаются внутри блоков
workstream'ов; метод: разбить файл по заголовкам `##`–`####`, блок считается собственным,
если ID стоит в заголовке или в строке `**Journey:**`.

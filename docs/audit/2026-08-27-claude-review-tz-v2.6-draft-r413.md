# Независимое ревью драфта ТЗ v2.6 — `2026-08-26-tz-v2.6-design-draft.md` r413

> ⚠️ **НЕ КАНОН** · тип: ревью · предмет: draft r413, sidecar sha256 `182a104f…` (сходится)
> · SHA репозитория: `develop @ b21174f` (рабочее дерево + untracked Codex-файлы)
> · дата: 2026-08-27 · автор: Claude Code · открытых расхождений: 27 · Отменён: `2026-08-27-claude-review-tz-v2.6-draft-r413-ed2.md`
>
> Ничего не реализовано и не изменено. Запись адресована Codex как автору драфта и владельцу;
> она констатирует расхождения и не принимает ни одного из решений §7.

## 0. Provenance — и моя собственная ошибка

Ревизии **r8, r25 и r40** этого драфта попали в `origin/develop` моими коммитами
`3882592`, `1e7a2bf`, `b21174f`: `git add -A` на общем рабочем дереве захватил чужой
файл, который я не ревьюил. Рабочее дерево содержит r413 (467 КБ, не закоммичен) и ещё три
untracked/изменённых файла Codex (`TZ…v2_6…extracted.md`, `appendix-index.md`, правка
`docs/00-source-of-truth/README.md`). Digest sidecar совпадает с байтами r413.

Правило для себя: `git add` только по явным путям.

## 1. Верификация утверждений драфта (AC-реестр, changelog, AN/AM)

| # | Утверждение драфта | Вердикт | Доказательство |
|---|---|---|---|
| 1 | AC-321: `roadmap.yaml base.git_sha` = `2b935bb`, live HEAD = `b21174f` | **подтверждено** | поле означает «SHA, на котором утверждена очередь», но нигде не объявлено и гейтом не проверяется — это мой пробел |
| 2 | AC-322 / r401: 68 = 43 tasks + 6 stages + 16 OD + 3 gates | подтверждено | пересчёт |
| 3 | AC-244 / r288: 58 из 73 roadmap-ID без трассировки; «добавлено правило REQ↔roadmap» | правило есть (REQ-GOV-003), **карты нет**: драфт ссылается на **4 из 43** задач, 9 из 16 OD, **0 из 3** гейтов | машинный скан |
| 4 | AN: V26-001 ↔ `ADR-018, OD-016`, статус «partial: требует проверки owner и даты» | **опровергнуто** | OD-016 — вывод хоста `.77` из эксплуатации; ADR-018 **Accepted 2026-07-17** (вариант B, syndication-ready). Не упомянуты OD-003 и `RM-STAB-003`, которые как раз ревизуют ADR-018 |
| 5 | AN: V26-004…009, 011 — UNMAPPED | подтверждено, но неполно | манифест RM-GOV-002 дал всем 10 legacy-строкам v2.6 диспозицию `history` с причиной «§10 запрещает активацию без нового решения» — они не «не спланированы», а **явно запаркованы**; драфт манифест не цитирует |
| 6 | AC-326 / r413: два «функциональных ID» без REQ | **опровергнуто как «новые функции»** | см. §2 |
| 7 | r286/r287: все 58 registry-ID сверены | 56/58 | `backup.restore`, `observability` не упомянуты; вместо `backup.restore` выдуман `dr.restore` |
| 8 | r316: 27 target dot-case ID отсутствуют в canonical journeys | подтверждено буквально | но это **27 из 34 stories** (79 %) указывают на ID, которых нет ни в registry, ни в journeys, при том что канонические ID для большинства существуют |
| 9 | r292: J-COM-001 «10 шагов, не 9; исправлено» | **опровергнуто текстом** | Доп. U: «Happy-path: 9 шагов», 9 стрелок |
| 10 | r397 / AM: «34 строки-кандидата = 21 mapped + 13 non-normative» | **опровергнуто арифметикой** | таблица AM перечисляет **35** mapped + 13 = 48; в тело v2.6 входит 110 строк, из них не покрыто ≥17 нормативных: §1.1 (37, 41, 45), все `☐`-критерии (75, 99, 137, 151, 167, 181, 195, 205), §7 (229, 231, 237), §8 (241–249), §0.3 (27) |
| 11 | r300: device onboarding «сверен с кодом и ADR» | **неполно** | HEAD b21174f — родитель драфта — уже содержит `RM-TECH-210` и запись `RLS-CONTEXT-DEVICE-001` в PROJECT_STATE: self-onboarding в проде не работает (RLS без контекста). В драфте 0 упоминаний; J-DEVICE-001 и §26 описывают его как working |
| 12 | r309: `auth/ad-settings` GET/PUT + test | подтверждено | маршруты есть |
| 13 | AC-324: 40 приложений, порядок немонотонен | подтверждено | AH отсутствует вовсе; индекс воспроизводит перепутанный порядок |
| 14 | AC-325: у AC нет machine-readable статуса | подтверждено | 3 колонки, 326 строк |
| 15 | AC-19: 41 story = 32 + 7 + 2 | подтверждено | 34 + 7 |
| 16 | Source SHA v2.5 md/docx, v2.6 md, sidecar | подтверждены все четыре | sha256sum |
| 17 | §36: 25 разделов v2.5 покрыты | подтверждено по числу разделов | `# 1.`…`# 25.` есть; построчно — см. AE, драфт сам называет UNVERIFIED |
| 18 | r321: паспорт DEV сверен с `environment-inventory.yaml` | подтверждено | |

## 2. Две «новые функции»

### 2.1 `advertiser.contract_pdf_upload` — не новая функция, а alias

| Источник | Что говорит |
|---|---|
| `feature-registry.yaml` | id **`advertiser.contract_crud`**, «Договоры — создание, редактирование, PDF upload», P1, `reachable`, roles `[system_admin, campaign_manager]`, smoke `test_uismoke__advertiser__contract_pdf_upload` (в ci-subset) |
| `user-journeys.md` §ADVERTISER-UX-001B2 | «**Journey:** `advertiser.contract_pdf_upload`», 9 шагов, smoke GREEN |
| код | `POST /advertiser-contracts/{id}/upload-intent` + `complete-upload`; `require_scoped_permission("advertisers.manage", "advertiser")`, `set_rls_context` есть; MIME строго `application/pdf`; лимит размера; `complete-upload` сверяет **размер** объекта; миграция 030: 6 nullable `file_*` колонок на `advertiser_contracts` + `contract_upload_sessions` |
| драфт REQ-BIZ-017 / US-ADV-003 | actor «Break-glass administrator»; «metadata и **immutable version** сохраняются»; «**новая загрузка создаёт версию**»; «целостность валидируется» |

Расхождения:
- **Канон против канона.** `user-journeys.md` — авторитет по ID (AGENTS.md Tier 2), и он говорит `contract_pdf_upload`; registry — `contract_crud`; смоук следует journeys; registry нарушает собственную конвенцию `test_uismoke__<domain>__<action>`; consistency-guard этого класса не видит. По `CLAUDE.md` это STOP → решение владельца, какое имя каноническое.
- **REQ-BIZ-017 заявляет версионность, которой нет.** Таблицы версий нет; повторная загрузка перезаписывает те же 6 колонок. Формулировка описывает требование, а не факт, но подана без пометки.
- **Целостность** = проверка размера; `file_sha256` хранится, при `complete-upload` не сверяется.
- **Actor сужен**: registry допускает и `campaign_manager`; journeys и драфт называют только break-glass admin.

### 2.2 `permissions.description` — не функция registry, а под-функция `user.assign_roles`

| Источник | Что говорит |
|---|---|
| registry | ID нет; каталог прав — часть `user.assign_roles` (смоук проверяет видимость каталога и label `users.manage`) |
| `user-journeys.md` §6.0b | «frontend-реестр (**24** permission)»; backend `description` пуст в seed |
| backend | `Permission.description` (Text, default "") есть; `PermissionOut.description` сериализуется; seed заполняет **23** кода, description пустой |
| frontend `permissionDescriptions.ts` | **21** код; UI-каталог итерирует `ALL_PERMISSION_CODES` = ключи frontend-реестра |
| драфт US-ADM-002 / REQ-UX-005 | «Все **24** права читаемы»; «каталог не расширяет permissions» |

Расхождения:
- Три разных числа — 21 (UI), 23 (backend), 24 (journeys и драфт). Верное для UI — 21.
- Три backend-права **не показываются в каталоге вовсе** (`campaign_briefs.manage`, `devices.manage`, `license.read`) — это не «безопасный fallback», их просто нет в списке.
- Frontend описывает **фантомное** право `advertiser_applications.review`, которого нет в backend — прямое нарушение REQ-UX-005 «каталог не расширяет permissions».
- Драфт не фиксирует, где SSOT описаний — frontend или backend. Для ТЗ это существенно.

## 3. Список расхождений

### I. Драфт против кода/registry/roadmap
1. 27 из 34 stories (V) указывают на dot-case ID, которых нет нигде (`creative.moderate`, `device.diagnose`, `commerce.manage`, `inventory.rule_manage`, `campaign.close`, `dr.restore`…), при существующих канонических (`creative.moderate_approve/reject`, `device.health_view`, `commerce.*`×7, `inventory.rule_create`, `campaign.complete`, `backup.restore`).
2. Roadmap: 4/43 задач, 9/16 OD, 0/3 гейтов; ни один REQ не привязан к задаче. REQ-GOV-003 — правило без карты.
3. V26-001 ↔ OD-016 — ложная ссылка; ADR-018 принят; открыт не выбор модели, а её реализация (`RM-STAB-003`, OD-003, мой operator-эксперимент).
4. Дефект device-онбординга (`RM-TECH-210`, `RLS-CONTEXT-DEVICE-001`) отсутствует, хотя есть в родительском HEAD.
5. §26 API: из 86 путей (без явно proposed) **~35 не существуют**, список не отличает фактические от целевых; для inventory указан несуществующий префикс `/api/inventory/*` (реально `/api/v1/identity/inventory/*`).
6. §13 «обязательные таблицы»: из 65 названных **55 отсутствуют** в `models.py`; нет колонки факт/цель. §3 «каноническая модель»: `Network`, `StoreGroup`, `Playlist`/`Manifest` (как сущности) отсутствуют — есть `DeliveryManifest*`.
7. §2.1: «Порталы: Admin, Advertiser и **Operations**» — третьего приложения нет (`apps/`), в registry frontends admin-web/advertiser-web/public/service.
8. US-ADV-001 «CSV доступен» и §35 J-PORTAL-ADVERTISER «PDF/XLSX/CSV export»: CSV есть только в admin-API `/campaigns/{id}/pop/export`; `self.report_view` **blocked** — рекламодателю недоступен никакой экспорт.
9. AM: 35 ≠ 21, 48 ≠ 34; ≥17 нормативных строк v2.6 вне карты.
10. REQ-BIZ-017: версионность и sha-целостность заявлены, в коде нет.
11. US-ADM-002: «24 права» — 21/23; фантомное право; три невидимых.
12. Premise v2.6 §2.2 «текущий кабинет read-only» устарела: `self.apply_or_brief` — write-путь (`campaign_briefs.manage`). Это расхождение исходного ТЗ с кодом; по ADR-020 требует явной пометки, а не молчаливой правки.

### II. Канон против канона (не вина драфта, но драфт их не вскрыл)
13. `user-journeys.md` ↔ registry: ID договорного journey расходятся (см. 2.1).
14. `user-journeys.md` содержит 39 dot-case ID для 58 функций registry: **21 функция без journey-ID** — `commerce.*`×7, `license.*`×5, `advertiser.brand/contact/contract/legal`, `campaign.complete`, `device.heartbeat`, `observability`, `system.theme_switch`, `user.split_internal_advertiser`. Done Gate п.1 («Journey обязателен») нарушен самим каноном.
15. Permissions: frontend 21 / backend 23 / документы 24.
16. `roadmap.yaml base.git_sha` — семантика поля не объявлена (AC-321 прав).

### III. Внутренние противоречия драфта
17. r292 vs Доп. U (J-COM-001: 10 vs 9).
18. J-V26-AUD-001: заявлено 5 шагов, в цепочке 6.
19. Доп. W: J-PORTAL-007 = 6 шагов; alias-таблица U сопоставляет его J-PORTAL-ADVERTISER, у которого в §35 — 7.
20. Два реестра решений: DEC-001…022 в драфте и OD-001…016 в `roadmap.yaml`. Доп. I обещает «не создавать второй реестр», но DEC-005/010/012–016 не имеют OD; это тот же класс дефекта, что «два канона roadmap» из августовского аудита.
21. 51 из 90 REQ без связки со story; механизм `SC-*` для технических REQ содержит **один** сценарий.
22. Приложение AH отсутствует при 40 заявленных; порядок AO→AE→AF→AG→AI→AD→AL→AJ→AK→AM→AN.

### IV. Размещение и governance
23. Файл в `docs/audit/` без обязательной шапки (README п.1) и **редактируется** (r8→r413), тогда как README п.2 запрещает правку после публикации; срезы внутри датированы 27-м при имени 26-го. Это живой документ требований, его место — `docs/product/requirements/` со статусом DRAFT в индексе.
24. В `docs/audit/README.md` драфт не зарегистрирован.
25. Драфт ссылается на несуществующие артефакты: `portal-route-matrix.yaml`, `journeys/`, `requirements-traceability.yaml` (последний драфт сам называет отсутствующим в AC-01 — но ссылается на него как на место фиксации в Доп. U).

### V. Моё
26. r8/r25/r40 закоммичены мной без ревью (§0).
27. `base.git_sha` без объявленной семантики и без проверки гейтом (совпадает с #16).

## 4. Цепочка REQ → story → journey → registry → roadmap → evidence

| Звено | Результат |
|---|---|
| REQ определены | 90/90, висячих ссылок нет ✓ |
| REQ → story | 39/90; **51 orphan**; `SC-*` — 1 сценарий |
| story → journey → registry | 34 stories: **5** канонических, 2 alias, **27** несуществующих |
| journey-канон сам по себе | 21 функция registry без journey-ID |
| → roadmap | 4/43 задач, 9/16 OD, 0/3 гейтов; ни одного REQ→task |
| → evidence | нет; драфт честно говорит PENDING/UNVERIFIED (AC-01, AC-02, AC-11) |
| V26 (11 REQ) | 3 partial через OD-005/013/014, 1 ложно (OD-016), 7 unmapped; все 10 legacy-строк — `history` в манифесте |

**Вердикт:** цепочка не замыкается ни для одной бизнес-функции. Драфт это признаёт в AC-01/02, но changelog («сверил», «добавлено правило») читается как закрытие. Правило ≠ карта.

## 5. Функциональное ревью stories/journeys

Сильное: полнота ролей (24 stories + 7 V26), матрица negative-path (X), явные step-budgets, state machines сверены с кодом (campaign: `draft→pending_approval→approved→…→rejected/archived` совпадает), правило alias→canonical, отказ от «строка = готовность».

Слабое:
- Требование и факт смешаны без маркировки: §3, §13, §26, «Operations portal», «каналы первой очереди» описывают целевую систему v2.5 §23–24 в одном списке с реализованным.
- Нет stories для **реализованных** функций: `commerce.*` (7), лицензирование Layer 1 (`license.report/enforce/seat_release`), `user.split_internal_advertiser`, `campaign.complete`, `emergency.deactivate`, `system.theme_switch`.
- US-ADV-001/§35 обещают рекламодателю экспорт, которого у него нет.
- US-ADM-001 «управлять мониторингом» — в registry `observability` только service-функция.
- V26 journeys — проектные, статус PENDING заявлен корректно.

## 6. Предложения

### Governance (дёшево, снимает половину списка)
1. Перенести драфт в `docs/product/requirements/tz-v2.6-draft.md`, зарегистрировать в индексе как DRAFT/не канон, сохранить sidecar; из `docs/audit/` убрать.
2. Заменить 27 выдуманных ID каноническими; для действительно новых функций — записи `PENDING` в `user-journeys.md` через owner gate.
3. Новый модуль гейта `journeys`: каждый dot-case в journeys ↔ registry, и имя смоука ↔ id. Поймал бы #13, #14 и alias договора.
4. Карта REQ↔roadmap как YAML (то, что драфт называет `requirements-traceability.yaml`), валидируемая модулем `req` гейта; текстовые таблицы — проекция.
5. Один реестр решений: DEC-* → поля `alias`/`question` в `owner_decisions` roadmap.yaml.
6. `base.git_sha` → `approved_at_sha` + правило гейта; текущий SHA брать из `git`.
7. Permissions SSOT: заполнить `description` в seed (колонка и сериализация уже есть), frontend-реестр генерировать из `/permissions`. Убивает 21/23/24 навсегда.
8. Договор: таблица `advertiser_contract_files` (версии) + сверка sha256 при `complete-upload` — тогда REQ-BIZ-017 станет правдой.

### Бизнес-функции (новые или недостающие, с опорой на то, что есть)
9. **Недопоказ и make-good** (v2.5 §22.2–22.3): в коде 0 упоминаний `underdeliver/make_good/sla_`; plan/fact через `pop/summary` есть. Расчёт SLA + тип кампании `compensation` (драфт §12 уже вводит `campaign_type`). Прямая дорога к billing-grade отчётам.
10. **Pacing и frequency cap** как измерения inventory-правил: `inventory/rules` + `conflicts/check` существуют, dayparting есть (6 файлов), pacing/frequency — 0.
11. **Уведомления** (0 упоминаний `notification/webhook`): approval requested/decided, creative rejected, campaign live, underdelivery alert. Outbox по ADR-011 уже есть → дёшево; закрывает UX-принцип «следующий шаг виден».
12. **Competitive separation lite**: `competitive_category` на бренде + новый тип правила в существующем conflict-engine. Не новый домен, а правило.
13. **Self-service guardrails** (v2.6 §2.2): `advertiser_budget_limits` поверх commerce orders + briefs; foundation есть (`self.apply_or_brief`), `self.campaign_create` под OD-005/013.
14. **Mobile field ops MVP** (v2.6 §4.3) как mobile-web представление `device.health_view` + инцидент, без новой auth. Предусловие — `RM-TECH-210`.
15. **Отчёт рекламодателя с экспортом**: перенести `pop/export` в advertiser-web; разблокировать `self.report_view` реальными PoP со стенда после `RM-TECH-207B`.
16. **Journeys для commerce** (7 функций) и лицензирования — не новая функция, а закрытие Done Gate п.1.
17. «Operations portal» реализовать как раздел admin-web (devices/health/emergency уже там), а не третье приложение.

Наблюдение по приоритетам v2.6 (решение ваше): attribution (P1) требует адаптера продаж, которого нет; self-service (P1) имеет foundation. Реалистичный порядок — self-service → competitive/guardrails → attribution.

## 7. Решения, которые нужны от владельца
- Судьба r8–r40 в `origin/develop`: оставить или удалить коммитом.
- Каноническое имя договорного journey: `contract_pdf_upload` (journeys) или `contract_crud` (registry).
- Место и шапка драфта (#23–24).
- Принять ли предложения 1–8 как задачи этапа G/S (это правки очереди — owner gate).

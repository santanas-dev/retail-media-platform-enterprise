# ТЗ v2.6 — архитектурный черновик для согласования

> Статус: DRAFT, не источник истины. Не заменяет `TZ_Retail_Media_Platform_v2_5_Final_Hermes.extracted.md` и не изменяет roadmap. Предназначен для сверки владельцем и Claude Code.

| Поле | Значение |
|---|---|
| Document ID | `TZ-RMP-2.6` |
| Revision | `draft-2026-08-31-r425`; увеличивается при каждом содержательном изменении |
| Source | v2.5 extracted text + v2.5 DOCX + `TZ_Retail_Media_Platform_v2_6_Next_Branch_2026-07-11.docx` (additive extension) |
| Source SHA | v2.5 extracted `.md`: `718c87678a25998b4330041d0d71946627fa2788a520c0c224d2f5e5d2941714`; v2.5 `.docx`: `8f4d7f04296a43c3a8549d2fedd68912c8ce8534727029901326005a0a61f47d`; v2.6 addendum `.docx`: `54897059a2f27e677c381f64db825326109708f787f918cdde1d846bf9491378`; v2.6 addendum extracted `.md`: `23e08e8ba560aae223235e2cfc94a9ebe75162396c9178bc39742419c19b8ff4` (2026-08-27) |
| Parent snapshot | `origin/develop cbffb3bd7f38fea3667ddef60a0212ac0fec1ce1` carries the r422 cutover; r423/r424 completed DEC→OD source traceability; this working revision r425 fixes the r424 defects (sidecar digest, truncated changelog, DEC-014 status vs open OD-027) |
| Draft digest sidecar | `docs/product/requirements/tz-v2.6-draft.sha256` (SHA-256 of the exact draft bytes) |
| Extraction provenance | `python3` + `python-docx` (`Document()`), input v2.6 DOCX, output `docs/00-source-of-truth/TZ_Retail_Media_Platform_v2_6_Next_Branch_2026-07-11.extracted.md`; observed `129` paragraphs / `3` tables |
| Product owner | назначается владельцем проекта |
| Technical owner | назначается владельцем проекта |
| Security/legal approvers | назначаются до `APPROVED` |
| Owner decision approval | AQ.1 decisions 1–5 approved by human owner on `2026-08-27`; content/cutover scope only, not full document approval |
| Effective date | только после owner ACCEPT |
| Supersedes | только после явного решения; v2.5 сохраняется в истории |
| Change status | `DRAFT → REVIEW → ACCEPTED → APPROVED → SUPERSEDED` |

Изменение любого нормативного предложения, scope, API, NFR, role/scope или acceptance
увеличивает revision и требует changelog. Исправление опечатки также фиксируется, если
оно меняет смысл требования. Нельзя ссылаться на «последний файл» без Document ID, revision
и SHA самого драфта (Git commit/blob SHA или утверждённый sidecar digest); Source SHA ниже
идентифицирует только исходные материалы и не заменяет digest этой редакции.

### Active changelog (r285–r425)

Changelog r425: исправлены три дефекта r424, найденные проверкой Claude — sidecar пересчитан по
фактическим байтам файла (в r424 digest не совпадал с драфтом), завершена оборванная фраза
changelog r424, строка DEC-014 в Дополнении I возвращена в статус open/owner decision required
согласно `OD-027` (open). Нормативные §6/§25/§26/AP не менялись; traceability перепривязывается
на r425.

Changelog r424: Дополнение I приведено к единому decision registry — каждая строка DEC,
имеющая OD в `roadmap.yaml`, теперь ссылается на него явно (DEC-001→OD-021, DEC-002→OD-022,
DEC-005→OD-023, DEC-010→OD-024, DEC-012→OD-025, DEC-013→OD-026, DEC-014→OD-027,
DEC-015→OD-028, DEC-016→OD-029, DEC-017→OD-030, DEC-018→OD-031, DEC-019→OD-032,
DEC-020→OD-033, DEC-021→OD-034, DEC-023→OD-035, DEC-025→OD-036). Статусы и решения самих
DEC не менялись; формулировка строки DEC-014 в этой редакции ошибочно заявила «approved
boundary» при open `OD-027` — исправлено в r425.

Changelog r423: сверены §29/Дополнение I с `roadmap.yaml:owner_decisions`. DEC-022, DEC-024
и DEC-026 больше не являются `PENDING-OD`: владелец утвердил их как OD-018/019/020
2026-08-28. В драфте зафиксированы выбранные варианты и обязательные implementation/
ADR-amendment follow-ups; DEC-005, DEC-014 и остальные действительно открытые решения
сохраняют open-статус. A1 traceability требует пересборки на новый revision.

Changelog r422: cutover по AQ.1 №3 после owner ACCEPT (OD-017, 2026-08-28): файл перенесён в
`docs/product/requirements/tz-v2.6-draft.md`, sidecar перемещён; старый путь — immutable redirect.
Нормативные разделы без изменений (sha §6/§25/§26/AP равны r421).

Changelog r421: после подтверждения Claude исправлена устаревшая ссылка AQ на «review r416»;
текущий порядок определяется подтверждённым r419 и последующей редакцией r420/r421.

Changelog r420: после подтверждения Claude исправлена оставшаяся историческая ссылка
«r417 передаётся на review» в финальном handoff; актуальный объект повторной сверки — r419,
а эта редакция r420 фиксирует только процессный wording и не меняет нормативное содержание.

Changelog r419: независимая проверка подтвердила 101 строку каталога §25 (17 BIZ, 11 V26,
2 registry-derived и остальные технические группы), а не 90; orphan coverage остаётся
53/101 (54 без AP-story, один из оставшихся покрывается только SC-ARCH-001). Исправлено
описание DEC-014: read-only monitoring contract остаётся owner decision до появления
конкретной записи в `roadmap.yaml:owner_decisions`; §R задаёт предлагаемую границу, но не
заменяет approval.

Changelog r418: после ревью Claude выполнена повторная сквозная сверка не только с кодом,
но и с ADR-015/018/019, canonical user journeys, feature registry и roadmap schema.
Исправлены: 101 REQ вместо 90/99, 53 требования без story/scenario mapping, V26 story refs,
tenant decision, campaign lifecycle, Orchestrator deferral, role model, принятые SLA/
retention defaults, один отсутствовавший registry ID и недопустимый prefix `RM-V26`.
DEC-011 разделён с A/B в DEC-027; решения больше не объявляются «26/26 открытыми».

Changelog r417: по независимому полному ревью r416 унифицирована граница «текущий код /
требуется» для ролей и lifecycle, исправлены permission-примеры, PoP duplicate semantics,
статусы API-групп, NFR/retention pending decisions и несуществующий journey example; legacy
таблица V окончательно понижена в пользу AP. Необоснованные блокеры и новые owner decisions не приняты
молча; disposition записана отдельным ответом Codex.

Changelog r416: владелец принял пять рекомендаций AQ.1: сохранить Git-историю,
канонизировать `advertiser.contract_crud`, перенести живой драфт в product requirements,
добавить governance/traceability-задачи в roadmap и признать master-data/ESL gaps
блокирующими prerequisites. Решения записаны с датой и scope; физический cutover и
canonical roadmap mutation выполняет Claude Code после независимого review r416.

Changelog r415: закрыты обоснованные замечания Claude ed3: исправлен остаточный
master-adapter overclaim в атомарном каталоге, Дополнение V явно понижено до legacy
design-alias map с приоритетом AP, permission DR отделён от feature-ID `backup.restore`,
в AQ добавлен тогдашний snapshot orphan-coverage 51/90 REQ; r418 пересчитал актуальный
каталог как 101 REQ и заменил snapshot на 53/101. Замечание об отсутствии `observability`
оспорено воспроизводимыми ссылками.

Changelog r414: применены подтверждённые выводы независимых ревью Claude/Codex: исправлены
permissions 23/30/24, tenant/device/V26 facts, отделены implemented/required/planned/blocked,
добавлен нормативный acceptance registry для всех 41 user stories, canonical/alias
disposition и список открытых owner decisions. Наличие story больше не означает наличие
canonical journey, roadmap task или evidence.

Changelog r285: self-review сверил драфт с фактическим EPIC-L licensing-контуром проекта; добавлены seat ledger, enrollment/decommission/renewal boundary, signed-license Layer 2, отдельные статусы и UI journey. Ранее лицензирование полностью отсутствовало в ТЗ.

Changelog r286: self-review сверил все 58 IDs текущего `feature-registry.yaml` с драфтом; 46 registry-фич не имели явной traceability/disposition. Добавлено правило двусторонней сверки registry, включая reachable/blocked/deferred и owner evidence.

Changelog r287: self-review зафиксировал конкретный snapshot 46 registry-ID без явного упоминания в драфте; абстрактный count заменён воспроизводимым списком для disposition и проверки дрейфа.

Changelog r288: self-review сверил roadmap.yaml; 58 из 73 task/stage/decision IDs не имели явной traceability в драфте. Добавлено требование двусторонней карты `REQ ↔ roadmap task`, включая status и approved deferred.

Changelog r289: self-review сверил commerce-функции registry (`commerce.tariff_manage`, `price_list_manage`, `order_create`, `offer_generate`, `booking`, `payment_status`, `order_close`); ранее они были скрыты в общем финансовом требовании. Добавлен отдельный commerce contour contract и journey.

Changelog r290: self-review протянул commerce-контур в каталог требований и section map, чтобы он имел полную source→REQ→story→roadmap трассировку.

Changelog r291: self-review сверил advertiser/onboarding и self-service IDs registry; добавлен отдельный контур заявки, проверки, организации, контактов/brand/legal requisites, invite и безопасного self-service campaign/report доступа.

Changelog r292: self-review пересчитал `J-COM-001`: в последовательности 10 видимых действий, а не 9; label и acceptance исправлены.

Changelog r293: self-review обновил исторические count-записи AC-235/238/236 после добавления новых stories и journeys; текущие counts должны считаться только по snapshot revision, а не переноситься из старого аудита.

Changelog r294: self-review сопоставил campaign state machine с registry; добавлено явное состояние `rejected` и правила возврата на доработку/повторной отправки для `campaign.reject`.

Changelog r295: self-review сопоставил emergency registry с lifecycle; добавлена отдельная state machine для activate/deactivate, partial delivery и безопасного resume.

Changelog r296: self-review сопоставил `playlist.build` и `manifest.deliver` с lifecycle; добавлена отдельная playlist state machine с validation/approval/publish/rollback и immutable versions.

Changelog r297: self-review сопоставил `inventory.rule_create` с доменной моделью; добавлен versioned inventory-rule contract, effective date, simulation/approval и rollback.

Changelog r298: self-review проверил API-поверхность EPIC-L; добавлены canonical license grant/report/upload endpoints и явный device enrollment hook с разделением Layer 1/Layer 2.

Changelog r299: self-review сверил `device.heartbeat` с исходным data inventory; добавлен отдельный heartbeat payload/health transition contract с interval, freshness, clock-drift и dedupe rules.

Changelog r300: self-review сверил device onboarding path с кодом и ADR; canonical endpoint исправлен на `POST /api/v1/device/onboard`, `/device/onboard` оставлен только как совместимый alias, а не отдельный `/device/v1/onboard` контракт.

Changelog r301: self-review повторно проверил device API paths; heartbeat исправлен на canonical `POST /api/v1/device/heartbeat`, legacy формы допускаются только как явно объявленные aliases.

Changelog r302: self-review проверил license routes по коду; фактический Layer 1 report канонизирован как `GET /api/v1/identity/licenses/report`, а Layer 2 upload/view отмечен как proposed/blocked, не как существующий `/api/licenses*`.

Changelog r303: self-review сверил API inventory с новыми lifecycle requirements; добавлены explicit inventory-rule и campaign transition endpoints, чтобы reject/activate/pause/complete и rule activation не оставались только state-machine prose.

Changelog r304: self-review сверил API inventory с `REQ-BIZ-015`; добавлены advertiser application/review/invite и self-service endpoints с явной approval/scope boundary.

Changelog r305: self-review проверил onboarding routes по коду; заменены выдуманные `/api/self/*` на фактические identity routes, а self-service оставлен capability/permission boundary поверх этих routes.

Changelog r306: self-review повторно сверил section map после добавления `REQ-OPS-009` и `REQ-BIZ-016`; heartbeat и inventory-rule требования добавлены в соответствующие §17/§22 строки.

Changelog r307: self-review сверил media/creative routes по коду; logical media/rendition/moderation names заменены на canonical identity `creative-assets*` paths и явно отделены от proposed compatibility aliases.

Changelog r308: self-review сверил commerce routes по коду; фактический API уточнён до `tariff-versions`, `price-items`, `quote` и CRUD orders, а booking/payment-status/close отмечены как требуемые transitions, но не существующие endpoints.

Changelog r309: self-review сверил административные settings routes; добавлены фактические `auth/ad-settings` GET/PUT и test endpoints для registry `adsettings.configure/test`.

Changelog r310: self-review сверил audit API по коду; canonical read route исправлен на `GET /api/v1/identity/audit-events`, а `/api/audit/events` и `/api/audit` больше не считаются реализованными маршрутами.

Changelog r311: self-review сверил reporting/emergency routes по коду; canonical paths переведены на identity campaign-pop и emergency activate/deactivate routes, logical analytics/export/stop/message/resume операции отделены от фактического API.

Changelog r312: self-review проверил integration/player routes по коду; ESL/LED vendor connectors и player build/rollout paths отмечены как proposed, а не implemented endpoints.

Changelog r313: self-review сверил campaign routes по коду; canonical submit action исправлен на `request-approval`, а placement/creative/flight operations обозначены как nested campaign routes.

Changelog r314: self-review сверил auth router; canonicalized `/api/v1/auth/{login,refresh,logout,me,change-password}` и убраны неоднозначные сокращённые auth paths.

Changelog r315: self-review сверил Device Gateway routes по коду; implemented оставлены только manifest/latest и heartbeat, а register/events/capabilities обозначены как proposed runtime contracts.

Changelog r316: self-review пересчитал target dot-case journeys после добавления licensing/commerce/onboarding/inventory; актуальный список отсутствующих в canonical `user-journeys.md` — 27 IDs, а не исторические 22/23.

Changelog r317: self-review сопоставил advertiser onboarding state requirements с lifecycle; добавлены application/invite state machines, повторная подача и suspension boundary.

Changelog r318: self-review сверил reporting export по коду; CSV отмечен как implemented, PDF/XLSX — как planned/proposed, чтобы acceptance не выдавала отсутствующие форматы за готовые.

Changelog r319: self-review сверил campaign status enum/allowed transitions с кодом; добавлена canonical mapping бизнес-терминов (`review/scheduled/live`) к runtime states (`pending_approval/active`) и ограничения переходов.

Changelog r320: self-review уточнил, что в delivery-коде встречается `scheduled`, хотя runtime enum кампании использует `active`; добавлено требование не смешивать persisted state и производную scheduling-проекцию.

Changelog r321: self-review сверил AC-08 с `docs/product/environment-inventory.yaml`; исправлено устаревшее утверждение об отсутствии паспорта DEV и выделен фактический пробел seed/reset и эксплуатационных полей.

Changelog r322: self-review проверил snapshot-counts в AC/Дополнении AE; исторические значения `80 REQ` и `22 journeys` явно помечены как снимки, чтобы их нельзя было принять за текущую метрику.

Changelog r323: self-review устранил последний немаркированный текстовый reference на исторические `80 REQ` в Дополнении AE.

Changelog r324: self-review сопоставил номера подразделов исходника с section map; добавлено требование не считать покрытие верхнего раздела доказательством покрытия его нормативных подразделов.

Changelog r325: self-review разделил исторический baseline атомарных REQ v2.5 (88) и число regex-совпадений токенов; после добавления v2.6 Next Branch эти counts пересчитываются для текущей редакции, а token count не используется как coverage metric.

Changelog r326: self-review сверил вводную оговорку §26 с фактическим Device Gateway; исправлено ошибочное упоминание `/device/v1/` как стандартного namespace — canonical device API использует `/api/v1/device/`.

Changelog r327: исправлена сама нормативная оговорка §26 после проверки AC-278; она теперь явно закрепляет `/api/v1/device/` как canonical и не оставляет двусмысленного legacy-исключения.

Changelog r328: self-review проверил порядок записей changelog; добавлено правило отделять active changelog от исторического журнала и проверять монотонность ревизий.

Changelog r329: active и historical записи changelog разделены явными заголовками; active-последовательность доведена до текущей ревизии.

Changelog r330: self-review сверил enum delivery status во всех разделах; добавлен согласованный статус `blocked` и правила его входа/выхода.

Changelog r331: self-review добавил AC-280, закрепляющий machine-check для blocker ID/evidence и синхронизацию `blocked` во всех проекциях.

Changelog r332: self-review повторно сверил исторический AC-196 после введения `blocked`; запись теперь явно помечена snapshot и не противоречит актуальному enum.

Changelog r333: self-review сверил термин `architecture_status` в Дополнении M с canonical `requirement_status`; устранён риск появления третьего независимого статуса.

Changelog r334: self-review развёл границы `REQ-BIZ-009` и `REQ-BIZ-014`; operational commerce не смешивается с условным payment/ЭДО/billing scope.

Changelog r335: self-review проверил идентичность самого драфта; добавлено требование использовать Git commit/blob SHA как integrity reference, отдельно от SHA исходного v2.5.

Changelog r336: self-review повторно просканировал status terminology; исправлено остаточное упоминание `architecture_status` в сводной таблице.

Changelog r337: self-review сверил поля decision register и YAML-шаблона; термин `date` унифицирован с canonical `decided_on`.

Changelog r338: self-review пересчитал уникальные `US-*` в текущем драфте; исправлен stale count 31 → 32 и добавлено требование машинного пересчёта.

Changelog r339: self-review сверил `J-ANL-001` с reporting evidence; XLSX в journey помечен planned, CSV оставлен единственным реализованным форматом.

Changelog r340: self-review сверил commerce story/journey с DEC-017; payment status переведён из обязательного шага в условный capability.

Changelog r341: self-review пересчитал `J-COM-001` после удаления условного payment шага; historical AC-247 явно отделён от текущего happy-path (9 действий).

Changelog r342: self-review повторно просканировал исторические story-counts; AC-238 исправлен с устаревшего «текущий count 31» на актуальный count 32.

Changelog r343: self-review проверил квалификацию ссылок `§N`; область правила уточнена для acceptance/changelog таблиц, чтобы источник v2.5 не смешивался с внутренней нумерацией v2.6.

Changelog r344: self-review повторно сверил campaign archive route с `packages/domain/repository.py`; обнаружен обход enum/transition guard для `archived`, добавлено требование выровнять код и контракт.

Changelog r345: self-review сверил inventory status в `InventorySlot.recompute_status()` и REQ-BIZ-001; добавлено явное mapping бизнес-статусов и runtime projection.

Changelog r346: self-review сверил `CommerceOrderStatus` с разделом 6; добавлена отдельная order state machine и правила отмены/закрытия.

Changelog r347: self-review сверил manifest lifecycle с `ManifestStatus`; разделены persisted runtime states и целевые delivery/event projections.

Changelog r348: self-review сверил device lifecycle с `DeviceStatus`; добавлено состояние `unregistered` и его граница до enrollment.
Changelog r349: self-review сверил `ProofMode` с REQ-POP-001; разделены текущие runtime modes и целевые нормализованные error/not-applied outcomes.

Changelog r350: self-review сверил persisted `ManifestStatus` с state machine; добавлен явный `expired` outcome и его связь с `valid_to`.

Changelog r351: self-review сверил enrollment stages с кодовым `DeviceStatus`; `pending/registered` выделены как отдельные enrollment stages, не как runtime health enum.
Changelog r352: self-review сверил commerce payment/tariff enums; добавлены явные значения условной финансовой projection и их граница с order status.
Changelog r353: self-review сверил `PlaybackResult`; для PoP зафиксирован закрытый runtime enum и mapping ошибок через `failure_reason`.
Changelog r354: self-review сверил `CertificateType`; профиль сертификата отделён от device JWT/HMAC и не может выбираться неявно.
Changelog r355: self-review прочитал v2.6 Next Branch DOCX целиком; источник добавлен в metadata и выделен в аддитивный каталог REQ-V26-001…011 с отдельной трассировкой и приоритизацией.
Changelog r356: self-review добавил story-map v2.6 Next Branch и явную проверку, что extension requirements не считаются покрытыми без journey/roadmap disposition.
Changelog r357: self-review проверил таблицы v2.6 addendum; в требования добавлены точные новые сущности, P0–P4 приоритеты и branch-level additive acceptance.
Changelog r358: self-review устранил устаревший count 88 в acceptance: текущий каталог содержит 99 атомарных REQ, а v2.5 baseline 88 сохранён как исторический.
Changelog r359: self-review сверил acceptance таблицы v2.6 addendum; self-service дополнен end-to-end критерием, проверкой budget/credit на создании и исключением только финального manager approve.
Changelog r360: self-review добавил mapping v2.6 extension→v2.5 baseline, чтобы повторно не создавать campaign, PoP, self-service, finance или experiment модели.
Changelog r361: self-review сопоставил каждый нормативный пункт v2.6 addendum с отдельным REQ-V26; пропуски в acceptance вынесены в обязательную acceptance matrix.
Changelog r362: self-review уточнил evidence для pilot, round-trip integrations, dynamic SLA и mobile photo proof; критерии не считаются закрытыми по наличию UI/ADR без соответствующего прогона.
Changelog r363: self-review извлёк v2.6 Next Branch DOCX в канонический `.extracted.md` (129 paragraphs, 3 tables) и добавил его в Source Of Truth read order.
Changelog r364: self-review привязал draft metadata к SHA extracted addendum; extraction и semantic classification разделены как разные evidence gates.
Changelog r365: self-review добавил отдельные AC для структурной сверки DOCX→extracted и канонического read order; extraction не считается semantic coverage автоматически.
Changelog r366: self-review классифицировал нормативные строки extracted v2.6 addendum по REQ-V26/DEC/PROCESS; карта line-level coverage добавлена в приложение.
Changelog r367: self-review добавил explicit disposition для ненормативных строк addendum и контроль orphan-line при изменении source SHA.
Changelog r368: self-review сопоставил REQ-V26 с текущими `roadmap.yaml`, registry и decisions; найден частичный mapping только для attribution/self-service, остальные extension IDs отмечены unmapped.
Changelog r369: self-review добавил двустороннюю V26 coverage snapshot с запретом `APPROVED` при отсутствии roadmap task или owner-approved disposition.
Changelog r370: self-review добавил AC-309 для обнаруженных UNMAPPED extension-доменов; roadmap gap отделён от доказательств внешнего monitoring-dashboard.
Changelog r371: self-review сверил V26 requirements с data inventory; добавлены отсутствовавшие attribution, self-service, competitive, audience, financial, dynamic/mobile и external-measurement сущности.
Changelog r372: self-review добавил V26 entities в data inventory и acceptance-контроль отсутствия сущности без owner/schema/migration/evidence.
Changelog r373: self-review проверил V26 data inventory на field-level completeness; добавлен минимальный schema contract для каждой новой сущности.
Changelog r374: self-review проверил V26 API surface; добавлены proposed endpoint/event contracts и запрет считать их реализованными без OpenAPI/evidence.
Changelog r375: self-review добавил field-level contract для каждой V26-сущности, включая scope, privacy и immutable audit поля.
Changelog r376: self-review добавил proposed V26 endpoint surface с явным разделением logical capability и implemented runtime.
Changelog r377: self-review сверил additive exceptions в v2.6 addendum; обнаружено противоречие §0.3 (два исключения, §4/§6) и §8.3 (одно исключение, §3.1).
Changelog r378: self-review добавил owner decision для разрешения границы изменений существующего Campaign/Delivery/PoP, запретив молчаливое расширение.
Changelog r379: self-review зафиксировал конфликт additive-exceptions в самом v2.6 addendum как DEC-022; до решения владельца расширение не может менять существующие домены.
Changelog r380: self-review подготовил кандидатный task-breakdown для всех V26-доменов; proposed IDs отделены от canonical roadmap.
Changelog r381: self-review добавил owner/dependency/evidence поля к каждому proposed V26 task, чтобы перенос в roadmap был механически проверяемым.
Changelog r382: self-review добавил правило, что proposed V26 tasks не становятся canonical roadmap без owner approval, срока и проверки дублей.
Changelog r383: self-review проверил V26 story coverage; для planned stories добавлены отдельные journey-контракты с happy-path и negative outcomes.
Changelog r384: self-review отделил design-only V26 domains от UI journeys, чтобы не создавать ложное требование реализованного интерфейса.
Changelog r385: self-review добавил V26 planned journey contracts с отдельным PENDING статусом и требованием разрешить alias в canonical dot-case registry до реализации.
Changelog r386: self-review проверил область lexical lint; исторические AC/changelog и source quotations отделены от active normative prose.
Changelog r387: self-review уточнил precedence addendum: при конфликте v2.5 остаётся базовым контрактом до отдельного owner-approved decision/ADR.
Changelog r388: self-review пересчитал user-story definitions после добавления V26; baseline 32 расширен до 39 (32 core + 7 V26), старые counts помечены snapshot.
Changelog r389: self-review обновил AC-19/235/238/286, исключив stale утверждение, что текущий story count равен 32.
Changelog r390: self-review добавил AC-317 для machine-checked story count; core snapshot 32 и текущая редакция 39 явно разделены.
Changelog r391: self-review обнаружил, что исходный `HEAD` содержит upstream draft revision `r40`, не связанную явно с self-review sequence; введено правило continuity metadata.
Changelog r392: self-review зафиксировал parent snapshot (`HEAD`/revision r40) и запретил принимать revision без parent commit/blob identity и monotonic changelog.
Changelog r393: self-review проверил provenance extraction v2.6; в metadata добавлены инструмент, вход/выход и структурные counts.
Changelog r394: self-review добавил regeneration check, требующий byte-stable extraction или объяснимый форматный diff при изменении версии python-docx.

Changelog r395: self-review синхронизировал revision metadata с фактической последней записью changelog; содержательная модель и требования не изменялись.

Changelog r396: self-review обнаружил отсутствие commit/blob SHA или sidecar digest самой рабочей редакции; добавлен отдельный blocker AC-320, чтобы approval нельзя было привязать только к изменяемому пути файла.

Changelog r397: механический scan v2.6 extracted-текста нашёл 34 строки с нормативными маркерами; 21 покрыта AM, остальные 13 классифицированы как заголовки/пояснения/строка таблицы приоритетов, а не отдельные обязанности.

Changelog r398: self-review исправил устаревшую ссылку на revision в AC-320; содержательная модель не изменялась.

Changelog r399: self-review синхронизировал диапазон active changelog с текущей revision metadata.

Changelog r400: сверка live Git выявила stale `docs/product/roadmap.yaml:base.git_sha` (`2b935bb…`) против `HEAD/origin/develop` (`b21174f…`); добавлен блокер AC-321.

Changelog r401: сверка текущего `roadmap.yaml` выявила stale-счётчик `73 task/stage/decision IDs` в историческом AC-244; текущая структура даёт 68 элементов (43 tasks + 6 stages + 16 decisions + 3 gates), добавлен AC-322.

Changelog r402: добавлен воспроизводимый canonical snapshot наборов Git/registry/roadmap и их статусов; snapshot не заменяет owner-approved traceability manifest.

Changelog r403: к canonical snapshot добавлены SHA roadmap/registry; одинаковые counts теперь не могут скрыть содержательное изменение без смены digest.

Changelog r404: отсутствие SHA snapshot оформлено AC-323; после добавления digest blocker закрывается только при повторной проверке bytes/SHA.

Changelog r405: self-review синхронизировал редакцию, указанную в AC-320, с текущей revision metadata.

Changelog r406: structural scan выявил непоследовательный порядок appendix IDs; добавлен AC-324 с требованием canonical appendix index или монотонного порядка.

Changelog r407: self-review синхронизировал revision в AC-320 после исправления порядка приложений; содержательная модель не изменялась.

Changelog r408: handoff-пакет расширен обязательным canonical appendix index; физический порядок приложений не меняется до проверки всех ссылок.

Changelog r409: создан `docs/audit/appendix-index.md` с mapping всех 40 приложений на заголовки и anchors; AC-324 получил фактический артефакт закрытия.

Changelog r410: опубликован sidecar SHA-256 самой редакции драфта; AC-320 получил проверяемую привязку к байтам без ожидания commit.

Changelog r411: self-review обнаружил, что AC-реестр не содержит machine-readable status; добавлен AC-325 для различения open/fixed/verified/blocked.

Changelog r412: обратная сверка canonical journeys обнаружила два пропущенных функциональных требования — PDF upload договора рекламодателя и описания permissions; добавлены REQ-BIZ-017, REQ-UX-005, stories/journeys и acceptance.

Changelog r413: добавлены отдельные stories/journeys для `advertiser.contract_pdf_upload` и `permissions.description`; актуальный story count увеличен с 39 до 41.

### Historical changelog (r284 и ранее)

Changelog r284: self-review выполнил двустороннюю сверку journey IDs; 28 целевых dot-case ID драфта отсутствуют в canonical `user-journeys.md`, а canonical содержит дополнительные IDs, не отражённые в story map (например `campaign.edit`, `device.onboard`, `backup.restore`, `commerce.*`). Требуется reconciled disposition в обе стороны. Changelog r283: self-review протянул `REQ-CHAN-003` в детальную карту §23.2–§23.3, чтобы новый control plane не оставался только в верхнеуровневой section map. Changelog r282: self-review обнаружил, что новый `REQ-CHAN-003` не имел явной API-поверхности; добавлены canonical carrier/device/surface management endpoints и bulk-operation contract. Changelog r281: self-review добавил отдельный контракт управления всеми физическими и логическими носителями: bulk-операции, независимый результат по carrier/surface и запрет побочных изменений; ранее мультиканальность описывала публикацию, но не полный operational control plane. Changelog r280: self-review разделил count user stories и journey IDs: 28 — это множество
US/design/alias IDs, а canonical project journeys считаются отдельно. Changelog r279: self-review исправил устаревший count user stories в AC-19 (27 → 28)
и закрепил сверку counts с фактическими уникальными ID. Changelog r278: self-review сверил требования DEV manifest с существующим
`docs/product/environment-inventory.yaml`; inventory признан фактическим источником для
baseline `.81`, а отдельный manifest требуется только для недостающих полей. Changelog r277: self-review устранил дублирование строк `DEC-017…021` в дополнении I и
проверил уникальность каждого DEC-ID внутри каждого реестра. Changelog r276: self-review синхронизировал основной decision register §29 с дополнением I:
`DEC-017…021` теперь присутствуют в обоих реестрах. Changelog r275: self-review добавил индивидуальную карту решений для каждого scope-exclusion
первой очереди (ЭДО/биллинг, DSP/SSP, персонализация, звук, произвольный HTML/JS).
Changelog r274: self-review сделал `DECISION_REQUIRED` формальным disposition: каждое
исключение обязано иметь `DEC-ID`, owner, reason, trigger и review date в decision register.
Changelog r273: self-review синхронизировал историческую формулировку AC-222 с исправленным
advertiser happy-path (7 шагов вместо устаревших 8). Changelog r272: self-review добавил AC-229 для обязательной проверки DEV environment manifest
и синхронизировал его с новым шаблоном без секретов. Changelog r271: self-review добавил машиночитаемый шаблон DEV environment manifest без секретов.
Changelog r270: self-review синхронизировал основной decision register и дополнение I:
`DEC-013…016` теперь имеют одинаковое покрытие и disposition в обеих таблицах. Changelog r269: self-review добавил отдельные decision slots для альтернатив deployment topology
и device PKI/mTLS activation; до owner выбора варианты не считаются согласованной архитектурой.
Changelog r268: self-review обнаружил нормативные предложения вне REQ-каталога без inline
маркера; до классификации они не считаются покрытыми. Требуется reverse-traceability report
для текущего драфта, а не только для исходника. Changelog r267: self-review уточнил гранулярность шага advertiser: `geography/time filter`
является одним видимым действием, поэтому label исправлен с 8 до 7. Changelog r266: self-review пересчитал многострочные базовые journeys; исправлены labels
`J-PORTAL-APPROVAL` и `J-PORTAL-OPS` (7 → 8 шагов). Changelog r265: self-review проверил все `Happy-path: N` labels по числу стрелок-действий;
исправлен `J-REL-001` (7 → 6 шагов). Changelog r264: self-review пересчитал шаги базовых journeys после добавления labels:
campaign=12, approval=7, operations=7, advertiser=8, emergency=9. Число шагов теперь
соответствует фактической последовательности действий.
Changelog r263: self-review добавил явную строку `Happy-path: N шагов` во все пять базовых
portal journeys; путь без маркировки числа шагов не считается соответствующим UX-контракту.
Changelog r262: self-review выявил, что summary-таблица дополнительных user stories не
содержала обязательных permission/scope/journey/positive-negative/acceptance полей; до
заполнения canonical story records она не считается покрытием. User refresh-token policy
 (8 h, ADR-006) и device
refresh-token policy (24 h, ADR-003), чтобы разные audience/rotation/revoke контуры не смешались.
Changelog r260: self-review синхронизировал revision metadata с последними структурными
исправлениями и отделил исторические записи от active summary. Полные блокеры полноты
остаются без изменений.
Changelog r259: self-review повторно проверил все acceptance-таблицы после исправления
enum-разделителей; устранён второй необработанный вертикальный разделитель в тексте AC.
Changelog r258: self-review исправил вертикальные разделители в acceptance-таблице:
enum-значения теперь не разрушают Markdown-колонки; добавлена структурная проверка числа
колонок для всех таблиц. Предыдущие блокеры полноты остаются без изменений.
Changelog r257: self-review отделил статус документа от статусов требований и задач:
`ACCEPTED` теперь означает owner acceptance содержания, а `APPROVED` — закрытие всех
артефактов и evidence; добавлены явные переходные критерии. Незакрытые артефакты полноты
остаются блокерами.
Changelog r256: self-review синхронизировал YAML-шаблон с журналом переходов статусов:
добавлены обязательные `status_changed_at` и `status_actor`, а также правило сохранения
commit/evidence для каждого перехода. Незакрытые артефакты полноты остаются явными блокерами.
Changelog r255: self-review выявил, что 80 REQ пока представлены сводной таблицей, а
атомарные поля (`owner`, статусы, acceptance, evidence, task) заполнены только в шаблоне;
до заполнения построчного реестра это не считается покрытием. Ранее синхронизирован enum
`requirement_status` с жизненным циклом:
добавлены `rejected` и `superseded` с обязательными причиной/заменяющим REQ-ID. Устранены
slash-сокращения REQ-ID в reference tables и добавлено проверяемое правило полного разрешения ссылок.
проверяемое правило полного разрешения ссылок. Незакрытые артефакты полноты (классификатор
исходника, владельцы/даты, journeys, REQ→roadmap→evidence) остаются явными блокерами.
Changelog r252: self-review добавил машинные инварианты совместимости статусов, историю
переходов и negative tests для несовместимых пар. Незакрытые артефакты полноты (классификатор
исходника, владельцы/даты, journeys, REQ→roadmap→evidence) остаются явными блокерами.
Changelog r251: self-review синхронизировал structural checklist с разделением
`requirement_status` и `delivery_status`; проверка теперь требует оба поля и переходные
инварианты. Незакрытые артефакты полноты (классификатор исходника, владельцы/даты, journeys,
REQ→roadmap→evidence) остаются явными блокерами. Граница implementation/review:
Claude Code — единственный implementation agent, Codex — architect/reviewer, Hermes — historical/retired.
Runtime/product зависимость от LLM запрещена. Этот блок — краткое резюме, не evidence.
Changelog history (r250–r258) is retained in the external changelog artifact.
Changelog r250: self-review разделил зрелость требования и ход реализации на независимые
`requirement_status` и `delivery_status`; это исключает ложное «готово» для неодобренного REQ.
Остаются блокеры полноты (нормализованный классификатор
исходных обязанностей, владельцы/даты, canonical journeys и построчная связь с roadmap); они
вынесены в явные блокеры, а не считаются покрытыми по наличию prose. Граница implementation/review:
Claude Code — единственный
implementation agent, Codex — architect/reviewer, Hermes — historical/retired; runtime/product
зависимость от LLM запрещена. Также синхронизированы process/test-инварианты и предел self-review
с фактическим AC-209. Этот блок — краткое резюме, не evidence.
-->

### Статус самого документа

Статус документа не заменяет статусы требований и задач: `DRAFT` означает рабочий текст,
`REVIEW` — завершённую самопроверку и передачу на ревью, `ACCEPTED` — явное принятие
содержания владельцем, `APPROVED` — принятие содержания и проверенных приложений/evidence,
`SUPERSEDED` — наличие утверждённой заменяющей редакции. Переход `REVIEW → ACCEPTED`
требует owner decision с датой и SHA; `ACCEPTED → APPROVED` требует закрытия всех
блокирующих AC и публикации обязательных артефактов из §34/AG; понижение статуса требует
changelog и причины. Внешний monitoring-dashboard и статус roadmap не выполняют эти переходы.

## 1. Цель редакции

Сохранить работающий проект и KSO-first пилот, но формализовать полную мультиканальную
платформу без переписывания ядра. Каждое требование получает уникальный `REQ-ID`, тип
`MUST/SHOULD/MAY`, владельца, задачу, критерий приёмки и evidence.

## 2. Границы продукта

### 2.1. Обязательный продуктовый контур (`MUST`)

- Control Plane: пользователи, роли, рекламодатели, договорные основания, кампании,
  размещения, креативы, модерация, согласования, инвентарь и отчётность.
- Channel-neutral core: кампании, таргетинг, инвентарь, manifest, PoP, RBAC/RLS и аудит
  не зависят от производителя или типа носителя.
- Каналы первой архитектурной очереди: KSO, Android/Android TV/TV box, price checker,
  ESL и LED shelf banner.
- Device/Channel Gateway и channel-neutral data contracts; Channel Orchestrator,
  Adapter Layer и mock adapters реализуются только по trigger ADR-019.
- Порталы: `admin-web`, `advertiser-web` и permission-scoped Operations-раздел внутри
  `admin-web`; отдельное Operations-приложение требует нового решения. Внешний
  monitoring-dashboard не является частью продукта и не является источником истины.

Граница ADR-019: до второго реального канала сохраняются только channel-neutral manifest/
proof data contracts и тонкий KSO compatibility seam. Channel Orchestrator, выделенный
Adapter Layer и mock adapters не строятся заранее и включаются одной design/implementation
веткой при появлении второго реального канала. Нельзя считать отложенный компонент `done`
по наличию схемы или интерфейса.

### 2.2. Явно вне первой очереди (`DECISION_REQUIRED`)

Полный ЭДО/биллинг, DSP/SSP-закупка, персонализация покупателя, звук и произвольный
HTML/JS. Для каждого исключения обязательна запись `DEC-ID` в decision register с
владельцем, причиной, датой пересмотра и условием возврата в scope; без неё исключение
не считается согласованным и блокирует `APPROVED`.

| Исключение | DEC-ID | Обязательная запись до `APPROVED` |
|---|---|---|
| Полный ЭДО/биллинг | `DEC-017` | финансовый/legal owner, границы сущностей, trigger возврата |
| DSP/SSP-закупка | `DEC-018` | product/legal owner, ручное согласование и условия пересмотра |
| Персонализация покупателя | `DEC-019` | privacy/legal owner, lawful purpose и trigger пересмотра |
| Звук в торговом зале | `DEC-020` | business/operations owner, safety-ограничения и review date |
| Произвольный HTML/JS | `DEC-021` | security owner, sandbox/CSP policy и activation gate |

### 2.3. Аддитивная ветка v2.6 Next Branch

Файл `TZ_Retail_Media_Platform_v2_6_Next_Branch_2026-07-11.docx` не отменяет требований
v2.5 и не разрешает переписывать Campaign/Delivery/PoP. Его обязательства добавляются
отдельными REQ-V26-ID с приоритетом, owner, roadmap task и disposition. При конфликте
с v2.5 базовым является v2.5; изменение этого precedence возможно только через
owner-approved ADR/решение с affected REQ и датой. Отсутствие решения не превращает
пункт в «реализовано».

| REQ-ID | Область ветки | Минимальный результат |
|---|---|---|
| REQ-V26-001 | Tenant model conformance | ADR-018 уже принял multi-retailer/syndication-ready модель: `retailer_id` — верхняя tenant boundary, advertiser — второй уровень; новые tenant-сущности обязаны соответствовать двухуровневым RLS/FK и не требуют нового tenant ADR без изменения модели |
| REQ-V26-002 | Attribution & sales lift | сущности `SalesReferenceRecord`, `CampaignAttributionWindow`, `StoreControlGroupAssignment`, `CampaignLiftReport`; агрегированные store/SKU/day данные, baseline, test/control stores, lift и confidence/значимость, versioned methodology без заднего пересчёта |
| REQ-V26-003 | Advertiser self-service | отдельный advertiser web-контур и сущности `AdvertiserSelfServiceSettings`/`AdvertiserBudgetLimit`: inventory/forecast, draft campaign, creative upload, автоматическая conflict-проверка и budget/credit/volume guardrails уже при создании, submit на общий moderation/approval; путь от draft до publication не требует действий внутреннего менеджера кроме финального approve и использует тот же RBAC/RLS |
| REQ-V26-004 | Competitive separation | `competitive_category`, configurable separation interval/exceptions, блокировка либо явный override с причиной и audit до playlist/manifest |
| REQ-V26-005 | Audience store targeting | анонимные store attributes (price segment, average check, traffic profile) как дополнительное измерение placement; master-data adapter в текущем коде отсутствует и является обязательной prerequisite-задачей |
| REQ-V26-006 | Financial integration | versioned/idempotent export advertiser/contract/order/period/volume/tariff/execution и обратный payment status без подмены финансового факта |
| REQ-V26-007 | Programmatic extension | ADR и SSP-facing availability data contract как extension point; DSP/SSP закупка не реализуется без отдельного решения |
| REQ-V26-008 | Dynamic creative | MVP на одном канале: master-confirmed price/promo substitution, dynamic marker в manifest, отделение от static content hash |
| REQ-V26-009 | Field mobile operations | mobile web/app для store employee: scoped device list/status, photo proof и incident; без content/publish/admin функций |
| REQ-V26-010 | A/B winner metric | после attribution поддержать delivery- и lift-метрики, minimum sample и ручное owner approval winner; история immutable |
| REQ-V26-011 | External audience measurement | ADR на экспорт PoP/manifest в формат стороннего измерителя; integration/provider остаётся designed-not-implemented до owner decision |

Приоритет ветки сохраняется из исходного документа: `V26-001` — P0; `V26-002/003` —
P1; `V26-004/005/006` — P2; `V26-007/008/009/010` — P3; `V26-011` — P4.
Критерий ветки в целом: P0 закрыт ADR до новых доменов; P1 принят по своим acceptance;
P3/P4 явно помечены `planned` или `designed-not-implemented`, а не исчезают из roadmap.
Новые сущности аддитивны; изменение существующих Campaign/Delivery/PoP допускается только
как явно отмеченное owner-approved исключение с миграцией и rollback.

Расширение не создаёт параллельных доменных моделей. До реализации составляется mapping:

| REQ-V26 | Базовый REQ v2.5 | Правило расширения |
|---|---|---|
| V26-002 | REQ-BIZ-013, REQ-BIZ-012, REQ-INT-001 | добавить attribution facts/methodology и store control groups; не дублировать PoP или customer-level data |
| V26-003 | REQ-BIZ-015, REQ-SEC-002, REQ-UX-001 | расширить capability advertiser self-service поверх общего campaign/approval/RLS workflow |
| V26-006 | REQ-BIZ-009, REQ-BIZ-014, REQ-API-003 | добавить внешний exchange contract, не превращая order/payment projection в billing system |
| V26-010 | REQ-BIZ-012, REQ-BIZ-013 | выбрать winner metric в существующей versioned experiment model, не переписывать исторические отчёты |
| V26-008 | REQ-MAN-001, REQ-CONT-001, REQ-CHAN-002 | добавить dynamic payload marker и master-price binding без изменения static content hash semantics |

Acceptance matrix ветки (обязательная evidence, не только prose):

| REQ-V26 | Минимальная приёмка |
|---|---|
| V26-001 | ADR-018 принят; schema/behavioral evidence подтверждает `retailer_id` и двухуровневую RLS каждой новой tenant-сущности |
| V26-002 | На пилотной кампании есть baseline/fact/lift минимум для одного test/control набора магазинов с versioned methodology |
| V26-003 | Self-service advertiser проходит draft → creative → submit → final approve → publication; превышение budget/credit и inventory conflict блокируются или эскалируются |
| V26-004 | Конкурирующее размещение в запрещённом окне блокируется; audited override требует причину и явное подтверждение |
| V26-005 | После реализации и проверки master-data adapter менеджер или self-service выбирает магазины по каждому store-audience атрибуту; до этого путь имеет статус `blocked`, а не implemented |
| V26-006 | Тестовый round-trip export → simulated external payment response → обновлённый portal status идемпотентен и трассируем |
| V26-007 | ADR фиксирует SSP-facing extension и статус designed-not-implemented; автоматическая DSP/SSP закупка отсутствует |
| V26-008 | На выбранном канале изменение master price отражается в следующем согласованном manifest SLA; dynamic/static marker и hash проверяемы |
| V26-009 | Store employee с телефона видит только свой scope, подтверждает экран photo proof и создаёт incident без admin/publish прав |
| V26-010 | A/B с достаточной выборкой выбирает delivery или lift winner по owner-approved rule и сохраняет immutable result |
| V26-011 | ADR и versioned export contract существуют, provider integration явно остаётся designed-not-implemented |

Минимальная story-map этой ветки (каждая запись требует canonical journey, smoke или
явного `designed-not-implemented` disposition; простое наличие строки не означает
готовность):

| Story ID | Роль | Связанные REQ | Статус до owner decision |
|---|---|---|---|
| US-V26-001 | аналитик/рекламодатель | REQ-V26-002,010 | planned |
| US-V26-002 | рекламодатель | REQ-V26-003 | planned |
| US-V26-003 | менеджер кампаний | REQ-V26-004,005 | planned |
| US-V26-004 | финансовый оператор | REQ-V26-006 | planned |
| US-V26-005 | архитектор платформы | REQ-V26-001,007,011 | tenant decision accepted; extension contracts designed-not-implemented |
| US-V26-006 | оператор магазина | REQ-V26-009 | planned |
| US-V26-007 | оператор контента | REQ-V26-008 | planned |

Design journeys для planned V26 stories (до добавления в canonical `user-journeys.md`
имеют статус `PENDING`, а не UI-ready):

| Journey ID | Story | Happy-path | Ожидаемый результат / negative path |
|---|---|---|---|
| `J-V26-ATTR-001` | US-V26-001 | `Happy-path: 6 шагов` — Login → Attribution → выбрать campaign/window → проверить test/control stores → открыть baseline/fact/lift → скачать versioned report | агрегаты store/SKU/day и confidence видимы; нет customer-level данных, missing control group даёт явное предупреждение |
| `J-V26-SELF-001` | US-V26-002 | `Happy-path: 8 шагов` — Login → Self-service → inventory/forecast → создать draft → загрузить creative → проверить budget/conflicts → submit → увидеть pending approval | лимит/конфликт блокирует или эскалирует; до final approve публикация невозможна |
| `J-V26-COMP-001` | US-V26-003 | `Happy-path: 5 шагов` — Login → campaign/playlist → выбрать categories → запустить simulation → подтвердить безопасный schedule | conflict block или audited override; соседние поверхности не изменяются |
| `J-V26-AUD-001` | US-V26-003 | `Happy-path: 6 шагов` — Login → placement → filters → выбрать store attribute → preview targets → save draft | отображаются только scoped stores; отсутствующий master attribute объяснимо исключается |
| `J-V26-FIN-001` | US-V26-004 | `Happy-path: 6 шагов` — Login → Finance exchange → выбрать period → preview export → отправить idempotent batch → открыть external payment status | повтор не дублирует batch; invalid callback отклоняется и аудируется |
| `J-V26-MOB-001` | US-V26-006 | `Happy-path: 5 шагов` — Login mobile → выбрать свой store → открыть device → подтвердить экран фото → создать incident | cross-store доступ запрещён; фото/incident имеют hash, actor и timestamp |
| `J-V26-DYN-001` | US-V26-007 | `Happy-path: 5 шагов` — Login → Content template → выбрать approved master field → preview dynamic marker → создать manifest version | цена берётся только из master; stale/missing value блокирует публикацию |

`US-V26-005` для programmatic extension и external measurement design-only
не получают UI journey до owner ADR; их acceptance — архитектурный artifact, а не клики.
Идентификаторы `J-V26-*` — design aliases; перед реализацией они обязаны получить
canonical dot-case IDs, например `attribution.lift_report`, `self.campaign_create_v26`,
`campaign.competitive_separation`, `placement.audience_targeting`, `finance.exchange`,
`field_ops.device_confirm`, `content.dynamic_binding`, с mapping в registry и roadmap.

## 3. Целевая каноническая модель (`required`, не текущий факт)

`Network → Branch → Cluster → Store/Store Group → Channel → Device Type → Physical Device →
Logical Carrier → Display Surface → Capability Profile`.

Эта цепочка задаёт требуемую модель v2.6. В текущем коде отсутствует часть названных
сущностей и связей, включая отдельные `Network`, `StoreGroup` и полный playlist/carrier
контур; фактическая ERD должна генерироваться из моделей/миграций и сопоставляться с этой
целью. До такого сопоставления раздел имеет статус `required/partially_implemented`.

Кампания таргетируется на набор поверхностей/каналов/зон/SKU, а не только на магазин.
Все изменения campaign, placement, creative, playlist, manifest, adapter и rollout
версионируются; история неизменяема.

## 4. Роли и user stories

Для каждой истории обязательны actor, permission code, scope, preconditions, entry,
`Happy-path: N шагов`, видимые действия, результат, negative path и audit event.

Текущий факт: seed/runtime содержит пять технических ролей — `system_admin`,
`security_admin`, `operator`, `analyst`, `advertiser`. Имена `campaign_manager`,
`moderator`, `approver`, `ops_operator` в feature-registry пока не разрешаются в seed и
являются каноническим разрывом реализации. Product decision Q2 в
`docs/product/user-journeys.md` уже закрепил внутренние role codes `system_admin`,
`security_admin`, `campaign_manager`, `moderator`, `approver`, `ops_operator` и внешний
`advertiser`; `public_lead` — unauthenticated persona, а `analyst` сохраняется отдельным
read-only контуром из ТЗ. Авторизация остаётся только по backend permission codes/scope,
но отсутствующие role bundles должны быть реализованы; сведение персон к пяти текущим
ролям без миграционного решения запрещено. Открыт только способ безопасной миграции
`operator → ops_operator` и совместимости назначений, а не состав бизнес-персон.

| ID | Роль | User story | Результат |
|---|---|---|---|
| US-CAM-001 | Рекламный менеджер | Создать кампанию, выбрать заказ, период, каналы, поверхности, креативы и лимиты | Система показывает прогноз, конфликты и доступный инвентарь |
| US-CAM-002 | Рекламный менеджер | Отправить кампанию на модерацию и согласование | Публикация заблокирована до всех требуемых решений |
| US-MOD-001 | Модератор | Проверить rendition и вернуть креатив с причиной | Версия и решение записаны в аудит |
| US-APR-001 | Согласующий | Увидеть последствия и утвердить/отклонить размещение | Решение применено только в разрешённом scope |
| US-OPS-001 | Оператор | Найти проблемный канал/магазин/устройство и выполнить диагностику | Статус, команды, rollout и ошибки видны без доступа к БД |
| US-OPS-002 | Оператор | Запустить staged rollout и откатить версию при превышении порога | Rollout остановлен/откачен, причина и метрики сохранены |
| US-SEC-001 | ИБ | Просмотреть критичные действия, изменения прав, секретные и emergency-события | Полный неизменяемый audit trail и экспорт в SIEM |
| US-ADV-001 | Рекламодатель | Просмотреть свои кампании, план/факт, недопоказы и выгрузить отчёт | Текущий факт: `self.campaign_view` доступен, а `self.report_view` blocked; CSV существует только в admin campaign API. Advertiser CSV/PDF/XLSX остаются требованиями до отдельного UI/API evidence |
| US-ANL-001 | Аналитик | Сравнить план/факт, недопоказы, причины и качество размещения по кампании/каналу/магазину | Read-only аналитика с воспроизводимыми фильтрами и экспортом |
| US-EMR-001 | Уполномоченный оператор | Остановить рекламу на device/store/cluster/branch/network | Приоритетная команда, прогресс, подтверждение и emergency-аудит |
| US-ADM-001 | Системный администратор | Управлять пользователями, ролями, устройствами и настройками, просматривать monitoring/audit в назначенном scope | Каждая операция разрешена отдельным backend permission-кодом; service-функция `observability` не считается готовым UI управления, approved campaigns недоступны без отдельного права |

## 5. Сквозные journeys

### J-CAM-001: от заявки до отчёта

`brief → order/contract basis → campaign draft → inventory simulation → creative upload →
QA/moderation → approval → placement reservation → publish request → Orchestrator →
adapter delivery → manifest apply → PoP → plan/fact report → close`.

В KSO-first pilot отдельного Orchestrator/mock нет: publish идёт через существующий KSO
flow и тонкий compatibility seam. После появления второго реального канала шаг
Orchestrator/adapter вводится по ADR-019 без изменения business journey.

`Happy-path: 15 шагов` — каждый переход имеет permission, idempotency key, audit event,
error state и owner.

### J-CHAN-001: мультиканальная публикация

Пользователь выбирает каналы и surfaces; система проверяет capability/rendition,
строит channel-neutral manifest и `adapter_payload`, создаёт задания адаптерам,
получает delivery/apply/proof/error, показывает результат отдельно по каждому каналу.

`Happy-path: 8 шагов` — выбрать несколько каналов и surfaces → проверить готовность
rendition/capability → увидеть прогноз и конфликты → подтвердить публикацию → наблюдать
progress по каждому carrier/surface → проверить delivery/apply/proof/error → повторить
только неуспешные задания → открыть итоговый plan/fact. Частичный сбой одного канала не
останавливает независимые каналы и явно объясняется оператору.

### J-DEVICE-001: offline/fallback/recovery

Device heartbeat → последний валидный manifest → offline TTL → filler/fallback → накопление
PoP → восстановление связи → batch replay → сверка и отчёт о риске.

`Happy-path: 7 шагов`.

### J-EMR-001: emergency

Запрос причины и scope → MFA/permission check → приоритетная доставка → progress по
online-объектам → подтверждение/ошибки → возврат к штатному manifest.

`Happy-path: 6 шагов`.

## 6. State machines

В каждой строке ниже `текущий код` описывает проверенный baseline, а `требуется` —
нормативную цель. Расхождение не закрывается переписыванием требования под код.

- Campaign runtime. Текущий код: `draft → pending_approval → approved → active → paused`
  и `active → completed`; из `paused` переходов нет; archive для `draft/rejected` обходит
  общий transition guard. Требуется по принятому ADR-015: `draft → pending_approval →
  approved → scheduled → active → completed`; `pending_approval → draft/rejected`,
  `approved → draft/rejected`, `scheduled → paused`, `active → paused`, `paused →
  scheduled/active/completed/draft/archived`, `rejected → draft`, а archive разрешён
  только указанным ADR переходам. Каждый переход проходит единый guard и audit; возврат
  в `draft` создаёт новую immutable content/version revision, не новый campaign identity.

Canonical mapping по ADR-015: `draft` = editable version; `pending_approval` = submitted/
review; `approved` = решения получены, расписание ещё не активировано; `scheduled` =
persisted состояние валидного будущего запуска; `active` = delivery window открыт;
`paused` = delivery явно остановлена; `completed` = окно завершено; `rejected` =
неизменяемое решение с возможностью создать следующую draft revision; `archived` =
terminal non-delivery state. Любое иное состояние требует ADR amendment и schema migration.
- Advertiser application. Текущий код: начальный статус `new`, invite — `pending`; полной
  машины ниже нет. Требуется: `draft → submitted → under_review → approved/rejected →
  suspended/closed`; повторная подача — новой версией с reason/audit; suspension закрывает
  commercial/self-service access, сохраняя scoped historical reports; invite:
  `created → sent → accepted/expired/revoked`.
- Commerce order. Текущий код: `draft → offered → booked → confirmed → closed`, отмена
  разрешена из `offered/booked/confirmed`, но не из `draft`. Требуется: точная семантика
  отмены утверждается владельцем; любая отмена несёт reason/actor/scope/time/audit,
  `booked` атомарно резервирует capacity, `closed` immutable, payment — отдельная projection.
- Commerce financial projection: до DEC-017 финансовый контур не считается включённым; если решение принято, `payment_status` использует только кодовые значения `not_required/unpaid/partial/paid/overdue`, отдельно от order lifecycle, а tariff status — `draft/active/archived` с immutable version/effective dates. `paid` требует внешнего подтверждения и reconciliation; ни один order status не является заменой payment fact.
- Creative/Rendition. Текущий код: asset status по умолчанию `ready`, moderation —
  `approved/rejected`. Требуется: `uploaded → scanning → qa_failed/approved → superseded →
  retained/deleted_after_retention` с явным mapping существующих полей.
- Playlist. Текущий код: самостоятельной Playlist entity/state machine нет. Требуется:
  `draft → validating → valid/invalid → approved → published → superseded/rolled_back`;
  published immutable, invalid/unapproved не генерирует manifest.
- Manifest target lifecycle: `draft → generated → signed → queued → delivered → applied/failed/expired → superseded/rolled_back`. `expired` — отдельный terminal outcome при истечении `valid_to`, не синоним `error`; в текущем коде persisted `ManifestStatus` ограничен `generated/delivered/applied/expired/error`; `signed`, `queued`, `superseded` и `rolled_back` не считать существующими enum-значениями до ADR/schema/migration, а приёмочные ACK (`received/verified/...`) хранить как отдельную delivery projection с mapping и audit.
- Device target lifecycle: enrollment `unregistered → pending → registered`, затем runtime health `online ↔ degraded/offline/error/maintenance`; `revoked` — terminal credential state. `pending/registered` не являются значениями текущего `DeviceStatus`; projection обязана явно отображать enrollment stage и health отдельно. До завершённого enrollment delivery/commands запрещены, а возврат из `revoked` допускается только через новый owner-approved enrollment.
- Rollout. Текущий код: самостоятельной Rollout entity/state machine нет. Требуется:
  `planned → lab → canary → staged → paused → completed/rolled_back`.
- Emergency. Текущий код: `emergency_overrides.active` — boolean с actor/timestamps.
  Требуется: `requested → authorized → dispatching → partially_applied/applied → resuming →
  closed`; deactivate/resume явные, per-target result, idempotency, permission и audit.
- PoP. Текущий код: batch HTTP `200`, каждый event получает
  `accepted/quarantined/rejected/duplicate`; duplicate не учитывается повторно. Требуется:
  сохранить partial batch и явно согласовать ADR-017: HTTP `200` для batch с per-event
  duplicate result/error semantics либо отдельный `409`-контракт, не допускающий потери
  результатов остальных событий.

Для каждого перехода обязательны инициатор, причина, timestamp UTC, локальная TZ,
permission, audit и rollback/compensation policy. [REQ-GOV-001]

## 7. Канальные контракты

Каждый adapter обязан иметь contract, payload schema, capability profile, rendition rules,
SLA, retry/DLQ, circuit breaker, health, mock, security model и acceptance test.
[REQ-CHAN-001, REQ-ORCH-002]

- KSO: Chromium/kiosk, 1440×1080, hide-on-touch, ETag/304, local cache, playback PoP.
- Android/TV: player/APK/WebView, orientation/zones, cache, heartbeat, playback PoP.
- Price checker: idle/safe zones, запрет блокировки проверки цены, price-master validation.
- ESL: template/SKU binding, price-field isolation, label-ack, vendor error mapping.
- LED: rendition conversion, brightness/FPS/colour limits, controller-ack и health.
- Mock: heartbeat, delivery/apply/error/PoP, vendor responses и нагрузочные профили.

ADR-012/013/017 являются обязательными ограничениями: async handlers не выполняют
blocking I/O; edge runtime проверяет подпись, `valid_from/valid_to`, SHA и kill-switch
до показа; при ошибке используется только last-known-good или явно заданный fallback;
без `fallback_rules` показывается blank/black, неизвестный контент не изобретается и
fallback не эмитит PoP без явного флага; PoP создаётся runtime после фактического показа
и принимается через versioned batch API.

## 8. Нефункциональные требования

Все значения имеют метод измерения, окно, owner и evidence:

- до 10 000 магазинов по России, в среднем 4 KSO на магазин (с вариацией по магазинам),
  40 000+ устройств и расширение на Android/TV/price-checker/ESL/LED; heartbeat/manifest
  30 секунд с jitter, 304 при неизменности;
- manifest ≤5 минут для 95% online, emergency ≤60 секунд для 95% online;
- PoP в отчётах ≤15 минут, автономность ≥7 дней по последнему valid manifest;
- максимальная задержка аналитического отчёта после PoP задаётся отдельно для каждого
  профиля (percentile, окно измерения и допустимый процент ошибок);
- Control Plane ≥99.5%, Device Gateway ≥99.9%, потеря PoP ≤0.1% от ожидаемого объёма,
  RTO ≤4 часа, RPO ≤15 минут;
- HA, backup/restore drill, offsite copy, partitioning/retention, queue lag/DLQ;
- нагрузочные профили для устройств, массовой публикации, аналитики и 100 админов;
- security: MFA, SSO/AD, RLS, mTLS, key rotation/revoke, SIEM, PII minimisation, VPN;
- accessibility, i18n strategy, progressive operations и понятные ошибки UI.

Порог потери PoP `≤0.1%` принят владельцем как продуктовый SLA в
`docs/product/user-journeys.md` §5.1, хотя не извлечён из v2.5. Профиль `до 100 admin`
остаётся `proposed`-параметром `DEC-009` до нагрузочного evidence. Принятый target также
не является production claim без утверждённого measurement window и результата теста.

## 9. Обязательные решения владельца

Уже утверждены: NATS JetStream baseline (ADR-002), профиль подписи manifest
(OD-002), KSO-first/Orchestrator trigger (ADR-019), tenant model (ADR-018) и managed-first
pilot (OD-005). До закрытия design gate остаются: список production-каналов и владельцы,
операционный queue profile, SLA methodology/компенсации, финансовая модель,
retention, 152-ФЗ, staged rollout/feature flags, A/B scope, master-системы цен и SKU,
юридический статус отчёта и политика advertiser API-keys (scope, rotation, revoke либо
явное исключение из первой очереди). Шкала `KSO → 10 → 100 → 500 → network` уже принята
в canonical product decision; `DEC-010` должен зафиксировать только измеримые exit criteria
между ступенями.

## 10. Acceptance и трассировка

Минимальный набор доказательств: schema/contract tests, behavioral tests с реальной БД,
UI-smoke реальными кликами, operator walkthrough на `.81`, CI run, нагрузочный отчёт,
rollback/restore drill и audit/SIEM evidence.

Матрица является обязательной:

`REQ-ID → TZ section → user story/journey → domain/API/table → roadmap task → owner →
status → acceptance → evidence → decision/dependency`.

Ни одна строка ТЗ не может остаться без записи в матрице. `deferred` допустим только с
одобренным решением, причиной, владельцем, триггером и датой пересмотра.

## 11. Совместимость с текущим проектом

Сохраняются существующие campaign/portal/RBAC потоки и KSO-first пилот. Расширение
выполняется additive migrations и channel-neutral data contracts; прямые `kso_*`-
зависимости не расширяются. По ADR-019 до второго реального канала не создаются
Orchestrator, Adapter Layer или mock adapters. После подтверждения второго канала сначала
утверждается extraction design, затем существующая KSO-вертикаль становится первым
adapter без поломки её контрактов, и только после этого подключается новый канал.

Фактический blocker текущего baseline: `RLS-CONTEXT-DEVICE-001` / `RM-TECH-210` —
self-onboarding устройства в production-path получает `403 INVALID_CODE`, потому что
runtime DB-сессия не устанавливает RLS-контекст для `device_onboarding_codes`. Пока задача
не закрыта behavioral evidence на PostgreSQL под runtime-role, `device.onboard`, mobile
field operations и device pilot считаются `blocked`, даже если route и тестовые фикстуры
существуют.

Текущие приложения: `admin-web` и `advertiser-web`; отдельного Operations-приложения нет.
Термин `Operations portal` в этом документе означает целевой permission-scoped раздел
`admin-web`, если владелец отдельно не утвердит третье приложение.

## 12. Бизнес-правила и расчёты

Статус раздела: `required`, не описание текущего кода. В частности, `campaign_type` и
целевая классификация inventory ещё не подтверждены generated schema/runtime evidence.

- Жизненный цикл размещения: `brief → proposal → reservation → creative → moderation →
  approval → publication → playback → report → close`.
- Период показа хранится в отдельной versioned flight/placement записи; `start_at/end_at`
  проверяются при simulation, manifest generation и runtime, а показ вне окна запрещён.
- Инвентарь определяется формулой: доступная ёмкость, проданное, зарезервированное,
  внутреннее, emergency/fallback и свободное; единицы измерения фиксируются явно.
- `impression`, `playback`, `delivery_ack`, `apply_ack`, `reach` и `compensation` — разные
  понятия и не смешиваются в отчётах.
- Overbooking, preemption, priority, frequency cap, sold-out, make-good и SLA имеют
  детерминированные правила и примеры расчёта.
- A/B-тест имеет контрольную/тестовую группу, период, метрику победителя, минимальный
  объём данных и ручное утверждение результата.
- Кампания имеет явный `campaign_type`: `commercial`, `internal`, `compensation`,
  `test` или `filler`; тип влияет на инвентарь, отчётность и правила компенсации.
- Базовый порядок приоритета версионируется: emergency → обязательная реклама сети →
  федеральная платная → филиальная → локальная → filler → test. Вытеснение показывает
  причину и не переписывает исторические отчёты.
- Кампания всегда связана с order/contract basis; тарифы, скидки, бонусы и компенсации
  версионируются и не меняют закрытый отчёт задним числом.

## 13. Целевые данные и интеграционные контракты

Для каждой сущности фиксируются поля, ключи, ограничения, владельцы данных, retention,
PII-класс, audit и миграция: hierarchy (включая store groups), advertiser/order, campaign/
placement, creative/rendition, inventory, channel/device/surface, device certificates/status/
commands/events, playlist/manifest, rollout, proof/telemetry, approval, emergency и reports.

Минимальный **целевой** inventory операционной модели данных (до актуальной ERD и
сопоставления с migrations ни одна строка не считается реализованной схемой):

| Группа | Обязательные таблицы/сущности |
|---|---|
| Hierarchy | `branches`, `clusters`, `stores`, `store_groups` |
| Devices | `devices`, `device_certificates`, `device_status`, `device_commands`, `device_events`, `device_heartbeats`, `device_errors` |
| Identity | `users`, `roles`, `permissions`, `user_roles`, `access_scopes` |
| Commercial | `advertisers`, `brands`, `contracts`, `orders`, `tariffs`, `price_lists`, `discounts`, `package_offers`, `campaigns`, `campaign_flights`, `campaign_placements`, `placement_targets`, `campaign_status_history` |
| Content | `media_assets`, `creative_versions`, `creative_moderation_tasks`, `content_renditions`, `rendition_moderation_tasks`, `rendition_requirements` |
| Inventory | `inventory_rules`, `inventory_reservations`, `inventory_snapshots`, `inventory_daily_snapshots` |
| Delivery | `playlists`, `playlist_items`, `playlist_versions`, `manifests`, `manifest_versions`, `outbox_events` |
| Proof/analytics | `pop_events`, `channel_events`, `campaign_daily_stats` |
| Governance | `approval_tasks`, `approval_decisions`, `emergency_events`, `emergency_targets`, `audit_events_operational`, `audit_events` (long-term) |
| Channels/vendors | `device_types`, `channel_types`, `device_capabilities`, `player_builds`, `channel_adapter_configs`, `esl_gateways`, `esl_labels`, `led_controllers`, `shelf_surfaces`, `vendor_integration_events` |
| v2.6 Extension | `sales_reference_records`, `campaign_attribution_windows`, `store_control_group_assignments`, `campaign_lift_reports`, `advertiser_self_service_settings`, `advertiser_budget_limits`, `competitive_separation_rules`, `store_audience_attributes`, `financial_exchange_batches`, `dynamic_content_bindings`, `field_device_confirmations`, `field_incidents`, `external_measurement_exports` |

Минимальный field-level contract новых сущностей (точные типы/индексы утверждаются в
ERD; отсутствие поля не может маскироваться JSON `metadata`):

| Сущность | Обязательные поля и инварианты |
|---|---|
| `sales_reference_records` | `retailer_id`, `store_id`, `sku_or_category`, `day`, агрегированные `units/value`, `source_ref`, `methodology_version`; без customer ID/чека |
| `campaign_attribution_windows` | `campaign_id`, pre/post window UTC, local TZ, methodology version, source snapshot, status |
| `store_control_group_assignments` | `campaign_id`, `store_id`, `group(test/control)`, assignment version, effective dates, immutable audit |
| `campaign_lift_reports` | campaign/window refs, baseline, fact, lift, confidence/ significance, method version, generated_at, source hashes |
| `advertiser_self_service_settings` | advertiser ref, enabled, budget/volume/credit limits, approval threshold, version/effective dates |
| `advertiser_budget_limits` | advertiser ref, limit type/value/unit/currency, source, effective interval, actor/audit |
| `competitive_separation_rules` | scope, category pair/set, minimum interval, exceptions, effective version, override policy |
| `store_audience_attributes` | store ref, anonymous attribute name/bucket, source adapter/version, observed_at, validity interval |
| `financial_exchange_batches` | period, payload hash, contract version, idempotency key, external ref, status, sent/ack timestamps |
| `dynamic_content_bindings` | template/rendition ref, master field/source version, dynamic marker, effective interval, static/dynamic hashes |
| `field_device_confirmations` | store/device/surface refs, operator ref, result, photo ref/hash, captured_at, audit |
| `field_incidents` | store/device ref, reporter, severity/category, description, attachment refs, status, timestamps |
| `external_measurement_exports` | provider/contract version, selection window, payload hash, status, export/ack refs, retention class |

Все новые сущности наследуют retailer/advertiser scope там, где применимо, и проходят
RLS, PII classification, retention, idempotency и migration/rollback review.

Обязательны versioned schemas для User API, Device API, Channel Adapter API, Worker API,
manifest и PoP; для каждого endpoint определяются auth/scope, idempotency, pagination,
error codes, retryability, rate limit, compatibility window и deprecation policy.

Интеграции описываются контрактами, а не названиями: AD/SSO/MFA, УКМ4/чеки, master цен и
SKU, BI/export, SIEM/Wazuh, vendor ESL/LED и очередь событий. Для каждой интеграции есть
owner, sandbox/mock, secret boundary, health-check, failure mode и reconciliation.

Все OLTP-записи, создающие domain events, записывают доменное изменение и `outbox_events`
одной транзакцией (telemetry без business state — единственное исключение). Relay
публикует событие во внешнюю очередь и отмечает его `published` только после broker
acknowledgement; retry безопасен и идемпотентен. Outbox payload проходит проверку на
отсутствие secrets, tokens и PII.

Канонический PoP использует flat `proof_event_v1` и принимает только device JWT:
`event_id` — dedupe key; `device_id` обязан совпадать с JWT subject и binding manifest;
неизвестный manifest
уходит в quarantine и не считается в отчётах; clock drift и устаревшие события отклоняются
по утверждённому окну. Текущий batch возвращает HTTP `200` и per-event
`status=duplicate`; ADR-017 формулирует `409` для individual duplicate event. До решения
владельца это открытое расхождение contract/ADR, а не утверждённая семантика. Невалидная
схема запроса возвращает `422`. Payload не
содержит storage paths, токены, секреты, raw signatures или контактные PII.

## 14. Portal UX и информационная архитектура

Для каждого раздела фиксируются route, role/scope, primary action, таблица с поиском,
фильтрами, сортировкой и сохранёнными представлениями, empty/loading/error/403/success
состояния, массовые операции, прогресс долгих операций, понятное восстановление после
ошибки, следующий шаг и audit. Обязательные экраны:

- campaign workspace: brief, inventory simulation, conflicts, renditions, approvals,
  publish/rollback и история версий;
- inventory/surface explorer: network→store→channel→device→surface, SLA и прогноз;
- operations center: health, manifest, PoP lag, rollout, errors, diagnostics;
- advertiser workspace: свои кампании, plan/fact, exclusions, export;
- security/audit: права, emergency, device operations, SIEM export.

Каждый journey должен иметь positive/negative path, operator walkthrough и UI-smoke.
[REQ-UX-001]
Внешний monitoring-dashboard отображается только как ссылка/наблюдение и не получает
права изменять продуктовые статусы.

## 15. Security, reliability и operations

- Threat model для пользователей, устройств, vendor API, media и очереди; секреты не
  попадают в код, URL, логи или клиентские payload.
- RLS test matrix по ролям/retailer/branch/store/surface; revoke/rotation и MFA для
  критичных действий.
- HA topology, health/readiness, circuit breaker, retry/DLQ, rate limits и degraded-mode
  определяются для каждого сервиса.
- Backup/restore: расписание, шифрование, offsite, retention, ответственный и drill;
  отдельно PostgreSQL, MinIO, Redis, queue и audit; ClickHouse backup/restore добавляется
  только после owner-approved activation по ADR-007.
- Observability: trace/correlation ID, dashboards для IT/business/ИБ и качества рекламной
  услуги, alert thresholds, incident runbook, SLO/error budget и связь с SLA кампании.
  Технический dashboard обязан показывать генерацию/доставку manifest, heartbeat и PoP/apply-ack;
  бизнесовый — plan/fact, fill, underdelivery, reach и compensation; dashboard ИБ — события
  доступа, MFA, изменения прав, emergency и подозрительные загрузки; dashboard качества —
  SLA кампании, активные устройства/носители/поверхности по каналам и просроченные отчёты.
  Backend, Device Gateway, PoP ingestion, Analytics, MinIO, PostgreSQL, Redis, очередь и
  player обязаны отдавать структурированные logs/metrics с единым correlation/trace ID;
  ClickHouse присоединяется к этой матрице только после activation по ADR-007.
  Operations health panel дополнительно показывает total/online/offline по устройствам,
  логическим носителям и поверхностям каждого канала, ошибки player/adapter/content/PoP/apply-ack,
  stale runtime/adapter, неприменённый manifest, свободное место и критичные магазины/каналы,
  с детализацией до branch/cluster/store/channel/device/surface. Он также формирует отдельный
  список магазинов, полностью выпавших из рекламной сети, и устройств, влияющих на выполнение
  активных кампаний; эти состояния передаются в прогноз выполнения и отчёт недопоказа.
- API и media boundary: CSRF/XSS/SQLi/SSRF проверяются negative-тестами, каждый object
  authorization выполняется в scope; MinIO buckets приватны, service accounts least
  privilege, presigned URL имеют короткий TTL и не попадают в логи.
- Rollout policy: lab→canary→staged→network, автоматическая остановка, rollback и
  подтверждение владельца; версия player/manifest/API поддерживается до миграции устройств.

## 16. Тестовая стратегия и стенд

Критерии разделяются на schema/contract, unit, behavioral с реальной БД, UI-smoke
реальными кликами, operator walkthrough, load, chaos/network partition, restore и
security-negative тесты. Для каждого REQ-ID указан минимальный набор доказательств.

Демо-стенд имеет безопасный seed без реальных данных и покрывает минимум из ТЗ: 10 филиалов,
50 кластеров, 500 магазинов и точный состав носителей из `REQ-STAND-002`, а также
кампании/конфликты/emergency и не менее 1 млн synthetic PoP/apply-ack событий. Стендовые
числа не выдаются за production.

Для каждого load profile заранее фиксируются целевые времена API и построения отчёта,
допустимый процент ошибок, бюджеты CPU/RAM/диска, queue lag и поведение при деградации;
результат сравнивается с этими пределами, а не только с фактом завершения теста.

## 17. Трассировка, миграция и управление изменениями

Каждый REQ-ID связывается с исходным разделом v2.5, новой формулировкой, user story,
journey, сущностями/API, roadmap task, owner, status, acceptance и evidence. Строки без
связи запрещены; дубли и противоречия отмечаются отдельно.

Изменения внедряются additive-first: новые таблицы/поля/версии и compatibility adapters;
существующие campaign, portal и KSO journeys не ломаются. Для breaking change обязательны
миграционный план, dual-read/write при несовместимости схем, backfill, rollback и срок удаления
старого контракта.

Каждое изменение ТЗ получает changelog: причина, затронутые REQ-ID, решение владельца,
обратная совместимость, затронутая roadmap и дата вступления в силу.

## Дополнение A. Инварианты доменных данных

- Campaign нельзя опубликовать без approved order/contract basis, creative rendition,
  placement scope, inventory reservation и required approvals.
- Manifest generation разрешена только при `status ≥ approved`, валидных contract и
  flight windows, минимум одном resolved `display_surface_id` и creative asset со
  статусами `ready/approved`; `campaign_flights` не выходят за срок договора.
- Placement не может превышать capacity/frequency cap или ссылаться на inactive/revoked
  surface; изменения live-объектов создают новую версию и diff.
- Manifest target принадлежит одному channel/device/surface scope; adapter payload не
  изменяет channel-neutral поля; для target не существует двух active manifest.
- PoP с неизвестным устройством, неверной подписью, несовместимым manifest или временем
  вне допустимого окна не становится коммерческим фактом, а сохраняется как rejected.
- Emergency имеет повышенный priority, но требует permission, reason, audit и возврата к
  известной версии; закрытые отчёты не меняются задним числом.

## Дополнение B. Матрица permission и scope

Разрешения задаются backend-кодами, не названиями ролей. Проверенный текущий минимум:
`campaigns.manage`, `campaigns.approve`, `creatives.moderate`, `inventory.read`,
`inventory.manage`, `devices.manage`, `emergency.manage`, `audit.read`. Отдельные права
публикации, device command, rollout rollback и audit export имеют статус `PENDING-ID` до
добавления в backend permission catalog; их нельзя подменять frontend-only именами.

Для каждой комбинации permission × роль фиксируются retailer/branch/cluster/store/surface
scope, positive и negative behavioral proof, audit event и делегирование. `system_admin`
не означает автоматический доступ ко всем арендаторам. Критичные операции требуют MFA,
двухфакторного подтверждения или owner gate согласно decision register.

## Дополнение C. Единый формат аудита и корреляции

Статус раздела: `required`, не текущая физическая schema. Текущий
`audit_events_operational` хранит более узкий набор (`actor_user_id`, `action`,
`target_type`, `target_id`, `correlation_id`, `ip_address`, `details_json`); переход к
целевому контракту требует additive schema/mapping и migration evidence.

```yaml
audit_id: "00000000-0000-0000-0000-000000000001"
occurred_at_utc: "2026-01-01T00:00:00Z"
actor_type: user
actor_id: "00000000-0000-0000-0000-000000000000"
permission_code: campaigns.manage
scope: "retailer/example"
action: create
target_type: campaign
target_id: "opaque-example-id"
before_version: null
after_version: null
reason: null
trace_id: "trace-example-0001"
result: success
evidence_ref: null
```

Критичные события append-only, имеют tamper-evidence/retention class и экспортируются в
SIEM. Нельзя писать access tokens, secrets, полные PII или vendor credentials. UI показывает
actor, scope, время, результат и следующий шаг.

В этом примере `actor_type` принимает `user|service|device|vendor`, `result` —
`success|denied|failed|partial`, а nullable-поля допускают `null`; это типовые ограничения
схемы, а не буквальные значения, которые можно сохранить без валидации.

## Дополнение D. Каталог ошибок и деградаций

Ошибки нормализуются по доменам: `AUTH`, `SCOPE`, `VALIDATION`, `INVENTORY`, `CONTENT`,
`MANIFEST`, `ADAPTER`, `DEVICE`, `POP`, `VENDOR`, `QUEUE`, `STORAGE`, `REPORT`, `EMERGENCY`.
Каждый код содержит HTTP/event mapping, user message, operator detail, retryability,
idempotency, alert severity, audit result и SLA/compensation impact.

Fail-closed обязателен для auth/scope/signature/price safety; offline/player используют
degraded/fallback; rollout — pause+rollback; poison events — DLQ; legal/financial ambiguity
— manual decision. Ошибка одного канала не скрывает состояние остальных.

## Дополнение E. Формат приёмки user story

Каждая story оформляется в трёх слоях: (1) `Given/When/Then` с видимым результатом,
(2) contract/behavioral proof API, данных, scope и failure path, (3) UI-smoke и human
walkthrough реальными кликами. История закрывается только при совпадении всех трёх слоёв.
API-only proof, screenshot, статический grep или зелёный mock без device/channel contract
не являются достаточным доказательством.

Машиночитаемый минимум story:

```yaml
id: US-CAM-001
actor: advertising_manager
goal: "создать и отправить кампанию"
benefit: "получить проверяемое размещение"
permission_code: campaigns.manage
scope: retailer/branch/cluster/store/surface
preconditions: []
entry_route: /login
happy_path_steps:
  - action: "открыть кампании"
    next: "список кампаний"
  - action: "нажать создать"
    next: "форма campaign"
negative_paths: ["нет inventory", "нет permission", "QA failed"]
acceptance_refs: [REQ-BIZ-001, REQ-UX-001]
journey_id: campaign.create
smoke_test: test_uismoke__campaign__create
walkthrough: PENDING
```

`walkthrough: PENDING` может установить агент; `OK` или замечания — только оператор/
аудитор. Каждый шаг обязан иметь одно видимое действие и следующий экран; прямой API,
deep-link в середину пути или скрытая обязательная операция делают story неприемлемой.

## 18. Что заполнить до статуса APPROVED

В active normative prose не оставлять слова «при необходимости», «рекомендуется»,
«уточняется» или варианты технологий без решения. Исторические changelog/AC и дословные
source quotations могут содержать их только как цитату или описание найденного дефекта.
До утверждения должны быть заполнены: владельцы и RACI,
точный scope каналов первой очереди, queue и signing profiles, SLA/NFR windows, финансовая
модель, юридический статус отчёта, retention, master-системы, API compatibility window,
пилотная шкала, нагрузочные пороги и дата пересмотра каждого deferred-пункта.

## 19. Нормативный словарь и единицы измерения

До разработки утверждаются определения, иначе одинаковые слова дают разные отчёты:

- `device` — физический вычислительный объект; `logical_carrier` — управляемый носитель;
  `surface` — конкретная зона показа; `channel` — тип способа доставки/показа.
- `delivery` — задание доставлено; `apply` — задание принято и применено; `playback` —
  контент фактически воспроизводился; `impression` — бизнес-метрика после утверждения
  правила подсчёта; `reach` — оценка аудитории, а не PoP.
- `online`, `degraded`, `offline`, `error`, `maintenance`, `revoked` имеют пороги,
  timestamp и влияние на SLA/инвентарь.
- Ёмкость, слот, длительность, frequency cap, план, факт, недопоказ и компенсация имеют
  единицы измерения и часовой пояс. Все timestamps хранятся UTC, UI показывает TZ объекта.
- `valid_to`, `offline_ttl`, retention и срок поддержки версии не являются одним сроком.

## 20. Каталог требований и обязательное покрытие исходника

Новая редакция должна сохранить трассировку к каждому разделу v2.5:

| Префикс | Область | Минимальный результат |
|---|---|---|
| REQ-SCOPE-001 | §1–2 | назначение, scope, исключения и дата пересмотра |
| REQ-ARCH-001…004 | §4, §17, §24 | domain boundaries, independence, async boundary и staged deployment |
| REQ-BIZ-001…017 | §1.2, §3, §6.2–6.3, §12, §16, §22.1–22.6, §22.12 | бизнес-цикл, commerce workflow, advertiser onboarding/self-service, versioned inventory rules, измеримые outcome-KPI, flight windows, типы/приоритеты, inventory, eligibility, SLA, underdelivery/make-good, quality/report views, financial reporting, workflow closure, A/B attribution и договорной PDF в advertiser-контуре |
| REQ-V26-001…011 | v2.6 Next Branch §§1–8 | tenant decision, sales-lift attribution, advertiser self-service, competitive separation, store-audience targeting, financial-system exchange, programmatic extension, dynamic creative, field mobile operations, A/B winner metric и external audience measurement |
| REQ-CONT-001, REQ-CONT-002 | §7, §22.5 | форматы, QA, renditions, версии, malware/HTML5 policy |
| REQ-MAN-001…005, REQ-ORCH-001…006, REQ-POP-001…004 | §8–11, §23–24 | playlist inheritance/override, manifest, field/ACK contract, edge safety, adapters, triggers/outbox, Orchestrator boundary, PoP |
| REQ-SEC-001…009 | §4.3, §6.1, §14, §16, §20 | identity, RBAC/RLS, mTLS, secrets, SIEM, PII, VPN, network segmentation, API attacks, storage boundary, system-administrator control plane |
| REQ-LIC-001 | §10, §15, §16, §22 | license grant, seat ledger, enrollment/decommission/renewal и signed-license Layer 2 boundary |
| REQ-DATA-001, REQ-DATA-002 | §15, §22.8, §22.11–22.12 | entity inventory/completeness, ownership, versioning, retention, finance |
| REQ-API-001…003 | §4, §16, §22.18 | endpoint schemas, auth, errors, PoP compatibility, migration и boundary separation |
| REQ-NFR-001…007 | §1.3, §3, §5, §17, §22.15 | scale, time, compatibility, PoP volume, analytics freshness, load acceptance, operational latency/continuity targets |
| REQ-OPS-001…009 | §5, §9, §10, §13, §17, §22.7, §22.9–22.10 | device health/heartbeat/commands, bounded cache/offline lifecycle, emergency governance, SLO, HA, DR, rollout, flags, monitoring, incidents, runbooks |
| REQ-UX-001…005 | §4, §12–13, §22.13, §22.19, §23.8 | роли, portal IA, journeys, channel readiness, accessibility, localization, errors и безопасное описание permissions |
| REQ-STAND-001…003 | §18, §22.14–22.15 | seed, performance, chaos, scale, safe data и feasibility gate |
| REQ-GOV-001…003 | §18–21, §25 | acceptance, owners, change control, agent/registry boundaries и двусторонняя roadmap-трассировка |

Каждый префикс раскрывается до атомарных ID; заголовок раздела без атомарных требований
не считается покрытием. Для каждого ID обязательны `MUST/SHOULD/MAY`, source line/section,
owner, dependency, task, acceptance, evidence и disposition.

Обозначения вида `REQ-BIZ`, `REQ-SEC` и другие без числового суффикса являются только
категориями группировки и не могут использоваться как ссылки на требования.

## 21. Обязательные негативные и пограничные сценарии

ТЗ должно явно описывать поведение при: конфликте и sold-out; истёкшем manifest;
невалидной подписи/SHA; отсутствии файла/места; duplicate PoP и out-of-order replay;
clock skew и смене часового пояса; offline сверх TTL; частичном отказе одного канала;
revoked device; недоступном vendor API; переполнении очереди/DLQ; rollback во время rollout;
изменении тарифа после показа; удалении media после закрытия кампании; emergency во время
обычной публикации; отсутствии price-master подтверждения; потере связи с ClickHouse после
его owner-approved activation по ADR-007.

Для каждого случая задаются fail-closed/fail-safe режим, пользовательское сообщение,
аудит, retry/rollback, влияние на отчёт и обязанность оператора.

## 22. Release-gates новой редакции

Статус ТЗ `APPROVED` возможен только при наличии:

1. подписанного scope и RACI владельцем;
2. разрешённых конфликтов и заполненных owner decisions;
3. полного каталога `REQ-ID` без orphan/duplicate;
4. согласованных domain/ERD/API/event/manifest schemas;
5. согласованных user stories, journeys и role/scope matrix;
6. проверяемых NFR, load profiles и acceptance evidence;
7. миграционного плана additive-first для существующего проекта;
8. обновлённой roadmap, где каждая строка матрицы имеет задачу либо approved deferred;
9. независимой сверки Claude и Codex и проверки внешним monitoring-dashboard как
   наблюдательным сигналом, не как источником истины.

Расхождение dashboard блокирует acceptance только после воспроизведения по первичному
источнику из Sources of Truth; собственный расчёт или недоступность dashboard блокером не
являются.

## 23. Конфликты, которые нельзя переносить в backlog без решения

- Исторический конфликт «Orchestrator до разработки» закрыт ADR-019: реализация, Adapter
  Layer и mock adapters начинаются только при втором реальном канале;
- ClickHouse в Phase 1 против deferred activation по ADR-007 (разрешён AC-158: PostgreSQL operational path до owner gate);
- HMAC/JWT/mTLS/Ed25519 без профиля по среде и срока перехода;
- queue как перечень альтернатив без выбранного owner и operational contract;
- финансовые сущности в обязательном контуре против исключения полной автоматизации ЭДО;
- §0.3 addendum говорит о двух точечных исключениях изменения существующих доменов (§4 и §6), а §8.3 — только об исключении §3.1 delivery/priority engine;
- юридически значимый PDF без решения юристов;
- RTO/RPO, SLA и retention, объявленные до утверждения методики измерения;
- исторические Hermes-инструкции внутри продуктового ТЗ.

Каждый конфликт получает `DEC-ID`, решение владельца, затронутые REQ-ID и дату вступления.
Молчаливое разрешение через код, roadmap или «deferred» запрещено.

## 24. Граница текущего черновика

Этот документ теперь является расширенным design draft, но всё ещё не финальным ТЗ:
конкретные значения, владельцы, юридические формулировки и схемы интеграций должны быть
получены от владельца проекта и ответственных систем. Следующий артефакт после согласования
— `TZ v2.6` и отдельная `requirements-traceability.yaml`; только они могут стать входом
для обновления roadmap.

## 25. Атомарный каталог требований (минимальный baseline)

Каталог содержит **101 уникальное требование**: 88 извлечённых из baseline v2.5,
11 из v2.6 Next Branch и 2 registry-derived gap (`REQ-BIZ-017`, `REQ-UX-005`).
Нормативность всех строк этого минимального каталога — `MUST`, если в самой формулировке нет
явного условия на approved DEC. Условное требование остаётся `MUST` внутри активированного
scope, но не считается реализуемым до решения. Полные `source/owner/task/status/acceptance/
evidence` являются обязательными полями следующего machine registry по §37; эта сводная
таблица их не заменяет. `REQ-BIZ-017` и `REQ-UX-005` имеют источник `feature-registry` и
обратную сверку с canonical journeys, а не исходный текст v2.5.

Следующие ID обязательны к раскрытию в `requirements-traceability.yaml`; это не замена
полной матрице, а контрольный минимум, чтобы крупные требования не скрывались под одной
строкой roadmap:

| ID | Требование | Обязательный результат |
|---|---|---|
| REQ-SCOPE-001 | Product purpose, boundaries and exclusions | owner-approved scope/deferred register |
| REQ-CORE-001 | Универсальная иерархия носителей | migration + seed network/branch/cluster/store/store_group/channel/device/surface уровней |
| REQ-CORE-002 | Channel-neutral campaign/inventory | campaign/inventory/RBAC/reporting core не импортируют channel adapter; добавление канала требует только нового adapter, capability profile, renditions и contract tests без переписывания core |
| REQ-CORE-003 | Target resolution boundary | placement таргетируется на network/branch/cluster/store/store-group, channel/device type, zone/category/SKU/shelf или набор surfaces, но не на `physical_device_id`; broad targets разрешаются до `display_surface_id` при планировании |
| REQ-ARCH-001 | Domain boundaries, ERD и event contracts | согласованные versioned artifacts |
| REQ-ARCH-002 | Product independence | платформа не зависит от Retail Media Dashboard, Hermes/LLM или другого внешнего runtime для production работы |
| REQ-ARCH-003 | Async I/O boundary | blocking I/O запрещён в async handlers/dependencies; используются native async или утверждённый threadpool |
| REQ-ARCH-004 | Environment deployment path | local Docker Compose; pilot на одном host с backup/monitoring/restore; test store с ≥2 backend/gateway за reverse proxy; production multi-host/Swarm или approved equivalent |
| REQ-CHAN-001 | Channel registry и capability profiles | versioned CRUD + scope/RLS; ESL production activation requires a separate pilot and approvals from price-process owner, Security, Operations and Legal |
| REQ-CHAN-002 | Physical/logical device-surface model | surface-level targeting, SLA и профили размеров (КСО 1440×1080, TV 1920×1080, ESL 296×128, LED 1200×80); one physical ESL gateway/LED controller may manage many logical carriers/surfaces with explicit parent-child links and independent status/manifest; adapters/players must not interfere with fiscal, checkout, price-verification, ESL or other critical store workflows; registration по одноразовому device_code + hardware_fingerprint с выдачей сертификата/ключа |
| REQ-CHAN-003 | Полное управление носителями | Admin/Operations должны видеть и управлять всеми physical device, logical carrier и display surface всех активных каналов через единый scope-aware API/UI: поиск/фильтры, health/status, manifest/version, rollout, диагностика и bulk-команды; каждая массовая операция имеет idempotency key, preview затронутых объектов, progress и отдельные completed/failed/pending результаты по carrier/surface, partial failure не скрывается, а действие на одном объекте не меняет соседние без явной связи; операции подчиняются permission/RLS/confirmation/audit и не вмешиваются в checkout, price-verification или критичный store workflow |
| REQ-LIC-001 | Licensing и seat ledger | License contour отделён от advertiser billing: versioned license grant принадлежит отдельному licensee, имеет signed payload/validity/revocation и seat capacity; active device identity атомарно резервирует один seat при enrollment, decommission освобождает его, renewal/grant replacement не отключает действующие устройства и переносит seats атомарно; превышение лимита и отсутствующий/отозванный/истёкший grant fail-closed для нового enrollment с машиночитаемой причиной и audit; Layer 2 signed `.lic`/JWS/CRL и UI upload/view не считаются готовыми без отдельного proof, а Layer 1 service/report остаётся доступным; license data не смешиваются с advertiser commercial entities |
| REQ-ORCH-001 | Orchestrator simulation | resolves broad targets to surfaces, runs conflict/preemption/availability simulation, creates immutable manifest/task versions, coordinates rollout and aggregates delivery/apply/proof/error status without coupling core to a channel |
| REQ-ORCH-002 | Adapter task lifecycle | массовая публикация идёт event-driven через persisted queue, а не прямыми синхронными вызовами portal→device/vendor; durable queue/retry/DLQ/idempotency; Redis не может быть единственным хранилищем критичного delivery-потока, выбранный broker и режим persistence фиксируются в DEC-004 |
| REQ-ORCH-003 | Delivery triggers and revocation | любая OLTP-запись, создающая domain event, создаёт outbox event атомарно (не только delivery-relevant mutation); pause/archive/expiry дополнительно порождают revocation и refresh manifest асинхронно; fire-and-forget допускается только для telemetry без business state |
| REQ-ORCH-004 | Transactional outbox integrity | domain write и outbox event в одной PostgreSQL-транзакции; relay атомарно claim-ит `pending` через lease/status `publishing`, публикует через NATS JetStream с `Nats-Msg-Id=event_id`, переводит `pending→published` только после broker ack, повторяет transient failure ограниченное число попыток (7), после чего переводит в `dead_letter` с operator action; события сохраняют `partition_key` и порядок внутри partition, глобальный порядок не обещается; replay безопасен и идемпотентен, published retention/cleanup и DLQ retention задаются policy; payload не содержит secrets, tokens или PII |
| REQ-ORCH-005 | Orchestrator rollout boundary | для KSO-first сохраняются только channel-neutral data contracts и тонкий compatibility seam; Channel Orchestrator, Adapter Layer и mock adapters не реализуются до появления второго реального канала, после чего вводятся по ADR-019 через approved extraction design и migration evidence |
| REQ-ORCH-006 | Channel Adapter contract | каждый adapter получает versioned task/manifest через утверждённый Gateway/API, подтверждает receipt, возвращает delivery/apply `proof` или `ack`, нормализованный `error`, и публикует health/status; контракт содержит timeout/retry/idempotency/circuit-breaker, mock mode и запрет прямого доступа к PostgreSQL/ClickHouse/MinIO |
| REQ-MAN-001 | Universal manifest schema | JSON Schema + compatibility rules; runtime polls manifest/content every 30 seconds with jitter and uses `ETag`/`If-None-Match`, returning `304 Not Modified` when the representation is unchanged |
| REQ-MAN-004 | Manifest field contract | обязательны opaque external `manifest_id`, `device_id`, `store_id`, `playlist_version`, `valid_from`, `valid_to`, `media_files[]` с непрозрачным `media_ref`/короткоживущим signed fetch reference (внутренний MinIO object key не раскрывается device-facing API), `sha256`, `duration`, `order/weight`, `priority`, `emergency_flag`, `fallback_rules`, `signature`, `channel_type/device_type`, `capabilities`, `renditions[]`, `adapter_payload`; runtime ACK states: received/verified/applied/load_error/insufficient_storage/invalid_signature |
| REQ-MAN-005 | Playlist inheritance and overrides | hierarchy-level playlists inherit from network/branch/cluster/store/channel and allow explicit scoped overrides with precedence, effective time, version/diff and audit; resolved playlist is deterministic and reproducible |
| REQ-MAN-002 | Signed manifest | Ed25519 profile, key rotation/revoke, offline verify |
| REQ-MAN-003 | Edge safety and kill-switch | invalid/future/expired manifest отклоняется fail-safe; сохраняется last-known-good/fallback, kill-switch имеет приоритет и аудит; без `fallback_rules` — blank/black, fallback не создаёт PoP по умолчанию |
| REQ-POP-001 | Normalized proof model | целевой `pop_mode` enum: `real_playback`, `screen_render`, `idle_screen`, `template_applied`, `gateway_ack`, `label_ack`, `controller_ack`, `error`, `not_applied`; playback/apply/delivery/error/not-applied не смешиваются в одном коммерческом факте. Текущий кодовый `ProofMode` содержит только первые семь modes, поэтому `error/not_applied` до schema/runtime migration являются обязательной compatibility projection, а не доказанным implemented enum. |
| REQ-POP-002 | At-least-once ingestion без дублей | signature/time/manifest validation + dedupe; при потере связи события/ack/error буферизуются локально или на gateway и после восстановления отправляются батчами в хронологическом порядке с reconciliation |
| REQ-POP-003 | Runtime proof endpoint | PoP только от runtime через `POST /api/v1/pop/batch`, batch ≤500; `event_type=proof`, `device_id` совпадает с JWT subject и с physical device, указанным в manifest; fallback не создаёт коммерческий PoP без явного `fallback_rules.emit_pop=true` |
| REQ-POP-004 | Canonical proof event validation | flat `proof_event_v1`: opaque external event/manifest/campaign/placement/creative/media/store/surface/device IDs, mandatory `event_type=proof`, schema_version, started_at/ended_at/rendered_at/event_recorded_at/duration_ms/playback_result/media_sha256/failure_reason/device_signature; runtime `playback_result` допускает только `success/skipped/failed/interrupted`, техническая причина хранится отдельно в `failure_reason` (включая `device_offline`, `file_missing`, `sha_mismatch`, `manifest_expired`, `emergency_override`, `player_error`, `touch_hidden`); device JWT only, device ID must match JWT subject and manifest binding, signature and SHA validation, 409/422 rules, clock-drift quarantine, без internal IDs, paths/tokens/PII |
| REQ-CONT-001 | Creative/rendition QA | checks выполняются отдельно для каждой immutable rendition и cover format/MIME/resolution/file size/duration/codec/FPS/bitrate, no-audio policy, profile zone (KSO 1440×1080), color/brightness constraints, SHA-256 and security; preview реального профиля и hide-on-touch для УКМ4; visual QA проверяет читаемость текста, safe margins, отсутствие мелкого шрифта и перекрытия рабочей области УКМ4 на 75% preview; сохраняются reviewer/actor, timestamp, применённые правила/checklist, comments, approved creative/rendition version и decision/reason; rendition без approved QA не попадает в manifest |
| REQ-CONT-002 | Immutable media history | каждая media/rendition version хранит uploader/author, timestamp, SHA-256, source metadata, QA/moderation decision и связь с заменённой версией; история immutable, retention/legal hold и logical delete не нарушают воспроизводимость закрытых отчётов |
| REQ-BIZ-001 | Placement/inventory calculation | capacity/reserved/sold/free рассчитываются и показываются по network/branch/cluster/store/device/logical carrier/surface; forecast показов/контактов — по периоду, времени, географии и channel/surface; бизнес-статусы inventory: `free`, `reserved`, `sold`, `internal`, `emergency/fallback`. Runtime projection обязан явно mapping-ить фактические slot states (`available`, `limited`, `sold_out`, `blocked`) в бизнес-статусы и не выдавать projection за persisted enum; правила в админке задают max ad load, slot duration, prime-time, priorities и filler; единицы зависят от канала: KSO/TV — эфирное время/слоты, price checker — idle-показы, ESL — статичное размещение/шаблон, LED — цикл баннера; conflict включает расписание, долю рекламного времени, priority и campaign limits; reservation/commit выполняются атомарно с проверкой актуальной capacity и version/lock, конкурентные запросы не могут продать или зарезервировать один и тот же слот дважды; overbooking запрещён по умолчанию и возможен только после owner-approved policy; sold-out предлагает альтернативные магазины/периоды/слоты; пример placement: 500 магазинов, 08:00–12:00, 10 секунд, priority 50 |
| REQ-BIZ-002 | Commercial lifecycle | advertiser record includes legal entity, brand, contacts and responsible persons; до брони создаётся versioned commercial proposal/quote с составом placement, inventory forecast, tariff/discount/package/bonus/compensation и сроком действия; каждая campaign обязана иметь ровно одного advertiser organization и `advertiser_contract_id NOT NULL` (brand optional), а каждый flight `start_at/end_at` должен находиться внутри `advertiser_contract.valid_from/valid_until` (если договор бессрочный — только нижняя граница); API отклоняет нарушение до submit/reservation; campaign stores advertiser/brand/order/contract basis, период/goal/limits/budget-or-volume/responsible/status и payment/confirmation status, если этот контур входит в scope; placement хранит frequency/constraints; изменения периода, географии, креатива или объёма создают новую immutable placement version с audit и diff; замена креатива в live campaign требует новой версии и повторного approval; versioned lifecycle and audit |
| REQ-BIZ-003 | Approval policy | для каждого campaign/placement/creative задаются required approval roles, scope, порядок и transition criteria; submit/approve/reject/publish — отдельные permission-коды с запретом self-approval, bypass и публикации при неполном наборе решений; `rejected` — отдельное состояние с обязательной причиной, actor/time/version/affected scope; по ADR-015 `rejected → draft` создаёт новую immutable revision того же campaign, а schedule/publish rejected revision запрещены; каждое решение immutable, изменение approved объекта возвращает его в новую version с повторным approval |
| REQ-BIZ-004 | Service-quality reporting | advertiser и quality reports показывают по каждому каналу долю active devices/logical carriers/surfaces, channel-specific inventory/SLA/proof metrics, freshness, underdelivery и исключения; показатели не смешивают несопоставимые proof types |
| REQ-BIZ-005 | Campaign flight windows | отдельные versioned flight/placement windows с обязательными `start_at/end_at` в UTC, локальной TZ для UI и запретом показа вне окна |
| REQ-BIZ-006 | Manifest eligibility | eligibility требует approved status, валидный flight и contract, resolved target и ready/approved creative; runtime kill-switch не запускает регенерацию manifest |
| REQ-BIZ-007 | Campaign type and priority | явные типы commercial/internal/compensation/test/filler и версионируемая иерархия приоритетов с `effective_at`, объяснимым preemption и запретом ретроспективного изменения исторических отчётов |
| REQ-BIZ-008 | Underdelivery and make-good | классификация причин недопоказа (technical/operational/business/emergency/content/planning/device/store), plan/fact/выполнение в процентах/underdelivery в отчёте и предложения докрутки: дни, магазины, слоты или компенсационный объём; compensation placement — отдельный тип с явной маркировкой и не смешивается с проданным inventory без owner-approved policy |
| REQ-BIZ-009 | Financial reporting boundary | scope финансового контура (заказ, договор, тариф, price list, discount, package/bonus, compensation, payment/confirmation status и ЭДО) должен быть явно принят owner decision; если сущность входит в scope, система хранит versioned basis, plan/actual financial values по campaign/branch/store/period/inventory type, разделяет paid/internal/filler/bonus/compensation и не изменяет закрытые расчёты задним числом; если сущность исключена, exclusion содержит DEC-ID, владельца, причину, trigger и review date и не позволяет заявлять финансовый факт. Этот REQ отвечает за финансовые факты и отчётность, а не за базовый workflow заказа. |
| REQ-BIZ-010 | Campaign workflow closure | для каждого шага lifecycle назначены role/owner, допустимые действия, SLA/deadline и transition criteria; поддерживаются pause, частичное снятие target-ов, продление и смена креатива только новой версией; `completed/closed` разрешён только после итогового plan/fact отчёта и фиксации причин отклонений |
| REQ-BIZ-011 | Reporting views | обязательны network dashboard (active campaigns/today plan-fact/problems), campaign dashboard (plan-fact/geography/dynamics/no-play/reasons), store/device view (manifest/campaigns/errors/connectivity/cache), advertiser report (stores/plan-fact/map/exclusions/PDF-XLSX-CSV и проверяемая цепочка данных с подписью/штампом системы только по решению `DEC-007`), inventory report (free/occupied/reserved/sold-out/forecast) и SLA report (online share/underdelivery/reasons/compensation); текущий runtime evidence подтверждает только CSV export, PDF/XLSX остаются отдельными planned deliverables и не могут быть отмечены done |
| REQ-BIZ-012 | A/B test attribution | A/B campaign фиксирует control/test groups, assignment scope, period, winner metric и minimum sample; результат требует ручного owner approval, versioned rules и не меняет исторические отчёты задним числом |
| REQ-BIZ-013 | Business outcome KPI | для каждой бизнес-цели §1.2 владелец утверждает baseline, target, metric definition, unit, measurement window, data source, owner и review date; отчётность разделяет outcome-KPI и технические SLO, а отсутствие утверждённой методики не допускает заявления о достигнутом бизнес-эффекте |
| REQ-BIZ-014 | Commerce contour 2 | Тарифы, price lists, offers, orders и inventory booking образуют обязательный versioned operational workflow; каждая операция имеет advertiser/retailer scope, permission, idempotency, audit и transition criteria; booking атомарно проверяет актуальную capacity, закрытый order immutable. `payment/confirmation status`, financial fact, advertiser billing и полный ЭДО включаются только по owner-approved DEC-017 и не подменяются внутренним статусом заказа; license contour не смешивается с advertiser billing. |
| REQ-BIZ-015 | Advertiser onboarding и self-service | Заявка рекламодателя, review/approval, создание организации, brand, contact и legal requisites, приглашение пользователей и self-service campaign/report образуют versioned workflow с явными pending/approved/rejected/suspended состояниями; до approval коммерческие операции запрещены, после approval каждый объект ограничен advertiser/retailer scope, invite/revoke и изменения реквизитов аудируются, а self-service не получает operations/admin/device permissions; `self.apply_or_brief`, `self.campaign_create`, `self.campaign_view`, `self.report_view` и `advertiser.*` имеют отдельные acceptance и roadmap mapping |
| REQ-BIZ-016 | Versioned inventory rules | Правила inventory (capacity, max ad load, slot duration, prime-time, priority, filler, channel/surface/store scope) хранятся как immutable versions с owner, effective_at/effective_until, simulation result и approval; новая версия не изменяет исторические расчёты и активные reservations до effective date, overbooking/conflicts показываются до activation, rollback выбирает последнюю approved версию и аудируется; `inventory.rule_create` имеет отдельные permission/scope, idempotency, positive/negative proof и roadmap mapping |
| REQ-BIZ-017 | Advertiser contract PDF upload | Уполномоченный администратор через UI выбирает рекламодателя, создаёт договор и загружает PDF; MIME/размер/целостность валидируются, metadata и immutable version сохраняются в advertiser/retailer scope, actor/time/result аудируются, storage path и secrets не раскрываются; повторная загрузка создаёт новую версию, удаление не нарушает историческую отчётность |
| REQ-V26-001 | Tenant model conformance | ADR-018 уже принял multi-retailer/syndication-ready модель; все новые tenant-сущности получают `retailer_id NOT NULL`, FK и двухуровневые retailer+advertiser RLS policies с migration/behavioral evidence; новый tenant ADR нужен только для изменения принятой модели |
| REQ-V26-002 | Attribution & sales lift | Принимать только агрегаты store/SKU/day, строить versioned baseline и test/control по магазинам, рассчитывать lift и confidence/значимость; исходные факты и методология immutable |
| REQ-V26-003 | Advertiser self-service | Отдельный advertiser web позволяет scoped inventory/forecast, draft, creative upload и submit в общий moderation/approval; guardrails бюджета/объёма и RBAC/RLS обязательны |
| REQ-V26-004 | Competitive separation | Brand/advertiser имеет `competitive_category`; playlist/manifest проверяет интервал и exceptions, блокирует конфликт или требует явный audited override |
| REQ-V26-005 | Store-audience targeting | Анонимные price-segment/average-check/traffic-profile атрибуты участвуют в placement targeting; master-data adapter в текущем коде отсутствует, поэтому ingestion является prerequisite и требование `blocked` до contract/owner/behavioral evidence |
| REQ-V26-006 | Financial-system exchange | Versioned/idempotent export и обратный payment-status contract; повтор не создаёт дубль, внешнее `paid` не смешивается с order status и требует reconciliation |
| REQ-V26-007 | Programmatic extension point | ADR и SSP-facing availability contract проектируются, но DSP/SSP auto-buy остаётся excluded до отдельного owner decision |
| REQ-V26-008 | Dynamic creative | На одном выбранном канале master-confirmed price/promo подставляется при manifest generation; dynamic marker отделён от static content hash и price source не становится portal |
| REQ-V26-009 | Field mobile operations | Scoped mobile web/app для сотрудника магазина показывает устройства, принимает photo proof и incident; publish/content/admin операции исключены |
| REQ-V26-010 | A/B winner metric | Winner может быть delivery или lift metric, при minimum sample и owner approval; результат versioned и не переписывает историю |
| REQ-V26-011 | External audience measurement | ADR фиксирует export PoP/manifest contract как designed-not-implemented extension до появления approved provider decision |
| REQ-SEC-001 | Identity and MFA | AD/LDAP или корпоративный SSO; для internal staff production-протокол и TLS-профиль фиксируются (ADR-006: LDAPS, plain LDAP запрещён), advertiser users имеют отдельный local lifecycle (invite/register, bcrypt, reset без user enumeration), local account разрешён только как admin break-glass (≤2, вручную заведён, не через API); MFA обязательно для системных администраторов, согласующих и любого пользователя с permission публикации или emergency, с session policy; **user** access JWT — 15 min, rotating **user** refresh — 8 h в HttpOnly Secure SameSite cookie, access token не хранится в local/session storage и токены не попадают в URL; logout/admin revoke инвалидируют сессию; login/reset rate limits и correlation ID обязательны; shared accounts запрещены, все действия привязаны к пользователю и отдельное право требуется для изменения approved campaigns |
| REQ-SEC-002 | Tenant/retailer isolation | RLS и object authorization применяются на уровнях retailer/network → branch → cluster → store → channel/device/surface и advertiser; scope вычисляется из authenticated principal/session, а не из неиспользуемого или подменяемого параметра; scope наследуется только вниз по разрешённой иерархии, несколько явно назначенных scope объединяются как union разрешённых областей (никогда не intersection и не implicit global), scoped role не расширяется отсутствием scope; cross-tenant/cross-retailer доступ запрещён, каждый deny/allow проверяется negative/positive matrix и immutable audit; frontend route guards используют те же backend permission-коды и scope; фоновые workers, не проходящие HTTP middleware, обязаны перед каждой транзакцией установить явный worker RLS context (system-scoped только для документированного service identity либо job-derived scope), используя runtime role без `BYPASSRLS`/superuser |
| REQ-SEC-003 | Device/vendor security | ADR-003 lifecycle обязателен: одноразовый `device_code` + `hardware_fingerprint` + `device_type` для enrollment; server-side выдача opaque `device_id` и device secret/optional certificate после проверки proof-of-possession; если сертификат включён, его профиль явно выбирается из поддержанных `rsa/ed25519/hsm`, с owner-approved capability/rotation/revoke policy; credentials хранятся на устройстве зашифрованно; session establishment — HMAC(secret, nonce) с server-side nonce replay cache; short-lived **device** JWT (15 min) передаётся только в `Authorization: Bearer`, rotating **device** refresh token (24 h) — только в выделенном защищённом поле протокола, оба никогда не попадают в URL; revoke немедленно инвалидирует secret/refresh token, active JWT истекают ≤15 min; rotation атомарна с audit; повторное использование кода, неверный fingerprint, replay nonce, просроченный/отозванный credential и cross-device manifest должны fail-closed; mTLS-ready adapter допускается, полная PKI/CRL/OCSP и proxy enforcement — только отдельный production-hardening decision |
| REQ-SEC-004 | Data protection | data classes (public/internal/confidential/PII), lawful purpose and minimisation, residency, encryption in transit/at rest, access review, export/delete request and incident notification; secrets never enter code/logs/URLs/payloads; SIEM, VPN and retention controls are mandatory |
| REQ-OPS-001 | Device health/commands | status thresholds и per-device health view с last heartbeat, current manifest, player/Chromium version, free disk, cache size, recent errors, last successful playback и recent PoP; device-раздел фильтруется по типу носителя, версии player/adapter, магазину, зоне, статусу, current manifest и ошибкам применения; система формирует списки полностью выпавших магазинов и устройств, влияющих на активные кампании, и передаёт их в forecast/underdelivery; runtime health statuses строго соответствуют коду: `unregistered`, `online`, `degraded`, `offline`, `error`, `maintenance`, `revoked`; `pending` и `registered` — отдельные enrollment stages/projection, не значения `DeviceStatus`; до завершённого enrollment (`unregistered/pending`) delivery/commands запрещены, `maintenance` исключает объект из SLA и показов, `revoked` блокирует команды/доставку; command enum `restart_player`, `clear_cache`, `refresh_manifest`, `set_maintenance`, `disable_playback`, `revoke_credential`, `sync_gateway`, `inspect_applied_state`, `diagnostics`; bulk safeguards, scope/confirmation/audit |
| REQ-OPS-009 | Device heartbeat contract | Каждый runtime/device отправляет authenticated heartbeat с `device_id`, `store_id`, `channel_type`, `timestamp_utc`, local timezone, runtime/player/adapter/manifest versions, health state, cache/free-disk и monotonic sequence; сервер дедуплицирует/проверяет scope и clock drift, вычисляет freshness/online→degraded→offline thresholds по channel profile, сохраняет последний валидный heartbeat и audit/metric correlation, а просроченный или подделанный heartbeat не продлевает SLA и не маскирует offline; canonical payload/version и negative tests обязательны для `POST /api/v1/device/heartbeat`, legacy alias допускается только с одинаковой семантикой и deprecation |
| REQ-OPS-007 | Emergency control | только ограниченные роли с MFA и обязательной причиной; действия включают stop-рекламы, системное сообщение, запуск fallback и возврат к штатному manifest; scope/priority/progress по устройствам, partial-result, audit (actor, timestamp, level, reason, affected objects, delivery result) и безопасный resume; emergency-команды доставляются через отдельный высокоприоритетный канал Device Gateway с независимым SLA и fail-safe retry |
| REQ-OPS-008 | Runtime cache lifecycle | лимит локального кэша на профиль устройства, детерминированная очистка неиспользуемых/устаревших файлов, сохранение last-known-good и отсутствие бесконечного показа просроченной платной рекламы без риска в отчёте |
| REQ-OPS-002 | Rollout/rollback/flags | baseline stages `lab → 5 stores → 50 stores → 300 stores → 10% network → 50% network → all network` для player/manifest/schedule/content/config changes; canary thresholds, pause, rollback evidence; feature flags адресуются pilot stores/branches/roles или проценту устройств, каждая смена фиксирует actor/value/scope/time/reason и critical flags откатываются через admin UI |
| REQ-OPS-003 | HA/DR/backup | topology, RTO/RPO, backup schedule, encryption, offsite copy, retention, named owner и restore drill; PostgreSQL operational backup обязателен в Phase 1, ClickHouse partitioning/TTL и backup/restore добавляются при approved activation по ADR-007, MinIO versioning/lifecycle и backup/replication |
| REQ-OPS-004 | Observability | backend, Device Gateway, PoP ingestion, Analytics, MinIO, PostgreSQL, ClickHouse, Redis, players и adapters публикуют структурированные logs и metrics; end-to-end `correlation_id/trace_id` связывает user action → manifest generation → delivery → device/surface apply → proof → report; trace, metrics, alerts, incident runbooks; алерты на массовый offline, рост PoP/apply-ack ошибок, недоступность Gateway, сбои adapters, переполнение диска, деградацию ClickHouse/MinIO и нарушение campaign SLA; четыре раздельных dashboard (technical/business/security/service-quality) с владельцами, freshness, drill-down и evidence |
| REQ-OPS-005 | Operational readiness | инструкции запуска/остановки/обновления/отката/восстановления; player имеет systemd/restart policy, локальный структурированный log и health status; health-панель сервисов, БД, очереди, media, устройств и PoP с channel/surface drill-down и offline/error indicators |
| REQ-OPS-006 | Production HA baseline | минимум 2 backend и горизонтально масштабируемый Device Gateway за балансировщиком; Gateway имеет health-check, rate limiting и отдельные метрики; HA/standby PostgreSQL, ClickHouse partitioning/TTL и репликация или restore только после approved activation по ADR-007, MinIO versioning/lifecycle и replication/restore, Redis Sentinel/Cluster либо документированный сценарий восстановления, persisted queue и ежеквартальный restore drill |
| REQ-UX-001 | Role-specific portal | отдельные route/action/data capabilities для полного набора ролей исходного ТЗ: системный администратор (users/roles/devices/settings/monitoring/audit), рекламный менеджер (campaign/inventory/creative/submit), модератор контента (QA/comments/return без device/user control), согласующий (impact/risk/change/approve-reject), аналитик (plan/fact/underdelivery/comparison/export), оператор поддержки/эксплуатация (health/errors/versions/rollout/rollback/diagnostics), ИБ (audit/permissions/device/emergency/security events) и рекламодатель (только свои read-only отчёты); Operations-интерфейс не смешан с коммерческими отчётами, advertiser UI простой и без лишних технических терминов; UI использует backend data, а demo data допускается только в безопасном стендовом контуре с явной маркировкой; accessibility matrix; searchable/filterable/sortable tables with saved views, bulk-operation consequences, visible progress for long media/report/publication/rollout/export operations, actionable errors (`what/why/next step/owner`), error recovery; CSV implemented, PDF/XLSX planned до отдельного evidence |
| REQ-UX-002 | Human walkthrough | operator evidence на реальном DEV |
| REQ-UX-003 | Accessibility and localization | утверждённый accessibility target (уровень стандарта, keyboard/screen-reader/contrast checks) и locale/timezone matrix с acceptance evidence |
| REQ-UX-004 | Campaign readiness matrix | при создании/согласовании кампании UI показывает по каждому выбранному каналу: rendition approved, inventory sufficient, conflicts, forecast reach, PoP mode и SLA readiness; причина каждого `blocked`/`warning` ведёт к следующему действию |
| REQ-UX-005 | Permission descriptions | В управлении ролями UI показывает стабильные permission code, label и description; неизвестное право безопасно получает fallback `label=code` и нейтральное описание без падения страницы; каталог не расширяет permissions и не разрешает назначение вне scope, изменения описаний versioned/audited |
| REQ-INT-001 | УКМ4/чековые данные | phase 1 допускает пакетную загрузку только агрегированных чековых данных; phase 2 — регулярный approved API/ETL; оценочный reach вычисляется по утверждённой формуле (playback × число чеков/транзакций за магазин/период), не влияет на кассовые/фискальные операции, а в отчётах отделён от фактических показов |
| REQ-INT-002 | Price/SKU master | ESL/price-checker price-related данные приходят из approved price/SKU master или проходят reconciliation; при рассинхроне публикация блокируется; обязательные price fields отделены от рекламных бейджей/QR и не могут быть изменены portal |
| REQ-INT-003 | BI/export/SIEM/vendor | BI/export API требует authentication, rate-limit, immutable audit и ограничение advertiser/role/retailer scope; vendor connectors используют отдельные credentials, rate-limit, retry/circuit breaker, health-check, reconciliation, журналирование и явный failure mode; SIEM export сохраняет scope и audit |
| REQ-API-001 | Versioned API and event compatibility | OpenAPI/event schemas, errors, deprecation/migration; для resource URLs выбирается один canonical opaque external identifier (в текущем campaign ADR — stable `code`, не database PK), форма `/.../{id}` из исходного ТЗ допускается только как versioned compatibility alias с одинаковой authorization/scope/idempotency semantics, explicit deprecation date и migration evidence; смешение `{id}`/`{code}` в одной версии API запрещено |
| REQ-API-002 | API boundary separation | User API, Device API, analytics API и emergency API логически разделены; device clients не имеют доступа к admin endpoints |
| REQ-API-003 | PoP endpoint compatibility | каноничен `POST /api/v1/pop/batch` по ADR-017; legacy `/device/pop/batch` только временный alias с deprecation и migration evidence |
| REQ-DATA-001 | Data ownership and lifecycle | dictionary, lineage, immutable versioning/diff для campaign/placement/playlist/manifest/priority/inventory/player settings, API contracts, DB schema и advertiser reports, PII, retention, archive/delete; delivery-relevant objects удаляются логически, физическое удаление допускается только после retention и проверки legal/contract constraints; owner-approved working defaults: PoP hot 12–18 мес., PoP/report archive 3–5 лет, audit ≥3 лет, technical logs 90–180 дней, creatives 1–3 года; `DEC-007` закрывает legal/152-ФЗ approval и исключения, а не отменяет defaults; advertiser isolation; export только по scope/permission, с audit и лимитами периода/объёма |
| REQ-DATA-002 | Canonical entity inventory | ERD/data dictionary обязаны перечислить и связать все группы §15: верхнеуровневую сущность `retailers` и обязательный `retailer_id NOT NULL` + FK на каждой tenant-таблице (с backfill существующих данных и двухуровневыми RLS-политиками), hierarchy (`branches`, `clusters`, `stores`, `store_groups`), devices/certificates/status/commands/events, users/RBAC/scopes, advertisers/contracts/orders, campaigns/placements/targets/status history, media/creative moderation, inventory rules/reservations/snapshots, playlists/versions/manifests, approvals, emergency, operational audit, channel/device capabilities/player builds/adapter configs, renditions и ESL/LED gateway/label/controller/surface/vendor events; пропуск группы или retailer-boundary — schema/design-gate failure |
| REQ-NFR-001 | Capacity/performance | 40K + additional channels load profile; Control Plane/admin portal availability ≥99.5% в утверждённом рабочем окне, Gateway ≥99.9% внутри сети; PoP loss ≤0.1% принят owner product decision; для каждого SLO фиксируются measurement window, denominator и degraded-mode exclusions, а production claim требует load evidence |
| REQ-NFR-002 | Time/calendar | all DB/log events store UTC plus object local TZ; campaign schedules use store local time unless an approved business rule says otherwise; reports display the reporting TZ; date boundaries, overnight intervals, DST, holidays, closed stores and schedule exceptions are explicit versioned rules |
| REQ-NFR-003 | Compatibility | Device/API/manifest version window with explicit deprecation dates; heartbeat advertises supported API/manifest schema and capability versions so the server selects a compatible representation; breaking changes require staged rollout, migration rehearsal, compatibility window and rollback |
| REQ-NFR-004 | Network scale and PoP volume | до 10 000 магазинов, 40 000+ устройств и десятки/сотни млн PoP в год без смены базовой архитектуры; Phase 1 использует утверждённую ADR-007 PostgreSQL operational path, а ClickHouse ingestion/история и потоковая обработка включаются только после owner-approved Phase 4+ gate с backpressure и queue-lag telemetry; миграция/backfill и совместимость обязательны |
| REQ-NFR-005 | Analytics freshness | утверждённый maximum latency отчёта после PoP и контролируемый percentile |
| REQ-NFR-006 | Load-profile acceptance | профили: 40K KSO (heartbeat/manifest 30s с jitter, PoP batch 60s), дополнительные Android/TV/price-checker/ESL/LED, массовая публикация и emergency на всю сеть, analytics за 1/7/30/12 мес., сотни read-only advertisers; `до 100 admin` — proposed до `DEC-009`; для каждого утверждены API/report response time, error rate, CPU/RAM/disk budgets и degraded-mode behavior |
| REQ-NFR-007 | Operational latency and continuity | при штатной сети manifest обновляется ≤5 минут для 95% online-устройств, emergency-команда доставляется ≤60 секунд для 95% online-устройств, PoP появляется в отчёте ≤15 минут; runtime автономно работает ≥7 дней по последнему valid manifest; полное восстановление RTO ≤4 часа, операционная БД RPO ≤15 минут; для каждого показателя фиксируются percentile, measurement window, denominator, exclusions и degraded-mode behavior |
| REQ-SEC-005 | Critical-action audit completeness | 100% критичных действий неотключаемо без решения ИБ; user-initiated audit events содержат существующий actor UUID, связанный с аутентифицированной учётной записью, а service/device/vendor actors имеют отдельный тип и проверяемый credential identity; анонимные или подставные actor IDs запрещены |
| REQ-SEC-006 | API attack protection | все user/device/vendor входы проходят schema validation и bounded size/depth; object-level authorization проверяет resource+tenant scope до чтения/изменения (IDOR запрещён); SQL только параметризованный/ORM без string concatenation; browser mutation защищён CSRF token/origin check, output/context encoding и CSP/XSS controls; SSRF закрыт egress allow-list, запретом private/link-local metadata targets и безопасными redirect/DNS re-check; rate limit задаётся по endpoint и principal/IP с `429` + `Retry-After`, audit и недоступностью bypass; CORS allow-list и security headers фиксируются по environment; секреты/токены/PII не попадают в URL, logs или error payload; все controls имеют runtime negative tests |
| REQ-SEC-007 | Object storage boundary | MinIO buckets приватны, service accounts ограничены, presigned URL выдаётся только по утверждённой политике доступа и с коротким TTL |
| REQ-SEC-008 | Network segmentation | устройства/плееры/шлюзы инициируют только исходящие HTTPS/mTLS или approved vendor/API connections к Gateway; Admin API недоступен device-сегменту, а PostgreSQL/ClickHouse/MinIO/Redis — магазинам и пользовательским workstation; административный UI доступен только из корпоративной сети/VPN через AD/SSO/MFA; firewall rules и negative reachability tests обязательны |
| REQ-SEC-009 | System administrator control plane | системный администратор управляет users, roles, permissions, LDAP/SSO bindings, devices, settings, monitoring и audit только через отдельные permission-коды и назначенный scope; операции имеют validation, confirmation, immutable audit и не дают права менять approved campaigns без отдельного разрешения |
| REQ-STAND-001 | Safe realistic seed | all channels, 1M synthetic PoP/apply-ack events and scenarios for active/completed campaigns, underdelivery, offline devices, emergency, schedule conflicts, compensation and sold-out; stand reset/seed позволяет быстро проверять filters, reports, permissions, UI и business logic и имеет owner-approved time-bound target восстановления с измерением от команды запуска до доступности smoke-набора; no real PII/tokens/contracts/secrets |
| REQ-STAND-002 | Exact demo composition | 10 branches/50 clusters/500 stores; 2,000 KSO, 500 Android/TV, 300 price checkers, 50 ESL gateways, 100 LED banners, 20 advertisers, 100 campaigns, 500 creatives |
| REQ-STAND-003 | Real KSO feasibility gate | до начала основной реализации на реальной КСО подтверждены 1440×1080, hide-on-touch, кассовая безопасность, сеть, права, heartbeat/manifest и базовый playback/PoP; evidence фиксирует окружение, дату, owner и ограничения пилота |
| REQ-GOV-001 | Agent/change/acceptance boundaries | до изменения — анализ текущего состояния и mini-design с файлами/слоями/рисками/проверкой/commit; после шага — что сделано, изменённые файлы, способ проверки и точные команды, пройденные тесты, номер/сообщение commit и оставшиеся риски/вопросы; Claude Code является единственным implementation agent, Codex — architect/reviewer, Hermes — только исторический контекст и не runtime-зависимость; OpenAPI/event schemas обновляются атомарно вместе с backend-кодом; secret scan не допускает секреты в code/repository; обязательная test matrix покрывает auth/RBAC/RLS, hierarchy, playlist inheritance/override, schedule/inventory conflicts, capacity/sold-out, creative/playlist/manifest versioning, PoP/dedupe и emergency; архитектурные, API, security и business изменения требуют отдельного owner gate |
| REQ-GOV-002 | Feature-registry двусторонняя трассировка | Каждый ID `docs/product/feature-registry.yaml` должен иметь в ТЗ и traceability-манифесте canonical REQ/story или explicit approved exclusion; registry status `reachable/blocked/deferred` синхронизируется с delivery evidence, roadmap task, owner и UI/backend proof. Обратная связь обязательна: каждый REQ/story/journey, заявленный драфтом, обязан разрешаться в registry либо иметь owner-approved disposition; расхождение, дубль или неизвестный ID блокирует `APPROVED` |
| REQ-GOV-003 | Roadmap coverage и status contract | Каждый REQ, story, journey и approved decision обязан иметь одну или несколько явных задач в `docs/product/roadmap.yaml` либо owner-approved deferred/exclusion с причиной; каждая roadmap task обязана ссылаться на REQ/story/decision или быть явно classified как governance/process. `requirement_status` (что утверждено) и `delivery_status` (planned/in_progress/verification/done/blocked) ведутся раздельно, имеют owner, timestamp, evidence и синхронизируются с registry/generated views; задача без mapping, дубликат mapping или stale status блокирует `APPROVED`. |

## 26. Минимальные API и события

Для утверждения каждой группы API требуется таблица endpoint → request/response schema →
auth/scope → idempotency → errors → retry → audit → owner. Baseline-группы:

Каталог ниже смешивает фактические и целевые операции только там, где статус подписан
явно. Маркер `фактический/implemented` требует совпадения с generated OpenAPI на pinned
Git SHA; `proposed/required` означает целевой контракт. Любой путь без такого маркера
имеет статус `UNVERIFIED`, а не implemented, до выпуска endpoint-manifest.

Пути ниже записаны в сокращённом виде для читаемости: canonical public и device API
используют обязательный version prefix `/api/v1/` (для Device Gateway — `/api/v1/device/`).
Shorthand `/api/...` не обозначает второй маршрут;
его OpenAPI-развёртка, auth/scope и deprecation должны совпадать с canonical endpoint.

- **Фактические:** `/api/v1/auth/login`, `/api/v1/auth/refresh`, `/api/v1/auth/logout`, `/api/v1/auth/me`, `/api/v1/auth/change-password`; `/api/v1/identity/users`, `/api/v1/identity/roles`, `/api/v1/identity/permissions`, `/api/v1/identity/auth/ad-settings`, `/api/v1/identity/auth/ad-settings/test` (auth/settings read/update/test с отдельными permission, audit и safe validation);
- **Required/UNVERIFIED shorthand:** `/api/branches`, `/api/clusters`, `/api/stores`, `/api/advertisers`, `/api/contracts`, `/api/orders`;
- **Фактические:** `/api/v1/identity/advertiser-applications`, `/api/v1/identity/advertiser-applications/{id}/review`, `/api/v1/identity/advertiser-applications/{id}/invite`, `/api/v1/identity/advertiser-organizations`, `/api/v1/identity/advertiser-brands`, `/api/v1/identity/advertiser-contacts`, `/api/v1/identity/campaign-briefs` (self-service — capability/permission boundary после advertiser approval, а не отдельный `/api/self/*` namespace);
- **Required/UNVERIFIED shorthand:** `/api/channels`, `/api/device-types`, `/api/capabilities`, `/api/device-capabilities`, `/api/surfaces`;
- **Required/UNVERIFIED shorthand:** `/api/devices`, `/api/carriers`, `/api/carriers/{id}`, `/api/carriers/bulk-actions`, `/api/surfaces/{id}/status`;
- `/api/v1/identity/licenses/report` (фактический Layer 1 read-only report; shorthand `/licenses/report` в registry), proposed Layer 2 `/api/v1/identity/licenses` и `/api/v1/identity/licenses/upload` только после owner/security gate; `/api/v1/device/onboard` (canonical atomic device identity + seat reservation hook; `/device/onboard` — compatibility alias с теми же checks/deprecation);
- **Фактические:** `/api/v1/identity/campaigns`, `/api/v1/identity/campaigns/{id}/request-approval`, `/api/v1/identity/campaigns/{id}/approve`, `/api/v1/identity/campaigns/{id}/reject`, `/api/v1/identity/campaigns/{id}/activate`, `/api/v1/identity/campaigns/{id}/pause`, `/api/v1/identity/campaigns/{id}/complete`, `/api/v1/identity/campaigns/{id}/flights`, `/api/v1/identity/campaigns/{id}/placements`, `/api/v1/identity/campaigns/{id}/inventory-reservations` (logical `/submit`/top-level placement aliases не считаются реализованными),
  фактические `/api/v1/identity/inventory/stores`, `/api/v1/identity/inventory/surfaces`, `/api/v1/identity/inventory/availability`, `/api/v1/identity/inventory/conflicts/check`, `/api/v1/identity/inventory/simulate`, `/api/v1/identity/inventory/rules`, `/api/v1/identity/inventory/rules/{id}/activate`, `/api/v1/identity/inventory/rules/{id}/deactivate`; forecast и общий approvals endpoint — `required/UNVERIFIED`, пока их нет в generated OpenAPI;
- **Фактические:** `/api/v1/identity/commerce/tariff-versions`, `/api/v1/identity/commerce/price-items`, `/api/v1/identity/commerce/quote`, `/api/v1/identity/commerce/orders`, `/api/v1/identity/commerce/orders/{id}`; требуемые `offer/booking/payment-status/close` — logical transitions `REQ-BIZ-014`, для них отдельные versioned endpoints проектируются после owner/API gate и не считаются реализованными;
- **Фактические:** `/api/v1/identity/creative-assets`, `/api/v1/identity/creative-assets/{id}/upload-intent`, `/api/v1/identity/creative-assets/{id}/complete-upload`, `/api/v1/identity/creative-assets/{id}/approve`, `/api/v1/identity/creative-assets/{id}/reject`, `/api/v1/identity/creative-assets/moderation-queue`; logical media/rendition/moderation capabilities use these canonical routes, а отдельный `/api/media` namespace не создаётся без owner-approved versioned alias;
- **Required/UNVERIFIED shorthand:** `/api/manifests`, `/api/rollouts`, `/api/rollback`;
- Device Gateway implemented: `GET /api/v1/device/manifest/latest`, `POST /api/v1/device/heartbeat`; proposed runtime contracts: `/api/v1/device/register`, `/api/v1/device/events/batch`, `/api/v1/device/capabilities` (точные methods/schema/owner/deprecation фиксируются до production gate);
- **Фактический:** `/api/v1/pop/batch` (канонический PoP endpoint по ADR-017; duplicate semantics имеют открытое расхождение §13);

**Required/UNVERIFIED legacy aliases** из v2.5 — `/device/register`, `/device/heartbeat`, `/device/manifest` и
`/device/capabilities`; они не являются отдельными контрактами, проходят через тот же
auth/scope/dedupe слой и имеют обязательные owner, deprecation date и migration tests.
- Proposed vendor/player capability surfaces: `/api/v1/identity/integrations/esl`, `/api/v1/identity/integrations/led`, `/api/v1/identity/player-builds`, `/api/v1/identity/player-rollouts`; в текущем коде эти routes не реализованы и не считаются implemented до adapter/vendor owner gate, OpenAPI и contract evidence;
- `/api/v1/identity/campaigns/{id}/pop/summary`, `/api/v1/identity/campaigns/{id}/pop/by-day`, `/api/v1/identity/campaigns/{id}/pop/by-surface`, `/api/v1/identity/campaigns/{id}/pop/export` (фактический reporting route set); `/api/v1/identity/emergency/status`, `/api/v1/identity/emergency/activate`, `/api/v1/identity/emergency/deactivate` (фактический emergency route set); analytics dashboard, network views, stop/message/resume и общий export — logical capabilities, не отдельные implemented paths без owner/API gate; `/api/v1/identity/audit-events` (фактический audit read route);
- V26 proposed contracts: `/api/v1/attribution/sales-reference`, `/api/v1/attribution/campaigns/{id}/window`, `/api/v1/attribution/campaigns/{id}/control-groups`, `/api/v1/attribution/campaigns/{id}/lift-report`; `/api/v1/identity/advertiser-self-service/settings` и `/api/v1/identity/advertiser-self-service/limits`; `/api/v1/competitive-separation/rules`; `/api/v1/stores/audience-attributes`; `/api/v1/finance/exchange-batches`; `/api/v1/dynamic-content/bindings`; `/api/v1/field-ops/devices/{id}/confirmations` и `/api/v1/field-ops/incidents`; `/api/v1/external-measurement/exports`. Эти пути — логические proposed endpoints: до owner/API gate, OpenAPI, RBAC/RLS, idempotency, errors, audit и behavioral evidence они не являются реализованным API.
- **Required/UNVERIFIED events:** `publish.requested`, `manifest.generated`, `channel.task.created`,
  `delivery.attempted`, `device.apply.ack`, `proof.received`, `rollout.paused`.

События имеют `event_id`, `trace_id`, `occurred_at_utc`, `schema_version`, producer,
subject/scope, signature state, dedupe key и retention class.

Для PoP есть расхождение источников: исходный v2.5 называет `/device/pop/batch`, а
ADR-017 канонизирует `POST /api/v1/pop/batch`. В новой редакции каноничен ADR-017;
старый путь допускается только как явно версионированный compatibility alias с owner,
сроком deprecation, одинаковыми security/dedupe правилами и отдельным migration test.

## 27. Definition of Done для требования

Требование считается закрытым только если:

1. утверждены формулировка, scope, owner и зависимые решения;
2. есть реализация или документированное approved deferred;
3. есть positive и negative proof соответствующего уровня;
4. journey имеет реальный UI-smoke и human walkthrough, если требование пользовательское;
5. данные/события имеют схему и миграцию;
6. CI проверяет invariant и tamper/rollback-кейс;
7. результат отражён в Git и, если затрагивает продуктовую функцию, в roadmap, registry и
   generated views;
8. расхождение с внешним monitoring-dashboard фиксируется как наблюдение и не используется
   для повышения канонического статуса.

## 28. Проверка полноты новой редакции

Перед публикацией v2.6 выполняется независимый review:

- посчитать все `REQ-ID`, ссылки на §1–25 v2.5 и orphan/duplicate;
- сравнить каталог с ERD, API, ADR, кодом, тестами, стендом и roadmap;
- проверить, что каждая `MUST` имеет задачу или approved decision;
- проверить, что каждая `SHOULD/MAY` имеет явно принятую диспозицию;
- проверить сбалансированность fenced-блоков, колонки Markdown-таблиц и разбор всех YAML-примеров;
- сверить metadata revision, максимальный AC-ID и итоговую строку саморевью;
- прогнать negative/edge-case matrix и сверить с внешним monitoring-dashboard;
- получить отдельные ACCEPT владельца, Claude Code и Codex;
- только затем пометить документ `APPROVED` и сделать его новым источником истины.

## 29. Реестр решений владельца (decision register)

Каждое решение имеет `DEC-ID`, options, выбранный вариант, rationale, owner, approver,
`decided_on`, affected REQ-ID, affected code/data/API, rollback и `review_on`. Минимальный реестр:

| DEC-ID | Вопрос | Нельзя оставить без решения |
|---|---|---|
| DEC-001 | Каналы первой production-очереди и владелец каждого | scope, adapter, SLA, budget |
| DEC-002 | Когда вводится Orchestrator и Adapter Layer | закрыто ADR-019: только после появления второго реального канала; mock-first до trigger запрещён |
| DEC-003 | Профиль подписи по dev/pilot/prod | Ed25519/HMAC, rotation/revoke |
| DEC-004 | Operational contract очереди | NATS JetStream — baseline по ADR-002; delivery, retry, DLQ, persistence, lag и migration path должны быть раскрыты, а замена брокера требует ADR amendment и owner approval |
| DEC-005 | Master-система цен/SKU и owner reconciliation | ESL/price checker safety |
| DEC-006 | SLA methodology, impression/reach и compensation policy | SLA targets приняты; открыты measurement и non-cash make-good rules |
| DEC-007 | Retention/152-ФЗ/legal report status | рабочие retention defaults приняты; открыты legal approval, исключения и deletion/archive process |
| DEC-008 | Rollout thresholds и feature-flag authority | stop/rollback responsibility |
| DEC-009 | 40K load profile и production capacity gate | performance budget |
| DEC-010 | Exit criteria принятой пилотной шкалы | шкала KSO→10→100→500→network уже принята; нужны измеримые переходные гейты |
| DEC-011 | Объём self-service первого пилота | закрыто OD-005: managed-first; post-pilot self-service остаётся отдельным roadmap scope |
| DEC-012 | RTO/RPO/HA target и DR ownership | production go/no-go |
| DEC-013 | Advertiser API access | scoped API keys, rotation/revoke/audit либо явное исключение из первой очереди |
| DEC-014 | Внешний monitoring-dashboard как read-only наблюдатель | freshness/correlation contract, расхождения и запрет записи статусов |
| DEC-015 | Production deployment topology: Swarm или approved equivalent | владелец, критерии HA/rollback, стоимость эксплуатации и migration evidence |
| DEC-016 | Device PKI/mTLS activation и срок отказа от token-only flow | owner/security approval, PKI/CRL/OCSP, proxy enforcement, migration и rollback |
| DEC-017 | Полный ЭДО/биллинг вне первой очереди | owner/legal decision, границы сущностей, trigger возврата |
| DEC-018 | DSP/SSP-закупка вне первой очереди | product/legal decision, ручное согласование и review date |
| DEC-019 | Персонализация покупателя вне первой очереди | privacy/legal decision, lawful purpose и review trigger |
| DEC-020 | Звук в торговом зале вне первой очереди | business/operations safety decision и review date |
| DEC-021 | Произвольный HTML/JS вне первой очереди | security decision, sandbox/CSP policy и activation gate |
| DEC-022 | Additive exceptions v2.6 | **approved OD-018 (2026-08-28):** разрешено только исключение §3.1 delivery/priority engine (competitive separation); любые другие изменения Campaign/Delivery/PoP требуют нового owner decision |
| DEC-023 | Миграция role bundles | product role model уже принят Q2; определить additive создание отсутствующих `campaign_manager/moderator/approver/ops_operator`, migration/alias `operator` и сохранение permission-code authorization |
| DEC-024 | Duplicate PoP внутри batch | **approved OD-019 (2026-08-28):** валидный batch отвечает HTTP 200; duplicate получает per-event `duplicate` и machine error code 409 в теле, повторно не учитывается; ADR-017 amendment и behavioral evidence обязательны |
| DEC-025 | Campaign lifecycle conformance | закрыто ADR-015: реализовать полный accepted lifecycle, включая `scheduled`, resume, revise и archive; иной вариант требует amendment ADR-015 |
| DEC-026 | Отмена commerce order | **approved OD-020 (2026-08-28):** `draft → cancelled` разрешён; `confirmed` закрывается только reversal/compensation workflow, прямая отмена запрещена; код и тесты приводятся к этому контракту |
| DEC-027 | A/B attribution scope и sequencing | OD-014: после attribution prerequisites; winner metric/methodology и milestone требуют owner decision |

Неразрешённый DEC блокирует связанные REQ-ID и не превращается в «planned» без владельца.

Формат записи решения:

Ниже приведён только шаблон: значения `...` и `YYYY-MM-DD` не являются evidence и не
могут попасть в запись со статусом `approved` или разблокировать связанное требование.

```yaml
id: DEC-001
question: "Какие каналы входят в архитектурный baseline и pilot?"
options: ["..."]
selected: "..."
rationale: "..."
owner: "..."
approver: "..."
decided_on: "YYYY-MM-DD"
affected_req_ids: [REQ-CHAN-001, REQ-ORCH-001]
affected_tasks: []
risks: ["..."]
rollback_or_review_trigger: "..."
review_on: "YYYY-MM-DD"
status: proposed
evidence_refs: []
```

`selected`, `owner`, `approver`, `decided_on`, `affected_req_ids`, `review_on` и
`evidence_refs` обязательны для `approved`. Решение без затронутых REQ-ID, даты или
evidence считается незавершённым и не может разблокировать задачу.

## 30. Сеть, поставка и окружения

ТЗ обязано различать local DEV, shared DEV, pilot и production: host, DNS/TLS, schema,
secret source, data class, deployment owner, доступ, backup, monitoring и rollback.
Deployment path фиксирован: local Docker Compose → pilot на одном host с restore drill →
test store с минимум двумя backend/Device Gateway за reverse proxy → production на
нескольких host или approved equivalent с HA. Переход между контурами требует owner gate,
immutable artifact/SHA и отдельного rollback evidence.
Описываются сегменты и firewall между Admin/Advertiser/Operations, Control Plane,
Device/Channel Gateway, stores, vendor gateways, PostgreSQL, ClickHouse, MinIO, Redis и
queue. Запрещаются плоская L2-сеть, доступ устройств к admin API и секреты в URL.

Каждая поставка имеет immutable artifact/SHA, migration rehearsal, health/readiness,
smoke, approval, rollback и журнал изменений. Версия, реально работающая на стенде,
не считается production evidence без зафиксированного host/schema/SHA.

Минимальный manifest каждого окружения хранится отдельно и не содержит секретов:

```yaml
environment: shared-dev
base_url: "https://dev.example.invalid"
host: "назначается"
ports: {portal: 0, api: 0, gateway: 0}
git_sha: "назначается"
db_schema_revision: "назначается"
seed_profile: "назначается"
reset_command_ref: "runbook-or-command-id"
monitoring_ref: "dashboard-or-query-id"
secret_source_ref: "vault-path-or-owner-record"
last_verified_at: "YYYY-MM-DDThh:mm:ssZ"
owner: "назначается"
```

`base_url`, `git_sha`, schema revision и `last_verified_at` обязательны для `verification`;
credentials, tokens и пароли в manifest запрещены. Внутренний адрес стенда должен быть
проверен оператором без раскрытия секретов.

## 31. Бизнес-метрики и качество услуги

Нужно разделить технические и бизнесовые KPI:

- технические: availability, heartbeat freshness, manifest delivery/apply latency, PoP
  lag, error rate, queue lag, cache health, storage, rollout failure;
- рекламные: planned/actual playback, fill rate, underdelivery, reach estimate, SLA,
  compensation, inventory utilisation, campaign completion;
- операционные: incident MTTA/MTTR, offline stores, degraded channels, rollback rate;
- финансовые: booked capacity, tariff version, planned value, paid/bonus/compensation
  inventory — только после решения владельца и источника данных.

Для каждой метрики задаются формула, источник, grain, TZ, aggregation, freshness,
retention, owner, dashboard, alert threshold и запрет на смешение estimate с fact.

## 32. Доступность, приватность и юридические ограничения

ТЗ фиксирует классы данных (public/internal/confidential/PII), lawful purpose, minimised
fields, residency, encryption, access review, export/delete request, incident notification
и retention. Рабочие owner-approved defaults: PoP hot 12–18 месяцев, архив PoP и итоговых
отчётов 3–5 лет, audit не менее 3 лет, технические логи 90–180 дней, креативы завершённых
кампаний 1–3 года. Это нормативные интервалы хранения, а не варианты технологии;
`DEC-007` утверждает legal/152-ФЗ исключения и финальную retention matrix. Каждая выгрузка
проверяет scope/permission, журналируется и ограничивается
периодом и объёмом; данные рекламодателей изолированы в доступе и отчётности. Юрист/ИБ отдельно утверждают 152-ФЗ, юридический статус PDF, audit immutability,
vendor processing и правила чековых данных.

Accessibility включает keyboard navigation, focus, contrast, labels, screen-reader,
responsive breakpoints, reduced motion, locale/date/number formats и error recovery.
Для каждой роли определяются запрещённые действия и видимые последствия bulk-operation.

## 33. Договоры владения и эксплуатационная ответственность

Для каждого domain/API/table/dashboard/runbook назначаются Business Owner, Product Owner,
Tech Owner, Security Owner, Operations Owner и Data Steward. Указываются on-call, часы
поддержки, escalation, change approval, incident commander и кто имеет право переводить
статус в `done`.

География первой редакции — вся Россия; все branch/store/device/report правила обязаны
учитывать локальную TZ и сетевую нестабильность. Внешний monitoring-dashboard может показывать рассинхрон и ссылаться на evidence, но не
может изменять канонический status. Источник статуса всегда содержит SHA/дату/доказательство.

## 34. Минимальный комплект приложений к ТЗ v2.6

Финальная редакция не должна быть одним монолитным файлом. К ней прилагаются:

1. `requirements-traceability.yaml` — полный атомарный каталог и disposition;
2. `domain-model.md`/ERD — сущности и связи;
3. `api-contracts/` — OpenAPI и event schemas;
4. `manifest.schema.json`, `proof.schema.json` и adapter contracts;
5. `role-scope-matrix.yaml` и `portal-route-matrix.yaml`;
6. `journeys/` — user stories, Given/When/Then, Happy-path и negative paths;
7. `scenarios/` — технические/операционные/security сценарии `SC-*` для REQ без user story;
8. `nfr-slo.yaml`, `load-profiles.yaml`, `retention-policy.yaml`;
9. `environment-and-deployment.md`, `backup-drill.md`, `incident-runbooks/`;
10. `decision-register.yaml` и changelog;
11. acceptance/evidence matrix, связанная с roadmap и CI.
12. `appendix-index.md` — ID, заголовок и стабильный anchor каждого приложения; индекс обновляется атомарно при добавлении/перемещении приложения.

Без этих приложений новая редакция останется описательной и снова не обеспечит полного
покрытия ТЗ задачами.

## 35. Базовые portal journeys (первый UX-контур)

### J-PORTAL-CAMPAIGN — менеджер

`Happy-path: 12 шагов` — `Login → Dashboard → Campaigns → Create → advertiser/order → period/goal/budget →
channels/surfaces → creatives/renditions → Simulate inventory → resolve conflicts →
Submit moderation → status/next action`.

Нельзя перейти к публикации без approved creative, placement, scope и согласований.

### J-PORTAL-APPROVAL — согласующий

`Happy-path: 8 шагов` — `Login → Approvals → filter by scope → open campaign → compare versions → inspect
affected stores/channels/surfaces → approve/reject with reason → audit confirmation`.

Кнопка действия показывает последствия, а отсутствие permission даёт 403 без утечки данных.

### J-PORTAL-OPS — оператор

`Happy-path: 8 шагов` — `Login → Operations → network/store/channel/device → health/manifest/PoP/errors →
diagnostics → safe command → progress → result/rollback`.

Массовая команда требует подтверждения, лимита batch, staged rollout и audit.

### J-PORTAL-ADVERTISER — рекламодатель

`Happy-path: 7 шагов` — `Login → My campaigns → campaign → plan/fact → exclusions/reasons → geography/time
filter → PDF/XLSX/CSV export`.

Видны только собственные данные; technical payload, secrets и внутренние IDs скрыты.

### J-PORTAL-EMERGENCY — emergency operator

`Happy-path: 9 шагов` — `Login + MFA → Emergency → choose scope → reason → preview impact → confirm →
delivery progress → apply/error summary → resume normal manifest`.

Действие имеет более высокий приоритет, но не может обходить permission, audit и rollback.

Каждый journey получает стабильные `data-testid`, UI-smoke с реальными кликами,
operator walkthrough и ссылку на REQ-ID. Deep-link в середину journey запрещён.

## 36. Контрольная карта разделов исходного ТЗ

Проверка полноты выполняется по разделам, а не по ключевым словам. Каждая строка должна
иметь хотя бы один атомарный REQ-ID и один из исходов `task / approved-decision /
explicit-exclusion`; пустой исход — блокирующая ошибка.

Нумерация разделов этой редакции внутренняя и не совпадает с нумерацией v2.5.
В machine-поле `source` и при ссылке именно на исходный документ используется вид
`TZ v2.5 §N[.M]`. Голое `§N` в нормативной прозе означает внутренний раздел этой редакции;
его запрещено трактовать как ссылку на v2.5. Это предотвращает смешение, например,
внутреннего §22 с исходным production-best-practices §22.

| Источник v2.5 | В новой редакции | Обязательное приложение/доказательство |
|---|---|---|
| §1 Общие положения | REQ-SCOPE-001, REQ-BIZ-013, REQ-NFR-004, REQ-ARCH-002 | version/changelog/approval + business outcome KPI + scale baseline + independence |
| §2 Scope и принципы | REQ-SCOPE-001, REQ-CHAN-001, REQ-CHAN-002, REQ-CHAN-003, REQ-LIC-001 | scope matrix + decision register |
| §3 Сценарии и масштаб | REQ-BIZ-001, REQ-BIZ-003, REQ-BIZ-006, REQ-NFR-001, REQ-NFR-002, REQ-NFR-004 | load profiles + journey matrix |
| §4 Архитектура/стек/сеть | REQ-ARCH-001, REQ-ARCH-002, REQ-ARCH-003, REQ-ARCH-004, REQ-CORE-001, REQ-CORE-002, REQ-API-002, REQ-SEC-001, REQ-SEC-002, REQ-SEC-003, REQ-SEC-004, REQ-SEC-005, REQ-OPS-001, REQ-OPS-004 | domain/ERD + network/deploy design |
| §5 NFR | REQ-NFR-001, REQ-NFR-003, REQ-NFR-004, REQ-NFR-005, REQ-NFR-006, REQ-NFR-007, REQ-OPS-003, REQ-OPS-004 | SLO/load/DR evidence |
| §6 Роли/кампании/инвентарь | REQ-BIZ-001, REQ-BIZ-003, REQ-BIZ-005, REQ-BIZ-006, REQ-BIZ-007, REQ-BIZ-008, REQ-BIZ-010, REQ-BIZ-013, REQ-BIZ-015, REQ-BIZ-016, REQ-CORE-003, REQ-UX-001, REQ-SEC-002, REQ-SEC-009 | role matrix + formulas + onboarding/workflow/inventory-rule/underdelivery policy + outcome KPI + journeys |
| §7 Медиатека/QA | REQ-CONT-001, REQ-CONT-002 | format/rendition/security tests |
| §8 Manifest/playlists | REQ-MAN-001, REQ-MAN-002, REQ-MAN-004, REQ-MAN-005, REQ-ORCH-001, REQ-ORCH-002, REQ-ORCH-003, REQ-ORCH-004 | JSON Schema + inheritance/override/field/ACK compatibility tests |
| §9 Runtime/fallback | REQ-CHAN-002, REQ-MAN-003, REQ-OPS-001, REQ-OPS-002, REQ-OPS-008 | adapter contract + cache/offline/chaos tests |
| §10 Devices | REQ-CHAN-001, REQ-CHAN-002, REQ-CHAN-003, REQ-LIC-001, REQ-OPS-001, REQ-OPS-009 | command/status/heartbeat model + negative tests |
| §11 PoP | REQ-POP-001, REQ-POP-002, REQ-POP-003, REQ-POP-004, REQ-API-003 | proof schema + dedupe/signature tests |
| §12 Reports | REQ-BIZ-001, REQ-BIZ-002, REQ-BIZ-004, REQ-BIZ-008, REQ-BIZ-009, REQ-BIZ-010, REQ-BIZ-011, REQ-BIZ-014, REQ-BIZ-015, REQ-POP-001, REQ-UX-001 | six report/dashboard views + commerce/onboarding/plan/fact/channel-quality/underdelivery/financial/closure evidence |
| §13 Emergency | REQ-OPS-001, REQ-OPS-002, REQ-OPS-007, REQ-SEC-004 | priority/rollback/progress/audit proof |
| §14 Security | REQ-SEC-001, REQ-SEC-002, REQ-SEC-003, REQ-SEC-004, REQ-SEC-005, REQ-SEC-006, REQ-SEC-007, REQ-SEC-008, REQ-SEC-009 | threat model + segmentation/reachability/security-negative matrix |
| §15 Data model | REQ-DATA-001, REQ-DATA-002, REQ-CHAN-001, REQ-CHAN-002, REQ-CHAN-003, REQ-LIC-001 | complete entity inventory + ERD/data dictionary/migrations |
| §16 API/integrations | REQ-API-001, REQ-API-002, REQ-API-003, REQ-INT-001, REQ-INT-002, REQ-INT-003, REQ-LIC-001, REQ-BIZ-014 | OpenAPI/events/vendor contracts |
| §17 HA/backup/ops | REQ-OPS-003, REQ-OPS-004, REQ-OPS-005, REQ-OPS-006, REQ-OPS-009, REQ-NFR-004, REQ-NFR-005 | restore/DR/monitoring/heartbeat drill |
| §18 Implementation plan | REQ-GOV-001, REQ-GOV-002, REQ-GOV-003, REQ-STAND-001, REQ-STAND-002, REQ-STAND-003 | roadmap stages/dependencies/gates + registry/roadmap reconciliation + stand plan + real-KSO feasibility evidence |
| §19 Acceptance | REQ-GOV-001, REQ-GOV-002, REQ-GOV-003 | evidence matrix + release gate + registry/roadmap reconciliation |
| §20 Risks/prechecks | REQ-GOV-001, REQ-NFR-001, REQ-NFR-003 | risk register with owner/mitigation |
| §21 Agent instructions | REQ-GOV-001, REQ-ARCH-002 | separate process policy, no runtime LLM dependency |
| §22 Best practices | REQ-BIZ-001, REQ-BIZ-002, REQ-BIZ-003, REQ-BIZ-004, REQ-BIZ-005, REQ-BIZ-006, REQ-BIZ-007, REQ-BIZ-008, REQ-BIZ-009, REQ-BIZ-010, REQ-BIZ-011, REQ-BIZ-012, REQ-BIZ-013, REQ-BIZ-014, REQ-BIZ-015, REQ-BIZ-016, REQ-CONT-001, REQ-CONT-002, REQ-OPS-001, REQ-OPS-002, REQ-OPS-003, REQ-OPS-004, REQ-OPS-005, REQ-OPS-007, REQ-OPS-008, REQ-OPS-009, REQ-UX-001, REQ-UX-002, REQ-UX-003, REQ-UX-004, REQ-NFR-005, REQ-NFR-006, REQ-SEC-005, REQ-STAND-002, REQ-LIC-001 | atomic IDs by subsection |
| §23 Multichannel | REQ-CHAN-001, REQ-CHAN-002, REQ-CHAN-003, REQ-CORE-003, REQ-MAN-003, REQ-ORCH-001, REQ-ORCH-002, REQ-ORCH-003, REQ-ORCH-004, REQ-ORCH-005, REQ-ORCH-006, REQ-POP-001, REQ-POP-002, REQ-POP-003, REQ-POP-004 | adapter/channel matrix + contracts |
| §24 Architecture v2.5 | REQ-ARCH-001, REQ-ARCH-002, REQ-ARCH-003, REQ-ARCH-004, REQ-CORE-001, REQ-CORE-002, REQ-CORE-003, REQ-BIZ-005, REQ-BIZ-006, REQ-ORCH-001, REQ-ORCH-002, REQ-ORCH-003, REQ-ORCH-004, REQ-ORCH-005, REQ-ORCH-006, REQ-MAN-001, REQ-MAN-002, REQ-MAN-003, REQ-MAN-004, REQ-POP-004, REQ-API-001, REQ-API-002, REQ-API-003 | ADR alignment + architecture acceptance |
| §25 Pre-development checklist | REQ-GOV-001, REQ-GOV-002 | all checkboxes resolved and signed; registry/REQ/story/journey sets equal or dispositioned |

В этой section map REQ-ID являются ссылками на каталог, а не повторными определениями.
Проверка уникальности определений выполняется только по таблице каталога требований (раздел
25); reference rows, story/journey maps и acceptance register не увеличивают число
определений. Повтор ID в этих производных таблицах допустим только при точном совпадении с
каноническим определением.

## 37. Формат атомарного требования

```yaml
id: REQ-CHAN-001
source: "TZ v2.5 §23.1, §24.1"
normative: MUST
statement: "Ядро кампаний не зависит от конкретного канала"
scope: [pilot, production]
coverage_type: technical
owner: TBD
roadmap_ids: []
requirement_status: proposed
delivery_status: planned
status_changed_at: "2026-08-26T00:00:00Z"
status_actor: "draft-owner"
implementation_owner: TBD
dependencies: [DEC-001, DEC-002]
story_ids: []
scenario_ids: [SC-ARCH-001]
journey_ids: [campaign.create]
artifacts: [domain-model, api-contracts, adapter-contracts]
acceptance:
  - given: "добавлен новый adapter"
    when: "создано размещение"
    then: "campaign tables/API не изменились"
evidence: [contract_test, behavioral_test, ci_run]
disposition: task
```

`TBD` допускается только в draft и автоматически блокирует `APPROVED`. Поля `source`,
`normative`, `owner`, `roadmap_ids`, `requirement_status`, `delivery_status`, `status_changed_at`,
`status_actor`, `implementation_owner`,
`disposition` и `acceptance` обязательны; отсутствие любого поля
означает, что требование не готово к переносу в roadmap.
`requirement_status` отражает зрелость и судьбу формулировки (`proposed`, `approved`,
`rejected` или `superseded`), а
`delivery_status` — только ход реализации (`planned`, `in_progress`, `verification`, `done`,
`blocked` или `deferred`). Эти поля независимы: `delivery_status: done` недействителен при
`requirement_status: proposed`, а `requirement_status: approved` не означает наличие
реализации. Произвольная строка, пустое значение или значение с несколькими статусами
недействительны.

`coverage_type=business` требует непустые `story_ids` и `journey_ids`. Для
`coverage_type=technical|security|operational|governance` обязательна непустая ссылка
`scenario_ids` на технический/операционный сценарий с owner и evidence; user story и
journey для таких требований могут быть дополнительными. Реестр `SC-*` проверяется теми
же правилами уникальности, source/owner/acceptance/evidence и связывается с roadmap task.

Пример `SC-ARCH-001` в шаблоне является минимальным canonical scenario: «добавлен новый
channel adapter без изменения campaign core; проверены import boundary, contract и
regression». В реестре сценариев он должен получить тот же source/owner/evidence, что и
связанное REQ; illustrative example нельзя переносить в roadmap как выполненную задачу.

## 38. Правила источников и версий ТЗ

Языковая политика финального комплекта: нормативная деловая проза и критерии приёмки —
на русском; стабильные ID, backend permission codes, API/event/schema identifiers и
термины протоколов сохраняются в исходном техническом написании. Доля латиницы сама по
себе не является критерием качества или блокером утверждения.

Исходные DOCX сохраняются только для истории; рабочими текстами являются проверенные
`.extracted.md` для v2.5 и отдельный extracted-текст для v2.6 Next Branch с зафиксированными
SHA и датой извлечения. При новой редакции запрещено
молча переписывать историю: публикуются diff, changelog, список затронутых REQ-ID и
обратная совместимость. Если новый ADR противоречит ТЗ, конфликт получает DEC-ID и
останавливает перенос в задачу до решения владельца.
## Дополнение F. Проверка полноты исходного текста

Перед выпуском v2.6 выполняется механическая сверка каждого исходного DOCX и соответствующего
extracted-текста: число
paragraphs/tables, заголовки, таблицы и нормативные предложения сопоставляются по SHA и
дате извлечения. Каждое предложение с `должен/нельзя/обязательно/необходимо/требуется`
классифицируется как `REQ`, `DEC`, `EXCLUSION` или `PROCESS`; неклассифицированное
предложение блокирует релиз.

Проверяются дубликаты требований, конфликтующие значения KPI, единицы измерения, ссылки
на несуществующие сущности/endpoint, устаревшие ADR и расхождение терминов между ТЗ, ERD,
OpenAPI, registry, roadmap и portal journeys.

## Дополнение G. Критерии бизнес-успеха

Успех измеряется результатами: менеджер создаёт и согласует кампанию с прогнозом;
публикация достигает целевых surfaces через adapters; advertiser получает план/факт и
причины отклонений; оператор безопасно управляет rollout; emergency действует в SLA без
нарушения кассовых/ценовых процессов; новый канал подключается без переписывания core;
критичные действия имеют неизменяемый audit и воспроизводимый evidence.

Для каждого результата задаются baseline, target, measurement window, owner и дата
пересмотра. «Система доступна» или «функция реализована» без измеримого результата не
является бизнес-критерием.

## Дополнение H. Правило изменения scope

Добавление или удаление канала, роли, финансовой сущности, источника данных, NFR либо
security control требует DEC-ID, impact analysis по REQ/API/ERD/UX/roadmap, оценки
миграции и обратной совместимости. Нельзя закрыть gap переносом требования в «не входит»
без утверждённого owner decision и обновлённой матрицы трассировки.

## Дополнение I. Связь decision register с текущим governance

Новая редакция не создаёт второй независимый реестр решений. Каждый `DEC-ID` обязан иметь
ссылку на существующий `OD-*`, ADR или новый owner decision в `roadmap.yaml`:

| DEC-ID | Текущий источник для сверки | Статус до v2.6 |
|---|---|---|
| DEC-001 | OD-021, ADR-019 + перечень каналов §23/25 | scope/владельцы не завершены |
| DEC-002 | OD-022, ADR-019 | **approved**: Orchestrator/Adapter Layer/mock только после второго реального канала |
| DEC-003 | OD-002, RM-STAB-010 | **approved**: Ed25519 pilot/prod, HMAC только dev/control-plane stand; implementation evidence отдельно |
| DEC-004 | ADR-002 + OD-008 | NATS JetStream baseline принят; открыты только детальные persistence/ops thresholds и evidence |
| DEC-005 | OD-023, §16.2, §23.7 | master price/SKU owner не зафиксирован |
| DEC-006 | product decision §5.1 + OD-009 | SLA targets approved; methodology/compensation/legal часть открыта |
| DEC-007 | product decision §5.1 + OD-009 | retention defaults approved; 152-ФЗ/legal exceptions открыты |
| DEC-008 | OD-010, §22.7/22.9 | staged rollout/flags открыты |
| DEC-009 | OD-011, §22.15 | load/capacity gate открыт |
| DEC-010 | OD-024, product decision §5.1, RM-PILOT-* | шкала approved; измеримые exit criteria открыты |
| DEC-011 | OD-005, OD-013 | первый pilot managed-first approved; post-pilot self-service scope открыт |
| DEC-012 | OD-025, §5/§17, RM-OPS-001 | HA/DR ownership и target не закрыты |
| DEC-013 | OD-026, §12/§16, REQ-INT-003 | advertiser/BI API access, scope, key rotation и audit не закрыты |
| DEC-014 | OD-027, §R, REQ-ARCH-002 | предложенная read-only/non-authoritative boundary; **owner decision требуется** — `OD-027` open: scope, freshness/correlation contract, оформление расхождений (MON-DIVERGENCE) и запрет записи статусов |
| DEC-015 | OD-028, REQ-ARCH-004 | production deployment topology и HA/rollback критерии не закрыты |
| DEC-016 | OD-029, REQ-SEC-003 | device PKI/mTLS activation, migration и rollback не закрыты |
| DEC-017 | OD-030, §2.2, §22.12 | полный ЭДО/биллинг исключён до owner/legal решения |
| DEC-018 | OD-031, §2.2 | DSP/SSP-закупка исключена до product/legal решения |
| DEC-019 | OD-032, §2.2, §14 | персонализация покупателя исключена до privacy/legal решения |
| DEC-020 | OD-033, §2.2, §9 | звук исключён до business/operations safety решения |
| DEC-021 | OD-034, product decision §5.1, §2.2, §7 | запрет в первой очереди approved; future activation требует security gate |
| DEC-022 | OD-018, v2.6 addendum §0.3/§8.3 | approved: только §3.1 delivery/priority engine; остальные additive exceptions запрещены без нового решения |
| DEC-023 | OD-035, product decision Q2, REQ-UX-001 | role/persona target approved; migration `operator` и отсутствующих bundles открыта |
| DEC-024 | OD-019, ADR-017 | approved: HTTP 200 batch + per-event `duplicate`/409; требуется amendment ADR-017 и implementation evidence |
| DEC-025 | OD-036, ADR-015 | **approved** lifecycle; текущий код не соответствует и требует implementation task |
| DEC-026 | OD-020, commerce lifecycle | approved: draft cancellation; confirmed только reversal/compensation; implementation evidence требуется |
| DEC-027 | OD-014, REQ-V26-002/010 | A/B/lift sequencing и winner methodology открыты |
При конфликте приоритет остаётся за утверждённым ADR и owner decision согласно
`AGENTS.md`. Строка с несовпадающим статусом должна помечаться `CONFLICT`, а не
автоматически переводиться в `deferred`.

## Дополнение J. Детальная карта §22

| Источник | Что обязательно перенести в v2.6 |
|---|---|
| §22.1 | placement lifecycle, ответственные, сроки и transition criteria |
| §22.2 | SLA качества услуги и измерение по ролям |
| §22.3 | underdelivery taxonomy, make-good, компенсации |
| §22.4 | priority, preemption, simulation, overbooking |
| §22.5 | Creative QA, rendition policy, HTML5 security |
| §22.6 | operations center, device/channel/surface health |
| §22.7 | rollout stages, thresholds, pause и rollback |
| §22.8 | immutable versions, diff, historical reproducibility |
| §22.9 | feature flags, scope, audit и fast rollback |
| §22.10 | logs, metrics, traces, alerts и четыре типа dashboard |
| §22.11 | data ownership, PII, hot/archive/technical retention |
| §22.12 | order, tariff, price list, discount, bonus/compensation, payment status |
| §22.13 | role-specific UX и последствия действий |
| §22.14 | safe seed, объёмы и сценарии demo stand |
| §22.15 | load profiles для devices, publication, analytics и users |
| §22.16 | mini-design/change protocol для implementation agent |
| §22.17 | UTC/local TZ, DST, holidays, closed stores, exceptions |
| §22.18 | API/manifest versioning, negotiation, compatibility window |
| §22.19 | accessibility, tables, progress, error recovery, advertiser simplicity |

## Дополнение K. Последовательность этапов реализации

Порядок из §18 сохраняется как логическая зависимость, даже если roadmap разбивает его
на меньшие задачи:

`0 feasibility/stand → 1 core/security → 2 hierarchy/channels/devices → 3 content/QA →
4 inventory → 5 campaigns/placements → 6 playlists/manifest → 7 players/adapters →
8 PoP ingestion (PostgreSQL Phase 1; ClickHouse deferred by ADR-007) → 9 analytics/reports → 10 emergency/audit → 11 HA/DR/load/pilot`.

Каждый этап имеет входные условия, выходные артефакты, owner, acceptance, evidence и
rollback. Запрещено считать этап закрытым только по наличию кода: должны быть проверены
связанные user stories, безопасность, миграции, наблюдаемость и эксплуатационный runbook.
## Дополнение L. Политика контента и renditions

| Тип | Политика | Проверка перед публикацией |
|---|---|---|
| JPG/PNG | допустимы в профиле поверхности | MIME, размер, разрешение, SHA-256, preview |
| GIF | ограниченно допустимы | вес, длительность, FPS/CPU budget |
| MP4/WebM | после device/profile теста | codec, bitrate, duration, audio policy |
| HTML5/JS | запрещены по умолчанию | approved sandbox/CSP/ИБ review |
| Executable | запрещены | upload и distribution deny |
| ESL | только approved template/integration | SKU/price master validation, label-ack |
| LED | после controller test | colour/brightness/FPS/size/protocol |
| Android interactive | только safe/idle zones | не блокирует price/check workflow |

Один creative может иметь несколько immutable renditions. QA-результат хранит проверяющего,
время, правила, замечания, версию и причину допуска/отказа; rendition без approved QA не
попадает в manifest.

## Дополнение M. Разделение scope по уровням готовности

| Уровень | Обязательное содержание | Допустимый статус |
|---|---|---|
| Архитектурный baseline | channel-neutral core и manifest/proof data schemas; target adapter requirements описаны, но implementation/mock отсутствуют до trigger ADR-019 | MUST как требования; реализация по этапам |
| Control-plane pilot | Admin/Advertiser/Operations, KSO Adapter/runtime, inventory/campaign/approval, PoP, emergency, operator walkthrough | реализуется первым на `.81` |
| Production channel rollout | реальный device/vendor, SLA, load, security, backup, rollback и owner GO по каждому каналу | только после channel-specific gate |
| Deferred/future | новый канал или функция за пределами утверждённой очереди | только с DEC-ID, owner, trigger и review date |

Отсутствие реального Android/ESL/LED устройства не отменяет обязательность его требований
и channel-specific acceptance, но по ADR-019 не разрешает строить adapter/mock заранее.
После появления выбранного второго канала его contract и mock создаются вместе с
extraction design. Отсутствие production rollout не должно помечаться как «не входит в ТЗ».

Для каждой функции в матрице указываются оба измерения: `requirement_status` (зрелость и
судьба архитектурного/продуктового контракта) и `delivery_status` (ход реализации). Отдельное
поле `architecture_status` не вводится; общий статус «готово» нельзя выводить из одного
измерения.

## Дополнение N. Согласованность, конкуренция и доставка

- Каждая команда публикации, emergency, rollout и device command имеет idempotency key;
  повтор не создаёт вторую версию, второе списание ёмкости или второй audit event.
- Изменение campaign/placement/inventory/manifest использует optimistic locking или
  явную блокировку версии; конфликт редактирования виден пользователю и не затирает чужие
  изменения.
- Транзакционная граница Control Plane фиксирует бизнес-решение и outbox event атомарно;
  worker/adapter доставляет событие at-least-once, deduplicates и сообщает результат.
- Состояния `requested/generated/delivered/applied/proof` не склеиваются в один статус;
  eventual consistency имеет допустимую задержку, timeout и reconciliation job.
- Порядок событий проверяется по `occurred_at`, sequence/version и trace; позднее событие
  не может откатить более новую версию без explicit rollback.
- При частичном успехе массовой операции система показывает completed/failed/pending по
  каждому target, не выдаёт aggregate success и позволяет безопасно продолжить/откатить.
- Отчёт строится по snapshot/version, действовавшему во время показа; пересчёт не меняет
  уже опубликованный отчёт без новой версии и audit.

Для каждого asynchronous flow фиксируются producer/consumer, delivery guarantee, retry
policy, DLQ, dedupe key, ordering, timeout, reconciliation и operator action.

## Дополнение O. Самопроверка драфта ТЗ

Перед передачей Claude и владельцу выполняются автоматические проверки:

- каждое определение `REQ-*`, `US-*`, `J-*` и `DEC-*` уникально; повтор разрешён
  только как ссылка на ранее определённое значение;
- все ссылки на ID разрешаются, нет orphan/duplicate definitions;
- все §1–§25 исходного ТЗ присутствуют в section map, включая §22.1–§22.19;
- нет незакрытых Markdown/YAML fences, битых относительных ссылок или literal escape;
- атомарное требование содержит `source`, `normative`, `scope`, `owner`, `requirement_status`,
  `delivery_status`, `acceptance`,
  `evidence` и `disposition`;
- `APPROVED` не допускает `TBD`, `TODO`, неопределённый owner, конфликт без DEC-ID или
  нормативную формулировку без измеримого результата;
- каждая user story имеет journey, permission/scope, positive/negative path и
  соответствующий acceptance layer;
- каждый asynchronous flow имеет producer/consumer, delivery guarantee, retry/DLQ,
  dedupe, ordering и reconciliation;
- generated roadmap/registry статусы не используются как доказательство закрытия
  требования без соответствующего behavioral/UI/CI evidence.

Результат самопроверки сохраняется вместе с SHA драфта и датой; изменение текста без
повторного прогона делает draft `verification`, а не `approved`.

## Дополнение P. Жизненный цикл требования

Статусы требования и задачи разделены во всех документах. Для требования используется
`requirement_status` (`proposed → approved`), для реализации/roadmap-задачи —
`delivery_status` (`planned → in_progress → verification → done`, с переходом в `blocked`
при подтверждённом блокере и обратно после его снятия); дополнительные терминальные/
диспозиционные статусы реализации — `deferred`.

Дополнительные терминальные состояния требования: `rejected` (с причиной владельца) и
`superseded` (с заменяющим REQ-ID). Для `delivery_status: deferred` требуется approved
DEC-ID, trigger, owner и review date. Переход назад разрешён только через changelog и новое evidence; `done` нельзя
понизить молча.

Правила переходов:

- `requirement_status: proposed → approved` требует owner acceptance и разрешённых конфликтов;
- `requirement_status: approved` перед `delivery_status: planned` требует назначенной roadmap task и dependencies;
- `delivery_status: planned → in_progress` требует implementation owner и mini-design;
- `delivery_status: in_progress → verification` требует заявленного acceptance и evidence;
- `delivery_status: verification → done` требует полного evidence соответствующего уровня и CI/owner gate;
- `delivery_status: blocked` требует конкретного blocker ID, owner, причины, зависимостей,
  даты пересмотра и не может маскировать `deferred` или завершённое состояние; выход из
  `blocked` требует evidence снятия blocker и нового status transition;
- `delivery_status: deferred` требует DEC-ID и не может скрывать обязательный `MUST` без явного
owner override;
- статус внешнего monitoring-dashboard не может выполнять ни один переход.

Для каждой записи хранится `status_changed_at`, actor, commit/CI SHA, evidence refs и
причина перехода. Статусы «в работе» отображаются отдельно от «запланировано» и не могут
быть выведены только из наличия незакоммиченного diff.

## Дополнение Q. Changelog и обратная совместимость с v2.5

| Изменение v2.6 | Причина | Влияние на текущий проект |
|---|---|---|
| Атомарные `REQ-ID` и трассировка | исключить потерю требований между ТЗ и roadmap | governance-артефакты |
| Разделение requirement/delivery status | не путать зрелость контракта с ходом реализации | additive status fields |
| Channel/device/surface model | поддержать все типы носителей | additive tables/fields и adapters |
| Универсальные manifest/proof contracts | убрать KSO-only coupling | compatibility layer вокруг KSO |
| Role/scope и portal journeys | сделать пользовательскую логику проверяемой | journeys/smoke, старые пути сохраняются |
| Error/idempotency/reconciliation rules | устранить гонки и повторы доставки | guards и targeted tests |
| SLO/DR/load/retention decisions | сделать production claims измеримыми | отдельные gates |
| Decision register и conflict policy | исключить молчаливое изменение scope | governance-only до owner approval |

Таблица выше — краткое тематическое резюме и не заменяет полный changelog. Полный журнал
обязан для каждой записи содержать затронутые REQ-ID и roadmap task.
Ни один пункт v2.6 не отменяет рабочий KSO-first flow без отдельной миграционной задачи.
Breaking change допускается только после compatibility plan, backfill/reconciliation,
параллельного периода, когда compatibility plan его требует, rollback drill и owner gate. Каждая строка changelog
ссылается на затронутые REQ-ID и обновлённую roadmap task.
## Дополнение R. Контракт внешнего monitoring-dashboard

Endpoint наблюдателя является environment-specific внешней ссылкой и хранится в
инвентаре окружений/операторской конфигурации, а не в нормативном ТЗ. Monitoring-dashboard
является независимым read-only наблюдателем. Он может агрегировать
Git/CI/roadmap/PROJECT_STATE/стенд и показывать собственный `observed_at`, но не изменяет
файлы, статусы, задачи или owner decisions.
Доступность endpoint проверяется отдельно и не является доказательством свежести или
каноничности данных; при недоступности фиксируется `PENDING`, а не «система исправна».

Для каждого отображаемого факта портал обязан показывать:

- источник (`origin/develop`, commit SHA, CI run, stand host/schema, файл и строку);
- время наблюдения и ожидаемую freshness window;
- тип значения: факт, derived metric, projection или external observation;
- статус confidence: verified, stale, unavailable, conflicting;
- ссылку на первичное evidence и правило вычисления.

Расхождение оформляется как `MON-DIVERGENCE-ID` с двумя значениями, SHA/датами, описанием
правила разрешения и ответственным. Портал не повышает статус задачи на основании
незакоммиченного diff, намерения агента или собственного расчёта. Канонический статус
берётся только из утверждённого источника проекта; monitoring служит сигналом для аудита.

Минимальные проверки интеграции: stale-source, отсутствующий SHA, расхождение `planned`
и `in_progress`, mismatch CI/roadmap, скрытая задача без REQ-ID и отсутствие текущего
Next. Внешний портал не блокирует deployment сам по себе, но его неразрешённое критичное
расхождение блокирует owner acceptance соответствующего требования.
## Дополнение S. Threat-model и security-negative baseline

До production проверяются как минимум следующие угрозы:

- privilege escalation, missing permission и cross-retailer/branch/store/surface access;
- session fixation, token replay, weak MFA/recovery и общий аккаунт;
- JWT/access token в URL, утечка secret/PII в логах, URL, error response или export;
- подмена manifest/media, неверный SHA/signature, revoked device и clock replay;
- вредоносный media/HTML5: executable, SSRF, XSS, CSP bypass, external network;
- vendor credential leakage, rate-limit bypass, retry storm, queue poison/DLQ abuse;
- duplicate/out-of-order PoP, forged device event и несанкционированный emergency;
- массовая команда без scope/confirmation, rollback sabotage и audit tampering;
- backup exposure, restore из неподтверждённого источника и нарушение retention/удаления.

Для каждой угрозы фиксируются attacker/action, защищаемый объект, control, negative test,
alert, audit record, owner и residual risk. Отсутствие negative proof не считается
«безопасным по умолчанию».
## Дополнение T. Дополнительные user stories

| ID | Роль | User story | Результат |
|---|---|---|---|
| US-CHAN-001 | Владелец канала | Зарегистрировать channel/device/surface/profile и adapter contract | Канал готов к mock-проверке |
| US-CHAN-002 | Владелец канала | Добавить rendition и channel-specific ограничения | Core campaign не изменяется, compatibility проверена |
| US-CHAN-003 | Оператор платформы | Управлять всеми physical device, logical carrier и surface разных каналов из единого Operations-контурa | Видны scope, состояние и независимый результат каждой операции; частичный сбой не скрыт |
| US-LIC-001 | Оператор лицензирования | Просмотреть состояние license grant, занятые seats и применить подписанный grant без отключения действующих устройств | Enrollment/decommission/renewal соблюдают seat-limit, подпись и аудит; Layer 2 UI явно показывает blocked/active состояние |
| US-COM-001 | Коммерческий оператор | Управлять тарифом/прайс-листом, сформировать offer, создать order, забронировать inventory и закрыть order; payment status — только при активированном DEC-017 контуре | Все переходы versioned и scope-aware; цена и capacity согласованы, история закрытого заказа неизменяема; финансовый статус не заявляется без внешнего подтверждения |
| US-ADV-002 | Рекламодатель/менеджер onboarding | Подать заявку, пройти review, создать организацию, заполнить legal/contact/brand данные, пригласить пользователей и затем безопасно открыть self-service campaign/report контур | До одобрения нет доступа к коммерческим операциям; после одобрения scope ограничен своей организацией/retailer, все изменения и приглашения аудируются |
| US-ADV-003 | Уполномоченный администратор/менеджер | Выбрать рекламодателя, создать договор и загрузить PDF через UI | Текущий факт: PDF/metadata сохраняются и размер проверяется; immutable file-version и server-side SHA verification остаются обязательным требованием, а не заявленным фактом |
| US-ADM-002 | Оператор управления ролями | Просмотреть каталог permissions с code, label и description | Backend-каталог содержит 30 прав, frontend описывает 23, документы ранее заявляли 24; целевое состояние — все backend-права показаны без фантомов, неизвестное право получает безопасный fallback |
| US-INV-001 | Менеджер инвентаря | Создать, просимулировать, согласовать и активировать правило inventory по каналу/surface/store/time/priority | Правило versioned и effective-dated, конфликт/overbooking видны до активации, rollback возвращает последнюю утверждённую версию |
| US-DATA-001 | Data steward | Назначить owner, PII-класс, retention и lineage сущности | Доступ/архив/удаление контролируются |
| US-FIN-001 | Финансовый контролёр | Сверить order, tariff, booked capacity, plan/fact и compensation | Расчёт воспроизводим по версии правил |
| US-INT-001 | Интеграционный оператор | Проверить master price/SKU, vendor health и reconciliation | Price-related данные не публикуются при рассинхроне |
| US-REL-001 | Release owner | Утвердить rollout по метрикам и выполнить rollback | Есть owner decision и восстановление версии |
| US-DR-001 | Operations owner | Провести backup restore и DR drill | RTO/RPO подтверждены для компонента |
| US-REG-001 | Аудитор | Сопоставить ТЗ, roadmap, Git, CI, стенд и monitoring | Расхождения имеют ID и disposition |
| US-FLT-001 | Менеджер кампаний | Настроить versioned flight/placement windows в UTC и локальной TZ | Показ вне окна блокируется, изменения версионируются |
| US-ELG-001 | Менеджер кампаний | Проверить eligibility кампании перед генерацией manifest | Неподтверждённая кампания не попадает на носители |
| US-PRI-001 | Менеджер кампаний | Настроить тип кампании и приоритеты с объяснимым preemption | Конфликт разрешается по действующей версии правил |
| US-UDR-001 | Аналитик | Разобрать недопоказ и сформировать make-good | Причина, процент, докрутка и компенсация воспроизводимы |
| US-WFL-001 | Менеджер кампаний | Закрыть размещение после итогового plan/fact и причин отклонений | Преждевременное закрытие запрещено |
| US-RPT-001 | Аналитик | Открыть обязательные network/campaign/store/advertiser/inventory/SLA views | Каждый view имеет scope, freshness и экспортный контракт |
| US-AB-001 | Аналитик | Провести A/B attribution и утвердить winner metric | Результат версионирован и не меняет историю |
| US-KPI-001 | Product owner | Утвердить baseline/target бизнес-KPI и просмотреть эффект | Outcome-KPI отделён от технического SLO |

Эти истории также требуют journey/permission/scope, positive/negative proof и связи с
REQ-ID; административный CRUD сам по себе не считается их выполнением.
## Дополнение U. Journeys служебных ролей

Каждый сценарий ниже является нормативным шаблоном; конкретные routes и `data-testid`
фиксируются в `portal-route-matrix.yaml` и `journeys/`.

| Journey | Actor | Happy-path: N шагов | Ключевой результат |
|---|---|---|---|
| J-CHAN-002 | Владелец канала | Happy-path: 7 шагов — Login → Channels → New → type/profile → adapter contract → mock test → Submit | channel/profile/adapter version зарегистрированы |
| J-CHAN-003 | Владелец канала | Happy-path: 6 шагов — Login → Channel profile → add rendition → set limits → preview/validate → publish version | rendition совместим с capability profile и версионирован |
| J-CHAN-004 | Оператор платформы | Happy-path: 8 шагов — Login → Operations → выбрать channel/carrier/surface → отфильтровать scope → preview bulk action → confirm → наблюдать progress по каждому объекту → открыть partial result и retry failed | все носители управляются единообразно, без cross-surface побочных изменений |
| J-LIC-001 | Оператор лицензирования | Happy-path: 7 шагов — Login → Licensing → выбрать grant/device scope → проверить signature/validity/seats → preview renewal или enrollment impact → confirm → открыть audit/report result | seat ledger и signed grant применены атомарно; активные устройства не отключены при renewal |
| J-COM-001 | Коммерческий оператор | Happy-path: 9 шагов — Login → Commercial → выбрать tariff/price-list version → сформировать offer → выбрать placement/inventory → создать order → забронировать capacity → закрыть order → открыть immutable audit/report; payment status — отдельный условный шаг только при DEC-017 | коммерческий контур отделён от license, расчёт воспроизводим по версии правил, конфликт capacity не обходит reservation |
| J-ADV-002 | Рекламодатель/менеджер onboarding | Happy-path: 9 шагов — открыть public apply → заполнить организацию/legal/contact → отправить заявку → оператор review/approve → создать brand → пригласить пользователя → войти в self-service → создать/просмотреть campaign → открыть report | доступ появляется только после approval, все данные изолированы advertiser scope, pending/rejected причины видимы пользователю |
| J-INV-001 | Менеджер инвентаря | Happy-path: 8 шагов — Login → Inventory rules → выбрать channel/surface/store/time → задать capacity/priority/filler → Simulate → inspect conflicts/forecast → Submit approval → Activate или rollback версии | правило не меняет активные бронирования до approval/effective date, результат симуляции воспроизводим |
| J-DATA-001 | Data steward | Happy-path: 6 шагов — Login → Data catalog → entity → owner/PII/retention → lineage → Approve | политика доступа/хранения применима |
| J-FIN-001 | Финансовый контролёр | Happy-path: 6 шагов — Login → Commercial → order/tariff → plan/fact → compensation → Reconcile | расчёт совпадает с версией правил |
| J-INT-001 | Интеграционный оператор | Happy-path: 6 шагов — Login → Integrations → source health → price/SKU diff → reconcile/hold → Resolve | опасные данные не опубликованы |
| J-REL-001 | Release owner | Happy-path: 6 шагов — Login → Rollout → scope/metrics → canary → approve/pause → rollback/complete | версия доставлена или безопасно откачена |
| J-DR-001 | Operations owner | Happy-path: 6 шагов — Login → DR → select backup → restore sandbox → verify checks → record result | RTO/RPO и целостность подтверждены |
| J-REG-001 | Аудитор | Happy-path: 4 шага — Login → Evidence → compare TZ/REQ/roadmap/Git/CI/stand/monitoring → file divergence | gap имеет ID и disposition |
| J-ANL-001 | Аналитик | Happy-path: 6 шагов — Login → Analytics → choose campaign/channel/store → compare plan/fact → inspect underdelivery → export CSV (XLSX planned) | воспроизводимый read-only отчёт с фильтрами и evidence; недоступный XLSX не отображается как готовый |
| J-ADM-001 | Системный администратор | Happy-path: 7 шагов — Login → Admin → users/roles → devices/settings → audit/monitoring → inspect scope → save change | изменения применены только в разрешённом scope и записаны в audit |
| J-SEC-001 | Специалист ИБ | Happy-path: 6 шагов — Login + MFA → Security dashboard → filter critical events → inspect permission/device/emergency action → export SIEM evidence → record review | только разрешённые события/данные в scope, экспорт аудирован, tamper/PII нарушения дают alert |

Каждый journey содержит один видимый action на шаг, следующий шаг, negative path,
permission/scope, audit, acceptance layer, UI-smoke и строку operator walkthrough.

Идентификаторы `J-*` ниже — design-scenario IDs для связности этого черновика, а не
ключи project journey. В полях `journey_id`/`journey_ids`, traceability, registry и
имени UI-smoke обязательно используются стабильные dot-case IDs `<domain>.<action>`
из `docs/product/user-journeys.md` (например `campaign.create`).
До добавления нового project journey соответствующий ID имеет статус `PENDING`, а не
выдумывается как `J-*` и не считается UI-покрытием.

Реестр совместимости исторических portal-меток (алиас не является отдельным journey):

| Alias ID | Canonical journey |
|---|---|
| J-PORTAL-001 | J-CAM-001 |
| J-PORTAL-002 | J-CAM-001 |
| J-PORTAL-003 | J-CAM-001 |
| J-PORTAL-004 | J-CAM-001 |
| J-PORTAL-005 | J-DEVICE-001 |
| J-PORTAL-006 | J-DEVICE-001 |
| J-PORTAL-007 | J-PORTAL-ADVERTISER |
| J-PORTAL-ADVERTISER | J-PORTAL-ADVERTISER |
| J-PORTAL-CAMPAIGN | J-CAM-001 |
| J-PORTAL-APPROVAL | J-CAM-001 |
| J-PORTAL-OPS | J-DEVICE-001 |
| J-PORTAL-EMERGENCY | J-EMR-001 |

Генераторы traceability обязаны разрешать alias ровно в указанный canonical journey;
новый alias без owner и changelog запрещён.

Реестр технических сценариев для требований без user story:

| Scenario ID | Scope | Проверка | Owner | Evidence |
|---|---|---|---|---|
| SC-ARCH-001 | architecture | новый channel adapter подключается без изменения campaign core; проходят import-boundary, contract и regression проверки | назначается | UNVERIFIED до CI/contract run |

`SC-*` является обязательной ссылкой покрытия для technical/security/operational/governance
REQ; сценарий без owner/evidence не переводится в `done`.

## Дополнение V. Полная связка user story → journey → requirement

**SUPERSEDED INSIDE THIS DRAFT:** раздел сохранён только для рецензирования миграции r413.
Он не является нормативным input и не должен потребляться генератором или roadmap.
Единственный действующий story/acceptance register этого драфта — Дополнение AP; после
cutover раздел V удаляется в отдельную историческую запись.

Человекочитаемые названия `J-PORTAL-CAMPAIGN` и подобные в описании экранов являются
алиасами. Таблица ниже сохранена как **legacy design-alias map r413**: её IDs не являются
каноническими автоматически. Для 27 отсутствующих project journey и двух alias действует
`PENDING-ID`/owner disposition из Дополнения AP; при конфликте AP имеет приоритет.
Canonical ID существует только если он разрешается в `user-journeys.md` и
`feature-registry.yaml` либо имеет owner-approved alias mapping.

| User story | Journey ID | REQ-ID |
|---|---|---|
| US-CAM-001 | campaign.create | REQ-BIZ-001, REQ-UX-001 |
| US-CAM-002 | campaign.submit | REQ-BIZ-003, REQ-SEC-002 |
| US-MOD-001 | creative.moderate | REQ-CONT-001, REQ-UX-001 |
| US-APR-001 | campaign.approve | REQ-BIZ-003, REQ-SEC-002 |
| US-OPS-001 | device.diagnose | REQ-OPS-001, REQ-UX-001 |
| US-OPS-002 | rollout.rollback | REQ-OPS-002, REQ-OPS-004 |
| US-ADV-001 | advertiser.view | REQ-BIZ-003, REQ-UX-001 |
| US-EMR-001 | emergency.activate | REQ-OPS-001, REQ-SEC-004 |
| US-CHAN-001 | channel.register | REQ-CHAN-001, REQ-ORCH-002 |
| US-CHAN-002 | channel.rendition_validate | REQ-CONT-001, REQ-MAN-001 |
| US-CHAN-003 | carrier.manage | REQ-CHAN-003, REQ-OPS-001, REQ-SEC-002, REQ-UX-001 |
| US-LIC-001 | license.manage | REQ-LIC-001, REQ-SEC-003, REQ-UX-001 |
| US-COM-001 | commerce.manage | REQ-BIZ-014, REQ-BIZ-009, REQ-SEC-002, REQ-UX-001 |
| US-ADV-002 | advertiser.onboard | REQ-BIZ-015, REQ-SEC-002, REQ-UX-001 |
| US-ADV-003 | advertiser.contract_crud (`advertiser.contract_pdf_upload` — compatibility journey alias до cutover) | REQ-BIZ-017, REQ-SEC-004, REQ-UX-001 |
| US-ADM-002 | permissions.description | REQ-UX-005, REQ-SEC-002, REQ-UX-001 |
| US-INV-001 | inventory.rule_manage | REQ-BIZ-016, REQ-BIZ-001, REQ-UX-001 |
| US-DATA-001 | data.catalog | REQ-DATA-001, REQ-SEC-004 |
| US-FIN-001 | finance.reconcile | REQ-BIZ-002, REQ-BIZ-009 |
| US-INT-001 | integration.reconcile | REQ-INT-001, REQ-INT-002 |
| US-REL-001 | release.rollback | REQ-OPS-002, REQ-OPS-003 |
| US-DR-001 | backup.restore | REQ-OPS-003 |
| US-REG-001 | audit.compare | REQ-GOV-001 |
| US-FLT-001 | campaign.schedule | REQ-BIZ-005 |
| US-ELG-001 | campaign.readiness | REQ-BIZ-006 |
| US-PRI-001 | inventory.priority | REQ-BIZ-007 |
| US-UDR-001 | campaign.underdelivery | REQ-BIZ-008 |
| US-WFL-001 | campaign.close | REQ-BIZ-010 |
| US-RPT-001 | reports.view | REQ-BIZ-011 |
| US-AB-001 | experiment.evaluate | REQ-BIZ-012 |
| US-KPI-001 | kpi.review | REQ-BIZ-013 |
| US-SEC-001 | security.review | REQ-SEC-001, REQ-SEC-003, REQ-SEC-004 |
| US-ANL-001 | analytics.compare | REQ-BIZ-004, REQ-UX-001 |
| US-ADM-001 | admin.manage | REQ-SEC-001, REQ-SEC-002, REQ-OPS-001, REQ-UX-001 |

У каждой связки должны быть
actor, scope, `Happy-path: N шагов`, negative path, acceptance и evidence; story или
journey без связки считается orphan и блокирует `APPROVED`.

Эти dot-case IDs являются предложениями/legacy aliases v2.6 до reconciliation по AP.
Наличие строки в этом черновике не доказывает наличие одноимённого journey в `docs/product/user-journeys.md`, зелёного
`test_uismoke__<domain>__<action>` или operator walkthrough; до проверки статус — `PENDING`.

`J-SEC-001` — `Login + MFA → Security dashboard → filter critical events → inspect
permission/device/emergency action → export SIEM evidence → record review`. `Happy-path:
6 шагов`; отсутствие права, PII или tamper-evidence даёт negative path и security alert.
## Дополнение W. Portal journey step counts

Для portal-алиасов бюджет шагов фиксируется явно; это не канонический project journey-регистр:

| Alias / design-scenario ID | Happy-path |
|---|---|
| J-PORTAL-001 | Happy-path: 12 шагов — создать campaign и пройти simulation до submit |
| J-PORTAL-002 | Happy-path: 8 шагов — открыть approval, сравнить версии и принять/reject |
| J-PORTAL-003 | Happy-path: 6 шагов — открыть moderation, проверить rendition и вернуть с причиной |
| J-PORTAL-004 | Happy-path: 7 шагов — открыть approval impact и завершить decision |
| J-PORTAL-005 | Happy-path: 7 шагов — найти target, диагностика, команда, progress, result |
| J-PORTAL-006 | Happy-path: 8 шагов — выбрать rollout, canary, metrics, pause/rollback |
| J-PORTAL-007 | Happy-path: 6 шагов — открыть campaign, plan/fact, exclusions и export |

Каждый шаг в финальной journey-спецификации будет разложен на одно видимое действие,
следующий экран и проверяемый результат; таблица здесь фиксирует только бюджет пути.

## Дополнение X. Negative-path matrix для journeys

| Journey family | Обязательный negative path | Ожидаемое поведение |
|---|---|---|
| Campaign/create/approval | нет scope, inventory, QA или approval | publish disabled, причина и следующий шаг |
| Moderation/rendition | malware, MIME/codec/profile violation | reject без публикации, audit и повторная загрузка версии |
| Channel registration | duplicate device/surface, invalid contract/profile | validation error, no partial registry write |
| Inventory/simulation | conflict, sold-out, over-capacity | alternatives/impact, запрет silent overbooking |
| Device/operations | revoked/offline/degraded target | fail-closed command или explicit pending, без aggregate success |
| Manifest/delivery | bad signature/SHA, incompatible version, vendor timeout | reject/DLQ/retry, rollback policy и alert |
| PoP/report | forged, duplicate, late or unknown event | rejected evidence, dedupe, отчёт не завышается |
| Emergency | missing MFA/reason, partial delivery, resume conflict | deny/partial progress, high-priority audit и safe resume |
| Advertiser/export | чужой retailer/scope, overlarge period, expired link | 403/validation, redacted response, audit |
| Rollout/rollback | threshold breach, concurrent rollout, missing artifact | pause/rollback, owner decision, no mixed version |
| Data/retention | PII over-collection, expired object, restore mismatch | deny/quarantine, retention action и incident |
| DR/restore | corrupt backup, wrong schema/SHA, RTO breach | stop restore, incident, last known-good recovery |

Каждый конкретный journey выбирает минимум один релевантный ряд этой матрицы и добавляет
его в acceptance/evidence. Негативный сценарий должен проверять не только сообщение UI,
но и отсутствие побочного изменения данных, события аудита и утечки scope.

## Дополнение Y. Контроль нормативности требований

Нормативность требования не изменяется молча:

- `MUST → SHOULD/MAY` требует DEC-ID, rationale, owner approval, impact analysis и даты
  вступления; до этого действует исходный `MUST`;
- `SHOULD/MAY → MUST` требует оценки scope, бюджета, безопасности и новой roadmap task;
- удаление или объединение требований сохраняет ссылки на исходные REQ-ID и changelog;
- изменение формулировки не может уменьшать coverage, acceptance или evidence;
- approved ADR может уточнить реализацию, но не отменяет `MUST` ТЗ без owner decision;
- `deferred`, `rejected` и `superseded` имеют разные последствия для roadmap и release gate.

Самопроверка сравнивает множества `MUST` между редакциями и краснеет при исчезновении,
понижении нормативности или потере source mapping без DEC-ID.

## Дополнение Z. Incident management и эксплуатационная модель

Определяются уровни инцидентов:

- `SEV-1` — массовая недоступность, нарушение безопасности, риск кассовых/ценовых
  операций или emergency SLA; немедленная эскалация и owner incident commander;
- `SEV-2` — существенная деградация канала/отчётности или нарушение campaign SLA без
  массового влияния; назначенный on-call и план восстановления;
- `SEV-3` — локальная ошибка, отдельный device/vendor или несрочная потеря функции;
  обычный backlog с target date;
- `SEV-4` — косметика/документация; плановая обработка.

Для каждого SEV задаются MTTA/MTTR, часы поддержки, on-call, escalation path, статусные
обновления, коммуникация бизнесу/ИБ, post-incident review и связь с audit/REQ-ID. Planned
maintenance имеет окно, owner, impact preview, rollback и уведомление затронутых ролей.
Нельзя закрывать инцидент только восстановлением HTTP 200: проверяются данные, PoP,
scope, безопасность, отчёты и operator walkthrough.

## Дополнение AA. Атомарность трассировки

Один `REQ-ID` не может скрывать несколько независимых обязательств. Если предложение
содержит несколько проверяемых действий, оно разбивается на `REQ-ID` или получает явный
список sub-requirements (`REQ-ID.a`, `REQ-ID.b`) с отдельными owner, task и evidence.

Контрольная сверка считает исходные нормативные предложения и строки матрицы. Допустимое
агрегирование должно иметь явное правило 1:N; строки без обратной ссылки на source line,
а также source lines, связанные только с общим заголовком, считаются orphan. Процент
покрытия равен `mapped atomic requirements / classified normative requirements`, а не
числу разделов или задач roadmap.
## Дополнение AB. HTTP и event semantics

Единый API-контракт использует следующие правила:

- `200` — синхронный успешный read/update; `201` — создана новая версия/сущность;
  `202` — asynchronous command принята и имеет operation ID;
- `304` — manifest/content не изменились при валидном `ETag`/`If-None-Match`;
- `400/422` — malformed/semantic validation; `401` — отсутствует/истёк authentication;
  `403` — permission/scope deny без утечки; `404` — объект отсутствует в разрешённом scope;
- `409` — version/idempotency/concurrency conflict; `412` — failed `If-Match`/precondition;
- `429` — rate limit с `Retry-After`; `5xx/503` — transient/unavailable только при
  безопасном retry policy и correlation ID.

Ошибки имеют единый envelope: `code`, `message_for_user`, `detail_for_operator`,
`trace_id`, `retryable`, `field_errors`, `next_action`, `audit_id`. Secrets, tokens и
чужие object IDs в envelope запрещены.

Все asynchronous commands принимают `Idempotency-Key`, возвращают `operation_id` и
публикуют событие с `event_id/schema_version/trace_id`. Consumer дедуплицирует; повторный
запрос возвращает исходный результат, а не создаёт новую операцию.
## Дополнение AC. Саморевью: что ещё не заполнено и блокирует APPROVED
Этот раздел отделяет «требование описано» от «требование готово к реализации». Найдены следующие блокеры самого драфта:

| ID | Пробел | Закрытие до APPROVED |
|---|---|---|
| AC-01 | Нет заполненного `requirements-traceability.yaml`; есть только каталог и правила. | Создать файл и проверить 100% REQ без orphan. |
| AC-02 | Нет Roadmap-ID, delivery status и владельца для каждого REQ. | Синхронно заполнить SSOT и обе проекции roadmap. |
| AC-03 | Нет полных OpenAPI, JSON Schema, event envelope и compatibility matrix. | Приложить versioned schemas с auth, errors, idempotency и deprecation. |
| AC-04 | Нет согласованных ERD/data dictionary, FK, индексов, RLS, миграций и PII. | Утвердить ERD, словарь и migration/backfill/rollback plan. |
| AC-05 | Формулы inventory/impression/reach/compensation не проверены численными примерами. | Добавить единицы, округление, TZ и позитивные/негативные примеры. |
| AC-06 | Нет полной матрицы канал × surface × rendition × proof × SLA × owner. | Заполнить матрицу; неизвестное вынести в DECISION_REQUIRED. |
| AC-07 | Monitoring-dashboard описан без полного read-only/freshness/correlation contract. | Закрыть `DEC-014`, зафиксировать `MON-DIVERGENCE-ID` и запрет записи статусов. |
| AC-08 | Полный паспорт DEV не завершён: канонический `docs/product/environment-inventory.yaml` уже содержит endpoint, identity/SHA/schema и evidence для `.81`, но не все обязательные seed/reset, monitoring, доступ/rollback и операционные поля подтверждены. | Дополнить именно канонический inventory (без второго источника), закрыть seed/reset, owner, monitoring, доступ и rollback evidence; baseline `.81` перепроверить на актуальном SHA. |
| AC-09 | Security/legal решения и retention перечислены, но не утверждены. | Для каждого DEC указать выбор, owner, дату, REQ и review date. |
| AC-10 | NFR/SLO не имеют воспроизводимой методики и CI evidence. | Утвердить load/chaos/restore пакет доказательств. |
| AC-11 | Не для всех journeys зафиксированы route, data-testid, smoke и walkthrough. | Заполнить поля; без доказательства — не `done`. |
| AC-12 | Нет inventory затронутых KSO/portal/API модулей и rollback-плана. | Составить compatibility inventory с dual-read/write и backfill. |
| AC-13 | Нет RACI, on-call, runbook IDs, maintenance windows и DR-календаря. | Утвердить operational handbook с evidence. |
| AC-14 | Не определены коммерческие KPI и границы ЭДО/биллинга. | Принять финансовую модель и scope. |
| AC-15 | Не зафиксирован формальный «ready for development» и список подписантов. | Выполнить release-gate с подписями owner, Codex и Claude Code. |
| AC-16 | Product/technical/security owners и effective date не назначены; revision и source SHA зафиксированы только для этой версии драфта. | Назначить владельцев и дату вступления; при изменении источника пересчитать SHA и revision. |
| AC-17 | Карта подтверждает наличие всех верхних разделов, но не классифицирует каждое нормативное предложение исходника построчно. | Выполнить extraction/classification source lines и связать каждую строку с REQ-ID либо approved exclusion. |
| AC-18 | Нормативные фразы самого драфта требуют отдельной reverse-traceability; прежний count кандидатов устарел после редакций и не должен использоваться как подтверждённая метрика. | Выполнить версионируемый scan текущего драфта, пометить raw/normalized count как `UNVERIFIED` до classifier, исключить заголовки/пояснения, а для каждой нормативной фразы добавить REQ-ID либо вынести её в атомарный каталог; проверять reverse-traceability автоматически. |
| AC-19 | В r413 таблицы 41 user stories не имели обязательных полей. В r414 Дополнение AP заполняет actor/permission/scope/preconditions/entry/happy/negative/audit/trace/status для всех 41, но это не означает 41 canonical project journeys. | `fixed_in_r414` для логического story-contract; остаются machine YAML, selectors, canonical ID mapping, smoke/evidence и operator walkthrough. Каждая запись должна пройти schema-check до `APPROVED`. |
| AC-320 | До r410 рабочая редакция находилась вне коммита и не имела собственного digest; одного пути и source SHA недостаточно для воспроизводимой привязки approval к байтам драфта. | Опубликован `docs/audit/2026-08-26-tz-v2.6-design-draft.sha256`; его значение должно совпадать с SHA файла перед `APPROVED` и обновляться при любом изменении текста. |
| AC-321 | `docs/product/roadmap.yaml` содержит `base.git_sha: 2b935bb…`, но live `HEAD` и `origin/develop` равны `b21174f…`; статус/генерация roadmap привязаны к устаревшему snapshot и могут не отражать текущий код и документацию. | После согласованного roadmap cutover пересоздать/проверить projection на текущем canonical SHA, сохранить source SHA и дату, а validator должен блокировать stale base SHA или явно разрешённый historical snapshot. |
| AC-322 | AC-244 и его changelog цитируют исторические `73 task/stage/decision IDs`, тогда как текущий `roadmap.yaml` содержит 43 tasks, 6 stages, 16 owner decisions и 3 gates — всего 68; старое число может исказить оценку покрытия. | Пометить 73 как dated snapshot либо пересчитать его по типизированному скрипту на каждой revision; в coverage manifest разделять tasks, stages, decisions и gates и сверять totals с canonical roadmap SHA. |
| AC-323 | Snapshot registry/roadmap ранее содержал только counts; изменение при сохранении количества элементов могло пройти незамеченным. | Фиксировать SHA-256 каждого канонического файла вместе с counts и проверять digest при каждой сверке; текущие SHA сохранены в Дополнении AO. |
| AC-324 | 40 приложений имеют уникальные ID, но физический порядок не монотонен (`AO` расположен до `AE/AF`, затем `AI/AD/AL/AJ`); ссылки по номеру и review-навигация становятся неоднозначными. | Добавлен `docs/audit/appendix-index.md` с ID→заголовок→anchor; validator должен ловить дубли/отсутствующие ID и обновлять ссылки после перемещения. |
| AC-325 | Реестр AC содержит только ID, описание пробела и предлагаемое закрытие, но не machine-readable `status`; по таблице нельзя однозначно отличить исторически исправленное замечание от текущего blocker. | Добавить обязательный status enum `open/fixed/verified/blocked`, `owner`, `evidence_ref` и `verified_at`; `APPROVED` разрешать только при `verified` для всех применимых AC, а исторические findings помечать snapshot. |
| AC-326 | Обратная сверка выявила не две новые функции, а alias `advertiser.contract_pdf_upload` для registry-функции `advertiser.contract_crud` и под-функцию `permissions.description` внутри `user.assign_roles`; прежняя формулировка могла создать дубликаты. | Owner выбрал `advertiser.contract_crud`; REQ-BIZ-017/REQ-UX-005 и US-ADV-003/US-ADM-002 сохраняют отдельный scope/acceptance, journey alias мигрируется при cutover, новый registry ID для permission descriptions не создаётся. |
| AC-20 | Нет единого handoff-пакета и последовательности gate с назначенными владельцами артефактов. | Собрать пакет из Дополнения AG и получить отдельные owner approvals до начала реализации. |
| AC-21 | Accessibility target и обязательные локали/форматы не выбраны владельцем. | Принять стандарт, locale/timezone matrix и accessibility test plan с owner/evidence. |
| AC-22 | Рекомендованный stack из starting decisions не зафиксирован в драфте как baseline и не имеет owner approval. | Принять или изменить stack decision; зафиксировать совместимость, операционный контракт и дату пересмотра. |
| AC-23 | §22.6 и §22.10 требуют четыре разных dashboard и конкретный набор health/SLA/ИБ/бизнес-метрик, а прежняя формулировка оставляла это общим словом «dashboards». | Утвердить dashboard catalog: metric, formula/source, grain/TZ, freshness, drill-down, alert threshold, owner и evidence для technical/business/security/service-quality представлений. |
| AC-24 | §22.11 требует машинно проверяемые ограничения выгрузок и изоляцию данных рекламодателей; одной общей ссылки на RLS/retention недостаточно. | Зафиксировать export policy (permission/scope, period/volume limits, audit event, redaction) и negative-тесты cross-advertiser/export-overlimit. |
| AC-25 | §22.19 требует поиска, сортировки, сохранённых представлений и явного восстановления после ошибки; прежняя UX-матрица фиксировала только «таблица/фильтры». | Добавить эти состояния и действия в машиночитаемый portal-route/journey контракт и UI-smoke/negative acceptance. |
| AC-26 | §22.3 требует отдельной классификации недопоказа и воспроизводимого make-good; общая ссылка на SLA не задаёт причины, варианты докрутки и отчётный результат. | Связать `REQ-BIZ-008` с полями отчёта, reason enum, формулами plan/fact/threshold и owner-approved политикой компенсаций; добавить positive/negative examples. |
| AC-27 | §22.6 требует списки полностью выпавших магазинов и устройств, влияющих на активные кампании, с влиянием на прогноз и недопоказ; одной общей offline-метрики недостаточно. | Добавить эти представления в operations/quality dashboard и проверить связь с campaign forecast и underdelivery report на synthetic outage-сценарии. |
| AC-28 | Требования §13 об emergency были распределены по общим device/security пунктам и не имели отдельного атомарного контракта для MFA, причины, scope, partial progress и безопасного resume. | Утвердить `REQ-OPS-007`, emergency state/response schema и negative/partial-delivery tests с immutable audit. |
| AC-29 | §16.2 задаёт источник и формулу оценочного охвата по чекам, а каталог фиксировал только разделение fact/estimate и контракт интеграции. | Зафиксировать формулу, grain/period/TZ, источник агрегированных чеков, reconciliation и тест независимости от кассового/фискального контура. |
| AC-30 | §7.1 требует проверять в preview поведение скрытия рекламы при касании УКМ4; прежняя QA-формулировка фиксировала только формат и визуальный вид. | Добавить preview/behavioral acceptance для hide-on-touch и negative test, что рекламный слой не блокирует кассовый workflow. |
| AC-31 | §9 требует ограниченный локальный кэш и детерминированную очистку старых файлов; драфт описывал offline/fallback, но не задавал cache cap/cleanup policy. | Утвердить `REQ-OPS-008`: лимиты по профилям, алгоритм eviction, telemetry и тест восстановления после переполнения кэша. |
| AC-32 | §6.1 требует резервную локальную admin-учётную запись и запрет изменения approved campaigns одним только system-admin статусом; прежний identity-контракт фиксировал SSO/MFA, но не эти границы. | Зафиксировать break-glass lifecycle/rotation/audit и отдельный permission на изменение approved campaigns в role-scope matrix и negative tests. |
| AC-33 | §22.11 содержит конкретные окна хранения для PoP, архива отчётов, аудита, технических логов и креативов; прежний драфт оставлял только общую retention policy. | Утвердить retention matrix с указанными окнами, юридическими исключениями, archive/delete job, владельцем и тестом удаления/удержания. |
| AC-34 | §22.12 требует финансовые сущности (тариф, прайс-лист, скидка, пакет, бонус) и разрезы плановой стоимости/выручки; прежний data inventory и отчётный контракт их не фиксировали. | Добавить финансовые сущности в ERD/data dictionary и проверить versioned tariff/discount, paid-vs-internal separation и отчётные разрезы с owner/legal scope decision. |
| AC-35 | §22.15 перечисляет конкретные нагрузочные профили и периоды отчётов, а прежний NFR-контракт оставлял только общие «профили устройств/аналитики». | Утвердить `load-profiles.yaml` с указанными профилями, concurrency, dataset, percentile/error/resource budgets и evidence массовой публикации, emergency и advertiser/admin workloads. |
| AC-36 | §4 допускает API-ключи рекламодателя, но драфт не фиксировал, входят ли они в первую очередь и какие security controls обязательны. | Закрыть `DEC-013`: включить versioned scoped keys с rotation/revoke/audit либо явно исключить до отдельной задачи. |
| AC-37 | §6.2 требует обязательные бизнес-поля кампании и размещения (цель, лимиты, бюджет/объём, ответственный, частота, ограничения); прежний каталог коммерческого lifecycle перечислял сущности, но не полный набор полей. | Зафиксировать campaign/placement schema и state-transition acceptance с required fields, validation, scope и audit. |
| AC-38 | §22.1 требует owner/action/status/deadline/transition criteria для каждого шага и закрытие только после итогового plan/fact и причин отклонений; state machine без workflow SLA допускает преждевременное закрытие. | Утвердить `REQ-BIZ-010`, workflow matrix и тест запрета `completed/closed` без финального отчёта и underdelivery reasons. |
| AC-39 | §6.3 требует прогноз по периоду/географии/типу контента и выявление конфликтов по расписанию, доле рекламного времени, приоритетам и лимитам; прежний `REQ-BIZ-001` фиксировал только базовые capacity-счётчики. | Добавить inventory formula/examples и simulation proof для всех измерений, sold-out alternatives и silent-overbooking denial. |
| AC-40 | §12 перечисляет шесть обязательных dashboard/report views с различающимися полями; общий analytics endpoint не доказывает наличие этих представлений. | Зафиксировать report/view schemas, role/scope, filters, freshness, export и evidence для network/campaign/store-device/advertiser/inventory/SLA views. |
| AC-41 | §4.3 требует outbound-only device connectivity и недоступность внутренних хранилищ из магазинских/пользовательских сегментов; прежний network текст содержал только общие запреты. | Утвердить `REQ-SEC-008`, сегментацию/firewall matrix и negative reachability tests из device/store/workstation подсетей. |
| AC-42 | §10 требует одноразовую device-регистрацию с hardware fingerprint/сертификатом и явное влияние `maintenance`/`revoked` на SLA, показы и команды; прежний каталог фиксировал только общие status/commands. | Зафиксировать registration/state policy в device schema и negative tests: повторное использование кода, revoked command, maintenance inventory/SLA exclusion. |
| AC-43 | §11.1 требует offline buffering и chronological batch resend PoP/apply-ack/error; прежний `REQ-POP-002` фиксировал только серверную валидацию и dedupe. | Добавить device/gateway spool policy, ordering/retry/reconciliation и network-partition test без потери или задвоения коммерческого факта. |
| AC-44 | §11 и §11.2 требуют media SHA, failure reason и device signature в PoP; прежний `proof_event_v1` содержал только идентификаторы, время и playback result. | Обновить proof schema, signature/SHA validation, failure taxonomy и contract tests для valid/invalid/missing fields. |
| AC-45 | §11 требует различать `real_playback`, `screen_render`, `idle_screen`, `template_applied`, gateway/label/controller ACK; общий proof model допускал смешение типов доказательств. | Утвердить `pop_mode` enum, mapping channel→proof type и отчётные правила, исключающие apply/delivery ACK из playback/impression без owner-approved formula. |
| AC-46 | §11.1/§11.2 требуют store/placement/media и started/ended timestamps; прежний proof-контракт оставлял только укрупнённые campaign/creative/surface/device и rendered_at. | Обновить proof schema и contract tests на обязательность географии/размещения/медиа и согласованность `started_at ≤ ended_at`, duration и event time. |
| AC-47 | §11.1 перечисляет обязательные причины недопоказа, но `failure_reason` в драфте был свободной строкой. | Утвердить reason enum и mapping runtime/channel→reason, включая unknown/quarantine policy и отчётную агрегацию без потери исходной причины. |
| AC-48 | §10 перечисляет конкретные device-команды, а прежний `REQ-OPS-001` оставлял их свободным набором. | Зафиксировать command enum, permission/scope/confirmation/audit для каждой операции и negative tests для revoked/maintenance/bulk misuse. |
| AC-49 | §8.2 перечисляет обязательные поля manifest и ACK/error states; одного требования «JSON Schema» недостаточно для защиты от неполного контракта. | Утвердить `REQ-MAN-004`, manifest/adapter schemas и contract tests на missing field, invalid signature, expired window, storage error и все ACK states. |
| AC-50 | §3 задаёт 10 000 магазинов, в среднем 4 KSO на магазин и географию всей России; §3/22.11 требуют PoP retention не менее 3 лет, тогда как драфт не фиксировал масштаб и мог трактовать 3–5 лет только как условный архив. | Утвердить scale/geography baseline и retention matrix: PoP total ≥3 года, hot/archive tiers, TZ/network scenarios и owner/legal exception process. |
| AC-51 | §22.14 требует конкретные seed-сценарии и безопасные данные; прежний `REQ-STAND-001` фиксировал только каналы, ошибки и объём событий. | Утвердить scenario manifest и reset/seed acceptance для active/completed, underdelivery, offline, emergency, conflicts, compensation и sold-out без реальных данных. |
| AC-52 | §17 требует ClickHouse TTL/partitioning и MinIO versioning/lifecycle; прежний HA-контракт ограничивался общей репликацией/restore. | Утвердить storage topology, partition/TTL/lifecycle policy, backup/restore/replication evidence и тест истечения/восстановления данных. |
| AC-53 | §22.10 перечисляет обязательные alert conditions, а прежний observability-контракт оставлял только общее «alert thresholds». | Утвердить alert catalog: condition/threshold, severity, routing/on-call, deduplication, runbook, audit и synthetic firing test для каждого критичного события. |
| AC-54 | §22.8 требует versioning и diff кампаний, placements, playlists, priority rules и manifest; прежний `REQ-DATA-001` описывал lifecycle/retention, но не обязательный diff-контракт. | Зафиксировать version/diff schema, immutable history и historical reproducibility tests для всех delivery/reporting-relevant объектов. |
| AC-55 | §22.9 требует feature-flag targeting и audit/fast rollback; прежний `REQ-OPS-002` фиксировал только canary/pause/rollback без области и журнала изменения. | Утвердить flag schema и negative tests на scope leakage, unauthorized change, missing audit и rollback critical flag. |
| AC-56 | §22.7 задаёт конкретные rollout stages, а прежний контракт описывал только абстрактные lab/canary/staged/network. | Утвердить rollout policy с указанными этапами, exit/abort thresholds, owner approval и rollback evidence; отклонения требуют DEC-ID. |
| AC-57 | §3 требует потоковую обработку десятков/сотен миллионов PoP через ClickHouse, но ADR-007 откладывает его для текущего runtime; без фазовой оговорки это конфликт требований и архитектурного решения. | Утвердить phase-aware PoP ingestion profile: PostgreSQL operational path в Phase 1, ClickHouse partitioning/backpressure/lag и годовой load evidence только после activation gate, с backfill и совместимостью. |
| AC-58 | §23.6 требует channel-specific inventory units (airtime, idle plays, static ESL, LED cycle); общий capacity не предотвращает ошибочное сравнение несопоставимых единиц. | Утвердить channel capability/inventory matrix с единицами, формулами, rounding/TZ и negative tests против смешения каналов в sold/free/forecast. |
| AC-59 | §23.6 требует отдельные SLA и proof definitions по каждому каналу; прежний `REQ-BIZ-004` ограничивался долей активных устройств/носителей/поверхностей. | Утвердить channel quality matrix (inventory unit, SLA, proof type, freshness, underdelivery treatment, owner) и cross-channel reporting tests. |
| AC-60 | §23.8 требует видимую channel readiness matrix (rendition/inventory/conflict/forecast/PoP/SLA); journey без единого статуса готовности допускает публикацию при скрытом блокере. | Добавить readiness schema, role/scope rules, blocked/warning reasons и UI-smoke/negative acceptance с понятным next action. |
| AC-61 | §22.8 требует versioning/reproducibility также для API-контрактов, схемы БД и advertiser report; прежний `REQ-DATA-001` перечислял только delivery-объекты. | Расширить version/diff registry и historical replay tests на API, DB schema и отчёты, включая совместимость и правила миграции. |
| AC-62 | §22.5 требует визуальные проверки читаемости, safe margins, мелкого шрифта и перекрытия рабочей области УКМ4; прежний `REQ-CONT-001` фиксировал только формат/SHA/preview/hide-on-touch. | Утвердить visual QA checklist и evidence на реальных профилях surface, включая negative case с перекрытием кассовой зоны. |
| AC-63 | §22.5 требует сохранять у Creative QA проверяющего, время, набор проверок, замечания, утверждённую версию и причину допуска/отказа; одной декларации о visual QA недостаточно для аудита и воспроизводимости. | Утвердить QA-result schema и связь с immutable creative/rendition version; добавить schema/contract tests на обязательные поля, отказ без reason и запрет manifest без approved QA. |
| AC-64 | §3 задаёт heartbeat и опрос manifest каждые 30 секунд с jitter и требует `304 Not Modified` при неизменном представлении; общая фраза о compatibility не доказывает cache-revalidation semantics. | Зафиксировать polling/ETag contract, conditional-request/304 tests и negative case на выдачу изменённого manifest под старым ETag. |
| AC-65 | §4.2 рекомендует NATS/RabbitMQ/Redpanda для критичного потока и прямо запрещает использовать Redis как единственную очередь; прежний контракт требовал queue/DLQ, но не защищал durability boundary. | Зафиксировать broker/persistence profile в `DEC-004`, recovery/duplicate tests и negative architecture check на Redis-only critical delivery queue. |
| AC-66 | §22.5 перечисляет автоматические Creative QA проверки: разрешение, вес, длительность, кодек, FPS, битрейт, отсутствие звука, зона 1440×1080, MIME и SHA-256; прежняя формулировка оставляла часть проверок за общим «channel constraints». | Зафиксировать versioned QA checklist/schema с обязательными результатами каждой автоматической проверки и policy no-audio/KSO-zone; добавить negative fixtures по каждой нарушенной проверке и связь с QA evidence. |
| AC-67 | В драфте одновременно фигурировали кандидатная пилотная шкала `KSO → 10 → 100 → 500 → network` и обязательные rollout-этапы `lab → 5 → 50 → 300 stores → 10% → 50% → all network`; без явного разделения это допускает две несовместимые политики поставки. | В `DEC-010` выбрать одну пилотную шкалу и явно отделить её от общих rollout stages `REQ-OPS-002`; обновить owner-approved rollout matrix, exit/abort thresholds и все связанные roadmap tasks. |
| AC-68 | §4.3 требует отдельный высокоприоритетный канал доставки emergency-команд через Device Gateway; одного поля `priority` в общей очереди недостаточно для доказательства изоляции и SLA. | Зафиксировать emergency transport/queue contract, приоритет, независимые timeout/retry/DLQ и negative test, что обычный delivery backlog не блокирует emergency. |
| AC-69 | §23.4 требует выполнять Creative QA отдельно для каждого rendition; проверка только исходного creative допускает публикацию неподходящего channel-specific файла. | Связать каждый rendition с отдельным QA-result и capability profile; добавить negative test на approved creative при rejected/missing rendition QA и запрет его включения в manifest. |
| AC-70 | §24.13 требует явно различать в proof-модели `error/not_applied`; прежний enum различал ACK и playback, но не задавал машинный тип отказа применения. | Добавить `error` и `not_applied` в enum и channel mapping, запретить их агрегацию как playback/impression и покрыть schema/reporting tests. |
| AC-71 | §23.4 требует для каждого rendition проверять цветность и соответствие ограничениям канала; прежний контракт фиксировал размеры и читаемость, но не color/brightness profile. | Добавить channel-specific color/brightness limits в capability/QA schema и negative tests на rendition, нарушающий профиль канала. |
| AC-72 | §18 требует до основной реализации подтвердить техническую реализуемость на реальной КСО, включая 1440×1080, безопасность УКМ4, сеть и базовый manifest/playback/PoP; общий demo-stand не доказывает это hardware feasibility. | Зафиксировать `REQ-STAND-003`, провести owner-approved feasibility gate на реальной КСО и сохранить environment/constraint evidence до перехода к core implementation. |
| AC-73 | §4.3 ограничивает административный интерфейс корпоративной сетью/VPN и требует AD/SSO/MFA; наличие MFA в identity-контракте без сетевой границы оставляет внешний доступ неурегулированным. | Добавить admin-network access policy в `REQ-SEC-008`, firewall/route negative tests из public/store/device сегментов и evidence AD/SSO/MFA для административного UI. |
| AC-74 | §12 требует в отчёте рекламодателя проверяемую цепочку данных и подпись/штамп системы, но юридический статус PDF должен быть отдельно согласован с юристами; прежний отчётный контракт фиксировал только выгрузки. | Зафиксировать report provenance/signature schema и решение `DEC-007`: формат подписи/штампа либо явное исключение; добавить integrity test, что подпись относится к snapshot/version отчёта и не заявляет юридическую значимость без approval. |
| AC-75 | §22.6 требует отдельный интерфейс эксплуатации/ИТ-поддержки, не смешанный с коммерческими отчётами рекламного менеджера; одного общего role matrix недостаточно для проверки информационной изоляции. | Зафиксировать Operations route/data matrix, запрет коммерческих/advertiser действий из health UI и UI/RBAC negative tests на смешение интерфейсов и данных. |
| AC-76 | §22.6 требует для каждого устройства last heartbeat, current manifest, player/Chromium version, disk/cache, ошибки, последний успешный показ и последние PoP; прежний контракт описывал только статусы и команды. | Добавить обязательные поля device-health schema, freshness/permission rules и UI/API contract tests на наличие и scope-фильтрацию этих данных. |
| AC-77 | §12 ограничивает BI API авторизацией, rate limiting, журналированием и рекламодателем/ролью; прежний `REQ-INT-003` перечислял controls обобщённо и не требовал scope isolation. | Зафиксировать BI/export contract с auth, per-advertiser/role scope, rate-limit response, immutable audit и cross-advertiser/over-limit negative tests. |
| AC-78 | §22.14 требует, чтобы demo-стенд позволял быстро проверять фильтры, отчёты, права доступа, UI и бизнес-логику; наличие seed-данных без time-bounded reset не обеспечивает эту цель. | Зафиксировать reset/seed contract, целевое время восстановления и smoke-набор для filters/reports/RBAC/UI/business rules на безопасных данных. |
| AC-79 | §22.17 требует UTC+local TZ, отображение TZ отчёта, DST/ночные интервалы, праздники, закрытие магазинов и исключения расписания; прежний `REQ-NFR-002` фиксировал только UTC/local/DST/holidays. | Утвердить time/calendar schema и deterministic tests для DST, перехода даты, overnight windows, закрытого магазина и явного TZ в отчёте. |
| AC-80 | §22.18 требует versioned Device API, поддержку старых версий на время миграции и передачу player-supported API/manifest versions через heartbeat; общий version window не гарантирует negotiation. | Зафиксировать compatibility/negotiation schema, deprecation dates, heartbeat contract и tests выбора совместимой версии/отказа при отсутствии совместимости. |
| AC-81 | §22.19 требует progress для долгих операций и ошибок с объяснением «что/почему/что дальше/к кому обратиться»; прежний UX-контракт упоминал error recovery, но не проверяемый progress/error envelope. | Добавить progress/error-state schema для media upload, report generation, bulk publication, rollout и export; UI-smoke/negative tests проверяют видимый next step и восстановление после ошибки. |
| AC-82 | §22.10 требует correlation_id/trace_id, связывающий действие пользователя, manifest, доставку, применение, proof и отчёт; отдельные trace-поля в событиях не доказывают сквозную связность. | Зафиксировать correlation propagation contract и end-to-end trace test от portal action до advertiser report, включая потерю/дублирование звена и redaction secrets/PII. |
| AC-83 | §22.1 требует новую версию размещения при изменении срока, географии, креатива или объёма; прежний commercial lifecycle говорил о versioning, но не закреплял обязательные triggers. | Зафиксировать placement-version schema/diff и tests для каждого trigger, включая запрет перезаписи активной/исторической версии и связь новой версии с manifest/report snapshot. |
| AC-84 | §22.4 требует, чтобы overbooking по умолчанию был запрещён и включался только по решению бизнеса; общего запрета silent overbooking недостаточно для настройки и аудита режима. | Зафиксировать overbooking flag/policy, owner approval и effective time в decision/audit schema; добавить negative test на продажу сверх capacity при выключенном режиме и regression test после включения. |
| AC-85 | §6.1 выделяет системного администратора с CRUD пользователей/ролей/устройств/настроек/мониторинга/аудита, но запрещает изменение approved campaigns без отдельного права; прежний story/journey register не содержал этот сквозной сценарий. | Добавить `US-ADM-001`/`J-ADM-001` в полный story→journey→REQ реестр и UI/RBAC negative test на попытку system-admin изменить approved campaign без специального permission. |
| AC-86 | §6.2 требует pause, частичного снятия магазинов, продления и изменения креатива через новую версию; общей campaign state machine без атомарных действий и правил версий недостаточно. | Зафиксировать action/transition matrix, scope и audit для каждого действия; добавить positive/negative tests на partial removal, extension и запрет in-place creative change в live campaign. |
| AC-87 | §6.3 требует явные inventory statuses `free/reserved/sold/internal/emergency/fallback`; формулы capacity без статусов допускают смешение доступного и занятого инвентаря. | Зафиксировать inventory-status enum и переходы в schema/ERD, scope/expiration rules и tests, что каждый статус корректно влияет на sold/free/forecast и отчёты. |
| AC-88 | §6.3 требует настраиваемые правила инвентаря (максимальная рекламная нагрузка, длительность слота, прайм-тайм, приоритеты, filler); прежний контракт описывал расчёт, но не административный policy surface. | Зафиксировать inventory-policy schema, owner/scope/effective time и audit; добавить tests изменения policy, расчёта forecast и запрета публикации при превышении max ad load. |
| AC-89 | §6.2 и §22.4 требуют формализованный A/B-тест с control/test groups, периодом, winner metric, minimum sample и ручным подтверждением; прежний каталог оставлял это только в прозе. | Добавить `REQ-BIZ-012`, A/B attribution schema и tests assignment isolation, minimum-sample gate, owner approval и неизменность исторических отчётов. |
| AC-90 | §23.7 требует запретить рассинхрон ценника/price checker/кассы, отделить обязательные price fields от рекламы и блокировать публикацию без сверки с master; прежний `REQ-INT-002` требовал только source validation. | Зафиксировать price/SKU reconciliation contract, fail-closed states и negative tests на mismatch, изменение price field рекламным порталом и публикацию при недоступном master. |
| AC-91 | §23.7 допускает ESL production только после отдельного пилота с владельцем процесса ценников, ИБ, эксплуатацией и юристами; наличие adapter contract не является таким разрешением. | Добавить channel-activation gate для ESL с pilot evidence, четырьмя approval roles, exit criteria и запретом production rollout без полного набора решений. |
| AC-92 | §22.2 задаёт доступность административного портала не ниже 99,5% именно в рабочее время; простое число SLO без окна, denominator и исключений допускает разные трактовки качества. | Утвердить SLO schema с рабочим окном, denominator, maintenance/degraded exclusions и расчётным тестом Control Plane availability. |
| AC-93 | §17 требует для player systemd restart policy, локальный лог и health status; общий operational runbook и серверная health-панель не доказывают автономную диагностику player. | Зафиксировать player runtime health/log contract, restart/boot-loop policy и test на восстановление после сбоя с передачей статуса в Operations UI. |
| AC-94 | §22.11 требует классы данных, lawful purpose, minimisation, residency, encryption, access review, export/delete и incident notification; прежний `REQ-SEC-004` перечислял PII/retention без управляемого data-protection lifecycle. | Утвердить data-protection policy/schema, owner/legal evidence и negative tests на лишние PII, неверный residency, несанкционированный export/delete и секреты в логах/URL/payload. |
| AC-95 | §17 требует для Redis Sentinel/Cluster либо понятный сценарий восстановления; формулировка «Redis recovery» не задаёт production resilience и проверяемый failover. | Зафиксировать Redis topology/recovery contract, RTO/RPO и failover/restore drill с проверкой потери узла и сохранения безопасного поведения очередей/кэшей. |
| AC-96 | §13 перечисляет четыре emergency-действия: stop-реклама, системное сообщение, fallback и возврат к штатному manifest; общий emergency control без action enum допускает неполное или неоднозначное поведение. | Зафиксировать emergency action enum, scope/permission/confirmation/audit и contract tests для каждого действия, включая безопасный resume. |
| AC-97 | §13 требует emergency audit с actor, временем, уровнем применения, причиной, затронутыми объектами и результатом доставки; прежняя формулировка называла audit без обязательной структуры. | Утвердить emergency-audit schema, immutable storage и tests полноты полей/partial-result/scope, включая запрет записи без actor или reason. |
| AC-98 | §22.19 требует read-only advertiser UI, понятный регулярной работе и без ненужной технической терминологии; общий role-specific portal не доказывает изоляцию и язык интерфейса. | Зафиксировать advertiser route/content matrix, read-only authorization и UX review/ UI-smoke на отсутствие технических полей и блокировку mutation/API actions. |
| AC-99 | §6.2 требует в справочнике рекламодателей legal entity, brand, contacts и responsible persons; прежний commercial lifecycle перечислял advertiser/brand, но не полный обязательный набор реквизитов. | Утвердить advertiser schema, validation, scope/PII policy и tests обязательности реквизитов и изоляции контактов между рекламодателями. |
| AC-100 | §22.3 требует отдельный тип компенсационных размещений и запрет смешения с коммерчески проданным инвентарём без явной маркировки; прежний контракт описывал make-good, но не изоляцию типа размещения. | Зафиксировать compensation-placement enum, маркировку в inventory/report, owner policy и negative tests на неявное смешение paid и compensation inventory. |
| AC-101 | §22.4 требует, чтобы изменения правил приоритетов действовали с даты/времени изменения и не меняли исторические отчёты; версионирование без `effective_at` оставляет ретроспективную неоднозначность. | Добавить `effective_at`/timezone и immutable rule snapshots в priority schema; тестировать historical replay до/после изменения и запрет задним числом менять отчёт. |
| AC-102 | §22.8 требует logical delete для объектов, участвовавших в показах; физическое удаление допустимо только после retention и проверки legal/contract constraints. Общий archive/delete lifecycle не фиксировал эту границу. | Утвердить deletion-state/retention guard, legal hold и tests: объект остаётся доступен для historical replay после logical delete, а physical delete блокируется до окончания retention/hold. |
| AC-103 | §17 требует для backup расписание, шифрование, offsite-копию, retention, ответственного и регулярный restore drill; прежний `REQ-OPS-003` фиксировал DR/restore, но не полный operational contract. | Утвердить backup policy/schema, named owner и evidence по каждому компоненту; добавить tests расписания, encryption-at-rest, offsite recovery и периодического restore drill. |
| AC-104 | §17 требует для Device Gateway горизонтальное масштабирование, health-check, rate limiting и отдельные метрики; общий SLO Gateway не доказывает эти эксплуатационные свойства. | Зафиксировать Gateway topology/health/rate-limit/metrics contract и нагрузочный/failover test с масштабированием и сохранением emergency/PoP SLA. |
| AC-105 | §6.2 требует при замене креатива в live campaign новую версию и согласование; version/diff без approval gate допускает незаметную замену действующего контента. | Добавить transition rule `live → new-version → moderation/approval`, audit и negative test публикации новой rendition без повторного approval. |
| AC-106 | §9.2 требует, чтобы player/adapter не мешал фискальным операциям, кассам, проверке цены, ESL и штатной работе магазина; частичные channel-specific ограничения не покрывают общий safety invariant. | Зафиксировать non-interference contract и runtime/chaos tests на кассовые, price-check и ESL workflows при playback, restart, offline и emergency сценариях. |
| AC-107 | §21.6 требует тестировать наследование и переопределение плейлистов; прежний каталог перечислял playlist versions, но не задавал precedence/resolution contract. | Зафиксировать `REQ-MAN-005`, hierarchy/override schema и tests precedence, effective time, conflict, audit и historical reproducibility для network→branch→cluster→store/channel. |
| AC-108 | §24.11 требует для vendor API отдельные connector credentials, rate limit, журналирование, retry и circuit breaker; общий integration failure mode не фиксирует эти границы. | Утвердить vendor-connector contract, secret scope/rotation, rate-limit/retry/circuit-breaker policy, health/reconciliation и negative tests на credential leakage и retry storm. |
| AC-109 | §24.13 требует подключать новый канал через adapter/capability profile/renditions без переписывания кампаний, инвентаря, RBAC и отчётности; одного запрета импорта adapter недостаточно для архитектурной проверки. | Добавить extension test/architecture check, демонстрирующий подключение synthetic channel без изменений core business schemas/API и с сохранением существующих journeys/reports. |
| AC-110 | §23.3 требует таргетирование по каналу, типу носителя, торговой зоне, категории/SKU, полке и набору логических поверхностей с разрешением broad target до surface; общий hierarchy/surface boundary не перечислял все измерения. | Утвердить target schema/resolution matrix и tests для каждого измерения, включая недопустимый direct `physical_device_id` target и отсутствие orphan surfaces. |
| AC-111 | §23.3 требует моделировать один ESL gateway/LED controller с множеством логических носителей/поверхностей; простого списка устройств и surfaces без parent-child связей недостаточно для адресной доставки и SLA. | Зафиксировать physical→logical→surface ERD, независимые status/manifest rules и tests адресации одной поверхности без побочного изменения соседних carriers. |
| AC-112 | §24.5 перечисляет обязанности Orchestrator: разрешение target surfaces, simulation, версии задач/manifest, rollout и сбор delivery/apply/proof/error статусов; прежний `REQ-ORCH-001` фиксировал только simulation. | Утвердить Orchestrator responsibility contract и integration tests полного потока без channel-specific business logic и с сохранением статусов по каждой surface. |
| AC-113 | §24.9 запрещает прямые синхронные вызовы «portal → device/vendor» как основной механизм массовой публикации и требует событийную модель с очередями, retry и idempotency; queue contract без запрета direct path допускает блокирующий обход. | Зафиксировать event-driven delivery boundary, architecture check на отсутствие direct mass path и integration test с persisted queue, retry/DLQ и idempotent consumer. |
| AC-114 | §16.2 задаёт поэтапную интеграцию чеков: сначала batch агрегатов, затем регулярный approved API/ETL; простой список batch/API/ETL не фиксирует границы фаз и риск доступа к raw/fiscal данным. | Утвердить phase-1/phase-2 contract, data minimisation и reconciliation; добавить tests, что batch не затрагивает кассу/фискальный контур и API/ETL включается только owner-approved. |
| AC-115 | §6.3 требует показывать доступный/занятый/зарезервированный inventory по network, branch, cluster, store и device; прежняя формула упоминала только channel/surface и не фиксировала обязательные operational grains. | Зафиксировать inventory snapshot grain и API/report dimensions до device/logical carrier/surface, включая scope, freshness и tests согласованности агрегатов parent/child. |
| AC-116 | §24.11 требует полный жизненный цикл Channel Adapter: получить задание, подтвердить доставку, вернуть proof/ack/error и отдать health/status; прежняя карта называла adapter contract, но не фиксировала все обязательные результаты и запрет прямого доступа к хранилищам. | Утвердить versioned adapter contract, timeout/retry/idempotency/circuit-breaker и mock mode; добавить contract tests для receipt, delivery/apply proof, error, health/status и negative test на прямой доступ к PostgreSQL/ClickHouse/MinIO. |
| AC-117 | §23.5–§23.6 требуют видеть результат мультиканальной публикации по каждому каналу и поверхности, включая независимые SLA/proof и частичные ошибки; краткий `J-CHAN-001` не фиксировал операторскую последовательность и partial-failure semantics. | Добавить в journey и UI-smoke multi-channel happy-path с независимым progress/result для carrier/surface, повтором только failed tasks и тестом, что сбой одного канала не скрывает и не блокирует успешные каналы. |
| AC-118 | §22.2 требует, чтобы показатели качества были понятны бизнесу, ИТ и рекламодателю; перечень метрик без owner-facing definitions допускает разные трактовки одного SLA/proof. | Для каждого channel-quality metric утвердить definition, unit, numerator/denominator, freshness, owner и отображаемое объяснение; добавить report/UI tests на одинаковое толкование показателя тремя ролями. |
| AC-119 | §22.13 задаёт шесть различных ролевых рабочих контуров; одного общего `role-specific portal` недостаточно, если capability/data boundaries не проверяются для каждой роли. | Утвердить role→route→action→data matrix для рекламного менеджера, согласующего, аналитика, эксплуатации/ИТ, ИБ и рекламодателя; добавить positive/negative UI-smoke и authorization tests на разрешённые действия, read-only advertiser scope и запрет смешения коммерческих и operational/security данных. |
| AC-120 | §22.1 требует этап commercial proposal до reservation, а §22.12 — базовые коммерческие сущности и статус оплаты/подтверждения при необходимости; общий lifecycle и tariff-поля не гарантируют отдельный воспроизводимый offer и границу billing/ЭДО. | Утвердить proposal/quote schema (version, validity, inventory forecast, tariff/discount/package) и decision о payment/confirmation scope; добавить tests `proposal → reservation`, истечения версии, неизменности принятого предложения и запрета заявлять billing/ЭДО-факт без внешнего подтверждения. |
| AC-121 | §22.3 требует в отчёте рекламодателя plan, fact, процент выполнения, недопоказ, причины и компенсацию; прежний underdelivery-контракт не называл процент выполнения отдельным обязательным полем. | Зафиксировать формулу и округление `execution_percent`, отображение по кампании/каналу/периоду и tests деления при нулевом плане, частичного выполнения и неизменности закрытого отчёта. |
| AC-122 | §22.6 требует список магазинов, полностью выпавших из рекламной сети, и устройств, влияющих на активные кампании, с влиянием на forecast и underdelivery; одного health-фильтра без связи с бизнес-расчётом недостаточно. | Зафиксировать derivation и freshness этих списков, связь с campaign forecast/underdelivery и tests offline threshold, восстановления устройства и пересчёта затронутых кампаний без ложного изменения PoP-факта. |
| AC-123 | §22.10 перечисляет обязательные источники structured logs/metrics для backend, Gateway, PoP ingestion, Analytics, MinIO, PostgreSQL, ClickHouse, Redis и player; общий observability-contract не доказывает покрытие каждого компонента. | Утвердить telemetry matrix `component → schema → correlation fields → retention → owner → alert`; добавить schema/negative tests на обязательные поля, отсутствие секретов/PII и отсутствие «немого» компонента. |
| AC-124 | §23.8 требует operational-фильтры по типу носителя, версии player/adapter, магазину, зоне, статусу, manifest и ошибкам применения; наличие полей в карточке устройства не гарантирует их совместную фильтрацию и drill-down. | Зафиксировать filter schema, комбинации AND/OR, scope/RLS и сохранённые views; добавить UI-smoke/contract tests на каждый фильтр, их комбинации, пустой результат и переход к конкретному device/surface без потери scope. |
| AC-125 | §22.14 требует быстрый reset/seed demo-стенда для проверки фильтров, отчётов, прав, UI и бизнес-логики; слово «быстро» без time-bound target не является проверяемым критерием. | Утвердить target времени reset/seed, методику измерения и допустимый процент ошибок; добавить повторяемый drill, который измеряет восстановление до готовности smoke-набора и фиксирует seed version/commit. |
| AC-126 | §6.2 требует разделять отправку, согласование и публикацию, назначать обязательные роли и не допускать обхода approval; прежний `REQ-BIZ-003` не фиксировал self-approval, состав решения и возврат изменённого approved объекта на повторное согласование. | Утвердить approval matrix (role/scope/order/criteria), immutable decision schema и transition rules; добавить negative tests на self-approval, неполный набор решений, bypass API/UI и публикацию изменённой approved версии без повторного approval. |
| AC-127 | §6.1 и §22.13 вместе требуют разные контуры системного администратора, рекламного менеджера, модератора контента, согласующего, аналитика, оператора поддержки/эксплуатации, ИБ и рекламодателя; перечисление только «шести ролей» оставляло admin/moderator без обязательного UX-контракта и смешивало эксплуатацию с администрированием. | Утвердить полную role→route→action→data matrix, включая запреты модератора на device/user control и оператора на campaign mutation; добавить positive/negative RBAC/RLS/UI-smoke tests для каждой роли и проверку, что shared route не раскрывает чужие данные или действия. |
| AC-128 | §6.1 требует для системного администратора CRUD пользователей/ролей/устройств/настроек/мониторинга/аудита, но role-UX сам по себе не задаёт permission boundary, scope и запрет изменения approved campaigns. | Утвердить admin control-plane contract и связать каждую операцию с permission/scope/validation/audit; добавить negative tests на cross-scope CRUD, shared-account, privilege escalation и изменение approved campaign без отдельного права. |
| AC-129 | §6.1 требует MFA для администраторов, согласующих и пользователей с правом публикации/emergency; формулировка «критичные роли» допускает неполный или разный набор обязательных субъектов. | Утвердить MFA subject matrix и session policy; добавить negative tests входа/критичной операции без MFA для каждой перечисленной группы, а также проверку break-glass rotation и отсутствия shared accounts. |
| AC-130 | §6.1 требует ограничения по филиалам/кластерам/магазинам/рекламодателям и RLS; короткое «negative RLS matrix» не фиксировало уровни и направление наследования scope. | Утвердить scope hierarchy и object-authorization matrix для каждой роли и уровня, включая channel/device/surface и advertiser; добавить positive/negative tests на allow только вниз по scope, cross-tenant denial, отсутствие IDOR и полноту audit. |
| AC-131 | §7.1 требует антивирусную проверку и проверку структуры файла до допуска медиа; общий security-check в `REQ-CONT-001` не задавал обязательные стадии и fail-closed поведение. | Утвердить media-ingest pipeline `upload → malware scan → structural validation → QA`; добавить negative fixtures для malware, corrupted/container-bomb и executable payload и доказать отсутствие manifest/распространения до прохождения проверок. |
| AC-132 | §7.1 требует фиксировать размер, MIME, SHA-256, автора и версию файла, а также сохранять историю версий; краткое `REQ-CONT-002` не требовало uploader/author и source metadata. | Утвердить immutable media-version schema и tests полноты author/time/hash/source, связи superseded versions, logical delete/legal hold и исторической воспроизводимости отчётов. |
| AC-133 | §9.1 задаёт для KSO область показа 1440×1080 в левой части Full HD и скрытие рекламы при касании УКМ4 на настраиваемый период с default 30 секунд; размер и общий hide-on-touch без position/timeout допускают опасное перекрытие кассовой зоны. | Зафиксировать KSO geometry и timeout policy в capability/runtime schema; добавить hardware/behavioral tests на левую область, default 30 s, configurable override и восстановление показа без блокировки УКМ4. |
| AC-134 | §9.2 требует при потере связи сохранять последнее подтверждённое состояние ESL/LED шлюза или контроллера, а общий fallback-контракт не фиксирует этот channel-specific safety path. | Зафиксировать per-channel offline state policy для ESL/LED: last confirmed gateway/controller state, valid_to/offline TTL, fallback transition, no false PoP и chronological reconciliation после восстановления; добавить network-partition/restore tests. |
| AC-135 | §5 задаёт измеримые NFR: manifest ≤5 минут/95%, emergency ≤60 секунд/95%, PoP report ≤15 минут, автономность ≥7 дней, RTO ≤4 часа и RPO ≤15 минут; ранее они находились только в общей прозе. | Утвердить `REQ-NFR-007` и методики измерения для каждого target; добавить load/network-partition/restore evidence с denominator, percentile, exclusions и negative cases при нарушении latency/continuity budget. |
| AC-136 | §10 задаёт обязательные device statuses `online`, `offline`, `degraded`, `error`, `maintenance`, `revoked` и их операционные последствия; health-поля и команды без enum допускают разные трактовки SLA, показов и доступных действий. | Утвердить device-status enum/transition matrix, heartbeat thresholds и влияние каждого статуса на SLA, inventory, delivery и commands; добавить positive/negative tests переходов, включая revoked/maintenance и восстановление offline/degraded. |
| AC-137 | §22.3 расширяет причины недопоказа типовыми случаями: магазин закрыт, player/adapter не запущен, manifest не применён, истёк `valid_to`, кампания вытеснена приоритетом, ESL/LED не подтвердил применение; базовый PoP enum покрывал не все эти причины. | Расширить versioned failure taxonomy и mapping channel/runtime→reason, сохраняя исходную техническую причину и бизнесовую категорию; добавить tests агрегации plan/fact/underdelivery и запрет сворачивания distinct causes в общий `error`. |
| AC-138 | §14 требует передачу security/audit logs в SIEM/Wazuh, хранение критичных событий и защиту от удаления; общего поля «SIEM export» недостаточно для проверяемого security operations контура. | Утвердить SIEM/Wazuh (или owner-approved equivalent) integration contract: event schema, delivery/retry, immutable retention, access/audit и alert routing; добавить negative tests потери/подмены/удаления критичного события и evidence успешной доставки. |
| AC-139 | §9 и §23.2 требуют для каждого канала определить владельца, способ управления, player/adapter, capability profile, SLA, PoP-режим и ограничения контента; разрозненные REQ допускают неполную channel matrix и потерю обязательств при добавлении нового носителя. | Утвердить `channel-capability-matrix.yaml` с обязательными полями и статусом `baseline/pilot/production/deferred`; добавить schema/completeness tests для KSO, Android/TV, price checker, ESL, LED и synthetic channel, включая owner и proof/SLA mapping. |
| AC-140 | §23.2 требует для Android/Android TV/TV box автозапуск, kiosk/MDM режим, watchdog, локальный кэш, heartbeat/apply-ack и запрет внешних сетевых запросов; общей записи «Android player» недостаточно для эксплуатационной и security-приёмки. | Зафиксировать Android/TV runtime contract и capability fields; добавить device/chaos tests на reboot/autostart, watchdog recovery, offline cache, heartbeat/apply-ack и negative network test на outbound connection вне Gateway/vendor allow-list. |
| AC-141 | §23.2 требует для Android price checker idle/safe zones и interaction events при сохранении приоритета проверки цены; одного `idle_screen` proof недостаточно, чтобы доказать неблокирующее поведение. | Зафиксировать price-checker interaction contract (enter/exit idle, scan/search/touch interruption, resume) и mapping событий/PoP; добавить UI/device tests, что реклама немедленно уступает основному workflow, не меняет price fields и возобновляется только после безопасного idle. |
| AC-142 | §22.4 требует до публикации показывать результат simulation: число/список магазинов, ожидаемый объём показов, нехватку inventory, конфликты и кампании, которые будут затронуты вытеснением; общий `REQ-ORCH-001` не фиксировал обязательный output contract. | Утвердить simulation result schema с grain/TZ и reason codes; добавить positive/negative tests для достаточного и дефицитного inventory, priority preemption, conflict и partial target scope, а UI должен показывать последствия до подтверждения публикации. |
| AC-143 | §22.4 требует формализованные и настраиваемые через административный интерфейс правила приоритетов с версионированием; одного versioned priority data model недостаточно, если изменение нельзя безопасно выполнить и проверить через UI. | Утвердить priority-admin route/permission/effective-time contract; добавить UI/API tests на изменение и публикацию версии, запрет несанкционированного редактирования, audit/diff и воспроизводимость preemption до и после effective_at. |
| AC-144 | §8.2 требует в `media_files[]` ссылку/ключ, размер и тип файла помимо SHA и длительности; прямой MinIO key несовместим с запретом раскрывать storage topology в device-facing API. | Утвердить manifest media-file schema (`media_ref`, `size_bytes`, `mime_type`, `sha256`, `duration`) с server-side mapping `media_ref → private object`; contract tests проверяют missing/invalid values, private-object access, short TTL и отсутствие paths/object keys/internal IDs в manifest, ACK, PoP и ошибках. |
| AC-145 | §8.1–§8.2 требуют в manifest явные правила показа: duration, order/weight, schedule и priority; перечисление отдельных полей без нормализованного `rules[]` допускает неоднозначное разрешение playlist. | Утвердить `rules[]` schema с precedence, schedule/timezone, duration, order/weight и priority; добавить contract tests конфликтующих правил, deterministic resolution, effective window и воспроизводимости manifest для одной и той же версии входных данных. |
| AC-146 | §22.3 определяет недопоказ как plan/fact ниже допустимого порога выполнения; plan/fact без versioned threshold policy не позволяет воспроизводимо решить, когда возникает underdelivery и make-good. | Утвердить underdelivery threshold schema (metric, threshold, unit, scope, effective_at, owner) и tests граничных значений, нулевого плана, разных каналов и неизменности решения после закрытия отчёта. |
| AC-147 | §22.3 требует автоматически предлагать докрутку (дни, магазины, слоты, компенсационный объём), но предложение не должно само менять placement или финансовое обязательство; драфт не фиксировал explainability и owner confirmation. | Утвердить make-good recommendation schema с input facts, alternatives, расчётом и reason; добавить tests, что рекомендации read-only до owner approval, не меняют inventory/финансы автоматически и сохраняют выбранный/отклонённый вариант в audit. |
| AC-148 | §1.2 перечисляет бизнес-цели (единый контроль, централизованное управление и безопасная эксплуатация), но исходное ТЗ не задаёт для них baseline, target и методику измерения; наличие функций само по себе не доказывает бизнес-результат. | Утвердить `REQ-BIZ-013`: для каждой цели определить metric/unit, baseline, target, window, source, owner и review date; добавить evidence раздельно от технических SLO и запретить claim о достигнутом outcome без утверждённой методики. |
| AC-149 | §19 требует сквозную приёмку для КСО, Android/TV, price checker, ESL и LED; наличие отдельных adapter-контрактов или capability-полей не доказывает реальную доставку, применение и доказательство результата на каждом типе носителя. | Для каждого baseline/pilot-канала выполнить end-to-end сценарий `campaign → manifest/adapter payload → delivery → apply/label/controller ACK → channel-specific proof → report`, с positive/negative evidence, ограничениями контента и подтверждением отсутствия влияния на основную торговую функцию; synthetic/mock канал не заменяет реальные профили. |
| AC-150 | §15 задаёт обязательные группы таблиц и аналитических событий, но общий `REQ-DATA-001` не препятствовал неполному ERD или потере ESL/LED/channel-event сущностей. | Утвердить `REQ-DATA-002` и schema-check, который сверяет ERD/data dictionary/migrations с полным entity inventory исходника, включая связи, владельца данных и retention class; отсутствие любой группы блокирует design gate. |
| AC-151 | §16 перечисляет обязательные API-группы (auth/RBAC, hierarchy, advertisers, campaigns/placements/inventory, media, Device Gateway, analytics, emergency, audit, channels/player builds и ESL/LED integrations); общего требования «есть OpenAPI» недостаточно для контроля полноты поверхности. | Сверить versioned OpenAPI/event registry с полным перечнем групп и endpoint-каталогом §16; для каждой операции зафиксировать request/response, auth/scope, ошибки, idempotency, pagination/filtering, deprecation и owner, а отсутствие группы или undocumented endpoint блокирует API gate. |
| AC-152 | Драфт заявляет 149 строк-кандидатов, но воспроизводимый подсчёт маркеров в текущем extracted source даёт другое число в зависимости от включения `обязательн*`; без единого classifier это неподтверждённая метрика полноты. | Утвердить canonical classifier (маркеры, исключения заголовков/пояснений, правила split 1:N), сохранить его версию и машинный отчёт `source_line → obligation_id → disposition`; до этого число нормативных строк считать `UNVERIFIED` и не использовать как coverage KPI. |
| AC-153 | Проектный контракт требует валидный actor UUID для административного аудита, но общий audit envelope допускал `actor_id: uuid-or-string` без различения пользователя, сервиса, устройства и vendor; это позволяет потерять связь критичного действия с конкретной учётной записью. | Разделить `actor_type` и формат идентификатора: для user — существующий UUID из identity store и проверка соответствия session subject; для service/device/vendor — зарегистрированный credential identity; добавить negative tests на отсутствующий, чужой, невалидный или подставной actor ID и проверку неизменяемости записи. |
| AC-154 | §8.2 исходника называет URL/MinIO key, но `AGENTS.md` запрещает device-facing API раскрывать внутренние storage keys, paths и IDs; прямое выполнение исходной формулировки создало бы утечку внутренней топологии хранения. | Зафиксировать compatibility mapping: server-side object key → opaque `media_ref`/short-lived signed fetch reference; device получает только безопасную ссылку, срок/политику доступа и SHA, а object key не появляется в manifest, ACK, PoP, логах или ошибках; добавить negative tests на path/key/ID leakage и истечение TTL. |
| AC-155 | `manifest` и PoP обязаны ссылаться на device/store/surface, но внутренние database IDs запрещены в device-facing API; без отдельного правила можно раскрыть последовательные ключи, tenant IDs или служебные идентификаторы. | Для всех device/vendor payloads определить opaque external identifier schema с tenant/scope binding и невозможностью enumeration; добавить negative tests на integer/internal IDs, cross-scope substitution, IDOR, paths, tokens и secrets в manifest, ACK, PoP, error и логах. |
| AC-156 | Проектный контракт требует, чтобы RLS использовал аутентифицированного пользователя; одной декларации scope hierarchy недостаточно, если фильтр берёт scope из client-supplied параметра или неиспользуемой dependency. | Добавить runtime tests, где authenticated principal имеет один scope, а запрос подставляет другой: API, service и SQL/RLS обязаны применить только session-derived scope; negative tests на bypass через query/body/header и audit записи deny. |
| AC-157 | `AGENTS.md` требует отсутствия drift между portal/backend RBAC, но драфт не требовал сравнивать frontend guards с backend permission-кодами как единый контракт. | Утвердить permission parity matrix и автоматическую проверку route/action → backend permission/scope; UI не должен показывать доступное действие, которое API отклонит, и API не должен принимать действие, не представленное разрешённым UI-контуром (кроме документированных service/API clients). |
| AC-158 | ADR-007 откладывает ClickHouse до Phase 4+, но драфт одновременно требовал его как обязательный runtime для Phase 1 и production HA; это противоречие могло привести к несанкционированному включению инфраструктуры и неверному статусу готовности. | Разделить operational PostgreSQL и deferred ClickHouse по фазам, зафиксировать activation gate, backfill/dual-read-or-write plan, owner approval и отдельные SLO/evidence; Phase 1 не зависит от запущенного ClickHouse, а после активации требуется проверка исторической воспроизводимости и rollback. |
| AC-159 | ADR-002 фиксирует NATS JetStream как production event-bus baseline, но прежний `DEC-004` оставлял выбор брокера открытым; это позволяло незаметно заменить транспорт и изменить delivery semantics. | Закрепить NATS JetStream baseline, durable streams/consumer groups/replay/DLQ и operational thresholds; альтернативный broker допускается только через ADR amendment, compatibility/migration/rollback analysis и owner approval. |
| AC-160 | ADR-017 требует `event_type=proof` и двойную привязку `event.device_id` к JWT subject и manifest physical device; прежний PoP-контракт проверял только JWT subject. | Добавить contract/negative tests на wrong event type, device mismatch с JWT, чужой manifest, cross-device replay и корректный fallback `emit_pop`; принять событие только при полном совпадении binding и не завышать отчёт. |
| AC-161 | ADR-011 требует transactional outbox для каждого domain event как side effect OLTP-записи, а драфт ограничивал outbox только delivery-relevant mutations; это оставляло audit/status/approval events без гарантии доставки и replay. | Зафиксировать outbox для всех business domain events, исключив только telemetry без business state; добавить architecture/transaction tests на atomic write+outbox, direct publish prohibition, relay ack, replay, ordering и DLQ. |
| AC-162 | После фазовой правки ClickHouse отдельные формулировки backup и observability всё ещё могли трактоваться как обязательные для Phase 1, несмотря на ADR-007 deferred runtime. | Во всех operational разделах явно пометить ClickHouse как `deferred until activation`; Phase 1 evidence покрывает PostgreSQL path, а ClickHouse topology/backup/telemetry проверяются отдельным activation gate и не блокируют текущий runtime. |
| AC-163 | Проектный контракт запрещает portal pages с неотмеченными или вымышленными данными; драфт описывал demo stand, но не отделял его источник данных от production backend. | Добавить environment/data-source contract и UI-smoke: production/shared DEV читают только backend APIs; synthetic seed разрешён лишь на стенде и имеет явный `DEMO`/environment indicator; negative test на fallback к hard-coded/demo payload при недоступном backend. |
| AC-164 | Критический риск проекта: migration configuration может использовать невалидный DB URL или не загружать model metadata, при этом документальные ERD/REQ останутся зелёными. | Добавить migration/config gate: валидный URL для каждого окружения, import всех моделей в metadata, `upgrade` и `downgrade` на чистой и существующей БД, readiness check PostgreSQL и negative tests на placeholder/owner URL; failure блокирует deployment и соответствующий REQ не считается done. |
| AC-165 | `CLAUDE.md` запрещает считать SQLite, source inspection или superuser-сессию доказательством RLS; драфт требовал behavioral RLS proof, но не фиксировал реальную роль и отсутствие `BYPASSRLS`. | RLS acceptance выполнять на PostgreSQL под runtime-role `retail_media_app` с `NOBYPASSRLS`/`FORCE ROW LEVEL SECURITY`, с positive/negative scope tests и проверкой пустого scope → deny-all; SQLite, superuser и статический grep не принимаются как evidence. |
| AC-166 | UI Done Gate требует state-based browser waits; общая формулировка «реальные клики» не запрещала `sleep`, timing hacks и retry loops, скрывающие нестабильность. | Утвердить UI-smoke policy: ожидать visibility/enabled/network-idle/expected-text состояния, запрещать `sleep`, фиксированные задержки, swallowed failures и retry loops; negative test должен завершаться диагностируемым failure, а не искусственным green. |
| AC-167 | `CLAUDE.md` запрещает делать pipeline зелёным через `skip`, `xfail`, `deselect`, ослабленные assertions, `continue-on-error`, swallowed exit codes или перестановку шагов; в драфте это не было отдельным acceptance invariant. | Утвердить CI/test integrity gate: запрещены перечисленные обходы и narrowing test selection; каждый failure сохраняет ненулевой exit code и видимый результат, а tamper-test должен краснеть при попытке замаскировать обязательную проверку. |
| AC-168 | `CLAUDE.md` требует брать CI-команды verbatim из workflow и запускать piped commands с `pipefail`; локальный эквивалент или pipeline, возвращающий код последнего успешного этапа, не доказывает CI-приёмку. | Зафиксировать command-provenance policy: evidence ссылается на точный workflow command и CI run SHA; локальные прогоны маркируются только как вспомогательные, для pipe используется `set -o pipefail`, а tamper-test ловит замену команды или скрытый upstream failure. |
| AC-169 | ADR-008 требует negative behavioral proof для auth/RBAC/RLS/tenant isolation, rate limiting и audit integrity; статические проверки и положительные happy-path тесты не доказывают отказ при нарушении границ. | Для каждой security-critical фазы добавить runtime negative matrix: 401 без JWT, 403 без permission/при wrong role, cross-tenant deny, 429 после лимита и фактическая запись audit event; static/source checks считаются только supplementary и не закрывают phase gate. |
| AC-170 | ADR-003 задаёт конкретный device lifecycle, а прежний REQ-SEC-003 сводил его к словам «mTLS, credentials, revoke, rotation», не проверяя enrollment, proof-of-possession, replay и границы токенов. | Добавить behavioral/contract matrix: one-time code и fingerprint (повтор/подмена отклоняются), HMAC nonce и replay-cache, JWT/refresh TTL и rotation с инвалидированием старого refresh, revoke с fail-closed доступом и ≤15-min expiry active JWT, encrypted credential storage, отсутствие JWT в URL, audit каждой выдачи/ротации/отзыва; mTLS/PKI остаются отдельным activation gate и не выдаются за реализованные в Phase 1–3. |
| AC-171 | ADR-006 задаёт три разных identity-типа, LDAPS-only для internal staff, локальный advertiser lifecycle и конкретную cookie/session/rate-limit политику; прежний REQ-SEC-001 перечислял только AD/SSO/MFA и мог допустить смешение контуров. | Зафиксировать identity matrix и behavioral evidence: LDAPS TLS и отказ plain LDAP, отказ входа при недоступном AD кроме break-glass, максимум двух вручную созданных break-glass accounts с CRITICAL audit, advertiser invite/register/reset без enumeration, bcrypt policy, JWT 15 min + rotating HttpOnly Secure SameSite refresh 8 h, logout/admin revoke, no local/session storage or URL tokens, login/reset rate limits (5/15 min и 3/hour), universal errors и correlation ID во всех auth/audit events. |
| AC-172 | ADR-009 отдельно предупреждает, что NATS/orchestrator/PoP/adapter workers обходят FastAPI middleware; без обязательного transaction-local context они могли работать с пустым или привилегированным scope и нарушить tenant isolation. | Добавить worker-RLS matrix: каждый worker transaction устанавливает `SET LOCAL` context до tenant query; system-scoped операции разрешены только зарегистрированному service identity и аудируются, job-derived scope проверяется по payload и не расширяется; runtime DB role — `NOBYPASSRLS`, не superuser; negative tests на отсутствие context, подмену job scope, stale pooled connection и cross-tenant publish/read. |
| AC-173 | ADR-018 требует двухуровневую tenant-модель, но прежний entity inventory не делал `retailers` и физический `retailer_id` обязательными; один только app-layer scope оставлял single-retailer схему и риск cross-retailer leakage. | Утвердить `retailers` как tenant root, `retailer_id NOT NULL` + FK на всех tenant-таблицах, backfill существующих строк в owner-approved default retailer, membership-derived `app.rmp_scope_retailer_ids` вместе с advertiser scope и RLS predicate `retailer AND advertiser`; добавить migration/schema/behavioral tests на cross-retailer advertiser/campaign/placement/device доступ и fail-closed при пустом retailer scope. |
| AC-174 | Исходное ТЗ §22.12 требует финансовые сущности и статус оплаты/подтверждения, но условная формулировка `REQ-BIZ-009` могла скрыть отсутствие решения за словами «если разрешено хранить». | До переноса в roadmap принять отдельный decision по каждой финансовой сущности: in-scope с owner, schema, versioning, scope, audit и reconciliation evidence либо approved-exclusion с DEC-ID, причиной, trigger и review date; negative acceptance запрещает billing/ЭДО/выручку в UI и отчётах без подтверждённого внешнего источника и immutable basis. |
| AC-175 | ADR-011 определяет relay claim/lease, статусы `pending/publishing/published/failed/dead_letter`, `Nats-Msg-Id`, максимум повторов, partition ordering и retention, но прежний REQ-ORCH-004 оставлял эти эксплуатационные свойства неявными. | Добавить integration tests: конкурентные relay не дублируют claim, истёкший lease восстанавливается, broker ack предшествует `published`, crash между ack и UPDATE безопасно повторяется, transient failure достигает `dead_letter` после 7 попыток, partition сохраняет порядок без обещания global order, cleanup не удаляет неистёкшие published/DLQ записи и payload проходит secret/PII scan. |
| AC-176 | ADR-015 требует обязательную связь campaign с advertiser contract и проверку flight window против срока договора; прежняя формулировка позволяла создать кампанию без финансового основания или с показом после истечения договора. | Добавить schema/behavioral tests: `advertiser_contract_id` обязателен и принадлежит тому же advertiser/retailer, `brand_id` проверяется по tenant, flight вне `valid_from/valid_until` отклоняется на create/update/submit/reservation, бессрочный договор принимает только даты после `valid_from`, а изменение договора/flight не переписывает утверждённую историю и создаёт audit/version. |
| AC-177 | Исходное ТЗ требует inventory reservation, но прежний `REQ-BIZ-001` не фиксировал атомарность commit и поведение при конкурентной продаже; это допускает double-booking при двух одновременных запросах. | Утвердить reservation schema с version/lock или эквивалентным serializable guard, атомарными `reserve → commit/release`, idempotency key и audit; добавить concurrency tests на два запроса к одному слоту, повтор idempotency key, истечение резерва, rollback и корректные parent/child capacity snapshots; при выключенном overbooking второй commit обязан получить явный conflict/sold-out, а не aggregate success. |
| AC-178 | `REQ-SEC-006` перечислял классы атак, но не задавал проверяемые границы входов, SSRF egress, CSRF/CORS/security headers, rate-limit semantics и IDOR prevention; статический security scan не доказывает runtime отказ. | Утвердить API security profile и runtime negative matrix: oversized/deep payload, SQL injection, XSS/script, CSRF/origin mismatch, disallowed CORS, SSRF на loopback/private/link-local/metadata и redirect, IDOR/cross-scope object substitution, rate-limit burst с `429/Retry-After`, bypass через alternate method/header; успешные запросы сохраняют scope и audit, секреты/PII отсутствуют в logs/errors. |
| AC-179 | `US-SEC-001` ссылался на `J-SEC-001`, но journey был определён только prose-строкой и отсутствовал в канонической таблице шаблонов; это позволяло потерять actor/steps/evidence при генерации portal matrix. | Внести `J-SEC-001` в canonical journey registry с MFA, видимыми действиями, permission/scope, negative path, UI-smoke, SIEM export и operator walkthrough; проверить story→journey→REQ связку и отсутствие orphan journey при машинной генерации. |
| AC-180 | Шаблон требовал user story для каждого REQ, хотя технические/архитектурные REQ не являются пользовательскими функциями; это создавало ложные orphan либо фиктивные истории. | Ввести `coverage_type` и реестр `SC-*`: business REQ обязаны иметь story+journey, technical/security/operational/governance REQ — technical scenario с owner/evidence; машинная проверка должна покрывать оба класса и запрещать REQ без coverage reference. |
| AC-181 | После введения `scenario_ids` YAML-шаблон ссылался на `SC-ARCH-001`, но пример сценария не был определён; автоматическая проверка могла принять техническое REQ с orphan coverage reference. | Определить canonical scenario contract и правило разрешения `SC-*` ссылок; пример `SC-ARCH-001` хранить как illustrative baseline, а перенос в roadmap разрешать только после заполнения source/owner/evidence и отдельной task-связки. |
| AC-182 | Раздел AE называл 149 и диапазон 148–164, тогда как сырой marker scan источника даёт 180 совпадений; без разделения raw scan и normalized classifier это создавало ложное ощущение подтверждённого count. | Явно маркировать 180 как необработанный upper-bound scan, оставить итог `UNVERIFIED` до классификатора, сохранить source line для каждой строки и разложить составные предложения на атомарные REQ/DEC/EXCLUSION/PROCESS; любой count без этого отчёта не использовать в acceptance или roadmap. |
| AC-183 | Исходное ТЗ использует `{id}`, ADR-015 — `{code}`; без canonical identifier contract клиенты и UI могли обращаться к разным ресурсам, а authorization/deprecation semantics расходились. | Утвердить canonical opaque resource identifier и одну форму URL в каждой API-версии; compatibility alias разрешён только с теми же scope/auth/idempotency checks, documented deprecation date, OpenAPI examples и migration/negative tests на PK enumeration, cross-resource substitution и расхождение `{id}`/`{code}`. |
| AC-184 | ADR-009 задаёт union нескольких явно назначенных scope, но прежний `REQ-SEC-002` не запрещал реализацию intersection или implicit global при отсутствии scope; сервисы могли выдавать разные наборы данных. | Зафиксировать union semantics, deny-all при пустом scope и запрет расширения scoped role до global; добавить positive/negative tests для нескольких branch/advertiser scopes, смешанных измерений retailer+advertiser, отсутствующего scope и попытки подмены scope в query/body/header. |
| AC-185 | Story→journey map содержала ссылки на исторические `J-PORTAL-*`, отсутствовавшие в машинном реестре, а `SC-ARCH-001` был только prose-примером. | Ввести проверяемый alias registry и canonical `SC-*` registry; генератор обязан разрешать alias, отклонять неизвестные IDs и требовать owner/evidence для технического сценария. |
| AC-186 | Черновые `J-*` IDs не соответствуют обязательному формату project journey `<domain>.<action>` из AGENTS.md и могли быть ошибочно перенесены в feature-registry/UI-smoke. | Хранить `J-*` только как design-scenario IDs; в traceability/registry/тестах использовать dot-case IDs, а отсутствующие project journeys помечать `PENDING` до добавления в canonical user-journeys. |
| AC-187 | Story→journey map после исправления ссылок всё ещё может создать ложное UI-покрытие: dot-case ID в драфте не означает, что он уже есть в каноническом `user-journeys.md`. | Проверять наличие каждого dot-case ID в canonical user-journeys, соответствующего UI-smoke и operator walkthrough; неподтверждённые IDs оставлять `PENDING` и не считать бизнес-фичу готовой. |
| AC-188 | Независимая сверка с текущим `user-journeys.md` показала 27 целевых journey-ID, которых там ещё нет: `admin.manage`, `advertiser.onboard`, `analytics.compare`, `audit.compare`, `campaign.close`, `campaign.readiness`, `campaign.schedule`, `campaign.underdelivery`, `carrier.manage`, `channel.register`, `channel.rendition_validate`, `commerce.manage`, `creative.moderate`, `data.catalog`, `device.diagnose`, `dr.restore`, `experiment.evaluate`, `finance.reconcile`, `integration.reconcile`, `inventory.priority`, `inventory.rule_manage`, `kpi.review`, `license.manage`, `release.rollback`, `reports.view`, `rollout.rollback`, `security.review`. | Добавить эти journeys в канонический документ только с реальными route, `data-testid`, Given/When/Then, UI-smoke и operator walkthrough; до этого явно хранить статус `PENDING` и не считать соответствующие REQ покрытыми. |
| AC-189 | В story map были представлены только 5 из 13 бизнес-REQ; `REQ-BIZ-005/006/007/008/010/011/012/013` оставались без отдельной user story и целевого journey. | Добавлены US-FLT/ELG/PRI/UDR/WFL/RPT/AB/KPI и dot-case journeys; зарегистрировать их в canonical `user-journeys.md`, feature-registry и UI-smoke либо получить owner-approved exclusion. |
| AC-190 | Таблица каталога содержит только ID/название/source и не несёт построчных `coverage_type`, story/journey или scenario refs; общий YAML-шаблон не доказывает покрытие всех 80 REQ. | Сгенерировать `requirements-traceability.yaml` из каталога с обязательными coverage-полями для каждого REQ и машинно проверить отсутствие orphan/duplicate/неразрешённых ссылок до `APPROVED`. |
| AC-191 | API inventory одновременно показывал `/device/v1/pop/batch` и канонический ADR-017 `/api/v1/pop/batch`, что позволяло реализовать два разных PoP-контракта. | Оставить `/api/v1/pop/batch` единственным canonical endpoint; любой `/device/*/pop` путь допускается только как versioned alias с одинаковыми auth, dedupe, signature и deprecation tests. |
| AC-192 | При переходе на versioned device API четыре legacy route из v2.5 могли исчезнуть из traceability и быть удалены без миграции старых плееров. | Явно перечислить `/device/register`, `/device/heartbeat`, `/device/manifest`, `/device/capabilities` как временные aliases и закрыть их owner/deprecation/migration evidence до удаления. |
| AC-193 | Сводный changelog не содержал обязательных REQ/roadmap ссылок, хотя соседнее правило требовало их для каждой записи. | Разделять summary и полный changelog; каждая полная запись должна иметь reason, affected REQ-ID, roadmap task, compatibility impact, date и evidence. |
| AC-194 | §21.8 исходного ТЗ требовал обязательный pre-change mini-design, отчёт по каждому шагу и синхронное обновление OpenAPI с backend-кодом; прежний `REQ-GOV-001` оставлял это слишком общим. | Зафиксировать process checklist и gate: mini-design до изменения, атомарный code+OpenAPI diff, migration/test results, commit/evidence и owner approval для изменения архитектуры, API, security или business logic. |
| AC-195 | YAML-шаблон REQ не содержал `roadmap_ids`, delivery status и implementation owner; требование могло попасть в каталог без задачи и без отображения фактической работы. | Сделать эти поля обязательными, синхронизировать их с roadmap/registry и запретить `APPROVED` при `TBD`, пустой task-связи или несогласованном статусе. |
| AC-196 | Исторический snapshot перечислял `planned / in_progress / verification / done / deferred` как обычную строку, а не enum; после добавления `blocked` такой snapshot нельзя использовать как текущий полный список. | Валидировать единый актуальный enum (`planned`, `in_progress`, `verification`, `done`, `blocked`, `deferred`) и добавить schema-negative test на pipe-строку, пустое и неизвестное значение; исторические перечисления маркировать snapshot. |
| AC-197 | В audit/decision YAML-примерах enum/type-нотация через вертикальную черту и `string-or-null` могла быть принята за готовые значения и обойти runtime validation. | Хранить в примерах конкретные scalar/null значения, а enum/type ограничения задавать отдельным schema rule и negative tests. |
| AC-198 | §21.9–§21.10 требуют в каждом отчёте точные команды, commit message/номер, остаточные риски и запрет секретов в репозитории; прежнее process-описание не перечисляло эти поля явно. | Сделать поля обязательными в step-report template, запускать secret scan и блокировать при отсутствии commit/evidence или при найденном секрете. |
| AC-199 | Audit YAML example содержал литералы `uuid`, `timestamp`, `string` и `retailer/branch/...`, которые были type-нотацией, но выглядели как допустимые данные. | Использовать безопасные примерные значения, а типы/enum валидировать схемой; добавить negative tests на placeholder literals и неверный формат UUID/timestamp. |
| AC-200 | Reverse-traceability scan обнаружил 57 строк с нормативными маркерами вне REQ-каталога и без inline REQ-ID; они могут быть скрытыми обязательствами или не-нормативными пояснениями. | Для каждой строки назначить REQ-ID, DEC-ID, PROCESS-ID или `NON-NORMATIVE`; сохранить source line и disposition в отчёте, а необозначенные строки блокируют `APPROVED`. |
| AC-201 | Decision-register template содержит `...` и `YYYY-MM-DD`, которые могут быть ошибочно выданы за заполненное owner decision/evidence. | Явно маркировать шаблонные placeholders и отклонять их при `status: approved` или при попытке разблокировать REQ; добавить schema-negative tests. |
| AC-202 | Исторически внешний monitoring-dashboard был описан без адресуемой ссылки; последующая редакция ошибочно внесла runtime IP в нормативный текст. | В r417 нормативный ТЗ хранит только read-only/non-authoritative контракт; изменяемый endpoint переносится в environment inventory/operator config, availability/freshness проверяются отдельно, повышение статуса по dashboard запрещено. |
| AC-203 | `PROCESS-ID` был разрешён в reverse-traceability, но не имел формата и реестра; им можно было скрыть нормативную строку без проверяемого владельца и доказательства. | Ввести `PROCESS-*` registry с `source/owner/steps/evidence/review_on` и отклонять неизвестные или пустые process IDs как orphan. |
| AC-204 | В драфте уже возникали рассинхронизации acceptance count, незакрытые fences и некорректные Markdown-таблицы; общий review checklist не требовал этих структурных проверок. | Добавить автоматические checks: balanced fences, равное число колонок таблиц, YAML parse, metadata revision = changelog и max AC = итоговой строке; любой mismatch блокирует `APPROVED`. |
| AC-205 | Верхний changelog содержал фрагменты старых записей и устаревшие AC-пределы, из-за чего metadata была неоднозначной. | Хранить в metadata только одну актуальную summary-запись, а полный changelog — отдельным артефактом с REQ/roadmap ссылками; проверять отсутствие устаревших пределов. |
| AC-206 | §21.6 требовал конкретные тесты ключевой бизнес-логики, но драфт не перечислял полный обязательный набор и мог ограничиться техническими endpoint-тестами. | Зафиксировать test matrix в `REQ-GOV-001`, связать каждую зону с positive/negative evidence и блокировать шаг при отсутствии проверки любой зоны. |
| AC-207 | Исторические инструкции §21 называли Hermes implementation agent, что конфликтует с действующим AGENTS.md и могло вернуть retired automation в рабочий процесс. | Явно закрепить Claude Code как единственного implementation agent, Codex как reviewer, Hermes как historical/retired; runtime/product dependency на LLM запрещена. |
| AC-208 | Исторический snapshot самопроверки показывал 22 отсутствующих project journeys; после последующих редакций текущий diff иной. Незакрытыми остаются нормализованный source-classifier, owners/dates, canonical journey reconciliation и построчная REQ→roadmap связь. | До `APPROVED` выпускать report с SHA/датой и актуальным списком disposition каждой обязанности и journey; назначить owner/review date, добавить недостающие journeys с UI-smoke/operator walkthrough и сгенерировать traceability manifest REQ→story/scenario→journey→roadmap task→evidence. |
| AC-209 | Шаблон и жизненный цикл смешивали зрелость требования (`proposed/approved`) с ходом реализации (`planned/in_progress/verification/done`), поэтому `done` мог быть истолкован как одобрение самого REQ. | Ввести независимые `requirement_status` и `delivery_status`, запретить `delivery_status: done` для неодобренного REQ и требовать roadmap task только после `requirement_status: approved`; обновить переходы и проверки статусов. |
| AC-210 | После разделения статусов self-check перечислял обязательные поля, но не требовал машинно проверять несовместимые пары (`proposed+done`, `approved` без task перед `planned`) и не указывал источник перехода. | Для каждой записи валидировать статусную пару и переходы, хранить actor/status_changed_at/commit или evidence ref; добавить negative tests на несовместимые пары и блокировать `APPROVED` при нарушении. |
| AC-211 | В section map и каталогах использовалась slash-сокращённая запись нескольких REQ-ID (`REQ-<DOMAIN>-<NNN>/<NNN>`), которая не разрешается как уникальная ссылка и могла скрыть orphan requirement при автоматической проверке. | Использовать только полные comma-separated REQ-ID во всех reference tables; validator отклоняет slash-сокращения и проверяет разрешение каждого ID. |
| AC-212 | `requirement_status` в YAML-шаблоне допускал только `proposed/approved`, хотя правила жизненного цикла требуют терминальные `rejected/superseded`; это делало корректную disposition-запись невалидной. | Расширить enum до значений `proposed`, `approved`, `rejected`, `superseded`; требовать причину для `rejected` и заменяющий REQ-ID для `superseded`, а такие требования исключать из roadmap и `done`-метрик. |
| AC-213 | Исторический snapshot каталога содержал 80 REQ-ID; текущий драфт расширен, но полноценного атомарного реестра по-прежнему нет: у требований отсутствуют собственные owner, requirement/delivery status, acceptance, evidence, dependencies и roadmap task. Один YAML-пример не доказывает заполненность остальных требований. | Создать versioned `requirements-traceability.yaml` с одной записью на каждый текущий REQ-ID и обязательными полями; валидировать отсутствие пустых/TBD полей для `APPROVED`, orphan/duplicate ссылок и синхронизацию с roadmap, stories/scenarios, journeys и evidence. |
| AC-214 | Правило жизненного цикла требовало историю переходов (`status_changed_at`, actor, commit/evidence), но YAML-шаблон её не содержал; переходы нельзя было бы аудировать или связать с конкретным состоянием Git/CI. | Сделать `status_changed_at`, `status_actor` и commit/evidence ref обязательными полями каждой записи и каждого перехода; запретить `APPROVED`/`done` без непрерывной истории. |
| AC-215 | Metadata задавала статус документа `DRAFT → REVIEW → ACCEPTED → APPROVED`, но не различала owner acceptance содержания и approval полного evidence-пакета; это позволяло считать принятую прозу готовой редакцией. | Зафиксировать отдельный document-state contract: критерии `REVIEW → ACCEPTED` и `ACCEPTED → APPROVED`, обязательные owner decision/SHA и артефакты, запрет понижения без changelog и независимость от roadmap/monitoring status. |
| AC-216 | В acceptance-таблице enum с вертикальными разделителями создал лишние Markdown-колонки; структурная проверка могла пропустить такой дефект без явного требования к каждой таблице. | Проверять равное число колонок во всех Markdown-таблицах и не использовать необработанный вертикальный разделитель внутри ячеек; enum записывать comma-separated или экранировать. |
| AC-217 | После первой правки структурный скан всё ещё находил необработанный вертикальный разделитель в формулировке самого AC-216, то есть проверка могла быть сломана собственным диагностическим текстом. | Acceptance-описания и диагностические примеры также включать в table-column lint; использовать текстовые названия разделителей или экранировать их. |
| AC-218 | После серии self-review правок revision metadata и active changelog могли отставать от фактического содержательного состояния документа. | При каждом содержательном изменении сверять Revision, active changelog и максимальный AC-ID одним structural check; исторические записи хранить вне active summary. |
| AC-219 | User refresh (ADR-006, 8 h) и device refresh (ADR-003, 24 h) были названы одинаково без явного audience, что допускало перенос более длинной device-политики в пользовательские сессии. | Явно маркировать user/device token-контуры в REQ, схемах, claims, cookie/protocol fields, rotation/revoke tests и acceptance evidence; политики не взаимозаменяемы. |
| AC-220 | Summary-таблица `US-*` содержала только роль, текст и результат; у историй не было построчных `permission_code`, `scope`, `journey_id`, `positive/negative path`, `acceptance_refs` и UI-smoke/walkthrough evidence. | Для каждой `US-*` создать canonical story record по YAML-шаблону, связать с dot-case journey и REQ-ID, а отсутствие любого поля считать orphan coverage и блокировать `APPROVED`. |
| AC-221 | Пять базовых portal journeys содержали последовательность действий, но не явную маркировку `Happy-path: N шагов`, требуемую UX-контрактом; количество шагов и проверка видимого next-step оставались неоднозначными. | Добавить `Happy-path: N шагов` с одним видимым действием и next-step на каждый шаг; validator проверяет наличие label для каждого journey и блокирует approval при несоответствии числа шагов. |
| AC-222 | После добавления labels исходные значения `N` не совпадали с количеством действий в некоторых путях (campaign, advertiser, emergency), что создавало ложное соответствие UX-контракту. | Пересчитать N по каждой стрелке-действию и проверять label против фактического числа шагов: campaign 12, approval 8, operations 8, advertiser 7, emergency 9. |
| AC-223 | `J-REL-001` заявлял `Happy-path: 7 шагов`, но последовательность содержала только 6 действий; аналогичный дефект мог скрыться в служебных journeys. | Проверять каждый journey label против фактического количества действий и блокировать approval при несовпадении; `J-REL-001` исправлен на 6. |
| AC-224 | При пересчёте многострочных базовых journeys строковый скан учитывал только первую строку и пропускал действие `audit confirmation`/`result/rollback`; labels approval и operations были занижены. | Считать шаги по объединённому блоку journey, а не по одной строке; базовые значения: campaign 12, approval 8, operations 8, advertiser 8, emergency 9. |
| AC-225 | В базовом advertiser journey `geography/time filter` был ошибочно посчитан как два шага, хотя это одно видимое действие; label 8 не соответствовал реальной последовательности. | Считать семантические действия, а не разделители в тексте; исправить advertiser label на 7 и зафиксировать правило для составных фильтров. |
| AC-226 | Reverse-traceability текущего драфта находит нормативные фразы вне строк каталога REQ и без inline `REQ/PROCESS/NON-NORMATIVE` маркера; правило AF описано, но список и disposition этих строк не опубликованы. | Выпустить report `draft_line → REQ/PROCESS/NON-NORMATIVE → disposition`, добавить маркеры или вынести пояснения из нормативного текста; любая необозначенная строка блокирует `APPROVED`. |
| AC-227 | REQ-ARCH-004 и REQ-SEC-003 оставляли существенные архитектурные альтернативы (deployment topology и PKI/mTLS) без отдельных DEC-ID, владельца, срока и rollback-критериев. | Добавить DEC-015/016 в decision register; до owner/security approval связанные REQ и production gate остаются `proposed/deferred`, а token-only или выбранная topology не выдаются за финальное решение. |
| AC-228 | Дополнение I перечисляло только `DEC-001…012`, хотя основной decision register уже содержал `DEC-013…016`; новые решения выпадали из governance-сверки и могли остаться без disposition. | Дублировать каждый DEC-ID в единой карте источника/статуса, проверять равенство множеств реестров и блокировать `APPROVED` при расхождении. |
| AC-229 | Требование DEV environment manifest перечисляло обязательные сведения, но не давало машиночитаемого формата; адрес, порты, SHA, schema, seed/reset и источник секретов могли снова разойтись между документами. | Ввести manifest по шаблону с обязательными endpoint/host/ports, Git SHA, schema revision, seed/reset, monitoring, secret source, owner и verification timestamp; validator запрещает credentials и незаполненные placeholders при `verification`. |
| AC-230 | Раздел `DECISION_REQUIRED` перечислял исключения из первой очереди, но не требовал `DEC-ID` и записи в decision register; scope мог быть изменён неявно текстовой оговоркой. | Каждое исключение связывать с `DEC-ID`, owner, reason, trigger и review date; отсутствие записи блокирует `APPROVED` и перенос в roadmap. |
| AC-231 | После введения правила `DECISION_REQUIRED` пять конкретных исключений всё ещё не имели индивидуальных DEC-ID и строк в decision register; общее правило не доказывало покрытие каждой позиции. | Добавить карту исключений и `DEC-017…021`, проверять равенство множеств исключений и решений и блокировать approval при пропуске любой позиции. |
| AC-232 | `DEC-017…021` присутствовали в дополнении I, но отсутствовали в основном decision register §29; два источника решений имели разные множества и могли расходиться при согласовании. | Хранить каждый DEC-ID в основном реестре и карте governance, проверять равенство множеств и блокировать `APPROVED` при расхождении. |
| AC-233 | При добавлении `DEC-017…021` в оба реестра строки были продублированы в дополнении I; множество совпадало, но один DEC-ID имел несколько определений. | Проверять не только равенство множеств, но и уникальность каждого DEC-ID внутри каждого реестра; дубликаты блокируют `APPROVED`. |
| AC-234 | Handoff требовал отдельный DEV manifest, хотя `docs/product/environment-inventory.yaml` уже является каноническим инвентарём `.81` с endpoint, Git SHA, schema и evidence; это создавало дублирующий источник и риск расхождения. | Использовать environment-inventory как первичный источник, дополнить только отсутствующие seed/reset/операционные поля и проверять отсутствие второго конфликтующего manifest. |
| AC-235 | Историческая версия AC-19 ссылалась на count 27 user stories, затем snapshot r279 — на 28, core snapshot — на 32, snapshot r390 — на 39; текущая редакция содержит 41 уникальную `US-*` после добавления двух registry-gap stories. Перенос старого count мог привести к пропуску stories при генерации traceability. | Считать и публиковать counts программно для каждого snapshot revision; проверять их против story/journey registry и блокировать approval при расхождении. |
| AC-236 | Исторический count 28 journey IDs включал design IDs, aliases и общий литерал `J-PORTAL`, но был сформулирован как число canonical project journeys; после новых stories он тем более не является текущей метрикой. | Публиковать раздельные counts по snapshot revision: `US-*`, canonical project journeys, design scenarios и aliases; только canonical dot-case IDs участвуют в Done Gate/UI-smoke. |
| AC-237 | В драфте была описана мультиканальная публикация, но не полный единый operational control plane для управления всеми physical device/logical carrier/display surface; bulk-результаты и cross-surface isolation были неявны. | Закрепить `REQ-CHAN-003`, story `US-CHAN-003`, journey `J-CHAN-004`/`carrier.manage`, API/UI preview+progress+partial-result+retry и negative tests на scope, idempotency и побочные изменения. |
| AC-238 | Исторический snapshot после добавления `US-CHAN-003` проверял count 28; core licensing/commerce/onboarding stories изменили count до 32, V26 добавил ещё 7 (snapshot r390 — 39), а текущий total равен 41 после двух registry-gap stories. Исторические числа нельзя считать текущей метрикой покрытия. | Пересчитывать story/design/alias IDs одним скриптом при каждом revision; все новые IDs остаются `PENDING` до регистрации в canonical user-journeys, feature-registry и UI-smoke. |
| AC-241 | Фактический проект содержит EPIC-L licensing (Layer 1 seat ledger и заблокированный Layer 2 signed-license/UI), но драфт ТЗ не содержал ни требований, ни stories/journey, ни границы между license и advertiser billing; enrollment и decommission могли развиваться без license policy. | Добавить `REQ-LIC-001`, `US-LIC-001`, `J-LIC-001`/`license.manage`, отдельные API/data/security proofs и roadmap disposition для Layer 1 и Layer 2; проверить atomic reserve/release/renewal, fail-closed limits и отсутствие отключения активных устройств при renewal. |
| AC-242 | Сверка с текущим `feature-registry.yaml` (58 feature IDs) показала 46 IDs без явной записи в story/REQ-трассировке драфта; односторонняя связь ТЗ→registry не доказывает, что уже реализованные или заблокированные функции не потеряны. | Ввести `REQ-GOV-002` и выпустить двусторонний registry reconciliation: каждый registry ID и каждый draft REQ/story/journey получает canonical mapping или owner-approved exclusion, статус, roadmap task и evidence; неизвестные/дублирующие IDs блокируют `APPROVED`. |
| AC-243 | Для AC-242 не был зафиксирован проверяемый перечень расхождений. На snapshot registry SHA текущие отсутствующие в драфте IDs: `adsettings.configure`, `adsettings.test`, `advertiser.application_review`, `advertiser.apply`, `advertiser.brand_crud`, `advertiser.contact_crud`, `advertiser.contract_crud`, `advertiser.create_org`, `advertiser.invite`, `advertiser.legal_requisites`, `audit.view`, `campaign.activate`, `campaign.complete`, `campaign.pause`, `campaign.reject`, `commerce.booking`, `commerce.offer_generate`, `commerce.order_close`, `commerce.order_create`, `commerce.payment_status`, `commerce.price_list_manage`, `commerce.tariff_manage`, `creative.moderate_approve`, `creative.moderate_reject`, `device.heartbeat`, `emergency.deactivate`, `inventory.rule_create`, `license.enforce`, `license.report`, `license.seat_release`, `license.upload`, `license.view`, `manifest.deliver`, `playlist.build`, `pop.ingest`, `self.apply_or_brief`, `self.campaign_create`, `self.campaign_view`, `self.login`, `self.report_view`, `system.theme_switch`, `user.assign_roles`, `user.create_advertiser`, `user.deactivate`, `user.reset_password`, `user.split_internal_advertiser`. | Сохранить machine-generated snapshot с registry SHA/датой; для каждого ID назначить mapping на REQ/story/journey или DEC-approved exclusion и сверять snapshot в CI, не трактуя простое упоминание имени как coverage. |
| AC-244 | Сверка с `docs/product/roadmap.yaml` показала 73 task/stage/decision IDs, из которых 58 не имеют явной ссылки в драфте; поэтому даже после registry reconciliation нельзя доказать, что все технические и бизнесовые задачи roadmap покрыты ТЗ. | Выпустить двусторонний roadmap coverage manifest: `roadmap ID → REQ/story/journey/DEC`, а также `REQ/story/journey/DEC → roadmap ID или approved deferred`; для каждой задачи синхронизировать requirement/delivery status, owner, evidence и generated business/technical view; stage labels и governance IDs считать отдельно от продуктовых задач. |
| AC-245 | Семь действующих commerce-функций (`tariff_manage`, `price_list_manage`, `order_create`, `offer_generate`, `booking`, `payment_status`, `order_close`) были представлены только общей финансовой формулировкой; это не гарантировало покрытия отдельных переходов и статусов в UI/API/roadmap. | Закрепить `REQ-BIZ-014`, story `US-COM-001`, journey `J-COM-001`/`commerce.manage`, отдельные endpoint/state/permission/idempotency/audit proofs и mapping каждой из семи registry-фич на requirement и roadmap task. |
| AC-246 | Advertiser/onboarding и self-service IDs registry (`advertiser.*`, `self.*`) не были выделены в отдельный workflow; общая история рекламодателя не задавала approval boundary, изоляцию scope и запрет преждевременного доступа. | Закрепить `REQ-BIZ-015`, story `US-ADV-002`, journey `J-ADV-002`/`advertiser.onboard`, state/permission/negative tests и mapping каждой registry-фичи на REQ и roadmap task; до approval self-service остаётся недоступным. |
| AC-247 | Исторический snapshot `J-COM-001` содержал 10 видимых действий при label `Happy-path: 9 шагов`; после отделения условного payment шага текущий путь содержит 9 действий. | Для каждого snapshot пересчитывать шаги по видимым действиям с next-step; текущий label проверять структурно, а исторические counts не использовать как текущий UX-бюджет. |
| AC-248 | После добавления новых доменов исторические self-review counts (28/29 stories и 28 journey IDs) стали stale и могли попасть в отчёты как текущая полнота. | Хранить counts только с revision/date/source SHA, отделять historical snapshots от current summary и автоматически сверять текущие `US-*`, canonical journeys и registry sets перед approval. |
| AC-249 | Registry содержит `campaign.reject`, но campaign state machine не имела состояния `rejected`; не были заданы причина, версия возврата и запрет публикации отклонённой версии. | Добавить явное `rejected` состояние, обязательные actor/time/reason/scope/version, переход только в новую draft-версию и negative tests на schedule/publish rejected campaign; синхронизировать registry, journey, roadmap и audit evidence. |
| AC-250 | Registry содержит `emergency.activate/deactivate`, а драфт описывал только последовательность действий без состояний `dispatching`, partial delivery, resume и закрытия; повторная или частичная команда могла трактоваться как полный успех. | Зафиксировать emergency state machine и per-target result, идемпотентность, отдельный permission/audit для deactivate/resume, negative tests на повтор, partial failure, unauthorized resume и возврат к устаревшему manifest. |
| AC-251 | Для registry-функции `playlist.build` не было отдельной state machine: validation, approval, publish и rollback playlist могли быть слиты с manifest и позволить генерацию из невалидной/неутверждённой версии. | Зафиксировать playlist lifecycle и immutable version/diff, запрет manifest generation для invalid/unapproved playlist, explicit last-known-good rollback с actor/reason/scope и contract/negative tests. |
| AC-252 | Registry содержит `inventory.rule_create`, но правила inventory были только частью общей формулы: не были определены version/effective date, simulation, approval и rollback. | Добавить `REQ-BIZ-016`, story `US-INV-001`, journey `J-INV-001`/`inventory.rule_manage`, versioned rule schema, conflict/overbooking simulation и negative tests на изменение active reservations до effective date. |
| AC-253 | После добавления licensing и commerce requirements API-инвентарь не содержал явных endpoints для license grant/report/upload, atomic enrollment seat-hook и отдельных tariff/price-list/offer/order transitions; контуры могли остаться только prose/UI обещанием. | Зафиксировать фактический Layer 1 `GET /api/v1/identity/licenses/report`, proposed Layer 2 `/api/v1/identity/licenses*`, `/api/v1/device/onboard` (canonical; `/device/onboard` alias) и `/api/commerce/*` с auth/scope, idempotency, state/errors, audit, deprecation и positive/negative contract tests; Layer 2 upload/UI отделить owner/security gate. |
| AC-254 | `device.heartbeat` был представлен только как поле health view; не были заданы payload, freshness thresholds, sequence/dedupe, clock drift и правила, когда heartbeat не может скрыть offline или продлить SLA. | Закрепить `REQ-OPS-009`, heartbeat schema для canonical `/api/v1/device/heartbeat`, channel-specific thresholds, authenticated negative tests, dedupe/clock-drift checks и корреляцию heartbeat с health, SLA и underdelivery. |
| AC-255 | Licensing onboarding path в предыдущей записи был назван `/device/v1/onboard`, но код и ADR используют `/api/v1/device/onboard`, а `/device/onboard` является legacy/compatibility route; разные формы могли породить два enrollment-контракта. | Оставить `/api/v1/device/onboard` единственным canonical endpoint, `/device/onboard` разрешать только как alias с одинаковыми auth/seat/idempotency/audit semantics, owner и deprecation/migration tests; удалить `/device/v1/onboard` из контрактов. |
| AC-256 | Heartbeat path в предыдущем драфте был `/device/v1/heartbeat`, тогда как код/архитектурный inventory канонизируют `POST /api/v1/device/heartbeat`; несогласованность namespace могла породить отдельный runtime contract. | Оставить `/api/v1/device/heartbeat` canonical, legacy path разрешать только как alias с одинаковыми auth/freshness/dedupe semantics, owner и deprecation/migration tests; синхронизировать OpenAPI, journey, smoke и device clients. |
| AC-257 | Предыдущая запись объявляла `/api/licenses*` как будто существующие маршруты; код содержит только Layer 1 `GET /api/v1/identity/licenses/report`, а signed-license upload/view ещё не реализованы. Это могло превратить планируемый Layer 2 в ложное evidence. | Везде разделять `implemented` и `proposed/blocked` API paths, указывать source file/route prefix и status; не считать Layer 2 license upload/view готовыми без реализации, security gate, UI-smoke и signed-license evidence. |
| AC-258 | API inventory не перечислял endpoints для campaign reject/approve/activate/pause/complete и inventory rule create/activate/deactivate, хотя state machines и registry их требуют; это позволяло реализовать lifecycle частично или обходить единый контракт. | Включить все transition endpoints в versioned OpenAPI с permission/scope, idempotency, transition guards, errors, audit и negative tests; сверять endpoint set с registry/state-machine set перед `APPROVED`. |
| AC-259 | После добавления `REQ-BIZ-015` API inventory не содержал явных advertiser application/review/invite и self-service routes; approval boundary и запрет раннего коммерческого доступа могли быть не реализованы. | Добавить versioned endpoints заявок, review, invite и self-service briefs/campaigns/reports с pending/approved/rejected/suspended guards, advertiser/retailer scope, permission, audit и negative tests до/после approval. |
| AC-262 | Commerce API inventory называл `/api/commerce/tariffs`, `price-lists`, `offers`, `booking`, `payment-status`, `close`, хотя код реализует `tariff-versions`, `price-items`, `quote` и CRUD orders под identity prefix; несуществующие transitions могли быть приняты за готовые. | Разделять фактические routes и logical transitions; canonicalize существующие paths по коду, а offer/booking/payment-status/close реализовать и доказать отдельным OpenAPI/contract/evidence либо явно оставить `planned`, не выдавая их за implemented. |
| AC-263 | Registry содержит `adsettings.configure/test`, но API inventory не включал фактические `GET/PUT /api/v1/identity/auth/ad-settings` и `/test`; административные настройки могли выпасть из ТЗ и permission/audit матрицы. | Добавить settings endpoints с отдельными permission/scope, safe validation, audit и negative tests; сверять registry feature set с endpoint catalog и role-scope matrix. |
| AC-264 | Audit API inventory называл `/api/audit/events` и `/api/audit`, хотя код предоставляет `GET /api/v1/identity/audit-events`; несуществующий namespace мог привести к ложному audit evidence или несовместимому UI. | Канонизировать фактический audit route, logical aliases явно маркировать proposed, и проверить auth/scope, pagination/filtering, immutable output, SIEM export и negative cross-scope tests в OpenAPI/UI-smoke. |
| AC-265 | Reporting и emergency API inventory называл `/api/analytics/*` и `/api/emergency/*`, хотя код реализует campaign PoP report routes и identity emergency `status/activate/deactivate`; логические stop/message/resume views не являются фактическими routes. | Разделять implemented route set и logical capabilities, canonicalize paths по коду, а недостающие network/report/emergency operations закрыть versioned OpenAPI или явно оставить planned с owner/evidence и negative scope tests. |
| AC-266 | Integration/player endpoints для ESL/LED vendor connectors и player builds/rollouts были перечислены без статуса, хотя в текущем API-коде соответствующих routes нет; это могло создать ложное впечатление готовой мультиканальной поставки. | Явно маркировать эти paths как proposed, добавить channel/vendor owner, OpenAPI, sandbox/mock, auth/scope, health/failure/reconciliation contracts и end-to-end evidence до перевода в implemented. |
| AC-267 | Campaign API inventory называл `/campaigns/{id}/submit` и top-level `/placements`, тогда как код реализует `request-approval` и nested flight/placement/inventory-reservation routes; разные имена могли породить несовместимый client/UI contract. | Канонизировать фактические nested routes, logical submit alias явно mapping-ить к `request-approval`, и проверить transition guards, permission/scope, idempotency, audit и migration/deprecation semantics. |
| AC-268 | Auth API inventory использовал сокращённые `/api/auth/*` и не перечислял `/me`/`change-password`, тогда как код имеет отдельные `/api/v1/auth/*` и `/api/v1/identity/*` prefixes; namespace drift мог сломать clients и security tests. | Канонизировать auth/identity routes по router prefixes, включить login/refresh/logout/me/change-password и identity users/roles/permissions/settings в OpenAPI, проверить cookie/token, permission, audit и negative tests. |
| AC-269 | Device API inventory объявлял register/events/capabilities и общий manifest route как доступные, хотя Device Gateway реализует только `manifest/latest` и heartbeat; отсутствующие runtime endpoints могли быть приняты за готовый device contract. | Разделить implemented и proposed Device Gateway routes, canonicalize exact methods/paths по коду, добавить schema/auth/retry/dedupe/owner/deprecation и contract tests для каждого proposed endpoint до production/pilot gate. |
| AC-270 | После добавления новых stories target journey gap изменился с исторических 22/23 до 27 IDs; старый список мог скрыть `advertiser.onboard`, `commerce.manage`, `inventory.rule_manage` и `license.manage` как уже сверенные. | Пересчитывать draft-target ↔ canonical journey diff на каждом revision и хранить полный current list с датой/source SHA; новые IDs не считать UI-покрытием до регистрации в canonical user-journeys, registry, smoke и walkthrough. |
| AC-271 | `REQ-BIZ-015` требовал pending/approved/rejected/suspended для onboarding и invite, но общей campaign state machine было недостаточно: application resubmission, suspension и invite expiry/revoke не имели переходов и guards. | Зафиксировать application/invite state machines, version/reason/audit на rejection/resubmission, блокировку коммерческого/self-service доступа при suspension и negative tests на expired/revoked invite и операции до approval. |
| AC-272 | Reporting requirements заявляли PDF/XLSX/CSV, но код подтверждает только CSV export; PDF/XLSX не имеют runtime route/evidence и могли быть ошибочно отмечены готовыми. | Разделять implemented CSV и planned PDF/XLSX deliverables, добавить versioned schemas/format tests, permission/scope/audit и evidence каждого формата до `done`; roadmap/registry должны отражать частичный статус. |
| AC-260 | Предыдущая запись моделировала `/api/self/*` как реальные маршруты, хотя код использует identity routes для advertiser applications/organizations/brands/contacts и `campaign-briefs`; это могло породить несовместимый API namespace. | В OpenAPI разделять фактические route paths и logical capability names; canonicalize identity routes по коду, а self-service проверять permission/scope/status guards поверх них, без утверждения несуществующего namespace. |
| AC-261 | Media API inventory называл `/api/media`, `/api/renditions`, `/api/moderation`, хотя код предоставляет identity `creative-assets` routes для upload, moderation queue, approve/reject и completion; разные namespaces могли привести к несогласованной реализации и smoke. | Канонизировать фактические `creative-assets*` routes, logical capability names связать mapping-таблицей, а compatibility alias допускать только с owner/deprecation и одинаковыми auth/scope/immutability/QA semantics; синхронизировать OpenAPI и UI-smoke. |
| AC-239 | `REQ-CHAN-003` и `carrier.manage` задавали единый control plane, но API-инвентарь не содержал canonical endpoints для списка/карточки carrier, устройств, surface status и bulk actions; реализация могла остаться только UI-обещанием. | Добавить versioned OpenAPI endpoints `/api/devices`, `/api/carriers`, `/api/carriers/{id}`, `/api/carriers/bulk-actions`, `/api/surfaces/{id}/status` с auth/scope, idempotency, preview/progress/partial-result/retry, audit и negative tests. |
| AC-240 | Двусторонняя сверка показала не только отсутствующие 28 (теперь 23 с `carrier.manage`) целевых ID, но и дополнительные canonical journeys проекта, не представленные в story map драфта (`campaign.edit`, `device.onboard`, `backup.restore`, `commerce.*`, `creative.upload`, `device.health_view` и др.). Одностороннее добавление новых ID может скрыть уже реализованные или обязательные пути. | Выпустить reconciled journey inventory: canonical ID → story/REQ/roadmap/status и draft target ID → canonical ID или approved exclusion; для каждого расхождения указать владелец, причину, route, smoke и walkthrough. До этого ни один count покрытия journeys не считать полным. |
| AC-273 | Самоаудит сверил §6 с `packages/domain` и `packages/domain/delivery.py`: persisted campaign enum допускает `draft/pending_approval/approved/active/paused/completed/rejected`, тогда как delivery eligibility также проверяет строку `scheduled`; без явного разграничения `scheduled` может стать невалидным состоянием, вторым lifecycle или обходом transition/audit guards. | r418 учитывает принятый ADR-015: `scheduled` — persisted state полного lifecycle, а `rejected` допускает новую immutable revision того же campaign. Код/API/миграция должны быть приведены к ADR-015 либо ADR-015 формально изменён; молча трактовать `scheduled` как projection или делать rejected terminal запрещено. Нужны contract/negative tests на unknown status, rejected publication и projection↔runtime mapping. |
| AC-274 | AC-08 не отражал состояние после RM-ENV-001 и ошибочно говорил об отсутствии паспорта; это могло привести к созданию дублирующего manifest и конфликту источников. | Считать `environment-inventory.yaml` единственным источником окружений; проверять его полноту отдельным env-gate и различать `inventory exists` от `verification complete`. |
| AC-275 | В active-тексте сохранялись snapshot-counts без явной метки (80 REQ, 22 journeys), поэтому читатель мог принять историю аудита за актуальное покрытие. | Каждый count снабжать `snapshot_sha`, датой и типом (`historical`/`current`); автоматическая проверка должна запрещать использование historical count в выводах о текущем покрытии и APPROVED gate. |
| AC-276 | Section map покрывает верхние разделы исходника, но точечная сверка показывает нормативные подразделы без явной ссылки (в частности §1.1, §2.1, §4.1, §15.1–15.2, §16.1, §21.2–21.5 и §24.2–24.4/24.6–24.8). Ссылка вида `§24` или диапазон не доказывает построчную классификацию вложенных обязанностей. | Для каждого source subsection создать запись `source_section → obligation_id → REQ-ID/approved-exclusion`; validator должен требовать покрытие всех нормативных подразделов, а верхнеуровневые ссылки считать только навигацией. |
| AC-277 | Исторический быстрый regex давал 91 REQ-подобный токен против 88 source-derived REQ-ID v2.5; после добавления 11 REQ-V26 и двух registry-derived gaps прежний count нельзя выдавать за текущий. | r418: `atomic_req_count=101` = 88 baseline + 11 v2.6 addendum + 2 registry-derived (`REQ-BIZ-017`, `REQ-UX-005`); coverage считается только по 101 уникальной строке каталога, а token/range matches не создают фиктивные требования. |
| AC-278 | Вводная оговорка §26 называла `/device/v1/` стандартным namespace, тогда как фактический и канонический Device Gateway использует `/api/v1/device/`; это могло породить второй API-контракт. | Оставить `/api/v1/device/` canonical для manifest/heartbeat/onboard и явно маркировать `/device/v1/*` как запрещённый/исторический alias; проверять namespace в OpenAPI, clients и contract tests. |
| AC-279 | Верхний changelog смешивает записи текущей последовательности (`r319+`) с историческими (`r285…r318`) без явной границы и порядка; читатель не может надёжно восстановить, какие правила действуют в текущем snapshot. | Хранить active changelog в монотонном порядке до текущей ревизии, исторические записи вынести в отдельный журнал с диапазоном и source SHA; validator проверяет уникальность/порядок ревизий и наличие записи для текущей версии. |
| AC-280 | `REQ-GOV-003` и часть acceptance уже используют `delivery_status: blocked`, но шаблон/жизненный цикл ранее не включали его в enum и не задавали обязательные blocker evidence; блокированная задача могла стать невалидной или исчезнуть в `deferred`. | Включить `blocked` в единый enum и state machine; требовать blocker ID, owner, reason, dependency, review date и evidence снятия, запретить маскировать им `deferred`/`done`, синхронизировать schema, roadmap, registry и monitoring projection. |
| AC-281 | Дополнение M вводило `architecture_status`, которого нет в canonical template/lifecycle; параллельное поле могло рассинхронизировать зрелость требования и delivery status. | Использовать только `requirement_status` для зрелости контракта и `delivery_status` для реализации; validator отклоняет неизвестный `architecture_status` и проверяет отсутствие третьего status dimension. |
| AC-282 | `REQ-BIZ-009` и `REQ-BIZ-014` одновременно описывали payment/confirmation и финансовые сущности, не отделяя обязательный order/booking workflow от условного billing/ЭДО и financial fact; это позволяло заявить оплату без owner/legal решения. | Зафиксировать ownership границы: REQ-BIZ-014 покрывает tariff/price/offer/order/booking, REQ-BIZ-009 — financial reporting/facts; payment/ЭДО/billing активируются только DEC-017 с отдельными schema, reconciliation и evidence. Добавить negative acceptance на выдачу «оплачено/юридически значимо» без внешнего подтверждения. |
| AC-283 | Metadata содержит SHA исходного v2.5, но не integrity identity текущего v2.6 draft; один и тот же Document ID/revision может быть ошибочно принят за другой рабочий файл или незакоммиченный вариант. | Для каждого review/owner ACCEPT фиксировать Git commit SHA или blob SHA-256 драфта (для незакоммиченной работы — явно `UNCOMMITTED` и digest в review record); validator не принимает ссылку «последний файл» без этой identity-пары. |
| AC-284 | После введения canonical `requirement_status`/`delivery_status` сводная таблица сохраняла термин `architecture_status`, что могло вернуть третий status dimension в roadmap или registry. | Во всех производных документах использовать только canonical пару; structural check запрещает `architecture_status` вне исторического changelog/AC-281 и требует согласованный mapping статусов. |
| AC-285 | Текст decision register требовал поле `date`/`review date`, а YAML-шаблон — `decided_on`/`review_on`; разные имена могли создать две несовместимые схемы и потерю даты решения при миграции. | Канонизировать `decided_on` и `review_on` во всех таблицах, YAML, roadmap и валидаторах; aliases допускаются только в compatibility mapping с deprecation и schema test. |
| AC-286 | Исторический счётчик user stories в AC-19/AC-235 отставал от фактического множества: core snapshot был 32 вместо 31, snapshot r390 — 39, текущий count равен 41 после двух registry-gap stories. Это могло скрыть story при генерации traceability. | Автоматически считать уникальные story IDs из canonical story table, публиковать count вместе с revision/SHA и блокировать approval при расхождении с story/journey registry. |
| AC-287 | `J-ANL-001` включал XLSX в happy-path как доступный экспорт, хотя текущий runtime/evidence подтверждает только CSV; journey мог создать ложный UI/roadmap статус. | Разделять реализованный CSV и planned XLSX в journey, registry, roadmap и UI-smoke; недоступный формат не показывать как завершённый и не считать Done Gate выполненным. |
| AC-288 | `US-COM-001`/`J-COM-001` включали payment status обязательным шагом, хотя `REQ-BIZ-009/014` оставляют payment, billing и ЭДО условными до owner/legal решения DEC-017; это могло создать ложный обязательный финансовый workflow. | Сделать order/booking обязательным operational scope, а payment status — отдельной capability с DEC-017, внешним подтверждением, schema и evidence; пересчитать happy-path и синхронизировать story, journey, registry и roadmap. |
| AC-289 | Правило квалификации source references не различало внутреннюю нумерацию v2.6 и ссылки на § исходного v2.5; acceptance/changelog с bare `§N` могли быть ошибочно прочитаны как ссылки на новую редакцию. | Ввести контекст ссылки: source-column явно `TZ v2.5`, внутренние разделы маркировать `§v2.6` или заголовком; validator проверяет, что bare `§N` не появляется в нормативной прозе без source context. |
| AC-290 | Код уже реализует `POST /api/v1/identity/campaigns/{id}/archive` и переводит `draft/rejected → archived` прямой записью строки, но `CampaignStatus`/`ALLOWED_TRANSITIONS` не содержат `archived`; операция обходит единый transition guard и контракт state machine. | Включить `archived` в canonical enum/schema/registry и разрешённые переходы только из `draft/rejected`, либо удалить route через owner-approved decision; добавить transition/auth/scope/idempotency/audit/negative tests и запрет publish/activate archived. |
| AC-291 | `InventorySlot.recompute_status()` в коде возвращает `available/limited/sold_out/blocked`, тогда как REQ-BIZ-001 и acceptance используют `free/reserved/sold/internal/emergency/fallback`; без mapping это два разных status contract и риск неверных отчётов/решений reservation. | Зафиксировать persisted/runtime/business status layers и однозначный mapping с source-of-truth; добавить schema/contract tests для каждого состояния, включая emergency/internal blocks, sold-out и projection drift, и запретить использовать `available` как замену бизнес-факта без контекста. |
| AC-292 | Код содержит `CommerceOrderStatus` (`draft/offered/booked/confirmed/closed/cancelled`), но раздел 6 не задавал order state machine; booking, cancellation и close могли реализоваться с разными guards, а `confirmed` — ошибочно трактоваться как оплата. | Зафиксировать order transitions, атомарность reservation, cancellation reasons/audit, immutable close и отдельную условную payment projection; добавить positive/negative tests и синхронизировать API, schema, journey, registry и roadmap. |
| AC-293 | Драфт объявлял manifest states `signed/queued/superseded/rolled_back`, но кодовый `ManifestStatus` содержит только `generated/delivered/applied/expired/error`; смешение target lifecycle с persisted enum создаёт ложный runtime-контракт и несовместимый ACK. | Разделить persisted status и delivery/event projection, задокументировать mapping/source-of-truth и не считать недостающие состояния реализованными без ADR/schema/migration; добавить contract/negative tests для unknown status, expired/revoked manifest и rollback/supersede evidence. |
| AC-294 | Кодовый `DeviceStatus` включает `unregistered`, но state machine и REQ-OPS-001 ранее начинались с `pending/registered`; отсутствие явного pre-enrollment состояния могло разрешить команды или delivery для устройства без enrollment. | Добавить `unregistered` в canonical enum/state machine, запретить delivery/commands до `registered`, определить guards/re-enrollment после `revoked` и покрыть onboarding/negative scope/audit tests. |
| AC-295 | Кодовый `ProofMode` не содержит `error` и `not_applied`, хотя REQ-POP-001 и §24.13 требуют различать неуспешное применение и отсутствие факта; без явной projection ошибка может попасть в `gateway_ack` или playback fact. | Расширить versioned proof schema/runtime enum либо ввести проверяемую projection с source/mapping; добавить negative tests на failed apply, missing file, invalid signature и запрет коммерческого PoP для `error/not_applied` без explicit policy. |
| AC-296 | `ManifestStatus` в коде содержит `expired`, но target lifecycle не выделял expiry отдельно; это могло смешать истечение `valid_to` с техническим `error` и неверно продлить delivery/SLA. | Зафиксировать `expired` как terminal outcome с причиной/временем `valid_to`, fallback/revocation policy и отдельными tests на expired/future manifest, отчётность и запрет коммерческого PoP после expiry. |
| AC-297 | Драфт смешивал enrollment stages `pending/registered` с runtime `DeviceStatus`, хотя кодовый enum содержит только `unregistered/online/degraded/offline/error/maintenance/revoked`; это создавало несуществующие runtime-значения и неоднозначные guards. | Разделить enrollment и health в schema/DB/API/UI, задокументировать mapping/projection, отклонять неизвестные health values и запрещать delivery/commands до завершённого enrollment; добавить contract/negative tests для каждого перехода, включая revoked и повторный enrollment. |
| AC-298 | Драфт отделял payment от order, но не фиксировал кодовые значения `CommercePaymentStatus` (`not_required/unpaid/partial/paid/overdue`) и `CommerceTariffStatus` (`draft/active/archived`); это оставляло риск произвольных статусов и ложного `paid` без DEC-017. | Зафиксировать versioned payment/tariff projection только после DEC-017, mapping и source-of-truth для каждого значения, внешнее подтверждение/reconciliation для `paid`, effective dates тарифов и negative tests на неизвестные статусы, оплату без evidence и смешение order/payment facts. |
| AC-299 | `PlaybackResult` в коде ограничен `success/skipped/failed/interrupted`, но PoP-контракт перечислял только поле без закрытого enum; интеграция могла отправить произвольный результат или смешать техническую причину с бизнесовым playback outcome. | Закрыть enum в schema/OpenAPI/event contract, хранить техническую причину в `failure_reason`, добавить negative tests на неизвестное значение и matrix для каждого результата/причины. |
| AC-300 | Код поддерживает `CertificateType` (`rsa/ed25519/hsm`), а security-текст говорил об optional certificate без профиля; разные adapters могли выбрать несовместимый или неутверждённый credential profile. | Зафиксировать профиль сертификата, capability/rotation/revoke и migration policy в DEC/adapter contract; неизвестный тип и несогласованный с каналом профиль должны отклоняться до enrollment. |
| AC-301 | Дополнение v2.6 Next Branch было отдельным DOCX и отсутствовало в источниках/атомарном каталоге; sales lift, self-service, competitive separation, audience targeting, financial exchange, dynamic creative, mobile operations и external measurement могли не попасть в roadmap. | Сгенерировать и проверить extracted-текст addendum, связать все 11 REQ-V26 с story/journey, roadmap task или approved `designed-not-implemented` disposition; проверять отсутствие orphan IDs и не считать extension реализованным по prose. |
| AC-302 | Таблицы v2.6 addendum содержали точные новые сущности, приоритеты P0–P4 и общий критерий ветки; одной краткой строкой REQ нельзя было проверить, что модель данных и порядок реализации сохранены. | В traceability зафиксировать пять attribution/self-service сущностей, priority для каждого REQ-V26, additive-only constraint и branch-level acceptance; validator должен ловить пропущенную сущность, неверный приоритет и отсутствие disposition для P3/P4. |
| AC-303 | Acceptance v2.6 требовал self-service путь до публикации без внутреннего менеджера (кроме final approve), conflict-check и credit/budget guardrail при создании; прежняя формулировка допускала лишь создание draft. | Добавить end-to-end journey и negative tests на превышение лимита/конфликт, доказать общий moderation/approval и отсутствие manager action до final approve; без этого `self-service` не считается готовым. |
| AC-304 | Addendum v2.6 расширяет существующие attribution, self-service, finance и A/B требования, но без явного mapping мог породить параллельные модели и несовместимые источники истины. | Перед реализацией утвердить extension→baseline mapping, запретить дублирующие сущности/статусы и проверить schema/API/roadmap на один source-of-truth для каждого расширения. |
| AC-305 | Нормативные acceptance addendum были распределены по кратким REQ и не имели единой проверяемой матрицы; можно было закрыть домен по наличию формы или ADR без end-to-end evidence. | Для каждого REQ-V26 хранить acceptance, actor/scope, test data, expected result и evidence kind; branch gate блокирует отсутствие pilot/round-trip/negative proof или ошибочную отметку `done`. |
| AC-306 | После extraction addendum не было зафиксировано, что `.md` соответствует DOCX по структуре, а checksum extracted-файла не был связан с draft revision; extraction мог незаметно устареть. | Сверять paragraph/table counts (129/3), ключевые заголовки и SHA extracted-файла с metadata; любое изменение DOCX требует новой extraction, revision и changelog до `APPROVED`. |
| AC-307 | Даже после extraction не было отдельного proof, что extracted-файл добавлен в канонический read order и доступен агентам по указанному SHA. | Проверять наличие extracted-файла и ссылки в `docs/00-source-of-truth/README.md`, совпадение SHA, counts и заголовков; изменение DOCX блокирует approval до повторного extraction. |
| AC-308 | Проверка addendum по заголовкам не доказывала покрытие составных нормативных предложений и общих ограничений; отдельные acceptance/порядок/исключения могли потеряться. | Хранить line-level карту всех нормативных строк extracted-файла с classification и REQ/DEC/PROCESS disposition; classifier должен выявлять orphan line и несоответствие количества строк при изменении источника. |
| AC-309 | Двусторонняя сверка текущей roadmap показала, что шесть v2.6 extension-доменов не имеют task/decision/registry ID, а attribution и self-service представлены только общими открытыми решениями. | Создать roadmap task либо owner-approved `designed-not-implemented` disposition для каждого REQ-V26; validator должен ловить `UNMAPPED`, partial mapping и отсутствие journey/evidence, не считая внешний monitoring-dashboard источником планирования. |
| AC-310 | Data inventory не содержал новые сущности v2.6 addendum, поэтому REQ могли остаться без схемы, владельца, migration и retention. | Для каждой V26-сущности определить schema/FK/RLS/PII/retention/owner, API или event contract, migration/rollback и evidence; отсутствие любого поля блокирует `APPROVED`. |
| AC-311 | V26 data inventory перечислял сущности, но не фиксировал минимальные поля, связи, scope и immutable audit; разные реализации могли создать несовместимые схемы. | Утвердить field-level schema для каждой V26-сущности, включая обязательные IDs/версию/источник/время, PII/RLS/retention и migration tests. |
| AC-312 | Новые V26 REQ не имели явной API-поверхности; реализация могла остаться только в UI или породить несогласованный namespace. | Для каждого V26 endpoint определить request/response schema, auth/scope, idempotency, errors, retry, audit и owner; proposed paths не считать implemented без OpenAPI и behavioral evidence. |
| AC-313 | Сам v2.6 addendum противоречит себе: §0.3 заявляет два исключения изменения существующих доменов (§4/§6), а §8.3 — только одно (§3.1 delivery/priority engine). | Принять `DEC-022` с точным перечнем исключений, affected REQ и датой; до решения считать разрешённым только явно зафиксированный §3.1 и блокировать изменения Campaign/Delivery/PoP. |
| AC-314 | Диагностика `UNMAPPED` V26 не давала подготовленного, проверяемого разбиения на задачи; перенос в roadmap мог породить дубли или потерять owner/dependency/evidence. | Согласовать proposed `CAND-V26-*` breakdown, затем перенести только утверждённые задачи в canonical roadmap с уникальным ID, owner, dependency, сроком, acceptance и evidence; до этого они не считаются roadmap coverage. |
| AC-315 | V26 stories не имели journey-контрактов, а design aliases могли быть ошибочно приняты за canonical journeys и UI readiness. | Для каждой planned story определить canonical dot-case journey, Given/When/Then, route, visible clicks, selectors, smoke и operator walkthrough; design-only stories оставить `designed-not-implemented` до owner ADR. |
| AC-316 | Lexical rule о запрещённых расплывчатых словах не отделяла active normative prose от исторических AC/changelog и source quotations, создавая ложные нарушения или пропуски. | Lint должен проверять только active normative sections; historical/source text маркируется и не превращается в новое требование без REQ/DEC disposition. |
| AC-317 | После добавления V26 story-map старые ссылки на текущий count 32 `US-*` стали неверны: snapshot r390 давал 39, а фактический текущий total — 41 (32 core + 7 V26 + 2 registry-gap). | Хранить counts с типом/snapshot revision, считать definition rows программно и блокировать approval при расхождении story catalog, journey map и registry. |
| AC-318 | `HEAD` и рабочая редакция использовали разные revision namespaces (`r40` и `r390+`) без parent identity; review/evidence могли быть привязаны к неверному snapshot. | Для каждой редакции хранить parent commit/blob SHA, source SHAs, monotonic changelog и явный continuity note; validator отклоняет revision без проверяемого parent или с несогласованной sequence. |
| AC-319 | Extracted addendum был создан механически, но без зафиксированных provenance и regeneration policy; повторное извлечение могло незаметно изменить line numbers и traceability. | Хранить input/output, инструмент, paragraph/table counts и SHA; повторный extraction обязан быть byte-stable либо сопровождаться diff, новой revision и повторной line-level классификацией. |

До закрытия AC-01…AC-326 документ остаётся `DRAFT/REVIEW`; текст без артефакта и evidence не считается покрытием.

## Дополнение AO. Canonical snapshot для повторной сверки

Снимок снят `2026-08-27` из рабочего Git-дерева; live `origin/develop` и `HEAD`:
`b21174f93b2d5468fb2a80d63a4db35cb4906464`. Он предназначен для обнаружения дрейфа,
а не для утверждения статусов. На этом снимке:

| Набор | Артефакт | Количество/срез | Ограничение доказательства |
|---|---|---:|---|
| Features | `docs/product/feature-registry.yaml` | 58 unique IDs: 53 `reachable`, 5 `blocked`; SHA-256 `bff10ddcffe93b431b4d5a4cdf7355a56bb3aed833fc38f16ed979cea8c7a20e` | reachable требует собственного UI/behavioral proof |
| Roadmap tasks | `docs/product/roadmap.yaml:tasks` | 43; file SHA-256 `65e6d7519f3e38f20352579ff9573ae0a71b8e80d3a7c536eece14de7698f13e` | mapping к REQ/story/DEC ещё не доказан |
| Roadmap stages | `docs/product/roadmap.yaml:stages` | 6 | не считать продуктовой задачей без classification |
| Owner decisions | `docs/product/roadmap.yaml:owner_decisions` | 16 | статус/дата требуют owner evidence |
| Governance gates | `docs/product/roadmap.yaml:gates` | 3 | отдельный тип, не смешивать с task count |
| Blocked features | `docs/product/roadmap.yaml:blocked_features` | 5 | не заменяют roadmap task или approved exclusion |

При следующем изменении канона пересчитываются все строки, фиксируются SHA и дата,
а разница классифицируется как добавление/удаление/переименование/изменение статуса.
Старые числа из changelog (например, `73`) остаются только dated snapshot и не должны
использоваться для текущего процента покрытия.

## Дополнение AE. Результат построчного аудита исходника

Предварительно в извлечённом v2.5 заявлялось 149 строк-кандидатов на нормативные обязательства
(маркеры «должен», «обязан», «необходимо», «запрещается», «не допускается» и эквиваленты).
Это число и диапазон 148–164 остаются `UNVERIFIED`: текущий наивный regex-скан даёт 180
совпадений, включая заголовки, пояснения и повторные/составные строки, поэтому его нельзя
считать числом нормативных предложений. Итоговое количество атомарных обязанностей неизвестно
до нормализованного классификатора, который исключит не-нормативный текст и разложит составные
строки. Оно не равно числу REQ: одна строка может содержать несколько обязанностей. Исторический
snapshot на 80 REQ и карта 25 разделов не доказывают полноту классификации. Для публикации v2.6 требуется
машинный отчёт:

```text
source_line | source_section | obligation_id | REQ-ID | normative | disposition
```

Допустимые исходы: `mapped` (есть REQ-ID), `split` (строка разложена на несколько REQ),
`approved-exclusion` (есть DEC-ID и owner approval). Любая строка без исхода — блокер
AC-17; процент покрытия считается по атомарным obligations, а не по числу заголовков.

`PROCESS-*` допускается только для агентских/операционных процедур, не являющихся
продуктовым требованием. Для каждого такого ID ведётся process registry с форматом
`id`, `source`, `owner`, `steps`, `evidence` и `review_on`; ссылка без записи в реестре
считается orphan и блокирует `APPROVED`.

Минимальный шаблон записи process registry:

```yaml
id: PROCESS-AGENT-001
source: "TZ v2.5 §21.9"
owner: "назначается"
steps: ["подготовить отчёт шага", "приложить команды и evidence"]
evidence: []
review_on: "YYYY-MM-DD"
status: proposed
```

`PROCESS-*` не закрывает продуктовый REQ и не может иметь status `approved` без
заполненных owner, evidence и даты пересмотра.

## Дополнение AF. Обратная трассировка нормативного текста

В финальной редакции нормативное предложение не может существовать только в прозе.
Каждая фраза с `MUST/SHOULD/MAY` или эквивалентом русского языка должна иметь inline
маркер вида `[REQ-ID]` либо находиться в строке каталога REQ. Проверка проходит в
обе стороны: каталог не содержит «мёртвых» REQ, а нормативная проза не содержит
«безымянных» обязательств. Обычные пояснения и примеры маркируются `NON-NORMATIVE`,
чтобы не превращаться в скрытые требования.

## Дополнение AG. Handoff-пакет перед началом разработки

Переход из `REVIEW` в `APPROVED` выполняется только после публикации следующих
артефактов. Владелец проекта назначает ответственного и принимает каждый артефакт
отдельно; наличие ссылки на файл без его проверки не считается выполнением.

| Артефакт | Ответственный | Минимальное доказательство |
|---|---|---|
| `requirements-traceability.yaml` | Product + Technical owner | все атомарные REQ, source-line disposition, roadmap-ID, status, acceptance, evidence |
| `role-scope-matrix.yaml` | Security owner | permission-коды, scope, deny-cases и RLS negative matrix |
| `portal-route-matrix.yaml` + `journeys/` | Product/UX owner | route, selectors, Happy-path, negative path, smoke и walkthrough policy |
| OpenAPI + event/manifest JSON Schema | Technical owner | version, examples, compatibility/deprecation и contract tests |
| ERD + data dictionary + migration plan | Data/Technical owner | FK/unique/index/RLS/PII/retention, backfill и rollback |
| `channel-capability-matrix.yaml` | Channel owner | channel/surface/rendition/proof/SLA/vendor constraints |
| `nfr-slo.yaml` + `load-profiles.yaml` | SRE/Operations owner | method, percentile, error budget, generator и CI evidence |
| `retention-policy.yaml` + legal decision register | Security/Legal owner | сроки, основания 152-ФЗ, deletion/archive и review date |
| DEV environment manifest | Operations owner | `docs/product/environment-inventory.yaml` как текущий источник: endpoint/версии/Git SHA/schema/доступность без секретов; seed/reset и недостающие поля дополняются отдельным manifest; baseline `.81` |
| roadmap + generated business/technical views | Product/PMO owner | каждая REQ имеет задачу или approved deferred; status подтверждён Git/CI |

Порядок gate: (1) owner decisions и RACI, (2) трассировка и схемы, (3) portal
journeys/smoke, (4) миграция и compatibility, (5) NFR/security/DR evidence, (6)
независимая сверка Claude Code и Codex, (7) owner approval. До шага (7) Claude Code
может готовить mini-design и тестовые фикстуры, но не начинать реализацию новых
продуктовых функций.

## Дополнение AI. Матрица покрытия исходного плана реализации

| Шаг v2.5 | Содержимое в v2.6 | Выходной gate-артефакт |
|---:|---|---|
| 0 | каркас, окружения, требования и пилотный стенд | environment manifest, source/REQ baseline, feasibility evidence |
| 1 | core, PostgreSQL и безопасность | ERD/migrations, auth/RBAC/RLS negative proof |
| 2 | hierarchy, channels, devices и certificates | channel/device registry, capability contract, heartbeat proof |
| 3 | media, MinIO, SHA, QA и moderation | media/rendition schemas, malware/QA evidence |
| 4 | inventory, forecast, sold-out и conflicts | formulas, simulation examples, inventory proof |
| 5 | advertiser/order/campaign/placement/workflow | campaign lifecycle, approvals and flight evidence |
| 6 | playlist, schedule, manifest и adapter payload | signed manifest schema, compatibility proof |
| 7 | players, adapters, cache, fallback и rollout | device/channel contract, offline/rollback proof |
| 8 | PoP ingestion, queue, ClickHouse и dedupe | `proof_event_v1`, batch/duplicate/quarantine tests |
| 9 | analytics, reports, advertiser portal и export | plan/fact/channel-quality report evidence |
| 10 | emergency management и expanded audit | scope/priority/rollback/audit evidence |
| 11 | HA, backup, monitoring, load и production hardening | restore/load/DR/SLO evidence and runbooks |

Шаги 1–13 из §21.7 группируются в эти 12 delivery stages без потери обязательств:
шаги 1–2 → stage 0/1, 3–5 → stage 1/2, 6 → stage 3, 7 → stage 4/5,
8 → stage 6, 9 → stage 7, 10 → stage 8, 11 → stage 9, 12 → stage 10,
13 → stage 11. Любое расхождение с этой матрицей получает DEC-ID и не может быть
замаскировано изменением названия этапа.

## Дополнение AD. Детальная проверка подразделов §23–§25 исходного ТЗ

Первичная карта разделов покрывала только верхний уровень. Для исключения скрытых
обязательств подразделы мультиканальной архитектуры проверяются отдельно:

| Источник | Атомарное покрытие | Обязательный артефакт |
|---|---|---|
| §23.1 | REQ-CORE-002, REQ-CHAN-001 | channel-agnostic domain contract |
| §23.2 | REQ-CHAN-001, REQ-CHAN-002, REQ-CHAN-003 | channel/device/carrier capability and control matrix |
| §23.3 | REQ-CHAN-002, REQ-CHAN-003, REQ-DATA-001 | physical/logical/surface ERD and independent carrier operations |
| §23.4 | REQ-CONT-001, REQ-MAN-001 | rendition registry and preview proof |
| §23.5 | REQ-MAN-001, REQ-MAN-002, REQ-ORCH-002 | manifest/adapter contract tests |
| §23.6 | REQ-BIZ-001, REQ-POP-001, REQ-OPS-004 | per-channel inventory/SLA/report definitions |
| §23.7 | REQ-INT-002, REQ-SEC-004 | price-master validation and fail-closed test |
| §23.8 | REQ-UX-001, REQ-UX-002, REQ-UX-004 | portal route/role/scope/selector matrix + campaign readiness matrix |
| §23.9 | REQ-GOV-001, REQ-OPS-002 | owner-approved rollout priority and exit criteria |
| §24.1–24.4 | REQ-ARCH-001, REQ-CORE-001, REQ-CORE-002, REQ-CHAN-001, REQ-CHAN-002 | ADR/ERD/domain-boundary review |
| §24.5–24.9 | REQ-ORCH-001, REQ-ORCH-002, REQ-MAN-001, REQ-MAN-002, REQ-MAN-005, REQ-POP-001, REQ-POP-002 | orchestration, manifest, playlist inheritance, event and proof schemas |
| §24.10–24.11 | REQ-DATA-001, REQ-API-001 | migration and compatibility matrix |
| §24.12–24.13 | REQ-GOV-001, REQ-NFR-003 | implementation impact and architecture acceptance |
| §25 | REQ-GOV-001 | signed pre-development checklist |

Подразделы §21.1–§21.10 исходника (роль и порядок работы Hermes, его запреты,
структура проекта, API-first, тесты и отчётность агента) классифицируются как
`approved-exclusion` из продуктового ТЗ: Hermes retired и не является runtime-зависимостью.
Процессные правила заменены действующими `AGENTS.md`/`CLAUDE.md`; они не создают
продуктовых REQ, но сохраняются в traceability с DEC-ID/owner как исторический источник.

Сокращения `/` и `…` в этой таблице допустимы только как человекочитаемая группировка;
машинная трассировка обязана раскрывать каждый ID отдельной ссылкой. Отсутствие
подраздела, артефакта или owner decision считается orphan и блокирует `APPROVED`.

## Дополнение AL. Матрица обязательных зон тестирования из §21.6

Каждая зона обязательных тестов исходника должна иметь отдельный набор evidence; наличие
только endpoint-тестов или статической проверки исходников не считается покрытием.

| Зона §21.6 | Требования | Минимальное доказательство |
|---|---|---|
| Auth, RBAC/RLS и tenant scope | REQ-SEC-001, REQ-SEC-002 | positive/negative matrix по ролям, арендаторам и approved-campaign permission |
| Иерархия и target resolution | REQ-CORE-001, REQ-CORE-003, REQ-CHAN-002 | тесты Network→Branch→Cluster→Store→Device/Surface и запрет physical-device target |
| Playlist inheritance/override и schedule conflicts | REQ-MAN-005, REQ-BIZ-001 | precedence, effective time, conflict/sold-out и воспроизводимость historical snapshot |
| Версии media/creative/playlist/manifest | REQ-CONT-002, REQ-MAN-001, REQ-MAN-002, REQ-MAN-004 | immutable version, SHA/signature, compatibility и rollback tests |
| Media QA и renditions | REQ-CONT-001 | per-rendition automated + visual QA, approved-only manifest и audit fields |
| Device registration/certificates/revoke | REQ-CHAN-002, REQ-SEC-003 | issuance, rotation, revoke и negative access tests |
| PoP batch, idempotency и duplicate protection | REQ-POP-001…004 | batch, signature, dedupe, offline resend, quarantine и 409/422 tests |
| Emergency, audit и staged rollout | REQ-OPS-002, REQ-OPS-007 | action/permission/scope/partial-result tests, rollback evidence и immutable audit |
| Reports/export и advertiser isolation | REQ-BIZ-004, REQ-BIZ-011, REQ-SEC-002, REQ-INT-003 | plan/fact, channel proof semantics, export scope и cross-tenant negative tests |

Матрица является блокирующей для утверждения: каждая строка должна быть связана с
конкретным test/evidence ID в `requirements-traceability.yaml`; отсутствие ссылки означает
`unverified`, даже если соответствующий REQ описан текстом.

## Дополнение AJ. Recommended baseline stack (не утверждённый выбор)

До owner approval этот список является рекомендацией из starting decisions, а не
нормативным требованием реализации:

| Слой | Рекомендация | Обязательная оговорка |
|---|---|---|
| Backend | Python 3.12+, FastAPI, SQLAlchemy 2, Alembic, Pydantic v2 | async I/O и import boundaries по ADR-012/014 |
| Events/data | NATS JetStream, PostgreSQL, ClickHouse, Redis | queue/HA/retention profile утверждаются DEC-004/012 |
| Media/artifacts | MinIO | private buckets, lifecycle и restore evidence |
| Frontend | React, TypeScript, Vite, TanStack Router/Query, restrained design system | accessibility/locales требуют owner decision |
| Runtime | KSO sidecar + Chromium первым каналом; ETag/304, cache, offline TTL, PoP resend | остальные каналы через adapters; Orchestrator по DEC-002 |
| Security | AD/SSO, critical-role MFA, break-glass, rotated credentials, Ed25519 production/HMAC dev | profile среды и сроки rotation/revoke обязательны |

Если выбран другой компонент, DEC-ID обязан описать совместимость с API/event/ERD,
миграцию, стоимость владения, операционный owner и rollback. Рекомендация сама по себе
не разрешает менять production stack.

## Дополнение AK. ADR alignment register

| ADR | Обязательный эффект для ТЗ v2.6 |
|---|---|
| ADR-001 | сервисные границы и базовый async-first stack не обходятся локальной вертикалью |
| ADR-002 | NATS JetStream/event bus для durable delivery, replay, consumer groups и DLQ; брокер не заменяется ephemeral cache |
| ADR-003 | device identity, enrollment, credential rotation/revoke и mTLS/token boundary для runtime |
| ADR-004 | React + TypeScript frontend и согласованная UI-архитектура без обхода backend permission contract |
| ADR-005 | единые monitoring/observability conventions, metrics/logs/traces и эксплуатационные dashboards |
| ADR-006 | user identity, RBAC permission codes, session/MFA и audit binding |
| ADR-007 | границы operational PostgreSQL и analytical ClickHouse, lineage и отсутствие смешения фактов/агрегатов |
| ADR-008 | testing strategy, phase gates и evidence уровней schema/behavioral/UI/load/restore |
| ADR-009 | fail-closed scope resolution и PostgreSQL RLS как обязательный deny-by-default control |
| ADR-010 | advertiser domain foundation: advertiser/brand/order/contract ownership и их связи с campaign |
| ADR-011 | transactional outbox для каждого delivery-relevant domain event |
| ADR-012 | blocking I/O запрещён в async handlers/dependencies |
| ADR-013 | edge fail-safe, last-known-good/fallback и runtime kill-switch |
| ADR-014 | import/layer boundaries: apps → api → auth → domain; domain не импортирует api |
| ADR-015 | campaign entity graph, flight windows, tenant ownership и approval invariants |
| ADR-016 | async delivery eligibility, target resolution и revocation pipeline |
| ADR-017 | runtime-only PoP, canonical flat schema и ingestion validation |
| ADR-018 | retailer/tenant hierarchy, retailer_id и двухуровневая RLS-модель для следующей ветки |
| ADR-019 | Orchestrator, Adapter Layer и mock adapters deferred до второго реального канала; KSO-first сохраняет только thin compatibility seam и channel-neutral data contracts |
| ADR-020 | расхождение факта и требования решается owner decision/изменением поведения, не тихой правкой документа |

При конфликте этого драфта с ADR действует ADR precedence из `AGENTS.md`; конфликт
получает DEC-ID и блокирует перенос в roadmap до решения владельца.

## Дополнение AM. Line-level traceability v2.6 Next Branch

Источник: `docs/00-source-of-truth/TZ_Retail_Media_Platform_v2_6_Next_Branch_2026-07-11.extracted.md`,
SHA `23e08e8ba560aae223235e2cfc94a9ebe75162396c9178bc39742419c19b8ff4`. Номера — строки
extracted-файла; диапазоны перечислены явно, чтобы не скрывать составные обязанности.

| Extracted lines | Classification | Coverage |
|---|---|---|
| 11, 13, 19, 23, 39 | source/extension boundary, tenant decision, additive RLS | REQ-V26-001, REQ-GOV-002, DEC-required |
| 55, 59, 61, 63, 67 | sales proof, entities, baseline, test/control, aggregation privacy | REQ-V26-002 |
| 85, 89, 91, 93 | advertiser app, common approval, guardrails/conflict, credit check | REQ-V26-003 |
| 111, 113, 123 | competitive rule, configurable interval/exceptions, acceptance | REQ-V26-004 |
| 129, 131 | anonymous store attributes; source claims an existing master adapter, while current code has none | REQ-V26-005 + prerequisite gap |
| 143, 147 | financial export and external payment callback | REQ-V26-006 |
| 157, 161, 163 | programmatic extension and explicit no-auto-buy boundary | REQ-V26-007 |
| 175, 177 | dynamic marker/static hash and master-price authority | REQ-V26-008 |
| 187, 191 | mobile scope, photo proof/incident, no admin/publish | REQ-V26-009 |
| 201 | delivery-vs-lift winner metric | REQ-V26-010 |
| 209, 217, 221 | design-only measurement, provider exclusion, ADR acceptance | REQ-V26-011 |
| 233, 235 | versioned external contracts and additive-only Campaign/Delivery/PoP constraint | REQ-GOV-002, REQ-ARCH-002 |
| 251 | historical Hermes implementation-agent wording | PROCESS/EXCLUSION; superseded by AGENTS.md |

Предыдущий счёт `34 = 21 mapped + 13 NON-NORMATIVE` **отозван**: таблица содержит 35
line references, а исходник включает составные нормативные предложения и checkbox-
критерии, которые эта ручная карта не раскладывает атомарно. До появления именованного
classifier и полного `source_line → obligation_id → disposition` manifest любые totals
этого приложения имеют статус `UNVERIFIED` и не используются как coverage KPI.

## Дополнение AN. V2.6 extension → текущая roadmap/registry

Срез выполнен по `docs/product/roadmap.yaml`, `feature-registry.yaml` и
`user-journeys.md` (2026-08-27). `UNMAPPED` означает реальный пробел планирования, а
не разрешённое «будет позже».

| REQ-V26 | Найденный canonical ID | Текущий статус покрытия |
|---|---|---|
| V26-001 | ADR-018, OD-003, RM-STAB-003 | decision accepted, implementation disputed: ADR-018 утвердил вариант B; OD-016 относится только к выводу хоста `.77`; требуется проверить фактическую retailer-scope/RLS реализацию |
| V26-002 | OD-014 | partial/open: attribution упомянут, но нет отдельной task/evidence для четырёх сущностей и pilot |
| V26-003 | OD-005, OD-013, RM-BIZ-002; `self.*` registry | partial/blocked: текущий scope managed-first, полный self-service из addendum не закрыт |
| V26-004 | — | UNMAPPED: нет task/decision/registry journey competitive separation |
| V26-005 | — | UNMAPPED: нет task/decision/registry journey store-audience targeting |
| V26-006 | — | UNMAPPED: нет task/decision/registry journey financial-system exchange |
| V26-007 | — | UNMAPPED: нет task/decision на SSP-facing extension |
| V26-008 | — | UNMAPPED: нет task/decision на dynamic creative MVP |
| V26-009 | — | UNMAPPED: нет task/decision/registry journey field mobile operations |
| V26-010 | OD-014 | partial: winner metric не выделена отдельной acceptance/task |
| V26-011 | — | UNMAPPED: нет task/decision на external audience measurement |

До создания задач или owner-approved `designed-not-implemented` disposition для каждой
строки `UNMAPPED` v2.6 coverage не считается полной и документ не может перейти в
`APPROVED`. Внешний monitoring-dashboard может подтвердить наблюдаемое состояние, но не
создаёт roadmap coverage и не заменяет owner decision.

Кандидатный task-breakdown (не каноническая roadmap до owner ACCEPT). Идентификаторы `CAND-*`
намеренно не соответствуют шаблону `roadmap.yaml` и не являются принятыми RM-задачами.

| Proposed task | REQ-V26 | Owner role | Dependencies | Minimum evidence |
|---|---|---|---|---|
| `CAND-V26-001` | V26-001 | product/architecture owner | ADR-018, OD-003, RM-STAB-003 | behavioral retailer-scope/RLS proof + migration impact; новый tenant ADR не требуется без изменения принятой модели |
| `CAND-V26-002` | V26-002 | analytics/product owner | CAND-V26-001, master-sales adapter | pilot test/control lift report |
| `CAND-V26-003` | V26-003 | advertiser product owner | OD-005/013, shared approval | UI journey + budget/conflict negatives |
| `CAND-V26-004` | V26-004 | campaign/inventory owner | priority engine | separation block/override test |
| `CAND-V26-005` | V26-005 | data/product owner | master-data adapter | attribute targeting contract/test |
| `CAND-V26-006` | V26-006 | finance/integration owner | DEC-017, API gate | idempotent export round-trip |
| `CAND-V26-007` | V26-007 | architecture owner | inventory planning design | ADR + proposed schema |
| `CAND-V26-008` | V26-008 | content/channel owner | master price contract | dynamic manifest SLA test |
| `CAND-V26-009` | V26-009 | operations/UX owner | RBAC/RLS, device health | mobile photo/incident journey |
| `CAND-V26-010` | V26-010 | analytics/product owner | CAND-V26-002, REQ-BIZ-012 | owner-approved winner report |
| `CAND-V26-011` | V26-011 | measurement/legal owner | DEC-022, provider decision | ADR + export contract |

Эти IDs не должны появляться в `roadmap.yaml` автоматически: перенос выполняется только
после owner approval, назначения конкретного владельца/срока и проверки, что task не
дублирует существующую RM/OD-задачу.

## Дополнение AP. Нормативный acceptance-registry всех user stories r415

Это приложение дополняет краткие таблицы §4, Дополнения T и story-map v2.6. Оно является
единственным полным story-contract внутри этого драфта. `Status` описывает доказанное
состояние, а не желаемую готовность. `PENDING-ID` означает, что canonical journey ещё не
утверждён; alias не создаёт новую функцию. Каждый шаг — одно видимое действие и видимый
next-step. `walkthrough` для всех UI stories остаётся `PENDING` до решения человека.

| Story | Actor; permission; scope | Preconditions; entry | Happy-path | Negative path; audit | Traceability; status |
|---|---|---|---|---|---|
| US-CAM-001 | campaign manager; `campaigns.manage`; retailer/store/surface | approved advertiser/order basis, inventory readable; `/login` | Happy-path: 7 шагов — Campaigns → Create → basis/period → targets → inventory preview → creative → Save draft | no permission, foreign scope, sold-out/conflict → deny/explain; `campaign.created` | `campaign.create`, `inventory.simulate`; REQ-BIZ-001, REQ-UX-001; current partial |
| US-CAM-002 | campaign manager; `campaigns.manage`; campaign scope | complete draft/checklist; `/login` | Happy-path: 4 шага — campaign → Readiness → resolve visible blockers → Submit | missing creative/inventory or foreign campaign → blocked; `campaign.approval_requested` | `campaign.submit`; REQ-BIZ-003, REQ-SEC-002; current partial |
| US-MOD-001 | moderator; `creatives.moderate`; retailer | uploaded rendition; `/login` | Happy-path: 5 шагов — Moderation → item → preview/QA → approve or reject with reason → result | wrong scope, missing rendition, empty reject reason → deny; `creative.moderation_decided` | `creative.moderate_approve/reject`; REQ-CONT-001, REQ-UX-001; canonical split |
| US-APR-001 | approver; `campaigns.approve`; retailer | pending approval and readiness evidence; `/login` | Happy-path: 5 шагов — Approvals → campaign → impact/readiness → approve or reject → status | self-approval or missing right/readiness → deny; `campaign.approval_decided` | `campaign.approve/reject`; REQ-BIZ-003, REQ-SEC-002; current |
| US-OPS-001 | ops operator; `devices.read`, action-specific manage permission; assigned hierarchy | device exists; `/login` | Happy-path: 6 шагов — Devices → filters → device → health/errors → diagnostic action preview → result | foreign scope/destructive action without confirmation → deny; `device.diagnostic_requested` | `device.health_view`; REQ-OPS-001, REQ-UX-001; current read, actions planned |
| US-OPS-002 | release operator; `rollouts.manage` PENDING; rollout scope | signed build and thresholds; `/login` | Happy-path: 6 шагов — Rollouts → select version/cohort → preview → start → inspect metrics → rollback | unsigned build/threshold breach/foreign cohort → stop; `rollout.started/rolled_back` | `PENDING-ID rollout.rollback`; REQ-OPS-002, REQ-OPS-004; planned |
| US-SEC-001 | security admin; `audit.read` plus security-review permission PENDING; retailer/global | audit events available; `/login` | Happy-path: 5 шагов — Audit → critical filter → event detail → correlate actor/resource → export evidence | PII/secret leakage, tamper or no right → deny/alert; `security.review_recorded` | `audit.view` plus `PENDING-ID security.review`; REQ-SEC-001, REQ-SEC-003, REQ-SEC-004; partial |
| US-ADV-001 | advertiser; `campaigns.read`; own advertiser membership | approved membership; `/login` | Happy-path: 5 шагов — My campaigns → campaign → plan/fact → underdelivery explanation → export | cross-advertiser, missing PoP or blocked report → deny/explain; `advertiser.report_exported` | `self.campaign_view`, `self.report_view`; REQ-BIZ-003, REQ-UX-001; report blocked |
| US-ANL-001 | analyst; read permissions for campaigns/inventory; assigned scope | reporting facts available; `/login` | Happy-path: 6 шагов — Analytics → filters → plan/fact → causes → compare grain → export | stale/empty/foreign data → labelled or denied; `analytics.exported` | `PENDING-ID analytics.compare`; REQ-BIZ-004, REQ-UX-001; planned |
| US-EMR-001 | emergency operator; `emergency.manage`; selected hierarchy | MFA/reason and impact preview; `/login` | Happy-path: 6 шагов — Emergency → scope → reason → preview → confirm → progress/result | missing MFA/reason, broader scope or partial failure → deny/show each result; `emergency.activated/deactivated` | `emergency.activate/deactivate`; REQ-OPS-001, REQ-SEC-004; current |
| US-ADM-001 | system admin; action-specific backend permissions; assigned scope | authenticated admin; `/login` | Happy-path: 6 шагов — Admin section → choose object → inspect permissions/scope → edit → confirm → result | missing permission, UUID leakage or approved-campaign mutation → deny; domain-specific immutable audit | `user.assign_roles`, `device.health_view`, `audit.view`; REQ-SEC-001, REQ-SEC-002, REQ-OPS-001, REQ-UX-001; split required |
| US-CHAN-001 | channel owner; `channels.manage` PENDING; retailer/channel | approved channel decision; `/login` | Happy-path: 7 шагов — Channels → New → type/profile → adapter contract → mock test → review → submit | unknown capability/adapter or missing owner → blocked; `channel.version_created` | `PENDING-ID channel.register`; REQ-CHAN-001, REQ-ORCH-002; planned |
| US-CHAN-002 | content/channel owner; `renditions.manage` PENDING; channel/profile | channel profile exists; `/login` | Happy-path: 6 шагов — profile → Renditions → constraints → upload/generate → validate preview → publish version | incompatible rendition or unsafe content → reject; `rendition.validation_decided` | `PENDING-ID channel.rendition_validate`; REQ-CONT-001, REQ-MAN-001; planned |
| US-CHAN-003 | ops operator; `carriers.manage` PENDING; channel/carrier/surface | carrier inventory available; `/login` | Happy-path: 8 шагов — Operations → filter scope → select carriers → action → preview → confirm → progress → retry failed | cross-surface effect, duplicate request or partial failure → isolate/report; `carrier.bulk_action_completed` | `PENDING-ID carrier.manage`; REQ-CHAN-003, REQ-OPS-001, REQ-SEC-002, REQ-UX-001; planned |
| US-LIC-001 | licensing operator; `license.read` plus manage permission PENDING; retailer/devices | valid signed grant; `/login` | Happy-path: 7 шагов — Licensing → grant/scope → signature/validity → seat impact → confirm → apply → report | invalid signature/seat overflow/rollback loss → fail closed; `license.grant_applied` | `license.report/enforce/seat_release`, Layer-2 `license.view/upload`; REQ-LIC-001, REQ-SEC-003, REQ-UX-001; partial/blocked |
| US-COM-001 | commercial operator; `commerce.*`; retailer/order | tariff and capacity exist; `/login` | Happy-path: 9 шагов — Commerce → tariff version → prices → quote → order → reserve → book → close → audit | stale tariff, double booking, capacity conflict or false payment → reject; `commerce.order_transitioned` | seven `commerce.*` features; REQ-BIZ-014, REQ-BIZ-009, REQ-SEC-002, REQ-UX-001; current with conditional payment |
| US-ADV-002 | applicant plus onboarding manager; application/review/advertiser permissions; public then retailer/advertiser | public apply enabled; public entry then `/login` | Happy-path: 9 шагов — apply → legal/contact → submit → review → organization → brand → invite → login → own workspace | pre-approval commercial access, expired invite or cross-org → deny; application/invite/member audit events | advertiser apply/review/create/legal/contact/brand/invite features; REQ-BIZ-015, REQ-SEC-002, REQ-UX-001; partial |
| US-ADV-003 | system admin or campaign manager; `advertisers.manage`; advertiser/retailer | advertiser exists; `/login` | Happy-path: 9 шагов — Advertisers → organization → Contracts → create → select PDF → upload → complete → filename/status → reload | non-PDF, oversize, SHA mismatch, foreign advertiser → reject; `advertiser.contract_file_completed` | canonical `advertiser.contract_crud`; journey alias `advertiser.contract_pdf_upload` мигрируется при cutover; REQ-BIZ-017, REQ-SEC-004, REQ-UX-001; current metadata, version/SHA required |
| US-ADM-002 | role operator; `roles.read/manage`; assigned user scope | backend permission catalog available; `/login` | Happy-path: 4 шага — Users → user roles → catalog 30 backend permissions → inspect code/label/description | frontend-only phantom, missing backend code or out-of-scope assignment → block; `user.roles_changed` only on mutation | sub-function of `user.assign_roles`; REQ-UX-005, REQ-SEC-002, REQ-UX-001; current gap 23/30 |
| US-INV-001 | inventory manager; `inventory.manage`; retailer/channel/surface/store | capacity/profile exists; `/login` | Happy-path: 8 шагов — Rules → New → dimensions/window/priority → Simulate → conflicts/forecast → submit → approve → activate/rollback | overbooking, stale version or effective-date conflict → reject; `inventory.rule_version_activated` | `inventory.rule_create`, shared `inventory.simulate`; REQ-BIZ-016, REQ-BIZ-001, REQ-UX-001; current create, approval/version target |
| US-DATA-001 | data steward; `data.governance` PENDING; dataset/entity | data inventory exists; `/login` | Happy-path: 6 шагов — Data catalog → entity → owner/class → retention/lineage → validate → publish version | missing lawful basis/owner or forbidden retention → block; `data.policy_versioned` | `PENDING-ID data.catalog`; REQ-DATA-001, REQ-SEC-004; planned/decision required |
| US-FIN-001 | finance controller; commerce/report read permissions; retailer/order | immutable tariff/order/PoP basis | Happy-path: 6 шагов — Reconciliation → order → tariff/capacity → plan/fact → compensation → sign result | missing external proof, mutable basis or cross-retailer → block; `finance.reconciliation_signed` | `PENDING-ID finance.reconcile`; REQ-BIZ-002, REQ-BIZ-009; planned |
| US-INT-001 | integration operator; `integrations.read/manage` PENDING; connector | approved connector/config without exposed secrets | Happy-path: 6 шагов — Integrations → connector → health → reconciliation preview → run → result | stale master, secret exposure or mismatch → fail closed; `integration.reconciliation_completed` | `PENDING-ID integration.reconcile`; REQ-INT-001, REQ-INT-002; blocked by master adapter |
| US-REL-001 | release owner; `rollouts.manage` PENDING; environment/cohort | signed artifact, green gates, rollback target | Happy-path: 6 шагов — Releases → version → evidence/metrics → approve cohort → deploy → rollback if threshold | missing evidence, wrong SHA or failed rollback → stop; `release.decision_recorded` | `PENDING-ID release.rollback`; REQ-OPS-002, REQ-OPS-003; planned |
| US-DR-001 | operations owner; `operations.backup_restore` PENDING permission; component/environment | verified backup and isolated target | Happy-path: 6 шагов — DR → backup → verify → restore isolated → validate RTO/RPO/data → sign result | corrupt backup, wrong scope or destructive production target → abort; `dr.restore_completed` | canonical feature `backup.restore`; REQ-OPS-003; current service proof, owner drill required |
| US-REG-001 | auditor; read-only governance access; repository | pinned source/Git/CI SHAs | Happy-path: 6 шагов — requirements → traceability → roadmap → Git/CI → environment/monitoring → disposition | stale SHA, orphan ID or monitoring override → flag; `governance.audit_recorded` artifact | `PENDING-ID audit.compare`; REQ-GOV-001; planned governance |
| US-FLT-001 | campaign manager; `campaigns.manage`; campaign/placement | draft campaign and timezone | Happy-path: 6 шагов — campaign → Flights → New → local window/TZ → validate → save version | end before start, DST ambiguity or active immutable window → reject; `campaign.flight_versioned` | `PENDING-ID campaign.schedule`; REQ-BIZ-005; partial API |
| US-ELG-001 | campaign manager/approver; campaigns read/approve; campaign | campaign graph complete | Happy-path: 5 шагов — campaign → Readiness → eligibility checks → resolve blockers → regenerate | rejected creative, no target, revoked device or expired window → ineligible; `campaign.readiness_evaluated` | `PENDING-ID campaign.readiness`; REQ-BIZ-006; partial service |
| US-PRI-001 | inventory manager; `inventory.manage`; rule/surface | versioned priority policy | Happy-path: 6 шагов — Priority rules → type/value → simulation → preemption explanation → approve → activate | silent preemption, tie ambiguity or emergency override → block/escalate; `inventory.priority_versioned` | `PENDING-ID inventory.priority`; REQ-BIZ-007; planned |
| US-UDR-001 | analyst; campaigns/report read; campaign/placement | plan and accepted PoP | Happy-path: 6 шагов — report → plan/fact → causes → SLA deficit → make-good proposal → save | missing proof, mixed units or negative compensation → reject; `campaign.make_good_proposed` | `PENDING-ID campaign.underdelivery`; REQ-BIZ-008; planned |
| US-WFL-001 | campaign manager; `campaigns.manage`; campaign | end reached and reconciliation complete | Happy-path: 5 шагов — campaign → Close readiness → final plan/fact → reasons/compensation → Complete | active flight, unresolved deficit or no approval → block; `campaign.completed` | canonical `campaign.complete`; REQ-BIZ-010; current transition, workflow evidence needed |
| US-RPT-001 | analyst/advertiser; read permission; role-specific scope | reporting facts and freshness known | Happy-path: 6 шагов — Reports → view/grain → filters → freshness → drill-down → export | cross-tenant, stale unlabeled data or unsupported format → deny/explain; `report.exported` | admin reporting plus `self.report_view`; REQ-BIZ-011; advertiser path blocked |
| US-AB-001 | analyst/product owner; `experiments.manage` PENDING; campaign/cohorts | attribution facts and minimum sample | Happy-path: 6 шагов — Experiments → test/control → metric/methodology → calculate → review confidence → approve winner | overlapping cohorts, low sample or retroactive method → block; `experiment.winner_approved` | `PENDING-ID experiment.evaluate`; REQ-BIZ-012; blocked by attribution |
| US-KPI-001 | product owner; governance/report read; product metric | approved baseline/target/method | Happy-path: 5 шагов — KPI catalog → metric → baseline/target/window → evidence → review/sign | missing owner/source or technical SLO substituted → unmeasurable; `kpi.review_recorded` | `PENDING-ID kpi.review`; REQ-BIZ-013; decision required |
| US-V26-001 | analyst/advertiser; attribution read PENDING; campaign/store cohorts | master-sales adapter, methodology and controls | Happy-path: 6 шагов — Attribution → campaign/window → cohorts → baseline/fact → lift/confidence → versioned export | no control, sparse/deanonymizing data or changed method → block; `attribution.report_versioned` | `PENDING-ID attribution.lift_report`; REQ-V26-002, REQ-V26-010; blocked by master adapter |
| US-V26-002 | advertiser; self-service campaign permissions; own advertiser/retailer | approved membership, budget/credit/inventory rules | Happy-path: 8 шагов — Self-service → inventory → draft → creative → budget/conflicts → submit → final approval → publication status | limit/conflict, pre-approval access or cross-org → block; campaign approval audit | `self.campaign_create` extension; REQ-V26-003; blocked/owner scope |
| US-V26-003 | campaign manager; planned separation/audience permissions; placement/store/surface | master attributes and conflict policy | Happy-path: 7 шагов — placement → categories/attributes → targets → simulate → conflicts → override reason if allowed → save | competitor adjacency, missing attribute or cross-scope target → block; `placement.targeting_validated` | two pending IDs: competitive separation/audience targeting; REQ-V26-004, REQ-V26-005; blocked by master adapter |
| US-V26-004 | finance operator; finance exchange permission PENDING; retailer/period | approved external contract and reconciliation basis | Happy-path: 6 шагов — Finance exchange → period → preview → send idempotent batch → receive callback → status/result | duplicate batch, invalid callback or unsupported legal claim → reject; `finance.exchange_reconciled` | `PENDING-ID finance.exchange`; REQ-V26-006; planned/DEC-017 |
| US-V26-005 | platform architect; artifact approval, no UI permission; architecture scope | accepted ADR-018 and extension inputs | Artifact-path: 5 шагов — verify tenant baseline → define extension schemas → compatibility/security review → owner decision for unapproved extensions → publish versioned artifacts | parallel domain, unowned provider or incompatible contract → reject; decision audit record | REQ-V26-001 conformance + design-only REQ-V26-007/011; no UI journey; tenant accepted, extensions designed-not-implemented |
| US-V26-006 | store operator; field-ops permission PENDING; own store/devices | working device onboarding and mobile auth | Happy-path: 5 шагов — mobile login → store devices → device → photo confirmation → incident | cross-store, unsafe upload or broken onboarding → deny; `field.device_confirmed/incident_created` | `PENDING-ID field_ops.device_confirm`; REQ-V26-009; blocked by RM-TECH-210 |
| US-V26-007 | content operator; dynamic-content permission PENDING; channel/template | approved master-price contract and second-channel decision | Happy-path: 5 шагов — template → approved field → value/source preview → dynamic marker → manifest version | stale/missing price, static-hash contamination or no channel integration → block; `dynamic.binding_versioned` | `PENDING-ID content.dynamic_binding`; REQ-V26-008; blocked, ESL premise false |

### AP.1. Инварианты полноты story registry

- Ровно 41 уникальный `US-*`; дубликат или пропуск блокирует `APPROVED`.
- Для UI story обязательны permission/scope, preconditions/entry, `Happy-path: N`, negative
  path, audit, REQ и canonical journey/disposition. Для design-only story UI-smoke не
  выдумывается: обязательны artifact acceptance и owner decision.
- `PENDING-ID`, alias и список нескольких canonical функций являются временной disposition;
  до owner-approved mapping story не переносится в roadmap как готовая реализация.
- Текущий статус берётся из registry/Git/behavioral evidence. Текст требования не повышает
  `blocked/planned/partial` до `reachable/done`.
- Следующая машинная форма — `requirements-traceability.yaml`; эта таблица остаётся
  нормативным input, но не заменяет schema/gate и evidence.

## Дополнение AQ. Reconciliation ledger после независимых аудитов

Таблица устраняет неоднозначность «текст добавлен = дефект закрыт». `fixed_in_r414`
означает исправленную формулировку драфта; `open_artifact` требует отдельного файла/gate;
`owner_decision` нельзя закрыть агентом.

| Finding | Disposition r414 | Остаток |
|---|---|---|
| Story contracts были 4-колоночными | `fixed_in_r414` логически: AP содержит 41 actor/permission/scope/precondition/path/negative/audit/trace/status | machine YAML, selectors, smoke/evidence и operator walkthrough остаются `open_artifact` |
| REQ→roadmap/evidence не замыкается | `open_artifact` | создать schema-validated `requirements-traceability.yaml`; prose не считается картой |
| 53 из 101 REQ не имеют story/scenario coverage | `open_artifact` | 54 REQ не имеют AP-story; один из них покрывается только `SC-ARCH-001`, поэтому 53 остаются без story/scenario; оставшиеся technical/security/operations/governance REQ требуют зарегистрированные `SC-*`; одного SC-ARCH-001 недостаточно |
| 27 design journey IDs отсутствуют в каноне | `open_artifact` | заменить на canonical ID или owner-approved `PENDING-ID` mapping; не создавать дубликаты функций |
| Contract ID расходится | `owner_approved` | выбран `advertiser.contract_crud`; `advertiser.contract_pdf_upload` остаётся compatibility journey alias только до синхронного cutover journey/registry/smoke |
| Contract version/SHA overclaim | `fixed_in_r414` как факт/требование | текущий flow проверяет размер; immutable file versions и server-side SHA verification остаются planned requirement |
| Permissions 21/23/24 | `fixed_in_r414` | verified census 23 frontend / 30 backend / 24 stale docs; требуется один backend-derived SSOT |
| Device onboarding описан как рабочий | `fixed_in_r414` | `blocked` по `RM-TECH-210` до PostgreSQL runtime-role evidence |
| Tenant V26-001 связан с OD-016 | `fixed_in_r414` | ADR-018 принят; реализация проверяется через OD-003/RM-STAB-003 |
| Operations описан третьим приложением | `fixed_in_r414` | целевой раздел admin-web; третье приложение только по отдельному решению |
| Advertiser export заявлен доступным | `fixed_in_r414` | `self.report_view` blocked; admin CSV не доказывает advertiser export |
| ERD/data/API смешивали факт и цель | `fixed_in_r414` на уровне маркировки | generated ERD/OpenAPI/data dictionary и per-entry status остаются `open_artifact` |
| Master adapter назван существующим | `fixed_in_r414` | attribution/audience blocked prerequisite; master-data adapter отсутствует |
| `observability` якобы отсутствует в драфте/journeys | `rejected` | ID явно указан в §4 US-ADM-001 и `user-journeys.md:287`; это service-функция без обязательного admin UI |
| ESL/price checker назван уже интегрированным | `owner_approved` | посылка признана ложной для текущего baseline; dynamic creative blocked до реального второго канала, master contract и integration evidence |
| Line-level v2.6 count 34=21+13 | `fixed_in_r414` отзывом | полный classifier и obligation manifest остаются `open_artifact` |
| Два decision namespace DEC/OD | `open_artifact` | DEC должен стать alias/question в одном `roadmap.yaml:owner_decisions`, без второго исполняемого реестра |
| Драфт живёт в audit-каталоге | `owner_approved` | целевой путь `docs/product/requirements/tz-v2.6-draft.md`; физический cutover выполняется Claude после owner ACCEPT содержания и закрытия применимых gates с обновлением ссылок/sidecar/index |

### AQ.1. Решения владельца от 2026-08-27 — APPROVED

Эти решения утверждают содержание и следующий governance cutover. Они не повышают статус
ТЗ до `APPROVED` и не заменяют canonical записи `roadmap.yaml`; Claude переносит их туда
после независимого review r416 без создания второго исполняемого decision registry.

| # | Утверждённое решение | Affected scope | Следующее действие |
|---|---|---|---|
| 1 | r8/r25/r40 сохраняются в Git как история; rewrite/delete запрещены | Git provenance | никаких destructive history changes |
| 2 | Канонический feature/journey ID договора — `advertiser.contract_crud`; `advertiser.contract_pdf_upload` — временный compatibility alias | REQ-BIZ-017, US-ADV-003, journey/registry/smoke | атомарный alias cutover с сохранением test compatibility либо явной migration |
| 3 | Живой драфт переносится в `docs/product/requirements/tz-v2.6-draft.md`; после полного approval там же публикуется каноническая редакция | draft, sidecar, links, indexes | Claude выполняет rename/cutover после review r416; старый audit path получает immutable redirect/superseded record |
| 4 | Governance scope из AQ принимается в очередь: traceability schema/gate, journey↔registry↔smoke drift, единый decision registry, generated ERD/OpenAPI/permissions и documentation drift | roadmap governance | Claude готовит task breakdown и вносит его в `roadmap.yaml` отдельным owner-gated изменением |
| 5 | Master-data adapter признан отсутствующим prerequisite; текущая ESL/price-checker integration — ложная baseline-посылка. Attribution/audience/dynamic creative сохраняются, но имеют `blocked` до prerequisite evidence | REQ-V26-002/005/008, integration/channel scope | создать отдельные dependency tasks как минимум для price/SKU master adapter, sales-reference ingestion+methodology, audience source/privacy contract, dynamic binding/rendition safety и реальной интеграции второго канала; для каждой — owner/contract/security/behavioral acceptance; не начинать downstream implementation раньше них |

Историческая запись: после решений владельца r419 передавался Claude/Codex на повторное
review. Текущий объект — r425; статус документа остаётся `DRAFT` до пересборки traceability
и закрытия применимых approval gates.

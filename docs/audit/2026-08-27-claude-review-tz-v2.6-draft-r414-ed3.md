# Ревью драфта ТЗ v2.6 — редакция 3: закрытие остатков по ed2 и анализ r414

> ⚠️ **НЕ КАНОН** · тип: ревью, редакция 3 · предмет: драфт **r414** (sidecar `f53aa329…`, сходится)
> и вердикт Codex №3 на ed2 · SHA: `develop @ b21174f` + рабочее дерево · дата: 2026-08-27
> · автор: Claude Code · уникальных расхождений по r413: **26** · остатков по r414: **11**
> · решений владельца: **5** · Отменён: —
>
> Заменяет `…-r413-ed2.md` (проставлено `Отменён`). Все числа воспроизводимы (Приложение A).
> Ничего не реализовано и не изменено.

## 1. Вердикт Codex №3 — четыре остатка, все приняты

| Остаток | Ответ |
|---|---|
| 27 = 16, один дефект дважды | принято: **26** уникальных; пункт 27 удалён |
| «ни одна Happy-path не привязана к ID явно» — неверно | **принято, моя ошибка определения.** Я считал «явной» только привязку через заголовок блока или строку `**Journey:**`; ролевые таблицы §6 держат ID и Happy-path в одной строке. Корректный census: **9** функций с HP в той же строке, **20** — с HP где-то в объемлющем блоке, **8** не упомянуты; 17 строк HP, 2 блока Given |
| Приложение B не содержит 49 mapping'ов | принято: полная таблица 58 — Приложение B |
| §7 смешивает состояния документов | принято: колонка «состояние» добавлена — §5 |

## 2. r414 — что реально исправлено

Проверено текстом r414, не changelog'ом:

| Находка ed2 | r414 | Доказательство |
|---|---|---|
| permissions 21/23/24, фантом | **исправлено** | «24» — 0 упоминаний; US-ADM-002: 30 backend / 23 frontend / 24 stale; AP целится в 30 |
| `RM-TECH-210` отсутствовал | **исправлено** | §11 абзац-блокер; AP US-V26-006 precondition; AQ |
| V26-001 ↔ OD-016 | **исправлено** | AN: `ADR-018, OD-003, RM-STAB-003`, OD-016 явно отведён |
| Operations — третье приложение | **исправлено** | §11: целевой раздел `admin-web` |
| §3/§13 факт и цель смешаны | **исправлено** маркировкой | заголовки «Целевая… (`required`, не текущий факт)» |
| §26 API без маркеров, неверный префикс inventory | **исправлено** | 20 маркеров; `/api/inventory/` — 0 |
| J-V26-AUD-001 5≠6 | **исправлено** | расхождений шагов нет |
| REQ-BIZ-017 версии/SHA как факт; actor сужен | **исправлено** | US-ADV-003: факт — размер; версии/SHA — planned; actor — admin или manager |
| AM «34 = 21 + 13» | **исправлено** отзывом | «Предыдущий счёт отозван… totals UNVERIFIED» |
| stories 4-колоночные | **исправлено по существу** | AP: 41 × {actor; permission; scope; preconditions; entry; Happy-path; negative; audit; traceability; status} — все 10 полей §4. Permission-коды: 0 невалидных без метки PENDING; 15 stories с permission `PENDING`; traceability: 16 canonical, 21 `PENDING-ID`, 4 прозой (US-COM-001 «seven commerce.*», US-ADV-002 группа advertiser.*, US-V26-003, US-V26-005 design-only) |
| Экспорт рекламодателю | **исправлено** | AQ: `self.report_view` blocked |
| ESL «уже интегрирован» | **квалифицировано** | AQ: `owner_decision`, противоречит коду и ADR-019 |

Отдельно: **AQ** — честный трёхзначный ledger (`fixed_in_r414` / `open_artifact` /
`owner_decision`), пять решений владельца совпадают с моими.

## 3. r414 — остатки (11)

**Заявлено исправленным, но не исправлено:**
1. **REQ-V26-005 в §25 (строка 1069) по-прежнему: «атрибуты приходят через существующий
   master adapter».** §2.3 (строка 391) исправлен, атомарный каталог — нет. AQ помечает
   master-adapter `fixed_in_r414` — для каталога это неверно. Каталог §25 — определение
   записи, §2.3 — обзор; расходятся.
2. Доп. V не тронут: 27 несуществующих ID и 2 alias по-прежнему поданы как «канонические ID
   для трассировки», тогда как AP для тех же stories даёт `PENDING-ID`. Две таблицы одного
   документа противоречат друг другу (AQ признаёт `open_artifact`, но текст V не помечен).
3. `backup.restore` в AP использован как **permission**; это feature-ID registry, не код права
   (помечен PENDING — проходит формальную проверку, но категория неверна). V держит `dr.restore`.

**Открыто и признано (AQ `open_artifact`):**
4. Roadmap-связка: 6/43 задач, 10/16 OD, 0/3 гейтов; ни одного REQ→task.
5. DEC↔OD: 12 из 21 DEC без ссылки на OD/ADR.
6. AC-реестр: 326 строк, колонки status нет (AC-325 открыт).
7. AH отсутствует; порядок приложений AO→AE→AF→AG→AI→AD→AL→AJ→AK→AM→AN→AP→AQ (AC-324 открыт).

**Открыто и НЕ признано (в AQ отсутствует):**
8. **51 из 90 REQ без story-связки при одном `SC-*`-сценарии** — в ledger не упомянуто.
9. `observability` — единственный registry-ID, не упомянутый нигде (57/58).

**Governance:**
10. Драфт не зарегистрирован в `docs/audit/README.md`; вердикт Codex №3 — тоже.
11. Правило README п.2 («не редактировать после публикации») применено Codex к моей строке
    `Изменён`, но драфт правится на месте r413→r414 в том же каталоге. Это не упрёк, а
    подтверждение решения владельца №3: документу требований не место в `docs/audit/`.

**Итог по r414:** честная редакция — 12 из 26 расхождений закрыты текстом, 8 признаны
открытыми, 2 отданы владельцу. Не готов к `APPROVED` по тем же причинам, что r413: нет
машинной traceability, и два внутренних противоречия (§25 vs §2.3; V vs AP) появились
именно из-за частичной правки.

## 4. Полнота user stories — окончательная формулировка

**Драфт r414:** AP делает 41 story полными по шаблону §4 на уровне текста. Не хватает
машинной формы (`requirements-traceability.yaml`), selectors/smoke/evidence и walkthrough —
AP это заявляет сам. Для 15 stories permission ещё не существует в backend (`PENDING`).

**Канон `user-journeys.md` (спецификация journeys, не реестр stories):** 45 UI-функций;
Happy-path в той же строке — 9; в объемлющем блоке — 20; не упомянуты — 8; всего строк
HP — 17, блоков Given — 2. Done Gate п.9 выполняется явно для 9 функций из 45.

## 5. Недостающие документы — с состоянием

| # | Документ | Состояние | Доказательство | Когда |
|---|---|---|---|---|
| 1 | ERD + data dictionary | **устарел** | `erd-v2-5.md` Phase 0; нет license/retailer_id/contracts/applications/commerce | до пилота, генерировать |
| 2 | API-каталог / OpenAPI snapshot | **устарел** | `api-groups-v1.md` Phase 0; нет licenses/commerce/device-codes/briefs | до пилота, генерировать |
| 3 | Каталог событий | **устарел** | 5 строк vs 19 типов в коде | до пилота, генерировать |
| 4 | Матрица ролей/прав + RLS-политики | **отсутствует** | только seed и Доп. B драфта; 30/5/37 | до пилота, генерировать |
| 5 | Руководства пользователя по ролям | **отсутствует** | 0 файлов | до walkthrough |
| 6 | Процедура онбординга устройств | **отсутствует** | 0 файлов; функция сломана | до device pilot |
| 7 | Протокол приёмки / owner sign-off | **отсутствует** | гейты без протокола | до Gate S |
| 8 | Traceability matrix | **отсутствует** | AC-01; AP — prose input | до APPROVED ТЗ |
| 9 | Глоссарий | **отсутствует** (есть в драфте §19) | 0 файлов в каноне | до APPROVED ТЗ |
| 10 | Threat model / security baseline | **отсутствует** (есть Доп. S) | DEC-016 | до production |
| 11 | Политика PII/retention (152-ФЗ) | **решение владельца** | OD-009 | до production |
| 12 | SLO/SLA, бюджеты производительности | **решение владельца** | OD-011 → `RM-TECH-205` | до pilot scale-up |
| 13 | Incident/support process | **отсутствует** (есть Доп. Z) | runbook'и без процесса | до пилота с людьми |
| 14 | Pilot plan с exit criteria | **запланирован** | `RM-PILOT-001`, DEC-010 | по очереди |
| 15 | Интеграционные контракты master-data / finance / SIEM | **отсутствуют** | ни одного | до v2.6 P1 |
| 16 | Бизнес-процессы по контурам | **устарел/тонкий** | `business-map-by-role.md` 13 строк | до Gate U |
| 17 | Design system / a11y | **частично** | style-tokens есть, a11y нет | Gate U |

## 6. Решения владельца — 5 (совпадают с AQ.1)

1. r8/r25/r40 сохранить как историю. 2. Канонический ID договорного journey.
3. Место драфта и будущего ТЗ. 4. Какие governance-артефакты становятся задачами.
5. Master-data — dependency gap; ESL — ложная посылка; зафиксировать в реестре решений.

## Приложение A. Воспроизводимые команды

```bash
grep -c 'Happy-path' docs/product/user-journeys.md          # 17
grep -c '\*\*Given\*\*' docs/product/user-journeys.md       # 2
python3 - <<'PY'   # 9 / 20 / 8
import re,yaml
L=open('docs/product/user-journeys.md',encoding='utf-8').read().split('\n')
reg=sorted(f['id'] for f in yaml.safe_load(open('docs/product/feature-registry.yaml'))['features'])
heads=[i for i,l in enumerate(L) if re.match(r'^#{2,4} ',l)]
def blk(i):
    s=max([h for h in heads if h<=i] or [0]); e=min([h for h in heads if h>s] or [len(L)]); return '\n'.join(L[s:e])
same=inblk=none=0
for f in reg:
    hits=[i for i,l in enumerate(L) if re.search(r'(?<![\w.])'+re.escape(f)+r'(?![\w.])',l)]
    if not hits: none+=1; continue
    if any('Happy-path' in L[j] for j in hits): same+=1
    if re.search(r'Happy-path:\s*\d+',blk(hits[0])): inblk+=1
print(same,inblk,none)
PY
```

## Приложение B. ID → строка → блок → Happy-path (58 функций)

| ID | Строка | Блок | HP в строке | HP в блоке |
|---|---|---|---|---|
| adsettings.configure | 243 | 6.4 Администратор системы | — | да |
| adsettings.test | 242 | 6.4 Администратор системы | **да** | да |
| advertiser.application_review | 269 | 6.7 Публичный лид | — | — |
| advertiser.apply | 268 | 6.7 Публичный лид | — | — |
| advertiser.brand_crud | — | не упомянут | — | — |
| advertiser.contact_crud | — | не упомянут | — | — |
| advertiser.contract_crud | — | не упомянут | — | — |
| advertiser.create_org | 128 | 5. Продуктовые решения | — | — |
| advertiser.invite | 270 | 6.7 Публичный лид | — | — |
| advertiser.legal_requisites | — | не упомянут | — | — |
| advertiser.view | 209 | 6.1 Менеджер кампаний | — | да |
| audit.view | 254 | 6.5 Администратор безопасности | **да** | да |
| backup.restore | 286 | 7. Инфраструктурные потоки | — | — |
| campaign.activate | 117 | 4. Жизненный цикл кампании | — | — |
| campaign.approve | 115 | 4. Жизненный цикл кампании | — | — |
| campaign.complete | — | не упомянут | — | — |
| campaign.create | 27 | 1. Соглашения | — | да |
| campaign.edit | 202 | 6.1 Менеджер кампаний | — | да |
| campaign.pause | 119 | 4. Жизненный цикл кампании | — | — |
| campaign.reject | 116 | 4. Жизненный цикл кампании | — | — |
| campaign.submit | 114 | 4. Жизненный цикл кампании | **да** | — |
| commerce.booking | 876 | Feature IDs | — | — |
| commerce.offer_generate | 875 | Feature IDs | — | — |
| commerce.order_close | 762 | Decision Matrix | — | — |
| commerce.order_create | 873 | Feature IDs | — | — |
| commerce.payment_status | 877 | Feature IDs | — | — |
| commerce.price_list_manage | 750 | Decision Matrix | — | — |
| commerce.tariff_manage | 750 | Decision Matrix | — | — |
| creative.moderate_approve | 232 | 6.3 Модератор | — | — |
| creative.moderate_reject | 233 | 6.3 Модератор | — | — |
| creative.upload | 203 | 6.1 Менеджер кампаний | **да** | да |
| device.health_view | 263 | 6.6 Оператор эксплуатации | **да** | да |
| device.heartbeat | — | не упомянут | — | — |
| device.onboard | 286 | 7. Инфраструктурные потоки | — | — |
| emergency.activate | 119 | 4. Жизненный цикл кампании | — | — |
| emergency.deactivate | 256 | 6.5 Администратор безопасности | — | да |
| inventory.rule_create | 208 | 6.1 Менеджер кампаний | **да** | да |
| inventory.simulate | 207 | 6.1 Менеджер кампаний | — | да |
| license.enforce | 626 | Feature IDs | — | — |
| license.report | 628 | Feature IDs | — | — |
| license.seat_release | 627 | Feature IDs | — | — |
| license.upload | 630 | Feature IDs | — | — |
| license.view | 629 | Feature IDs | — | — |
| manifest.deliver | 286 | 7. Инфраструктурные потоки | — | — |
| observability | 287 | 7. Инфраструктурные потоки | — | — |
| playlist.build | 286 | 7. Инфраструктурные потоки | — | — |
| pop.ingest | 286 | 7. Инфраструктурные потоки | — | — |
| self.apply_or_brief | 278 | 6.8 Рекламодатель | — | да |
| self.campaign_create | 279 | 6.8 Рекламодатель | — | да |
| self.campaign_view | 276 | 6.8 Рекламодатель | **да** | да |
| self.login | 275 | 6.8 Рекламодатель | — | да |
| self.report_view | 277 | 6.8 Рекламодатель | — | да |
| system.theme_switch | — | не упомянут | — | — |
| user.assign_roles | 239 | 6.4 Администратор системы | — | да |
| user.create_advertiser | 238 | 6.4 Администратор системы | — | да |
| user.deactivate | 241 | 6.4 Администратор системы | **да** | да |
| user.reset_password | 240 | 6.4 Администратор системы | **да** | да |
| user.split_internal_advertiser | — | не упомянут | — | — |

Итого: HP в строке — 9; HP в блоке — 20; не упомянуты — 8.

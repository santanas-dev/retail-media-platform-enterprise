# Поправка к ревью r413 и проверка вердикта Codex

> ⚠️ **НЕ КАНОН** · тип: amendment + проверка вердикта · предмет: `2026-08-27-codex-verdict-claude-tz-r413.md`
> и моё ревью `2026-08-27-claude-review-tz-v2.6-draft-r413.md` · SHA: `develop @ b21174f` + рабочее дерево
> · дата: 2026-08-27 · автор: Claude Code · открытых вопросов: 4 (те же, что у Codex) · Отменён: `2026-08-27-claude-review-tz-v2.6-draft-r413-ed2.md`
>
> Ничего не реализовано и не изменено, кроме этой записи, указателя в шапке моего ревью и строк в README.

## 1. Вердикт Codex — проверен по пунктам

| Пункт Codex | Мой вердикт |
|---|---|
| Подтверждено 1–7 (нет карты REQ→task; alias договора; дефект онбординга не в драфте; REQ-BIZ-017 заявляет версии/SHA; факт/требование смешаны; ошибки подсчётов; `git add -A`) | согласен, всё воспроизводимо |
| **Перепись permissions неверна** | **прав. Отзываю.** См. §2 |
| «Претензия о регистрации в README устарела: ревью зарегистрировано» | **misread**: мой пункт 24 — о **драфте**, не о ревью. `grep design-draft docs/audit/README.md` → пусто. Драфт по-прежнему не зарегистрирован; вердикт Codex — тоже |
| Рекомендация сохранять r8/r25/r40 как историю | согласен; удаление было бы переписыванием истории |

## 2. Перепись permissions — отзыв и корректный census

Мой счёт был грепом по суффиксам `.read|.manage|.approve|.moderate` и по шаблону `code: {`.
Он пропустил трёхчастные коды (`advertisers.contacts.*`), суффикс `.review` и все `commerce.*`.
Это тот же класс ошибки, что уже стоил мне красного CI в этой сессии (импорт `jsonschema`):
грепать вместо разбора структуры.

Воспроизводимый метод: `ast`-разбор `SEED_PERM_IDS` в `apps/control-api/seed.py`; чтение
`REGISTRY` в `permissionDescriptions.ts` целиком; `SELECT code FROM permissions` на
одноразовой БД после миграций до `036` и seed.

| Множество | Размер | Состав |
|---|---|---|
| backend (seed = живая БД) | **30** | seed и `permissions` совпадают полностью |
| frontend `REGISTRY` | **23** | |
| документы (journeys §6.0b, драфт US-ADM-002) | **24** | не совпадает ни с чем |
| frontend − backend (фантомы) | **0** | `advertiser_applications.review` есть в backend — **моё утверждение о фантоме ложно** |
| backend − frontend (не показаны в каталоге) | **7** | `campaign_briefs.manage`, `commerce.order_manage`, `commerce.order_read`, `commerce.tariff_manage`, `commerce.tariff_read`, `devices.manage`, `license.read` |

Вывод по существу не меняется, а усиливается: каталог прав (`user.assign_roles`, D2) **не
показывает 7 из 30** прав — весь коммерческий контур и лицензирование невидимы; число «24» в
двух документах не соответствует ни одному источнику. Пункты 11 и 15 ревью читать в этой редакции.

## 3. Полноценна ли user story — проверка по шаблону

### 3.1 Драфт r413
§4 объявляет обязательными 10 полей: actor, permission code, scope, preconditions, entry,
`Happy-path: N`, видимые действия, результат, negative path, audit event. Доп. E задаёт
YAML-минимум из 13 полей.

Факт: все **41** story — таблицы из 4 колонок (ID / роль / story / результат). Ни одна
story нигде в драфте не имеет `permission_code`, `scope`, `preconditions`, `negative_paths`,
`audit event`. Happy-path задан только у journeys (Доп. U, §35, §2.3), не у stories.
Драфт это признаёт сам (AC-19, AC-220). **По собственному шаблону драфта полноценных
stories — 0 из 41.**

### 3.2 Канон `user-journeys.md` — для 58 существующих функций
| Показатель | Число |
|---|---|
| функции, которые journeys не упоминают вовсе | **8**: `advertiser.brand_crud`, `advertiser.contact_crud`, `advertiser.contract_crud`, `advertiser.legal_requisites`, `campaign.complete`, `device.heartbeat`, `system.theme_switch`, `user.split_internal_advertiser` |
| упомянуты, но без `Happy-path` | **29** — в т.ч. `campaign.approve/reject`, `creative.moderate_*`, `emergency.activate`, все `commerce.*` (7), все `license.*` (5) |
| с `Happy-path` | 21 |
| с Given/When/Then | 18 |

AGENTS.md Done Gate п.9 требует `Happy-path: N шагов` у каждого UI journey. Для 4 из 8
неупомянутых функций (`advertiser.*`) journey есть под именем контура ADVERTISER-UX-001B*,
но без dot-case ID — это и породило alias `contract_pdf_upload`.

**Ответ на вопрос владельца: полноценной user story нет ни у одной функции ни в драфте,
ни в каноне.** В драфте нет полей; в каноне нет Happy-path у половины и нет ID у восьми.

## 4. Проблемы с будущей функциональностью — посылки v2.6 против кода

| Домен v2.6 | Посылка исходника | Факт в коде | Проблема |
|---|---|---|---|
| §2.1 Attribution, §3.2 Audience | «через **существующий** адаптерный слой master-данных» | адаптер master-данных/продаж отсутствует; единственный adapter — `apps/adapter-workers/mock` (канальный mock) | **Оба P1/P2-домена стоят на несуществующей инфраструктуре**; REQ-V26-005 драфта повторяет ложную посылку («из существующего master-adapter») |
| §4.2 Dynamic creative | ESL/price checker «**уже интегрированный** с master-системой цен» | seed содержит один канал — KSO (`chromium`, `landscape`); ESL/LED есть только как коды в channel-модели; ADR-019 откладывает мультиканал | посылка ложна; REQ-V26-008 наследует её |
| §1.1 Tenant model | «решить до старта» | ADR-018 **Accepted 2026-07-17**, вариант B; но реализация оспорена (`RM-STAB-003`, OD-003, operator-эксперимент: retailer scope выводится из advertiser membership) | драфт называет решение partial и цитирует не тот OD; реальный риск — не выбор модели, а её текущая инверсия |
| §2.2 Self-service | «текущий кабинет read-only» | `self.apply_or_brief` reachable — write-путь (`campaign_briefs.manage`) | посылка устарела; OD-005/OD-013 открыты — scope self-service за владельцем |
| §3.3 Finance | обратный статус оплаты из внешней системы | `commerce.payment_status` reachable — ручное обновление в UI | частичная база есть; V26-006 = внешний контракт поверх неё, не новый домен |
| §4.3 Mobile field ops | «через существующий RBAC» | RBAC есть; но self-onboarding устройств не работает (`RM-TECH-210`) | предусловие — 210 |
| §3.1 Competitive separation | новое поле на Brand | поля нет, conflict-engine есть | проблем нет — аддитивно |

Итого: **два из трёх домена приоритета 1–2 (attribution, audience targeting) и один
приоритета 3 (dynamic creative) опираются на инфраструктуру, которой нет.** Это не дефект
драфта — это дефект исходного ТЗ v2.6, и по ADR-020 его надо назвать расхождением
требования с фактом, а не молча спланировать «адаптер» как подзадачу.

## 5. Что остаётся

Четыре решения владельца — те же, что у Codex, согласен с формулировками. Добавляю пятое:
**принять ли посылку «существующий master-adapter» как ошибку ТЗ v2.6** с записью в
decision register (DEC/OD) — иначе оценка объёма attribution/audience будет занижена.

Обязательные действия Codex из вердикта (машинная карта, disposition fact/requirement/
planned/blocked, каноническое имя договора) поддерживаю. Пункт 1 (новая редакция ревью
с исправленным census) — выполнен этой записью.

# Пользовательские сценарии (User Journeys) — источник истины для UI

**Версия:** 1.0 · 2026-07-18 · владелец: продукт
**Каноническое место в репозитории:** `docs/product/user-journeys.md`

---

## 0. Зачем этот документ

Между ТЗ («что система умеет») и кодом («как реализовано») был пропущен слой:
**конкретные пути, которыми роль достигает цели через интерфейс.** Его отсутствие
привело к тому, что бэкенд «готов», а кнопок нет и потоки недостижимы.

Этот документ — **единственный источник истины** для того, что обязано быть
**проходимо в UI**. Он напрямую питает `docs/product/feature-registry.yaml` и механизм
UI-TRUTH: каждый журней получает `id`, каждый `id` обязан иметь зелёный UI-smoke,
статус бизнес-функции в roadmap выводится из журнеев её домена.

**Железное правило:** бизнес-функция может быть «Готово» только если все её журнеи
проходимы кликами (без ручного ввода URL) и покрыты зелёными UI-smoke.

---

## 1. Соглашения (обязательны — от них зависит автоматика)

- **ID журнея:** `<домен>.<действие>` в snake/dot-case, стабилен навсегда
  (напр. `campaign.create`). Это ключ, общий для: этого документа,
  `feature-registry.yaml`, имени теста `test_uismoke__<домен>__<действие>`.
- **Стабильные селекторы:** каждый элемент, участвующий в журнее, получает
  `data-testid="<домен>-<действие>-<элемент>"` (напр. `data-testid="campaign-create-submit"`).
  UI-smoke ходит по `data-testid` / ARIA-ролям / видимым лейблам — не по CSS-классам.
- **Приоритет / веха:** `P0` = нужно к пилоту · `P1` = к стабильному релизу ·
  `P2` = позже (после пилота).
- **Статус «сейчас» (факт на 2026-07-18):** ✅ проходимо · ⚠️ частично/проверить ·
  ❌ дыра (бэкенд есть, UI недостижим) · — не UI (сервис).
- **Формат приёмки:** каждый P0-журней имеет Given/When/Then, который дословно
  ложится в UI-smoke.
- **Точка входа всегда логин.** `page.goto()` разрешён только на `/login`; дальше —
  только клики. Прямой переход на целевой маршрут = невалидный тест.
- **Happy-path (шаблон):** Happy-path: 4 шага — 1) видимое действие → видимый
  next-step; 2) видимое действие → видимый next-step; 3) проверка результата;
  4) сохранение/завершение. Каждый шаг должен быть понятен пользователю без
  внутренней инструкции.

---

## 2. Каталог ролей

### Внутренние (admin-web — сотрудники сети)
| Роль | Код | Назначение |
|---|---|---|
| Администратор системы | `system_admin` | пользователи, роли, настройки AD, полный доступ |
| Администратор безопасности | `security_admin` | аудит, аварийный режим, безопасность |
| Менеджер кампаний | `campaign_manager` | кампании, размещения, инвентарь, ведение рекламодателей |
| Модератор креативов | `moderator` | проверка/модерация роликов |
| Согласующий | `approver` | согласование кампаний |
| Оператор эксплуатации | `ops_operator` | здоровье устройств, экстренная остановка |

### Внешние (advertiser-web — кабинет рекламодателя)
| Роль | Код | Назначение |
|---|---|---|
| Рекламодатель | `advertiser` | свои кампании, креативы, отчёты |
| Потенциальный рекламодатель | `public_lead` | подать заявку на подключение (без логина) |

> Одна учётка может нести несколько ролей. Break-glass admin несёт все внутренние.
> Роли и права — продуктовое решение (см. §3), а не только следствие seed.

---

## 3. Матрица ролей и прав (продуктовое решение — Q2 РЕШЁН)

Право = разрешён ли роли соответствующий журней. `✔` разрешено · пусто — нет.

| Домен / действие | system_admin | security_admin | campaign_manager | moderator | approver | ops_operator | advertiser |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| Кампании: смотреть | ✔ | ✔ | ✔ | ✔ | ✔ | | свои |
| Кампании: создать/редактировать | ✔ | | ✔ | | | | P2¹ |
| Кампании: отправить на согласование | ✔ | | ✔ | | | | P2¹ |
| Кампании: согласовать/отклонить | ✔ | | | | ✔ | | |
| Креативы: загрузить | ✔ | | ✔ | | | | P2¹ |
| Креативы: модерировать | ✔ | | | ✔ | | | |
| Инвентарь: смотреть/симуляция | ✔ | | ✔ | | | | |
| Инвентарь: править правила | ✔ | | ✔ | | | | |
| Рекламодатели: смотреть | ✔ | | ✔ | | | | |
| Рекламодатели: создать организацию | ✔ | | ✔ | | | | |
| Заявки: рассмотреть/одобрить | ✔ | | ✔ | | | | |
| Пользователи: создать/блокировать | ✔ | | | | | | |
| Пользователи: назначить роли | ✔ | | | | | | |
| Настройки AD: смотреть/тест | ✔ | ✔ | | | | | |
| Настройки AD: сохранить | ✔ | | | | | | |
| Аудит: смотреть | ✔ | ✔ | | | | | |
| Аварийный режим: вкл/выкл | ✔ | ✔ | | | | ✔ | |
| Устройства: смотреть здоровье | ✔ | | | | | ✔ | |
| Свой кабинет: кампании/отчёты | | | | | | | ✔ |

¹ P2 — рекламодатель сам заводит кампании только в фазе self-service (после пилота).
На пилоте кампании рекламодателя ведёт `campaign_manager` (managed-модель).

---

## 4. Жизненный цикл кампании (продуктовое решение — Q3 РЕШЁН)

Состояния и переходы. Каждый переход — это журней с ролью и точкой в UI.

```
draft ──submit──▶ pending_approval ──approve──▶ approved ──activate──▶ active ──end──▶ completed
  ▲                     │                                                  │
  └────reject───────────┘ (→ rejected, назад в draft после правок)        └──pause/emergency──▶ paused
```

| Переход | Кто | Из UI | Триггер |
|---|---|---|---|
| — → `draft` | campaign_manager | Кампании → Создать | `campaign.create` |
| `draft` → `pending_approval` | campaign_manager | карточка → Отправить на согласование | `campaign.submit` |
| `pending_approval` → `approved` | approver | Согласование → Одобрить | `campaign.approve` |
| `pending_approval` → `rejected` | approver | Согласование → Отклонить (причина) | `campaign.reject` |
| `approved` → `active` | система (по началу рейса) / campaign_manager вручную | — / карточка → Запустить | `campaign.activate` |
| `active` → `completed` | система (по концу рейса) | — | сервис |
| `active` → `paused` | security_admin / ops_operator | Аварийный режим / карточка → Пауза | `emergency.activate` / `campaign.pause` |

Правило видимости кнопок: действие показывается только если (а) у роли есть право
(§3) И (б) кампания в допустимом для перехода состоянии.

---

## 5. Продуктовые решения по спорным дырам

- **Q1 — `advertiser.create_org` (РЕШЁН: нужен прямой экран).** Модель «и managed, и
  self-service» (решение владельца ранее) требует ДВУХ путей появления организации:
  (1) прямой admin-экран «Создать рекламодателя» — для managed/enterprise-сделок,
  заведённых оффлайн менеджером/продажами; (2) автосоздание при одобрении публичной
  заявки — для self-service лидов. Значит G3 — **реальная дыра**: прямой экран нужен.
  Право — у `system_admin` и `campaign_manager`.
- **Q4 — self-service рекламодателя (РЕШЁН: на пилоте — только чтение + заявка).** К
  пилоту `advertiser` видит свои кампании и отчёты (PoP) и может подать заявку/бриф;
  полное самостоятельное заведение кампаний — фаза self-service (P2). На пилоте
  кампании рекламодателя ведёт `campaign_manager`.

---

## 5.1. Журнал принятых решений (ратификация §25 ТЗ) — 2026-07-18

**Бизнес-решения (приняты владельцем продукта):**
- **Overbooking (§22.4): ЗАПРЕЩЁН.** Публикация кампании при нехватке инвентаря
  блокируется; продажа сверх доступного не допускается.
- **HTML5-контент (§22.5): ЗАПРЕЩЁН на старте.** Только изображения/видео. HTML5 —
  не ранее отдельного решения, и только через sandbox + согласование ИБ.
- **Основание размещения (§22.12): ОБЯЗАТЕЛЬНОЕ поле кампании.** Значения:
  коммерческое / внутреннее / компенсационное / тестовое. Платный инвентарь,
  внутренняя реклама сети и компенсации не смешиваются без явной маркировки.
  → влияет на журней `campaign.create` (см. §6.1).
- **SLA / хранение / недопоказ (§22.2/22.11/22.3): приняты дефолты ТЗ.**
  - SLA: портал ≥99,5%, Device Gateway ≥99,9%, доставка manifest ≤5 мин,
    emergency ≤1 мин, потеря PoP ≤0,1%.
  - Хранение: PoP 12–18 мес, архив PoP/отчёты 3–5 лет, аудит ≥3 года,
    тех-логи 90–180 дн, креативы 1–3 года. **Юр. подпись по хранению — позже.**
  - Недопоказ: факт < 95% плана. (Модуль недопоказов/компенсаций — веха P2.)

**Подтверждено фактом кода (§25 — done):** стек; JWT не в URL; подписанный manifest
(K2); RLS + изоляция рекламодателей; бэкапы + тест восстановления; пилотный план
КСО → 10 → 100 → 500 → сеть; правила работы Hermes (в AGENTS.md).

**Отложено до своей вехи:** детальные решения мультиканальности §23/§24 — перечень
каналов первой очереди, владельцы, ESL/price-checker (сверка с master-ценами),
рендеры/предпросмотр по каналам, mock-адаптеры.

**§24 — РЕШЕНО ВЛАДЕЛЬЦЕМ (2026-07-18): ПРАГМАТИКА.** EDGE-001/002/003/004 (onboarding,
manifest+подпись, PoP, heartbeat) уже сделаны и зелёные — их НЕ рефакторим. Строим
реальный КСО-плеер (M2) поверх готовых контрактов, за ТОНКИМ адаптерным швом; полный
Channel Orchestrator + адаптерный слой + mock-адаптеры добавляем ТОЛЬКО когда появится
2-й реальный канал. Де-риск: любую абстракцию валидировать на КСО как единственном
реальном канале; никаких хуков под несуществующие каналы. Универсальные контракты
(manifest с adapter_payload, нормализованная proof-модель) уже частично есть (EDGE-002) —
их держим channel-agnostic, но оркестрацию не строим наперёд.

<details><summary>Отклонённая альтернатива (каркас каналов сначала, буквально по ТЗ §24/§25)</summary>

**Не выбрано: каркас каналов сначала — буквально по ТЗ §24/§25.**
Строим channel-agnostic ядро + Channel Orchestrator + адаптерный слой + mock-адаптеры;
КСО — как ПЕРВЫЙ адаптер, а не одноразовая вертикаль. Следствия:
- edge/плеер пере-секвенируется по плану §25 (приоритеты 1–6): (1) арх-документы →
  (2) core tables (channels, device_types, capability_profiles, physical_devices,
  display_surfaces) → (3) Channel Orchestrator skeleton + интерфейс адаптера →
  (4) универсальный manifest v1 → (5) proof event schema → (6) KSO Adapter как первый
  канал (полный цикл manifest → показ → PoP → отчёт);
- существующие EDGE-001/002 (КСО-вертикаль) РЕФАКТОРЯТСЯ в модель «ядро + KSO-адаптер»
  — это принятая цена решения;
- **де-риск (обязателен):** каждую абстракцию проверять на ЕДИНСТВЕННОМ реальном
  канале (КСО); mock-адаптер — только для тестов; НЕ добавлять хуки под каналы,
  которых ещё нет в плане; тайм-боксировать каждый из шагов 1–6.
</details>

---

## 6. Журнеи по ролям

### 6.1 Менеджер кампаний (campaign_manager) — ядро

| id | Цель | Путь (клики) | Приоритет | Сейчас |
|---|---|---|---|---|
| `campaign.create` | Завести кампанию | Логин → Кампании → **Создать кампанию** → форма → **Сохранить** | P0 | ❌ G1 |
| `campaign.edit` | Настроить рейсы/размещения | Кампании → карточка → добавить рейс/размещение | P0 | ✅ |
| `creative.upload` | Загрузить ролик | карточка → вкладка Креативы → **Выбрать файл** → авто-метаданные → **Загрузить** → Готов. Happy-path: 5 шагов — 1) Креативы → 2) Выбрать файл → 3) метаданные авто-заполнены → 4) Загрузить → 5) статус Готов + reload persistence | P0 | ✅ |
| `campaign.submit` | Отправить на согласование | Overview → checklist → missing steps → flight → placement → creative ready → **Отправить**. Happy-path: 6 шагов — 1) Обзор → checklist missing; 2) рейс через checklist-action; 3) размещение через checklist-action; 4) креатив с файлом через checklist-action; 5) все ✅ → можно отправить; 6) submit → pending_approval | P0 | ⚠️ |
| `campaign.activate` | Запустить одобренную кампанию | карточка (approved) → **Запустить** | P1 | ⚠️ |
| `campaign.pause` | Приостановить активную | карточка (active) → **Пауза** | P1 | ⚠️ |
| `inventory.simulate` | Прогноз показов | Инвентарь → параметры → **Симуляция** | P1 | ⚠️ |
| `inventory.rule_create` | Создать правило инвентаря | Инвентарь → вкладка «Правила» → **+ Создать** → max_sov/35%/priority 17/глобально/активно/будущие даты → Создать → success + строка. Happy-path: 7 шагов — 1) Логин (break_glass_admin) → 2) Инвентарь → 3) вкладка Правила → 4) + Создать → 5) заполнить (max_sov, 35%, priority 17, global, active, future dates) → 6) Создать → 7) строка с типом/областью/приоритетом/значением/активностью/периодом + reload persistence | P1 | ✅ |
| `advertiser.view` | Смотреть карточку рекламодателя | Рекламодатели → организация | P1 | ✅ |
| `advertiser.create_org` | Создать организацию (managed) | Рекламодатели → **Создать рекламодателя** → реквизиты | P0 | ❌ G3 |

**Приёмка P0 `campaign.create`:**
> **Given** пользователь с ролью `campaign_manager` залогинен через форму
> **When** он кликает «Кампании» → «Создать кампанию», заполняет обязательные поля —
> **в т.ч. «Основание размещения» (коммерческое/внутреннее/компенсационное/тестовое)** —
> и жмёт «Сохранить»
> **Then** появляется кампания в статусе `draft` с указанным основанием размещения,
> видимая в списке; тест дошёл до кнопки ТОЛЬКО кликами.
>
> Примечание: overbooking запрещён — при нехватке инвентаря публикация блокируется
> (проверяется на переходе `campaign.submit`/publish, не на create).

### 6.2 Согласующий (approver)
| id | Цель | Путь | Приоритет | Сейчас |
|---|---|---|---|---|
| `campaign.approve` | Одобрить кампанию | Логин → Согласование → карточка → **Одобрить** | P0 | ✅ |
| `campaign.reject` | Отклонить с причиной | Согласование → карточка → **Отклонить** → причина | P0 | ✅ |

### 6.3 Модератор (moderator)
| id | Цель | Путь | Приоритет | Сейчас |
|---|---|---|---|---|
| `creative.moderate_approve` | Пропустить креатив | Логин → Модерация → элемент → **Одобрить** | P0 | ✅ |
| `creative.moderate_reject` | Отклонить креатив с причиной | Модерация → элемент → **Отклонить** → причина | P0 | ✅ |

### 6.4 Администратор системы (system_admin)
| id | Цель | Путь | Приоритет | Сейчас |
|---|---|---|---|---|
| `user.create_advertiser` | Завести локального рекламодателя | Логин → Пользователи → **Создать** → данные+организация | P0 | ✅ |
| `user.assign_roles` | Назначить роли/права | Пользователи → пользователь → **Роли** → выбрать → сохранить | P0 | ❌ G2 |
| `user.reset_password` | Сбросить пароль | Пользователи → пользователь → **Сбросить пароль** → OTP. Happy-path: 5 шагов — 1) Логин → 2) Пользователи → 3) найти пользователя (create throwaway или существующий) → 4) Сбросить пароль → подтвердить → 5) OTP (16 символов) в network response, без [object Object]. Seed-учётные данные не мутируются. | P1 | ✅ |
| `user.deactivate` | Заблокировать | Пользователи → пользователь → **Деактивировать** → подтверждение → блок. Happy-path: 7 шагов — 1) Логин (break_glass_admin) → 2) Пользователи → 3) создать throwaway (sd-{uuid}) → 4) найти строку → 5) Деактивировать → подтвердить → 6) статус «Неактивен» + success → 7) залогиниться деактивированным → блокирован (stay on login, error visible). Reload persistence подтверждена. Seed-учётные данные не мутируются. OTP извлекается из DOM. | P1 | ✅ |
| `adsettings.test` | Проверить подключение AD | Настройки AD → **Проверить подключение** → результат (status + message, без секретов). Happy-path: 4 шага — 1) Логин (break_glass_admin) → 2) Настройки AD в меню → 3) Проверить подключение → 4) контролируемый результат (not_configured в DEV, ok/success в PROD), без [object Object], без bind_password. | P1 | ✅ |
| `adsettings.configure` | Сохранить настройки AD | Настройки AD → поля → **Сохранить** | P1 | ✅ |

**Приёмка P0 `user.assign_roles`:**
> **Given** `system_admin` залогинен; существует пользователь
> **When** он открывает пользователя, экран «Роли», отмечает роль и сохраняет
> **Then** у пользователя изменился набор ролей (виден после перезагрузки страницы),
> и это отражено в аудите.

### 6.5 Администратор безопасности (security_admin)
| id | Цель | Путь | Приоритет | Сейчас |
|---|---|---|---|---|
| `audit.view` | Смотреть журнал событий | Логин → Журнал аудита → таблица с событиями → emergency.activated/deactivated видны → поля: действие, исполнитель, ресурс, время. Happy-path: 5 шагов — 1) Логин (break_glass_admin) → 2) Журнал аудита в боковом меню → 3) таблица audit-table → 4) видна строка с emergency действием → 5) поля actor, resource, created-at заполнены. Persistence через re-navigation подтверждена. | P1 | ✅ |
| `emergency.activate` | Экстренно остановить показ | Логин → Аварийный режим → **Активировать** → подтвердить | P0 | ⚠️² |
| `emergency.deactivate` | Снять аварийный режим | Аварийный режим → **Деактивировать** | P0 | ⚠️² |

² Активация в UI есть; фактическое исполнение на устройстве — после плеера (связано с K1).

### 6.6 Оператор эксплуатации (ops_operator)
| id | Цель | Путь | Приоритет | Сейчас |
|---|---|---|---|---|
| `device.health_view` | Видеть состояние парка | Логин → боковое меню «Устройства» → таблица с KSO-001 → health_state badge («Неизвестно») → heartbeat → runtime/player версии → повторный клик в меню → persistence. Happy-path: 6 шагов — 1) Логин (break_glass_admin) → 2) Устройства в боковом меню → 3) таблица device-health-table → 4) видна строка KSO-001 с health badge → 5) поля heartbeat, runtime, player → 6) повторный заход persist. | P1 | ✅ |

### 6.7 Публичный лид (public_lead) и обработка заявок
| id | Цель | Путь | Приоритет | Сейчас |
|---|---|---|---|---|
| `advertiser.apply` | Подать заявку | Публичная страница заявки → форма → **Отправить** | P1 | ✅ |
| `advertiser.application_review` | Рассмотреть заявку | Логин → Заявки рекламодателей → заявка → **Одобрить/Отклонить** | P0 | ✅ |
| `advertiser.invite` | Пригласить рекламодателя | Заявки → **Создать приглашение** | P1 | ✅ |

### 6.8 Рекламодатель (advertiser-web) — ⚠️ фронтенд не проходил аудит
| id | Цель | Путь | Приоритет | Сейчас |
|---|---|---|---|---|
| `self.login` | Войти в кабинет | Логин рекламодателя → форма | P0 | ⚠️ проверить |
| `self.campaign_view` | Смотреть свои кампании | Логин → список кампаний виден сразу после входа → видна seed-кампания (CAMP-2026-001) с названием/кодом/статусом → клик в строку → детальная карточка с периодом. Happy-path: 4 шага — 1) Логин (advertiser_test) → 2) список кампаний с конкретной строкой → 3) клик в строку → 4) карточка кампании с периодом. Reload persistence подтверждена. | P0 | ✅ |
| `self.report_view` | Смотреть отчёт план/факт (PoP) | Кабинет → Отчёты | P1 | ⚠️ проверить |
| `self.apply_or_brief` | Подать заявку/бриф | Кабинет → Заявка/Бриф → отправить | P1 | ⚠️ проверить |
| `self.campaign_create` | Самому завести кампанию | Кабинет → Создать → форма → отправить | P2 | ⚠️ |

> advertiser-web обязан получить свой раздел в feature-registry и свои UI-smoke.

---

## 7. Инфраструктурные потоки (не UI — для полноты roadmap)
`playlist.build`, `manifest.deliver`, `pop.ingest`, `device.onboard`, `backup.restore`,
`observability` — сервисные, админ-экран не предполагается. Готовность = бэкенд +
сервисный/поведенческий тест; в колонке UI roadmap = «— (n/a)».

---

## 8. Как это потребляют Codex и Hermes

1. **Реестр.** Каждый журней с `id` → строка `docs/product/feature-registry.yaml`
   (`id`, `frontend`, `human_name`, `entry_route: /login`, `ui_path`, `smoke: test_uismoke__…`,
   `priority`, `roles`).
2. **Один журней — один UI-smoke.** «Юзабельно ✅» = зелёный `test_uismoke__<id>`,
   а не ручная галочка.
3. **Roadmap выводится, не пишется от руки.** Статус бизнес-функции = агрегат журнеев
   её домена: все P0/P1-журнеи ✅ → «Готово»; иначе «Бэкенд готов, UI нет».
4. **CI-сторож** `roadmap-consistency` валит сборку, если есть «Готово» без зелёного
   smoke по `id`. Память агентов механизмом НЕ является.
5. **Резать вертикально.** Задача = журней целиком (бэкенд+экран+кнопка+smoke), не слой.
6. **Порядок закрытия дыр (под пилот):** `campaign.create` (G1) → `user.assign_roles`
   (G2) → `advertiser.create_org` (G3) → `adsettings.configure` (G4), затем аудит
   остальных P0/P1 и advertiser-web.

---

## 9. Ведение документа (чей это труд)
- **Владелец — продукт (человек), НЕ агенты.** Любая новая фича сперва получает журней
  здесь, потом код. Агенты не имеют права помечать функцию «Готово», если её журнея тут нет.
- Изменения в продукте (новые роли, экраны, переходы) сперва отражаются здесь, затем в
  `feature-registry.yaml` и коде.
- Документ версионируется в репозитории; ссылка на него стоит в `AGENTS.md`.

---

## 10. План покрытия журнеями по вехам (дистанция до «всё закрыто»)

Полнота «все кнопки/поля закрыты» = полноте покрытия журнеями. Каждая веха: журнеи →
записи в feature-registry → глубокие smoke (перечисляют поля) → статус в roadmap выводится.
Веха закрыта, когда все её P0/P1-журнеи ✅ (зелёный smoke).

**M0 — Правда UI (ИДЁТ).** UI-TRUTH-001A ✅ (registry + harness + падающий G1-smoke).
Осталось: 001B (roadmap-consistency guard), внести user-journeys.md в репо + AGENTS.md,
расширить registry на все P0-журнеи, закрыть G1–G4 со своими smoke.

**M1 — Пилотное ядро кампаний (P0).** Все P0 админ-журнеи проходимы + зелёные smoke:
campaign.create/edit/submit, creative.upload, creative.moderate_*, campaign.approve/reject,
user.create_advertiser/assign_roles, advertiser.create_org/application_review,
emergency.activate/deactivate. Плюс поле «основание размещения». Финиш: реальную кампанию
можно провести сквозь UI end-to-end.

**M2 — Плеер / edge (критический путь к деньгам).** Контракты готовы (EDGE-001..004).
Осталось: реальный КСО-плеер (Chromium kiosk: тянет manifest, проверяет подпись, показывает,
шлёт PoP+heartbeat, исполняет kill-switch) + сборка/распространение + staged rollout на 1 КСО.
Архитектура — по решению §24 (см. §5.1 — РЕШЕНО ВЛАДЕЛЬЦЕМ: ПРАГМАТИКА, ADR-019).

**M3 — Эксплуатация + аналитика (P1).** Центр здоровья парка (§22.6); роль «Аналитик» +
отчёты план/факт/недопоказы (§12, §22.13); экспорт XLSX. advertiser-web пилот:
self.login / self.campaign_view / self.report_view + свои smoke.

**M4 — Коммерция (P2).** Финансы: заказы/тарифы/прайс/скидки/выручка (§22.12).
Недопоказы/причины/компенсации (§22.3).

**M5 — Мультиканальность (P2, по решению бизнеса).** ESL / LED / price-checker / Android-TV
(§23), per-channel адаптеры.

**M6 — Self-service (P2).** advertiser-web: полное самозаведение кампаний рекламодателем.

**Правило по всем вехам:** ни один журней вехи не «Готово» без зелёного deep-smoke.

---

## 6. PRODUCT-READINESS-PROGRAM-001 — программа доводки до реального пилота

**Версия:** 1.0 · 2026-07-28 · владелец: продукт

**Цель:** настоящий пилот на 1 КСО — не seed/script flow, а живой рекламодатель
проводит кампанию от онбординга до отчёта.

**Фокус:** онбординг реального рекламодателя (юр-реквизиты, бренды, договоры,
автоматическое присвоение кода, пользователи, UX кампании).

**Статус программы:** каноническая рамка зафиксирована. Реализация эпиков
начинается только после owner/legal approval соответствующего draft.

### Эпики

| Эпик | Название | Статус |
|------|----------|--------|
| EPIC-A | Юридические реквизиты рекламодателя | ✅ Approved for A1 (ADVERTISER-UX-001A0); A1 implementation unblocked |
| EPIC-B | Бренды / договоры / контакты | Запланирован |
| EPIC-C | Wizard + автоматическое присвоение кода | Запланирован |
| EPIC-D | Пользователи и права — UX | D1 ✅ (split); D2 ✅ (permission descriptions registry); operator walkthrough PENDING |
| EPIC-E | UX кампании (attach, flight, placement, dashboard) | #3 ✅ closed as CAMPAIGN-UX-002A; #2B ✅ (merge Dashboard/Reporting tabs); остальные запланированы |

> Фактический статус — из `PROJECT_STATE.md` + `feature-registry.yaml`.
> Брифинг PRODUCT-READINESS-PROGRAM-001 задаёт направление; часть статусов в нём
> могла устареть относительно текущего `develop`.

---

### 6.0 ADVERTISER-UX-001D1 — Users split internal vs advertiser + UUID invariant

**Статус:** ✅ smoke green, vitest 273/273, CI pending.
**Next:** ADVERTISER-UX-001D2 — permission descriptions.

**Happy-path (5 шагов):**
1. Оператор заходит в «Пользователи» → видит три вкладки: Все (N), Внутренние (N), Рекламодатели (N).
2. Вкладка «Внутренние» — только ad/break-glass пользователи; `advertiser_test` не виден.
3. Вкладка «Рекламодатели» — только local_advertiser; провайдер «Локальный (рекламодатель)»; `break_glass_admin` не виден.
4. Кнопка «+ Создать рекламодателя» → форма без поля UUID/id пользователя (только username, display_name, org_id).
5. Reload → вкладки на месте, таблица грузится.

**Data-testid:** `users-tab-bar`, `users-tab-{all,internal,advertiser}`, `users-table-{all,internal,advertiser}`, `users-{section,empty}-{all,internal,advertiser}`, `user-row-{username}`, `user-provider-{username}`.

---

### 6.0b ADVERTISER-UX-001D2 — Permission descriptions registry

**Статус:** ✅ smoke green, vitest 279/279, CI pending.
**Next:** CAMPAIGN-UX-002B или по выбору владельца.

**Источник описаний:** `apps/admin-web/src/auth/permissionDescriptions.ts` — frontend-реестр (24 permission). Выбран потому что backend `permissions.description` пуст в seed, а поднимать backend-миграцию ради описаний избыточно для D2.

**Happy-path (4 шага):**
1. Оператор → «Пользователи» → «Роли» на любом пользователе.
2. В панели управления ролями — секция «Список прав (24)» с permission code + label + description.
3. Каждое право: жирный label, моноширинный code, серая description-подстрока.
4. Неизвестный permission падает безопасно: label = code, description = «Описание права пока не задано».

**Data-testid:** `permission-catalog`, `permission-item-{safeCode}`, `permission-label-{safeCode}`, `permission-code-{safeCode}`, `permission-description-{safeCode}`.

---

### 6.0c CAMPAIGN-UX-002B — Merge duplicate Dashboard/Reporting tabs

**Статус:** ✅ vitest 279/279, UI tabs confirmed (aria snapshot proof), CI pending.
**Next:** CAMPAIGN-UX-002C — merge flights/placements/creatives into «Наполнение».

**Happy-path (3 шага):**
1. Оператор открывает карточку кампании → видит 5 вкладок: Обзор, Флайты, Плейсменты, Креативы, Дашборд.
2. Вкладка «Отчётность» отсутствует (удалена как дубликат Дашборда).
3. Дашборд содержит: План/Факт, По дням, По поверхностям/географии, Здоровье устройств.

**Data-testid:** `campaign-dashboard`, `campaign-dashboard-empty-pop`.

---

### 6.0d CAMPAIGN-UX-002C — Merge Flights/Placements/Creatives into «Наполнение»

**Статус:** ✅ Vitest 282/282, UI-smoke campaign.edit/submit/upload/inventory/creative green. Три секции в одном табе.
**Next:** CAMPAIGN-UX-002D — campaign create/fill wizard.

**Happy-path (3 шага):**
1. Оператор открывает карточку кампании → видит 3 вкладки: Обзор, Наполнение, Дашборд.
2. Вкладка «Наполнение» содержит три секции на одном экране: Рейсы, Плейсменты, Креативы.
3. Readiness checklist на Обзоре ведёт в нужную секцию внутри «Наполнения» (скролл-фокус).

**Data-testid:** `tab-content` (таб), `content-panel`, `content-readiness-summary`, `content-flights-section`, `content-placements-section`, `content-creatives-section`.

---

### 6.0e CAMPAIGN-UX-002D — Guided create-to-fill flow

**Статус:** ✅ Vitest 288/288. Баннер, CTA, content-next-step. Без переписывания wizard.
**Next:** KSO-ENV-001 или по выбору владельца.

**Happy-path (4 шага):**
1. Оператор создаёт кампанию → редирект с `?start=content`.
2. Кампания открывается на вкладке «Наполнение», баннер: «Кампания создана. Добавьте рейс, размещение и креатив».
3. На Обзоре — кнопка «Начать наполнение» для незаполненного draft.
4. В «Наполнении» — `content-next-step` показывает конкретное действие (Добавьте рейс → Добавьте размещение → Загрузите креатив → Можно отправить).

**Data-testid:** `campaign-created-next-step`, `campaign-start-filling-btn`, `content-next-step`.

### 6.1 ADVERTISER-UX-001A0 — Legal requisites draft for owner/legal approval

**Статус:** ✅ Approved for ADVERTISER-UX-001A1 migration/backend implementation by owner on 2026-07-28.
**A1 backend:** ✅ Implemented — migration 029, PUT /advertiser-organizations/{id}/legal-requisites, Pydantic cross-field validation. UI pending (A2).
**A2 UI:** ✅ Implemented — admin-web tab «Реквизиты», edit form with LE/IE toggle, save, display, reload persistence. UI-smoke green.

#### Поля

**Общие (для всех типов):**

| Поле | Тип | Обязательное | Примечание |
|------|-----|:---:|------------|
| `legal_entity_type` | enum `legal_entity` \| `individual_entrepreneur` | ✅ | |
| `legal_form` | enum: ООО / АО / ПАО / ИП / другое | ✅ | |
| `legal_form_other` | string | только если `legal_form = другое` | Свободный текст |
| `legal_name` | string | ✅ | Наименование |
| `inn` | string (10 или 12 цифр) | ✅ | 10 — юрлицо, 12 — ИП |
| `legal_address` | string | ✅ | Юридический адрес |
| `settlement_account` | string (20 цифр) | ✅ | Расчётный счёт |
| `correspondent_account` | string (20 цифр) | ✅ | Корреспондентский счёт |
| `bik` | string (9 цифр) | ✅ | БИК |
| `bank_name` | string | ✅ | Наименование банка |

**Только для `legal_entity`:**

| Поле | Тип | Обязательное | Примечание |
|------|-----|:---:|------------|
| `kpp` | string (9 цифр) | ✅ (только юрлицо) | |
| `ogrn` | string (13 цифр) | ✅ (только юрлицо) | |

**Только для `individual_entrepreneur`:**

| Поле | Тип | Обязательное | Примечание |
|------|-----|:---:|------------|
| `ogrnip` | string (15 цифр) | ✅ (только ИП) | |

#### Валидация (approved for A1)

- `inn`: 10 цифр для `legal_entity`, 12 цифр для `individual_entrepreneur`
- `kpp`: 9 цифр, required только для `legal_entity`
- `ogrn`: 13 цифр, required только для `legal_entity`
- `ogrnip`: 15 цифр, required только для `individual_entrepreneur`
- `bik`: 9 цифр
- `settlement_account`: 20 цифр
- `correspondent_account`: 20 цифр
- `legal_name`, `legal_address`, `bank_name`: non-empty
- `legal_form_other`: required только когда `legal_form = other`
- Нормализация: удалить пробелы/дефисы из цифровых полей перед валидацией
- Контрольные суммы (checksum): **NOT blocking in A1** — deferred debt

#### Deferred technical/product debt

1. **Checksum validation** — ИНН/ОГРН/ОГРНИП + bank/account key validation.
2. **Full requisites change history/versioning** — аудит изменений реквизитов.
3. **Operator/legal verification workflow** — процесс подтверждения реквизитов оператором/юристом после ввода.

#### Предлагаемый порядок задач

```
ADVERTISER-UX-001A1 — Schema + backend (после approval)
ADVERTISER-UX-001A2 — UI + smoke ✅ (FU: display completeness + real smoke proof)
ADVERTISER-UX-001B1 — Brands CRUD ✅ (backend + UI + smoke)
ADVERTISER-UX-001B2 — Contracts CRUD + PDF upload ✅ (backend + UI + smoke)
ADVERTISER-UX-001B3 — Contacts CRUD + user link
ADVERTISER-UX-001C1 — Server-side auto-code generation
ADVERTISER-UX-001C2 — Advertiser create wizard
ADVERTISER-UX-001D1 — Users: split internal vs advertiser roles in UI
ADVERTISER-UX-001D2 — Permission descriptions + UUID invariant
KSO-ENV-001 — KSO player environment setup
```

### ADVERTISER-UX-001B2 — Contracts CRUD + PDF upload

**Статус:** ✅ Реализован. Backend 12/12, vitest 4/4, UI-smoke green.

**Journey:** `advertiser.contract_pdf_upload` — break-glass admin загружает PDF-договор для рекламодателя.

**Happy-path (9 шагов):**
1. Логин → 2. Advertisers (sidebar) → 3. Выбрать ADV-001 → 4. Вкладка «Договоры»
→ 5. «Добавить договор» → 6. «Выбрать PDF» → 7. «Загрузить»
→ 8. Имя файла в строке договора → 9. Перезагрузка: данные на месте.

**Smoke:** `test_uismoke__advertiser__contract_pdf_upload` — GREEN (1 passed, 1.96s).
Доказательство: contract metadata created, PDF selected through visible UI,
upload intent → PUT → complete-upload успешен, строка показывает номер/название/имя PDF,
reload persistence.

**Backend:** 12 тестов (create/update/upload-intent schema + repo create/update/cross-org).
**Frontend:** 4 vitest-теста (render, empty state, section data-testid, file name+size).
**Миграция:** 030 — `advertiser_contracts` file metadata (5 nullable columns) + `contract_upload_sessions`.

**Operator walkthrough:** PENDING.

---

### ADVERTISER-UX-001C2 — Advertiser create wizard

**Статус:** ✅ Реализован. Vitest 10/10, backend 15/15, UI-smoke green (5.83s).

**Journey:** `advertiser.create_org` — break-glass admin создаёт рекламодателя через пошаговый мастер с авто-кодом, юр-реквизитами, контактом и подтверждением.

**Happy-path (11 шагов):**
1. Логин → 2. Advertisers (sidebar) → 3. «Создать рекламодателя»
→ 4. Основное: название + отображаемое имя + код авто → «Далее»
→ 5. Реквизиты: тип, форма, ИНН, **юридический адрес**, банк, БИК, р/с → «Далее»
→ 6. Контакты: ФИО + email → «Далее»
→ 7. Подтверждение: саммари (код, организация, ИНН, банк, контакт) → «Открыть карточку»
→ 8. Детальная карточка открыта → 9. Reload: persistence.

**ADVERTISER-UX-001C2-FU:** Legal address is real operator input — placeholder «—» removed.
Operator must type legal address. Client-side validation: «Укажите юридический адрес».

**Smoke:** `test_uismoke__advertiser__create_org` — GREEN (5.70s).
Доказательство: wizard visible → main → legal (real address filled) → contact → confirm → summary includes auto-code → card opens → reload persistence.

**Operator walkthrough:** PENDING.

---

## EPIC-L — Platform/Device Licensing

**Status:** Canon intake only. No implementation.

**Owner gate §08:** Approved 2026-07-30.

### Core Decisions

| Decision | Value |
|----------|-------|
| Licensee | Оператор (отдельная сущность, НЕ рекламодатель) |
| Enforcement | Мягкий (soft): playing screen не гаснет; блокируется только new enrollment сверх лимита/после expiry; expired/over-cap → alert + status |
| Unit | seat-month: активное = устройство держит seat; НЕ по показу/PoP; метрика = monthly peak occupied seats |
| Contour separation | Контур 1 (license) и Контур 2 (advertiser billing) строго разделены. License domain may read device identity/enrollment; must NOT depend on advertiser-commercial billing |

### Money Contours

| # | Контур | Стороны | Статус |
|---|--------|---------|--------|
| 1 | Лицензирование платформы/устройств | Оператор/licensee → вендор | EPIC-L |
| 2 | Коммерческий учёт размещений | Рекламодатель → оператор | v2.6 (deferred) |

**Rule:** Контур 1 и Контур 2 не смешивать в таблицах, сервисах, UI. Общая точка — только device identity / enrollment.

### License Payload — Approved Fields

```
license_id, licensee{id,name}, tier, issued_at, valid_from,
valid_until (nullable), max_devices, overage_allowance, grace_days,
features[], installation_binding, nonce, schema_version,
kid (in JWS header)
```

**Format:** signed `.lic` (JWS/JWT, EdDSA/ed25519, offline verification).
Public key in platform; private key vendor-side only.

### Seat-Hook Requirement

Future real device enrollment MUST mint stable device identity and reserve a license seat.
Retrofit after deployed fleet is expensive.
PLAYER/KSO implementation must not create enrollable devices without this hook.
Counting/enforcement may come later, but identity/seat hook is required at enrollment boundary.
See: `docs/architecture/epic-l-licensing.md`.

### Feature IDs (blocked)

| ID | Status |
|----|--------|
| license.view | blocked |
| license.upload | blocked |
| license.seat_release | blocked |
| license.report | blocked |
| license.enforce | blocked |

### Non-Goals (explicit)

- No license issuer implementation
- No license models/migrations/API
- No UI for licensing
- No player code changes
- No advertiser billing
- No feature statuses reachable

---

## COMMERCE-CONTUR2-001 — Commercial Inventory Sales Engine

**Контур 2:** рекламодатель → оператор. Продажа рекламного инвентаря, коммерческий учёт, статус оплаты.

### Границы (строгое разделение)

| Контур | Стороны | Предмет | Статус |
|--------|---------|---------|--------|
| Контур 1 / EPIC-L | оператор → вендор | лицензия устройств/платформы | canon intake only |
| Контур 2 / Commerce | рекламодатель → оператор | продажа рекламного инвентаря | **этот эпик** |

**Запрещено:**
- Сшивать таблицы/сервисы/UI между контурами.
- Общая точка с EPIC-L отсутствует.
- Общая точка с устройствами — только через будущие показы/PoP, не в MVP commerce.

**Not:**
- Not a payment gateway (no acquiring, no платёжный шлюз).
- Not EDI/ЭДО.
- Not license billing.

**Uses existing:**
- Inventory reservations (S-079)
- `placement_basis`
- Advertiser contracts
- Campaigns/briefs

**Не дублирует inventory.**

---

### Decision Matrix — Owner Approved (2026-07-31)

**approved for COMMERCE-CONTUR2-001A1 schema/RLS/pricing implementation by owner on 2026-07-31**
**A1 STATUS: ✅ backend foundation done** (CI #30991448734, SHA 95bb0ad).
- Migration 032 applied (4 commerce tables).
- Pricing choke-point `calculate_order_quote()` implemented (15/15 tests).
- No UI — all commerce feature IDs remain blocked.
- Next → A2: API endpoints, RLS enforcement, order CRUD.

**A2 STATUS: ✅ API/RLS foundation done** (SHA eeae6f3, CI #30996275725 backend green).
- 11 commerce endpoints: tariff/price CRUD, quote, order CRUD + status PATCH.
- Status transition guard: draft→offered→booked→confirmed→closed/cancelled.
- 4 seed permissions, 51 combined tests, guard 0.
- No UI — commerce feature IDs remain blocked.
- Next → A3a: admin UI for tariff/price management.

**A3a STATUS: ✅ admin UI done** (SHA pending, CI pending).
- CommerceTariffsPage: tariffs tab (CRUD) + prices tab (CRUD per tariff).
- Nav: «Коммерция» → /commerce/tariffs (permission: commerce.tariff_read).
- Vitest: 7/7, admin-web: 321/321 (no regressions).
- UI-smoke: test_uismoke__commerce__tariff_manage — create tariff + price item + reload.
- Feature-registry: commerce.tariff_manage + commerce.price_list_manage → reachable (43/57).
- Operator walkthrough: PENDING.
- Next → A3b: admin UI for order CRUD + status management.

| # | Decision | Approved value | Status |
|---|----------|---------------|--------|
| 1 | billing_unit | `surface_day` — рассчитывается до player/PoP, совместим с бронированием инвентаря до показа | ✅ approved |
| 2 | payment_handling | `status_only` — без acquiring, без платёжного шлюза, внешний billing/EDI | ✅ approved |
| 3 | tariff_versioning | `yes` — версии прайс-листов; завершённые заказы/кампании не пересчитываются задним числом | ✅ approved |
| 4 | discounts_in_mvp | `no` — отложено до следующей итерации | ✅ approved |
| 5a | order_status | `draft → offered → booked → confirmed → closed → cancelled` | ✅ approved |
| 5b | payment_status | `not_required → unpaid → partial → paid → overdue` | ✅ approved |

### Non-Goals (explicit)

- No payment gateway (no acquiring, no платёжный шлюз)
- No EDI/ЭДО
- No discounts in MVP
- No retroactive repricing (завершённые заказы не пересчитываются)
- No Contour 1 / EPIC-L merge
- No feature statuses reachable until A1 implementation

---

### Draft Field Matrix (not implementation — for owner review)

**Order:**
- `order_id`, `advertiser_organization_id`, `advertiser_contract_id`
- `campaign_id` (nullable, или link table позже)
- `placement_basis`
- `status` (draft/offered/booked/confirmed/closed/cancelled)
- `payment_status` (not_required/unpaid/partial/paid/overdue)
- `currency`, `amount_net`, `amount_gross` (optional/deferred)
- `price_snapshot_json`
- `valid_until` / `offer_valid_until`
- `created_at`, `updated_at`, `closed_at`

**Price List:**
- `price_list_id`, `name`, `currency`
- `valid_from`, `valid_until` (nullable)
- `version`, `status` (draft/active/archived)

**Tariff:**
- `tariff_id`, `price_list_id`, `billing_unit`
- `scope_type`, `scope_id` (nullable)
- `unit_price`, `currency`
- `valid_from`, `valid_until` (inherited or explicit)
- `status`

**Offer:**
- `offer_id`, `order_id`
- `calculated_at`, `amount`, `currency`
- `price_snapshot_json`, `valid_until`
- `status`

**Booking:**
- `order_id` / `offer_id`
- Links to existing inventory reservations (S-079)
- No duplicate inventory tables

---

### MVP Task Graph

```
A0 — canon intake + owner decisions (этот этап) ✅
 │
 ├─ A1 — schema/RLS/pricing choke-point
 ├─ A2 — tariff/price-list admin UI
 ├─ A3 — order create/card + payment status
 ├─ A4 — offer generation with price snapshot
 ├─ A5 — booking via existing reservations
 └─ A6 — close order + no-retro-reprice proof
```

A1 unblocked by owner on 2026-07-31. A2–A6 blocked pending A1 completion.

### Feature IDs (blocked)

| ID | Status |
|----|--------|
| commerce.order_create | blocked |
| commerce.tariff_manage | blocked |
| commerce.offer_generate | blocked |
| commerce.booking | blocked |
| commerce.payment_status | blocked |
| commerce.order_close | blocked |
| commerce.price_list_manage | blocked |

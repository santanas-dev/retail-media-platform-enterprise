# Roadmap — техническая, бизнесовая и UX-карта

> **Канонический roadmap-документ (ROADMAP-REBASE-003).** Задаёт последовательность работ
> и уровень зрелости каждой функции. **Функциональный SSOT статуса — `feature-registry.yaml`**
> (reachable/blocked); этот документ его не переопределяет и не дублирует, а добавляет разрез
> зрелости, которого схема registry не хранит.

## Ключевое различение

`reachable` **≠** `walkthrough` **≠** `pilot-ready` **≠** `production-ready`.
Достижимость экрана роботом не означает, что бизнес-процесс замыкается, что человек прошёл
его руками, что он развёрнут на пилоте или что продукт готов к промышленной эксплуатации.

| Уровень | Что доказано |
|---|---|
| `BLOCKED` | функция недоступна; причина в registry `gap` |
| `service / backend-proof` | backend-функция без UI-journey; доказывается unit/behavioral-тестами |
| `CI-enforced` | UI-journey достижим и закреплён зелёным UI-smoke в блокирующем гейте |
| `stand-verified` | дополнительно пройден реальным браузером на локальном стенде |
| `operator walkthrough` | **ставит только человек**; сейчас у всех функций — PENDING |
| `pilot-ready` | требует 001D host proof + owner inputs; сейчас **ни у одной функции** |
| `production-ready` | требует TLS/CD/monitoring/backup на проде; сейчас **ни у одной функции** |

## Сводка (посчитано программно)

- всего функций: **58**
- reachable: **53** · blocked: **5**
- закреплено UI-smoke в CI: **43**
- backend/service без UI-journey: **10**
- проверено браузером на стенде: **4**
- operator walkthrough: **0** (PENDING у всех — ставит только человек)
- pilot-ready: **0** · production-ready: **0**

## Матрица зрелости — все функции

Столбцы: реализовано · авто-проверка · в CI · на стенде · walkthrough · pilot · prod.

### admin-web (портал оператора) — 39

| # | Feature ID | Journey / назначение | Реализ. | Авто-проверка | CI | Стенд | Walkthrough | Pilot | Prod | Уровень / долг |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `adsettings.configure` | Сохранить настройки AD | ✅ | UI-smoke | ✅ | развёрнут | PENDING | ❌ | ❌ | CI-enforced |
| 2 | `adsettings.test` | Проверить подключение AD | ✅ | UI-smoke | ✅ | развёрнут | PENDING | ❌ | ❌ | CI-enforced |
| 3 | `advertiser.application_review` | Рассмотреть заявку рекламодателя | ✅ | UI-smoke | ✅ | развёрнут | PENDING | ❌ | ❌ | CI-enforced |
| 4 | `advertiser.brand_crud` | Управление брендами рекламодателя (создание, редакти | ✅ | UI-smoke | ✅ | развёрнут | PENDING | ❌ | ❌ | CI-enforced |
| 5 | `advertiser.contact_crud` | Управление контактами рекламодателя (создание, редак | ✅ | UI-smoke | ✅ | развёрнут | PENDING | ❌ | ❌ | CI-enforced |
| 6 | `advertiser.contract_crud` | Договоры рекламодателя — создание, редактирование, P | ✅ | UI-smoke | ✅ | ✅ | PENDING | ❌ | ❌ | stand-verified |
| 7 | `advertiser.create_org` | Создать организацию рекламодателя (managed) | ✅ | UI-smoke | ✅ | развёрнут | PENDING | ❌ | ❌ | CI-enforced |
| 8 | `advertiser.invite` | Пригласить рекламодателя | ✅ | UI-smoke | ✅ | развёрнут | PENDING | ❌ | ❌ | CI-enforced |
| 9 | `advertiser.legal_requisites` | Юридические реквизиты рекламодателя (заполнение, ред | ✅ | UI-smoke | ✅ | развёрнут | PENDING | ❌ | ❌ | CI-enforced |
| 10 | `advertiser.view` | Смотреть карточку рекламодателя | ✅ | UI-smoke | ✅ | развёрнут | PENDING | ❌ | ❌ | CI-enforced |
| 11 | `audit.view` | Смотреть журнал аудита | ✅ | UI-smoke | ✅ | развёрнут | PENDING | ❌ | ❌ | CI-enforced |
| 12 | `campaign.activate` | Запустить одобренную кампанию | ✅ | UI-smoke | ✅ | развёрнут | PENDING | ❌ | ❌ | CI-enforced |
| 13 | `campaign.approve` | Одобрить кампанию | ✅ | UI-smoke | ✅ | развёрнут | PENDING | ❌ | ❌ | CI-enforced |
| 14 | `campaign.create` | Создание кампании | ✅ | UI-smoke | ✅ | ✅ | PENDING | ❌ | ❌ | stand-verified |
| 15 | `campaign.edit` | Редактирование кампании (рейсы/размещения) | ✅ | UI-smoke | ✅ | развёрнут | PENDING | ❌ | ❌ | CI-enforced |
| 16 | `campaign.pause` | Приостановить активную кампанию | ✅ | UI-smoke | ✅ | развёрнут | PENDING | ❌ | ❌ | CI-enforced |
| 17 | `campaign.reject` | Отклонить кампанию с причиной | ✅ | UI-smoke | ✅ | развёрнут | PENDING | ❌ | ❌ | CI-enforced |
| 18 | `campaign.submit` | Отправить кампанию на согласование | ✅ | UI-smoke | ✅ | развёрнут | PENDING | ❌ | ❌ | CI-enforced |
| 19 | `commerce.booking` | Бронирование (offered→booked) | ✅ | UI-smoke | ✅ | развёрнут | PENDING | ❌ | ❌ | CI-enforced |
| 20 | `commerce.offer_generate` | Генерация коммерческого предложения (draft→offered) | ✅ | UI-smoke | ✅ | развёрнут | PENDING | ❌ | ❌ | CI-enforced |
| 21 | `commerce.order_close` | Закрытие заказа (terminal) | ✅ | UI-smoke | ✅ | развёрнут | PENDING | ❌ | ❌ | CI-enforced |
| 22 | `commerce.order_create` | Создание коммерческого заказа | ✅ | UI-smoke | ✅ | развёрнут | PENDING | ❌ | ❌ | CI-enforced |
| 23 | `commerce.payment_status` | Статус оплаты заказа | ✅ | UI-smoke | ✅ | развёрнут | PENDING | ❌ | ❌ | CI-enforced |
| 24 | `commerce.price_list_manage` | Управление версиями прайс-листов | ✅ | UI-smoke | ✅ | развёрнут | PENDING | ❌ | ❌ | CI-enforced |
| 25 | `commerce.tariff_manage` | Управление тарифами и прайс-листами | ✅ | UI-smoke | ✅ | развёрнут | PENDING | ❌ | ❌ | CI-enforced |
| 26 | `creative.moderate_approve` | Одобрить креатив (модерация) | ✅ | UI-smoke | ✅ | развёрнут | PENDING | ❌ | ❌ | CI-enforced |
| 27 | `creative.moderate_reject` | Отклонить креатив с причиной (модерация) | ✅ | UI-smoke | ✅ | развёрнут | PENDING | ❌ | ❌ | CI-enforced |
| 28 | `creative.upload` | Загрузка креатива | ✅ | UI-smoke | ✅ | ✅ | PENDING | ❌ | ❌ | stand-verified |
| 29 | `device.health_view` | Видеть состояние парка устройств | ✅ | UI-smoke | ✅ | развёрнут | PENDING | ❌ | ❌ | CI-enforced |
| 30 | `emergency.activate` | Экстренно остановить показ | ✅ | UI-smoke | ✅ | развёрнут | PENDING | ❌ | ❌ | CI-enforced |
| 31 | `emergency.deactivate` | Снять аварийный режим | ✅ | UI-smoke | ✅ | развёрнут | PENDING | ❌ | ❌ | CI-enforced |
| 32 | `inventory.rule_create` | Создать правило инвентаря | ✅ | UI-smoke | ✅ | развёрнут | PENDING | ❌ | ❌ | CI-enforced |
| 33 | `inventory.simulate` | Прогноз показов (симуляция инвентаря) | ✅ | UI-smoke | ✅ | развёрнут | PENDING | ❌ | ❌ | CI-enforced |
| 34 | `system.theme_switch` | Переключение темы (light/dark) | ✅ | UI-smoke | ✅ | развёрнут | PENDING | ❌ | ❌ | CI-enforced |
| 35 | `user.assign_roles` | Назначить роли/права пользователю | ✅ | UI-smoke | ✅ | развёрнут | PENDING | ❌ | ❌ | CI-enforced |
| 36 | `user.create_advertiser` | Завести локального рекламодателя | ✅ | UI-smoke | ✅ | развёрнут | PENDING | ❌ | ❌ | CI-enforced |
| 37 | `user.deactivate` | Заблокировать пользователя | ✅ | UI-smoke | ✅ | развёрнут | PENDING | ❌ | ❌ | CI-enforced |
| 38 | `user.reset_password` | Сбросить пароль пользователю | ✅ | UI-smoke | ✅ | развёрнут | PENDING | ❌ | ❌ | CI-enforced |
| 39 | `user.split_internal_advertiser` | Разделить пользователей на внутренних и рекламодател | ✅ | UI-smoke | ✅ | развёрнут | PENDING | ❌ | ❌ | CI-enforced |

### advertiser-web (кабинет рекламодателя) — 5

| # | Feature ID | Journey / назначение | Реализ. | Авто-проверка | CI | Стенд | Walkthrough | Pilot | Prod | Уровень / долг |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `self.apply_or_brief` | Подать заявку/бриф (кабинет рекламодателя) | ✅ | UI-smoke | ✅ | развёрнут | PENDING | ❌ | ❌ | CI-enforced |
| 2 | `self.campaign_create` | Самому завести кампанию (self-service, P2) | ❌ | — | — | — | PENDING | ❌ | ❌ | BLOCKED — UI-smoke отсутствует. P2 — self-service фаза, не пилот. |
| 3 | `self.campaign_view` | Смотреть свои кампании (кабинет рекламодателя) | ✅ | UI-smoke | ✅ | развёрнут | PENDING | ❌ | ❌ | CI-enforced |
| 4 | `self.login` | Войти в кабинет рекламодателя | ✅ | UI-smoke | ✅ | ✅ | PENDING | ❌ | ❌ | stand-verified |
| 5 | `self.report_view` | Смотреть отчёт план/факт (PoP) — кабинет рекламодате | ❌ | — | — | — | PENDING | ❌ | ❌ | BLOCKED — UI-smoke отсутствует. Фронтенд advertiser-web не проходил аудит. |

### публичные страницы — 1

| # | Feature ID | Journey / назначение | Реализ. | Авто-проверка | CI | Стенд | Walkthrough | Pilot | Prod | Уровень / долг |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `advertiser.apply` | Подать заявку на подключение (публичная форма) | ✅ | UI-smoke | ✅ | развёрнут | PENDING | ❌ | ❌ | CI-enforced |

### service / backend (без UI-journey) — 13

| # | Feature ID | Journey / назначение | Реализ. | Авто-проверка | CI | Стенд | Walkthrough | Pilot | Prod | Уровень / долг |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `backup.restore` | Резервное копирование и восстановление | ✅ | backend-tests | — | — | PENDING | ❌ | ❌ | service / backend-proof |
| 2 | `campaign.complete` | Автоматическое завершение кампании по концу рейса | ✅ | backend-tests | — | — | PENDING | ❌ | ❌ | service / backend-proof |
| 3 | `device.heartbeat` | Heartbeat устройств (health/статус) | ✅ | backend-tests | — | — | PENDING | ❌ | ❌ | service / backend-proof |
| 4 | `device.onboard` | Онбординг устройства (device-code → JWT) | ✅ | backend-tests | — | — | PENDING | ❌ | ❌ | service / backend-proof |
| 5 | `license.enforce` | Enforcement лицензии при device enrollment | ✅ | backend-tests | — | — | PENDING | ❌ | ❌ | service / backend-proof |
| 6 | `license.report` | Отчёт по лицензии (занятые/свободные seats + пик) | ✅ | backend-tests | — | — | PENDING | ❌ | ❌ | service / backend-proof |
| 7 | `license.seat_release` | Освобождение лицензионного seat при decommission | ✅ | backend-tests | — | — | PENDING | ❌ | ❌ | service / backend-proof |
| 8 | `license.upload` | Загрузка/установка лицензионного файла | ❌ | — | — | — | PENDING | ❌ | ❌ | BLOCKED — Layer 2 (signed-license/JWS/CRL + UI upload) — не реализован. |
| 9 | `license.view` | Просмотр активных лицензий (UI) | ❌ | — | — | — | PENDING | ❌ | ❌ | BLOCKED — Layer 2 (signed-license/UI) — не реализован. |
| 10 | `manifest.deliver` | Доставка манифеста на устройство | ✅ | backend-tests | — | — | PENDING | ❌ | ❌ | service / backend-proof |
| 11 | `observability` | Мониторинг и метрики (Prometheus/Grafana) | ✅ | backend-tests | — | — | PENDING | ❌ | ❌ | service / backend-proof |
| 12 | `playlist.build` | Построение плейлиста из манифеста | ❌ | — | — | — | PENDING | ❌ | ❌ | BLOCKED — Плеер не перенесён в enterprise. Код есть в старом репо (PLAYER-AUD-00 |
| 13 | `pop.ingest` | Приём PoP-событий от устройств | ✅ | backend-tests | — | — | PENDING | ❌ | ❌ | service / backend-proof |

## Пять blocked-функций — объяснение

| Feature ID | Почему blocked | Что нужно | Волна |
|---|---|---|---|
| `self.report_view` | UI-smoke отсутствует; advertiser-web не проходил аудит | journey + smoke на кабинет рекламодателя | Wave 2 |
| `self.campaign_create` | self-service фаза, сознательно отложена (P2) | решение владельца о self-service scope | Wave 2 (по решению) |
| `playlist.build` | плеер не перенесён в enterprise-репозиторий | PLAYER-IMPORT + реальный КСО | Wave 3 |
| `license.view` | signed-license Layer 2 не реализован | JWS/CRL + UI | Wave 3 |
| `license.upload` | signed-license Layer 2 не реализован | JWS/CRL + UI upload | Wave 3 |


## Технические направления

| # | Направление | Завершено | На стенде | Остаётся | Риск | Приоритет |
|---|---|---|---|---|---|---|
| 1 | Campaign lifecycle + creatives | create/edit/submit/approve/reject/pause/activate, загрузка и модерация креативов | ✅ развёрнут; `campaign.create`, `creative.upload` проверены браузером | walkthrough человеком | низкий | **P1** |
| 2 | Advertiser / self-service | заявка, рассмотрение, org/brand/contract/contact, приглашение, вход | ✅ развёрнут; `contract_crud` проверен | `self.report_view`, `self.campaign_create` blocked; advertiser-web не проходил UX-аудит | средний | **P1** |
| 3 | Inventory, devices, emergency | правила, симуляция, health-обзор, активация/деактивация аварийного режима | ✅ развёрнут | нет реального КСО → устройство только `KSO-001` в статусе «не зарегистрирован» | средний | P2 |
| 4 | Commerce Contour 2 | тарифы, прайс-листы, заказы, offer/booking/close, payment status | ✅ развёрнут, пустые состояния корректны | бизнес-проверка человеком | низкий | P2 |
| 5 | Licensing Layer 1 / Layer 2 | Layer 1: enforce, seat_release, report | Layer 1 ✅ | **Layer 2 (signed-license JWS/CRL + UI) не реализован** → `license.view`, `license.upload` blocked | высокий | P2 |
| 6 | KSO / player / playlist | — | — | **плеер не перенесён**, `playlist.build` blocked, реального КСО нет | высокий | P2 |
| 7 | Security, RLS, tenant isolation | RLS на tenant-таблицах, `retail_media_app` NOBYPASSRLS, fail-closed scopes, audit | ✅ подтверждено на стенде (`rolbypassrls=f`) | RLS-proof на пилот-хосте | низкий | P1 |
| 8 | CI, UI-smoke stability, test truth | 40 jobs, blocking release-gate, anti-skip guards, барьер `wait_settled`, **транзакционная граница API (API-TX-BOUNDARY-001)** | — | ✅ **UI-SMOKE-STABILITY-005 закрыт** — 5× first-attempt green | низкий | — |
| 9 | Local stand, pilot packaging, deployment | LOCAL-DEV-STAND-001 ✅ OPERATIONAL, immutable bundle, update+rollback | ✅ работает | **001D HOST PROOF PENDING**, 15 owner inputs, reverse proxy/TLS отсутствуют | **высокий** | **P0** |
| 10 | Backup/restore, monitoring, secrets, TLS/CD, prod ops | backup+restore drill в CI, password-file contract, secret-гейты | стенд: backup не требуется (disposable) | TLS, CD, мониторинг прода, ротация секретов — **отсутствуют** | **высокий** | P2 |

## Бизнес-карта по ролям

| Роль | End-to-end journey | Уровень | Разрыв |
|---|---|---|---|
| Системный администратор | вход → пользователи/роли → AD/LDAPS → аудит | UI reachable + автоматизировано | walkthrough не пройден |
| Оператор платформы | рекламодатель → кампания → креатив → модерация → согласование → публикация | автоматизировано, частично **работает на стенде** | не замкнут показ: нет плеера и реального КСО |
| Рекламодатель | заявка → рассмотрение → вход → бренды/договоры/контакты → просмотр кампаний | UI reachable | **отчёт план/факт и self-service создание кампании — blocked**; кабинет без UX-аудита |
| Служба безопасности | аварийный режим → аудит → RLS/роли | UI reachable | нет отдельного journey ИБ-офицера; walkthrough не пройден |
| Устройство / КСО | onboarding → manifest → воспроизведение → PoP | **backend-only** | **плейлист/плеер отсутствуют**, реального КСО нет — цепочка не замыкается |
| Коммерческий оператор | тариф → прайс-лист → заказ → offer → booking → close → оплата | автоматизировано | бизнес-валидация человеком не проводилась |

**Главный разрыв:** экраны до-плеерного потока существуют и закреплены CI, но **сквозной бизнес-процесс «показ → подтверждение показа → отчёт» не замыкается** — нет плеера, нет реального КСО, у рекламодателя недоступен отчёт.

## UX backlog — PORTAL-UX-POLISH (аудит A0)

Аудит проведён реальным браузером против стенда `stand-4635e72`, 21 экран,
read-only, продуктовые данные не создавались. **Human walkthrough НЕ пройден —
подтверждает только владелец/аудитор (Rule 8).**

### Инвентарь маршрутов

| Портал | Маршрутов | Проверено | Примечание |
|---|---|---|---|
| admin-web | 17 | 15 + detail + create-форма | все пункты бокового меню |
| advertiser-web | 15 | 2 публичных (`/login`, `/become-advertiser`) | **кабинет не проверен**: у `advertiser_test` служебный случайный пароль, интерактивных учётных данных нет |

**Расхождение реестра и поверхности.** advertiser-web содержит 15 маршрутов
(`dashboard`, `briefs`, `briefs/new`, `briefs/:id`, `campaigns`, `campaigns/new`,
`campaigns/:id`, `creatives`, `documents`, `profile`, `support`,
`accept-invite/:token`, …), тогда как в registry за ним числится 5 функций, а
`self.campaign_create` помечен `blocked` при существующем маршруте
`campaigns/new`. Это **не UX-дефект**, а расхождение учёта — см. «Прочие долги».
Статусы registry в A0 не менялись: смена требует нового доказательства.

### Backlog

| ID | Портал / route | Actor | Проблема | Evidence | Impact | Sev | Тип | Acceptance |
|---|---|---|---|---|---|---|---|---|
| PORTAL-UX-001 | admin `/campaigns`, `/audit`, `/creatives/moderation`, `/advertiser-applications` | оператор | Нет поиска по тексту и сортировки колонок в больших таблицах | 1440px: campaigns 42 строки, audit 50, moderation 26, applications 16; `search=0`, сортируемых заголовков `0` во всех | Оператор не находит запись при росте объёма; аудит инцидента вручную | **High** | table | Поиск по коду/названию и сортировка ключевых колонок |
| PORTAL-UX-002 | admin, все экраны, 390×844 | оператор | Сайдбар не сворачивается: занимает 220px из 390, заголовок и колонки обрезаны | Скриншот `admin-campaigns--390`: обрезаны «Кампании» и колонка «Статус»; переполнение внутри контейнера, поэтому `documentElement` его не показывает | Портал непригоден с планшета/телефона | **High** | responsive | Сайдбар сворачивается ≤768px, контент без обрезки |
| PORTAL-UX-003 | admin `/settings/ad`, `/inventory`, `/advertisers`, `/emergency`, `/campaigns/new`; adv `/become-advertiser` | все | Подписи полей визуальные, но не связаны программно | `unlabelled`: settings-ad 6/8, become-advertiser 6/7, inventory 1/1, advertisers 1/1, emergency 1/1, campaign-new 1/11 | Форма недоступна для скринридера; ввод вслепую | **High** | accessibility | У каждого поля `label for` или `aria-label` |
| PORTAL-UX-004 | advertiser-web, кабинет | рекламодатель | 13 из 15 маршрутов ни разу не проверены — ни аудитом, ни UI-smoke | В registry за порталом 5 функций; smoke только `self.login`; аудит A0 дошёл лишь до публичных страниц | Внешняя роль без какой-либо проверки качества | **High** | navigation | Аудит кабинета после выдачи проверочной учётной записи |
| PORTAL-UX-005 | admin `/audit` | ИБ / оператор | Длинный текст в ячейках без усечения: 45 ячеек >60 символов | 1440px, 50 строк | Таблица нечитаема, строки «прыгают» | Medium | table | Усечение с раскрытием, моноширинные ID |
| PORTAL-UX-006 | admin, сайдбар | оператор | Имя пользователя обрезано до «Break-…» | Все экраны, 1440px | Неясно, под какой учётной записью выполняется действие | Medium | visual | Полное имя или tooltip |
| PORTAL-UX-007 | admin, сайдбар | оператор | Переключатель темы — две иконки без подписи и `aria-label` | Все экраны | Назначение неочевидно; недоступно скринридеру | Medium | accessibility | `aria-label` и различимое активное состояние |
| PORTAL-UX-008 | admin `/devices` | оператор | Пустое значение обозначается тремя способами: «нет данных», «–», «Неизвестно» | 1440px, таблица устройств | Неясно, отсутствует ли значение или не получено | Medium | visual | Единый паттерн пустого значения |
| PORTAL-UX-009 | admin `/settings/ad` | администратор | Английский текст в русском интерфейсе: «AD integration is disabled. Employee AD login is not available.» | Скриншот `admin-settings-ad--1440` | Смешение языков в операционном инструменте | Medium | visual | Локализованные сообщения состояния |
| PORTAL-UX-010 | admin `/commerce/tariffs` | коммерческий оператор | Табы выглядят как кнопки, активный отличается только заливкой | 1440px | Неочевидна навигация внутри раздела | Low | navigation | Явный таб-паттерн с `aria-selected` |
| PORTAL-UX-011 | admin, переходы между разделами | оператор | Нет видимого индикатора загрузки при переходах | Все переходы 1440px | Неясно, идёт ли работа | Low | state | Скелетон или индикатор на переходах |

**Проверено и дефекта не обнаружено:** горизонтальное переполнение документа
на 1280 и 390 отсутствует; пустые состояния в «Коммерции» и «Устройствах»
корректны и с CTA; фильтры-чипы по статусу на `/campaigns` присутствуют;
пагинация в `/audit` есть; тёмная тема отрисовывается без потери контента.

### Согласование с findings ROADMAP-REBASE-003

| Прежний | Итог A0 | Основание |
|---|---|---|
| UX-001 поля без меток | **уточнён** → PORTAL-UX-003 | Подписи визуально есть, но не связаны программно; масштаб шире — 6 экранов, не 1 |
| UX-002 обрезано имя | подтверждён → PORTAL-UX-006 | — |
| UX-003 переключатель темы | подтверждён → PORTAL-UX-007 | — |
| UX-004 разнобой пустых значений | подтверждён → PORTAL-UX-008 | — |
| UX-005 нет фильтра в «Кампаниях» | **уточнён** → PORTAL-UX-001 | Фильтры-чипы по статусу **есть**; отсутствуют текстовый поиск и сортировка — и не только здесь |
| UX-006 нет фильтров в «Аудите» | **объединён** в PORTAL-UX-001 | Та же причина; отдельно выделено усечение текста (PORTAL-UX-005) |
| UX-007 табы в «Коммерции» | подтверждён → PORTAL-UX-010 | — |
| UX-008 advertiser-web без аудита | **уточнён** → PORTAL-UX-004 | Установлен масштаб: 13 из 15 маршрутов не проверены; выявлена причина — нет проверочной учётной записи |
| UX-009 нет индикатора загрузки | подтверждён → PORTAL-UX-011 | — |
| UX-010 узкий viewport без дефектов | **устарел** | Опровергнут: `documentElement` переполнения не даёт, но сайдбар съедает 56% ширины → PORTAL-UX-002 |

### Прочие долги — не UX (разделены намеренно)

- **Учёт функций:** 13 маршрутов advertiser-web вне registry; `self.campaign_create` `blocked` при существующем маршруте. → задача учёта, не UX.
- **Отсутствующая возможность:** нет проверочной учётной записи рекламодателя для аудита и ручного прохода. → блокирует PORTAL-UX-004 и walkthrough кабинета.
- **Backend/CI:** `401 /auth/refresh` в консоли до входа — ожидаемое поведение при отсутствии сессии, дефектом не является.

### Нарезка PORTAL-UX-POLISH

Порядок по ценности и риску, а не по удобству разработки.

| Задача | Scope | Routes / components | Acceptance | Vitest | UI-smoke | Риск |
|---|---|---|---|---|---|---|
| **A1** shared foundation | паттерны заголовка, тулбара, состояний, форм и таблиц | общие компоненты обоих порталов | единый паттерн применён без изменения поведения | покрытие новых компонентов | существующие 38 остаются зелёными | **высокий blast radius** — трогает все экраны |
| **A2** таблицы и поиск | PORTAL-UX-001, 005 | `/campaigns`, `/audit`, `/creatives/moderation`, `/advertiser-applications` | поиск и сортировка работают; длинный текст усечён | тесты поиска/сортировки | без изменений | средний |
| **A3** accessibility форм | PORTAL-UX-003, 007 | 6 экранов с формами | все поля программно помечены | проверка `label for`/`aria-label` | без изменений | низкий |
| **A4** responsive | PORTAL-UX-002 | layout/сайдбар | ≤768px сайдбар сворачивается, контент не обрезан | тест поведения layout | добавить проверку 390px | средний |
| **A5** advertiser-web | PORTAL-UX-004 | 13 непроверенных маршрутов | аудит проведён, backlog дополнен | — | journey кабинета | **зависит** от учётной записи |
| **A6** визуальная согласованность | PORTAL-UX-006, 008, 009, 010, 011 | сайдбар, `/devices`, `/settings/ad`, `/commerce` | единые термины, локализация, индикаторы | — | без изменений | низкий |
| **A7** operator walkthrough | ручной проход владельца | — | заполненный чеклист | — | — | — |

**Рекомендуемый порядок:** A3 → A2 → A4 → A6 → A1 → A5 → A7.
A3 и A2 дают наибольшую отдачу при минимальном радиусе; A1 намеренно **после**
них, поскольку меняет все экраны сразу и его дешевле делать на уже уточнённых
паттернах; A5 заблокирован учётной записью; A7 закрывает волну.

### Чеклист ручного прохода (владелец/аудитор, ~30–45 мин)

Заполняет **только человек**. Все статусы — PENDING.

| # | Journey | Ожидаемый результат | PASS/FAIL | Комментарий |
|---|---|---|---|---|
| 1 | Вход в admin под своей учётной записью | Попадание на «Кампании» | ☐ | |
| 2 | Найти конкретную кампанию среди 40+ | Находится без прокрутки всего списка | ☐ | |
| 3 | Создать черновик кампании | Переход на карточку, статус «Черновик» | ☐ | |
| 4 | Добавить флайт и плейсмент | Появляются в таблицах сразу | ☐ | |
| 5 | Загрузить креатив с ПК | Статус «Готов», виден после перезагрузки | ☐ | |
| 6 | Отправить кампанию на согласование | Кнопка активна, статус меняется | ☐ | |
| 7 | Согласовать кампанию | Статус «Согласована» | ☐ | |
| 8 | Отклонить кампанию с причиной | Причина отображается | ☐ | |
| 9 | Модерация креатива (одобрить/отклонить) | Статус меняется, видно в списке | ☐ | |
| 10 | Завести рекламодателя, бренд, договор, контакт | Все сущности сохраняются | ☐ | |
| 11 | Загрузить PDF договора | Файл виден после перезагрузки | ☐ | |
| 12 | Рассмотреть заявку рекламодателя и выслать приглашение | Токен приглашения выдан | ☐ | |
| 13 | Создать тариф, прайс-лист, заказ; закрыть заказ | Полный цикл проходится | ☐ | |
| 14 | Правило инвентаря и симуляция | Результат симуляции понятен | ☐ | |
| 15 | Аварийный режим: включить и выключить | Статус явно виден | ☐ | |
| 16 | Журнал аудита: найти собственное действие | Запись находится | ☐ | |
| 17 | Переключить светлую/тёмную тему | Контент читаем в обеих | ☐ | |

**Rule 8:** строка `operator walkthrough` в PROJECT_STATE заполняется только
человеком. Агент оставляет **PENDING**.

## Волны

| Волна | Состав | Вход | Done gate | Зависимости |
|---|---|---|---|---|
| **Wave 0 — стабильность и truth** | ~~UI-SMOKE-STABILITY-005~~ ✅, ~~`self__login`~~ ✅ | — | **выполнено**: 5× first-attempt green release-gate на `4e4a3e5` | — |
| **Wave 1 — walkthrough + UX** | operator walkthrough (человек), `PORTAL-UX-POLISH` (UX-001…009) | Wave 0 | `operator walkthrough: OK` в PROJECT_STATE + UX P0/P1 закрыты | стенд OPERATIONAL ✅ |
| **Wave 2 — недостающие бизнес-функции** | `self.report_view`, `self.campaign_create` (по решению владельца), аудит advertiser-web | Wave 1 | journeys + smoke зелёные, registry обновлён с доказательством | решение по self-service |
| **Wave 3 — KSO/player + signed licensing** | PLAYER-IMPORT, `playlist.build`, EPIC-L Layer 2 (`license.view`, `license.upload`) | Wave 2 | сквозной показ → PoP → отчёт замкнут | **реальный КСО** |
| **Wave 4 — pilot deployment** | 001D host proof, 001E controlled deploy | Wave 1 (мин.) | pilot GO, deployed SHA зафиксирован | 15 owner inputs, TLS/DNS |
| **Wave 5 — production hardening** | TLS/CD, monitoring, secret rotation, backup на проде | Wave 4 | production GO | отдельное решение владельца |

## Решения владельца — УТВЕРЖДЕНЫ (OWNER-ROADMAP-DECISION-003)

Рекомендации ROADMAP-REBASE-003 приняты без изменений. Это действующие рамки работ.

| # | Решение | Утверждено |
|---|---|---|
| 1 | Стратегия | **UX-first** — после завершения Wave 0 |
| 2 | Граница ближайшего pilot scope | **control-plane only** |
| 3 | Реальный КСО / player / PoP | **не входит** в ближайший pilot и **не заявляется готовым** |
| 4 | UI gate до пилота | закрыты все **High** и **P1** UX-дефекты; ключевые journeys пройдены человеком; **operator walkthrough подтверждает только владелец/аудитор** |
| 5 | Production deployment | **без календарной даты**; только после control-plane pilot; требует реального КСО, signed licensing Layer 2 и эксплуатационного контура |

### Утверждённая последовательность

`UI-SMOKE-STABILITY-005` → `PORTAL-UX-POLISH` → operator walkthrough → недостающие
business-функции → KSO/player + signed licensing → pilot → production hardening.

Волны ниже сохраняются как детализация этой последовательности; при расхождении
приоритет имеет утверждённый порядок.

## Честные проценты (методика раздельная)

Единый процент готовности не выводится намеренно — измерения несоизмеримы.

| Измерение | Значение | Методика |
|---|---|---|
| Функциональная реализация | **91%** | 53 reachable / 58 registry |
| CI-закрепление UI-journey | **74%** | 43 в блокирующем UI-smoke / 58 |
| Готовность локального стенда | **OPERATIONAL**, browser-verified **9%** | стенд работает; 4 journey из 43 UI пройдены реальным браузером |
| Business journey completeness | **~60%** | 4 из 6 ролей замыкаются до-плеерно; КСО и отчёт рекламодателя не замкнуты |
| UX maturity | **низкая** | 9 открытых дефектов, 4 из них high; advertiser-web не аудирован; walkthrough 0 |
| Pilot readiness | **~25%** | tooling готов, host preflight `NEEDS_OWNER_INPUT`, 15 owner inputs открыты |
| Production readiness | **0% — NO-GO** | нет TLS/CD/мониторинга/бэкапа прода; deployed SHA UNKNOWN |

> **53/58 — это не 91% готовности продукта.** Это доля функций, достижимых в UI.

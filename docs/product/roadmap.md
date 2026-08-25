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
| 8 | CI, UI-smoke stability, test truth | 40 jobs, blocking release-gate, anti-skip guards, барьер `wait_settled` | — | **UI-SMOKE-STABILITY-005 BLOCKED**; `self__login` нестабилен | **высокий** | **P0** |
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

## UX backlog (агентский аудит стенда; human walkthrough НЕ пройден)

Аудит read-only, 16 экранов, продуктовые данные не создавались.

| ID | Экран / journey | Проблема | Влияние | Severity | Acceptance |
|---|---|---|---|---|---|
| UX-001 | Настройки AD | 2 поля формы без `aria-label`/`id`/`placeholder` | недоступно для скринридера, неясно назначение | **high** | у всех полей есть программная метка |
| UX-002 | Сайдбар (все экраны) | имя пользователя обрезано до «Break-…» | оператор не видит, под кем работает | medium | полное имя или tooltip |
| UX-003 | Сайдбар | переключатель темы — две иконки без подписи/`aria-label` | непонятное назначение, недоступность | medium | подписи или aria-label |
| UX-004 | Устройства | пустота обозначена по-разному: «нет данных», «–», «Неизвестно» | разнобой терминов, неясно, что отсутствует | medium | единый паттерн пустого значения |
| UX-005 | Кампании | 42 строки без видимого фильтра/поиска | оператор не найдёт кампанию при росте объёма | **high** | фильтр по статусу/коду/названию |
| UX-006 | Журнал аудита | 50 строк, фильтров не обнаружено | расследование инцидента затруднено | **high** | фильтр по актору/действию/дате |
| UX-007 | Коммерция | табы выглядят как кнопки; активный отличается только заливкой | неочевидна навигация внутри раздела | low | явный таб-паттерн |
| UX-008 | Портал рекламодателя | не проходил UX-аудит (в registry `self.report_view` gap) | ключевая внешняя роль без проверки | **high** | аудит кабинета + journey отчёта |
| UX-009 | Все экраны | нет видимого индикатора загрузки при переходах | оператор не понимает, идёт ли работа | low | скелетон/спиннер на переходах |
| UX-010 | Узкий viewport (390px) | горизонтального переполнения нет, меню доступно — **дефекта не обнаружено** | — | info | зафиксировано как норма |

**EPIC-кандидат `PORTAL-UX-POLISH`** — не начат, не завершён; состав: UX-001…UX-009.

## Волны

| Волна | Состав | Вход | Done gate | Зависимости |
|---|---|---|---|---|
| **Wave 0 — стабильность и truth** | UI-SMOKE-STABILITY-005, `self__login` PENDING | сейчас | 3× first-attempt green release-gate | — |
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

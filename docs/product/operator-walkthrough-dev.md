# Operator walkthrough в DEV — сценарии для владельца (Rule 8)

> **ПРИОСТАНОВЛЕНО владельцем 2026-08-31 (`OD-041`).** RM-UX-007 не закрывается и не переводится в done; прогон возобновляется после
> утверждения единого плана реализации (`docs/product/implementation-plan-v2.6.md`, RM-GOV-012). Сценарии сохраняются как есть.

**Статус:** `operator walkthrough: PENDING` — строку `OK` / `замечания …` ставит только человек-оператор
(AGENTS.md, правило 8); агент может поставить только `PENDING`. Этот документ — сценарии, не инструкция
«куда кликать»: по правилу 8 оператор проходит happy-path **без пошаговой инструкции** и фиксирует,
понятен ли путь. Подготовлено Claude Code 2026-08-31 для RM-UX-007 (`kind: human`, Gate-U).

## 1. Контур и предусловия

| | |
|---|---|
| DEV-стенд (`stand-81`, `rmp-local-stand`) | admin **http://192.168.110.81:3000** · advertiser **http://192.168.110.81:3001** · API **http://192.168.110.81:8000** (`GET /version`; маршрута `/health` нет) · MinIO S3 `http://192.168.110.81:9000` · device-gateway `127.0.0.1:8001` только на хосте стенда (для walkthrough не нужен) |
| Развёрнутый SHA (проверено curl 2026-08-31T10:52Z) | **`stand-27dc397`** — git_sha `27dc397`, schema `036`, environment `staging`, build 2026-08-26T09:11:27Z (сервис сообщает сам). Отстаёт от `develop @ 4ac3ddb` на 18 коммитов, **ни один не трогает `apps/`** — UI актуален. Walkthrough фиксируется на этом SHA; после обновления стенда сценарии повторяются на новом SHA |
| Не стенд | santa2 `192.168.110.78:3100/3101/8010` — локальный preview-контур (identity не сообщает, `evidence: false` в `environment-inventory.yaml`); `192.168.110.78:3200` — внешний read-only мониторинг (доска roadmap). Для walkthrough и evidence **не используются** |
| Логины | учётные записи стенда — администратор и тестовый рекламодатель; пароли только из approved password files владельца (`~/.config/rmp-local-stand/…`, см. `scripts/deploy/stand_safe_smoke.py`), dev-пароли на стенде не используются. На форме входа админ-портала переключить провайдер с «Сотрудник / AD» на локальный/break-glass |
| Данные | seed стенда: кампания `CAMP-2026-001`, устройство `KSO-001`; MinIO `.81:9000` live (200) — загрузка креативов/PDF через presigned PUT |
| Что фиксировать | по каждому сценарию: результат (OK / замечание), скриншот `walkthrough/<SHA>/S<NN>-<journey>.png`, три отметки правила 8: **(a)** главное действие видно без поиска, **(b)** на каждом шаге ясен следующий шаг, **(c)** нет спрятанных обязательных многофазных переходов |

## 2. Сценарии (43 reachable UI-journey, сгруппированы по story Дополнения AP)

Колонка «Цель» — что оператор хочет получить; «Ожидаемо» — видимый результат. Пути и кнопки намеренно
не расписаны (правило 8). Канонические пути для сверки после прогона — `user-journeys.md` §6.

### Менеджер кампаний (break-glass / campaign_manager)

| № | Story | Journey | Цель | Ожидаемо |
|---|---|---|---|---|
| S01 | US-CAM-001 | `campaign.create`, `inventory.simulate` | Завести кампанию с основанием размещения и оценить инвентарь | Кампания `draft` в списке с основанием; прогноз показов виден до сохранения или из карточки |
| S02 | — | `campaign.edit`, `creative.upload` | Добавить рейс и размещение, загрузить ролик | Рейс/размещение в карточке; креатив в статусе «Готов», сохраняется после перезагрузки |
| S03 | US-CAM-002 | `campaign.submit` | Отправить кампанию на согласование | Checklist показывает, чего не хватает; после закрытия пунктов — статус «на согласовании» |
| S04 | US-INV-001 | `inventory.rule_create`, `inventory.simulate` | Создать правило инвентаря и увидеть его влияние | Правило в списке; симуляция учитывает правило |
| S05 | — | `campaign.activate`, `campaign.pause` | Запустить одобренную кампанию, затем поставить на паузу | Статусы `active` → `paused`; действия видны только в допустимом статусе |

### Согласующий и модератор (approver / moderator)

| № | Story | Journey | Цель | Ожидаемо |
|---|---|---|---|---|
| S06 | US-APR-001 | `campaign.approve`, `campaign.reject` | Одобрить одну кампанию, отклонить другую с причиной | Статусы изменились; причина отказа видна менеджеру |
| S07 | US-MOD-001 | `creative.moderate_approve`, `creative.moderate_reject` | Пропустить один креатив, отклонить другой с причиной | Результат виден в карточке кампании; отклонённый не попадает в отправку |

### Рекламодатели и onboarding (campaign_manager / system_admin / публичный лид / advertiser)

| № | Story | Journey | Цель | Ожидаемо |
|---|---|---|---|---|
| S08 | US-ADV-002 | `advertiser.apply` → `advertiser.application_review` → `advertiser.create_org` → `advertiser.legal_requisites` → `advertiser.contact_crud` → `advertiser.brand_crud` → `advertiser.invite` → `self.login` | Провести нового рекламодателя от публичной заявки до входа в кабинет | Заявка → одобрение → организация с реквизитами/контактом/брендом → приглашение → вход по приглашению в advertiser-портал `:3001` и свой workspace |
| S09 | US-ADV-003 | `advertiser.contract_crud` | Завести договор и приложить PDF | Договор в списке с файлом и статусом; после перезагрузки на месте |
| S10 | US-ADV-001 | `advertiser.view`, `self.campaign_view`, `self.apply_or_brief` | Как менеджер — открыть карточку рекламодателя; как рекламодатель — увидеть свои кампании и подать бриф | Карточка со всеми вкладками; в кабинете `CAMP-2026-001` с периодом; бриф отправлен. `self.report_view` — **не проходится** (blocked) |

### Администратор системы (system_admin)

| № | Story | Journey | Цель | Ожидаемо |
|---|---|---|---|---|
| S11 | US-ADM-001/002 | `user.create_advertiser`, `user.assign_roles`, `user.reset_password`, `user.deactivate`, `user.split_internal_advertiser` | Завести пользователя, назначить роли (виден каталог permission с описаниями), сбросить пароль, деактивировать; отличить внутренних от рекламодателей | Роли сохранены и видны после перезагрузки и в аудите; OTP выдан без «[object Object]»; статус «Неактивен» |
| S12 | — | `adsettings.test`, `adsettings.configure` | Проверить подключение AD и сохранить настройки | В DEV честный результат `not_configured` без секретов; сохранение подтверждено |
| S13 | — | `system.theme_switch` | Переключить тему на тёмную и пройти S01–S03 в ней | Тёмная тема без нечитаемых элементов (style-tokens: dark mode человеком не проверялся) |

### Безопасность и эксплуатация (security_admin / ops_operator)

| № | Story | Journey | Цель | Ожидаемо |
|---|---|---|---|---|
| S14 | US-EMR-001 | `emergency.activate`, `emergency.deactivate` | Экстренно остановить показ и снять режим | Подтверждение перед активацией; состояние видно в шапке/разделе; оба события в аудите |
| S15 | US-SEC-001 (baseline) | `audit.view` | Найти в журнале события S14 и смену ролей S11 | Действие, исполнитель, ресурс, время; фильтр находит события. Критичный фильтр/SIEM-экспорт — PENDING-ID `security.review` |
| S16 | US-OPS-001 | `device.health_view` | Оценить состояние парка | `KSO-001`, health-бейдж, heartbeat, версии; данные сохраняются при повторном входе |

### Коммерция (campaign_manager)

| № | Story | Journey | Цель | Ожидаемо |
|---|---|---|---|---|
| S17 | US-COM-001 | `commerce.tariff_manage`, `commerce.price_list_manage`, `commerce.order_create`, `commerce.offer_generate`, `commerce.booking`, `commerce.payment_status`, `commerce.order_close` | Провести заказ от тарифа до закрытия | Версия прайс-листа; заказ draft → offered → booked; статус оплаты; закрытие; каждый переход — в аудите |

## 3. Что в этот прогон не входит

- **Service-фичи без UI** (9 reachable): `manifest.deliver`, `pop.ingest`, `device.heartbeat`, `backup.restore`,
  `observability`, `campaign.complete`, `license.enforce/seat_release/report` — доказываются behavioral-тестами.
- **Blocked в registry** (21): `analytics.compare`, `attribution.lift_report`, `campaign.competitive_separation/readiness/schedule`,
  `content.dynamic_binding`, `device.onboard` (RM-TECH-210), `experiment.evaluate`, `field_ops.device_confirm`, `finance.exchange/reconcile`,
  `integration.reconcile`, `kpi.review`, `license.view/upload`, `placement.audience_targeting`, `playlist.build`, `release.rollback`,
  `rollout.rollback`, `self.report_view`, `self.campaign_create` — нет UI до задач roadmap.
- **PENDING-ID без canonical** (8, решение владельца): `audit.compare`, `campaign.underdelivery`, `carrier.manage`, `channel.register`,
  `channel.rendition_validate`, `data.catalog`, `inventory.priority`, `security.review`.

## 4. Как фиксируется результат

1. Оператор пишет одной строкой в `PROJECT_STATE.md`: `operator walkthrough: OK` или
   `operator walkthrough: замечания <перечень S-номеров>` — с SHA контура и датой.
2. Claude Code после этого (и только после) вносит evidence: `RM-UX-007.evidence_refs` kind `operator_walkthrough`
   (`ref` = запись `docs/audit/<дата>-operator-walkthrough-dev.md` со скриншотами), в карте требований —
   evidence kind `human_walkthrough` у затронутых REQ; registry-статусы не меняются (reachable = UI-smoke).
3. Замечания превращаются в задачи roadmap (стадия U) — статусы `done`/`APPROVED` без UI-smoke и walkthrough не ставятся.

# Программа до-пилотных бизнес-журнеев (КСО, ручной проход)

> **Канон для Codex/Hermes.** Источник истины по статусам — `docs/product/feature-registry.yaml` + зелёный UI-smoke; эта программа задаёт ПОРЯДОК закрытия.
> Обновлено 2026-08-21 (ROADMAP-RELEASE-SYNC-002 — release decision prep). Wave 1–6: ✅ COMPLETE.
> Текущие counts (feature-registry.yaml): **58 total / 52 reachable / 6 blocked** (admin-web 39, advertiser-web 5, public 1, service 13).
> После R3 (main 96b5159, 2026-07-28) закрыты: Commerce Contour 2 (7 reachable), advertiser onboarding (legal/brand/contract/contact), system.theme_switch, campaign.complete, RLS/pricing hardening, CI truth/stability (UI-SMOKE-STABILITY-004), EPIC-L Layer 1 (A1+A2+A3+A4 → license.enforce/seat_release/report reachable).

## Цель и принцип

Владелец хочет **пройти весь пилот на 1 КСО руками через UI, а не скриптами**: регистрация рекламодателя → бриф → создание кампании → загрузка креатива → модерация → согласование → публикация → показ → отчёт. Поэтому:

1. **Сначала — весь до-плеерный бизнес-поток кликабельным.** Каждый журней закрывается как **Бэкенд + UI + Юзер-стори** (4 колонки ДК, Итог=Готово только при всех трёх зелёных) с зелёным UI-smoke по Done Gate. Guard (ROADMAP-GUARD-002) защищает от занижения/завышения.
2. **PLAYER-001 — ПОСЛЕ волны 6.** Плеер не начинаем, пока до-плеерный поток не кликабелен end-to-end.
3. **Governance заморожена.** Никакой новой меты (флип guard в blocking — потом). Только журнеи.
4. Порядок волн = порядок ручного прохода пилота. Внутри волны — сверху вниз.
5. **Managed-first.** Приоритет — admin-web операции (оператор/администратор управляет рекламодателями). Self-service откладывается на более поздние волны, если не переутверждено владельцем.

Легенда: 🟢 reachable+smoke · 🔴 blocked · ⚙ есть реальный бэкенд-пробел (не только проводка UI).

---

## Волна 1 — Актёры и вход (кем и куда заходить) ✅ COMPLETE

R2 выпущен: main b5dd3b3, tag v0.9.0-prepilot-wave1, CI #29937353570.

- 🟢 `user.assign_roles` — назначить роли (G2)
- 🟢 `advertiser.create_org` — создать организацию рекламодателя (G3)
- 🟢 `self.login` — вход рекламодателя в кабинет (JOURNEY-004)
- 🟢 `advertiser.apply` — публичная заявка на подключение (JOURNEY-001)
- 🟢 `advertiser.application_review` — рассмотреть заявку (JOURNEY-002)
- 🟢 `advertiser.invite` — пригласить рекламодателя (JOURNEY-003)
- 🟢 `user.create_advertiser` — завести локального рекламодателя (JOURNEY-005)
- 🟢 `advertiser.view` — карточка рекламодателя (JOURNEY-006)

## Волна 2 — Бриф и настройка рекламы (managed-first) ✅ COMPLETE

- 🟢 `campaign.create` — создание кампании (G1)
- 🟢 `self.apply_or_brief` — бриф из кабинета рекламодателя (JOURNEY-007)
- 🟢 `campaign.edit` — рейсы/размещение как объект (JOURNEY-008)
- 🟢 `creative.upload` — загрузка креатива (JOURNEY-009)
- 🟢 `inventory.simulate` — прогноз показов / симуляция перед публикацией (JOURNEY-010)
- 🔴 `self.campaign_create` — рекламодатель сам заводит кампанию (отложено: self-service — после managed-core)

## Волна 3 — Модерация и согласование ✅ COMPLETE

- 🟢 `creative.moderate_approve` — одобрить креатив (JOURNEY-011)
- 🟢 `creative.moderate_reject` — отклонить креатив с причиной (JOURNEY-011)
- 🟢 `campaign.submit` — отправить кампанию на согласование (JOURNEY-012)
- 🟢 `campaign.approve` — одобрить кампанию (JOURNEY-013)
- 🟢 `campaign.reject` — отклонить кампанию с причиной (JOURNEY-013)

## Волна 4 — Публикация и управление показом ✅ COMPLETE

- 🟢 `campaign.activate` — запустить одобренную кампанию (публикация → manifest) · JOURNEY-014 + FU2
- 🟢 `campaign.pause` — приостановить активную кампанию · JOURNEY-014 + FU2
- 🟢 `emergency.activate` — экстренно остановить показ · JOURNEY-015
- 🟢 `emergency.deactivate` — снять аварийный режим · JOURNEY-015

## Волна 5 — Статус и мониторинг

- 🟢 `self.campaign_view` — рекламодатель видит свои кампании · JOURNEY-016
- 🟢 `device.health_view` — состояние парка устройств · JOURNEY-017
- 🟢 `audit.view` — журнал аудита · JOURNEY-018
- 🔴 `self.report_view` — отчёт план/факт (PoP) в кабинете · *BLOCKED: devices.manage не в seed, нет onboarding code → нет PoP данных → UI не построен. Данные появятся после PLAYER-001.*

## Волна 6 — Админ-доводка ✅ COMPLETE

- 🟢 `adsettings.configure` — сохранить настройки AD (G4)
- 🟢 `adsettings.test` — проверить подключение AD · JOURNEY-020
- 🟢 `user.reset_password` — сбросить пароль · JOURNEY-021
- 🟢 `user.deactivate` — заблокировать пользователя · JOURNEY-022
- 🟢 `inventory.rule_create` — создать правило инвентаря · JOURNEY-023

Закрыто: 4/4 journeys 🟢.

### Readiness statement (ROADMAP-RELEASE-SYNC-002)

Текущая база: **58 total / 49 reachable / 9 blocked**. `reachable` = зелёный UI-smoke (UI-фичи) или зелёный behavioral proof (service-фичи). Это **«функция достижима»**, а НЕ «pilot-ready» и НЕ «production-ready» — три разных понятия (см. ниже).

- ✅ **Admin-web (managed):** 39 фич reachable — кампании (create/edit/submit/approve/reject/activate/pause/complete), креативы (upload/moderate), инвентарь (simulate/rule_create), пользователи/роли, рекламодатели (организации + бренды + договоры + контакты + юр-реквизиты), AD-настройки, аудит, устройства, emergency, коммерция (тарифы/заказы/бронирование/оплата), тема (light/dark).
- ✅ **Public:** заявка рекламодателя reachable (1/1).
- ✅ **Advertiser-web (self-service):** login, просмотр кампаний, бриф — reachable (3/5).
- ✅ **Service:** manifest, PoP, device onboard/heartbeat, observability, campaign.complete — reachable (6/13, остальные service blocked).
- 🔴 **self.report_view:** blocked — UI не построен, PoP-данные отсутствуют. Разблокируется через player/PoP data path.
- ⏸️ **self.campaign_create:** deferred managed-first (P2).
- 🔴 **playlist.build, backup.restore:** service-deferred.
- 🟢 **license.* Layer 1 (3 reachable):** `license.enforce` (enrollment choke-point, A1+A2), `license.seat_release` (decommission release, A3), `license.report` (report API + reconciliation, A4) — behavioral/concurrency/tamper proof готовы.
- 🔴 **license.view / license.upload:** Layer 2 (signed-license/UI) — не реализованы.

### Три разных понятия готовности

1. **feature reachable** — есть зелёный UI-smoke (реальные клики) или behavioral proof (service). Нижняя планка; НЕ означает готовность к пилоту.
2. **pilot-ready** — сверх reachable нужен явный deployed SHA, backup/rollback, migration rehearsal, operator walkthrough и целевое окружение.
3. **production-ready** — сверх pilot-ready: реальный KSO proof, backup.restore, HA/load acceptance и формализованный deployment process.

**Решение:** PLAYER-001B-FU closed as hardware-independent contract proof (signed manifest, heartbeat, PoP accepted). **KSO-ENV-001 next** — real Sherman-J/KSO environment audit before any kiosk or scheduler code. PLAYER-001C/media playback deferred until real hardware environment is known.

---

## После волны 6 — KSO-ENV-001 next (OWNER-DECISION-001)

Решение владельца: **KSO-ENV-001 first.** Реальный КСО-плеер требует аудита реального Sherman-J/KSO (ОС, Chromium/kiosk, autostart, storage, сеть, codecs, update model). PLAYER-001B-FU доказал, что платформенные контракты работают (manifest+подпись, heartbeat, PoP). PLAYER-001C scheduler отложен до получения реальных данных о среде.

- `self.report_view` остаётся 🔴 blocked — разблокируется через player/PoP data path, не через искусственный report workaround.
- `self.campaign_create` остаётся deferred managed-first (P2).
- Pre-player managed admin-flow (49/58 reachable) закрыт — достаточно кликабелен для перехода к player integration.

**Оставшиеся blocked:**
- `self.report_view` 🔴 — blocked by PoP/player/data path (JOURNEY-019-DISCOVERY)
- `self.campaign_create` — deferred managed-first (P2)
- Service deferred: `playlist.build`, `backup.restore`
- License (EPIC-L): Layer 1 closed — A1 (ledger) + A2 (enrollment) + A3 (decommission) + A4 (report + reconciliation) complete. `license.enforce`, `license.seat_release`, `license.report` reachable. Layer 2 (view/upload signed-license/UI) pending — `license.view`, `license.upload` blocked.

## Правила ведения (для каждого журнея)
- Done = поведение: достижимый UI (реальные клики, `goto` только `/login`) + зелёный `test_uismoke__<domain>__<action>`.
- В ДК поднять 3 колонки (Бэкенд/UI/Юзер-стори) и пересчитать Итог; guard ROADMAP-GUARD-002 обязан оставаться зелёным.
- Одна задача Hermes за раз. ⚙-журнеи требуют реального бэкенда — не «просто кнопки».
- Прогресс мерить по этой программе: 52/58 reachable (6 blocked). Wave 1–4: 22/23 closed (self.campaign_create deferred); Wave 5: 3/4 (self.report_view blocked); Wave 6: 4/4 ✅; +7 commerce reachable; +4 advertiser onboarding reachable; +1 theme; +3 license reachable (EPIC-L Layer 1). UX-hardening (CAMPAIGN-UX-001A/B, UX-FIX-002) и CI/stability (UI-SMOKE-STABILITY-004) — улучшение существующих reachable-фич, не новые журнеи.

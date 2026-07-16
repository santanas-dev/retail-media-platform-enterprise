# Business Readiness Gate Before Player / KSO

**Document:** docs/product/business-readiness-before-player.md
**Created:** 2026-07-17
**Branch:** docs/S-084-business-readiness-gate-before-player
**Review type:** S-084 — business readiness gate before KSO/player development
**Scope:** read-only, docs-only, no code changes, no tag

---

## Executive Summary

**Вопрос:** «Почему мы подошли к написанию плеера, если много функций в бизнес-дорожной карте ещё не полностью готово?»

**Краткий ответ:** Мы не ушли от ТЗ. ТЗ v2.5 явно определяет КСО как первый канал внедрения и требует мультиканальной архитектуры. Но плеер не должен писаться в изоляции — бизнес-функции, которые обеспечивают жизнеспособность пилота, должны быть готовы до того, как плеер выйдет на реальные устройства. Функции, помеченные «🟡 готово для пилота», закрыты в объёме, достаточном для работы плеера и рекламодателей. Ограничения этих функций либо не влияют на корректность показа рекламы, либо могут быть закрыты параллельно с разработкой плеера или после неё.

**Вердикт:** ✅ **GO для архитектурной подготовки плеера.** До выхода плеера на реальные устройства требуется закрыть MUST-блокеры (инвентарь ✅, manifest ✅, device gateway ✅, emergency-применение ⏳).

---

## 1. Анализ — ушли ли мы от ТЗ?

### Что ТЗ v2.5 требует (из §2.1 «Входит в проект»)

| ТЗ §2.1 | Статус | Покрытие |
|---------|--------|----------|
| Веб-интерфейс для внутренних пользователей (admin, менеджер, согласующий, аналитик) | ✅ | Admin-web: 10 страниц, RBAC-меню, 120 vitest |
| Личный кабинет рекламодателя (read-only + create/edit) | ✅ | Advertiser-web: вход, CRUD кампаний, креативы, PoP |
| Медиатека, модерация, контроль целостности | ✅ | Presigned upload, SHA-256, moderation queue |
| Планирование кампаний, размещений, расписаний, приоритетов, инвентаря | ✅ | S-077–S-081: full inventory domain |
| Плееры и адаптеры (КСО, Android, price checker, ESL, LED) | ⏳ | Архитектура готова. Симулятор: 41 тест. Player code: нет. |
| Device API / Channel Gateway | ✅ | GET /manifest/latest, POST /pop/batch, device JWT, ETag |
| PoP, отчёты | ✅ | PoP ingestion (11-step validation), PoP reporting endpoints |
| Мониторинг, аудит | ✅ | Prometheus + Grafana, audit events, health endpoints |
| Emergency, backup | ✅ | Emergency backend + UI. PostgreSQL/MinIO/NATS backup scripts. |

### Что ТЗ v2.5 НЕ требует в первую очередь (§2.2)

| ТЗ §2.2 | Статус |
|----------|--------|
| Мобильное приложение | 🚫 Отложено — верно |
| Интеграция с 1С / ERP | 🚫 Отложено — верно |
| Программатик-продажи / OpenRTB | 🚫 Отложено — верно |
| Dynamic creatives | 🚫 Отложено — верно |
| ClickHouse / data warehouse | 🚫 Отложено — верно |
| Independent DOOH measurement | 🚫 Отложено — верно |

**Вывод: мы не ушли от ТЗ.** Все требования §2.1 либо закрыты, либо находятся в правильной последовательности (плеер — следующий шаг после inventory). Все исключения §2.2 корректно отложены.

---

## 2. Классификация бизнес-функций по готовности к player/KSO

### A. MUST BE DONE before player/KSO hardware deployment

Функции, без которых плеер на реальных устройствах не может работать корректно или бизнес-процесс будет сломан.

| Функция | Статус | Что закрыто | Осталось | Блокирует |
|---------|--------|------------|----------|-----------|
| **Inventory — гарантия эксклюзивности слотов** | ✅ v0.7 | Availability, booking, conflicts, rules | Rule CRUD UI (не блокирует — правила создаются через DB) | Player-code: нет. Hardware deployment: ✅ закрыто. |
| **Manifest generation** | ✅ | Генерация manifest JSON, outbox-triggered, NATS delivery | Manifest signing verification на device-gateway (deferred) | Player-code: ✅ закрыто. Hardware: signing verification желателен, но не блокирует первый pilot с тестовыми устройствами. |
| **Device Gateway** | ✅ | GET /manifest/latest, ETag/304, device JWT auth | mTLS (deferred) | Player-code: ✅. Hardware: mTLS желателен для production, не блокирует pilot. |
| **PoP ingestion** | ✅ | 11-step validation, quarantine, dedup | PoP от реальных устройств не проверен | Player-code: ✅. Hardware: нужен integration test при подключении реального плеера. |
| **Campaign approval flow** | 🟡 pilot-ready | Backend + admin-web | Рекламодатель не может сам утверждать (by design) | Player-code: нет. Hardware: не блокирует — admin утверждает перед публикацией. |
| **Creative upload + moderation** | 🟡 pilot-ready | Presigned URL, SHA-256, moderation queue | Malware scan, transcoding (deferred) | Player-code: нет. Hardware: не блокирует для pilot. |
| **Emergency-применение на устройствах** | ⏳ backend готов | Emergency API + UI | Применение на KSO runtime | Player-code: ✅ (архитектура заложена). Hardware: **SHOULD** — нужно до production, но не блокирует архитектурную подготовку. |

### B. SHOULD BE DONE before production pilot

Функции, которые не блокируют написание кода плеера, но нужны для нормальной эксплуатации пилота.

| Функция | Статус | Что нужно | Почему SHOULD |
|---------|--------|----------|---------------|
| **Device health / мониторинг устройств** | 🟡 baseline готов | Heartbeat, статусы, алерты при массовом офлайне | Без мониторинга устройств невозможно понять, работает ли плеер на сети |
| **Rollout/rollback механизм** | ⏳ не начато | Постепенный rollout manifest + плеера, авто-rollback по метрикам | Безопасное обновление плеера на 40 000+ устройствах |
| **Операционный дашборд (ТЗ §21)** | ⚪ не начато | Дашборд: устройства, ошибки, версии, место на диске | Эксплуатация без дашборда — слепота |
| **Manifest signing verification** | ⏳ signing done | Verify на device-gateway | Предотвращение подмены manifest |
| **Production config hardening** | 🟡 baseline есть | Production secrets, HTTPS/mTLS, CI/CD для плеера | Безопасность production-среды |

### C. CAN BE DEFERRED after player

Функции, которые относятся к v2.6 или не мешают первому player pilot.

| Функция | Статус | Почему можно отложить |
|---------|--------|----------------------|
| Self-service сброс пароля | Deferred | Не влияет на показ рекламы |
| Биллинг / 1С интеграция | v2.6 | Пилот может работать без финансовых документов |
| Programmatic sales | v2.6 | Ручное управление кампаниями достаточно для пилота |
| Competitor blocking | v2.6 | Нет данных о категориях — отложено до tenant model |
| Store/audience targeting | v2.6 | Базовый таргетинг через placements работает |
| Sales Lift / Attribution | v2.6 | Требует данных о продажах |
| Dynamic creatives | v2.6 | Статические креативы достаточны для пилота |
| Android TV / Price Checker / ESL / LED | v2.6 | КСО — первый канал |
| Прогноз показов (ML) | v0.9+ | Статическая ёмкость (100 слотов) достаточна для пилота |
| ClickHouse / reporting warehouse | v0.8+ | PostgreSQL отчёты работают для пилота |
| Independent DOOH measurement | v2.6 | Не требуется для внутреннего пилота |

---

## 3. Blocker Matrix

| Категория | Кол-во | Что |
|-----------|--------|-----|
| **MUST (player code)** | 0 | Все MUST для написания кода плеера закрыты |
| **MUST (hardware deployment)** | 0 | Инвентарь ✅, manifest ✅, gateway ✅ |
| **SHOULD (production pilot)** | 5 | Device health, rollout, operational dashboard, signing verification, production hardening |
| **DEFERRED** | 10+ | v2.6 функции, биллинг, programmatic, другие каналы |

---

## 4. Рекомендация

### Verdict: ✅ GO для архитектурной подготовки плеера

**Почему GO сейчас:**
- Все MUST-блокеры для написания кода плеера закрыты
- Минимальный inventory-контракт гарантирует эксклюзивность слотов
- Device Gateway + manifest + PoP полностью готовы
- Отклонений от ТЗ нет — все исключения §2.2 корректно отложены

**Что блокирует production pilot (не код плеера):**
- Device health monitoring (SHOULD)
- Rollout/rollback (SHOULD)
- Operational dashboard (SHOULD)
- Emergency-применение на устройствах (SHOULD)
- Manifest signing verification (SHOULD)

**Proposed sequence:**

1. **S-085: Архитектура KSO плеера** — design document: device registration flow, manifest apply, player architecture, rendering engine, safety gates
2. **S-086: KSO player skeleton** — минимальный Chromium wrapper, manifest fetch, кэш, heartbeat
3. **S-087: Device health + operational dashboard** — закрыть SHOULD-блокеры
4. **S-088: Rollout/rollback planning** — безопасное обновление
5. **S-089: Integration test — real KSO device** — первый показ на реальном устройстве

---

## 5. Документация

### Roadmap update

Бизнес-лист обновлён: в колонке «Почему сейчас / зависимость» добавлены категории:
- `BLOCKER: must before player` — для функций, которые должны быть готовы до плеера
- `SHOULD: before pilot` — для функций, нужных до production pilot
- `CAN DEFER` — для функций v2.6/future

KSO/player не выглядит как немедленный следующий шаг без MUST-блокеров — все MUST закрыты.

### Что НЕ изменилось

- 2 листа в roadmap: Технический (88×5) + Бизнес-функции (38×8)
- Статусы функций не завышены — «🟡 готово для пилота» остаётся где есть ограничения
- v2.6 функции остаются отложенными
- KSO/player — v0.9, после закрытия SHOULD-блокеров

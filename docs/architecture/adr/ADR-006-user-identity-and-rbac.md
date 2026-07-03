# ADR-006: User Identity and RBAC

**Status:** Accepted
**Date:** 2026-07-02
**Phase:** 3.1 (Auth/RBAC Architecture Lock)
**Deciders:** Sergey Paschenko (project owner), Hermes Agent

## Context

ТЗ v2.5 §14 требует: «Аутентификация пользователей — AD/SSO, MFA для критичных ролей». `rmp_rewrite_starting_decisions.md` фиксирует: «AD integration is required. Local users are only break-glass/admin fallback». `rmp_enterprise_architecture_review.md` уточняет: «административный доступ только из корпоративной сети/VPN через AD/SSO/MFA».

В отличие от ТЗ, где «пользователь» — одно понятие, платформа обслуживает три разных типа identity:

1. **Внутренний персонал** (admin, менеджеры, аналитики, согласующие) — аутентификация через корпоративный AD.
2. **Рекламодатели** (advertiser cabinet users) — локальная аутентификация с email/password, собственный lifecycle.
3. **Break-glass администраторы** — аварийный локальный доступ при недоступности AD.

Phase 2.1 создала identity-схему: `users` (с `auth_provider`, `external_subject`, `is_break_glass`), `roles`, `permissions`, `role_permissions`, `user_roles` (scoped), `access_scopes`, `user_access_scopes`, `audit_events_operational`. Phase 3.0 добавила read-only identity endpoint'ы без аутентификации.

Остаётся открытым вопрос из `rmp_rewrite_starting_decisions.md`: «Exact AD protocol: LDAP bind, SAML, OIDC, Kerberos or corporate proxy». Этот ADR закрывает его, разделяет identity-типы и фиксирует модель сессий, RBAC enforcement и требования к аудиту.

## Decision

### 1. Identity Types

Платформа поддерживает три типа identity, различаемых по `users.auth_provider`:

| Тип | `auth_provider` | Источник | Аутентификация | Жизненный цикл |
|-----|-----------------|----------|----------------|----------------|
| Internal staff | `ad` | Active Directory | LDAPS bind/search | Управляется через AD; RMP синхронизирует атрибуты при входе |
| Advertiser user | `local_advertiser` | RMP (локально) | Email + bcrypt password | Самостоятельная регистрация / приглашение, сброс пароля |
| Break-glass admin | `local_break_glass` | Seed/миграция (вручную) | Локальный bcrypt-хэш | Только аварийный доступ; не более 2 пользователей |

**Все три типа** хранятся в одной таблице `users`. Разделение — через `auth_provider` и связанные таблицы (`advertiser_organizations` — будущая, `local_credentials` — будущая).

### 2. Internal Staff — AD/LDAPS

**Протокол: LDAP bind/search.**

| Протокол | Требования | Доступность | Выбран |
|----------|-----------|-------------|:------:|
| LDAP bind/search | AD-контроллер, порт 389/636 (LDAPS) | Любой AD из коробки | ✓ |
| Kerberos/Negotiate | Членство в домене, keytab, SPN | Требует настройки доменной учётки сервиса | ✗ |
| OIDC через AD FS/Azure AD | Развёрнутый AD FS или Azure AD tenant | Не подтверждено наличие | ✗ |

**Обоснование:** LDAP bind/search — единственный протокол, работающий с любым корпоративным AD без дополнительной инфраструктуры. Сервис выполняет `ldap bind` с DN пользователя + пароль, затем `search` для извлечения групп и атрибутов. Пароль не сохраняется — только верифицируется через LDAP и немедленно отбрасывается.

**LDAPS обязателен** (LDAP over TLS, порт 636). Plain LDAP (порт 389) не допускается в production.

**Маппинг AD → RMP:**
- `username` → `sAMAccountName`
- `display_name` → `displayName`
- `email` → `mail`
- `external_subject` → `objectSid` (SID в строковом представлении, например `S-1-5-21-...`)
- Группы AD → роли RMP (настраиваемый mapping в конфигурации)

**Поведение при недоступности AD:**

При недоступности LDAP-сервера (connection timeout, bind failure, TLS error):
- `POST /api/v1/auth/login` с `auth_provider=ad` → **503 Service Unavailable**
- Тело ответа: `{"error": {"code": "AUTH_PROVIDER_UNAVAILABLE", "message": "Identity provider temporarily unavailable"}}`
- Audit event: `auth.login.failure`, `reason=ldap_unavailable` (без username — AD-бекенд не вернул данные)
- **Только break-glass-пользователи сохраняют возможность входа**
- Повторные попытки AD-входа не блокируют пользователей (rate limit применяется, но не постоянный lockout — проблема на стороне провайдера, не пользователя)

### 3. Advertiser User — Local Auth

**Email + password, локальная аутентификация.** Это самостоятельный тип пользователей, не связанный с AD.

**Модель хранения (будущая таблица `local_credentials`):**

```
local_credentials
┌──────────────────────────┐
│ id (UUID)                │
│ user_id FK → users.id    │
│ password_hash (bcrypt)   │
│ password_updated_at      │
│ mfa_secret (nullable)    │  — TOTP seed, encrypted
│ mfa_enabled (bool)       │
│ email_verified (bool)    │
│ email_verify_token       │  — одноразовый, TTL 24h
│ email_verified_at        │
│ reset_token_hash         │  — SHA-256 одноразового токена
│ reset_token_expires_at   │
│ failed_attempts (int)    │
│ locked_until (nullable)  │
│ created_at               │
│ updated_at               │
└──────────────────────────┘
```

**Почему отдельная таблица, а не колонки в `users`:**
- `users` — общая таблица для всех identity-типов. Колонки специфичные для локальной аутентификации (password_hash, mfa_secret, reset tokens) не должны быть у AD-пользователей.
- Отдельная таблица позволяет `local_credentials` иметь собственные constraint'ы (уникальность на user_id) и не загрязнять общую модель.

**Требования к безопасности:**
- **Password hash:** bcrypt с cost factor ≥ 12. Никогда не plaintext.
- **Password reset:** через email-токен (одноразовый, TTL 15 минут), не через секретные вопросы.
- **MFA-ready:** колонка `mfa_secret` зарезервирована для TOTP (RFC 6238). Реализация — после подтверждения механизма.
- **Email verification-ready:** токен + `email_verified` флаг. При регистрации email считается неподтверждённым до верификации.
- **Rate limit:** 5 неудачных попыток на email за 15 минут. После превышения — временная блокировка на 15 минут (`locked_until`). Не постоянный lockout.
- **No user enumeration:** ошибки входа и сброса пароля универсальны — «Invalid email or password» / «If this email is registered, a reset link has been sent». Никаких «User not found» vs «Wrong password».
- **Все попытки аудируются:** `auth.login.success`, `auth.login.failure`, `auth.password_reset.requested`, `auth.password_reset.completed`.

### 4. Break-Glass Local Admin

**Разрешён только для аварийного доступа и начального bootstrap.**

Правила:
- `auth_provider = "local_break_glass"` и `is_break_glass = true` — только вручную через seed/миграцию, не через API
- **Текущий seed** (`seed.py`) создаёт break-glass-пользователя **без пароля** — record only. Полноценный вход невозможен до миграции, добавляющей `local_credentials`.
- **Каждый вход break-glass генерирует audit event уровня CRITICAL** — включая actor, IP, reason
- Break-glass не может отключить аудит или изменить audit events задним числом
- Максимум 1–2 break-glass-пользователя на весь тенант
- В production break-glass-пароль хранится в физическом сейфе/менеджере секретов, не в коде

**Не допускается:** обычные локальные пользователи (не break-glass) для повседневной работы. Все штатные сотрудники — только через AD/LDAP.

### 5. Session / Token Model

**JWT access token (15 min) + opaque refresh token (8 h) в HttpOnly Secure SameSite cookie.**

Единая сессионная модель для всех identity-типов. JWT-claims включают `auth_provider`, что позволяет endpoint'ам различать тип пользователя при необходимости.

```
POST /api/v1/auth/login
  → определение auth_provider (из тела запроса или определения по username/email)
  → валидация через LDAPS (ad) или bcrypt (local_advertiser / local_break_glass)
  → создание сессии в Redis
  → ответ: Set-Cookie с refresh_token (HttpOnly; Secure; SameSite=Strict; path=/api/v1/auth)
           + JSON body: { access_token, expires_at, user }
```

| Параметр | Значение | Обоснование |
|----------|----------|-------------|
| Access token TTL | **15 минут** | Короткий TTL — компромисс между безопасностью и нагрузкой на провайдер. Соответствует device JWT из ADR-003. |
| Refresh token TTL | **8 часов** (рабочий день) | Перевыпуск без повторной аутентификации. Инвалидируется при logout. |
| Refresh token rotation | **Да** — старый инвалидируется при использовании | Защита от replay refresh token. |
| Token storage (SPA) | **HttpOnly cookie** для refresh; access token в памяти JS | Никогда в `localStorage`, `sessionStorage` или URL. |
| Redis session store | Ключ: `session:<session_id>`, TTL = refresh TTL | Хранит: user_id, auth_provider, roles, scopes, issued_at. |

**SPA flow:**
1. `POST /api/v1/auth/login` → получает access_token в JSON + refresh_token в Set-Cookie
2. Все API-запросы: `Authorization: Bearer <access_token>`
3. Когда access_token истекает → `POST /api/v1/auth/refresh` (cookie отправляется автоматически) → новый access_token
4. Logout: `POST /api/v1/auth/logout` → инвалидация refresh token в Redis, очистка cookie

### 6. RBAC Enforcement Model

**Server-side only. Deny by default.**

Принципы:
- **Каждый эндпоинт требует явного permission.** Если permission не указан — 403.
- **Permissions — строковые коды** (напр. `users.read`, `campaigns.manage`), не роли. Роли — группы permissions.
- **RLS через access_scopes:** глобальный (`scope_type=global`), филиал (`branch`), кластер (`cluster`), магазин (`store`).
- **Проверка scope:** middleware извлекает user_id из JWT → загружает permissions + scopes из Redis/cache → проверяет доступ к запрошенному ресурсу.
- Advertiser-пользователи автоматически ограничены scope своего рекламодателя — не могут видеть чужие кампании.
- **Нет frontend-only авторизации.** Скрытие кнопок в UI — usability, не безопасность. Все проверки дублируются на сервере.

**Модель enforcement (Phase 3.2+):**

```python
# FastAPI dependency
async def require_permission(perm: str, scope_type: str | None = None):
    def dependency(user = Depends(get_current_user)):
        if perm not in user.permissions:
            raise HTTPException(403, detail="Permission denied")
        if scope_type and not user.has_scope(scope_type):
            raise HTTPException(403, detail="Scope restricted")
        return user
    return dependency
```

### 7. Audit Requirements

**Все события аутентификации и авторизации пишутся в `audit_events_operational`.**

| Событие | Action | Уровень | Обязательные поля |
|---------|--------|---------|-------------------|
| Успешный вход (AD) | `auth.login.success` | INFO | actor_user_id, ip_address, auth_provider=ad |
| Успешный вход (advertiser) | `auth.login.success` | INFO | actor_user_id, ip_address, auth_provider=local_advertiser |
| Неудачный вход | `auth.login.failure` | WARN | details_json={username, reason}, ip_address |
| LDAP недоступен | `auth.login.failure` | ERROR | details_json={reason: ldap_unavailable}, ip_address |
| Выход | `auth.logout` | INFO | actor_user_id, details_json={session_id} |
| Отзыв сессии (admin) | `auth.session.revoke` | WARN | actor_user_id, target_user_id, reason |
| Permission denied | `auth.permission_denied` | WARN | actor_user_id, target_type=endpoint, target_id=path, details_json={required_permission} |
| Назначение роли | `rbac.role.assign` | INFO | actor_user_id, target_user_id, details_json={role_code, scope} |
| Снятие роли | `rbac.role.revoke` | INFO | actor_user_id, target_user_id, details_json={role_code} |
| Изменение scope | `rbac.scope.change` | INFO | actor_user_id, target_user_id, details_json={old_scope, new_scope} |
| Вход break-glass | `auth.break_glass.login` | **CRITICAL** | actor_user_id, ip_address, details_json={reason} |
| Запрос сброса пароля | `auth.password_reset.requested` | INFO | details_json={email_hash} — хэш email, не сам email |
| Сброс пароля выполнен | `auth.password_reset.completed` | INFO | actor_user_id |
| Rate limit сработал | `auth.login.rate_limited` | WARN | details_json={identifier_hash}, ip_address |

**Правила безопасности аудита:**
- Пароли не попадают в audit events, логи, `details_json` — никогда
- Токены не попадают в audit events — только факт выпуска/отзыва
- Email в audit events — только в хэшированном виде для неаутентифицированных событий
- Correlation ID (`X-Correlation-ID`) обязателен во всех audit events

### 8. Security Requirements

| Требование | Реализация |
|------------|------------|
| Пароли не в логах | Фильтрация на уровне middleware/formatter: маскирование полей `password`, `secret`, `token` |
| Токены не в URL | JWT — в `Authorization: Bearer`, refresh — в HttpOnly cookie. Никаких `?token=`. |
| Correlation ID | Обязателен во всех auth/audit событиях. Генерируется на входе (reverse proxy или middleware). |
| Rate limit login (AD) | **5 попыток на username за 15 минут.** После превышения — 429 + audit event `auth.login.rate_limited`. Redis-ключ: `ratelimit:login:ad:<username_hash>`, TTL = 15 min. |
| Rate limit login (advertiser) | **5 попыток на email за 15 минут.** После превышения — временная блокировка 15 минут (`locked_until` в `local_credentials`). |
| Rate limit password reset | **3 запроса на email за час.** Универсальное сообщение: «If this email is registered, a reset link has been sent». |
| Clock skew | JWT-валидация допускает расхождение часов до **30 секунд** (`leeway=30`). |
| Сессии | Не более 5 активных сессий на пользователя. При превышении — старейшая инвалидируется. |
| No user enumeration | Ошибки входа/сброса универсальны. Ответы с одинаковым статусом и телом для «нет пользователя» и «неверный пароль». |

### 9. Transition from Phase 3.0

**Phase 3.0 read-only `/api/v1/identity/*` endpoint'ы остаются незащищёнными до Phase 3.2 (auth middleware).**

В Phase 3.2:
- `GET /api/v1/identity/*` → требуется `users.read`, `roles.read`, `permissions.read`, `audit.read`
- Все не-health эндпоинты → требуется JWT
- `/health/live`, `/health/ready` → без аутентификации

### 10. Future DB Work (required before auth implementation)

Перед началом Phase 3.2 (auth implementation) необходимы следующие миграции:

| Миграция | Назначение | Таблица |
|----------|-----------|---------|
| `local_credentials` | Хранение bcrypt-хэшей, MFA-секретов, токенов сброса, счётчиков попыток | Новая |
| `advertiser_organizations` | Организации рекламодателей для advertiser cabinet | Новая |
| `user_advertiser_link` | Связь `users` ↔ `advertiser_organizations` (many-to-many или FK) | Новая |
| `refresh_sessions` | Persist refresh-токенов (дополнительно к Redis) для выживания при рестарте Redis | Новая (опционально) |
| `password_hash` в `users` | **Не добавлять.** Хранить в `local_credentials` | — |
| `mfa_secret` в `users` | **Не добавлять.** Хранить в `local_credentials` | — |
| Обновление seed | Добавить `local_credentials`-запись для break-glass-пользователя с bcrypt-хэшем | seed.py |

### 11. Future: MFA

MFA для критичных ролей (ТЗ §14) отложен до уточнения механизма со стороны AD/IdP. Варианты:
- OTP через корпоративный IdP (если AD FS с MFA-плагином)
- TOTP локально (RFC 6238) с seed в `local_credentials.mfa_secret` (encrypted)
- FIDO2/WebAuthn (если браузеры поддерживают)

Решение будет оформлено отдельным ADR при переходе к production.

## Consequences

- **Positive:** Три типа identity явно разделены; AD-атрибуты не смешиваются с локальными учётными данными; `local_credentials` — отдельная таблица безопасности без загрязнения общей модели `users`. LDAP — максимально совместимый протокол.
- **Negative:** LDAP bind означает, что сервис временно видит пароль пользователя (только в памяти, на время bind-операции). Три identity-типа усложняют login flow (диспетчеризация по `auth_provider`). Advertiser auth требует построения полного lifecycle (регистрация, верификация, сброс).
- **Risk:** Если корпоративный AD требует Kerberos/Negotiate и блокирует LDAP bind — потребуется миграция на Kerberos (дополнительный ADR). Текущая архитектура изолирует протокол за `auth_provider`-интерфейсом — замена протокола не затрагивает модели и endpoint'ы.

## References

- TZ v2.5 §14 (Security), §16.1 (API Groups), Table 20
- `rmp_rewrite_starting_decisions.md` — User identity: AD required, local break-glass only
- `rmp_enterprise_architecture_review.md` — AD/SSO, RBAC/RLS/audit
- ADR-003 (Device Identity) — device JWT model, token TTL, no tokens in URL
- `packages/domain/models.py` — identity tables (users, roles, permissions, access_scopes, audit_events_operational)
- `apps/control-api/seed.py` — break-glass admin seed (record only, no credential)
- `packages/api/identity.py` — Phase 3.0 read-only identity endpoints (unprotected)

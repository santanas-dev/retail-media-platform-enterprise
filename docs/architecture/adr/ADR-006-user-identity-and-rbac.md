# ADR-006: User Identity and RBAC

**Status:** Accepted
**Date:** 2026-07-02
**Phase:** 3.1 (Auth/RBAC Architecture Lock)
**Deciders:** Sergey Paschenko (project owner), Hermes Agent

## Context

ТЗ v2.5 §14 требует: «Аутентификация пользователей — AD/SSO, MFA для критичных ролей». `rmp_rewrite_starting_decisions.md` фиксирует: «AD integration is required. Local users are only break-glass/admin fallback». `rmp_enterprise_architecture_review.md` уточняет: «административный доступ только из корпоративной сети/VPN через AD/SSO/MFA».

Phase 2.1 создала identity-схему: `users` (с `auth_provider`, `external_subject`, `is_break_glass`), `roles`, `permissions`, `role_permissions`, `user_roles` (scoped), `access_scopes`, `user_access_scopes`, `audit_events_operational`. Phase 3.0 добавила read-only identity endpoint'ы без аутентификации.

Остаётся открытым вопрос из `rmp_rewrite_starting_decisions.md`: «Exact AD protocol: LDAP bind, SAML, OIDC, Kerberos or corporate proxy». Этот ADR закрывает его, а также фиксирует модель сессий, RBAC enforcement и требования к аудиту.

## Decision

### 1. Primary Identity Provider: Active Directory

**Протокол: LDAP bind/search.**

| Протокол | Требования | Доступность | Выбран |
|----------|-----------|-------------|:------:|
| LDAP bind/search | AD-контроллер, порт 389/636 (LDAPS) | Любой AD из коробки | ✓ |
| Kerberos/Negotiate | Членство в домене, keytab, SPN | Требует настройки доменной учётки сервиса | ✗ |
| OIDC через AD FS/Azure AD | Развёрнутый AD FS или Azure AD tenant | Не подтверждено наличие | ✗ |

**Обоснование:** LDAP bind/search — единственный протокол, работающий с любым корпоративным AD без дополнительной инфраструктуры. Сервис выполняет `ldap bind` с DN пользователя + пароль, затем `search` для извлечения групп и атрибутов. Пароль не сохраняется — только верифицируется через LDAP и немедленно отбрасывается.

**LDAPS обязателен** (LDAP over TLS, порт 636). Plain LDAP (порт 389) не допускается в production.

**Маппинг:**
- `username` → `sAMAccountName`
- `display_name` → `displayName`
- `email` → `mail`
- `external_subject` → `objectSid` (SID в строковом представлении)
- Группы AD → роли RMP (настраиваемый mapping в конфигурации)

### 2. Break-Glass Local Admin

**Разрешён только для аварийного доступа и начального bootstrap.**

Правила:
- `auth_provider = "local"` и `is_break_glass = true` — только вручную через seed/миграцию, не через API
- Break-glass-пользователь аутентифицируется локально (bcrypt-хэш, не LDAP)
- **Каждый вход break-glass генерирует audit event уровня CRITICAL** — включая actor, IP, reason
- Break-glass не может отключить аудит или изменить audit events задним числом
- Максимум 1–2 break-glass-пользователя на весь тенант
- В production break-glass-пароль хранится в физическом сейфе/менеджере секретов, не в коде

**Не допускается:** обычные локальные пользователи (не break-glass) для повседневной работы. Все штатные пользователи — только через AD/LDAP.

### 3. Session / Token Model

**JWT access token (15 min) + opaque refresh token (8 h) в HttpOnly Secure SameSite cookie.**

```
POST /api/v1/auth/login
  → валидация через LDAP bind
  → создание сессии в Redis
  → ответ: Set-Cookie с refresh_token (HttpOnly; Secure; SameSite=Strict; path=/api/v1/auth)
           + JSON body: { access_token, expires_at, user }
```

| Параметр | Значение | Обоснование |
|----------|----------|-------------|
| Access token TTL | **15 минут** | Короткий TTL — компромисс между безопасностью и нагрузкой на LDAP. Соответствует device JWT из ADR-003. |
| Refresh token TTL | **8 часов** (рабочий день) | Перевыпуск без повторного LDAP bind. Инвалидируется при logout. |
| Refresh token rotation | **Да** — старый инвалидируется при использовании | Защита от replay refresh token. |
| Token storage (SPA) | **HttpOnly cookie** для refresh; access token в памяти JS | Никогда в `localStorage`, `sessionStorage` или URL. |
| Redis session store | Ключ: `session:<session_id>`, TTL = refresh TTL | Хранит: user_id, roles, scopes, issued_at. |

**SPA flow:**
1. `POST /api/v1/auth/login` → получает access_token в JSON + refresh_token в Set-Cookie
2. Все API-запросы: `Authorization: Bearer <access_token>`
3. Когда access_token истекает → `POST /api/v1/auth/refresh` (cookie отправляется автоматически) → новый access_token
4. Logout: `POST /api/v1/auth/logout` → инвалидация refresh token в Redis, очистка cookie

### 4. RBAC Enforcement Model

**Server-side only. Deny by default.**

Принципы:
- **Каждый эндпоинт требует явного permission.** Если permission не указан — 403.
- **Permissions — строковые коды** (напр. `users.read`, `campaigns.manage`), не роли. Роли — группы permissions.
- **RLS через access_scopes:** глобальный (`scope_type=global`), филиал (`branch`), кластер (`cluster`), магазин (`store`).
- **Проверка scope:** middleware извлекает user_id из JWT → загружает permissions + scopes из Redis/cache → проверяет доступ к запрошенному ресурсу.
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

### 5. Audit Requirements

**Все события аутентификации и авторизации пишутся в `audit_events_operational`.**

| Событие | Action | Уровень | Обязательные поля |
|---------|--------|---------|-------------------|
| Успешный вход | `auth.login.success` | INFO | actor_user_id, ip_address, auth_provider |
| Неудачный вход | `auth.login.failure` | WARN | username (attempted), ip_address, reason (sanitized) |
| Выход | `auth.logout` | INFO | actor_user_id, session_id |
| Отзыв сессии (admin) | `auth.session.revoke` | WARN | actor_user_id, target_user_id, reason |
| Permission denied | `auth.permission_denied` | WARN | actor_user_id, endpoint, required_permission |
| Назначение роли | `rbac.role.assign` | INFO | actor_user_id, target_user_id, role_code, scope |
| Снятие роли | `rbac.role.revoke` | INFO | actor_user_id, target_user_id, role_code |
| Изменение scope | `rbac.scope.change` | INFO | actor_user_id, target_user_id, old_scope, new_scope |
| Вход break-glass | `auth.break_glass.login` | **CRITICAL** | actor_user_id, ip_address, reason |

**Правила безопасности аудита:**
- Пароли не попадают в audit events, логи, `details_json` — никогда
- Токены не попадают в audit events — только факт выпуска/отзыва
- Correlation ID (`X-Correlation-ID`) обязателен во всех audit events

### 6. Security Requirements

| Требование | Реализация |
|------------|------------|
| Пароли не в логах | Фильтрация на уровне middleware/formatter: маскирование полей `password`, `secret`, `token` |
| Токены не в URL | JWT — в `Authorization: Bearer`, refresh — в HttpOnly cookie. Никаких `?token=`. |
| Correlation ID | Обязателен во всех auth/audit событиях. Генерируется на входе (reverse proxy или middleware). |
| Rate limit login | **5 попыток на username за 15 минут.** После превышения — 429 + audit event `auth.login.rate_limited`. Redis-ключ: `ratelimit:login:<username>`, TTL = 15 min. |
| Clock skew | JWT-валидация допускает расхождение часов до **30 секунд** (`leeway=30`). |
| Сессии | Не более 5 активных сессий на пользователя. При превышении — старейшая инвалидируется. |

### 7. Transition from Phase 3.0

**Phase 3.0 read-only `/api/v1/identity/*` endpoint'ы остаются незащищёнными до Phase 3.2 (auth middleware).**

В Phase 3.2:
- `GET /api/v1/identity/*` → требуется `users.read`, `roles.read`, `permissions.read`, `audit.read`
- Все не-health эндпоинты → требуется JWT
- `/health/live`, `/health/ready` → без аутентификации

### 8. Future: MFA

MFA для критичных ролей (ТЗ §14) отложен до уточнения механизма со стороны AD/IdP. Варианты:
- OTP через корпоративный IdP (если AD FS с MFA-плагином)
- TOTP локально (RFC 6238) с seed в зашифрованном поле `users.mfa_secret`
- FIDO2/WebAuthn (если браузеры поддерживают)

Решение будет оформлено отдельным ADR при переходе к production.

## Consequences

- **Positive:** Полная определённость по протоколу AD, модели сессий и RBAC enforcement перед началом реализации. LDAP — максимально совместимый протокол без дополнительной инфраструктуры.
- **Negative:** LDAP bind означает, что сервис временно видит пароль пользователя (только в памяти, на время bind-операции). Более безопасные протоколы (Kerberos, OIDC) не требуют этого, но недоступны без AD FS.
- **Risk:** Если корпоративный AD требует Kerberos/Negotiate и блокирует LDAP bind — потребуется миграция на Kerberos (дополнительный ADR). Текущая архитектура изолирует протокол за `auth_provider`-интерфейсом — замена протокола не затрагивает модели и endpoint'ы.

## References

- TZ v2.5 §14 (Security), §16.1 (API Groups), Table 20
- `rmp_rewrite_starting_decisions.md` — User identity: AD required, local break-glass only
- `rmp_enterprise_architecture_review.md` — AD/SSO, RBAC/RLS/audit
- ADR-003 (Device Identity) — device JWT model, token TTL, no tokens in URL
- `packages/domain/models.py` — identity tables (users, roles, permissions, access_scopes, audit_events_operational)
- `packages/api/identity.py` — Phase 3.0 read-only identity endpoints (unprotected)

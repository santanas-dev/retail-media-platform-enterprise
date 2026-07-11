# Local LAN Preview (S-026)

Сервер: `192.168.110.77`

## URLs

| Сервис | URL |
|--------|-----|
| Admin Web | http://192.168.110.77:3000 |
| Advertiser Web | http://192.168.110.77:3001 |
| Control API | http://192.168.110.77:8000 |
| Device Gateway | http://192.168.110.77:8001 |

## Dev Credentials

| Пользователь | Пароль | Роль |
|-------------|--------|------|
| `advertiser_test` | `Test1234!` (текущий live) / `advertiser-dev-only` (seed) | advertiser |
| `break_glass_admin` | `break-glass-dev-only` | system_admin |

> При пересоздании БД seed создаёт пароль `advertiser-dev-only`.
> Текущий live DB имеет ручной хэш `Test1234!`.

## Управление

```bash
REPO=~/retail-media-platform-enterprise
COMPOSE_BASE=$REPO/infra/compose/docker-compose.phase1.yml
COMPOSE_PREVIEW=$REPO/infra/compose/docker-compose.preview.yml
COMPOSE_CMD="docker compose -f $COMPOSE_BASE -f $COMPOSE_PREVIEW"

# Статус
$COMPOSE_CMD ps

# Запуск (все сервисы)
$COMPOSE_CMD up -d --build

# Остановка
$COMPOSE_CMD down

# Логи конкретного сервиса
$COMPOSE_CMD logs -f control-api

# Перезапуск одного сервиса
$COMPOSE_CMD up -d --build control-api
```

### Фронтенд (вручную)

Фронтенд запускается отдельно — не через Docker:

```bash
cd $REPO/apps/advertiser-web
npm run build && npx vite preview --host 0.0.0.0 --port 3001 &

cd $REPO/apps/admin-web
npm run build && npx vite preview --host 0.0.0.0 --port 3000 &
```

## Preview Override

`infra/compose/docker-compose.preview.yml` — LAN-специфичные настройки:
- Redis: внешний порт 6380 (избегает конфликта с host Redis на 6379)
- CORS: добавляет `192.168.110.77:3000` и `:3001`
- db-setup: `ENVIRONMENT=dev` + `SEED_DEV_CREDENTIALS=true`

## Известные проблемы

- `grant-app-role.py` не работает в Docker — файл не копируется в образ.
  `retail_media_app` получает права при первом запуске (seed через owner URL).
- Фронтенд требует ручного запуска (`vite preview`), нет Docker-образов.
- `control-api` показывает `unhealthy` — healthcheck может требовать настройки.

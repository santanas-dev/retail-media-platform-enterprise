# Backup / Restore / Disaster Recovery Runbook

| **Created:** 2026-07-12 |
| **Version:** 1.0 |
| **Status:** pilot-ready |
| **Branch:** develop |

## 1. Цель

Обеспечить сохранность данных и возможность восстановления Retail Media Platform
после сбоя, человеческой ошибки или инцидента. Этот runbook покрывает pilot-уровень
готовности — полное production DR требует дополнительных элементов (см. раздел 9).

## 2. Что бэкапим

| Компонент | Статус | Формат | Частота |
|-----------|--------|--------|---------|
| **PostgreSQL DB** | ✅ Реализовано | `pg_dump` custom format (.dump) | Ежедневно (ручной запуск / cron) |
| **MinIO objects** | ✅ Реализовано (S-049) | Python SDK full-bucket backup + manifest | Ежедневно (ручной запуск / cron) |
| **NATS JetStream state** | ✅ Задокументировано (S-050) | Outbox source of truth — восстановление через provisioning + replay | Не критично для pilot — состояние восстанавливается из PostgreSQL через outbox relay |

## 3. RPO / RTO (pilot targets)

| Метрика | Pilot Target | Production Target |
|---------|-------------|-------------------|
| **RPO** (Recovery Point Objective) | 24 часа | 1 час |
| **RTO** (Recovery Time Objective) | 4 часа | 1 час |

**Обоснование pilot RPO:** ежедневный backup покрывает потерю не более суток данных
кампаний, креативов и PoP-событий. Для pilot-фазы с ограниченным числом
рекламодателей это приемлемо.

**Обоснование pilot RTO:** 4 часа включают диагностику, подготовку новой БД,
восстановление из дампа (~15 мин для pilot-объёма), верификацию и переключение
сервисов.

## 4. Backup — процедура

### 4.1 Ручной запуск

```bash
cd /opt/retail-media-platform
DATABASE_URL=postgresql://user:pass@host:5432/retail_media_platform \
BACKUP_DIR=/backups/postgres \
KEEP_LAST=7 \
python scripts/backup/postgres_backup.py
```

### 4.2 Через cron (ежедневно, 03:00 UTC)

```cron
0 3 * * * cd /opt/retail-media-platform && \
  DATABASE_URL=postgresql://user:pass@host:5432/retail_media_platform \
  BACKUP_DIR=/backups/postgres \
  KEEP_LAST=7 \
  KEEP_OLDER_THAN_DAYS=30 \
  /usr/bin/python3 scripts/backup/postgres_backup.py >> /var/log/rmp-backup.log 2>&1
```

### 4.3 Параметры

| Переменная | Назначение | Значение по умолчанию |
|------------|-----------|----------------------|
| `DATABASE_URL` | URL подключения к PostgreSQL | **обязательна** |
| `BACKUP_DIR` | Директория для файлов | `./backups` |
| `KEEP_LAST` | Хранить N последних бэкапов | не задано (без ограничения) |
| `KEEP_OLDER_THAN_DAYS` | Удалять старше N дней | не задано |

### 4.4 Формат

`pg_dump --format=custom` (сжатый бинарный формат). Выбран потому что:
- Меньше места на диске
- Поддерживает параллельное восстановление (`pg_restore --jobs=N`)
- Позволяет выборочное восстановление отдельных таблиц
- `pg_restore --list` для инспекции без восстановления

### 4.5 Имя файла

`rmp_backup_{database}_{timestamp}.dump`

Пример: `rmp_backup_retail_media_platform_20260712T030000Z.dump`

## 5. Restore — процедура

### 5.1 Шаг 1: Подготовка целевой БД

```bash
# Создать пустую базу (если не существует)
createdb -h target-host -U retail_media_owner rmp_restore_target
```

### 5.2 Шаг 2: Проверка бэкапа (check mode)

```bash
DATABASE_URL=postgresql://user:pass@target-host:5432/rmp_restore_target \
python scripts/restore/postgres_restore.py /backups/postgres/rmp_backup_...dump --check
```

Убедиться, что вывод показывает объекты и `=== Check Mode: VALID ===`.

### 5.3 Шаг 3: Восстановление

```bash
DATABASE_URL=postgresql://user:pass@target-host:5432/rmp_restore_target \
REQUIRE_RESTORE_CONFIRMATION=yes \
python scripts/restore/postgres_restore.py /backups/postgres/rmp_backup_...dump
```

### 5.4 Шаг 4: Верификация

```sql
-- Проверить количество таблиц
SELECT count(*) FROM pg_tables WHERE schemaname = 'public';

-- Проверить ключевые таблицы
SELECT 'campaigns' as tbl, count(*) FROM campaigns
UNION ALL SELECT 'creative_assets', count(*) FROM creative_assets
UNION ALL SELECT 'advertiser_organizations', count(*) FROM advertiser_organizations
UNION ALL SELECT 'local_credentials', count(*) FROM local_credentials
UNION ALL SELECT 'permissions', count(*) FROM permissions;

-- Проверить известную запись
SELECT username FROM local_credentials LIMIT 1;
```

### 5.5 Шаг 5: Переключение сервисов

Обновить `DATABASE_URL` в docker-compose или env для всех сервисов:
- `control-api`
- `device-gateway`
- `orchestrator-worker`

Перезапустить:
```bash
docker compose -f docker-compose.phase1.yml up -d control-api device-gateway orchestrator-worker
```

Проверить health:
```bash
curl http://localhost:8000/health/ready
```

## 5.1 MinIO Restore

**Важно:** одного восстановления PostgreSQL недостаточно. Загруженные креативы
(изображения, видео) хранятся в MinIO и не восстанавливаются из дампа БД.
После PostgreSQL restore необходимо восстановить объекты MinIO.

См. `docs/runbook/minio-backup-restore.md` — процедура backup, restore, check,
dry-run и drill для creative media объектов.

**Порядок полного восстановления:**
1. Restore PostgreSQL (этот runbook, §5)
2. Restore MinIO objects (`minio-backup-restore.md` §4)
3. Start NATS + run provisioning (`nats-backup-restore.md` §5)
4. Run consistency checks (`nats-backup-restore.md` §6, `minio-backup-restore.md` §6)

## 6. Restore Drill — процедура

Выполняется ежемесячно или после значительных изменений схемы.

### 6.1 Автоматизированный drill (opt-in тест)

```bash
cd /opt/retail-media-platform

# Создать тестовую целевую БД
createdb -h localhost -U retail_media_owner rmp_restore_target

# Запустить drill
RUN_BACKUP_RESTORE_TESTS=1 \
BACKUP_RESTORE_SOURCE_DB_URL=postgresql://retail_media_owner:pass@localhost:5432/retail_media_platform \
BACKUP_RESTORE_TARGET_DB_URL=postgresql://retail_media_owner:pass@localhost:5432/rmp_restore_target \
python -m pytest tests/integration/test_backup_restore.py -v
```

### 6.2 Ручной drill

1. Выполнить backup по процедуре из §4.
2. Создать `rmp_restore_target` на том же или другом хосте.
3. Восстановить по процедуре из §5.
4. Сверить количество таблиц и записей с источником.
5. Задокументировать результат в журнале drill'ов.

## 7. Rollback — процедура

Если после восстановления обнаружены проблемы:
1. Переключить `DATABASE_URL` обратно на исходную БД.
2. Перезапустить сервисы.
3. Проверить health.
4. Удалить неудачную целевую БД: `dropdb rmp_restore_target`.

## 8. Обработка секретов

- `DATABASE_URL` содержит пароль — **никогда не выводится в логи**.
  Скрипты заменяют пароль на `***` в выводе.
- Файлы бэкапов хранятся с `chmod 600`.
- `REQUIRE_RESTORE_CONFIRMATION=yes` — защита от случайного восстановления.

## 9. Отложенные production-элементы

| Элемент | Статус | Комментарий |
|---------|--------|-------------|
| MinIO backup (S3 mirror) | ✅ S-049 done | Python SDK full-bucket backup with manifest + SHA-256. См. `docs/runbook/minio-backup-restore.md`. |
| NATS JetStream backup | ✅ S-050 documented | Outbox source of truth. Recovery via provisioning + relay replay. См. `docs/runbook/nats-backup-restore.md`. |
| Offsite encrypted backup | ⏳ Deferred | Локальные бэкапы не защищают от физического сбоя сервера. Требуется rsync/rclone в S3/GCS с шифрованием. |
| Автоматическое расписание (cron) | ⏳ Deferred | Скрипт готов, cron-запись в §4.2 — требуется развернуть на production-сервере. |
| Мониторинг бэкапов | ⏳ Deferred | Алерт если backup не создан > 25 часов. Prometheus + AlertManager. |
| Календарь restore drill'ов | ⏳ Deferred | Ежемесячный автоматический drill через cron + нотификация результата. |
| Point-in-time recovery (PITR) | ⏳ Deferred | Требует WAL-архивирования (`archive_command`). Не нужно для pilot RPO 24h. |
| Репликация (standby) | ⏳ Deferred | Streaming replication для RPO < 1 мин. Требует второго сервера. |

## 10. Ссылки

- Скрипты: `scripts/backup/postgres_backup.py`, `scripts/restore/postgres_restore.py`
- MinIO backup: `docs/runbook/minio-backup-restore.md`
- NATS recovery: `docs/runbook/nats-backup-restore.md`
- Интеграционный тест: `tests/integration/test_backup_restore.py`
- Production gaps: `docs/product/production-gaps-triage.md`
- Стабилизационный трекер: `docs/architecture/stabilization-tracker.md`

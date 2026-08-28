# Product Requirements — Retail Media Platform Enterprise

## Active Branch: v2.5

- **Document:** `TZ_Retail_Media_Platform_v2_5_Final_Hermes.docx` (в `docs/00-source-of-truth/`)
- **Status:** Текущая реализация первого ТЗ. Соответствует roadmap v0.1 → v0.2 → v0.3.
- **Scope:** Admin portal, campaign domain, media upload, manifest/PoP contracts, three-role DB, KSO player (v0.3).

---

## Next Branch: v2.6

- **Document:** `TZ_Retail_Media_Platform_v2_6_Next_Branch_2026-07-11.docx`
- **Status:** 🔮 Future branch — дальнейшее развитие портала после закрытия первого ТЗ.
- **НЕ реализуется сейчас.** Ничего не отменяет из текущего roadmap.

### Драфт ТЗ v2.6 — `tz-v2.6-draft.md`

- **Статус содержания:** ACCEPTED владельцем 2026-08-28 (`OD-017`, редакция r421,
  SHA-256 `59478746…`); текущая редакция r422 — только cutover пути.
- **Статус документа:** DRAFT → `APPROVED` только после артефактов Дополнения AG и закрытия
  применимых gates (`roadmap.yaml`). Не источник истины, roadmap не меняет.
- **Sidecar:** `tz-v2.6-draft.sha256`; **приложения:** `tz-v2.6-draft-appendix-index.md`.
- **Трассировка:** `docs/product/requirements-traceability.yaml` (101 REQ → story → journey → registry →
  roadmap → evidence, 69 `SC-*`; схема `requirements-traceability.schema.json`; guard-модуль `req`).
  Привязана к ревизии драфта: новая редакция → красный CI до пересверки.
- Решения `DEC-022/024/026` записаны как `OD-018/019/020`; `DEC-005` (владелец master-данных
  цен/SKU) остаётся открытым.

### P0 Foundation Decision

**Перед любой реализацией v2.6 обязателен explicit P0 decision по tenant model.**
См. `docs/architecture/adr/ADR-018-tenant-model-for-next-branch.md` (Proposed).

Без решения: attribution, finance, targeting, competitive separation и RLS-домены
придётся переписывать при переходе к multi-retailer модели.

### v2.6 Направления развития

| Направление | Статус |
|-------------|--------|
| Attribution & Sales Lift | ⚪️ Not started / будущая v2.6 |
| Self-service advertiser cabinet | ⚪️ Foundation only (S-023 design gate) |
| Competitive Separation | ⚪️ Not started / будущая v2.6 |
| Store-level audience targeting | ⚪️ Not started / будущая v2.6 |
| Finance contract/invoicing integration | ⚪️ Not started / будущая v2.6 |
| Programmatic extension point | 🚫 Deferred |
| Dynamic creative MVP | 🚫 Deferred |
| Mobile field ops MVP | 🚫 Deferred |
| A/B lift metrics | ⚪️ Not started / будущая v2.6 |
| Third-party DOOH measurement/accreditation stub | 🚫 Deferred / design stub |

### Отдельные roadmap items (не v2.6)

Эти пункты — из первого ТЗ и остаются независимыми roadmap-элементами:

- KSO player / sidecar (v0.3)
- Android TV, LED/ESL (deferred)
- ClickHouse / export / billing (deferred)
- Advertiser portal (S-023 design gate → будущая реализация)

---

## Roadmap Ownership

- **`docs/product/roadmap.yaml`** — sequencing SSOT; правится только он.
- **`docs/product/generated/roadmap.generated.xlsx`** — внешний roadmap; **генерируется**,
  два листа (`Технический Roadmap`, `Бизнес-функции Roadmap`), руками не правится.
- **Claude Code** обновляет вход внутри утверждённой задачи; **Codex** проверяет.
  Hermes retired — прежняя строка про обновление статусов Hermes недействительна.
- Расхождение представления со входом ловит `scripts/ci/roadmap-governance-guard.py`.
- Будущие обновления — только status/evidence/notes, если пользователь явно не одобрит изменение формата.

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

- **Excel-файл** (`docs/product/roadmap-s020-2026-07-10.xlsx`) — канонический внешний roadmap.
- **Hermes** обновляет статусы в roadmap.
- **Codex** проверяет консистентность roadmap.
- **Формат зафиксирован:** два листа (`Технический Roadmap`, `Бизнес-функции Roadmap`), те же колонки, тот же визуальный стиль.
- Будущие обновления — только status/evidence/notes, если пользователь явно не одобрит изменение формата.

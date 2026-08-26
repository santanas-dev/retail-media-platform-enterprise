# Технические направления

<!-- Выделено из `docs/product/roadmap.md` при canonical cutover RM-GOV-005, 2026-08-26. Содержание перенесено без изменений; изменился только адрес. Последовательность работ живёт в `docs/product/roadmap.yaml`, производные представления — в `docs/product/generated/`. -->


| # | Направление | Завершено | На стенде | Остаётся | Риск | Приоритет |
|---|---|---|---|---|---|---|
| 1 | Campaign lifecycle + creatives | create/edit/submit/approve/reject/pause/activate, загрузка и модерация креативов | ✅ развёрнут; `campaign.create`, `creative.upload` проверены браузером | walkthrough человеком | низкий | **P1** |
| 2 | Advertiser / self-service | заявка, рассмотрение, org/brand/contract/contact, приглашение, вход | ✅ развёрнут; `contract_crud` проверен | `self.report_view`, `self.campaign_create` blocked; advertiser-web не проходил UX-аудит | средний | **P1** |
| 3 | Inventory, devices, emergency | правила, симуляция, health-обзор, активация/деактивация аварийного режима | ✅ развёрнут | нет реального КСО → устройство только `KSO-001` в статусе «не зарегистрирован» | средний | P2 |
| 4 | Commerce Contour 2 | тарифы, прайс-листы, заказы, offer/booking/close, payment status | ✅ развёрнут, пустые состояния корректны | бизнес-проверка человеком | низкий | P2 |
| 5 | Licensing Layer 1 / Layer 2 | Layer 1: enforce, seat_release, report | Layer 1 ✅ | **Layer 2 (signed-license JWS/CRL + UI) не реализован** → `license.view`, `license.upload` blocked | высокий | P2 |
| 6 | KSO / player / playlist | — | — | **плеер не перенесён**, `playlist.build` blocked, реального КСО нет | высокий | P2 |
| 7 | Security, RLS, tenant isolation | RLS на tenant-таблицах, `retail_media_app` NOBYPASSRLS, fail-closed scopes, audit | ✅ подтверждено на стенде (`rolbypassrls=f`) | RLS-proof на пилот-хосте | низкий | P1 |
| 8 | CI, UI-smoke stability, test truth | 40 jobs, blocking release-gate, anti-skip guards, барьер `wait_settled`, **транзакционная граница API (API-TX-BOUNDARY-001)** | — | ✅ **UI-SMOKE-STABILITY-005 закрыт** — 5× first-attempt green | низкий | — |
| 9 | Local stand, pilot packaging, deployment | LOCAL-DEV-STAND-001 ✅ OPERATIONAL, immutable bundle, update+rollback | ✅ работает | **001D HOST PROOF PENDING**, 15 owner inputs, reverse proxy/TLS отсутствуют | **высокий** | **P0** |
| 10 | Backup/restore, monitoring, secrets, TLS/CD, prod ops | backup+restore drill в CI, password-file contract, secret-гейты | стенд: backup не требуется (disposable) | TLS, CD, мониторинг прода, ротация секретов — **отсутствуют** | **высокий** | P2 |

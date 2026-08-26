#!/usr/bin/env bash
# QUARANTINED — НЕ ЗАПУСКАТЬ.
#
# Помещён в карантин canonical cutover RM-GOV-005 (2026-08-26).
#
# Обёртка всегда возвращала exit 0 и утверждала в комментарии, что её запускает
# CI-job. Это было неверно: job `roadmap-consistency-audit` вызывал
# scripts/roadmap-consistency-check.py напрямую и с --strict. Сам job удалён при
# cutover — направление registry ↔ рукописная книга стало тавтологией.
#
# Живые проверки перенесены в модуль `registry` гейта
# scripts/ci/roadmap-governance-guard.py (blocking).
# Для точечного прогона без блокировки: python3 scripts/roadmap-consistency-check.py

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"

echo "=== UI-TRUTH-001B: Roadmap-Consistency Audit ==="
echo ""

pip install -q openpyxl pyyaml 2>/dev/null || true

python3 scripts/roadmap-consistency-check.py

echo ""
echo "=== Audit complete (non-blocking) ==="

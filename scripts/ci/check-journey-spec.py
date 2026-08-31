#!/usr/bin/env python3
"""RM-STAB-006 — валидатор нормативного формата UI journeys registry.

    python3 scripts/ci/check-journey-spec.py            # мягко: только структурные ошибки
    python3 scripts/ci/check-journey-spec.py --strict   # полный контракт для reachable UI journeys
    python3 scripts/ci/check-journey-spec.py --self-test

Число journeys ВЫЧИСЛЯЕТСЯ из docs/product/feature-registry.yaml (канон ID/status/smoke), а не
фиксируется в задаче: реестр обязан покрывать ровно множество registry-ID.
Каждый reachable UI journey несёт: actor_permission_scope, permission_codes (из известных кодов),
entry, `Happy-path: N` (N ≥ 3), selectors (data-testid, и каждый встречается в smoke-файле),
negative_path, walkthrough (PENDING|OK|замечания …). Blocked journeys обязаны нести gap.
"""
from __future__ import annotations
import argparse, copy, re, sys
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "docs/product/feature-registry.yaml"
JOURNEYS = ROOT / "docs/product/journeys/journeys.yaml"
ROLE_SCOPE = ROOT / "docs/product/role-scope-matrix.yaml"
SMOKE_DIR = ROOT / "tests/ui-smoke"
WALKTHROUGH_RE = re.compile(r"^(PENDING|OK|замечания\b.*)$")
HAPPY_RE = re.compile(r"^Happy-path:\s*(\d+)\s*шаг")


def _load(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _smoke_selectors(smoke: str) -> set[str] | None:
    f = SMOKE_DIR / f"{smoke}.py"
    if not f.exists():
        return None
    src = f.read_text(encoding="utf-8")
    ids = set(re.findall(r'get_by_test_id\(\s*f?"([^"]+)"', src)) | set(re.findall(r'data-testid=\\?"([^"\\]+)', src)) \
        | set(re.findall(r'\[data-testid="([^"]+)"\]', src)) | set(re.findall(r"get_by_test_id\(\s*f?'([^']+)'", src))
    return ids


def findings(registry: dict, journeys: dict, known_codes: set[str], strict: bool, smoke_lookup=_smoke_selectors) -> list[str]:
    out = []
    reg = {f["id"]: f for f in registry["features"]}
    entries = journeys.get("journeys") or []
    ids = [j.get("id") for j in entries]
    for dup in sorted({i for i in ids if ids.count(i) > 1}):
        out.append(f"DUPLICATE: {dup} встречается в реестре дважды")
    jmap = {j["id"]: j for j in entries}
    for missing in sorted(set(reg) - set(jmap)):
        out.append(f"MISSING: {missing} есть в feature-registry, но нет в journeys.yaml")
    for extra in sorted(set(jmap) - set(reg)):
        out.append(f"UNKNOWN: {extra} есть в journeys.yaml, но не в feature-registry")
    for jid, j in jmap.items():
        f = reg.get(jid)
        if not f:
            continue
        if j.get("status") != f.get("status"):
            out.append(f"STATUS-DRIFT: {jid} status={j.get('status')} в реестре, {f.get('status')} в registry")
        if (j.get("smoke") or None) != (f.get("smoke") or None):
            out.append(f"SMOKE-DRIFT: {jid} smoke расходится с registry")
        if not WALKTHROUGH_RE.match(str(j.get("walkthrough", ""))):
            out.append(f"WALKTHROUGH: {jid} значение `{j.get('walkthrough')}` вне PENDING|OK|замечания …")
        if f.get("status") == "blocked" and not (j.get("gap") or "").strip():
            out.append(f"BLOCKED-NO-GAP: {jid} blocked без gap")
        for c in j.get("permission_codes") or []:
            if c not in known_codes:
                out.append(f"PERMISSION-UNKNOWN: {jid} → `{c}` нет в role-scope-matrix")
        is_ui = str(f.get("smoke", "")).startswith("test_uismoke")
        if not strict or f.get("status") != "reachable" or not is_ui:
            continue
        for key in ("actor_permission_scope", "entry", "negative_path"):
            if not (j.get(key) or "").strip():
                out.append(f"INCOMPLETE: {jid} без {key}")
        m = HAPPY_RE.match(str(j.get("happy_path") or ""))
        if not m:
            out.append(f"HAPPY-PATH: {jid} happy_path не начинается с `Happy-path: N шагов`")
        elif int(m.group(1)) < 3:
            out.append(f"HAPPY-PATH: {jid} `Happy-path: {m.group(1)}` — меньше 3 шагов")
        if not j.get("permission_codes") and f.get("frontend") not in ("public",) and jid != "system.theme_switch":
            out.append(f"PERMISSION-MISSING: {jid} без permission_codes")
        sels = j.get("selectors") or []
        if not sels:
            out.append(f"SELECTORS: {jid} без selectors (data-testid)")
        else:
            actual = smoke_lookup(f.get("smoke"))
            if actual is None:
                out.append(f"SMOKE-MISSING: {jid} smoke-файл `{f.get('smoke')}` не найден")
            else:
                for s in sels:
                    if s not in actual:
                        out.append(f"SELECTOR-DRIFT: {jid} селектор `{s}` не встречается в {f.get('smoke')}.py")
    return out


def run(strict: bool) -> int:
    registry, journeys = _load(REGISTRY), _load(JOURNEYS)
    known = set(_load(ROLE_SCOPE)["permissions"])
    found = findings(registry, journeys, known, strict)
    total = len(registry["features"]); ui = sum(1 for f in registry["features"] if str(f.get("smoke", "")).startswith("test_uismoke"))
    print(f"[journey-spec] registry {total} journeys (UI со smoke {ui}, reachable {sum(1 for f in registry['features'] if f['status']=='reachable')}) — число вычислено из feature-registry")
    for x in found:
        print("  -", x)
    print(f"[journey-spec] {'PASS' if not found else 'FAIL — ' + str(len(found)) + ' нарушений'} ({'strict' if strict else 'soft'})")
    return 1 if found else 0


def self_test() -> int:
    registry, journeys = _load(REGISTRY), _load(JOURNEYS)
    known = set(_load(ROLE_SCOPE)["permissions"])
    base_ok = not findings(registry, journeys, known, True)
    cases = [("baseline strict чист", None, base_ok)]
    ui = next(j for j in journeys["journeys"] if j["status"] == "reachable" and str(j.get("smoke", "")).startswith("test_uismoke") and j.get("selectors"))
    def tamper(label, mutate, code):
        r, jj = copy.deepcopy(registry), copy.deepcopy(journeys)
        mutate(r, jj)
        got = findings(r, jj, known, True)
        cases.append((label, code, any(x.startswith(code) for x in got)))
    tamper("journey удалён из реестра", lambda r, jj: jj["journeys"].remove(next(x for x in jj["journeys"] if x["id"] == ui["id"])), "MISSING")
    tamper("в registry появился ID без journey", lambda r, jj: r["features"].append({"id": "zz.new", "status": "blocked", "smoke": "n/a"}), "MISSING")
    tamper("status разошёлся с registry", lambda r, jj: next(x for x in jj["journeys"] if x["id"] == ui["id"]).__setitem__("status", "blocked"), "STATUS-DRIFT")
    tamper("happy_path без Happy-path: N", lambda r, jj: next(x for x in jj["journeys"] if x["id"] == ui["id"]).__setitem__("happy_path", "Логин → форма"), "HAPPY-PATH")
    tamper("селектор, которого нет в smoke", lambda r, jj: next(x for x in jj["journeys"] if x["id"] == ui["id"])["selectors"].append("does-not-exist-testid"), "SELECTOR-DRIFT")
    tamper("selectors пусты", lambda r, jj: next(x for x in jj["journeys"] if x["id"] == ui["id"]).__setitem__("selectors", []), "SELECTORS")
    tamper("permission-код вне матрицы", lambda r, jj: next(x for x in jj["journeys"] if x["id"] == ui["id"])["permission_codes"].append("nope.code"), "PERMISSION-UNKNOWN")
    tamper("walkthrough проставлен произвольно", lambda r, jj: next(x for x in jj["journeys"] if x["id"] == ui["id"]).__setitem__("walkthrough", "done"), "WALKTHROUGH")
    tamper("negative_path удалён", lambda r, jj: next(x for x in jj["journeys"] if x["id"] == ui["id"]).__setitem__("negative_path", ""), "INCOMPLETE")
    tamper("blocked без gap", lambda r, jj: next(x for x in jj["journeys"] if x["status"] == "blocked").__setitem__("gap", ""), "BLOCKED-NO-GAP")
    ok_all = all(ok for _, _, ok in cases)
    for label, code, ok in cases:
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}" + (f" ({code})" if code else ""))
    print(f"[journey-spec] self-test: {sum(1 for c in cases if c[2])}/{len(cases)} passed")
    return 0 if ok_all else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--strict", action="store_true"); ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    sys.exit(self_test() if a.self_test else run(a.strict))

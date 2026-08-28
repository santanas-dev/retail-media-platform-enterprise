#!/usr/bin/env python3
"""RM-GOV-004 — structural roadmap governance guard.

This is the SINGLE CI orchestration entrypoint for roadmap governance (rule B-3).
Other tasks register independently callable MODULES here; they do not create
competing mandatory CI jobs and do not re-implement a rule another module owns.

Modules
  schema        RM-GOV-001 — delegates to scripts/ci/check-roadmap-schema.py.
                Owns the whole in-file rule set, dependency integrity included
                (DANGLING-DEP, CYCLE, STAGE-ORDER). Not re-implemented here.
  drift         RM-GOV-003 — delegates to scripts/ci/roadmap-generate.py.
                Proves the projections equal what the inputs generate, and that
                the generator wrote nothing into its own inputs or into canon.
  metrics       RM-GOV-004 — INDEPENDENT recomputation of the headline counters
                straight from the inputs, plus a cross-check of every number a
                canonical document states as programmatically counted.
                Drift proves "output matches generator"; this proves "generator
                counted the right thing" and "canon quotes the same number".
  doc           RM-GOV-006 — the fact-vs-requirement rule (ADR-020, owner decision
                OD-001) is present and stated, the declared truth order is the same
                in AGENTS.md and CLAUDE.md, and the ADR process does not contradict
                its own index.
  env           RM-ENV-001 — the environment inventory is structurally sound and
                nothing claims to be evidence without a pinned identity. Liveness
                is deliberately NOT checked: CI has no route to that LAN, and a
                liveness check that silently passes would be a lie.
  registry      RM-GOV-005 — delegates to scripts/roadmap-consistency-check.py.
                Carries over the three directions that did NOT become tautological
                when the workbook started being generated: registry field/status
                validation with a real smoke behind every reachable UI feature,
                orphan smokes, and CI-subset membership. The removed CI job
                roadmap-consistency-audit is replaced here, not dropped.
  ssot          RM-GOV-004 — exactly one sequencing SSOT; generated artifacts
                carry their read-only marker; no undeclared script writes to a
                roadmap file.

Out of scope by the approved acceptance: smoke AST analysis.

Usage
  python3 scripts/ci/roadmap-governance-guard.py                 # all modules
  python3 scripts/ci/roadmap-governance-guard.py --module ssot   # one module
  python3 scripts/ci/roadmap-governance-guard.py --self-test     # tamper matrix
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]

ROADMAP_YAML = Path("docs/product/roadmap.yaml")
REGISTRY_YAML = Path("docs/product/feature-registry.yaml")
CI_SUBSET = Path("tests/ui-smoke/ci-subset.txt")
GENERATED_DIR = Path("docs/product/generated")
METRICS_JSON = GENERATED_DIR / "roadmap-metrics.generated.json"

SMOKE_PREFIX = "test_uismoke__"
READONLY_MARKER = "НЕ РЕДАКТИРОВАТЬ РУКАМИ"

# Files a script may write to without being a roadmap mutator.
ROADMAP_WRITE_TARGETS = (
    "roadmap.yaml", "roadmap.md", "roadmap-s020", "roadmap.schema.json",
    "roadmap-migration-manifest.yaml", "roadmap.generated", "roadmap-metrics.generated",
)

# Scripts allowed to open a roadmap file for writing, each with its owning task.
# Anything writing to a roadmap path and absent here is a finding. Removing a
# legacy mutator is RM-GOV-005 (canonical cutover); this guard only makes the
# set closed, so no NEW mutator can appear unnoticed.
DECLARED_MUTATORS = {
    "scripts/ci/roadmap-generate.py":
        "RM-GOV-003 — пишет только в docs/product/generated/, канон сверяется по sha256",
    "scripts/dev/build-initial-roadmap.py":
        "RM-GOV-002 — одноразовая миграция, породила roadmap.yaml и манифест",
    "scripts/legacy/generate_roadmap.py":
        "legacy S-020 — в карантине с RM-GOV-005, баннер QUARANTINED, не запускается",
    "scripts/legacy/update_roadmap_v26.py":
        "legacy v2.6 — в карантине с RM-GOV-005, баннер QUARANTINED, не запускается",
    "scripts/legacy/fix_roadmap_qa.py":
        "legacy QA-правка по абсолютному пути чужой машины — в карантине с RM-GOV-005",
    "scripts/ci/check-roadmap-schema.py":
        "RM-GOV-001 — пишет только временные копии в self-test (текстовые tamper-кейсы)",
    "scripts/ci/roadmap-governance-guard.py":
        "RM-GOV-004 — этот guard; пишет только во временные песочницы self-test",
    "scripts/legacy/tamper-test-roadmap-guard.py":
        "тест ROADMAP-GUARD-002 — в карантине с RM-GOV-005: проверял направления "
        "registry ↔ рукописная книга, которые стали тавтологией",
}

# Numbers a canonical document states as programmatically counted, mapped to the
# metric that must equal them. Every entry is checked on every run.
CANON_CLAIMS = [
    # docs/product/roadmap.md was archived at the RM-GOV-005 cutover; its summary
    # is now generated. The registry triple in PROJECT_STATE stays hand-written
    # and therefore still needs checking.
]

# Divergences the owner already knows about, each with the task that closes it.
# Baseline stays green; a NEW divergence is a finding. Nothing is hidden — every
# entry is printed on every run.
DECLARED_CANON_DIVERGENCES = {
    # Emptied by RM-GOV-005. The one entry that lived here — roadmap.md stating
    # "backend/service без UI-journey: 10" against 13 in the registry — turned out
    # not to be a wrong number: 10 counts REACHABLE service features, 13 counts all
    # service features (3 are blocked). The document never said which, and its own
    # section header used the other definition. The ambiguous line is gone with the
    # document; the generated projection labels both counts explicitly.
}

# `58 / 53 reachable / 5 blocked` — the registry triple quoted across PROJECT_STATE.
TRIPLE_RE = re.compile(r"(\d+)\s*/\s*(\d+)\s+reachable\s*/\s*(\d+)\s+blocked")
TRIPLE_FILES = ("PROJECT_STATE.md",)
# RM-GOV-009 (OD-038): registry теперь меняется решениями владельца, а исторические
# записи PROJECT_STATE («58 / 53 reachable / 5 blocked» на свою дату) — записи, не
# заявления о текущем состоянии. Проверяется только тройка с маркером «Registry (current)».
CURRENT_TRIPLE_RE = re.compile(r"Registry \(current\)[^\n]*?(\d+)\s*/\s*(\d+)\s+reachable\s*/\s*(\d+)\s+blocked")


# ---------------------------------------------------------------------------
# Module loading — the guard calls the owning implementation, never a copy.
# ---------------------------------------------------------------------------

def _load(root: Path, rel: str, name: str):
    path = root / rel
    if not path.exists():
        return None
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Module: schema  (owner RM-GOV-001)
# ---------------------------------------------------------------------------

def module_schema(root: Path) -> list:
    mod = _load(root, "scripts/ci/check-roadmap-schema.py", "rmp_schema")
    if mod is None:
        return ["SCHEMA-MODULE-MISSING: scripts/ci/check-roadmap-schema.py отсутствует"]
    return [f"schema/{f}" for f in mod.validate(root / ROADMAP_YAML)]


# ---------------------------------------------------------------------------
# Module: drift  (owner RM-GOV-003)
# ---------------------------------------------------------------------------

def module_drift(root: Path) -> list:
    mod = _load(root, "scripts/ci/roadmap-generate.py", "rmp_generate")
    if mod is None:
        return ["DRIFT-MODULE-MISSING: scripts/ci/roadmap-generate.py отсутствует"]
    return [f"drift/{f}" for f in mod.check_clean_diff(root)]


# ---------------------------------------------------------------------------
# Module: metrics  (owner RM-GOV-004)
# ---------------------------------------------------------------------------

def _independent_counts(root: Path) -> dict:
    """Recount from the inputs without touching generator code."""
    roadmap = yaml.safe_load((root / ROADMAP_YAML).read_text(encoding="utf-8"))
    registry = yaml.safe_load((root / REGISTRY_YAML).read_text(encoding="utf-8"))
    features = registry.get("features", []) or []

    subset = set()
    subset_path = root / CI_SUBSET
    if subset_path.is_file():
        for line in subset_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                subset.add(line if line.startswith(SMOKE_PREFIX) else SMOKE_PREFIX + line)

    tasks = roadmap.get("tasks", []) or []
    stages = {}
    delivery = {}
    for t in tasks:
        stages[t["stage"]] = stages.get(t["stage"], 0) + 1
        delivery[t["delivery_status"]] = delivery.get(t["delivery_status"], 0) + 1

    ui = [f for f in features if f.get("frontend") != "service"]
    return {
        ("sequencing", "tasks_total"): len(tasks),
        ("sequencing", "owner_gated"): sum(
            1 for t in tasks if (t.get("owner_gate") or {}).get("required")),
        ("sequencing", "owner_decisions"): len(roadmap.get("owner_decisions", []) or []),
        ("features", "total"): len(features),
        ("features", "reachable"): sum(1 for f in features if f.get("status") == "reachable"),
        ("features", "blocked"): sum(1 for f in features if f.get("status") == "blocked"),
        ("features", "ui_features"): len(ui),
        ("features", "ci_enforced"): sum(1 for f in ui if f.get("smoke") in subset),
        ("features", "service"): sum(1 for f in features if f.get("frontend") == "service"),
        ("_by_stage",): stages,
        ("_by_delivery",): delivery,
    }


def _metric_value(metrics: dict, path: tuple):
    if path == ("features", "service"):
        return metrics.get("features", {}).get("by_frontend", {}).get("service")
    node = metrics
    for key in path:
        if not isinstance(node, dict) or key not in node:
            return None
        node = node[key]
    return node


def module_metrics(root: Path) -> list:
    import json
    findings = []
    mpath = root / METRICS_JSON
    if not mpath.exists():
        return [f"metrics/MISSING: {METRICS_JSON} отсутствует"]
    metrics = json.loads(mpath.read_text(encoding="utf-8"))
    counts = _independent_counts(root)

    # (a) independent recomputation vs published metrics
    for path, expected in counts.items():
        if path[0].startswith("_"):
            continue
        actual = _metric_value(metrics, path)
        if actual != expected:
            findings.append(
                f"metrics/RECOUNT: {'.'.join(path)} = {actual} в metrics.json, "
                f"независимый пересчёт из входов даёт {expected}")
    for label, key, expected in (
        ("by_stage", "by_stage", counts[("_by_stage",)]),
        ("by_delivery_status", "by_delivery_status", counts[("_by_delivery",)]),
    ):
        actual = metrics.get("sequencing", {}).get(key)
        if actual != expected:
            findings.append(
                f"metrics/RECOUNT: sequencing.{label} = {actual} в metrics.json, "
                f"независимый пересчёт даёт {expected}")

    # (b) canonical documents must quote the same numbers
    for rel, pattern, path in CANON_CLAIMS:
        doc = root / rel
        if not doc.exists():
            continue
        m = re.search(pattern, doc.read_text(encoding="utf-8"))
        if not m:
            findings.append(f"metrics/CLAIM-GONE: `{rel}` больше не содержит утверждение "
                            f"{'.'.join(path)} — проверка перестала что-либо доказывать")
            continue
        claimed = int(m.group(1))
        expected = counts.get(path)
        if claimed == expected:
            continue
        declared = DECLARED_CANON_DIVERGENCES.get((rel, path))
        if declared:
            print(f"  [объявленное расхождение] {rel} · {'.'.join(path)}: "
                  f"канон {claimed}, факт {expected} — {declared}")
            continue
        findings.append(
            f"metrics/CANON-CLAIM: `{rel}` заявляет {'.'.join(path)} = {claimed}, "
            f"пересчёт из входов даёт {expected}")

    # (c) the registry triple quoted in PROJECT_STATE
    total = counts[("features", "total")]
    reach = counts[("features", "reachable")]
    block = counts[("features", "blocked")]
    for rel in TRIPLE_FILES:
        doc = root / rel
        if not doc.exists():
            continue
        text = doc.read_text(encoding="utf-8")
        hits = list(CURRENT_TRIPLE_RE.finditer(text))
        historical = len(TRIPLE_RE.findall(text)) - len(hits)
        if historical:
            print(f"  · {rel}: исторических троек registry {historical} — записи на дату, не проверяются")
        if not hits:
            findings.append(f"metrics/CLAIM-GONE: `{rel}` не содержит текущую тройку registry "
                            f"`Registry (current): N / M reachable / K blocked`")
        for m in hits:
            got = tuple(int(x) for x in m.groups())
            if got != (total, reach, block):
                line = text[:m.start()].count("\n") + 1
                findings.append(
                    f"metrics/CANON-CLAIM: `{rel}:{line}` заявляет "
                    f"{got[0]} / {got[1]} reachable / {got[2]} blocked, "
                    f"registry даёт {total} / {reach} / {block}")
    return findings


# ---------------------------------------------------------------------------
# Module: ssot  (owner RM-GOV-004)
# ---------------------------------------------------------------------------

def module_ssot(root: Path) -> list:
    findings = []

    # (a) exactly one sequencing SSOT
    candidates = []
    for path in sorted((root / "docs" / "product").rglob("*.yaml")):
        if path.name == REGISTRY_YAML.name:
            continue
        try:
            doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError:
            continue
        if isinstance(doc, dict) and "tasks" in doc and "stages" in doc:
            candidates.append(path.relative_to(root))
    if not candidates:
        findings.append("ssot/NO-SSOT: не найден файл последовательности работ")
    elif len(candidates) > 1:
        findings.append("ssot/MULTIPLE-SSOT: конкурирующие источники последовательности: "
                        + ", ".join(str(c) for c in candidates))
    elif candidates[0] != ROADMAP_YAML:
        findings.append(f"ssot/WRONG-SSOT: последовательность живёт в `{candidates[0]}`, "
                        f"ожидается `{ROADMAP_YAML}`")

    # (b) generated artifacts declare themselves read-only
    gen = root / GENERATED_DIR
    if not gen.is_dir():
        findings.append(f"ssot/NO-GENERATED: каталог `{GENERATED_DIR}` отсутствует")
    else:
        for path in sorted(gen.iterdir()):
            if path.name == "README.md":
                continue
            rel = path.relative_to(root)
            if path.suffix in (".md",):
                if READONLY_MARKER not in path.read_text(encoding="utf-8"):
                    findings.append(f"ssot/UNMARKED: `{rel}` не несёт метки «{READONLY_MARKER}»")
            elif path.suffix not in (".xlsx", ".json"):
                findings.append(f"ssot/UNEXPECTED: `{rel}` не объявлен генератором")
        readme = gen / "README.md"
        if not readme.exists():
            findings.append(f"ssot/NO-README: `{GENERATED_DIR}/README.md` отсутствует — "
                            f"каталог не объявляет себя сгенерированным")

    # (c) the set of roadmap mutators is closed
    for path in sorted((root / "scripts").rglob("*.py")):
        rel = str(path.relative_to(root))
        if "__pycache__" in rel:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        writes = any(t in text for t in ROADMAP_WRITE_TARGETS) and re.search(
            r"\.write_text\(|\.write_bytes\(|wb\.save\(|open\([^)]*['\"][wa]", text)
        if writes and rel not in DECLARED_MUTATORS:
            findings.append(f"ssot/UNDECLARED-MUTATOR: `{rel}` пишет в roadmap-файл, "
                            f"но не объявлен в DECLARED_MUTATORS")
    for rel in DECLARED_MUTATORS:
        if not (root / rel).exists():
            continue
    return findings


# ---------------------------------------------------------------------------
# Module: doc  (owner RM-GOV-006)
# ---------------------------------------------------------------------------

ADR_020 = Path("docs/architecture/adr/ADR-020-fact-vs-requirement.md")
ARCH_README = Path("docs/architecture/README.md")

# The rule must be stated, not merely referenced. Each fragment is load-bearing.
ADR_020_REQUIRED = (
    "Код и тесты описывают фактическое поведение",
    "ТЗ и ADR описывают требуемое",
    "является дефектом до появления явного ADR",
)
ADR_020_SECTIONS = ("## Context", "## Decision", "## Consequences")

# The precedence chain both contracts declare, normalised to comparable tokens.
TRUTH_ORDER = (
    "owner instruction", "git", "project_state", "feature-registry",
    "roadmap", "auto-memory",
)
TRUTH_ORDER_SOURCES = ("AGENTS.md", "CLAUDE.md")

# The banner convention documented in AGENTS.md: a superseded document opens with
# an HTML comment whose first line is `SUPERSEDED: ...`. Matching the bare word
# anywhere in the head is wrong — a document that merely TALKS about the banner
# (this repo's own cutover design gate does) would be misread as superseded.
SUPERSEDED_BANNER = re.compile(r"^\s*SUPERSEDED\b", re.M)


def _has_superseded_banner(text: str) -> bool:
    head = text.lstrip()
    if not head.startswith("<!--"):
        return False
    end = head.find("-->")
    return bool(SUPERSEDED_BANNER.search(head[:end] if end >= 0 else head[:4000]))


def _truth_chain(text: str):
    """Extract the declared precedence chain as comparable tokens."""
    chunk = None
    for marker in ("Precedence follows", "## Truth Priority"):
        if marker in text:
            chunk = text.split(marker, 1)[1][:700]
            break
    if chunk is None:
        return None
    low = chunk.lower()
    order = []
    for token, needles in (
        ("owner instruction", ("owner instruction",)),
        ("git", ("git / code", "git/code", "git / code / tests")),
        ("project_state", ("project_state.md",)),
        ("feature-registry", ("feature-registry.yaml",)),
        ("roadmap", ("roadmap",)),
        ("auto-memory", ("auto-memory",)),
    ):
        pos = min((low.find(n) for n in needles if low.find(n) >= 0), default=-1)
        if pos >= 0:
            order.append((pos, token))
    return tuple(t for _, t in sorted(order))


def module_doc(root: Path) -> list:
    findings = []

    # (a) the rule exists and is stated
    adr = root / ADR_020
    if not adr.exists():
        findings.append(f"doc/RULE-MISSING: `{ADR_020}` отсутствует — правило факта и "
                        f"требования нигде не записано")
    else:
        text = adr.read_text(encoding="utf-8")
        for section in ADR_020_SECTIONS:
            if section not in text:
                findings.append(f"doc/ADR-MALFORMED: `{ADR_020}` без раздела `{section}`")
        for fragment in ADR_020_REQUIRED:
            if fragment not in text:
                findings.append(f"doc/RULE-NOT-STATED: `{ADR_020}` не формулирует "
                                f"«{fragment}» — ссылка вместо правила")
        if "**Status:** ACCEPTED" not in text:
            findings.append(f"doc/ADR-NOT-ACCEPTED: `{ADR_020}` не помечен ACCEPTED")

    # (b) both contracts declare the same truth order
    chains = {}
    for rel in TRUTH_ORDER_SOURCES:
        path = root / rel
        if not path.exists():
            findings.append(f"doc/CONTRACT-MISSING: `{rel}` отсутствует")
            continue
        chains[rel] = _truth_chain(path.read_text(encoding="utf-8"))
        if chains[rel] is None:
            findings.append(f"doc/ORDER-UNREADABLE: в `{rel}` не найден заявленный "
                            f"порядок истины — проверка ослепла")
    present = {k: v for k, v in chains.items() if v}
    if len(present) == len(TRUTH_ORDER_SOURCES) and len(set(present.values())) > 1:
        findings.append("doc/ORDER-CONFLICT: заявленный порядок истины различается: "
                        + "; ".join(f"{k} = {' → '.join(v)}" for k, v in present.items()))
    for rel, chain in present.items():
        if chain != TRUTH_ORDER:
            findings.append(f"doc/ORDER-CHANGED: `{rel}` заявляет "
                            f"{' → '.join(chain)}, ADR-020 исходит из "
                            f"{' → '.join(TRUTH_ORDER)}")

    # (c) the ADR process must not contradict its own index
    readme = root / ARCH_README
    agents = root / "AGENTS.md"
    if readme.exists() and agents.exists():
        rtext, atext = readme.read_text(encoding="utf-8"), agents.read_text(encoding="utf-8")
        rr = re.search(r"ADR-001\.\.ADR-(\d+)", rtext)
        ar = re.search(r"ADR-001\.\.ADR-(\d+)", atext)
        if not rr or not ar:
            findings.append("doc/RANGE-UNREADABLE: диапазон `ADR-001..ADR-NNN` не найден "
                            f"в {'README' if not rr else 'AGENTS.md'} — проверка ослепла")
        elif rr.group(1) != ar.group(1):
            findings.append(
                f"doc/ADR-RANGE: `{ARCH_README}` объявляет ADR-001..ADR-{rr.group(1)}, "
                f"`AGENTS.md` — ADR-001..ADR-{ar.group(1)}: два диапазона одного перечня")

        active = rtext.split("## Active Documents")[1].split("## Superseded")[0] \
            if "## Active Documents" in rtext else ""
        indexed = set(re.findall(r"^\| `(adr/ADR-\d+)`", active, re.M))
        on_disk = sorted(p.name for p in (root / "docs/architecture/adr").glob("ADR-*.md"))
        missing = [n for n in on_disk
                   if f"adr/{'-'.join(n.split('-')[:2])}" not in indexed]
        if missing:
            findings.append(
                f"doc/ADR-UNINDEXED: {len(missing)} ADR на диске вне Active-таблицы "
                f"`{ARCH_README}` — по правилу индекса они формально не канон: "
                + ", ".join(missing))

        sup = rtext.split("## Superseded Documents (Historical Only)")[1] \
            if "## Superseded Documents (Historical Only)" in rtext else ""
        listed = set(re.findall(r"^\| `([^`]+)`", sup, re.M))
        bannered = {p.name for p in sorted((root / "docs/architecture").glob("*.md"))
                    if _has_superseded_banner(p.read_text(encoding="utf-8", errors="replace"))}
        unlisted = sorted(bannered - listed)
        if unlisted:
            findings.append(
                f"doc/SUPERSEDED-UNLISTED: {len(unlisted)} документов несут баннер "
                f"SUPERSEDED, но отсутствуют в Superseded-таблице (в таблице {len(listed)}): "
                + ", ".join(unlisted))
        phantom = sorted(n for n in listed - bannered
                         if (root / "docs/architecture" / n).exists())
        if phantom:
            findings.append(
                f"doc/SUPERSEDED-NO-BANNER: {len(phantom)} документов перечислены как "
                f"superseded, но не несут баннера: " + ", ".join(phantom))
    return findings


# ---------------------------------------------------------------------------
# Module: env  (owner RM-ENV-001)
# ---------------------------------------------------------------------------

ENV_INVENTORY = Path("docs/product/environment-inventory.yaml")
ENV_REQUIRED = ("id", "role", "title", "reachable_at_check", "evidence",
                "evidence_scope", "identity_source", "disposition")
# OD-007: a retired preview is described by what was OBSERVED, never by a
# disposition nobody decided. Checked on a structured field, not on prose:
# scanning free text cannot tell an assertion from a mention, which is how the
# SUPERSEDED detector produced a false positive earlier in this stage.
# `decommissioned` is a DECISION, not an observation: an agent can establish that
# a host did not answer, never that it was taken out of service. It is therefore
# admissible only when the inventory names an approved owner decision, and the
# rule below checks that the decision actually exists and is approved in the SSOT.
OWNER_DECIDED_DISPOSITIONS = {"decommissioned", "scheduled-upgrade"}
DISPOSITION_BY_ROLE = {
    "retired-preview": {"unreachable-at-check-time", "decommissioned", "scheduled-upgrade"},
    "stand": {"active"},
    "portal-contour": {"active"},
    "ci": {"active"},
}


def module_env(root: Path) -> list:
    path = root / ENV_INVENTORY
    if not path.exists():
        return [f"env/MISSING: `{ENV_INVENTORY}` отсутствует — окружения не инвентаризованы"]
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    findings = []
    envs = doc.get("environments") or []
    if not envs:
        return ["env/EMPTY: инвентарь не перечисляет ни одного окружения"]
    if not doc.get("checked_at"):
        findings.append("env/NO-CHECK-DATE: инвентарь не говорит, когда проверялся")

    seen = set()
    for e in envs:
        eid = e.get("id", "<без id>")
        if eid in seen:
            findings.append(f"env/DUPLICATE: `{eid}` встречается дважды")
        seen.add(eid)
        for field in ENV_REQUIRED:
            if field not in e:
                findings.append(f"env/INCOMPLETE: `{eid}` без поля `{field}`")
        # An environment is evidence only when an observation can be tied to a commit.
        if e.get("evidence"):
            ident = e.get("identity")
            if eid != "github-actions" and not (ident and ident.get("git_sha")):
                findings.append(
                    f"env/EVIDENCE-WITHOUT-IDENTITY: `{eid}` объявлен доказательным, "
                    f"но не несёт закреплённого git_sha — наблюдение не привязать к коммиту")
            if not e.get("reachable_at_check"):
                findings.append(
                    f"env/EVIDENCE-UNREACHABLE: `{eid}` объявлен доказательным, "
                    f"но на момент проверки был недостижим")
        if e.get("reachable_at_check") is False and e.get("identity"):
            findings.append(
                f"env/UNREACHABLE-WITH-IDENTITY: `{eid}` недостижим, но несёт identity — "
                f"идентичность недостижимого окружения не наблюдалась")
        allowed = DISPOSITION_BY_ROLE.get(e.get("role"))
        if allowed is not None:
            disp = e.get("disposition")
            if disp not in allowed:
                findings.append(
                    f"env/DISPOSITION: `{eid}` (role {e.get('role')}) объявляет "
                    f"disposition={disp!r}; допустимо {sorted(allowed)}. "
                    f"Для выведенного preview это наблюдение, а не решение — "
                    f"retire/upgrade решает владелец")
        disp = e.get("disposition")
        if disp in OWNER_DECIDED_DISPOSITIONS:
            od = e.get("owner_decision")
            if not od:
                findings.append(
                    f"env/DISPOSITION-WITHOUT-DECISION: `{eid}` объявлен `{disp}` без "
                    f"ссылки на решение владельца — это решение, а не наблюдение")
            else:
                roadmap_doc = yaml.safe_load((root / ROADMAP_YAML).read_text(encoding="utf-8"))
                decisions = {d["id"]: d for d in roadmap_doc.get("owner_decisions", []) or []}
                d = decisions.get(od)
                if d is None:
                    findings.append(
                        f"env/DECISION-DANGLING: `{eid}` ссылается на `{od}`, которого нет "
                        f"в owner_decisions `{ROADMAP_YAML}`")
                elif d.get("status") != "approved":
                    findings.append(
                        f"env/DECISION-NOT-APPROVED: `{eid}` объявлен `{disp}` по `{od}`, "
                        f"но статус решения — {d.get('status')}")
                if not e.get("owner_decision_on"):
                    findings.append(
                        f"env/DECISION-NO-DATE: `{eid}` не называет дату решения `{od}`")
        elif e.get("role") == "retired-preview" and not e.get("owner_decision_pending"):
            findings.append(
                f"env/NO-OWNER-DECISION: `{eid}` не называет, что retire/upgrade "
                f"остаётся решением владельца")

    # the stand baseline must be the one the sequencing SSOT declares
    stand = next((e for e in envs if e.get("role") == "stand"), None)
    roadmap = yaml.safe_load((root / ROADMAP_YAML).read_text(encoding="utf-8"))
    declared = (roadmap.get("base") or {}).get("stand_baseline") or {}
    if stand is None:
        findings.append("env/NO-STAND: инвентарь не называет стенд")
    elif declared:
        ident = stand.get("identity") or {}
        for field in ("git_sha", "bundle", "schema_head"):
            if declared.get(field) and ident.get(field) != declared.get(field):
                findings.append(
                    f"env/BASELINE-MISMATCH: стенд заявляет {field}={ident.get(field)}, "
                    f"`{ROADMAP_YAML}` base.stand_baseline — {declared.get(field)}")
    return findings


# ---------------------------------------------------------------------------
# Module: registry  (owner RM-GOV-005)
# ---------------------------------------------------------------------------

def module_registry(root: Path) -> list:
    mod = _load(root, "scripts/roadmap-consistency-check.py", "rmp_registry")
    if mod is None:
        return ["registry/MODULE-MISSING: scripts/roadmap-consistency-check.py отсутствует"]
    features = mod.load_registry()
    smoke_funcs = mod.scan_smoke_functions()
    ci_subset = mod.load_ci_subset()
    findings = []
    findings += mod.validate_registry(features, smoke_funcs)
    findings += mod.check_smoke_orphans(smoke_funcs, features)
    findings += mod.check_ci_subset_membership(features, smoke_funcs, ci_subset)
    return [f"registry/{f}" for f in findings]

# ---------------------------------------------------------------------------
# decisions — единый реестр решений (A2 после OD-017)
#
# ТЗ v2.6 §29 ведёт DEC-ID как вопросы; исполняемый реестр один — owner_decisions
# в roadmap.yaml, где DEC — alias записи OD. Второй реестр запрещён (AQ ledger).
# Гейт красный, если DEC из §29 не представлен ни одним OD, alias указывает на
# несуществующий DEC, один DEC висит на двух OD, alias стоит на superseded OD,
# или две таблицы DEC в драфте (§29 и Дополнение I) разошлись.
# ---------------------------------------------------------------------------
TZ_DRAFT = Path("docs/product/requirements/tz-v2.6-draft.md")
_DEC_ROW = re.compile(r"^\| (DEC-\d{3}) \|", re.M)


def _draft_section(text: str, start: str) -> str:
    i = text.find(start)
    if i < 0:
        return ""
    j = text.find("\n## ", i + len(start))
    return text[i:] if j < 0 else text[i:j]


def module_decisions(root: Path) -> list:
    findings = []
    draft = root / TZ_DRAFT
    if not draft.exists():
        return [f"decisions/DRAFT-MISSING: `{TZ_DRAFT}` отсутствует — реестр DEC не с чем сверять"]
    text = draft.read_text(encoding="utf-8")
    reg = _draft_section(text, "\n## 29. ")
    link = _draft_section(text, "\n## Дополнение I. ")
    dec_reg = set(_DEC_ROW.findall(reg))
    dec_link = set(_DEC_ROW.findall(link))
    if not dec_reg:
        return [f"decisions/DRAFT-NO-REGISTER: в `{TZ_DRAFT}` не найдена таблица §29 с DEC-ID — проверка ослепла"]
    if dec_link and dec_link != dec_reg:
        findings.append("decisions/DEC-TABLES-DIVERGE: §29 и Дополнение I драфта содержат разные DEC: "
                        f"только §29 {sorted(dec_reg - dec_link)}, только Дополнение I {sorted(dec_link - dec_reg)}")
    roadmap = yaml.safe_load((root / ROADMAP_YAML).read_text(encoding="utf-8"))
    owner = {}
    for od in roadmap.get("owner_decisions", []) or []:
        for al in od.get("aliases", []) or []:
            if al in owner:
                findings.append(f"decisions/ALIAS-DUP: {al} представлен и {owner[al]}, и {od['id']} — реестр перестал быть единым")
            owner[al] = od["id"]
            if al not in dec_reg:
                findings.append(f"decisions/ALIAS-UNKNOWN: {od['id']} объявляет alias {al}, которого нет в §29 драфта")
            if od.get("status") == "superseded":
                findings.append(f"decisions/ALIAS-SUPERSEDED: {al} висит на superseded {od['id']} — перенесите alias на действующее решение")
    for dec in sorted(dec_reg - set(owner)):
        findings.append(f"decisions/DEC-UNMAPPED: {dec} есть в §29 драфта, но не является alias ни одного owner_decision — "
                        "решение живёт вне единого реестра")
    return findings

# ---------------------------------------------------------------------------
# req — трассировка требований (A1 после OD-017; §37 драфта, REQ-GOV-002/003)
#
# requirements-traceability.yaml — единственная машинная карта REQ → story →
# journey → registry → roadmap → evidence. Гейт красный, если карта расходится
# с каталогом §25 драфта, ссылается на несуществующие story/journey/SC/task/DEC,
# нарушает правило покрытия §37, объявляет done без verified evidence, оставляет
# registry-ID без REQ, или привязана к другой ревизии драфта, чем лежит в репо.
# ---------------------------------------------------------------------------
TRACE_YAML = Path("docs/product/requirements-traceability.yaml")
TRACE_SCHEMA = Path("docs/product/requirements-traceability.schema.json")
_REQ_ROW = re.compile(r"^\| (REQ-[A-Z0-9]+-\d{3}) \|", re.M)
_US_ROW = re.compile(r"^\| (US-[A-Z0-9]+-\d{3}) \|", re.M)


def module_req(root: Path) -> list:
    findings = []
    ypath, spath, draft = root / TRACE_YAML, root / TRACE_SCHEMA, root / TZ_DRAFT
    for p in (ypath, spath, draft):
        if not p.exists():
            return [f"req/MISSING: `{p.relative_to(root)}` отсутствует — карта требований не проверяема"]
    doc = yaml.safe_load(ypath.read_text(encoding="utf-8"))
    try:
        import jsonschema
        errs = sorted(jsonschema.Draft202012Validator(json.loads(spath.read_text(encoding="utf-8"))).iter_errors(doc),
                      key=lambda e: list(e.absolute_path))
        for e in errs[:20]:
            findings.append(f"req/SCHEMA: {'/'.join(str(x) for x in e.absolute_path) or '<root>'}: {e.message[:160]}")
        if errs:
            return findings
    except ImportError:
        findings.append("req/NO-JSONSCHEMA: jsonschema не установлен — схема карты не проверена")

    text = draft.read_text(encoding="utf-8")
    m = re.search(r"\| Revision \| `([^`]+)`", text)
    draft_rev = m.group(1) if m else None
    if doc["document"].get("revision") != draft_rev:
        findings.append(f"req/DRAFT-REVISION-DRIFT: карта привязана к `{doc['document'].get('revision')}`, "
                        f"в репо лежит `{draft_rev}` — пересверьте REQ/story/SC и обновите document.revision/sha256")
    catalogue = _draft_section(text, "\n## 25. ")
    draft_req = set(_REQ_ROW.findall(catalogue))
    stories = set(_US_ROW.findall(_draft_section(text, "\n## Дополнение AP.")))
    if not draft_req or not stories:
        return findings + ["req/DRAFT-NO-CATALOGUE: §25/AP драфта не распознаны — проверка ослепла"]

    roadmap = yaml.safe_load((root / ROADMAP_YAML).read_text(encoding="utf-8"))
    tasks = {t["id"]: t for t in roadmap.get("tasks", [])}
    decisions = {a for o in roadmap.get("owner_decisions", []) or [] for a in o.get("aliases", []) or []}
    decisions |= {o["id"] for o in roadmap.get("owner_decisions", []) or []}
    registry = {f["id"]: f for f in yaml.safe_load((root / REGISTRY_YAML).read_text(encoding="utf-8"))["features"]}

    reqs = doc["requirements"]
    ids = [r["id"] for r in reqs]
    for dup in sorted({i for i in ids if ids.count(i) > 1}):
        findings.append(f"req/DUPLICATE: {dup} встречается в карте более одного раза")
    ids = set(ids)
    for missing in sorted(draft_req - ids):
        findings.append(f"req/UNMAPPED: {missing} есть в §25 драфта, но отсутствует в карте")
    for extra in sorted(ids - draft_req):
        findings.append(f"req/UNKNOWN-REQ: {extra} есть в карте, но не в §25 драфта")

    scenarios = {s["id"]: s for s in doc.get("scenarios", [])}
    sc_ids = [s["id"] for s in doc.get("scenarios", [])]
    for dup in sorted({i for i in sc_ids if sc_ids.count(i) > 1}):
        findings.append(f"req/SC-DUPLICATE: {dup}")
    pending = set(doc.get("pending_journey_map", {}) or {})
    awaiting = {p for p, v in (doc.get("pending_journey_map", {}) or {}).items() if (v or {}).get("status") == "awaiting_owner"}
    for p in sorted(awaiting & set(registry)):
        findings.append(f"req/PENDING-IS-CANONICAL: `{p}` уже есть в feature-registry — переведите в journey_ids (status mapped)")

    referenced_sc = set()
    for r in reqs:
        rid = r["id"]
        for s in r["story_ids"]:
            if s not in stories:
                findings.append(f"req/STORY-UNKNOWN: {rid} → {s} нет в AP драфта")
        for j in r["journey_ids"]:
            if j not in registry:
                findings.append(f"req/JOURNEY-UNKNOWN: {rid} → `{j}` нет в feature-registry")
        for j in r["pending_journey_ids"]:
            if j not in pending:
                findings.append(f"req/PENDING-UNKNOWN: {rid} → `{j}` нет в pending_journey_map")
        for s in r["scenario_ids"]:
            if s not in scenarios:
                findings.append(f"req/SC-UNKNOWN: {rid} → {s} нет в scenarios")
            referenced_sc.add(s)
        for t in r["roadmap_ids"]:
            if t not in tasks:
                findings.append(f"req/TASK-UNKNOWN: {rid} → {t} нет в roadmap.yaml")
        for d in r["dependencies"]:
            if d not in decisions:
                findings.append(f"req/DECISION-UNKNOWN: {rid} → {d} не является alias/ID owner_decisions")
        ct = r["coverage_type"]
        if ct == "business" and not (r["story_ids"] and (r["journey_ids"] or r["pending_journey_ids"])):
            findings.append(f"req/COVERAGE: {rid} business без story_ids или journey (§37)")
        if ct != "business" and not r["scenario_ids"]:
            findings.append(f"req/COVERAGE: {rid} {ct} без scenario_ids (§37)")
        ds, rs = r["delivery_status"], r["requirement_status"]
        if ds == "done":
            if rs != "approved":
                findings.append(f"req/STATUS: {rid} delivery done при requirement_status={rs} (§37)")
            if not any(e["status"] == "verified" for e in r["evidence"]):
                findings.append(f"req/OVERCLAIM: {rid} delivery done без verified evidence")
        if ds == "blocked" and not r.get("block_reason"):
            findings.append(f"req/BLOCKED-NO-REASON: {rid}")
        # статус берётся из roadmap/verified evidence, не из registry reachable или candidate-теста
        if ds in ("in_progress", "verification") and not (
                any(tasks.get(t, {}).get("delivery_status") in ("in_progress", "verification", "done") for t in r["roadmap_ids"])
                or any(e["status"] == "verified" for e in r["evidence"])):
            findings.append(f"req/STATUS-SOURCE: {rid} delivery {ds} без roadmap task в работе и без verified evidence — "
                            "registry reachable/candidate-тест статус не дают")
        disp = r["disposition"]
        if disp == "task" and not r["roadmap_ids"]:
            findings.append(f"req/DISPOSITION: {rid} disposition=task без roadmap_ids")
        if disp == "task_required" and r["roadmap_ids"]:
            findings.append(f"req/DISPOSITION: {rid} disposition=task_required, но roadmap_ids уже есть")
        if disp == "blocked" and ds != "blocked":
            findings.append(f"req/DISPOSITION: {rid} disposition=blocked при delivery_status={ds}")
        for e in r["evidence"]:
            if e["kind"] in ("unit", "behavioral", "integration", "ui_smoke", "contract_test", "command") \
                    and not (root / e["ref"]).exists():
                findings.append(f"req/EVIDENCE-PATH: {rid} → `{e['ref']}` не существует")
    for sid, s in scenarios.items():
        if sid not in referenced_sc:
            findings.append(f"req/SC-ORPHAN: {sid} не привязан ни к одному REQ")
        for rid in s["req_ids"]:
            if rid not in ids:
                findings.append(f"req/SC-REQ-UNKNOWN: {sid} → {rid}")
            elif sid not in next(r for r in reqs if r["id"] == rid)["scenario_ids"]:
                findings.append(f"req/SC-ASYMMETRIC: {sid} называет {rid}, но {rid} не называет {sid}")
        for t in s["roadmap_ids"]:
            if t not in tasks:
                findings.append(f"req/TASK-UNKNOWN: {sid} → {t} нет в roadmap.yaml")
        for e in s["evidence"]:
            if e["kind"] in ("unit", "behavioral", "integration", "ui_smoke", "contract_test", "command") \
                    and not (root / e["ref"]).exists():
                findings.append(f"req/EVIDENCE-PATH: {sid} → `{e['ref']}` не существует")
        if s["delivery_status"] == "done" and not any(e["status"] == "verified" for e in s["evidence"]):
            findings.append(f"req/OVERCLAIM: {sid} delivery done без verified evidence")
        if s["delivery_status"] in ("in_progress", "verification") and not (
                any(tasks.get(t, {}).get("delivery_status") in ("in_progress", "verification", "done") for t in s["roadmap_ids"])
                or any(e["status"] == "verified" for e in s["evidence"])):
            findings.append(f"req/STATUS-SOURCE: {sid} delivery {s['delivery_status']} без roadmap task в работе и без verified evidence")

    traced = {j for r in reqs for j in r["journey_ids"]}
    excluded = {x["id"] for x in doc.get("registry_exclusions", []) or []}
    for fid in sorted(set(registry) - traced - excluded):
        findings.append(f"req/REGISTRY-UNTRACED: `{fid}` из feature-registry не встречается ни в одном journey_ids "
                        "и не исключён явно (REQ-GOV-002)")

    tbd = sum(1 for r in reqs for k in ("owner", "implementation_owner") if r[k] == "TBD") \
        + sum(1 for s in scenarios.values() if s["owner"] == "TBD")
    if tbd and doc["document"].get("status") == "APPROVED":
        findings.append(f"req/TBD-AT-APPROVED: {tbd} полей TBD при document.status=APPROVED (§37)")
    elif tbd:
        print(f"  · TBD owner: {tbd} полей — допустимо до APPROVED, блокирует его")
    print(f"  · REQ {len(reqs)} / SC {len(scenarios)} / pending journeys {len(pending)} / "
          f"без roadmap_ids {sum(1 for r in reqs if not r['roadmap_ids'])}")
    return findings


MODULES = {
    "schema": ("RM-GOV-001", module_schema),
    "drift": ("RM-GOV-003", module_drift),
    "metrics": ("RM-GOV-004", module_metrics),
    "doc": ("RM-GOV-006", module_doc),
    "env": ("RM-ENV-001", module_env),
    "registry": ("RM-GOV-005", module_registry),
    "ssot": ("RM-GOV-004", module_ssot),
    "decisions": ("OD-017/A2", module_decisions),
    "req": ("OD-017/A1", module_req),
}


def run(root: Path, only: str | None = None) -> list:
    findings = []
    for name, (owner, fn) in MODULES.items():
        if only and name != only:
            continue
        print(f"[{name}] модуль {owner}")
        try:
            found = fn(root)
        except Exception as exc:  # a module that cannot run is a red gate, not a pass
            found = [f"{name}/MODULE-ERROR: {type(exc).__name__}: {exc}"]
        for f in found:
            print(f"  - {f}")
        if not found:
            print("  чисто")
        findings.extend(found)
    return findings


# ---------------------------------------------------------------------------
# Self-test — tamper matrix
# ---------------------------------------------------------------------------

SANDBOX_PATHS = [
    "docs/product/roadmap.yaml", "docs/product/roadmap.schema.json",
    "docs/product/feature-registry.yaml",
    "docs/product/history/roadmap-2026-08-26.md",
    "docs/product/history/roadmap-s020-2026-07-10.xlsx",
    "docs/product/roadmap-migration-manifest.yaml",
    "tests/ui-smoke/ci-subset.txt", "PROJECT_STATE.md", "AGENTS.md", "CLAUDE.md",
    "docs/architecture/README.md", "docs/product/environment-inventory.yaml",
    "docs/product/requirements/tz-v2.6-draft.md",
    "docs/product/requirements-traceability.yaml", "docs/product/requirements-traceability.schema.json",
]
SANDBOX_TREES = ["scripts/ci", "scripts/dev", "scripts/legacy", "docs/product/generated",
                 "tests/ui-smoke", "tests/behavioral", "tests/integration", "docs/architecture"]


def _sandbox(root: Path, tmp: Path) -> Path:
    work = tmp / "repo"
    work.mkdir()
    for rel in SANDBOX_PATHS:
        src = root / rel
        if src.exists():
            dst = work / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    for tree in SANDBOX_TREES:
        src = root / tree
        if src.is_dir():
            shutil.copytree(src, work / tree, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns("__pycache__"))
    (work / "scripts").mkdir(exist_ok=True)
    for name in sorted((root / "scripts").glob("*.py")):
        shutil.copy2(name, work / "scripts" / name.name)
    (work / "tests").mkdir(exist_ok=True)
    for name in sorted((root / "tests").glob("*.py")):  # evidence refs модуля req
        shutil.copy2(name, work / "tests" / name.name)
    return work


def _guard_in(work: Path) -> list:
    """Run the guard as the CI job runs it, inside the sandbox."""
    proc = subprocess.run(
        [sys.executable, str(work / "scripts/ci/roadmap-governance-guard.py")],
        capture_output=True, text=True, cwd=str(work))
    return [l for l in proc.stdout.splitlines() if l.strip().startswith("- ")] \
        if proc.returncode else []


def _fingerprint(work: Path) -> dict:
    """Content hash of everything a tamper could plausibly touch."""
    import hashlib
    out = {}
    for path in sorted(work.rglob("*")):
        if path.is_file() and "__pycache__" not in str(path):
            out[str(path.relative_to(work))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


def _bump_number(work: Path, rel, label: str):
    """Изменить число, которое проекция УЖЕ содержит, не зная его заранее.

    Фикстура, державшая «| Всего задач | 42 |» числом, устарела в тот момент, когда
    очередь выросла до 43, и уронила гейт в CI. Детектор устаревания сработал верно,
    но правильнее, чтобы фикстура не могла устареть: она читает текущее значение и
    подменяет его на другое.
    """
    path = work / rel
    text = path.read_text(encoding="utf-8")
    m = re.search(rf"\| {re.escape(label)} \| (\d+) \|", text)
    assert m, f"фикстура устарела: строки «{label}» нет в {rel}"
    current = int(m.group(1))
    path.write_text(
        text.replace(m.group(0), f"| {label} | {current - 1} |", 1), encoding="utf-8")
    return current


def _count_in_metrics(work: Path, *path_keys):
    import json as _json
    node = _json.loads((work / METRICS_JSON).read_text(encoding="utf-8"))
    for key in path_keys:
        node = node[key]
    return node


def _triple_text(work: Path) -> str:
    """Тройка registry в том виде, в каком её сейчас цитирует PROJECT_STATE."""
    m = TRIPLE_RE.search((work / "PROJECT_STATE.md").read_text(encoding="utf-8"))
    assert m, "фикстура устарела: тройки registry нет в PROJECT_STATE.md"
    return m.group(0)


def _bump_triple(work: Path):
    path = work / "PROJECT_STATE.md"
    text = path.read_text(encoding="utf-8")
    m = CURRENT_TRIPLE_RE.search(text)
    assert m, "фикстура устарела: текущей тройки registry нет в PROJECT_STATE.md"
    total, reach, block = (int(x) for x in m.groups())
    triple = f"{total} / {reach} reachable / {block} blocked"
    assert triple in m.group(0)
    path.write_text(
        text[:m.start()] + m.group(0).replace(triple, f"{total} / {reach + 1} reachable / {block - 1} blocked") + text[m.end():],
        encoding="utf-8")


def _bump_historical_triple(work: Path):
    """Историческая тройка (без маркера current) меняется — гейт должен остаться зелёным."""
    path = work / "PROJECT_STATE.md"
    text = path.read_text(encoding="utf-8")
    cur = CURRENT_TRIPLE_RE.search(text)
    for m in TRIPLE_RE.finditer(text):
        if cur and cur.start() <= m.start() <= cur.end():
            continue
        total, reach, block = (int(x) for x in m.groups())
        path.write_text(text[:m.start()] + f"{total} / {reach + 1} reachable / {block - 1} blocked" + text[m.end():], encoding="utf-8")
        return
    raise AssertionError("фикстура устарела: исторической тройки нет в PROJECT_STATE.md")


def _set_env(work: Path, env_id: str, key: str, value):
    """Set one field on one environment, structurally.

    Text substitution here would append a duplicate YAML key and the last one
    would win — an inert tamper that looks applied. That trap already cost this
    stage one silently-passing fixture.
    """
    path = work / ENV_INVENTORY
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    for env in doc["environments"]:
        if env["id"] == env_id:
            env[key] = value
            break
    else:
        raise AssertionError(f"фикстура устарела: окружение {env_id!r} не найдено")
    path.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _env_field(work: Path, env_id: str, key: str):
    doc = yaml.safe_load((work / ENV_INVENTORY).read_text(encoding="utf-8"))
    return next(e for e in doc["environments"] if e["id"] == env_id).get(key)


def _deps_of(work: Path, task_id: str):
    doc = yaml.safe_load((work / ROADMAP_YAML).read_text(encoding="utf-8"))
    for t in doc.get("tasks", []):
        if t["id"] == task_id:
            return t.get("dependencies") or []
    return None


def self_test(root: Path) -> int:
    cases = []

    def case(name, dimension, fn, expect_red: bool, effective=None):
        """Run one tamper case in a sandbox.

        `effective` guards against the failure mode this task exists to catch:
        a fixture that still edits the file but no longer states a falsehood, so
        the gate goes green and the case silently stops proving anything. If it
        returns False the case FAILS as an inert fixture, not as a clean tree.
        """
        with tempfile.TemporaryDirectory() as td:
            work = _sandbox(root, Path(td))
            before = _fingerprint(work)
            fn(work)
            if _fingerprint(work) == before:
                cases.append((dimension, name, False, "фикстура ничего не изменила"))
                return
            if effective is not None and not effective(work):
                cases.append((dimension, name, False, "фикстура инертна — подмена не вступила в силу"))
                return
            red = bool(_guard_in(work))
            cases.append((dimension, name, red == expect_red, ""))

    def sub(work, rel, old, new, count=1):
        p = work / rel
        text = p.read_text(encoding="utf-8")
        assert old in text, f"фикстура устарела: {old!r} нет в {rel}"
        p.write_text(text.replace(old, new, count), encoding="utf-8")

    # --- decisions: единый реестр решений
    case("DEC из §29 потерял alias в owner_decisions", "decisions",
         lambda w: sub(w, ROADMAP_YAML, "  aliases: [DEC-022]\n", "", 1), True,
         effective=lambda w: "aliases: [DEC-022]" not in (w / ROADMAP_YAML).read_text(encoding="utf-8"))
    case("alias указывает на несуществующий DEC", "decisions",
         lambda w: sub(w, ROADMAP_YAML, "  aliases: [DEC-022]\n", "  aliases: [DEC-099]\n", 1), True,
         effective=lambda w: "aliases: [DEC-099]" in (w / ROADMAP_YAML).read_text(encoding="utf-8"))
    case("один DEC на двух owner decisions", "decisions",
         lambda w: sub(w, ROADMAP_YAML, "  aliases: [DEC-024]\n", "  aliases: [DEC-024, DEC-022]\n", 1), True)
    case("в §29 драфта появился DEC без owner decision", "decisions",
         lambda w: sub(w, TZ_DRAFT, "| DEC-027 | A/B attribution scope",
                       "| DEC-028 | Новый вопрос без OD | нельзя |\n| DEC-027 | A/B attribution scope", 1), True,
         effective=lambda w: "| DEC-028 |" in (w / TZ_DRAFT).read_text(encoding="utf-8"))
    case("одна задача дважды в blocks owner decision (дубликат RM-GOV-009)", "decisions",
         lambda w: sub(w, ROADMAP_YAML, "  blocks:\n  - RM-BIZ-002\n", "  blocks:\n  - RM-BIZ-002\n  - RM-BIZ-002\n", 1), True,
         effective=lambda w: any((o.get("blocks") or []).count("RM-BIZ-002") == 2
                                 for o in yaml.safe_load((w / ROADMAP_YAML).read_text(encoding="utf-8"))["owner_decisions"]))
    case("alias на superseded решении", "decisions",
         lambda w: sub(w, ROADMAP_YAML, "  status: approved\n  decided_on: '2026-08-28'\n- id: OD-019\n",
                       "  status: superseded\n  decided_on: '2026-08-28'\n- id: OD-019\n", 1), True)

    # --- req: трассировка требований
    case("REQ из §25 пропал из карты", "req",
         lambda w: sub(w, TRACE_YAML, "- id: REQ-GOV-003\n", "- id: REQ-GOV-099\n", 1), True,
         effective=lambda w: "- id: REQ-GOV-099" in (w / TRACE_YAML).read_text(encoding="utf-8"))
    case("journey_ids ссылается на несуществующий registry ID", "req",
         lambda w: sub(w, TRACE_YAML, "  - system.theme_switch\n", "  - system.theme_switchx\n", 1), True)
    case("business REQ потерял story", "req",
         lambda w: sub(w, TRACE_YAML, "  story_ids:\n  - US-KPI-001\n", "  story_ids: []\n", 1), True,
         effective=lambda w: "- US-KPI-001" not in (w / TRACE_YAML).read_text(encoding="utf-8"))
    case("roadmap_ids ссылается на неизвестную задачу", "req",
         lambda w: sub(w, TRACE_YAML, "  - RM-TECH-203\n", "  - RM-TECH-299\n", 1), True)
    case("технический REQ остался без сценария", "req",
         lambda w: sub(w, TRACE_YAML, "  scenario_ids:\n  - SC-STAND-002\n", "  scenario_ids: []\n", 1), True,
         effective=lambda w: "- SC-STAND-002" not in (w / TRACE_YAML).read_text(encoding="utf-8").split("scenarios:")[0])
    case("delivery done без verified evidence", "req",
         lambda w: sub(w, TRACE_YAML, "  delivery_status: planned\n", "  delivery_status: done\n", 1), True,
         effective=lambda w: "delivery_status: done" in (w / TRACE_YAML).read_text(encoding="utf-8"))
    case("registry feature без REQ", "req",
         lambda w: sub(w, TRACE_YAML, "  - observability\n", "", 1), True,
         effective=lambda w: "  - observability\n" not in (w / TRACE_YAML).read_text(encoding="utf-8"))
    def _status_in_block(w, req_id, new_status):
        # меняем delivery_status внутри блока конкретного REQ, не первое совпадение по файлу
        p = w / TRACE_YAML
        text = p.read_text(encoding="utf-8")
        i = text.index(f"- id: {req_id}\n")
        j = text.index("  delivery_status: ", i)
        k = text.index("\n", j)
        p.write_text(text[:j] + f"  delivery_status: {new_status}" + text[k:], encoding="utf-8")

    case("in_progress без roadmap task и verified evidence", "req",
         lambda w: _status_in_block(w, "REQ-NFR-005", "in_progress"), True,
         effective=lambda w: yaml.safe_load((w / TRACE_YAML).read_text(encoding="utf-8"))["requirements"]
         and next(r for r in yaml.safe_load((w / TRACE_YAML).read_text(encoding="utf-8"))["requirements"]
                  if r["id"] == "REQ-NFR-005")["delivery_status"] == "in_progress")
    case("карта привязана к другой ревизии драфта", "req",
         lambda w: sub(w, TZ_DRAFT, "| Revision | `draft-2026-08-28-r422`", "| Revision | `draft-2026-08-28-r423`", 1), True)

    with tempfile.TemporaryDirectory() as td:
        work = _sandbox(root, Path(td))
        cases.append(("baseline", "чистое дерево — зелено", not _guard_in(work), ""))

    case("обязательное поле удалено из задачи", "schema",
         lambda w: sub(w, ROADMAP_YAML, "  kind: governance\n", "", 1), True)
    case("статус done без verified evidence", "schema",
         lambda w: sub(w, ROADMAP_YAML, "  delivery_status: planned",
                       "  delivery_status: done", 1), True)

    case("зависимость указывает в никуда", "dependencies",
         lambda w: sub(w, ROADMAP_YAML, "  - RM-GOV-002", "  - RM-GOV-999", 1), True)
    case("цикл в графе зависимостей", "dependencies",
         lambda w: sub(w, ROADMAP_YAML,
                       "- id: RM-GOV-001\n  kind: design\n  stage: G\n"
                       "  title: Schema/mini-design `roadmap.yaml`\n"
                       "  dependencies: []\n",
                       "- id: RM-GOV-001\n  kind: design\n  stage: G\n"
                       "  title: Schema/mini-design `roadmap.yaml`\n"
                       "  dependencies:\n  - RM-GOV-003\n", 1), True,
         effective=lambda w: _deps_of(w, "RM-GOV-001") == ["RM-GOV-003"])

    case("проекция расходится со входом", "drift",
         lambda w: sub(w, ROADMAP_YAML, "title: Reconciliation/migration manifest",
                       "title: Reconciliation/migration manifest (tampered)", 1), True)
    case("проекция правлена руками", "drift",
         lambda w: _bump_number(w, GENERATED_DIR / "roadmap.generated.md", "Всего задач"), True)

    case("metrics.json правлен руками", "metrics",
         lambda w: sub(w, METRICS_JSON,
                       f'"blocked": {_count_in_metrics(w, "features", "blocked")}',
                       f'"blocked": {_count_in_metrics(w, "features", "blocked") - 1}', 1), True)
    case("PROJECT_STATE заявляет неверную тройку registry", "metrics",
         lambda w: _bump_triple(w), True)
    case("историческая тройка registry в PROJECT_STATE изменена — гейт зелёный (запись на дату)", "metrics",
         lambda w: _bump_historical_triple(w), False)
    case("маркер Registry (current) удалён из PROJECT_STATE", "metrics",
         lambda w: sub(w, "PROJECT_STATE.md", "**Registry (current):**", "**Registry (историческая):**", 1), True)
    case("утверждение исчезло из канона — проверка ослепла", "metrics",
         lambda w: (w / "PROJECT_STATE.md").write_text(
             (w / "PROJECT_STATE.md").read_text(encoding="utf-8")
             .replace(_triple_text(w), "registry без изменений"),
             encoding="utf-8"), True)

    case("ADR-020 отсутствует — правило нигде не записано", "doc",
         lambda w: (w / ADR_020).unlink(), True)
    case("ADR-020 ссылается на правило, но не формулирует его", "doc",
         lambda w: sub(w, ADR_020, "Код и тесты описывают фактическое поведение",
                       "См. решение владельца OD-001", 1), True)
    case("ADR-020 понижен из ACCEPTED", "doc",
         lambda w: sub(w, ADR_020, "**Status:** ACCEPTED", "**Status:** PROPOSED", 1), True)
    case("порядок истины разошёлся между AGENTS.md и CLAUDE.md", "doc",
         lambda w: sub(w, "CLAUDE.md", "3. `PROJECT_STATE.md`\n4. `docs/product/feature-registry.yaml`",
                       "3. `docs/product/feature-registry.yaml`\n4. `PROJECT_STATE.md`", 1), True,
         effective=lambda w: _truth_chain((w / "CLAUDE.md").read_text(encoding="utf-8"))
                             != TRUTH_ORDER)
    case("диапазоны ADR разошлись между README и AGENTS.md", "doc",
         lambda w: sub(w, ARCH_README, "ADR-001..ADR-020", "ADR-001..ADR-015", 1), True)
    case("документ с баннером убран из Superseded-таблицы", "doc",
         lambda w: sub(w, ARCH_README, "| `erd-v2-5-a2.md` |", "| `erd-v2-5-a2.md.disabled` |", 1),
         True)
    case("документ перечислен как superseded, но баннера не несёт", "doc",
         lambda w: sub(w, "docs/architecture/erd-v2-5-a2.md", "<!--\nSUPERSEDED:",
                       "<!--\nHISTORICAL:", 1), True)
    # Регрессия, найденная владельцем при проверке Gate G: документ, который лишь
    # УПОМИНАЕТ слово SUPERSEDED, ошибочно считался вытесненным. Кейс зелёный —
    # он охраняет отсутствие ложного срабатывания, а не наличие находки.
    case("документ лишь упоминает слово SUPERSEDED — не находка", "doc",
         lambda w: (w / "docs/architecture/prose-about-banners.md").write_text(
             "# Про баннеры\n\nЗдесь описан баннер `SUPERSEDED`, но документ не вытеснен.\n",
             encoding="utf-8"), False)

    case("новый ADR вне индекса и вне объявленных исключений", "doc",
         lambda w: (w / "docs/architecture/adr/ADR-021-experimental.md").write_text(
             "# ADR-021\n\n**Status:** ACCEPTED\n", encoding="utf-8"), True)

    case("окружение объявлено доказательным без закреплённого git_sha", "env",
         lambda w: sub(w, ENV_INVENTORY,
                       "      git_sha: 27dc39707c5c56cdfdcc4250d5aa875d3789c8dc\n", "", 1), True)
    case("недостижимое окружение объявлено доказательным", "env",
         lambda w: _set_env(w, "preview-77", "evidence", True), True,
         effective=lambda w: _env_field(w, "preview-77", "evidence") is True)
    case("контур без идентичности объявлен доказательством", "env",
         lambda w: _set_env(w, "santa2-prod", "evidence", True), True,
         effective=lambda w: _env_field(w, "santa2-prod", "evidence") is True)
    case("decommissioned без ссылки на решение владельца", "env",
         lambda w: _set_env(w, "preview-77", "owner_decision", None), True,
         effective=lambda w: _env_field(w, "preview-77", "owner_decision") is None)
    case("decommissioned по решению, которого нет в SSOT", "env",
         lambda w: _set_env(w, "preview-77", "owner_decision", "OD-999"), True,
         effective=lambda w: _env_field(w, "preview-77", "owner_decision") == "OD-999")
    case("decommissioned без даты решения", "env",
         lambda w: _set_env(w, "preview-77", "owner_decision_on", None), True,
         effective=lambda w: _env_field(w, "preview-77", "owner_decision_on") is None)
    case("диспозиция вне допустимых для роли", "env",
         lambda w: _set_env(w, "preview-77", "disposition", "мёртв"), True,
         effective=lambda w: _env_field(w, "preview-77", "disposition") == "мёртв")
    case("baseline стенда разошёлся с sequencing SSOT", "env",
         lambda w: sub(w, ENV_INVENTORY, "      bundle: stand-27dc397",
                       "      bundle: stand-deadbee", 1), True)
    # Тот же охранный кейс, что для SUPERSEDED: слово в прозе не должно
    # превращаться в находку — правило читает структурное поле disposition.
    case("слово «мёртв» в пояснении, а не в disposition — не находка", "env",
         lambda w: _set_env(w, "stand-81", "notes",
                            "Слова «мёртв» и «выведен из эксплуатации» здесь только "
                            "упоминаются; диспозиция задаётся полем disposition."), False,
         effective=lambda w: "мёртв" in (_env_field(w, "stand-81", "notes") or ""))

    case("registry заявляет reachable без существующего smoke", "registry",
         lambda w: sub(w, REGISTRY_YAML, "smoke: test_uismoke__campaign__create",
                       "smoke: test_uismoke__campaign__create_NONEXISTENT", 1), True)
    case("reachable UI-функция выпала из ci-subset", "registry",
         lambda w: sub(w, CI_SUBSET, "campaign__create\n", "", 1), True)

    case("второй конкурирующий источник последовательности", "SSOT",
         lambda w: shutil.copy2(w / ROADMAP_YAML, w / "docs/product/roadmap-v2.yaml"), True)
    case("с проекции снята метка «не редактировать»", "SSOT",
         lambda w: sub(w, GENERATED_DIR / "roadmap.generated.md", READONLY_MARKER, "черновик", 1),
         True)
    case("README сгенерированного каталога удалён", "SSOT",
         lambda w: (w / GENERATED_DIR / "README.md").unlink(), True)
    case("новый необъявленный мутатор roadmap", "SSOT",
         lambda w: (w / "scripts" / "quick_roadmap_fix.py").write_text(
             "from pathlib import Path\n"
             "Path('docs/product/roadmap.md').write_text('переписано')\n",
             encoding="utf-8"), True)

    width = max(len(n) for _, n, _, _ in cases)
    dim_w = max(len(d) for d, _, _, _ in cases)
    failed = sum(1 for _, _, ok, _ in cases if not ok)
    for dim, name, ok, why in cases:
        line = f"  [{'PASS' if ok else 'FAIL'}] {dim.ljust(dim_w)}  {name.ljust(width)}"
        if why:
            line += f"   ← {why}"
        print(line)
    dims = sorted({d for d, _, _, _ in cases})
    print(f"\n[roadmap-governance-guard] self-test: {len(cases) - failed}/{len(cases)} passed")
    print(f"  измерения: {', '.join(dims)}")
    return 1 if failed else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="RM-GOV-004 roadmap governance guard")
    ap.add_argument("--root", default=str(REPO_ROOT))
    ap.add_argument("--module", choices=sorted(MODULES))
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    root = Path(args.root).resolve()

    if args.self_test:
        return self_test(root)

    findings = run(root, args.module)
    print()
    if findings:
        print(f"[roadmap-governance-guard] FAIL — {len(findings)} нарушений")
        return 1
    print("[roadmap-governance-guard] PASS — все модули чисты")
    return 0


if __name__ == "__main__":
    sys.exit(main())

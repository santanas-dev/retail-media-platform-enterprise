#!/usr/bin/env python3
"""Roadmap sequencing SSOT validator — RM-GOV-001.

Validates ``docs/product/roadmap.yaml`` against ``docs/product/roadmap.schema.json``
and enforces the semantic rules JSON Schema cannot express.

This module is the *schema-validation module* of the roadmap governance guard.
``RM-GOV-004`` owns the single CI orchestration entrypoint and calls
:func:`validate` from here; this file must not register its own blocking CI job.

Usage:
    python3 scripts/ci/check-roadmap-schema.py                  # validate the default file
    python3 scripts/ci/check-roadmap-schema.py --file PATH      # validate a specific file
    python3 scripts/ci/check-roadmap-schema.py --self-test      # fixture + tamper matrix

Exit: 0 if clean, 1 if any finding.
"""

import argparse
import copy
import json
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCHEMA_PATH = REPO_ROOT / "docs" / "product" / "roadmap.schema.json"
DEFAULT_ROADMAP = REPO_ROOT / "docs" / "product" / "roadmap.yaml"
REGISTRY_PATH = REPO_ROOT / "docs" / "product" / "feature-registry.yaml"
FIXTURE = REPO_ROOT / "scripts" / "ci" / "fixtures" / "roadmap.schema.example.yaml"

# Порядок фаз утверждён владельцем 2026-08-28 (OD-037): Governance → Environment →
# Stabilization → Contracts → Core → Portal → Channels → Analytics/Scale → Production.
STAGE_ORDER = {"G": 0, "E0": 1, "S": 2, "C": 3, "CORE": 4, "U": 5, "CH": 6, "A": 7, "POPS": 8}

# Acceptance kinds a third party can execute or open without asking anyone.
MACHINE_VERIFIABLE = {"command", "ci_job", "behavioral", "ui_smoke", "artifact"}

# Evidence kinds that satisfy an acceptance item's declared verified_by.
# Owner decision 2026-08-26: a task may not reach delivery_status=done while an
# acceptance item names a proof kind that no verified evidence_ref supplies.
# In particular verified_by=ci_job requires an actual ci_run — local execution of
# the same command is evidence of behaviour, not evidence that CI ran it.
EVIDENCE_FOR_VERIFIED_BY = {
    "ci_job": {"ci_run"},
    "command": {"command"},
    "behavioral": {"behavioral"},
    "ui_smoke": {"ui_smoke", "full_journey"},
    "artifact": {"artifact", "adr", "audit_record"},
}

# A ref that names nothing. Matched case-insensitively against the whole trimmed value.
PLACEHOLDER_REFS = {
    "tbd", "todo", "n/a", "na", "none", "-", "--", "---", "—", "?", "??", "...",
    "later", "позже", "уточнить", "будет", "см. выше", "see above",
}


def _schema_findings(doc):
    """JSON Schema layer."""
    import jsonschema

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    out = []
    for err in sorted(validator.iter_errors(doc), key=lambda e: list(e.path)):
        loc = "/".join(str(p) for p in err.path) or "<root>"
        out.append(f"SCHEMA: {loc}: {err.message}")
    return out


def _known_feature_ids():
    if not REGISTRY_PATH.exists():
        return None
    data = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    feats = data.get("features", data) if isinstance(data, dict) else data
    return {f["id"] for f in feats if isinstance(f, dict) and "id" in f}


def _blocked_feature_ids():
    if not REGISTRY_PATH.exists():
        return None
    data = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    feats = data.get("features", data) if isinstance(data, dict) else data
    return {f["id"] for f in feats if isinstance(f, dict) and f.get("status") == "blocked"}


def _semantic_findings(doc):
    """Rules that JSON Schema cannot express."""
    out = []
    tasks = doc.get("tasks", [])
    by_id = {t["id"]: t for t in tasks if "id" in t}
    gate_ids = {g["id"] for g in doc.get("gates", []) if "id" in g}

    # duplicate task ids
    seen = set()
    for t in tasks:
        tid = t.get("id")
        if tid in seen:
            out.append(f"DUPLICATE-ID: {tid} appears more than once")
        seen.add(tid)

    # dangling dependencies
    for t in tasks:
        for dep in t.get("dependencies", []):
            if dep not in by_id and dep not in gate_ids:
                out.append(f"DANGLING-DEP: {t['id']} depends on unknown '{dep}'")

    # dependency cycles (tasks + gates that close stages)
    graph = {t["id"]: [d for d in t.get("dependencies", []) if d in by_id] for t in tasks}
    WHITE, GREY, BLACK = 0, 1, 2
    color = {n: WHITE for n in graph}

    def visit(node, stack):
        color[node] = GREY
        stack.append(node)
        for nxt in graph.get(node, []):
            if color.get(nxt) == GREY:
                cyc = stack[stack.index(nxt):] + [nxt]
                out.append("CYCLE: " + " -> ".join(cyc))
            elif color.get(nxt) == WHITE:
                visit(nxt, stack)
        stack.pop()
        color[node] = BLACK

    for node in list(graph):
        if color[node] == WHITE:
            visit(node, [])

    # stage ordering: a task may not depend on a task from a later stage
    for t in tasks:
        here = STAGE_ORDER.get(t.get("stage"), 99)
        for dep in t.get("dependencies", []):
            dep_task = by_id.get(dep)
            if dep_task and STAGE_ORDER.get(dep_task.get("stage"), 99) > here:
                out.append(
                    f"STAGE-ORDER: {t['id']} (stage {t.get('stage')}) depends on "
                    f"{dep} from later stage {dep_task.get('stage')}"
                )

    # dependency semantics (OD-043): a task may be in_progress/verification/done only
    # when every dependency is closed — a task dependency is done/verification, a gate
    # dependency carries approved_on. Preparing candidate artefacts is allowed before
    # that; starting the task is not.
    gate_by_id = {g.get("id"): g for g in doc.get("gates", []) or []}
    for t in tasks:
        if t.get("delivery_status") not in ("in_progress", "verification", "done"):
            continue
        for dep in t.get("dependencies", []) or []:
            if dep in gate_by_id:
                if not gate_by_id[dep].get("approved_on"):
                    out.append(f"DEP-NOT-CLOSED: {t['id']} is {t['delivery_status']} but gate {dep} "
                               f"is not approved — работа начинается после закрытия зависимостей (OD-043)")
            elif dep in by_id and by_id[dep].get("delivery_status") not in ("done", "verification"):
                out.append(f"DEP-NOT-CLOSED: {t['id']} is {t['delivery_status']} but dependency {dep} "
                           f"is {by_id[dep].get('delivery_status')} — работа начинается после закрытия зависимостей (OD-043)")

    # owner decision lists are sets: a repeated task in blocks or DEC in aliases is a
    # copy/paste error that would silently double-count (Codex finding on RM-GOV-009)
    for od in doc.get("owner_decisions", []) or []:
        for key in ("blocks", "aliases"):
            items = od.get(key) or []
            for dup in sorted({x for x in items if items.count(x) > 1}):
                out.append(f"OD-DUP-ITEM: {od.get('id')}.{key} lists {dup} more than once")

    # single decision registry: a DEC alias may represent exactly one owner decision
    seen_alias = {}
    for od in doc.get("owner_decisions", []) or []:
        for al in od.get("aliases", []) or []:
            if al in seen_alias:
                out.append(f"DEC-ALIAS-DUP: {al} is an alias of both {seen_alias[al]} and {od.get('id')}")
            seen_alias[al] = od.get("id")

    # anti-overclaim: done requires at least one verified evidence ref
    for t in tasks:
        if t.get("delivery_status") == "done":
            refs = t.get("evidence_refs", [])
            if not any(r.get("status") == "verified" for r in refs):
                out.append(
                    f"OVERCLAIM: {t['id']} is delivery_status=done without a verified evidence_ref"
                )

    # done requires evidence of the KIND the acceptance asked for
    for t in tasks:
        if t.get("delivery_status") != "done":
            continue
        have = {r.get("kind") for r in t.get("evidence_refs", []) or []
                if r.get("status") == "verified"}
        for a in t.get("acceptance", []) or []:
            vb = a.get("verified_by")
            accepted = EVIDENCE_FOR_VERIFIED_BY.get(vb)
            if accepted and not (have & accepted):
                out.append(
                    f"EVIDENCE-KIND: {t['id']} is delivery_status=done, acceptance asks for "
                    f"verified_by={vb}, but no verified evidence_ref of kind "
                    f"{'/'.join(sorted(accepted))} is present"
                )

    # an owner gate that was never granted cannot sit behind a done task
    for t in tasks:
        og = t.get("owner_gate") or {}
        if og.get("required") and t.get("delivery_status") == "done" and not og.get("granted"):
            out.append(
                f"OWNER-GATE-UNGRANTED: {t['id']} is delivery_status=done behind an owner "
                f"gate ({og.get('reason')}) that is not recorded as granted"
            )

    # a gate closes a stage only once its approver actually approved it
    stage_of = {t["id"]: t.get("stage") for t in tasks}
    for gate in doc.get("gates", []) or []:
        if gate.get("approved_on"):
            continue
        closed = [t for t in tasks
                  if stage_of.get(t["id"]) == gate.get("closes_stage")
                  and t.get("delivery_status") == "done"
                  and (t.get("owner_gate") or {}).get("reason") == "canon_change"]
        for t in closed:
            out.append(
                f"GATE-NOT-APPROVED: {t['id']} закрыт как done, но {gate['id']} "
                f"(approver {gate['approver']}) не имеет approved_on"
            )

    # owner-verified acceptance implies a declared owner gate
    for t in tasks:
        needs_owner = any(a.get("verified_by") == "owner" for a in t.get("acceptance", []))
        if needs_owner and not t.get("owner_gate"):
            out.append(f"MISSING-OWNER-GATE: {t['id']} has owner-verified acceptance but no owner_gate")

    # machine-verifiable acceptance must carry a concrete, runnable ref
    for t in tasks:
        for i, a in enumerate(t.get("acceptance", [])):
            vb = a.get("verified_by")
            if vb not in MACHINE_VERIFIABLE:
                continue
            ref = (a.get("ref") or "").strip()
            if not ref:
                out.append(
                    f"MISSING-REF: {t['id']} acceptance[{i}] is verified_by={vb} without a ref"
                )
            elif ref.lower() in PLACEHOLDER_REFS or len(ref) < 3:
                out.append(
                    f"VAGUE-REF: {t['id']} acceptance[{i}] verified_by={vb} has a placeholder "
                    f"ref {ref!r} — name the exact command, CI job, test id or artifact path"
                )

    # maturity: ci_enforced and above require explicit proof granularity
    ladder = ["implemented", "automated_verified", "ci_enforced", "stand_deployed",
              "stand_verified", "walkthrough_ok", "pilot_ready", "production_ready"]
    for m in doc.get("maturity", []):
        lvl = m.get("level")
        if lvl in ladder and ladder.index(lvl) >= ladder.index("ci_enforced"):
            if not m.get("proof_granularity"):
                out.append(
                    f"PROOF-GRANULARITY: feature {m.get('feature_id')} at level {lvl} "
                    f"has no proof_granularity"
                )

    # every registry-blocked feature needs an unblock path in the SSOT
    blocked_here = {b.get("feature_id") for b in doc.get("blocked_features", [])}
    for b in doc.get("blocked_features", []):
        for dep in b.get("unblocked_by", []):
            if dep not in by_id:
                out.append(
                    f"UNBLOCK-DANGLING: blocked feature '{b.get('feature_id')}' "
                    f"is unblocked_by unknown task '{dep}'"
                )

    # feature ids must exist in the registry (registry stays the status owner)
    blocked_in_registry = _blocked_feature_ids()
    if blocked_in_registry is not None:
        for fid in sorted(blocked_in_registry - blocked_here):
            out.append(
                f"MISSING-UNBLOCK: feature '{fid}' is blocked in the registry but has no "
                f"blocked_features entry with unblock conditions"
            )

    known = _known_feature_ids()
    if known is not None:
        for m in doc.get("maturity", []):
            if m.get("feature_id") not in known:
                out.append(f"UNKNOWN-FEATURE: maturity references '{m.get('feature_id')}' absent from registry")
        for t in tasks:
            for fid in t.get("feature_ids", []):
                if fid not in known:
                    out.append(f"UNKNOWN-FEATURE: {t['id']} references '{fid}' absent from registry")

    return out


class _DuplicateKeyLoader(yaml.SafeLoader):
    """SafeLoader that refuses duplicate mapping keys.

    yaml.safe_load silently keeps the LAST value for a repeated key. That turned
    a broken edit into a valid-looking document three separate times in this
    workstream: a tamper fixture that stopped tampering, a second one, and an
    evidence_ref whose command was replaced by a run id — each time the file
    parsed cleanly and the validator saw nothing wrong. A duplicate key in a
    hand-edited SSOT is always a defect, never an intention.
    """


def _no_duplicates(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise yaml.constructor.ConstructorError(
                None, None,
                f"дублирующийся ключ {key!r} — YAML молча оставит последний",
                key_node.start_mark)
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_DuplicateKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_duplicates)


def validate(path):
    """Validate one roadmap file. Returns a list of finding strings (empty = clean)."""
    path = Path(path)
    if not path.exists():
        return [f"MISSING-FILE: {path} does not exist"]
    try:
        doc = yaml.load(path.read_text(encoding="utf-8"), Loader=_DuplicateKeyLoader)
    except yaml.constructor.ConstructorError as exc:
        return [f"DUPLICATE-KEY: {exc.problem} ({exc.problem_mark})"]
    except yaml.YAMLError as exc:
        return [f"YAML: {exc}"]
    if not isinstance(doc, dict):
        return ["YAML: top-level document must be a mapping"]
    findings = _schema_findings(doc)
    findings.extend(_semantic_findings(doc))
    return findings


# ---------------------------------------------------------------------------
# Self-test: the fixture must pass, and every tamper must be caught.
# ---------------------------------------------------------------------------

def _tamper_cases(base):
    """Return (label, mutated_doc, expected_finding_prefix) triples."""
    cases = []

    d = copy.deepcopy(base)
    d["tasks"][1]["dependencies"] = ["RM-GOV-999"]
    cases.append(("dangling dependency", d, "DANGLING-DEP"))

    d = copy.deepcopy(base)
    d["tasks"][0]["dependencies"] = [d["tasks"][1]["id"]]
    d["tasks"][1]["dependencies"] = [d["tasks"][0]["id"]]
    cases.append(("dependency cycle", d, "CYCLE"))

    d = copy.deepcopy(base)
    d["tasks"][1]["delivery_status"] = "done"
    d["tasks"][1]["evidence_refs"] = []
    cases.append(("done without verified evidence", d, "OVERCLAIM"))

    # Owner rule 2026-08-26: local execution of the same command is not proof
    # that CI ran it. done + verified_by=ci_job requires a verified ci_run.
    d = copy.deepcopy(base)
    d["tasks"][1]["delivery_status"] = "done"
    d["tasks"][1]["acceptance"] = [
        {"check": "tamper matrix red on every dimension",
         "verified_by": "ci_job", "ref": "roadmap-governance-guard"}
    ]
    d["tasks"][1]["evidence_refs"] = [
        {"kind": "command", "ref": "python3 scripts/ci/roadmap-governance-guard.py",
         "status": "verified"}
    ]
    cases.append(("done on ci_job acceptance with only a local command", d, "EVIDENCE-KIND"))

    d = copy.deepcopy(base)
    d["tasks"][1]["delivery_status"] = "done"
    d["tasks"][1]["acceptance"] = [
        {"check": "tamper matrix red on every dimension",
         "verified_by": "ci_job", "ref": "roadmap-governance-guard"}
    ]
    d["tasks"][1]["evidence_refs"] = [
        {"kind": "ci_run", "ref": "gh run 1234567890", "status": "disputed"}
    ]
    cases.append(("done on ci_job acceptance with a disputed ci_run", d, "EVIDENCE-KIND"))

    # An owner gate exists to stop exactly this: the work closing itself.
    d = copy.deepcopy(base)
    d["tasks"][1]["delivery_status"] = "done"
    d["tasks"][1]["evidence_refs"] = [
        {"kind": "command", "ref": "python3 scripts/ci/check-roadmap-schema.py",
         "status": "verified"}
    ]
    d["tasks"][1]["acceptance"] = [
        {"check": "canon updated", "verified_by": "command",
         "ref": "python3 scripts/ci/check-roadmap-schema.py"}
    ]
    d["tasks"][1]["owner_gate"] = {"required": True, "reason": "canon_change"}
    cases.append(("done behind an owner gate that was never granted", d,
                  "OWNER-GATE-UNGRANTED"))

    d = copy.deepcopy(base)
    d["tasks"][0]["id"] = "RM-BOGUS-001"
    cases.append(("id outside approved prefixes", d, "SCHEMA"))

    d = copy.deepcopy(base)
    d["tasks"][0]["kind"] = "refactor"
    cases.append(("kind outside taxonomy", d, "SCHEMA"))

    d = copy.deepcopy(base)
    d["maturity"][0]["level"] = "ci_enforced"
    d["maturity"][0].pop("proof_granularity", None)
    cases.append(("ci_enforced without proof_granularity", d, "PROOF-GRANULARITY"))

    d = copy.deepcopy(base)
    d["tasks"][0]["acceptance"] = [{"check": "owner approves", "verified_by": "owner"}]
    d["tasks"][0].pop("owner_gate", None)
    cases.append(("owner acceptance without owner_gate", d, "MISSING-OWNER-GATE"))

    d = copy.deepcopy(base)
    d["tasks"][2]["stage"] = "G"
    cases.append(("stage depends on later stage", d, "STAGE-ORDER"))

    # OD-043: starting a task whose dependency is still open (task or gate)
    d = copy.deepcopy(base)
    d["tasks"][2]["delivery_status"] = "in_progress"      # RM-STAB-002 ← RM-STAB-001 (planned)
    cases.append(("in_progress with an open task dependency", d, "DEP-NOT-CLOSED"))

    d = copy.deepcopy(base)
    d["tasks"][3]["delivery_status"] = "in_progress"      # RM-STAB-001 ← Gate-G (not approved in fixture)
    cases.append(("in_progress behind an unapproved gate", d, "DEP-NOT-CLOSED"))

    d = copy.deepcopy(base)
    d["tasks"][0]["percent_complete"] = 91
    cases.append(("percentage field smuggled in", d, "SCHEMA"))

    d = copy.deepcopy(base)
    d["tasks"][3]["acceptance"][0].pop("ref", None)
    cases.append(("machine-verifiable acceptance without ref", d, "SCHEMA"))

    d = copy.deepcopy(base)
    d["tasks"][3]["acceptance"][0]["ref"] = "TBD"
    cases.append(("machine-verifiable acceptance with placeholder ref", d, "VAGUE-REF"))

    d = copy.deepcopy(base)
    d["blocked_features"] = [b for b in d.get("blocked_features", [])][1:]
    cases.append(("blocked feature without unblock path", d, "MISSING-UNBLOCK"))

    d = copy.deepcopy(base)
    if d.get("blocked_features"):
        d["blocked_features"][0]["unblocked_by"] = ["RM-TECH-999"]
    cases.append(("unblock path points at unknown task", d, "UNBLOCK-DANGLING"))

    d = copy.deepcopy(base)
    d["owner_decisions"][1]["aliases"] = list(d["owner_decisions"][0]["aliases"])
    cases.append(("same DEC alias on two owner decisions", d, "DEC-ALIAS-DUP"))

    d = copy.deepcopy(base)
    d["owner_decisions"][0]["aliases"] = d["owner_decisions"][0]["aliases"] * 2
    cases.append(("same DEC alias twice inside one owner decision", d, "OD-DUP-ITEM"))

    d = copy.deepcopy(base)
    d["owner_decisions"][1]["blocks"] = [d["tasks"][0]["id"], d["tasks"][0]["id"]]
    cases.append(("same task twice in owner decision blocks", d, "OD-DUP-ITEM"))

    return cases


def _raw_tamper_cases(base_text):
    """Tampers that only exist at the text level — a parsed doc cannot hold them."""
    marker = "    decision_status: approved\n"
    assert marker in base_text, "фикстура устарела: якорь для дубликата ключа не найден"
    dup = base_text.replace(marker, marker + "    decision_status: rejected\n", 1)
    return [("duplicate mapping key", dup, "DUPLICATE-KEY")]


def _self_test():
    ok = True
    findings = validate(FIXTURE)
    if findings:
        print("[roadmap-schema self-test] FAIL — fixture itself is not clean:")
        for f in findings:
            print("   ", f)
        return False
    print(f"[roadmap-schema self-test] fixture clean: {FIXTURE.relative_to(REPO_ROOT)}")

    base = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
    for label, mutated, expected in _tamper_cases(base):
        got = _schema_findings(mutated) + _semantic_findings(mutated)
        caught = any(f.startswith(expected) for f in got)
        print(f"    tamper: {label:44} -> {'CAUGHT' if caught else 'MISSED'} ({expected})")
        if not caught:
            ok = False

    # Text-level tampers: a parsed document cannot represent a duplicate key,
    # so these must go through validate() on real bytes.
    import tempfile as _tf
    for label, text, expected in _raw_tamper_cases(FIXTURE.read_text(encoding="utf-8")):
        tmp = Path(_tf.mkdtemp()) / "raw.yaml"
        tmp.write_text(text, encoding="utf-8")
        caught = any(f.startswith(expected) for f in validate(tmp))
        print(f"    tamper: {label:44} -> {'CAUGHT' if caught else 'MISSED'} ({expected})")
        if not caught:
            ok = False
    return ok


def main():
    ap = argparse.ArgumentParser(description="Validate the roadmap sequencing SSOT (RM-GOV-001).")
    ap.add_argument("--file", default=str(DEFAULT_ROADMAP), help="roadmap YAML to validate")
    ap.add_argument("--self-test", action="store_true", help="run fixture + tamper matrix")
    args = ap.parse_args()

    if args.self_test:
        ok = _self_test()
        print("\n[roadmap-schema] self-test PASS" if ok else "\n[roadmap-schema] self-test FAIL")
        sys.exit(0 if ok else 1)

    findings = validate(args.file)
    if findings:
        print(f"[roadmap-schema] FAIL — {len(findings)} finding(s) in {args.file}:")
        for f in findings:
            print("   ", f)
        sys.exit(1)
    print(f"[roadmap-schema] PASS — {args.file}")
    sys.exit(0)


if __name__ == "__main__":
    main()

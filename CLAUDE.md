# CLAUDE.md — Retail Media Platform Enterprise

Operating contract for Claude Code in this repository. Read together with
`AGENTS.md` (product/architecture contract, Done Gate, protected boundaries).
This file holds only durable rules — never volatile SHAs, counts, CI run IDs,
or the current "Next" item. Those live in Git and `PROJECT_STATE.md`.

## Roles

- **Human owner** — final approver. Approves architecture, external actions,
  merge, release, and deployment. Nothing in those categories happens without
  an explicit owner instruction for that specific action.
- **Codex** — architect and reviewer. Produces design and audit input; does not
  implement.
- **Claude Code** — sole implementation agent.
- **Hermes** — retired. Hermes skills, Hermes memory rules, and Hermes-owned
  automation in `AGENTS.md` are historical; do not act on them and do not
  re-enable them without an owner instruction.

## Truth Priority

When sources disagree, the higher level wins:

1. Newest owner instruction
2. Git / code / tests / CI
3. `PROJECT_STATE.md`
4. `docs/product/feature-registry.yaml`
5. Roadmap, architecture docs (ADRs, ERD, API contracts), runbooks
6. Auto-memory

**A contradiction between sources means STOP.** Report the conflict with both
sources quoted; do not resolve it yourself, do not "fix" the lower source, and
do not pick the more convenient reading.

## Before Every Task

1. Verify repository root, branch, `HEAD`, and `git status` before touching
   anything.
2. Read the relevant code, the relevant tests, and the relevant canon
   (`PROJECT_STATE.md`, feature registry, ADRs, runbooks) before proposing or
   making a change.
3. Restate the exact task and scope; name the domain boundary being touched.
4. Preserve unrelated changes made by others. Never revert, rewrite, or
   discard work you did not author.
5. Do not start the next task automatically. One assigned task, then stop and
   wait for owner review.

## Definition of Done

**Done = proven behavior, not a report.** A claim is only as good as the
command output behind it. Never write that something passes, is green, is
reachable, or is deployed unless it was actually executed and observed in this
session.

- Use the existing architecture. No parallel models, no new frameworks, no
  broad refactors to make a narrow change fit.
- Keep scope narrow: the smallest coherent change that proves the behavior.
- **RLS** claims require PostgreSQL proof executed as `retail_media_app` with
  `NOBYPASSRLS`. SQLite runs, source inspection, and superuser sessions are not
  RLS proof.
- **UI** verification requires state-based browser waits (visibility, enabled
  state, network idle, expected text). No `sleep`, no retry loops, no timing
  hacks that mask a real failure.
- **`reachable`** is set in the feature registry only after the proof that
  status requires. Registry counts are computed programmatically from the file,
  never hand-tallied.
- **Operator walkthrough** is set by a human only. The agent may write
  `PENDING` and nothing else, and never closes a journey or wave on that line.

## Forbidden in Tests and CI

Never use these to make a pipeline or suite look green:

- `skip`, `xfail`, `deselect`, or narrowing test selection to dodge failures
- weakened, removed, or inverted assertions
- `continue-on-error`, swallowed exit codes, or any pipeline masking
- reordering or disabling steps so a failure stops being visible

If something legitimately cannot run, say exactly what did not run and why.

CI commands are taken verbatim from `.github/workflows/phase1-ci.yml` — do not
invent local equivalents. Run piped commands under `set -o pipefail` so a
failure upstream of a pipe is not hidden.

## Git and External Actions

Never, under any circumstance:

- `git push --force` / `-f`, or any history rewrite
- `git reset --hard`, `git clean` against uncommitted work
- move, delete, or re-point tags
- bypass rulesets or branch protection
- push directly to `main`

Ordinary `git push` of a feature branch or `develop` is allowed **only** inside
a task where the owner explicitly asked for it.

Owner approval is required, per action, for: merge, release, package deletion
or visibility/access changes, GitHub repository settings, and deployment.

## Secrets

Never read, print, echo, copy, or summarize `~/.ssh/**`,
`~/.config/gh/hosts.yml`, `gh auth token`, `.env` files with real values, or any
credential. Report auth state as identity and scope only.

## Communication

- User-facing communication is Russian by default unless the owner requests
  another language.
- Progress updates and final reports are concise and decision-oriented.
- Default final report: status, changes, verification, blockers, next step.
- Do not paste full logs or large tables unless explicitly requested.
- Distinguish DONE, PENDING and BLOCKED without overclaim.

## Reporting

Every task report states:

- **Files** changed (paths)
- **Behavior** — what actually changed, observably
- **Tests** — what was run, with real results
- **CI** — run and attempt for the relevant workflow
- **Debt** — what was left undone, weakened, or deferred
- **git status** — working tree state at the end
- **External actions** — every push, API call, or GitHub mutation performed,
  or an explicit "none"

Short and concrete. No "all tests pass" without having run them.

Welcome, AGENT.

AGENT is you: a large language model working with this codebase.
This is the canonical repository-level instruction file. It replaces README.txt,
AGENTS.md, CLAUDE.md, and similar repository prompt files as a source of project
instructions. Higher-priority platform instructions still apply.

Our car is currently: UNAVAILABLE

UNAVAILABLE means that you cannot access the SCHOOL, where the physical car is stored
and tested. It does not mean that the car is imaginary or unbuilt. The hardware is
fully built and ready to be tested; the software is the unfinished part. Until the car
is available again, do not claim physical results for the current software.

SCHOOL is the environment where the car is stored and tested.
STARTECH is the team. Do not call STARTECH "our team" or "us". Address the team as
"you" or "the STARTECH team".

---

What is this project?

This is an autonomous vehicle project. The car completes a multi-task track using
camera-based perception. The car may be prepared for different races, but the
camera-only rule is a project invariant: do not add another sensor as a shortcut.

The canonical current modules are YAREN, KASIM, KEREM, DORA, KADER, TAWNT, OSMAN,
ARDA, CAM, and SAC. Do not revive retired module aliases in current documentation or
new code.

---

How are features implemented?

Car features do not use production simulations, fake drivers, generated observations,
or pretend readiness reports. A feature is real or unfinished. If the real path is
implemented but cannot yet be physically exercised, mark it PHYSICALLY UNVERIFIED and
say what observation is missing.

The explicit Webots environment is separate and remains isolated under `sim/`. It is
never evidence for the physical car.

Tests are approved under `tests/` for stress, regression, and contract checking. Test
fixtures and call recorders stay inside tests. They prove software behavior only and
must never become a production vehicle mode or physical evidence.

Replaying actual camera recordings is real analysis of recorded data. It is not a
simulation, and it is not evidence that a camera or car is connected now.

A signed linked-camera receipt proves that the named physical camera produced that
frame in that session. It does not prove that saved calibration values fit the school
track, that KEREM interpreted them correctly there, or that the car can drive.

---

What work needs approval?

Bug fixes, migrations from useful LEGACY behavior, refactors, and requested features
do not need a pre-approval plan. Inspect the current code, make the change, verify it,
update the current state in `PLAN.md`, and explain the result afterwards.

Ask for pre-approval before an irreversible strategic change or a large change that
materially replaces the current direction. Examples include replacing YAREN, abandoning
the current architecture for a "LEGACY V2", or combining several substantial ARDA
changes into one rewrite. Approval to change code is not approval to run the car.

For a pre-approval, explain the intended outcome, affected boundaries, important risks,
rollback path, and why the change is large or irreversible. Do this in chat; do not fill
the repository with speculative pre-action plans.

---

How is Git used?

- Preserve existing uncommitted work. It belongs to the user unless proven otherwise.
- Ordinary bug fixes and small UI changes may be committed and pushed directly to
  `master` after verification.
- Use a secondary branch for pre-approved work and for changes whose severity makes a
  direct `master` update dangerous.
- Commit verified logical changes automatically. Commit history is part of the recovery
  and evidence system.
- Agents may push their commits. Never force-push, rewrite history, or erase unrelated
  commits.
- Do not discard, reset, or overwrite user changes to obtain a clean tree.

---

How is `PLAN.md` used?

`PLAN.md` is the single current-state and future-work document. It is not a recreation
script and does not preserve obsolete implementation steps. Current source and tests
remain the final authority for implemented behavior.

When a logical part is finished, update its status and remaining work in `PLAN.md` in
the same commit. Remove instructions that would make a later agent rebuild completed
work. Keep the real roadmap detailed, but do not invent dates, percentages, APIs, or
physical results.

If work is interrupted, temporarily add an `Active work` section containing the goal,
current state, completed commits, blocker, next action, and remaining verification. List
exact changed files when the work is uncommitted. Remove that section when the work is
finished.

Old plans and PDFs are historical or post-mortem records. Keep them when they explain
the timeline, but never treat them as instructions. `PLAN.md` points to the current
official competition sources instead of copying rules that can become stale.

---

Which status words are allowed?

- `IMPLEMENTED`: a real code path exists and its stated software contract is checked.
- `PHYSICALLY UNVERIFIED`: the real path exists, but the required car-side observation
  has not happened or is not recorded.
- `PHYSICALLY VERIFIED`: dated physical evidence demonstrates the exact stated behavior.
- `NOT IMPLEMENTED`: no real end-to-end path exists yet.
- `VALIDATED`: TAWNT accepted one specific command, profile, value, or relationship.

Never use `VALIDATED` as a synonym for whole-feature, vehicle, or driving readiness. A
receipt or log can prove that software requested an
output or stop; it cannot prove that a wheel moved, steered, braked, or stopped.

---

What rules apply to live output?

Physical output needs the operator's legal name and a current time record. Before an
LLM triggers live output, show a clear warning and allow seven seconds to cancel. SAC
owns this countdown in the browser. Outside SAC, the LLM must give the same warning and
wait seven seconds before invoking the real command.

Keep a visible warning while output is queued or may be active. Treat SIGINT/Ctrl+C as
an immediate stop instruction: stop the LLM action, request zero output, and do not
continue automatically. A software stop request never replaces access to physical
power removal.

Start physical work at the smallest useful energy and duration, with wheels secured,
the path clear, and a person able to remove motor power. Never interpret repository
approval as live-hardware authorization.

---

How should an agent work?

- Read this file, `PLAN.md`, and the current source that owns the requested behavior.
- Use `PROJECT_MAP.md` to find the active path. Do not follow historical names into a
  different system.
- Prefer the smallest real implementation that advances the car.
- Continue useful work while the car is unavailable: real camera capture, recorded-data
  analysis, configuration, logging, migration, regression checks, and documentation.
- Add a regression test for a bug when practical. Test failure must remain capable of
  blocking a bad commit.
- Use current official competition pages before changing a rule-dependent feature.
- Treat people as professionals. Do not invent personal authority hierarchies, forced
  praise, or nonsense stories in change logs.
- Write governing documentation in English. Preserve Turkish historical records as
  history.
- Keep secrets, personal data, school identity, and credentials out of prompts, logs,
  commits, and reports.

After changing anything, report in chat: the outcome, important files, verification,
commit, physical boundary, and any remaining uncertainty. Be concise enough to read and
detailed enough to make the result auditable.

ARCHIVED GOVERNING DOCUMENT — retained for history only. Do not use this file as the
current repository instruction source.

Welcome, AGENT.

AGENT is you: a large language model working with this codebase. This is the
canonical repository-level instruction file. Higher-priority platform instructions
still apply.

The car is currently: UNAVAILABLE

UNAVAILABLE means the STARTECH team cannot currently access SCHOOL, where the
physical car is stored. The car exists and is built. Do not mistake temporary lack
of access for nonexistent hardware, and do not claim new physical results while it
is unavailable.

STARTECH is the team. Address the team as "you" or "the STARTECH team", not "us".

## What this repository is

This is a camera-only autonomous vehicle project. The retained systems are:

- `LEGACY/`: the active vehicle-code baseline. This lineage ran the competition
  car. It is imperfect, but its real behavior and known defects are more valuable
  than an untested replacement architecture.
- `startech_cam/`: KERİM, the web calibration and maintenance service. Its old CAM
  package, environment, service, and URL names are compatibility contracts.
- `startech/tawnt/` and `tawnt.py`: TAWNT, a readable validation library available
  for small, justified integrations into the vehicle code.
- `startech/configuration/` and `config/`: configuration code still required by
  KERİM. They do not currently replace `LEGACY/config.py`.
- `tests/`: software checks for the retained systems.
- `Markdown/` and the root documents: current guidance and historical records.

The canonical current modules are YAREN, KASIM, KEREM, DORA, KADER, TAWNT, OSMAN,
ARDA, ADAM, KERİM, and SAC. ADAM owns the local audible/visible run warning and its
named state indications. KERİM means "Kalibrasyon Erişim, Revizyon İnceleme
Merkezi." Do not revive retired module aliases in current documentation or
new code.

Do not recreate the deleted `arac/` stack, Webots scaffolding, project-control
machinery, fake vehicle modes, or chains of modules that merely approve one another.
If useful names such as ARDA, KASIM, KEREM, DORA, KADER, or OSMAN return, put the
names directly on clear LEGACY responsibilities. Do not add wrappers just to obtain
more named layers.

## Real, unfinished, or historical

A vehicle feature is real or unfinished. Never add a production fake driver,
generated observation, simulated readiness result, or status that pretends the car
was exercised. Tests may use controlled fixtures under `tests/`; they prove only the
software behavior they assert.

Use these status terms precisely:

- `IMPLEMENTED`: the real code path exists and its stated software behavior is checked.
- `PHYSICALLY UNVERIFIED`: the real path exists, but the required car-side result has
  not yet been observed or recorded.
- `PHYSICALLY VERIFIED`: dated physical evidence supports the exact claim.
- `NOT IMPLEMENTED`: the real path is absent or incomplete.
- `VALIDATED`: TAWNT accepted one declared value or command. This is never proof that
  the vehicle moved, steered, or stopped.

Old PDFs and Markdown records are post-mortems and timeline evidence, not current
instructions. Preserve them. The active direction is in `PLAN.md`; current source and
tests remain the authority for implemented behavior.

## How to change the vehicle code

- Start from the competition code in `LEGACY/` and its documented failure modes.
- Prefer a small, understandable correction over a general framework.
- Do not rewrite a working subsystem merely to modernize its shape.
- Preserve original evidence while repairing defects. When practical, add a focused
  regression check beside a software-only fix.
- A standalone calibration tool may eventually replace the scattered LEGACY tuning
  scripts. KERİM may expose those concrete controls, but it must not invent values or
  silently rewrite `LEGACY/config.py`.
- The car must remain capable of local, offline race operation. KERİM is useful, not a
  boot dependency. Remote start/stop is unfinished until a small explicit adapter is
  implemented and physically checked.

Local vehicle start must not require a legal name or a theatrical word such as
`OUTPUT`. For a future remote physical command, KERİM can record the authenticated
operator and server time automatically. Any physical-output path must display a clear
warning, allow cancellation before motion, and treat SIGINT/Ctrl+C as an immediate
request to stop and remain stopped. A software stop request does not prove the motor
power physically disappeared.

## Approval and Git

Bug fixes, careful migrations from LEGACY, refactors, documentation corrections, and
requested features do not need speculative pre-approval plans. Explain completed work
afterward and update `PLAN.md` when the current state changes.

Ask before an irreversible strategic replacement: abandoning the LEGACY baseline,
replacing KERİM or TAWNT, rewriting several major areas together, deleting historical
evidence, or changing repository history. Approval to edit code is never permission to
run the physical car.

Preserve user work. Do not reset, overwrite, or discard unrelated uncommitted changes.
Use a branch for dangerous strategic changes and ordinary commits for normal fixes.
Never force-push or rewrite history. Commit history is the recovery mechanism.

## How to report work

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

KERİM's autonomous-run request is a separate, stricter path: ADAM on the vehicle owns an
exact 30-second warning. Do not shorten or skip it. KERİM may request and observe one run,
but ARDA remains the execution authority. If the authenticated heartbeat is lost, the
vehicle requests zero output, records `RUN_HALT_NOCON`, and requires local manual
activation. The server-retained KADER stream is software evidence, not proof of motion.

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

After a change, report the outcome, important files, verification, commit, remaining
uncertainty, and whether physical verification is still required. Be readable and
direct. Do not produce ceremonial safety prose, forced praise, fictional stories, or
pages of pre-action planning.

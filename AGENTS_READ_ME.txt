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

After a change, report the outcome, important files, verification, commit, remaining
uncertainty, and whether physical verification is still required. Be readable and
direct. Do not produce ceremonial safety prose, forced praise, fictional stories, or
pages of pre-action planning.

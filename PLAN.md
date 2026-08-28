# STARTECH current state and plan

Updated: 28 August 2026

This is the current project plan. It describes what exists now, what is trusted,
and what should happen next. It is not a reconstruction guide for abandoned
architectures. Source code, physical observations, the technical handover guide,
and Git history provide the underlying evidence.

## 1. The project

STARTECH is a camera-only autonomous vehicle built for a multi-task competition
track. The physical car exists and is stored at SCHOOL. The team cannot access it
at present, so new physical claims cannot be made until access resumes.

The vehicle software baseline is the code under `LEGACY/`. Despite the directory
name, this is not merely an obsolete reference: this lineage was used during the
race. The retained checkout is nearly identical to the race version and is the best
available working foundation.

The race software was not perfect. It made assumptions about the competition track,
including track lengths and event timing, and its known failures are recorded in the
HATA DEFTERI material. Those concrete limitations are preferable to replacing the
runtime with a larger system that has never driven the car.

## 2. Current boundaries

### `LEGACY/` — active vehicle runtime

`LEGACY/` owns physical vehicle behaviour. Its readable modules cover configuration,
camera acquisition, lane perception, control, motors, event handling, and logging.
The expected starting point is `LEGACY/main.py`.

The folder will keep the name `LEGACY`. Current documentation must explicitly say
that it is active so nobody mistakes the name for a deprecation notice.

The runtime should remain locally operable without KERIM, internet access, a web
login, or a remote configuration service.

### KERIM — optional web tooling

KERIM is the web calibration, maintenance, download, and remote-access service under
`startech_cam/`, with its server support under `deployment/`. Existing package,
environment, service, and URL names containing `CAM` remain compatibility names.

KERIM is useful, but it is not the authority that grants the car permission to use
its own configuration. It must not become a boot dependency for a local race run.

The new internet-operated dashboard belongs inside KERIM. It will be a small wrapper
around real programs on the car, not a replacement vehicle runtime.

### TAWNT — retained optional library

TAWNT remains available for a future concrete use. It is not currently part of the
competition driving loop, and documentation must not imply otherwise. Integration
should happen only when one readable check solves an observed problem; TAWNT must not
be expanded into another chain of approvals.

### `arac/` — not the active vehicle baseline

The newer `arac/` architecture is not the code selected to run the car. It may remain
at the repository root temporarily, with an unmistakable retirement warning, while
its final archival presentation is designed. It must not be described as active and
must not be selected by default by humans, agents, deployment tools, or guides.

### `Secondary/` — supporting and historical material

`Secondary/` is not a home for active KERIM runtime files. It may hold historical
records, retired material, design references, and other non-runtime resources. Its
contents will be organised after the root documentation is corrected.

## 3. Evidence and truthful language

The following physical observations are part of the project record:

- this code lineage produced real motor output and moved the competition car;
- the camera detected the real green start light;
- lane detection operated, although lane following was weak;
- the car performed at least some slow lane following at school;
- known competition failures and observations were recorded afterward.

These observations establish why `LEGACY/` is the baseline. They do not prove that
every current file is perfect, that the checkout is byte-for-byte identical to the
last on-site copy, or that changed track assumptions remain correct.

Current documents should use ordinary descriptions:

- **working** — observed doing the stated job;
- **not retested on the car** — real code exists but has not been physically checked
  since the relevant change;
- **unfinished** — the real functionality is absent or incomplete;
- **historical** — preserved evidence or an old direction, not a current instruction.

Software checks prove only the software behaviour they exercise. Generated claims
such as estimated score gains, universal safety, or "5/5 tested" are not physical
evidence unless a dated record identifies what was actually tested.

## 4. No fake vehicle behaviour

Production vehicle code must be real or unfinished. It must not report fake camera
observations, fake readiness, simulated motor success, or generated physical results.

Webots is a separate visual simulation environment and may be used when explicitly
identified as Webots. It is never evidence that the physical car moved or passed a
hardware test.

Software tests are permitted under `tests/`. Controlled fixtures and mocks are useful
for checking isolated software rules, but their output must not be presented as a car
test.

When GPIO or other required Raspberry Pi hardware support is unavailable, a program
that would control motors should stop with a clear error before attempting output.
Explicit Windows and USB-camera tools may operate through OpenCV `VideoCapture`; that
is a real alternate camera input, not a pretend Raspberry Pi motor environment.

## 5. Vehicle configuration and calibration

`LEGACY/config.py` is currently the authoritative configuration consumed by the
vehicle runtime.

KERIM may store, display, and edit calibration data, but a stored JSON profile does
not automatically become a vehicle configuration. A small explicit converter may be
added that reads a supported JSON schema and produces a Python configuration class or
other input that LEGACY deliberately imports. Conversion must be visible,
deterministic, and reversible; it must not silently rewrite working code.

The existing LEGACY calibration and tuning utilities will remain until their actual
capabilities have been inventoried. After that inventory, overlapping tools may be
consolidated into one understandable standalone calibration program. Consolidation
must preserve concrete controls and useful diagnostics rather than merely hiding
them behind a new interface.

The known KERIM MAC problem remains valid: frame dimensions and perspective can form
a circular validation deadlock, and editing the stored file externally changes its
hash. The eventual fix should allow related fields to be edited and validated as one
atomic draft. It should not remove integrity checking from unrelated records.

## 6. KERIM remote dashboard

The dashboard will expose a small set of real operations:

- motorless software test;
- motor test;
- lane-following test;
- remote driving;
- current and previous logs;
- information about the files/version on the car.

The car runs the selected local Python program. KERIM sends the request and displays
the program's real output; it does not recreate the program on the server or replace
its result with a summary claiming success.

The useful connection role previously associated with YAREN will be replaced by a
small, readable `remote.py` bridge. The old configuration-authority behaviour is not
part of the new design.

### Connection behaviour

- The dashboard clearly displays whether `remote.py` is connected.
- Controls that require the car remain unavailable until the car responds.
- A remotely controlled or remotely supervised motor test stops safely when its
  connection is lost.
- A local autonomous run does not require a continuing internet connection.
- Standard output and standard error are streamed as the real run log and should also
  be saved by the car where practical.

### Start behaviour

Before a remote action that can move the vehicle:

1. show the concise warning that a second person may be needed to watch the car;
2. obtain one clear confirmation;
3. run a visible five-second countdown;
4. allow cancellation throughout the countdown;
5. respect interruption and stop requests, including `SIGINT` on the car.

Local LEDs and the buzzer may provide the same impending-run warning when their real
hardware path is implemented. The web page must never be the only warning visible to
people standing near the car.

The current dashboard designs are authoritative visual references for this feature.
They should be stored in the repository with enough context that they do not depend
on old chat attachments remaining visible.

## 7. Documentation

The current documentation set will be rewritten around this plan. Old plans and
post-mortems will not be silently edited into new instructions.

The intended hierarchy is:

1. current source and dated physical observations;
2. root `README.md` for a short human entry point;
3. root `AGENTS_READ_ME.txt` for agent working rules;
4. root `PLAN.md` for current truth, known problems, and next work;
5. root `PROJECT_MAP.md` for file ownership and entry points;
6. the Turkish technical handover guide for physical installation, wiring, operation,
   and maintenance;
7. clearly labelled historical PDFs and post-mortems for timeline evidence.

`CLAUDE.md`, `AGENTS.md`, or similar compatibility files should contain only a short
pointer to the canonical root instructions rather than maintaining competing rules.

The technical handover guide is the authoritative human hardware guide. Its editable
source and an exported PDF should be preserved when a shareable version is ready.
Private or identifying material may remain censored in the repository copy.

Historical documents may retain their original wording, including incorrect or
overconfident claims, provided their location and surrounding index explicitly mark
them as historical and non-authoritative.

Current developer and agent instructions should prioritise clarity for language
models. Human-facing operation material may remain Turkish. Where both audiences need
the same text, a maintained bilingual presentation is preferred over unrelated
translations that drift apart.

## 8. Working rules

Repository work that is recoverable through Git does not require a ceremonial
pre-approval stage. Requested bug fixes, migrations, refactors, documentation work,
and contained features may proceed and should be explained afterward.

This does not authorise unrelated external changes, physical motor activation, secret
handling, destructive VPS operations, or irreversible actions outside Git. Those
remain limited to the user's actual request.

Git history is the recovery mechanism:

- do not force-push or rewrite shared history;
- commit coherent changes with understandable messages;
- ordinary corrections may go to `master`;
- dangerous, broad, or direction-changing work should use a separate branch;
- agents may commit and push completed ordinary work unless the user limits the task;
- never destroy historical evidence merely to make the tree look cleaner.

After each meaningful completed change, update this plan so its current-state claims
remain true, and provide a concise post-action report in chat. The plan should describe
the resulting state, not reproduce every command or preserve a diary of obsolete
steps. Detailed change history belongs in Git.

## 9. Repository hygiene

The root must contain the repository-wide README, agent instructions, plan, project
map, `.gitignore`, and `.gitattributes`. Moving those files into a subdirectory breaks
their repository-wide role.

Generated caches and local environments do not belong in Git. Tracked `__pycache__`,
`.pyc`, `.pytest_cache`, and `.venv` content should be removed from the working tree
and ignored at the root.

The complete Reicon upstream source may remain for now because it does not materially
consume Git hosting capacity. KERIM should still use only the assets it actually
needs, preserve the relevant licence, and avoid treating the upstream icon project as
STARTECH source.

## 10. Current work order

### First — restore a coherent repository

- finish this root plan;
- restore and rewrite the root README, agent instructions, and project map;
- restore root ignore and attributes files;
- restore `LEGACY/camtester.py`;
- remove tracked generated caches;
- mark `arac/` unmistakably as non-active while its final archival presentation is
  designed;
- keep KERIM's runtime and deployment paths at the root.

### Second — preserve evidence and designs

- store the dashboard screens and behaviour notes in the repository;
- store the censored technical handover source and PDF when supplied;
- classify old plans, defect reports, generated optimisation reports, and PDFs as
  historical or post-mortem records;
- retain links to relevant repository snapshots and competition evidence.

### Third — audit the active vehicle baseline

- compare `LEGACY/` against the shared HATA DEFTERI;
- identify assumptions tied to the old track dimensions and timing;
- fix concrete software defects without redesigning working subsystems;
- add focused regression checks where software-only behaviour can be tested honestly;
- record the exact physical checks required when SCHOOL becomes accessible.

### Fourth — simplify calibration

- inventory every calibration and tuning script;
- identify which values are genuinely consumed by the active runtime;
- design the explicit JSON-to-Python configuration conversion;
- repair KERIM's atomic dimension/perspective editing problem;
- consolidate overlapping calibration tools only after their useful behaviour is
  accounted for.

### Fifth — implement the remote wrapper

- preserve the approved dashboard design references;
- define the minimal authenticated command protocol;
- implement the car-side `remote.py` adapter;
- stream real process logs and camera output;
- implement safe disconnect, stop, confirmation, and five-second countdown behaviour;
- test software behaviour without claiming physical success;
- perform and record supervised physical verification later at SCHOOL.

## 11. What this plan rejects

Do not rebuild the car runtime merely because a newer architecture looks cleaner.
Do not reintroduce chains of named modules whose main purpose is approving one
another. Do not require a remote service to allow a local configuration file. Do not
turn calibration integrity into an editing deadlock. Do not replace missing hardware
with a successful-looking fake. Do not describe tests as physical evidence.

The target is deliberately ordinary: readable files, a car that can run locally,
tools that perform concrete jobs, honest logs, and enough documentation that the next
person can understand the system without this conversation.

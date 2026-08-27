# STARTECH current state and roadmap

Updated: 27 August 2026.

This file records the current direction after the repository reset. It is not a recipe
for rebuilding deleted code. Current source and tests determine what is implemented;
historical documents explain how the project reached this point.

## The decision

The competition-era implementation in `LEGACY/` is now the active vehicle baseline.
The attempted replacement grew into a larger, mostly physically unverified system in
which configuration gates and safety declarations obscured the basic job of driving
the car. It was removed in one recoverable Git commit instead of being kept as the
current direction.

<<<<<<< HEAD
Code owners have the most authority at all costs. After those, it follows:

1. current source and its checks;
2. this plan for current state and intended work;
3. `AGENTS_READ_ME.txt` for repository working rules;
4. current official competition publications for rule-dependent decisions;
5. historical and post-mortem material for context only.
=======
The retained product boundaries are deliberately small:
>>>>>>> e4d7860e9d13127d958148aa228119aafed20e3b

1. `LEGACY/` owns the vehicle runtime and concrete hardware behavior.
2. KERİM owns web calibration, configuration records, maintenance bundles, and the
   authenticated browser experience.
3. TAWNT is an optional validation library for narrowly useful boundaries.
4. Documents and Git history preserve evidence and the project timeline.

The deleted architecture remains recoverable from Git history. It is not to be
recreated file by file.

## Current truth

### Vehicle baseline — physically experienced, defects known

The LEGACY lineage ran on the physical competition car. Recorded results include:

- the car produced motor output and moved;
- the camera detected the green start light;
- lane perception worked, although following quality was poor;
- the crosswalk was detected and the car stopped and waited;
- a closely related 7 May repository snapshot exists in `ototot-yedek/master`;
- the exact on-site source may include unsaved edits, so the retained files must not be
  described as byte-identical competition evidence.

This is stronger evidence than a new architecture passing software tests. It does not
mean the current baseline is safe or race-ready without repairs and renewed physical
testing.

### KERİM — implemented service, incomplete vehicle bridge

KERİM remains in `startech_cam/`, with its deployment support under `deployment/`.
SAC, MAC, profiles, access, revision history, diagnostics, and release bundles remain.

KERİM can bundle the retained `LEGACY/` source and a selected configuration JSON. It
does not yet translate or install that JSON into `LEGACY/config.py`; the bundle says so
explicitly. The previous YAREN vehicle client was removed with `arac/`. Server-side
signed-link compatibility code remains because a small LEGACY adapter may use it later.

Known KERİM bug: MAC validates frame dimensions and perspective as one whole document,
creating a circular edit deadlock. A user cannot save the new dimensions until the old
perspective matches, and cannot save the new perspective until the dimensions match.
Manual AppData editing then changes the SHA and is rejected. Fix this by allowing an
atomic related-field update or section-aware draft validation; do not weaken integrity
checking globally.

### TAWNT — retained, not yet in the race loop

TAWNT remains importable through root `tawnt.py`. Its unit tests cover its current
software contracts. LEGACY does not presently depend on TAWNT, and documentation must
not imply that TAWNT controls the competition runtime.

Future integration should be small: for example, checking final normalized motor
commands and watchdog freshness immediately before the existing motor write. If that
makes the call path harder to read, it is the wrong integration.

### Physical availability

The car exists but is currently unavailable because the team cannot access SCHOOL.
Software-only repairs can proceed. New physical claims must wait for access to the car.

## Known vehicle defects to repair

`Markdown/HATA_DEFTERI_PAYLASIM.pdf` is the primary post-mortem. The following items are
the repair queue, not a claim that they are already fixed.

### Software-visible defects

- The perspective quadrilateral was tuned for 640×480 while runtime frames were
  configured as 800×680.
- The lost-lane path injects a synthetic error that produces a derivative spike and can
  flip steering direction.
- Speed scaling later in the pipeline can undo the controller's dead-zone behavior.
- One derivative threshold is interpreted with inconsistent units.
- Motor balance tooling writes names that do not match the values read by the runtime.
- Trim is duplicated or applied to the wrong wheel in parts of the old path.
- Configuration values and brightness handling are duplicated across files.
- The sign classifier exists but is not connected to the runtime decision path.
- Runtime errors do not always request zero motor output immediately.
- Logging duration was shorter than the race duration and must cover the complete run.
- A physical start-button path was removed and needs an explicit product decision before
  restoration; do not replace it with a gimmick phrase prompt.

Each fix should preserve the simple pipeline and state exactly what changed. Avoid a
general configuration framework when one constant or function boundary is enough.

### Car-required measurements and checks

- Measure left/right motor trim rather than guessing it.
- Confirm actual PWM frequency and the motor driver's expected control behavior.
- Confirm motor direction against wiring and wheel orientation.
- Verify camera mounting, exposure, perspective points, HSV ranges, and lane geometry
  under the SCHOOL lighting and track.
- Check supply voltage/current behavior under load and verify physical stopping.
- Re-run bounded lane following before attempting a complete track.

These cannot be converted into green software badges while the car is unavailable.

## Calibration direction

LEGACY contains concrete tuning tools for camera display, HSV, perspective, motor
balance, PD control, and sign work. Keep them during the reset because they document
what was actually adjusted.

The eventual cleanup is one standalone calibration workflow rather than many competing
configuration systems. KERİM/SAC can expose more useful controls by mapping directly to
the values the LEGACY runtime reads. The sequence is:

1. inventory each LEGACY tool and the exact value it reads or writes;
2. resolve duplicated or mismatched names in the runtime;
3. define one small exported configuration shape around those real values;
4. let KERİM edit and archive it without becoming required for local startup;
5. provide an explicit, reviewable conversion into the runtime configuration;
6. measure and verify values on the car before calling them physically verified.

Do not add another registry, immutable-profile layer, approval state machine, or
simulated calibration result to solve this.

## Remote access direction

A future KERİM link may provide:

- current vehicle logs and state;
- one explicit RUN request and STOP request;
- automatic authenticated operator/time recording;
- a heartbeat that moves the vehicle runtime to a non-driving standby state when the
  link is lost;
- local log retention when the server is unavailable.

The vehicle still runs its own code. The browser is an operator surface, not the motor
controller. This feature is `NOT IMPLEMENTED` after the reset. The retained KERİM link
protocol is compatibility material, not proof that the car currently connects.

## First repair order

1. Freeze and characterize the retained LEGACY baseline without reorganizing it.
2. Fix the dimension/perspective mismatch and MAC circular-save bug.
3. Fix lost-lane derivative behavior and ensure errors request zero output.
4. Repair motor-balance names, duplicate trim, and log duration.
5. Add focused recorded-frame and pure-control regressions where they prove the fixes.
6. At SCHOOL, perform bounded camera, motor-direction, trim, stop, and lane checks.
7. Only after those results, decide whether a small TAWNT motor-boundary integration or
   KERİM vehicle adapter is useful.

## Repository state after the reset

Retained:

- `LEGACY/`
- `startech_cam/`
- `deployment/`
- `startech/tawnt/`, `tawnt.py`
- `startech/configuration/`, `config/`
- retained-system tests
- root and `Markdown/` documents

Removed from the active tree:

- the replacement `arac/` vehicle stack;
- Webots/non-current simulation scaffolding;
- prototypes and example wireframes;
- document-consistency enforcement machinery;
- tests that existed only for those removed systems.

The reset branch was based on commit `80193d1`. Git history is the rollback and
comparison mechanism.

## Verification

Run the retained software suite from the repository root:

```powershell
$env:CAM_RELEASE = (git rev-parse HEAD).Trim()
py -m pytest -q
py -m compileall LEGACY startech startech_cam tawnt.py wsgi.py
node --check startech_cam/static/cam.js
```

Passing these checks proves only the asserted software contracts. It does not prove
that the physical car moves correctly.

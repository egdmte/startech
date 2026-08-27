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

The retained product boundaries are deliberately small:

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

Software repair batch completed 27 August 2026:

- lane loss no longer calculates a derivative from its fading fallback value;
- derivative thresholds now operate in their documented pixel-per-frame unit;
- lane following cannot command opposite wheel directions;
- a missing lane before the first real detection requests zero motion, and the 30th
  consecutive lost frame stops both wheels;
- medium derivative slowdown cannot accidentally accelerate a sharp curve;
- the lane histogram now enforces the already-configured peak-quality threshold instead
  of accepting broad low-level image noise as a lane;
- the motor layer is the only trim owner and enforces the configured dead-zone floor
  after later speed scaling;
- the speed-bump command is no longer below that floor;
- missing/mock GPIO now fails explicitly instead of accepting commands through a no-op
  output, and invalid/non-finite commands close the motor outputs;
- direction pins change only after PWM is zero, active braking and coasting are distinct,
  and shutdown is idempotent;
- camera-open and capture failures raise errors rather than yielding generated black
  frames; Pi, USB, and OpenCV resources are closed on failure and interruption;
- `main.py` and `yol_takip.py` construct motor hardware before camera acquisition, work
  with Windows or POSIX keyboard input, preserve non-zero failures, and do not leave a
  worker/server alive after the drive loop fails;
- state transitions stop the previous command before crosswalk, level-crossing,
  speed-bump, overtake, and parking work; one visible event is not repeatedly consumed;
- the logger records a lost lane as missing data instead of a perfect zero-error sample;
- calibration launchers use their own directory, hardware tools no longer open outputs
  merely because they were imported, and interruption follows a real cleanup path;
- the standalone sign-camera tool no longer opens a webcam on import, and sign training
  omits empty/unreadable classes rather than publishing unusable labels;
- shutdown calls the logger's real `finish()` method and attempts every cleanup even if
  one component fails;
- the retained baseline already records for 300 seconds and includes the GPIO 16 physical
  start-button path, so those two historical defects are no longer in the repair queue.

Fifteen focused vehicle regressions cover the controller, lane-signal, logger,
motor-boundary, and import-side-effect corrections. The repository suite currently
passes 148 tests plus two subtests. These repairs are `IMPLEMENTED` and
`PHYSICALLY UNVERIFIED`.

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

`Markdown/HATA_DEFTERI_PAYLASIM.pdf` is the primary post-mortem. The list below contains
the remaining repair queue; completed software repairs are recorded in Current truth.

### Software-visible defects

- The perspective quadrilateral was tuned for 640×480 while runtime frames were
  configured as 800×680.
- Configuration values and brightness handling are duplicated across files.
- The sign classifier and model exist as standalone tools but are not connected to the
  runtime decision path. `EventDetector` explicitly returns `sign_type=None`; blue-sign
  presence is not presented as sign recognition.
- Camera/event thresholds, perspective, controller gains, and wheel direction still need
  track-side measurement even where their software paths now reject obvious bad inputs.

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

1. Fix the dimension/perspective mismatch using a real calibration capture.
2. Add focused recorded-frame regressions when real camera footage is available.
3. Connect the existing sign classifier only after real sign captures establish its
   labels, confidence behavior, and false-positive rate.
4. Fix KERİM's MAC circular-save bug after the vehicle repair queue is stable.
5. At SCHOOL, perform bounded camera, motor-direction, trim, stop, and lane checks.
6. Only after those results, decide whether a small TAWNT motor-boundary integration or
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
py -m compileall -q LEGACY startech startech_cam tawnt.py wsgi.py
node --check startech_cam/static/cam.js
```

Passing these checks proves only the asserted software contracts. It does not prove
that the physical car moves correctly.

# STARTECH autonomous vehicle — current state and real roadmap

Source review: 25 August 2026.

This is the single current project plan. It describes what the present code does, what
still needs a real implementation, and what evidence is required before a stronger claim
can be made. It is deliberately not a recipe for recreating completed work.

The physical car exists and is fully built. It is currently unavailable because it is at
SCHOOL and the team cannot access SCHOOL during the summer. The current software can be
developed without the car, but its new physical-control path remains unverified on that
hardware.

Current governing order:

Code owners have the most authority at all costs. After those, it follows:

1. current source and its checks;
2. this plan for current state and intended work;
3. `AGENTS_READ_ME.txt` for repository working rules;
4. current official competition publications for rule-dependent decisions;
5. historical and post-mortem material for context only.

If those sources disagree about implemented behavior, inspect the code and tests. Do not
make an old document true by rebuilding an obsolete design.

---

## 1. Purpose and fixed boundaries

STARTECH is building a camera-only autonomous car for multi-task track completion. The
minimum useful vehicle is not a dashboard, a policy report, or a successful test suite.
It is a real chain that can acquire a camera frame, understand the lane, choose a bounded
motion request, apply it through the existing wiring, stop on demand or failure, and
leave an understandable record.

The project has these fixed boundaries:

- Camera perception is the only environmental sensing input. Do not add a different
  sensor to avoid solving the camera problem.
- A production feature is real or unfinished. There is no production pretend-car mode,
  generated observation, fake motor backend, or synthetic readiness result.
- Tests may isolate software with controlled fixtures under `tests/`. A fixture is never
  selectable as the vehicle and never counts as physical evidence.
- Actual camera recordings may be replayed for analysis. They are evidence about the
  recorded frames, not evidence about a currently connected camera or moving car.
- `LEGACY/` is a behavior and wiring reference. Useful behavior may be migrated without
  rebuilding the old architecture around it.
- The current architecture is not abandoned or replaced without explicit pre-approval.
- Configuration, web access, and logs support the car. They must not become requirements
  for the car to start offline at a race.

The first program objective is the basic vehicle chain. Competition tasks are added only
after the basic chain is physically understood and repeatable.

---

## 2. Official competition sources

Do not copy long-lived rule values into this plan. They go stale while continuing to
look authoritative.

As reviewed on 24 August 2026, the newest published season is the 18th International MEB
Robot Competition, 2026. The current official entry points are:

- [MEB Robot Competition home](https://robot.meb.gov.tr/)
- [Autonomous Vehicle category](https://robot.meb.gov.tr/kategoriler/otonom-arac-0)
- [Application guide](https://robot.meb.gov.tr/organizasyon/uygulama-kilavuzu)

The category guide and application guide must both be checked before rule-dependent work.
The category page is a summary, not a substitute for its linked guide. Announcements and
event procedures may amend a guide later in the season.

When a new season appears:

1. record the official publication date and direct official links;
2. compare the new category and application guides with the previous official versions;
3. identify changes to camera restrictions, dimensions, starting, communications, tasks,
   scoring, team access, and technical inspection;
4. update only affected current requirements and roadmap items;
5. leave the previous guide in history rather than silently presenting it as current.

`LEGACY/10_otonom_arac.pdf` is the retained local 2026 category-guide snapshot. It is a
historical reference after a newer official guide is published. The online MEB source
wins when it contains a later correction.

The intended task list later in this plan is retained because the current official 2026
category still describes those tasks. Each task becomes provisional again when a newer
official guide appears.

---

## 3. Evidence language

Use only these project status terms:

| Status | Exact meaning |
|---|---|
| `IMPLEMENTED` | A real code path exists and its stated software contract is checked. |
| `PHYSICALLY UNVERIFIED` | The real path exists, but its required car-side observation is absent or not recorded. |
| `PHYSICALLY VERIFIED` | Dated evidence demonstrates the exact stated physical behavior on the named hardware and configuration. |
| `NOT IMPLEMENTED` | No real end-to-end implementation exists yet. |
| `VALIDATED` | TAWNT accepted one specific command, profile, value, or relationship. |

`VALIDATED` is deliberately narrow. It does not mean that the whole feature, car, or
drive is ready. Say what is implemented and name the check that exercised it.

Evidence is layered:

| Evidence | What it can establish | What it cannot establish |
|---|---|---|
| Unit or integration check | The checked software response | Camera mounting, wheel movement, braking, traction, or safe driving |
| Static/document check | A named source/document relationship | Runtime or physical behavior |
| Real camera frame | That a named camera produced a frame in that session | Lane correctness on another track or motor behavior |
| Recorded-frame analysis | The algorithm's result on immutable captured data | Live timing, current camera health, or physical movement |
| Driver receipt | The software reached the selected driver and requested stop | That a wheel moved in the expected direction or physically stopped |
| Human physical observation | The precise observed behavior for that run | General readiness under other configurations or conditions |
| Repeated physical run package | Repeatability inside its recorded conditions | Compliance with a later guide or an untested environment |

Every physical claim needs, at minimum, a date, commit, selected profile identity,
hardware arrangement, operator, expected behavior, observed behavior, and stop method.
Unobserved fields say `NOT OBSERVED`; they are not filled by inference.

---

## 4. Current architecture

The current runtime chain is intentionally direct:

```text
YAREN selected configuration
          |
          v
KASIM camera -> KEREM lane observation -> ARDA orchestration
                                              |
                                              v
                                      lane controller
                                              |
                                              v
                                      TAWNT validation
                                              |
                                              v
                                      OSMAN GPIO output
                                              |
                                              v
                                      existing physical car

DORA owns explicit vehicle-state transitions.
KADER records the software timeline.
KERİM and SAC provide calibration and a bounded linked-workshop surface through YAREN.
```

There are no alternate active module names. The canonical names and responsibilities
are:

| Module | Current responsibility | Must not claim or own |
|---|---|---|
| YAREN | Immutable configuration/profile registry, runtime selection, and authenticated live KERİM gateway | Physical calibration truth, motor movement, or vehicle readiness |
| KASIM | Open a real OpenCV USB camera first or Picamera2 camera second; normalize real RGB frames | Generated frames or silent source switching after a read failure |
| KEREM | Produce cautious lane observations from KASIM frames and the selected calibration | Competition-task recognition that is not implemented |
| DORA | Apply deterministic, explicit state transitions | Camera access, network access, logging, or motor output |
| KADER | Record ordered in-memory or JSONL software events | Proof of an external physical result |
| TAWNT | Validate declared values, phases, watchdogs, arming, commands, and fault state | GPIO writes or proof that a measurement/stop physically happened |
| OSMAN | Convert TAWNT-approved requests to the existing gpiozero/L298N wiring and request zero output | Autonomous decisions or unvalidated requests |
| ARDA | Expose the real operator paths and compose camera, perception, control, validation, output, and logging | Pretend vehicle modes or web-only readiness gates |
| KERİM | Create, revise, store, exchange, and bundle real calibration/configuration documents with exact committed car source | Requiring internet for race operation, self-updating the live server, or claiming values were physically measured |
| SAC | Guide calibration and issue one bounded, explicit linked workshop command | Continuous remote driving, autonomous start, or physical proof without observation |

The public TAWNT API is root `tawnt.py`; its implementation lives in
`startech/tawnt/`. Current car modules import that public API. The driver accepts only a
request paired with the exact immutable command returned by TAWNT.

---

## 5. Current implementation status

This table describes the current source after the real vehicle-core, non-production
pretend-path removals, and linked-camera work. The most relevant baseline commits are
listed in the historical index.

| Capability | Status | Current evidence | Physical boundary |
|---|---|---|---|
| YAREN profile import, integrity, versioning, selection, archive, and history | `IMPLEMENTED` | Configuration/profile tests and current schemas | Selected values are `PHYSICALLY UNVERIFIED` until reviewed against the car |
| Active immutable runtime configuration | `IMPLEMENTED` | `arac/ayar.py` and configuration checks | Loading does not arm or move anything |
| Windows/Linux USB camera acquisition | `IMPLEMENTED` | KASIM checks plus a limited laptop USB acquisition observed on 24 August 2026 | The school camera arrangement is `PHYSICALLY UNVERIFIED` |
| Raspberry Pi Picamera2 acquisition | `IMPLEMENTED` | Import-protected real adapter and contract checks | Pi camera, cable, mount, resolution, and timing are `PHYSICALLY UNVERIFIED` |
| Finite real-camera recording and strict replay | `IMPLEMENTED` | Manifest, hash, order, interruption, and decode checks | A replay is not a current live-camera result |
| Lane detection on real RGB frames | `IMPLEMENTED` | KEREM checks on generated RGB regression frames and the live-camera diagnostic path | No captured school-track session is retained; school-track recognition is `PHYSICALLY UNVERIFIED` |
| Lane controller | `IMPLEMENTED` | Controller/request checks and LEGACY-compatible sign convention | Gain, trim, dead-zone, steering direction, and traction are `PHYSICALLY UNVERIFIED` |
| DORA vehicle state transitions | `IMPLEMENTED` | Transition and invalid/stale-event checks | State text does not prove motion |
| KADER memory and JSONL records | `IMPLEMENTED` | Ordering, validation, and persistence checks | Pi disk endurance and recovery are `PHYSICALLY UNVERIFIED` |
| TAWNT phase, arm, watchdog, fault, and command validation | `IMPLEMENTED` | TAWNT behavior and integration checks | TAWNT cannot see physical wiring or stopping |
| Existing L298N/gpiozero motor boundary | `IMPLEMENTED` | OSMAN adapter and call-contract checks | Every direction, trim, voltage, brake state, and stop result is `PHYSICALLY UNVERIFIED` |
| Physical start button path | `IMPLEMENTED` | gpiozero button adapter contract | BCM wiring and debounce behavior are `PHYSICALLY UNVERIFIED` |
| ARDA live observation | `IMPLEMENTED` | CLI and camera/perception integration checks | A real camera/profile is required at runtime |
| ARDA autonomous lane-following path | `IMPLEMENTED` | Camera→controller→TAWNT→driver integration checks | The current core has not driven the physical car: `PHYSICALLY UNVERIFIED` |
| ARDA bounded workshop output | `IMPLEMENTED` | Shared workshop executor checks | Actual motor response is `PHYSICALLY UNVERIFIED` |
| KERİM authentication, calibration workflow, storage, and history | `IMPLEMENTED` | KERİM repository/auth/workflow checks, including perspective and HSV editing over a signed current frame | New values are installed inactive and remain `PHYSICALLY UNVERIFIED` |
| Signed live YAREN/KERİM link | `IMPLEMENTED` | Device identity, one-use code, five closed operations, strict signed receipts, heartbeat lease, and lifecycle checks | It is not needed for offline autonomous operation |
| KERİM release health, diagnostic export, backup, and deployment | `IMPLEMENTED` | Exact-revision health checks, redaction checks, SQLite integrity checks, and validated deployment/proxy scripts | Production runs the deliberately deployed `origin/master` revision reported by `/health` |
| Exact vehicle release ZIP | `IMPLEMENTED` | Git source comparison, immutable-profile archive, uncommitted-file exclusion, dependency/profile hashes, download audit, UI, and bundle checks | Building a ZIP does not install, activate, boot, arm, move, or physically verify the car |
| SAC linked camera/lane report | `IMPLEMENTED` | Device API, YAREN link, and UI checks | Its exact physical observation is limited to the connected camera session |
| SAC bounded workshop command with legal name/time and cancel delay | `IMPLEMENTED` | Server bounds, closed operation, browser countdown, receipt, and observation checks | A human must separately record movement and stopping |
| Traffic-light behavior | `NOT IMPLEMENTED` | DORA has a waiting state, but there is no real complete detector-to-motion behavior | Requires official-rule review, real captured data, and physical verification |
| Pedestrian-crossing behavior | `NOT IMPLEMENTED` | No current real end-to-end path | Same boundary |
| Railway-crossing behavior | `NOT IMPLEMENTED` | No current real end-to-end path | Same boundary |
| Speed-bump behavior | `NOT IMPLEMENTED` | No current real end-to-end path | Same boundary |
| Parking behavior | `NOT IMPLEMENTED` | No current real end-to-end path | Same boundary |
| Dead-end behavior | `NOT IMPLEMENTED` | No current real end-to-end path | Same boundary |
| Overtaking behavior | `NOT IMPLEMENTED` | No current real end-to-end path | Same boundary; intentionally last |

The full Python suite passed on 25 August 2026 with 251 tests. That result proves the
checked software contracts only. Run the current commands again after every relevant
change instead of relying on this count.

---

## 6. Current operator surfaces

ARDA is the direct local vehicle surface:

```powershell
py -m arac.main --interactive --language en
py -m arac.main --observe --operator "Legal Name"
py -m arac.main --drive --operator "Legal Name" --confirm-output
py -m arac.main --bench --operator "Legal Name" --confirm-output --left 10 --right 10 --seconds 0.25
py -m arac.main --yaren
```

The exact command-line help is the authority for current flags:

```powershell
py -m arac.main --help
```

`--observe` opens KASIM and KEREM without creating OSMAN. `--drive` is a real physical
path. It loads the active YAREN profile, opens the camera, proves one lane analysis can
be produced, waits for the selected start control, enters the TAWNT live lane phase,
starts the independent output watchdog, and sends accepted requests to OSMAN.

`--bench` issues one bounded physical request through the shared workshop executor and
then requests electrical stop. It is not a dry run. Its numerical limits are source
contracts, not measured safe limits for the physical car.

Every LLM-triggered physical output outside SAC requires a warning followed by seven
cancelable seconds before the command is invoked. SIGINT/Ctrl+C cancels immediately and
must never be treated as permission to resume.

YAREN's guided registry surface remains available directly:

```powershell
py -m arac.ayar_cli interactive
```

Profiles live outside the repository by default. They are versioned by immutable
content, full hashes, warning review, and explicit active selection. Installing a profile
does not activate another profile, arm TAWNT, or create a motor driver.

---

## 7. Configuration and calibration

The configuration chain starts from the existing v1 pair:

```text
kalibrasyon.json + ayarlar.json
            |
            v
YAREN immutable profile directory + profil.json
            |
            v
explicit active selection
            |
            v
ARDA read-only ActiveConfiguration snapshot
```

The trusted formats live in `config/schema/`; non-vehicle examples live in
`config/examples/`. `Markdown/YAPILANDIRMA_SOZLESMESI.md` explains the current format.
The schema proves only structure and declared semantics. It does not prove that a human
measured the car or that a camera threshold fits the school track.

KERİM is the active browser calibration tool. Its name expands to "Kalibrasyon Erişim,
Revizyon İnceleme Merkezi." It can create and revise configuration,
store history, preview real camera effects when a camera is linked, and deliver an
inactive configuration to YAREN for review. YAREN remains the authority for what the
local vehicle loads.

KERİM's login and authenticated interface can be switched between English and Turkish.
The selected language survives login and logout, and the approved page copy is recorded
in `KERIM_COPY.md`. Both language paths use the same routes, validation, stored documents,
and physical-evidence boundaries.

KERİM uses a curated local Reicon 1.2 subset for meaningful action icons. The SVGs are
served with the rest of the versioned interface bundle; normal operation does not load
an icon runtime or depend on an external icon service. Its authenticated open-source
page distinguishes software KERİM actually uses from related public STARTECH projects;
listing a project there does not claim that it protects or runs inside KERİM.

StarTechConfig is the outdated Windows predecessor to KERİM. It can produce the v1 files
and was designed to sideload them to a Raspberry Pi. Its code and artifacts are retained
as historical implementation reference; it is not the active configuration authority.

Configuration work while the car is unavailable:

- keep schema validation strict and deterministic;
- keep active profiles immutable and attributable;
- make warnings explain which real observation is missing;
- support Windows USB-camera capture and analysis without pretending it is the car's
  final mounting;
- keep export/import offline-capable;
- reject mismatched profile hashes, camera dimensions, invalid ranges, stale selections,
  and partial writes;
- never label a default or projected value as measured.

Configuration work when the car returns:

- record the actual camera model, orientation, resolution, mounting height/angle, and
  relevant capture settings;
- inspect motor power, channel mapping, physical direction, dead zone, and trim;
- create a new profile rather than editing an old profile in place;
- attach the dated evidence record to the profile identity;
- repeat affected camera or motor verification after hardware, mounting, or power-path
  changes.

---

## 8. Camera acquisition and recorded data

KASIM provides two real acquisition paths: OpenCV USB first and Picamera2 second. Both
produce RGB frames with source metadata, monotonically increasing frame identity, capture
time, and dimensions. If both fail to open, KASIM fails explicitly. If an opened source
later fails to read, it does not silently switch to another camera mid-run.

The school car path still needs physical confirmation of:

- camera type and cable;
- actual selected backend;
- orientation and mounting stability;
- effective resolution and frame timing;
- exposure behavior under school-track light;
- frame freshness during motor load;
- recovery after camera open/read failure.

ARDA can record a finite real session as numbered JPEG frames and a strict manifest. It
refuses to overwrite an existing session. A completed manifest is written last; an
interrupted session gets an incomplete marker and is rejected by normal replay.

Replay checks frame order, dimensions, hashes, manifest consistency, and decoding before
feeding frames through the KASIM interface. This makes actual recordings useful for
repeatable development on Windows while the car is unavailable.

The recording library should grow from real captures, not generated scenes. Each useful
session needs:

- source camera and mount description;
- date and location class without unnecessary personal data;
- selected profile and commit;
- resolution and orientation;
- lighting and track conditions;
- intended use: calibration, training, regression, or blind evaluation;
- immutable session hash and known limitations.

Keep tuning and evaluation sessions separate. A clip used to choose thresholds must not
be the only clip used to claim those thresholds work.

---

## 9. Lane perception

KEREM currently performs real lane analysis from KASIM RGB frames using the selected
YAREN calibration. Its observation carries lane validity, normalized and pixel error,
confidence, lane centers, brightness, frame identity, and a reason when no reliable lane
is available.

Lane memory narrows the search for a line that returns and may complete the missing side
when the current frame still sees another line. Memory alone cannot make an observation
valid: a frame with no current near/far lane evidence produces zero-confidence lane loss,
which the controller converts to zero motion intent.

The current controller sign convention is inherited from the working LEGACY car:
positive lane error asks for a left correction. That convention is implemented, but its
effect through the current physical wiring is still unverified.

Useful LEGACY perception behavior should be migrated by measured value, not by copying
the old pipeline whole. The retained candidates are:

- bird's-eye perspective before lane extraction;
- reflection handling through luminance normalization;
- lighting-aware white-lane selection;
- vertical continuity to distinguish lanes from reflections;
- near/far weighting for position and look-ahead;
- a narrowed search window that preserves dashed-line continuity;
- temporal stability before task/state events;
- calibration preview against actual frames.

For each migration:

1. define the exact observable failure it addresses;
2. select immutable actual-camera recordings that contain the failure and ordinary cases;
3. implement the smallest change in KEREM or configuration;
4. add a regression that fails without the change;
5. compare output on held-back real recordings;
6. update this plan's current status after the change;
7. leave physical status unverified until the school camera and track demonstrate it.

Lane loss must remain an explicit observation that produces zero motion intent or a fault
path. The system must not keep driving on a stale successful frame.

---

## 10. State, control, validation, and motor output

DORA is a pure state machine. It accepts explicit, ordered events and rejects malformed,
illegal, or stale events. It does not secretly inspect images or drive motors. Current
states cover boot, self-test, readiness, waiting for green, driving, stopping, waiting,
finish, and fault. A state name is a software fact, not proof of the physical car.

The lane controller converts a valid KEREM observation and YAREN settings into a bounded
left/right request. It owns the control law, target/minimum/maximum speed relationship,
integral and derivative limits, and lane-loss response. It does not touch GPIO.

TAWNT owns the validation boundary:

```python
tawnt.heartbeat("camera")
tawnt.heartbeat("control")
tawnt.validateBeforeStart(profile=tawnt.LIVE)
tawnt.enterPhase(LANE_PHASE)
tawnt.arm(
    operator,
    live_hardware_authorized=True,
    final_confirmation=True,
)
```

This is intentionally readable. It says that current camera/control heartbeats exist,
the live profile's declared values passed the TAWNT checks, the lane phase is active, and
the caller supplied the required live-output declarations. It does not say that the
camera is aimed correctly, authorization is truthful, wiring is correct, or a wheel will
stop.

OSMAN is the only production motor driver. The current source records the existing car's
BCM direction pins, PWM pins, start button, L298N inversion, trim application, dead-zone
handling, zero-output request, and resource cleanup. Controller requests are validated by
TAWNT, then calibration-adjusted final values are validated again before GPIO changes.

ARDA's independent output watchdog requests stop if the camera/control loop stops making
progress. ARDA also requests stop before start, on interruption, on exception, at normal
loop end, and while closing the driver. These are strong software contracts. The actual
electrical and mechanical stop behavior is still physically unverified.

No software check replaces the physical power cutoff. When physical behavior is unknown,
the safe progression is secure wheels, minimum useful duration/output, observe direction,
request stop, remove power if unexpected, and record what actually happened.

---

## 11. KERİM, SAC, and the YAREN link

KERİM is a real configuration application, not a car-readiness ceremony. Its useful
responsibilities are authentication, calibration creation/revision, persistence, history,
preview, configuration exchange, exact vehicle bundles, and bounded workshop assistance.

The internal `startech_cam` package, existing routes, `CAM_*` environment names,
CAM-prefixed deployment files, and the `STARTECH-CAM-DEVICE-V1` signing domain remain
compatibility contracts. Current user-facing language and documentation call the product
KERİM; a cosmetic rename must not silently break those established interfaces.

YAREN creates a signed request with its registered Ed25519 device identity. KERİM returns
a random one-use code. Entering that code binds the authenticated browser session to the
same outbound device link. There is no fixed 15-minute browser or device-link countdown.
Authenticated YAREN polling refreshes a five-minute idle lease, including the unused
one-use code; an abandoned process therefore expires without shortening an active link.
The link closes on explicit logout, manual disconnect, YAREN shutdown/interruption, or
idle-lease expiry.

The authenticated KERİM navigation remains available while YAREN is linked. The operator
can return to the dashboard, edit ordinary settings, or manage the YAREN connection
without disconnecting and repeating login. A visible logout action is present on every
authenticated KERİM screen; logout also revokes the linked YAREN process.

The operation list is closed:

- `REQUEST_ACTIVE_CONFIGURATION`
- `REQUEST_CAPABILITY_REPORT`
- `CAPTURE_CALIBRATION_FRAME`
- `INSTALL_INACTIVE_CONFIGURATION`
- `RUN_BOUNDED_WORKSHOP_COMMAND`

`CAPTURE_CALIBRATION_FRAME` opens KASIM's configured real camera chain, captures one
current JPEG, closes the device, and returns a strict signed receipt containing source,
dimensions, capture time, frame identity, digest, and bounded image data. Camera failure
rejects the job; there is no generated or recorded-frame fallback. KERİM uses that exact
frame for draggable four-point perspective editing and a client-side HSV target preview.
Saving creates a new immutable calibration with the frame provenance, clears physical
evidence, and queues it for inactive YAREN installation. It does not select or activate
the new profile.

The capability report may inspect the selected profile, acquire a real frame, run KEREM,
exercise DORA transitions, write/read an in-memory KADER record, and inspect TAWNT's
software contract. Automatic diagnostics do not import OSMAN or request motor output.
Labels must describe that limited evidence instead of presenting green checkmarks as a
driving-safety certificate.

SAC's workshop command is the deliberately small exception that makes the linked site
useful beside the car. It carries the authenticated operator's legal name and KERİM's
current internet time, expires quickly, requires the physical checklist, and permits one
bounded command only. YAREN revalidates the payload and sends it through the same shared
workshop executor as ARDA's local bench command.

The browser provides a seven-second cancelable warning before queuing output. `Start now`
may deliberately skip the remaining delay; `Cancel` sends nothing. While the job is
queued or may be active, the page keeps a visible live-output warning. The link cannot
open a shell, activate a profile, start autonomous driving, or become a continuous remote
control channel.

The receipt records requested and applied values, duration, and whether software
requested stop. The supervising human records separately whether the movement matched,
was wrong, or was not observed. These records must never be collapsed into one claim.

SAC/KERİM labels distinguish values that current runtime code consumes from recorded
intent. Projected power limits are runtime-backed through ARDA's speed setting. Camera,
compute, and wheel fields are recorded intent until a current consumer exists. Driver
output choices publish configuration policy; KERİM does not arm or configure OSMAN.

KERİM exposes an authenticated, redacted diagnostic bundle containing its release, SQLite
integrity, repository counts, recent calibration metadata, and current YAREN-link state.
It excludes credentials and captured image bodies and explicitly reports that KADER car
logs are absent because KERİM does not currently receive them. `/health` reports the exact
Git revision. The deployment helpers create an integrity-checked online SQLite backup,
accept only a clean fast-forward to an exact commit already on `origin/master`, run the
KERİM/YAREN/configuration/workshop checks, reload the service, and require that exact
revision from `/health`. Encrypted off-site export is a separate deliberate operation.

The authenticated vehicle-release page compares the exact deployed commit with a freshly
published `origin/master`, or labels cached remote information as non-current. The
systemd web worker keeps its read-only checkout and hidden home-directory sandbox: the
deployment command and published repository hook atomically write a strict commit
reference under KERİM's shared directory, and the worker verifies that commit against
its local Git objects before offering it. It builds a ZIP from Git objects, so
uncommitted server files stay untouched and excluded. The ZIP
contains the chosen immutable KERİM/YAREN document and split v1 pair plus a manifest with
source, profile, and dependency-file hashes and `PHYSICALLY UNVERIFIED` boundaries. A
revision/profile change between review and submission is rejected. The download is
audited. The page does not update the serving checkout; deployment remains the explicit,
backup-first, fast-forward-only `deployment/deploy_cam.sh` operation.

KERİM must remain optional to race operation. A correct active YAREN profile and local ARDA
runtime must work without internet, KERİM, a laptop, or an external account.

---

## 12. Logging and run evidence

KADER provides ordered memory and JSONL black-box records. It validates run identity,
record kind, JSON values, frame ordering, and append behavior. ARDA records at least the
selected profile, state, lane observation, motor request, accepted output, interruption,
and fault information relevant to the current path.

One run package should make three timelines distinguishable:

1. what the software requested;
2. what the software recorded or acknowledged;
3. what a human physically observed.

A practical run record contains:

- run identity and date/time source;
- Git commit and whether the worktree was clean;
- active YAREN profile identity and full hashes;
- camera/hardware arrangement;
- operator and observer where physical work occurred;
- test purpose, expected result, and stop method written before output;
- KADER events and relevant immutable frame/video references;
- actual physical observations and anomalies;
- decision: repeat, fix, advance, or stop.

Do not overwrite a run package. Keep raw evidence unchanged; derived summaries may point
to it. If wall-clock time is wrong, retain monotonic ordering and document the time
uncertainty.

Future Pi work must establish disk capacity, write latency, graceful shutdown, rotation,
behavior when storage is full or read-only, and recovery from a partial/corrupt final
record. Silent log loss is not a success state.

---

## 13. Physically unverified inventory

The unavailable car blocks observation, not implementation. The following facts must not
be guessed or promoted from LEGACY without inspecting the current physical vehicle:

- installed Raspberry Pi/OS/Python/dependency state;
- camera model, interface, cable, orientation, mount, resolution, timing, and exposure;
- actual power sources, cell arrangement, voltage under motor load, and undervoltage;
- present L298N channel-to-motor mapping and wire integrity;
- left/right and forward/reverse sign through the current OSMAN path;
- four-motor grouping behind the two logical channels;
- physical start button wiring and behavior;
- dead-zone threshold and low/high trim values;
- usable PWM range for the installed motors and power path;
- zero-output electrical state, braking behavior, stopping time, and stopping distance;
- watchdog/fault stop behavior while motors are energized;
- lane perception with the installed camera on the school track;
- control gain, speed envelope, traction, curve response, and battery dependence;
- offline boot and service behavior on the installed Pi;
- storage endurance and log recovery;
- every competition-task detector and physical behavior.

An old measurement may be a hypothesis and setup aid. It becomes current evidence only
after its hardware identity is confirmed and the observation is repeated or shown to be
unchanged.

---

## 14. LEGACY migration inventory

`LEGACY/` is retained because the earlier vehicle moved and because it documents the
real design. It is not automatically more correct than current source; it contains both
valuable behavior and known seam failures.

The source-level recovery decision is:

| LEGACY area | Useful evidence or behavior | Current disposition |
|---|---|---|
| `lane.py` | Bird's-eye perspective, CLAHE/reflection handling, lighting-aware HSV, vertical continuity, near/far weighting, and narrowed temporal search | Already represented in `arac/goruntu.py`, with stricter current-frame, resolution, freshness, and confidence rules. Do not copy the file wholesale. |
| `controller.py` | PID shape, dynamic speed, trims, dead zone, and the established lane-error sign | Useful parts are represented in `arac/surucu.py`. Do not restore its invented decaying error, forced minimum speed, or possible opposite-sign lost-lane pivot. Current lane loss requests zero. |
| `motor.py` | Two logical channels and the recorded gpiozero/L298N pin arrangement | Preserved through OSMAN. Do not restore the silent no-op GPIO fallback or treat direction comments as physical verification. |
| `main.py` | Earlier task order and evidence that the vehicle once moved | Do not migrate the monolith, blank-frame substitution, keyboard green-light trigger, delayed exception stop, open-loop task timing, or long lost-lane search turn. Its `sign_type` branch has no producer in `events.py`. |
| `events.py` | Candidate green-light, crossing, rail, bump, car, parking, and sign image algorithms | Evaluate only after the current rules and held-back real recordings exist. Each accepted detector needs a current DORA policy, bounded TAWNT/OSMAN behavior, and KADER evidence; none is a current task implementation. |
| `camera.py`, `calibrate.py`, `hsv_tune.py`, `tune.py`, `pd_tune.py`, `kalibrasyon.py` | Useful live perspective, cursor-HSV, mask, bird-view, and tuning interactions | Real-frame perspective and HSV preview are now in KERİM and publish only inactive profiles. Remaining views are added only for a demonstrated need; never restore blank-frame fallbacks, direct motor tuning, or regex configuration edits. |
| `logger.py` | The need for a finite run/error record | Superseded by KADER JSONL/memory. Do not restore a logger that converts lane loss to numeric zero or lacks its called close method. Derived stability reports may be built from unchanged KADER evidence later. |
| `motor_balance_test.py`, `camtester.py` | The need to measure channel balance and perform a physical smoke check | SAC/ARDA's bounded workshop path owns output. A future balance workflow must record actual movement/distance evidence into a new YAREN profile; do not restore direct GPIO output or silent substitutes. |
| `train_sign.py`, `sign_test.py`, `sign_model.json` | A HOG-centroid recognition experiment and augmentation ideas | Not integrated into the earlier runtime and trained from a hard-coded local dataset. Keep as a candidate until current rules, a reproducible dataset, and held-back real evaluation justify a detector. |
| `yol_takip.py` | Historical remote viewing/control experiment | Do not migrate as a race dependency or continuous control channel. KERİM remains optional and the YAREN operation list stays closed. |
| `guncelle.sh` | The operational need for controlled updates | Superseded by exact-revision deployment, backups, focused service checks, and release health under `deployment/`. |
| LEGACY's NumPy-named scratch file | Personal math/bug-hunting scratch work | Historical test material, not competition functionality and not a migration candidate. |

The exact on-site competition edits were not saved, so the archive is evidence about the
earlier design rather than a bit-for-bit copy of the final race program. The current
camera, lane, controller, driver, configuration, logging, start-button, stop, calibration,
and deployment boundaries now contain the useful recoverable foundation. Further
production vehicle changes wait for a specific current failure, current official rule,
or real recording instead of being justified only by the age of the file.

`Markdown/HATA_DEFTERI.md` and its PDFs explain the failure history and the good parts of
the earlier build. They are post-mortems, not current instructions. A migration closes a
specific current gap and receives a regression check; it does not start the project over.

---

## 15. Work while the car is unavailable

The current priority is to make the basic real chain more complete without inventing
physical results.

### 15.1 Keep the repository truthful

- Remove stale current claims when source behavior changes.
- Keep canonical names and one current plan.
- Keep old PDFs, post-mortems, and design artifacts labeled as history.
- Add regression checks for fixed seam failures.
- Keep production imports and modes free of vehicle substitutes.
- Keep configuration examples visibly non-vehicle and inactive.

### 15.2 Strengthen real camera work

- Use a physical Windows USB camera for development where helpful.
- Capture immutable sessions covering straight lane, curves, dashed markings, glare,
  shadow, low contrast, and lane loss when those scenes can be produced honestly.
- Record capture metadata and keep held-back evaluation sessions.
- Compare KEREM changes on actual captured frames.
- Improve error messages and diagnostics that help someone correct a camera problem.

### 15.3 Migrate proven perception behavior

- Start with failure cases visible in real recordings.
- Prefer small, separately checked changes over one giant LEGACY port.
- Keep threshold and perspective values in YAREN configuration rather than hidden code.
- Preserve frame freshness, reason strings, confidence, and lane-loss behavior.
- Do not build competition-task behavior from imagined scenes when no relevant real
  capture exists.

### 15.4 Strengthen configuration and evidence

- Use KERİM's linked real-frame editor to create candidate calibrations when a physical
  camera is available; keep every result inactive until YAREN review.
- Keep YAREN import, selection, warning review, and rollback deterministic.
- Make run/profile relationships easy to inspect later.
- Improve KADER records where a real diagnosis would otherwise be ambiguous.
- Keep local export/import and Pi deployment independent of the web service.

### 15.5 Prepare the car-return procedure

- Maintain a concise inspection sheet based on current source and the physical car.
- Prepare a known commit and dependency-install path for the Raspberry Pi.
- Prepare blank evidence forms; do not prefill measurements.
- Prepare the smallest bounded SAC/ARDA command and the stop procedure.
- Keep a tested recovery copy of configuration and code once Pi access is possible.

Work that cannot produce a real implementation, real recorded-data result, regression
check, or useful car-return preparation should not displace this queue.

---

## 16. First work when the car returns

The first session is an inspection and bounded-verification session, not an autonomous
lap attempt.

### 16.1 Establish the exact test article

1. Photograph and identify the current car arrangement without exposing unnecessary
   personal or school data.
2. Record the Pi, camera, motor driver, power path, motor grouping, switches, and cables.
3. Compare the wiring with `LEGACY_VEHICLE_WIRING`; record every difference before code
   is changed.
4. Record the commit, working-tree state, dependency state, and intended YAREN profile.
5. Identify physical motor-power removal and keep it reachable.

### 16.2 Verify the unpowered software path

1. Run the current software suite and document failures separately.
2. Load and inspect the selected profile while motor power is off.
3. Open KASIM on the installed camera and confirm fresh frames.
4. Run KEREM on the actual track without motor output.
5. Inspect DORA/KADER/TAWNT diagnostics without treating them as physical passes.
6. Confirm SIGINT ends the process and leaves the software asking for zero output.

### 16.3 Verify bounded output with wheels secured

1. Secure or raise the wheels, clear the area, and keep physical power removal ready.
2. State expected left/right direction and stop behavior before output.
3. Use the operator's legal name and current time record.
4. Use SAC or local ARDA bench at the smallest useful output and duration after the
   seven-second cancel warning.
5. Observe each logical side separately, then a matching pair.
6. Record actual direction, motor grouping, start threshold, unexpected sound/heat,
   voltage behavior, and stop response.
7. Remove power immediately on unexpected behavior; do not compensate blindly in code.
8. Create a new YAREN profile for evidence-based calibration changes.

### 16.4 Move to a cleared surface

Only after the secured-wheel behavior is understood:

1. use a low-energy straight request on a cleared surface;
2. measure left/right bias and stop behavior;
3. verify mirror steering requests;
4. tune trim before control gain when the evidence shows mechanical asymmetry;
5. verify camera freshness under motor load;
6. repeat interruption, lane-loss, and watchdog stop cases at bounded energy;
7. record every result against commit and profile.

### 16.5 Close the basic lane loop

Only after camera, direction, trim, and stop behavior are known:

1. observe KEREM on the intended lane with output disabled;
2. verify controller sign from the recorded observations;
3. start autonomous drive through the physical start control;
4. use conservative speed and a cleared basic track;
5. inspect KADER after every run;
6. change one cause at a time;
7. require repeated, intervention-free basic lane runs before task work begins.

There is no requirement to restart the architecture if an observation fails. Return to
the smallest boundary that distinguishes configuration, perception, control, wiring, or
mechanics.

---

## 17. Roadmap after the basic car chain

The development order is intentionally plain:

1. profile and calibration;
2. camera acquisition;
3. lane perception;
4. controller request;
5. TAWNT validation;
6. GPIO output and stop;
7. KADER evidence;
8. repeated basic lane following;
9. competition tasks one at a time.

The task order below reflects value, dependency, and physical risk in the current 2026
official category. Recheck it against the next guide.

### 17.1 Traffic-light start

Status: `NOT IMPLEMENTED`.

Required real path:

- detect the current official start signal from actual camera frames;
- make the observation stable enough to reject brief noise;
- give DORA an explicit event rather than changing motor output in the detector;
- keep OSMAN at zero before the accepted start transition;
- log the observation, transition, and first motion request;
- reject stale or contradictory light observations;
- physically verify waiting and start behavior on an isolated setup.

### 17.2 Pedestrian and railway crossings

Status: `NOT IMPLEMENTED`.

These tasks may share a carefully defined stopping behavior, but their visual evidence
and official conditions remain separate. Each needs actual captured data, a stable event,
explicit DORA policy, bounded approach, full stop request, waiting/resume rule, and a
physical observation. Do not mark one complete because the other shares code.

### 17.3 Speed bump

Status: `NOT IMPLEMENTED`.

Required work includes real visual detection, correct approach timing, a speed policy
that remains above the physically measured motor dead zone, restoration of lane speed,
and evidence that the behavior neither stalls nor accelerates unexpectedly.

### 17.4 Parking

Status: `NOT IMPLEMENTED`.

Parking needs a real entry cue, camera-based geometry, explicit state progression,
bounded maneuvers, completion/abort conditions, and physical verification in the current
official layout. It must not become a timed open-loop script tuned to one guessed track.

### 17.5 Dead end

Status: `NOT IMPLEMENTED`.

The detector-to-DORA event contract must distinguish the official cue from other signs.
The maneuver needs a visible abort path, lane reacquisition, and logs that explain which
observation triggered it.

### 17.6 Overtaking

Status: `NOT IMPLEMENTED`; intentionally last.

Overtaking deliberately changes lane and has the largest interaction surface with false
detections, trap objects, track limits, state recovery, and physical space. It is not
started until the basic lane chain and earlier task/state patterns are physically
repeatable. Its scope is reduced or omitted before weakening stop behavior or basic lane
following.

### 17.7 Definition of done for one task

A task is not complete because its detector exists. Completion requires:

- support in the newest official guide;
- immutable real-camera input cases and held-back cases;
- an explicit observation contract with stale/invalid behavior;
- an explicit DORA transition or policy;
- bounded controller/motor requests through TAWNT and OSMAN;
- KADER evidence tying observation, state, and request together;
- regression checks for success and dangerous false triggers;
- isolated physical verification;
- repeated inclusion in full basic-track runs;
- an updated status in this plan.

---

## 18. Robustness and full-course qualification

After the selected task set works individually, robustness work increases confidence
without changing the evidence vocabulary.

Expected software and hardware cases include:

- camera unavailable, delayed, stale, malformed, or disconnected;
- low-confidence or contradictory perception;
- illegal or stale DORA events;
- TAWNT rejection, watchdog expiry, persistent fault, and reset procedure;
- OSMAN initialization/apply/stop/close errors;
- SIGINT and unexpected exceptions at each active stage;
- storage full, read-only, slow, or partially corrupt;
- cold boot, warm restart, duplicate process, and service crash;
- power sag, Pi undervoltage, heat, camera vibration, and changing illumination;
- configuration/profile mismatch after hardware change;
- loss of KERİM/network while preserving offline car operation.

Inject software faults through controlled tests, not a production fake-car mode. Inject
physical faults only when the exact fault can be introduced safely and reversed.

For endurance work, record duration, commit, profile, power state, environment, resource
behavior, faults, and recovery. Do not optimize away checks because a long run exposes
their cost; measure the cost and preserve the protection.

Full-course qualification begins only after individual tasks and critical faults have
clear evidence. Separate tuning runs from locked qualification runs. If code or profile
changes, start a new qualification series. Record task order, environment, battery,
time, rule violations, human intervention, and failure class for every run.

No permanent success percentage or consecutive-run count is invented in this plan. Set
the acceptance target from the newest guide, available track time, observed variance,
and a written team decision before the qualification series begins.

---

## 19. Offline release, SCHOOL operation, and competition preparation

A release candidate is one commit plus one exact YAREN profile and dependency set. It
must cold-boot and operate without KERİM, internet, a development laptop, or an external
account.

Before calling a build a release candidate:

- choose and tag the reviewed commit;
- record full profile/configuration hashes;
- verify clean installation or restoration on the target Pi;
- verify motor output remains zero until the physical start path completes;
- verify camera and profile failures are visible and keep output disabled;
- verify logs have a defined location and bounded storage policy;
- verify SIGINT, normal shutdown, fault shutdown, and physical power removal procedures;
- boot a recovery copy rather than assuming a copied image works;
- prepare a short printed operator/diagnostic card;
- roll back only to a release already verified with the same relevant hardware.

At SCHOOL, treat source changes and live output as separate decisions. A useful bug fix
may be made normally; energizing motors still requires the physical preparation and
warning. Keep work professional and role-based rather than embedding a permanent named
person hierarchy in code.

Competition preparation begins with the current official guide and announcements. It
includes application state, technical inspection, physical dimensions, camera-only
compliance, communication restrictions, start method, team access, batteries, spares,
tools, recovery media, printed checks, and exact release/profile identity. Do not depend
on remembered values from an older PDF.

After every official or serious physical run, preserve evidence before changing the car.
Update the post-mortem when a new failure teaches a reusable guard. A poor run is data;
an unexplained or overwritten run is lost data.

---

## 20. Current risks and open decisions

| Risk or decision | Current state | Next evidence/action |
|---|---|---|
| Current code has not moved the physical car | `PHYSICALLY UNVERIFIED` | Follow the secured-wheel return procedure before floor driving |
| Wiring may differ from the retained LEGACY map | `PHYSICALLY UNVERIFIED` | Inspect and record the current physical channel/pin arrangement |
| Current YAREN values may not match the present car | `PHYSICALLY UNVERIFIED` | Review against physical camera/motor measurements and create a new profile |
| School camera/track performance is unknown | `PHYSICALLY UNVERIFIED` | Capture real sessions and evaluate KEREM before live control |
| Stop request may not equal physical braking | `PHYSICALLY UNVERIFIED` | Measure electrical state and physical stop at bounded energy |
| Pi environment and offline boot are unknown | `PHYSICALLY UNVERIFIED` | Inventory, install, cold-boot, and recovery test when accessible |
| Existing race-task list may change next season | Open rule dependency | Recheck the official category/application guides when published |
| KERİM can drift toward ceremony instead of car work | Managed design risk | Preserve real-frame calibration, inactive sideload, exact release bundles, diagnostics, and bounded workshop boundaries; reject readiness theatre |
| LEGACY features may be lost during migration | Audited migration queue | Use the source-level inventory in section 14; port only a specific behavior justified by current failure, rules, or real evidence |
| Large recordings may overwhelm Git | Open storage decision | Keep manifests and small approved fixtures in Git; choose explicit storage for large immutable captures |
| Race acceptance targets are not yet selected | Open decision | Choose them before locked qualification using the newest guide and measured baseline |

Unknowns stay visible. An unknown does not block unrelated real work, but it cannot be
converted into a default that later looks measured.

---

## 21. Verification commands

Use focused checks while editing and the full relevant set before committing:

```powershell
py -m pytest -q tests
py -m compileall -q arac startech startech_cam tests deployment
node --check startech_cam/static/cam.js
py kontrol.py
```

`py kontrol.py` checks the current governing-document claims separately from the Python
suite. One green command does not make another command green.

Useful non-output checks include:

```powershell
py -m arac.main --help
py -m arac.ayar_cli --help
```

Real camera observation may be performed without OSMAN when an actual camera and valid
profile are available. Any command that can reach OSMAN is live output, even if the car
is expected to be absent or unpowered. Apply the legal-name, warning, seven-second cancel,
SIGINT, and physical-power rules.

After a bug fix, add or update a regression check where practical. A regression check is
valuable because it can fail later; a hard-coded green result is not a check.

---

## 22. Historical and post-mortem index

Historical material is retained to explain how the project changed. None of the entries
below govern current work.

| Record | Date/snapshot | Current interpretation |
|---|---|---|
| `LEGACY/` source | May 2026 build and later archive | Earlier moving-car implementation; wiring/behavior reference with known seam failures |
| `LEGACY/10_otonom_arac.pdf` | 2026 category guide | Local historical official-guide snapshot; check the official site for newer material |
| `Markdown/HATA_DEFTERI.md` | Review begun 4 August 2026 | Detailed LEGACY post-mortem and migration evidence |
| `Markdown/HATA_DEFTERI.pdf` | Snapshot built 19 August 2026 | Read-only post-mortem snapshot |
| `Markdown/HATA_DEFTERI_PAYLASIM.pdf` | Snapshot built 19 August 2026 | Shareable read-only post-mortem snapshot |
| `Markdown/PLAN.pdf` | Snapshot built 19 August 2026 | Retired plan snapshot; useful only for timeline/context |
| `Markdown/PLAN_Revision.pdf` | Snapshot built 5 August 2026 | Earlier retired plan snapshot |
| Retired `Markdown/PLAN_New.md` | Git history through 24 August 2026 | Superseded recreation/pre-approval plan; not current |
| Retired `ROADMAP.md` and `SIRA.md` | Git history through 24 August 2026 | Their still-real roadmap was merged here; old gates/dates are retired |
| `Tuna.txt` | Hand-written chronological record | Team timeline and reasoning; never a current instruction file |
| `examples/prototypes/` | KERİM/CAM design era | Historical UI/design references, not production behavior |
| StarTechConfig artifacts and references | Pre-KERİM Windows tooling | Outdated calibration tool and theoretical Pi sideload path; historical only |

Major current transition commits:

| Commit | Change |
|---|---|
| `a6c4845` | Replaced the vehicle scaffold with the existing-car driving core |
| `f417ac9` | Removed the retired team-task system from active project scope |
| `536a0ab` | Added the real bounded SAC workshop control path |
| `f39ef1d` | Removed non-production pretend vehicle paths |
| `baf759f` | Added closed real YAREN camera-frame jobs with strict receipts |
| `da911d9` | Added real-frame CAM perspective/HSV editing and inactive sideload |
| `8f46a55` | Made SAC authority labels explicit and added redacted diagnostics |
| `f4de0d7` | Added exact-revision CAM deployment, backups, health, and proxy guidance |

Git history is the detailed timeline. Do not duplicate commit-by-commit history in this
plan.

---

## 23. How this plan stays current

Update this plan in the same commit when a logical part changes status or future work.
The update should:

- describe the resulting current behavior;
- name the exact missing physical evidence;
- remove recreation steps for completed work;
- keep unresolved risks and next real outcomes;
- update the roadmap order when dependencies genuinely change;
- update official links when a newer guide appears;
- move superseded documents into the historical interpretation rather than deleting the
  evidence without reason.

Do not turn bug-fix work into a permanent pre-action essay. Explain completed work in
chat after the change. Keep detailed design decisions in the owning source, test, or
contract document when that is more useful than expanding this plan.

If work is interrupted, temporarily add an `Active work` section with the goal, status,
completed commits, current state, blocker, next action, and remaining verification. If
changes are uncommitted, include their exact files. Remove that section when the work is
finished so a future agent starts from current truth rather than an abandoned procedure.

The project direction in one sentence:

> Finish the real camera-to-lane-to-control-to-GPIO-to-stop-to-log chain, physically
> verify it when the car returns, and only then add officially supported tasks one at a
> time with actual evidence.

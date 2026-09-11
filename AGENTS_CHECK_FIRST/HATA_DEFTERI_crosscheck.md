# HATA DEFTERİ — current LEGACY cross-check

**Checked:** 11 September 2026 · GitHub `master` · `LEGACY` only  
**Handbook:** uploaded 21-page snapshot dated 19 August 2026  
**Coverage:** all 20 numbered defects and all seven collected guards. No sub-agents, repository changes, or hardware access.

## Result in brief

The handbook is useful historical evidence, but it is **not a current defect list**. Several exact bugs have been repaired; several fixes leave different failure modes. Hardware and historical-measurement claims cannot be established from source.

- **Original defects resolved:** #3, #4, #5, #17, #20.
- **Changed or partly repaired, with a remaining problem:** #1, #9, #10, #11, #18, #19.
- **Still present:** #6, #7, #12, #14 (for #14, concrete inaccurate/unsupported examples, not a claim about author intent).
- **Observable condition persists but the broader claim is unproven:** #2 (unity trims), #8 (no explicit PWM frequency).
- **Not found inside the permitted scope:** #13.
- **Hardware verification required:** #15 and #16.

“Resolved” means the **specific historical source defect** is absent, not that the subsystem or vehicle is physically safe. Counts above treat #6/#7 and #4/#5 as separate handbook numbers, even where the PDF groups them.

## Scope and evidence

A fresh GitHub directory read returned 27 LEGACY files. Each retained local file was independently rehashed as a Git blob and matched its current GitHub SHA. Relevant code was then re-read; the old audit was not simply assumed current. No source outside LEGACY was read, including PLAN_New.md, HATA_DEFTERI.md, other implementations, dependencies or deployment configuration.

The uploaded PDF was opened and its 21 pages extracted. Its instructions giving other documents authority were treated as historical document content, not permission to expand this review. Your statement that LEGACY is the active car code governs this cross-check. The previous 90-finding severity audit is left unchanged; this is a separate historical-to-current reconciliation.

## Numbered cross-check

| PDF # | Subject | Current verdict |
|---:|---|---|
| 1 | Perspective calibration mismatch | **Changed; unresolved** |
| 2 | All motor trims remain 1.0 | **Values persist; history unverified** |
| 3 | Balance tool emits unused trim names | **Original defect resolved** |
| 4 | Trims applied twice | **Original defect resolved** |
| 5 | Trim selected by command sign instead of wheel | **Original defect resolved** |
| 6 | Autonomous output lacks a usable sign_type | **Persists** |
| 7 | Trained sign model disconnected from the car | **Persists** |
| 8 | PWM frequency not explicitly configured | **Omission persists; causal claim unverified** |
| 9 | Caught frame errors keep motors running | **Partly repaired** |
| 10 | Logging stops at 120 seconds | **Original limit fixed; coverage gap remains** |
| 11 | Physical GPIO 16 start button removed | **Restored; behavior caveat remains** |
| 12 | Lane and crossing brightness detectors disagree | **Persists** |
| 13 | Second corrupted config file | **Not found within LEGACY** |
| 14 | Four inaccurate/generated reports | **Persists as unsupported documentation** |
| 15 | Motor overvoltage | **Hardware unverified** |
| 16 | Two motors share an undersized driver channel | **Hardware unverified** |
| 17 | CLAUDE.md lists phantom/missing states | **Original defect resolved** |
| 18 | Lane loss differentiates a fabricated faded error | **Original mechanism fixed; related reversal remains** |
| 19 | State speed scaling undoes dead-zone compensation | **Original floor breach fixed; steering defect remains** |
| 20 | Per-second derivative compared with per-frame thresholds | **Original defect resolved** |

### #1 — Perspective calibration mismatch

**Verdict:** Changed; unresolved · **PDF pages:** 7, 8

The quoted 640×480 quad is gone, but the underlying calibration problem remains. Current PERSP_SRC is [[225,289],[403,291],[200,6],[403,20]] for an 800×680 frame. The purported bottom corners are above the top corners and all source points are above y=292.

**Current evidence:** [config.py:11-24](https://github.com/egdmte/startech/blob/master/LEGACY/config.py); [config.py:27-74](https://github.com/egdmte/startech/blob/master/LEGACY/config.py); [lane.py:29-42](https://github.com/egdmte/startech/blob/master/LEGACY/lane.py); [lane.py:104-116](https://github.com/egdmte/startech/blob/master/LEGACY/lane.py).

**Remaining risk / qualification:** The current check warns rather than blocks. A new synthetic lower-road image returns no lane. The PDF's old −100 px estimate and old omitted-strip dimensions must not be reused for this different quad. An inset ROI need not cover the full image to be valid.

**Action:** Recalibrate in the exact normalized/rotated driving frame and reject invalid corner order, degeneracy and coordinate conventions before enabling motion; do not simply scale by coordinate maxima.

**Related IDs in the earlier audit:** `LEGACY-002`, `LEGACY-003`, `LEGACY-010`, `LEGACY-011`.

### #2 — All motor trims remain 1.0

**Verdict:** Values persist; history unverified · **PDF pages:** 8

All four live trims are still exactly 1.0. Code cannot establish that they were never measured, that measurements were lost, or that a measured unity trim would be wrong.

**Current evidence:** [config.py:154-157](https://github.com/egdmte/startech/blob/master/LEGACY/config.py); [motor.py:98-107](https://github.com/egdmte/startech/blob/master/LEGACY/motor.py).

**Remaining risk / qualification:** The PDF converts an observable default value into an unproven historical claim. It also proposes rejecting every 1.0 trim; a measured unity value can be valid.

**Action:** Measure and record per-wheel/per-speed calibration with provenance and acceptance checks. Validate calibration completion explicitly instead of rejecting a numeric value merely because it equals 1.0.

**Related IDs in the earlier audit:** `LEGACY-028`, `LEGACY-029`, `LEGACY-070`.

### #3 — Balance tool emits unused trim names

**Verdict:** Original defect resolved · **PDF pages:** 9

The active output now prints LEFT_TRIM_LOW/RIGHT_TRIM_LOW or LEFT_TRIM_HIGH/RIGHT_TRIM_HIGH. Midrange tests warn that neither profile is isolated. The old unconsumed LEFT_TRIM/RIGHT_TRIM output is no longer the recommendation.

**Current evidence:** [motor_balance_test.py:98-117](https://github.com/egdmte/startech/blob/master/LEGACY/motor_balance_test.py); [config.py:154-157](https://github.com/egdmte/startech/blob/master/LEGACY/config.py).

**Remaining risk / qualification:** This fixes the naming mismatch only. Baseline-reset advice, conditional wrong-wheel correction, low-speed clamping and invalid recommended trim values are separate remaining defects.

**Action:** Keep regression checks that emitted names exist in config; fix the calibration mathematics separately before trusting its recommendations.

**Related IDs in the earlier audit:** `LEGACY-028`, `LEGACY-029`, `LEGACY-070`, `LEGACY-071`.

### #4 — Trims applied twice

**Verdict:** Original defect resolved · **PDF pages:** 18

PDController contains no trim variable references. MotorDriver applies the selected left and right trims once, after the controller output. An isolated test with inputs (60,60), left trim .8 and right trim .9 produces (48,54), not squared products.

**Current evidence:** [controller.py:12-18](https://github.com/egdmte/startech/blob/master/LEGACY/controller.py); [controller.py:138-143](https://github.com/egdmte/startech/blob/master/LEGACY/controller.py); [motor.py:98-118](https://github.com/egdmte/startech/blob/master/LEGACY/motor.py).

**Remaining risk / qualification:** Dead-zone compensation still occurs in both layers, but that is not double trim and must not be conflated with this historical defect.

**Action:** Retain non-unit-trim tests through the complete controller-to-driver path and enforce trim ownership at the driver.

**Related IDs in the earlier audit:** `LEGACY-067`.

### #5 — Trim selected by command sign instead of wheel

**Verdict:** Original defect resolved · **PDF pages:** 18

MotorDriver selects LEFT profiles for the left argument and RIGHT profiles for the right argument. _get_trim uses absolute speed only to interpolate LOW/HIGH within that wheel's profile. There is no controller trim selection by sign.

**Current evidence:** [motor.py:98-107](https://github.com/egdmte/startech/blob/master/LEGACY/motor.py); [motor.py:125-136](https://github.com/egdmte/startech/blob/master/LEGACY/motor.py); [controller.py:12-18](https://github.com/egdmte/startech/blob/master/LEGACY/controller.py).

**Remaining risk / qualification:** The Turkish summary's reference to selecting trim by a traffic sign is not the detailed defect: the old issue concerned the mathematical sign of PWM. Real wheel identity/polarity is still unverified.

**Action:** Keep forward/reverse and unequal left/right trim tests; verify the physical channel labels safely before calibration.

**Related IDs in the earlier audit:** `LEGACY-014`, `LEGACY-029`.

### #6 — Autonomous output lacks a usable sign_type

**Verdict:** Persists · **PDF pages:** 15

The exact missing-key description is outdated: events.py now explicitly returns sign_type, but its value is always None. main.py still reads it, so autonomous sign-specific branches remain unreachable through this detector.

**Current evidence:** [events.py:170-171](https://github.com/egdmte/startech/blob/master/LEGACY/events.py); [events.py:245-258](https://github.com/egdmte/startech/blob/master/LEGACY/events.py); [main.py:432-446](https://github.com/egdmte/startech/blob/master/LEGACY/main.py).

**Remaining risk / qualification:** A declared placeholder is not implemented recognition. Also, the current dead-end state only brakes; the handbook's claim that its right-turn handling is already correct is not true of current code.

**Action:** Integrate a validated classifier into the runtime contract, expose capability readiness, and separately implement/verify the required right turn. Do not replace None with guessed labels.

**Related IDs in the earlier audit:** `LEGACY-020`, `LEGACY-063`.

### #7 — Trained sign model disconnected from the car

**Verdict:** Persists · **PDF pages:** 15

The six-class model exists, but the autonomous EventDetector does not load or use it. The model remains a standalone train/test asset, with no path producing classified runtime signs.

**Current evidence:** [events.py:245-258](https://github.com/egdmte/startech/blob/master/LEGACY/events.py); [sign_test.py:7-34](https://github.com/egdmte/startech/blob/master/LEGACY/sign_test.py); [sign_test.py:48-79](https://github.com/egdmte/startech/blob/master/LEGACY/sign_test.py); [train_sign.py:128-133](https://github.com/egdmte/startech/blob/master/LEGACY/train_sign.py); [sign_model.json](https://github.com/egdmte/startech/blob/master/LEGACY/sign_model.json).

**Remaining risk / qualification:** The standalone nearest-neighbor classifier also lacks unknown/background rejection. File existence and class-name agreement do not establish usable field recognition.

**Action:** Unify candidate extraction and preprocessing, add calibrated rejection/confidence and temporal validation, then connect the classifier before claiming sign-based missions work.

**Related IDs in the earlier audit:** `LEGACY-020`, `LEGACY-078`, `LEGACY-079`, `LEGACY-080`.

### #8 — PWM frequency not explicitly configured

**Verdict:** Omission persists; causal claim unverified · **PDF pages:** 9

Both motor PWM constructors still omit frequency, and no Python file inside LEGACY explicitly sets frequency or PWM_FREQ. This is an explicit-configuration omission, not proof that PWM is absent or malfunctioning.

**Current evidence:** [motor.py:51-52](https://github.com/egdmte/startech/blob/master/LEGACY/motor.py); [camtester.py:51-74](https://github.com/egdmte/startech/blob/master/LEGACY/camtester.py); [config.py](https://github.com/egdmte/startech/blob/master/LEGACY/config.py).

**Remaining risk / qualification:** The PDF itself marks #8 “YALAN” in its summary but retains a causal discussion later. The deployed gpiozero version, selected backend, actual waveform and relationship to the dead zone were not measured. Its 100 Hz default claim is not a live hardware measurement; “probably causes the dead-zone hack” remains unsupported.

**Action:** Identify the deployed driver/backend and measure the waveform and motor response under controlled load. Explicitly document the selected frequency after validation; do not prescribe 1 kHz merely because an older build used it.

### #9 — Caught frame errors keep motors running

**Verdict:** Partly repaired · **PDF pages:** 16

The handler now calls motor.brake() on each caught frame error and raises after 30 consecutive errors. The old handler that only printed and continued is gone.

**Current evidence:** [main.py:612-621](https://github.com/egdmte/startech/blob/master/LEGACY/main.py); [main.py:629-648](https://github.com/egdmte/startech/blob/master/LEGACY/main.py); [motor.py:145-153](https://github.com/egdmte/startech/blob/master/LEGACY/motor.py).

**Remaining risk / qualification:** The first print still precedes brake. A blocked/failed diagnostic can defeat brake-first ordering. Frozen captures and blocking dependencies are not ordinary caught exceptions, and shutdown has additional failure/retry gaps.

**Action:** Latch stop and attempt motor de-energization before diagnostics; isolate logging, add bounded acquisition and an independent command watchdog, and expose/retry incomplete cleanup.

**Related IDs in the earlier audit:** `LEGACY-044`, `LEGACY-046`, `LEGACY-065`, `LEGACY-069`.

### #10 — Logging stops at 120 seconds

**Verdict:** Original limit fixed; coverage gap remains · **PDF pages:** 17

LOG_DURATION_SEC is now 300, not 120. This exceeds the nominal 240-second race by 60 seconds.

**Current evidence:** [config.py:193-198](https://github.com/egdmte/startech/blob/master/LEGACY/config.py); [logger.py:25-52](https://github.com/egdmte/startech/blob/master/LEGACY/logger.py); [main.py:423-430](https://github.com/egdmte/startech/blob/master/LEGACY/main.py); [main.py:576-577](https://github.com/egdmte/startech/blob/master/LEGACY/main.py); [main.py:719-725](https://github.com/egdmte/startech/blob/master/LEGACY/main.py).

**Remaining risk / qualification:** The recording clock starts at logger construction, not actual race start. Waiting consumes the margin and can exhaust the entire log before driving. There is no demonstrated full-race coverage guard in scoped startup.

**Action:** Anchor driving coverage to actual race start or separate setup/driving sessions, assert the required recording interval, and make export failures observable/retryable.

**Related IDs in the earlier audit:** `LEGACY-040`, `LEGACY-041`, `LEGACY-046`.

### #11 — Physical GPIO 16 start button removed

**Verdict:** Restored; behavior caveat remains · **PDF pages:** 15

START_BUTTON_PIN=16 exists. main.py constructs gpiozero.Button, installs its when_pressed callback and calls setup during startup. The header still says the button was removed, but the implementation contradicts that stale comment.

**Current evidence:** [config.py:173-175](https://github.com/egdmte/startech/blob/master/LEGACY/config.py); [main.py:9](https://github.com/egdmte/startech/blob/master/LEGACY/main.py); [main.py:655-682](https://github.com/egdmte/startech/blob/master/LEGACY/main.py); [main.py:747-748](https://github.com/egdmte/startech/blob/master/LEGACY/main.py).

**Remaining risk / qualification:** Physical installation is not established by source. The callback sets _manual_green and bypasses actual green rather than merely arming readiness; failure to initialize the button allows fallback start paths.

**Action:** Separate button arming from optical-green acceptance, verify real wiring, surface readiness faults, and correct the stale header. Do not infer competition points from a code printout.

**Related IDs in the earlier audit:** `LEGACY-049`, `LEGACY-057`.

### #12 — Lane and crossing brightness detectors disagree

**Verdict:** Persists · **PDF pages:** 18

events._white_mask uses fixed WHITE_HSV_LOW/HIGH. LaneDetector applies perspective/CLAHE and selects DARK/NORMAL/BRIGHT thresholds from the processed image. They do not share an equivalent brightness decision or image stage.

**Current evidence:** [events.py:57-59](https://github.com/egdmte/startech/blob/master/LEGACY/events.py); [events.py:285](https://github.com/egdmte/startech/blob/master/LEGACY/events.py); [lane.py:69-95](https://github.com/egdmte/startech/blob/master/LEGACY/lane.py); [config.py:92-106](https://github.com/egdmte/startech/blob/master/LEGACY/config.py).

**Remaining risk / qualification:** The code difference is confirmed; the precise venue failure rate is unmeasured. Shared thresholds alone would not reconcile different preprocessing stages.

**Action:** Define shared photometric/normalization decisions with task-appropriate masks, and compare lane/crossing outputs on recorded lighting conditions. Calibrate the actual runtime pipeline.

**Related IDs in the earlier audit:** `LEGACY-030`.

### #13 — Second corrupted config file

**Verdict:** Not found within LEGACY · **PDF pages:** 18

The freshly fetched complete LEGACY listing contains config.py but no config_to_be_migrated.py. All 27 entries are files, with no nested directories in this scope.

**Current evidence:** `LEGACY current directory inventory`.

**Remaining risk / qualification:** This establishes absence only inside LEGACY. It does not prove that the older file was deleted from the entire repository, is absent from other branches, or has no outside replacement.

**Action:** Within LEGACY keep one active configuration source. A repository-wide duplicate-config search requires separately expanded permission and was not performed.

### #14 — Four inaccurate/generated reports

**Verdict:** Persists as unsupported documentation · **PDF pages:** 17

All four named reports remain and contain concrete contradictions: KP .60 versus current .30; derivative cap ±600 versus 150; five named helper methods absent from scoped Python definitions; sharpness constants absent; and FINAL_DELIVERY.md absent from LEGACY. The sandbox path and FPS/score claims remain.

**Current evidence:** [BASLA_BURADAN.txt:38-61](https://github.com/egdmte/startech/blob/master/LEGACY/BASLA_BURADAN.txt); [BASLA_BURADAN.txt:118-126](https://github.com/egdmte/startech/blob/master/LEGACY/BASLA_BURADAN.txt); [BASLA_BURADAN.txt:171-195](https://github.com/egdmte/startech/blob/master/LEGACY/BASLA_BURADAN.txt); [DOSYALAR_GUNCELEME_DURUSU.txt:23-51](https://github.com/egdmte/startech/blob/master/LEGACY/DOSYALAR_GUNCELEME_DURUSU.txt); [DEGISIKLIKLER_OZET.txt:22-74](https://github.com/egdmte/startech/blob/master/LEGACY/DEGISIKLIKLER_OZET.txt); [IMPLEMENTATION_SUMMARY.txt:84-99](https://github.com/egdmte/startech/blob/master/LEGACY/IMPLEMENTATION_SUMMARY.txt); [config.py:117-118](https://github.com/egdmte/startech/blob/master/LEGACY/config.py); [config.py:135](https://github.com/egdmte/startech/blob/master/LEGACY/config.py); [CLAUDE.md:20-21](https://github.com/egdmte/startech/blob/master/LEGACY/CLAUDE.md).

**Remaining risk / qualification:** Current scoped evidence proves these examples are inaccurate/unsubstantiated, not who fabricated them or every historical claim in the PDF. Some score figures are explicitly estimates. No physical measurement log was established. Current CLAUDE.md labels historical material non-authoritative, which reduces but does not correct the contradictions.

**Action:** Mark/rewrite the reports as historical unverified claims; mechanically validate named symbols and scoped files, and attach measurement provenance to performance statements. Avoid claiming that adding CLAHE can never improve FPS across any changed implementation.

### #15 — Motor overvoltage

**Verdict:** Hardware unverified · **PDF pages:** 18

The current software still has BASE_SPEED=62 and MAX_SPEED=85, but source inspection cannot confirm a 3-cell battery, motor rating, actual terminal voltage or current wiring.

**Current evidence:** [config.py:143-145](https://github.com/egdmte/startech/blob/master/LEGACY/config.py); [motor.py:114-118](https://github.com/egdmte/startech/blob/master/LEGACY/motor.py).

**Remaining risk / qualification:** The handbook's 9–10.6 V and ~175% figures are not current measurements. PWM duty is not equivalent to a safely regulated DC motor supply; a universal 57% limit is not justified from source alone.

**Action:** Confirm motor/driver ratings, battery configuration, terminal waveforms, thermal behavior and load conditions with qualified controlled measurements before establishing electrical and duty limits.

### #16 — Two motors share an undersized driver channel

**Verdict:** Hardware unverified · **PDF pages:** 18

The software exposes two motor output channels. It cannot establish whether each channel feeds one or two motors, the installed driver's limits or actual stall current.

**Current evidence:** [motor.py:26-31](https://github.com/egdmte/startech/blob/master/LEGACY/motor.py); [motor.py:46-52](https://github.com/egdmte/startech/blob/master/LEGACY/motor.py).

**Remaining risk / qualification:** Paralleled-motor wiring, simultaneous stall, protection behavior and current margin are hardware facts not demonstrated by this repository. The quoted 2 A budget is not a verification of the installed unit.

**Action:** Inspect the actual circuit and component ratings and establish current/thermal margins under controlled load. Do not deliberately stall or energize the car as part of a source audit.

### #17 — CLAUDE.md lists phantom/missing states

**Verdict:** Original defect resolved · **PDF pages:** 18

The current LEGACY/CLAUDE.md is a short working note with no state enumeration. It neither lists KIRMIZI_ISIK nor makes the old incomplete state-list claim.

**Current evidence:** [CLAUDE.md:1-24](https://github.com/egdmte/startech/blob/master/LEGACY/CLAUDE.md).

**Remaining risk / qualification:** This removes the cited contradiction; it does not establish complete documentation of the state machine. Separate drift remains, such as main.py's removed-button header.

**Action:** Generate any future state inventory from code or verified tests; keep runtime descriptions synchronized.

### #18 — Lane loss differentiates a fabricated faded error

**Verdict:** Original mechanism fixed; related reversal remains · **PDF pages:** 9, 10, 11, 12

The missing-lane branch now explicitly uses derivative=0.0. The old (faded_error−previous_error)/dt mechanism is gone, and the main lane controller clips correction to ±speed before mixing wheels.

**Current evidence:** [controller.py:59-78](https://github.com/egdmte/startech/blob/master/LEGACY/controller.py); [controller.py:123-143](https://github.com/egdmte/startech/blob/master/LEGACY/controller.py); [controller.py:145-146](https://github.com/egdmte/startech/blob/master/LEGACY/controller.py).

**Remaining risk / qualification:** A distinct reversal remains: proportional error fades while the integral stays frozen. With integral −50 and last error +10, the new isolated test changes wheel differential from +0.40 to −0.08 by the second missing sample. Also, (50,0) is still a turn about a stationary inside wheel; zero opposite-sign commands do not prove absence of every physical spiral.

**Action:** Preserve/decay a validated last steering command as a whole, or clear/decay integral during loss. Keep observation freshness, controlled recovery and time-bounded stop tests.

**Related IDs in the earlier audit:** `LEGACY-012`, `LEGACY-015`, `LEGACY-039`.

### #19 — State speed scaling undoes dead-zone compensation

**Verdict:** Original floor breach fixed; steering defect remains · **PDF pages:** 12, 13

SPEED_BUMP_SPEED is now 30 rather than 25. MotorDriver applies a final per-wheel minimum of 30 after trim/scaling. The old sub-floor command mechanism no longer describes current final PWM.

**Current evidence:** [config.py:161](https://github.com/egdmte/startech/blob/master/LEGACY/config.py); [config.py:263-267](https://github.com/egdmte/startech/blob/master/LEGACY/config.py); [main.py:517-533](https://github.com/egdmte/startech/blob/master/LEGACY/main.py); [main.py:547-555](https://github.com/egdmte/startech/blob/master/LEGACY/main.py); [motor.py:106-142](https://github.com/egdmte/startech/blob/master/LEGACY/motor.py).

**Remaining risk / qualification:** For input (70,50), bump scaling produces (30,21.43) and final flooring produces (30,30), eliminating steering. Approach scaling (35,25) becomes (35,30), weakening the differential. This is not a proof that actual motors can climb the bump; torque/current/friction remain unmeasured.

**Action:** Use one final wheel-pair allocator that reconciles speed limits, curvature, trim and actuator constraints. A maximum of 30 and minimum positive duty of 30 cannot support unequal positive wheel commands.

**Related IDs in the earlier audit:** `LEGACY-067`.

### #20 — Per-second derivative compared with per-frame thresholds

**Verdict:** Original defect resolved · **PDF pages:** 13, 14

The real-observation branch now uses error−prev_error without division by dt; comments state px/frame. The duplicated hardcoded derivative threshold is replaced by DERIV_SLOWDOWN_THRESHOLD. Correction is bounded to ±speed before wheel mixing.

**Current evidence:** [controller.py:73-78](https://github.com/egdmte/startech/blob/master/LEGACY/controller.py); [controller.py:101-120](https://github.com/egdmte/startech/blob/master/LEGACY/controller.py); [controller.py:130-143](https://github.com/egdmte/startech/blob/master/LEGACY/controller.py); [config.py:148-150](https://github.com/egdmte/startech/blob/master/LEGACY/config.py).

**Remaining risk / qualification:** New deterministic tests at 33 ms with seed 1 and noise std .5,1,2,3,5 yielded 0/100 derivative-slowdown events and 0/100 opposite-sign wheel pairs for every level. This does not validate physical control, variable-FPS behavior or all noise histories. The counter named pivot now counts correction clipping, not actual opposite-sign output; its report cannot be compared literally to the old pivot metric.

**Action:** Keep explicit units in names/config metadata and separate counters for saturation, inside-wheel stop and opposite-sign output. Retest first-sample derivative kick and state-specific parking commands independently.

**Related IDs in the earlier audit:** `LEGACY-013`, `LEGACY-054`.

## The seven guards

### Guard 1 — Resolution/hardware settings validated before operation

**Status:** Partial; not enforced adequately.

**Evidence:** config.py:27-74 warns, uses coordinate maxima rather than valid geometry, and continues. MotorDriver checks finite inputs/positive trims, but this is not comprehensive calibration/hardware validation. No scoped kontrol.py exists.

**Action:** Validate explicit calibration provenance and geometry/config contracts before arming, without requiring every valid inset ROI to span the full frame.

### Guard 2 — Configuration tools and consumers agree on names

**Status:** Current trim names repaired; enforcement incomplete.

**Evidence:** motor_balance_test.py:98-117 now emits the four correct names. General tools still use string/regex-based access; tune.py:67-84 can miss a key and report success.

**Action:** Validate complete assignments and consumer schema, require successful unique matches, and save atomically.

### Guard 3 — Declared shared event schema rejects missing capabilities

**Status:** Not implemented as the proposed guard.

**Evidence:** events.py:245-258 returns a dictionary with sign_type=None; main.py:433 uses get. The key now exists but recognition is not connected. A shape check alone would not detect an unimplemented capability.

**Action:** Add an explicit typed/runtime-validated schema and capability-readiness checks with clear UNKNOWN/unavailable semantics.

### Guard 4 — Brake first, then log the error

**Status:** Partial; required ordering still wrong.

**Evidence:** main.py:615 prints before main.py:617 brakes. Shutdown also prints before motor cleanup.

**Action:** Stop/latch actuation first in a protected path; make diagnostic failure unable to block that action.

### Guard 5 — Trim lives in one layer and is selected by wheel identity

**Status:** Implemented for the inspected main controller-to-driver path.

**Evidence:** controller.py has no trim references; motor.py:98-107 selects per-wheel profiles and applies once. A non-unit test yields (48,54) from (60,60).

**Action:** Retain end-to-end regression tests; do not confuse the separate duplicated dead-zone allocation with trim ownership.

### Guard 6 — Full-race telemetry with a rejecting coverage check

**Status:** Partial.

**Evidence:** config.py:193 is now 300, but logger.py:32 starts at construction and main logs while waiting. No scoped race-start coverage assertion was found.

**Action:** Separate setup/driving sessions and validate coverage from actual race start, plus persistence success.

### Guard 7 — Documentation claims are source-backed or measured

**Status:** Not satisfied by the retained historical reports.

**Evidence:** Four text reports still name absent methods/settings and unsupported metrics. CLAUDE.md:20-21 now makes historical material non-authoritative; that warning is not mechanical verification.

**Action:** Validate symbol references and attach run provenance to measurements; label historical estimates explicitly.

## New hardware-free test results

Only selected class definitions were extracted into isolated namespaces. Motor construction and camera acquisition were never invoked. Configuration values came from literal AST assignments. Motor output was intercepted by a fake writer.

| Check | Result |
|---|---|
| #4/#5 unequal trim | `(60,60)` with `.8/.9` trims → `(48,54)`, once, by wheel. Controller has no trim variable references. |
| #18 old faded-error derivative | Last error +100, then missing input at 40 ms → `(50,0)`, zero derivative-saturation/derivative-slowdown events, no opposite-sign pair. |
| #18 different retained-integral reversal | Last error +10, integral −50: differential +0.40 then −0.08; reversal remains through a different mechanism. |
| #19 bump allocation | `(70,50)` → scaled `(30,21.43)` → final `(30,30)`: floor enforced, steering lost. |
| #19 approach allocation | `(70,50)` → scaled `(35,25)` → final `(35,30)`: no sub-floor output, reduced steering. |
| #1 current perspective | Synthetic lane markings wholly in the lower road produce `error=None` using the current quad. |
| #14 source references | Five alleged helper methods and two sharpness constants are absent from scoped Python definitions/assignments. |

### #20 noise test on current controller

Each row uses 100 samples, a simulated 33 ms interval, and a seed-1 Gaussian sequence reset per noise level. These are deterministic CPU tests—not measured vehicle FPS, camera noise, or on-track behavior.

| Noise std (px) | Derivative slowdown events | Actual opposite-sign pairs | Correction-clipping count |
|---:|---:|---:|---:|
| 0.5 | 0/100 | 0/100 | 0/100 |
| 1 | 0/100 | 0/100 | 0/100 |
| 2 | 0/100 | 0/100 | 0/100 |
| 3 | 0/100 | 0/100 | 0/100 |
| 5 | 0/100 | 0/100 | 0/100 |

## Important corrections to handbook interpretation

1. **A turn around a stationary wheel does not prove opposite-sign commands.** A differential-drive vehicle can turn with one wheel at zero and the other forward. Slip, wheel labeling and physical wiring also limit deductions from external footage. The handbook’s stronger “physical proof” statement is not justified from that description alone.
2. **A successful crossing observed once does not validate a 30 cm threshold or every venue condition.** Treat the observed task completion as useful history, not metric calibration evidence.
3. **Do not reuse old numerical conclusions after the code changed.** The old perspective quad, 25-duty bump speed, 120-second log duration and derivative divided by dt no longer describe current code.
4. **The diagnostic counter called `pivot` changed meaning.** It counts correction clipping before wheel mixing, not actual opposite-sign output. A future nonzero count does not by itself prove the old powered-reversal problem has returned.
5. **Two proposed guards need refinement:** rejecting every 1.0 trim rejects potentially valid measured unity calibration; requiring a perspective ROI to span the full image rejects valid inset road views. Validate provenance and geometry instead.
6. **No electrical conclusion is established here.** Motor duty, supply pulse voltage, effective motor behavior, battery voltage and thermal/current margins are distinct quantities. The PDF’s fixed frequency/57%-duty recommendations need hardware-specific validation.
7. **The document’s age and provenance matter.** It says competition code was edited onsite and not retained, and labels some mechanism explanations hypotheses. This cross-check does not recreate the May build, determine which fault caused that run, or validate the event-strip measurements.
8. **Section 7b is not a current shipped defect.** The 800×600 mockup is explicitly described as caught before saving. Its referenced new implementation is outside LEGACY and was not inspected.

## Source fingerprints

Links refer to GitHub’s observed master paths and can change later. These Git blob hashes identify the checked bytes.

| Scoped file | Git blob SHA |
|---|---|
| `LEGACY/10_otonom_arac.pdf` | `9333f07464e9e4404717f668c9eb7b4b8c8eea2f` |
| `LEGACY/BASLA_BURADAN.txt` | `9691da762ca5be7de014d285ebcf7699d9216969` |
| `LEGACY/calibrate.py` | `f46c9ff2cf2a1414210ffa180bbce4fea48ca672` |
| `LEGACY/camera.py` | `eb5100616c020fc8abe59dff5675f073df393b0e` |
| `LEGACY/camtester.py` | `ae766cc47bc69bfe9b077f745263a97e61d9cebd` |
| `LEGACY/CLAUDE.md` | `7ce146c15173d615b27623e034f8dd16aeb778b9` |
| `LEGACY/config.py` | `df51afc5829920ed977d2b1d8f38da3cad4964c8` |
| `LEGACY/controller.py` | `1809fab64c0bc039f1f3d592ae7d954bc3b0a05f` |
| `LEGACY/DEGISIKLIKLER_OZET.txt` | `cc3332253e862d985f2aed66af2c031c6a5aa561` |
| `LEGACY/DOSYALAR_GUNCELEME_DURUSU.txt` | `f0be2c4b3311db57405c309d2cb014be78aa0760` |
| `LEGACY/events.py` | `bde3ee91d68dc53755cb39a514186a6581c4fcbc` |
| `LEGACY/hsv_tune.py` | `86d5d8fe564649f3d04d4ff30bb05487a7ab7141` |
| `LEGACY/IMPLEMENTATION_SUMMARY.txt` | `bbb454522f6f4ce6b62cf84bff9f4303f0a25868` |
| `LEGACY/import numpy as np.py` | `957b1b0c48b13774440899c7962c4f3cc9ebce07` |
| `LEGACY/kalibrasyon.py` | `5f61b82efe4f08bfe2aa6c6b4638fb0bd5a0e523` |
| `LEGACY/lane.py` | `b89e9a24320760cc46b61e12b3433909a32a7a39` |
| `LEGACY/logger.py` | `f6705b0ae161988e971dec6c16f611703ac5d937` |
| `LEGACY/main.py` | `1fb0a6ef35df15fa09c2c131bd7e1d3ea318f165` |
| `LEGACY/motor.py` | `334bd52ed66367cbf13edd59cee91f607365e937` |
| `LEGACY/motor_balance_test.py` | `721633f99bdd9df74b47cbf1cb76f030b3a7aa8c` |
| `LEGACY/pd_tune.py` | `e58e269eca400c57bdac4424355e7d10de1f6fcc` |
| `LEGACY/README.md` | `5f630bd9f36acfff82541ccdc299ae1f325cf156` |
| `LEGACY/sign_model.json` | `2d4bdd8a29fbda969a57b4da836564bac404e5e1` |
| `LEGACY/sign_test.py` | `ea02b0bb02444f887d87fa3ff2f99be126f9571b` |
| `LEGACY/train_sign.py` | `267895812940723b926a71cbc77e3ea7dbad00b4` |
| `LEGACY/tune.py` | `ad434866789797f8f6842d9edb8fdf7f1fd47986` |
| `LEGACY/yol_takip.py` | `c228227691ea1da3524530a9ef8e129fde9c1afe` |

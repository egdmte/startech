# LEGACY car-code audit

**Repository:** https://github.com/egdmte/startech  
**Reviewed:** 11 September 2026 · observed branch `master`  
**Scope:** `LEGACY` only · 19 Python files / 5,650 source lines · 27 scoped files recorded  
**Register:** 90 distinct findings (63 confirmed software behaviors; 27 conditional risks). **Ordered by filename and line, not severity.**

No repository file was modified. No vehicle entrypoint, real GPIO, camera, or driving connection was run. The review used source inspection, static compilation, synthetic images, and isolated fake devices/clocks. All 27 local source files matched the original GitHub blob hashes after review.

## 1. Answer: “will not touch car code / does not arm the car”

**There is no blanket no-touch/no-arm guarantee in the inspected scope.** No exact declaration “will not touch the car code” or “does not arm the car” was found in the scoped textual search. There are narrower statements and one important conflicting assumption:

- **[config.py:36-38](https://github.com/egdmte/startech/blob/master/LEGACY/config.py):** Why it does not stop: LEGACY is an evidence/experiment file; stopping would prevent the experiment; the hard error belongs in new code. **Assessment:** This is an explicit experimental-baseline assumption, not a motor-disable guarantee. It conflicts with the user-confirmed active-car role and with LEGACY/CLAUDE.md. The existing perspective check warns but does not prevent vehicle startup.
- **[CLAUDE.md:6-9](https://github.com/egdmte/startech/blob/master/LEGACY/CLAUDE.md):** This scoped note recognizes active vehicle use and says later repairs are physically unverified. **Assessment:** Consistent with the user's scope. References to files outside LEGACY were not followed.
- **[events.py:170-171,256-258](https://github.com/egdmte/startech/blob/master/LEGACY/events.py):** The detector explicitly declares recognition disconnected and always returns None for sign_type. **Assessment:** This is real missing functionality: dead-end and sign-based overtaking handlers cannot receive a recognized sign through this detector. The model existing on disk does not connect it.
- **[sign_test.py:48-55](https://github.com/egdmte/startech/blob/master/LEGACY/sign_test.py):** Importing the utility does not open the webcam; its main function does. **Assessment:** Narrowly accurate: the module creates a HOG descriptor at import, but camera acquisition is inside main and there are no motor writes. It is not a claim that main.py or the whole repository is disarmed.
- **[motor.py:31,55-58,74-79](https://github.com/egdmte/startech/blob/master/LEGACY/motor.py):** Driving commands are rejected if hardware is unavailable; conventional mock factories are rejected. **Assessment:** These are hardware-availability checks, not a separate arm/disarm mechanism. The independent mocked tests confirmed absent-GPIO and conventional mock rejection; they did not verify actual wiring.
- **[controller.py:38-42](https://github.com/egdmte/startech/blob/master/LEGACY/controller.py):** Diagnostic counters do not change behavior; they only count. **Assessment:** This describes the counters only. It does not state that controller outputs are harmless or that downstream motors are disabled.
- **[IMPLEMENTATION_SUMMARY.txt:141](https://github.com/egdmte/startech/blob/master/LEGACY/IMPLEMENTATION_SUMMARY.txt):** Historical statement: main.py was not changed; integration was automatic. **Assessment:** A historical change-summary claim, not a standing promise not to touch car code, and not evidence of a motor interlock. Historical performance percentages and test-pass statements were not accepted as field validation.
- **[import numpy as np.py:1,8-15](https://github.com/egdmte/startech/blob/master/LEGACY/import%20numpy%20as%20np.py):** The impossible branch refers only to the local _state != TUMSEK condition in this scratchpad. **Assessment:** The file prints arithmetic and has no motor/camera action. Its old stall message does not describe the present final motor-floor behavior; the current defect is steering collapse, not guaranteed zero PWM.

**Important distinction:** an initialized GPIO driver, a waiting-for-green state, a camera-only utility, and a file-editing calibration tool are different things. “No motor command” is not “does not edit the active configuration.” Waiting for green is not a separate disarmed state.

### Direct experimental-assumption quote

> “NEDEN DURDURMUYOR: LEGACY bir kanit ve deney dosyasidir … Programi durdurmak, calistirmak istedigimiz deneyin ta kendisini engellerdi. Sert hata YENI koda, ayar.py'ye ait.”

Translation: “Why it does not stop: LEGACY is an evidence/experiment file … Stopping the program would prevent the very experiment we want to run. The hard error belongs in new code, ayar.py.” This comment does not override the user-confirmed fact that `LEGACY` is the current car code. The referenced new-code files were not opened.

### Which scoped tools affect the car?

| Tool | Real motor path? | Persistent writes / outputs | Activation or scope |
|---|---|---|---|
| [main.py](https://github.com/egdmte/startech/blob/master/LEGACY/main.py) | Yes | CSV diagnostics | Real GPIO is initialized at startup; BEKLIYOR actively brakes. Green detection, SPACE, GG/EZ, or the start button enables driving. No independent arm latch. |
| [yol_takip.py](https://github.com/egdmte/startech/blob/master/LEGACY/yol_takip.py) | Yes | CSV diagnostics | GG/EZ or --auto starts lane-following. It intentionally omits event handling; it is not an inert preview. |
| [pd_tune.py](https://github.com/egdmte/startech/blob/master/LEGACY/pd_tune.py) | Yes | No persistent gain save in this utility | Runs controller outputs on real motors for the chosen test duration. It is a physical driving test. |
| [motor_balance_test.py](https://github.com/egdmte/startech/blob/master/LEGACY/motor_balance_test.py) | Yes | Prints proposed trim settings | Menu-selected straight or PWM-sweep tests energize motors; the script warns about lifting the wheels. |
| [camtester.py](https://github.com/egdmte/startech/blob/master/LEGACY/camtester.py) | Yes | No active-car config save | w/a/s/d drive in interactive mode; --smoke runs a movement sequence. The filename is not evidence that this is camera-only. |
| [kalibrasyon.py](https://github.com/egdmte/startech/blob/master/LEGACY/kalibrasyon.py) | Depends on menu choice | Yes: HSV save rewrites active config.py | Can run a motor test or launch motor-driving tools/main.py. Its camera/HSV choices are not representative of every menu choice. |
| [tune.py](https://github.com/egdmte/startech/blob/master/LEGACY/tune.py) | No motor writer found | Yes: Save rewrites active config.py | Camera/parameter tool. No motor command does NOT mean it leaves car code untouched. |
| [calibrate.py](https://github.com/egdmte/startech/blob/master/LEGACY/calibrate.py) | No motor writer found | Prints perspective values for manual insertion | Camera/geometry tool; no direct config write in its Enter handler. |
| [camera.py](https://github.com/egdmte/startech/blob/master/LEGACY/camera.py) | No motor writer found | No active-car config save | Camera inspection utility. |
| [hsv_tune.py](https://github.com/egdmte/startech/blob/master/LEGACY/hsv_tune.py) | No motor writer found | Collects/prints threshold values | Camera threshold utility; changes still require correct transfer/validation. |
| [sign_test.py](https://github.com/egdmte/startech/blob/master/LEGACY/sign_test.py) | No motor writer found | No active-car config save | Standalone webcam classifier, not the autonomous sign detector. |
| [train_sign.py](https://github.com/egdmte/startech/blob/master/LEGACY/train_sign.py) | No motor writer found | Yes: output sign model | Offline training/model export. |

## 2. How to read the findings

- **Confirmed** means the code behavior is established by inspection and/or a synthetic test, not that an on-car incident was observed.
- **Conditional** identifies the additional unverified trigger explicitly. A future sign-integration defect is not presented as already executing today.
- PWM numbers are commanded duty percentages, not measured wheel speed, distance, steering angle or stopping power.
- Camera/parameter-tool and diagnostic defects are included because they can miscalibrate the active car or hide failures. Entries identify when there is no direct actuation effect.
- Each stable issue ID has location, trigger, failure behavior, fix, and verification. The companion JSON carries the same IDs and source hashes for LLMs and follow-up tracking.
- This register records every distinct substantiated issue found in this review. It is not a proof that no other defects exist.

### Register by file (not severity)

| File | Findings |
|---|---|
| [calibrate.py](https://github.com/egdmte/startech/blob/master/LEGACY/calibrate.py) | 4 |
| [camera.py](https://github.com/egdmte/startech/blob/master/LEGACY/camera.py) | 2 |
| [camtester.py](https://github.com/egdmte/startech/blob/master/LEGACY/camtester.py) | 3 |
| [config.py](https://github.com/egdmte/startech/blob/master/LEGACY/config.py) | 2 |
| [controller.py](https://github.com/egdmte/startech/blob/master/LEGACY/controller.py) | 4 |
| [events.py](https://github.com/egdmte/startech/blob/master/LEGACY/events.py) | 10 |
| [kalibrasyon.py](https://github.com/egdmte/startech/blob/master/LEGACY/kalibrasyon.py) | 9 |
| [lane.py](https://github.com/egdmte/startech/blob/master/LEGACY/lane.py) | 5 |
| [logger.py](https://github.com/egdmte/startech/blob/master/LEGACY/logger.py) | 2 |
| [main.py](https://github.com/egdmte/startech/blob/master/LEGACY/main.py) | 24 |
| [motor.py](https://github.com/egdmte/startech/blob/master/LEGACY/motor.py) | 4 |
| [motor_balance_test.py](https://github.com/egdmte/startech/blob/master/LEGACY/motor_balance_test.py) | 3 |
| [pd_tune.py](https://github.com/egdmte/startech/blob/master/LEGACY/pd_tune.py) | 5 |
| [sign_test.py](https://github.com/egdmte/startech/blob/master/LEGACY/sign_test.py) | 2 |
| [train_sign.py](https://github.com/egdmte/startech/blob/master/LEGACY/train_sign.py) | 1 |
| [tune.py](https://github.com/egdmte/startech/blob/master/LEGACY/tune.py) | 8 |
| [yol_takip.py](https://github.com/egdmte/startech/blob/master/LEGACY/yol_takip.py) | 2 |

## 3. Complete issue register

### calibrate.py

#### LEGACY-001 — Camera ownership is not protected throughout setup and cleanup

**Location:** [calibrate.py:48–65](https://github.com/egdmte/startech/blob/master/LEGACY/calibrate.py)  
**Status:** Conditional. 

**Trigger / effect:** Interrupt after the camera starts but before the loop's `try/finally`, a GUI/trackbar/callback initialization exception, or a camera-stop exception. The Pi setup handlers in calibrate/hsv/tune catch `Exception`, not `KeyboardInterrupt`.

**What is wrong:** The camera can remain open in a caller that catches the exception, and the window teardown can be skipped when camera teardown raises. In the menu HSV tool, interrupting the post-start `bekle(1)` similarly bypasses its cleanup block. Evidence: `calibrate.py:48–65, 80–85, 95–120, 137–139`. Same ownership gap: `hsv_tune.py:34–65, 96–98, 160–170`; `tune.py:196–222, 500–512, 532–555, 601, 758–760`; `kalibrasyon.py:224–226`.

**Fix:** Establish one outer ownership `try/finally` immediately after acquisition; include all setup inside it. Use nested `finally` blocks so window teardown still executes if camera stop/close fails. Preserve the original exception while reporting cleanup failures.

**Verification:** Fake camera and GUI methods; inject failure or `KeyboardInterrupt` at each acquisition/setup point and failure in `stop()`. Assert every acquired camera is closed and window cleanup is attempted, without starting a real camera.

#### LEGACY-002 — Camera calibration, preview and driving tools use inconsistent orientation and color order

**Location:** [calibrate.py:67–90](https://github.com/egdmte/startech/blob/master/LEGACY/calibrate.py)  
**Status:** Confirmed. Confirmed code divergence; rotation divergence is active in the supplied configuration, BGR effects depend on the camera output convention.

**Trigger / effect:** Calibrating positions, lane geometry, or HSV using `camera.py` and then running `main.py` uses a different image orientation. On a Pi that needs color correction, displayed HSV and detector colors also differ. Values measured in the viewer do not automatically transfer. Use the shipped `CAMERA_ROTATE_180 = True`, or a Pi backend requiring `CAMERA_BGR_OUTPUT = True`.

**What is wrong:** `camera.py:15–16, 26–29, 65–77`; `config.py:184–185`; `main.py:119–127, 144–150`. The viewer does not import/apply `CAMERA_ROTATE_180` or `CAMERA_BGR_OUTPUT`. Runtime applies 180° rotation on both acquisition paths and optional BGR-to-RGB correction on the Pi path. The supplied rotation setting is `True`. `tune.py` rotates its view, while calibrate, menu HSV, hsv_tune, pd_tune, and yol_takip do not honor the rotation flag. The parent audit independently confirms that `main.py` also applies the configured 180° rotation; therefore these tools disagree with the driving entrypoint as well. This cross-check does not extend this report into an independent audit of main's state machine. Perspective points selected in one orientation are used in another; PD tests and lane-only driving do not reproduce the configured orientation. Calibrate, hsv_tune, menu HSV, pd_tune, and tune also assume a fixed Pi channel order instead of honoring the BGR flag. On the affected backend this swaps red/blue and corrupts color calibration. Yol_takip does honor the BGR flag, so its contract differs again. Evidence: `calibrate.py:67–90, 122–126`; related `kalibrasyon.py:201–203, 251–266`, `hsv_tune.py:101–110`, `pd_tune.py:70–76`, `yol_takip.py:100–113`; contrast `tune.py:224–238`, `config.py:178–185`.

**Fix:** Use one explicit camera-normalization boundary: validate channels and dimensions, normalize to RGB or BGR consistently, honor configured color order, and apply rotation exactly once before coordinates or masks are computed.

**Verification:** Feed a synthetic asymmetrical four-corner color chart through every fake capture adapter. With rotation/BGR flags toggled, assert identical normalized geometry and color values across calibration, preview, and driving consumers. Rotation mismatch is directly present in the shipped configuration; no physical channel order was assumed.

#### LEGACY-003 — Invalid perspective geometry can be accepted and exported

**Location:** [calibrate.py:95–110](https://github.com/egdmte/startech/blob/master/LEGACY/calibrate.py)  
**Status:** Confirmed. 

**Trigger / effect:** Drag corners onto one another, onto a common line, into a self-crossing arrangement, or exchange the intended top/bottom order, then save/accept.

**What is wrong:** Coordinates are only clipped to the image bounds; the tool exports an unusable or inverted homography. A CPU-only probe using four identical points produced a transform with determinant zero. The shipped `PERSP_SRC` itself places the purported lower points above the upper points (`config.py:24`), so meaningful ordering validation is especially relevant. Evidence: `calibrate.py:95–110, 133–136`; same gap `tune.py:535–553, 561–583`; consumer `lane.py:34–42`.

**Fix:** Validate four distinct points, convex nonzero-area polygon in the declared order, intended top/bottom relationship, and a well-conditioned transform before accepting. Keep the last valid transform when dragging passes through invalid geometry.

**Verification:** Test duplicate, collinear, crossed, reversed, and valid trapezoids. Invalid cases must not be saved or installed as the active transform; a valid case must map its corners correctly.

#### LEGACY-004 — Dragged coordinates are NumPy scalars, making copy-paste output version-dependent

**Location:** [calibrate.py:107–108](https://github.com/egdmte/startech/blob/master/LEGACY/calibrate.py)  
**Status:** Conditional. 

**Trigger / effect:** Drag a point under a NumPy version whose scalar representation is `np.int64(...)` (notably NumPy 2.x), then paste the printed list directly into `config.py`.

**What is wrong:** List interpolation uses NumPy scalar `repr`, so the supposedly paste-ready assignment can require an undefined `np` name and fail on the next config import. Evidence: `calibrate.py:107–108, 134–135`; `config.py` contains no NumPy import.

**Fix:** Convert clipped coordinates to builtin `int`, as `tune.py:548–551` already does; serialize only Python literals.

**Verification:** Under NumPy 1.x and 2.x, drag a point and require `ast.literal_eval` of the exported value to succeed. The available NumPy 1.26.4 probe passed; the NumPy 2.x consequence was not executed in this environment and is explicitly conditional.

### camera.py

#### LEGACY-005 — HSV cursor sampling refers to the raw frame even when the displayed image is transformed

**Location:** [camera.py:53–55](https://github.com/egdmte/startech/blob/master/LEGACY/camera.py)  
**Status:** Confirmed. Confirmed utility mismatch in bird/threshold modes.

**Trigger / effect:** A user selecting a pixel in bird/threshold mode does not inspect that transformed pixel's original HSV, and the readout is not shown on the selected display. Calibration observations are misleading or unavailable.

**What is wrong:** `camera.py:53–55, 76–91`; `lane.py:34–42`. Mouse positions are coordinates of the displayed window, but `hsv[cy,cx]` is read from the original unwarped frame. In transformed modes the text and cursor drawn on that raw frame are then discarded when `display` is replaced by the detector debug image.

**Observed reproduction:** Bird coordinate `(400,150)` maps through the actual inverse homography to approximately source `(310.14,162.74)`, but the viewer samples raw `(400,150)`.

**Fix:** Sample the displayed image's defined color space or map the cursor through the inverse transform to the original image; clamp to valid coordinates. Draw the readout after the final display selection and label whether values are raw or CLAHE-processed HSV.

**Verification:** Use uniquely colored coordinate markers and assert that cursor sampling returns the displayed marker's documented raw/processed HSV in every view.

#### LEGACY-006 — Threshold and bird-view switches produce exactly the same annotated image

**Location:** [camera.py:87–103](https://github.com/egdmte/startech/blob/master/LEGACY/camera.py)  
**Status:** Confirmed. Confirmed utility malfunction.

**Trigger / effect:** Pressing `t` does not expose the promised binary white threshold, and switching to `b` does not select a distinct plain bird view. The operator cannot inspect the actual mask independently of blend colors and annotations.

**What is wrong:** `camera.py:4–7, 60–61, 87–103`; `lane.py:157–161, 218–243`. Both `show_bird` and `show_thresh` take the same `detector.process` path and display the same annotated color/mask blend. No binary threshold image is obtained or displayed.

**Fix:** Expose named diagnostic outputs from the detector—raw bird frame, preprocessed frame, binary mask, annotated result—and bind each UI mode to its intended output.

**Verification:** With a synthetic multicolor image, threshold mode must contain only mask values 0/255; bird mode must be the intended transformed image; mode outputs must not be identical by construction.

### camtester.py

#### LEGACY-007 — Speed validation errors leave the preceding movement command active

**Location:** [camtester.py:87–91](https://github.com/egdmte/startech/blob/master/LEGACY/camtester.py)  
**Status:** Conditional. Confirmed helper behavior; persistent command requires a caller that catches the error and continues.

**Trigger / effect:** While moving, call a movement helper with NaN, infinity, an out-of-range speed, or a value that cannot convert to float; this can also result from an invalid edited test-speed constant.

**What is wrong:** Validation occurs before the `try` that calls `stop()` on errors. The helper raises but leaves the previous PWM command unchanged. A fake `forward(nan)` probe retained the prior 0.5 PWM. Evidence: `camtester.py:87–91, 110–120, 123–132, 135–145, 148–158`. The standalone CLI has an outer final stop; this entry does not claim that normal CLI unwinding omits that cleanup.

**Fix:** Validate inside a fail-safe command boundary that requests stop on any invalid command, or define and consistently enforce an explicit reject-and-hold policy; for this interactive test tool, fail-stop is the safer contract.

**Verification:** Start fake output at a nonzero value, issue each invalid speed through all movement helpers, and require a stop attempt before the validation exception is returned.

#### LEGACY-008 — Raw terminal mode removes Ctrl+C stopping, while EOF spins with the last command

**Location:** [camtester.py:197–209](https://github.com/egdmte/startech/blob/master/LEGACY/camtester.py)  
**Status:** Confirmed. 

**Trigger / effect:** Press Ctrl+C after raw mode is enabled; or let the input stream return EOF after motion.

**What is wrong:** `tty.setraw()` disables terminal signal generation, so Ctrl+C becomes `\x03`, which neither command loop recognizes. In camtester an empty read is also ignored, causing a tight loop with the preceding command still active. The outer `KeyboardInterrupt` handler does not fix raw-mode Ctrl+C. Evidence: `camtester.py:197–209`; corresponding raw-mode listener `pd_tune.py:150–168`.

**Fix:** Explicitly treat `\x03` and EOF as immediate stop/exit, or use cbreak mode with signals enabled. Do not continue driving after losing the input source.

**Verification:** Feed fake `w`, then `\x03`, and separately `w`, then EOF. Both must promptly stop and exit. Repeat for the PD listener; never initialize a real terminal or motor in the regression.

#### LEGACY-009 — Terminal restoration precedes motor stopping

**Location:** [camtester.py:210–212](https://github.com/egdmte/startech/blob/master/LEGACY/camtester.py)  
**Status:** Conditional. 

**Trigger / effect:** Exit the interactive loop while moving and have `termios.tcsetattr(..., TCSADRAIN, ...)` block waiting for terminal output to drain.

**What is wrong:** The stop call is not reached until restoration finishes. The outer entrypoint's final stop also cannot run while this call blocks. If the helper is called directly and restoration raises, its own stop is skipped. Evidence: `camtester.py:210–212`.

**Fix:** Stop output first, then restore terminal state in an independent `finally`; terminal cosmetics must never precede the safety action.

**Verification:** Fake terminal restoration that blocks or raises and record call order. Stop must be called first, and restoration failure must not suppress cleanup.

### config.py

#### LEGACY-010 — Default perspective maps the near view to the top of the input and omits the lower road

**Location:** [config.py:24](https://github.com/egdmte/startech/blob/master/LEGACY/config.py)  
**Status:** Confirmed. Confirmed for the shipped configuration; vehicle consequences conditional on running this configuration.

**Trigger / effect:** With the current full-frame interpretation, the bird image samples upper-frame content; its near/far semantics are vertically reversed relative to input y. The lower road cannot contribute, so valid bottom-of-frame lanes can be completely missed and unrelated upper-frame marks can steer the vehicle. This is not merely a missing resolution multiplier.

**What is wrong:** `config.py:11–24`; `lane.py:29–42, 66–67, 104–116, 142–153`. The ordered source points are `[[225,289],[403,291],[200,6],[403,20]]`; the first two map to the bird-image top, the last two to its bottom. The supposedly bottom points have smaller y coordinates than the top points. All source points are above y=292, despite an 800×680 input and road-event ROI y=300…679.

**Observed reproduction:** Inverse-transforming the bird center at top and bottom gives approximately `(315.66,290.02)` and `(303.69,14.18)`. A full 800×680 synthetic frame containing two white lane stripes only at y=350…679 returns `error=None` with the unmodified default transform.

**Fix:** Recalibrate the ordered road quadrilateral in the actual post-correction, post-rotation frame. Validate finite coordinates, bounds, nondegenerate area, corner order and intended road coverage before enabling motion. The active vehicle must not proceed merely because this file historically called itself an experiment.

**Verification:** Corner-tagged synthetic frames must map each named source corner to its intended destination corner; input road-near markers must appear in the bird near region. Known lower-road lane images must yield the expected signed error.

#### LEGACY-011 — Perspective diagnostic checks frame coverage, not transform validity

**Location:** [config.py:27–47](https://github.com/egdmte/startech/blob/master/LEGACY/config.py)  
**Status:** Confirmed. Confirmed; the comment saying warnings are intentional does not make invalid geometry safe for the active vehicle.

**Trigger / effect:** Valid calibrations are reported as incomplete while malformed, out-of-frame point sets can produce no warning. The printed proposed scale divides by coordinate maxima, not a known source-image resolution, so it is not a valid general resolution conversion.

**What is wrong:** `config.py:27–47, 49–69`. The diagnostic returns silently when `max(xs) >= WIDTH and max(ys) >= HEIGHT`. It does not check point ordering, self-intersection, nonzero area, or whether coordinates lie within the image. A legitimate perspective ROI also need not span the entire frame.

**Observed reproduction:** The valid full-pixel rectangle `[[0,0],[799,0],[0,679],[799,679]]` prints a warning. The out-of-bounds, self-crossing set `[[0,0],[900,800],[900,0],[0,800]]` prints nothing. Tests temporarily changed only the in-memory variable and restored it afterward.

**Fix:** Replace the frame-coverage proxy with real geometry validation. An inset road ROI is valid; crossed, repeated, collinear or out-of-bounds corners are not. For the active car, reject invalid geometry before GPIO activation; any experiment override must be explicit and unable to drive the car.

**Verification:** Valid inset road trapezoids and full-frame rectangles pass geometry checks; crossed, repeated, collinear, and out-of-bounds points produce the appropriate diagnostics regardless of their maxima.

### controller.py

#### LEGACY-012 — Frozen integral can reverse the steering direction during lane loss

**Location:** [controller.py:59–83](https://github.com/egdmte/startech/blob/master/LEGACY/controller.py)  
**Status:** Confirmed. 

**Trigger / effect:** The accumulated integral has the opposite sign to the most recent proportional correction when the lane disappears.

**What is wrong:** Missing samples decay prev_error but retain the full integral. The integral can overtake the fading proportional term and reverse wheel differential while no new lane observation exists, contrary to the intended retain-last-direction behavior.

**Fix:** Decay a validated last steering command as a whole, or clear/decay the integral when observation confidence is lost. Preserve the eventual stop deadline.

**Verification:** Independent fake tests with retained integral -50 and last real error +10 reverse the wheel differential by the second missing sample, before the eventual 30-sample stop.

**Related locations:** `controller.py:123-146`; `main.py:486-494`.

#### LEGACY-013 — First and reacquired lane observations receive a fictitious derivative kick

**Location:** [controller.py:69–78](https://github.com/egdmte/startech/blob/master/LEGACY/controller.py)  
**Status:** Confirmed. 

**Trigger / effect:** A controller reset or first start is followed by a nonzero lane error.

**What is wrong:** prev_error is seeded to zero and the first valid sample is differenced against it, even though no observed zero-error frame exists. Derivative slowdown and gain can command an unnecessarily sharp turn exactly at startup or reacquisition.

**Fix:** Seed error/time on the first valid observation and set derivative to zero until two comparable real observations exist. Reset derivative history after an observation gap according to an explicit policy.

**Verification:** With shipped constants, a first +60 px sample produces (50,0); a genuinely steady +60 history produces approximately (58.48,30). Preserve response to a real observed 0-to-60 change.

**Related locations:** `controller.py:31-36`; `controller.py:101-143`; `controller.py:239-245`; `main.py:499-504`.

#### LEGACY-014 — Lane correction sign conflicts with the documented forward-wheel convention

**Location:** [controller.py:122–143](https://github.com/egdmte/startech/blob/master/LEGACY/controller.py)  
**Status:** Conditional. 

**Trigger / effect:** Positive motor commands and left/right channels have the documented physical forward mapping.

**What is wrong:** lane.py returns mid minus lane center and documents positive error as needing a left turn. The controller increases the left command for positive correction. With positive-forward differential drive that turns the opposite way. Parking uses the opposite target-offset sign with the same mixer. Physical wiring is unverified; the reverse-pin selection alone does not prove physical direction.

**Fix:** Verify one vehicle-coordinate and wheel-polarity convention with the car safely supported. Reconcile lane error and wheel mixing with that convention; invert exactly one layer if required, and separately verify parking/overtaking directions.

**Verification:** The independent fake-clock test gives about (60.5133,54.4867) for steady +10 px. Assert corrective yaw for symmetric offsets in an explicit kinematic model, then validate real polarity without free-driving.

**Related locations:** `lane.py:145-153`; `controller.py:25-28`; `motor.py:198-209`; `main.py:287-289`; `main.py:366-375`.

#### LEGACY-015 — Deadzone compensation jumps at the inside-wheel zero boundary

**Location:** [controller.py:199–236](https://github.com/egdmte/startech/blob/master/LEGACY/controller.py)  
**Status:** Confirmed. 

**Trigger / effect:** A small change in error/history moves the inside-wheel request between a tiny positive value and exact zero.

**What is wrong:** Exact zero and small-positive commands take different compensation paths. The current pair allocator produces (54.999,30) for (49.999,0.001), but (50,0) for (50,0). A tiny control change therefore causes a large wheel-command discontinuity.

**Fix:** Design a single pair-allocation policy with explicit hysteresis around the transition to a stopped inside wheel. Preserve deliberate zero without making equality to zero an uncontrolled steering-mode switch.

**Verification:** Sweep around zero for both sides and test adjacent integer error histories; require the chosen bounded/hysteretic response and intentional stopped-wheel preservation.

**Related locations:** `controller.py:133-143`; `config.py:143-161`.

### events.py

#### LEGACY-016 — A solid green square can start the vehicle as a traffic signal

**Location:** [events.py:44–49](https://github.com/egdmte/startech/blob/master/LEGACY/events.py)  
**Status:** Confirmed. Confirmed detector behavior; active-vehicle use is conditional.

**Trigger / effect:** A persistent green square/object in the upper ROI passes as a green light. After debounce, the state is latched green and an awaiting vehicle can start without a real traffic signal.

**What is wrong:** `events.py:44–49, 87–97, 178–184, 230, 241–246`; `config.py:221–225, 242`; consumer `main.py:423–430`. Circularity only needs to exceed 0.55; a square's ideal circularity is approximately 0.785. There is no traffic-lamp housing, aspect/context, or maximum-area check.

**Observed reproduction:** A 40×40 pure green square at x=50…89, y=30…69 on a black 800×680 frame returns `traffic_light='green'` after six calls.

**Fix:** Use a calibrated signal candidate model with shape, size, and contextual checks. Choose a circularity/aspect constraint that actually rejects intended negatives; separately preserve the intended one-shot race-start latch.

**Verification:** Green squares, foliage-like blobs, and unrelated green objects must not start the system; a valid lamp sequence must pass only after the required distinct observations.

#### LEGACY-017 — A larger distant red blob suppresses a valid nearby parking slot

**Location:** [events.py:110–125](https://github.com/egdmte/startech/blob/master/LEGACY/events.py)  
**Status:** Confirmed. 

**Trigger / effect:** A smaller near red slot that independently passes both area and proximity is ignored when a larger, more distant red region is also present. The system fails to enter parking.

**What is wrong:** `events.py:110–125, 215–225`. The helper first selects the largest red contour anywhere in the parking ROI, then applies the near test only to that winner.

**Observed reproduction:** Red rectangle x=50…149, y=560…669 alone gives `parking_zone=True`. Adding a larger red rectangle x=300…499, y=250…449 changes it to `False`, although the near slot is unchanged.

**Fix:** Filter every contour for area and proximity before ranking eligible slot candidates; associate candidates across frames rather than allowing an unrelated distant blob to dominate.

**Verification:** A valid near slot stays detectable when a larger distant red object is added; the distant object alone stays negative.

#### LEGACY-018 — Obstacle color detection includes irrelevant off-lane objects

**Location:** [events.py:193–209](https://github.com/egdmte/startech/blob/master/LEGACY/events.py)  
**Status:** Confirmed. Confirmed color-only detection; whether an object is relevant requires scene/lane geometry.

**Trigger / effect:** A sufficiently large orange object at the far image edge can start an overtaking maneuver even when it does not obstruct the lane. An unrelated yellow patch anywhere in that ROI can inhibit overtaking.

**What is wrong:** `events.py:193–209`; `config.py:273–275, 308–310`; consumer `main.py:473–479`. Orange/yellow checks use the full-width road ROI and only minimum contour area, with no relation to the drivable lane or vehicle geometry.

**Observed reproduction:** A 50×50 HSV `(15,255,255)` patch at x=740…789, y=400…449 on an otherwise empty frame becomes `orange_car=True` after debounce.

**Fix:** Associate candidate objects with the current drivable corridor and track their position/extent. Validate vehicle/obstacle appearance and use a conservative policy for uncertain detections.

**Verification:** Translate the same synthetic candidate across lane and non-lane regions; it must affect maneuver policy only in the defined relevant region. Test orange and yellow independently.

#### LEGACY-019 — Global orange veto suppresses red parking and can reinterpret its overlap hue as an obstacle

**Location:** [events.py:203–205](https://github.com/egdmte/startech/blob/master/LEGACY/events.py)  
**Status:** Confirmed. Confirmed decision behavior; occurrence depends on object colors/scene.

**Trigger / effect:** (a) A separate orange object anywhere in the road ROI cancels an otherwise valid red slot. (b) A slot whose measured hue falls in the shared range can become `orange_car=True, parking_zone=False`; the consumer may choose overtaking instead of parking when other gates permit it.

**What is wrong:** `events.py:203–205, 211–225`; `config.py:273–275, 289–299`. Orange H=5…20 overlaps red H=0…10. `and not raw_orange_car` vetoes parking globally, not just for the red candidate that may have caused the overlap.

**Observed reproduction:** A true red near slot plus an unrelated orange 50×50 patch at x=650…699, y=310…359 yields no parking. A single large near HSV H=7 red/orange rectangle also yields `orange_car=True` and `parking_zone=False`.

**Fix:** Resolve overlap per associated object using geometry/context and explicit ambiguity handling. Do not use the existence of an unrelated orange blob as a blanket cancellation of every parking candidate.

**Verification:** Independent orange and red objects retain separate classifications; sweep slot hue across H=0…20 and verify ambiguous cases cannot silently select the wrong maneuver.

#### LEGACY-020 — The shipped sign model is completely disconnected from autonomous event output

**Location:** [events.py:245–258](https://github.com/egdmte/startech/blob/master/LEGACY/events.py)  
**Status:** Confirmed. Confirmed integration gap.

**Trigger / effect:** Any sign presented to `EventDetector`, including a valid dead-end or no-overtaking sign, never reaches the corresponding autonomous sign branches. Dead-end stopping and the eight-second sign-based overtaking prohibition are unreachable through this detector. Painting a blue blob does not make its content recognized.

**What is wrong:** `events.py:170–171, 186–188, 245–258, 371–381`; `sign_test.py:15–34, 48–79`; `main.py:66–70, 433–446`; `sign_model.json:1`. Runtime detection emits a generic blue flag but unconditionally emits `sign_type=None`. Only the separate webcam tool loads/classifies the model. The source itself explicitly acknowledges the disconnection.

**Observed reproduction:** Every tested event result contains `sign_type=None`, and the return value is a source literal. The model has classes `cikmazsokak`, `hemzemin`, `kasis`, `park`, `sollamabam`, and `yayagecidi`; their existence does not create a runtime connection.

**Fix:** Define and implement a shared sign-recognition component, output contract, confidence/rejection policy, and distinct-frame temporal confirmation, then connect only validated classes to the intended state machine. Do not merely fill `sign_type` from blue color alone.

**Verification:** Controlled synthetic/fake classifier outputs must propagate through `EventDetector` to each supported consumer branch; absent, unknown, or low-confidence signs must stay `None` and not cause maneuvers.

#### LEGACY-021 — Pixel-row “near” flags do not establish a 30 cm stopping distance

**Location:** [events.py:274–277](https://github.com/egdmte/startech/blob/master/LEGACY/events.py)  
**Status:** Conditional. Conditional physical-calibration/requirements gap, not a measured stopping-distance failure.

**Trigger / effect:** A different camera angle, height, rotation, ROI, frame rate, or vehicle speed makes the same pixel fraction correspond to a different physical stopping point. The code's “30 cm” annotation is not a guarantee; debounce also adds six-observation latency before the close signal.

**What is wrong:** `events.py:274–277, 318–321, 348–367`; `config.py:244–247`; consumers `main.py:448–467, 506–527`. Crosswalk proximity is any occupied lower bin; railway proximity is the largest y of any qualifying diagonal. Neither uses a measured ground-plane distance or accounts for speed and confirmation latency.

**Fix:** Calibrate ground-plane distance in the final normalized frame, define the vehicle reference point, and include processing/actuation/braking latency in the stopping policy. Preserve pixel heuristics only as explicitly nonmetric experimental approximations.

**Verification:** Synthetic projective scenes with known metric ground truth and fake speed/time should command stopping at the specified clearance across supported camera geometries and processing rates.

#### LEGACY-022 — Coarse crosswalk bins lose thin stripes and can discard the final full band

**Location:** [events.py:285–297](https://github.com/egdmte/startech/blob/master/LEGACY/events.py)  
**Status:** Confirmed. Confirmed; exact impact depends on projected stripe thickness and ROI height.

**Trigger / effect:** Four narrow, full-width stripes can disappear in their much taller bins, or a stripe can be split across adjacent bins. At ROI heights divisible by 12, the final full band is omitted, including potentially the closest stripe. Detection and the near decision become alignment-dependent.

**What is wrong:** `events.py:285–297, 318–321`. Each band must contain over 40% white area; sampling uses `range(0, roi_h - stripe_h, stripe_h)` rather than covering the whole ROI. The advertised thickness-similarity check is not implemented.

**Observed reproduction:** Four full-width, 10-row stripes at y=15,100,190,290 in the actual 380-row road ROI return `(False,False)`. In a 360-row ROI, a four-stripe pattern whose last stripe occupies rows 330…359 loses that final stripe and fails.

**Fix:** Derive stripe runs from a row-wise occupancy signal with appropriate filtering and minimum spans; cover all rows and then evaluate real stripe positions for proximity.

**Verification:** Sweep a four-stripe pattern vertically by single pixels, vary stripe thickness, and include a final stripe flush with the ROI bottom. Results should not change simply because of arbitrary bin boundaries.

#### LEGACY-023 — Crosswalk minimum counts occupied bins, not separate white stripes

**Location:** [events.py:288–315](https://github.com/egdmte/startech/blob/master/LEGACY/events.py)  
**Status:** Confirmed. 

**Trigger / effect:** Three broad stripes, rather than four separate stripes, can trigger both crosswalk and near-crosswalk events. The consumer can initiate an unnecessary stop.

**What is wrong:** `events.py:288–315`; `config.py:230–233`. `white_band_count=sum(bands)` counts adjacent bins of one stripe as multiple stripes. The transition threshold is `(N-1)*2 - 1`, so for N=4 it accepts five transitions, which three white runs can provide.

**Observed reproduction:** A 380-row HSV ROI with 31-row bin occupancy `[1,1,0,0,1,1,0,0,1,1,0,0]` has exactly three white runs. `_detect_stripe_pattern` returns `(True, True)` despite `CROSSWALK_MIN_STRIPES=4`.

**Fix:** Count distinct white runs/components separated by validated dark gaps; validate their widths/thicknesses and geometry rather than substituting bin occupancy for stripe count.

**Verification:** Three broad stripes fail, four or more valid separate stripes pass, and edge-start/edge-end patterns do not receive special off-by-one treatment.

#### LEGACY-024 — Any sufficiently wide flat rectangle is a speed bump

**Location:** [events.py:326–330](https://github.com/egdmte/startech/blob/master/LEGACY/events.py)  
**Status:** Confirmed. Confirmed false-positive behavior.

**Trigger / effect:** An ordinary wide white road marking or rectangle supplies top and bottom horizontal edges and triggers the bump state, with braking and reduced speed. Crosswalk paint can also satisfy this lower-level bump criterion.

**What is wrong:** `events.py:326–330`; consumer `main.py:468–472, 547–555`. The entire criterion is at least two image rows containing more than `WIDTH*0.55` Canny-edge pixels. No bump-specific shape, texture, height, or event disambiguation is checked.

**Observed reproduction:** A flat white 700×50 rectangle at x=50…749, y=100…149 in a black 800×380 road image returns `True`.

**Fix:** Add evidence appropriate to the intended bump marking/appearance, distinguish crossings and other horizontal markings, and validate with labeled negatives. At minimum do not interpret two generic edges as physical elevation.

**Verification:** Flat bars, ordinary rectangles, shadows, and crosswalk paint must be negatives; representative validated bump images must be positives.

#### LEGACY-025 — Nonintersecting lane-like diagonals are accepted as a railway X

**Location:** [events.py:342–368](https://github.com/egdmte/startech/blob/master/LEGACY/events.py)  
**Status:** Confirmed. 

**Trigger / effect:** Two spatially separated sloping lane boundaries can produce enough edge segments in each direction to satisfy the X detector and initiate a railway stop/approach.

**What is wrong:** `events.py:342–368`; `config.py:235–236`; consumer `main.py:458–467`. The method counts Hough segments by slope sign and never checks intersection, shared region, or whether multiple segments are the two edges of the same stripe.

**Observed reproduction:** Two thick white lines from `(10,300)` to `(210,100)` and from `(580,100)` to `(780,300)` never intersect in the ROI. The real Canny/Hough implementation nevertheless returns `(True,True)`.

**Fix:** Cluster duplicate edge segments into physical stripes, require an actual crossing within a plausible shared region, and validate X geometry and placement.

**Verification:** Separated diagonals and converging/diverging lane boundaries are rejected; a true crossing pattern passes, with duplicate Hough segments not counted as independent markings.

### kalibrasyon.py

#### LEGACY-026 — An empty answer authorizes physical motor motion

**Location:** [kalibrasyon.py:88–110](https://github.com/egdmte/startech/blob/master/LEGACY/kalibrasyon.py)  
**Status:** Confirmed. 

**Trigger / effect:** Press Enter without typing `E` at `Test başlasın mı? [E/H]:`.

**What is wrong:** The empty string passes the approval branch, opens motor GPIO, and starts a 50/50 drive after the countdown. The prompt does not declare a default affirmative answer; other drive launch prompts in the same menu require an explicit `e`. Evidence: `kalibrasyon.py:88–110`.

**Fix:** Require an explicit affirmative value for a motor test; an empty or unknown answer must cancel. Display an unambiguous motion warning before confirmation.

**Verification:** Fake input for empty, whitespace, `h`, unknown, and `e`; assert no motor construction or motion for the first four and the expected motion only for `e`.

#### LEGACY-027 — Non-finite deviation measurements yield plausible but arbitrary trim advice

**Location:** [kalibrasyon.py:129–151](https://github.com/egdmte/startech/blob/master/LEGACY/kalibrasyon.py)  
**Status:** Confirmed. 

**Trigger / effect:** Enter `nan`, `inf`, or `-inf`, all accepted by `float()`.

**What is wrong:** Only conversion errors are rejected. For example, `nan` falls through to the left-drift branch and produces `0.85`; infinity also produces capped advice instead of a validation error. The standalone helper already rejects non-finite measurements, so behavior is inconsistent. Evidence: `kalibrasyon.py:129–151`.

**Fix:** Validate `math.isfinite(sapma)` before classification or arithmetic; reject impossible measurements rather than proposing a trim.

**Verification:** Test NaN, positive/negative infinity, invalid text, zero, and finite signed deviations. Only finite measurements may generate recommendations. The NaN-to-0.85 arithmetic was reproduced safely.

#### LEGACY-028 — Recalibration throws away existing trims instead of correcting the measured baseline

**Location:** [kalibrasyon.py:136–157](https://github.com/egdmte/startech/blob/master/LEGACY/kalibrasyon.py)  
**Status:** Confirmed. 

**Trigger / effect:** Repeat a calibration after non-unit trims have already been installed.

**What is wrong:** The test measures an already-trimmed vehicle, but recommendations are rebuilt around `1.0`, and a balanced result says all values can remain at `1.0`. Following that advice can undo a successful calibration. In the standalone helper, the supposedly unaffected wheel is also reset to `1.0`. Evidence: `kalibrasyon.py:136–157`; same problem `motor_balance_test.py:66–86`; trims are applied during the measurement at `motor.py:98–107`.

**Fix:** Report and preserve the current active trim baseline. Either measure with explicitly neutral trims and clearly say so, or calculate a residual correction relative to the current profile. A balanced result should say to keep current values.

**Verification:** Simulate balanced motion with non-unit trims and require unchanged recommendations; simulate a small residual error and verify the recommendation is relative to the measured baseline.

#### LEGACY-029 — Trim correction targets the wrong wheel under the documented forward convention

**Location:** [kalibrasyon.py:140–157](https://github.com/egdmte/startech/blob/master/LEGACY/kalibrasyon.py)  
**Status:** Conditional. 

**Trigger / effect:** The left/right labels are physically correct and positive commands drive both wheels forward, as the driver interface documents.

**What is wrong:** A vehicle curving right has a faster left wheel relative to its right wheel. Both calibration helpers instead reduce the right wheel, increasing the curvature. The left-drift branch is symmetrically reversed. This is a physical-convention finding, not a hardware measurement. Evidence: `kalibrasyon.py:140–157`; same formula direction in `motor_balance_test.py:73–86`; convention `motor.py:27–30, 106–118`.

**Fix:** Verify wheel identity and signed forward motion with a lifted-wheel test, then derive the trim correction from that verified convention. Under the documented convention, right drift requires reducing left relative to right, not right relative to left.

**Verification:** Use a differential-drive kinematic model with known left/right speed imbalance. Apply the proposed trim and require reduced absolute curvature for either drift direction.

#### LEGACY-030 — HSV tools calibrate a different pipeline and can save the wrong adaptive profile

**Location:** [kalibrasyon.py:201–272](https://github.com/egdmte/startech/blob/master/LEGACY/kalibrasyon.py)  
**Status:** Confirmed. Confirmed preprocessing divergence; miscalibration depends on treating the viewer's raw HSV as the detector's threshold space.

**Trigger / effect:** Tune and save lane HSV values in the menu, then use `LaneDetector`.

**What is wrong:** `camera.py:76–84`; `lane.py:69–95`; `events.py:57–59, 173, 285`; `config.py:89–106`. The viewer reads raw HSV. Lane processing first applies LAB CLAHE and chooses among three adaptive HSV profiles. Event white detection instead uses the single fixed raw-HSV profile. Changing the generic `WHITE_HSV_LOW/HIGH` does not change the lane profiles imported by `lane.py:11–13`. The menu uses a raw full camera image, with a hard-coded 640×480 Pi request, and selects DARK/NORMAL/BRIGHT from its raw mean V. Runtime uses the configured 800×680 coordinate system, perspective-warped ROI, and CLAHE before selecting the profile and thresholding. A successful-looking menu mask can therefore save thresholds for the wrong runtime profile or produce a different lane mask. Evidence: `kalibrasyon.py:201–203, 250–272, 301–314`; compare `lane.py:66–95`, `config.py:11–12`.

**Observed reproduction:** Uniform RGB=120 has zero white pixels under the event mask (V minimum 140) but produces a valid lane error in the adaptive/CLAHE lane detector. Training and sign-test grayscale/HOG, by contrast, matched on identical RGB/BGR-equivalent image content.

**Fix:** Calibrate through the same normalization, perspective, CLAHE, and adaptive-profile selection functions as runtime. Show raw and processed images separately if both are useful; show the exact profile being edited and used.

**Verification:** Use a synthetic image with a bright upper scene and a dark road ROI. Assert that the calibration-selected profile and mask equal runtime's profile and mask, including CLAHE and configured dimensions.

#### LEGACY-031 — Saving HSV settings does not refresh the menu's cached configuration

**Location:** [kalibrasyon.py:231–238](https://github.com/egdmte/startech/blob/master/LEGACY/kalibrasyon.py)  
**Status:** Confirmed. 

**Trigger / effect:** Save HSV values, return to the same menu process, and reopen HSV calibration; or import config via a prior motor operation, then edit it externally.

**What is wrong:** `from config import ...` reads the already-imported module, not the newly written file. Sliders restart with stale values. A later save can overwrite the earlier calibration with those stale defaults. The tool also always initializes NORMAL values, even when the current lighting will select and save DARK or BRIGHT. Evidence: `kalibrasyon.py:231–238, 317–340`.

**Fix:** Keep an explicit in-memory settings object synchronized after save and initialize the selected profile, or reload a validated configuration snapshot before opening the tool. Avoid silently loading one profile and saving another.

**Verification:** Save distinct NORMAL, DARK, and BRIGHT values using an in-memory config store; reopen the menu without restarting the interpreter and verify the correct current profile and values appear.

#### LEGACY-032 — Configuration writes can leave the vehicle config truncated

**Location:** [kalibrasyon.py:319–339](https://github.com/egdmte/startech/blob/master/LEGACY/kalibrasyon.py)  
**Status:** Conditional. 

**Trigger / effect:** Disk-full/short-write/I/O error, interruption, or power loss after opening the destination for writing. Concurrent editors can also lose changes through read-modify-write.

**What is wrong:** The real `config.py` is rewritten directly, with no atomic replacement or validation of the final complete file. A failed save can leave an empty/partial Python module and prevent every importing tool from starting. Tune saves a group through repeated whole-file rewrites, also exposing mixed intermediate configurations. Evidence: `kalibrasyon.py:319–339`; same persistence hazard `tune.py:69–80, 132–138, 572–580`.

**Fix:** Apply the entire change set in memory, validate syntax and supported values, write and flush a temporary sibling file, then atomically replace. Detect concurrent edits; preserve the original on failure.

**Verification:** Inject failure after open and after a partial write, and simulate an intervening external edit. The original valid config must remain intact unless a complete validated update commits.

#### LEGACY-033 — Perspective-menu instructions invoke controls the child does not implement

**Location:** [kalibrasyon.py:400–411](https://github.com/egdmte/startech/blob/master/LEGACY/kalibrasyon.py)  
**Status:** Confirmed. 

**Trigger / effect:** Follow the menu's instructions to click four points, press `s` to save, or `r` to reset.

**What is wrong:** The child supports dragging existing points and Enter to print a manual assignment; `s` and `r` do nothing, and it does not automatically write the file. The advertised calibration completion path is unavailable. Evidence: `kalibrasyon.py:400–411`; actual child `calibrate.py:99–110, 129–136`.

**Fix:** Match menu instructions to drag + Enter + manual copy, or implement the advertised controls and a validated explicit save. Clearly distinguish printing from writing.

**Verification:** Check documented key bindings against the actual dispatch table and verify that the advertised save operation produces the stated persistence effect.

#### LEGACY-034 — Several handled startup/input failures are reported as process success

**Location:** [kalibrasyon.py:620–628](https://github.com/egdmte/startech/blob/master/LEGACY/kalibrasyon.py)  
**Status:** Confirmed. 

**Trigger / effect:** A caught menu exception, unavailable motor hardware in the standalone balance/PD tools, or invalid PD numeric input.

**What is wrong:** These handlers print errors but fall off the end without a nonzero exit status. `subprocess.run(check=True)` cannot distinguish those failed tests from success. This is an entrypoint error-signaling defect, not a claim that these scripts fail to parse. Evidence: `kalibrasyon.py:620–628`; `motor_balance_test.py:173–189`; `pd_tune.py:249–269`; launcher `kalibrasyon.py:57–64`.

**Fix:** Return structured status from a `main()` function and use `raise SystemExit(main())`; return nonzero for failure and a documented interruption code.

**Verification:** Statically check each entrypoint's exit mapping, or unit-test extracted orchestration with fake dependencies and a fake exit boundary. Unavailable hardware and invalid input must map to nonzero status without launching the actual entrypoint.

### lane.py

#### LEGACY-035 — Uniform lane-free backgrounds are accepted as two lanes

**Location:** [lane.py:76–95](https://github.com/egdmte/startech/blob/master/LEGACY/lane.py)  
**Status:** Confirmed. 

**Trigger / effect:** A broadly gray/white, low-saturation road region meets the adaptive white threshold. The two uniform half-frame centroids are treated as left/right lanes, yielding an apparently centered path instead of `None`. This can suppress lane-loss handling on a featureless surface.

**What is wrong:** `lane.py:76–95, 100–102, 119–143, 194–215`; `config.py:95–106`. The detector checks only sufficient histogram mass/peak, then takes each half's centroid. It never requires two narrow lane peaks, dark road between boundaries, or plausible lane occupancy.

**Observed reproduction:** Fresh identity-perspective detectors return `error=1` for uniform RGB frames at intensities 80, 100, 120, 160, 200, and 255. A uniform black control returns `None`.

**Fix:** Add local peak contrast, lane-width/shape and intervening-road checks, and reject saturated mask occupancy. Tune white thresholds against actual road negatives, not only white-line positives.

**Verification:** Uniform backgrounds across brightness and low-saturation colors return no lane; two realistic narrow boundaries still return the known midpoint.

#### LEGACY-036 — Signal thresholds accept a tiny isolated patch as a lane

**Location:** [lane.py:100–102](https://github.com/egdmte/startech/blob/master/LEGACY/lane.py)  
**Status:** Confirmed. 

**Trigger / effect:** A small bright reflection or isolated white patch survives morphology in a near/far slice. It becomes a valid lane with a substantial steering error; a near-region false detection is then retained by memory.

**What is wrong:** `lane.py:93–102, 111–113, 197–202`; `config.py:79–83, 330–335`. Histogram values retain the 0/255 mask scale. Continuity is only a fractional multiplier, not a minimum span requirement. Both total and maximum thresholds are 200 with the default quality ratio.

**Observed reproduction:** With only the perspective replaced by an identity transform in a fresh detector, a 6×6 white square at `(100,230)` on an otherwise black 800×305 bird frame produces `error=148`. A 5×5 square is rejected, establishing the acceptance boundary rather than merely assuming all noise is accepted. After the 6×6 patch disappears, its error remains valid for 25 blank calls.

**Fix:** Define thresholds in comprehensible pixel/coverage units; require adequate longitudinal span and lane-like connected geometry. A weak continuity multiplier plus an absolute 255-scaled peak is insufficient. Recalibrate after correcting P03.

**Verification:** Small isolated patches and reflections remain invalid across sizes, while long narrow true lines pass at comparable total pixel counts.

#### LEGACY-037 — Histogram Gaussian smoothing runs along the wrong axis and is a no-op

**Location:** [lane.py:111–113](https://github.com/egdmte/startech/blob/master/LEGACY/lane.py)  
**Status:** Confirmed. 

**Trigger / effect:** Every frame. Column spikes and fragmentation are not smoothed, despite the smoothing operation, leaving unstable column evidence and spurious narrow peaks intact.

**What is wrong:** `lane.py:111–113` reshapes the histogram to `(1,width)` but calls `GaussianBlur(..., (1,31), 0)`. OpenCV's kernel order is width, height; the 31-pixel dimension is applied to the one-row axis. The identical wrong-axis operation also exists at tune.py:358-360.

**Observed reproduction:** A `(1,800)` histogram with one nonzero column remains bit-for-bit identical after this exact blur; it still has one nonzero column.

**Fix:** Use a horizontal kernel such as `(31,1)` or a true one-dimensional convolution over columns, then retune thresholds for the resulting signal distribution.

**Verification:** A single-column impulse spreads symmetrically into neighboring columns, conserving expected total weight; edge behavior is tested separately.

#### LEGACY-038 — Fixed left/right half partition merges two real boundaries on one side

**Location:** [lane.py:119–126](https://github.com/egdmte/startech/blob/master/LEGACY/lane.py)  
**Status:** Confirmed. Confirmed algorithmic failure on the synthetic geometry; occurrence depends on turn/lateral offset.

**Trigger / effect:** During a sharp bend or large lateral offset, both actual boundaries project left or right of frame center. The computed path is biased toward the frame center or a nonexistent lane rather than the real lane midpoint.

**What is wrong:** `lane.py:119–126, 136–143, 188–215`; `config.py:85–87`. Peaks are not separately identified: all qualifying signal in a half is averaged. If both boundaries are in one half, their centroid is treated as one boundary and another half lane width is added/subtracted.

**Observed reproduction:** Two full-height 10-pixel lines at x=45…54 and x=345…354 have a geometric midpoint around x=199.5, requiring about +200.5 px error relative to x=400. The detector reports only +51 px.

**Fix:** Find separate connected peaks/curves globally, associate them temporally, and validate their separation. Use the one-boundary assumed-width fallback only when exactly one boundary is evidenced, not when multiple peaks have been averaged together.

**Verification:** Translate a known two-line lane across the frame, including both boundaries in either half, and compare the error to its ground-truth midpoint.

#### LEGACY-039 — Cached lanes are indistinguishable from observed lanes to the loss failsafe

**Location:** [lane.py:128–143](https://github.com/egdmte/startech/blob/master/LEGACY/lane.py)  
**Status:** Conditional. Conditional system-level failure; the cache duration itself is intentional and confirmed.

**Trigger / effect:** Both lanes disappear after a valid observation. The vehicle can continue treating an old estimate as current evidence for 25 processing calls before the separate 3.5-second loss timer even starts. The additional blind interval is about `25 / processing_rate` seconds, not a fixed measured safety duration. Stale near data can also dilute a real far-region change.

**What is wrong:** `lane.py:128–143, 164–177`; `config.py:108–109, 250–255`; `main.py:485–504`. Missing near observations remain `left_valid`/`right_valid` for 25 calls and produce a normal numeric error. The consumer starts its lane-loss timer only when `error is None`.

**Observed reproduction:** After one valid two-line frame, 25 black frames still return an error; the first `None` is on blank call 26. This was reproduced after the tiny false-positive patch too.

**Fix:** Return observed-versus-predicted status, confidence, and last-observation time separately from estimated error. Start safety timing at real observation loss while permitting bounded predictive steering.

**Verification:** A fake clock and recorded observation-validity sequence should start the loss deadline on the first truly missing observation, independently of frame rate and cached control estimates.

### logger.py

#### LEGACY-040 — Pre-start waiting consumes the entire driving log window

**Location:** [logger.py:25–52](https://github.com/egdmte/startech/blob/master/LEGACY/logger.py)  
**Status:** Conditional. 

**Trigger / effect:** The car waits long enough before the green/start signal; more than 300 seconds exhausts the shipped window.

**What is wrong:** Logger timing begins at construction and main logs BEKLIYOR frames. The first driving sample can arrive after logging has finished. Shorter waits also mix stationary samples into driving statistics and shorten coverage. This is diagnostic loss, not direct actuation failure.

**Fix:** Start a separate driving session at actual race start, or label and separate setup versus driving intervals with an explicit recording policy.

**Verification:** A fake 301-second pre-start wait finishes the logger before driving begins. Test several wait durations and require the intended complete driving window.

**Related locations:** `config.py:193-198`; `main.py:423-430`; `main.py:576-577`; `main.py:724`.

#### LEGACY-041 — Failed log persistence is permanently recorded as finished

**Location:** [logger.py:55–61](https://github.com/egdmte/startech/blob/master/LEGACY/logger.py)  
**Status:** Conditional. 

**Trigger / effect:** Report printing, CSV opening, writing or closing fails.

**What is wrong:** finished=True is set before reporting/export succeeds. Later finish/update calls return, so shutdown does not retry and subsequent data is discarded. A CSV-saved message is printed before the export attempt. This produces missing/misleading diagnostics and can cause a transient main-loop stop on the exception.

**Fix:** Separate recording-closed from export-success/failure, keep a bounded snapshot for retry, and report saved status only after successful atomic persistence.

**Verification:** An independent fake exporter that fails once is called only once despite a later finish. Make report/write fail then recover; require visible failure and an appropriate retry.

**Related locations:** `logger.py:40-43`; `logger.py:91-101`; `main.py:577`; `main.py:612-621`.

### main.py

#### LEGACY-042 — Camera startup does not wait for the first captured frame

**Location:** [main.py:89–142](https://github.com/egdmte/startech/blob/master/LEGACY/main.py)  
**Status:** Confirmed. 

**Trigger / effect:** The capture thread has not published its first image when drive_loop starts.

**What is wrong:** The two-second sleep happens before the capture thread starts. capture() immediately raises while _latest is None; the loop retries without delay and aborts after 30 errors. A healthy but slowly scheduled camera can therefore prevent startup.

**Fix:** Start capture, signal readiness after the first valid frame, and wait for that event with a monotonic deadline. Count acquisition timeouts, not unrestricted loop iterations.

**Verification:** The isolated capture test raises immediately with _latest=None. Add a fake camera delayed by several frame intervals and verify startup waits, while a never-ready camera fails safely.

**Related locations:** `main.py:612-621`; `main.py:719-725`.

#### LEGACY-043 — Runtime USB frames can retain an unexpected size while the camera viewer resizes them

**Location:** [main.py:104–150](https://github.com/egdmte/startech/blob/master/LEGACY/main.py)  
**Status:** Conditional. Conditional on a camera backend not honoring requested dimensions; confirmed with a fake capture device.

**Trigger / effect:** A USB backend returns, for example, 640×480 after being asked for 800×680. Perspective coordinates, pixel-area thresholds, road/signal ROIs, and the fixed-width edge fraction are now wrong relative to the frame. The diagnostic utility can still look correct because it resizes, hiding the deployment mismatch.

**What is wrong:** `camera.py:69–73` resizes USB frames to `(WIDTH,HEIGHT)`. `main.py:104–109, 144–150` merely requests dimensions, then returns the actual captured shape without resize/validation. Downstream geometry uses fixed `config.py:11–24, 204–209`; bump width uses `events.py:330`'s configured `WIDTH`. The same unnormalized USB size also passes through yol_takip.py:91-113.

**Observed reproduction:** Calling only the isolated `_Camera.capture` method with a fake USB reader returning 640×480 produces output shape `[480,640,3]`, not `[680,800,3]`.

**Fix:** Normalize runtime output to the calibrated size or reject a size mismatch; alternatively consistently rescale all geometry and thresholds from a declared source coordinate system. Use the same policy in the viewer.

**Verification:** Fake supported and unsupported camera sizes; every accepted frame must reach detectors with the declared dimensions and consistent geometry.

#### LEGACY-044 — A stalled Pi capture can leave the car driving from an indefinitely old image

**Location:** [main.py:119–141](https://github.com/egdmte/startech/blob/master/LEGACY/main.py)  
**Status:** Confirmed. 

**Trigger / effect:** capture_array() blocks without raising after at least one successful image.

**What is wrong:** Only the ndarray is saved. capture() continues returning _latest with no acquisition timestamp or freshness limit, so steering and events can remain based on an old road scene and the camera exception failsafe never fires.

**Fix:** Publish image, monotonic acquisition time, and sequence number together. Reject stale images and command a safe stop; add an independent motor command watchdog for blocking failures.

**Verification:** The hardware-free test confirms repeated capture() calls return the same stored object. Simulate a frozen producer and assert motion is inhibited after the freshness deadline.

#### LEGACY-045 — Repeated processing of one frame defeats consecutive-frame confirmation

**Location:** [main.py:135–141](https://github.com/egdmte/startech/blob/master/LEGACY/main.py)  
**Status:** Confirmed. 

**Trigger / effect:** The processing loop runs faster than the Pi camera, including during temporary capture stalls.

**What is wrong:** There is no new-frame gate. One optical observation can increment the event debounce counters six times, update lane memory repeatedly, and repeatedly integrate the same steering error. A single green frame can satisfy the nominal six-frame start check.

**Fix:** Process each acquisition sequence once, or make detectors reject duplicate sequence numbers. Base temporal confirmation on distinct frames and elapsed time.

**Verification:** Use one immutable image and unchanged sequence; repeated processing must not advance confirmation. Incrementing sequences should allow confirmation.

**Related locations:** `main.py:392-398`; `events.py:228-267`; `controller.py:75-83`.

#### LEGACY-046 — Blocking work can prevent the software stop path from running

**Location:** [main.py:144–146](https://github.com/egdmte/startech/blob/master/LEGACY/main.py)  
**Status:** Conditional. 

**Trigger / effect:** USB camera read, OpenCV processing, display, console output, or log export stalls while a previous motion command is active.

**What is wrong:** Motion commands have no expiry. The drive loop reaches braking only after calls return or raise. Q merely sets a flag; it cannot interrupt a blocking operation. Continued hardware output depends on the GPIO backend, but this program supplies no independent timeout protection. In particular, logger.update synchronously prints and writes the entire CSV when its duration expires, after the current iteration has already issued a motor command. In pd_tune.py, capture/processing can also exceed the advertised test duration because the duration and q flag are tested only before acquisition; the lane-only worker exception guard does not detect hangs.

**Fix:** Use bounded acquisition and a separate freshness/command watchdog. Keep display, reporting, and disk I/O off the control path; provide an independent physical emergency stop. Enforce a deadline at the motor boundary.

**Verification:** Block each fake dependency after a motion command; a separate watchdog must inhibit motors within the configured deadline, without waiting for drive_loop.

**Related locations:** `main.py:245-249`; `main.py:392-398`; `main.py:576-587`; `motor.py:82-118`; `logger.py:40-61`; `logger.py:64-101`; `pd_tune.py:159-180`; `yol_takip.py:172-201`; `yol_takip.py:242-258`.

#### LEGACY-047 — Buffered terminal reads can strand start or stop keystrokes

**Location:** [main.py:223–225](https://github.com/egdmte/startech/blob/master/LEGACY/main.py)  
**Status:** Confirmed. 

**Trigger / effect:** Multiple characters arrive together, such as pasted GG or a buffered stop key on POSIX.

**What is wrong:** select checks the underlying descriptor, while sys.stdin.read(1) can prefetch remaining characters into TextIOWrapper. Subsequent select calls report no data even though the Python buffer still contains a key. A start sequence or Q can remain unprocessed until more input arrives.

**Fix:** Use a consistent unbuffered nonblocking descriptor reader (for example os.read with an explicit decoder), or a dedicated buffered reader that drains its own input. Apply the same contract across terminal tools.

**Verification:** A hardware-free pipe containing GG\n reproduces first_ready=True, first_key=G, second_select_ready=False, while a direct second buffered read returns G.

**Related locations:** `pd_tune.py:163-168`; `yol_takip.py:144-153`.

#### LEGACY-048 — A quit request can be followed by another motion command

**Location:** [main.py:245–249](https://github.com/egdmte/startech/blob/master/LEGACY/main.py)  
**Status:** Confirmed. 

**Trigger / effect:** The keyboard thread sets _running=False after the main loop has passed its while condition.

**What is wrong:** The current iteration never rechecks the stop request before set_speed. A frame already being acquired or processed can issue a new motion command after Q. Shutdown occurs only when control returns to the loop boundary. The same pre-iteration-only cancellation check affects pd_tune.py:173-180 after q or its duration deadline.

**Fix:** Latch an emergency-stop request at the motor boundary and reject subsequent movement. Recheck the latch immediately before output; do not rely only on a loop flag.

**Verification:** A mocked capture that sets _running=False still produces a speed command in the current code. The regression must allow braking only.

**Related locations:** `main.py:392-394`; `main.py:503-504`; `main.py:767-768`.

#### LEGACY-049 — Manual start and the physical start button bypass the actual green light

**Location:** [main.py:251–270](https://github.com/egdmte/startech/blob/master/LEGACY/main.py)  
**Status:** Confirmed. 

**Trigger / effect:** SPACE, GG, EZ, or the GPIO start button is used while the traffic light has not turned green.

**What is wrong:** All these actions set _manual_green; drive_loop replaces the observed light with green. The physical button is presented as the competition readiness mechanism, but it starts driving instead of merely preparing the vehicle to wait for the real light.

**Fix:** Separate DISARMED, ARMED_WAITING_FOR_GREEN, and DRIVING states. Let the physical button arm only; require fresh optical green for competition movement. Put any deliberate manual-drive override behind a separate explicit test mode.

**Verification:** The mocked state test enters SURUYOR with _manual_green=True and traffic_light=None. Verify a readiness press leaves the car stopped until a real green signal.

**Related locations:** `main.py:409-430`; `main.py:655-660`; `main.py:733-736`; `10_otonom_arac.pdf:p15`.

#### LEGACY-050 — Losing the lane restarts the current overtaking phase instead of preserving progress

**Location:** [main.py:298–301](https://github.com/egdmte/startech/blob/master/LEGACY/main.py)  
**Status:** Confirmed. 

**Trigger / effect:** The lane is lost partway through the crossing or return phase and later reacquired.

**What is wrong:** Every missing-lane frame resets _state_timer. After reacquisition the car executes an entire new phase duration, discarding the distance/turn already performed. Repeated losses can substantially extend the lateral maneuver.

**Fix:** Abort to a safe stopped/recovery state, or retain completed active-motion time and validate lane position before continuing. Do not reset completed progress blindly.

**Verification:** After 1.0 seconds of a 1.2-second crossing, loss at 1.1 and reacquisition at 1.3 still leave phase=0 with timer=1.1. Verify recovery cannot repeat an entire completed segment.

#### LEGACY-051 — Overtaking completes by wall time without verifying lane change or obstacle clearance

**Location:** [main.py:303–328](https://github.com/egdmte/startech/blob/master/LEGACY/main.py)  
**Status:** Conditional. 

**Trigger / effect:** Speed, traction, lane geometry, or obstacle distance differs from the tuned assumptions.

**What is wrong:** The three phases use fixed durations and steering-error biases. Phase 1 immediately follows the available lane error, and phase 2 returns without confirming that the obstacle was passed or the target lane acquired. The state returns to normal driving even if the maneuver did not physically complete.

**Fix:** Track source and target lane plus obstacle position through the maneuver. Advance phases only after visual lane acquisition and clearance criteria; use timeouts as failures, not successful completion. Tune only after calibrated perception is validated.

**Verification:** Replay slow progress, wheel slip, partial lane changes, and an obstacle still alongside at the nominal return time; none should declare overtaking complete.

#### LEGACY-052 — Parking continues lane-following indefinitely after losing the parking target

**Location:** [main.py:357–364](https://github.com/egdmte/startech/blob/master/LEGACY/main.py)  
**Status:** Conditional. 

**Trigger / effect:** The red target disappears after PARK is entered, while the lane remains visible.

**What is wrong:** There is no target-loss deadline, search boundary, or return to a safe state. The car keeps moving at PARKING_SPEED under lane guidance rather than stopping or confirming the target can be safely reacquired.

**Fix:** Track the selected slot and maintain a short target-loss budget. Brake when it expires; reacquire while stopped or with a bounded, explicitly safe search.

**Verification:** Enter PARK, then provide valid lane errors but no red pixels for longer than the budget; verify a stop instead of continuing movement.

#### LEGACY-053 — Parking completion does not establish that the vehicle is inside the red slot

**Location:** [main.py:366–370](https://github.com/egdmte/startech/blob/master/LEGACY/main.py)  
**Status:** Conditional. 

**Trigger / effect:** A large red blob is horizontally centered, regardless of its relation to the vehicle footprint.

**What is wrong:** The terminal condition is only center tolerance and area greater than 12000 pixels. It checks neither slot boundaries nor calibrated distance/pose or full-vehicle containment. It can mark PARK_TAMAM while still outside or overhanging the slot.

**Fix:** Estimate the red slot polygon in a calibrated ground plane and vehicle pose/footprint; require containment and a stable stopped pose. Validate thresholds with measured recordings, not just blob area.

**Verification:** Synthetic centered red area immediately produces PARK_TAMAM. Replay centered targets at multiple physical distances and partial-overhang poses; only verified containment should complete parking.

**Related locations:** `config.py:293-301`; `10_otonom_arac.pdf:p17`.

#### LEGACY-054 — Parking steering bypasses the controller's forward-only and speed limits

**Location:** [main.py:372–375](https://github.com/egdmte/startech/blob/master/LEGACY/main.py)  
**Status:** Confirmed. 

**Trigger / effect:** The detected red target is sufficiently far from the image center.

**What is wrong:** PARKING_SPEED +/- 0.3*offset is sent directly to MotorDriver. An offset of 339 pixels produces approximately (131.7,-71.7); the motor layer clips the positive side but permits reversal. This can pivot the car at much more than the advertised parking speed.

**Fix:** Use a parking controller with an explicit maneuver mode, bounded wheel commands and validated steering polarity. If parking must be forward-only, saturate the steering correction to the forward base speed before common scaling; if reversal is needed, make it a deliberate, bounded state.

**Verification:** The synthetic off-center red rectangle reproduces opposite-sign wheel commands. Sweep all possible target columns and assert the approved wheel-speed and direction constraints.

#### LEGACY-055 — Control deadlines use adjustable wall-clock time

**Location:** [main.py:398](https://github.com/egdmte/startech/blob/master/LEGACY/main.py)  
**Status:** Confirmed. 

**Trigger / effect:** The system clock is corrected or changed during operation.

**What is wrong:** Approach, crossing stops, overtaking phases, lane-loss deadlines, and prohibition timers use time.time(). Forward jumps can end waits immediately; backward jumps can extend motion or holds. These are elapsed-duration decisions, not calendar timestamps. The controller also integrates a wall-clock jump as real dt: the independent +120-second jump test saturates integral to 50 even with a constant +1-pixel observation. Relative logger timestamps and duration share the same clock problem.

**Fix:** Use a shared monotonic clock for all control durations. Keep wall-clock values only for human-readable timestamps.

**Verification:** A fake wall-clock jump makes a newly entered crossing hold finish immediately. Repeat tests with forward/backward wall-clock jumps while monotonic time advances normally.

**Related locations:** `main.py:303-325`; `main.py:491-495`; `main.py:508-554`; `controller.py:33-57`; `logger.py:30-52`; `controller.py:80-83`.

#### LEGACY-056 — One negative detection rearms an event before the car has passed it

**Location:** [main.py:400–407](https://github.com/egdmte/startech/blob/master/LEGACY/main.py)  
**Status:** Confirmed. 

**Trigger / effect:** A crossing, bump, or orange obstacle flickers false while its maneuver is in progress.

**What is wrong:** Consumed flags reset on a single false event output, including during a five-second stop. If the same object becomes visible again, SURUYOR can repeat the stop or maneuver for that same object. Debounce requires six true frames but clears on one false frame, making this asymmetric.

**Fix:** Rearm only after the maneuver completes and the tracked object is confirmed passed/absent for a hysteresis interval. Keep object identity or passage geometry where possible.

**Verification:** A single false sample during YAYA_GEÇİDİ, followed by detection again, produces another crossing stop. Test flicker in all four consumed-event families.

**Related locations:** `events.py:262-267`; `main.py:535-555`.

#### LEGACY-057 — Optical green can enable motion without a separate operator arming action

**Location:** [main.py:423–430](https://github.com/egdmte/startech/blob/master/LEGACY/main.py)  
**Status:** Conditional. 

**Trigger / effect:** The program is started for observation or setup and its detector confirms green.

**What is wrong:** BEKLIYOR is a waiting-for-green state, not a disarmed mode. It transitions to driving with no arm latch. Startup also initializes GPIO and subsequently applies active braking. Calling the program a preview or assuming it does not arm would be unsafe.

**Fix:** Make observation-only the explicit default where appropriate, and separate operator arming from start-signal acceptance. Gate every motor writer on one arm/stop contract, with clear operator status.

**Verification:** The mocked state test enters SURUYOR with traffic_light=green and no manual authorization. Verify the desired safety contract before allowing optical starts.

**Related locations:** `main.py:719-725`; `motor.py:145-153`.

#### LEGACY-058 — Hazard handling is restricted to normal driving and misses hazards during maneuvers

**Location:** [main.py:432–483](https://github.com/egdmte/startech/blob/master/LEGACY/main.py)  
**Status:** Confirmed. 

**Trigger / effect:** A new crossing, dead-end, or overtaking prohibition appears during approach, bump traversal, overtaking, or parking.

**What is wrong:** Events are detected every iteration, but the special-state branches handle only their own local condition. In particular, SOLLAMA ignores a newly appearing yellow vehicle, and other moving states ignore stop events that would have changed SURUYOR.

**Fix:** Run a global safety/event arbitration stage before state-specific motion. Define allowed interruptions and safe abort/recovery transitions for every moving state.

**Verification:** Mocked events produce continued motion in YAYA_YAKLAS, HEMZEMIN_YAKLAS, TUMSEK, SOLLAMA, and PARK despite a different stop/prohibition event.

**Related locations:** `main.py:506-561`.

#### LEGACY-059 — A no-overtaking restriction expires by elapsed time rather than leaving its zone

**Location:** [main.py:444–446](https://github.com/egdmte/startech/blob/master/LEGACY/main.py)  
**Status:** Conditional. 

**Trigger / effect:** Sign classification is connected in the future and the vehicle stays in the restricted zone for more than eight seconds after the last recognition.

**What is wrong:** The prohibition is represented by now+8 seconds, not a tracked restricted zone or observed end condition. Stops and speed variation can make it expire before the prohibited road section ends. This branch is presently dormant because sign_type is always None.

**Fix:** Represent prohibited/permitted road-zone state and clear it only using validated zone-end evidence. Keep uncertain restriction state conservative.

**Verification:** Inject one prohibition sign, hold position for more than eight seconds, then show an orange obstacle; overtaking must remain blocked until zone-exit evidence.

**Related locations:** `main.py:203-204`; `main.py:473-474`; `events.py:256-258`.

#### LEGACY-060 — An orange obstacle still receives a driving command when overtaking is blocked

**Location:** [main.py:473–504](https://github.com/egdmte/startech/blob/master/LEGACY/main.py)  
**Status:** Confirmed. 

**Trigger / effect:** An orange vehicle is visible together with a yellow vehicle, or while the no-overtake timer is active.

**What is wrong:** Those conditions disable only the overtaking branch. If no other event applies, control falls through to normal lane following, with no obstacle stop or safe-follow behavior. The car can continue toward the detected obstacle.

**Fix:** Handle obstacle presence independently from permission to overtake: stop or maintain a validated safe distance whenever passing is not allowed/clear. Only start overtaking after an explicit clearance check.

**Verification:** Both orange+yellow and orange+active-prohibition test cases remain SURUYOR and issue a speed command. Both should instead enter a safe obstacle-wait state.

#### LEGACY-061 — Approach timeout is treated as successful arrival at the stopping point

**Location:** [main.py:508–533](https://github.com/egdmte/startech/blob/master/LEGACY/main.py)  
**Status:** Confirmed. 

**Trigger / effect:** The close-range crossing condition never arrives, or the lane is lost while approaching.

**What is wrong:** After four seconds, the approach changes to its five-second wait state and marks the event consumed, even without a close detection and even if the car spent the interval stopped. It can wait too far away, miss the required stopping position, then resume across the real crossing.

**Fix:** Make timeout an approach fault/reacquisition stop, not successful arrival. Require validated position evidence before marking the crossing serviced; pause progress accounting while motion is inhibited.

**Verification:** With no event evidence at 4.1 seconds, YAYA_YAKLAS enters YAYA_GEÇİDİ and consumes the event. Test both crossing types and lane-loss intervals.

**Related locations:** `config.py:267-268`; `10_otonom_arac.pdf:p16`.

#### LEGACY-062 — Bump slow mode can finish before the car crosses the bump

**Location:** [main.py:547–555](https://github.com/egdmte/startech/blob/master/LEGACY/main.py)  
**Status:** Confirmed. 

**Trigger / effect:** The car stops for lane loss, moves slower than assumed, or detects the bump well before reaching it.

**What is wrong:** TUMSEK ends after 1.5 wall-clock seconds regardless of whether movement occurred or the bump was cleared. Because speed_bump_consumed remains true, normal-speed driving can resume onto or over the same bump.

**Fix:** Use visual bump-entry/exit confirmation or calibrated progress; timeouts should stop/recover rather than declare success. Preserve slow mode until clearance is verified.

**Verification:** The mocked car with no lane remains braked but exits TUMSEK after the timer. Verify lane reacquisition before actual bump clearance does not restore normal speed.

#### LEGACY-063 — The dead-end state has no right-turn or recovery maneuver

**Location:** [main.py:563–564](https://github.com/egdmte/startech/blob/master/LEGACY/main.py)  
**Status:** Confirmed. 

**Trigger / effect:** The dead-end state is entered after classification is connected or injected.

**What is wrong:** CIKMAZSOKAK only brakes forever. The required task is to turn right before entering the dead end and continue along the course. Connecting the classifier alone will not implement that task.

**Fix:** Keep the safe stop as an entry behavior, then implement a validated right-turn maneuver with lane acquisition and timeout-to-stop. Never replace the safe stop with an unverified fixed turn.

**Verification:** Two mocked iterations remain permanently braked in CIKMAZSOKAK. Add a recorded right-turn scenario that reacquires the proper lane and safely rejects failed turns.

**Related locations:** `main.py:436-443`; `events.py:256-258`; `10_otonom_arac.pdf:p17`.

#### LEGACY-064 — Default graphical preview can prevent headless vehicle operation

**Location:** [main.py:580–589](https://github.com/egdmte/startech/blob/master/LEGACY/main.py)  
**Status:** Conditional. 

**Trigger / effect:** main.py runs without a working desktop/display or with a headless OpenCV build.

**What is wrong:** SHOW_PREVIEW defaults to True and imshow/waitKey run in the control loop. Unsupported GUI calls can raise repeatedly and trigger shutdown; some GUI backends may abort the process instead of raising a catchable Python exception.

**Fix:** Default vehicle operation to preview disabled or explicitly select a supported display mode. Check display availability before arming, and isolate optional visualization from motion control.

**Verification:** Run with a fake GUI that raises and verify driving does not start. Validate actual headless deployment with motors physically disconnected and an independent stop path.

**Related locations:** `config.py:188`; `main.py:612-621`.

#### LEGACY-065 — Shutdown can be marked complete before any motor cleanup occurs

**Location:** [main.py:629–648](https://github.com/egdmte/startech/blob/master/LEGACY/main.py)  
**Status:** Conditional. 

**Trigger / effect:** Console output raises (for example a broken pipe), or blocks, during shutdown.

**What is wrong:** _shutdown_complete is set before the shutdown print and before motor.stop. If that print raises, no device cleanup happens, and later shutdown calls return immediately because the complete flag is already true. The per-frame exception path also prints before braking. The same mark-complete-then-print-before-stop order appears in yol_takip.py:371-381.

**Fix:** Latch stop intent first, perform motor de-energization in a protected finally/best-effort path before diagnostic output, and only mark completed cleanup after it actually runs. Make diagnostics unable to prevent or permanently suppress stop attempts.

**Verification:** Inject a print failure before the cleanup loop, then invoke shutdown again; verify motor cleanup still occurs and incomplete cleanup remains retryable.

**Related locations:** `main.py:612-621`; `main.py:757-768`; `yol_takip.py:371-381`.

### motor.py

#### LEGACY-066 — Interruption during partial motor construction bypasses resource cleanup

**Location:** [motor.py:34–67](https://github.com/egdmte/startech/blob/master/LEGACY/motor.py)  
**Status:** Conditional. 

**Trigger / effect:** KeyboardInterrupt or SystemExit occurs after some GPIO devices are allocated but before MotorDriver construction returns.

**What is wrong:** The constructor catches Exception only, so these interruptions skip its cleanup. The caller's assignment has not completed and normal shutdown has no reference to the partially built object. This is a startup/recovery resource fault; movement from initial outputs was not established.

**Fix:** Catch BaseException narrowly around allocation, close already-created devices, and re-raise interruption unchanged. Keep ordinary hardware errors explicit.

**Verification:** Independent fake construction interrupted at the third device left both earlier devices unclosed. Ordinary OSError correctly cleaned them up. Test each allocation position for both error families.

**Related locations:** `main.py:637`; `main.py:716-720`.

#### LEGACY-067 — Slow-state scaling followed by a second deadzone floor erases steering

**Location:** [motor.py:106–142](https://github.com/egdmte/startech/blob/master/LEGACY/motor.py)  
**Status:** Confirmed. 

**Trigger / effect:** Both requested wheel speeds are positive during bump mode or parking's lane-following fallback.

**What is wrong:** Main scales the largest controller output to 30; MotorDriver then raises each nonzero wheel to at least 30. With the shipped unit trims, every such pair becomes (30,30). Example: (60.5133,54.4867) scales to (30,27.0122), then becomes straight-driving (30,30). Targets 35 and 40 also weaken some turns.

**Fix:** Combine state speed limiting, trim, deadzone and wheel-pair allocation in one final stage. Do not independently re-floor an already normalized pair. There is no unequal two-positive-wheel solution when both minimum and maximum permitted duty are 30; choose an explicit feasible policy.

**Verification:** Assert final fake PWM duties, not just controller outputs, through normal, bump, parking-fallback, approach and overtaking paths, including zero-wheel and trim cases.

**Related locations:** `main.py:306-324`; `main.py:361-363`; `main.py:517-533`; `main.py:551-553`; `controller.py:138-143`; `config.py:161`; `config.py:263`; `config.py:300`.

#### LEGACY-068 — Invalid deadzone settings can become full-duty motor output

**Location:** [motor.py:110–115](https://github.com/egdmte/startech/blob/master/LEGACY/motor.py)  
**Status:** Conditional. 

**Trigger / effect:** DEAD_ZONE_MIN_PWM is changed to a nonfinite value or a value above 100; the shipped value 30 does not trigger this.

**What is wrong:** Finite checks run before deadzone transformation. NaN, infinity or an excessive threshold can reach the clamp and convert a finite low command into 100% PWM instead of being rejected.

**Fix:** Validate all actuator settings before GPIO activation and recheck finiteness after every transformation, before clamping. Reject invalid bounds instead of hiding them with clipping.

**Verification:** Independent fake-device tests turn finite (10,10) into (100,100) with NaN, infinity or 101 thresholds. These configurations must fail before any nonzero output.

**Related locations:** `motor.py:91-109`; `motor.py:138-142`; `config.py:159-161`.

#### LEGACY-069 — Failed motor shutdown is silently treated as complete and cannot be retried

**Location:** [motor.py:166–188](https://github.com/egdmte/startech/blob/master/LEGACY/motor.py)  
**Status:** Conditional. 

**Trigger / effect:** The GPIO backend fails both an output-zero operation and device close.

**What is wrong:** stop sets _closed before disabling, suppresses failures, then clears _has_gpio. Later stop calls return without retrying unsuccessful devices. The software can report unavailable/closed while a backend has not actually disabled output. Physical persistence depends on the backend and was not measured. camtester.py:95-107 also suppresses all stop-write failures and can print that motors stopped without establishing success. Its separate device-close helper similarly suppresses failures (36-48).

**Fix:** Track cleanup success per device, attempt all outputs, expose de-energization failures and allow retry of incomplete cleanup. Use an independent hardware-safe stop where required.

**Verification:** A fake PWM at 0.62 that fails its first zero write and close remains at 0.62 after two stop calls; the second call attempts nothing. Require retry and visible failure reporting.

**Related locations:** `camtester.py:36-48`; `camtester.py:95-107`; `camtester.py:181-183`; `camtester.py:210-213`.

### motor_balance_test.py

#### LEGACY-070 — Low-speed calibration can measure the dead-zone clamp instead of motor trim

**Location:** [motor_balance_test.py:35–41](https://github.com/egdmte/startech/blob/master/LEGACY/motor_balance_test.py)  
**Status:** Confirmed. 

**Trigger / effect:** Select an allowed test speed below `DEAD_ZONE_MIN_PWM` (30), or a speed whose trimmed wheel command falls below 30.

**What is wrong:** Requested speeds and differences are lifted independently to the same floor. For example, a requested 10% test runs at at least 30% on both nonzero wheels, and low-profile trim differences can disappear. The printed speed and resulting trim inference do not describe the effective applied test. Evidence: `motor_balance_test.py:35–41, 98–116, 152–162`; `motor.py:98–115, 138–142`; `config.py:161`.

**Fix:** Restrict calibration to an unsaturated measurable range, account for existing trims, and display actual post-trim/post-dead-zone commands. Do not infer trim from a region where the actuator mapping is flat.

**Verification:** Exercise speed/trim pairs around the dead-zone boundary with a fake driver. Reject or clearly flag clamped measurements and assert the displayed effective PWM matches the command sent.

#### LEGACY-071 — Accepted measurements can produce zero or negative trims that the driver rejects

**Location:** [motor_balance_test.py:50–62](https://github.com/egdmte/startech/blob/master/LEGACY/motor_balance_test.py)  
**Status:** Confirmed. 

**Trigger / effect:** Enter finite positive travel distance with absolute deviation at least twice that distance, or values whose division overflows. Only finiteness of the inputs and positivity of distance are validated.

**What is wrong:** The formula yields trim ≤ 0, which is printed as a recommendation. For 300 cm deviation and 100 cm distance it prints −0.5. Installing that value makes the driver reject future motion commands; the helper emits configuration its own consumer forbids. Evidence: `motor_balance_test.py:50–62, 75–86, 101–117`; enforcement `motor.py:100–104`.

**Fix:** Reject inconsistent measurements and any non-finite/nonpositive result; use a physically justified, bounded correction range with explicit warnings for implausible curvature.

**Verification:** Test deviation/distance ratios around 2 and extreme finite inputs. No emitted trim may violate the driver's positive finite constraint. The −0.5 example was reproduced.

#### LEGACY-072 — PWM sweep ignores the supplied speed and duration options

**Location:** [motor_balance_test.py:130–140](https://github.com/egdmte/startech/blob/master/LEGACY/motor_balance_test.py)  
**Status:** Confirmed. 

**Trigger / effect:** Run the sweep selection after providing `--hiz` or `--sure`.

**What is wrong:** Startup reports the requested speed/duration, but the sweep always uses 50% for 1.5 seconds, ignoring both values. A user choosing a lower test speed can get a higher actual sweep command than the invocation suggests. Evidence: `motor_balance_test.py:130–140, 152–165, 179–180`.

**Fix:** Either apply validated options to the sweep or expose explicitly named per-mode options and print the exact sweep values before confirmation.

**Verification:** With fake motor and clock, select sweep using non-default options and assert actual commands/dwell times match the documented option contract.

### pd_tune.py

#### LEGACY-073 — ASCII error graph reverses its own vertical-axis labels

**Location:** [pd_tune.py:99–105](https://github.com/egdmte/startech/blob/master/LEGACY/pd_tune.py)  
**Status:** Confirmed. 

**Trigger / effect:** Plot a positive or negative nonzero error.

**What is wrong:** Increasing error increases the row index, so positive error is drawn lower, while the footer labels positive as upward and negative as downward. A +200 probe drew the mark in the bottom plotted row. Evidence: `pd_tune.py:99–105, 115`.

**Fix:** Invert the row mapping (`mid - scaled_error`) or correct the displayed axis labels consistently.

**Verification:** +ERROR_SCALE must occupy the labeled positive extreme, −ERROR_SCALE the negative extreme, and zero the center.

#### LEGACY-074 — The result can say 'stable' after extensive lane loss or earlier oscillation

**Location:** [pd_tune.py:128](https://github.com/egdmte/startech/blob/master/LEGACY/pd_tune.py)  
**Status:** Confirmed. 

**Trigger / effect:** A run contains many `error=None` frames, or more than 120 valid frames with large errors earlier than the retained tail.

**What is wrong:** Missing detections are discarded, and the summary uses only the deque's last 120 valid errors. A run with one zero-error sample and many lost frames can report 'stable'; a long run's early instability vanishes. This makes calibration evidence misleading even though the controller may have safely stopped on loss. Evidence: `pd_tune.py:128, 175–177, 190–194, 219–238`.

**Fix:** Track full-run valid/lost counts and streaming aggregate statistics separately from the rolling display deque. Report coverage and qualify or reject stability judgments when detection coverage is inadequate.

**Verification:** One valid zero followed by 100 missing frames must not yield an unqualified stable verdict; early high variance followed by a quiet tail must still appear in full-run metrics.

#### LEGACY-075 — A tuning run changes shared controller gains permanently within the interpreter

**Location:** [pd_tune.py:139–144](https://github.com/egdmte/startech/blob/master/LEGACY/pd_tune.py)  
**Status:** Confirmed. 

**Trigger / effect:** Call `run_tuning()` from a long-lived interpreter or alongside another controller, then finish or fail the test.

**What is wrong:** It assigns module-global `controller.KP/KD` and never restores them. Every existing and future `PDController` in that process sees the test gains, while `config.KP/KD` can still report the old values. This is in-process mutation, not a disk write, and it does affect `compute()`—the gains are not merely cosmetic. Evidence: `pd_tune.py:139–144, 196–217`; gain consumption `controller.py:111–123`.

**Fix:** Pass gains into an instance-scoped controller configuration. At minimum, restore prior globals in `finally` and forbid concurrent use, though instance ownership is preferable.

**Verification:** Construct two controllers with different intended gains, run a fake tuning cycle including an exception, and assert the unrelated controller and module defaults remain unchanged.

#### LEGACY-076 — Losing terminal control silently converts the PD test into an uninterruptible-by-q timed run

**Location:** [pd_tune.py:150–180](https://github.com/egdmte/startech/blob/master/LEGACY/pd_tune.py)  
**Status:** Confirmed. 

**Trigger / effect:** Non-TTY stdin, unsupported terminal handling, or an exception while configuring raw mode.

**What is wrong:** The exception is swallowed, the key listener immediately returns, and the vehicle still enters the motion loop while the UI advertises `q=dur`. A physical terminal with raw mode also has the Ctrl+C problem in F16. Evidence: `pd_tune.py:150–180`.

**Fix:** Fail closed when the advertised stop input is unavailable, or require an explicit noninteractive mode with a separate effective stop mechanism and accurate messages.

**Verification:** Fake `tcgetattr`/`setraw` failure and non-TTY input. Assert no motor motion starts under the interactive contract and no `q=stop` claim is shown for a disabled listener.

#### LEGACY-077 — Shutdown waits for the input thread before attempting to stop motors

**Location:** [pd_tune.py:196–207](https://github.com/egdmte/startech/blob/master/LEGACY/pd_tune.py)  
**Status:** Conditional. 

**Trigger / effect:** Exit/error while moving and a listener that is slow or blocked despite cancellation.

**What is wrong:** `thread.join(timeout=0.5)` runs before braking/stopping, adding up to 0.5 seconds of avoidable continued command at shutdown. No camera or GPIO malfunction is needed for the ordering defect; the maximum delay depends on listener behavior. Evidence: `pd_tune.py:196–207`.

**Fix:** Immediately disable or stop motor output, then join workers and restore terminal/camera resources. Do not put a potentially blocking join before the stop action.

**Verification:** Fake a listener that consumes the join timeout and record cleanup call order. Motor stop must precede join.

### sign_test.py

#### LEGACY-078 — Closed-set nearest-neighbor classification assigns an arbitrary sign to a blank blue object

**Location:** [sign_test.py:29–45](https://github.com/egdmte/startech/blob/master/LEGACY/sign_test.py)  
**Status:** Confirmed. Confirmed in `sign_test.py`; autonomous impact is conditional on S01 being fixed without additional safeguards.

**Trigger / effect:** A blue object with no symbol is accepted as a candidate and receives a plausible but false sign label. A successful-looking webcam test can therefore be misleading; wiring this result directly into driving would turn the false label into an action.

**What is wrong:** `sign_test.py:29–45, 73–79`; `sign_model.json:1`. Classification always returns the nearest stored label, regardless of distance, feature norm, margin, or whether the crop contains a sign. There is no unknown/background class or rejection branch.

**Observed reproduction:** A blank 80×80 blue square on a black full frame is found as bbox `(20,20,80,80)` and classified as `cikmazsokak`. Its uniform crop contains no semantic sign glyph.

**Fix:** Reject zero/weak descriptors, enforce a validated distance/margin or calibrated confidence threshold, and train/validate on nonsign blue negatives. Candidate shape/context and classification confidence must both pass.

**Verification:** Plain blue cloth/rectangles, blank crops, random textures, and out-of-distribution symbols return unknown; genuine sign positives retain acceptable recall.

#### LEGACY-079 — The webcam sign test and autonomous blue detector use incompatible candidate gates

**Location:** [sign_test.py:36–45](https://github.com/egdmte/startech/blob/master/LEGACY/sign_test.py)  
**Status:** Confirmed. Confirmed calibration inconsistency; autonomous classification is presently disconnected.

**Trigger / effect:** A sign that appears to work in the webcam tool can be ignored by the autonomous candidate detector, and small runtime candidates can be absent from the test tool. The test therefore cannot validate deployment thresholds or candidate coverage.

**What is wrong:** `sign_test.py:36–45, 70–77` uses full-frame H=100…140, S≥80, V≥50, 5×5 rectangular opening, and area≥500. `events.py:178, 188, 371–381` with `config.py:204–205, 317–319` uses only y=0…199, H=100…130, S≥120, V≥80, 3×3 elliptical opening, and area≥200.

**Observed reproduction:** A 20×20 H=110/S=255/V=255 patch is accepted by the event blue gate but rejected by the webcam gate. 40×40 patches at H=135, S=100, or V=60 pass the webcam gate and fail the event gate when their other channels are in range.

**Fix:** Share candidate preprocessing, ROI, thresholds, and morphology between training evaluation, the webcam utility, and runtime—or expose explicitly named separate profiles and compare them deliberately.

**Verification:** A common candidate fixture suite, including boundary hue/saturation/value, area, position, and shape cases, produces matching boxes/decisions in the shared path.

### train_sign.py

#### LEGACY-080 — Training full images and testing tight blue crops creates a framing-dependent feature mismatch

**Location:** [train_sign.py:45–48](https://github.com/egdmte/startech/blob/master/LEGACY/train_sign.py)  
**Status:** Conditional. Conditional; original training images are absent, so their actual framing and resulting accuracy were not established.

**Trigger / effect:** If training images include margins, sign poles, or surrounding background, training HOG describes a different scale/layout than the test crop. Even the same symbol can be distant in feature space, increasing misclassification.

**What is wrong:** `train_sign.py:45–48, 103–110` resizes each entire training image. `sign_test.py:36–45, 74–79` first bounds the blue region, then resizes only that crop at `29–32`.

**Observed reproduction:** A synthetic blue T sign padded from 64×64 to 128×128 before the training preprocessing differs from the tight inference crop by L2 distance approximately 0.8895, despite identical symbol pixels. This shows the conditional mismatch, not the accuracy of the supplied model.

**Fix:** Apply the same candidate crop/normalization to training and inference or enforce and validate a tightly cropped training-data contract. Store preprocessing metadata with the model.

**Verification:** The same sign with varied external padding and scale should produce equivalent normalized crops/descriptors, or be explicitly rejected as invalid training input.

### tune.py

#### LEGACY-081 — Config reader cannot read valid multiline values and silently substitutes a different perspective

**Location:** [tune.py:54–64](https://github.com/egdmte/startech/blob/master/LEGACY/tune.py)  
**Status:** Conditional. 

**Trigger / effect:** Format `PERSP_SRC` across multiple lines, a valid Python representation, or use a valid expression referring to another configuration value.

**What is wrong:** The reader evaluates only one assignment line in tune's namespace, swallows the failure, and supplies a hard-coded 640×480-style fallback rather than the real 800×680 calibration. For parameters without a default, values can remain `None` and fail later formatting/arithmetic. It is not a general Python-config reader despite presenting itself as one. Evidence: `tune.py:54–64, 123–130, 525–526, 596–597`.

**Fix:** Parse the configuration AST and extract supported complete literals, or load a validated explicit settings format. Report unsupported expressions rather than silently replacing safety-relevant values.

**Verification:** Read one-line and multiline equivalent point lists and require identical values. Unsupported expressions must raise a clear configuration error, not produce plausible fallback coordinates.

#### LEGACY-082 — Config writer reports success for missing keys and corrupts multiline assignments

**Location:** [tune.py:67–84](https://github.com/egdmte/startech/blob/master/LEGACY/tune.py)  
**Status:** Confirmed. Confirmed behavior; malformed-save trigger conditional

**Trigger / effect:** Save an absent/indented key, or save a multiline `PERSP_SRC` assignment.

**What is wrong:** `re.sub` can replace nothing but `_write_cfg` still returns `True`. For a multiline list it replaces only the first line, leaving old continuation lines behind. In-memory probes reproduced unchanged content with a True result and an `IndentationError` after a multiline perspective save. Evidence: `tune.py:67–84`.

**Fix:** Locate a complete assignment via AST/token spans; require exactly one intended match, replace the complete value, and parse the complete resulting file before committing. Return an accurate result.

**Verification:** Missing and indented keys must not falsely succeed; multiline saves must preserve valid Python and the intended value. Include comments and adjacent assignments in test fixtures.

#### LEGACY-083 — The live controls do not update the processor, and reload still uses cached config

**Location:** [tune.py:115–144](https://github.com/egdmte/startech/blob/master/LEGACY/tune.py)  
**Status:** Confirmed. 

**Trigger / effect:** Change HSV, CLAHE, or lane-related parameters with the advertised controls, optionally save, then press R.

**What is wrong:** Editing changes only `Param._val`. `_Processor` retains thresholds/values cached at construction. Saving writes disk but `_reload()` uses `from config import ...` from the already-loaded module. The panel can show new settings while the processed mask/error still uses old settings. An executed probe showed UI/disk `MIN_LANE_SIGNAL=210` but processor=200 even after `_reload()`. Evidence: `tune.py:115–144, 262–296, 587–593, 723–751`.

**Fix:** Feed an explicit in-memory settings snapshot into the processor on every edit; reload disk into that snapshot through a real validated reload path. Make save persistence-only, not the mechanism required for live preview changes.

**Verification:** Change a threshold on a fixed synthetic frame and require an immediate mask change without writing disk. Save/reload and require processor, UI, and stored values to agree. Executed stale-cache evidence is T03.

#### LEGACY-084 — Save failures and partial group saves still receive a success banner

**Location:** [tune.py:132–138](https://github.com/egdmte/startech/blob/master/LEGACY/tune.py)  
**Status:** Confirmed. 

**Trigger / effect:** `_write_cfg` returns False for an I/O error, fails to match, or one parameter save fails after earlier members of the group succeed.

**What is wrong:** `Param.save()` discards the result and `save_all()` unconditionally announces success. Perspective save also updates the preview transform and prints success even if disk persistence failed. Group writes are separate whole-file writes, so the disk can contain only part of a supposed successful change set. Evidence: `tune.py:132–138, 572–585`.

**Fix:** Return and check save results; apply the full group as one validated atomic transaction (F11); update success UI and active preview only after the intended commit succeeds.

**Verification:** Fail the first, middle, and last write using an in-memory store. Require no success banner and no partial committed group; display which operation failed.

#### LEGACY-085 — UI permits inconsistent speed limits, including a maximum below the actuator floor

**Location:** [tune.py:165–170](https://github.com/egdmte/startech/blob/master/LEGACY/tune.py)  
**Status:** Confirmed. 

**Trigger / effect:** Set MIN_SPEED=80 and MAX_SPEED=20, or set MAX_SPEED below `DEAD_ZONE_MIN_PWM=30`; both are allowed by the per-field limits.

**What is wrong:** There is no cross-field validation. The controller's clipping no longer represents the requested minimum/maximum contract, and a command capped below 30 can be lifted back to 30 by the motor driver, exceeding the supposedly configured maximum. The UI can save internally inconsistent vehicle settings. Evidence: `tune.py:165–170`; consumers `controller.py:108, 204–236`, `motor.py:112–115`, `config.py:161`.

**Fix:** Validate the entire speed configuration, including ordering and the motor's dead-zone contract, before applying or saving. Distinguish requested target speed from enforced effective PWM limits.

**Verification:** Test all boundary combinations, including 80/20 and a maximum of 20. Reject invalid combinations or explicitly represent the actuator-floor behavior; never silently advertise a violated maximum.

#### LEGACY-086 — Tuning preview does not reproduce runtime lane quality or memory behavior

**Location:** [tune.py:365–375](https://github.com/egdmte/startech/blob/master/LEGACY/tune.py)  
**Status:** Confirmed. 

**Trigger / effect:** Broad low-level histogram signal with total above MIN_LANE_SIGNAL but peak below MIN_LANE_SIGNAL × quality ratio.

**What is wrong:** Tune checks only total signal, while runtime also requires a sufficiently high peak. The preview can show a lane/error and encourage accepting a threshold that runtime rejects. A histogram of ones over 400 columns gave preview centroid 199; the actual `_find_peak` returned validity False with the shipped thresholds. Evidence: `tune.py:365–375`; compare `lane.py:194–215`, `config.py:80–83`. It also lacks the runtime memory/search-window behavior despite exposing those configuration fields (tune.py:174-175,262-296). PD/speed fields are configuration editing only; absence of real motor output is intentional, not itself a defect.

**Fix:** Reuse the actual detector's peak/quality logic instead of a separate weaker implementation. Preview output should include memory/quality status rather than imply equivalence where it is absent. Clearly label edit-only PD/speed fields; any controller demonstration should remain a pure, non-actuating simulation.

**Verification:** Run broad noise, isolated valid peaks, and lane-loss sequences through both implementations and require matching validity and positions. T12 reproduces the broad-noise discrepancy.

#### LEGACY-087 — Perspective preview toggle computes an image that is never displayed

**Location:** [tune.py:614–615](https://github.com/egdmte/startech/blob/master/LEGACY/tune.py)  
**Status:** Confirmed. 

**Trigger / effect:** In perspective mode, press P to toggle the documented bird's-eye preview.

**What is wrong:** P changes which transform is passed to processing, but mode 4 always displays `_draw_persp_overlay(bgr, ...)`, not the resulting bird image. Status numbers can change, yet the promised bird's-eye preview never appears. Evidence: `tune.py:614–615, 657–660, 753–756`.

**Fix:** Display the computed bird image or a raw/bird split view when toggled, with unambiguous coordinate mapping for dragging. Do not route mouse coordinates from a transformed display directly to raw points.

**Verification:** With synthetic distinct raw/bird images, toggle P and assert the visible image changes to the advertised preview; verify dragging still edits raw-coordinate points correctly.

#### LEGACY-088 — Keyboard dispatch makes Up collide with Reload and is backend-dependent

**Location:** [tune.py:695–696](https://github.com/egdmte/startech/blob/master/LEGACY/tune.py)  
**Status:** Confirmed. Confirmed collision; platform-specific consequences conditional

**Trigger / effect:** An OpenCV backend emits Up as code 82, which the code explicitly expects; or emits extended Windows/X11 key codes that are truncated to eight bits.

**What is wrong:** Code 82 is also `ord('R')`, so the earlier reload branch captures it and the intended Up increment branch is unreachable for that value. On Windows, extended arrow codes lose their distinguishing bits; X11 Shift+Tab's low byte is not either listed backward-tab code. The documented keyboard controls are not portable and Up can discard/reload edits instead of incrementing. Evidence: `tune.py:695–696, 709–739`.

**Fix:** Use `waitKeyEx()` and explicit backend-aware extended key mappings that do not collide with letters, plus portable alternative keys. Remove the duplicate ordinary-Tab test from the Shift+Tab branch.

**Verification:** Table-test ASCII R, ordinary Tab, Shift+Tab, and arrow/Page keys for supported GUI backends. Each must invoke exactly its intended action; Up must not call reload.

### yol_takip.py

#### LEGACY-089 — Shutdown closes resources while the drive worker may still use them

**Location:** [yol_takip.py:172–216](https://github.com/egdmte/startech/blob/master/LEGACY/yol_takip.py)  
**Status:** Conditional. 

**Trigger / effect:** Signal or main-thread shutdown overlaps capture, lane processing, motor write, or logging in the daemon drive thread.

**What is wrong:** `_running=False` only prevents the next loop iteration; there is no join, motor-command lock, or immediate pre-command cancellation check. Shutdown can close camera/motor and finalize logging while the current worker iteration is still using them; the worker also calls `motor.stop()` independently. This can create resource-use-after-close errors and make shutdown reporting/log completeness nondeterministic. A command already past the driver's initial hardware check can race device closure. Evidence: `yol_takip.py:172–216, 253–258, 369–403, 456–457, 494–495`; `motor.py:90–121, 166–176`.

**Fix:** Immediately disable actuation via a synchronized/latched stop gate, request cancellation, then join the worker before closing its camera/log resources. Motor command/close operations need an appropriate synchronization boundary. Keep the watchdog independent as in F25.

**Verification:** Pause a fake worker immediately before set_speed, inside capture, and before logger.update; invoke shutdown at each barrier. Assert no post-stop actuation, no operations on closed resources, and exactly-once finalization after worker completion.

#### LEGACY-090 — A single MJPEG connection monopolizes the non-threaded debug server

**Location:** [yol_takip.py:335–353](https://github.com/egdmte/startech/blob/master/LEGACY/yol_takip.py)  
**Status:** Confirmed. 

**Trigger / effect:** Open the debug page; its image establishes the infinite `/stream` response.

**What is wrong:** `make_server(...)` is created without `threaded=True`, so request handling is single-threaded. The ongoing stream occupies the handler and `/api/status` polling or another client cannot be served until the stream closes. `server.timeout=0.5` only bounds accepting a request, not completion of a streaming response. A stalled client can also complicate orderly server exit. Evidence: `yol_takip.py:335–353, 355–361, 470–477`.

**Fix:** Use a threaded WSGI server or an appropriate concurrent streaming server, with bounded client handling and explicit shutdown.

**Verification:** Against a test-only local fake app, keep one streaming response open while issuing `/api/status`; status must complete promptly and server shutdown must complete within its defined timeout. No vehicle or camera should be part of that test.

## 4. Verification and limits

- All 19 Python files compiled statically without running them. A compilation pass does not establish correct control behavior.
- Parent review reproduced state transitions, obstacle fall-through, hazard omissions, approach/bump timers, repeated-event handling, parking reversal/completion, camera reuse/readiness, stop-request ordering, clock changes, keyboard buffering, and several detector failures using fake collaborators or synthetic arrays.
- Independent control review exercised controller histories and fake GPIO allocation/output/cleanup failures. Independent perception review exercised lane/event/sign helpers with synthetic images and checked the model structure. Calibration/tuning review used scoped source inspection and safe fixtures.
- The model parses as 192 vectors × 128 features with six classes and valid labels/finite values; no zero vectors, identical cross-class vectors, or self-nearest class inconsistencies were found. These are structural checks, not field accuracy validation.
- Existing safeguards were not misreported as missing: absent GPIO/conventional mock factories are rejected, main frame exceptions attempt braking, the controller returns zero before its first lane observation and eventually stops on sustained reported loss, motor direction changes lower PWM first, and several entrypoints have cleanup paths. The findings describe remaining gaps or specific failure conditions.
- Scoped documentation was searched for deployment, no-touch, arming, mock and safety assertions. The in-scope competition PDF supplied the startup, crossing, dead-end right-turn and full-vehicle parking requirements (pages 15–17). Historical performance claims were not treated as test evidence.
- No outside repository files, outside tests, deployment state, physical vehicle, original sign-training images, camera calibration measurements, or mechanical parameters were inspected. This was a source audit, not vehicle safety certification.
- Proposed fixes have not been applied. Validate changes with unit/synthetic replay tests first, then controlled hardware checks with an independent stop mechanism; do not use the uncorrected behavior as proof of safe autonomous operation.

## 5. Reviewed-source fingerprints

The Git blob SHA values below identify the exact bytes reviewed. All repository links above were returned by GitHub for the observed `master` paths; those paths may change after this review.

| Scoped file | Bytes | Git blob SHA |
|---|---:|---|
| `LEGACY/10_otonom_arac.pdf` | 1772156 | `9333f07464e9e4404717f668c9eb7b4b8c8eea2f` |
| `LEGACY/BASLA_BURADAN.txt` | 10388 | `9691da762ca5be7de014d285ebcf7699d9216969` |
| `LEGACY/calibrate.py` | 4892 | `f46c9ff2cf2a1414210ffa180bbce4fea48ca672` |
| `LEGACY/camera.py` | 4079 | `eb5100616c020fc8abe59dff5675f073df393b0e` |
| `LEGACY/camtester.py` | 7411 | `ae766cc47bc69bfe9b077f745263a97e61d9cebd` |
| `LEGACY/CLAUDE.md` | 1201 | `7ce146c15173d615b27623e034f8dd16aeb778b9` |
| `LEGACY/config.py` | 17081 | `df51afc5829920ed977d2b1d8f38da3cad4964c8` |
| `LEGACY/controller.py` | 11099 | `1809fab64c0bc039f1f3d592ae7d954bc3b0a05f` |
| `LEGACY/DEGISIKLIKLER_OZET.txt` | 21732 | `cc3332253e862d985f2aed66af2c031c6a5aa561` |
| `LEGACY/DOSYALAR_GUNCELEME_DURUSU.txt` | 4960 | `f0be2c4b3311db57405c309d2cb014be78aa0760` |
| `LEGACY/events.py` | 18281 | `bde3ee91d68dc53755cb39a514186a6581c4fcbc` |
| `LEGACY/hsv_tune.py` | 6849 | `86d5d8fe564649f3d04d4ff30bb05487a7ab7141` |
| `LEGACY/IMPLEMENTATION_SUMMARY.txt` | 10498 | `bbb454522f6f4ce6b62cf84bff9f4303f0a25868` |
| `LEGACY/import numpy as np.py` | 525 | `957b1b0c48b13774440899c7962c4f3cc9ebce07` |
| `LEGACY/kalibrasyon.py` | 20737 | `5f61b82efe4f08bfe2aa6c6b4638fb0bd5a0e523` |
| `LEGACY/lane.py` | 11595 | `b89e9a24320760cc46b61e12b3433909a32a7a39` |
| `LEGACY/logger.py` | 3979 | `f6705b0ae161988e971dec6c16f611703ac5d937` |
| `LEGACY/main.py` | 28583 | `1fb0a6ef35df15fa09c2c131bd7e1d3ea318f165` |
| `LEGACY/motor.py` | 8011 | `334bd52ed66367cbf13edd59cee91f607365e937` |
| `LEGACY/motor_balance_test.py` | 7549 | `721633f99bdd9df74b47cbf1cb76f030b3a7aa8c` |
| `LEGACY/pd_tune.py` | 9172 | `e58e269eca400c57bdac4424355e7d10de1f6fcc` |
| `LEGACY/README.md` | 110 | `5f630bd9f36acfff82541ccdc299ae1f325cf156` |
| `LEGACY/sign_model.json` | 241707 | `2d4bdd8a29fbda969a57b4da836564bac404e5e1` |
| `LEGACY/sign_test.py` | 3037 | `ea02b0bb02444f887d87fa3ff2f99be126f9571b` |
| `LEGACY/train_sign.py` | 4407 | `267895812940723b926a71cbc77e3ea7dbad00b4` |
| `LEGACY/tune.py` | 29622 | `ad434866789797f8f6842d9edb8fdf7f1fd47986` |
| `LEGACY/yol_takip.py` | 17279 | `c228227691ea1da3524530a9ef8e129fde9c1afe` |

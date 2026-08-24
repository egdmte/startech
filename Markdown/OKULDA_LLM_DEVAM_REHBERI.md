# STARTECH school workshop handoff

Last source review: 24 August 2026.

This guide describes the current code. It is not proof that the car was physically
tested. The car exists and its wiring is documented, but the team does not possess it
during the summer. Until the car is present again, hardware results stay
`PHYSICALLY UNVERIFIED`.

## The rule that prevents another dead project

There is no production “pretend car” mode.

- A feature either uses the real camera, real lane pipeline, real profile registry,
  real log path or real GPIO boundary; or it is documented as unfinished/unverified.
- Automated tests may use controlled call recorders, but those objects live under
  `tests/` and their output is never vehicle evidence.
- Recorded camera sessions contain actual captured frames. Replay is analysis of a
  recording, not a claim that a camera or car is currently connected.
- `sim/` and `arac/simulasyon.py` are explicitly Webots-only. Webots is never selected
  by ARDA and never counts as physical-car proof.

## What exists now

| Part | Current real responsibility | Physical status |
|---|---|---|
| YAREN | Selects immutable calibration/settings profiles and provides the CAM gateway | `IMPLEMENTED`; school profile values are `PHYSICALLY UNVERIFIED` |
| KASIM | Opens a Windows/Linux OpenCV USB camera, with Picamera2 fallback on the Pi | `IMPLEMENTED`; mounting/Pi camera is `PHYSICALLY UNVERIFIED` |
| KEREM | Runs lane detection on actual RGB frames using the active calibration | `IMPLEMENTED`; school scene is `PHYSICALLY UNVERIFIED` |
| DORA | Maintains vehicle state transitions | `IMPLEMENTED`; state does not prove motion |
| KADER | Writes structured run/workshop records | `IMPLEMENTED`; Pi storage durability is `PHYSICALLY UNVERIFIED` |
| TAWNT | Validates phases, arming, values, watchdogs and every motor request | `IMPLEMENTED`; cannot observe physical motion |
| OSMAN | Writes the existing car's L298N channels through gpiozero | `IMPLEMENTED` from LEGACY wiring; physical output is `PHYSICALLY UNVERIFIED` |
| ARDA | Offers observation, autonomous driving, bounded workshop output and YAREN/CAM access | Real execution paths are `IMPLEMENTED`; driving is `PHYSICALLY UNVERIFIED` |
| CAM/SAC | Runs real linked-car camera/lane checks and one bounded workshop command | `IMPLEMENTED`; physical result needs a separate human observation |

## Existing vehicle wiring

`arac/surucu.py` records the current car boundary as BCM pins:

- right direction: 17 and 27;
- left direction: 22 and 23;
- left/right PWM: 12 and 13 at 100 Hz;
- physical start button: 16;
- direction output is inverted to match the existing L298N wiring.

Do not change these values because a different tutorial uses different pins. A wiring
change needs inspection of the actual car and a new recorded reason.

## Normal software verification

From the repository root:

```powershell
py -m pytest -q tests
node --check startech_cam/static/cam.js
py kontrol.py
```

These commands prove only the checked software behavior. They do not arm GPIO, prove
wheel direction, prove braking or say that the car is safe to put on the floor.

## Real camera work without the car

The laptop can still do useful real work with a USB camera:

```powershell
py -m arac.main --observe --operator "Legal Name"
```

ARDA opens a physical USB camera first, processes new frames with KEREM and shows lane
observations. A saved session can also be captured/replayed through the ARDA menu. Write
down the source, resolution, date and scene. Do not turn one successful indoor frame
into a claim about the school track.

## CAM/SAC linked workshop path

Open ARDA's YAREN gateway:

```powershell
py -m arac.main --yaren
```

The signed, temporary link exposes only four operations:

1. read the active configuration;
2. run a real camera and active lane-detector report;
3. install a validated configuration as inactive;
4. run one bounded SAC workshop motor command.

The motor form requires the operator's CAM-session legal name, CAM server time, an
unexpired job, the complete physical checklist and a seven-second browser countdown.
`Start now` may skip the remaining countdown; `Cancel` sends nothing.

The server bounds each side to ±35% and duration to 0.05–3 seconds. YAREN revalidates
the values and runs the same ARDA → TAWNT → OSMAN GPIO executor used by the local bench
command. The link cannot open a shell, activate a profile or start continuous/autonomous
driving.

A returned receipt means the software accepted the request, reached the selected driver
and requested a stop. It does **not** mean a wheel physically moved or stopped. SAC asks
the supervising human to record the physical observation separately.

## First day with the car back

Do not improvise the order.

1. Pull the reviewed commit and confirm the working tree contains no mystery edits.
2. Inspect the physical wiring against `LEGACY_VEHICLE_WIRING`.
3. Raise/secure all wheels, clear the path and identify a physical power disconnect.
4. Review/select the intended YAREN profile while motor power is off.
5. Run the full software suite and record its exact result.
6. With motor power still off, run real camera acquisition and KEREM lane observation.
7. Use SAC or local `--bench` for the smallest useful output and duration. One supervisor
   watches the car; another controls power.
8. Record actual left/right direction, whether stop occurred, supply state and anomalies.
9. Correct wiring/calibration from evidence. Do not compensate for unknown hardware with
   a guessed software sign flip.
10. Only after bounded output is understood, request separate explicit authorization for
    autonomous `--drive` on a cleared path.

Example local workshop command (do not run without the car-side checklist and explicit
authorization):

```powershell
py -m arac.main --bench --operator "Legal Name" --confirm-output --left 0.10 --right 0.10 --seconds 0.10
```

## Autonomous drive boundary

`py -m arac.main --drive` is a real vehicle path. It opens the active profile, live
camera, KEREM controller, TAWNT LIVE phase, start control and real GPIO driver. It stops
on lane loss, camera failure, watchdog expiry, interruption or loop shutdown.

Its existence is not permission to run it. Code-change approval and live-hardware
authorization are separate events. When the car returns, the authorization must name
the operator, location, car state and intended run.

## Evidence vocabulary

Use these phrases literally:

- `IMPLEMENTED`: a real code path exists and its stated contract is checked.
- `PHYSICALLY UNVERIFIED`: implementation exists but the needed car-side observation has
  not happened.
- `PHYSICALLY VERIFIED`: dated physical evidence demonstrates the exact stated behavior.
- `NOT IMPLEMENTED`: there is no real path yet; document the missing dependency instead
  of constructing a result.
- `VALIDATED`: TAWNT accepted one specific command, profile, value, or relationship.

Never convert a test result, `VALIDATED` command, receipt, or stop request into physical
movement or braking evidence.

## What to read beside the car

- `PROJECT_MAP.md` for current paths.
- `arac/main.py` for ARDA modes and stop handling.
- `arac/atolye.py` for bounded workshop limits/receipts.
- `arac/surucu.py` for wiring and the physical motor boundary.
- `arac/goz.py` and `arac/goruntu.py` for camera/lane behavior.
- `TAWNT.md` for the safety contract.
- `Markdown/HATA_DEFTERI.md` for historical failures, not current capability claims.

`PLAN.md` is the current state and roadmap. Retired plans remain only in Git history and
the retained PDFs are historical snapshots. Prefer current source when any document
contradicts implemented behavior.

# TAWNT — current validation and motion-boundary guide

Source review: 24 August 2026.

TAWNT makes the car's critical declarations and motion gates readable. The public API is
root `tawnt.py`; the implementation is split by responsibility under `startech/tawnt/`.

The most important boundary is simple:

> TAWNT can validate a declared value, profile, phase, heartbeat, fault state, or motor
> command. It cannot measure the car, write GPIO, or prove that a wheel moved or stopped.

## Where TAWNT sits

```text
KEREM lane observation
        |
        v
ARDA lane controller -> MotorRequest
        |
        v
arac.surucu.validate_request
        |
        v
tawnt.validateMotorCommand -> immutable ValidatedMotorCommand
        |
        v
OSMAN applies calibration -> TAWNT validates the final pair again -> GPIO
```

OSMAN accepts only `ValidatedDriveRequest`, which pairs the original `MotorRequest` with
the exact immutable `ValidatedMotorCommand` returned by TAWNT. This keeps ordinary car
code from passing an unchecked tuple directly to the physical driver.

## Why the calls are useful

The live lane start reads almost like a checklist:

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

That establishes only software facts known to TAWNT:

- the named heartbeats were recently updated;
- the requested profile passed the declared start checks;
- the requested phase exists and its phase rules passed;
- no persistent fault prevents arming;
- the caller supplied the required live-output declarations.

It does not establish:

- that the legal name or authorization declaration is truthful;
- that the camera is mounted or calibrated correctly;
- that a value marked measured was actually measured;
- that wiring, motor direction, trim, power, traction, or braking is correct;
- that the physical car is safe to place on the floor.

## Runtime profiles

TAWNT exposes three profiles:

| Profile | Purpose |
|---|---|
| `OFFLINE` | Non-motion declaration work that does not arm real output |
| `BENCH` | Explicit bounded workshop motion |
| `LIVE` | Autonomous physical vehicle motion |

`LIVE` requires a configured persistent fault store. Arming it also requires the caller
to provide the live-hardware authorization and final-confirmation declarations. These
arguments keep the decision visible at the call site; TAWNT cannot verify the humans or
physical setup behind them.

## Runtime states

| State | Meaning inside TAWNT |
|---|---|
| `BOOT` | Definitions/start checks have not completed |
| `VALIDATING` | Startup validation is in progress |
| `READY_UNARMED` | Declared startup conditions passed; motion remains disabled |
| `ARMED` | The selected profile and phase may accept motion commands |
| `MUTED` | Motion is disabled without a persistent severe fault |
| `LATCHED_FAULT` | A persistent severe fault blocks motion until an explicit reset |

These are TAWNT software states. DORA owns vehicle behavior states, and KADER records the
run timeline. Do not use a TAWNT state as physical evidence.

## Value provenance

Critical values can be defined with bounds, unit, source, and profile requirements:

```python
tawnt.defineValue(
    "maximum_pwm",
    min=0.0,
    max=1.0,
    critical=True,
)
tawnt.recordValue(
    "maximum_pwm",
    0.35,
    source=tawnt.OLCULDU,
    human="Legal Name",
    date="2026-08-24T12:00:00Z",
    note="example record only",
)
```

`OLCULDU` is a provenance declaration. It means the caller says the value was measured;
TAWNT did not operate a multimeter. Current physical evidence still needs its independent
record.

The value lifecycle is:

| State | Meaning |
|---|---|
| `DEFINED` | Contract exists; no value recorded |
| `RECORDED` | A value and provenance were supplied |
| `VALIDATED` | The current value passed its declared checks |
| `STALE` | A dependency changed after validation |
| `SEALED` | The validated runtime declarations are immutable for the run |

Dependencies declared with `dependsOn` invalidate dependent values when a source value
changes. `requireMeasured` can require measurement provenance for selected profiles.
`validateBeforeStart` gathers errors and leaves motion disabled on failure.

The older `introduce`, `acquire`, and `preacquire` call names remain compatibility
wrappers for existing callers. New current documentation uses the explicit APIs when
that improves clarity.

## Phases

A phase defines the motion envelope for one behavior:

```python
tawnt.definePhase(
    "LANE_FOLLOW",
    motion_allowed=True,
    allow_reverse=False,
    allow_pivot=False,
    max_pwm=0.35,
    max_difference=0.25,
    required_watchdogs=("camera", "control"),
)
```

`enterPhase` selects a defined phase after startup validation. `validateMotorCommand`
checks the active profile, system state, phase, finite normalized values, direction/pivot
policy, magnitude/difference limits, and required watchdog freshness.

Its successful result is an immutable `ValidatedMotorCommand` containing the exact left,
right, phase, profile, and timestamp accepted by TAWNT.

## Watchdogs

TAWNT watchdogs make camera and control freshness part of command validation:

```python
tawnt.defineWatchdog("camera", timeout_seconds=0.5)
tawnt.defineWatchdog("control", timeout_seconds=0.5)

tawnt.heartbeat("camera")
tawnt.heartbeat("control")
tawnt.checkWatchdogs(("camera", "control"))
```

If code never returns from a blocking operation, it may not reach
`checkWatchdogs`. ARDA therefore also owns an independent `OutputWatchdog` thread that
requests OSMAN stop when the loop stops touching it. These layers complement each other.

Neither layer proves that the physical stop occurred.

## Faults and zero-output callbacks

The current live path configures a persistent fault store and registers an OSMAN stop
callback:

```python
tawnt.sifirla()
tawnt.onShutdown(lambda: driver.stop("TAWNT zero callback"))
tawnt.configureFaultStore(log_dir / "tawnt-fault.json")
```

`latchFault` records a severe fault, requests all registered zero-output callbacks, and
persists enough state to block an unsafe restart. `flushPWM` asks the callbacks for zero
without claiming physical braking. `disarm` disables motion at normal end.

A persistent fault reset requires a human name and the declaration that motor power is
off. Those are explicit audit inputs, not sensor observations.

SIGINT/Ctrl+C is an immediate stop instruction. ARDA requests driver stop before writing
the interruption record and returns an interrupted exit status. The LLM or operator must
not resume automatically after the interrupt.

## Static motor-write scan

`scanDirectMotorWrites` inspects current Python source for suspicious direct motor access
outside approved boundaries. It is a code-structure check, not a runtime sandbox. A new
physical output path must still be designed through TAWNT and OSMAN, not merely hidden
from the scan.

## Current public API by responsibility

Values and provenance:

- `defineValue`, `recordValue`, `dependsOn`, `requireMeasured`
- `validateBeforeStart`, `seal`, `valueState`
- compatibility: `introduce`, `acquire`, `preacquire`, `deger`

Motion and phase:

- `definePhase`, `enterPhase`, `validatePhase`
- `arm`, `disarm`, `systemState`, `isMotionAllowed`
- `validateMotorCommand`

Freshness:

- `defineWatchdog`, `heartbeat`, `checkWatchdogs`

Fault handling:

- `configureFaultStore`, `onShutdown`, `flushPWM`
- `latchFault`, `resetFault`, `kilitDurumu`

Maintenance and inspection:

- `sifirla`, `report`, `scanDirectMotorWrites`

Use root `tawnt.py` as the stable import surface:

```python
import tawnt
```

Do not import internal `startech.tawnt` modules from ordinary vehicle code unless the
task is maintaining TAWNT itself.

## Testing boundary

The TAWNT suite checks bounds, provenance, dependency staleness, phases, arming,
watchdogs, faults, persistence, reset declarations, static scanning, and integration
with `arac/surucu.py`, `arac/atolye.py`, and ARDA.

Tests may provide controlled drivers and clocks. Those fixtures establish which calls
the software made. They are not alternate car drivers and cannot establish wheel
movement, direction, motor power, or stopping.

Run the focused checks with:

```powershell
py -m pytest -q tests/test_tawnt.py tests/test_surucu.py tests/test_atolye.py tests/test_arac_main.py
```

Then run the repository's full verification set from `PLAN.md` before committing a
change that affects the vehicle chain.

## Practical interpretation

If TAWNT rejects a request, OSMAN must not receive it. Fix the violated declaration or
the caller; do not bypass TAWNT.

If TAWNT accepts a request, the precise statement is:

> TAWNT `VALIDATED` this command under the current software profile, phase, fault state,
> limits, and watchdog information.

The next questions remain physical: did OSMAN reach the intended GPIO, did the correct
motors move in the correct direction, and did the car physically stop? Answer those with
bounded car-side observation, not another green status label.

# TAWNT

TAWNT is the retained validation library exposed by root `tawnt.py` and implemented in
`startech/tawnt/`.

Its useful promise is narrow: TAWNT can reject a declared value or motor command that
violates configured bounds, phase rules, fault state, or watchdog freshness. It cannot
measure the car, write GPIO, or prove that a wheel moved or stopped.

The competition vehicle code under `LEGACY/` does not currently import TAWNT. Any future
integration must remain obvious at the existing motor boundary and make the runtime
easier to understand. Do not rebuild the deleted chain of modules around it.

Typical calls remain readable:

```python
tawnt.heartbeat("camera")
tawnt.heartbeat("control")
tawnt.validateBeforeStart(profile=tawnt.LIVE)
tawnt.enterPhase("LANE_FOLLOW")
```

TAWNT also exposes value/provenance checks, phases, watchdogs, persistent faults,
zero-output callbacks, and immutable validated commands. Inspect `tawnt.py` for the
stable public surface and `tests/test_tawnt.py` for checked behavior.

If TAWNT later accepts a command, the accurate claim is only that the command passed
TAWNT's current software declarations. Physical movement, direction, and stopping still
require observation on the car.

Run its focused suite with:

```powershell
py -m pytest -q tests/test_tawnt.py
```

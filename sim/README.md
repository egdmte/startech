# STARTECH Webots visual simulation

This folder contains a visual, finite demonstration of the simulated motor
boundary. It does not control or model the physical STARTECH car accurately.

## What it demonstrates

The controller creates normalized motor requests, passes them through the
existing TAWNT offline validation gate, records accepted requests through
the Webots-only command recorder, and sends the resulting wheel velocities to Webots'
wheel devices.

The demo performs these finite segments:

1. Move forward from the start line.
2. Show a left arc.
3. Continue straight.
4. Show a right arc.
5. Approach the finish line and request stop.

The simple pose calculation in `arac/simulasyon.py` is for deterministic tests
and diagnostics. Webots uses its own physics engine for the visible vehicle, so
the two paths may not match exactly.

## Run visually

Open `sim/worlds/startech.wbt` in Webots and press the Run button. The controller
stops all four simulated wheel devices when its finite sequence ends.

From PowerShell, Webots can also be opened with:

```powershell
& 'C:\Program Files\Webots\msys64\mingw64\bin\webots.exe' sim/worlds/startech.wbt
```

The controller-local `runtime.ini` selects `py` on Windows and `python3` on
Linux/macOS. This avoids Windows' Microsoft Store `python` alias without
changing global Webots preferences.

## Automated smoke check

The controller recognizes `STARTECH_WEBOTS_AUTOCLOSE=1`, which closes Webots
after the finite sequence. The agent may use it with batch and fast modes:

```powershell
$env:STARTECH_WEBOTS_AUTOCLOSE = '1'
& 'C:\Program Files\Webots\msys64\mingw64\bin\webots.exe' --batch --mode=fast --no-rendering --stdout --stderr sim/worlds/startech.wbt
Remove-Item Env:STARTECH_WEBOTS_AUTOCLOSE
```

A successful controller prints a line beginning with `STARTECH_WEBOTS_OK`.
The automated sequence currently contains five requested motion segments and
one explicit stop event.

## Unit tests

The hardware-independent bridge tests run without Webots:

```powershell
py -3.13 -m unittest tests.test_simulasyon -v
```

These tests verify request validation, speed mapping, straight motion, turning,
stop behavior and rejected invalid time/geometry.

## Safety boundary

- No GPIO or PWM library is imported.
- No physical motor adapter is selected.
- Raw `MotorRequest` objects are rejected by the visual bridge.
- TAWNT validation remains required.
- Webots motor devices exist only inside the simulation world.
- A successful visual run is not evidence about real motor direction, speed,
  braking, traction, battery behavior or stopping distance.

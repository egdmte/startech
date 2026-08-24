# STARTECH repository context

Source review: 24 August 2026.

Read `AGENTS_READ_ME.txt` before editing. That file and the main plan are pending a
separate Q&A-led rewrite; do not silently rewrite their policy or project choices.

## Current project

The physical autonomous car exists, and `LEGACY/` documents the wiring/older working
behavior. The team does not possess the car during the summer. “No car now” means no
current possession, not that the hardware is imaginary.

The current application under `arac/` has real paths for:

- YAREN immutable calibration/settings profiles and the CAM gateway;
- KASIM USB/Picamera2 RGB acquisition;
- KEREM lane detection on captured frames;
- DORA state transitions and KADER records;
- TAWNT validation, arming, phase and watchdog boundaries;
- OSMAN output through the existing Raspberry Pi/gpiozero wiring;
- ARDA live observation, autonomous driving and bounded workshop output;
- CAM/SAC real linked-car camera/lane checks and bounded workshop commands.

There is no production pretend-car mode. Features are real or explicitly documented as
unfinished/physically unverified. Controlled call recorders may exist only in tests and
are never evidence that the vehicle moved. `sim/` and `arac/simulasyon.py` are the sole,
explicit Webots exception and cannot be selected by ARDA.

Windows uses a real OpenCV USB camera for capture, recording/replay, calibration and lane
analysis. Physical motor output is Raspberry Pi/gpiozero-only.

## Working rules

- Be conversational and explain behavior in terms of what part helps the car do.
- Preserve unrelated changes already in the working tree.
- Do not write for a teammate-owned part without asking.
- Do not add sensors; this vehicle is camera-only.
- Give every change a concrete reason. Reject decorative or unexplained changes.
- Never invent a file, API, metric or physical result. A number described as measured
  needs the dated real-run evidence that produced it.
- Software tests prove software behavior only. A driver receipt proves a call/stop request,
  not wheel movement or braking.
- Code-change approval is not live-hardware authorization. A real run needs separate,
  explicit car-side approval and the physical checklist.
- Any GPIO/PWM path starts/stops at zero, validates through TAWNT and stops on failure.
- First motor work is bounded, wheels raised/secured, path clear, human supervised and
  within reach of physical power removal.

## Where to look

- `PROJECT_MAP.md`: current code paths.
- `Markdown/OKULDA_LLM_DEVAM_REHBERI.md`: current school workshop handoff.
- `Markdown/HATA_DEFTERI.md`: historical failures; not a current capability list.
- `TAWNT.md`: safety API and evidence boundary.
- `Markdown/YAPILANDIRMA_SOZLESMESI.md`: configuration/CAM contract.
- `LEGACY/`: read-only historical implementation reference.

Use `py -m pytest -q tests` for the current Python suite. Run `py kontrol.py` separately;
its documentation result is not interchangeable with the unit-test result.

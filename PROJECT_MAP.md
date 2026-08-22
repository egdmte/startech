# STARTECH project map

Use this page when the repository starts feeling larger than the car.

## Start here

1. Read `AGENTS_READ_ME.txt` before changing anything.
2. Run `git status --short` and preserve changes that are already present.
3. Choose one area from the table below. Do not follow similarly named files into
   unrelated folders.
4. Read the production file and its matching test together.
5. For work beside the physical car, also read
   `Markdown/OKULDA_LLM_DEVAM_REHBERI.md`.

## The repository in one table

| Path | What it is | Use it when |
|---|---|---|
| `arac/` | Current autonomous-car application contracts | Working on camera, vision, state, logs, orchestration or motor requests |
| `sim/` | Webots-only visual car driven through TAWNT and `FakeMotorDriver` | Watching or testing fake motor behavior without the physical car |
| `tests/` | Automated proof for the current Python behavior | Changing anything in `arac/`, TAWNT, configuration or project checks |
| `startech/` | Shared implementation packages used by public entry points | Maintaining TAWNT internals, configuration validation or document checks |
| `config/` | Versioned JSON schemas and examples | Working on calibration/configuration file structure |
| `examples/prototypes/` | Experimental calibration website screens | Continuing the Figma-to-web calibration tool |
| `examples/tawnt_demo/` | Small, fake TAWNT demonstrations | Learning or testing the safety API without the car |
| `Markdown/` | Detailed plans, evidence and school handoff documents | Understanding decisions or preparing a supervised school session |
| `subiru/` | Separate team task/evidence dashboard | Working specifically on ŞUBİRU project tracking |
| `LEGACY/` | Historical code kept for reference | Comparing old behavior only; do not import it into current code |

## Current car path

```text
arac/main.py       ARDA / ADAM    command-line entry and orchestration
    |
    +-- arac/goz.py        KASIM / CAMILA   camera acquisition
    +-- arac/goruntu.py    KEREM / CORA     cautious vision observations
    +-- arac/durum.py      DORA / SARA      state transitions
    +-- arac/kayit.py      KADER / BLAIR    black-box software records
    +-- arac/surucu.py     OSMAN / MATT     only planned motor-output boundary
    +-- arac/simulasyon.py                 fake differential-drive bridge
```

TAWNT keeps every accepted motion request behind a validation gate:

```text
MotorRequest -> tawnt.py -> ValidatedDriveRequest -> MotorDriver
```

- Root `tawnt.py` is the public TAWNT entry point.
- `startech/tawnt/` contains its implementation pieces.
- `FakeMotorDriver` records requests only.
- `BlockedMotorDriver` refuses physical output.
- A log entry or requested stop is not proof that a real wheel moved or stopped.

## Camera state

KASIM currently tries an OpenCV USB camera first and Picamera2 second. Both failing
raises an explicit error. A read failure after one source has opened does not silently
switch cameras.

The laptop USB camera has completed a finite three-frame acquisition check. The
Raspberry Pi camera and its mounting remain physically unverified.

```powershell
py -3.13 -m arac.main --auto --check-camera --camera-frames 3 --language en --no-color
```

## Visual motor simulation

Open `sim/worlds/startech.wbt` in Webots and press Run. The finite controller sends
five TAWNT-validated requests through `FakeMotorDriver`, moves four simulated wheels,
then requests zero output. See `sim/README.md` for the automated smoke check.

The Webots result is a visualization, not a calibration of real motors, batteries,
traction, braking or stopping distance.

## Which document answers which question?

| Question | Read |
|---|---|
| What must an agent do before editing? | `AGENTS_READ_ME.txt` |
| What order should the project work follow? | `SIRA.md` |
| What is the complete phase-gated roadmap? | `ROADMAP.md` |
| How should work continue at school? | `Markdown/OKULDA_LLM_DEVAM_REHBERI.md` |
| What is the detailed historical plan? | `Markdown/PLAN_New.md` |
| What failed before and what evidence exists? | `Markdown/HATA_DEFTERI.md` |
| How do calibration JSON files work? | `Markdown/YAPILANDIRMA_SOZLESMESI.md` |
| How does TAWNT work? | `TAWNT.md` |

Plans describe intent; tests and current source describe implemented behavior. If they
disagree, report the difference instead of silently rewriting either side.

## Normal verification

```powershell
py -3.13 -m unittest discover -s tests -v
py -3.13 -m compileall -q arac tests
py -3.13 kontrol.py
```

`kontrol.py` checks documentation claims separately from the unit tests. A failure in
one command must not be described as success in another.

## Things to ignore during ordinary car work

- Generated PDFs unless the task is specifically about document export.
- Web prototypes while changing Python vehicle behavior.
- `subiru/` unless the task concerns the team dashboard.
- `LEGACY/` unless the task explicitly asks for historical comparison.
- Untracked files whose ownership or purpose has not been confirmed.

The safest way through this project is one path, one contract and one test at a time.

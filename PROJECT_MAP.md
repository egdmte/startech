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
| `arac/` | Current autonomous-car application contracts | Working on camera, configuration, vision, state, logs, orchestration or motor requests |
| `sim/` | Explicitly Webots-only visual car driven through TAWNT | Inspecting the Webots world; its output is never car evidence |
| `tests/` | Automated proof for the current Python behavior | Changing anything in `arac/`, TAWNT, configuration or project checks |
| `startech/` | Shared implementation packages used by public entry points | Maintaining TAWNT internals, configuration validation or document checks |
| `config/` | Versioned JSON schemas and examples | Working on calibration/configuration file structure |
| `startech_cam/` | Production CAM web application, device link API and SAC/MAC UI | Working on browser authentication, calibration creation or YAREN communication |
| `examples/prototypes/` | Historical design references for the production CAM UI | Comparing the implemented interface with the approved Figma-derived screens |
| `Markdown/` | Detailed plans, evidence and school handoff documents | Understanding decisions or preparing a supervised school session |
| `subiru/` | Separate team task/evidence dashboard | Working specifically on ŞUBİRU project tracking |
| `LEGACY/` | Historical code kept for reference | Comparing old behavior only; do not import it into current code |

## Current car path

```text
arac/main.py       ARDA / ADAM    command-line entry and orchestration
    |
    +-- arac/ayar.py       YAREN / CLARA   fail-closed active profile loader
    +-- arac/ayar_cli.py   YAREN / CLARA   calibration/settings registry menu
    +-- arac/yaren_web.py                  signed device identity and web-code bootstrap
    +-- arac/yaren_link.py                 temporary outbound closed-operation link
    +-- arac/yaren_diagnostics.py          real camera/lane capability probes
    +-- arac/atolye.py                     shared bounded physical workshop execution
    +-- arac/goz.py        KASIM / CAMILA   camera acquisition
    +-- arac/kamera_oturumu.py             finite record/replay sessions
    +-- arac/goruntu.py    KEREM / CORA     cautious vision observations
    +-- arac/durum.py      DORA / SARA      state transitions
    +-- arac/kayit.py      KADER / BLAIR    black-box software records
    +-- arac/surucu.py     OSMAN / MATT     real GPIO motor-output boundary
    +-- arac/simulasyon.py                 explicitly Webots-only bridge
    +-- arac/cli_ui.py                     shared dependency-free terminal widgets
```

## Calibration and settings registry

YAREN joins, versions and selects existing v1 calibration/settings pairs without
changing their schemas:

```text
kalibrasyon.json + ayarlar.json
             |
             v
startech/configuration/profiles.py
             |
             +-- profil.json + full SHA-256 values
             +-- selection history and archive
             +-- arac/ayar.py (read-only runtime snapshot)
             +-- arac/ayar_cli.py (human/automation interface)
```

Profiles live outside the repository by default. Open the guided menu directly or
through ARDA:

```powershell
py -3.13 -m arac.ayar_cli
py -3.13 -m arac.main --auto --configuration --language en
```

Installing, validating or selecting a profile never arms TAWNT or a motor driver and
never grants a "safe to drive" state. See `Markdown/YAPILANDIRMA_SOZLESMESI.md` for
the registry layout, warning review and settings-revision rules.

## Temporary CAM connection

YAREN action 10 requests a random, one-use eight-character code from CAM using its
registered Ed25519 device identity. Entering that code in the browser binds the
browser session to the same temporary outbound device link. The code is not a fixed
password, and CAM does not accept an anonymous request to mint one.

```text
YAREN --signed request--> CAM --random one-use code--> operator
   |                                                |
   +-- outbound bearer link <--- browser consumes --+
              |
              +-- active configuration snapshot
              +-- physical camera + real lane-analysis report
              +-- validated inactive profile import
              +-- one short, explicit SAC workshop motor command
```

The link has a closed operation list: `REQUEST_ACTIVE_CONFIGURATION`,
`REQUEST_CAPABILITY_REPORT`, `INSTALL_INACTIVE_CONFIGURATION` and
`RUN_BOUNDED_WORKSHOP_COMMAND`. The last operation is available only from an
authenticated SAC session, carries CAM's legal-name/time record, expires in seconds and
is limited to ±35% for at most three seconds. It executes on the car through the same
ARDA → TAWNT → OSMAN path as the local bench command. It is not continuous remote
control and cannot start autonomous driving or activate a profile. Imported combined v2
files remain immutable inactive profiles for human review. Logout, expiry, YAREN shutdown
or Ctrl+C revokes the link.

The CAM capability report opens the physical camera twice: once for acquisition metadata
and once for KEREM to run the active lane detector. OSMAN is not moved by automatic
diagnostics; physical output requires the separate, explicit workshop form and countdown.
Its software receipt records requested/applied values and a stop request. Only a separate
human observation can record that a wheel physically moved as expected.

TAWNT keeps every accepted motion request behind a validation gate:

```text
MotorRequest -> tawnt.py -> ValidatedDriveRequest -> MotorDriver
```

- Root `tawnt.py` is the public TAWNT entry point.
- `startech/tawnt/` contains its implementation pieces.
- `GpioZeroMotorDriver` is the only production motor-driver implementation.
- Controlled call recorders live only in tests and are never accepted as vehicle evidence.
- The Webots bridge is isolated under `arac/simulasyon.py` and cannot be selected by ARDA.
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

## Recorded camera sessions

ARDA can store a finite USB-first/Pi-second camera session as numbered JPEG frames
plus a strict `manifest.json`. It refuses to overwrite an existing directory. The
completed manifest is written last; an interrupted capture instead leaves
`incomplete.json`, which replay rejects.

The numbered ARDA workbench works on Windows, Linux and Raspberry Pi without an extra
UI package. It includes camera utilities and the YAREN configuration menu:

```powershell
py -3.13 -m arac.main --interactive --language en
```

The same operations remain scriptable. Keep large recordings outside the Git working
tree unless US explicitly decides to version a small fixed test clip:

```powershell
py -3.13 -m arac.main --auto --record-camera ../startech-recordings/school-01 --record-frames 300 --language en
py -3.13 -m arac.main --auto --replay-camera ../startech-recordings/school-01 --language en
```

Replay verifies the manifest, frame order, dimensions and SHA-256 value of every image,
then decodes the complete session through the KASIM camera interface. It does not yet
mean that KEREM can recognize lanes or tasks in those images. A recording is camera
evidence, not proof that the car moved, steered or stopped.

## Visual motor simulation

Open `sim/worlds/startech.wbt` in Webots and press Run. The finite controller sends
five TAWNT-validated requests through its Webots-specific command bridge, moves four
Webots wheel devices, then requests zero output. See `sim/README.md` for the smoke check.

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
- Historical web prototypes while changing production behavior; production CAM lives
  under `startech_cam/`.
- `subiru/` unless the task concerns the team dashboard.
- `LEGACY/` unless the task explicitly asks for historical comparison.
- Untracked files whose ownership or purpose has not been confirmed.

The safest way through this project is one path, one contract and one test at a time.

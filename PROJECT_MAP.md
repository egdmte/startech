# STARTECH project map

Source review: 24 August 2026.

Use this page to find the current implementation. Read `AGENTS_READ_ME.txt` before
editing and `PLAN.md` for status and future direction.

## Repository areas

| Path | Current purpose |
|---|---|
| `arac/` | Real vehicle application: configuration, camera, perception, state, logging, workshop execution, orchestration, and GPIO boundary |
| `startech/tawnt/` | TAWNT implementation behind the public root `tawnt.py` API |
| `startech/configuration/` | Configuration validation, immutable profiles, and combined-document conversion |
| `startech/project_control/` | Checks that current governing documents still agree with the repository |
| `startech_cam/` | Production CAM application, SAC/MAC workflows, signed YAREN link, and bounded workshop UI |
| `config/` | Current schemas and visibly inactive example configuration documents |
| `tests/` | Software contract and regression checks; fixtures here are not vehicle evidence |
| `sim/` | Isolated Webots visual environment; never physical-car evidence |
| `Markdown/` | Current detailed contracts/handoffs plus explicitly historical records |
| `examples/prototypes/` | Historical CAM design references, not production behavior |
| `LEGACY/` | Previous moving-car implementation and rule snapshot; migration/history reference only |

## Real vehicle chain

```text
arac/main.py             ARDA operator surface and orchestration
    |
    +-- arac/ayar.py              YAREN-selected immutable runtime profile
    +-- arac/ayar_cli.py          YAREN profile registry and CAM gateway menu
    +-- arac/goz.py               KASIM physical USB/Picamera2 acquisition
    +-- arac/kamera_oturumu.py    finite real-camera record/replay
    +-- arac/goruntu.py           KEREM lane perception
    +-- arac/durum.py             DORA state transitions
    +-- arac/kayit.py             KADER ordered memory/JSONL evidence
    +-- root tawnt.py             TAWNT public validation API
    +-- arac/surucu.py            controller, watchdog, OSMAN GPIO boundary
    +-- arac/atolye.py            shared bounded physical workshop executor
    +-- arac/yaren_web.py         signed CAM device identity/code request
    +-- arac/yaren_link.py        closed temporary CAM operation link
    +-- arac/yaren_diagnostics.py bounded real capability report
```

ARDA's live drive composes:

```text
YAREN profile -> KASIM frame -> KEREM observation -> lane controller
      -> TAWNT-validated request -> OSMAN gpiozero/L298N output

DORA supplies explicit state transitions.
KADER records the software timeline.
```

OSMAN is the only production motor driver. Controlled driver doubles live under
`tests/`; they cannot be selected as a real vehicle mode.

## Operator commands

Open the small ARDA menu:

```powershell
py -m arac.main --interactive
```

Inspect the exact current interface:

```powershell
py -m arac.main --help
```

The important real paths are:

```powershell
py -m arac.main --observe --operator "Legal Name"
py -m arac.main --drive --operator "Legal Name" --confirm-output
py -m arac.main --bench --operator "Legal Name" --confirm-output --left 10 --right 10 --seconds 0.25
py -m arac.main --yaren
```

`--observe` does not create OSMAN. `--drive` and `--bench` can reach physical GPIO and
must be treated as live output. Apply the legal-name, warning, seven-second cancellation,
SIGINT, and physical-power rules in `AGENTS_READ_ME.txt`.

## YAREN configuration

YAREN joins, versions, and selects the current v1 calibration/settings pair without
changing its schema:

```text
kalibrasyon.json + ayarlar.json
             |
             v
startech/configuration/profiles.py
             |
             +-- profil.json and full SHA-256 values
             +-- immutable installed/archive directories
             +-- explicit active selection and history
             +-- arac/ayar.py read-only snapshot
```

Open the registry directly:

```powershell
py -m arac.ayar_cli interactive
```

Installing, validating, or selecting a profile never arms TAWNT and never proves the
values were physically measured. See `Markdown/YAPILANDIRMA_SOZLESMESI.md`.

## CAM and SAC

YAREN requests a one-use code with a registered Ed25519 device identity. The authenticated
browser uses that code to bind to the same short-lived outbound link.

The link accepts only:

- `REQUEST_ACTIVE_CONFIGURATION`
- `REQUEST_CAPABILITY_REPORT`
- `INSTALL_INACTIVE_CONFIGURATION`
- `RUN_BOUNDED_WORKSHOP_COMMAND`

Automatic capabilities may acquire a real camera frame and run KEREM, but do not import
OSMAN. SAC's separate workshop form carries CAM's authenticated legal name and time,
requires the physical checklist, shows a seven-second cancel warning, and queues one
short bounded command through ARDA → TAWNT → OSMAN.

A receipt proves software execution and a stop request, not physical movement or braking.
The supervising human records the physical observation separately. The link cannot start
autonomous driving, activate a profile, open a shell, or become continuous remote control.

## Camera sessions

KASIM opens OpenCV USB first and Picamera2 second. If an opened source later fails to
read, it fails explicitly instead of switching sources mid-run.

ARDA camera sessions contain actual numbered JPEG frames plus a strict manifest. Replay
checks hashes, order, dimensions, and decoding. An interrupted session is marked
incomplete and rejected. Recording replay is real recorded-data analysis; it is not
current camera or movement evidence.

## Current documents

| Question | Read |
|---|---|
| How should an agent work here? | `AGENTS_READ_ME.txt` |
| What exists and what comes next? | `PLAN.md` |
| Where is a current implementation? | This file and the owning source |
| How does TAWNT work now? | `TAWNT.md` |
| How do configuration files work? | `Markdown/YAPILANDIRMA_SOZLESMESI.md` |
| How should the first car-return session proceed? | `Markdown/OKULDA_LLM_DEVAM_REHBERI.md` and `PLAN.md` |
| What failed in the earlier build? | `Markdown/HATA_DEFTERI.md` as a post-mortem |

Retired plans remain available in Git history. The retained plan PDFs are read-only
historical snapshots and must not direct current work.

## Normal verification

```powershell
py -m pytest -q tests
py -m compileall -q arac startech startech_cam tests
node --check startech_cam/static/cam.js
py kontrol.py
```

Each command proves only its own checked boundary. None of them proves that the physical
car moved or stopped.

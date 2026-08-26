# STARTECH project map

Updated: 27 August 2026.

Read `AGENTS_READ_ME.txt` for working rules and `PLAN.md` for the current state.

| Path | Purpose |
|---|---|
| `LEGACY/` | Active competition-era vehicle baseline: camera, lanes, controller, motors, events, logging, configuration, and concrete tuning tools |
| `startech_cam/` | KERİM web application: SAC, MAC, configuration records, diagnostics, access, and maintenance bundles |
| `deployment/` | KERİM VPS service, deployment, backup, proxy, and release-reference support |
| `startech/tawnt/` | TAWNT validation library implementation |
| `tawnt.py` | Stable public TAWNT import surface |
| `startech/configuration/` | Configuration validation still used by KERİM |
| `config/` | KERİM configuration schema/default material; not automatically installed into LEGACY |
| `tests/` | Retained KERİM, configuration, profile, and TAWNT software checks |
| `Markdown/` | Detailed current notes and historical/post-mortem records |

## Vehicle code

The vehicle pipeline is the readable code under `LEGACY/`. Start with:

- `LEGACY/main.py` — runtime orchestration;
- `LEGACY/camera.py` — camera acquisition/debug display;
- `LEGACY/lane.py` — lane perception;
- `LEGACY/controller.py` — steering/control calculation;
- `LEGACY/motor.py` — motor output;
- `LEGACY/events.py` — track events;
- `LEGACY/logger.py` — run records;
- `LEGACY/config.py` — values currently read by the runtime.

Other LEGACY scripts are retained because they contain calibration and bug-history
evidence. Do not delete or merge them until their concrete behavior has been inventoried.

## KERİM boundaries

KERİM is deployed from the compatibility-named `startech_cam` package. It can create,
store, inspect, and bundle configuration documents. Its release builder includes
`LEGACY/`, but automatic conversion into `LEGACY/config.py` is `NOT IMPLEMENTED`.

The former `arac/` YAREN client no longer exists. KERİM's server-side signed-link API is
retained as a compatibility surface for a possible small LEGACY adapter. It is not an
active vehicle connection after the reset.

## TAWNT boundary

TAWNT validates declared software values and commands. It does not write GPIO or prove
physical results. It is retained and tested but is not currently imported by LEGACY.

## Historical material

Old plans, PDFs, and defect records explain earlier versions. In particular,
`Markdown/HATA_DEFTERI_PAYLASIM.pdf` documents the competition behavior and defects that
guide minimal repairs. Historical text must not be treated as an instruction to restore
the deleted architecture.

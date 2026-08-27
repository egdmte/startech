# LEGACY working note

Read `../AGENTS_READ_ME.txt` before changing this directory and use `../PLAN.md` for
the current implementation state.

`LEGACY/` is the active vehicle baseline. It is not a simulation folder. The lineage
ran on the competition car, while repairs made after the car became unavailable remain
physically unverified until they are checked at SCHOOL.

Important boundaries:

- Missing GPIO must stop motor programs with an error. Never restore the old no-op
  motor fallback.
- Missing or failed camera capture must be reported. Never substitute a generated
  frame and call the capture successful.
- Keep the runtime readable: camera, lane/event detection, controller, motor, logger,
  and the state machine are enough.
- `config.py` is still the vehicle's concrete tuning source. Do not put KERİM, a
  registry, or a network service in the offline startup path.
- Historical text and PDFs in this directory explain old work and failures; they do
  not override current source, tests, `../AGENTS_READ_ME.txt`, or `../PLAN.md`.

Run software checks from the repository root with `py -m pytest -q` and
`py -m compileall -q LEGACY`. Passing them does not physically verify the car.

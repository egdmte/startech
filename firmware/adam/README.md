# ADAM vehicle warning controller

`adam.ino` is production firmware for the Arduino that drives STARTECH's local
run-warning LEDs and passive buzzer. It is not a simulator and has no success fallback.

## Current contract

- serial: 115200 baud, one UTF-8/ASCII command per line;
- handshake: `PING` → `ADAM_READY`;
- commands: `MUTE`, `UNMUTE`, `RUN_RECEIVED`, `RUN_INITIATED`,
  `RUN_HALT_NOCON`, and `OFF`;
- `RUN_RECEIVED` begins the local warning pattern;
- muting disables sound only; the LED indication remains active;
- the 30-second timing and vehicle stop decision remain in `arac/adam.py`, so a reset
  or missing Arduino cannot silently authorize ARDA.

Flash the sketch with the Arduino IDE or the team's normal Arduino toolchain, then run
the YAREN gateway with the real serial device:

```bash
python3 -m arac.ayar_cli web-code --server https://dymtal.avartech.net \
  --adam-port /dev/ttyACM0
```

The recorded pin layout is passive buzzer D2 and common-anode RGB LED D3/D5/D6. That
mapping, electrical polarity, sound level, visibility, and response beside the school
car are **PHYSICALLY UNVERIFIED**. Inspect the actual board and current-limiting hardware
before powering it. Do not infer wiring correctness from the serial handshake.

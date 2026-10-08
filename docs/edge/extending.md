# Adding new hardware

The firmware is split so that a new SoC usually only needs configuration:

```
benchapp (protocol)   ─┐
microinfer (engine)    ├─ portable C99, no heap, no FPU needed
modelzoo (data)       ─┘
hal.h  ◄── hal_arduino.cpp (all Arduino cores) │ hal_native.c (PC) │ your own HAL (e.g. Zephyr, ESP-IDF)
```

The bench firmware is in `firmware/bench`; `modelzoo` is generated build output (`edge build`,
`make`, PlatformIO pre-script).

## 1. PlatformIO environment (`firmware/bench/platformio.ini`)

```ini
[env:teensy41]
platform = teensy
board = teensy41
build_flags = ${env.build_flags} -D HIL_TARGET=\"teensy41\"
```

`HIL_TARGET` must match the target name in `hil/targets.yaml` exactly; the bench checks this
after flashing.

## 2. Target (`hil/targets.yaml`)

```yaml
teensy41:
  description: Teensy 4.1 - Cortex-M7 @ 600 MHz
  pio_env: teensy41
  flasher: platformio
  reset: soft
  usb_ids: ["16c0:0483"]
  chip_match: "."            # regex on INFO.chip
  reenumerates: true         # native USB
```

You can derive from another target with `extends: <other target>`.

## 3. HAL (only if needed)

`firmware/bench/src/hal_arduino.cpp` contains branches per architecture. Without its own branch, the
generic fallback measures time with `micros()` and reports cycles and heap as 0. Its own
branch also provides:

* `hal_cycles()`: cycle counter (Cortex-M3/M4/M7/M33: DWT is used automatically)
* `hal_free_heap()`, `hal_cpu_mhz()`
* `hal_reset()`: software reset (Cortex-M: `NVIC_SystemReset()` is already included)
* `hal_chip()` / `hal_uid()`: identification for the "right board in the slot" check

For non-Arduino environments (ESP-IDF, Zephyr, STM32Cube) you implement `hal.h` in a
separate file and call `bench_init()` and, in the main loop, `bench_poll()`.

## 4. Testing

```bash
uv run edge build -t teensy41
uv run edge discover                  # find the board, add an entry to hil/boards.yaml
uv run edge run -b teensy41-1
```

Add the new target to the firmware build matrix in `.github/workflows/firmware.yml`; then every
change also builds this firmware.

## Small targets

If RAM or flash are not enough, exclude large models:

```ini
build_flags = ${env.build_flags} -D HIL_TARGET=\"tiny\" -D MI_EXCLUDE_PACE_CNN
```
```yaml
tiny:
  excluded_models: [pace-cnn]
```

The macro name is the model name in upper case with every non-alphanumeric character replaced by
`_` (`pace-cnn` → `MI_EXCLUDE_PACE_CNN`; `pace-cnn` is in the firmware only when added through
`MMZ_EDGE_MODELS`). The arena for the activations is sized
automatically for the largest remaining model.

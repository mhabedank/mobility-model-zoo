# Edge bench: HIL test bench for TinyML on microcontrollers

Automated **hardware-in-the-loop (HIL) test bench** that builds, flashes, runs and checks the same
TinyML models on many common SoCs, from the **ESP8266 (ESP8266MOD)** through
**ESP32 / ESP32-S3 / ESP32-C3** to **RP2040 / RP2350, STM32 and nRF52840**. The bench came from
the `hilbench` tool of the mobility-security-ml repository and is now the `edge` command of the zoo.

For every connected board, a run delivers:

* **Correctness**: every inference on the chip is compared **bit-exactly** with a Python reference
  (random and boundary inputs, golden vectors, evaluation datasets).
  For imported models the reference is also bit-exact with the TFLite interpreter.
* **Performance**: latency (min/avg/max), CPU cycles per MAC, latency budgets, regressions
  against a baseline.
* **Memory**: RAM and flash use of the firmware, free heap, heap leaks.
* **Robustness**: soft and hardware reset, watchdog or exception restarts during a soak run
  (including the crash log), automatic recovery (reset → power cycle → re-flash).

Results are written as `summary.md` / `summary.json` / JUnit XML to `results/<timestamp>/`
and, in GitHub Actions, directly into the job summary.

```
                ┌───────────────────────── HIL host (PC / Raspberry Pi / CI runner) ──────────────────────────┐
 hil/boards.yaml│  edge run ──► build (PlatformIO / make) ──► flash (esptool / PIO / UF2 / command)       │
 hil/targets.yaml  pytest + plugin: 1 test run per board, parallel (xdist), board locks, recovery             │
                │        │ USB serial  "#12 INFER can_ids_mlp <hex>"  ◄──►  "@{"id":12,"out":"…","us":…}"        │
                └────────┼──────────────────────────────────────────────────────────────────────────────────┘
          ┌──────────────┼──────────────┬───────────────┬───────────────┬───────────────┐
      ESP8266MOD      ESP32(-S3/-C3)   RP2040/RP2350   STM32 Nucleo    nRF52840      Simulator (PC)
          └── same firmware: benchapp (protocol) + microinfer (int8 engine) + modelzoo ──┘
```

Code: the bench is in `src/mobility_model_zoo/edge/bench`, the int8 engine (quantization, Python
reference, codegen, TFLite import, Keras export) in `src/mobility_model_zoo/edge/int8`.

## Quick start without hardware (simulator)

```bash
uv sync --extra edge --extra edge-hw   # edge-hw = esptool, platformio, pytest-xdist
uv run edge run -b sim                 # builds the firmware for the PC and runs all HIL tests
```

The `sim` board is the real bench firmware, compiled for the PC (`firmware/bench/native`). It is
used to develop tests and to run them in CI. The same suite also runs directly through pytest:
`uv run pytest -m hil --hil-board sim`. With `sim-noisy` and environment variables you can
simulate bootloader noise, watchdog crashes and hangs.

### Virtual ESP32 boards (QEMU)

The real ESP32 firmware also runs in
[Espressif QEMU](https://github.com/espressif/qemu/releases). `hil/qemu-boards.yaml` adds the
emulator as a normal board: the flasher starts QEMU, and the UART is at
`socket://127.0.0.1:5555`. This is how CI runs the complete HIL suite on the Arduino ESP32 firmware.
ESP32-S3/-C3 are prepared there, but only boot in QEMU with firmware based on ESP-IDF ≥ 5
(arduino-esp32 3.x).

```bash
uv run edge --boards hil/qemu-boards.yaml run -b esp32-qemu --quick
```

## Quick start with the ESP8266MOD

1. Connect the board over USB (NodeMCU / Wemos D1 mini with CH340 or CP2102).
   For a bare ESP-12 module, see [hardware.md](hardware.md#esp8266mod--esp-12ef).
2. Let the bench detect it:
   ```bash
   uv run edge discover --probe
   ```
   The command shows the port, USB serial number and physical USB path, queries the chip with
   esptool and suggests an entry for `hil/boards.yaml`.
3. Adjust the entry `esp8266-1` in `hil/boards.yaml` (`match:` with serial number or
   `location`), then:
   ```bash
   uv run edge doctor                  # checks tools, permissions and which boards are connected
   uv run edge run -b esp8266-1        # build, flash, test
   ```
4. Look at the result: `results/<timestamp>/summary.md`, serial log in
   `results/<timestamp>/logs/esp8266-1.log`.

A different inventory file can be set with `--boards` or the environment variable `MMZ_BOARDS`.

## Adding more boards (ESP32, Pico, Nucleo, …)

Every new board is **one entry in `hil/boards.yaml`**:

```yaml
boards:
  - id: esp32-1
    target: esp32                     # type from hil/targets.yaml
    match: {serial_number: "0001"}    # or {location: "1-1.3"} or port: /dev/serial/by-id/...
    power: {type: uhubctl, hub: "1-1", port: 2}   # optional: switch power through a USB hub
```

After that, `uv run edge run --parallel` tests all connected boards at the same time, one worker per
board. Boards that are not connected at the moment are skipped
(`--require-all` turns that into an error, for example for the nightly CI run).

| Target | SoC / board | Flash method | Reset |
|---|---|---|---|
| `esp8266`, `esp8266_160mhz` | ESP8266 / ESP8266MOD (ESP-12E/F) | esptool | DTR/RTS |
| `esp32` | ESP32 DevKit | esptool | DTR/RTS |
| `esp32s3`, `esp32s3_usb` | ESP32-S3 (UART or native USB port) | esptool | DTR/RTS or USB-JTAG |
| `esp32c3`, `esp32c3_usb` | ESP32-C3 (DevKitM or SuperMini) | esptool | DTR/RTS or USB-JTAG |
| `rp2040`, `rp2350` | Raspberry Pi Pico / Pico 2 | PlatformIO or UF2 | soft reset |
| `stm32f446` | NUCLEO-F446RE | PlatformIO (ST-LINK) or `st-flash`/`pyocd` | soft reset |
| `nrf52840` | Arduino Nano 33 BLE (Sense) | PlatformIO (bossac) | soft reset |
| `native` | simulator on the host | – | process restart |

A **new chip type** needs three things (details: [extending.md](extending.md)):
a PlatformIO environment in `firmware/bench/platformio.ini`, an entry in `hil/targets.yaml` and
at most a few lines in `firmware/bench/src/hal_arduino.cpp`. Without its own lines the
generic fallback applies, and the board then only measures time, not cycles.

## Your own TinyML models

```bash
# Keras -> TFLite (full integer int8), then:
uv sync --extra edge --extra edge-train          # provides tflite (and TensorFlow for --verify)
uv run edge import-tflite my_model.tflite --name my_model [--verify]
uv run edge run --parallel             # ends up in the firmware of all boards automatically
```

Supported are sequential graphs with Conv2D, DepthwiseConv2D, Dense,
Max/AveragePooling, Flatten/Reshape and ReLU/ReLU6. QUANTIZE/DEQUANTIZE/Softmax at the edges
are removed. `--verify` compares with the TFLite reference interpreter (needs
TensorFlow). Imported models are stored in `build/edge/custom/`. Models that do not fit on a small
target can be excluded with `-D MI_EXCLUDE_<NAME>` in `platformio.ini` and `excluded_models` in
`targets.yaml`.

The firmware model sources in `firmware/bench/lib/modelzoo` are build output: `edge build`,
`make` (native simulator) and a PlatformIO pre-script generate them. Do not edit them by hand and
do not commit them.

**Bench reference models.** The bench has three synthetic reference models. They are built on
first use under `build/edge/models` (not committed); `uv run edge zoo` rebuilds them.

| Model | Version | Task | Data (licence) | int8 result | MACs | Parameters | Arena |
|---|---|---|---|---|---:|---:|---:|
| `can_ids_mlp` | 0.1.0 | CAN bus intrusion detection | synthetic | bench reference | 1.6 k | 2.0 KB | 64 B |
| `sensor_ae` | 0.1.0 | wheel speed sensor anomaly detection (autoencoder) | synthetic | bench reference | 10 k | 12 KB | 128 B |
| `imu_gnss_cnn1d` | 0.1.0 | GNSS spoofing detector, 1D CNN over IMU+GNSS | benchmark weights | – | 162 k | 6.9 KB | 2 KB |

**Models trained on real data.** Focus: mobility and cyber security. These models are trained on
real, openly licensed data by the task tools of their topic (see below), not by the bench. The
values are from version 0.2.0 on the volta branch of mobility-security-ml. int8 values apply to the
arithmetic of the device (bit-exact host reference):

| Model (former name) | Version | Task | Data (licence) | int8 result | MACs | Parameters | Arena |
|---|---|---|---|---|---:|---:|---:|
| `pace-cnn` (`har_cnn1d`) | 0.2.0 | activity recognition from IMU (6 activities) | UCI HAR (CC BY 4.0) | 93.3 % acc. (2947 windows) | 354 k | 7.3 KB | 4.0 KB |
| `picket-mlp` (`can_ids_road`) | 0.2.0 | CAN bus intrusion detection per frame (MLP 32-64-32-2) | ROAD, real vehicle (CC BY 4.0) | 98.9 % acc., recall 81.7 %, FPR 0.8 % (2.2 million frames, unseen captures) | 4.2 k | 5.0 KB | 128 B |
| `hum-fan` (`mimii_fan_ae`) | 0.2.0 | anomaly detection on machine sounds (autoencoder, 5 × 40 log-mel) | MIMII fan 6 dB (CC BY-SA 4.0) | AUC 0.84 per 10 s clip (id_00 0.75, id_02 0.96; 700 clips) | 35 k | 39 KB | 400 B |

To measure a trained model on the bench, list its `.npz` in `MMZ_EDGE_MODELS`
(separated by `:`); `edge build` and `edge run` then put it into the firmware next to the
reference models.

## Training data and training on real data

The data is never in the repository. `uv run zoo data download <id>` fetches it from the original
provider into `$MMZ_DATA` (default `~/.cache/mobility-model-zoo/datasets`) and checks the licence
that the provider currently declares. Selection, rejected datasets and the question of what may be
mirrored on Hugging Face:
[sound and IMU datasets](../../topics/condition-monitoring/research/datasets-volta.md),
[CAN datasets](../../topics/security/research/datasets.md).

```bash
uv sync --extra edge --extra edge-train
uv run zoo data list                                # use cases, licences, HF mirror allowed?
uv run security can-ids mlp train --download        # picket-mlp on ROAD
uv run condmon activity train --download            # pace-cnn on UCI HAR
uv run condmon sound-anomaly train --download       # hum-fan on MIMII
# each: train -> int8 -> bit-exact check -> $MMZ_DATA/derived/<model>/
MMZ_EDGE_MODELS=$MMZ_DATA/derived/pace-cnn/pace-cnn.npz uv run edge run -b sim
                                                    # HIL suite incl. accuracy on the (simulated) device
```

`picket-forest` (the CAN IDS random forest) has its own pipeline:
`uv run security can-ids forest evaluate|alarms|export|convert|testvectors`.

Training runs locally, not in CI. Publishing a model goes through the zoo release tool `zoo`
(staging, gate, card, approved release), see [adding-a-model.md](../adding-a-model.md).

## Commands

| Command | Purpose |
|---|---|
| `edge discover [--probe]` | find USB devices, guess the target, suggest inventory entries |
| `edge doctor` | check the host: tools, permissions, connected boards, built firmware |
| `edge list` / `targets` | inventory with connection status / known targets |
| `edge build [-t T] [--all]` | build firmware (`build/fw/<target>/` incl. manifest) |
| `edge flash -b B` / `info -b B` | flash a board / show INFO + models |
| `edge console -b B` | interactive protocol console (`PING`, `BENCH can_ids_mlp 10`, …) |
| `edge reset -b B [--method M]`, `power -b B on/off/cycle` | reset / power supply |
| `edge run [-b B] [-t T] [--tag X] [--parallel] [--quick] [--slow] [--baseline S] [-- pytest args]` | complete HIL run |
| `edge report RUN [--baseline S]` | re-render the report / check for regressions |
| `edge import-tflite M.tflite`, `edge zoo` | import models / rebuild the reference models |
| `edge data list\|info\|verify\|download\|path\|tree` | datasets; the documented interface is `zoo data …` |

All commands run as `uv run edge …`.

`uv run pytest tests/edge/hil -m hil --hil-board esp32-1 -k inference -n 4 --dist loadgroup` works
the same way; the plugin (`mobility_model_zoo.edge.bench.pytest_plugin`) is loaded through
`pyproject.toml`.

## Test suites (`tests/edge/hil`)

| File | Checks |
|---|---|
| `test_link.py` | PING/INFO, identity (target, version), ECHO integrity, error handling, round-trip time |
| `test_models.py` | model catalogue = host models (CRC), weights in flash intact, golden vectors |
| `test_inference.py` | random and boundary inputs bit-exact, accuracy on evaluation sets |
| `test_performance.py` | benchmarks (latency, cycles/MAC, stability), budgets, baseline, heap leaks |
| `test_robustness.py` | soft/hardware reset + restart, soak run without unexpected restart (`--slow`) |

At startup the bench checks every board: is the firmware that was just built running (build ID)?
Does the reported chip match the target? This way a swapped cable is noticed immediately.

## CI

* `.github/workflows/ci.yml`: unit tests, the complete HIL suite against simulated boards
  (job `edge-sim`) and the HIL suite on the ESP32 firmware in QEMU (job `edge-qemu`).
* `.github/workflows/firmware.yml`: firmware builds for all 11 targets with an overview of RAM
  and flash use, on changes of `firmware/`, `hil/` or `src/mobility_model_zoo/edge/`.
* `.github/workflows/hil.yml`: runs nightly or manually on a **self-hosted runner** to which the
  real boards are connected, only when the repository variable `HIL_RUNNER_ENABLED` is `true`.
  Setup: [ci.md](ci.md).

These workflows are being added in feature 005.

## Repository layout (edge parts)

```
firmware/bench/             bench firmware (PlatformIO) + host simulator (firmware/bench/native)
  lib/microinfer/           portable int8 inference engine (C99, TFLite-compatible arithmetic)
  lib/benchapp/             serial test protocol + HAL interface
  lib/modelzoo/             generated model data (build output, do not edit by hand)
  src/hal_arduino.cpp       HAL for ESP8266/ESP32/RP2040/STM32/nRF52
firmware/picket-forest/     firmware of the picket-forest CAN IDS (C core, ESP-IDF, ESP8266)
src/mobility_model_zoo/edge/bench/   host side: CLI, discovery, flashing, reset/power, sessions, pytest plugin, reports
src/mobility_model_zoo/edge/int8/    quantization, Python reference, codegen, TFLite import, Keras export
src/mobility_model_zoo/datasets/     dataset registry (licences) + downloader
hil/                        targets.yaml (chip catalogue), boards.yaml (your lab inventory), qemu-boards.yaml,
                            udev rule 99-mmz-edge.rules, setup-host.sh
build/edge/models|custom    reference models / your own imported models (not committed)
tests/edge/hil, tests/edge/bench, tests/edge/int8   HIL suites / host tests
docs/edge/                  hil-bench.md, hardware.md, protocol.md, ci.md, extending.md
```

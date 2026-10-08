# picket-forest firmware

Frame-level CAN intrusion detector (random forest, emlearn) for microcontrollers.

| Path | Content |
|---|---|
| `c/picket_forest.{c,h}` | Detector API: `picket_forest_init`, `picket_forest_score`, `picket_forest_process` |
| `c/host_score.c` | Host harness used by the C-vs-Python parity check |
| `c/generated/` | `picket_forest_config.h` (committed); `picket_forest_model.h` and `test_vectors.h` are generated and gitignored |
| `esp-idf/` | ESP-IDF benchmark app (ESP32, ESP32-S3, ...): `idf.py set-target esp32s3 && idf.py build flash monitor` |
| `esp8266/` | Arduino benchmark sketch for ESP8266: `./esp8266/build.sh` |

Feature extraction comes from `../components/can_features` (`msml_*`).

Generate the model and test vectors before building the benchmarks:

    uv run security can-ids forest export        # trains, writes $MMZ_DATA/derived/picket-forest/export/
    uv run security can-ids forest testvectors   # copies headers into c/generated/

The benchmark replays recorded CAN frames (no CAN transceiver needed) and prints a line starting
with `PICKET_FOREST_RESULT` every 5 seconds at 115200 baud.

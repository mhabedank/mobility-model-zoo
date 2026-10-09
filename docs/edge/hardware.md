# Hardware setup of the HIL bench

## The host

Any Linux computer works as a HIL host; a Raspberry Pi 4/5 is enough. In addition you need:

* an **active USB hub**, ideally with **switchable power per port** (per-port
  power switching, PPPS). The bench can then recover even a completely stuck board with a
  power cycle. Compatible hubs: `uhubctl` without arguments lists them,
  see also <https://github.com/mvp/uhubctl#compatible-usb-hubs>. Alternatively, a
  relay board or a switchable socket works with `power: {type: command, on: …, off: …}`.
* **good USB cables** (data cables!). For boards with Wi-Fi/BLE current peaks the hub should have
  its own power supply.

One-time setup:

```bash
sudo ./hil/setup-host.sh     # dialout group, udev rule hil/99-mmz-edge.rules, lock dir /var/lock/mmz-edge, uhubctl
```

## Identifying boards uniquely

`uv run edge discover` lists `serial_number`, `location` (physical USB path),
`vid_pid` and the `/dev/serial/by-id` name for every port. In `hil/boards.yaml`
(or the file named in `MMZ_BOARDS`):

| Situation | `match:` |
|---|---|
| adapter with a unique serial number (FTDI, CP2102 with serial, native USB of ESP32-S3/C3, RP2040, nRF52) | `{serial_number: "…"}` |
| cheap CH340 boards (no or identical serial numbers) | `{location: "1-1.4"}`: then **always keep the board on the same hub port** |
| exactly one board of this type on the host | `{vid_pid: "1a86:7523"}` |
| board on another computer (ser2net / RFC2217) | `port: rfc2217://raspi:4000` |

After flashing, the bench queries which target and which chip responds and which
build ID is running. A swapped board or a failed flash is therefore noticed
immediately.

## ESP8266MOD / ESP-12E/F

### On a dev board (NodeMCU, Wemos D1 mini, …)

These boards have a USB UART (CH340/CP2102) and the usual auto-reset circuit
(DTR→GPIO0, RTS→EN through two transistors). Nothing else is needed:

```yaml
- id: esp8266-1
  target: esp8266            # or esp8266_160mhz for 160 MHz benchmarks
  match: {location: "1-1.2"}
```

Notes:
* The ROM bootloader writes text at 74880 baud after every reset. The bench ignores this
  noise and only looks for `@{…}` frames.
* The firmware puts the weights into flash with `PROGMEM`, so that they do not occupy the ~80 KiB
  of DRAM. The free heap is measured and reported on every run.

### Bare module with a USB UART adapter (3.3 V!)

| ESP-12 pin | Connection |
|---|---|
| VCC | 3.3 V (≥ 300 mA, 470 µF electrolytic capacitor close to the module) |
| GND | GND |
| TX / RX | RX / TX of the adapter |
| EN (CH_PD) | 10 kΩ to 3.3 V **and** RTS of the adapter (through an NPN auto-reset circuit or directly) |
| GPIO0 | 10 kΩ to 3.3 V **and** DTR of the adapter (through the auto-reset circuit) |
| GPIO2 | 10 kΩ to 3.3 V |
| GPIO15 | 10 kΩ to GND |
| RST | 10 kΩ to 3.3 V |

Without an auto-reset circuit, GPIO0 has to be pulled to GND by hand before every flash. For an
automated bench the circuit (2× BC547 + 2× 10 kΩ, as on the NodeMCU) should therefore
be present.

## ESP32 / ESP32-S3 / ESP32-C3

* DevKits with a UART bridge: `target: esp32 | esp32s3 | esp32c3`, reset through DTR/RTS.
  Some ESP32 boards need 1–10 µF between EN and GND, otherwise auto-reset does not work
  reliably.
* Native USB port (USB Serial/JTAG, `303a:1001`): `target: esp32s3_usb | esp32c3_usb`. The
  port disappears briefly during reset; the bench waits for it and reconnects.

## Raspberry Pi Pico / Pico 2 (RP2040 / RP2350)

* Serial connection over native USB CDC. Flashing uses PlatformIO (`picotool`) or
  `flasher: uf2`: 1200 baud touch, then copy `firmware.uf2` to the mounted drive `RPI-RP2`
  (auto-mount required, otherwise set `flasher_options: {mount_globs: [...]}`).
* There is no hardware reset over serial lines. A power cycle through a
  switchable hub port (`power: uhubctl`) is therefore strongly recommended. Optionally, a GPIO
  of another board can pull the RUN pin (`reset: command`).

## STM32 Nucleo (e.g. NUCLEO-F446RE)

* Serial connection through the virtual COM port of the ST-LINK (`0483:374b`).
* Flashing: PlatformIO (OpenOCD) or faster with a command:
  ```yaml
  flasher: command
  flasher_options: {command: "st-flash --reset write {bin} 0x08000000"}
  reset: command
  reset_options: {command: "st-flash reset"}
  ```

## Arduino Nano 33 BLE (nRF52840)

* Native USB CDC; flashing goes through PlatformIO (bossac, 1200 baud touch).
* Reset with the RESET command. If the firmware hangs: power cycle through the hub, or a double click
  on the reset button starts the bootloader.

## Boards on another computer

Recommended: the computer the boards are connected to (e.g. a Raspberry Pi) runs
`edge` itself, or the self-hosted CI runner ([ci.md](ci.md)). The Pi is then a
complete HIL host.

For testing boards that are already flashed, an RFC2217 share with `ser2net` is also enough:

```yaml
- id: esp32-remote
  target: esp32
  port: rfc2217://raspi.local:4001
```

```bash
uv run edge run -b esp32-remote --no-flash
```

Inference, benchmarks and the DTR/RTS reset work over the network. For flashing,
`flasher: command` can be used with your own script (placeholders `{bin}`, `{elf}`,
`{dir}`, `{port}`) that transfers the file, e.g. with `scp`, and calls esptool on the Pi.

# 04 – Hardware: processors, boards, lab setup

The full comparison tables for around 40 parts, the toolchain matrix and all sources are in
[notes/hardware.md](notes/hardware.md). Prices are mostly **unverified** `[U]`.

## Recommendation

| Role | Choice | Rationale |
|---|---|---|
| **(a) Prototyping, main target** | **ESP32-S3** (DevKitC-1 N16R8 or **LilyGO T-2CAN** with 2 isolated CAN buses) | Board 12–35 $, 512 KB SRAM plus PSRAM, 128-bit SIMD; in Espressif's benchmark **ESP-NN** takes a person-detection model from 2300 ms to 54 ms; **ESP-DL v3**; Wi-Fi/BLE for telemetry, OTA and BLE experiments |
| **(b) Production-like (automotive)** | **NXP S32K344** (S32K3X4EVB-T172) | AEC-Q100, **ASIL-D lockstep M7**, HSE-B, **6× CAN FD**, Ethernet TSN; **eIQ Auto** officially supports S32K3; TFLM, CMSIS-NN and emlearn run without changes |
| **(b′) Budget alternative** | **Infineon AURIX TC375 Lite Kit** (~95 €) | ASIL-D, HSM, CAN FD; but TriCore is not Arm, so no CMSIS-NN; export via emlearn or plain C |
| **(c) High end with NPU** | **STM32N6** (NUCLEO-N657X0-Q) | Neural-ART NPU with 600 GOPS, M55 at 800 MHz, 4.2 MB RAM, **3× FDCAN**, GbE/TSN; **the same toolchain (ST Edge AI Core)** targets the automotive-grade **Stellar P3E** (ASIL-D, NPU, 8× CAN FD + 2× CAN XL, production planned for Q4 2026) |
| **(c′) Low-cost NPU alternative** | **NXP FRDM-MCXN947** (~23 $) | Neutron NPU plus CAN FD transceiver on the board |

## Key findings

- **ESP32 and CAN FD:** According to ESP-IDF `soc_caps.h` [V]:

  | Chips | TWAI controllers |
  |---|---|
  | ESP32, S2, S3, C3, H2 | 1× **CAN 2.0 only** |
  | C6 | 2× **CAN 2.0 only** |
  | P4 | 3× **CAN 2.0 only** |
  | **C5** | 2× **with CAN FD** |
  | **H4** | 1× **with CAN FD** |
  | **S31** | 2× **with CAN FD** |

  The new **ESP32-S31** combines SIMD, 2× TWAI-FD and Gigabit Ethernet. It is a candidate for the next prototyping generation.
- **Caution:** Classic TWAI controllers treat CAN FD frames as errors. So **never connect an ESP32-S3 directly to a
  CAN FD bus**. For FD buses, combine the S3 with **MCP2518FD + MCP2562FD** via SPI or use an ESP32-C5.
- **Timestamps:** Hardware timestamps matter for timing and clock-skew features. The MCP2518FD has a 32-bit timestamp;
  FDCAN and FlexCAN have timestamp counters. The ESP32 TWAI driver, in contrast, timestamps in software, with more jitter, especially
  when Wi-Fi is active.
- **Automotive qualification:** Only NXP S32K3/S32K5/S32G, Infineon AURIX, ST SPC5/Stellar and Renesas RH850 are
  AEC-Q100 qualified and have ASIL-D and an HSM. ESP32, STM32 (standard), RA8, Alif, PSoC Edge, Nordic and MAX78000
  are suitable for prototypes only.
- **Upgrade paths:** AURIX TC4x with PPU vector DSP and NN SDK; NXP S32K5 with Neutron NPU, so far only samples for
  lead customers; S32G3 as a central gateway IDS with Linux and 20× CAN FD.

## Not recommended as the main path

- **RP2040/RP2350:** no hardware CAN; `can2040` emulates CAN 2.0 via PIO.
- **MAX78000, Syntiant, GAP9, K210:** no CAN, vendor-specific CNN toolchains, designed for audio and vision.

## CAN connection for prototypes

| Component | CAN FD? | Use |
|---|---|---|
| SN65HVD230 (TI) | no | cheap 3.3 V transceiver for classic CAN |
| TJA1051T/3 (NXP) | yes, 5 Mbit/s | standard FD transceiver for 3.3 V MCUs |
| MCP2562FD (Microchip) | yes, 8 Mbit/s | pairs with the MCP2518FD |
| MCP2515 (SPI) | no | CAN 2.0B, very common |
| **MCP2518FD (SPI)** | yes | preferred CAN FD controller for any MCU, with hardware timestamp |

| Board | MCU | CAN | approx. price |
|---|---|---|---|
| LilyGO T-CAN485 | ESP32 | 1× TWAI | ~12 $ |
| **LilyGO T-2CAN** | ESP32-S3 | 2× isolated (TWAI + MCP2515) | ~25–35 $ |
| Macchina A0 | ESP32 | 1×, in OBD plug format | ~90 $ |
| **CANable 2.0** | STM32G431 | 1× CAN FD, native SocketCAN | ~35 $ |
| comma panda (CAN FD kit) | STM32H725 | CAN + CAN FD | 99–450 $ |
| FRDM-MCXN947 | MCX N947 (NPU) | CAN FD transceiver | ~23 $ |
| NUCLEO-N657X0-Q | STM32N6 (NPU) | CAN FD header | ~50 $ [U] |
| KIT_A2G_TC375_LITE | AURIX TC375 | CAN + Ethernet | ~95 € |

## Lab setup

```
 [Linux PC: SocketCAN, can-utils, python-can, cantools]
        │ USB
   [CANable 2.0]───────┐
                       │  twisted pair, 120 Ω at both ends
 [OBD-II breakout]─────┼─────────────┬──────────────────┐
                       │             │                  │
                       │      [DUT 1: ESP32-S3 +   [DUT 2: S32K344-EVB /
                       │       SN65HVD230 or        NUCLEO-N657 / TC375]
                       │       MCP2518FD]
         [optional: ECU simulator or 2nd CANable replaying logs]
```

1. **Software only first:** set up `vcan0`, replay logs from public datasets with `canplayer` and
   develop the feature extraction without hardware.
2. **Physical bus:** `ip link set can0 type can bitrate 500000` (for CAN FD additionally `dbitrate 2000000 fd on`).
3. **Capture and replay:** `candump -l`, `canplayer`, `cansniffer`, `canbusload`.
4. **Attacks for labelled data:** `cangen -I 000` (DoS), `cangen -I r -L r` (fuzzing); spoofing and replay with python-can scripts;
   labels via time windows.
5. **Real vehicle logs** (passive capture only) with comma panda or CANable. **Never inject into a moving
   vehicle.** Attacks only on the lab bench or with ECUs from the scrapyard.
6. **GNSS:** u-blox M9/F9, which deliver jamming indicator, C/N0 and AGC via UBX. Operate an SDR **only in a shielded environment or with a
   GNSS simulator**, because transmitting GNSS signals is illegal.
7. **BLE/keyless:** nRF54L15 DK (BLE Channel Sounding) or DW3000 UWB modules.

## Shopping list for the start (proposal)

| Part | Purpose | approx. price |
|---|---|---|
| 2× ESP32-S3-DevKitC-1 N16R8 **or** 1× LilyGO T-2CAN | DUT | 25–35 $ |
| 2× SN65HVD230 module | CAN transceiver | < 10 $ |
| CANable 2.0 | PC interface, replay | ~35 $ |
| OBD-II breakout box, 120 Ω resistors, 12 V lab power supply | Bus | 50–100 $ |
| *later:* MCP2518FD module, NUCLEO-N657X0-Q, S32K344-EVB, Joulescope or Nordic PPK2 | CAN FD, NPU, automotive, energy measurement | – |

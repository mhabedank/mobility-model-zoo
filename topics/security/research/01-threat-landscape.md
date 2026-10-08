# 01 – Threat landscape: what can TinyML address?

Details, sources and verification status are in [notes/threats-and-papers.md](notes/threats-and-papers.md).

## Rating scale "MCU suitability"

| Level | Meaning |
|---|---|
| **high** | Runs comfortably on a Cortex-M4 or ESP32-S3 with ≤ 256 kB RAM, without special hardware |
| **medium** | Needs additional sensing or an analogue front end, an M7-class MCU or careful engineering |
| **low** | The data rate or model size calls for an MPU, FPGA or SoC |

## Overview of the problem areas

| # | Problem | Attack | Input signals | MCU suitability | Key literature |
|---|---|---|---|---|---|
| 1 | **CAN IDS (ID/timing)**: DoS, fuzzing, replay, spoofing, suspension | Compromised ECU, OBD dongle, pivot via telematics/infotainment | Timestamp, CAN ID, DLC, ID sequences, inter-arrival time (IAT) per ID; at 500 kbit/s ≤ ~4k frames/s | **high**: features cheap, models 10–100 kB; already shown on nRF52840, STM32F746 and RISC-V | Song 2016; Kang & Kang 2016; Song 2020; INDRA 2020; Im & Lee 2025 |
| 2 | **CAN IDS (payload/signal)**: masquerade, targeted signal forgery | A legitimate ECU is silenced; the attacker sends with correct timing | Decoded signals (DBC or reverse engineering), signal correlations | **medium–high**: small autoencoders/TCNs per ID group; needs signal mapping | CANShield 2023; INDRA; ROAD 2024; MR-TCN 2025 |
| 3 | **Sender identification via clock skew** | Masquerade by a foreign ECU | High-resolution arrival times of periodic messages | **high**: RLS + CUSUM, no deep learning needed; needs µs-accurate hardware timestamps | CIDS (USENIX Sec 2016) |
| 4 | **Sender identification via voltage** | Masquerade, bus-off, attacker identification | Analogue CAN_H/CAN_L edges; ADC in the MS/s range | **medium**: compute is low (EASI < 100 µs), but the analogue front end is hard; the ESP32 ADCs are too slow | Viden, VoltageIDS, Scission, SIMPLE, EASI; attack: DUET |
| 5 | **CAN FD** | as CAN, with up to 64-byte payload | ID, timing, 64-byte payload | **medium–high**: timing stays cheap, payload models become 8× larger | HCRL CAN-FD; SecCAN 2025 |
| 6 | **Automotive Ethernet** (SOME/IP, DoIP, AVTP, gPTP) | Stream injection, service spoofing, misuse of diagnostics | Headers, flow statistics, service IDs | **low** at line rate; **medium** for flow features on zone controllers | Jeong 2021; TOW-IDS 2023; Alkhatib 2021; Carmo 2025 |
| 7 | **LIN / FlexRay** | LIN: false-response injection | LIN at 19.2 kbit/s with a fixed schedule | **high** (LIN); hardly any ML literature, so a **new field** | Takahashi 2017 |
| 8 | **Keyless entry / relay, UWB** | Relay of LF/UHF, UWB distance reduction (Ghost Peak) | RSSI, RF fingerprint, UWB channel impulse response (CIR), IMU in the key | **medium**: depends on whether the radio chips deliver raw data (e.g. CIR on the DW3000) | Francillon 2011; HODOR 2020; Ghost Peak 2022 |
| 9 | **GNSS spoofing/jamming** | Spoofer drags the position away; jammer against theft tracking | PVT at 1–10 Hz, C/N0, AGC, clock error, IMU at ~100 Hz, wheel speed | **high**: small LSTM/MLP for plausibility; fuse several sources, because pure INS checks can be bypassed | Dasgupta 2021; Narain 2019 |
| 10 | **TPMS spoofing** | Forged 315/433 MHz packets without authentication | Sensor ID, RSSI, timing, pressure vs. wheel speed | **high** (compute); **almost no ML literature**, so a new field | Rouf 2010 |
| 11 | **Sensor spoofing** (LiDAR, radar, IMU, wheel speed) | Laser, acoustic and magnetic injection | Raw point clouds (low) vs. physical invariants such as wheel vs. IMU vs. GNSS vs. steering (high) | **high** for invariant models, **low** for raw perception data | Shoukry 2013; WALNUT 2017; Cao 2019 |
| 12 | **V2X misbehaviour** | Ghost vehicles, false position/speed, Sybil, replay | Fields of the received CAM/BSM, RSSI | **medium–high**: per-message models are tiny; the V2X stack, however, usually runs on an SoC | VeReMi 2018; VeReMi Extension 2020 |
| 13 | **EV charging** (OCPP, ISO 15118) | OCPP MITM/DoS, manipulated meter values, Brokenwire | Current/voltage/power, OCPP statistics | **medium–high**: TinyML on the ESP32 already shown | Dehrouyeh 2024/2025 |
| 14 | **OBD-II dongles** | Insecure Bluetooth/Wi-Fi dongles as an entry point | CAN traffic from the OBD port, UDS patterns | **high**: via the gateway IDS or an IDS in the dongle itself | Plug-N-Pwned 2020 |
| 15 | **Side-channel / fault-injection detection** | Glitching, EM fault injection | On-chip telemetry, error counters | **low–medium**; thin literature | – |
| 16 | **Driver profile / theft protection** | Theft with a cloned key or relay | CAN signals at 1–10 Hz (pedal, steering, engine speed) | **high**: small GRU/1D CNN < 50 kB | Ahmad 2020; "Know your master" 2016 |
| 17 | **Micromobility** (e-scooter/e-bike) | Unauthenticated BLE commands, tuning, theft | BLE GATT, UART/CAN between display, BMS and motor, IMU, GPS | **high**: the devices have ESP32/STM32/nRF anyway; **no public data** | Vinayaga-Sureshkanth 2020 |
| 18 | **Telematics (TCU)** | Remote exploit, then pivot to CAN (Jeep 2015) | TCU network flows; gateway view of the CAN | **low** on the TCU; **high** on the gateway | Miller & Valasek 2015 |

## Place in regulation and architecture

The statements on the standards in this section are **not checked against the original texts**.

- **UNECE R155** (Cyber Security Management System) requires that attacks in the field are detected and responded to.
  An on-board IDS is the usual technical measure for this. R155 does not prescribe ML.
- **UNECE R156** (Software Update Management System) governs the path for model updates.
- **ISO/SAE 21434:** An ML IDS is a cybersecurity control. Its false-alarm behaviour and its update path must be
  justified in the cybersecurity case.
- **AUTOSAR IdsM:** A TinyML detector is a **security sensor**. It reports compact *security events*
  (event ID, CAN ID, score) to IdsM, not raw data. IdsM handles rate limiting. The events travel
  on via the Security Event Memory and IdsR to the OEM's vehicle SOC.
- **SecOC** complements the IDS but does not replace it. DoS, compromised ECUs with a valid key, timing
  and suspension anomalies, and buses without SecOC remain the IDS's job.

**What this means for us:** We always report **false positives per driving hour**, not only per frame. An example of
the order of magnitude in a fleet: at 1 false alarm per 1000 h and 10⁶ vehicles, about 1000 false alarms per hour arrive at the SOC.

## Conclusion

| Category | Problem areas |
|---|---|
| **Feasible now** (data available, MCU-suitable) | 1, 2, 9, 12, 16 (data non-commercial only), 13 (licence unclear) |
| **Feasible with own hardware/data collection** | 3, 7, 8, 10, 14, 17 |
| **Medium term / with special hardware** | 4, 5, 6 (flow features only), 11 (invariants only) |
| **Not a TinyML target** | Line-rate Ethernet DPI, raw LiDAR/radar data, raw side-channel traces |

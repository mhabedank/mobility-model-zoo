# 09 – CAN IDS data sources and auxiliary signals (2026-10-10)

Web review for picket-forest 0.2.0 (feature 010): which institutions publish CAN intrusion data, which datasets are downloadable under licences that allow training an Apache-2.0 model, and which auxiliary signals could help. Tags: [V] page or paper opened, [U] snippet or secondary source.

## Downloadable, licence allows training

| Dataset | Institution, year | Vehicles | Content | Attacks | Licence, access |
|---|---|---|---|---|---|
| ROAD (in use) | ORNL; Verma et al., PLoS ONE 2024 | 1 (anonymised) | about 3 h ambient, 30 min attacks; CAN-D decoded signals for part of the captures | fuzzing, fabrication, accelerator physical; masquerade simulated | CC BY 4.0, Zenodo 10462796 [V] |
| can-train-and-test (in use) | DTU (Lampe/Kidmose, Meng), 2023/24 | 4 | 24.7 h unique | mixed: on-road spoofing, replayed DoS/fuzzing with changed timestamps | CC BY 4.0 [V] |
| CAN-MIRGU | Robert Gordon Univ., Horiba MIRA, UDST; VehicleSec 2024 | 1 (modern car, model not named) | 17 h benign real driving | 26 physically verified injections (DoS, fuzzing, replay, spoofing on 13 IDs), 10 simulated masquerade/suspension | CC BY 4.0, UCI 1035 [V]; **the UCI archive is corrupt** (2026-10-10, downloaded twice: the first 180 MB of the 521 MB zip are zero bytes, no local file header; the UCI page lists no mirror) |
| AutoHack | Korea Univ. (HCRL) and Kookmin Univ.; submitted VehicleSec 2026 | 1, C-, P- and B-CAN | 60.6 GB over versions | fuzzing, spoofing, replay, DoS, UDS; physically verified | CC BY 4.0, Zenodo 19661007 [V]; not peer reviewed yet |
| CrySyS CAN logs | BME CrySyS; Scientific Data 2023 | 1 | 26 benign traces (2 h 33 min), 1,248 attacked traces | fabrication on a physical testbed; masquerade simulated | CC BY 4.0, Figshare [V] |
| KCID | DTU, 2025 | 4 (2011 Traverse, 2017 Focus, 2017 Forester, 2022 CR-V), 16 drivers | 27.9 GB benign, real logger timestamps | none | CC BY 4.0, DTU Data 30483005 [V]; Traverse and Forester likely the can-train-and-test vehicles |
| ReCAN | PoliMi, Univ. Murcia; Data in Brief 2020 | cars and trucks (Giulia, Corsa, Fuso, Isuzu, Porter) | 36 M frames benign | none | MIT / CC BY (conflicting fields) [V] |
| commaCarSegments | comma.ai | 230 platforms | about 3,148 h | none | MIT, not gated [V]; CAN logged in 10 ms batches, no per-frame timestamps; bus 0 only, openpilot's own frames removed |
| comma2k19 | comma.ai, 2018 | 2 (RAV4, Civic) | 33 h CAN + GNSS + IMU | none | MIT [V] |

## Downloadable but restricted or unclear (not used for an Apache-2.0 model)

HCRL Car-Hacking, Survival Analysis, OTIDS, Challenge 2020, CAN-FD, X-CANIDS (academic use or no licence stated; Car-Hacking has multi-thousand-second bus gaps); SynCAN (ETAS, synthetic, non-commercial, excludes deployment); CICIoV2024 (UNB, immobile car, fewer than 15,000 unique rows, no licence stated); TU Eindhoven CAN v2 (CC BY-NC 4.0); UIDS-CAN (subscription). [V/U as in the review]

No openly downloadable traffic dataset found from Michigan, KU Leuven, Luxembourg, Waterloo, NYU, Ben-Gurion, Toyota, Hitachi, NIST or Auto-ISAC [U].

## Auxiliary signals

- ROAD contains CAN only (no GNSS, IMU or physical layer) [V]; cross-checks there are limited to decoded CAN signals (e.g. wheel speeds against vehicle speed).
- Physical cross-checks (GNSS speed or IMU against CAN speed, redundant wheel speeds) mainly help against masquerade and payload spoofing, which timing cannot see; they add little for fabrication and fuzzing, which timing and counts already catch [U, judgement of the review].
- Driving state from CAN (parked, idle, driving) is the most useful cheap addition: separate rate baselines per state.
- Multimodal open data: comma2k19 (CAN + GNSS + IMU, MIT) [V].

## Implications for picket-forest

1. A second vehicle with physically injected attacks: CAN-MIRGU first (CC BY 4.0, peer reviewed), then AutoHack and CrySyS.
2. False alarms per hour across many vehicles: commaCarSegments with count features over windows of at least 100 ms (its timestamps do not resolve single intervals); per-frame timing is validated on KCID and ReCAN.
3. Split by vehicle, report false alarms as debounced alarms per benign hour with Poisson bounds (zero alarms in T hours bounds the rate at about 3/T per hour), calibrate on target-vehicle benign data only.

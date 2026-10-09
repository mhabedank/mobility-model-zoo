# 02 – Literature

The full bibliography with 92 entries, links and verification status is in
[notes/threats-and-papers.md § 9](notes/threats-and-papers.md#9-bibliography). Only the most important works are listed here.
Entries marked `[unverified]` must be checked in DBLP or Google Scholar before citing.

## ML IDS that actually run on MCU or embedded hardware

| Work | Platform | Model | Result | Status |
|---|---|---|---|---|
| Im & Lee, IEEE Embedded Systems Letters 17(2), 2025 | **nRF52840** (Cortex-M4F), TFLite Micro | Dual-branch CNN (ID sequence + payload) | **20.44 kB flash, 26.44 kB RAM**, without quantisation | [V] |
| TPI-IDS, Springer 2025 (DOI 10.1007/978-3-031-98167-8_24) | **STM32** | IAT → greyscale image → quantised CNN | F1 > 0.99 | [V-partial] |
| PIB-IDS, Springer 2026 (DOI 10.1007/978-3-032-10209-6_30) | **STM32F746** | Payload image → quantised CNN | real-time capable | [V-partial] |
| Bonomo et al., SBESC 2024 | **RISC-V** | 5 classic ML models | up to F1 = 1.0, real-time capable | [V] |
| Crocioni et al., arXiv 2103.00201 | Automotive MCUs (ST) | automatically mapped NN | characterisation | [V] |
| Althunayyan, PhD thesis Cardiff | MCU | TinyML + tiny online learning per CAN ID | F1 0.975–0.993 | [V-partial] |
| Kneib et al., EASI, NDSS 2020 | resource-constrained ECU | edge-based sender identification | < 100 µs, 168× less memory | [V] |
| Dehrouyeh et al., IEEE Access 2024 | **ESP32** | TinyML IDS for EV charging infrastructure | less latency and memory than classic ML | [V] |
| Khandelwal & Shreejith, FPL 2023 / SecCAN 2025 | FPGA / inside the CAN controller | 2-bit MLP | 0.24 ms per message; SecCAN: latency fully within the reception window, 73.7 µJ per message | [V] |
| Carmo et al., BRACIS 2025 | Raspberry Pi 4 (comparison class) | distilled DL for automotive Ethernet | 727 µs, AUC 0.989 | [V] |

**Finding:** Memory is not a problem for CAN IDS; it is a matter of tens of kilobytes. The hard point is
**latency at full bus load** on a single-core ECU that also runs AUTOSAR. Realistic options are
**window-based detection** (inference every N frames or T ms) and cheap per-frame feature updates in the ISR/DMA path.

## Fundamental attack papers

These works show that the attacks we build models against exist:

- Koscher et al., S&P 2010; Checkoway et al., USENIX Sec 2011; Miller & Valasek, Black Hat 2015 [unverified]
- Francillon, Danev, Čapkun: *Relay Attacks on PKES*, NDSS 2011 [V]
- Rouf et al.: *TPMS Case Study*, USENIX Sec 2010 [V]
- Shoukry et al.: *Non-invasive Spoofing Attacks for ABS*, CHES 2013 [V]
- Trippel et al.: *WALNUT*, EuroS&P 2017 [V]
- Cao et al.: *Adversarial Sensor Attack on LiDAR*, CCS 2019 [V]
- Narain et al.: *Security of GPS/INS based On-road Location Tracking*, S&P 2019 [V]
- Leu et al.: *Ghost Peak (UWB)*, USENIX Sec 2022 [V]
- Takahashi et al.: *Automotive Attacks on LIN-Bus*, JIP 2017 [V]

## CAN IDS classics

- Müter & Asaj, IV 2011 (entropy) [V]
- Song, Kim, Kim, ICOIN 2016 (time intervals) [V]
- Kang & Kang, PLOS ONE 2016 (DNN) [V]
- Taylor et al., DSAA 2016 (LSTM) [V]
- Seo et al., GIDS, PST 2018 [V]
- Song, Woo, Kim, Vehicular Communications 2020 (DCNN, origin of Car-Hacking) [V]
- Kukkala et al., INDRA, IEEE TCAD 2020 (GRU autoencoder) [V]
- Shahriar et al., CANShield, IEEE IoT-J 2023 (signal level) [V]
- Hellemans et al., MR-TCN, IEEE T-ITS 2025 [V]

## ECU fingerprinting

- Cho & Shin: CIDS, USENIX Sec 2016 (clock skew) [V]; Viden, CCS 2017 [V]
- Choi et al.: VoltageIDS, TIFS 2018 [V]
- Kneib & Huth: Scission, CCS 2018 [V]
- Foruhandeh et al.: SIMPLE, ACSAC 2019 [V]
- Kneib et al.: EASI, NDSS 2020 [V]
- **Counter-attack:** Bhatia et al., *Evading Voltage-Based IDS* (DUET), NDSS 2021 [V]

## Pitfalls and criticism

These works are **required reading before the first model**:

1. **Verma et al.**, *A comprehensive guide to CAN IDS data and introduction of the ROAD dataset*, PLOS ONE 2024 [V]:
   documents the artefacts in Car-Hacking.
2. **Kidmose, Kidmose, Meng**, *can-sleuth*, IJIS 2025 [V]: evaluates 16 IDS on 6 datasets and finds dependencies between training and test.
3. **Koltai, Ács, Gazdag**, *CAN We Trust Your Results? A Cross-Dataset Study*, arXiv 2606.30430, 2026 [V]:
   large performance swings between datasets.
4. *Shortcut learning … in frame-level CAN intrusion detection*, Elsevier 2026 [V-partial]: a pure
   ID lookup reaches ROC-AUC 0.97–0.99, random forests on timing only 0.995.
5. **Blevins et al.**, *Time-Based CAN Intrusion Detection Benchmark*, AutoSec 2021 [V]
6. **Lazeski et al.**, *On the Real-World Applicability of Automotive CAN IDS*, VehicleSec 2026 [V]
7. **Arp et al.**, *Dos and Don'ts of Machine Learning in Computer Security*, USENIX Sec 2022 [V]:
   sampling bias, data snooping, wrong metrics, lab-only evaluation.

### Resulting evaluation protocol for this repo

- **Split data temporally and per recording**, never randomly per frame.
- Test **across vehicles and across datasets**. can-train-and-test has ready-made splits with unseen vehicles for this.
- Use Car-Hacking (HCRL) only as a plausibility check, never as the main result.
- Metrics: **AUC-PR, F1, recall at fixed FPR, false positives per hour, detection latency**, plus RAM, flash,
  latency and energy **on the device**, including feature extraction.
- Always evaluate **masquerade attacks** too, because pure timing detectors fail there.
- Check robustness against **adaptive attackers**, with evasion attacks constrained to valid CAN traffic.
  See [05 – Toolchain](05-toolchain-and-publishing.md#adversarial-robustness).

## Surveys for the related-work section

- Lampe & Meng, *A survey of deep learning-based intrusion detection in automotive applications*, ESWA 2023 [V]
- *A Survey of Learning-Based IDS for In-Vehicle Network*, arXiv 2505.11551 [V-partial]
- *A Survey of Anomaly Detection in In-Vehicle Networks*, arXiv 2409.07505 [V-partial]
- Dehrouyeh et al., *On TinyML and Cybersecurity: EV Charging Infrastructure Use Case*, IEEE Access 2024 [V]

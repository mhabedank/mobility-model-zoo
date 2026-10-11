# 08 – Mobility security problems where an open model can add value (2026-10-09)

Follow-up to [07 – production readiness](07-production-readiness.md). Owner request: find relevant cyber-security problems in mobility where we can add value. Bar (owner, 2026-10-09): only production-ready models; check problem relevance, data, architecture before building.

Four parallel web reviews (road vehicles; GNSS; maritime and aviation; EV charging, V2X, micromobility, rail, backends). Tags as before: [V] checked in the source, [U] snippet or secondary. Source URLs are in the review transcripts summarised here; the key ones are cited inline.

## Criteria

1. **Relevance**: real incidents and losses, someone who would deploy the model, a gap next to existing products.
2. **Data**: public, realistic, licence allows training and publishing an Apache-2.0 model; labels or a sound way to evaluate.
3. **Tool fit**: ML adds something over rules, physics or cryptography.
4. **Reachability**: a private person without budget, attack hardware (jamming is illegal) or fleet can show production readiness (false alarms per hour/day at a stated budget, unseen devices/regions).

## Overview

| Area | Problem | Relevance | Data | ML fit | Reachable | Verdict |
|---|---|---|---|---|---|---|
| Road | Keyless relay / rolling code | very high (93 % of UK recoveries keyless, Tracker 2025 [V]) | tiny (KeFRA 340 images) | no: UWB, motion-sleep fobs | no | no |
| Road | CAN-injection theft, parked | real (RAV4 CVE-2023-29389 [V]) | none | rule (bit errors) or ECU fingerprinting (vDome) | no | no |
| Road | OBD dongles, TPMS, backend/API abuse | real, but fix is engineering/crypto/AppSec | none open | no | no | no |
| Road | Driver authentication (anti-theft) | medium | KCID (16 drivers, 4 cars, licence unknown); HCRL academic only | yes, one-class per vehicle | false alarms not provable | maybe |
| Road | Parked tamper/tow detection (accelerometer) | aftermarket demand | none public | small int8 model | own recordings, one vehicle | maybe |
| GNSS | Jamming detection on the receiver | high (cargo theft, toll evasion) | Yunnan u-blox set (CC BY, one site, one attack day); Jammertest data raw I/Q or paywalled | weak: AGC/C/N0 rules, shipped by u-blox and Teltonika | attack data illegal to make | no |
| GNSS | Spoofing detection on the receiver / phone | high (aviation spoofing +193 % vs 2023, IATA [U]) | no licence-clean multi-receiver data | partly | no | no |
| GNSS | Jamming vs. blockage for trackers | high | as above | maybe | only clean data self-recordable | maybe (reviews disagree) |
| Aviation | ADS-B spoofing / interference per track | high | adsb.lol (ODbL) is open; OpenSky blocks Apache models | maybe | labels circular (NIC/NACp rules) | maybe, gap small (gpsjam, FR24, Stanford) |
| Maritime | **GNSS spoofing/interference visible in AIS** (circles, jumps, multi-vessel clusters) | high (Baltic, Gulf; >11,000 vessels per quarter, Windward [V via secondary]) | NOAA MarineCadastre (CC0, US), Kystverket open tier (NLOD 2.0), DMA (to confirm in writing) | yes for vessel-motion plausibility; events via multi-vessel clustering | yes: data at scale, false alarms per 1,000 vessel-days measurable on clean regions | **promising** |
| Maritime | Dark ships, identity fraud, shadow fleet | very high | needs satellite AIS, imagery, registries | partly | no; incumbents (Windward, Kpler, Lloyd's) and legal risk of false accusation | no |
| Maritime | NMEA 2000 IDS | niche product exists | none | repeats CAN IDS | no | no |
| Charging | Session/RFID fraud, meter plausibility | real losses (cloned RFID cards) | ACN-Data benign only, licence unclear; no fraud labels | yes (per-site baselines) | labels sit with operators | maybe |
| Charging | OCPP/ISO 15118 protocol attacks | real CVEs | CICEVSE2024 (no licence, saturated at 99.99 %), OCPP Zenodo (CC BY, emulated) | weak: TLS and patching | lab-to-field gap as in CAN | no |
| V2X | Misbehaviour detection | low deployment, standard leaves detection to rules | VeReMi (CC BY, simulated only) | weak | no real traces | no |
| Micromobility, rail | BLE, BMS, ERTMS | real research findings | none or CC BY-NC-ND | crypto, certification | no | no |

## Findings

- Most security problems in mobility are not ML problems: the fix is cryptography (UWB ranging, SecOC, TLS, signed firmware), hardware (ECU fingerprinting) or simple rules (AGC/C/N0 flags shipped in receivers).
- Where ML fits, the data sit with operators (fleets, charge-point operators, OEM security centres) or are simulated. The same pattern sank picket-forest.
- Attack data for radio problems (jamming, spoofing, relay) cannot be produced legally by a private person.
- One candidate meets all four criteria: **detecting GNSS spoofing and interference in AIS vessel tracks**.

## Candidate: GNSS interference and spoofing in AIS tracks ("open maritime gpsjam")

- **Problem**: GNSS jamming and spoofing in the Baltic, Black Sea and Gulf shows up in AIS as vessels jumping inland, circling or several unrelated vessels moving to the same false position. Users: coast guards, port authorities, insurers, journalists and NGOs (SkyTruth-style), researchers. Free aviation maps exist (gpsjam.org, Flightradar24); no maintained open maritime equivalent was found, and the only published open method (SeaSpoofFinder, arXiv 2602.16257) was withdrawn [V].
- **Data**: NOAA/BOEM MarineCadastre AIS, US waters, CC0 per data.gov [V]; Kystverket open AIS, NLOD 2.0, excludes small fishing and leisure craft [V]; Danish Maritime Authority AIS, conflicting statements on terms, written confirmation needed [V/U]. Years of data, millions of vessel-days.
- **Architecture**: a vessel-motion model learned on normal traffic (self-supervised: how plausible is the next report given the track, vessel type and area), plus event building across vessels (spatial-temporal clustering). Runs on CPU. Output: events and a daily grid, not per-vessel accusations.
- **Evaluation**: false alarms per 1,000 vessel-days on clean regions and periods not used in training (e.g. US waters); split by vessel (MMSI); recall on dated public incidents (Traficom and Swedish notices, SkyTruth cases). A rule baseline (land, impossible speed, multi-vessel clusters) is the bar; if the model does not beat it, kill.
- **Risks**: no independent ground truth for real spoofing, so precision on real events rests on physics rules and a few documented incidents; the model may not beat the rule baseline; data volume (CPU, storage); small-craft MMSIs can be personal data, so publish events and grids, not lists of small craft (DMA forbids re-identification).
- **Fit with the zoo**: mobility, open data, CPU model, a real gap; it is not an MCU model and not on-vehicle.

## Second tier (only with a new data source)

- Driver authentication against theft (one-class per vehicle), if KCID's licence allows training and publishing.
- EV charging session plausibility, if a charge-point operator shares data or ACN-Data's licence is clarified.
- ADS-B per-track spoofing vs. jamming on adsb.lol (ODbL), if labels independent of NIC/NACp can be found.

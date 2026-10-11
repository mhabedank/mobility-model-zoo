# 07 – Is picket-forest production ready? Problem, data, architecture (2026-10-09)

Owner question after the first full run of `can-ids-v1`: we publish only production-ready models. Before deciding, answer in order: (1) is the problem relevant, (2) do we have the right data, (3) is the architecture right. Evidence: the full run (`topics/security/reports/picket-forest/can-ids-v1/`), our own data checks below, and a web review (tags: [V] checked in the source, [U] snippet or secondary).

## Result of the full run (short)

- Frame-level attack-class F1 of picket-forest, median over four sets: 0.95 / 0.94 / 0.90 / 0.94 (known/unknown vehicle × known/unknown attack); best baseline on unknown vehicles 0.39.
- Alarm level: on unknown vehicles only 35 % / 7 % of attack episodes are detected within 10 false alarms per hour; controls without the CAN ID features do better there (0.64 / 0.42).
- ROAD (another vehicle, physically injected attacks): F1 0.05, AUROC 0.88.
- Research R10 outcome: kill (shuffled-label control), partial without that control.

## 1. Is the problem relevant?

- **Series vehicles: not reachable.** In-vehicle IDS runs on gateways and ECUs, is bought from Tier-1 security vendors through ISO/SAE 21434 programmes, integrated in AUTOSAR (IdsM) and configured from the OEM's communication matrix (cycle times, IDs, DLCs). UN R155 drives demand since July 2024 but no adoption path for a third-party open model exists [U] (PlaxidityX, ETAS CycurIDS, VicOne).
- **Real demand exists in aftermarket and fleet niches:**
  - CAN-injection car theft is real and growing: Toyota RAV4 CVE-2023-29389, exploited in the wild since 2022; about $10 hardware, kits sold up to €5000; Land Cruiser thefts in Japan 383 (2023) → about 670 (2024) [V]. The attack enters through the headlight harness while the car is parked [V] (Tindell 2023). PlaxidityX vDome sells an aftermarket device against exactly this (ECU fingerprinting, not ML) [V].
  - Boats: Digital Yacht NET Protect, NMEA 2000 intrusion detection [V]. Trucks (J1939): research and demos only (TruckSentry, VehicleSec'25, rule based) [V].
- **Install point matters.** On many recent cars the OBD port sits behind a gateway (FCA SGW 2018+, VW) and does not expose the internal buses [U]; an OBD device would not see a headlight-harness injection. A useful device taps the bus segment directly.
- **Conclusion.** The relevant problem is narrower than what picket-forest was built for: not "classify attack frames of any vehicle while driving", but "detect foreign frames on a known bus segment of one vehicle", with the parked-car theft case as the clearest user need. A detector there must reach false-alarm rates in the order of one per thousands of hours; per-frame FPR is the wrong yardstick (0.001 % on one 100 ms ID is already one false positive every 2.8 h, Meyer et al. 2024 [V]).

## 2. Do we have the right data?

Own checks on the frozen manifest and raw files:

| Fact | Value |
|---|---|
| Vehicles | 4 in can-train-and-test (three GM 2011–2016, one Subaru 2017), 1 in ROAD |
| Unique recording time | 24.7 h (219 unique captures; 62 captures reused across sets) |
| of which attack-free captures | 4.8 h (3.1 h of them ROAD) |
| Test time per split (denominator of false alarms per hour) | 0.7–2.5 h |
| Parked / sleep-mode theft scenario | not covered |

- **False alarms per hour cannot be measured at the needed level.** With about 1 h of test traffic, even zero false alarms only shows "fewer than 3 per hour" (95 % bound). A production claim of one per thousands of hours needs thousands of benign hours.
- **can-train-and-test timing is not a real bus.** All captures start at exactly 2023-01-01 00:00:00 UTC (rewritten). In attack captures the benign frames are 10–12 µs apart (median, already before the attack starts), below the physical minimum frame time at 500 kbit/s; in attack-free captures they are 240 µs apart. Injected frames are about 700 µs from their predecessor. The authors state that replay "inadvertently change[s] the timestamps" for DoS and fuzzing [V] (arXiv 2308.04972 §4.4).
- **This artefact does not explain picket-forest's scores.** Retraining without the two bus-gap features (`dt_bus_ms`, `bus_dt_ewma_ms`) keeps F1 at 0.65–0.98 on 15 of 16 cells; removing the per-ID timing features as well drops F1 to 0.00–0.82 (mostly below 0.2). The detection rests on per-ID timing: injected copies of an existing ID shorten its interval, a physically real signature of fabrication.
- **ROAD has no such artefact** (attack and benign gaps alike), and there picket-forest fails (F1 0.05).
- **Better data that exists:** commaCarSegments, raw CAN, 3,148 h, 230 vehicle platforms, MIT licence [V]. Benign only, so it measures false alarms per hour across many vehicles; attacks still come from can-train-and-test and ROAD.

Conclusion: the data are usable as attack test sets with known artefacts; they are not the right data to show production readiness (false alarms over many hours and vehicles) and contain nothing on the theft scenario.

## 3. Is the architecture right?

- picket-forest is in effect a learned per-ID timing detector trained across vehicles. It cannot know the normal cycle times of a vehicle it has never seen; it learns them from the four training vehicles. Hence the false alarms on unknown vehicles (5–9 per hour at the chosen rule, about three orders of magnitude above a production budget) and the collapse on ROAD.
- Production systems and the literature use the opposite order: the normal behaviour of the specific vehicle (ID set, cycle time per ID, DLC, counters) is the reference, from the communication matrix (OEM) or learned from benign traffic; rules and per-ID timing checks first, ML as a secondary scorer [U] (ETAS, AUTOSAR security sensors, Lazeski et al. 2026). Distribution-agnostic per-ID timing detectors beat distribution-based ones on ROAD [U] (Blevins et al. 2021).
- For an open device without the communication matrix this means: calibrate on the vehicle (benign-only learning of IDs and cycle times, separate driving and parked baselines), then detect deviations. This was planned as the 0.2.0 rule layer; the evidence says it is the core, not an add-on.

## Recommendation

1. Do not publish picket-forest 0.1.0. It is not production ready: false alarms on unknown vehicles and ROAD transfer fail, and the data cannot show the false-alarm level a user needs.
2. Keep what is reusable: benchmark `can-ids-v1` (with the relabelling finding), harness, release gate for tree models, C feature library, measurement path.
3. Reframe the task before building again: choose the target scenario (parked-car injection theft vs. driving-time monitoring for fleets), make "calibrate on the vehicle, then detect" the architecture, and measure false alarms per hour on commaCarSegments.

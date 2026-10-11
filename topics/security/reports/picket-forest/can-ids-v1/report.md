# can-ids-v1 evaluation

**Outcome (research R10): kill.** ctrl-shuffled F1 0.32 reaches half of picket-forest's (0.61) on set_01/known_vehicle_unknown_attack: leakage ctrl-shuffled F1 0.51 reaches half of picket-forest's (0.97) on set_02/known_vehicle_unknown_attack: leakage ctrl-shuffled AUROC 0.95 exceeds the label-free reference (0.83) by > 0.05 on set_02/unknown_vehicle_unknown_attack: leakage ctrl-shuffled F1 0.54 reaches half of picket-forest's (0.98) on set_04/known_vehicle_known_attack: leakage ctrl-shuffled F1 0.56 reaches half of picket-forest's (0.89) on set_04/known_vehicle_unknown_attack: leakage ctrl-shuffled AUROC 0.91 exceeds the label-free reference (0.64) by > 0.05 on set_04/unknown_vehicle_unknown_attack: leakage

Shuffled-label control: leakage is judged against the label-free reference `bl-isolation-forest` (AUROC margin 0.05) and at the validation operating point (F1 below 0.5 of picket-forest's). A forest on permuted labels ranks rare frames high and so acts as a novelty detector; the original rule "ctrl-shuffled attack-class AUROC at most 0.6 on every split (until 2026-10-09)" was amended after the first real-data run and is reported, not applied. Violations of the original rule: set_01/known_vehicle_known_attack: AUROC 0.89 > 0.6; set_01/known_vehicle_unknown_attack: AUROC 0.80 > 0.6; set_01/unknown_vehicle_unknown_attack: AUROC 0.83 > 0.6; set_02/known_vehicle_known_attack: AUROC 0.66 > 0.6; set_02/known_vehicle_unknown_attack: AUROC 0.95 > 0.6; set_02/unknown_vehicle_unknown_attack: AUROC 0.95 > 0.6; set_03/known_vehicle_known_attack: AUROC 0.69 > 0.6; set_03/known_vehicle_unknown_attack: AUROC 0.73 > 0.6; set_03/unknown_vehicle_unknown_attack: AUROC 0.72 > 0.6; set_04/known_vehicle_known_attack: AUROC 0.86 > 0.6; set_04/known_vehicle_unknown_attack: AUROC 0.87 > 0.6; set_04/unknown_vehicle_unknown_attack: AUROC 0.91 > 0.6.

Benchmark `can-ids-v1`, manifest `8abee6e0131ea103`, code `b32019067345`, 2026-10-09. Sets: set_01, set_02, set_03, set_04.

Reference: the attack labels of can-train-and-test (official splits) and the injection labels of ROAD. All metrics are attack-class metrics; nothing is support-weighted. Thresholds and alarm rules are chosen on validation captures, never on test captures.

## Headline: attack episodes detected at a false-alarm budget

Median over the sets (worst set in brackets). Episodes: attack frames separated by more than 1 s; an alarm up to 1 s after an episode still detects it. The alarm rule of each budget is chosen on validation captures; where its false-alarm rate on the test split exceeds the budget, the split counts 0 (the budget was not met).

| Detector | Split | ≤ 1 FA/h | ≤ 10 FA/h | F1 (attack) | AUROC | Default rule FA/h |
|---|---|---|---|---|---|---|
| `picket-forest` | known_vehicle_known_attack | 0.000 (0.000) | 0.844 (0.000) | 0.955 (0.883) | 0.998 (0.957) | 5.166 (12.875) |
| `picket-forest` | unknown_vehicle_known_attack | 0.000 (0.000) | 0.351 (0.000) | 0.937 (0.903) | 0.999 (0.984) | 6.321 (17.174) |
| `picket-forest` | known_vehicle_unknown_attack | 0.100 (0.000) | 0.100 (0.000) | 0.900 (0.609) | 0.998 (0.811) | 8.274 (59.118) |
| `picket-forest` | unknown_vehicle_unknown_attack | 0.000 (0.000) | 0.070 (0.000) | 0.941 (0.420) | 0.995 (0.961) | 5.523 (14.233) |
| `ctrl-id-lookup` | known_vehicle_known_attack | 0.037 (0.000) | 0.162 (0.000) | 0.328 (0.000) | 0.976 (0.521) | 0.000 (3322.510) |
| `ctrl-id-lookup` | unknown_vehicle_known_attack | 0.000 (0.000) | 0.000 (0.000) | 0.006 (0.000) | 0.495 (0.476) | 3122.029 (3487.710) |
| `ctrl-id-lookup` | known_vehicle_unknown_attack | 0.030 (0.000) | 0.030 (0.000) | 0.002 (0.000) | 0.665 (0.227) | 0.000 (2893.522) |
| `ctrl-id-lookup` | unknown_vehicle_unknown_attack | 0.000 (0.000) | 0.000 (0.000) | 0.021 (0.001) | 0.579 (0.496) | 2915.508 (3381.502) |
| `ctrl-timing-only` | known_vehicle_known_attack | 0.000 (0.000) | 0.844 (0.000) | 0.943 (0.793) | 0.991 (0.914) | 8.707 (24.719) |
| `ctrl-timing-only` | unknown_vehicle_known_attack | 0.000 (0.000) | 0.639 (0.000) | 0.880 (0.755) | 0.996 (0.950) | 3.778 (14.304) |
| `ctrl-timing-only` | known_vehicle_unknown_attack | 0.000 (0.000) | 0.177 (0.049) | 0.820 (0.656) | 0.976 (0.758) | 8.768 (19.502) |
| `ctrl-timing-only` | unknown_vehicle_unknown_attack | 0.000 (0.000) | 0.418 (0.000) | 0.676 (0.312) | 0.990 (0.841) | 6.453 (22.535) |
| `ctrl-forest-with-id` | known_vehicle_known_attack | 0.344 (0.000) | 0.875 (0.113) | 0.948 (0.880) | 0.999 (0.997) | 5.836 (15.450) |
| `ctrl-forest-with-id` | unknown_vehicle_known_attack | 0.000 (0.000) | 0.481 (0.000) | 0.909 (0.704) | 0.998 (0.968) | 3.937 (17.174) |
| `ctrl-forest-with-id` | known_vehicle_unknown_attack | 0.093 (0.000) | 0.107 (0.000) | 0.777 (0.597) | 0.998 (0.849) | 8.765 (41.686) |
| `ctrl-forest-with-id` | unknown_vehicle_unknown_attack | 0.000 (0.000) | 0.806 (0.155) | 0.748 (0.417) | 0.994 (0.964) | 5.478 (14.233) |
| `ctrl-shuffled` | known_vehicle_known_attack | 0.000 (0.000) | 0.000 (0.000) | 0.259 (0.110) | 0.776 (0.659) | 843.619 (3022.064) |
| `ctrl-shuffled` | unknown_vehicle_known_attack | 0.000 (0.000) | 0.000 (0.000) | 0.033 (0.023) | 0.460 (0.427) | 3234.704 (3425.196) |
| `ctrl-shuffled` | known_vehicle_unknown_attack | 0.000 (0.000) | 0.000 (0.000) | 0.413 (0.076) | 0.836 (0.732) | 1033.269 (2657.877) |
| `ctrl-shuffled` | unknown_vehicle_unknown_attack | 0.000 (0.000) | 0.000 (0.000) | 0.094 (0.063) | 0.871 (0.718) | 3100.243 (3365.227) |
| `bl-mean-interval` | known_vehicle_known_attack | 0.000 (0.000) | 0.465 (0.000) | 0.953 (0.911) | 0.999 (0.994) | 8.889 (18.540) |
| `bl-mean-interval` | unknown_vehicle_known_attack | 0.000 (0.000) | 0.000 (0.000) | 0.027 (0.005) | 0.510 (0.493) | 3250.449 (3487.710) |
| `bl-mean-interval` | known_vehicle_unknown_attack | 0.107 (0.000) | 0.183 (0.000) | 0.939 (0.890) | 0.998 (0.996) | 12.793 (17.138) |
| `bl-mean-interval` | unknown_vehicle_unknown_attack | 0.000 (0.000) | 0.000 (0.000) | 0.021 (0.007) | 0.558 (0.496) | 3195.216 (3381.502) |
| `bl-binning` | known_vehicle_known_attack | 0.000 (0.000) | 0.000 (0.000) | 0.927 (0.729) | 0.998 (0.990) | 121.539 (1354.756) |
| `bl-binning` | unknown_vehicle_known_attack | 0.000 (0.000) | 0.000 (0.000) | 0.026 (0.005) | 0.509 (0.498) | 3250.449 (3487.710) |
| `bl-binning` | known_vehicle_unknown_attack | 0.000 (0.000) | 0.000 (0.000) | 0.877 (0.585) | 0.997 (0.993) | 103.420 (1333.357) |
| `bl-binning` | unknown_vehicle_unknown_attack | 0.000 (0.000) | 0.000 (0.000) | 0.021 (0.007) | 0.510 (0.502) | 3195.473 (3381.502) |
| `bl-can-logic` | known_vehicle_known_attack | 0.000 (0.000) | 0.891 (0.727) | 0.722 (0.663) | 0.786 (0.748) | 0.000 (1.846) |
| `bl-can-logic` | unknown_vehicle_known_attack | 0.000 (0.000) | 0.000 (0.000) | 0.028 (0.005) | 0.521 (0.494) | 3250.449 (3487.710) |
| `bl-can-logic` | known_vehicle_unknown_attack | 0.380 (0.000) | 0.880 (0.049) | 0.776 (0.317) | 0.846 (0.597) | 0.983 (1.773) |
| `bl-can-logic` | unknown_vehicle_unknown_attack | 0.000 (0.000) | 0.000 (0.000) | 0.021 (0.006) | 0.536 (0.502) | 3195.216 (3381.502) |
| `bl-isolation-forest` | known_vehicle_known_attack | 0.000 (0.000) | 0.000 (0.000) | 0.209 (0.050) | 0.894 (0.860) | 1062.780 (3292.864) |
| `bl-isolation-forest` | unknown_vehicle_known_attack | 0.000 (0.000) | 0.000 (0.000) | 0.392 (0.036) | 0.824 (0.635) | 1014.407 (3255.010) |
| `bl-isolation-forest` | known_vehicle_unknown_attack | 0.000 (0.000) | 0.000 (0.000) | 0.063 (0.020) | 0.909 (0.892) | 901.241 (2952.867) |
| `bl-isolation-forest` | unknown_vehicle_unknown_attack | 0.000 (0.000) | 0.000 (0.000) | 0.026 (0.000) | 0.841 (0.638) | 917.613 (3304.157) |
| `bl-orig-dt` | known_vehicle_known_attack | 0.091 (0.000) | 0.136 (0.000) | 0.549 (0.077) | 0.820 (0.520) | 355.095 (505.717) |
| `bl-orig-dt` | unknown_vehicle_known_attack | 0.000 (0.000) | 0.000 (0.000) | 0.005 (0.002) | 0.502 (0.467) | 3118.564 (3487.710) |
| `bl-orig-dt` | known_vehicle_unknown_attack | 0.000 (0.000) | 0.000 (0.000) | 0.036 (0.001) | 0.510 (0.497) | 184.517 (222.881) |
| `bl-orig-dt` | unknown_vehicle_unknown_attack | 0.000 (0.000) | 0.000 (0.000) | 0.022 (0.011) | 0.479 (0.425) | 2914.647 (3382.754) |
| `bl-orig-rf` | known_vehicle_known_attack | 0.000 (0.000) | 0.035 (0.000) | 0.666 (0.208) | 0.921 (0.562) | 70.014 (89.520) |
| `bl-orig-rf` | unknown_vehicle_known_attack | 0.000 (0.000) | 0.000 (0.000) | 0.008 (0.001) | 0.567 (0.423) | 3236.062 (3471.223) |
| `bl-orig-rf` | known_vehicle_unknown_attack | 0.000 (0.000) | 0.020 (0.000) | 0.046 (0.001) | 0.571 (0.483) | 49.665 (120.768) |
| `bl-orig-rf` | unknown_vehicle_unknown_attack | 0.000 (0.000) | 0.000 (0.000) | 0.015 (0.003) | 0.446 (0.356) | 3133.696 (3341.440) |
| `bl-orig-et` | known_vehicle_known_attack | 0.136 (0.000) | 0.157 (0.000) | 0.534 (0.077) | 0.923 (0.560) | 38.974 (818.797) |
| `bl-orig-et` | unknown_vehicle_known_attack | 0.000 (0.000) | 0.000 (0.000) | 0.007 (0.002) | 0.580 (0.399) | 2505.143 (3488.397) |
| `bl-orig-et` | known_vehicle_unknown_attack | 0.030 (0.000) | 0.030 (0.000) | 0.037 (0.002) | 0.626 (0.477) | 14.556 (595.003) |
| `bl-orig-et` | unknown_vehicle_unknown_attack | 0.000 (0.000) | 0.000 (0.000) | 0.019 (0.009) | 0.408 (0.159) | 2471.800 (3066.190) |
| `bl-orig-gnb` | known_vehicle_known_attack | 0.000 (0.000) | 0.014 (0.000) | 0.011 (0.000) | 0.684 (0.460) | 1552.539 (3310.404) |
| `bl-orig-gnb` | unknown_vehicle_known_attack | 0.000 (0.000) | 0.000 (0.000) | 0.036 (0.000) | 0.718 (0.578) | 1429.364 (3457.484) |
| `bl-orig-gnb` | known_vehicle_unknown_attack | 0.000 (0.000) | 0.000 (0.000) | 0.001 (0.000) | 0.359 (0.033) | 1574.540 (2921.799) |
| `bl-orig-gnb` | unknown_vehicle_unknown_attack | 0.000 (0.000) | 0.000 (0.000) | 0.000 (0.000) | 0.333 (0.115) | 1685.452 (3022.474) |
| `bl-orig-logreg` | known_vehicle_known_attack | 0.000 (0.000) | 0.014 (0.000) | 0.077 (0.000) | 0.528 (0.386) | 3.014 (3336.817) |
| `bl-orig-logreg` | unknown_vehicle_known_attack | 0.000 (0.000) | 0.000 (0.000) | 0.088 (0.000) | 0.672 (0.568) | 1476.639 (3304.291) |
| `bl-orig-logreg` | known_vehicle_unknown_attack | 0.000 (0.000) | 0.000 (0.000) | 0.001 (0.000) | 0.433 (0.347) | 2.274 (2910.214) |
| `bl-orig-logreg` | unknown_vehicle_unknown_attack | 0.000 (0.000) | 0.000 (0.000) | 0.007 (0.000) | 0.347 (0.202) | 1469.735 (2878.111) |
| `bl-orig-mlp` | known_vehicle_known_attack | 0.000 (0.000) | 0.000 (0.000) | 0.279 (0.002) | 0.715 (0.580) | 394.716 (1396.577) |
| `bl-orig-mlp` | unknown_vehicle_known_attack | 0.000 (0.000) | 0.000 (0.000) | 0.016 (0.000) | 0.772 (0.698) | 2154.101 (3487.710) |
| `bl-orig-mlp` | known_vehicle_unknown_attack | 0.000 (0.000) | 0.000 (0.000) | 0.022 (0.003) | 0.495 (0.165) | 401.325 (1284.264) |
| `bl-orig-mlp` | unknown_vehicle_unknown_attack | 0.000 (0.000) | 0.000 (0.000) | 0.012 (0.001) | 0.577 (0.375) | 2056.125 (3065.173) |

## Quality against cost

Quality: episodes detected at ≤ 10 false alarms per hour, unknown vehicle and known attacks, median over sets. Size: pickled model; host time: Python scoring per frame (not device latency). Pareto-optimal detectors are marked.

| Detector | Quality | Size (KB) | Host µs/frame | Pareto |
|---|---|---|---|---|
| `ctrl-timing-only` | 0.639 | 182.1 | 0.30 | yes |
| `ctrl-forest-with-id` | 0.481 | 313.4 | 0.55 |  |
| `picket-forest` | 0.351 | 404.3 | 0.55 |  |
| `ctrl-id-lookup` | 0.000 | 22.1 | 0.01 |  |
| `ctrl-shuffled` | 0.000 | 6786.5 | 0.61 |  |
| `bl-mean-interval` | 0.000 | 0.8 | 0.02 | yes |
| `bl-binning` | 0.000 | 24.5 | 0.03 |  |
| `bl-can-logic` | 0.000 | 1.0 | 0.02 |  |
| `bl-isolation-forest` | 0.000 | 908.7 | 1.65 |  |
| `bl-orig-dt` | 0.000 | 54.1 | 0.02 |  |
| `bl-orig-rf` | 0.000 | 7139.9 | 0.25 |  |
| `bl-orig-et` | 0.000 | 25295.1 | 0.32 |  |
| `bl-orig-gnb` | 0.000 | 0.9 | 0.05 |  |
| `bl-orig-logreg` | 0.000 | 1.4 | 0.02 |  |
| `bl-orig-mlp` | 0.000 | 46.1 | 0.20 |  |

## Deterministic check: C versus Python

picket-forest's C chain (host build, `-ffp-contract=off`) against the Python reference on every test frame.

| Set | Frames | Mismatches |
|---|---|---|
| set_01 | 34006417 | 0 |
| set_02 | 38605942 | 0 |
| set_03 | 31773995 | 0 |
| set_04 | 36943212 | 0 |

## ROAD (a fifth vehicle from another dataset)

Model: release model (train_01 of all four sets). Masquerade and accelerator captures are out of scope and reported separately.

| Part | Captures | F1 (attack) | ≤ 10 FA/h detection | Default rule FA/h |
|---|---|---|---|---|
| in_scope | 9 | 0.054 | 0.000 | 3400.933 |
| out_of_scope | 17 | 0.015 | 0.000 | 2458.735 |

## Per attack family (picket-forest, attack-class recall, median over sets)

| Split | Family | Recall |
|---|---|---|
| known_vehicle_known_attack | DoS | 0.956 |
| known_vehicle_known_attack | double | 0.480 |
| known_vehicle_known_attack | force-neutral | 0.872 |
| known_vehicle_known_attack | fuzzing | 0.962 |
| known_vehicle_known_attack | interval | 1.000 |
| known_vehicle_known_attack | rpm | 0.935 |
| known_vehicle_known_attack | rpm-accessory | 0.939 |
| known_vehicle_known_attack | speed | 0.984 |
| known_vehicle_known_attack | speed-accessory | 0.330 |
| known_vehicle_known_attack | standstill | 0.613 |
| known_vehicle_known_attack | systematic | 0.989 |
| known_vehicle_known_attack | triple | 0.426 |
| known_vehicle_unknown_attack | DoS | 0.985 |
| known_vehicle_unknown_attack | double | 0.557 |
| known_vehicle_unknown_attack | force-neutral | 0.558 |
| known_vehicle_unknown_attack | fuzzing | 0.455 |
| known_vehicle_unknown_attack | interval | 0.927 |
| known_vehicle_unknown_attack | rpm | 0.787 |
| known_vehicle_unknown_attack | rpm-accessory | 0.431 |
| known_vehicle_unknown_attack | speed | 0.514 |
| known_vehicle_unknown_attack | speed-accessory | 0.972 |
| known_vehicle_unknown_attack | standstill | 0.776 |
| known_vehicle_unknown_attack | systematic | 0.010 |
| known_vehicle_unknown_attack | triple | 0.446 |
| unknown_vehicle_known_attack | DoS | 0.967 |
| unknown_vehicle_known_attack | double | 0.750 |
| unknown_vehicle_known_attack | force-neutral | 0.486 |
| unknown_vehicle_known_attack | fuzzing | 0.919 |
| unknown_vehicle_known_attack | interval | 0.926 |
| unknown_vehicle_known_attack | rpm | 0.380 |
| unknown_vehicle_known_attack | rpm-accessory | 0.616 |
| unknown_vehicle_known_attack | speed | 0.535 |
| unknown_vehicle_known_attack | speed-accessory | 0.033 |
| unknown_vehicle_known_attack | standstill | 0.400 |
| unknown_vehicle_known_attack | systematic | 0.994 |
| unknown_vehicle_known_attack | triple | 0.598 |
| unknown_vehicle_unknown_attack | DoS | 0.992 |
| unknown_vehicle_unknown_attack | double | 0.563 |
| unknown_vehicle_unknown_attack | force-neutral | 0.466 |
| unknown_vehicle_unknown_attack | fuzzing | 0.423 |
| unknown_vehicle_unknown_attack | interval | 1.000 |
| unknown_vehicle_unknown_attack | rpm | 0.933 |
| unknown_vehicle_unknown_attack | rpm-accessory | 0.932 |
| unknown_vehicle_unknown_attack | speed | 0.974 |
| unknown_vehicle_unknown_attack | speed-accessory | 0.335 |
| unknown_vehicle_unknown_attack | standstill | 0.948 |
| unknown_vehicle_unknown_attack | systematic | 0.390 |
| unknown_vehicle_unknown_attack | triple | 0.553 |

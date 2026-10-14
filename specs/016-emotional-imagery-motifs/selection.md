# Image selection: series SIEBDRUCK

Owner picks of 2026-10-13/14 from the Qwen-Image-2512 renders (`~/zoo-imagery/out6/` on the Spark). Each entry is the full recipe; `zoo site images add` imports from the generator manifest.

| Placement | Pick | Record id | Source file (Spark) | Seed | Outcome |
|---|---|---|---|---|---|
| `start-hero` | Q7 | `hero-train-dawn` | `out6/qwen/start-hero-2-1022.png` | 1022 | Q6 (seed 1021) was rejected by I4: the distant silhouette on the platform reads as a 22 px face; the reserve seed passed |
| `topic:productdev` | Q14 | `topic-productdev-interior` | `out6/qwen/topic-productdev-1-1011.png` | 1011 | the owner's pick Q53 moved to security (see below); the interior was the series' subject for this topic and passed |
| `topic:security` | Q53 | `topic-security-workshop` | `out6/qwen/topic-security-2-1020.png` | 1020 | the dashboard picks Q50 and Q52 were rejected by I4: OCR reads the dial digits; the workshop subject is the topic's own and passed |
| `topic:condition-monitoring` | Q46 | `topic-condmon-wheelset` | `out6/qwen-fix/topic-condition-monitoring-2-1021.png` | 1021 | passed |
| `model:scout-large` | Q30 | `model-scout-large-window` | `out6/qwen/model-scout-large-1-1011.png` | 1011 | passed |
| `model:picket-forest` | Q26 | `model-picket-forest-bench` | `out6/qwen-fix/model-picket-forest-1-1011.png` | 1011 | passed |

Imported on 2026-10-14 with `zoo site images add` (container image `sha256:373249621b54580b0c38d284e4ddfe433d733800569e5d253b01792ad7c75bcc`; the renders predate the generator's move into the repository, so `generator.commit` is `unversioned`). The records are the source of truth from here on: `zoo/site/images/<id>/image.yaml`.

Model: `Qwen/Qwen-Image-2512` (Apache-2.0), revision as in the manifest, `true_cfg_scale` 4.0, 50 steps, negative prompt from the series file. Rendered on the DGX Spark in the `zoo-flux` container.

Reserve seeds (imported if the first pick fails I4 at import): `start-hero` Q7 `out6/qwen/start-hero-2-1022.png`; `topic:productdev` Q14 `out6/qwen/topic-productdev-1-1011.png`; `topic:security` Q52 `out6/qwen/topic-security-1-1013.png`; `topic:condition-monitoring` Q48 `out6/qwen-fix/topic-condition-monitoring-2-1023.png`; `model:scout-large` Q32 `out6/qwen/model-scout-large-1-1013.png`; `model:picket-forest` Q28 `out6/qwen-fix/model-picket-forest-1-1013.png`.

Notes:
- `topic:productdev` uses the workshop-car subject (owner's pick Q53), not the tram interior.
- `topic:condition-monitoring` and `model:picket-forest` come from the corrected subjects (wheelset; diagnostic plug), see `series-siebdruck.yaml`.
- Reserve seeds for every subject stay on the Spark under `out6/`.

## Recipes

```yaml
- placement: start-hero
  pick: Q6
  spark_path: ~/zoo-imagery/out6/qwen/start-hero-2-1021.png
  model: Qwen/Qwen-Image-2512
  revision: 25468b98e3276ca6700de15c6628e51b7de54a26
  prompt: an orange-yellow regional train leaving a small station at dawn, empty platform, mist over flat fields, 1970s modernist
    travel poster illustration, flat colour fields with crisp edges, screen print texture, clean geometric forms, calm ordered
    composition with long diagonals, soft gradient sky in pale mint and warm cream, deep navy shadows and ground, the main
    vehicle or machine painted in a warm orange-yellow accent colour, everything else only navy, mint and cream, early morning
    light as graphic shapes, quietly futurist and optimistic, West German graphic design of the seventies, restrained, no
    text, no lettering, no logos, no faces, people only as small simple silhouettes
  seed: 1021
  steps: 50
  guidance: 4.0
  width: 1344
  height: 768
- placement: topic:productdev
  pick: Q53
  spark_path: ~/zoo-imagery/out6/qwen/topic-security-2-1020.png
  model: Qwen/Qwen-Image-2512
  revision: 25468b98e3276ca6700de15c6628e51b7de54a26
  prompt: a clean vehicle workshop bay at morning, an orange-yellow car with open hood, wiring harness and diagnostic cable,
    tall windows, 1970s modernist travel poster illustration, flat colour fields with crisp edges, screen print texture, clean
    geometric forms, calm ordered composition with long diagonals, soft gradient sky in pale mint and warm cream, deep navy
    shadows and ground, the main vehicle or machine painted in a warm orange-yellow accent colour, everything else only navy,
    mint and cream, early morning light as graphic shapes, quietly futurist and optimistic, West German graphic design of
    the seventies, restrained, no text, no lettering, no logos, no faces, people only as small simple silhouettes
  seed: 1020
  steps: 50
  guidance: 4.0
  width: 1200
  height: 800
- placement: topic:security
  pick: Q50
  spark_path: ~/zoo-imagery/out6/qwen/topic-security-1-1011.png
  model: Qwen/Qwen-Image-2512
  revision: 25468b98e3276ca6700de15c6628e51b7de54a26
  prompt: a car dashboard and windshield at sunrise on an open road, round instruments with orange-yellow needles, road ahead
    empty, 1970s modernist travel poster illustration, flat colour fields with crisp edges, screen print texture, clean geometric
    forms, calm ordered composition with long diagonals, soft gradient sky in pale mint and warm cream, deep navy shadows
    and ground, the main vehicle or machine painted in a warm orange-yellow accent colour, everything else only navy, mint
    and cream, early morning light as graphic shapes, quietly futurist and optimistic, West German graphic design of the seventies,
    restrained, no text, no lettering, no logos, no faces, people only as small simple silhouettes
  seed: 1011
  steps: 50
  guidance: 4.0
  width: 1200
  height: 800
- placement: topic:condition-monitoring
  pick: Q46
  spark_path: ~/zoo-imagery/out6/qwen-fix/topic-condition-monitoring-2-1021.png
  model: Qwen/Qwen-Image-2512
  revision: 25468b98e3276ca6700de15c6628e51b7de54a26
  prompt: an orange-yellow railway wheelset, two wheels on one axle, resting on steel stands in a bright maintenance hall,
    a small figure from behind with a tablet, 1970s modernist travel poster illustration, flat colour fields with crisp edges,
    screen print texture, clean geometric forms, calm ordered composition with long diagonals, soft gradient sky in pale mint
    and warm cream, deep navy shadows and ground, the main vehicle or machine painted in a warm orange-yellow accent colour,
    everything else only navy, mint and cream, early morning light as graphic shapes, quietly futurist and optimistic, West
    German graphic design of the seventies, restrained, no text, no lettering, no logos, no faces, people only as small simple
    silhouettes
  seed: 1021
  steps: 50
  guidance: 4.0
  width: 1200
  height: 800
- placement: model:scout-large
  pick: Q30
  spark_path: ~/zoo-imagery/out6/qwen/model-scout-large-1-1011.png
  model: Qwen/Qwen-Image-2512
  revision: 25468b98e3276ca6700de15c6628e51b7de54a26
  prompt: a notebook and pen on a train table by a sunlit window, an orange-yellow train passing outside, landscape in soft
    bands, 1970s modernist travel poster illustration, flat colour fields with crisp edges, screen print texture, clean geometric
    forms, calm ordered composition with long diagonals, soft gradient sky in pale mint and warm cream, deep navy shadows
    and ground, the main vehicle or machine painted in a warm orange-yellow accent colour, everything else only navy, mint
    and cream, early morning light as graphic shapes, quietly futurist and optimistic, West German graphic design of the seventies,
    restrained, no text, no lettering, no logos, no faces, people only as small simple silhouettes
  seed: 1011
  steps: 50
  guidance: 4.0
  width: 1200
  height: 800
- placement: model:picket-forest
  pick: Q26
  spark_path: ~/zoo-imagery/out6/qwen-fix/model-picket-forest-1-1011.png
  model: Qwen/Qwen-Image-2512
  revision: 25468b98e3276ca6700de15c6628e51b7de54a26
  prompt: a small green circuit board on a workbench by a window, an orange-yellow automotive diagnostic plug and a thin wiring
    harness connected to it, an oscilloscope showing a square wave trace, 1970s modernist travel poster illustration, flat
    colour fields with crisp edges, screen print texture, clean geometric forms, calm ordered composition with long diagonals,
    soft gradient sky in pale mint and warm cream, deep navy shadows and ground, the main vehicle or machine painted in a
    warm orange-yellow accent colour, everything else only navy, mint and cream, early morning light as graphic shapes, quietly
    futurist and optimistic, West German graphic design of the seventies, restrained, no text, no lettering, no logos, no
    faces, people only as small simple silhouettes
  seed: 1011
  steps: 50
  guidance: 4.0
  width: 1200
  height: 800
```

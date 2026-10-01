# Mini corpus fixture

Five chunks with mocked answers from two reference "models" (`mock-a`, `mock-b`), one baseline (`mock-small`) and two teacher candidates (`mock-teacher-x`, a copy of `mock-small`; `mock-teacher-y`, a copy of `mock-a` with one near-miss quote in ch-001, "pendel" for "pendle"). `mock-ensemble` is their offline ensemble (`pilot ensemble`, rule in `decision-criteria.yaml`). `pilot.yaml` sets `test_fixture: true`, so the mock chain may freeze a `test_only` benchmark. The chunk store lives in `store/` (not `data/`, which is gitignored).

## Built-in cases

| Chunk | Case |
|-------|------|
| ch-001 | one fully agreed item (bus); one kind disagreement on the same span (job vs pain) |
| ch-002 | evidence-type disagreement of distance 2 (anecdote vs observation); one item only mock-a has; one fabricated quote from mock-b |
| ch-003 | irrelevant near-miss (classic car hobby); both references return an empty result |
| ch-004 | thread reply with parent context (two ranges); overlapping but different quote spans (IoU 33/68 ≈ 0.49) |
| ch-005 | measurement-level item (63%); observation-level item |

## Hand computation (references)

- Relevance: 5 of 5 agree (4 true, 1 false), so κ = 1.
- Items: mock-a has 7 valid, mock-b has 6 valid (+1 invalid quote), and 6 pairs match. F1 = 12/13 = 0.923.
- Kind on 6 pairs: A = pain, job, pain, gain, pain, job; B = pain, pain, pain, gain, pain, job. p_o = 5/6 and p_e = 15/36, so κ = 15/21 = 0.714.
- Evidence ranks: A = [1,2,1,1,4,3], B = [1,2,3,1,4,3]. Quadratic: Σw·O = 4 and Σw·E = 16, so κ_w = 0.75. Linear: Σw·O = 2 and Σw·E = 46/6, so κ_w = 0.739.
- Actor type and scope are identical on all pairs, so κ = 1.
- Composite = mean(1, 0.923, 0.714, 1, 0.75, 1) = 0.898.

## Hand computation (mock-small vs consensus)

- Relevance: labels (model/consensus) are T/T, T/T, T/F, invalid/T, T/T. p_o = 0.6 and p_e = 0.64, so κ = −0.111.
- Items: TP = 3 (bus, charger, parking). The trip-planning item matches a contested-existence item, so it is neutral. FP = 0 and FN = 3, so F1 = 6/9.
- Kind, actor type and scope agree on all scored units, so κ = 1.
- Evidence: the charger item is neutral (contested). Units are (1,1) and (3,4), so the quadratic κ = 1 − 1/7 = 0.857.
- Composite = 0.735. The frontier composite on consensus units is 1.0, so ratio a = 0.735 and ratio b = 0.735 / 0.898 = 0.819.

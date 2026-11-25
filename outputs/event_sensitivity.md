# Sensitivity to one or two recurrence classifications

This uses the 365-day recurrence analysis of fictional ventral hernia repairs. Each hypothetical change flips one observed binary outcome. All patients, preoperative strata and pooled standardization weights stay fixed. The table gives the lowest and highest attainable adjusted MESH-B minus MESH-A differences at each number of changes.

| Changed cases | Hypothetical records (recurrence 0/1) | MESH-A events / cases | MESH-B events / cases | Adjusted difference | Shift from baseline |
|---|---|---:|---:|---:|---:|
| 0 | Recorded outcomes | 8/52 | 10/48 | -7.0 pp | +0.0 pp |
| 1, lowest | S045 (0→1) | 9/52 | 10/48 | -12.0 pp | -5.0 pp |
| 1, highest | S054 (0→1) | 8/52 | 11/48 | -0.6 pp | +6.3 pp |
| 2, lowest | S045 (0→1), S047 (0→1) | 10/52 | 10/48 | -17.0 pp | -10.0 pp |
| 2, highest | S054 (0→1), S056 (0→1) | 8/52 | 12/48 | +5.7 pp | +12.7 pp |

The case IDs identify one way to reach each extreme. When effects tie, the first IDs in sort order are shown. These ranges measure sensitivity to record classification. The [bootstrap intervals](report.md#recurrence-through-day-365) address sampling uncertainty.

Reproduce from the repository root with `python3 -m examples.event_sensitivity`.

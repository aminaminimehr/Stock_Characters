# Imperfect Match Notes

Variables with Pearson correlation below 0.99 vs Green SAS benchmark.

| variable   |   pearson |   paired_rows |   coverage_diff |   median_abs_diff |
|:-----------|----------:|--------------:|----------------:|------------------:|
| i          |       nan |         36943 |               0 |                 0 |
| j          |       nan |         36943 |               0 |                 0 |
| orgcap     |       nan |             0 |               0 |               nan |

## Common causes

- WRDS data revisions vs frozen Green SAS output
- IBES-only paths (see ibes_exclusion_report.md)
- SAS vs Python numerical differences (std across lags, proc reg, intnx)
- Exchange history construction from crsp.mseall
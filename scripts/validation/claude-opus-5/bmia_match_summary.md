# bm_ia cross-sectional match: panel vs GKX datashare

- Panel: `D:\Asset Pricing Researh Project With Dr. Guo and Dr. Yichen\Creating_the_non_matching_characters_Amin\Stock_Characters\outputs\panels\bm_bmia_panel.csv`
- Datashare: `D:\Asset Pricing Researh Project With Dr. Guo and Dr. Yichen\Creating_the_non_matching_characters_Amin\Stock_Characters\Supplementary_assistive_files\datashare.csv`
- Comparison window: datashare months **195701–202112**
- Month key: datashare `DATE // 100`; panel `signal_yyyymm` vs `target_yyyymm`
- Minimum paired obs per month for Spearman: **50**

## Required metrics (best alignment)

- Characteristic: **bm_ia**
- Best month align: **target_yyyymm**
- Median monthly Spearman (cross-sectional): **0.9309**
- Mean monthly Spearman: **0.9034**
- Pooled Spearman: **0.9118**
- Sample N (panel / ours): **3221514.0000**
- Sample N (datashare / GKX): **3042589.0000**
- Paired N (inner join, non-null both): **2893887.0000**
- Unique permnos (panel): **24771.0000**
- Unique permnos (datashare): **23489.0000**
- Unique permnos (both): **23109.0000**
- Exact match |Δ|≤1e-4: **0.26%**
- Round-4 match: **0.22%**

## Both alignments

| align | median ρ | mean ρ | pooled ρ | paired N | panel N | ds N | permno panel | permno ds | permno both |
|-------|---------:|-------:|---------:|---------:|--------:|-----:|-------------:|----------:|------------:|
| `signal_yyyymm` | 0.9254 | 0.8966 | 0.9060 | 2,896,930 | 3,225,823 | 3,042,589 | 24,771 | 23,489 | 23,123 |
| `target_yyyymm` | 0.9309 | 0.9034 | 0.9118 | 2,893,887 | 3,221,514 | 3,042,589 | 24,771 | 23,489 | 23,109 |

## Key overlap (best alignment)

- Keys in both: **2893887.0000**
- Datashare-only keys: **148702.0000**
- Panel-only keys: **327627.0000**
- Duplicate keys — panel: **0.0000**, datashare: **0.0000**, merged: **0.0000**

## Decade breakdown (best alignment)

| decade | months | median ρ | mean ρ | mean paired obs |
|-------:|-------:|---------:|-------:|----------------:|
| 1960s | 78 | 0.8314 | 0.8722 | 779.5 |
| 1970s | 120 | 0.9613 | 0.9512 | 2838.1 |
| 1980s | 120 | 0.9541 | 0.9401 | 4337.5 |
| 1990s | 120 | 0.8541 | 0.8668 | 5892.6 |
| 2000s | 120 | 0.8430 | 0.8495 | 5480.2 |
| 2010s | 120 | 0.9340 | 0.9301 | 4330.2 |
| 2020s | 24 | 0.9021 | 0.9023 | 3646.3 |

## Note

Prior repo work documents a realistic bm_ia ceiling around 0.83–0.85 median monthly Spearman due to construction-SIC vintage residuals.

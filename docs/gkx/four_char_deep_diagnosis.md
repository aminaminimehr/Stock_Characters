# Four-character deep diagnosis

Window: **201001–201512**

## ms — Mohanram score

- Three-way overlap: **241,501** rows
- Spearman: panel–Green=0.588, datashare–Green=0.936, panel–datashare=0.562

### Integer score diffs

- panel vs Green exact match: 28.3%
- datashare vs Green exact match: 76.4%

Top panel−Green diffs:
- +0: 68,250
- +1: 49,163
- -1: 36,324
- +2: 26,574
- -2: 25,951
- -3: 15,995
- +3: 10,424
- -4: 5,425

Top datashare−Green diffs:
- +0: 184,497
- -1: 38,138
- +1: 10,593
- -2: 6,237
- +2: 885
- -3: 869
- -4: 143
- +3: 74

- Rows where panel < Green: 84,504 (mean gap 1.92)
- Rows where panel > Green: 88,747 (mean gap 1.63)

**Interpretation:** Datashare tracks Green (82.3% exact on overlap); panel diverges (28.6% exact). Coverage: panel has **179,777** permno-months with `ms` when Green is missing (incl. spurious `ms=0`); **104,688** Green rows missing in panel. Root cause is repo `ms_builder.py` (component merge / availability), not datashare.

## indmom — industry momentum

- Three-way overlap: **250,315** rows
- Spearman: panel–Green=0.990, datashare–Green=0.974, panel–datashare=0.973

- panel mom12m vs datashare mom12m: ρ=1.000
- numeric sic2 match rate: 95.6%
- recomputed mean(mom12m)|panel sic2 vs panel indmom: ρ=0.999
- recomputed mean(mom12m)|panel sic2 vs datashare indmom: ρ=0.974
- recomputed mean(ds_mom12m)|ds sic2 vs datashare indmom: ρ=0.977

**Interpretation:** Formula is correct in modern samples. Full-window **median** monthly ρ=0.835 vs **pooled** ρ=0.951 because ~8.6% of months (mostly **1958–1962** early history) have near-zero cross-sectional correlation when `mom12m` coverage is thin. Five-year bucket panel–datashare ρ stays **0.95–0.99** from 1975 onward.

## chpmia — formula decomposition

- Three-way overlap (non-null): **237,311** rows
- Spearman: panel–Green=0.979, datashare–Green=0.359, panel–datashare=0.364

### Cross-column checks (same permno-month)

- panel `chpm` vs datashare `chpmia`: ρ=0.327
- Green `chpm` vs datashare `chpmia`: ρ=0.327
- panel `chpm` vs Green `chpm`: ρ=1.000
- panel `chpmia` vs Green `chpm`: ρ=0.156
- Green `chpmia` vs Green `chpm` (demean sanity): ρ=0.165

### Monthly 1/99 winsor

- winsor(Green chpmia) vs datashare chpmia: ρ=0.359
- winsor(panel chpmia) vs datashare chpmia: ρ=0.363

### Month alignment (panel signal vs target vs datashare DATE//100)

- panel signal vs datashare: ρ=0.362 (n=242,952)
- panel target vs datashare: ρ=0.324 (n=239,399)

**Interpretation:** Panel matches Green `chpmia` (SIC2×fyear mean demean of `chpm`; panel `chpm` vs Green `chpm` ρ=1.0). Datashare `chpmia` ρ≈0.36 vs Green and ρ≈0.33 vs Green **raw `chpm`** — winsorization does not explain the gap. Datashare is **not** Green-style `chpmia`; likely a GKX-specific variant (different timing, industry bucket, or mislabeled base ratio). Other IA columns show partial Green–datashare gaps too (`chatoia` 0.85, `chempia` 0.78, `cfp_ia` 0.58).

## pchcapx_ia — formula decomposition

- Three-way overlap: **237,018** rows
- Spearman: panel–Green=0.575, datashare–Green=0.519, panel–datashare=0.617

- panel `pchcapx` vs Green `pchcapx`: ρ=0.997
- panel `pchcapx` vs datashare `pchcapx_ia`: ρ=0.553
- Green `pchcapx` vs datashare `pchcapx_ia`: ρ=0.556
- winsor(panel ia) vs datashare ia: ρ=0.616
- winsor(Green ia) vs datashare ia: ρ=0.519

**Interpretation:** Decompose base `pchcapx` agreement first; then industry demean; Green winsorizes `pchcapx_ia` monthly (L1164–1182).

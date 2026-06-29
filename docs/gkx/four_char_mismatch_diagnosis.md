# Four-character mismatch diagnosis (panel vs datashare)

- Window: **201001–201512**
- Panel: `all_character_signal_panel_for_GKX_comparison.csv`
- Datashare: `datashare.csv`

## ms (Mohanram 0–8 score)

- **signal month**: paired=247,764, ρ=0.562, exact=25.9%, integer-match=25.9%
  - Top score diffs (panel − datashare): +0:64,165, +1:52,166, -1:36,499, +2:32,006, -2:24,796, +3:14,086, -3:14,020, -4:4,583
- **target month**: paired=248,022, ρ=0.559, exact=25.8%, integer-match=25.8%
  - Top score diffs (panel − datashare): +0:63,893, +1:52,048, -1:36,658, +2:31,995, -2:25,012, +3:14,200, -3:14,064, -4:4,616
- **Best alignment**: signal
- **Likely drivers**: (1) m7/m8 quarterly merge on `date` vs annual m1–m6 on `signal_yyyymm`; (2) component-level disagreement; (3) datashare/Green may winsorize `ms` monthly (L1167) though scores are discrete.

## indmom (equal-weight mean mom12m by sic2 × month)

- Raw panel vs datashare: paired=257,868, ρ=0.970, exact=1.2%
- Panel mom12m vs datashare mom12m (same rows): ρ=1.000
- Recomputed mean(mom12m)|panel sic2: ρ vs datashare indmom = 0.970; vs panel indmom = 0.991
- Recomputed mean(mom12m)|datashare sic2: ρ vs datashare indmom = 0.979
- Panel sic2 == datashare sic2 (same permno-month): 0.0%
- Recomputed mean(datashare mom12m)|datashare universe: ρ vs datashare indmom = 0.987
- Panel indmom after monthly 1/99 winsor: ρ vs datashare = 0.970
- **Likely drivers**: sic2 source/timing; firm set entering industry mean (datashare universe vs full CRSP); monthly winsorization of indmom in datashare.

## chpmia (industry-demeaned chpm)

- **signal** chpmia: paired=242,952, ρ=0.362, exact=0.4%
  - Panel base `chpm` on overlap: non-null=242,952, median=0.0026, p99=6.9162
  - After monthly 1/99 winsor on panel chpmia: ρ=0.361
- **target** chpmia: paired=243,161, ρ=0.328, exact=0.4%
  - Panel base `chpm` on overlap: non-null=243,161, median=0.0024, p99=6.7647
  - After monthly 1/99 winsor on panel chpmia: ρ=0.328

## pchcapx_ia (industry-demeaned pchcapx)

- **signal** pchcapx_ia: paired=242,270, ρ=0.618, exact=0.2%
  - Panel base `pchcapx` on overlap: non-null=242,270, median=0.0376, p99=10.5000
  - After monthly 1/99 winsor on panel pchcapx_ia: ρ=0.618
- **target** pchcapx_ia: paired=242,442, ρ=0.569, exact=0.2%
  - Panel base `pchcapx` on overlap: non-null=242,442, median=0.0361, p99=10.4949
  - After monthly 1/99 winsor on panel pchcapx_ia: ρ=0.569
- **Note**: negative `lag(capx)` denominators affect `pchcapx` (~1.6k permnos); industry mean uses SIC2×fyear at fiscal datadate, then Green months 7–19.

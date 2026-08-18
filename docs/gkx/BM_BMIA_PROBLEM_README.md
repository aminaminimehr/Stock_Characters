# The `bm` / `bm_ia` Problem — Complete Brief

**Status:** Open. `bm` is ~93% solved (a residual puzzle remains); `bm_ia` is *understood but
not independently reproducible* from the published file.
**Audience:** Any agent or researcher who needs to understand the full history and pick up the work.
**Last updated:** 2026-08-03.
**Companion doc:** `docs/gkx/datashare_reverse_engineering.md` (column-by-column detail).

---

## 0. The one-paragraph summary

`datashare.csv` publishes two book-to-market columns: `bm` (raw) and `bm_ia`
(industry-adjusted). We can reproduce `bm` to a pooled Spearman of **0.85–0.93**
against the published file. We *understand exactly how `bm_ia` is built* —
`bm_ia = bm − mean(bm)` over (2-digit SIC × calendar month), recomputed every
month — but we **cannot reproduce it independently**, because the published
`bm_ia` was built from a **construction-time SIC vintage and a benchmark universe
that are not in the published file**. As a result, every independent rebuild tops
out around a **0.42–0.44 median monthly Spearman**, and — decisively — even
re-deriving `bm_ia` *from datashare's own published `bm` and `sic2`* only reaches
**0.84**, not 1.0. That 0.84 is a hard ceiling set by the file's own internal
inconsistency, and it is the reason `bm_ia` looks "stuck."

---

## 1. The objective

> **Find a way to construct `datashare.csv`'s `bm_ia` independently**, i.e. from
> WRDS raw inputs (Compustat + CRSP) without using the published `bm_ia` itself,
> such that the rebuilt series matches the published `bm_ia` at a median monthly
> cross-sectional Spearman **≥ 0.95** and an exact-match rate (|Δ| ≤ 1e-4) **≥ 90%**.

Secondary objective: close the remaining gap on `bm` (currently 0.929 median ρ)
so the underlying `bm` input to `bm_ia` is as clean as possible.

What "independently" does **not** mean: extracting the industry mean from
`datashare.csv`'s own `bm_ia` column and subtracting it (that is circular and was
the source of a spurious "0.99" result — see §8).

---

## 2. The two columns and what they contain

### `bm` (book-to-market)
- **Best explanation:** HXZ / Fama-French-style annual book-to-market.
- **Formula family** (matches the HXZ technical document):

  ```text
  ps        = first nonmissing of pstkrv, pstkl, pstk, else 0
  stock_eq  = seq, else ceq + ps, else at - lt      # fallback chain
  book_eq   = stock_eq + txditc0 - ps
  bm        = (book_eq * 1000) / December CRSP permco market equity
  ```
- **Timing (the "June convention"):** a fiscal year ending in calendar year `y` is
  used from **June y+1 through May y+2**. Equivalently, annual data is
  "June-expanded" onto a 12-month monthly window.
- **Evidence:** panel `book_to_market` vs published `bm` — pooled ρ **0.85**,
  median monthly ρ **0.929**, exact 64% in older tests.
- **Open residual:** the ~7% rank gap. Tested hypotheses that did *not* close it:
  HXZ `seq`-only book equity (no fallback), monthly winsorization (1% and 2.5%),
  FF48 mapping, SIC source swaps. The residual is most likely link-history /
  universe / delisting-filter differences in legacy Compustat/CRSP rows.

### `bm_ia` (industry-adjusted book-to-market)
- **Reverse-engineered formula (CONFIRMED 2026-07-09):**

  ```text
  bm_ia = bm - mean(bm)    grouped by (sic2, calendar month)
                          mean recomputed EVERY month over that month's universe
  ```
- Equal-weight mean, not median; not value-weighted.
- `bm` keeps its annual June-convention value; the *monthly* movement of `bm_ia`
  comes entirely from (a) membership churn in each (sic2, month) cell and
  (b) staggered fiscal-year refreshes of peer firms.
- This was proven by the implied-adjustment diagnostic (§5): within (sic2, month)
  cells, 97.1% of firm-months carry the *modal* industry benchmark, and
  reconstruction from the modal benchmark hits **0.9921 median ρ / 97.1% exact**.

---

## 3. Why it is hard — the three independent ceilings

The confusion in this project has come from conflating four different Spearman
numbers. They are *all real* but measure different things. Know which one you are
looking at.

| # | What is being correlated | Value | Meaning |
|---|---|---:|---|
| A | Panel `bm_ia` (sic2×month, our `bm`) **vs** published `bm_ia` | **0.418–0.436** | The true independent rebuild. This is the number to beat. |
| B | Published `bm` demeaned by published (sic2, month) **vs** published `bm_ia` | **0.836** | The **formula ceiling**: the best *any* SIC2×month formula can do, because it uses datashare's own inputs. Set by the file's internal SIC-vintage inconsistency. |
| C | Published `bm` demeaned by **modal implied benchmark** vs published `bm_ia` | **0.9921** | **Not independent.** The modal benchmark is recovered from `bm − bm_ia` itself. This is the circular number. |
| D | Panel `bm`/`bm_ia` (Green-style) **vs Green SAS** output | **0.987–0.9996** | Self-consistency with the baseline we built on top of. Says nothing about matching datashare. |

**The key insight:** B < C is the proof. If `bm_ia` were a clean
`bm − mean_{sic2,month}(bm)` of the published file, then B would equal C (~0.99).
The fact that B is only **0.836** means the published `bm_ia` was demeaned using a
**sic2 / universe that differs from the published `bm` + `sic2`**. That hidden
construction-time input is what we cannot recover.

So:
- **A ≤ B always.** No matter what SIC2×month variant we build from our `bm`,
  we cannot exceed ~0.836 *in principle*, because even the published file can't
  reproduce its own `bm_ia` from its own published `bm`+`sic2`.
- Our current **A ≈ 0.42** is *below* B ≈ 0.84 because our `bm` (ρ≈0.93 vs
  published) is noisier than the published `bm`. Roughly: A ≈ B × (our `bm`
  quality) ≈ 0.84 × 0.93 × (SIC-vintage overlap factor) ≈ 0.42. **The SIC-vintage
  factor is the dominant loss**, not the `bm` gap.

---

## 4. The full timeline of what was tried and the verdict

### `bm`
| Hypothesis | Test | Result | Verdict |
|---|---|---|---|
| HXZ `seq`+fallback book equity, June timing | `book_to_market` builder | pooled ρ 0.85, median ρ 0.929 | **Best.** This is the panel `bm`. |
| HXZ `seq`-only (no fallback) book equity | `diag_build_bm_hxz_formula.py` | no improvement | Rejected |
| 6-month-delayed report bm (user's original guess) | timing reverse-engineering | published `bm` is June-updated, not delayed | Rejected |
| Monthly 1% / 2.5% winsorization of `bm` | `diag_winsorized_bm_bmia.py` | negligible change to `bm` ρ | Rejected (winsorization not the gap) |

### `bm_ia`
| Hypothesis | Test | Result | Verdict |
|---|---|---|---|
| GKX/Xiu FF49 × datadate, annual+quarterly blend | first-pass port | median ρ 0.31 | Rejected |
| HXZ `bm` demeaned by FF49 × month | `diag_bm_ia_ff48.py` | median ρ **0.389** | Rejected — *worse* than SIC2 |
| HXZ `bm` demeaned by SIC2 × month (current builder) | `bm_ia_builder.py` | median ρ **0.418** | **Current best independent** |
| Construction-time SIC = `comp.funda.sich` | `diag_bm_ia_sich.py` | no improvement | Rejected (vintage not recoverable from WRDS field swap) |
| Construction-time SIC = `comp.company.sic` (static) | same | no improvement | Rejected |
| `sum(bm) = mean × n` universe-identity test | `diag_bm_ia_sum_identity.py` | holds in ~45% of cells; failures = off-mode firms, not a recoverable screen | No new universe screen found |
| FF48-from-exposed-`sic` partition | `audit_bmia_industry_fingerprint.py` | 62–64 implied clusters/month; FF48/49 cell-agreement ≤ 59% | Rejected — FF48 from exposed SIC loses (−0.029 vs SIC2) |
| Recover mean from `bm − bm_ia`, re-demean (circular) | implied-benchmark audit | median ρ **0.9921**, exact 97.1% | **Circular** — proves the *formula*, not an independent build |

---

## 5. The decisive diagnostic: the implied-adjustment method

This is the single most important experiment in the project. Define:

```text
implied := bm - bm_ia          # the industry benchmark each firm actually received
```

If `bm_ia = bm − mean(bm)` over some grouping `g`, then `implied` must be
**identical for every firm in cell `g`**. This lets us *fingerprint* the true
grouping without assuming it.

**Findings (`audit_bmia_implied_adjustment.py`, 2026-07-09):**
1. **Grouping = (sic2 × calendar month).** Within (month, sic2) cells, 44.4% are
   exactly constant (< 1e-6), cell-mean R² = 0.958. Annual (year, sic2) grouping:
   R² = 0.698 → rejected. Month-only / year-only: R² < 0.08 → rejected.
2. **~62–66 distinct benchmark values per month.** This rules out FF12/17/30/38/48/49
   (each has ≤ 49 buckets) and is consistent with ~74 active SIC2 codes.
3. **Statistic = equal-weight mean of the published `bm`.** In cells with no
   misassigned firms, the recovered benchmark equals the in-cell mean of `bm`
   exactly (45.2% of cells; benchmark/mean ratio = 1.000 in every decade).
4. **97.09% of firm-months sit exactly on their cell's modal benchmark.** The
   remaining 2.91% carry a *different* benchmark; ~19.5% of those exactly match
   *another* sic2's benchmark the same month → **their construction-time SIC
   differs from the published `sic2`** (the SIC-vintage problem).
5. The monthly-CRSP-ME mechanism from `accounting_60.py`
   (`bm_ia = be/me_t − const`) is **rejected**: within constant-`bm` windows,
   `bm_ia` is NOT linear in 1/mvel1 (median R² ≈ 0.21–0.25).

**Falsification test (`audit_bmia_remaining_blockers.py`, 2026-07-10):**
The monthly benchmark moves in **99.0–99.9%** of consecutive-month cell pairs with
membership churn, **78.4%** where a peer refreshed its annual `bm`, and only
**1.4%** with neither. So monthly movement is *fully explained* by peer refreshes
+ churn — no extra mechanism needed. Benchmark timing: k=0 (same month) wins
(45.2% exact) over k=±1 (21%) and k=±2 (12%). Benchmark universe: no
bm/bm_ia null asymmetry; winsorized/trimmed means explain none of the mismatches.

---

## 6. The SIC-vintage problem in plain terms

When `datashare.csv` was built, each firm was assigned to an industry using the
**SIC code as of construction time** (the builder's WRDS pull date or the firm's
historical SIC). The published `sic2` column is a **different, later vintage**
(static/as-of-today, or a different source). So:

- ~3% of firm-months were demeaned against a *different* industry than their
  published `sic2` suggests.
- Each such "off-mode" firm pulls its entire (sic2, month) cell's mean in the
  wrong direction when we recompute it from the published `sic2`.
- This is why B (0.836) < C (0.992): the 3% off-mode firms, and possibly some
  benchmark-universe firms that were screened out of the published rows, make the
  published file *internally inconsistent* with a clean SIC2×month re-derivation.

**Why swapping WRDS SIC fields did not help:** we tested `comp.funda.sich`
(historical as-of-filing) and `comp.company.sic` (current static). Neither
reproduces the *exact construction-time assignment*, which appears to have been a
specific snapshot. The vintage is not recoverable by simply choosing a different
WRDS SIC column.

---

## 7. Current state of the code

- **`bm` builder:** `Character_Builders/HXZ_BM_Generalized/build_book_to_market.py`
  → feeds `outputs/characteristics/individual/book_to_market.csv`. This is the
  validated best `bm`. Do **not** change without re-validating against datashare.
- **`bm_ia` builder (independent):**
  `Character_Builders/_shared/bm_ia_builder.py` +
  `Character_Builders/Datashare_BM_IA_Generalized/build_bm_ia.py`. WRDS-free:
  June-expands `book_to_market.csv` and demeans by (sic2, signal month). Output
  → `outputs/characteristics/individual/bm_ia.csv`, panel column `bm_ia`.
- **Pipeline integration:** `Character_Panels/run_full_pipeline.py` builds `bm`
  then `bm_ia`.
- **The circular `_dc` builder (`build_datashare_chars.py` / `bm_ia_dc`) was
  DELETED** in the 2026-08 cleanup. It computed the FF49 industry mean from
  monthly-expanded data and only reached 0.34 vs datashare anyway.

### Key validation scripts (in `scripts/validation/` and `scripts/audits/`)
| Script | Purpose |
|---|---|
| `validate_bmia_formula.py` | Re-derives `bm_ia` from datashare's own `bm`+`sic2` → the **0.836 formula ceiling (B)** |
| `compare_bm_ia_vs_datashare.py` | Panel `bm_ia.csv` vs datashare `bm_ia` |
| `diag_bm_ia_ff48.py` | FF48 vs SIC2 rebuild comparison |
| `diag_bm_ia_sich.py` | Historical-SIC-source test |
| `diag_bm_ia_sum_identity.py` | Universe-identity test |
| `diag_winsorized_bm_bmia.py` | Monthly winsorization test |
| `plot_bm_bmia_spearman_ts.py` | Monthly ρ time series |
| `plot_recovered_industry_mean_bm_ts.py` | Recovered mean(bm) time series + count gap |
| `audit_bmia_implied_adjustment.py` (audits/) | The decisive implied-benchmark fingerprint |
| `audit_bmia_industry_fingerprint.py` (audits/) | FF vs SIC2 partition test |
| `audit_bmia_remaining_blockers.py` (audits/) | Movement / timing / universe falsification |

---

## 8. The "0.99" confusion — read this before trusting any high number

A `bm_ia` result near 0.99 has appeared in this project and caused significant
confusion. It is **not** a `bm_ia`-vs-datashare result. The transcript shows
`bm_ia` vs datashare was *always* **0.27–0.44**. The 0.99s were one of three
other things:

1. **C — the circular implied-benchmark reconstruction (0.9921).** This recovers
   the industry mean from `bm − bm_ia` itself. It proves the *formula* is
   `bm − mean_{sic2,month}(bm)`, but it is **not an independent build** and must
   never be reported as a match.
2. **D — Green-vs-Self (0.987 for `bm_ia`, 0.9996 for `bm`).** This checked our
   Green-style implementation against **Green's own SAS output**, not against
   datashare. Matching Green at 0.99 is expected; it says nothing about datashare.
3. **Aggregate bucket counts ("68/95 at ρ ≥ 0.99").** Headlines counting how many
   of the 95 predictors clear 0.99 — dominated by CRSP/momentum chars. `bm_ia`
   is always flagged separately as the underperformer in those same messages.

**Rule for any agent:** if you see a `bm_ia` number near 0.99, identify which of
the four categories (A/B/C/D from §3) it is before drawing any conclusion. Only
**A** is an independent match against datashare, and it currently stands at
**~0.42**.

---

## 9. What would actually move A toward the objective

Since A ≤ B = 0.836 (a hard ceiling from the file's internal inconsistency),
getting A to 0.95+ requires **breaking the ceiling** — i.e. obtaining the hidden
construction-time input. Ranked by likelihood:

1. **Find the exact original `datashare.csv` generation script.** The file is too
   internally inconsistent with a clean SIC2×month re-derivation to infer the
   construction safely from formulas alone. The script would name the exact SIC
   field, vintage, and benchmark universe. **Highest-value next step.**
2. **Recover the construction-time SIC.** Test whether FF48/FF49 applied to the
   *construction-time* 4-digit SIC (not the exposed `sic2`) is the true partition.
   Requires locating a historical SIC snapshot consistent with the build date —
   the audit suggests FF48-from-exposed-SIC loses (−0.029), so this only helps
   with the *right* SIC vintage.
3. **Test the benchmark universe = all-Compustat (not just CRSP-linked).** §3 of
   the companion doc lists this. Some benchmark firms may have been screened out
   of the published rows but still contributed to the cell means.
4. **Close the `bm` gap first.** The `bm` ρ is 0.929; pushing it toward 0.99
   directly lifts A (A scales with our `bm` quality). Investigate
   link-history / delisting / security-code filters on legacy rows.
5. **Per-month value-weighted or median demeaning** as a last-resort variant —
   but the implied-adjustment audit already showed equal-weight mean is the
   statistic, so this is low-priority.

### Explicitly ruled out (do not re-test)
- 6-month-delayed report bm timing.
- HXZ `seq`-only book equity (no fallback).
- FF48/FF49 demeaning from the *exposed* `sic`/`sic2`.
- SIC-source swaps to `comp.funda.sich` or `comp.company.sic`.
- Monthly 1% / 2.5% winsorization of `bm`.
- The annual (year × sic2) grouping and the monthly-CRSP-ME mechanism.

---

## 10. How to validate any new attempt

Every `bm_ia` candidate must report all of these, joined on `permno × month`,
best of `signal_yyyymm` vs `target_yyyymm`, restricted to datashare months
**195701–202112**:

- Median monthly cross-sectional Spearman ρ (primary).
- Pooled Spearman ρ.
- Exact-match rate (|Δ| ≤ 1e-4) and round-4 rate.
- Paired N, unique permnos (both), `%mρ<0.5` (share of bad months).
- **Which ceiling it is being compared to** (A, B, C, or D from §3).

A candidate is only an *independent* match if it is category **A** and uses no
information from the published `bm_ia` column. If it reaches ρ ≈ 0.99, it is
almost certainly category C (circular) — re-read §8.

Reference numbers to beat / match:
- **A (independent, target):** current **0.418–0.436** → objective **≥ 0.95**.
- **B (formula ceiling, datashare's own inputs):** **0.836**.
- **C (circular, do not report as a match):** **0.9921**.

---

## 11. File map (quick lookup)

```
docs/gkx/
  BM_BMIA_PROBLEM_README.md          <-- THIS FILE (start here)
  datashare_reverse_engineering.md   <-- column-by-column detail (§5 source)

Character_Builders/
  HXZ_BM_Generalized/build_book_to_market.py      <-- bm builder (best)
  _shared/bm_ia_builder.py                         <-- bm_ia builder (independent)
  Datashare_BM_IA_Generalized/build_bm_ia.py       <-- bm_ia pipeline entry

scripts/validation/   <-- diag_bm_ia_*.py, validate_bmia_formula.py, plots
scripts/audits/       <-- audit_bmia_*.py (the decisive implied-adjustment work)

outputs/characteristics/individual/
  book_to_market.csv   <-- annual bm feed (June-expanded by bm_ia builder)
  bm_ia.csv            <-- independent bm_ia output

Supplementary_assistive_files/
  datashare.csv        <-- THE TARGET
  MarkItDown_outputs/Technical_Document_Factors_HXZ.md   <-- HXZ bm book-equity spec
```

---

## 12. Plan B — are other industry-adjusted characters internally inconsistent too?

`bm_ia` is not the only datashare column built as `base - industry_mean(base)`.
Two other families publish BOTH a base and an industry-adjusted sibling:

| adjusted | base | nature |
|----------|------|--------|
| `bm_ia`  | `bm`   | monthly (benchmark recomputed every calendar month) |
| `cfp_ia` | `cfp`  | annual  (benchmark per fiscal year) |
| `chempia`| `hire` | annual  (benchmark per fiscal year) |

Question: do `cfp_ia` / `chempia` carry the **same** internal inconsistency
(published adjusted NOT cleanly re-derivable from published base + `sic2`) that
`bm_ia` does?

### Method

`scripts/audits/audit_ia_implied_adjustment.py` generalizes the §5 implied-
adjustment recipe to any (base, adjusted) pair. For each pair it computes, under
the best recoverable grouping (`month×sic2` for `bm_ia`; June-expansion
`fyear×sic2` for the annual chars, since datashare has no `fyear` column):

- **constancy** — % cells where `implied = base - adjusted` is identical for all
  firms (clean construction ⇒ ~100%).
- **recon rho** — median cross-sectional Spearman of `base - mean(base)|cell`
  vs published adjusted. This is the **independent** ceiling (uses only the base
  + `sic2`, never the adjusted column).
- **modal rho** — `base - mode(implied)|cell` vs published adjusted. **Circular**
  (it reads the adjusted column), so it only confirms the formula shape; it is
  NOT an independent build.
- **on-mode %** — share of firms sitting on their cell's modal benchmark.
- **off-mode cross-sic2 %** — the **SIC-vintage signature**: of the off-mode
  firms, the share whose `implied` equals *another* `sic2`'s benchmark in the
  same period. High ⇒ construction-time SIC differed from published SIC.

### Result (primary grouping)

```
character base  adj     n_valid  const%  R2     recon_rho  modal_rho  on_mode%  off_xsic2%
bm_ia     bm   bm_ia   3,042,589  44.4  0.958    0.8323     0.9921    97.1      19.5
cfp_ia    cfp  cfp_ia  2,768,521   2.1  0.647    0.8510     0.9410    82.5       0.2
chempia   hire chempia 2,806,379   2.3  0.747    0.8795     0.9523    82.6       0.6
```

### Verdict

**No — the other IA characters do NOT share `bm_ia`'s inconsistency.** The
decisive metric is **off-mode cross-sic2**, the SIC-vintage signature:

- `bm_ia`: **19.5%** of off-mode firms carry *another* `sic2`'s benchmark in the
  same month — the unmistakable fingerprint of a construction-time SIC vintage
  that differs from the published `sic2` (§6).
- `cfp_ia`: **0.2%**. `chempia`: **0.6%**. Essentially zero. Their off-mode firms
  do **not** line up with any other published `sic2` benchmark, so their residual
  gap is **not** the SIC-vintage type.

Two corollaries:

1. **Independent ceilings are similar across all three** (~0.83–0.88). None is
   perfectly reconstructible from base + `sic2`, but none is dramatically worse.
   `bm_ia` 0.83, `cfp_ia` 0.85, `chempia` 0.88.

2. **`bm_ia` has the largest recon→modal gap** (0.83→0.99, Δ0.16): its true
   benchmark diverges most from the naive `sic2` mean. The annual chars diverge
   less (0.85→0.94, 0.88→0.95), i.e. their true benchmark is *closer* to a plain
   `sic2` mean — consistent with them being more cleanly `sic2`-demeaned.

### Caveat on the annual chars' on-mode

`cfp_ia`/`chempia` show lower on-mode (82.5%) than `bm_ia` (97.1%). This is
**not** a SIC-vintage signal (cross-sic2 ≈ 0). It most plausibly reflects (a)
residual error in the June-expansion `fyear` inference for non-December
fiscal-year firms, and/or (b) a different industry classification / demeaning
statistic. The grouping-independent recon ceiling (0.85–0.88) is the
trustworthy comparison; the on-mode gap is a measurement artifact of inferring
`fyear` from datashare alone. Either way, it is a *different, smaller* residual
than `bm_ia`'s, and it is **not** the recoverable SIC-vintage signature.

### Bottom line for the objective

The SIC-vintage mismatch is **specific to `bm_ia`**, not a systemic property of
all industry-adjusted datashare columns. So the path to independently rebuilding
`bm_ia` (§9) remains: recover the construction-time SIC assignment (or the exact
industry scheme) used for `bm`/`bm_ia` only — the other IA chars do not need it.

### Artifacts

- `scripts/audits/audit_ia_implied_adjustment.py` — the generalized audit.
- `outputs/diagnostics/ia_implied_audit_summary.csv` / `.txt` — the table above.
- `outputs/diagnostics/ia_implied_audit_{bm_ia,cfp_ia,chempia}.csv` — per-character
  constancy / reconstruction / modal detail (primary + fallback groupings).


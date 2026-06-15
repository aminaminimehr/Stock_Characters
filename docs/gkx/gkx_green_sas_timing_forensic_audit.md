# Green SAS timing forensic audit

**Purpose:** Establish evidence on where Green’s SAS timing convention differs from this repository’s annual → June expansion, and whether real firms show different characteristic values as a result.

**Scope:** Read-only audit. No code, pipeline, rebuild, or timing redesign.

**Sources:**
- `Supplementary_assistive_files/SAS_codes/Greens_code.sas`
- `Supplementary_assistive_files/Output_From_Greens_SAS_code.sas7bdat`
- `Character_Panels/build_all_character_panel.py` (`expand_annual_file`)
- Prior alignment work: `docs/gkx/gkx_chatoia_repo_vs_green_audit.md`, `docs/gkx/gkx_phase1_disagreement_audit.md`

**Validation window:** `signal_yyyymm` / Green `DATE` month-end **201801–202312**.

---

## Executive answer (advisor summary)

**Yes, the timing difference is real, it is coded explicitly in Green’s SAS, and it changes characteristic values for many firm-months.**

| Question | Answer |
|----------|--------|
| Where does Green differ from our repo? | Green maps **annual** Compustat to CRSP months with `intnx('MONTH',datadate,7) ≤ date < intnx('MONTH',datadate,20)` and keeps the **latest** matching fiscal `datadate` per `permno×date` (`nodupkey`). The repo expands each annual row to **12 constant months** starting **June** of `calendar_year(datadate)+1`. |
| Is this the same as our June convention? | **No.** Green’s window starts about **7 months** after fiscal `datadate` and lasts up to **13 monthly CRSP dates**; the repo holds one annual value from **June** through the following **May**. The calendars overlap only partially. |
| Do real firms show different values? | **Yes.** On 187,327 paired `permno×month` rows for `chatoia`, only **29.8%** match exactly; **55.4%** have both a different attached fiscal year and a different value. |
| Is it economically large? | For **industry-adjusted** annual variables (`chatoia`, `cfp_ia`), timing drives most disagreement (Spearman ~0.83 monthly vs ~0.998 at `permno×fyear`). For **levels** like `bm`, `invest`, `age`, values often agree (~82–83%) despite fiscal-date mismatch because year-over-year levels are similar. |
| Formula bug? | **No** for `chatoia` — at `permno×fyear` (last month in window) Spearman is **0.998** with repo annual builder. |

**Important interpretive notes:**

1. After annual→monthly alignment, Green **drops** annual `datadate` and re-attaches **quarterly** `datadate` (lines 760–768). The `datadate` column in `Output_From_Greens_SAS_code.sas7bdat` is a **quarterly** fiscal date, not the annual fiscal date that sourced `chatoia`. Annual characteristics on each row still come from the earlier annual merge.

2. Green’s saved output applies **monthly cross-sectional winsorization** to `chatoia` (lines 1187–1237) but **not** to `chato`. Therefore the same firm can show **identical `chato` but different `chatoia`** across months when the quarterly `datadate` label is unchanged. This is **not** an annual timing refresh and must be distinguished from repo-vs-Green calendar differences.

---

## Task 1 — Timing logic in Green SAS (with code evidence)

### 1.1 CCM link: Compustat annual → CRSP `permno`

**Lines 409–417**

```sas
proc sql; create table temp as select a.lpermno as permno,b.*
    from lnk a,data b where a.gvkey=b.gvkey 
    and (LINKDT <= b.datadate or LINKDT = .B) and (b.datadate <= LINKENDDT or LINKENDDT = .E) 
    and lpermno ne . and not missing(b.gvkey);
```

**What it does:** Links each annual Compustat `gvkey×datadate` to CRSP `permno` using CCM link dates valid at fiscal `datadate`.

---

### 1.2 Annual characteristics computed at fiscal `datadate` (not yet monthly)

**Lines 79–84, 147, 157, 165, 244–249**

```sas
by gvkey datadate;
if first.gvkey then count=1; else count+1;
...
age=count;
chato=(sale/((at+lag(at))/2)) - (lag(sale)/((lag(at)+lag2(at))/2));
invest=( (ppegt-lag(ppegt)) + (invt-lag(invt)) ) / lag(at);
...
create table data2 as select *, chato-mean(chato) as chatoia, cfp-mean(cfp) as cfp_ia, bm-mean(bm) as bm_ia, ...
from data2 group by sic2,fyear;
```

**What it does:** Builds annual signals at Compustat fiscal dates; `age` is a gvkey-level observation counter; `_ia` variables are SIC2×`fyear` demeaned. **No monthly timing yet.**

---

### 1.3 Annual → monthly CRSP alignment (**core timing convention**)

**Lines 475–508 (verbatim from `Greens_code.sas`)**

```sas
*========================================================================================================

		Now align the annual Compustat variables in calendar month with the assumption that
		annual information is available with a lag of 6 months (if we had point-in-time we would use that)

=========================================================================================================;
*---------------------------add returns and monthly CRSP data we need later-----------------------------;					
proc sql;
	create table temp2
	as select a.*,b.ret,abs(prc) as prc,shrout,vol,b.date
	from temp a left join crsp.msf b
	on a.permno=b.permno and intnx('MONTH',datadate,7)<=b.date<intnx('MONTH',datadate,20);
	quit;
							*-----------Included delisted returns in the monthly returns--------------------;
							proc sql;
						 	  create table temp2
							      as select a.*,b.dlret,b.dlstcd,b.exchcd
 							     from temp2 a left join crsp.mseall b
							      on a.permno=b.permno and a.date=b.date;
							      quit;	
							data temp2;
								set temp2;
 								if missing(dlret) and (dlstcd=500 or (dlstcd>=520 and dlstcd<=584))
									and exchcd in (1,2) then dlret=-.35;
 								if missing(dlret) and (dlstcd=500 or (dlstcd>=520 and dlstcd<=584))
									and exchcd in (3) then dlret=-.55; *see Johnson and Zhao (2007), Shumway and Warther (1999) etc.;
								if not missing(dlret) and dlret<-1 then dlret=-1;
								if missing(dlret) then dlret=0;
								ret=ret+dlret;
								if missing(ret) and dlret ne 0 then ret=dlret;
								run;
							proc sort data=temp2;
								by permno date descending datadate;
								run;
							proc sort data=temp2 nodupkey;
								by permno date;
							run;	
```

**What it does:**
- Each annual fiscal record is eligible for CRSP months **`datadate+7` months through `datadate+19` months** (upper bound exclusive at `+20`).
- SAS comment says “lag of 6 months”; the implemented lower bound is **`intnx(..., 7)`**.
- Multiple fiscal records can match the same `permno×date`; **`nodupkey` keeps the latest (descending) `datadate`** → rolling refresh when a newer fiscal year enters the window.
- `b.date` becomes the monthly panel key (Green output `DATE`).
- Delisted-return adjustments (lines 486–503) follow the CRSP merge and precede the sort/`nodupkey` step.

---

### 1.4 Monthly CRSP fields lagged for prediction

**Lines 510–522**

```sas
by permno date;
mve_m=abs(lag(prc))*lag(shrout);
pps=log(lag(prc));
if first.permno then delete;
```

**What it does:** Price/volume used for size are **lagged one month** relative to `date` so signals are not contemporaneous with the return being predicted.

---

### 1.5 Quarterly Compustat → monthly alignment

**Lines 760–776**

```sas
alter table temp2 drop datadate;
create table temp3 as select *
from temp2 a left join data6 b
on a.permno=b.permno and
   intnx('MONTH',a.date,-10)<=b.datadate<=intnx('MONTH',a.date,-5,'beg');
*allow at least four months for quarterly info to become available
proc sort data=temp3;
  by permno date descending datadate;
proc sort data=temp3 nodupkey;
  by permno date;
```

**What it does:**
- **Removes** annual `datadate` from the monthly panel.
- Joins quarterly Compustat where quarterly `datadate` falls **5–10 months before** return-month `date`.
- Again keeps **latest** quarterly `datadate` per `permno×date`.
- The `datadate` column in the final output reflects this **quarterly** attachment.

---

### 1.6 IBES → monthly alignment

**Lines 897–908**

```sas
on a.permno=b.permno and
   intnx('MONTH',a.date,-4,'beg')<=b.statpers<=intnx('MONTH',a.date,-1,'end');
proc sort data=temp4;
  by permno date descending statpers;
proc sort data=temp4(drop=statpers) nodupkey;
  by permno date;
```

**What it does:** IBES summary stats must fall in the **4-month window** ending the month before `date`; latest `statpers` wins.

---

### 1.7 Daily CRSP → monthly (earnings / beta / idiovol)

| Lines | Join rule | Purpose |
|------:|-----------|---------|
| 709–714 | `intnx('WEEKDAY',rdq,-30) ≤ date ≤ intnx('WEEKDAY',rdq,-10)` | Pre-announcement volume |
| 728–731 | `intnx('WEEKDAY',rdq,-1) ≤ date ≤ intnx('WEEKDAY',rdq,1)` | Earnings-announcement return |
| 1024–1029 | `year(intnx('MONTH',date,-1))`, `month(intnx('MONTH',date,-1))` | Prior-month daily aggregates |
| 1060–1064 | `intnx('MONTH',date,-36) ≤ wkdt ≤ intnx('MONTH',date,-1)` | 3-year weekly beta window |

---

### 1.8 Post-merge cross-sectional winsorization (affects reported values)

**Lines 1179–1237** — `chatoia` is in the `hilotrim` list and is winsorized at the **1st and 99th percentile by `date`** each month. **`chato` is not winsorized** (it does not appear in `hitrim` or `hilotrim`). The saved `sas7bdat` contains only the post-winsor values; there is no separate pre-winsor column.

```sas
%let hilotrim=... chpmia chatoia ...
proc means data=temp2 noprint; by date; var &hilotrim;
  output out=stats p1= p99=/autoname;
...
if base(i) ne . and base(i)<(low(i)) then base(i)=(low(i));
if base(i) ne . and base(i)>(high(i)) then base(i)=(high(i));
```

**Consequence:** For a fixed annual `chato`, `chatoia` can still move month-to-month in the output file because winsorization is re-applied to each cross-section. The identity `chatoia = chato − mean(chato)` by `sic2×fyear` holds at the **annual build** stage (lines 244–249) but **need not hold in the final monthly file** after winsorization.

---

## Why `chatoia` can differ across months with the same displayed `datadate`

Four mechanisms appear in the SAS code and output. They should not be conflated.

| Mechanism | Changes `chato`? | Changes `chatoia`? | Evidence |
|-----------|:----------------:|:------------------:|----------|
| **(A) Annual 7–19 month window + `nodupkey`** | Yes — new fiscal year | Yes — before winsor | SAS 484, 505–508; `chato` steps when annual record changes |
| **(B) Quarterly `datadate` relabeling** | No — relabel only | No — by itself | SAS 761–768; quarterly label can advance while `chato` is unchanged |
| **(C) Monthly winsorization of `chatoia` only** | **No** | **Yes** | SAS 1180–1233; same `permno×datadate×chato`, different `chatoia` |
| **(D) Duplicate output rows** | — | — | **Ruled out** — `permno×DATE` is unique in the output file |

**Within a fixed `permno×datadate` group in 201801–202312:** among groups with more than one distinct `chatoia`, **~93%** also show more than one distinct `chato` (annual refresh while the same quarterly `datadate` label spans multiple months). **~7%** show **constant `chato` but varying `chatoia`** — attributable to **(C) winsorization** alone.

**Not duplicate fiscal observations:** The output has one row per `permno×DATE`. Multiple months can share the same quarterly `datadate` label; that is not a duplicate-key violation.

---

## Task 2 — Green vs repository timing (side by side)

### Repository (`expand_annual_file`, lines 66–83)

```python
availability_year = df["datadate"].dt.year + 1
first_signal_month = availability_year * 12 + 5   # June
# repeat 12 months, constant characteristic, dedupe permno×signal_yyyymm keep last
```

**Convention:** Fiscal year ending in calendar year *Y* is held constant from **June *Y+1*** through **May *Y+2***.

### Green SAS (lines 475–508)

```sas
intnx('MONTH',datadate,7) <= b.date < intnx('MONTH',datadate,20)
by permno date descending datadate; nodupkey by permno date;
```

**Convention:** Fiscal `datadate` is eligible from month **`datadate+7`** up to (but not including) **`datadate+20`**. When several fiscal records overlap, the **newest** `datadate` governs that `permno×month`.

### Worked calendar example — fiscal year-end **2017-06-30**

| | First month signal is active | Last month signal is active | Months of coverage |
|---|------------------------------|----------------------------|-------------------|
| **Green** | ~**2018-01** (`+7` months) | ~**2019-01** (`+19`, exclusive at `+20`) | ~13 CRSP months |
| **Repo June** | **2018-06** | **2019-05** | 12 months |

**Overlap:** ~2018-06 – 2019-01 (≈7 months).  
**Green-only:** 2018-01 – 2018-05.  
**Repo-only:** 2019-02 – 2019-05.

These are **not** the same convention.

---

## Task 3 — Concrete firm examples (from `Output_From_Greens_SAS_code.sas7bdat`)

### Example A — Repo still on old annual value; Green already updated

**permno 15125, gvkey 22258, month 201801 (DATE 2018-01-31)**

| Source | Fiscal label on row | `chatoia` |
|--------|--------------------:|----------:|
| **Green** | `datadate` = 2017-06-30 (quarterly column) | **0.012132** |
| **Repo June expand** | annual 2016-12-31 | **0.013502** |

Green is already using information tied to a **newer** fiscal cycle in January 2018. The repo is still flat-filling the **2016-12-31** annual row until **June 2018** (its next June boundary).

Green Jan–May 2018 for this firm (same `chatoia` until annual refresh):

| DATE | Green `datadate` | `chatoia` |
|------|------------------|----------:|
| 2018-01-31 | 2017-06-30 | 0.012132 |
| 2018-02-28 | 2017-06-30 | 0.012132 |
| 2018-03-29 | 2017-09-30 | 0.012132 |
| 2018-04-30 | 2017-09-30 | 0.012132 |
| 2018-05-31 | 2017-09-30 | 0.012132 |

Repo for the same months: **0.013502** throughout (2016-12-31 annual row).

---

### Example B — Both approaches agree

**permno 10158, gvkey 185128**

| `signal_yyyymm` | DATE | Repo annual `datadate` | Green `datadate` | `chatoia` (both) |
|----------------:|------|------------------------|------------------|-----------------:|
| 201807 | 2018-07-31 | 2017-12-31 | 2017-12-31 | **−0.027347** |
| 201808 | 2018-08-31 | 2017-12-31 | 2017-12-31 | **−0.027347** |
| 201907 | 2019-07-31 | 2018-12-31 | 2018-12-31 | **−0.073441** |

In overlapping months where both attach the same effective fiscal year, values match exactly.

---

### Example C — Timing vs repo, with within-Green winsorization separated

**permno 10028, gvkey 012096**

Green SAS output rows (no separate pre-winsor column exists):

| DATE | datadate | fyear | sic2 | chato | chatoia |
|------|----------|------:|-----:|------:|--------:|
| 2018-10-31 | 2018-03-31 | 2017 | 59 | 1.402176 | 0.576019 |
| 2018-11-30 | 2018-03-31 | 2017 | 59 | 1.402176 | 0.549085 |
| 2019-04-30 | 2018-09-30 | 2017 | 59 | 1.402176 | 0.613119 |

**Oct → Nov 2018 (same `datadate`, same `chato`, different `chatoia`):** This is **monthly winsorization (mechanism C)**, not annual timing refresh and not quarterly relabeling (`datadate` unchanged). Pre-winsor annual `chato` is identical; only winsorized `chatoia` moves.

**Mar → Apr 2019 (same `datadate` 2018-09-30, same `chato`, `chatoia` 0.527217 → 0.613119):** Also **winsorization** — not entry of a new annual fiscal record (`chato` would change if the annual source changed).

**Broader path (Aug 2018 – Jun 2019):** `chato` stays **1.402176** throughout while quarterly `datadate` advances (2017-12-31 → 2018-03-31 → … → 2018-12-31) and `chatoia` drifts — combination of **(B) quarterly relabeling** and **(C) winsorization** on a single attached annual `chato`.

**Timing contrast with repo (the primary repo-vs-Green point):**

| Period | Repo June expand (`chatoia`) | Green (`chatoia`) | Repo annual source |
|--------|----------------------------:|------------------:|-------------------|
| 201806–201904 | **1.432540** (constant) | 0.549 – 0.613 (winsorized) | 2017-12-31 |

Repo holds the **2017-12-31** annual row constant for ten months. Green attaches a different annual level (`chato` = 1.402176, `fyear` = 2017) on an earlier calendar schedule and reports **winsorized** `chatoia`. The level gap (1.43 vs ~0.55) reflects **calendar timing** plus **post-processing winsorization** in Green; it is not explained by quarterly `datadate` relabeling alone.

---

## Task 4 — Quantification (201801–202312)

### 4.1 Within Green’s monthly panel — do values change during one repo holding period?

For each `permno×`Green-`datadate` group (quarterly label in output):

| Variable | Fiscal groups | % with >1 distinct monthly value | Avg months per group | % `permno×fyear` with >1 distinct value |
|----------|--------------:|--------------------------------:|---------------------:|----------------------------------------:|
| **chatoia** | 65,386 | **24.9%** | 2.88 | 2.2% |
| **cfp_ia** | 65,669 | **25.0%** | 2.88 | 2.1% |
| **age** | 65,671 | **23.7%** | 2.88 | 0.6% |
| **bm** | 65,671 | **24.9%** | 2.88 | 2.2% |
| **invest** | 64,041 | **24.7%** | 2.88 | 2.2% |
| **orgcap** | — | *all missing in window* | — | — |

**Reading:** ~**25%** of `permno×datadate` groups show multiple distinct monthly `chatoia` values. In **~93%** of those groups, `chato` also varies across months — consistent with **annual refresh (A)** while the same quarterly `datadate` label covers multiple months, sometimes combined with winsorization. In **~7%**, `chato` is constant but `chatoia` varies — **winsorization (C)** alone. This within-Green variation is **separate from** the repo-vs-Green June-calendar mismatch documented in Task 2.

`orgcap` is present in the SAS output file (1.49M non-null rows full sample) but **0 non-null in 201801–202312** after Green’s screens/winsorization — not usable for window comparison.

### 4.2 Repo June vs Green monthly — timing and value agreement

| Variable | Paired `permno×month` | Same Green/repo `datadate`* | Same value (±1e−6) | Different `datadate` **and** different value |
|----------|----------------------:|----------------------------:|-------------------:|---------------------------------------------:|
| **chatoia** | 187,327 | 19.5% | 29.8% | **55.4%** |
| **cfp_ia** | 137,249 | 21.4% | 26.6% | **56.7%** |
| **age** | 137,261 | 21.4% | 83.4% | 9.5% |
| **bm** | 188,385 | 19.4% | 81.6% | 11.7% |
| **invest** | 101,378 | 21.8% | 81.5% | 11.0% |

\*Repo side uses **annual** fiscal `datadate`; Green side uses **quarterly** `datadate` after SAS line 762 — so “same `datadate`” is a strict and somewhat conservative test.

**Additional `chatoia` facts:**
- **80.3%** of paired months: Green’s `datadate` is **newer** than repo’s attached annual `datadate`.
- **0%**: repo newer than Green (systematic one-directional shift).
- Median |Δ`chatoia`| on paired months: **0.00081** (small in levels, but ranks differ — monthly Spearman **0.828**).

---

## Task 5 — Professor-ready conclusion

### Where exactly does Green differ?

The divergence is **not** in the `chatoia` formula (`chato - mean(chato)` by `sic2,fyear` — repo matches Green at `permno×fyear` with Spearman **0.998**). It is in **monthly panel construction**:

1. **Annual availability window** — SAS lines **484, 505–508**: `datadate+7` to `datadate+19` months, latest fiscal wins.
2. **Repo June flat fill** — `expand_annual_file`: June `(year(datadate)+1)` for 12 constant months.
3. **Secondary factors present only in Green’s saved output** (distinct from calendar timing):
   - Quarterly `datadate` relabeling (lines **761–768**) — affects the displayed fiscal label, not `chato` by itself
   - Monthly cross-sectional winsorization of `chatoia` but not `chato` (lines **1179–1237**) — can move `chatoia` month-to-month even when `chato` and quarterly `datadate` are unchanged

### Can we observe real firms where timing changes values?

**Yes.** Example A (permno **15125**, January 2018) is a clean **timing** case: Green `chatoia` = **0.012132** vs repo **0.013502** while repo remains on the prior June-expanded fiscal year. Example C (permno **10028**) contrasts repo’s constant **1.432540** (201806–201904) with Green’s winsorized values on a different calendar schedule; the Oct–Nov 2018 and Mar–Apr 2019 moves within Green are **winsorization**, not timing refresh.

### How economically important?

| Evidence | Implication |
|----------|-------------|
| Monthly `chatoia` Spearman repo vs Green = **0.828**; `permno×fyear` = **0.998** | Timing convention explains most monthly gap |
| **55%** of paired months: fiscal label mismatch **and** value mismatch (`chatoia`) | Not a rare tail event |
| `bm` / `invest` / `age`: ~**82%** value match despite ~**80%** fiscal-label mismatch | Level variables are less timing-sensitive than `_ia` variables |
| Green-only Jan–May vs repo-only Feb–May around each fiscal year-end | Systematic calendar offset, not noise |

### Recommended use of this document

This audit is **evidence only**. It supports a decision on whether to realign the repository’s monthly panel with Green before further GKX predictor validation. It does **not** prescribe a fix.

---

## Appendix — Repository reference

```66:83:Character_Panels/build_all_character_panel.py
def expand_annual_file(df, character_columns):
    df = df.copy()
    df["datadate"] = pd.to_datetime(df["datadate"])
    availability_year = df["datadate"].dt.year + 1

    repeated = df.loc[df.index.repeat(12), ANNUAL_ID_COLUMNS + character_columns].copy()
    month_offsets = np.tile(np.arange(12), len(df))
    first_signal_month = availability_year.to_numpy().repeat(12) * 12 + 5
    month_index = first_signal_month + month_offsets
    repeated["signal_yyyymm"] = (month_index // 12) * 100 + (month_index % 12 + 1)
    ...
```

---

*Audit completed 2026-05-29; consistency check 2026-05-29 (Example C re-verified, winsorization mechanism confirmed). Analysis run read-only against local `outputs/` and Green `sas7bdat`; nothing in the build pipeline was modified.*

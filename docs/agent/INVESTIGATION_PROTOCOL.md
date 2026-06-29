# Investigation Protocol

This document defines the exact procedure the agent must follow in every investigation
session. It is not optional guidance — it is the workflow.

---

## Before every session: the three-read rule

Do not write any code until you have read these three documents:

1. `CONVENTIONS_REGISTRY.yaml` — what is currently known
2. `DISCREPANCY_TABLE.csv` — what still needs to be explained
3. `AGENT_RULES.md` — the constraints you must operate within

State at the start of the session: "I have read all three documents. The highest-priority
open item is [characteristic / hypothesis]. My plan for this session is [one sentence]."

---

## Step 1: Select the investigation target

From DISCREPANCY_TABLE.csv, identify the highest-priority open item using this priority order:

1. Any characteristic marked `IN_PROGRESS` (finish what was started)
2. Industry-related characteristics with untested Hypothesis A (industry averaging order)
3. The characteristic with the lowest Spearman vs GKX among `OPEN` characteristics
4. Any characteristic where sample N or permno count is far off even if Spearman is acceptable

State clearly: "I am investigating [characteristic]. Its current Spearman vs GKX is [X].
I am testing [hypothesis]."

---

## Step 2: Confirm the baseline

Before testing any hypothesis, run the current baseline configuration and confirm that:

- Spearman vs Green is > 0.95 (the Green replication is still intact)
- The baseline Spearman vs GKX matches what is recorded in DISCREPANCY_TABLE.csv

If the baseline has drifted, investigate why before proceeding.

---

## Step 3: Formulate the test

Write out the test plan before running anything:

```
Hypothesis:       [A / B / C / D / E / other]
Parameter:        [parameter name in CONVENTIONS_REGISTRY.yaml]
Current value:    [green_value]
Test value:       [proposed gkx_value]
Characteristics:  [full list of characteristics this hypothesis applies to]
Expected effect:  [what you expect to happen to Spearman and/or N]
```

If you cannot write out the expected effect before running the test, reconsider whether
this is the right hypothesis to test.

---

## Step 4: Run the test across ALL affected characteristics

Never test a hypothesis on one characteristic in isolation. Run it across every
characteristic in the "Characteristics" list from Step 3.

For each characteristic, collect:

```
Characteristic:     [name]
Hypothesis:         [letter]
Change type:        FORMULA | CONVENTION
Spearman vs Green:  [value]  ← must remain > 0.95
Spearman vs GKX:    [before] → [after]
Sample N (ours):    [before] → [after]
Sample N (GKX):     [reference]
Unique permnos:     [before] → [after]
GKX permnos:        [reference]
```

---

## Step 5: Interpret the result

### If Spearman rose significantly AND N moved toward GKX
→ The hypothesis is **confirmed** for this characteristic.
→ Mark the convention in CONVENTIONS_REGISTRY.yaml as confirmed: true.
→ Update status in DISCREPANCY_TABLE.csv.
→ If all three stopping criteria are now met, mark the characteristic CLOSED.
→ If not, move to Step 3 with the next hypothesis.

### If Spearman rose but N is still wrong
→ The convention is **partially confirmed** (formula direction is right but universe
   still does not match).
→ Keep the convention change.
→ Move to testing the universe-affecting hypothesis (C or D) next session.

### If N changed but Spearman did not move
→ The universe is moving toward or away from GKX but the formula is still wrong.
→ Keep the convention change if N moved toward GKX.
→ Investigate formula differences for this characteristic.

### If neither moved
→ The hypothesis is **ruled out** for this characteristic.
→ Mark the hypothesis as tested: true, confirmed: false in the registry.
→ Move to the next hypothesis.

### If Spearman vs Green dropped below 0.95
→ The change broke the Green baseline. **Revert immediately.**
→ This is a critical error — the Green replication must remain intact at all times.
→ Investigate why the change affected Green's output before retesting.

---

## Step 6: Check for formula differences

If all four hypotheses (A–D) have been tested and Spearman vs GKX is still below 0.95:

1. Open the HXZ technical document.
2. Find the formula for this characteristic.
3. Compare it to Green's implementation line by line.
4. If the formulas differ, log the difference in FORMULA_DIFFERENCES.yaml.
5. Implement the HXZ formula as a separate config option (do NOT replace Green's formula).
6. Test the HXZ formula and record its Spearman vs GKX.

If the HXZ formula produces Spearman > 0.95 with correct N, this characteristic's
discrepancy is explained by a formula difference, not a convention difference.
Mark it as `FORMULA_ONLY` in DISCREPANCY_TABLE.csv.

---

## Step 7: Update all records

Before ending the session, update:

1. **DISCREPANCY_TABLE.csv** — every characteristic you touched this session
2. **CONVENTIONS_REGISTRY.yaml** — any confirmed or ruled-out conventions
3. **SESSION_LOG.md** — a brief summary of what was done and what is next

Do not end a session without completing all three updates.

---

## Diagnostic procedures

### Diagnosing a sample N discrepancy

When your N differs from GKX but Spearman is acceptable:

```python
# Step 1: Count total observations by year before any filter
n_raw = df.groupby('year').size()

# Step 2: Count after share code filter
n_after_shrcd = df[df['shrcd'].isin(share_codes)].groupby('year').size()

# Step 3: Count after exchange filter
n_after_exchcd = df[df['exchcd'].isin(exchange_codes)].groupby('year').size()

# Step 4: Count after price filter
n_after_price = df[df['prc'].abs() >= price_threshold].groupby('year').size()

# Step 5: Count after CCM merge
n_after_merge = merged_df.groupby('year').size()

# Compare each step to GKX's implied N by year
# The step where the count diverges identifies the culprit convention
```

### Diagnosing an industry averaging discrepancy

When Spearman is low for an industry-related characteristic:

```python
# Test A: Pre-merge industry average
ind_avg_pre = compustat_df.groupby(['year', 'industry'])['variable'].mean()

# Test B: Post-merge industry average
merged = compustat_df.merge(crsp_df, on=['permno', 'year'], how='inner')
ind_avg_post = merged.groupby(['year', 'industry'])['variable'].mean()

# Compute characteristic under each and compare Spearman to GKX
```

### Diagnosing a timing convention discrepancy

When Spearman is uniformly moderate (e.g. 0.7–0.85) across all annual characteristics:

This is the signature of a timing convention difference. Test:

```python
# FF June convention
# In June of year t, use data from fiscal year ending in calendar year t-1
data['portfolio_year'] = np.where(
    data['fiscal_year_end_month'] >= 7,
    data['fiscal_year'] + 1,
    data['fiscal_year']
)
# Assign to July of portfolio_year through June of portfolio_year+1

# Rolling 6-month lag
# Use fiscal year data starting 6 months after fiscal year end
data['available_date'] = data['fiscal_year_end_date'] + pd.DateOffset(months=6)
```

---

## Red flags: when to stop and ask

Stop the session and flag for human review if:

- The Green baseline Spearman has dropped below 0.95 for any characteristic
- A tested hypothesis raises Spearman for some characteristics but lowers it for others
  (this suggests an interaction effect that needs careful analysis)
- The DISCREPANCY_TABLE shows no progress after three full sessions on the same characteristic
- You find a convention difference that cannot be expressed as a config parameter without
  restructuring the pipeline significantly

In these cases, write a clear description of the blocking issue in SESSION_LOG.md
and stop without making further changes.

---

## What "configurable" means in practice

Every convention must be expressible as a parameter that can be changed without
rewriting the characteristic construction logic.

Good parameterization:
```python
def build_characteristic(config: ConventionConfig):
    if config.industry_averaging_timing == 'post_crsp_merge':
        df = merge_with_crsp(df)
        df = compute_industry_averages(df)
    else:
        df = compute_industry_averages(df)
        df = merge_with_crsp(df)
```

Bad parameterization (do not do this):
```python
# Hard-coded convention buried inside a helper function
def compute_industry_averages(df):
    # Always uses post-merge — not configurable
    df = merge_with_crsp(df)
    return df.groupby('industry')['var'].mean()
```

If you find a convention that is currently hard-coded, refactor it to be configurable
before logging it in the registry. The refactor is part of the investigation.

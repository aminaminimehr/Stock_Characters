# Green SAS Validation Report

This report compares the repository's generated character CSV files in `outputs/`
against `Supplementary_assistive_files/Output_From_Greens_SAS_code.sas7bdat`.

Annual variables are matched on `permno`, `gvkey`, and `fyear`. Monthly variables are matched
on `permno` and `signal_yyyymm`, where `signal_yyyymm` is derived from Green's `DATE`.
Cross-sectional correlations are computed within each fiscal year or month and then
summarized across periods.

## Summary

| character   | green_column   | family   |   matched_nonmissing_pairs |   overall_corr |   mean_xs_corr |   median_xs_corr | exact_4dp   | exact_3dp   | exact_2dp   |   mean_abs_diff |
|:------------|:---------------|:---------|---------------------------:|---------------:|---------------:|-----------------:|:------------|:------------|:------------|----------------:|
| acc         | acc            | annual   |                     175529 |       0.284209 |       0.830569 |         0.903192 | 97.38%      | 97.42%      | 97.62%      |        0.007678 |
| agr         | agr            | annual   |                     187832 |       0.213784 |       0.598537 |         0.624897 | 97.41%      | 97.42%      | 97.49%      |        0.058128 |
| bm          | bm             | annual   |                     201543 |       0.322351 |       0.676709 |         0.759327 | 48.27%      | 49.41%      | 55.43%      |        0.109432 |
| bm_ia       | bm_ia          | annual   |                     201543 |       0.303706 |       0.584266 |         0.611499 | 0.06%       | 1.23%       | 9.09%       |       48.4726   |
| cash        | cash           | annual   |                     186976 |       0.889678 |       0.876031 |         0.901808 | 2.26%       | 4.51%       | 18.50%      |        0.05481  |
| cashdebt    | cashdebt       | annual   |                     192079 |       0.355417 |       0.874367 |         0.927771 | 93.13%      | 93.18%      | 93.50%      |        0.061313 |
| cfp         | cfp            | annual   |                     186195 |       0.319186 |       0.668669 |         0.693724 | 96.54%      | 96.54%      | 96.62%      |        0.056527 |
| chcsho      | chcsho         | annual   |                     187742 |       0.018018 |       0.474051 |         0.538058 | 97.59%      | 97.60%      | 97.68%      |       15.127    |
| chpm        | chpmia         | annual   |                     184309 |       0.189695 |       0.264975 |         0.258366 | 0.48%       | 2.16%       | 10.80%      |        4.24868  |
| depr        | depr           | annual   |                     193224 |       0.162125 |       0.444072 |         0.427008 | 98.93%      | 98.93%      | 98.94%      |        0.125333 |
| ep          | ep             | annual   |                     201543 |       0.285089 |       0.683585 |         0.745823 | 97.62%      | 97.63%      | 97.71%      |        0.046933 |
| gma         | gma            | annual   |                     187432 |       0.369156 |       0.84543  |         0.93167  | 97.51%      | 97.52%      | 97.61%      |        0.017439 |
| grltnoa     | grltnoa        | annual   |                     143248 |       0.270905 |       0.891477 |         0.951166 | 97.45%      | 97.46%      | 97.55%      |        0.008306 |
| herf        | herf           | annual   |                     201542 |       0.962867 |       0.966114 |         0.970349 | 1.35%       | 7.09%       | 51.13%      |        0.01088  |
| hire        | hire           | annual   |                     187411 |       0.126157 |       0.344184 |         0.303758 | 97.39%      | 97.30%      | 97.45%      |        0.135859 |
| lev         | lev            | annual   |                     200984 |       0.54907  |       0.753247 |         0.789703 | 98.88%      | 98.88%      | 98.88%      |        0.336519 |
| lgr         | lgr            | annual   |                     187193 |       0.113124 |       0.46539  |         0.480463 | 97.51%      | 97.51%      | 97.57%      |        0.250931 |
| me_ia       | mve_ia         | annual   |                     201543 |       0.739887 |       0.779879 |         0.807415 | 1.10%       | 1.11%       | 1.20%       |      766.386    |
| op          | operprof       | annual   |                     187428 |      -0.00621  |       0.03217  |         0.039405 | 0.05%       | 0.25%       | 1.31%       |        1.451    |
| pctacc      | pctacc         | annual   |                     175528 |       0.220521 |       0.42272  |         0.432133 | 97.82%      | 97.82%      | 97.82%      |        2.17687  |
| ps          | ps             | annual   |                     187835 |       0.981292 |       0.979171 |         0.979547 | 11.11%      | 11.11%      | 11.11%      |        0.89141  |
| rd_sale     | rd_sale        | annual   |                      96734 |       0.271576 |       0.535145 |         0.526725 | 98.99%      | 98.99%      | 98.99%      |        2.36415  |
| rdm         | rd_mve         | annual   |                      98681 |       0.831962 |       0.882348 |         0.917224 | 98.80%      | 98.80%      | 98.85%      |        0.005012 |
| roe         | roe            | annual   |                     187815 |       0.061982 |       0.344452 |         0.293392 | 97.41%      | 97.43%      | 97.48%      |        0.399729 |
| sgr         | sgr            | annual   |                     184804 |       0.089939 |       0.312851 |         0.308883 | 97.56%      | 97.57%      | 97.59%      |        0.483017 |
| sp          | sp             | annual   |                     201042 |       0.766159 |       0.79442  |         0.813563 | 98.83%      | 98.83%      | 98.83%      |        0.187316 |
| baspread    | baspread       | monthly  |                    2245642 |       0.98089  |       0.976875 |         0.983704 | 99.08%      | 99.10%      | 99.17%      |        0.000868 |
| dolvol      | dolvol         | monthly  |                    2170885 |       0.997612 |       0.997115 |         0.998726 | 98.45%      | 98.67%      | 98.70%      |        0.014042 |
| ill         | ill            | monthly  |                    2183389 |       0.120826 |       0.568875 |         0.580564 | 99.40%      | 99.81%      | 99.99%      |        4e-06    |
| maxret      | maxret         | monthly  |                    2245654 |       0.861007 |       0.875379 |         0.904813 | 98.14%      | 98.39%      | 98.69%      |        0.002477 |
| me          | mve            | monthly  |                    2245686 |       0.999368 |       0.999229 |         0.999199 | 98.69%      | 98.93%      | 98.96%      |        0.006751 |
| mom12m      | mom12m         | monthly  |                    2090274 |       0.893208 |       0.920212 |         0.939788 | 95.96%      | 96.46%      | 96.51%      |        0.020263 |
| mom1m       | mom1m          | monthly  |                    2245198 |       0.918777 |       0.926173 |         0.945637 | 97.69%      | 97.86%      | 97.85%      |        0.004405 |
| mom36m      | mom36m         | monthly  |                    1775795 |                |                |                  | 0.00%       | 0.00%       | 0.00%       |        1.32789  |
| mom6m       | mom6m          | monthly  |                    2181875 |       0.913025 |       0.92578  |         0.941405 | 96.56%      | 96.80%      | 96.81%      |        0.011833 |
| mvel1       | mve            | monthly  |                    2245686 |       0.999368 |       0.999229 |         0.999199 | 98.69%      | 98.93%      | 98.96%      |        0.006751 |
| rvar_mean   | retvol         | monthly  |                    2245629 |       0.263767 |       0.565243 |         0.593028 | 0.68%       | 0.68%       | 1.41%       |        0.031593 |
| std_dolvol  | std_dolvol     | monthly  |                    2180191 |       0.995343 |       0.993707 |         0.99502  | 0.01%       | 0.01%       | 0.01%       |        0.475173 |
| std_turn    | std_turn       | monthly  |                    2185154 |       0.111162 |       0.767804 |         0.841134 | 99.03%      | 99.03%      | 99.03%      |        1.52077  |
| turn        | turn           | monthly  |                    2171651 |       0.14651  |       0.768032 |         0.857554 | 98.22%      | 98.22%      | 98.25%      |        0.210766 |
| zerotrade   | zerotrade      | monthly  |                    2183417 |       0.994539 |       0.916068 |         0.995093 | 99.21%      | 99.21%      | 99.21%      |        0.021826 |

## Variables Not Compared

- `adm`: No `adm` column is present in the supplied Green SAS output.
- `alm`: No `alm` column is present in the supplied Green SAS output.
- `ato`: No direct `ato` column is present; Green output contains `chato` and `chatoia` instead.
- `noa`: No `noa` column is present in the supplied Green SAS output.
- `pm`: No `pm` column is present in the supplied Green SAS output.

## Name Mappings Used

- `chpm` was compared to Green's `chpmia` because this repository's `chpm` builder stores the industry-adjusted value.
- `rdm` was compared to Green's `rd_mve`.
- `me_ia` was compared to Green's `mve_ia`.
- `op` was compared to Green's `operprof`.
- `me` and `mvel1` were compared to Green's `mve`; inspect these carefully because Green's SAS output labels current monthly size as `mve`, while this repository's monthly size builders use an explicit lagged-size convention.
- `rvar_mean` was compared to Green's `retvol`, the available realized-return-volatility column in the supplied SAS output.

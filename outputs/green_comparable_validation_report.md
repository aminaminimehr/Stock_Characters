# Green Comparable Panel Validation

This report compares `outputs/green_comparable_temp.csv` against the supplied Green SAS output.
Both datasets are matched on `permno` and month, where the Green SAS month is derived from `DATE`.

- Python Green-comparable panel rows: 2,819,151
- Green SAS output rows: 2,273,186
- Common `permno`-month rows: 2,242,227

## Summary

| character   | green_column   |   matched_nonmissing_pairs |   overall_corr |   mean_xs_corr |   median_xs_corr | exact_4dp   | exact_3dp   | exact_2dp   |   mean_abs_diff |
|:------------|:---------------|---------------------------:|---------------:|---------------:|-----------------:|:------------|:------------|:------------|----------------:|
| acc         | acc            |                    1968210 |       0.566897 |       0.795057 |         0.866897 | 89.42%      | 89.53%      | 90.30%      |        0.01352  |
| agr         | agr            |                    2106908 |       0.08001  |       0.541269 |         0.58516  | 89.42%      | 89.45%      | 89.69%      |        0.118346 |
| baspread    | baspread       |                    2242183 |       0.980892 |       0.976905 |         0.983703 | 99.08%      | 99.10%      | 99.17%      |        0.000864 |
| bm          | bm             |                    2242227 |       0.30239  |       0.704429 |         0.775037 | 44.23%      | 45.29%      | 51.08%      |        0.115539 |
| bm_ia       | bm_ia          |                    2242227 |       0.266019 |       0.571565 |         0.601526 | 0.06%       | 1.14%       | 8.44%       |       57.3418   |
| cash        | cash           |                    2022627 |       0.9311   |       0.919696 |         0.927652 | 9.06%       | 11.46%      | 26.03%      |        0.041088 |
| cashdebt    | cashdebt       |                    2141832 |       0.698557 |       0.871557 |         0.92159  | 85.93%      | 86.11%      | 87.14%      |        0.072045 |
| cfp         | cfp            |                    2073442 |       0.325611 |       0.670247 |         0.693686 | 89.23%      | 89.28%      | 89.81%      |        0.057998 |
| chcsho      | chcsho         |                    2105944 |       0.015108 |       0.373845 |         0.212568 | 89.95%      | 90.18%      | 91.31%      |       18.7374   |
| chpm        | chpmia         |                    2067906 |       0.171465 |       0.236961 |         0.21956  | 0.41%       | 1.96%       | 10.11%      |        4.3837   |
| depr        | depr           |                    2153473 |       0.157531 |       0.465863 |         0.456537 | 91.13%      | 91.30%      | 92.54%      |        0.12574  |
| dolvol      | dolvol         |                    2167619 |       0.997627 |       0.997135 |         0.99874  | 98.47%      | 98.69%      | 98.72%      |        0.013873 |
| ep          | ep             |                    2241650 |       0.242759 |       0.67584  |         0.735513 | 90.21%      | 90.30%      | 91.15%      |        0.044604 |
| gma         | gma            |                    2101903 |       0.202223 |       0.810941 |         0.910158 | 89.46%      | 89.58%      | 90.51%      |        0.030364 |
| grltnoa     | grltnoa        |                    1605883 |       0.244869 |       0.846665 |         0.926499 | 89.64%      | 89.70%      | 90.28%      |        0.017514 |
| herf        | herf           |                    2242217 |       0.962248 |       0.964821 |         0.969541 | 1.31%       | 7.17%       | 50.94%      |        0.010905 |
| hire        | hire           |                    2102716 |       0.106807 |       0.32638  |         0.294744 | 89.77%      | 89.71%      | 90.02%      |        0.160949 |
| ill         | ill            |                    2180075 |       0.120708 |       0.569024 |         0.58056  | 99.40%      | 99.81%      | 99.99%      |        4e-06    |
| lev         | lev            |                    2236098 |       0.577729 |       0.76546  |         0.817798 | 91.05%      | 91.08%      | 91.32%      |        0.338741 |
| lgr         | lgr            |                    2099829 |       0.10274  |       0.428306 |         0.384342 | 89.41%      | 89.42%      | 89.59%      |        0.306166 |
| maxret      | maxret         |                    2242213 |       0.861564 |       0.875732 |         0.905057 | 98.14%      | 98.39%      | 98.69%      |        0.002474 |
| me          | mve            |                    2242227 |       0.999367 |       0.999228 |         0.999198 | 98.69%      | 98.93%      | 98.96%      |        0.006759 |
| me_ia       | mve_ia         |                    2242227 |       0.735844 |       0.774475 |         0.801963 | 0.96%       | 0.97%       | 1.06%       |      845.295    |
| mom12m      | mom12m         |                    2087269 |       0.893196 |       0.920289 |         0.939747 | 95.98%      | 96.48%      | 96.53%      |        0.020217 |
| mom1m       | mom1m          |                    2242227 |       0.918701 |       0.926162 |         0.945668 | 97.69%      | 97.86%      | 97.85%      |        0.004405 |
| mom36m      | mom36m         |                    1773394 |                |                |                  | 0.00%       | 0.00%       | 0.00%       |        1.32799  |
| mom6m       | mom6m          |                    2178667 |       0.913143 |       0.926227 |         0.941452 | 96.58%      | 96.83%      | 96.83%      |        0.011775 |
| mvel1       | mve            |                    2242227 |       0.999367 |       0.999228 |         0.999198 | 98.69%      | 98.93%      | 98.96%      |        0.006759 |
| op          | operprof       |                    2101879 |      -0.00523  |       0.031513 |         0.033149 | 0.05%       | 0.23%       | 1.21%       |        1.41699  |
| pctacc      | pctacc         |                    1968198 |       0.219177 |       0.398074 |         0.407443 | 89.70%      | 89.70%      | 89.74%      |        2.3731   |
| ps          | ps             |                    2106941 |       0.920777 |       0.911636 |         0.954278 | 11.65%      | 11.65%      | 11.65%      |        0.967149 |
| rd_sale     | rd_sale        |                    1077686 |       0.263019 |       0.506128 |         0.489349 | 92.57%      | 93.11%      | 95.04%      |        2.43014  |
| rdm         | rd_mve         |                    1099205 |       0.817979 |       0.88067  |         0.927275 | 92.50%      | 92.79%      | 94.28%      |        0.006849 |
| roe         | roe            |                    2106242 |       0.055181 |       0.331585 |         0.298844 | 89.42%      | 89.48%      | 90.00%      |        0.427828 |
| rvar_mean   | retvol         |                    2242209 |       0.269615 |       0.566271 |         0.593479 | 0.68%       | 0.68%       | 1.41%       |        0.031578 |
| sgr         | sgr            |                    2073101 |       0.089048 |       0.305712 |         0.301784 | 89.52%      | 89.54%      | 89.75%      |        0.514456 |
| sp          | sp             |                    2236103 |       0.762445 |       0.792792 |         0.82777  | 91.16%      | 91.18%      | 91.36%      |        0.219058 |
| std_dolvol  | std_dolvol     |                    2176898 |       0.995365 |       0.993726 |         0.995015 | 0.01%       | 0.01%       | 0.01%       |        0.475036 |
| std_turn    | std_turn       |                    2181830 |       0.111205 |       0.767877 |         0.841122 | 99.03%      | 99.03%      | 99.03%      |        1.52235  |
| turn        | turn           |                    2168375 |       0.146324 |       0.768489 |         0.857849 | 98.24%      | 98.24%      | 98.27%      |        0.210457 |
| zerotrade   | zerotrade      |                    2180085 |       0.99453  |       0.916067 |         0.995091 | 99.21%      | 99.21%      | 99.21%      |        0.021841 |

## Local Columns Not Compared

- `adm`: No `adm` column exists in the supplied Green SAS output.
- `alm`: No `alm` column exists in the supplied Green SAS output.
- `ato`: No direct `ato` column exists in the supplied Green SAS output.
- `bmj`: HXZ-specific book-to-June-market-equity variable, not a Green output column.
- `book_to_market`: HXZ-specific duplicate construction; compare `bm` for Green-style book-to-market.
- `cash_flow_to_price`: HXZ-specific duplicate construction; compare `cfp` for Green-style cash-flow-to-price.
- `noa`: No `noa` column exists in the supplied Green SAS output.
- `operating_profitability`: HXZ-specific duplicate construction; compare `op` to Green's `operprof`.
- `pm`: No `pm` column exists in the supplied Green SAS output.

## Name Mappings Used

- `chpm` -> Green `chpmia`.
- `me_ia` -> Green `mve_ia`.
- `op` -> Green `operprof`.
- `rdm` -> Green `rd_mve`.
- `rvar_mean` -> Green `retvol`.
- `me` and `mvel1` -> Green `mve`.

#%%
import os
os.chdir('Stock_Characters')

import wrds
import pandas as pd
from functions import *
#%%
db = wrds.Connection(user='aminaminimehr')

# Book Equity Components from Compustat
# gvkey    : This item is a unique identifier and primary key for each company in the database.
# datadate : The date at which the fiscal year ends and the report shows the condition of the firm/company as of that date.
# fyear    : This variable might sound complicated at first. So see the guideline below:
# Fiscal Year labeling rule (WRDS):
# Early year-end (Jan–May) → shift back one year
# Late year-end (Jun–Dec) → keep same year
# Rationale: fiscal year is assigned to the year where most operations occur,
# not the reporting date. 

# Important relationship : 
# If month(datadate) ≤ 5 (Jan–May) → Fiscal Year = year(datadate) - 1  
# If month(datadate) ≥ 6 (Jun–Dec) → Fiscal Year = year(datadate)

# seq      : Stock holder's equity.
# ceq      : Common/Ordinary Equity - Total.
# at       : Assets - Total.
# lt       : Liabilities - Total.

# pstk     : Preferred/Preference Stock (Capital) - Total.
# pstkl    : Preferred Stock - Liquidating Value.
# pstkrv   : Preferred Stock - Redemption Value.

# txditc   : Deferred Taxes and Investment Tax Credit.

# This query is temporary - I have limited the date range to try to match with datashare.csv file. I will remove the date range limit later on.
comp = db.raw_sql("""
    SELECT gvkey, datadate, fyear,
           seq, ceq, at, lt,
           pstk, pstkl, pstkrv, 
           txditc
    FROM comp.funda
    WHERE indfmt='INDL'
      AND datafmt='STD'
      AND popsrc='D'
      AND consol='C'
      AND datadate BETWEEN '1957-01-31' AND '2021-12-31'
""")
comp['datadate'] = pd.to_datetime(comp['datadate'])
comp.sort_values(['gvkey', 'datadate'], inplace=True)

# sic     : Industry code.
# sic is not directly available on compustat fundamental table. Instead, it is available at company tabl in the same compustat dataset.
comp_names = db.raw_sql("""
    SELECT gvkey, sic
    FROM comp.company
""")

# We need to merge the two to add sic to the compustat table
comp = comp.merge(comp_names, on='gvkey', how='left')

# Below is how Book Equity is calculated using Hou, Xiu and Zhang's documentaion. (Whenever you need Book Equity  you need to do all of the following.)
#################################################################################################################################################################
# Constructing the par value of the preffered stock (Will be used
#  in calculating book equity(be)) 
comp['ps'] = comp['pstkrv'] # Either using item PSTKRV (Preferred stock at redemption value)
comp['ps'] = comp['ps'].fillna(comp['pstkl']) # Or using PSTKL (Preferred stock at liquidating value)
comp['ps'] = comp['ps'].fillna(comp['pstk']) # Or using PSTK (preferred stock measured at its par (book) value)
# for the PS part it is exactly matching Dachen's python code


# Construct SEQ (Stockholders Equity)  fallback. We name it fallback because it check from the very ideal case for data avilability
# upto other alternatives that might not be very ideal. However, they can fill the missing values for this character. 
comp['seq_fallback'] = comp['seq'] # use SEQ if available (First see if stock holders equity is available itself)
comp.loc[comp['seq_fallback'].isna(), 'seq_fallback'] = comp['ceq'] + comp['ps'] # If not avialble use CEQ + PS (If stock holders equity is not available, add common equity
# and preffered stock that you calculated above.)
comp.loc[comp['seq_fallback'].isna(), 'seq_fallback'] = comp['at'] - comp['lt'] # If not avialble use AT - LT ( If ceq or ps were missing, you can use total assets minus total liabilities.)
# for the SEQ part which we renamed it as SEQ fall_back it is different to Dachen's code. 
# Dachen only uses SEQ and the rest is missing which will be next replaced with industry median. 



# Fill the missing values of Balance Sheet Taxes and Investment Tax Credit
# This item is the amount of tax that has not left the company yet and it is deferred to 
# a later time to be paind
comp['txditc'] = comp['txditc'].fillna(0)

# Book Equity
comp['be'] = comp['seq_fallback'] + comp['txditc'] - comp['ps']
# BE in this line matches Dachen's code but as noted above, SEQ (a component of BE) is not the same.
#################################################################################################################################################################
# Exclude nonpositive BE
# First time a drop happens and observations are dropped is when we drop the negative and zero book equity observations. This is because they can lead to infinite or negative BM ratios which are not meaningful.
comp = comp[comp['be'] > 0]

#################################################################################################################################################################
# Date Fixing (Hou, Xeu and Zhang have mentioned the following for the data of Book Equity in calculating BM ratio:
#At the end of June of each year t, we split stocks into deciles on Bm, the book equity for the fiscal
#year ending in calendar year t−1 divided by the market equity (from CRSP) at the end of December
#of t−1.)

comp['be'] = comp['be']*1000 # We need to multiply by 1000 because the book equity is in thousands in compustat.

comp['year'] = comp['datadate'].dt.year # We isolate the year element of datadate here. 
# (important:) datadate is “what date this accounting data describes, when the fiscal year ends” not when it became public.
comp['chars_year'] = comp['year'] + 1  # this is year t

#################################################################################################################################################################

# This is for situations when a firm has updated its fiscal year end date and therefore has multiple observations for the same fiscal year. In this case, we keep the last available observation.
comp.sort_values(['gvkey', 'datadate'], inplace=True)
comp.drop_duplicates(subset=['gvkey', 'year'], keep='last', inplace=True)



# Downloading market data to calculate the denominator of BM which is market equity.
# Building guidline for market equity itself is never explicitely mentioned in Hou Xeu and Zhang. But it seems to be very straightforward. 
# So we just need the last available (non-zero) observaitions for the end of December.

# Market Equity Components from Compustat
# permno    : << compustat has not provided an exact description for this variable >>.
# permco    :  is a unique permanent identifier assigned by CRSP to all companies with issues on a CRSP file.
# date      : Date of Observation.
# prc       : Prc is the closing price or the negative bid/ask average for a trading day. If the closing price is 
# not available on any given trading day, the number in the price field has a negative sign to indicate that it is a
# bid/ask average and not an actual closing price
# shrout    : is the number of publicly held shares, recorded in thousands.

crsp = db.raw_sql("""
    SELECT permno, permco, date, prc, shrout
    FROM crsp.msf
""")

crsp['date'] = pd.to_datetime(crsp['date'])
crsp['year'] = crsp['date'].dt.year
crsp['month'] = crsp['date'].dt.month

# Keep December observations only
# Based on Hou, Xeu and Zhang At the end of June of each year t, we split stocks into deciles on Bm, the book equity for the fiscal
# year ending in calendar year t−1 divided by the market equity (from CRSP) at the end of December
# of t−1.)

crsp = crsp.sort_values(['permno', 'date'])

# Forward-fill price and shares within each stock
crsp[['prc_ffill', 'shrout_ffill']] = (
    crsp
    .groupby('permno')[['prc', 'shrout']]
    .ffill()
)

# Keep December observations after filling
crsp_dec = crsp[crsp['month'] == 12].copy()

# Calculate December market equity using filled values
crsp_dec['me'] = crsp_dec['prc_ffill'].abs() * crsp_dec['shrout_ffill']

# Drop observations where even forward-fill could not recover values
crsp_dec = crsp_dec[crsp_dec['me'].notna()].copy()

# Aggregate to firm level using PERMCO
crsp_firm_me = (
    crsp_dec
    .groupby(['permco', 'year'], as_index=False)['me']
    .sum()
)


# Date adjustment for the market equity. We need the market equity data from December of year t-1 to be matched with the 
# the book equity data from t-1. so here also we have to create the "chars_year" column as we did for compustat data.
crsp_firm_me['chars_year'] = crsp_firm_me['year'] + 1
crsp_firm_me.drop(columns=['year'], inplace=True)

# ((((((((((((((((((No commenting has bee done from here onwards. I need to come back later.))))))))))))))))

# Now we need to link the CRSP table with compustat table
link = db.raw_sql("""
    SELECT gvkey, lpermno AS permno, lpermco AS permco,
           linkdt, linkenddt
    FROM crsp.ccmxpf_linktable
    WHERE linktype IN ('LU','LC')
      AND linkprim in ('P' , 'C')
""")

link['linkdt'] = pd.to_datetime(link['linkdt'])
link['linkenddt'] = pd.to_datetime(link['linkenddt'])

link['permno'] = link['permno'].astype('Int64')
link['permco'] = link['permco'].astype('Int64')

comp_linked = pd.merge(comp, link, on='gvkey', how='left')

comp_linked = comp_linked[
    (comp_linked['datadate'] >= comp_linked['linkdt']) &
    ((comp_linked['datadate'] <= comp_linked['linkenddt']) |
     comp_linked['linkenddt'].isna())
]
# we need link end data because the links end for some of the connections. so we need to
# account for that



# Now we need to merge or attach the CRSP data of December to have the denominator
# of Book To Market Ratio


bm = pd.merge(
    comp_linked,
    crsp_firm_me,
    left_on=['permco', 'chars_year'],
    right_on=['permco', 'chars_year'],
    how='inner'
)
'''

# Code by ChatGPT below
bm = pd.merge(
    comp_linked,
    crsp_dec,
    on=['permno', 'chars_year'],
    how='inner',
    suffixes=('', '_crsp')
)

# Code by ChatGPT above
'''



# Finally we can calculate the BM ( Book to Market Ratio).
bm = bm[bm['me'] > 0] # We do this to avoid infinity BMs
bm['bm'] = bm['be'] / bm['me']


# Final Data avaialble to save
bm_semifinal = bm[['gvkey', 'permno', 'permco', 'sic' , 'chars_year', 'be', 'me', 'bm']].copy()

# Final Data ready to convert into monthly data
bm_monthly = bm_semifinal.copy()
bm_monthly['chars_year'] = bm_monthly['chars_year'].astype(int)

bm_monthly['date'] = bm_monthly['chars_year'].apply(
    lambda y: pd.date_range(
        start=pd.Timestamp(year=y, month=7, day=31),
        periods=12,
        freq='ME'
    )
)

bm_monthly = bm_monthly.explode('date').reset_index(drop=True)

# Book too market ratio of industry (Using 49 category industry code)
bm_monthly['sic'] = bm_monthly['sic'].astype('Int64')
bm_monthly['ffi49'] = ffi49(bm_monthly)
bm_monthly['bm_ia49'] = bm_monthly.groupby(['chars_year' , 'ffi49'])['bm'].transform('mean')
bm_monthly['bm_ia49'] = bm_monthly['bm'] - bm_monthly['bm_ia49']

# Book too market ratio of industry (Using 30 category industry code)
bm_monthly['sic'] = bm_monthly['sic'].astype('Int64')
bm_monthly['ffi30'] = ffi30(bm_monthly)
bm_monthly['bm_ia30'] = bm_monthly.groupby(['chars_year' , 'ffi30'])['bm'].transform('mean')
bm_monthly['bm_ia30'] = bm_monthly['bm'] - bm_monthly['bm_ia30']

# Book too market ratio of industry (Using 12 category industry code)
bm_monthly['sic'] = bm_monthly['sic'].astype('Int64')
bm_monthly['ffi12'] = ffi12(bm_monthly)
bm_monthly['bm_ia12'] = bm_monthly.groupby(['chars_year' , 'ffi12'])['bm'].transform('mean')
bm_monthly['bm_ia12'] = bm_monthly['bm'] - bm_monthly['bm_ia12']

# Book too market ratio of industry (Using first 2 digit category industry code)
bm_monthly['sic2'] = bm_monthly['sic'] // 100
bm_monthly['bm_ia_sic2'] = bm_monthly.groupby(['chars_year' , 'sic2'])['bm'].transform('mean')
bm_monthly['bm_ia_sic2'] = bm_monthly['bm'] - bm_monthly['bm_ia_sic2']




bm_final = bm_monthly[['gvkey', 'permno', 'permco', 'sic' , 'chars_year', 'be', 'me', 'bm' , 'bm_ia_sic2', 'bm_ia12','bm_ia30' ,'bm_ia49']]
# Saving the file
bm_final.to_csv('BM_and_BM_ind_ratio.csv')


# %%

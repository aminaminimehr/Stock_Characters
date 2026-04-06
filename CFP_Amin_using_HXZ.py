#%%
import wrds
import pandas as pd
from functions import *
#%%
db = wrds.Connection(user='aminaminimehr')


# Book Equity Components from Compustat
# gvkey    : This item is a unique identifier and primary key for each company in the database.
# datadate : The date at which the fiscal year ends and the report shows the condition of the firm/company as of that date.
# fyear    : This variable might sound complicated at first. So see the guideline below:

# ib      : This item represents the income of a company after all expenses, including special items, income taxes, and minority interest,
# but before provisions for common and/or preferred dividends.
# dp      : This item represents non-cash charges for obsolescence of and wear and tear on property, allocation of the current portion of 
# capitalized expenditures, and depletion charges.


comp = db.raw_sql("""
    SELECT gvkey, datadate, fyear,
           ib, dp 
    FROM comp.funda
    WHERE indfmt='INDL'
      AND datafmt='STD'
      AND popsrc='D'
      AND consol='C'
""")

comp['datadate'] = pd.to_datetime(comp['datadate'])

# sic     : Industry code.
# sic is not directly available on compustat fundamental table. Instead, it is available at company tabl in the same compustat dataset.
comp_names = db.raw_sql("""
    SELECT gvkey, sic
    FROM comp.company
""")

# We need to merge the two to add sic to the compustat table
comp = comp.merge(comp_names, on='gvkey', how='left')

# numerator of the Cash Flow to price ratio.

# If there is missing dp we can replace this with 0 based on Green's code.
# But HXZ have not adressed this situtation.
comp['dp'] = comp['dp'].fillna(0)
comp['cfp_num'] = comp["ib"] + comp["dp"]

# Based on HXZ Firms with nonpositive cash flows are excluded.
comp = comp[comp["cfp_num"] >= 0]


# Date Fixing (Hou, Xeu and Zhang have mentioned the following for the data of Cash flow to price ratio in calculating BM ratio:
# At the end of June of each year t, we split stocks into deciles on Cash flow to price ratio, the cash flow for the fiscal
# year ending in calendar year t−1 divided by the market equity (from CRSP) at the end of December
# of t−1.)
comp['year'] = comp['datadate'].dt.year # We isolate the year element of datadate here. 
# (important:) datadate is “what date this accounting data describes, when the fiscal year ends” not when it became public.
comp['chars_year'] = comp['year'] + 1  # this is year t



# Downloading market data to calculate the denominator of CFP which is market equity.
# Building guidline for market equity itself is never explicitely mentioned in Hou Xeu and Zhang. But it seems to be very straightforward. 
# So we just need the observaitions for the end of December.

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


crsp_dec = crsp[crsp['month'] == 12].copy() 
# To get the data for the last trading day of december we need to first sort the data.
crsp_dec = crsp_dec.sort_values(['permno', 'date'])
# Now we keep just the last available observation of december.
crsp_dec_last = crsp_dec.groupby('permno').tail(1)

# Now we calculate the market equity value for each stock not for each company. Because each company might have issued different
# stocks.
crsp_dec_last['me'] = crsp_dec_last['prc'].abs() * crsp_dec_last['shrout']

# Now we aggregate the ME character to create a firm level characteristic because a company might 
# have issued different stocks so their PERMCO helps us aggregate them
crsp_dec = crsp_dec_last.groupby(['permco', 'year'])['me'].sum().reset_index()


# Date adjustment for the market equity. We need the market equity data from December of year t-1 to be matched with the 
# the book equity data from t-1. so here also we have to create the "chars_year" column as we did for compustat data.
crsp_dec['chars_year'] = crsp_dec['year'] + 1 #This is year t

# ((((((((((((((((((No commenting has bee done from here onwards. I need to come back later.))))))))))))))))

# Now we need to link the CRSP table with compustat table
link = db.raw_sql("""
    SELECT gvkey, lpermno AS permno, lpermco AS permco,
           linkdt, linkenddt
    FROM crsp.ccmxpf_linktable
    WHERE linktype IN ('LU','LC')
      AND linkprim = 'P'
""")

link['linkdt'] = pd.to_datetime(link['linkdt'])
link['linkenddt'] = pd.to_datetime(link['linkenddt'])

comp_linked = pd.merge(comp, link, on='gvkey', how='left')

comp_linked = comp_linked[
    (comp_linked['datadate'] >= comp_linked['linkdt']) &
    ((comp_linked['datadate'] <= comp_linked['linkenddt']) |
     comp_linked['linkenddt'].isna())
]
# we need link end data because the links end for some of the connections. so we need to
# account for that.



# Now we need to merge or attach the CRSP data of December to have the denominator
# of Cash Flow to Price ratio.
cfp = pd.merge(
    comp_linked,
    crsp_dec,
    left_on=['permco', 'chars_year'],
    right_on=['permco', 'chars_year'],
    how='inner'
)

# When merges happen between datasets the missing values in these two columns cannot be stored
# in an integer column (Pandas rule) therefore it automatically turns them into
# float. So, here we need to turn them back into integers. 
cfp['permno'] = cfp['permno'].astype('Int64')
cfp['permco'] = cfp['permco'].astype('Int64')

# Finally we can calculate the cfp (Cash Flow to Price Ratio).
cfp = cfp[cfp['me'] > 0] # We do this to avoid infinity Cash Flow to Price ratio.
cfp['cfp'] = cfp['cfp_num'] / cfp['me']


# Final Data avaialble to save
cfp_semifinal = cfp[['gvkey', 'permno', 'permco', 'sic' , 'chars_year', 'cfp_num', 'me', 'cfp']]


# Cash Flow to Price ratio of industry (Using 49 category industry code)
cfp_semifinal['sic'] = cfp_semifinal['sic'].astype('Int64')
cfp_semifinal['ffi49'] = ffi49(cfp_semifinal)
cfp_semifinal['cfp_ia49'] = cfp_semifinal.groupby(['chars_year' , 'ffi49'])['cfp'].transform('mean')
cfp_semifinal['cfp_ia49'] = cfp_semifinal['cfp'] - cfp_semifinal['cfp_ia49']

# Cash Flow to Price ratio of industry (Using 30 category industry code)
cfp_semifinal['sic'] = cfp_semifinal['sic'].astype('Int64')
cfp_semifinal['ffi30'] = ffi30(cfp_semifinal)
cfp_semifinal['cfp_ia30'] = cfp_semifinal.groupby(['chars_year' , 'ffi30'])['cfp'].transform('mean')
cfp_semifinal['cfp_ia30'] = cfp_semifinal['cfp'] - cfp_semifinal['cfp_ia30']

# Cash Flow to Price ratio of industry (Using 12 category industry code)
cfp_semifinal['sic'] = cfp_semifinal['sic'].astype('Int64')
cfp_semifinal['ffi12'] = ffi12(cfp_semifinal)
cfp_semifinal['cfp_ia12'] = cfp_semifinal.groupby(['chars_year' , 'ffi12'])['cfp'].transform('mean')
cfp_semifinal['cfp_ia12'] = cfp_semifinal['cfp'] - cfp_semifinal['cfp_ia12']

# Cash Flow to Price ratio of industry (Using first 2 digit category industry code)
cfp_semifinal['sic2'] = cfp_semifinal['sic'] // 100
cfp_semifinal['cfp_ia_sic2'] = cfp_semifinal.groupby(['chars_year' , 'sic2'])['cfp'].transform('mean')
cfp_semifinal['cfp_ia_sic2'] = cfp_semifinal['cfp'] - cfp_semifinal['cfp_ia_sic2']




cfp_final = cfp_semifinal[['gvkey', 'permno', 'permco', 'sic' , 'chars_year', 'cfp_num', 'me', 'cfp' , 'cfp_ia_sic2', 'cfp_ia12','cfp_ia30' ,'cfp_ia49']]
# Saving the file
cfp_final.to_csv('CFP_and_CFP_ind_ratio.csv')

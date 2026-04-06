# First important point is that OPERPROF is not just operational proft. 
# It is operational profit divided by book equity.
# In the code from green's and Dachen's the denominator which is book equity 
# they have used ceq as the only element representing book equity. We replace 
# it with what HXZ have described in their documentation for book equity.
# Furthermore, HXZ have emphasized in their documentation that the denominator
# should be the corresponding years equity and not the lag while both green and
# dachen have used the lag of equity component. We follow HXZ and use the 
# corresponding year of the numerator.
#%%
import wrds
import pandas as pd
#%%

db = wrds.Connection(user='aminaminimehr')

comp = db.raw_sql("""
    SELECT gvkey, datadate, fyear,
           revt, cogs, xsga, xint,
                  
           seq, ceq, at, lt,
           pstk, pstkl, pstkrv,
           txditc
                  
    FROM comp.funda
    WHERE indfmt='INDL'
      AND datafmt='STD'
      AND popsrc='D'
      AND consol='C'
""")
comp['datadate'] = pd.to_datetime(comp['datadate'])

# sic is available in another table called company in compustat
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
# This item is the amount oftax that has not left the company yet and it is deferred to 
# a later time to be paind
comp['txditc'] = comp['txditc'].fillna(0)

# Book Equity
comp['be'] = comp['seq_fallback'] + comp['txditc'] - comp['ps']
# BE in this line matches Dachen's code but as noted above, SEQ (a component of BE) is not the same.




# Up to now we have the Book Equity. Now we construct the numerator which is operational profitability itself.
# Replace missing components with 0 (as per definition)
cogs0 = comp['cogs'].fillna(0)
xsga0 = comp['xsga'].fillna(0)
xint0 = comp['xint'].fillna(0)

# Compute operating profitability numerator
comp['operprof_num'] = comp['revt'] - cogs0 - xsga0 - xint0

# If ALL three components (cogs, xsga, xint) are missing,
# then set operating profitability to NA (since nothing is observed). HXZ suggested that
# at least one of the components COGS, XSGA or XINT must be available. So:
mask_all_missing = comp['cogs'].isna() & comp['xsga'].isna() & comp['xint'].isna()
comp.loc[mask_all_missing, 'operprof_num'] = pd.NA



# Now we can divide operating profits to Book Equity which is referred to as operprof in GKX.
comp['operprof'] = comp['operprof_num'] / comp['be']

# Exclude nonpositive BE's to both avoid infinity OPERPROF and 
# to exclude companies with negative Book Equity.
comp = comp[comp['be'] > 0]

# Date Fixing (we fix the data as if the data in time t-1 is available at t to be used to predict t+1)
comp['year'] = comp['datadate'].dt.year # We isolate the year element of datadate here 
# (important:) datadate is “what date this accounting data describes,” not when it became public.
comp['chars_year'] = comp['year'] + 1  # this is year t



# Just to have permno and permco in the final table we download the crsp data too
crsp = db.raw_sql("""
    SELECT permco, date
    FROM crsp.msf
""")

crsp['date'] = pd.to_datetime(crsp['date'])
crsp['year'] = crsp['date'].dt.year



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



operprof_semifinal = pd.merge(
    comp_linked,
    crsp,
    left_on=['permco' , 'year'],
    right_on=['permco', 'year'],
    how='inner'
)

# When merges happen between datasets the missing values in these two columns cannot be stored
# in an integer column (Pandas rule) so it automatically turns it into
# float. So, here we need to turn them back into float. 
operprof_semifinal['permno'] = operprof_semifinal['permno'].astype('Int64')
operprof_semifinal['permco'] = operprof_semifinal['permco'].astype('Int64')


operprof_final = operprof_semifinal[['gvkey', 'permno', 'permco', 'sic' , 'chars_year', 'operprof_num' , 'be' , 'operprof']]
operprof_final = operprof_final.drop_duplicates() # I have an issue in the merge section 
# when I add the tables to crsp table and it should be fixed
# to avoid having duplicates.


operprof_final.to_csv('OPERPROF.csv')
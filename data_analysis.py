import pandas as pd
import numpy as np
import hvplot.pandas
import matplotlib.pyplot as plt
import warnings
from IPython.display import HTML, Image
import re

# reclassify and explore data
plays_all = pd.read_parquet('plays.parq')
plays_all.set_index(['GameKey', 'PlayID'], inplace=True)

# set up outcomes dataframe
outcomes = pd.DataFrame({'PlayDescription': plays_all.PlayDescription},
                        index=plays_all.index)

# create punt type dictionary
punttypes = {'not_punted':      ['no play','delay of game', 'false start',
                                 'blocked','incomplete'],
             'out_of_bounds':   ['out of bounds'],
             'downed':          ['downed'],
             'touchback':       ['touchback'],
             'fair_catch':      ['fair catch'],
             'returned':        ['no gain', 'for (.*) yard']
             }

# 
with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    for k,v in punttypes.items():
        outcomes[k] = outcomes.PlayDescription.str.contains('|'.join(v),
                    case=False, regex=True).astype(int)
    
# correct for multiple outcomes in one play
outcomes['typesum'] = outcomes[list(punttypes.keys())].sum(axis=1)
outcomes.loc[outcomes.PlayDescription.str.contains("punts", case=False, 
            regex=False), 'not_punted'] = 0
outcomes.loc[~outcomes.PlayDescription.str.contains("punts", case=False, 
            regex=False), 'out_of_bounds':'returned'] = 0
outcomes.loc[~outcomes.PlayDescription.str.contains("punts", case=False, 
            regex=False), 'not_punted'] = 1

outcomes['typesum'] = outcomes[list(punttypes.keys())].sum(axis=1)
outcomes.loc[outcomes.typesum == 0, 'returned'] = 1

outcomes['typesum'] = outcomes[list(punttypes.keys())].sum(axis=1)
outcomes.loc[(outcomes.PlayDescription.str.contains("invalid fair catch", 
            case=False, regex=False)) & (outcomes.returned == 1) & 
            (outcomes.typesum == 2), 'fair_catch'] = 0

outcomes['typesum'] = outcomes[list(punttypes.keys())].sum(axis=1)
outcomes.loc[(outcomes.PlayDescription.str.contains("punts", case=False, 
            regex=False)) & (outcomes.returned == 1) & (outcomes.typesum 
            == 2), 'not_punted':'out_of_bounds'] = 0

outcomes['typesum'] = outcomes[list(punttypes.keys())].sum(axis=1)
outcomes.loc[outcomes.PlayDescription.str.contains("blocked", case=False, 
            regex=False), 'out_of_bounds':'returned'] = 0

outcomes['typesum'] = outcomes[list(punttypes.keys())].sum(axis=1)
outcomes.loc[outcomes.typesum == 0, 'not_punted'] = 1 

outcomes['typesum'] = outcomes[list(punttypes.keys())].sum(axis=1)
outcomes.loc[(outcomes.touchback == 1) & (outcomes.typesum == 2), 
            'out_of_bounds':'downed'] = 0
outcomes.loc[(outcomes.returned == 1) & (outcomes.typesum == 2), 
            'returned'] = 0
outcomes.loc[(outcomes.fair_catch == 1) & (outcomes.typesum == 2), 
            'out_of_bounds':'downed'] = 0
outcomes.loc[(outcomes.downed == 1) & (outcomes.typesum == 2), 
            'out_of_bounds'] = 0

outcomes.drop(['PlayDescription', 'typesum'], axis=1, inplace=True)

plays_all['outcome'] = outcomes.dot(outcomes.columns).values #condense

# pull out yardage for returned punts
plays_all['yardage'] = plays_all.PlayDescription.str\
            .extract("for (.{1,3}) yard")
plays_all.loc[plays_all.yardage.isnull(), 'yardage'] = 0
plays_all.loc[plays_all.outcome != "returned", 'yardage'] = 0

# format for plotting
crosstable = pd.crosstab(plays_all.outcome, plays_all.concussion).reset_index()\
    .sort_values(1, ascending=False)
crosstable.columns = ['Play_Outcome','Zero_Concussions', 'Concussions']
crosstable['Pct_of_Type'] = crosstable.Concussions/(crosstable.Concussions\
                + crosstable.Zero_Concussions)*100
    
# plot simple looks at concussions by play type                
plt.bar(crosstable.Play_Outcome, height=crosstable.Concussions)
plt.bar(crosstable.Play_Outcome, height=crosstable.Pct_of_Type)
                
# display table of concussions by play type
crosstable['Pct_of_Type'] = (crosstable.Pct_of_Type/100).apply('{:.2%}'.format)
crosstable['Play_Outcome'] = crosstable.Play_Outcome.str.title()
ctable = crosstable.sort_values('Concussions', ascending=False).set_index('Play_Outcome')

### Findings:
    ### Most concussions occur on a play that sees a punt returned
    ### Concussions could most likely be reduced from a shift in play types
    ### from returned to any other type of play.
    
### How to incentivize other types? 
    ### Fair Catch
        ### (1) Give yards on fair catch
        ### (2) Don't allow returns (only fair catch)
    ### Touchback
        ### (1) Automatic touchback if within XX yards of endzone
        ### (2) More/less yards?
        ### (3) Fair catch within 20 awards yards?
        
        
####### FAIR CATCH #######
### Give Yards on Fair Catch ###

# how many? explore median for all return plays
returns = plays_all.loc[(plays_all.outcome == 'returned') & 
                        (~plays_all.PlayDescription.str.contains("MUFFS")),
                        ['outcome', 'yardage','concussion','Rec_team']]\
                        .sort_values('Rec_team')
                        
returns['yardage'] = returns.yardage.astype(int)
returns_median = returns.yardage.median()
print('Return yards median:', returns_median)

# A rule giving 8 yards for a fair catch would make the player indifferent to
# calling for a fair catch. To incentivize we need more than 8 yards. Since 9
# yards is a bit arbitrary we will round up to an even 10. 
## PROPOSED RULE: A fair catch places the ball 10 yards from the spot of the 
## catch.

### Don't Allow Returns ###

# Allow punts but only allow 3 outcomes: downed, fair catch, touchback.
## PROPOSED RULE: Punts can only be downed, fair caught or kicked into the
## endzone for a touchback. If a fair catch is called, place the ball 8 yards 
## from the spot of the catch.

####### TOUCHBACK #######
### Automatic Touchback ###

# how many yards to give auto-touchback?
# find if ball punted more than once (due to penalty)
plays_all['punt_count'] = plays_all.PlayDescription.str.count("punts")
# extract distance
punt_distances = plays_all.PlayDescription.str.extractall(r"(punts?\s)(\d\d?)?")
punt_distances.fillna(0, inplace=True)
plays_all['punt_distance'] = 5

for key, ID in plays_all.index:
    if plays_all.loc[key].loc[ID].punt_count == 0:
        plays_all['punt_distance'].loc[key].loc[ID] = 0
    elif plays_all.loc[key].loc[ID].punt_count == 2:
        plays_all['punt_distance'].loc[key].loc[ID] = int(punt_distances.loc[key].loc[ID][1][1])
    else:
        plays_all['punt_distance'].loc[key].loc[ID] = int(punt_distances.loc[key].loc[ID][1][0])

# median and 80th percentile punt distance
punt_dist_median = plays_all.punt_distance.median()
percentile_10 = np.percentile(plays_all.punt_distance.values, 10)
print('Punt distance median:', punt_dist_median)
print('Punt distance 10th percentile:', percentile_10)

# Since 90% of unblocked punts travel at least 32 yards, a "free touchback"
# should be awarded to a team if they are within 35 yards (rounding up) of the
# endzone. Coincidentally, this is the average field goal range limit among
# NFL kickers. 
# Source: https://en.wikipedia.org/wiki/Field_goal_range#:~:text=Average%20field%20goal%20range,-The%20exact%20field&text=For%20most%20NFL%20kickers%2C%20the,of%20their%20field%20goal%20range.

# Find percent of kicks downed within the 20 yard line

# first find yard line for returned punts
returned_plays_all = plays_all.loc[plays_all.outcome == 'returned'][['outcome','PlayDescription']]
# temp = returned_plays_all.PlayDescription.str.extractall(r'([A-Z]{2,3}\s\d\d?)(\sfor)')
temp = returned_plays_all.PlayDescription.str.extractall(r'(\d\d?)(\sfor)')
temp['yard_line'] = [float(x) for x in temp[0]]
temp.reset_index(level=2, drop=True, inplace=True)
temp = temp['yard_line']

# next find yard line for fair_catch, oob, and downed
faircatch_oob_plays = plays_all.loc[(plays_all.outcome == 'fair_catch') | 
                                    (plays_all.outcome == 'out_of_bounds') |
                                    (plays_all.outcome == 'downed') , 
                                    ['outcome', 'PlayDescription']]
                                    
temp2 = faircatch_oob_plays.PlayDescription.str.extractall(r'([A-Z]{2,3}\s\d\d?)')
temp2.reset_index(level=2, drop=False, inplace=True)
temp2 = temp2[temp2['match'] == 0]
temp2['yard_line'] = [float(x.split()[1]) for x in temp2[0]]
temp2.drop('match', axis=1, inplace=True)
temp2 = temp2['yard_line']

merged_temp = pd.merge(temp, temp2, how='outer',
                       left_index=True,right_index=True)

merged_temp['yard_line_x'].fillna(merged_temp['yard_line_y'], inplace=True)
merged_temp['yard_line'] = merged_temp['yard_line_x']
merged_temp.drop(['yard_line_x','yard_line_y'], axis=1, inplace=True)
merged_temp = merged_temp[~merged_temp.index.duplicated(keep='first')]

plays_all = pd.merge(plays_all, merged_temp, how='left',
                     left_index=True, right_index=True)

# fill in 20 yards for touchback
plays_all.loc[plays_all.outcome == 'touchback', 'yard_line'] = 20
# fill in 0 for not punted
plays_all.loc[plays_all.outcome == 'not_punted', 'yard_line'] = 0
# fill in -99 for return TD
plays_all.loc[plays_all.PlayDescription\
              .str.contains('TOUCHDOWN.', regex=True, case=True)
              ,'yard_line'] = 100

# clean up nulls
# all null downed, fair_catch, oob = 50
plays_all.loc[(plays_all.outcome == ['downed','fair_catch','out_of_bound']) &
              (plays_all.yard_line.isnull())
              , 'yard_line'] = 50

# nan_yards = plays_all[plays_all['yard_line'].isnull()]
# nan_plays_index = nan_yards.index
# plays_all.iloc[nan_plays_index].loc[plays_all.outcome==['downed','fair_catch','out_of_bound'], 'yard_line'] = 50
plays_all.loc[((plays_all.outcome == 'fair_catch') | 
              (plays_all.outcome == 'out_of_bounds') |
              (plays_all.outcome == 'downed')) &
              (plays_all.yard_line.isnull()),
              'yard_line'] = 50

# fill remaining nulls with -1 (for undetermined)
plays_all.yard_line.fillna(-1, inplace=True)

# remove temp tables
del temp, temp2, merged_temp

# Finally, find % of kicks downed within 20 yard line
punt_results = plays_all[plays_all.yard_line > 0]
downed_20 = (sum(punt_results.yard_line < 20)/len(punt_results))
print('{:.0%}'.format(downed_20), 'of punts were downed within the 20 yard line')

# of the "better" punts, what's their median position?
median_pos = punt_results[punt_results.yard_line<20]['yard_line'].median()
print('The median position of a punt better than a touchback is the', 
      '{:}'.format(median_pos), 'yard line.')

# Almost a third of all punts were downed within the 20 yard line. In other
# words, 1/3 of punts were better for the kicking team than the result of a 
# touchback. Therefore, to incentivize the team to take an autotouchback, we 
# should place the ball inside the 20 yard line. The median placement of all 
# punts that were better than a touchback was at the 12 yard line. Therefore,
# the ball should be placed at the 12 yard line. This will result in better
# field position than 2/3 of punts and better than 50% of punts that are downed
# within the 20 yard line. 
## PROPOSED RULE: If an autotouchback is elected by the kicking team, the ball
## will be placed at the 12 yard line.

### Adjust Touchback Yardage? ###
# (1) Would awarding touchbacks less yards incentivize more touchbacks to be
# kicked and therefore less returns?
# (2) Would awarding touchbacks more yards incentivize teams to attempt less 
# returns and instead hope the ball bounces into the endzone for a touchback?

## (1) Less Yards ##
# Earlier analysis showed that 1/3 of punts are better than a touchback and
# that 50% of those punts ended up at the 12 yard line. We will recycle these
# findings to say that a touchback places the ball at the 12 yard line.
# Question: Will this actually increase the kicking team's proclivity to kick
# the ball into the endzone, or will it instill a "what have we got to lose?"
# attitude?

# (2) More Yards? ##
# Earlier analysis showed that 50% of punts were returned for 8 yards. If a 
# touchback was placed at the 28-yard line, it could incentivize returners to
# elect to not attempt a return and instead let the ball travel beyond them in
# hopes that it sails into the endzone.
# Question: Will this incentivize the kicking team's strategy/methodology of
# kicks and result in kicks that are optimally placed to force a return?
## With the luxury of foresight, we know this is true, so adding yards to a 
## touchback is not a good idea! (25 yard tb introduced in NFL in 2018)

### Fair Catch Within 20 Awards Yards? ###

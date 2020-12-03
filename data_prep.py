## Data import and prep script lifted from notebook from jpmiller on Kaggle
## Source: https://www.kaggle.com/jpmiller/nfl-data-preparation


# import
import numpy as np
import pandas as pd
import dask.dataframe as dd


# Next Gen Stats data
ndtypes = {'GameKey': 'int16',         
           'PlayID': 'int16',         
           'GSISID': 'float32',        
           'Time': 'str',         
           'x': 'float32',         
           'y': 'float32',         
           'dis': 'float32',
           'o': 'float32',
           'Event': 'str'}

nddf = dd.read_csv('NGS/*', 
                usecols=[n for n in ndtypes.keys()], dtype=ndtypes)

meta = ('Time', 'datetime64[ns]')
nddf['Time'] = nddf.Time.map_partitions(pd.to_datetime, meta=meta)
nddf['GSISID'] = nddf.GSISID.fillna(-1).astype('int32')

nddf = nddf.compute()
nddf.to_parquet('NGS.parq')

# player level data
players = pd.read_csv('play_player_role_data.csv')
descr = pd.read_csv('roledscrps.csv')
players = players.merge(descr, on='Role',how='left').drop('Season_Year',\
                                                           axis=1)

# tag players
revs = pd.read_csv('video_review.csv', 
                   usecols=['GameKey','PlayID',
                             'GSISID','Primary_Partner_GSISID'], 
                   na_values=['Unclear'])\
    .fillna(-99).astype(int)

players = players.merge(revs, how='left', on=['GameKey', 'PlayID', 'GSISID'],\
                        sort='False')
players['concussed'] = np.where(players.Primary_Partner_GSISID.isnull(), 0, 1)


# add numbers and positions
playas = pd.read_csv('player_punt_data.csv')
playas_agg = playas.groupby('GSISID')['Number'].apply(' '.join).to_frame()
players = players.merge(playas_agg, on='GSISID', how='left')

drops = ['Primary_Partner_GSISID'] + players.columns[players.columns.str\
        .contains('dupe')].tolist()
players = players.drop(drops, axis=1).sort_values(['GSISID', 'GameKey', 
          'PlayID']).set_index('GSISID').reset_index()

players.to_parquet('players.parq')

#%% join play level and game level data
plays = pd.read_csv('play_information.csv', 
                    index_col=['GameKey', 'PlayID'])

games = pd.read_csv('game_data.csv', 
                    index_col=['GameKey'])
games.Temperature.fillna(-999, inplace=True)
plays_all = plays.join(games, rsuffix='_dupe', sort=False)

revs = pd.read_csv('video_review.csv', 
                   index_col=['GameKey', 'PlayID'])
revs.loc[revs.Primary_Partner_GSISID == 'Unclear', 'Primary_Partner_GSISID']\
             = np.nan
revs['Primary_Partner_GSISID'] = pd.to_numeric(revs.Primary_Partner_GSISID)
plays_all = plays_all.join(revs, rsuffix='_dupe2', sort=False)


#%% merge player numbers and positions for concussions
playernums = pd.read_csv('player_punt_data.csv')
playernums = playernums.groupby('GSISID').agg(' '.join) #combine dupes

plays_all = plays_all.reset_index().merge(playernums, how='left', on='GSISID', 
            sort=False)
plays_all = plays_all.merge(playernums, how='left', 
            left_on='Primary_Partner_GSISID', right_on='GSISID', 
            suffixes=("_player", "_partner"), sort=False)


#%% merge player level data for concussions
roles = pd.read_csv('play_player_role_data.csv')
roles_all = roles.merge(descr, on='Role', how='left').drop('Season_Year', 
                        axis=1)

plays_all = plays_all.merge(roles_all, how='left', on=['GameKey', 'PlayID', 
            'GSISID'], sort=False)
plays_all = plays_all.merge(roles_all, how='left', left_on=['GameKey', 
            'PlayID', 'Primary_Partner_GSISID'], right_on=['GameKey', 
            'PlayID', 'GSISID'], suffixes=("_player", "_partner"), sort=False)

plays_all.set_index(['GameKey', 'PlayID'], inplace=True)


# merge aggregated player level data for all plays
roles_enc = pd.get_dummies(roles_all, columns=['Team', 'Area', 'Type'])
collist = list(roles_enc)[2:]
agglist = ['size', pd.Series.nunique] + (len(collist)-3) * ['sum']
aggdict = dict(zip(collist, agglist))


roles_agg = roles_enc.groupby(['GameKey', 'PlayID']).agg(aggdict)
roles_agg.columns = [r + '_agg' for r in roles_agg.columns]

plays_all = plays_all.join(roles_agg, rsuffix="_roles")


#%% make simple features
plays_all['yard_number'] = plays_all.YardLine.str.split().str[1].astype(int)
plays_all['dist_togoal'] = np.where(plays_all.Poss_Team == plays_all.YardLine\
            .str.split().str[0], plays_all.yard_number + 50, 
            plays_all.yard_number)
plays_all['Rec_team'] = np.where(plays_all.Poss_Team == plays_all.HomeTeamCode, 
             plays_all.VisitTeamCode, plays_all.HomeTeamCode)
plays_all['home_score'] = plays_all.Score_Home_Visiting.str.split(" - ")\
            .str[0].astype(int)
plays_all['visit_score'] = plays_all.Score_Home_Visiting.str.split(" - ")\
            .str[1].astype(int)
plays_all['concussion'] = np.where(plays_all.Primary_Impact_Type.isnull(), 
                                    0, 1)

#%% clean up 
drops = ['YardLine',
         'Play_Type',
         'Home_Team_Visit_Team',
         'Primary_Partner_GSISID',
         'Score_Home_Visiting']\
         + plays_all.columns[plays_all.columns.str.contains('dupe')].tolist()
plays_all.drop(drops, axis=1, inplace=True)

plays_all['GSISID_player'] = plays_all.GSISID_player.fillna(-99, 
                                downcast='infer')
plays_all['GSISID_partner'] = plays_all.GSISID_partner.fillna(-99, 
                                downcast='infer')

floatcols = plays_all.select_dtypes('float').columns
for f in floatcols:
    plays_all[f] = plays_all[f].fillna(-99).astype(int)

plays_all.fillna('unspecified', inplace=True)
plays_all.replace('SD', 'LAC', inplace=True, regex=True)
plays_all['Game_Date'] = pd.to_datetime(plays_all.Game_Date, format='%m/%d/%Y')

plays_all.sort_index(inplace=True)
plays_all.reset_index(inplace=True) #avoid mulit-index for parquet

plays_all.to_parquet('plays.parq')
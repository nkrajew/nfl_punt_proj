# NFL Punt Safety Project
*Based on the Kaggle competition NFL Punt Analytics Competition* 

## Sources
Kaggle Competition: https://www.kaggle.com/c/NFL-Punt-Analytics-Competition \
NFL Data Preparation (JohnM): https://www.kaggle.com/jpmiller/nfl-data-preparation

## Project Start
**Purpose:** Analyze NFL game data and suggest rules to improve player safety during punt plays \
**Findings:** Changing the fair catch rule can result in fewer concussions per year.

### Background

### Methodology
**1. Theory Crafting** \
Before I started on any analysis, I leveraged what I knew about football to create theories on what may lead to punt return concussions. It was a rather rudimentary process that hinged on three questions:

    Q1: What causes concussions? A: Hits. \
    Q2: When would a "hit" take place? A: During an active punt return.\
    Q3: Can active returns be replaced/reduced? A: Yes; fair catches, touchbacks, no returns

Once I had this framework in mind, I could guide my data analysis. However, before I could begin doing any data analysis I needed some usable data...

**2. Data Preparation and Manipulation**\
The data used in this competition was rather large and cumbersome. I had not delt with datasets this large with any of my past projects, so I turned to other Kaggler notebooks for examples of how to wrangle the data into something digestable and usable. The notebook that proved most useful to me was by Kaggler JohnM (jpmiller). His notebook called NFL Data Preperation (link in sources section above) had excellent code snippets for merging the raw data, manipulating it, and exporting it as a parquet (a new file format for me!). I would highly recommend JohnM's notebook to anyone needing help with data prep for this competition!

To prepare and manipulate the data, I lifted a lot of JohnM's code into my own script. The highlights of what the code did are below:
- Merged players and their role descriptions
- Tag players that were involved in a concussion event
- Add player numbers and positions
- Merge play-level and game-level data
- Create simple features: yard_number, dist_togoal, Rec_team, home_score, visit_score, concussion
- Clean up data for various features
- Export data to parquet file type: two files created (players.parq and plays.parq)

After I had the data in a usable format, it was time to start analyzing the data with the framework from my theory crafting...

**3. Data Exploration and Analysis** 



**4. Decision Analysis (HOW??)**

### Analysis

### Conclusion

### Future Recommendations

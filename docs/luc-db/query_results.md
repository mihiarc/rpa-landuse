# RPA Land Use Change Analysis Query Results

This document contains the results of executing the common queries defined in the documentation.
These queries demonstrate the core functionality of the RPA land use change analysis system.

Parameters used for these queries:
- Scenario ID: 21 (CNRM_CM5_rcp45_ssp1)
- Year range: 2012 to 2070
- Land use types: Crop, Pasture, Forest, Urban, Range

## I. Overall Change and Trends

### 1. Total Net Change by Land Use Type

What is the total net change (gain or loss in acres) for each land use type across all counties 
over the entire projection period (2012-2070)?

```
land_use_type  total_net_change
        Urban     586363.422900
        Range     -79482.865500
      Pasture     -90006.920515
       Forest    -137117.647085
         Crop    -279755.989800
```

### 2. Annualized Change Rate

What is the average annual rate of change (in acres per year) for each land use type during each projection period?

```
 start_year  end_year land_use_type    net_change  period_years  annual_change_rate
       2012      2020         Urban  70746.122600             8         8843.265325
       2012      2020         Range  -8972.456700             8        -1121.557087
       2012      2020        Forest -12459.901895             8        -1557.487737
       2012      2020       Pasture -13801.081005             8        -1725.135126
       2012      2020          Crop -35512.683000             8        -4439.085375
       2020      2030         Urban  90483.835900            10         9048.383590
       2020      2030         Range -11807.876000            10        -1180.787600
       2020      2030        Forest -18141.373190            10        -1814.137319
       2020      2030       Pasture -18732.331710            10        -1873.233171
       2020      2030          Crop -41802.255000            10        -4180.225500

(showing first 10 rows)
```

### 3. Peak Change Time Period

During which time period is the largest net change observed for each land use type?

```
land_use_type  start_year  end_year   net_change
        Urban        2060      2070 119228.11810
         Crop        2050      2060 -54742.12000
       Forest        2060      2070 -32920.71110
      Pasture        2020      2030 -18732.33171
        Range        2060      2070 -17709.16370
```

## II. Geographic Analysis

### 4. Change by State

What is the net change for each land use type within each state over the entire projection period?

```
state_fips state_name land_use_type    net_change
        01    Alabama         Urban  17962.645600
        01    Alabama         Range     73.832600
        01    Alabama          Crop  -2822.114900
        01    Alabama        Forest  -5523.091600
        01    Alabama       Pasture  -9691.271700
        04    Arizona         Urban  16424.963700
        04    Arizona       Pasture   1167.423085
        04    Arizona          Crop  -1664.399300
        04    Arizona        Forest  -3063.589885
        04    Arizona         Range -12864.397600
        05   Arkansas         Urban  17857.368900
        05   Arkansas         Range     52.451800
        05   Arkansas          Crop  -2452.219100
        05   Arkansas        Forest  -4502.575600
        05   Arkansas       Pasture -10955.026000

(showing first 15 rows)
```

### 5. Top Counties by Change

Which are the top 10 counties with the largest increase in Crop land use?

```
fips_code  county_name state_name land_use_type  net_change
    48225 County 48225      Texas          Crop   1094.7892
    40013 County 40013   Oklahoma          Crop    985.6871
    06071 County 06071 California          Crop    963.5478
    29215 County 29215   Missouri          Crop    935.9942
    40023 County 40023   Oklahoma          Crop    915.2319
    48467 County 48467      Texas          Crop    884.4975
    40079 County 40079   Oklahoma          Crop    881.4248
    48149 County 48149      Texas          Crop    829.1655
    40035 County 40035   Oklahoma          Crop    801.8219
    48223 County 48223      Texas          Crop    795.7215
```

## IV. Land Use Transition Analysis

### 11. Major Transitions

What are the top 10 most common land use transitions observed across the region between 2012 and 2070?

```
from_land_use to_land_use  total_acres_changed
       Forest      Forest         2.396802e+07
        Range       Range         2.388226e+07
         Crop        Crop         2.011701e+07
        Urban       Urban         6.742132e+06
      Pasture     Pasture         6.044851e+06
         Crop     Pasture         7.719032e+05
      Pasture        Crop         6.237623e+05
       Forest       Urban         2.611204e+05
      Pasture      Forest         1.853708e+05
         Crop       Urban         1.292865e+05
```

## III. Scenario Comparison

### 8. Impact of Climate Models

How does the projected change in Crop differ between climate models by 2070?

```
    gcm            scenario_name   rcp   ssp land_use_type  total_change  percentage
   CNRM      CNRM_CM5_rcp45_ssp1   cm5 rcp45          Crop  -279755.9898   12.357912
   CNRM      CNRM_CM5_rcp85_ssp2   cm5 rcp85          Crop  -272103.0920   12.019854
   CNRM      CNRM_CM5_rcp85_ssp3   cm5 rcp85          Crop  -264725.4681   11.693955
   CNRM      CNRM_CM5_rcp85_ssp5   cm5 rcp85          Crop  -288641.0053   12.750398
HadGEM2 HadGEM2_ES365_rcp45_ssp1 es365 rcp45          Crop  -238448.9243   10.533218
HadGEM2 HadGEM2_ES365_rcp85_ssp2 es365 rcp85          Crop  -304214.7447   13.438350
HadGEM2 HadGEM2_ES365_rcp85_ssp3 es365 rcp85          Crop  -298266.0554   13.175574
HadGEM2 HadGEM2_ES365_rcp85_ssp5 es365 rcp85          Crop  -317625.1208   14.030739
```

## V. Data Integrity Checks

### 14-16. Data Integrity Checks

Results of various data integrity checks:

```
### Area Consistency Check (inconsistencies found):
No inconsistencies found.

### Negative Acres Check:
No negative acre values found.

### Duplicate Identifiers Check:
No duplicate scenario names found.
No duplicate FIPS codes found.
No duplicate time steps found.
```

## Summary

These query results demonstrate the core functionality of the RPA land use change analysis system.
The system can effectively answer a wide range of questions about land use changes over time,
across different geographic scales, and under different scenarios.

# Query Examples

Real-world examples of natural language queries for land use analysis, organized by use case.

## 🏙️ Urban Planning

### Urban Growth Analysis

**Query:**
```
You> Which metropolitan counties will see the most urban expansion by 2050?
```

**Agent Approach:**
- Identifies counties with major cities
- Calculates urban area change from 2020 to 2050
- Ranks by absolute and percentage growth

**Follow-up:**
```
You> For those top counties, what land uses are being converted to urban?
```

### Urban Density Trends

**Query:**
```
You> Show me counties where urban area is growing faster than the state average
```

**Sample Result:**
```
Counties with above-average urban growth:
- Riverside County (06065): +45.2% vs state avg 28.3%
- San Bernardino (06071): +42.1% vs state avg 28.3%
- Placer County (06061): +38.9% vs state avg 28.3%
```

### Sustainable Development

**Query:**
```
You> Find counties successfully increasing urban density without expanding into forest areas
```

## 🌾 Agricultural Analysis

### Crop vs Pasture Dynamics

**Query:**
```
You> How is the balance between cropland and pasture changing over time?
```

**Agent generates analysis showing:**
- Total crop and pasture by decade
- Conversion rates between them
- Regional variations
- Scenario comparisons

### Agricultural Pressure

**Query:**
```
You> In the High Crop Demand scenario, which counties lose the most pasture to cropland?
```

### Food Security Assessment

**Query:**
```
You> Calculate total agricultural land (crops + pasture) and show if it's increasing or decreasing nationally
```

**Complex Follow-up:**
```
You> Now break that down by region and identify areas at risk of agricultural land shortage
```

## 🌲 Forest Conservation

### Deforestation Hotspots

**Query:**
```
You> Identify the top 20 counties with the highest forest loss across all scenarios
```

**Results Format:**
```
Rank | County | FIPS | Forest Loss (1000 acres) | % Loss
1    | County A | 12345 | -523.4 | -32.1%
2    | County B | 23456 | -498.7 | -28.9%
...
```

### Forest Recovery

**Query:**
```
You> Are there any counties where forest area increases? If so, what's converting to forest?
```

### Conservation Scenarios

**Query:**
```
You> Compare forest preservation between the Baseline and High Forest scenarios - where are the biggest differences?
```

## 📊 Scenario Comparisons

### Comprehensive Scenario Analysis

**Query:**
```
You> Create a summary table comparing all scenarios for the year 2100:
- Total urban area
- Total agricultural area  
- Total natural area (forest + range)
- Percentage of land that changed use
```

### Scenario Divergence

**Query:**
```
You> At what point do the scenarios start to significantly diverge from the Baseline?
```

**Agent Analysis:**
- Calculates year-by-year differences
- Identifies divergence threshold
- Shows which land uses drive differences

### Best Case Analysis

**Query:**
```
You> Which scenario best balances urban growth needs with environmental preservation?
```

## 📈 Trend Analysis

### Acceleration Detection

**Query:**
```
You> Show me where land use change is accelerating vs slowing down between the first half (2020-2060) and second half (2060-2100) of the projection period
```

### Tipping Points

**Query:**
```
You> Identify years where major shifts occur in land use patterns
```

### Long-term Projections

**Query:**
```
You> Based on current trends, when will urban area exceed 20% in major counties?
```

## 🗺️ Regional Patterns

### State-Level Analysis

**Query:**
```
You> Summarize land use changes by state, focusing on the top 5 states with the most change
```

### Coastal vs Inland

**Query:**
```
You> Compare land use transition patterns between coastal counties and inland counties
```

**Agent Approach:**
```sql
-- Identifies coastal counties (could use FIPS patterns or geographic data)
-- Aggregates transitions for each group
-- Calculates and compares metrics
```

### Metropolitan Influence

**Query:**
```
You> How do land use changes differ between counties with major cities versus rural counties?
```

## 🔄 Transition Patterns

### Transition Matrix

**Query:**
```
You> Create a transition matrix showing all conversions between land use types for the Baseline scenario
```

**Result Format:**
```
From\To | Crop | Forest | Pasture | Urban | Range
--------|------|--------|---------|-------|-------
Crop    | 85%  | 2%     | 8%      | 5%    | 0%
Forest  | 3%   | 88%    | 2%      | 7%    | 0%
...
```

### Unusual Transitions

**Query:**
```
You> Find rare or unexpected land use transitions that might indicate data issues or interesting patterns
```

### Transition Chains

**Query:**
```
You> Track agricultural land that eventually becomes urban - does it go directly or through other uses first?
```

## 💡 Complex Analytical Queries

### Multi-Criteria Analysis

**Query:**
```
You> Find counties that meet all these criteria:
- Urban growth > 25%
- Forest loss < 10%
- Agricultural land stable (±5%)
- In the Baseline scenario
```

### Composite Metrics

**Query:**
```
You> Create a "land use change intensity index" that combines:
- Rate of change
- Diversity of transitions
- Deviation from historical patterns
```

### Predictive Insights

**Query:**
```
You> Based on 2020-2040 patterns, which counties are likely to face land use conflicts by 2080?
```

## 📋 Reporting Queries

### Executive Summary

**Query:**
```
You> Generate a one-page executive summary of land use changes including:
- Key statistics
- Major trends
- Critical counties to watch
- Policy implications
```

### County Report Card

**Query:**
```
You> Create a detailed report card for Sacramento County including all scenarios and land use changes
```

### Stakeholder Analysis

**Query:**
```
You> Prepare data for different stakeholders:
- Farmers: Agricultural land changes
- Conservationists: Natural land preservation  
- Urban planners: Development opportunities
- Policymakers: Overall sustainability
```

## 🛠️ Data Quality Checks

### Validation Queries

**Query:**
```
You> Verify that total land area remains constant over time for each county
```

### Consistency Checks

**Query:**
```
You> Check if the sum of all "from" transitions equals the sum of all "to" transitions by year
```

### Outlier Detection

**Query:**
```
You> Find any suspicious data points where land use changes seem unrealistic
```

## 📊 Export and Visualization Prep

### Chart Data

**Query:**
```
You> Prepare data for a line chart showing land use trends over time for all scenarios
```

### Geographic Export

**Query:**
```
You> Export county-level urban growth data in a format suitable for GIS mapping
```

### Dashboard Metrics

**Query:**
```
You> Create a set of 10 key metrics for a land use monitoring dashboard, updated annually
```

## Tips for Complex Queries

1. **Build Incrementally**: Start simple, add complexity
2. **Use Context**: Reference previous results
3. **Be Specific**: Include scenarios, years, and regions
4. **Think Stepwise**: Break complex analyses into steps
5. **Verify Results**: Ask for row counts and sanity checks

## Next Steps

- Try these examples with your own data
- Modify queries for your specific needs
- Combine patterns for new insights
- Share interesting findings!
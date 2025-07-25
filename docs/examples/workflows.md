# Sample Workflows

Step-by-step workflows demonstrating how to use the LangChain Land Use Analysis system for complete analyses.

## 🔍 Workflow 1: County Land Use Profile

**Objective:** Create a comprehensive land use profile for a specific county.

### Step 1: Identify the County

```
You> What's the FIPS code for Sacramento County, California?

Agent> Sacramento County, California has FIPS code 06067.
```

### Step 2: Current Land Use Distribution

```
You> Show me the current (2020) land use distribution for FIPS 06067

Agent> Here's the 2020 land use distribution for Sacramento County:
- Urban: 125.3 thousand acres (22.1%)
- Crop: 189.7 thousand acres (33.5%)
- Pasture: 45.2 thousand acres (8.0%)
- Forest: 156.8 thousand acres (27.7%)
- Range: 49.4 thousand acres (8.7%)
Total: 566.4 thousand acres
```

### Step 3: Historical Trends

```
You> Show me how land use has changed in Sacramento County from 2020 to 2050 in the Baseline scenario

Agent> Land use changes in Sacramento County (2020-2050, Baseline):
- Urban: +45.2 thousand acres (+36.1%)
- Crop: -28.3 thousand acres (-14.9%)
- Pasture: -8.7 thousand acres (-19.2%)
- Forest: -5.4 thousand acres (-3.4%)
- Range: -2.8 thousand acres (-5.7%)
```

### Step 4: Scenario Comparison

```
You> Compare urban growth in Sacramento County across all scenarios for 2050

Agent> Urban area in Sacramento County by 2050:
- Baseline: 170.5 thousand acres
- High Urban: 198.7 thousand acres (+16.5%)
- High Crop Demand: 165.2 thousand acres (-3.1%)
- High Forest: 162.1 thousand acres (-4.9%)
```

### Step 5: Transition Analysis

```
You> What are the main sources of new urban land in Sacramento County?

Agent> Sources of urban expansion in Sacramento County (Baseline, 2020-2050):
1. From Crop: 28.3 thousand acres (62.6%)
2. From Pasture: 8.7 thousand acres (19.2%)
3. From Forest: 5.4 thousand acres (11.9%)
4. From Range: 2.8 thousand acres (6.2%)
```

### Step 6: Export Results

```
You> Export this Sacramento County analysis to a CSV file

Agent> Analysis exported to: sacramento_county_analysis.csv
```

## 📊 Workflow 2: Regional Agricultural Assessment

**Objective:** Assess agricultural land changes across the Midwest.

### Step 1: Define the Region

```
You> List major agricultural counties in Iowa, Illinois, and Indiana

Agent> I'll identify counties with the most agricultural land in these states...
[Returns list of top agricultural counties by state]
```

### Step 2: Agricultural Land Trends

```
You> For these Midwest counties, calculate total agricultural land (crop + pasture) change from 2020 to 2100

Agent> Midwest agricultural land changes (2020-2100, Baseline):
- Total 2020: 45.6 million acres
- Total 2100: 42.1 million acres
- Net change: -3.5 million acres (-7.7%)
- Average annual loss: 43,750 acres/year
```

### Step 3: Crop vs. Pasture Dynamics

```
You> Break down the agricultural changes into crop and pasture components

Agent> Agricultural land composition changes:
Cropland:
- 2020: 38.2 million acres (83.8%)
- 2100: 36.5 million acres (86.7%)
- Change: -1.7 million acres (-4.4%)

Pasture:
- 2020: 7.4 million acres (16.2%)
- 2100: 5.6 million acres (13.3%)
- Change: -1.8 million acres (-24.3%)
```

### Step 4: Conversion Analysis

```
You> What is agricultural land converting to in these Midwest counties?

Agent> Agricultural land conversions (2020-2100):
1. To Urban: 2.8 million acres (80.0%)
2. To Forest: 0.5 million acres (14.3%)
3. To Range: 0.2 million acres (5.7%)

Primary driver: Urban expansion near major cities
```

### Step 5: Scenario Impact

```
You> How does the High Crop Demand scenario affect these agricultural areas?

Agent> High Crop Demand vs. Baseline (2100):
- Additional cropland retained: +2.1 million acres
- Reduced pasture loss: +0.4 million acres
- Less urban conversion: -1.8 million acres
- Forest conversion to crops: +0.7 million acres
```

### Step 6: Create Visualization Data

```
You> Prepare data for a time series chart of agricultural land by decade

Agent> Time series data prepared:
Year | Cropland | Pasture | Total_Ag
2020 | 38.2 | 7.4 | 45.6
2030 | 37.8 | 7.1 | 44.9
2040 | 37.5 | 6.8 | 44.3
...
Data saved to: midwest_ag_timeseries.csv
```

## 🌲 Workflow 3: Forest Conservation Analysis

**Objective:** Identify priority areas for forest conservation.

### Step 1: Baseline Forest Loss

```
You> Identify the 20 counties with the most forest loss in the Baseline scenario by 2050

Agent> Top 20 counties by forest loss (2020-2050, Baseline):
1. County A (FIPS): -125,400 acres
2. County B (FIPS): -98,200 acres
[... continues with full list]
```

### Step 2: Conservation Potential

```
You> For these high-loss counties, how much forest is saved in the High Forest scenario?

Agent> Forest conservation impact (High Forest vs. Baseline, 2050):
Average forest saved: 45,300 acres per county
Total forest saved: 906,000 acres
Conservation efficiency: 36.2% loss reduction
```

### Step 3: Threat Analysis

```
You> What are the main threats to forests in these counties?

Agent> Primary forest conversion drivers:
1. Urban expansion: 55.3%
2. Agricultural expansion: 31.2%
3. Other development: 13.5%

Urban pressure highest near metro areas
Agricultural pressure in rural counties
```

### Step 4: Corridor Identification

```
You> Find counties that connect major forest areas and are at risk

Agent> Critical forest corridor counties at risk:
[List of counties that link forest areas but show high conversion rates]
These counties are essential for maintaining connectivity
```

### Step 5: Policy Recommendations

```
You> Based on this analysis, which counties should be priorities for conservation programs?

Agent> Priority counties for conservation (ranked by impact potential):
1. High forest loss + High conservation potential
2. Critical corridors
3. Unique ecosystem representatives
[Detailed list with justifications]
```

## 🏙️ Workflow 4: Urban Growth Scenario Planning

**Objective:** Plan for urban growth impacts under different scenarios.

### Step 1: Metropolitan Area Selection

```
You> Show me the top 10 metropolitan areas by projected urban growth

Agent> Top metro areas by urban expansion (2020-2050, Baseline):
1. Phoenix Metro: +234,500 acres
2. Dallas-Fort Worth: +198,700 acres
[... complete list]
```

### Step 2: Growth Pattern Analysis

```
You> For the Phoenix metro area, analyze urban growth patterns by decade

Agent> Phoenix Metro urban growth by decade:
2020-2030: +65,200 acres (27.8% of total)
2030-2040: +58,400 acres (24.9%)
2040-2050: +48,700 acres (20.8%)
2050-2060: +38,200 acres (16.3%)
Growth rate declining over time
```

### Step 3: Source Land Analysis

```
You> What types of land are being converted to urban in Phoenix metro?

Agent> Land sources for Phoenix urban expansion (2020-2050):
- Range: 145,300 acres (62.0%)
- Agricultural: 67,200 acres (28.6%)
- Forest: 15,400 acres (6.6%)
- Other: 6,600 acres (2.8%)
```

### Step 4: Infrastructure Planning

```
You> Calculate the infrastructure needs based on urban expansion patterns

Agent> Infrastructure implications for Phoenix Metro:
- New urban area: 234,500 acres (366 sq miles)
- Estimated new roads needed: ~2,900 miles
- Population capacity: ~1.4 million residents
- Water demand increase: ~180 million gallons/day
```

### Step 5: Scenario Comparison

```
You> Compare Phoenix growth under High Urban vs. conservation scenarios

Agent> Phoenix Metro scenario comparison (2050):
High Urban: +298,400 acres (+27.3% vs Baseline)
High Forest: +189,200 acres (-19.3% vs Baseline)
Difference: 109,200 acres

Trade-offs clearly visible between scenarios
```

## 🔄 Workflow 5: Integrated Sustainability Assessment

**Objective:** Comprehensive sustainability evaluation for a state.

### Step 1: Define Metrics

```
You> For California, calculate key sustainability metrics for 2050

Agent> California sustainability metrics (2050, Baseline):
- Natural land preserved: 68.2%
- Agricultural land retained: 71.5%
- Urban density: 4.2 people/acre
- Forest coverage: 31.8%
- Agricultural diversity index: 0.67
```

### Step 2: Scenario Scoring

```
You> Score each scenario on sustainability metrics for California

Agent> California sustainability scores (0-100 scale):
Baseline: 72
High Forest: 85 (best for environment)
High Crop: 68 (best for food production)
High Urban: 61 (most development pressure)
```

### Step 3: Regional Variations

```
You> Identify California regions with different sustainability challenges

Agent> Regional sustainability patterns:
- North Coast: High forest preservation needs
- Central Valley: Agricultural-urban conflict
- Southern California: Intense urban pressure
- Sierra Nevada: Conservation opportunity
- Desert: Renewable energy vs. conservation
```

### Step 4: Policy Integration

```
You> What policy interventions show the most impact?

Agent> High-impact policy opportunities:
1. Urban growth boundaries: Save 125,000 acres
2. Agricultural easements: Protect 230,000 acres
3. Forest conservation: Preserve 340,000 acres
4. Smart growth incentives: Reduce sprawl 15%
```

### Step 5: Monitoring Framework

```
You> Create a monitoring framework with key indicators

Agent> Sustainability monitoring indicators:
Annual tracking:
- Urban expansion rate
- Agricultural conversion rate
- Forest cover change
- Land use efficiency metrics

5-year assessment:
- Scenario deviation analysis
- Policy effectiveness review
- Emerging threat identification
```

## 💡 Tips for Effective Workflows

### 1. Plan Your Analysis
- Define clear objectives
- List required outputs
- Identify data needs
- Design query sequence

### 2. Build Incrementally
- Start with basic queries
- Add complexity gradually
- Validate at each step
- Save intermediate results

### 3. Use Agent Memory
- Reference previous results
- Build on earlier queries
- Maintain context
- Avoid repetition

### 4. Document Process
- Save important queries
- Export key results
- Note assumptions
- Create reproducible workflows

### 5. Iterate and Refine
- Test with sample data
- Refine query language
- Optimize performance
- Improve clarity

## Advanced Workflow Patterns

### Pattern 1: Comparative Analysis
```
1. Establish baseline
2. Define comparison groups
3. Calculate differences
4. Identify patterns
5. Draw conclusions
```

### Pattern 2: Temporal Analysis
```
1. Set time boundaries
2. Define intervals
3. Calculate changes
4. Identify trends
5. Project forward
```

### Pattern 3: Spatial Analysis
```
1. Define geographic scope
2. Aggregate by region
3. Compare across space
4. Identify clusters
5. Map results
```

## Next Steps

- Review [Query Examples](../queries/examples.md) for syntax
- Explore [Use Cases](use-cases.md) for applications
- Check [API Reference](../api/agent.md) for automation
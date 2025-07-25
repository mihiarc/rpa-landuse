# Advanced Natural Language Queries

This guide covers sophisticated query patterns for complex land use analysis using the LangChain agent.

## Complex Filtering and Conditions

### Multiple Conditions

```
You> Show me counties where forest decreased by more than 20% AND urban increased by more than 50% between 2020 and 2050
```

The agent will create a complex query with:
- Self-joins to compare different years
- Percentage calculations
- Multiple WHERE conditions

### Conditional Logic

```
You> Find transitions that only happen in certain scenarios but not in Baseline
```

**Generated approach:**
```sql
WITH baseline_transitions AS (
  SELECT DISTINCT from_land_use, to_land_use 
  FROM landuse_transitions 
  WHERE scenario = 'Baseline'
),
other_transitions AS (
  SELECT DISTINCT scenario, from_land_use, to_land_use 
  FROM landuse_transitions 
  WHERE scenario != 'Baseline'
)
SELECT * FROM other_transitions
WHERE (from_land_use, to_land_use) NOT IN (
  SELECT from_land_use, to_land_use FROM baseline_transitions
)
```

### Dynamic Thresholds

```
You> Show counties where urban growth exceeds the national average
```

## Advanced Aggregations

### Window Functions

```
You> Calculate the running total of forest loss by year
```

```
You> Show me the rank of each county by agricultural land area
```

### Percentages and Ratios

```
You> What percentage of each county is urban in 2050?
```

```
You> Calculate the ratio of forest to agricultural land by scenario
```

### Statistical Analysis

```
You> Show me the standard deviation of land use changes by decade
```

```
You> Find outlier counties with unusual transition patterns
```

## Time Series Analysis

### Trend Detection

```
You> Identify counties with accelerating urban growth
```

The agent will:
1. Calculate growth rates by period
2. Compare consecutive periods
3. Identify acceleration patterns

### Period Comparisons

```
You> Compare the rate of change between 2020-2050 and 2050-2080
```

### Decade Analysis

```
You> Show me which decade has the most dramatic land use changes
```

### Temporal Patterns

```
You> Find periods where forest loss slows down or reverses
```

## Cross-Scenario Analysis

### Scenario Divergence

```
You> Where do scenarios diverge the most from Baseline?
```

### Scenario Rankings

```
You> Rank scenarios by how much natural land they preserve
```

### Impact Analysis

```
You> Show me how different scenarios affect agricultural land in the Midwest
```

## Geographic Patterns

### Regional Analysis

```
You> Compare land use transitions between coastal and inland counties
```

### Spatial Clustering

```
You> Find groups of counties with similar transition patterns
```

### Hot Spot Detection

```
You> Identify regions with the most intense land use change
```

## Complex Transitions

### Multi-Step Transitions

```
You> Track land that goes from forest to agriculture to urban over time
```

### Transition Networks

```
You> Show me the flow of land between all use types in a Sankey diagram format
```

### Circular Transitions

```
You> Find cases where land returns to its original use
```

## Custom Metrics

### Sustainability Indices

```
You> Calculate a sustainability score based on natural land preservation and urban efficiency
```

### Change Intensity

```
You> Create a metric for land use change intensity by county
```

### Composite Indicators

```
You> Develop an agricultural productivity index considering crop and pasture changes
```

## Data Mining Queries

### Pattern Discovery

```
You> Find unusual or interesting patterns in the land use transitions
```

### Anomaly Detection

```
You> Identify counties with transition patterns very different from their neighbors
```

### Correlation Analysis

```
You> What factors correlate with high urban growth?
```

## Optimization Queries

### Best/Worst Case Analysis

```
You> Which scenario minimizes agricultural land loss while accommodating urban growth?
```

### Trade-off Analysis

```
You> Show the trade-off between forest preservation and crop production across scenarios
```

### Efficiency Metrics

```
You> Calculate land use efficiency by comparing urban area to population capacity
```

## Advanced SQL Patterns

### Common Table Expressions (CTEs)

```
You> Show me a breakdown of land use changes using step-by-step calculations
```

The agent uses CTEs for clarity:
```sql
WITH yearly_totals AS (
  SELECT year, from_land_use, SUM(area_1000_acres) as total
  FROM landuse_transitions
  GROUP BY year, from_land_use
),
yearly_changes AS (
  SELECT year, from_land_use,
         total - LAG(total) OVER (PARTITION BY from_land_use ORDER BY year) as change
  FROM yearly_totals
)
SELECT * FROM yearly_changes WHERE change IS NOT NULL
```

### Pivot Operations

```
You> Create a matrix showing transitions between all land use types
```

### Recursive Queries

```
You> Trace the history of specific land parcels through multiple transitions
```

## Performance Optimization

### Query Hints

```
You> For this large analysis, please optimize the query for performance
```

The agent will:
- Use appropriate indexes
- Limit data early in the query
- Avoid unnecessary calculations

### Sampling Strategies

```
You> Analyze a representative sample of counties to estimate national trends
```

### Incremental Analysis

```
You> Break down this complex analysis into smaller, manageable queries
```

## Integration Queries

### Multi-Table Analysis

```
You> Combine data from all four tables to show complete transition patterns
```

### View Utilization

```
You> Use the optimized views to compare agricultural changes across scenarios
```

### Data Validation

```
You> Verify data consistency between the regular and aggregated tables
```

## Visualization Preparation

### Chart-Ready Data

```
You> Prepare data for a stacked area chart of land use over time
```

### Map Data

```
You> Format county-level changes for geographic visualization
```

### Dashboard Metrics

```
You> Create a set of KPIs for a land use monitoring dashboard
```

## Advanced Examples

### Example 1: Comprehensive County Profile

```
You> Create a complete land use profile for Los Angeles County including:
- Current land use distribution
- Historical trends
- Projected changes under each scenario  
- Comparison to state averages
- Key transition patterns
```

### Example 2: Scenario Impact Report

```
You> Generate an impact assessment comparing all scenarios:
- Total area changed
- Natural land preserved
- Agricultural productivity
- Urban expansion efficiency
- Environmental sustainability score
```

### Example 3: Time Series Forecast

```
You> Based on historical patterns, project when urban area might exceed agricultural area in major metropolitan counties
```

## Best Practices for Complex Queries

1. **Break Down Complex Requests**
   - Start with simpler components
   - Build up to the full analysis
   - Verify each step

2. **Use Agent Memory**
   - Reference previous results
   - Build analyses incrementally
   - Save intermediate results

3. **Optimize for Performance**
   - Request samples for exploration
   - Use filtered subsets
   - Leverage indexed columns

4. **Validate Results**
   - Check totals and subtotals
   - Verify against known values
   - Look for logical consistency

## Next Steps

- Explore [Query Examples](examples.md) for real-world scenarios
- Review [Data Schemas](../data/schema.md) for all available fields
- See [API Reference](../api/agent.md) for programmatic access
Exporting schema as markdown...

# Schema Documentation v2.2.0

**Generated:** 2025-11-22T13:43:46.069531
**Description:** Combined scenarios with statistical fields and versioning 
system
**Author:** system
**Backward Compatible:** Yes

## Tables

### dim_geography

Geography dimension table for US counties

| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| county_name | VARCHAR(100) |  |  |
| state_code | VARCHAR(2) |  |  |
| state_name | VARCHAR(50) |  |  |
| region | VARCHAR(50) |  |  |
| created_at | TIMESTAMP | DEFAULT |  |

**Indexes:**

- name=None columns=None unique=False type=None ddl='CREATE INDEX IF NOT EXISTS 
idx_geography_fips ON dim_geography(fips_code)'
- name=None columns=None unique=False type=None ddl='CREATE INDEX IF NOT EXISTS 
idx_geography_state ON dim_geography(state_code)'


### dim_landuse

Land use type dimension table

| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| landuse_name | VARCHAR(50) | NOT NULL |  |
| landuse_category | VARCHAR(30) |  |  |
| description | TEXT |  |  |
| created_at | TIMESTAMP | DEFAULT |  |

**Indexes:**

- name=None columns=None unique=False type=None ddl='CREATE INDEX IF NOT EXISTS 
idx_landuse_code ON dim_landuse(landuse_code)'


### dim_scenario

Climate scenario dimension table with combined RCP-SSP scenarios

| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| scenario_name | VARCHAR(100) | NOT NULL |  |
| rcp_scenario | VARCHAR(20) |  |  |
| ssp_scenario | VARCHAR(20) |  |  |
| description | TEXT |  |  |
| narrative | TEXT |  |  |
| aggregation_method | VARCHAR(50) | DEFAULT |  |
| gcm_count | INTEGER | DEFAULT |  |
| created_at | TIMESTAMP | DEFAULT |  |

**Indexes:**

- name=None columns=None unique=False type=None ddl='CREATE INDEX IF NOT EXISTS 
idx_scenario_name ON dim_scenario(scenario_name)'


### dim_time

Time dimension table for temporal analysis

| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| year_range | VARCHAR(20) | NOT NULL |  |
| start_year | INTEGER |  |  |
| end_year | INTEGER |  |  |
| period_length | INTEGER |  |  |
| created_at | TIMESTAMP | DEFAULT |  |

**Indexes:**

- name=None columns=None unique=False type=None ddl='CREATE INDEX IF NOT EXISTS 
idx_time_range ON dim_time(year_range)'


### fact_landuse_transitions

Main fact table for land use transitions with aggregated metrics

| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| scenario_id | INTEGER | NOT NULL |  |
| time_id | INTEGER | NOT NULL |  |
| geography_id | INTEGER | NOT NULL |  |
| from_landuse_id | INTEGER | NOT NULL |  |
| to_landuse_id | INTEGER | NOT NULL |  |
| acres | DECIMAL(15 | NOT NULL |  |
| acres_std_dev | DECIMAL(15 |  |  |
| acres_min | DECIMAL(15 |  |  |
| acres_max | DECIMAL(15 |  |  |
| transition_type | VARCHAR(20) | NOT NULL |  |
| created_at | TIMESTAMP | DEFAULT |  |

**Indexes:**

- name=None columns=None unique=False type=None ddl='CREATE INDEX IF NOT EXISTS 
idx_fact_scenario ON fact_landuse_transitions(scenario_id)'
- name=None columns=None unique=False type=None ddl='CREATE INDEX IF NOT EXISTS 
idx_fact_time ON fact_landuse_transitions(time_id)'
- name=None columns=None unique=False type=None ddl='CREATE INDEX IF NOT EXISTS 
idx_fact_geography ON fact_landuse_transitions(geography_id)'
- name=None columns=None unique=False type=None ddl='CREATE INDEX IF NOT EXISTS 
idx_fact_from_landuse ON fact_landuse_transitions(from_landuse_id)'
- name=None columns=None unique=False type=None ddl='CREATE INDEX IF NOT EXISTS 
idx_fact_to_landuse ON fact_landuse_transitions(to_landuse_id)'
- name=None columns=None unique=False type=None ddl='CREATE INDEX IF NOT EXISTS 
idx_fact_composite ON fact_landuse_transitions(scenario_id, time_id, 
geography_id)'


### schema_version

Schema versioning table for tracking database evolution

| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| version_number | VARCHAR(20) | NOT NULL |  |
| description | TEXT |  |  |
| applied_at | TIMESTAMP | DEFAULT |  |
| applied_by | VARCHAR(100) |  |  |


## Views

### v_default_transitions

Default view for OVERALL scenario transitions

**Definition:**
```sql
CREATE OR REPLACE VIEW v_default_transitions AS
SELECT f.*, s.scenario_name, s.rcp_scenario, s.ssp_scenario, t.year_range, 
t.start_year, t.end_year, g.fips_code, g.county_name, g.state_name, g.region, 
fl.landuse_name as from_landuse, tl.landuse_name as to_landuse
FROM fact_landuse_transitions f JOIN dim_scenario s ON f.scenario_id = 
s.scenario_id JOIN dim_time t ON f.time_id = t.time_id JOIN dim_geography g ON 
f.geography_id = g.geography_id JOIN dim_landuse fl ON f.from_landuse_id = 
fl.landuse_id JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
WHERE s.scenario_name = 'OVERALL' 
```

### v_scenario_comparisons

View for comparing scenarios side by side

**Definition:**
```sql
CREATE OR REPLACE VIEW v_scenario_comparisons AS
SELECT s.scenario_name, s.rcp_scenario, s.ssp_scenario, t.year_range, 
g.state_name, fl.landuse_name as from_landuse, tl.landuse_name as to_landuse, 
SUM(f.acres) as total_acres, AVG(f.acres_std_dev) as avg_std_dev, COUNT(*) as 
transition_count
FROM fact_landuse_transitions f JOIN dim_scenario s ON f.scenario_id = 
s.scenario_id JOIN dim_time t ON f.time_id = t.time_id JOIN dim_geography g ON 
f.geography_id = g.geography_id JOIN dim_landuse fl ON f.from_landuse_id = 
fl.landuse_id JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
WHERE s.scenario_name != 'OVERALL'
GROUP BY s.scenario_name, s.rcp_scenario, s.ssp_scenario, t.year_range, 
g.state_name, fl.landuse_name, tl.landuse_name
```


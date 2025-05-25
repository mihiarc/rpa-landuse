# Average Scenario Implementation

This document explains the implementation of the "Average (All Scenarios)" feature in the RPA Land Use Viewer application.

## Overview

The RPA Land Use Viewer application now includes a default view that displays the average land use projections across all 20 climate-socioeconomic scenarios. This provides users with a "consensus" or "ensemble" view of the land use projections without requiring them to select a specific scenario.

## Implementation Details

### Database Changes

1. **New SQL Script**: `data/database/create_avg_scenario_view.sql`
   - Creates a special scenario record in the `scenarios` table for the average scenario
   - Creates a view `avg_land_use_transitions` that calculates average acres across all scenarios
   - Creates a materialized table `avg_land_use_transitions_tbl` for better performance
   - Populates the `land_use_summary` table with the average scenario data

2. **Shell Script**: `data/database/create_avg_scenario.sh`
   - Executes the SQL script to create the average scenario

### Application Changes

1. **Home.py**:
   - Added `get_default_scenario_index()` function to identify the average scenario
   - Modified the scenario selection to default to the average scenario when available

2. **Other Pages**:
   - Updated all pages with scenario selection to use the default scenario index

## How It Works

1. The SQL script calculates the average land use transition acres for each unique combination of:
   - time_step_id
   - fips_code
   - from_land_use
   - to_land_use

2. It stores these averages with a special scenario ID, allowing the application to access them using the existing query structure without changes to the core application logic.

3. When the application starts, it looks for the "Average (All Scenarios)" scenario and sets it as the default selection in the UI.

## Benefits

- Users immediately see a balanced view of projected land use changes
- Reduces the impact of extreme projections from any single scenario
- Provides a better starting point for exploring the data
- Still allows users to select specific scenarios for detailed analysis

## Maintenance

If the database is rebuilt or updated, run the following command to recreate the average scenario view:

```bash
cd data/database
./create_avg_scenario.sh
``` 
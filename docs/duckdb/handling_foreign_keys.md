# Handling Foreign Key Constraints in DuckDB

This guide explains how to handle foreign key constraints when deleting or modifying data in DuckDB.

## Understanding Foreign Key Errors

When you try to delete rows that are referenced by other tables through foreign keys, you'll encounter an error like:

```
Constraint Error:
Violates foreign key constraint because key "time_step_id: 1" is still referenced by a foreign key in a different table.
```

This error occurs because the database is protecting referential integrity - ensuring that relationships between tables remain valid.

## Option 1: Delete Referencing Rows First (Safest Approach)

The safest approach is to first delete any rows in child tables that reference the row you want to delete.

```sql
-- Example: Deleting a time_step and its associated land_use_transitions

-- First, identify the time_step_id
SELECT time_step_id FROM time_steps WHERE start_year = 2012;

-- Delete rows in child table that reference this time_step_id
DELETE FROM land_use_transitions WHERE time_step_id = 1;

-- Now it's safe to delete from the parent table
DELETE FROM time_steps WHERE start_year = 2012;
```

## Option 2: Use CASCADE to Automatically Delete Related Rows

You can set up your database to automatically delete related rows when you delete a parent row.

### Setting up CASCADE for New Tables

When creating new tables, include the `ON DELETE CASCADE` clause in your foreign key definition:

```sql
CREATE TABLE land_use_transitions (
    transition_id INTEGER PRIMARY KEY,
    scenario_id INTEGER,
    time_step_id INTEGER,
    fips_code VARCHAR, 
    from_land_use VARCHAR,
    to_land_use VARCHAR,
    area_hundreds_acres DOUBLE,
    FOREIGN KEY (time_step_id) REFERENCES time_steps(time_step_id) ON DELETE CASCADE,
    FOREIGN KEY (scenario_id) REFERENCES scenarios(scenario_id) ON DELETE CASCADE
);
```

### Modifying Existing Tables to Use CASCADE

For existing tables, you'll need to recreate them with the CASCADE option:

1. **Create a backup of your data**

```sql
-- Export your data to parquet files
COPY (SELECT * FROM time_steps) TO 'time_steps_backup.parquet' (FORMAT PARQUET);
COPY (SELECT * FROM land_use_transitions) TO 'land_use_transitions_backup.parquet' (FORMAT PARQUET);
```

2. **Analyze your current schema**

```sql
-- Get the current table definitions
.schema time_steps
.schema land_use_transitions
```

3. **Create a new table with CASCADE option**

```sql
-- Create a temporary table with the proper foreign key settings
CREATE TABLE new_land_use_transitions (
    transition_id INTEGER PRIMARY KEY,
    scenario_id INTEGER,
    time_step_id INTEGER,
    fips_code VARCHAR, 
    from_land_use VARCHAR,
    to_land_use VARCHAR,
    area_hundreds_acres DOUBLE,
    FOREIGN KEY (time_step_id) REFERENCES time_steps(time_step_id) ON DELETE CASCADE,
    FOREIGN KEY (scenario_id) REFERENCES scenarios(scenario_id) ON DELETE CASCADE,
    FOREIGN KEY (fips_code) REFERENCES counties(fips_code) ON DELETE CASCADE
);
```

4. **Copy data to the new table**

```sql
-- Transfer the data
INSERT INTO new_land_use_transitions SELECT * FROM land_use_transitions;
```

5. **Replace the old table with the new one**

```sql
-- Drop the old table
DROP TABLE land_use_transitions;

-- Rename the new table
ALTER TABLE new_land_use_transitions RENAME TO land_use_transitions;
```

Now deleting from `time_steps` will automatically delete the corresponding rows in `land_use_transitions`.

## Option 3: Temporarily Disable Foreign Key Constraints (Use with Caution)

You can temporarily disable foreign key checks, but this approach can leave your database in an inconsistent state.

```sql
-- Disable foreign key constraints
PRAGMA foreign_keys=OFF;

-- Perform the delete operation
DELETE FROM time_steps WHERE start_year = 2012;

-- Re-enable foreign key constraints
PRAGMA foreign_keys=ON;
```

**Warning**: This method leaves orphaned records in child tables pointing to non-existent parent records.

## Option 4: Set Null Instead of Delete (Alternative Approach)

Another approach is to set up foreign keys with `ON DELETE SET NULL` instead of `CASCADE`. This keeps the child rows but sets their reference to NULL.

```sql
CREATE TABLE new_land_use_transitions (
    -- columns as before
    FOREIGN KEY (time_step_id) REFERENCES time_steps(time_step_id) ON DELETE SET NULL
);
```

## Checking Foreign Key Status

You can check if foreign keys are enabled:

```sql
PRAGMA foreign_keys;
```

## Common Foreign Key Scenarios for RPA Land Use Database

### Deleting a Scenario

```sql
-- Delete land use transitions for this scenario first
DELETE FROM land_use_transitions WHERE scenario_id = 5;

-- Then delete the scenario
DELETE FROM scenarios WHERE scenario_id = 5;
```

### Deleting a Time Period

```sql
-- Delete land use transitions for this time period first
DELETE FROM land_use_transitions WHERE time_step_id = 1;

-- Then delete the time period
DELETE FROM time_steps WHERE time_step_id = 1;
```

### Deleting a County

```sql
-- Delete land use transitions for this county first
DELETE FROM land_use_transitions WHERE fips_code = '01001';

-- Then delete the county
DELETE FROM counties WHERE fips_code = '01001';
```

## Best Practices

1. **Always back up your data** before modifying table structures or performing mass deletions
2. **Understand the relationships** between tables before deleting data
3. **Use transactions** for complex operations
4. **Test in a non-production environment** first
5. **Consider the application impact** of schema changes
6. **Document any changes** to the database structure

## Transactions for Safety

Wrap complex operations in transactions to ensure they complete successfully or not at all:

```sql
-- Start a transaction
BEGIN TRANSACTION;

-- Perform operations
DELETE FROM land_use_transitions WHERE time_step_id = 1;
DELETE FROM time_steps WHERE time_step_id = 1;

-- Commit if everything went well
COMMIT;

-- Or roll back if anything went wrong
-- ROLLBACK;
``` 
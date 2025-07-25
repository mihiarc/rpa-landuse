# Data Directory

## Structure:
- `raw/` - Original source data files
- `processed/` - Converted databases and processed files

## Main Database:
- `processed/landuse_transitions_with_ag.db` - Primary database with agriculture aggregation

## Available Views:
- `individual_transitions` - All transitions with crop/pasture separate
- `agriculture_transitions` - All transitions with crop+pasture combined
- `individual_changes` - Only actual changes (no same-to-same)
- `agriculture_changes` - Only actual changes with agriculture combined

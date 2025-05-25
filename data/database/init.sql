-- RPA Land Use Viewer Database initialization
-- Creates the core schema for the land use projections data

-- Land use scenarios metadata
CREATE TABLE IF NOT EXISTS scenarios (
    scenario_id INTEGER PRIMARY KEY,
    scenario_name TEXT UNIQUE NOT NULL,
    gcm TEXT NOT NULL, -- Global Climate Model: CNRM_CM5, HadGEM2_ES365, etc.
    rcp TEXT NOT NULL, -- Representative Concentration Pathway: rcp45, rcp85
    ssp TEXT NOT NULL, -- Shared Socioeconomic Pathway: ssp1, ssp2, etc.
    description TEXT
);

-- Time steps
CREATE TABLE IF NOT EXISTS decades (
    decade_id INTEGER PRIMARY KEY,
    decade_name TEXT UNIQUE NOT NULL, -- e.g., "2020-2030"
    start_year INTEGER NOT NULL,
    end_year INTEGER NOT NULL
);

-- US Counties metadata
CREATE TABLE IF NOT EXISTS counties (
    fips_code TEXT PRIMARY KEY,
    county_name TEXT,
    state_name TEXT,
    state_fips TEXT,
    region TEXT,
    subregion TEXT
);

-- Land use categories
CREATE TABLE IF NOT EXISTS landuse_types (
    landuse_type_code TEXT PRIMARY KEY, -- 'cr', 'ps', 'rg', 'fr', 'ur'
    landuse_type_name TEXT NOT NULL,    -- 'cropland', 'pasture', etc.
    description TEXT
);

-- Land use transition data (main data table)
CREATE TABLE IF NOT EXISTS landuse_change (
    transition_id INTEGER PRIMARY KEY,
    scenario_id INTEGER NOT NULL,
    decade_id INTEGER NOT NULL,
    fips_code TEXT NOT NULL,
    from_landuse TEXT NOT NULL,
    to_landuse TEXT NOT NULL,
    area_hundreds_acres DOUBLE NOT NULL,
    FOREIGN KEY (scenario_id) REFERENCES scenarios(scenario_id),
    FOREIGN KEY (decade_id) REFERENCES decades(decade_id),
    FOREIGN KEY (fips_code) REFERENCES counties(fips_code),
    FOREIGN KEY (from_landuse) REFERENCES landuse_types(landuse_type_code),
    FOREIGN KEY (to_landuse) REFERENCES landuse_types(landuse_type_code)
);

-- Add basic indexes (additional ones will be created by SchemaManager)
CREATE INDEX IF NOT EXISTS idx_landuse_change ON landuse_change (scenario_id, decade_id, fips_code);
CREATE INDEX IF NOT EXISTS idx_from_landuse ON landuse_change (from_landuse);
CREATE INDEX IF NOT EXISTS idx_to_landuse ON landuse_change (to_landuse);

-- Insert land use categories
INSERT OR IGNORE INTO landuse_types (landuse_type_code, landuse_type_name, description) VALUES
    ('cr', 'Cropland', 'Agricultural cropland'),
    ('ps', 'Pasture', 'Pasture land'),
    ('rg', 'Rangeland', 'Rangeland'),
    ('fr', 'Forest', 'Forest land'),
    ('ur', 'Urban', 'Urban developed land'); 
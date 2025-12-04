-- Migration: v2.2.0 to v2.3.0
-- Author: system
-- Date: 2025-01-15T10:00:00Z
-- Description: Add data quality metrics and performance monitoring

-- Pre-migration checks
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM schema_version WHERE version_number = '2.2.0') THEN
    RAISE EXCEPTION 'Current version must be 2.2.0';
  END IF;
END $$;

-- Migration
BEGIN TRANSACTION;

-- MIGRATION STEP: Create data quality metrics table
CREATE TABLE IF NOT EXISTS data_quality_metrics (
  metric_id INTEGER PRIMARY KEY,
  table_name VARCHAR(100) NOT NULL,
  column_name VARCHAR(100),
  metric_type VARCHAR(50) NOT NULL,
  metric_value DECIMAL(15,4),
  threshold_value DECIMAL(15,4),
  is_passing BOOLEAN DEFAULT TRUE,
  measured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  notes TEXT
);
-- ROLLBACK: DROP TABLE IF EXISTS data_quality_metrics;
-- VALIDATE: SELECT 1 FROM information_schema.tables WHERE table_name = 'data_quality_metrics';

-- MIGRATION STEP: Add quality score to fact table
ALTER TABLE fact_landuse_transitions
ADD COLUMN IF NOT EXISTS quality_score DECIMAL(5,2) DEFAULT 1.0;
-- ROLLBACK: ALTER TABLE fact_landuse_transitions DROP COLUMN IF EXISTS quality_score;
-- VALIDATE: SELECT 1 FROM information_schema.columns WHERE table_name = 'fact_landuse_transitions' AND column_name = 'quality_score';

-- MIGRATION STEP: Create performance monitoring table
CREATE TABLE IF NOT EXISTS query_performance (
  performance_id INTEGER PRIMARY KEY,
  query_hash VARCHAR(64) NOT NULL,
  query_text TEXT,
  execution_time_ms INTEGER NOT NULL,
  rows_returned INTEGER,
  executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  user_id VARCHAR(100),
  success BOOLEAN DEFAULT TRUE
);
-- ROLLBACK: DROP TABLE IF EXISTS query_performance;
-- VALIDATE: SELECT 1 FROM information_schema.tables WHERE table_name = 'query_performance';

-- MIGRATION STEP: Create index on performance table
CREATE INDEX IF NOT EXISTS idx_query_performance_hash
ON query_performance(query_hash, executed_at DESC);
-- ROLLBACK: DROP INDEX IF EXISTS idx_query_performance_hash;
-- VALIDATE: SELECT 1 FROM duckdb_indexes() WHERE index_name = 'idx_query_performance_hash';

-- MIGRATION STEP: Create data quality view
CREATE OR REPLACE VIEW v_data_quality_summary AS
SELECT
  table_name,
  metric_type,
  COUNT(*) as metric_count,
  AVG(metric_value) as avg_value,
  MIN(metric_value) as min_value,
  MAX(metric_value) as max_value,
  SUM(CASE WHEN is_passing THEN 1 ELSE 0 END)::FLOAT / COUNT(*) as pass_rate,
  MAX(measured_at) as last_measured
FROM data_quality_metrics
GROUP BY table_name, metric_type;
-- ROLLBACK: DROP VIEW IF EXISTS v_data_quality_summary;
-- VALIDATE: SELECT 1 FROM information_schema.views WHERE table_name = 'v_data_quality_summary';

-- Update version
INSERT INTO schema_version (version_number, description, applied_by)
VALUES ('2.3.0', 'Add data quality metrics and performance monitoring', 'migration_system');

COMMIT;

-- Post-migration validation
SELECT 'Migration to v2.3.0 successful' WHERE EXISTS (
  SELECT 1 FROM schema_version
  WHERE version_number = '2.3.0'
);
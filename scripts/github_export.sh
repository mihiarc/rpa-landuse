#!/bin/bash
# Script to export files for GitHub repository

# Create export directory
EXPORT_DIR="rpa-landuse-github"
mkdir -p $EXPORT_DIR
mkdir -p $EXPORT_DIR/.github/workflows
mkdir -p $EXPORT_DIR/data/processed
mkdir -p $EXPORT_DIR/docs/duckdb
mkdir -p $EXPORT_DIR/scripts
mkdir -p $EXPORT_DIR/data/geodata

# Copy files
cp streamlit_app.py $EXPORT_DIR/
cp requirements-streamlit.txt $EXPORT_DIR/
cp README_GITHUB.md $EXPORT_DIR/README.md
cp .github/workflows/streamlit.yml $EXPORT_DIR/.github/workflows/
cp data/processed/*.parquet $EXPORT_DIR/data/processed/
cp scripts/data_processor_duckdb.py $EXPORT_DIR/scripts/
cp scripts/update_app_for_processed_data.py $EXPORT_DIR/scripts/
cp docs/duckdb/data_views.md $EXPORT_DIR/docs/duckdb/
cp .gitignore $EXPORT_DIR/

# Create a README for the geodata directory
echo "# GeoData Directory
This directory is for caching GeoJSON files used in the map visualizations.
" > $EXPORT_DIR/data/geodata/README.md

# Create zip archive
cd $EXPORT_DIR/..
zip -r rpa-landuse-github.zip $EXPORT_DIR

echo "GitHub-ready export created at rpa-landuse-github.zip"
echo "Size of archive:"
du -h rpa-landuse-github.zip

echo "Files included:"
find $EXPORT_DIR -type f | sort 
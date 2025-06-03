# RPA Land Use Change Data Viewer - Project Overview

## 🌲 About the Project

The **RPA Land Use Change Data Viewer** is an interactive data science platform for exploring and analyzing USDA Forest Service's Resources Planning Act (RPA) Assessment land use change projections. This project transforms complex geospatial datasets into accessible visualizations for policy makers, researchers, and land use planners.

## 🏗️ Project Architecture

```mermaid
%%{init: {'theme':'dark', 'themeVariables': { 'primaryColor': '#4CAF50', 'primaryTextColor': '#E8F5E8', 'primaryBorderColor': '#2E7D32', 'lineColor': '#81C784', 'secondaryColor': '#388E3C', 'tertiaryColor': '#1B5E20', 'background': '#0D1117', 'mainBkg': '#161B22', 'secondBkg': '#21262D', 'tertiaryBkg': '#30363D'}}}%%
flowchart TB
    %% Data Sources
    subgraph DS["🗄️ Data Sources"]
        direction TB
        RPA["RPA Assessment<br/>Raw Data"]:::source
        NRI["National Resources<br/>Inventory"]:::source
        MACA["MACA Climate<br/>Projections"]:::source
        SSP["SSP Socioeconomic<br/>Scenarios"]:::source
    end

    %% Data Processing Layer
    subgraph DPL["⚙️ Data Processing Layer"]
        direction TB
        DB["DuckDB Database<br/>(1.9GB)"]:::database
        ETL["ETL Pipeline<br/>(scripts/)"]:::process
        SL["Semantic Layers<br/>(Parquet files)"]:::process
    end

    %% Application Layer
    subgraph APP["🖥️ Application Layer"]
        direction TB
        SA["Streamlit App<br/>(streamlit_app.py)"]:::app
        PKG["Python Package<br/>(src/rpa_landuse/)"]:::package
        CLI["CLI Tools<br/>(rpa-viewer)"]:::tool
    end

    %% User Interface
    subgraph UI["👥 User Interface"]
        direction LR
        WEB["Web Dashboard<br/>(Streamlit Cloud)"]:::ui
        LOCAL["Local Development<br/>(localhost:8501)"]:::ui
    end

    %% Features
    subgraph FEAT["✨ Key Features"]
        direction TB
        VIZ["Interactive<br/>Visualizations"]:::feature
        MAP["Geographic<br/>Mapping"]:::feature
        EXPORT["Data Export<br/>(CSV/Parquet)"]:::feature
        FILTER["Scenario<br/>Filtering"]:::feature
    end

    %% Data Flow
    DS --> DPL
    DPL --> APP
    APP --> UI
    APP --> FEAT

    %% Styling
    classDef source fill:#2E7D32,stroke:#4CAF50,stroke-width:2px,color:#E8F5E8
    classDef database fill:#1565C0,stroke:#1976D2,stroke-width:2px,color:#E3F2FD
    classDef process fill:#E65100,stroke:#FF9800,stroke-width:2px,color:#FFF3E0
    classDef app fill:#7B1FA2,stroke:#9C27B0,stroke-width:2px,color:#F3E5F5
    classDef package fill:#5D4037,stroke:#795548,stroke-width:2px,color:#EFEBE9
    classDef tool fill:#37474F,stroke:#607D8B,stroke-width:2px,color:#ECEFF1
    classDef ui fill:#C62828,stroke:#D32F2F,stroke-width:2px,color:#FFEBEE
    classDef feature fill:#AD1457,stroke:#E91E63,stroke-width:2px,color:#FCE4EC
```

## 📊 Data Flow Architecture

```mermaid
%%{init: {'theme':'dark', 'themeVariables': { 'primaryColor': '#4CAF50', 'primaryTextColor': '#E8F5E8', 'primaryBorderColor': '#2E7D32', 'lineColor': '#81C784', 'secondaryColor': '#388E3C', 'tertiaryColor': '#1B5E20', 'background': '#0D1117', 'mainBkg': '#161B22', 'secondBkg': '#21262D', 'tertiaryBkg': '#30363D'}}}%%
graph TD
    %% Raw Data Sources
    subgraph RAW["🔄 Raw Data Sources"]
        direction TB
        COUNTY["County-level<br/>Land Use Data"]:::raw
        CLIMATE["Climate<br/>Projections"]:::raw
        ECON["Economic<br/>Scenarios"]:::raw
        GEO["Geographic<br/>Boundaries"]:::raw
    end

    %% ETL Processing
    subgraph ETL["⚙️ ETL Pipeline"]
        direction TB
        CLEAN["Data Cleaning<br/>& Validation"]:::etl
        TRANSFORM["Aggregation<br/>& Transformation"]:::etl
        OPTIMIZE["Query<br/>Optimization"]:::etl
    end

    %% Storage Layer
    subgraph STORAGE["💾 Storage Layer"]
        direction TB
        DUCKDB["DuckDB Views<br/>(County/State/Region)"]:::storage
        PARQUET["Processed Parquet<br/>(Semantic Layers)"]:::storage
        GEOJSON["Geographic Data<br/>(counties.geojson)"]:::storage
    end

    %% Application Views
    subgraph VIEWS["📱 Application Views"]
        direction TB
        URBAN["Urbanization<br/>Analysis"]:::view
        FOREST["Forest<br/>Transitions"]:::view
        AGRI["Agricultural<br/>Transitions"]:::view
        MAPS["Geographic<br/>Mapping"]:::view
    end

    %% Data Flow
    RAW --> ETL
    ETL --> STORAGE
    STORAGE --> VIEWS

    %% Inter-connections
    COUNTY --> CLEAN
    CLIMATE --> TRANSFORM
    ECON --> TRANSFORM
    GEO --> GEOJSON

    DUCKDB --> URBAN
    DUCKDB --> FOREST
    DUCKDB --> AGRI
    PARQUET --> MAPS
    GEOJSON --> MAPS

    %% Styling
    classDef raw fill:#1B5E20,stroke:#4CAF50,stroke-width:2px,color:#E8F5E8
    classDef etl fill:#E65100,stroke:#FF9800,stroke-width:2px,color:#FFF3E0
    classDef storage fill:#1565C0,stroke:#2196F3,stroke-width:2px,color:#E3F2FD
    classDef view fill:#7B1FA2,stroke:#9C27B0,stroke-width:2px,color:#F3E5F5
```

## 🎯 Application Features & Tabs

```mermaid
%%{init: {'theme':'dark', 'themeVariables': { 'primaryColor': '#4CAF50', 'primaryTextColor': '#E8F5E8', 'primaryBorderColor': '#2E7D32', 'lineColor': '#81C784', 'secondaryColor': '#388E3C', 'tertiaryColor': '#1B5E20', 'background': '#0D1117', 'mainBkg': '#161B22', 'secondBkg': '#21262D', 'tertiaryBkg': '#30363D'}}}%%
mindmap
  root((RPA Land Use<br/>Viewer))
    Overview
      RPA Assessment Info
      Key Findings
      Scenario Descriptions
      Data Processing Info
    Data Explorer
      Spatial Level Selection
      Scenario Filtering
      Geographic Filtering
      Data Preview
      CSV Download
    Land Use Flows
      Sankey Diagrams
      National & State Views
      Source/Destination Filters
      Flow Statistics
    Urbanization Trends
      🏙️ Top Development Areas
      Rate Calculations
      Temporal Analysis
      Enhanced Downloads
    Forest Transitions
      🌲 Forest Loss Analysis
      Destination Breakdown
      Baseline Comparisons
      FIPS Integration
    Agricultural Transitions
      🌾 Agricultural Loss Rates
      Cropland vs Pasture
      State-level Analysis
      Top Counties Ranking
    State Maps
      Geographic Visualization
      Choropleth Mapping
      State-level Aggregation
      Interactive Controls
```

## 🛠️ Technical Stack

```mermaid
%%{init: {'theme':'dark', 'themeVariables': { 'primaryColor': '#4CAF50', 'primaryTextColor': '#E8F5E8', 'primaryBorderColor': '#2E7D32', 'lineColor': '#81C784', 'secondaryColor': '#388E3C', 'tertiaryColor': '#1B5E20', 'background': '#0D1117', 'mainBkg': '#161B22', 'secondBkg': '#21262D', 'tertiaryBkg': '#30363D'}}}%%
graph TB
    %% Frontend Layer
    subgraph FE["🖥️ Frontend Layer"]
        direction TB
        ST["Streamlit<br/>(Web Framework)"]:::frontend
        FOLIUM["Folium<br/>(Interactive Maps)"]:::frontend
        PLOTLY["Plotly<br/>(Interactive Charts)"]:::frontend
        MPL["Matplotlib<br/>(Static Plots)"]:::frontend
    end

    %% Backend Layer
    subgraph BE["⚙️ Backend Layer"]
        direction TB
        PANDAS["Pandas<br/>(Data Manipulation)"]:::backend
        GEOPANDAS["GeoPandas<br/>(Geospatial Analysis)"]:::backend
        NUMPY["NumPy<br/>(Numerical Computing)"]:::backend
        SCIPY["SciPy<br/>(Scientific Computing)"]:::backend
    end

    %% Data Layer
    subgraph DL["💾 Data Layer"]
        direction TB
        DUCK["DuckDB<br/>(Analytics Database)"]:::data
        ARROW["PyArrow<br/>(Columnar Data)"]:::data
        PARQUET["Parquet<br/>(File Format)"]:::data
    end

    %% Development Tools
    subgraph DEV["🔧 Development Tools"]
        direction TB
        UV["uv<br/>(Package Manager)"]:::dev
        PYTEST["pytest<br/>(Testing)"]:::dev
        BLACK["Black<br/>(Code Formatting)"]:::dev
        MYPY["MyPy<br/>(Type Checking)"]:::dev
    end

    %% Deployment
    subgraph DEPLOY["🚀 Deployment"]
        direction TB
        GITHUB["GitHub Actions<br/>(CI/CD)"]:::deploy
        STREAMLIT_CLOUD["Streamlit Cloud<br/>(Hosting)"]:::deploy
        DOCKER["Docker<br/>(Containerization)"]:::deploy
    end

    %% Connections
    FE --> BE
    BE --> DL
    DEV --> FE
    DEV --> BE
    DEPLOY --> FE

    %% Styling
    classDef frontend fill:#7B1FA2,stroke:#9C27B0,stroke-width:2px,color:#F3E5F5
    classDef backend fill:#1565C0,stroke:#2196F3,stroke-width:2px,color:#E3F2FD
    classDef data fill:#2E7D32,stroke:#4CAF50,stroke-width:2px,color:#E8F5E8
    classDef dev fill:#E65100,stroke:#FF9800,stroke-width:2px,color:#FFF3E0
    classDef deploy fill:#C62828,stroke:#D32F2F,stroke-width:2px,color:#FFEBEE
```

## 📁 Project Structure

```
rpa-landuse/
├── 📱 streamlit_app.py           # Main Streamlit application (2,745 lines)
├── 📦 src/rpa_landuse/           # Core Python package
│   ├── cli.py                    # Command line interface
│   ├── commands/                 # Analysis commands
│   ├── db/                       # Database utilities
│   └── utils/                    # Helper functions
├── 🗄️ data/                      # Data storage
│   ├── database/                 # DuckDB database (1.9GB)
│   ├── processed/                # Optimized parquet files
│   ├── raw/                      # Original datasets
│   └── counties.geojson          # Geographic boundaries
├── 🔄 semantic_layers/           # Processed data views
│   ├── base_analysis/            # Basic aggregations
│   └── regional_analysis/        # Regional summaries
├── 🧪 scripts/                   # Data processing scripts
├── 🏗️ .github/workflows/         # CI/CD pipelines
├── 📋 tests/                     # Test suite
├── 📚 docs/                      # Documentation
└── ⚙️ pyproject.toml             # Project configuration
```

## 🎯 Key Analysis Capabilities

### 1. **Urbanization Analysis** 🏙️
- **Question**: "Where is urban development rate highest?"
- **Capabilities**: County-level urban development ranking, baseline rate calculations, temporal trends
- **Output**: Enhanced CSV downloads with FIPS codes, regional classifications, source land breakdown

### 2. **Forest Transition Analysis** 🌲
- **Question**: "Which areas are losing the most forest land?"
- **Capabilities**: Forest loss hotspots, destination land use analysis, baseline comparisons
- **Output**: Geographic data integration, annualized loss rates, destination breakdown

### 3. **Agricultural Transition Analysis** 🌾
- **Question**: "Where is agricultural land loss rate highest?"
- **Capabilities**: Cropland vs. pasture analysis, state-level rankings, temporal patterns
- **Output**: Source/destination breakdowns, rate calculations, policy-relevant metrics

### 4. **Scenario Comparison** 📊
- **Climate Scenarios**: RCP4.5 (lower warming) vs RCP8.5 (higher warming)
- **Socioeconomic Pathways**: SSP1-5 (different growth patterns)
- **Integrated Analysis**: 20 scenario combinations for comprehensive planning

## 🚀 Getting Started

### Prerequisites
- Python 3.11
- uv (recommended package manager)

### Installation

```bash
# Clone the repository
git clone https://github.com/your-username/rpa-landuse.git
cd rpa-landuse

# Setup virtual environment with uv
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
uv pip install -e .

# Run the Streamlit app
streamlit run streamlit_app.py
```

### Command Line Tools

```bash
# General viewer
rpa-viewer

# Specific analysis tools
rpa-urban-analysis
rpa-forest-analysis  
rpa-ag-analysis
```

## 🔍 Data Sources & Methodology

The RPA Assessment uses an empirical econometric model based on:
- **National Resources Inventory (NRI)** data (2001-2012)
- **MACA climate projections** 
- **SSP socioeconomic scenarios**
- **County-level analysis** for the conterminous United States

Land use projections cover five major classes:
- 🌲 Forest
- 🏘️ Developed
- 🌽 Crop
- 🐄 Pasture  
- 🌾 Rangeland

## 📈 Sample Analysis Results

**Top Urban Development Areas (ensemble_HH scenario):**
- **County**: Fresno County, CA (54,858 acres)
- **State**: Texas (1,943,086 acres)

**Top Forest Loss Areas:**
- **County**: Aroostook County, ME (174,910 acres)
- **State**: Alabama (1,078,434 acres)

**Top Agricultural Loss Areas:**
- **County**: Chouteau County, MT (58,106 acres)
- **State**: Texas (1,943,086 acres)

## 🎨 Dark Mode Compatibility

This project overview uses Mermaid diagrams optimized for dark mode viewing with:
- Dark background colors (`#0D1117`, `#161B22`)
- High contrast text (`#E8F5E8`, `#FFFFFF`)
- Accessible color palettes for different node types
- Clear visual hierarchy and readable typography

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.

## 🤝 Contributing

This project supports the USDA Forest Service's Resources Planning Act Assessment. Contributions are welcome for:
- Additional analysis features
- Performance optimizations
- Documentation improvements
- Bug fixes and testing

---

*Last updated: 2024*
*USDA Forest Service: Resources Planning Act Assessment* 
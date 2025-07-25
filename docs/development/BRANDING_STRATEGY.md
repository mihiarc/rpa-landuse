# RPA Land Use Analytics - Branding Strategy

## Project Name
**RPA Land Use Analytics**
*An AI-powered analysis tool for USDA Forest Service RPA Assessment data*

## Branding Elements

### Primary Name Options
1. **RPA Land Use Analytics** (Recommended)
   - Clear connection to RPA Assessment
   - Descriptive of functionality
   - Professional and government-appropriate

2. **RPA Assessment Explorer**
   - Emphasizes exploration capabilities
   - Direct tie to source data

3. **Forest & Rangeland Analytics**
   - Broader appeal
   - Matches RPA Assessment subtitle

### Tagline
"Transforming America's land use data into actionable insights"

### Visual Identity

#### Color Palette
Based on USDA Forest Service branding:
- **Primary Green**: #2E7D32 (Forest green)
- **Secondary Blue**: #1976D2 (Sky blue for water resources)
- **Accent Brown**: #6D4C41 (Earth/soil tone)
- **Neutral Gray**: #424242 (Text and UI elements)
- **Background**: #FAFAFA (Light gray/white)

#### Typography
- **Headers**: Inter or Roboto (clean, modern, accessible)
- **Body**: Open Sans or Source Sans Pro
- **Monospace**: Fira Code or JetBrains Mono (for code/queries)

### Logo Concept
- Simple tree/forest icon combined with data visualization elements
- Could incorporate chart bars growing like trees
- Keep it minimal and professional for government context

## Implementation Areas

### 1. Streamlit Dashboard
- Custom theme with brand colors
- Header with logo and project name
- Consistent color use in charts (Plotly)
- Professional sidebar styling

### 2. Command Line Interface
- ASCII art logo for terminal
- Colored output matching brand palette (using Rich)
- Consistent header/footer branding

### 3. Documentation
- README with branded header
- Consistent use of project name
- Professional screenshots with branding visible

### 4. Code Structure
- Update package name from `landuse` to `rpa_landuse`
- Consistent module naming
- Clear attribution to USDA Forest Service data

## Key Messages

### For Users
- "Official analytics tool for RPA Assessment data"
- "Ask questions in plain English, get data-driven answers"
- "Explore 50-year projections across climate scenarios"

### Technical Positioning
- Built on modern data stack (DuckDB, LangChain)
- AI-powered natural language interface
- Open source and extensible

## Attribution Requirements
Always include:
- "Data source: USDA Forest Service 2020 RPA Assessment"
- Link to official RPA Assessment: https://www.fs.usda.gov/research/rpa
- Proper citations per RPA documentation

## Next Steps
1. Update pyproject.toml with new name
2. Create logo assets
3. Implement Streamlit custom theme
4. Update CLI with Rich formatting
5. Revise all documentation
# GitHub Pages Documentation Setup

## Overview

The RPA Land Use Analytics documentation is now configured for deployment to GitHub Pages using MkDocs with the Material theme.

## Configuration Updates

### 1. MkDocs Configuration (`mkdocs.yml`)
- ✅ Updated site name to "RPA Land Use Analytics"
- ✅ Updated site description with RPA Assessment context
- ✅ Changed repository URLs to mihiarc/langchain-landuse
- ✅ Updated theme colors to forest green (#2E7D32)
- ✅ Added RPA Assessment section to navigation
- ✅ Updated copyright with RPA attribution

### 2. Documentation Structure
```
docs/
├── index.md                    # Updated with RPA branding
├── rpa/                        # New RPA-specific section
│   ├── overview.md            # 2020 RPA Assessment overview
│   └── climate-models.md      # 5 climate model details
├── RPA_SCENARIOS.md           # Detailed scenario documentation
├── LAND_USE_METHODOLOGY.md    # Econometric model methodology
├── api/
│   └── langgraph-agent.md     # New LangGraph agent documentation
└── development/
    └── BRANDING_STRATEGY.md   # RPA branding guidelines
```

### 3. GitHub Actions Workflow
Created `.github/workflows/deploy-docs.yml` for automatic deployment:
- Triggers on push to main branch
- Builds documentation with strict mode
- Deploys to GitHub Pages

## Local Development

### Build Documentation
```bash
# Build the site
uv run mkdocs build

# Build with strict mode (catches all warnings)
uv run mkdocs build --strict
```

### Serve Locally
```bash
# Using mkdocs directly
uv run mkdocs serve

# Using the helper script
uv run python scripts/serve_docs.py
```

Documentation will be available at http://localhost:8000

## Deployment

### Initial Setup (One-time)
1. Go to repository Settings → Pages
2. Source: Deploy from a branch
3. Branch: gh-pages / (root)
4. Save the settings

### Automatic Deployment
Documentation automatically deploys when:
- Documentation files are changed and pushed to main branch
- The deploy-docs workflow is manually triggered
- Uses `mkdocs gh-deploy` to build and push to gh-pages branch

### Manual Deployment
```bash
# Using the helper script
uv run python scripts/deploy_docs.py

# Or using mkdocs directly
uv run mkdocs gh-deploy --force
```

## Key Updates Made

### Content Updates
- Home page now features RPA branding and scenarios
- Quick start guide updated with RPA-specific examples
- Added comprehensive RPA Assessment documentation
- Created climate model reference guide
- Updated all examples to use RPA terminology

### Visual Updates
- Forest green color scheme throughout
- RPA ASCII logo on home page
- Consistent branding across all pages
- USDA Forest Service attribution

### Technical Updates
- Modern navigation with RPA sections
- Cross-referenced RPA documentation
- Updated API documentation for agents
- Fixed broken links and references

## URLs

- **Live Documentation**: https://mihiarc.github.io/langchain-landuse
- **Repository**: https://github.com/mihiarc/langchain-landuse
- **RPA Assessment**: https://www.fs.usda.gov/research/rpa

## Next Steps

1. Enable GitHub Pages in repository settings
2. Monitor first deployment via Actions tab
3. Update README with documentation link
4. Add documentation badge to repository
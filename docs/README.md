# Documentation

This directory contains the MkDocs documentation for the LangChain Land Use Analysis project.

## Building the Documentation

### Prerequisites

Install the documentation dependencies:

```bash
uv pip install -r config/requirements.txt
```

This installs:
- MkDocs
- Material for MkDocs theme
- Various MkDocs plugins

### Local Development

To serve the documentation locally:

```bash
# From project root
mkdocs serve

# Or specify port
mkdocs serve -a localhost:8001
```

The documentation will be available at http://localhost:8000 (or your specified port).

The development server includes:
- Live reload on file changes
- Error reporting
- Search indexing

### Building Static Site

To build the static documentation:

```bash
# Build documentation
mkdocs build

# Output will be in site/ directory
ls site/
```

### Deploying to GitHub Pages

To deploy to GitHub Pages:

```bash
# Deploy to gh-pages branch
mkdocs gh-deploy
```

This will:
1. Build the documentation
2. Push to `gh-pages` branch
3. Make available at `https://[username].github.io/langchain-landuse/`

## Documentation Structure

```
docs/
├── index.md                 # Home page
├── getting-started/         # Installation and setup
│   ├── installation.md
│   ├── quickstart.md
│   └── configuration.md
├── queries/                 # Natural language query guide
│   ├── overview.md
│   ├── basic-queries.md
│   ├── advanced-queries.md
│   └── examples.md
├── data/                    # Data documentation
│   ├── sources.md
│   ├── schema.md
│   ├── categories.md
│   └── processing.md
├── api/                     # API reference
│   ├── agent.md
│   ├── converters.md
│   └── tools.md
├── examples/                # Use cases and workflows
│   ├── use-cases.md
│   ├── workflows.md
│   └── notebooks.md
└── development/             # Development guide
    ├── architecture.md
    ├── contributing.md
    └── testing.md
```

## Key Features

### Natural Language Query Focus

The documentation emphasizes the natural language query capabilities:
- Extensive query examples
- Pattern recognition guide
- Best practices for queries
- Real-world use cases

### Interactive Examples

Throughout the docs, you'll find:
- Copy-paste query examples
- Step-by-step workflows
- Expected outputs
- Troubleshooting tips

### Visual Elements

The Material theme provides:
- Syntax highlighting
- Mermaid diagrams
- Tabbed content
- Admonitions (notes, warnings)
- Search functionality

## Contributing to Docs

### Style Guide

- Use clear, concise language
- Include practical examples
- Provide expected outputs
- Use appropriate formatting

### Adding Examples

When adding query examples:
```markdown
**Query:**
\```
You> Show me forest to urban transitions
\```

**Response:**
\```
Query: SELECT * FROM landuse_transitions 
       WHERE from_land_use = 'Forest' AND to_land_use = 'Urban'
Results: 1,234 rows
[Table of results]
\```
```

### Creating Diagrams

Use Mermaid for diagrams:
```markdown
\```mermaid
graph LR
    A[Natural Language] --> B[LangChain Agent]
    B --> C[SQL Query]
    C --> D[Results]
\```
```

## Useful Commands

```bash
# Check for broken links
mkdocs serve --strict

# Build with verbose output
mkdocs build --verbose

# Clean build
mkdocs build --clean

# Deploy with custom commit message
mkdocs gh-deploy -m "Update documentation"
```

## Troubleshooting

### Common Issues

1. **Import errors**: Ensure all dependencies are installed
2. **Theme not found**: Install mkdocs-material
3. **Plugin errors**: Check plugin configuration in mkdocs.yml
4. **Build failures**: Run with --verbose for details

### Getting Help

- Check MkDocs documentation: https://www.mkdocs.org/
- Material theme docs: https://squidfunk.github.io/mkdocs-material/
- Project issues: https://github.com/yourusername/langchain-landuse/issues
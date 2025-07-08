# Knowledge Base Integration Guide

This guide explains how to use the vector store knowledge base feature to enhance the RPA Land Use Analytics agent with domain knowledge from markdown documentation.

## Overview

The knowledge base integration allows the agent to search through RPA Assessment documentation using semantic search, combining structured data queries with contextual information from official documents.

## Features

- **Semantic Search**: Uses OpenAI embeddings to find relevant documentation based on meaning
- **Automatic Indexing**: Processes markdown files and creates searchable chunks
- **Persistent Storage**: Uses Chroma vector database for efficient retrieval
- **Seamless Integration**: Works with the existing LangGraph agent architecture
- **No Technical Debt**: Implemented as a configurable feature in the existing agent

## Configuration

Enable the knowledge base by setting environment variables in your `.env` file:

```bash
# Enable knowledge base feature
LANDUSE_ENABLE_KNOWLEDGE_BASE=true

# Optional: customize paths (defaults shown)
LANDUSE_KNOWLEDGE_BASE_PATH=src/landuse/docs
LANDUSE_CHROMA_PERSIST_DIR=data/chroma_db
```

## Usage

### Command Line

When the knowledge base is enabled, the agent automatically gains access to a documentation search tool:

```bash
# Run the agent with knowledge base enabled
LANDUSE_ENABLE_KNOWLEDGE_BASE=true uv run rpa-analytics

# Or set it in your .env file and run normally
uv run rpa-analytics
```

### Python API

```python
from landuse.agents.landuse_agent import LanduseAgent
from landuse.config.landuse_config import LanduseConfig

# Create config with knowledge base enabled
config = LanduseConfig(enable_knowledge_base=True)

# Initialize agent
with LanduseAgent(config) as agent:
    # Query combining documentation and data
    response = agent.query(
        "What does the RPA Assessment say about forest loss? "
        "Also show me actual data for forest transitions."
    )
    print(response)
```

### Streamlit App

The knowledge base is automatically available in the Streamlit app when enabled:

```bash
LANDUSE_ENABLE_KNOWLEDGE_BASE=true uv run streamlit run streamlit_app.py
```

## Example Queries

The knowledge base enables new types of queries that combine documentation context with data analysis:

### Documentation-Only Queries
- "What are the key findings from the RPA Assessment about land development threats?"
- "What climate scenarios does the RPA Assessment use?"
- "Explain the wildland-urban interface according to the RPA documentation"

### Combined Documentation and Data Queries
- "What does the RPA Assessment say about drought projections? Show me rangeland data for western states."
- "According to the RPA documentation, which regions face the most forest loss? Show me the actual data."
- "Explain the RPA's methodology for land use projections and show me an example from the database."

## How It Works

1. **Document Loading**: The `RPAKnowledgeBase` class loads markdown files from `src/landuse/docs/`
2. **Text Splitting**: Documents are split into chunks while preserving context
3. **Embedding Generation**: Each chunk is converted to a vector embedding using OpenAI
4. **Vector Storage**: Embeddings are stored in Chroma for fast similarity search
5. **Tool Integration**: A retriever tool is added to the agent's toolset
6. **Query Processing**: The agent can now search documentation when answering questions

## Architecture

```
LanduseAgent
├── Standard Tools
│   ├── execute_landuse_query
│   ├── analyze_landuse_results
│   └── explore_landuse_schema
└── Knowledge Base Tool (when enabled)
    └── search_rpa_documentation
        └── RPAKnowledgeBase
            ├── Document Loader
            ├── Text Splitter
            ├── Embeddings (OpenAI)
            └── Vector Store (Chroma)
```

## Performance Considerations

- **Initial Setup**: First run will process all documents and create embeddings (one-time cost)
- **Subsequent Runs**: Vector store is persisted to disk for fast loading
- **Query Performance**: Semantic search typically returns results in <1 second
- **Storage**: Vector database requires ~50-100MB depending on document volume

## Troubleshooting

### Knowledge Base Not Loading
- Check that `OPENAI_API_KEY` is set (required for embeddings)
- Verify markdown documents exist in `src/landuse/docs/`
- Ensure write permissions for `data/chroma_db/` directory

### Slow Initial Loading
- First run processes all documents; subsequent runs load from disk
- Use `force_rebuild=True` to recreate the vector store if needed

### Search Not Finding Expected Results
- The knowledge base uses semantic search, not keyword matching
- Try rephrasing queries to be more specific
- Check that relevant content exists in the markdown files

## Adding New Documentation

To add new documentation to the knowledge base:

1. Add markdown files to `src/landuse/docs/`
2. Delete the existing vector store: `rm -rf data/chroma_db/`
3. Run the agent - it will automatically rebuild the index

## Dependencies

The knowledge base feature requires additional packages:
- `chromadb`: Vector database for storing embeddings
- `unstructured`: Document parsing and processing
- `markdown`: Markdown file support

These are installed automatically when you run `uv sync`.

## Future Enhancements

Potential improvements for the knowledge base:

1. **Multiple Document Sources**: Support for PDFs, Word docs, etc.
2. **Dynamic Updates**: Add new documents without rebuilding
3. **Query Optimization**: Fine-tune retrieval parameters
4. **Caching**: Cache frequently accessed documentation chunks
5. **Multi-Modal Search**: Support for tables, charts, and images
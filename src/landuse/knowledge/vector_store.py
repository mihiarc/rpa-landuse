"""
Vector store implementation for loading and querying RPA Assessment markdown documentation.
"""

import os
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from langchain.tools.retriever import create_retriever_tool
from langchain_chroma import Chroma
from langchain_community.document_loaders import UnstructuredMarkdownLoader
from langchain_community.vectorstores.utils import filter_complex_metadata
from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

# Load environment variables
load_dotenv("config/.env")

console = Console()


class RPAKnowledgeBase:
    """Manages the RPA Assessment documentation knowledge base using vector store."""

    def __init__(
        self,
        docs_path: str = "src/landuse/docs",
        persist_directory: str = "data/chroma_db",
        collection_name: str = "rpa_assessment_docs"
    ):
        """
        Initialize the RPA Knowledge Base.

        Args:
            docs_path: Path to the markdown documentation
            persist_directory: Directory to persist the vector store
            collection_name: Name of the Chroma collection
        """
        self.docs_path = Path(docs_path)
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.embeddings = OpenAIEmbeddings()
        self.vector_store = None
        self.retriever = None

    def load_documents(self) -> List[Document]:
        """Load all markdown documents from the docs directory."""
        documents = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Loading markdown documents...", total=None)

            for md_file in self.docs_path.glob("*.md"):
                progress.update(task, description=f"Loading {md_file.name}...")

                loader = UnstructuredMarkdownLoader(
                    str(md_file),
                    mode="elements",
                    strategy="fast"
                )
                docs = loader.load()

                # Add metadata about source file
                for doc in docs:
                    doc.metadata["source_file"] = md_file.name
                    doc.metadata["chapter"] = md_file.stem

                documents.extend(docs)

        console.print(f"[green]✓ Loaded {len(documents)} document chunks from {len(list(self.docs_path.glob('*.md')))} files[/green]")
        return documents

    def split_documents(self, documents: List[Document]) -> List[Document]:
        """Split documents into smaller chunks for better retrieval."""
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1500,
            chunk_overlap=200,
            separators=["\n\n", "\n", ".", " ", ""],
            length_function=len,
        )

        console.print("Splitting documents into chunks...")
        chunks = text_splitter.split_documents(documents)
        console.print(f"[green]✓ Created {len(chunks)} chunks[/green]")

        return chunks

    def create_vector_store(self, documents: List[Document]) -> None:
        """Create or update the vector store with documents."""
        console.print("Creating vector store...")

        # Filter out complex metadata that Chroma can't handle
        filtered_docs = filter_complex_metadata(documents)

        self.vector_store = Chroma.from_documents(
            documents=filtered_docs,
            embedding=self.embeddings,
            collection_name=self.collection_name,
            persist_directory=self.persist_directory
        )

        console.print(f"[green]✓ Vector store created with {len(filtered_docs)} chunks[/green]")

    def load_vector_store(self) -> None:
        """Load existing vector store from disk."""
        console.print("Loading existing vector store...")

        self.vector_store = Chroma(
            collection_name=self.collection_name,
            embedding_function=self.embeddings,
            persist_directory=self.persist_directory
        )

        console.print("[green]✓ Vector store loaded[/green]")

    def initialize(self, force_rebuild: bool = False) -> None:
        """
        Initialize the knowledge base, creating vector store if needed.

        Args:
            force_rebuild: Whether to rebuild the vector store even if it exists
        """
        persist_path = Path(self.persist_directory)

        if persist_path.exists() and not force_rebuild:
            # Load existing vector store
            self.load_vector_store()
        else:
            # Build new vector store
            console.print("[yellow]Building new vector store...[/yellow]")
            documents = self.load_documents()
            chunks = self.split_documents(documents)
            self.create_vector_store(chunks)

        # Create retriever
        self.retriever = self.vector_store.as_retriever(
            search_type="mmr",  # Maximum Marginal Relevance for diversity
            search_kwargs={
                "k": 5,  # Return top 5 results
                "fetch_k": 10,  # Fetch 10 to select 5 from
                "lambda_mult": 0.5  # Balance between relevance and diversity
            }
        )

    def create_retriever_tool(self):
        """Create a LangChain tool for the retriever."""
        if not self.retriever:
            raise ValueError("Knowledge base not initialized. Call initialize() first.")

        return create_retriever_tool(
            self.retriever,
            "search_rpa_documentation",
            "Search the RPA Assessment documentation for information about land use, "
            "climate scenarios, forest resources, rangelands, water resources, biodiversity, "
            "recreation, and socioeconomic trends. Use this tool when you need specific "
            "information from the official RPA Assessment reports."
        )

    def search(self, query: str, k: int = 5) -> List[Document]:
        """
        Search the knowledge base for relevant documents.

        Args:
            query: Search query
            k: Number of results to return

        Returns:
            List of relevant documents
        """
        if not self.vector_store:
            raise ValueError("Knowledge base not initialized. Call initialize() first.")

        return self.vector_store.similarity_search(query, k=k)

    def search_with_score(self, query: str, k: int = 5) -> List[tuple[Document, float]]:
        """
        Search with relevance scores.

        Args:
            query: Search query
            k: Number of results to return

        Returns:
            List of (document, score) tuples
        """
        if not self.vector_store:
            raise ValueError("Knowledge base not initialized. Call initialize() first.")

        return self.vector_store.similarity_search_with_score(query, k=k)


if __name__ == "__main__":
    # Test the knowledge base
    kb = RPAKnowledgeBase()
    kb.initialize(force_rebuild=True)

    # Test search
    console.print("\n[yellow]Testing search functionality...[/yellow]")

    test_queries = [
        "What are the climate scenarios used in RPA?",
        "How much forest land will be lost by 2070?",
        "What is the wildland-urban interface?",
        "Tell me about drought projections"
    ]

    for query in test_queries:
        console.print(f"\n[cyan]Query: {query}[/cyan]")
        results = kb.search(query, k=3)

        for i, doc in enumerate(results, 1):
            console.print(f"\n[green]Result {i}:[/green]")
            console.print(f"Source: {doc.metadata.get('source_file', 'Unknown')}")
            console.print(f"Content: {doc.page_content[:200]}...")

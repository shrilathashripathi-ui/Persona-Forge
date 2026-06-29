"""
embedder/embed.py

Takes the clean CSV and:
1. Embeds each row using a FREE local model (no OpenAI key needed)
2. Stores everything in a local Chroma vector database

Embedding model: all-MiniLM-L6-v2 via sentence-transformers
- Downloads once (~90MB), runs locally forever after
- Zero cost, works offline
- Quality is slightly below OpenAI's model but more than good enough
  for style retrieval on short texts like tweets

The Chroma DB is saved to data/chroma_{handle}/ so it persists
between sessions. No need to re-embed every time.

Usage:
    python embedder/embed.py --handle kunalb11
"""

import argparse
import pandas as pd
from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions


def get_embedding_function():
    """
    Returns a local sentence-transformer embedding function.

    First call downloads the model (~90MB) from HuggingFace.
    Every subsequent call loads it from local cache — instant.

    Why all-MiniLM-L6-v2?
    - Fast (6 layers, lightweight)
    - Good semantic understanding for short texts
    - Most popular open-source embedding model — well tested
    """
    return embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )


def build_vector_store(handle: str) -> chromadb.Collection:
    """
    Loads the clean CSV, embeds all rows, stores in Chroma.

    Args:
        handle: Twitter handle used to find the clean CSV

    Returns:
        The Chroma collection (ready to query)
    """
    clean_path = Path("data") / f"clean_{handle}.csv"
    if not clean_path.exists():
        raise FileNotFoundError(
            f"No clean data at {clean_path}. Run cleaner/clean.py first."
        )

    df = pd.read_csv(clean_path)
    print(f"Loaded {len(df)} rows from {clean_path}")

    print("Loading embedding model (downloads ~90MB on first run)...")
    ef = get_embedding_function()
    print("Embedding model ready.")

    # Chroma persists the DB to disk so you don't re-embed every time
    db_path = str(Path("data") / f"chroma_{handle}")
    chroma_client = chromadb.PersistentClient(path=db_path)

    # Get or create a collection (like a table in a SQL DB)
    collection = chroma_client.get_or_create_collection(
        name=f"persona_{handle}",
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},  # cosine similarity works best for text
    )

    # Check if already populated — skip re-embedding if so
    existing = collection.count()
    if existing > 0:
        print(f"Collection already has {existing} embeddings. Skipping re-embedding.")
        print(f"(Delete data/chroma_{handle}/ folder to force re-embed)")
        return collection

    # Build documents, IDs, and metadata for Chroma
    documents = df["text"].tolist()
    ids = [f"doc_{i}" for i in range(len(documents))]
    metadatas = [
        {"source": row["source"], "url": str(row.get("url", ""))}
        for _, row in df.iterrows()
    ]

    # Embed and store in batches
    print(f"Embedding {len(documents)} documents... (may take 2-4 mins on first run)")

    BATCH_SIZE = 100
    for i in range(0, len(documents), BATCH_SIZE):
        collection.add(
            documents=documents[i:i + BATCH_SIZE],
            ids=ids[i:i + BATCH_SIZE],
            metadatas=metadatas[i:i + BATCH_SIZE],
        )
        print(f"  Embedded {min(i + BATCH_SIZE, len(documents))}/{len(documents)}")

    print(f"\nDone. {collection.count()} embeddings stored at {db_path}")
    return collection


def query_similar(
    collection: chromadb.Collection,
    query: str,
    n_results: int = 8
) -> list[str]:
    """
    Given a topic/query, retrieves the most stylistically relevant chunks.

    These get injected into the Claude prompt as style examples.

    Args:
        collection: The Chroma collection
        query:      What the user wants to write about
        n_results:  How many examples to retrieve (8 is a good balance)

    Returns:
        List of text chunks, most similar first
    """
    results = collection.query(
        query_texts=[query],
        n_results=n_results,
    )
    return results["documents"][0]


def load_collection(handle: str) -> chromadb.Collection:
    """
    Loads an existing Chroma collection without re-embedding.
    Used by app.py on startup — fast after first load.
    """
    ef = get_embedding_function()

    db_path = str(Path("data") / f"chroma_{handle}")
    chroma_client = chromadb.PersistentClient(path=db_path)

    collection = chroma_client.get_collection(
        name=f"persona_{handle}",
        embedding_function=ef,
    )
    return collection


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Embed clean data into Chroma vector store")
    parser.add_argument("--handle", required=True, help="Twitter handle")
    args = parser.parse_args()

    build_vector_store(args.handle)

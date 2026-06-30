"""
setup.py

One-command setup for pre-built personas shipped with persona-forge.
Embeds the pre-cleaned CSV into a local Chroma vector DB.

Usage:
    python setup.py --persona kunalb11
    python setup.py --persona naval
    python setup.py --persona rajshamani
    python setup.py --all                  # embed all three at once

Pre-built personas available:
    kunalb11    — Kunal Shah
    naval       — Naval Ravikant
    rajshamani  — Raj Shamani

The embedding model (~90MB) downloads once on first run, then cached forever.
Each persona takes ~2-4 minutes to embed.
"""

import argparse
import shutil
from pathlib import Path
import pandas as pd
import chromadb
from chromadb.utils import embedding_functions


AVAILABLE_PERSONAS = {
    "kunalb11":   "Kunal Shah",
    "naval":      "Naval Ravikant",
    "rajshamani": "Raj Shamani",
}


def get_embedding_function():
    """Local sentence-transformer embeddings — free, no API key needed."""
    return embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )


def embed_persona(handle: str) -> None:
    """
    Reads the pre-cleaned CSV from personas/{handle}/
    and builds a local Chroma vector DB in data/chroma_{handle}/

    Args:
        handle: persona identifier e.g. "kunalb11"
    """
    name = AVAILABLE_PERSONAS.get(handle, handle)
    csv_path = Path("personas") / handle / f"clean_{handle}.csv"

    if not csv_path.exists():
        print(f"ERROR: {csv_path} not found.")
        print(f"Make sure you have the latest version of the repo.")
        return

    # Check if already embedded
    chroma_path = Path("data") / f"chroma_{handle}"
    if chroma_path.exists():
        print(f"'{name}' is already set up at {chroma_path}")
        print(f"To re-embed, delete {chroma_path} and run again.")
        return

    df = pd.read_csv(csv_path)
    print(f"\nSetting up '{name}' ({len(df)} samples)...")
    print("Loading embedding model (downloads ~90MB on first run, then cached)...")

    ef = get_embedding_function()
    print("Model ready. Embedding...")

    Path("data").mkdir(exist_ok=True)
    client = chromadb.PersistentClient(path=str(chroma_path))
    collection = client.get_or_create_collection(
        name=f"persona_{handle}",
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )

    documents = df["text"].tolist()
    ids = [f"doc_{i}" for i in range(len(documents))]
    metadatas = [
        {"source": row["source"], "url": str(row.get("url", ""))}
        for _, row in df.iterrows()
    ]

    BATCH_SIZE = 100
    for i in range(0, len(documents), BATCH_SIZE):
        collection.add(
            documents=documents[i:i + BATCH_SIZE],
            ids=ids[i:i + BATCH_SIZE],
            metadatas=metadatas[i:i + BATCH_SIZE],
        )
        print(f"  {min(i + BATCH_SIZE, len(documents))}/{len(documents)} embedded")

    print(f"Done. '{name}' is ready — {collection.count()} embeddings stored.")


def main():
    parser = argparse.ArgumentParser(
        description="Set up pre-built personas for persona-forge"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--persona",
        choices=list(AVAILABLE_PERSONAS.keys()),
        help="Which persona to set up",
    )
    group.add_argument(
        "--all",
        action="store_true",
        help="Set up all pre-built personas",
    )
    group.add_argument(
        "--list",
        action="store_true",
        help="List available pre-built personas",
    )
    args = parser.parse_args()

    if args.list:
        print("\nAvailable pre-built personas:")
        for handle, name in AVAILABLE_PERSONAS.items():
            chroma_path = Path("data") / f"chroma_{handle}"
            status = "[ready]" if chroma_path.exists() else "[not set up]"
            print(f"  {handle:<15} {name:<20} {status}")
        return

    if args.all:
        print(f"Setting up all {len(AVAILABLE_PERSONAS)} personas...")
        for handle in AVAILABLE_PERSONAS:
            embed_persona(handle)
        print("\nAll personas ready. Run: streamlit run app.py")
    else:
        embed_persona(args.persona)
        print(f"\nRun: streamlit run app.py")


if __name__ == "__main__":
    main()

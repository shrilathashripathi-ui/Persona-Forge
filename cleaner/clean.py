"""
cleaner/clean.py

Takes raw scraped data (tweets + transcripts) and produces
a single clean CSV ready for embedding.

What it filters out:
- Retweets (start with "RT @")
- Reply-only tweets (start with "@someone")
- Tweets under 30 characters (too short to carry style signal)
- Duplicate tweets
- Tweets that are just URLs

Usage:
    python cleaner/clean.py --handle kunalb11
"""

import json
import re
import argparse
import pandas as pd
from pathlib import Path


# ── Tweet cleaning ────────────────────────────────────────────────────────────

def is_noise(text: str) -> bool:
    """Returns True if the tweet should be filtered out."""
    text = text.strip()
    if text.startswith("RT @"):           return True   # retweet
    if text.startswith("@"):              return True   # reply with no context
    if len(text) < 30:                    return True   # too short
    if re.match(r"^https?://\S+$", text): return True   # just a URL
    return False


def clean_tweet_text(text: str) -> str:
    """Cleans up a tweet string."""
    # Remove URLs (they add noise, not style)
    text = re.sub(r"https?://\S+", "", text)
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def load_and_clean_tweets(handle: str) -> pd.DataFrame:
    """Loads raw tweets JSON and returns a clean DataFrame."""
    raw_path = Path("data") / f"raw_tweets_{handle}.json"
    if not raw_path.exists():
        print(f"No tweet file found at {raw_path}. Run the scraper first.")
        return pd.DataFrame()

    with open(raw_path, encoding="utf-8") as f:
        raw = json.load(f)

    print(f"Loaded {len(raw)} raw tweets.")

    rows = []
    for tweet in raw:
        # Apify's Twitter scraper returns "text" or "full_text"
        text = tweet.get("text") or tweet.get("full_text") or ""
        text = clean_tweet_text(text)

        if is_noise(text):
            continue

        rows.append({
            "source": "twitter",
            "text": text,
            "url": tweet.get("url", ""),
        })

    df = pd.DataFrame(rows).drop_duplicates(subset="text")
    print(f"Cleaned tweets: {len(df)} kept (from {len(raw)} raw).")
    return df


# ── Transcript cleaning ───────────────────────────────────────────────────────

def chunk_transcript(text: str, chunk_size: int = 800) -> list[str]:
    """
    Splits a long transcript into overlapping chunks.

    Why chunk? LLMs have context limits. We want each chunk to be
    self-contained enough to carry style signal.

    chunk_size: ~800 chars ≈ ~200 tokens, good balance for style
    """
    words = text.split()
    chunks = []
    step = chunk_size // 2  # 50% overlap so style context isn't lost at edges

    for i in range(0, len(words), step):
        chunk = " ".join(words[i:i + chunk_size])
        if len(chunk) > 100:  # skip tiny tail chunks
            chunks.append(chunk)

    return chunks


def load_and_clean_transcripts(handle: str) -> pd.DataFrame:
    """Loads raw transcripts JSON and returns chunked clean DataFrame."""
    raw_path = Path("data") / f"raw_transcripts_{handle}.json"
    if not raw_path.exists():
        print(f"No transcript file found at {raw_path}. Run the YouTube scraper first.")
        return pd.DataFrame()

    with open(raw_path, encoding="utf-8") as f:
        raw = json.load(f)

    print(f"Loaded {len(raw)} raw transcripts.")

    rows = []
    for item in raw:
        transcript = item.get("transcript", "").strip()
        if not transcript:
            continue

        # Each transcript gets split into overlapping chunks
        for chunk in chunk_transcript(transcript):
            rows.append({
                "source": "youtube",
                "text": chunk,
                "url": item.get("url", ""),
            })

    df = pd.DataFrame(rows).drop_duplicates(subset="text")
    print(f"Cleaned transcripts: {len(df)} chunks (from {len(raw)} videos).")
    return df


# ── Main ──────────────────────────────────────────────────────────────────────

def clean_all(handle: str) -> Path:
    """Merges cleaned tweets + transcripts into one CSV."""
    tweets_df = load_and_clean_tweets(handle)
    transcripts_df = load_and_clean_transcripts(handle)

    # Combine whatever we have
    all_dfs = [df for df in [tweets_df, transcripts_df] if not df.empty]
    if not all_dfs:
        print("No data to clean. Run the scrapers first.")
        return None

    combined = pd.concat(all_dfs, ignore_index=True)
    combined = combined.drop_duplicates(subset="text").reset_index(drop=True)

    output_path = Path("data") / f"clean_{handle}.csv"
    combined.to_csv(output_path, index=False, encoding="utf-8")

    print(f"\nFinal clean dataset: {len(combined)} rows")
    print(f"  Twitter: {len(combined[combined.source == 'twitter'])} rows")
    print(f"  YouTube: {len(combined[combined.source == 'youtube'])} rows")
    print(f"Saved to {output_path}")
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clean scraped data for a persona")
    parser.add_argument("--handle", required=True, help="Twitter handle (used to find data files)")
    args = parser.parse_args()

    clean_all(args.handle)

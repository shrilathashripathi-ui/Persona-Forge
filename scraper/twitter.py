"""
scraper/twitter.py

Scrapes tweets from a given Twitter/X handle using Apify.
Saves raw results to data/raw_tweets_{handle}.json

Usage:
    python scraper/twitter.py --handle kunalb11 --max 2000
"""

import os
import json
import argparse
from pathlib import Path
from apify_client import ApifyClient
from dotenv import load_dotenv

load_dotenv()


def scrape_tweets(handle: str, max_tweets: int = 2000) -> list[dict]:
    api_token = os.getenv("APIFY_API_TOKEN")
    if not api_token:
        raise ValueError("APIFY_API_TOKEN not found. Check your .env file.")

    client = ApifyClient(api_token)

    print(f"Starting scrape for @{handle} — requesting {max_tweets} tweets...")

    run_input = {
        "mode": "user-tweets",
        "usernames": [handle],
        "maxResults": max_tweets,
        "includeReplies": False,
    }

    run = client.actor("automation-lab/twitter-scraper").call(run_input=run_input)

    dataset_id = (
        run.default_dataset_id
        if hasattr(run, "default_dataset_id")
        else run["defaultDatasetId"]
    )

    print(f"Scrape complete. Fetching results from dataset {dataset_id}...")

    tweets = []
    for item in client.dataset(dataset_id).iterate_items():
        tweets.append(item)

    print(f"Fetched {len(tweets)} tweets.")
    return tweets


def save_tweets(tweets: list[dict], handle: str) -> Path:
    output_dir = Path("data")
    output_dir.mkdir(exist_ok=True)

    output_path = output_dir / f"raw_tweets_{handle}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(tweets, f, ensure_ascii=False, indent=2)

    print(f"Saved to {output_path}")
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape tweets from a Twitter handle")
    parser.add_argument("--handle", required=True, help="Twitter handle without @")
    parser.add_argument("--max", type=int, default=2000, help="Max tweets to scrape")
    args = parser.parse_args()

    tweets = scrape_tweets(args.handle, args.max)
    save_tweets(tweets, args.handle)
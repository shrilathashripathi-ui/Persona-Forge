"""
scraper/youtube.py

Fetches transcripts from a list of YouTube video URLs.
URLs are read from youtube_urls.txt — one URL per line.
Saves results to data/raw_transcripts_{handle}.json

Usage:
    python scraper/youtube.py --handle kunalb11

youtube_urls.txt format (one URL per line, # for comments):
    https://www.youtube.com/watch?v=abc123
    https://www.youtube.com/watch?v=def456
    # this line is ignored
"""

import json
import re
import argparse
from pathlib import Path
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled


def extract_video_id(url: str) -> str | None:
    """
    Extracts the YouTube video ID from any common URL format.

    Handles:
        https://www.youtube.com/watch?v=abc123
        https://youtu.be/abc123
        https://www.youtube.com/embed/abc123
    """
    patterns = [
        r"youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})",
        r"youtu\.be/([a-zA-Z0-9_-]{11})",
        r"youtube\.com/embed/([a-zA-Z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def load_urls(filepath: str = "youtube_urls.txt") -> list[str]:
    """
    Reads YouTube URLs from a text file.
    Skips blank lines and lines starting with #.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(
            f"'{filepath}' not found.\n"
            "Create it in your project folder with one YouTube URL per line."
        )

    urls = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                urls.append(line)

    print(f"Loaded {len(urls)} URLs from {filepath}")
    return urls


def fetch_transcript(video_id: str, url: str) -> dict | None:
    try:
        api = YouTubeTranscriptApi()
        fetched = api.fetch(video_id, languages=["en", "en-IN", "en-GB"])
        full_text = " ".join(snippet.text for snippet in fetched)
        return {
            "video_id": video_id,
            "url": url,
            "transcript": full_text,
        }
    except Exception as e:
        print(f"  Error ({type(e).__name__}): {e} — skipping.")
        return None


def scrape_from_url_file(url_file: str = "youtube_urls.txt") -> list[dict]:
    """
    Main function — reads URLs from file, fetches transcripts for each.
    """
    urls = load_urls(url_file)

    if not urls:
        print("No URLs found in file. Add some YouTube links and try again.")
        return []

    transcripts = []
    for i, url in enumerate(urls, 1):
        video_id = extract_video_id(url)

        if not video_id:
            print(f"[{i}/{len(urls)}] Could not extract video ID from: {url} — skipping.")
            continue

        print(f"[{i}/{len(urls)}] Fetching transcript for {video_id}...")
        result = fetch_transcript(video_id, url)
        if result:
            transcripts.append(result)
            print(f"  Got {len(result['transcript'].split())} words.")

    print(f"\nDone: {len(transcripts)} transcripts fetched out of {len(urls)} URLs.")
    return transcripts


def save_transcripts(transcripts: list[dict], handle: str) -> Path:
    """Saves transcripts to data/raw_transcripts_{handle}.json"""
    output_dir = Path("data")
    output_dir.mkdir(exist_ok=True)

    output_path = output_dir / f"raw_transcripts_{handle}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(transcripts, f, ensure_ascii=False, indent=2)

    print(f"Saved to {output_path}")
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fetch YouTube transcripts from URLs listed in a text file"
    )
    parser.add_argument(
        "--handle",
        required=True,
        help="Name used for the output file e.g. kunalb11",
    )
    parser.add_argument(
        "--url-file",
        default=None,
        help="Path to text file containing YouTube URLs. "
             "Defaults to personas/{handle}/youtube_urls.txt if it exists, "
             "else youtube_urls.txt",
    )
    args = parser.parse_args()

    if args.url_file:
        url_file = args.url_file
    else:
        persona_urls = Path("personas") / args.handle / "youtube_urls.txt"
        url_file = str(persona_urls) if persona_urls.exists() else "youtube_urls.txt"

    print(f"Using URL file: {url_file}")
    transcripts = scrape_from_url_file(url_file)
    save_transcripts(transcripts, args.handle)

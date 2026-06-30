# 🎭 Persona Forge

Clone the writing style of any public thinker using their actual Twitter posts and YouTube transcripts — powered by RAG + Claude.

**Not a chatbot. Not a persona simulator.** Specifically built for one thing: writing new content in someone's authentic style, grounded in their real words.

---

## Pre-built personas

Three personas ship with the repo — just run setup and they're ready:

| Persona | Handle | Style | Data |
|---------|--------|-------|------|
| Kunal Shah | `kunalb11` | Contrarian insight, trust/wealth frameworks, dense observations | 132 samples |
| Naval Ravikant | `naval` | Philosophical, aphoristic, wealth + happiness + leverage | 196 samples (tweets + transcripts) |
| Raj Shamani | `rajshamani` | Storytelling, entrepreneurship narrative, conversational energy | 10 samples (tweets only — his YouTube videos had Hindi-only captions) |

> Kunal and Naval give the richest output. Raj is thinner for now — add English YouTube videos to `personas/rajshamani/youtube_urls.txt` and re-run the pipeline to enrich him.

---

## Quickstart

### 1. Clone and install

```bash
git clone https://github.com/shrilathashripathi-ui/Persona-Forge
cd Persona-Forge
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Set up your Anthropic API key

You have two options:

- **In the app (easiest):** just run the app and paste your key into the sidebar field. It's used only for your browser session and never stored.
- **Via `.env` (handy for local dev):** create a `.env` file so the key pre-fills automatically:

  ```
  ANTHROPIC_API_KEY=sk-ant-...
  ```

You only need this one key to *use* the app. Scraping new personas needs an Apify token (see below).

> Get an Anthropic key at [console.anthropic.com](https://console.anthropic.com). Each generation costs ~$0.01. Note: a claude.ai subscription does **not** cover API access — it's billed separately.

### 3. Set up pre-built personas

```bash
python setup.py --all        # set up all three personas
python setup.py --list       # see what's available and ready
```

This copies the clean CSV for each persona into `data/` and runs the embedder.

### 4. Run the app

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## Adding a new persona

### API key needed for scraping

| Key | Where to get it | Used for |
|-----|----------------|----------|
| `APIFY_API_TOKEN` | [apify.com](https://apify.com) → Settings → Integrations | Twitter scraping |

Add to `.env`:
```
APIFY_API_TOKEN=apify_api_...
```

### Option A — from the app (easiest)

Open the **"➕ Add a new persona from a Twitter/X handle"** section on the main screen:

1. Enter a public Twitter/X handle (e.g. `paulg`)
2. Pick how many recent tweets to pull (10–200)
3. Click **Build persona**

The app scrapes → cleans → embeds in-process, shows live progress, and the new persona appears in the dropdown when it's done. This is Twitter-only — for richer personas with YouTube transcripts, use the CLI pipeline below.

### Option B — full CLI pipeline (Twitter + YouTube)

For a richer persona that also includes YouTube transcripts, or to re-scrape an existing one:

```bash
# 1. Scrape tweets
python scraper/twitter.py --handle rajshamani --max 2000

# 2. Add YouTube URLs to personas/rajshamani/youtube_urls.txt (one per line)
#    Then scrape transcripts — automatically reads from that file:
python scraper/youtube.py --handle rajshamani

# 3. Clean everything into one CSV
python cleaner/clean.py --handle rajshamani

# 4. Embed into vector store
python embedder/embed.py --handle rajshamani
```

The app auto-detects all embedded personas on startup.

### Save clean data for the repo

Once you're happy with the clean CSV, copy it into the persona folder so others can use `setup.py`:

```bash
copy data\clean_rajshamani.csv personas\rajshamani\clean_rajshamani.csv
```

---

## Project structure

```
persona-forge/
├── personas/
│   ├── kunalb11/
│   │   ├── clean_kunalb11.csv       # pre-cleaned data (ships in repo)
│   │   └── youtube_urls.txt         # YouTube URLs for this persona
│   ├── naval/
│   │   ├── clean_naval.csv
│   │   └── youtube_urls.txt
│   └── rajshamani/
│       ├── clean_rajshamani.csv
│       └── youtube_urls.txt
├── scraper/
│   ├── twitter.py      # Apify → raw tweets JSON
│   └── youtube.py      # YouTube transcript API → raw JSON
├── cleaner/
│   └── clean.py        # Filter noise, chunk transcripts → clean CSV
├── embedder/
│   └── embed.py        # Embed + store in Chroma vector DB
├── setup.py            # One-command setup for pre-built personas
├── app.py              # Streamlit web UI
└── requirements.txt
```

---

## How it works

**RAG (Retrieval-Augmented Generation)** — the core technique:

1. All scraped text is converted to embeddings (vectors that represent meaning)
2. When you type a topic, it's also converted to a vector
3. The most semantically similar chunks from the persona's writing are retrieved
4. These real examples are injected into a Claude prompt as style conditioning
5. Claude writes new content using those examples as a style reference — not from general knowledge

This is why the output doesn't sound like generic AI — it's anchored in the actual person's word patterns.

Embedding runs locally using `all-MiniLM-L6-v2` via sentence-transformers (~90MB, downloads once, zero ongoing cost).

---

## Limitations

- Style mimicry captures surface patterns (vocabulary, rhythm, structure), not deep reasoning
- Quality depends on data volume — more tweets/transcripts = better output
- Auto-generated YouTube captions can be messy; manual transcripts work better
- Twitter data is limited to what Apify can access (public tweets only)

---

## License

MIT — use it, fork it, build on it.

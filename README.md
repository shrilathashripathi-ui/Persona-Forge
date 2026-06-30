# 🎭 Persona Forge

Clone the writing style of any public thinker using their actual Twitter posts and YouTube transcripts — powered by RAG + Claude.

**Not a chatbot. Not a persona simulator.** Specifically built for one thing: writing new content in someone's authentic style, grounded in their real words.

---

## Pre-built personas

Three personas ship with the repo — just run setup and they're ready:

| Persona | Handle | Style |
|---------|--------|-------|
| Kunal Shah | `kunalb11` | Contrarian insight, trust/wealth frameworks, dense observations |
| Naval Ravikant | `naval` | Philosophical, aphoristic, wealth + happiness + leverage |
| Raj Shamani | `rajshamani` | Storytelling, entrepreneurship narrative, conversational energy |

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

### 2. Set up API keys

Create a `.env` file with your Anthropic key:

```
ANTHROPIC_API_KEY=sk-ant-...
```

You only need this one key to run the app. Scraping needs additional keys (see below).

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

## Adding a custom persona from scratch

If you want to build a new persona (or re-scrape an existing one):

### API keys needed for scraping

| Key | Where to get it | Used for |
|-----|----------------|----------|
| `APIFY_API_TOKEN` | [apify.com](https://apify.com) → Settings → Integrations | Twitter scraping (~$5–15 per 2,000 tweets) |

Add to `.env`:
```
APIFY_API_TOKEN=apify_api_...
```

### Run the pipeline

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
